#!/usr/bin/env python3
"""Compare complete evaluation reports using cases, not repeated trials, as units.

Consumes evaluate_run reports only. This module never reads solver prompts,
rubrics, raw answers, credentials, or network services and never grades prose.
Python 3.12+, standard library only.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import re
import sys
from typing import Any


SCHEMA_VERSION = "1.0.0"
CONDITIONS = ("no-skill", "current-corrected", "engine")
METRICS = ("useful_conclusion", "useful_decision", "operator_burden")


class ComparisonError(ValueError):
    """An incomplete, inconsistent, or unmatched comparison cannot be reported."""


def _object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ComparisonError(f"{label} must be an object with string keys")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ComparisonError(f"{label} must be nonempty text")
    return value


def _count(value: object, label: str, *, positive: bool = False) -> int:
    if type(value) is not int or not (1 if positive else 0) <= value <= 2**53 - 1:
        raise ComparisonError(f"{label} must be a {'positive' if positive else 'nonnegative'} integer within the portable JSON integer range")
    return value


def _hash(value: object, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-fA-F]{64}", value) is None:
        raise ComparisonError(f"{label} must be a SHA-256 hex digest")
    return value.lower()


def _json_key(value: object, label: str) -> str:
    """Compare declared controls without repairing or dropping their values."""
    def check(item: object, ancestors: set[int]) -> None:
        if item is None or type(item) in (str, bool, int):
            if type(item) is str:
                item.encode("utf-8", "strict")
            return
        if type(item) is float:
            if not math.isfinite(item):
                raise ComparisonError(f"{label} contains a nonfinite number")
            return
        if type(item) not in (dict, list):
            raise ComparisonError(f"{label} must contain only JSON values")
        if id(item) in ancestors:
            raise ComparisonError(f"{label} contains a cycle")
        ancestors.add(id(item))
        try:
            if isinstance(item, dict):
                for key, child in item.items():
                    if type(key) is not str:
                        raise ComparisonError(f"{label} contains a non-string object key")
                    check(key, ancestors)
                    check(child, ancestors)
            else:
                for child in item:
                    check(child, ancestors)
        finally:
            ancestors.remove(id(item))
    try:
        check(value, set())
        return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
    except (UnicodeError, RecursionError, TypeError, ValueError) as exc:
        if isinstance(exc, ComparisonError):
            raise
        raise ComparisonError(f"{label} is not valid JSON: {exc}") from exc


def _supported(judgment: dict[str, Any], label: str) -> None:
    _text(judgment.get("reason"), f"{label}.reason")
    quotes = judgment.get("quotes")
    if not isinstance(quotes, list) or not quotes:
        raise ComparisonError(f"{label}.quotes must contain supporting text")
    for quote in quotes:
        _text(quote, f"{label}.quotes entry")


def _report(report: object, condition: str, repeats: int, case_count: int | None) -> dict[str, Any]:
    """Validate every trial and recompute all report summary assertions."""
    report = _object(report, condition)
    _json_key(report, condition)
    if report.get("schema_version") != SCHEMA_VERSION:
        raise ComparisonError(f"{condition}: unsupported report schema_version")
    if report.get("condition") != condition:
        raise ComparisonError(f"Expected condition {condition!r}, got {report.get('condition')!r}")
    run_id = _text(report.get("run_id"), f"{condition}.run_id")
    model = _text(report.get("model"), f"{condition}.model")
    settings = _json_key(_object(report.get("settings"), f"{condition}.settings"), "settings")
    rubric = _hash(report.get("rubric_sha256"), f"{condition}.rubric_sha256")
    assessor = _object(report.get("assessor"), f"{condition}.assessor")
    _text(assessor.get("id"), f"{condition}.assessor.id")
    if assessor.get("blinded") is not True:
        raise ComparisonError(f"{condition}: assessor blinding must be explicitly true")
    trials = report.get("trials")
    if not isinstance(trials, list) or not trials:
        raise ComparisonError(f"{condition}.trials must be a nonempty array")
    by_case: dict[str, dict[int, dict[str, Any]]] = {}
    trial_ids: set[str] = set()
    counts: Counter[str] = Counter()
    metric_values: dict[str, list[int]] = {key: [] for key in METRICS}
    coverage: dict[tuple[str, int], tuple[str, str, tuple[str, ...]]] = {}
    for index, trial in enumerate(trials):
        label = f"{condition}.trials[{index}]"
        trial = _object(trial, label)
        trial_id = _text(trial.get("trial_id"), f"{label}.trial_id")
        case = _text(trial.get("case_id"), f"{label}.case_id")
        repeat = _count(trial.get("repeat"), f"{label}.repeat", positive=True)
        if trial_id in trial_ids:
            raise ComparisonError(f"{condition}: duplicate trial ID {trial_id!r}")
        trial_ids.add(trial_id)
        records = by_case.setdefault(case, {})
        if repeat in records:
            raise ComparisonError(f"{condition}: duplicate case/repeat pair {case!r}/{repeat}")
        records[repeat] = trial
        if trial.get("complete") is not True:
            raise ComparisonError(f"{label}: incomplete scoring")
        prompt = _hash(trial.get("prompt_sha256"), f"{label}.prompt_sha256")
        _hash(trial.get("answer_sha256"), f"{label}.answer_sha256")
        _count(trial.get("answer_words"), f"{label}.answer_words", positive=True)
        split = trial.get("split")
        if split not in ("regression", "held_out"):
            raise ComparisonError(f"{label}: invalid case split")
        checks = _object(trial.get("critical_checks"), f"{label}.critical_checks")
        if not checks:
            raise ComparisonError(f"{label}: no critical checks supplied")
        for check_id, judgment in checks.items():
            _text(check_id, f"{label}.critical check ID")
            judgment = _object(judgment, f"{label}.{check_id}")
            state = judgment.get("status")
            if state not in ("pass", "fail"):
                raise ComparisonError(f"{label}.{check_id}: each critical check requires pass or fail")
            _supported(judgment, f"{label}.{check_id}")
            counts[state] += 1
        metrics = _object(trial.get("metrics"), f"{label}.metrics")
        if set(metrics) != set(METRICS):
            raise ComparisonError(f"{label}: exactly all three secondary metrics are required")
        for metric, judgment in metrics.items():
            judgment = _object(judgment, f"{label}.{metric}")
            score = judgment.get("score")
            if type(score) is not int or score not in (0, 1, 2):
                raise ComparisonError(f"{label}.{metric}: complete metric score must be 0, 1, or 2")
            _supported(judgment, f"{label}.{metric}")
            metric_values[metric].append(score)
        coverage[(case, repeat)] = (prompt, split, tuple(sorted(checks)))
    if case_count is not None and len(by_case) != case_count:
        raise ComparisonError(f"{condition}: expected {case_count} cases, found {len(by_case)}")
    for case, records in by_case.items():
        if len(records) != repeats or min(records) != 1 or max(records) != repeats:
            raise ComparisonError(f"{condition}/{case}: requires exactly repeats 1 through {repeats}")
        shapes = {coverage[(case, repeat)] for repeat in records}
        if len(shapes) != 1:
            raise ComparisonError(f"{condition}/{case}: prompt, split, and critical-check coverage must match across repeats")

    total = len(trials)
    declared_coverage = _object(report.get("coverage"), f"{condition}.coverage")
    for key in ("trials_expected", "answers_present", "trials_complete"):
        if _count(declared_coverage.get(key), f"{condition}.coverage.{key}") != total:
            raise ComparisonError(f"{condition}: incomplete or inconsistent declared coverage ({key})")
    declared_checks = _object(report.get("critical_checks"), f"{condition}.critical_checks")
    if set(declared_checks) != {"pass", "fail", "unscored"}:
        raise ComparisonError(f"{condition}: critical summary requires pass, fail, and unscored counts")
    for key in ("pass", "fail", "unscored"):
        if _count(declared_checks[key], f"{condition}.critical_checks.{key}") != counts[key]:
            raise ComparisonError(f"{condition}: inconsistent critical-check summary ({key})")
    expected_status = "failed_observed_checks" if counts["fail"] else "passed_observed_checks"
    if report.get("status") != expected_status:
        raise ComparisonError(f"{condition}: report status disagrees with complete trial scores")
    declared_metrics = _object(report.get("metrics"), f"{condition}.metrics")
    if set(declared_metrics) != set(METRICS):
        raise ComparisonError(f"{condition}: incomplete secondary metric summary")
    for metric, values in metric_values.items():
        summary = _object(declared_metrics[metric], f"{condition}.metrics.{metric}")
        if any(_count(summary.get(key), f"{condition}.{metric}.{key}") != total for key in ("scored", "expected")):
            raise ComparisonError(f"{condition}: incomplete metric coverage ({metric})")
        mean = summary.get("mean")
        if type(mean) not in (int, float) or not 0 <= mean <= 2 or not math.isfinite(mean) or not math.isclose(mean, sum(values) / total, rel_tol=0, abs_tol=1e-12):
            raise ComparisonError(f"{condition}: metric mean disagrees with trial scores ({metric})")

    cases: dict[str, Any] = {}
    for case, records in sorted(by_case.items()):
        ordered = [records[repeat] for repeat in range(1, repeats + 1)]
        checks = {}
        for check in sorted(ordered[0]["critical_checks"]):
            failed = [trial["repeat"] for trial in ordered if trial["critical_checks"][check]["status"] == "fail"]
            checks[check] = {"passes_all_repeats": not failed, "failed_repeats": failed}
        cases[case] = {
            "primary_pass": all(check["passes_all_repeats"] for check in checks.values()),
            "critical_checks": checks,
            "secondary_metrics": {metric: sum(trial["metrics"][metric]["score"] for trial in ordered) / repeats for metric in METRICS},
            "answer_words_mean": sum(trial["answer_words"] for trial in ordered) / repeats,
        }
    passed = sum(case["primary_pass"] for case in cases.values())
    return {
        "controls": (model, settings, rubric), "coverage": coverage,
        "summary": {"run_id": run_id,
            "primary": {"passed_cases": passed, "total_cases": len(cases), "pass_rate": passed / len(cases)},
            "cases": cases,
            "secondary_metrics": {metric: math.fsum(case["secondary_metrics"][metric] for case in cases.values()) / len(cases) for metric in METRICS}},
    }


def _paired(engine: dict[str, Any], comparator: dict[str, Any], name: str, role: str) -> dict[str, Any]:
    counts = {"both_pass": 0, "both_fail": 0, "wins": 0, "losses": 0}
    regressions = []
    for case_id, case in engine["cases"].items():
        other = comparator["cases"][case_id]
        current_pass, other_pass = case["primary_pass"], other["primary_pass"]
        key = ("both_pass" if other_pass else "wins") if current_pass else ("losses" if other_pass else "both_fail")
        counts[key] += 1
        for criterion, check in case["critical_checks"].items():
            if other["critical_checks"][criterion]["passes_all_repeats"] and not check["passes_all_repeats"]:
                regressions.append({"case_id": case_id, "criterion": criterion, "engine_failed_repeats": list(check["failed_repeats"])})
    total = len(engine["cases"])
    difference = (counts["wins"] - counts["losses"]) / total
    return {
        "role": role, "comparator": name, "case_count": total, **counts,
        "rate_difference": difference,
        "case_rate_comparison": "higher" if difference > 0 else "lower" if difference < 0 else "equal",
        "improvement": "higher_observed_case_rate" if difference > 0 else "not_improved",
        "new_regression_count": len(regressions), "new_regressions": regressions,
        "secondary_metric_differences": {metric: engine["secondary_metrics"][metric] - comparator["secondary_metrics"][metric] for metric in METRICS},
    }


def compare_engine_reports(no_skill: object, current_corrected: object, engine: object,
                           *, expected_repeats: int = 2, expected_cases: int | None = None) -> dict[str, Any]:
    """Require matched complete reports and compare case-level repeat conjunctions.

    A case passes only if every critical check passes on every expected repeat.
    The current-corrected comparison is primary; no-skill is supporting. Metric
    means first average repeats within each case, then give each case equal weight.
    No significance test or general improvement claim is produced.
    """
    repeats = _count(expected_repeats, "expected_repeats", positive=True)
    if expected_cases is not None:
        _count(expected_cases, "expected_cases", positive=True)
    parsed = {condition: _report(report, condition, repeats, expected_cases)
              for condition, report in zip(CONDITIONS, (no_skill, current_corrected, engine))}
    baseline = parsed["current-corrected"]
    for condition, report in parsed.items():
        if report["controls"] != baseline["controls"]:
            raise ComparisonError(f"{condition}: model, settings, and rubric fingerprints must match the comparator")
        if report["coverage"] != baseline["coverage"]:
            raise ComparisonError(f"{condition}: case/repeat/prompt/split/critical-check coverage differs")
    summaries = {condition: report["summary"] for condition, report in parsed.items()}
    cases = sorted(baseline["summary"]["cases"])
    return {
        "schema_version": SCHEMA_VERSION, "comparison_status": "descriptive_case_comparison",
        "coverage": {"case_count": len(cases), "repeats_per_case": repeats,
                     "trials_per_condition": len(cases) * repeats, "case_ids": cases},
        "conditions": summaries,
        "comparisons": {
            "engine_vs_current_corrected": _paired(summaries["engine"], summaries["current-corrected"], "current-corrected", "primary"),
            "engine_vs_no_skill": _paired(summaries["engine"], summaries["no-skill"], "no-skill", "supporting"),
        },
        "limitations": [
            "Descriptive comparison of the supplied cases only; no statistical significance, general accuracy, calibration, or causal improvement is inferred.",
            "A tied observed case pass rate is not improved; a higher rate does not erase any listed criterion regression.",
            "Cases are comparison units. Repeats are not independent trials for this aggregation.",
            "Scores and supporting quotes are assessor judgments from the supplied reports; this tool does not regrade answers or authenticate the declared trial procedure.",
            "Matching settings and assessor blinding are declarations, not independently verified execution controls.",
            "Secondary metrics average repeats within each case before averaging cases; signed differences do not establish metric direction or practical significance.",
            "Answer word counts are descriptive and are not operator-burden scores.",
        ],
    }


def _read_json(path: Path) -> object:
    def unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ComparisonError(f"Duplicate JSON key: {key!r}")
            result[key] = value
        return result

    def invalid_constant(value: str) -> None:
        raise ComparisonError(f"Nonfinite JSON constant: {value}")

    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_pairs,
                          parse_constant=invalid_constant)
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        raise ComparisonError(f"Cannot read report {path}: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    """Read three reports in named order and emit only JSON on standard output."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("no_skill_report", type=Path)
    parser.add_argument("current_corrected_report", type=Path)
    parser.add_argument("engine_report", type=Path)
    parser.add_argument("--expected-repeats", type=int, default=2)
    parser.add_argument("--expected-cases", type=int)
    args = parser.parse_args(argv)
    try:
        result = compare_engine_reports(_read_json(args.no_skill_report), _read_json(args.current_corrected_report),
                                        _read_json(args.engine_report), expected_repeats=args.expected_repeats,
                                        expected_cases=args.expected_cases)
    except ComparisonError as exc:
        print(json.dumps({"schema_version": SCHEMA_VERSION, "comparison_status": "invalid", "error": str(exc)}, ensure_ascii=True))
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
