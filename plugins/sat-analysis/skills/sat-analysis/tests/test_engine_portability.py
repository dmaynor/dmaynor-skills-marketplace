"""Portable golden replay plus separately authored semantic invariants.

Complete expected results were captured once from the Python engine. They are
regression snapshots, not independent proof of correct analysis. The case files
also contain hand-authored arithmetic, clock, provenance, dependency and missing
rating expectations, checked separately below. No second-language implementation
has executed these fixtures; cross-platform parity is not claimed.
"""

from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
from pathlib import Path
import struct
import unittest

from sat_engine.pipeline import assess
from sat_engine.validators import canonical_bytes, loads_json


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "engine"


class PortableContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = {
            path.name.removesuffix(".case.json"): loads_json(path.read_bytes())
            for path in sorted(FIXTURES.glob("*.case.json"))
        }
        cls.results = {
            name: assess(deepcopy(case["request"])) for name, case in cls.cases.items()
        }

    def test_light_and_each_full_domain_have_actual_successful_requests(self) -> None:
        coverage = {(case["request"]["mode"], case["request"]["submode"]) for case in self.cases.values()}
        self.assertEqual(coverage, {
            ("LIGHT", "GENERAL"), ("FULL", "BREACH"), ("FULL", "CRASH"),
            ("FULL", "FIX"), ("FULL", "STATEMENT"), ("FULL", "GENERAL"),
        })
        self.assertEqual(len(self.cases), 6)
        for name, case in self.cases.items():
            with self.subTest(case=name):
                self.assertEqual(self.results[name]["status"], "ok")
                self.assertTrue(case["request"]["observations"])
                self.assertIsInstance(case["request"]["judgment"], dict)
                self.assertTrue(case["request"]["calculations"])

    def test_complete_expected_result_bytes_replay_without_normalizing_events(self) -> None:
        for name, case in self.cases.items():
            with self.subTest(case=name):
                expected_path = FIXTURES / case["expected_result_file"]
                expected_bytes = expected_path.read_bytes()
                self.assertEqual(hashlib.sha256(expected_bytes).hexdigest(), case["expected_result_bytes_sha256"])
                # The expected side is checked-in bytes, never another assess call.
                self.assertEqual(canonical_bytes(self.results[name]) + b"\n", expected_bytes)

    def test_replay_never_mutates_supplied_inputs(self) -> None:
        for name, case in self.cases.items():
            with self.subTest(case=name):
                value = deepcopy(case["request"])
                before = deepcopy(value)
                assess(value)
                self.assertEqual(value, before)

    def test_each_artifact_and_complete_trace_has_the_expected_byte_commitment(self) -> None:
        for name, case in self.cases.items():
            with self.subTest(case=name):
                artifacts = self.results[name]["artifacts"]
                for kind, view in artifacts.items():
                    actual_digest = hashlib.sha256(canonical_bytes(view)).hexdigest()
                    self.assertEqual(actual_digest, case["expected_artifact_canonical_sha256"][kind])
                trace = artifacts["analytic_trace"]
                content = {key: value for key, value in trace.items() if key != "content_hash"}
                digest = hashlib.sha256(canonical_bytes(content)).hexdigest()
                self.assertEqual(trace["content_hash"], digest)
                for view in artifacts.values():
                    if view is not None:
                        self.assertEqual(view["content_hash"], digest)
                        self.assertEqual(view["analysis_id"], case["request"]["analysis_id"])
                        self.assertEqual(view["revision"], 2)

    def test_hand_authored_arithmetic_expectations_include_unresolved_and_identity_cases(self) -> None:
        for name, case in self.cases.items():
            with self.subTest(case=name):
                calculations = self.results[name]["artifacts"]["analytic_trace"]["calculations"]
                expected_values = case["independent_expectations"]["calculation_values"]
                self.assertEqual({item["id"]: item["value"] for item in calculations}, expected_values)
                for item in calculations:
                    self.assertEqual(item["status"], "unresolved" if expected_values[item["id"]] is None else "resolved")
                    if item["value"] is not None:
                        self.assertIn(type(item["value"]), (int, float))
                    if item["operation"] == "reported_interval":
                        self.assertIs(item["physical_latency_established"], False)
                        self.assertEqual(item["unit"], "seconds")
                        self.assertTrue(item["caveats"])
        crash = self.results["full_crash_unknown_clocks"]["artifacts"]["analytic_trace"]
        self.assertIsNone(crash["calculations"][0]["value"])
        general = self.results["full_general_unrated"]["artifacts"]["analytic_trace"]
        self.assertEqual([item["value"] for item in general["calculations"]], [0.75, 0, 1])

    def test_hand_authored_utc_order_unknown_clocks_and_parse_counts(self) -> None:
        for name, case in self.cases.items():
            with self.subTest(case=name):
                timeline = self.results[name]["artifacts"]["analytic_trace"]["timeline"]
                expected = case["independent_expectations"]
                self.assertEqual([event["id"] for event in timeline["events"]], expected["event_ids_ordered"])
                self.assertEqual({event["id"]: event["timestamp_utc"] for event in timeline["events"]}, expected["timestamp_utc_by_id"])
                for field in ("resolved_events", "unresolved_events", "parse_counts"):
                    self.assertEqual(timeline["analysis"][field], expected[field])
                self.assertEqual(timeline["analysis"]["total_events"], len(case["request"]["observations"]))
                for interval in timeline["analysis"]["gaps"] + timeline["analysis"]["rapid_succession"]:
                    self.assertIs(interval["physical_latency_established"], False)

    def test_raw_identifiers_timestamp_spelling_and_source_bytes_survive_exactly(self) -> None:
        for name, case in self.cases.items():
            with self.subTest(case=name):
                trace = self.results[name]["artifacts"]["analytic_trace"]
                observations = case["request"]["observations"]
                self.assertEqual(trace["request"]["observations"], observations)
                events = {event["id"]: event for event in trace["timeline"]["events"]}
                for observation in observations:
                    event = events[observation["id"]]
                    for field in ("raw", "source", "timestamp", "record_sha256", "parse_status", "reliability"):
                        self.assertEqual(event[field], observation[field])
                    for field in ("origin_id", "dependency_groups", "source_id", "clock_domain", "timestamp_semantics", "timestamp_uncertainty_seconds", "timestamp_context", "raw_bytes_base64"):
                        if field in observation:
                            self.assertEqual(event[field], observation[field])
                    original_bytes = (
                        base64.b64decode(observation["raw_bytes_base64"], validate=True)
                        if observation.get("raw_bytes_base64") else observation["raw"].encode("utf-8")
                    )
                    self.assertEqual(hashlib.sha256(original_bytes).hexdigest(), observation["record_sha256"])
                    self.assertEqual(original_bytes.decode("utf-8", errors="replace"), observation["raw"])
                for identifier, expected_hex in case["independent_expectations"].get("rejected_original_bytes_hex", {}).items():
                    self.assertEqual(base64.b64decode(events[identifier]["raw_bytes_base64"], validate=True).hex(), expected_hex)
                    self.assertEqual(events[identifier]["parse_status"], "rejected")

    def test_hand_authored_matrix_totals_missing_cells_and_no_causal_winner(self) -> None:
        for name, case in self.cases.items():
            with self.subTest(case=name):
                artifacts = self.results[name]["artifacts"]
                matrix = artifacts["analytic_trace"]["ach_matrix"]
                expected = case["independent_expectations"]["ach"]
                if expected is None:
                    self.assertIsNone(matrix)
                    self.assertIsNone(artifacts["tasking_view"])
                    self.assertEqual(artifacts["decision_card"]["assessment_status"], "not_evaluated")
                    continue
                assessment = matrix["assessment"]
                for field in ("status", "scores", "heuristic_leaders", "contributing_record_count", "missing_ratings"):
                    self.assertEqual(assessment[field], expected[field])
                self.assertEqual(matrix["diagnosticity"], expected["diagnosticity"])
                self.assertIs(matrix["sensitivity"]["heuristic_stable"], expected["heuristic_stable"])
                self.assertIsNone(assessment["winner"])
                self.assertIsNone(matrix["sensitivity"]["base_winner"])
                self.assertEqual(artifacts["decision_card"]["assessment_status"], expected["status"])
                self.assertIsNotNone(artifacts["tasking_view"])
                for group_key, expected_impact in expected.get("groups", {}).items():
                    impact = matrix["sensitivity"]["group_impact"][group_key]
                    self.assertEqual(impact["removed_evidence_ids"], expected_impact["removed_evidence_ids"])
                    self.assertEqual(impact["status"], expected_impact["status"])
                    self.assertIsNone(impact["winner"])

    def test_copied_origin_does_not_add_support_and_source_removal_closes_over_copies(self) -> None:
        matrix = self.results["full_breach_origin_closure"]["artifacts"]["analytic_trace"]["ach_matrix"]
        # Two copies of [+,-] and one [N,N] give [+1,-1], not [+2,-2].
        self.assertEqual(matrix["assessment"]["scores"], {"H_admin": -1, "H_stolen": 1})
        self.assertEqual(matrix["assessment"]["contributing_record_count"], 2)
        # Removing the gateway also removes its mirrored authentication origin.
        impact = matrix["sensitivity"]["group_impact"]["source:gateway.log"]
        self.assertEqual(impact["removed_evidence_ids"], ["E_auth", "E_auth_copy", "E_ticket"])
        self.assertEqual(impact["status"], "insufficient_evidence")
        self.assertTrue(impact["changes_assessment"])

    def test_missing_rating_stays_missing_and_overlapping_probabilities_are_not_normalized(self) -> None:
        trace = self.results["full_crash_unknown_clocks"]["artifacts"]["analytic_trace"]
        matrix = trace["ach_matrix"]
        self.assertNotIn("H_memory", matrix["evidence"][0]["ratings"])
        self.assertEqual(matrix["assessment"]["status"], "incomplete")
        self.assertIsNone(matrix["diagnosticity"]["E_stack"])
        self.assertEqual([hypothesis["initial_probability"] for hypothesis in matrix["hypotheses"]], [0.8, 0.7])
        self.assertEqual(trace["request"]["relationship"], "overlapping")

    def test_shared_business_event_keeps_distinct_measurement_origins(self) -> None:
        trace = self.results["full_general_unrated"]["artifacts"]["analytic_trace"]
        events = trace["timeline"]["events"]
        self.assertEqual(len(events), 2)
        self.assertNotEqual(events[0]["origin_id"], events[1]["origin_id"])
        self.assertEqual(events[0]["dependency_groups"], ["shipment-27"])
        self.assertEqual(events[1]["dependency_groups"], ["shipment-27"])
        self.assertEqual(trace["calculations"][0]["value"], 0.75)

    def test_judgment_likelihood_confidence_and_missing_task_owners_are_not_synthesized(self) -> None:
        for name, case in self.cases.items():
            with self.subTest(case=name):
                request = case["request"]
                judgment = request["judgment"]
                artifacts = self.results[name]["artifacts"]
                trace = artifacts["analytic_trace"]
                card = artifacts["decision_card"]
                self.assertEqual(trace["request"]["judgment"], judgment)
                self.assertEqual(card["summary"], judgment["summary"])
                self.assertEqual(card["likelihood"], judgment.get("likelihood"))
                self.assertEqual(card["confidence"], judgment.get("confidence"))
                self.assertEqual(trace["request"]["assumptions"], request["assumptions"])
                if artifacts["tasking_view"] is not None:
                    self.assertEqual(artifacts["tasking_view"]["tasks"], request.get("tasks", []))
                    for original, projected in zip(request.get("tasks", []), artifacts["tasking_view"]["tasks"]):
                        if "owner" not in original:
                            self.assertNotIn("owner", projected)
        # An analyst selection remains distinct from a heuristic leader.
        trace = self.results["full_breach_origin_closure"]["artifacts"]["analytic_trace"]
        self.assertEqual(trace["request"]["judgment"]["selected_hypothesis_ids"], ["H_admin"])
        self.assertEqual(trace["ach_matrix"]["assessment"]["heuristic_leaders"], ["H_stolen"])


class PortableCanonicalVectors(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.vectors = loads_json((FIXTURES / "rfc8785.vectors.json").read_bytes())

    def test_known_binary64_serializations_match_literal_expected_bytes(self) -> None:
        for vector in self.vectors["binary64_vectors"]:
            with self.subTest(ieee754=vector["ieee754_hex"]):
                value = struct.unpack(">d", bytes.fromhex(vector["ieee754_hex"]))[0]
                self.assertEqual(canonical_bytes(value), vector["canonical_utf8"].encode("utf-8"))

    def test_known_key_order_signed_zero_and_unicode_preservation(self) -> None:
        for vector in self.vectors["json_vectors"]:
            with self.subTest(input_json=vector["input_json"]):
                self.assertEqual(canonical_bytes(loads_json(vector["input_json"])), vector["canonical_utf8"].encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
