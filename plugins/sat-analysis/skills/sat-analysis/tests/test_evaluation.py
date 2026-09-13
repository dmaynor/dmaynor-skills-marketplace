"""Regression tests for evaluation integrity, not for SAT prose keywords."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


EVALUATIONS = Path(__file__).resolve().parents[1] / "evaluations"
SPEC = importlib.util.spec_from_file_location("sat_evaluation", EVALUATIONS / "run_evaluation.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Cannot load the evaluation harness")
evaluation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evaluation)


class EvaluationTests(unittest.TestCase):
    """Exercise attribution, completeness, frozen inputs, and comparisons."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.run = self.directory / "trial"
        evaluation.prepare_run(
            self.run,
            condition="none",
            model="test-model",
            settings={"reasoning": "fixed", "tools": "none"},
            selected=["case-06"],
        )

    def scores(self) -> dict:
        """Supply explicit, deliberately synthetic unit-test ratings."""
        answer = "Division by zero caused the exception. Test zero rejection and nonzero division."
        (self.run / "answers/case-06-r01.txt").write_text(answer, encoding="utf-8")
        scores = evaluation.make_score_template(self.run)
        scores["assessor"] = {"id": "synthetic-unit-test-only", "blinded": True}
        for trial in scores["trials"]:
            for judgment in trial["critical_checks"].values():
                judgment.update(status="pass", reason="Synthetic test assertion.", quotes=[answer])
            for judgment in trial["metrics"].values():
                judgment.update(score=2, reason="Synthetic test assertion.", quotes=[answer])
        return scores

    def save_scores(self, scores: dict) -> Path:
        path = self.directory / "scores.json"
        evaluation.write_json(path, scores)
        return path

    def test_suite_and_split_coverage(self) -> None:
        suite, rubric = evaluation.load_suite()
        self.assertEqual(8, sum(case["split"] == "regression" for case in suite["cases"]))
        self.assertGreaterEqual(sum(case["split"] == "held_out" for case in suite["cases"]), 3)
        self.assertEqual(set(rubric["cases"]), {case["id"] for case in suite["cases"]})

    def test_prepared_prompt_contains_only_raw_case(self) -> None:
        suite, _ = evaluation.load_suite()
        raw = next(case["prompt"] for case in suite["cases"] if case["id"] == "case-06")
        prompt = (self.run / "prompts/case-06-r01.txt").read_text(encoding="utf-8")
        self.assertEqual(raw + "\n", prompt)
        self.assertEqual(["case-06-r01.txt"], [path.name for path in (self.run / "prompts").iterdir()])

    def test_missing_scores_are_not_a_perfect_score(self) -> None:
        report = evaluation.evaluate_run(self.run)
        self.assertEqual("not_evaluated", report["status"])
        self.assertEqual(0, report["critical_checks"]["pass"])
        self.assertGreater(report["critical_checks"]["unscored"], 0)
        self.assertEqual(0, report["coverage"]["trials_complete"])
        for metric in report["metrics"].values():
            self.assertIsNone(metric["mean"])
            self.assertEqual(0, metric["scored"])

    def test_valid_explicit_scores_aggregate(self) -> None:
        report = evaluation.evaluate_run(self.run, self.save_scores(self.scores()))
        self.assertEqual("passed_observed_checks", report["status"])
        self.assertEqual(1, report["coverage"]["trials_complete"])
        self.assertEqual(0, report["critical_checks"]["fail"])
        self.assertEqual(2.0, report["metrics"]["useful_decision"]["mean"])

    def test_partial_scores_preserve_denominators(self) -> None:
        scores = self.scores()
        scores["trials"][0]["metrics"].pop("operator_burden")
        scores["trials"][0]["critical_checks"].pop("C2")
        report = evaluation.evaluate_run(self.run, self.save_scores(scores))
        self.assertEqual("incomplete", report["status"])
        self.assertEqual(1, report["critical_checks"]["unscored"])
        self.assertEqual({"mean": None, "scored": 0, "expected": 1}, report["metrics"]["operator_burden"])

    def test_missing_trial_scores_are_unscored(self) -> None:
        scores = self.scores()
        scores["trials"] = []
        report = evaluation.evaluate_run(self.run, self.save_scores(scores))
        self.assertEqual("not_evaluated", report["status"])
        self.assertEqual(1, report["coverage"]["answers_present"])

    def test_explicit_failure_is_preserved_with_missing_metrics(self) -> None:
        scores = self.scores()
        scores["trials"][0]["critical_checks"]["C1"]["status"] = "fail"
        scores["trials"][0]["metrics"] = {}
        report = evaluation.evaluate_run(self.run, self.save_scores(scores))
        self.assertEqual("failed_observed_checks", report["status"])
        self.assertEqual(1, report["critical_checks"]["fail"])
        self.assertEqual(0, report["coverage"]["trials_complete"])

    def test_fabricated_quote_is_rejected(self) -> None:
        scores = self.scores()
        scores["trials"][0]["critical_checks"]["C1"]["quotes"] = ["Words the answer never contained."]
        with self.assertRaisesRegex(evaluation.EvaluationError, "Quote does not occur"):
            evaluation.evaluate_run(self.run, self.save_scores(scores))

    def test_score_without_rationale_or_quote_is_rejected(self) -> None:
        for field, invalid in (("reason", ""), ("quotes", [])):
            with self.subTest(field=field):
                scores = self.scores()
                scores["trials"][0]["metrics"]["operator_burden"][field] = invalid
                with self.assertRaises(evaluation.EvaluationError):
                    evaluation.evaluate_run(self.run, self.save_scores(scores))

    def test_missing_answer_and_changed_answer_are_rejected(self) -> None:
        scores = self.scores()
        answer = self.run / "answers/case-06-r01.txt"
        answer.write_text(answer.read_text() + " New material.", encoding="utf-8")
        with self.assertRaisesRegex(evaluation.EvaluationError, "Missing or changed answer"):
            evaluation.evaluate_run(self.run, self.save_scores(scores))
        answer.unlink()
        with self.assertRaises(evaluation.EvaluationError):
            evaluation.evaluate_run(self.run, self.save_scores(scores))

    def test_unknown_or_duplicate_score_ids_are_rejected(self) -> None:
        for change in ("unknown", "duplicate"):
            with self.subTest(change=change):
                scores = self.scores()
                if change == "unknown":
                    scores["trials"][0]["trial_id"] = "not-a-trial"
                else:
                    scores["trials"].append(deepcopy(scores["trials"][0]))
                with self.assertRaisesRegex(evaluation.EvaluationError, "Unknown or duplicate"):
                    evaluation.evaluate_run(self.run, self.save_scores(scores))

    def test_unknown_check_is_rejected(self) -> None:
        scores = self.scores()
        scores["trials"][0]["critical_checks"]["invented_check"] = evaluation.empty_judgment()
        with self.assertRaisesRegex(evaluation.EvaluationError, "Unknown check"):
            evaluation.evaluate_run(self.run, self.save_scores(scores))

    def test_boolean_and_out_of_range_metric_scores_are_rejected(self) -> None:
        for invalid in (True, False, -1, 3, "2", 1.5):
            with self.subTest(invalid=invalid):
                scores = self.scores()
                scores["trials"][0]["metrics"]["useful_conclusion"]["score"] = invalid
                with self.assertRaisesRegex(evaluation.EvaluationError, "score must be"):
                    evaluation.evaluate_run(self.run, self.save_scores(scores))

    def test_scored_results_require_named_assessor_and_blinding_declaration(self) -> None:
        for assessor in ({"id": "", "blinded": True}, {"id": "a", "blinded": None}, {"id": "a", "blinded": "true"}):
            with self.subTest(assessor=assessor):
                scores = self.scores()
                scores["assessor"] = assessor
                with self.assertRaises(evaluation.EvaluationError):
                    evaluation.evaluate_run(self.run, self.save_scores(scores))

    def test_frozen_rubric_mutation_is_rejected(self) -> None:
        rubric_path = self.run / "assessor/rubric.json"
        rubric = evaluation.read_json(rubric_path)
        rubric["rubric_version"] = "mutated"
        evaluation.write_json(rubric_path, rubric)
        with self.assertRaisesRegex(evaluation.EvaluationError, "rubric fingerprint mismatch"):
            evaluation.evaluate_run(self.run)

    def test_frozen_prompt_mutation_is_rejected(self) -> None:
        (self.run / "prompts/case-06-r01.txt").write_text("Different question.", encoding="utf-8")
        with self.assertRaisesRegex(evaluation.EvaluationError, "Prompt fingerprint mismatch"):
            evaluation.evaluate_run(self.run)

    def test_manifest_path_escape_is_rejected(self) -> None:
        manifest_path = self.run / "manifest.json"
        manifest = evaluation.read_json(manifest_path)
        manifest["trials"][0]["answer_path"] = "../elsewhere.txt"
        evaluation.write_json(manifest_path, manifest)
        with self.assertRaisesRegex(evaluation.EvaluationError, "escapes"):
            evaluation.evaluate_run(self.run)

    def test_run_and_rubric_score_identity_must_match(self) -> None:
        for field in ("run_id", "rubric_sha256"):
            with self.subTest(field=field):
                scores = self.scores()
                scores[field] = "different"
                with self.assertRaisesRegex(evaluation.EvaluationError, "Scores must match"):
                    evaluation.evaluate_run(self.run, self.save_scores(scores))

    def test_comparison_exposes_different_settings_and_incomplete_coverage(self) -> None:
        left = evaluation.evaluate_run(self.run)
        right = deepcopy(left)
        right["condition"] = "revised"
        right["settings"] = {"reasoning": "different"}
        result = evaluation.compare_reports([left, right])
        self.assertEqual("comparison_limited", result["comparison_status"])
        self.assertIn("Different settings", result["limitations"])
        self.assertIn("Incomplete scoring", result["limitations"])

    def test_comparison_requires_matched_prompts(self) -> None:
        left = evaluation.evaluate_run(self.run, self.save_scores(self.scores()))
        right = deepcopy(left)
        right["condition"] = "revised"
        right["trials"][0]["prompt_sha256"] = "changed"
        result = evaluation.compare_reports([left, right])
        self.assertIn("Different case/repeat/prompt coverage", result["limitations"])

    def test_complete_comparison_does_not_claim_general_improvement(self) -> None:
        left = evaluation.evaluate_run(self.run, self.save_scores(self.scores()))
        right = deepcopy(left)
        right["condition"] = "revised"
        result = evaluation.compare_reports([left, right])
        self.assertEqual("descriptive_comparison", result["comparison_status"])
        self.assertNotIn("winner", result)
        self.assertTrue(any("No statistical significance" in text for text in result["limitations"]))

    def test_prepare_never_overwrites_a_run(self) -> None:
        with self.assertRaisesRegex(evaluation.EvaluationError, "Refusing to overwrite"):
            evaluation.prepare_run(self.run, condition="new", model="m", settings={})

    def test_prepare_rejects_selected_case_outside_split(self) -> None:
        with self.assertRaisesRegex(evaluation.EvaluationError, "outside"):
            evaluation.prepare_run(self.directory / "bad", condition="none", model="m", settings={}, selected=["case-09"])

    def test_cli_produces_an_honest_unscored_report(self) -> None:
        report_path = self.directory / "report.json"
        result = subprocess.run(
            [sys.executable, str(EVALUATIONS / "run_evaluation.py"), "report", "--run", str(self.run), "--output", str(report_path)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("not_evaluated", result.stdout)
        self.assertEqual("not_evaluated", json.loads(report_path.read_text())["status"])


if __name__ == "__main__":
    unittest.main()
