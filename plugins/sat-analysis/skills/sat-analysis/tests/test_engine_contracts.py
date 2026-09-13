"""Behavioral tests of strict portable contracts, separate from analytic validity."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import struct
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator
from referencing import Registry

from sat_engine import validators
from sat_engine.models import AnalysisRequest, NormalizedAnalysisRequest, Observation
from sat_engine.validators import (
    SCHEMA_KINDS, ValidationFailure, canonical_bytes, content_hash, load_schema,
    loads_json, validate,
)


def observation(**fields: object) -> dict:
    return {"schema_version": "1", "id": "O1", "raw": "unaltered source", "source": "inline", "parse_status": "unparsed", **fields}


def request(**fields: object) -> dict:
    return {"schema_version": "1", "mode": "FULL", "submode": "GENERAL", "question": "What is established?", **fields}


def empty_timeline() -> dict:
    return {
        "schema_version": "1", "events": [], "gap_threshold_seconds": 300,
        "rapid_threshold_seconds": 1,
        "analysis": {
            "total_events": 0, "resolved_events": 0, "unresolved_events": 0,
            "parse_counts": {"parsed": 0, "unparsed": 0, "rejected": 0},
            "time_range": {"first": None, "last": None}, "actors": {},
            "tag_sequences": [], "rapid_succession": [], "gaps": [], "caveats": [],
        },
    }


def empty_matrix() -> dict:
    assessment = {
        "status": "insufficient_evidence", "heuristic_leaders": [], "winner": None,
        "missing_ratings": [], "caveats": [], "scores": {}, "contradictions": {},
        "contributing_record_count": 0,
    }
    return {
        "schema_version": "1", "title": "Q", "relationship": "unspecified",
        "hypotheses": [], "evidence": [], "assessment": assessment,
        "diagnosticity": {}, "sensitivity": {
            "base_assessment": deepcopy(assessment), "base_scores": {}, "base_winner": None,
            "evidence_impact": {}, "group_impact": {}, "heuristic_stable": None,
            "caveat": "No tested heuristic stability is available.",
        },
    }


class JSONPortabilityTests(unittest.TestCase):
    def test_duplicate_keys_rejected_at_any_depth_and_after_escape_decoding(self) -> None:
        for text in ('{"a":1,"a":2}', '{"items":[{"a":1,"a":2}]}', '{"a":1,"\\u0061":2}'):
            with self.subTest(text=text), self.assertRaises(ValidationFailure) as caught:
                loads_json(text)
            self.assertEqual(caught.exception.code, "duplicate_key")

    def test_nonfinite_constants_and_overflow_rejected(self) -> None:
        for text in ("NaN", "Infinity", "-Infinity", "1e400", '{"x":-1e999}'):
            with self.subTest(text=text), self.assertRaises(ValidationFailure) as caught:
                loads_json(text)
            self.assertEqual(caught.exception.code, "nonfinite_number")

    def test_malformed_json_is_structured_failure(self) -> None:
        for text in ('{"x":}', '/*comment*/{}', b'{"x":"\xff"}', '{}{}'):
            with self.subTest(text=text), self.assertRaises(ValidationFailure) as caught:
                loads_json(text)
            self.assertEqual(caught.exception.code, "invalid_json")

    def test_large_integers_are_not_silently_rounded(self) -> None:
        for number in (2**53, -(2**53), 10**60):
            for operation in (lambda: canonical_bytes(number), lambda: loads_json(str(number))):
                with self.subTest(number=number), self.assertRaises(ValidationFailure) as caught:
                    operation()
                self.assertEqual(caught.exception.code, "nonportable_number")
        self.assertEqual(canonical_bytes(2**53 - 1), b"9007199254740991")

    def test_unpaired_unicode_is_rejected_but_valid_surrogate_pair_parses(self) -> None:
        for text in ('"\\ud800"', '{"\\udfff":0}', '"\\ud800x"'):
            with self.subTest(text=text), self.assertRaises(ValidationFailure) as caught:
                loads_json(text)
            self.assertEqual(caught.exception.code, "invalid_unicode")
        self.assertEqual(loads_json('"\\ud83d\\ude00"'), "😀")
        with self.assertRaises(ValidationFailure):
            canonical_bytes({"bad": "\udfff"})

    def test_non_json_objects_and_cycles_are_rejected(self) -> None:
        cycle: list = []
        cycle.append(cycle)
        for value in ((1, 2), {1: "one"}, {1, 2}, b"bytes", object(), cycle):
            with self.subTest(kind=type(value)), self.assertRaises(ValidationFailure) as caught:
                canonical_bytes(value)
            self.assertEqual(caught.exception.code, "non_json_value")

    def test_shared_subobjects_are_valid_and_inputs_are_unchanged(self) -> None:
        child = [None, True, "e\u0301"]
        value = {"z": child, "a": child}
        before = deepcopy(value)
        canonical_bytes(value)
        self.assertEqual(value, before)
        self.assertIs(value["z"], child)
        self.assertIs(value["a"], child)

    def test_exact_rfc8785_number_vectors(self) -> None:
        vectors = {
            "0000000000000000": "0", "8000000000000000": "0",
            "0000000000000001": "5e-324", "8000000000000001": "-5e-324",
            "7fefffffffffffff": "1.7976931348623157e+308",
            "ffefffffffffffff": "-1.7976931348623157e+308",
            "4340000000000000": "9007199254740992",
            "4430000000000000": "295147905179352830000",
            "44b52d02c7e14af5": "9.999999999999997e+22",
            "44b52d02c7e14af6": "1e+23",
            "44b52d02c7e14af7": "1.0000000000000001e+23",
            "444b1ae4d6e2ef4e": "999999999999999700000",
            "444b1ae4d6e2ef4f": "999999999999999900000",
            "444b1ae4d6e2ef50": "1e+21",
            "3eb0c6f7a0b5ed8c": "9.999999999999997e-7",
            "3eb0c6f7a0b5ed8d": "0.000001",
        }
        for bits, expected in vectors.items():
            with self.subTest(bits=bits):
                number = struct.unpack(">d", bytes.fromhex(bits))[0]
                self.assertEqual(canonical_bytes(number), expected.encode("ascii"))

    def test_exact_utf16_key_order_and_escaping(self) -> None:
        value = {"דּ": 7, "😀": 6, "€": 5, "ö": 4, "\x80": 3, "1": 2, "\r": 1}
        expected = '{"\\r":1,"1":2,"\x80":3,"ö":4,"€":5,"😀":6,"דּ":7}'.encode("utf-8")
        self.assertEqual(canonical_bytes(value), expected)
        self.assertEqual(canonical_bytes("\b\t\n\f\r\x00\x0f\"\\/"), b'"\\b\\t\\n\\f\\r\\u0000\\u000f\\\"\\\\/"')

    def test_hash_is_sha256_of_canonical_bytes_without_unicode_normalization(self) -> None:
        value = {"b": [1.0, -0.0], "a": True}
        expected = b'{"a":true,"b":[1,0]}'
        self.assertEqual(content_hash(value), hashlib.sha256(expected).hexdigest())
        self.assertEqual(content_hash(value), content_hash({"a": True, "b": [1, 0]}))
        self.assertNotEqual(content_hash("é"), content_hash("e\u0301"))


class SchemaBoundaryTests(unittest.TestCase):
    def assert_invalid(self, kind: str, value: object) -> ValidationFailure:
        with self.assertRaises(ValidationFailure) as caught:
            validate(kind, value)
        return caught.exception

    def test_all_eleven_packaged_schemas_are_draft_2020_12(self) -> None:
        self.assertEqual(len(SCHEMA_KINDS), 11)
        for kind in SCHEMA_KINDS:
            schema = load_schema(kind)
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
            Draft202012Validator.check_schema(schema)

    def test_minimal_records_preserve_optional_missing_fields(self) -> None:
        values = {
            "observation": observation(),
            "hypothesis": {"schema_version": "1", "id": "H1", "description": "Combined causes possible"},
            "evidence": {"schema_version": "1", "id": "E1", "observation_id": "O1", "ratings": {}},
            "analysis_request": request(),
        }
        for kind, value in values.items():
            before = deepcopy(value)
            validate(kind, value)
            self.assertEqual(value, before)
        self.assertNotIn("initial_probability", values["hypothesis"])
        self.assertNotIn("reliability", values["observation"])
        self.assertNotIn("judgment", values["analysis_request"])

    def test_typed_record_metadata_preserves_input_optionality(self) -> None:
        self.assertEqual(Observation.__required_keys__, {"schema_version", "id", "raw", "source", "parse_status"})
        self.assertIn("reliability", Observation.__optional_keys__)
        self.assertIn("judgment", AnalysisRequest.__optional_keys__)
        self.assertIn("judgment", NormalizedAnalysisRequest.__required_keys__)

    def test_unknown_reliability_and_unknown_clock_bounds_remain_unknown(self) -> None:
        for reliability in ("F", "unknown"):
            validate("observation", observation(reliability=reliability, clock_domain=None, timestamp_uncertainty_seconds=None, timestamp="Sep 9 10:00:00", timestamp_context={}))
        self.assert_invalid("observation", observation(reliability="unrated"))

    def test_nonempty_ids_and_questions_reject_whitespace(self) -> None:
        for bad in ("", " \t\n", 1, None):
            self.assert_invalid("observation", observation(id=bad))
            self.assert_invalid("analysis_request", request(question=bad))

    def test_semantic_records_reject_unfamiliar_fields(self) -> None:
        self.assert_invalid("observation", observation(observation_id="legacy"))
        self.assert_invalid("observation", observation(inferred_attacker=True))
        self.assert_invalid("analysis_request", request(judgment={"summary": "Bounded conclusion", "automatic_winner": "H1"}))
        self.assert_invalid("analysis_request", request(tasks=[{"id": "T1", "action": "Review", "execute_shell": "rm"}]))
        self.assert_invalid("analysis_request", request(timeline_options={"timezone_guess": "UTC"}))
        self.assert_invalid("evidence", {"schema_version": "1", "id": "E1", "observation_id": "O1", "ratings": {}, "reliability": "A"})

    def test_probability_and_optional_falsifier_shapes(self) -> None:
        base = {"schema_version": "1", "id": "H1", "description": "Hypothesis"}
        for value in (None, 0, 1, 0.125):
            validate("hypothesis", {**base, "initial_probability": value, "falsifier": None})
        for value in (True, False, -0.1, 1.01, "0.5", [0.1, 0.3]):
            self.assert_invalid("hypothesis", {**base, "initial_probability": value})

    def test_missing_ratings_are_allowed_and_not_replaced_with_neutral(self) -> None:
        value = {"schema_version": "1", "id": "E1", "observation_id": "O1", "ratings": {"H1": "N"}}
        validate("evidence", value)
        self.assertEqual(value["ratings"], {"H1": "N"})
        for rating in (None, 0, "unknown", "", "+++", True):
            self.assert_invalid("evidence", {**value, "ratings": {"H1": rating}})

    def test_cross_record_resolution_is_not_falsely_claimed_by_schemas(self) -> None:
        # This is structurally valid. Pipeline/ACH must reject the dangling IDs.
        validate("analysis_request", request(evidence=[{"schema_version": "1", "id": "E1", "observation_id": "missing", "ratings": {"missing": "-"}}]))

    def test_light_disallows_evidence_but_full_may_be_incomplete(self) -> None:
        validate("analysis_request", request(mode="LIGHT", evidence=[]))
        value = {"schema_version": "1", "id": "E1", "observation_id": "O1", "ratings": {}}
        self.assert_invalid("analysis_request", request(mode="LIGHT", evidence=[value]))
        validate("analysis_request", request(evidence=[value]))

    def test_judgment_likelihood_and_confidence_are_distinct(self) -> None:
        judgment = {"summary": "Proceed with a bounded action", "likelihood": {"proposition": "P in this scope", "value": None, "basis": "Sparse observations"}, "confidence": {"level": "unassessed", "reasoning": "Coverage unverified"}}
        validate("analysis_request", request(judgment=judgment))
        validate("analysis_request", request(judgment=None))
        for bad in ({"summary": " "}, {"summary": "X", "likelihood": 0.5}, {"summary": "X", "confidence": {"level": "certain", "reasoning": "X"}}, {"summary": "X", "likelihood": {"proposition": "P", "value": True, "basis": "X"}}):
            self.assert_invalid("analysis_request", request(judgment=bad))

    def test_task_owner_is_optional_without_invented_person(self) -> None:
        value = request(tasks=[{"id": "T1", "action": "Collect independent record"}])
        validate("analysis_request", value)
        self.assertNotIn("owner", value["tasks"][0])
        self.assert_invalid("analysis_request", request(tasks=[{"id": "T1", "action": "Act", "owner": None}]))

    def test_calculation_operations_have_precise_inputs(self) -> None:
        for operation, operands in (("sum", []), ("product", []), ("sum", [1, 2, 3]), ("difference", [1, 2]), ("ratio", [1, 0])):
            validate("analysis_request", request(calculations=[{"id": "C1", "operation": operation, "operands": operands}]))
        for calculation in (
            {"id": "C1", "operation": "difference", "operands": [1]},
            {"id": "C1", "operation": "ratio", "operands": [1, 2, 3]},
            {"id": "C1", "operation": "sum", "operands": [True]},
            {"id": "C1", "operation": "eval", "operands": [1, 2]},
            {"id": "C1", "operation": "reported_interval", "operands": [1, 2]},
            {"id": "C1", "operation": "reported_interval", "start_observation_id": "O1"},
        ):
            self.assert_invalid("analysis_request", request(calculations=[calculation]))
        validate("analysis_request", request(calculations=[{"id": "C1", "operation": "reported_interval", "start_observation_id": "O1", "end_observation_id": "O2"}]))

    def test_timeline_thresholds_accept_fractions_but_not_booleans_or_negative_values(self) -> None:
        validate("analysis_request", request(timeline_options={"rapid_threshold_seconds": 0.125, "gap_threshold_seconds": 0, "fold": 1}))
        for fields in ({"rapid_threshold_seconds": True}, {"gap_threshold_seconds": -0.1}, {"default_year": None}, {"fold": False}, {"fold": 2}):
            self.assert_invalid("analysis_request", request(timeline_options=fields))

    def test_provenance_encoding_and_hash_formats_are_checked(self) -> None:
        validate("observation", observation(raw="�", raw_bytes_base64="/w==", record_sha256=hashlib.sha256(b"\xff").hexdigest(), parse_status="rejected"))
        for encoded in ("!!!!", "/x==", "_w==", "é", "/w", "/w==\n"):
            self.assert_invalid("observation", observation(raw_bytes_base64=encoded))
        for digest in ("", "a" * 63, "g" * 64, "A" * 64, "a" * 64 + "\n"):
            self.assert_invalid("observation", observation(record_sha256=digest))

    def test_doctrine_rules_have_explicit_adaptation_and_citation_fields(self) -> None:
        rule = {"rule_id": "R1", "title": "Engine rule", "summary": "Keep unknowns", "standard": "Engine adaptation", "section": "1", "citation": "Implementation policy", "url": "https://example.org/policy", "severity": "NOTE", "implementation_policy": True}
        validate("doctrine", {"schema_version": "1", "catalog_version": "1", "rules": [rule]})
        for fields in ({"implementation_policy": "true"}, {"severity": "CRITICAL"}, {"url": "not a URI"}, {"extra": 1}):
            self.assert_invalid("doctrine", {"schema_version": "1", "catalog_version": "1", "rules": [{**rule, **fields}]})

    def test_invalid_engine_result_cannot_claim_artifacts(self) -> None:
        value = {"schema_version": "1", "engine_version": "1.1.0", "status": "invalid", "diagnostics": [ValidationFailure("bad", "Input rejected").diagnostic()], "artifacts": None}
        validate("engine_result", value)
        self.assert_invalid("engine_result", {**value, "status": "ok"})
        self.assert_invalid("engine_result", {**value, "artifacts": {}})

    def test_timeline_resolved_clocks_require_rfc3339_with_valid_offset(self) -> None:
        value = empty_timeline()
        validate("timeline", value)
        for clock in ("2026-09-09T10:00:00Z", "2026-09-09T10:00:00.125+02:00", "2026-09-09t10:00:00z"):
            value["analysis"]["time_range"]["first"] = clock
            validate("timeline", value)
        for clock in ("2026-09-09T10:00:00", "2026-09-09 10:00:00Z", "2026-02-30T10:00:00Z", "2026-09-09T10:00:00+01:99", "2026-09-09T10:00:00+24:00"):
            value["analysis"]["time_range"]["first"] = clock
            self.assert_invalid("timeline", value)

    def test_reported_intervals_cannot_assert_physical_latency(self) -> None:
        value = empty_timeline()
        interval = {"event1": "O1", "event2": "O2", "delta_seconds": 0.25,
                    "kind": "reported_clock_interval", "same_known_clock_domain": False,
                    "combined_timestamp_uncertainty_seconds": None, "physical_latency_established": False}
        value["analysis"]["gaps"] = [interval]
        validate("timeline", value)
        interval["physical_latency_established"] = True
        self.assert_invalid("timeline", value)
        del interval["physical_latency_established"]
        self.assert_invalid("timeline", value)

    def test_matrix_nested_computation_shapes_are_typed_and_never_select_a_winner(self) -> None:
        value = empty_matrix()
        validate("ach_matrix", value)
        for keys, invalid in ((["assessment", "winner"], "H1"), (["assessment", "scores"], {"H1": True}),
                              (["sensitivity", "heuristic_stable"], "high confidence"),
                              (["sensitivity", "base_winner"], "H1"),
                              (["diagnosticity"], {"E1": -0.25}),
                              (["assessment", "missing_ratings"], [{"evidence_id": "E1"}])):
            candidate = deepcopy(value)
            cursor = candidate
            for key in keys[:-1]:
                cursor = cursor[key]
            cursor[keys[-1]] = invalid
            self.assert_invalid("ach_matrix", candidate)

    def test_calculation_results_distinguish_unresolved_from_zero(self) -> None:
        value = {"schema_version": "1", "analysis_id": "A1", "revision": 1, "content_hash": "0" * 64,
                 "question": "Q", "summary": "No analyst judgment supplied.", "likelihood": None,
                 "confidence": None, "implications": [], "assessment_status": "not_evaluated", "limitations": [],
                 "calculations": [{"id": "C1", "operation": "reported_interval", "value": None,
                                   "unit": "seconds", "status": "unresolved", "caveats": ["Unknown endpoint clock"],
                                   "physical_latency_established": False}]}
        validate("decision_card", value)
        for fields in ({"value": 0}, {"status": "resolved"}, {"physical_latency_established": True}, {"unit": "milliseconds"}):
            candidate = deepcopy(value)
            candidate["calculations"][0].update(fields)
            self.assert_invalid("decision_card", candidate)

    def test_trace_requires_normalized_request_and_mode_specific_matrix(self) -> None:
        normalized = request(mode="LIGHT", analysis_id="A1", revision=1, observations=[], hypotheses=[], evidence=[],
                             relationship="unspecified", judgment=None, assumptions=[], limitations=[], tasks=[],
                             rule_ids=[], calculations=[], timeline_options={"gap_threshold_seconds": 300, "rapid_threshold_seconds": 1})
        trace = {"schema_version": "1", "analysis_id": "A1", "revision": 1, "content_hash": "0" * 64,
                 "engine_version": "1.1.0", "request": normalized, "ach_matrix": None,
                 "timeline": empty_timeline(), "calculations": [], "diagnostics": [], "coherence": None}
        validate("analytic_trace", trace)
        minimal = deepcopy(trace)
        minimal["request"] = request(mode="LIGHT")
        self.assert_invalid("analytic_trace", minimal)
        wrong_light = deepcopy(trace)
        wrong_light["ach_matrix"] = empty_matrix()
        self.assert_invalid("analytic_trace", wrong_light)
        trace["request"]["mode"] = "FULL"
        self.assert_invalid("analytic_trace", trace)
        trace["ach_matrix"] = empty_matrix()
        validate("analytic_trace", trace)

    def test_result_projections_have_mode_specific_structures(self) -> None:
        normalized = request(mode="LIGHT", analysis_id="A1", revision=1, observations=[], hypotheses=[], evidence=[],
                             relationship="unspecified", judgment=None, assumptions=[], limitations=[], tasks=[],
                             rule_ids=[], calculations=[], timeline_options={})
        identity = {"schema_version": "1", "analysis_id": "A1", "revision": 1, "content_hash": "0" * 64}
        trace = {**identity, "engine_version": "1.1.0", "request": normalized, "ach_matrix": None,
                 "timeline": empty_timeline(), "calculations": [], "diagnostics": [], "coherence": None}
        card = {**identity, "question": "Q", "summary": "No analyst judgment supplied.", "likelihood": None,
                "confidence": None, "implications": [], "assessment_status": "not_evaluated", "limitations": [], "calculations": []}
        result = {"schema_version": "1", "engine_version": "1.1.0", "status": "ok", "diagnostics": [],
                  "artifacts": {"decision_card": card, "analytic_trace": trace, "tasking_view": None}}
        validate("engine_result", result)
        result["artifacts"]["tasking_view"] = {**identity, "tasks": [], "limitations": []}
        self.assert_invalid("engine_result", result)
        trace["request"]["mode"] = "FULL"
        trace["ach_matrix"] = empty_matrix()
        self.assert_invalid("engine_result", result)
        card["assessment_status"] = "insufficient_evidence"
        validate("engine_result", result)
        result["artifacts"]["tasking_view"] = None
        self.assert_invalid("engine_result", result)

    def test_failure_diagnostic_exposes_precise_path_and_remediation(self) -> None:
        failure = self.assert_invalid("analysis_request", request(hypotheses=[{"schema_version": "1", "id": "H1", "description": "D", "initial_probability": True}]))
        self.assertEqual(failure.path, '$["hypotheses"][0]["initial_probability"]')
        diagnostic = failure.diagnostic()
        self.assertEqual(diagnostic["severity"], "error")
        self.assertEqual(diagnostic["code"], "schema_validation")
        self.assertTrue(diagnostic["remediation"])
        self.assertIsInstance(failure, ValueError)

    def test_loaded_schemas_are_independent_copies(self) -> None:
        changed = load_schema("observation")
        changed["properties"]["id"] = {"type": "integer"}
        validate("observation", observation())
        self.assertEqual(load_schema("observation")["properties"]["id"]["type"], "string")

    def test_unknown_schema_does_not_become_a_path_or_url_lookup(self) -> None:
        for kind in ("https://example.org/schema", "../../etc/passwd", "not_present"):
            for operation in (load_schema, lambda candidate: validate(candidate, {})):
                with self.subTest(kind=kind), self.assertRaises(ValidationFailure) as caught:
                    operation(kind)
                self.assertEqual(caught.exception.code, "unknown_schema")

    def test_schema_resolution_is_bundled_only_and_never_retrieves_network(self) -> None:
        with patch("urllib.request.urlopen", side_effect=AssertionError("network attempted")):
            validate("analysis_request", request(observations=[observation()]))
            untrusted = {"observation": {"$ref": "https://example.org/remote-schema"}}
            registry = Registry(retrieve=validators._deny_retrieval)
            with patch.object(validators, "_bundled_contracts", return_value=(untrusted, registry)):
                failure = self.assert_invalid("observation", observation())
            self.assertEqual(failure.code, "forbidden_schema_reference")

    def test_schema_files_have_no_undocumented_any_object_escape_hatches(self) -> None:
        # Inspect object contracts recursively: dynamic-key maps must type values.
        def inspect(node: object) -> None:
            if isinstance(node, dict):
                if node.get("type") == "object":
                    self.assertIn("additionalProperties", node)
                    self.assertNotEqual(node["additionalProperties"], True)
                    if isinstance(node["additionalProperties"], dict):
                        self.assertTrue(node["additionalProperties"])
                for child in node.values():
                    inspect(child)
            elif isinstance(node, list):
                for child in node:
                    inspect(child)
        for kind in SCHEMA_KINDS:
            inspect(load_schema(kind))


if __name__ == "__main__":
    unittest.main()
