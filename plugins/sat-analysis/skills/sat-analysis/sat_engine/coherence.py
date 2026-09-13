"""Probability coherence: coherentize raw elicitations, measure incoherence, aggregate runs.

Rule MANDEL-COHERENTIZE. Mandel, Karvetski and Dhami (2018) found that coherentizing
then aggregating independent judgments cut mean absolute error by 61 percent, while
ACH alone did not improve accuracy or coherence. Normalization slightly beat the
Coherent Approximation Principle; equal-weight aggregation matched coherence weighting.

The engine boundary keeps exclusive_exhaustive probabilities strictly coherent. These
functions are the analyst-side pre-step: elicit raw numbers, coherentize them, record
the incoherence metric, then author the request with the coherent values.
"""

from __future__ import annotations

from collections.abc import Sequence
import math
from typing import Any

INCOHERENCE_WARN_THRESHOLD: float = 0.15
INCOHERENCE_REFUSE_THRESHOLD: float = 0.50


class IncoherentElicitation(ValueError):
    """Raised for degenerate vectors or above INCOHERENCE_REFUSE_THRESHOLD."""


def _check_vector(raw: Sequence[float], name: str = "vector") -> list[float]:
    values = list(raw)
    if not values:
        raise IncoherentElicitation(f"{name} is empty")
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise IncoherentElicitation(f"{name} must contain finite non-negative numbers")
    return [float(v) for v in values]


def coherentize(raw: Sequence[float]) -> list[float]:
    """Project onto the simplex by normalization."""
    values = _check_vector(raw)
    total = math.fsum(values)
    if total <= 0.0:
        raise IncoherentElicitation("all-zero probability vector")
    return [v / total for v in values]


def incoherence_metric(raw: Sequence[float], coherent: Sequence[float]) -> float:
    """Euclidean distance between the elicited and the coherentized vector."""
    return math.sqrt(math.fsum((a - b) ** 2 for a, b in zip(raw, coherent, strict=True)))


def check_and_project(raw: Sequence[float]) -> dict[str, Any]:
    """Return raw, coherent, raw_sum, incoherence_metric and a warning; refuse above the threshold."""
    values = _check_vector(raw)
    coherent = coherentize(values)
    metric = incoherence_metric(values, coherent)
    if metric > INCOHERENCE_REFUSE_THRESHOLD:
        raise IncoherentElicitation(f"incoherence metric {metric:.3f} exceeds {INCOHERENCE_REFUSE_THRESHOLD}; re-elicit")
    warning = (f"Incoherence metric {metric:.3f} exceeds {INCOHERENCE_WARN_THRESHOLD}; raw sum {math.fsum(values):.3f}."
               if metric > INCOHERENCE_WARN_THRESHOLD else None)
    return {"raw": values, "coherent": coherent, "raw_sum": math.fsum(values),
            "incoherence_metric": metric, "warning": warning}


def aggregate(vectors: Sequence[Sequence[float]]) -> list[float]:
    """Equal-weight linear opinion pool over coherentized vectors; the mean of simplex points is on the simplex."""
    if not vectors:
        raise IncoherentElicitation("no vectors to aggregate")
    coherent = [coherentize(v) for v in vectors]
    dimension = len(coherent[0])
    if any(len(v) != dimension for v in coherent):
        raise IncoherentElicitation("vectors differ in length")
    return [math.fsum(v[i] for v in coherent) / len(coherent) for i in range(dimension)]


def _leaders(values: Sequence[float | None], ids: Sequence[str]) -> list[str]:
    quantified = [(v, i) for v, i in zip(values, ids, strict=True) if v is not None]
    if not quantified:
        return []
    top = max(v for v, _ in quantified)
    return sorted(i for v, i in quantified if v == top)


def trace_record(request: dict[str, Any], matrix: dict[str, Any] | None) -> dict[str, Any] | None:
    """Engine-computed coherence facts for the analytic trace.

    Present only for an exclusive_exhaustive set. Sums are reported for prior and
    posterior; the boundary has already rejected an incoherent fully-quantified
    vector, so a nonzero metric here means the set is partially quantified.
    Leader disagreement compares the analyst's posterior leaders with the matrix's
    descriptive heuristic leaders; it is a fact to report, not an error.
    """
    if request.get("relationship") != "exclusive_exhaustive" or not request.get("hypotheses"):
        return None
    ids = [h["id"] for h in request["hypotheses"]]
    record: dict[str, Any] = {"relationship": "exclusive_exhaustive", "prior": None, "posterior": None,
                              "posterior_leaders": [], "heuristic_leaders": [], "leaders_disagree": None,
                              "caveats": ["Coherence facts describe supplied probabilities; they do not establish accuracy."]}
    for label in ("initial_probability", "posterior_probability"):
        values = [h.get(label) for h in request["hypotheses"]]
        quantified = [v for v in values if v is not None]
        if quantified and len(quantified) == len(values):
            coherent = coherentize(quantified)
            record["prior" if label == "initial_probability" else "posterior"] = {
                "sum": math.fsum(quantified), "incoherence_metric": incoherence_metric(quantified, coherent)}
        elif quantified:
            record["caveats"].append(f"{label} is partially quantified; coherence is not assessable.")
    posterior = [h.get("posterior_probability") for h in request["hypotheses"]]
    record["posterior_leaders"] = _leaders(posterior, ids)
    if matrix is not None:
        record["heuristic_leaders"] = list(matrix.get("assessment", {}).get("heuristic_leaders", []))
    if record["posterior_leaders"] and record["heuristic_leaders"]:
        record["leaders_disagree"] = record["posterior_leaders"] != record["heuristic_leaders"]
        if record["leaders_disagree"]:
            record["caveats"].append("Posterior leaders differ from descriptive heuristic leaders; reported, not resolved.")
    return record
