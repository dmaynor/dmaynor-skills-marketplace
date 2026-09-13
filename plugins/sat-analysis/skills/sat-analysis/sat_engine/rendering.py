"""Pure projections and inert Markdown views of one canonical analysis trace.

Projection does not assess evidence, infer judgments, calculate values, or update
hashes. The pipeline owns those operations and verifies artifacts before export.
The source templates in assets/templates are copied into package resources by
the build; there is no separately maintained installed template set.
"""

from __future__ import annotations

from copy import deepcopy
from html import escape as html_escape
from importlib import resources
import json
from pathlib import Path
import re
from string import Template
from typing import Any, Mapping


_COMMON_FIELDS = ("schema_version", "analysis_id", "revision", "content_hash")
_MARKDOWN_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+.!|~=\-])")
_NO_JUDGMENT = "No analyst judgment supplied."


def project(trace: Mapping[str, Any]) -> dict[str, Any]:
    """Return independent views derived exclusively from a canonical trace.

    Every mutable value is copied, including values shared by multiple views.
    Missing judgments, estimates and owners remain absent in the data; human
    readable absence labels are added only by the renderer.
    """
    canonical = deepcopy(dict(trace))
    request = canonical["request"]
    judgment = request.get("judgment")
    common = {key: canonical[key] for key in _COMMON_FIELDS}
    card = {
        **common,
        "question": request["question"],
        "summary": judgment["summary"] if judgment is not None else _NO_JUDGMENT,
        "likelihood": deepcopy(judgment.get("likelihood")) if judgment else None,
        "confidence": deepcopy(judgment.get("confidence")) if judgment else None,
        "implications": deepcopy(judgment.get("implications", [])) if judgment else [],
        "assessment_status": (
            "not_evaluated" if request["mode"] == "LIGHT"
            else canonical["ach_matrix"]["assessment"]["status"]
        ),
        "limitations": deepcopy(request.get("limitations", [])),
        "calculations": deepcopy(canonical["calculations"]),
    }
    tasking = None
    if request["mode"] == "FULL":
        tasking = {
            **common,
            "tasks": deepcopy(request.get("tasks", [])),
            "limitations": deepcopy(request.get("limitations", [])),
        }
    return {"decision_card": card, "analytic_trace": canonical, "tasking_view": tasking}


def _text(value: Any, *, absent: str = "Not supplied.") -> str:
    """Escape supplied inline text before inserting trusted Markdown structure."""
    if value is None:
        value = absent
    elif not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False, allow_nan=False)
    # Escaping happens before introducing HTML entities, so the entity's own
    # punctuation is never backslash-escaped. Newlines cannot inject new blocks.
    value = _MARKDOWN_SPECIAL.sub(r"\\\1", value)
    return html_escape(value, quote=False).replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def _literal(text: str) -> str:
    """Preserve forensic whitespace and punctuation as inert preformatted text.

    HTML escaping prevents closing the pre element or introducing active markup.
    Markdown punctuation remains literal, without altering the displayed raw log.
    Original bytes, where present, are retained separately in observation metadata.
    """
    return "<pre>" + html_escape(text, quote=False) + "</pre>"


def _record(value: Any) -> str:
    return _literal(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2))


