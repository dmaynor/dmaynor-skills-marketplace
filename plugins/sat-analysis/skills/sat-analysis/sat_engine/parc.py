"""Opt-in descriptive PARC weighted-inconsistency ranking over an ACHMatrix.

Off by default and never called by the pipeline (SAT-NO-CAUSAL-WINNER holds). This
is an analyst-invoked SDK function for comparison in the evaluation harness.

Heuer's rule counts only inconsistent cells; PARC ACH 2.0 weights them by the
analyst's explicit credibility and relevance assertions:

    cell  = base[rating] * mult[credibility] * mult[relevance]
    base  = {"--": -2, "-": -1, "N": 0, "+": 0, "++": 0}
    mult  = {"L": 1/sqrt(2), "M": 1, "H": sqrt(2)}      # credibility 1-2 -> H, 3-4 -> M, 5 -> L, 6 -> 1 + flag

Weights are supplied per evidence ID by the caller; the matrix's reliability text
is never converted into a number (SAT-UNKNOWN-RELIABILITY).

Known failure mode, reproduced in this repository's harness and documented in
Mandel, Karvetski and Dhami (2018): a hypothesis consistent with everything has
zero inconsistency and ranks first. `descriptive_ranking(..., guard_vague=True)`
demotes such hypotheses; the harness compares both variants.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any

from .ach import ACHMatrix

PARC_MULTIPLIER: dict[str, float] = {"L": 1 / math.sqrt(2), "M": 1.0, "H": math.sqrt(2)}
INCONSISTENCY_BASE: dict[str, int] = {"--": -2, "-": -1, "N": 0, "+": 0, "++": 0}
CREDIBILITY_TO_LEVEL: dict[str, str | None] = {"1": "H", "2": "H", "3": "M", "4": "M", "5": "L", "6": None}
VAGUE_MIN_RATED_ITEMS: int = 3


@dataclass(frozen=True)
class CellWeight:
    """Analyst-asserted Admiralty information credibility (1-6) and PARC relevance (L/M/H)."""
    credibility: str
    relevance: str

    def multiplier(self) -> tuple[float, bool]:
        level = CREDIBILITY_TO_LEVEL[self.credibility]
        unjudged = level is None
        return (1.0 if unjudged else PARC_MULTIPLIER[level]) * PARC_MULTIPLIER[self.relevance], unjudged


@dataclass
class DescriptiveRanking:
    order: list[str]
    weighted_inconsistency: dict[str, float]
    heuer_tie_at_top: bool
    tie_resolved_by_predicted_by: bool
    needs_discriminating_evidence: list[str]
    vague_hypotheses: list[str]
    unjudged_evidence: list[str]
    caveats: list[str] = field(default_factory=lambda: [
        "Descriptive ranking of analyst-authored ratings under PARC weighting; not a probability, causal finding, or confidence.",
        "Pure inconsistency counting ranks a hypothesis consistent with everything first (Mandel, Karvetski and Dhami 2018).",
    ])


def weighted_inconsistency(matrix: ACHMatrix, weights: dict[str, CellWeight]) -> tuple[dict[str, float], list[str]]:
    """PARC weighted inconsistency per hypothesis (<= 0) and the evidence IDs with unjudged credibility."""
    matrix.validate()
    scores = {h.id: 0.0 for h in matrix.hypotheses}
    unjudged: list[str] = []
    for evidence in matrix._unique_evidence():
        if evidence.id not in weights:
            raise ValueError(f"no PARC weight supplied for evidence {evidence.id!r}")
        multiplier, is_unjudged = weights[evidence.id].multiplier()
        if is_unjudged:
            unjudged.append(evidence.id)
        for hypothesis_id, rating in evidence.ratings.items():
            scores[hypothesis_id] += INCONSISTENCY_BASE[rating] * multiplier
    return scores, unjudged


def vague_hypotheses(matrix: ACHMatrix) -> list[str]:
    """Hypotheses with >= VAGUE_MIN_RATED_ITEMS ratings, no contradiction, and no strong support."""
    result = []
    for hypothesis in matrix.hypotheses:
        ratings = [e.ratings[hypothesis.id] for e in matrix._unique_evidence() if hypothesis.id in e.ratings]
        if len(ratings) >= VAGUE_MIN_RATED_ITEMS and not any(r in ("-", "--") for r in ratings) and "++" not in ratings:
            result.append(hypothesis.id)
    return result


def descriptive_ranking(matrix: ACHMatrix, weights: dict[str, CellWeight], guard_vague: bool = False) -> DescriptiveRanking:
    """Least-inconsistent first; ties reported; a consistency sum is never consulted."""
    weighted, unjudged = weighted_inconsistency(matrix, weights)
    strong = {h.id: 0 for h in matrix.hypotheses}
    any_contra = {h.id: 0 for h in matrix.hypotheses}
    predicted_by = {h.id: 0 for h in matrix.hypotheses}
    for evidence in matrix._unique_evidence():
        for hypothesis_id, rating in evidence.ratings.items():
            strong[hypothesis_id] += rating == "--"
            any_contra[hypothesis_id] += rating in ("-", "--")
            predicted_by[hypothesis_id] += rating == "++"

    def heuer_key(hypothesis_id: str) -> tuple[float, int, int]:
        return (-weighted[hypothesis_id], strong[hypothesis_id], any_contra[hypothesis_id])

    order = sorted((h.id for h in matrix.hypotheses), key=lambda h: (*heuer_key(h), -predicted_by[h], h))
    top = heuer_key(order[0])
    tied = [h for h in order if heuer_key(h) == top]
    heuer_tie = len(tied) > 1
    resolved = heuer_tie and len({predicted_by[h] for h in tied}) > 1
    unresolved = [h for h in tied if predicted_by[h] == predicted_by[order[0]]] if heuer_tie else []
    vague = vague_hypotheses(matrix)
    if guard_vague and vague and not set(order) <= set(vague):
        order = [h for h in order if h not in vague] + [h for h in order if h in vague]
    return DescriptiveRanking(order, weighted, heuer_tie, resolved,
                              unresolved if len(unresolved) > 1 else [], vague, unjudged)
