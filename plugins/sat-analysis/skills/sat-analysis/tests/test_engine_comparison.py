"""Comparison behavior from hand-authored synthetic assessor reports only.

These fixtures do not load evaluation prompts, rubrics, answers, or benchmark data.
They establish aggregation and refusal behavior, not empirical skill accuracy.
"""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import hashlib
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from evaluations.compare_engine_runs import ComparisonError, compare_engine_reports, main


CONDITIONS = ("no-skill", "current-corrected", "engine")
METRICS = ("useful_conclusion", "useful_decision", "operator_burden")
CHECKS = ("trace", "restraint")


def _fingerprint(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _supported(**value: object) -> dict:
    return {**value, "reason": "Synthetic assessor rationale.", "quotes": ["Synthetic answer excerpt."]}


def _summarize(report: dict) -> dict:
    """Keep a synthetic evaluator report internally consistent after fixture edits."""
    trials = report["trials"]
    statuses = [check["status"] for trial in trials for check in trial["critical_checks"].values()]
    report["coverage"] = {
        "trials_expected": len(trials),
        "answers_present": len(trials),
        "trials_complete": sum(trial["complete"] is True for trial in trials),
    }
    report["critical_checks"] = {status: statuses.count(status) for status in ("pass", "fail", "unscored")}
    report["metrics"] = {}
    for metric in METRICS:
        scores = [trial["metrics"][metric]["score"] for trial in trials]
        observed = [score for score in scores if score is not None]
        report["metrics"][metric] = {
            "mean": sum(observed) / len(observed) if observed else None,
            "scored": len(observed),
            "expected": len(trials),
        }
    report["status"] = (
        "failed_observed_checks" if "fail" in statuses
        else "incomplete" if report["coverage"]["trials_complete"] != len(trials)
        else "passed_observed_checks"
    )
    return report


def _report(condition: str, cases: tuple[str, ...] = ("orchid", "quartz"), repeats: int = 2) -> dict:
    trials = []
    for case in cases:
        for repeat in range(1, repeats + 1):
            trials.append({
                "trial_id": f"{condition}-{case}-{repeat}",
                "case_id": case,
                "repeat": repeat,
                "split": "regression",
                "prompt_sha256": _fingerprint(f"synthetic prompt {case}"),
                "answer_sha256": _fingerprint(f"synthetic answer {condition} {case} {repeat}"),
                "answer_words": 12,
                "complete": True,
                "critical_checks": {check: _supported(status="pass") for check in CHECKS},
                "metrics": {metric: _supported(score=1) for metric in METRICS},
            })
    return _summarize({
        "schema_version": "1.0.0",
        "run_id": f"synthetic-{condition}",
        "condition": condition,
        "model": "synthetic-model",
        "settings": {"temperature": 0, "reasoning": "synthetic-setting"},
        "skill_sha256": None if condition == "no-skill" else _fingerprint(condition),
        "rubric_sha256": _fingerprint("synthetic rubric identity"),
        "assessor": {"id": f"assessor-{condition}", "blinded": True},
        "trials": trials,
        "limitations": ["Hand-authored synthetic report for software behavior tests."],
    })


def _reports(cases: tuple[str, ...] = ("orchid", "quartz"), repeats: int = 2) -> list[dict]:
    return [_report(condition, cases, repeats) for condition in CONDITIONS]


def _fail(report: dict, case: str, criterion: str, *repeats: int) -> None:
    for trial in report["trials"]:
        if trial["case_id"] == case and trial["repeat"] in repeats:
            trial["critical_checks"][criterion]["status"] = "fail"
    _summarize(report)


class EngineComparisonResultTests(unittest.TestCase):
    def test_tied_primary_is_not_improved_even_when_all_secondary_metrics_rise(self) -> None:
        reports = _reports()
        for trial in reports[2]["trials"]:
            for metric in METRICS:
                trial["metrics"][metric]["score"] = 2
        _summarize(reports[2])

        result = compare_engine_reports(*reports)

        comparison = result["comparisons"]["engine_vs_current_corrected"]
        self.assertEqual(comparison["role"], "primary")
        self.assertEqual(comparison["comparator"], "current-corrected")
        self.assertEqual(comparison["both_pass"], 2)
        self.assertEqual(comparison["wins"], 0)
        self.assertEqual(comparison["losses"], 0)
        self.assertEqual(comparison["rate_difference"], 0)
        self.assertEqual(comparison["case_rate_comparison"], "equal")
        self.assertEqual(comparison["improvement"], "not_improved")
        self.assertEqual(comparison["secondary_metric_differences"], dict.fromkeys(METRICS, 1))

    def test_primary_requires_every_criterion_in_every_repeat(self) -> None:
        reports = _reports()
        _fail(reports[2], "orchid", "trace", 2)

        result = compare_engine_reports(*reports)

        engine = result["conditions"]["engine"]
        self.assertEqual(engine["primary"], {"passed_cases": 1, "total_cases": 2, "pass_rate": 0.5})
        self.assertIs(engine["cases"]["orchid"]["primary_pass"], False)
        self.assertIs(engine["cases"]["quartz"]["primary_pass"], True)
        self.assertEqual(engine["cases"]["orchid"]["critical_checks"]["trace"], {
            "passes_all_repeats": False, "failed_repeats": [2],
        })
        self.assertEqual(engine["cases"]["orchid"]["critical_checks"]["restraint"], {
            "passes_all_repeats": True, "failed_repeats": [],
        })
        comparison = result["comparisons"]["engine_vs_current_corrected"]
        self.assertEqual(comparison["losses"], 1)
        self.assertEqual(comparison["case_rate_comparison"], "lower")
        self.assertEqual(comparison["improvement"], "not_improved")

    def test_new_criterion_regression_is_exposed_despite_more_case_wins(self) -> None:
        reports = _reports(("orchid", "quartz", "tulip"))
        _fail(reports[1], "quartz", "trace", 1, 2)
        _fail(reports[1], "tulip", "trace", 1, 2)
        _fail(reports[2], "orchid", "restraint", 2)

        result = compare_engine_reports(*reports)

        comparison = result["comparisons"]["engine_vs_current_corrected"]
        self.assertEqual(comparison["wins"], 2)
        self.assertEqual(comparison["losses"], 1)
        self.assertAlmostEqual(comparison["rate_difference"], 1 / 3)
        self.assertEqual(comparison["case_rate_comparison"], "higher")
        self.assertEqual(comparison["improvement"], "higher_observed_case_rate")
        self.assertEqual(comparison["new_regression_count"], 1)
        self.assertEqual(comparison["new_regressions"], [
            {"case_id": "orchid", "criterion": "restraint", "engine_failed_repeats": [2]},
        ])

    def test_regression_on_already_failed_case_is_not_masked_by_primary_tie(self) -> None:
        reports = _reports()
        _fail(reports[1], "orchid", "trace", 1)
        _fail(reports[2], "orchid", "trace", 1)
        _fail(reports[2], "orchid", "restraint", 1, 2)

        result = compare_engine_reports(*reports)

        comparison = result["comparisons"]["engine_vs_current_corrected"]
        self.assertEqual(comparison["both_fail"], 1)
        self.assertEqual(comparison["improvement"], "not_improved")
        self.assertEqual(comparison["new_regressions"], [
            {"case_id": "orchid", "criterion": "restraint", "engine_failed_repeats": [1, 2]},
        ])

    def test_no_skill_is_supporting_and_cannot_replace_corrected_primary(self) -> None:
        reports = _reports()
        for case in ("orchid", "quartz"):
            _fail(reports[0], case, "trace", 1, 2)

        result = compare_engine_reports(*reports)

        self.assertEqual(result["comparisons"]["engine_vs_current_corrected"]["improvement"], "not_improved")
        supporting = result["comparisons"]["engine_vs_no_skill"]
        self.assertEqual(supporting["role"], "supporting")
        self.assertEqual(supporting["wins"], 2)
        self.assertEqual(supporting["improvement"], "higher_observed_case_rate")

    def test_secondary_metrics_average_repeats_then_cases_and_ignore_answer_length(self) -> None:
        reports = _reports()
        scores = ((0, 2, 0), (2, 0, 1), (2, 0, 1), (2, 0, 2))
        for trial, values, words in zip(reports[2]["trials"], scores, (10, 30, 500, 1500)):
            for metric, score in zip(METRICS, values):
                trial["metrics"][metric]["score"] = score
            trial["answer_words"] = words
        _summarize(reports[2])

        result = compare_engine_reports(*reports)

        engine = result["conditions"]["engine"]
        self.assertEqual(engine["cases"]["orchid"]["secondary_metrics"], {
            "useful_conclusion": 1, "useful_decision": 1, "operator_burden": 0.5,
        })
        self.assertEqual(engine["cases"]["quartz"]["secondary_metrics"], {
            "useful_conclusion": 2, "useful_decision": 0, "operator_burden": 1.5,
        })
        self.assertEqual(engine["secondary_metrics"], {
            "useful_conclusion": 1.5, "useful_decision": 0.5, "operator_burden": 1,
        })
        self.assertEqual(engine["cases"]["orchid"]["answer_words_mean"], 20)
        self.assertEqual(engine["cases"]["quartz"]["answer_words_mean"], 1000)
        self.assertEqual(result["comparisons"]["engine_vs_current_corrected"]["secondary_metric_differences"], {
            "useful_conclusion": 0.5, "useful_decision": -0.5, "operator_burden": 0,
        })

    def test_trial_order_and_condition_specific_ids_do_not_change_pairing(self) -> None:
        reports = _reports()
        _fail(reports[1], "orchid", "trace", 1)
        expected = compare_engine_reports(*reports)
        reports[0]["trials"].reverse()
        reports[1]["trials"] = reports[1]["trials"][2:] + reports[1]["trials"][:2]
        reports[2]["trials"].reverse()

        self.assertEqual(compare_engine_reports(*reports), expected)

    def test_comparison_does_not_mutate_reports(self) -> None:
        reports = _reports()
        _fail(reports[2], "orchid", "trace", 1)
        original = deepcopy(reports)

        compare_engine_reports(*reports)

        self.assertEqual(reports, original)

    def test_explicit_case_count_and_three_repeats_are_supported(self) -> None:
        result = compare_engine_reports(*_reports(repeats=3), expected_repeats=3, expected_cases=2)

        self.assertEqual(result["schema_version"], "1.0.0")
        self.assertEqual(result["comparison_status"], "descriptive_case_comparison")
        self.assertEqual(result["coverage"], {
            "case_count": 2, "repeats_per_case": 3, "trials_per_condition": 6,
            "case_ids": ["orchid", "quartz"],
        })
        self.assertTrue(result["limitations"])


class EngineComparisonValidationTests(unittest.TestCase):
    def test_rejects_wrong_condition_in_each_positional_slot(self) -> None:
        for position, wrong in ((0, "baseline"), (1, "current"), (2, "current-corrected")):
            reports = _reports()
            reports[position]["condition"] = wrong
            with self.subTest(position=position), self.assertRaises(ComparisonError):
                compare_engine_reports(*reports)

    def test_rejects_mismatched_model_settings_and_rubric(self) -> None:
        changes = {
            "model": "other-model",
            "settings": {"temperature": 1, "reasoning": "synthetic-setting"},
            "rubric_sha256": _fingerprint("different synthetic rubric"),
        }
        for field, value in changes.items():
            reports = _reports()
            reports[2][field] = value
            with self.subTest(field=field), self.assertRaises(ComparisonError):
                compare_engine_reports(*reports)

    def test_rejects_unblinded_or_undeclared_assessment(self) -> None:
        for value in (False, None, 1, "true"):
            reports = _reports()
            reports[1]["assessor"]["blinded"] = value
            with self.subTest(value=value), self.assertRaises(ComparisonError):
                compare_engine_reports(*reports)

    def test_rejects_incomplete_trial_even_when_report_counts_claim_completion(self) -> None:
        for value in (False, None, 1, "true"):
            reports = _reports()
            reports[2]["trials"][0]["complete"] = value
            with self.subTest(value=value), self.assertRaises(ComparisonError):
                compare_engine_reports(*reports)

    def test_rejects_unscored_invalid_and_empty_critical_checks(self) -> None:
        for status in ("unscored", "unknown", None, True):
            reports = _reports()
            reports[2]["trials"][0]["critical_checks"]["trace"]["status"] = status
            with self.subTest(status=status), self.assertRaises(ComparisonError):
                compare_engine_reports(*reports)
        reports = _reports()
        for report in reports:
            for trial in report["trials"]:
                trial["critical_checks"] = {}
            _summarize(report)
        with self.assertRaises(ComparisonError):
            compare_engine_reports(*reports)

    def test_rejects_metric_scores_outside_three_integer_values(self) -> None:
        for metric in METRICS:
            for score in (None, True, False, 1.0, -1, 3, "1"):
                reports = _reports()
                reports[2]["trials"][0]["metrics"][metric]["score"] = score
                with self.subTest(metric=metric, score=score), self.assertRaises(ComparisonError):
                    compare_engine_reports(*reports)

    def test_rejects_missing_and_extra_metric_coverage(self) -> None:
        for change in ("missing", "extra"):
            reports = _reports()
            metrics = reports[2]["trials"][0]["metrics"]
            if change == "missing":
                del metrics["operator_burden"]
            else:
                metrics["unrequested_metric"] = _supported(score=2)
            with self.subTest(change=change), self.assertRaises(ComparisonError):
                compare_engine_reports(*reports)

    def test_rejects_missing_support_for_checks_and_metrics(self) -> None:
        for group, key in (("critical_checks", "trace"), ("metrics", "useful_decision")):
            for field, value in (("reason", ""), ("reason", "  "), ("quotes", []), ("quotes", "excerpt"), ("quotes", [""]), ("quotes", ["valid", None])):
                reports = _reports()
                reports[2]["trials"][0][group][key][field] = value
                with self.subTest(group=group, field=field, value=value), self.assertRaises(ComparisonError):
                    compare_engine_reports(*reports)

    def test_rejects_missing_or_malformed_provenance_hashes(self) -> None:
        for field in ("answer_sha256", "prompt_sha256"):
            for value in (None, "", " ", "not-a-hash", "z" * 64):
                reports = _reports()
                reports[2]["trials"][0][field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ComparisonError):
                    compare_engine_reports(*reports)

    def test_rejects_different_case_repeat_prompt_coverage(self) -> None:
        for field, value in (("case_id", "unpaired-case"), ("prompt_sha256", _fingerprint("changed prompt"))):
            reports = _reports()
            reports[2]["trials"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ComparisonError):
                compare_engine_reports(*reports)

    def test_rejects_prompt_change_between_repeats_even_when_conditions_match(self) -> None:
        reports = _reports()
        for report in reports:
            report["trials"][1]["prompt_sha256"] = _fingerprint("different second repeat")
        with self.assertRaises(ComparisonError):
            compare_engine_reports(*reports)

    def test_rejects_critical_check_coverage_mismatch(self) -> None:
        for scope in ("one_repeat", "entire_condition"):
            reports = _reports()
            trials = reports[2]["trials"][:1] if scope == "one_repeat" else reports[2]["trials"]
            for trial in trials:
                trial["critical_checks"]["renamed"] = trial["critical_checks"].pop("trace")
            _summarize(reports[2])
            with self.subTest(scope=scope), self.assertRaises(ComparisonError):
                compare_engine_reports(*reports)

    def test_rejects_duplicate_trial_id_even_with_distinct_case_repeat(self) -> None:
        reports = _reports()
        reports[2]["trials"][1]["trial_id"] = reports[2]["trials"][0]["trial_id"]
        with self.assertRaises(ComparisonError):
            compare_engine_reports(*reports)

    def test_rejects_duplicate_case_repeat_even_with_distinct_trial_ids(self) -> None:
        reports = _reports()
        reports[2]["trials"][1]["repeat"] = 1
        with self.assertRaises(ComparisonError):
            compare_engine_reports(*reports)

    def test_rejects_missing_repeat_with_consistent_summaries_in_all_conditions(self) -> None:
        reports = _reports()
        for report in reports:
            report["trials"].pop(1)
            _summarize(report)
        with self.assertRaises(ComparisonError):
            compare_engine_reports(*reports)

    def test_rejects_noncontiguous_and_noninteger_repeat_ids(self) -> None:
        for repeat in (0, 3, True, 1.0, "1"):
            reports = _reports()
            for report in reports:
                report["trials"][0]["repeat"] = repeat
            with self.subTest(repeat=repeat), self.assertRaises(ComparisonError):
                compare_engine_reports(*reports)

    def test_rejects_invalid_expected_counts_and_wrong_case_count(self) -> None:
        for keyword in ("expected_repeats", "expected_cases"):
            for count in (0, -1, True, 2.0, "2"):
                with self.subTest(keyword=keyword, count=count), self.assertRaises(ComparisonError):
                    compare_engine_reports(*_reports(), **{keyword: count})
        with self.assertRaises(ComparisonError):
            compare_engine_reports(*_reports(), expected_cases=3)

    def test_rejects_forged_coverage_and_critical_summary_counts(self) -> None:
        for section, field in (
            ("coverage", "trials_expected"), ("coverage", "answers_present"),
            ("coverage", "trials_complete"), ("critical_checks", "pass"),
            ("critical_checks", "fail"), ("critical_checks", "unscored"),
        ):
            reports = _reports()
            reports[2][section][field] += 1
            with self.subTest(section=section, field=field), self.assertRaises(ComparisonError):
                compare_engine_reports(*reports)

    def test_rejects_forged_metric_summary_statistics(self) -> None:
        for metric in METRICS:
            for field, value in (("mean", 1.5), ("scored", 3), ("expected", 3)):
                reports = _reports()
                reports[2]["metrics"][metric][field] = value
                with self.subTest(metric=metric, field=field), self.assertRaises(ComparisonError):
                    compare_engine_reports(*reports)

    def test_rejects_missing_required_summaries(self) -> None:
        for field in ("coverage", "critical_checks", "metrics"):
            reports = _reports()
            del reports[2][field]
            with self.subTest(field=field), self.assertRaises(ComparisonError):
                compare_engine_reports(*reports)


class EngineComparisonCLITests(unittest.TestCase):
    def _invoke(self, reports: list[dict], *options: str) -> tuple[int, dict, str]:
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for index, report in enumerate(reports):
                path = Path(directory) / f"report-{index}.json"
                path.write_text(json.dumps(report), encoding="utf-8")
                paths.append(str(path))
            output, error = StringIO(), StringIO()
            with redirect_stdout(output), redirect_stderr(error):
                status = main([*paths, *options])
            return status, json.loads(output.getvalue()), error.getvalue()

    def test_cli_emits_same_comparison_as_python_api(self) -> None:
        reports = _reports(repeats=3)
        _fail(reports[1], "orchid", "trace", 1, 3)

        status, output, _ = self._invoke(reports, "--expected-repeats", "3", "--expected-cases", "2")

        self.assertEqual(status, 0)
        self.assertEqual(output, compare_engine_reports(*reports, expected_repeats=3, expected_cases=2))

    def test_cli_invalid_report_returns_json_error_and_exit_two(self) -> None:
        reports = _reports()
        reports[2]["trials"][0]["complete"] = False

        status, output, _ = self._invoke(reports)

        self.assertEqual(status, 2)
        self.assertIn("error", output)
        self.assertNotIn("comparisons", output)

    def test_cli_unreadable_report_returns_json_error_and_exit_two(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = str(Path(directory) / "missing.json")
            output, error = StringIO(), StringIO()
            with redirect_stdout(output), redirect_stderr(error):
                status = main([missing, missing, missing])

        self.assertEqual(status, 2)
        self.assertIn("error", json.loads(output.getvalue()))


if __name__ == "__main__":
    unittest.main()