def _bullets(values: list[Any], empty: str) -> str:
    return "\n".join("- " + _text(value) for value in values) if values else empty


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    return "\n".join([
        "| " + " | ".join(_text(value) for value in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
        *("| " + " | ".join(_text(value) for value in row) + " |" for row in rows),
    ])


def _metadata(view: Mapping[str, Any], trace: Mapping[str, Any]) -> str:
    # IDs are caller supplied, so they need the same escaping as other text.
    return _table(["Field", "Value"], [
        ["Analysis ID", view["analysis_id"]],
        ["Revision", view["revision"]],
        ["Content hash", view["content_hash"]],
        ["Schema version", view["schema_version"]],
        ["Engine version", trace["engine_version"]],
    ])


def _likelihood(value: Mapping[str, Any] | None) -> str:
    if value is None:
        return "Not supplied; likelihood remains unknown."
    rows: list[list[Any]] = [
        ["Proposition", value["proposition"]],
        ["Value", value.get("value") if value.get("value") is not None else "Unknown; not quantified."],
        ["Basis", value["basis"]],
    ]
    for key in ("term", "horizon"):
        if key in value:
            rows.append([key.capitalize(), value[key]])
    return _table(["Likelihood field", "Analyst input"], rows)


def _confidence(value: Mapping[str, Any] | None) -> str:
    if value is None:
        return "Not supplied; confidence remains unassessed."
    return _table(["Confidence field", "Analyst input"], [
        ["Level", value["level"]], ["Reasoning", value["reasoning"]],
    ])


def _judgment(request: Mapping[str, Any]) -> str:
    judgment = request.get("judgment")
    if judgment is None:
        return _NO_JUDGMENT
    return "\n\n".join([
        _text(judgment["summary"]),
        "### Selected hypothesis references",
        _bullets(judgment.get("selected_hypothesis_ids", []), "No selected hypotheses supplied."),
        "### Observation references",
        _bullets(judgment.get("observation_ids", []), "No judgment observation references supplied."),
        "### Likelihood", _likelihood(judgment.get("likelihood")),
        "### Confidence", _confidence(judgment.get("confidence")),
        "### Implications", _bullets(judgment.get("implications", []), "No implications supplied."),
    ])


def _hypotheses(request: Mapping[str, Any]) -> str:
    hypotheses = request.get("hypotheses", [])
    if not hypotheses:
        return "No hypotheses supplied."
    return _table(["ID", "Description", "Category", "Initial probability", "Posterior probability", "Falsifier"], [
        [hypothesis["id"], hypothesis["description"], hypothesis.get("category"),
         hypothesis.get("initial_probability") if hypothesis.get("initial_probability") is not None else "Unknown; not quantified.",
         hypothesis.get("posterior_probability") if hypothesis.get("posterior_probability") is not None else "Not elicited.",
         hypothesis.get("falsifier")]
        for hypothesis in hypotheses
    ])


def _observations(request: Mapping[str, Any]) -> str:
    observations = request.get("observations", [])
    if not observations:
        return "No observations supplied."
    parts = []
    for observation in observations:
        metadata = {key: value for key, value in observation.items() if key != "raw"}
        parts.extend([
            "### Observation " + _text(observation["id"]),
            "Raw source text:", _literal(observation["raw"]),
            "Source, parse status, timestamps and provenance:", _record(metadata),
        ])
    return "\n\n".join(parts)


def _evidence(request: Mapping[str, Any]) -> str:
    evidence = request.get("evidence", [])
    if not evidence:
        return "No evidence ratings supplied."
    hypothesis_ids = [hypothesis["id"] for hypothesis in request.get("hypotheses", [])]
    rows = [
        [item["id"], item["observation_id"],
         *(item["ratings"].get(identifier, "Missing; not evaluated.") for identifier in hypothesis_ids),
         item.get("rationale")]
        for item in evidence
    ]
    return "\n\n".join([
        "Ratings are analyst inputs. N means evaluated and nondiscriminating; a missing rating is not N.",
        _table(["Evidence ID", "Observation ID", *hypothesis_ids, "Rationale"], rows),
        "Source, reliability, origin and dependencies follow each referenced observation.",
    ])


def _coherence(record: Mapping[str, Any] | None) -> str:
    if record is None:
        return "Not assessed; the hypothesis set is not declared exclusive and exhaustive."
    lines = []
    for label in ("prior", "posterior"):
        vector = record.get(label)
        lines.append(f"- {label}: " + ("not fully quantified." if vector is None else
                     f"sum {vector['sum']:.6g}; incoherence metric {vector['incoherence_metric']:.6g}."))
    lines.append("- posterior leaders: " + (", ".join(_text(i) for i in record["posterior_leaders"]) or "none"))
    lines.append("- descriptive heuristic leaders: " + (", ".join(_text(i) for i in record["heuristic_leaders"]) or "none"))
    lines.append("- leaders disagree: " + ("not assessable" if record["leaders_disagree"] is None else str(record["leaders_disagree"]).lower()))
    lines.extend("- " + _text(c) for c in record["caveats"])
    return "\n".join(lines)


def _calculations(calculations: list[Mapping[str, Any]]) -> str:
    if not calculations:
        return "No calculations supplied."
    return _table(["ID", "Operation", "Computed value", "Unit", "Status", "Physical latency established", "Caveats"], [
        [item["id"], item["operation"],
         item["value"] if item["value"] is not None else "Unresolved; no numeric value.",
         item.get("unit"), item["status"], item.get("physical_latency_established", "Not applicable."), item.get("caveats", [])]
        for item in calculations
    ])


def _tasks(tasks: list[Mapping[str, Any]]) -> str:
    if not tasks:
        return "No tasks supplied."
    return _table(["ID", "Action", "Owner", "Trigger", "Observation IDs", "Hypothesis IDs"], [
        [task["id"], task["action"], task.get("owner") or "Unassigned",
         task.get("trigger") or "Not supplied.", task.get("observation_ids", []),
         task.get("hypothesis_ids", [])]
        for task in tasks
    ])


def _diagnostics(trace: Mapping[str, Any]) -> str:
    diagnostics = trace.get("diagnostics", [])
    if not diagnostics:
        return "No engine diagnostics recorded."
    return _table(["Severity", "Code", "Path", "Message", "Remediation"], [
        [item["severity"], item["code"], item["path"], item["message"], item.get("remediation")]
        for item in diagnostics
    ])


def _review_limits(trace: Mapping[str, Any]) -> str:
    request = trace["request"]
    parts = [
        "Engine calculations describe supplied inputs; they do not establish a causal judgment, likelihood, or analytic confidence.",
        "Versions identify contracts and software, not assessment accuracy or certified compliance.",
    ]
    if request["mode"] == "LIGHT":
        parts.append("LIGHT mode: ACH is not evaluated. No tasking view is generated.")
    else:
        assessment = trace["ach_matrix"]["assessment"]
        status = assessment["status"]
        labels = {
            "insufficient_evidence": "Insufficient evidence: the supplied hypotheses or evidence do not support an ACH comparison.",
            "incomplete": "Incomplete assessment: missing ratings remain unevaluated; they are not neutral observations.",
            "underdetermined": "Underdetermined assessment: the descriptive comparison does not distinguish a unique heuristic leader.",
            "differentiated": "Differentiated assessment: descriptive scores differ; this is not a computed causal winner.",
        }
        parts.append(labels.get(status, "Assessment status: " + str(status)))
        parts.extend(assessment.get("caveats", []))
        sensitivity = trace["ach_matrix"].get("sensitivity", {})
        if sensitivity.get("caveat"):
            parts.append(sensitivity["caveat"])
    parts.extend(trace["timeline"].get("analysis", {}).get("caveats", []))
    return _bullets(parts, "No review limits recorded.")


def _template(name: str, values: Mapping[str, str]) -> str:
    try:
        template = resources.files("sat_engine").joinpath("resources", "templates", name).read_text(encoding="utf-8")
    except (ModuleNotFoundError, FileNotFoundError):
        template = (Path(__file__).resolve().parent.parent / "assets" / "templates" / name).read_text(encoding="utf-8")
    return Template(template).substitute(values).rstrip() + "\n"


def render_markdown(artifacts: Mapping[str, Any]) -> dict[str, str]:
    """Render the supplied projections without mutating them or doing arithmetic.

    This is presentation, not artifact verification. Call verify_artifacts at a
    trust boundary before rendering externally supplied or stored artifacts.
    """
    trace = artifacts["analytic_trace"]
    card = artifacts["decision_card"]
    request = trace["request"]
    common = {
        "diagnostics": _diagnostics(trace),
        "review_limits": _review_limits(trace),
    }
    rendered = {
        "decision_card.md": _template("decision_card.md", {
            **common, "metadata": _metadata(card, trace),
            "question": _text(card["question"]), "summary": _text(card["summary"]),
            "likelihood": _likelihood(card["likelihood"]),
            "confidence": _confidence(card["confidence"]),
            "implications": _bullets(card["implications"], "No implications supplied."),
            "assessment_status": _text(card["assessment_status"]),
            "limitations": _bullets(card["limitations"], "No analyst limitations supplied; this does not establish completeness."),
            "calculations": _calculations(card["calculations"]),
        }),
    }
    trace_values = {
        **common, "metadata": _metadata(trace, trace),
        "question": _text(request["question"]), "mode": _text(request["mode"]),
        "submode": _text(request["submode"]), "judgment": _judgment(request),
        "relationship": _text(request.get("relationship", "unspecified")),
        "hypotheses": _hypotheses(request), "observations": _observations(request),
        "evidence": _evidence(request),
        "assumptions": _bullets(request.get("assumptions", []), "No assumptions supplied."),
        "limitations": _bullets(request.get("limitations", []), "No analyst limitations supplied; this does not establish completeness."),
        "ach_matrix": _record(trace["ach_matrix"]),
        "timeline": _record(trace["timeline"]),
        "calculations": _calculations(trace["calculations"]),
        "coherence": _coherence(trace.get("coherence")),
        "tasks": _tasks(request.get("tasks", [])),
        "request": _record(request),
    }
    trace_template = "analytic_trace_light.md" if request["mode"] == "LIGHT" else "analytic_trace.md"
    rendered["analytic_trace.md"] = _template(trace_template, trace_values)
    tasking = artifacts.get("tasking_view")
    if request["mode"] == "FULL":
        if tasking is None:
            raise ValueError("FULL artifacts require a tasking_view.")
        rendered["tasking_view.md"] = _template("tasking_view.md", {
            **common, "metadata": _metadata(tasking, trace),
            "tasks": _tasks(tasking["tasks"]),
            "limitations": _bullets(tasking["limitations"], "No analyst limitations supplied; this does not establish completeness."),
        })
    return rendered
