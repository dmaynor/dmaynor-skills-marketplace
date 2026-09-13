#!/usr/bin/env python3
"""Prepare SAT trials and aggregate explicit assessor judgments without grading prose.

Python 3.12+, standard library only. No model, network, or credential integration.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any
import uuid


ROOT = Path(__file__).resolve().parent
SCHEMA_VERSION = "1.0.0"
METRICS = ("useful_conclusion", "useful_decision", "operator_burden")
RATING_STATES = {"pass", "fail", "unscored"}


class EvaluationError(ValueError):
    """Invalid evaluation data or an unsupported comparison."""


def digest(content: bytes) -> str:
    """Return a content fingerprint, not a claim of evidentiary validity."""
    return hashlib.sha256(content).hexdigest()


def canonical_digest(value: object) -> str:
    """Fingerprint a JSON value independently of whitespace and key order."""
    return digest(json.dumps(value, sort_keys=True, ensure_ascii=False).encode())


def read_json(path: Path) -> Any:
    """Load JSON with useful CLI errors."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise EvaluationError(f"Cannot read JSON {path}: {exc}") from exc


def write_json(path: Path, value: object) -> None:
    """Write an inspectable UTF-8 JSON artifact."""
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def require_object(value: object, label: str) -> dict[str, Any]:
    """Require an object before accessing schema fields."""
    if not isinstance(value, dict):
        raise EvaluationError(f"{label} must be an object")
    return value


def nonempty(value: object, label: str) -> str:
    """Require actual text rather than coercing data into a string."""
    if not isinstance(value, str) or not value.strip():
        raise EvaluationError(f"{label} must be nonempty text")
    return value


