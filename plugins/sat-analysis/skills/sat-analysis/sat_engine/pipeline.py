"""Validate explicit analyst inputs, compute facts, and produce coherent views."""

from __future__ import annotations

from copy import deepcopy
import math
from typing import Any

from . import __version__
from .ach import compute_matrix
from .doctrine import resolve_rules
from .rendering import project
from .timeline import build_timeline, resolve_timestamp
from .uncertainty import check_likelihood_term, check_sentence_separation
from .validators import ValidationFailure, canonical_bytes, content_hash, validate


def _warning(code: str, message: str, path: str = "$") -> dict[str, str]:
    """Construct a nonblocking diagnostic without inventing a confidence value."""
    return {"code": code, "message": message, "path": path,
            "severity": "warning", "remediation": ""}


def _normalize(request: dict[str, Any]) -> dict[str, Any]:
    """Copy inputs and fill mechanical defaults without synthesizing judgments."""
    normalized = deepcopy(request)
    for name in ("observations", "hypotheses", "evidence", "assumptions", "limitations",
                 "tasks", "rule_ids", "calculations"):
        normalized.setdefault(name, [])
    normalized.setdefault("judgment", None)
    normalized.setdefault("relationship", "unspecified")
    normalized.setdefault("revision", 1)
    options = normalized.setdefault("timeline_options", {})
    options.setdefault("gap_threshold_seconds", 300)
    options.setdefault("rapid_threshold_seconds", 1)
    if "analysis_id" not in normalized:
        normalized["analysis_id"] = "sat-" + content_hash(normalized)[:24]
    return normalized


def _unique(records: list[dict[str, Any]], kind: str) -> set[str]:
    """Reject duplicate identifiers within a typed record collection."""
    identifiers: set[str] = set()
    for index, record in enumerate(records):
        if record["id"] in identifiers:
            raise ValidationFailure("duplicate_id", f"Duplicate {kind} ID: {record['id']}",
                                    f"$.{kind}[{index}].id", "Assign a unique ID to each distinct record.")
        identifiers.add(record["id"])
    return identifiers


def _references(values: list[str], known: set[str], path: str) -> None:
    """Validate declared references without extracting implied ones from prose."""
    for index, value in enumerate(values):
        if value not in known:
            raise ValidationFailure("unknown_reference", f"Unknown reference: {value}",
                                    f"{path}[{index}]", "Supply the referenced record or correct its ID.")


def _check_links(request: dict[str, Any]) -> None:
    """Enforce relations that cannot be established by JSON shape alone."""
    observations = _unique(request["observations"], "observations")
    hypotheses = _unique(request["hypotheses"], "hypotheses")
    _unique(request["evidence"], "evidence")
    _unique(request["tasks"], "tasks")
    _unique(request["calculations"], "calculations")
    if request["mode"] == "LIGHT" and request["evidence"]:
        raise ValidationFailure("light_has_ratings", "LIGHT does not evaluate ACH evidence ratings.",
                                "$.evidence", "Use FULL for an evidence-hypothesis matrix.")
    judgment = request["judgment"]
    if judgment is not None:
        _references(judgment.get("observation_ids", []), observations, "$.judgment.observation_ids")
        _references(judgment.get("selected_hypothesis_ids", []), hypotheses,
                    "$.judgment.selected_hypothesis_ids")
        check_likelihood_term(judgment.get("likelihood"))
        check_sentence_separation(judgment)
    for index, task in enumerate(request["tasks"]):
        _references(task.get("observation_ids", []), observations, f"$.tasks[{index}].observation_ids")
        _references(task.get("hypothesis_ids", []), hypotheses, f"$.tasks[{index}].hypothesis_ids")
    for index, calculation in enumerate(request["calculations"]):
        if calculation["operation"] == "reported_interval":
            for key in ("start_observation_id", "end_observation_id"):
                _references([calculation[key]], observations, f"$.calculations[{index}].{key}")
    resolve_rules(request["rule_ids"])


def _calculate(request: dict[str, Any]) -> list[dict[str, Any]]:
    """Calculate requested values; reported clock arithmetic is not latency proof."""
    observations = {record["id"]: record for record in request["observations"]}
    outputs: list[dict[str, Any]] = []
    options = request["timeline_options"]
    for index, calculation in enumerate(request["calculations"]):
        operation = calculation["operation"]
        result: dict[str, Any] = {"id": calculation["id"], "operation": operation,
                                  "value": None, "unit": calculation.get("unit", ""),
                                  "status": "resolved", "caveats": []}
        if operation == "reported_interval":
            start = observations[calculation["start_observation_id"]]
            end = observations[calculation["end_observation_id"]]
            timestamps = []
            errors = []
            for observation in (start, end):
                context = observation.get("timestamp_context", {})
                timestamp, error = resolve_timestamp(
                    observation.get("timestamp"),
                    default_year=context.get("year", options.get("default_year")),
                    default_timezone=context.get("timezone", options.get("default_timezone")),
                    fold=context.get("fold", options.get("fold")),
                )
                timestamps.append(timestamp)
                if error:
                    errors.append(f"{observation['id']}: {error}")
            result["unit"] = "seconds"
            result["physical_latency_established"] = False
            result["caveats"] = [
                "Difference between reported clock values; physical latency is not established.",
                "Clock alignment, event meaning, and observation coverage require independent validation.",
            ]
            if any(timestamp is None for timestamp in timestamps):
                result["status"] = "unresolved"
                result["caveats"].extend(errors)
            else:
                result["value"] = (timestamps[1] - timestamps[0]).total_seconds()
                if result["value"] < 0:
                    result["caveats"].append("End precedes start in reported time; inspect order and clocks.")
        else:
            operands = calculation["operands"]
            try:
                match operation:
                    case "sum":
                        value = sum(operands) if all(type(v) is int for v in operands) else math.fsum(operands)
                    case "difference":
                        value = operands[0] - operands[1]
                    case "product":
                        value = math.prod(operands)
                    case "ratio":
                        value = operands[0] / operands[1]
                    case _:
                        raise ValueError(f"Unknown operation: {operation}")
                if not math.isfinite(value):
                    raise ValueError("Calculation result is not finite.")
                canonical_bytes(value)
                result["value"] = value
            except (ArithmeticError, ValueError) as exc:
                raise ValidationFailure("invalid_calculation", str(exc),
                                        f"$.calculations[{index}]",
                                        "Correct operands; results must be finite and portable.") from exc
        outputs.append(result)
    return outputs


