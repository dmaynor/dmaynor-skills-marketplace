"""Regression tests for evidence-preserving ACH assessments (stdlib only)."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "ach_matrix.py"
SPEC = importlib.util.spec_from_file_location("sat_ach_matrix_test", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
ach = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ach
SPEC.loader.exec_module(ach)


def matrix_with(rows: list[dict[str, object]]) -> ach.ACHMatrix:
    """Construct two comparable hypotheses and explicitly supplied evidence."""
    return ach.from_json({
        "hypotheses": [{"id": "H1", "description": "Transport delay"},
                       {"id": "H2", "description": "Telemetry artifact"}],
        "evidence": rows,
    })


def row(evidence_id: str, ratings: dict[str, str], **metadata: object) -> dict[str, object]:
    return {"id": evidence_id, "description": evidence_id, "ratings": ratings, **metadata}


class AssessmentTests(unittest.TestCase):
    def test_empty_is_insufficient_and_not_robust(self) -> None:
        for matrix in (ach.ACHMatrix(), matrix_with([]),
                       ach.ACHMatrix(evidence=[ach.Evidence("E1", "Unrated")])):
            with self.subTest(matrix=matrix):
                result = matrix.assessment()
                self.assertEqual(result["status"], "insufficient_evidence")
                self.assertEqual(result["heuristic_leaders"], [])
                self.assertIsNone(result["winner"])
                self.assertIsNone(matrix.sensitivity_analysis()["heuristic_stable"])
                self.assertIn("insufficient_evidence", matrix.to_markdown())

    def test_missing_is_not_neutral(self) -> None:
        matrix = matrix_with([row("E1", {"H1": "N"})])
        result = matrix.assessment()
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["missing_ratings"], [{"evidence_id": "E1", "hypothesis_id": "H2"}])
        self.assertIsNone(matrix.get_diagnosticity()["E1"])
        matrix.rate("E1", "H2", "N")
        self.assertEqual(matrix.assessment()["status"], "underdetermined")
        self.assertEqual(matrix.get_diagnosticity()["E1"], 0)
        self.assertEqual(matrix.assessment()["missing_ratings"], [])

    def test_tied_top_scores_are_underdetermined_and_order_invariant(self) -> None:
        matrix = matrix_with([row("E1", {"H1": "+", "H2": "N"}),
                              row("E2", {"H1": "N", "H2": "+"})])
        result = matrix.assessment()
        matrix.hypotheses.reverse()
        matrix.evidence.reverse()
        self.assertEqual(matrix.assessment(), result)
        self.assertEqual(result["status"], "underdetermined")
        self.assertEqual(result["heuristic_leaders"], ["H1", "H2"])
        self.assertIsNone(result["winner"])

    def test_uniform_support_cannot_differentiate_even_one_hypothesis(self) -> None:
        matrix = ach.ACHMatrix(hypotheses=[ach.Hypothesis("H1", "Only proposed explanation")],
                               evidence=[ach.Evidence("E1", "Supports", ratings={"H1": "++"})])
        self.assertEqual(matrix.assessment()["status"], "underdetermined")

    def test_differentiated_is_still_not_a_causal_winner(self) -> None:
        matrix = matrix_with([row("E1", {"H1": "++", "H2": "--"})])
        result = matrix.assessment()
        self.assertEqual(result["status"], "differentiated")
        self.assertEqual(result["heuristic_leaders"], ["H1"])
        self.assertIsNone(result["winner"])
        self.assertEqual(result["contradictions"]["H2"][0]["rating"], "--")
        self.assertTrue(any("not probabilities" in c for c in result["caveats"]))

    def test_mutated_unknown_hypothesis_and_invalid_ratings_are_rejected(self) -> None:
        matrix = matrix_with([row("E1", {"H1": "N", "H2": "N"})])
        for key, value in (("H9", "+"), ("H1", "maybe")):
            with self.subTest(key=key):
                previous = dict(matrix.evidence[0].ratings)
                matrix.evidence[0].ratings[key] = value
                with self.assertRaises(ValueError):
                    matrix.assessment()
                matrix.evidence[0].ratings = previous
        with self.assertRaises(ValueError):
            matrix.rate("E1", "H9", "+")
        with self.assertRaises(ValueError):
            matrix.rate("E9", "H1", "+")


class OriginAndSensitivityTests(unittest.TestCase):
    def test_republished_observation_is_scored_once(self) -> None:
        original = row("E1", {"H1": "++", "H2": "N"}, origin_id="measurement-9")
        matrix = matrix_with([original])
        scores = matrix.get_scores()
        matrix.evidence.append(ach.Evidence("E2", "Reworded bulletin", "bulletin", "A",
                                           {"H1": "++", "H2": "N"}, "measurement-9"))
        self.assertEqual(matrix.get_scores(), scores)
        self.assertEqual(matrix.assessment()["contributing_record_count"], 1)
        self.assertTrue(any("derivative" in c for c in matrix.assessment()["caveats"]))

    def test_conflicting_or_incomplete_derivative_ratings_fail_closed(self) -> None:
        for duplicate_ratings in ({"H1": "-", "H2": "N"}, {"H1": "+"}):
            with self.subTest(ratings=duplicate_ratings):
                with self.assertRaisesRegex(ValueError, "Conflicting ratings"):
                    matrix_with([row("E1", {"H1": "+", "H2": "N"}, origin_id="same"),
                                 row("E2", duplicate_ratings, origin_id="same")])

    def test_distinct_measurements_about_same_order_remain_distinct(self) -> None:
        matrix = matrix_with([
            row("sent", {"H1": "+", "H2": "N"}, origin_id="order-1-send", source="COL-2"),
            row("received", {"H1": "+", "H2": "N"}, origin_id="order-1-receive", source="COL-2"),
        ])
        self.assertEqual(matrix.get_scores()["H1"], 2)
        self.assertEqual(matrix.assessment()["contributing_record_count"], 2)

    def test_removing_sole_discriminator_exposes_tie(self) -> None:
        matrix = matrix_with([row("E1", {"H1": "+", "H2": "N"}),
                              row("E2", {"H1": "N", "H2": "N"})])
        sensitivity = matrix.sensitivity_analysis()
        impact = sensitivity["evidence_impact"]["E1"]
        self.assertEqual(impact["status"], "underdetermined")
        self.assertEqual(impact["heuristic_leaders"], ["H1", "H2"])
        self.assertTrue(impact["changes_assessment"])
        self.assertFalse(sensitivity["heuristic_stable"])

    def test_removing_last_row_exposes_insufficient_evidence(self) -> None:
        matrix = matrix_with([row("E1", {"H1": "+", "H2": "N"})])
        impact = matrix.sensitivity_analysis()["evidence_impact"]["E1"]
        self.assertEqual(impact["status"], "insufficient_evidence")
        self.assertEqual(impact["heuristic_leaders"], [])
        self.assertTrue(impact["changes_assessment"])

    def test_group_sensitivity_exposes_dependence_hidden_by_row_tests(self) -> None:
        matrix = matrix_with([
            row("E1", {"H1": "+", "H2": "N"}, dependency_groups=["COL-2"]),
            row("E2", {"H1": "+", "H2": "N"}, dependency_groups=["COL-2"]),
            row("E3", {"H1": "N", "H2": "N"}),
        ])
        sensitivity = matrix.sensitivity_analysis()
        self.assertTrue(all(not i["changes_assessment"] for i in sensitivity["evidence_impact"].values()))
        self.assertTrue(sensitivity["group_impact"]["dependency:COL-2"]["changes_assessment"])
        self.assertFalse(sensitivity["heuristic_stable"])

    def test_group_removal_includes_derivatives_with_different_labels(self) -> None:
        matrix = matrix_with([
            row("E1", {"H1": "+", "H2": "N"}, origin_id="event", dependency_groups=["COL-2"]),
            row("E2", {"H1": "+", "H2": "N"}, origin_id="event"),
        ])
        sensitivity = matrix.sensitivity_analysis()
        group = sensitivity["group_impact"]["dependency:COL-2"]
        self.assertEqual(group["removed_evidence_ids"], ["E1", "E2"])
        self.assertEqual(group["status"], "insufficient_evidence")
        self.assertIn("origin:event", sensitivity["group_impact"])
        self.assertFalse(sensitivity["evidence_impact"]["E1"]["changes_assessment"])

    def test_shared_source_removal_exposes_dependence_hidden_by_row_tests(self) -> None:
        matrix = matrix_with([
            row("E1", {"H1": "+", "H2": "N"}, source="collector"),
            row("E2", {"H1": "+", "H2": "N"}, source="collector"),
            row("E3", {"H1": "N", "H2": "N"}, source="independent"),
        ])
        sensitivity = matrix.sensitivity_analysis()
        self.assertEqual(matrix.get_scores()["H1"], 2)
        self.assertTrue(all(not i["changes_assessment"] for i in sensitivity["evidence_impact"].values()))
        group = sensitivity["group_impact"]["source:collector"]
        self.assertEqual(group["removed_evidence_ids"], ["E1", "E2"])
        self.assertEqual(group["status"], "underdetermined")
        self.assertEqual(group["heuristic_leaders"], ["H1", "H2"])
        self.assertTrue(group["changes_assessment"])
        self.assertFalse(sensitivity["heuristic_stable"])

    def test_source_group_removal_includes_republished_observations(self) -> None:
        matrix = matrix_with([
            row("E1", {"H1": "+", "H2": "N"}, source="collector", origin_id="measurement"),
            row("E2", {"H1": "+", "H2": "N"}, source="bulletin", origin_id="measurement"),
            row("E3", {"H1": "N", "H2": "N"}, source="independent"),
        ])
        group = matrix.sensitivity_analysis()["group_impact"]["source:collector"]
        self.assertEqual(group["removed_evidence_ids"], ["E1", "E2"])
        self.assertEqual(group["status"], "underdetermined")
        self.assertTrue(group["changes_assessment"])

    def test_unknown_source_locators_do_not_form_a_shared_source_group(self) -> None:
        matrix = matrix_with([
            row("E1", {"H1": "+", "H2": "N"}, source=""),
            row("E2", {"H1": "+", "H2": "N"}, source=" \t"),
        ])
        self.assertEqual(matrix.sensitivity_analysis()["group_impact"], {})

    def test_status_change_counts_even_if_leader_ids_remain_equal(self) -> None:
        matrix = matrix_with([row("E1", {"H1": "+", "H2": "N"}), row("E2", {"H1": "+"})])
        impact = matrix.sensitivity_analysis()["evidence_impact"]["E2"]
        self.assertEqual(matrix.assessment()["status"], "incomplete")
        self.assertEqual(impact["status"], "differentiated")
        self.assertEqual(matrix.assessment()["heuristic_leaders"], impact["heuristic_leaders"])
        self.assertTrue(impact["changes_assessment"])
        self.assertIsNone(matrix.sensitivity_analysis()["heuristic_stable"])

    def test_unknown_reliability_remains_unknown_without_weighting(self) -> None:
        matrix = matrix_with([row("E1", {"H1": "+", "H2": "N"}, reliability="F")])
        before = matrix.get_scores()
        self.assertTrue(any("unknown or unjudged" in c for c in matrix.assessment()["caveats"]))
        matrix.evidence[0].reliability = "A"
        self.assertEqual(matrix.get_scores(), before)


class ProbabilityAndValidationTests(unittest.TestCase):
    def probabilities(self, values: list[object], relationship: str) -> ach.ACHMatrix:
        return ach.from_json({"relationship": relationship, "hypotheses": [
            {"id": f"H{i}", "description": "Proposition", "initial_probability": value}
            for i, value in enumerate(values)
        ]})

    def test_invalid_probability_types_and_ranges_are_rejected(self) -> None:
        for value in (True, False, math.nan, math.inf, -math.inf, -0.1, 1.01, "0.5", [0.4, 0.6], 10 ** 1000):
            with self.subTest(value=str(value)[:40]), self.assertRaises(ValueError):
                self.probabilities([value], "unspecified")

    def test_exhaustive_requires_one_only_when_fully_quantified(self) -> None:
        self.probabilities([0.2, 0.3, 0.5], "exclusive_exhaustive")
        partial = self.probabilities([0.2, None], "exclusive_exhaustive")
        self.assertIsNone(partial.hypotheses[1].initial_probability)
        with self.assertRaises(ValueError):
            self.probabilities([0.2, 0.3], "exclusive_exhaustive")
        with self.assertRaises(ValueError):
            self.probabilities([0.8, 0.8, None], "exclusive_exhaustive")

    def test_exclusive_nonexhaustive_allows_unallocated_mass(self) -> None:
        self.probabilities([0.2, 0.3], "exclusive_nonexhaustive")
        with self.assertRaises(ValueError):
            self.probabilities([0.8, 0.8, None], "exclusive_nonexhaustive")

    def test_overlapping_and_unspecified_have_no_arbitrary_sum_band(self) -> None:
        for relationship in ("overlapping", "unspecified"):
            self.probabilities([0.9, 0.9, 0.9], relationship)
            self.probabilities([0.01, 0.01], relationship)
            self.probabilities([0.0, None], relationship)

    def test_ids_and_structures_are_strictly_validated(self) -> None:
        bad_inputs = [
            [], {"hypotheses": None}, {"evidence": {}}, {"title": None},
            {"relationship": []}, {"relationship": "exclusive"}, {"extra": 1},
            {"schema_version": "99"}, {"hypotheses": [{"id": "", "description": "x"}]},
            {"hypotheses": [{"id": "  ", "description": "x"}]},
            {"hypotheses": [{"id": "H", "description": "x"}, {"id": "H", "description": "y"}]},
            {"hypotheses": [{"id": "H"}]},
            {"evidence": [row("E", {}), row("E", {})]},
            {"evidence": [row("E", {}, dependency_groups="source")]},
            {"evidence": [row("E", {}, dependency_groups=["s", "s"])]},
            {"evidence": [row("E", {}, dependency_groups=[""])]},
            {"evidence": [row("E", {}, origin_id="")]},
            {"evidence": [row("E", {}, unexpected=True)]},
            {"evidence": [row("E", {"H9": "N"})]},
            {"evidence": [{"id": "E", "description": "x", "ratings": []}]},
        ]
        for data in bad_inputs:
            with self.subTest(data=data), self.assertRaises(ValueError):
                ach.from_json(data)

    def test_add_entrypoints_reject_duplicate_ids_and_bad_metadata(self) -> None:
        matrix = ach.create_empty_matrix([("H", "one")], [("E", "two")])
        with self.assertRaises(ValueError):
            matrix.add_hypothesis("H", "duplicate")
        with self.assertRaises(ValueError):
            matrix.add_evidence("E", "duplicate")
        with self.assertRaises(ValueError):
            matrix.add_evidence("new", "bad groups", dependency_groups="source")


class ExportAndCLITests(unittest.TestCase):
    def test_roundtrip_preserves_inputs_but_recomputes_derived_outputs(self) -> None:
        matrix = matrix_with([row("E1", {"H1": "+", "H2": "--"}, origin_id="measurement", dependency_groups=["collector"])])
        matrix.hypotheses[0].initial_probability = 0
        matrix.hypotheses[0].falsifier = "A valid observation contradicts its necessary prediction."
        data = json.loads(matrix.to_json())
        data["scores"] = {"H1": 9999}
        data["assessment"] = {"winner": "H1"}
        restored = ach.from_json(data)
        self.assertEqual(restored.to_json(), matrix.to_json())
        self.assertIn("initial likelihood: 0", matrix.to_markdown())

    def test_markdown_escapes_all_supplied_text_without_truncation(self) -> None:
        malicious = "<script>alert(1)</script>|[x](https://example.org)\n## forged `command`"
        matrix = ach.ACHMatrix(title=malicious)
        matrix.add_hypothesis("H|1", malicious, category=malicious, falsifier=malicious)
        matrix.add_evidence("E|1", malicious, source=malicious, reliability=malicious,
                            origin_id=malicious, dependency_groups=[malicious])
        matrix.rate("E|1", "H|1", "--")
        output = matrix.to_markdown()
        self.assertNotIn("<script>", output)
        self.assertNotIn("\n## forged", output)
        self.assertNotIn("[x](https://", output)
        self.assertIn("&lt;script&gt;", output)
        self.assertIn("E\\|1", output)
        self.assertIn("forged", output)

    def test_json_cli_emits_machine_readable_assessment(self) -> None:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = ach.main(["example", "--output-format", "json"])
        self.assertEqual(code, 0)
        data = json.loads(out.getvalue())
        self.assertIsNone(data["assessment"]["winner"])
        self.assertEqual(data["relationship"], "overlapping")

    def test_create_cli_rejects_duplicate_keys_and_nonfinite_json(self) -> None:
        for content in ('{"hypotheses": [], "hypotheses": []}',
                        '{"hypotheses": [{"id":"H","description":"x","initial_probability":NaN}]}',
                        '{"evidence": [{"id":"E","description":"x","ratings":{"H":"+","H":"-"}}]}'):
            with self.subTest(content=content), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "bad.json"
                path.write_text(content, encoding="utf-8")
                out, err = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    code = ach.main(["create", str(path), "--output-format", "json"])
                self.assertEqual(code, 2)
                self.assertEqual(out.getvalue(), "")
                self.assertIn("ach_matrix:", err.getvalue())


if __name__ == "__main__":
    unittest.main()
