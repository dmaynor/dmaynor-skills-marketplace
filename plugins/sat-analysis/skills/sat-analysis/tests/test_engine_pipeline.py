"""Contract integration tests over the SDK's complete canonical artifact set."""

from __future__ import annotations

import copy
import json
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sat_engine import ValidationFailure, assess, ingest_text, validate, verify_artifacts
from sat_engine.rendering import render_markdown
from sat_engine.validators import canonical_bytes, content_hash


def observation(identifier: str, timestamp: str | None = None, **fields: object) -> dict[str, object]:
    result = {"schema_version": "1", "id": identifier, "raw": f"Recorded fact {identifier}",
              "source": f"collector/{identifier}", "parse_status": "parsed", **fields}
    if timestamp is not None:
        result["timestamp"] = timestamp
    return result


def basic_request(mode: str = "FULL", **fields: object) -> dict[str, object]:
    return {"schema_version": "1", "mode": mode, "submode": "GENERAL",
            "question": "What explains the delay?", **fields}


def full_request(submode: str = "GENERAL") -> dict[str, object]:
    descriptions = {
        "BREACH": ("Was the session unauthorized?", "Credential misuse", "Authorized maintenance"),
        "CRASH": ("What explains the process exit?", "Invalid object lifetime", "Resource exhaustion"),
        "FIX": ("Does the proposed guard address the observed fault?", "Guard covers the fault", "An uncovered path remains"),
        "STATEMENT": ("Does the observation support the scoped claim?", "Claim holds in scope", "Claim has a counterexample"),
        "GENERAL": ("What explains the delay?", "Transport degradation", "Telemetry inflation"),
    }
    question, first, second = descriptions[submode]
    return basic_request(
        submode=submode, question=question, analysis_id=f"integration-{submode.lower()}", revision=2,
        observations=[observation("O1", "2026-09-09T10:00:00+02:00", reliability="F"),
                      observation("O2", "2026-09-09T08:00:02.250Z")],
        hypotheses=[{"schema_version": "1", "id": "H1", "description": first},
                    {"schema_version": "1", "id": "H2", "description": second}],
        evidence=[{"schema_version": "1", "id": "E1", "observation_id": "O1",
                   "ratings": {"H1": "+", "H2": "N"}, "rationale": "Scoped analyst comparison."}],
        judgment={"summary": "A bounded response is justified while the alternative remains unresolved.",
                  "selected_hypothesis_ids": ["H2"], "observation_ids": ["O1"],
                  "likelihood": {"proposition": second, "value": None, "basis": "Evidence is not sufficient for a point estimate."},
                  "confidence": {"level": "low", "reasoning": "One source is unjudged and coverage is incomplete."},
                  "implications": ["Collect an independent observation before expanding the response."]},
        assumptions=["The supplied record was retained without truncation."],
        limitations=["Collection does not cover every path."],
        tasks=[{"id": "T1", "action": "Collect independent evidence", "observation_ids": ["O1"],
                "hypothesis_ids": ["H2"]}],
        calculations=[{"id": "C1", "operation": "reported_interval",
                       "start_observation_id": "O1", "end_observation_id": "O2"}],
    )


def rehash_all_views(artifacts: dict[str, object]) -> None:
    """Model an attacker who can recompute a valid hash after editing the trace."""
    trace = artifacts["analytic_trace"]
    trace.pop("content_hash", None)
    digest = content_hash(trace)
    for view in artifacts.values():
        if view is not None:
            view["content_hash"] = digest