def assess(request: object) -> dict[str, Any]:
    """Return a validated result envelope, preserving incomplete analytical states.

    A status of ok means the supplied request was processed consistently. It does
    not establish that analyst-authored claims or source assertions are true.
    """
    try:
        validate("analysis_request", request)
        normalized = _normalize(request)
        _check_links(normalized)
        # Also validates hypothesis relationships in LIGHT; no ACH is emitted there.
        matrix = compute_matrix(normalized)
        timeline = build_timeline(normalized["observations"], **normalized["timeline_options"])
        calculations = _calculate(normalized)
        diagnostics: list[dict[str, str]] = []
        if normalized["judgment"] is None:
            diagnostics.append(_warning("judgment_missing", "No analyst judgment was supplied.", "$.judgment"))
        else:
            diagnostics.append(_warning("judgment_not_verified",
                "Judgment is analyst-authored; engine validation does not establish its factual truth.", "$.judgment"))
        rejected = sum(o["parse_status"] == "rejected" for o in normalized["observations"])
        unparsed = sum(o["parse_status"] == "unparsed" for o in normalized["observations"])
        if rejected or unparsed:
            diagnostics.append(_warning("extraction_incomplete",
                f"Preserved {rejected} rejected and {unparsed} unparsed observations.", "$.observations"))
        if normalized["mode"] == "FULL" and matrix["assessment"]["status"] != "differentiated":
            diagnostics.append(_warning("matrix_" + matrix["assessment"]["status"],
                "ACH assessment: " + matrix["assessment"]["status"] + ". This is distinct from the analyst's judgment.",
                "$.evidence"))
        for calculation in calculations:
            if calculation["status"] == "unresolved":
                diagnostics.append(_warning("calculation_unresolved",
                    f"Calculation {calculation['id']} has unresolved inputs.", "$.calculations"))
        trace: dict[str, Any] = {"schema_version": "1", "engine_version": __version__,
            "analysis_id": normalized["analysis_id"], "revision": normalized["revision"],
            "request": normalized, "ach_matrix": matrix if normalized["mode"] == "FULL" else None,
            "timeline": timeline, "calculations": calculations, "diagnostics": diagnostics}
        trace["content_hash"] = content_hash(trace)
        validate("analytic_trace", trace)
        artifacts = project(trace)
        validate("decision_card", artifacts["decision_card"])
        if artifacts["tasking_view"] is not None:
            validate("tasking_view", artifacts["tasking_view"])
        result = {"schema_version": "1", "engine_version": __version__,
                  "status": "ok", "diagnostics": diagnostics, "artifacts": artifacts}
        validate("engine_result", result)
        return result
    except ValidationFailure as exc:
        return {"schema_version": "1", "engine_version": __version__, "status": "invalid",
                "diagnostics": [exc.diagnostic()], "artifacts": None}
    except (ValueError, TypeError, KeyError, OverflowError) as exc:
        error = ValidationFailure("invalid_analysis", str(exc), "$",
                                  "Inspect the supplied records, references, and calculation inputs.")
        return {"schema_version": "1", "engine_version": __version__, "status": "invalid",
                "diagnostics": [error.diagnostic()], "artifacts": None}


def verify_artifacts(artifacts: object) -> None:
    """Reject stale or forged views by recomputing inputs and every derived field."""
    if not isinstance(artifacts, dict) or set(artifacts) != {"decision_card", "analytic_trace", "tasking_view"}:
        raise ValidationFailure("invalid_artifacts", "Expected the three named artifact fields.")
    trace = artifacts["analytic_trace"]
    validate("analytic_trace", trace)
    if trace["engine_version"] != __version__:
        raise ValidationFailure("engine_version_mismatch", "This engine cannot verify a different engine version.")
    expected = assess(trace["request"])
    if expected["status"] != "ok":
        raise ValidationFailure("invalid_trace_request", "Trace request no longer validates.")
    if canonical_bytes(artifacts) != canonical_bytes(expected["artifacts"]):
        raise ValidationFailure("artifact_mismatch",
            "Artifacts differ from recomputed evidence, calculations, judgments, or projections.",
            "$", "Reassess the canonical request and regenerate the complete artifact set.")