def load_suite(case_path: Path = ROOT / "cases.json", rubric_path: Path = ROOT / "rubric.json") -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate the fixture/rubric relationship while keeping their content separate."""
    suite = require_object(read_json(case_path), "case suite")
    rubric = require_object(read_json(rubric_path), "rubric")
    if suite.get("schema_version") != SCHEMA_VERSION or rubric.get("schema_version") != SCHEMA_VERSION:
        raise EvaluationError("Unsupported suite/rubric schema version")
    cases = suite.get("cases")
    if not isinstance(cases, list) or not cases:
        raise EvaluationError("cases must be a nonempty list")
    seen: set[str] = set()
    criteria = require_object(rubric.get("cases"), "rubric cases")
    for case in cases:
        case = require_object(case, "case")
        case_id = nonempty(case.get("id"), "case id")
        if not all(character.isalnum() or character == "-" for character in case_id):
            raise EvaluationError(f"Unsafe case id: {case_id}")
        if case_id in seen:
            raise EvaluationError(f"Duplicate case id: {case_id}")
        seen.add(case_id)
        if case.get("split") not in {"regression", "held_out"}:
            raise EvaluationError(f"Unknown split: {case_id}")
        nonempty(case.get("prompt"), f"prompt for {case_id}")
        checks = require_object(criteria.get(case_id), f"rubric for {case_id}").get("critical_checks")
        if not isinstance(checks, dict) or not checks:
            raise EvaluationError(f"Missing critical checks for {case_id}")
        for check_id, description in checks.items():
            nonempty(check_id, "check id")
            nonempty(description, "check description")
    if set(criteria) != seen:
        raise EvaluationError("Cases and rubric must contain exactly the same case IDs")
    if set(require_object(rubric.get("metrics"), "metrics")) != set(METRICS):
        raise EvaluationError("Rubric must define all three decision/usefulness/burden metrics")
    return suite, rubric


def skill_fingerprint(path: Path | None) -> str | None:
    """Record the selected skill instructions/references, without copying them into prompts."""
    if path is None:
        return None
    if not (path / "SKILL.md").is_file():
        raise EvaluationError("--skill-root must contain SKILL.md")
    files = [path / "SKILL.md", *sorted((path / "references").glob("*.md"))]
    return canonical_digest({str(file.relative_to(path)): digest(file.read_bytes()) for file in files})


def prepare_run(output: Path, *, condition: str, model: str, settings: dict[str, Any], split: str = "regression", selected: list[str] | None = None, repeats: int = 1, skill_root: Path | None = None, case_path: Path = ROOT / "cases.json", rubric_path: Path = ROOT / "rubric.json") -> dict[str, Any]:
    """Freeze inputs and prepare solver-only prompts plus an assessor-only rubric."""
    suite, rubric = load_suite(case_path, rubric_path)
    nonempty(condition, "condition")
    nonempty(model, "model")
    require_object(settings, "model settings")
    if type(repeats) is not int or repeats < 1:
        raise EvaluationError("repeats must be a positive integer")
    if split not in {"regression", "held_out", "all"}:
        raise EvaluationError("Unknown split")
    available = {case["id"] for case in suite["cases"]}
    if selected and (set(selected) - available or len(selected) != len(set(selected))):
        raise EvaluationError("Requested case IDs must exist and must not be repeated")
    cases = [case for case in suite["cases"] if (split == "all" or case["split"] == split) and (not selected or case["id"] in selected)]
    if not cases or (selected and set(selected) != {case["id"] for case in cases}):
        raise EvaluationError("No matching cases, or a selected case is outside the selected split")
    fingerprint = skill_fingerprint(skill_root)
    if output.exists():
        raise EvaluationError(f"Refusing to overwrite existing run: {output}")
    output.mkdir(parents=True)
    for directory in ("prompts", "answers", "assessor"):
        (output / directory).mkdir()
    write_json(output / "assessor" / "rubric.json", rubric)
    trials = []
    for case in cases:
        for repeat in range(1, repeats + 1):
            trial_id = f"{case['id']}-r{repeat:02}"
            prompt_path = f"prompts/{trial_id}.txt"
            prompt = case["prompt"].rstrip() + "\n"
            (output / prompt_path).write_text(prompt, encoding="utf-8")
            trials.append({"id": trial_id, "case_id": case["id"], "repeat": repeat, "split": case["split"], "prompt_path": prompt_path, "prompt_sha256": digest(prompt.encode()), "answer_path": f"answers/{trial_id}.txt"})
    manifest = {"schema_version": SCHEMA_VERSION, "run_id": str(uuid.uuid4()), "created_at": datetime.now(timezone.utc).isoformat(), "condition": condition, "model": model, "settings": settings, "skill_sha256": fingerprint, "suite_version": suite["suite_version"], "rubric_version": rubric["rubric_version"], "rubric_sha256": canonical_digest(rubric), "trials": trials}
    write_json(output / "manifest.json", manifest)
    write_json(output / "assessor" / "scores-template.json", make_score_template(output))
    return manifest


def safe_child(root: Path, relative: object) -> Path:
    """Prevent manifest paths from escaping the evaluation directory."""
    text = nonempty(relative, "artifact path")
    result = (root / text).resolve()
    if not result.is_relative_to(root.resolve()):
        raise EvaluationError("Artifact path escapes run directory")
    return result


def load_run(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load frozen inputs and reject mutated prompts or rubric."""
    manifest = require_object(read_json(root / "manifest.json"), "manifest")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise EvaluationError("Unsupported manifest schema version")
    for key in ("run_id", "condition", "model", "rubric_sha256"):
        nonempty(manifest.get(key), key)
    require_object(manifest.get("settings"), "model settings")
    rubric = require_object(read_json(root / "assessor" / "rubric.json"), "frozen rubric")
    if canonical_digest(rubric) != manifest["rubric_sha256"]:
        raise EvaluationError("Frozen rubric fingerprint mismatch")
    trials = manifest.get("trials")
    if not isinstance(trials, list) or not trials:
        raise EvaluationError("Manifest must contain trials")
    seen: set[str] = set()
    for trial in trials:
        trial = require_object(trial, "trial")
        trial_id = nonempty(trial.get("id"), "trial id")
        if trial_id in seen:
            raise EvaluationError(f"Duplicate trial ID: {trial_id}")
        seen.add(trial_id)
        if trial.get("case_id") not in rubric["cases"]:
            raise EvaluationError(f"Unknown case: {trial_id}")
        prompt = safe_child(root, trial.get("prompt_path")).read_bytes()
        safe_child(root, trial.get("answer_path"))
        if digest(prompt) != trial.get("prompt_sha256"):
            raise EvaluationError(f"Prompt fingerprint mismatch: {trial_id}")
    return manifest, rubric


def empty_judgment() -> dict[str, Any]:
    """Return an unscored critical check, never an implicit pass."""
    return {"status": "unscored", "reason": "", "quotes": []}


def make_score_template(root: Path) -> dict[str, Any]:
    """Prepare explicit scoring fields; refresh after saving solver answers."""
    manifest, rubric = load_run(root)
    trials = []
    for trial in manifest["trials"]:
        answer = safe_child(root, trial["answer_path"])
        trials.append({"trial_id": trial["id"], "answer_sha256": digest(answer.read_bytes()) if answer.is_file() else None, "critical_checks": {key: empty_judgment() for key in rubric["cases"][trial["case_id"]]["critical_checks"]}, "metrics": {key: {"score": None, "reason": "", "quotes": []} for key in METRICS}})
    return {"schema_version": SCHEMA_VERSION, "run_id": manifest["run_id"], "rubric_sha256": manifest["rubric_sha256"], "assessor": {"id": "", "blinded": None}, "trials": trials}