class PipelineIntegrationTests(unittest.TestCase):
    def successful(self, request: dict[str, object]) -> dict[str, object]:
        result = assess(request)
        self.assertEqual(result["status"], "ok", result.get("diagnostics"))
        validate("engine_result", result)
        verify_artifacts(result["artifacts"])
        return result

    def invalid(self, request: object) -> dict[str, object]:
        result = assess(request)
        self.assertEqual(result["status"], "invalid", result)
        self.assertIsNone(result["artifacts"])
        self.assertTrue(result["diagnostics"])
        self.assertTrue(all(d["severity"] == "error" for d in result["diagnostics"]))
        validate("engine_result", result)
        return result

    def test_light_has_two_views_and_explicit_unknown_judgment(self) -> None:
        data = basic_request("LIGHT")
        artifacts = self.successful(data)["artifacts"]
        card, trace = artifacts["decision_card"], artifacts["analytic_trace"]
        self.assertIsNone(artifacts["tasking_view"])
        self.assertIsNone(trace["ach_matrix"])
        self.assertEqual(card["assessment_status"], "not_evaluated")
        self.assertEqual(card["summary"], "No analyst judgment supplied.")
        self.assertIsNone(card["likelihood"])
        self.assertIsNone(card["confidence"])
        self.assertEqual(set(render_markdown(artifacts)), {"decision_card.md", "analytic_trace.md"})
        self.assertEqual(data, basic_request("LIGHT"))

    def test_all_five_full_submodes_produce_coherent_preserved_inputs(self) -> None:
        for submode in ("BREACH", "CRASH", "FIX", "STATEMENT", "GENERAL"):
            with self.subTest(submode=submode):
                data = full_request(submode)
                original = copy.deepcopy(data)
                result = self.successful(data)
                artifacts = result["artifacts"]
                trace, card, tasking = (artifacts[k] for k in ("analytic_trace", "decision_card", "tasking_view"))
                self.assertEqual(data, original)
                self.assertEqual(trace["request"]["submode"], submode)
                for key in ("question", "judgment", "assumptions", "limitations", "observations", "evidence"):
                    self.assertEqual(trace["request"][key], original[key])
                self.assertEqual(card["summary"], data["judgment"]["summary"])
                self.assertEqual(card["confidence"], data["judgment"]["confidence"])
                self.assertIsNone(card["likelihood"]["value"])
                self.assertEqual(trace["ach_matrix"]["assessment"]["heuristic_leaders"], ["H1"])
                self.assertIsNone(trace["ach_matrix"]["assessment"]["winner"])
                self.assertEqual(trace["request"]["judgment"]["selected_hypothesis_ids"], ["H2"])
                self.assertEqual(card["calculations"], trace["calculations"])
                self.assertEqual(tasking["tasks"], data["tasks"])
                self.assertNotIn("owner", tasking["tasks"][0])
                for view in artifacts.values():
                    for field in ("analysis_id", "revision", "content_hash"):
                        self.assertEqual(view[field], trace[field])
                rendered = render_markdown(artifacts)
                self.assertEqual(set(rendered), {"decision_card.md", "analytic_trace.md", "tasking_view.md"})
                self.assertIn("Unassigned", rendered["tasking_view.md"])
                self.assertIn("engine validation does not establish its factual truth", rendered["decision_card.md"])
                self.assertIn("does not establish", rendered["analytic_trace.md"])

    def test_full_can_be_empty_or_incomplete_without_inventing_ratings(self) -> None:
        empty = self.successful(basic_request())["artifacts"]
        self.assertEqual(empty["decision_card"]["assessment_status"], "insufficient_evidence")
        self.assertIsNotNone(empty["tasking_view"])
        data = full_request()
        data["evidence"][0]["ratings"].pop("H2")
        result = self.successful(data)
        assessment = result["artifacts"]["analytic_trace"]["ach_matrix"]["assessment"]
        self.assertEqual(assessment["status"], "incomplete")
        self.assertEqual(assessment["missing_ratings"], [{"evidence_id": "E1", "hypothesis_id": "H2"}])
        self.assertTrue(any(d["code"] == "matrix_incomplete" for d in result["diagnostics"]))
        self.assertEqual(result["artifacts"]["decision_card"]["summary"], data["judgment"]["summary"])

    def test_normalization_and_identity_are_deterministic_without_mutation(self) -> None:
        data = basic_request()
        first = self.successful(data)
        second = self.successful(dict(reversed(list(data.items()))))
        self.assertEqual(canonical_bytes(first), canonical_bytes(second))
        trace = first["artifacts"]["analytic_trace"]
        self.assertEqual(trace["revision"], 1)
        self.assertTrue(trace["analysis_id"].startswith("sat-"))
        normalized = trace["request"]
        for key in ("observations", "hypotheses", "evidence", "tasks", "calculations", "rule_ids", "assumptions", "limitations"):
            self.assertEqual(normalized[key], [])
            self.assertNotIn(key, data)
        self.assertIsNone(normalized["judgment"])
        self.assertEqual(normalized["relationship"], "unspecified")
        digest_input = copy.deepcopy(trace)
        digest_input.pop("content_hash")
        self.assertEqual(trace["content_hash"], content_hash(digest_input))
        self.assertEqual(self.successful(normalized), first)
        changed = self.successful(basic_request(question="A different question"))
        self.assertNotEqual(trace["analysis_id"], changed["artifacts"]["analytic_trace"]["analysis_id"])

    def test_views_do_not_alias_mutable_inputs_or_each_other(self) -> None:
        data = full_request()
        original = copy.deepcopy(data)
        artifacts = self.successful(data)["artifacts"]
        trace = artifacts["analytic_trace"]
        artifacts["decision_card"]["confidence"]["level"] = "high"
        artifacts["decision_card"]["calculations"][0]["value"] = 999
        artifacts["tasking_view"]["tasks"][0]["action"] = "Altered projection"
        self.assertEqual(trace["request"]["judgment"]["confidence"]["level"], "low")
        self.assertEqual(trace["calculations"][0]["value"], 2.25)
        self.assertEqual(trace["request"]["tasks"][0]["action"], "Collect independent evidence")
        self.assertEqual(data, original)

    def test_rejected_and_unparsed_observations_survive_pipeline_and_rendering(self) -> None:
        raw = "opaque evidence with no parser\n{bad JSON\n"
        observations = ingest_text(raw, source="case/input.log", log_format="json")
        data = basic_request(observations=observations, assumptions=["Collection completeness unknown."])
        result = self.successful(data)
        trace = result["artifacts"]["analytic_trace"]
        self.assertEqual(trace["request"]["observations"], observations)
        self.assertEqual(len(trace["timeline"]["events"]), 2)
        self.assertTrue(any(d["code"] == "extraction_incomplete" for d in result["diagnostics"]))
        rendered = render_markdown(result["artifacts"])["analytic_trace.md"]
        self.assertIn("opaque evidence with no parser", rendered)
        self.assertIn("{bad JSON", rendered)
        self.assertIn("Collection completeness unknown", rendered)

    def test_duplicate_ids_and_all_cross_record_reference_types_fail(self) -> None:
        variants = []
        for kind in ("observations", "hypotheses", "evidence", "tasks", "calculations"):
            data = full_request()
            data[kind].append(copy.deepcopy(data[kind][0]))
            variants.append((f"duplicate {kind}", data))
        for owner, field in (("judgment", "observation_ids"), ("judgment", "selected_hypothesis_ids"),
                             ("tasks", "observation_ids"), ("tasks", "hypothesis_ids")):
            data = full_request()
            target = data[owner] if owner == "judgment" else data[owner][0]
            target[field] = ["absent"]
            variants.append((f"{owner}.{field}", data))
        for field in ("start_observation_id", "end_observation_id"):
            data = full_request()
            data["calculations"][0][field] = "absent"
            variants.append((field, data))
        for field, value in (("observation_id", "absent"), ("ratings", {"absent": "+"})):
            data = full_request()
            data["evidence"][0][field] = value
            variants.append((f"evidence.{field}", data))
        for label, data in variants:
            with self.subTest(label=label):
                original = copy.deepcopy(data)
                self.invalid(data)
                self.assertEqual(data, original)

    def test_invalid_schema_values_and_unknown_rules_produce_error_envelopes(self) -> None:
        for data in (None, [], {}, basic_request(mode="LIGHT", evidence=full_request()["evidence"]),
                     basic_request(submode="UNKNOWN"), basic_request(question=" "),
                     basic_request(extra="unsupported"), basic_request(revision=True),
                     basic_request(rule_ids=["not-in-the-catalog"]),
                     basic_request(timeline_options={"gap_threshold_seconds": -1}),
                     basic_request(timeline_options={"rapid_threshold_seconds": math.inf})):
            with self.subTest(data=data):
                self.invalid(data)

    def test_probability_relationships_and_optional_likelihood_survive_full_pipeline(self) -> None:
        for mode in ("LIGHT", "FULL"):
            for relationship, probabilities, valid in (
                ("exclusive_exhaustive", [0.3, 0.7], True),
                ("exclusive_exhaustive", [0.3, None], True),
                ("exclusive_exhaustive", [0.3, 0.3], False),
                ("exclusive_exhaustive", [0.5, 0.5000000005], True),
                ("exclusive_exhaustive", [0.5, 0.500000002], False),
                ("exclusive_nonexhaustive", [0.3, 0.3], True),
                ("exclusive_nonexhaustive", [0.8, 0.8], False),
                ("overlapping", [0.8, 0.8], True),
                ("unspecified", [0.8, 0.8], True),
            ):
                data = basic_request(mode, relationship=relationship, hypotheses=[
                    {"schema_version": "1", "id": f"H{i}", "description": "Explicit proposition", "initial_probability": value}
                    for i, value in enumerate(probabilities)
                ])
                with self.subTest(mode=mode, relationship=relationship, probabilities=probabilities):
                    if valid:
                        result = self.successful(data)
                        self.assertEqual(result["artifacts"]["analytic_trace"]["request"]["hypotheses"], data["hypotheses"])
                    else:
                        self.invalid(data)

    def test_likelihood_and_calculation_numbers_reject_nonfinite_and_boolean_values(self) -> None:
        for value in (math.nan, math.inf, -math.inf, True, False, 2**53, -0.1, 1.1):
            data = full_request()
            data["judgment"]["likelihood"]["value"] = value
            with self.subTest(value=str(value)):
                self.invalid(data)
        for value in (None, 0, 1):
            data = full_request()
            data["judgment"]["likelihood"]["value"] = value
            self.assertEqual(self.successful(data)["artifacts"]["decision_card"]["likelihood"]["value"], value)

    def test_unjudged_reliability_does_not_automatically_cap_analyst_confidence(self) -> None:
        data = full_request()
        data["judgment"]["confidence"] = {
            "level": "high", "reasoning": "Analyst's stated basis remains a claim requiring review.",
        }
        result = self.successful(data)
        self.assertEqual(result["artifacts"]["decision_card"]["confidence"], data["judgment"]["confidence"])
        assessment = result["artifacts"]["analytic_trace"]["ach_matrix"]["assessment"]
        self.assertTrue(any("unknown or unjudged" in caveat for caveat in assessment["caveats"]))
        self.assertTrue(any(d["code"] == "judgment_not_verified" for d in result["diagnostics"]))

    def test_arithmetic_results_are_computed_once_and_projected_exactly(self) -> None:
        data = basic_request(calculations=[
            {"id": "sum", "operation": "sum", "operands": [0.1, 0.2, 0.3], "unit": "units"},
            {"id": "difference", "operation": "difference", "operands": [9, 4]},
            {"id": "product", "operation": "product", "operands": [2, 3, 4]},
            {"id": "ratio", "operation": "ratio", "operands": [7, 2]},
        ])
        artifacts = self.successful(data)["artifacts"]
        calculated = artifacts["analytic_trace"]["calculations"]
        self.assertEqual([c["value"] for c in calculated], [0.6, 5, 24, 3.5])
        self.assertEqual(calculated, artifacts["decision_card"]["calculations"])
        self.assertTrue(all(c["status"] == "resolved" for c in calculated))
        self.assertTrue(all("physical_latency_established" not in c for c in calculated))

    def test_arithmetic_rejects_zero_division_overflow_and_wrong_arity(self) -> None:
        for operation, operands in (("ratio", [1, 0]), ("difference", [1]), ("ratio", [1, 2, 3]),
                                    ("product", [1e308, 1e308]), ("sum", [2**53 - 1, 1]),
                                    ("sum", [True, 1]), ("sum", [math.nan])):
            with self.subTest(operation=operation, operands=operands):
                self.invalid(basic_request(calculations=[{"id": "C", "operation": operation, "operands": operands}]))

    def test_reported_clock_interval_preserves_original_times_and_physical_limits(self) -> None:
        data = full_request()
        data["timeline_options"] = {"gap_threshold_seconds": 2, "rapid_threshold_seconds": 0.5}
        artifacts = self.successful(data)["artifacts"]
        trace = artifacts["analytic_trace"]
        interval = trace["calculations"][0]
        self.assertEqual(interval["value"], 2.25)
        self.assertEqual(interval["unit"], "seconds")
        self.assertFalse(interval["physical_latency_established"])
        self.assertTrue(any("Clock alignment" in c for c in interval["caveats"]))
        self.assertEqual([e["timestamp"] for e in trace["timeline"]["events"]],
                         [o["timestamp"] for o in data["observations"]])
        self.assertEqual(trace["timeline"]["gap_threshold_seconds"], 2)
        self.assertEqual(trace["timeline"]["rapid_threshold_seconds"], 0.5)
        self.assertEqual(len(trace["timeline"]["analysis"]["gaps"]), 1)
        self.assertFalse(trace["timeline"]["analysis"]["gaps"][0]["physical_latency_established"])

    def test_unknown_endpoint_is_unresolved_not_zero_until_context_is_explicit(self) -> None:
        data = full_request()
        data["observations"][0]["timestamp"] = "2026-09-09T08:00:00"
        result = self.successful(data)
        interval = result["artifacts"]["analytic_trace"]["calculations"][0]
        self.assertEqual(interval["status"], "unresolved")
        self.assertIsNone(interval["value"])
        self.assertFalse(interval["physical_latency_established"])
        self.assertTrue(any(d["code"] == "calculation_unresolved" for d in result["diagnostics"]))
        self.assertEqual(result["artifacts"]["analytic_trace"]["timeline"]["analysis"]["unresolved_events"], 1)
        data["observations"][0]["timestamp_context"] = {"timezone": "UTC"}
        explicit = self.successful(data)["artifacts"]["analytic_trace"]
        self.assertEqual(explicit["calculations"][0]["value"], 2.25)
        self.assertEqual(explicit["request"]["observations"][0]["timestamp"], "2026-09-09T08:00:00")

    def test_reversed_and_equivalent_zoned_clocks_are_not_silently_repaired(self) -> None:
        for end, expected in (("2026-09-09T08:00:00Z", 0), ("2026-09-09T07:59:59Z", -1)):
            data = full_request()
            data["observations"][1]["timestamp"] = end
            with self.subTest(end=end):
                interval = self.successful(data)["artifacts"]["analytic_trace"]["calculations"][0]
                self.assertEqual(interval["value"], expected)
                self.assertFalse(interval["physical_latency_established"])
                if expected < 0:
                    self.assertTrue(any("End precedes start" in c for c in interval["caveats"]))

    def test_verify_rejects_rehashed_forged_derived_fields_and_stale_projections(self) -> None:
        original = self.successful(full_request())["artifacts"]
        mutations = {
            "scores": lambda a: a["analytic_trace"]["ach_matrix"]["assessment"]["scores"].update(H1=999),
            "variance": lambda a: a["analytic_trace"]["ach_matrix"]["diagnosticity"].update(E1=999),
            "sensitivity": lambda a: a["analytic_trace"]["ach_matrix"]["sensitivity"].update(heuristic_stable=True),
            "calculation": lambda a: a["analytic_trace"]["calculations"][0].update(value=999),
            "clock": lambda a: a["analytic_trace"]["timeline"]["events"][0].update(timestamp_utc="2026-09-09T08:00:01+00:00"),
            "timeline_count": lambda a: a["analytic_trace"]["timeline"]["analysis"].update(total_events=99),
            "trace_diagnostics": lambda a: a["analytic_trace"].update(diagnostics=[]),
            "card_summary": lambda a: a["decision_card"].update(summary="Unsupported conclusion"),
            "card_confidence": lambda a: a["decision_card"]["confidence"].update(level="high"),
            "card_likelihood": lambda a: a["decision_card"]["likelihood"].update(value=0.99),
            "task_owner": lambda a: a["tasking_view"]["tasks"][0].update(owner="Invented owner"),
            "stale_judgment": lambda a: a["analytic_trace"]["request"]["judgment"].update(summary="Revised analyst judgment"),
            "stale_rating": lambda a: a["analytic_trace"]["request"]["evidence"][0]["ratings"].update(H1="--"),
            "stale_task": lambda a: a["analytic_trace"]["request"]["tasks"][0].update(action="Different task"),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                forged = copy.deepcopy(original)
                mutate(forged)
                rehash_all_views(forged)
                for kind, value in forged.items():
                    validate(kind, value)
                with self.assertRaises(ValidationFailure):
                    verify_artifacts(forged)
        self.assertEqual(original, self.successful(full_request())["artifacts"])

    def test_coordinated_forgery_in_trace_and_card_still_fails_recomputation(self) -> None:
        artifacts = self.successful(full_request())["artifacts"]
        for key in ("analytic_trace", "decision_card"):
            artifacts[key]["calculations"][0]["value"] = 999
        matrix = artifacts["analytic_trace"]["ach_matrix"]
        matrix["assessment"]["scores"]["H1"] = 999
        matrix["sensitivity"]["base_scores"]["H1"] = 999
        matrix["sensitivity"]["base_assessment"]["scores"]["H1"] = 999
        rehash_all_views(artifacts)
        with self.assertRaises(ValidationFailure):
            verify_artifacts(artifacts)

    def test_verify_rejects_foreign_versions_missing_views_and_stale_revision(self) -> None:
        original = self.successful(full_request())["artifacts"]
        variants = []
        missing = copy.deepcopy(original)
        missing.pop("tasking_view")
        variants.append(missing)
        foreign = copy.deepcopy(original)
        foreign["analytic_trace"]["engine_version"] = "9.9.9"
        rehash_all_views(foreign)
        variants.append(foreign)
        revision = copy.deepcopy(original)
        for view in revision.values():
            view["revision"] = 3
        rehash_all_views(revision)
        variants.append(revision)
        for data in variants:
            with self.subTest(data=data), self.assertRaises(ValidationFailure):
                verify_artifacts(data)

    def test_verified_json_roundtrip_is_exact_and_rendering_does_not_mutate(self) -> None:
        artifacts = self.successful(full_request())["artifacts"]
        serialized = json.dumps(artifacts, allow_nan=False)
        restored = json.loads(serialized)
        verify_artifacts(restored)
        before = canonical_bytes(restored)
        rendered = render_markdown(restored)
        self.assertEqual(canonical_bytes(restored), before)
        self.assertEqual(rendered, render_markdown(artifacts))


if __name__ == "__main__":
    unittest.main()