def validate_support(judgment: dict[str, Any], answer: str, label: str) -> None:
    """Require a stated rationale and literal answer evidence for each actual score."""
    nonempty(judgment.get("reason"), f"reason for {label}")
    quotes = judgment.get("quotes")
    if not isinstance(quotes, list) or not quotes:
        raise EvaluationError(f"{label} requires supporting answer quotes")
    for quote in quotes:
        nonempty(quote, f"quote for {label}")
        if quote not in answer:
            raise EvaluationError(f"Quote does not occur in saved answer: {label}")


def evaluate_run(root: Path, scores_path: Path | None = None) -> dict[str, Any]:
    """Validate supplied judgments and summarize observations without inventing ratings."""
    manifest, rubric = load_run(root)
    scores = make_score_template(root) if scores_path is None else require_object(read_json(scores_path), "scores")
    if scores.get("schema_version") != SCHEMA_VERSION or scores.get("run_id") != manifest["run_id"] or scores.get("rubric_sha256") != manifest["rubric_sha256"]:
        raise EvaluationError("Scores must match the prepared run and frozen rubric")
    assessor = require_object(scores.get("assessor"), "assessor")
    score_trials = scores.get("trials")
    if not isinstance(score_trials, list):
        raise EvaluationError("Score trials must be a list")
    known = {trial["id"] for trial in manifest["trials"]}
    provided: dict[str, dict[str, Any]] = {}
    for trial in score_trials:
        trial = require_object(trial, "trial scores")
        trial_id = nonempty(trial.get("trial_id"), "trial_id")
        if trial_id not in known or trial_id in provided:
            raise EvaluationError(f"Unknown or duplicate scored trial: {trial_id}")
        provided[trial_id] = trial
    result_trials = []
    totals: Counter[str] = Counter()
    metric_values: dict[str, list[int]] = {metric: [] for metric in METRICS}
    any_scored = False
    for trial in manifest["trials"]:
        scoring = provided.get(trial["id"], {})
        answer_path = safe_child(root, trial["answer_path"])
        answer = answer_path.read_text(encoding="utf-8") if answer_path.is_file() else ""
        answer_hash = digest(answer_path.read_bytes()) if answer_path.is_file() else None
        expected_checks = rubric["cases"][trial["case_id"]]["critical_checks"]
        checks = require_object(scoring.get("critical_checks", {}), "critical_checks")
        metrics = require_object(scoring.get("metrics", {}), "metrics")
        if set(checks) - set(expected_checks) or set(metrics) - set(METRICS):
            raise EvaluationError(f"Unknown check or metric for {trial['id']}")
        normalized_checks: dict[str, dict[str, Any]] = {}
        normalized_metrics: dict[str, dict[str, Any]] = {}
        trial_scored = False
        for check_id in expected_checks:
            judgment = require_object(checks.get(check_id, empty_judgment()), check_id)
            status = judgment.get("status")
            if not isinstance(status, str) or status not in RATING_STATES:
                raise EvaluationError(f"Invalid status for {check_id}")
            if status != "unscored":
                validate_support(judgment, answer, check_id)
                trial_scored = True
            normalized_checks[check_id] = judgment
            totals[f"critical_{status}"] += 1
        for metric in METRICS:
            judgment = require_object(metrics.get(metric, {"score": None, "reason": "", "quotes": []}), metric)
            score = judgment.get("score")
            if score is not None:
                if type(score) is not int or score not in {0, 1, 2}:
                    raise EvaluationError(f"{metric} score must be null, 0, 1, or 2")
                validate_support(judgment, answer, metric)
                metric_values[metric].append(score)
                trial_scored = True
            normalized_metrics[metric] = judgment
        if trial_scored:
            if not answer.strip() or scoring.get("answer_sha256") != answer_hash:
                raise EvaluationError(f"Missing or changed answer for scored trial {trial['id']}")
            nonempty(assessor.get("id"), "assessor id")
            if type(assessor.get("blinded")) is not bool:
                raise EvaluationError("Scored results require an explicit blinded true/false declaration")
            any_scored = True
        complete = all(value["status"] != "unscored" for value in normalized_checks.values()) and all(value["score"] is not None for value in normalized_metrics.values())
        totals["answers_present"] += int(bool(answer.strip()))
        totals["trials_complete"] += int(complete)
        result_trials.append({"trial_id": trial["id"], "case_id": trial["case_id"], "repeat": trial["repeat"], "split": trial["split"], "prompt_sha256": trial["prompt_sha256"], "answer_sha256": answer_hash, "answer_words": len(answer.split()) if answer.strip() else None, "complete": complete, "critical_checks": normalized_checks, "metrics": normalized_metrics})
    total = len(manifest["trials"])
    if totals["critical_fail"]:
        status = "failed_observed_checks"
    elif not any_scored:
        status = "not_evaluated"
    elif totals["trials_complete"] != total:
        status = "incomplete"
    else:
        status = "passed_observed_checks"
    return {"schema_version": SCHEMA_VERSION, "run_id": manifest["run_id"], "condition": manifest["condition"], "model": manifest["model"], "settings": manifest["settings"], "skill_sha256": manifest["skill_sha256"], "rubric_sha256": manifest["rubric_sha256"], "assessor": assessor, "status": status, "coverage": {"trials_expected": total, "answers_present": totals["answers_present"], "trials_complete": totals["trials_complete"]}, "critical_checks": {key: totals[f"critical_{key}"] for key in ("pass", "fail", "unscored")}, "metrics": {key: {"mean": sum(values) / len(values) if values else None, "scored": len(values), "expected": total} for key, values in metric_values.items()}, "trials": result_trials, "limitations": ["Judgments are supplied by the named assessor; literal quote checks do not establish that a judgment is correct.", "Missing scores are unscored and excluded from means, never treated as passes or zeros.", "A small fixture suite does not establish general accuracy, calibration, causal attribution, or release readiness.", "Answer word counts are descriptive and are not operator-burden scores."]}


def compare_reports(reports: list[dict[str, Any]]) -> dict[str, Any]:
    """Show comparable condition summaries; block naive comparison when controls differ."""
    if len(reports) < 2:
        raise EvaluationError("Compare requires at least two reports")
    conditions = [report.get("condition") for report in reports]
    if len(set(conditions)) != len(conditions):
        raise EvaluationError("Comparison conditions must be unique")
    reasons = []
    for field in ("model", "settings", "rubric_sha256"):
        if len({canonical_digest(report.get(field)) for report in reports}) != 1:
            reasons.append(f"Different {field}")
    coverage = [{(trial["case_id"], trial["repeat"], trial["prompt_sha256"]) for trial in report["trials"]} for report in reports]
    if any(value != coverage[0] for value in coverage[1:]):
        reasons.append("Different case/repeat/prompt coverage")
    if any(report["coverage"]["trials_complete"] != report["coverage"]["trials_expected"] for report in reports):
        reasons.append("Incomplete scoring")
    if any(report["assessor"].get("blinded") is not True for report in reports):
        reasons.append("Assessor blinding not established for every condition")
    return {"schema_version": SCHEMA_VERSION, "comparison_status": "descriptive_comparison" if not reasons else "comparison_limited", "limitations": reasons + ["No statistical significance or general improvement is inferred by this harness.", "Blinding and matched settings are declarations; verify the actual trial procedure."], "conditions": [{key: report[key] for key in ("condition", "status", "coverage", "critical_checks", "metrics")} for report in reports]}


def main(argv: list[str] | None = None) -> int:
    """Run the evaluation preparation/reporting CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare", help="Freeze cases and create raw prompts plus unscored templates")
    prepare.add_argument("--output", type=Path, required=True)
    prepare.add_argument("--condition", required=True)
    prepare.add_argument("--model", required=True)
    prepare.add_argument("--settings", type=Path, required=True, help="JSON object recording actual model/reasoning/tool settings")
    prepare.add_argument("--split", choices=("regression", "held_out", "all"), default="regression")
    prepare.add_argument("--case", action="append", dest="selected")
    prepare.add_argument("--repeats", type=int, default=1)
    prepare.add_argument("--skill-root", type=Path)
    template = subparsers.add_parser("score-template", help="Refresh blank score template with hashes of saved answers")
    template.add_argument("--run", type=Path, required=True)
    template.add_argument("--output", type=Path, required=True)
    report = subparsers.add_parser("report", help="Aggregate assessor scores; omitted --scores leaves all checks unscored")
    report.add_argument("--run", type=Path, required=True)
    report.add_argument("--scores", type=Path)
    report.add_argument("--output", type=Path, required=True)
    compare = subparsers.add_parser("compare", help="Compare reports with explicit controls/coverage caveats")
    compare.add_argument("reports", nargs="+", type=Path)
    compare.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        match args.command:
            case "prepare":
                result = prepare_run(args.output, condition=args.condition, model=args.model, settings=read_json(args.settings), split=args.split, selected=args.selected, repeats=args.repeats, skill_root=args.skill_root)
                print(f"Prepared {len(result['trials'])} unscored trials in {args.output}")
            case "score-template":
                write_json(args.output, make_score_template(args.run))
                print(f"Wrote unscored template to {args.output}")
            case "report":
                result = evaluate_run(args.run, args.scores)
                write_json(args.output, result)
                print(f"{result['status']}: {result['coverage']['trials_complete']}/{result['coverage']['trials_expected']} fully scored trials")
            case "compare":
                result = compare_reports([require_object(read_json(path), "report") for path in args.reports])
                write_json(args.output, result)
                print(result["comparison_status"])
    except (EvaluationError, OSError) as exc:
        print(f"Evaluation error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
