"""ICD 203 likelihood ladder and likelihood/confidence sentence separation.

Rules: ICD203-LIKELIHOOD-TERMS (D.6.e.(2)(a)), ICD203-LIKELIHOOD-CONFIDENCE-SENTENCE (D.6.e.(2)(b)).
Judgments are analyst-authored; these checks reject expressions the standard forbids.
They never rewrite the analyst's text.
"""

from __future__ import annotations

import re
from typing import Any

from .validators import ValidationFailure

LIKELIHOOD_LADDER: tuple[tuple[str, float, float], ...] = (
    ("almost no chance", 0.01, 0.05),
    ("very unlikely", 0.05, 0.20),
    ("unlikely", 0.20, 0.45),
    ("roughly even chance", 0.45, 0.55),
    ("likely", 0.55, 0.80),
    ("very likely", 0.80, 0.95),
    ("almost certain", 0.95, 0.99),
)
_LADDER_ALIASES: dict[str, str] = {
    "remote": "almost no chance", "highly improbable": "very unlikely", "improbable": "unlikely",
    "roughly even odds": "roughly even chance", "probable": "likely", "probably": "likely",
    "highly probable": "very likely", "nearly certain": "almost certain", "almost certainly": "almost certain",
}
CONFIDENCE_LEVELS: tuple[str, ...] = ("low", "moderate", "high")

_TERM_PATTERN = re.compile(
    r"\b(almost no chance|very unlikely|unlikely|roughly even chance|roughly even odds|very likely|likely|"
    r"almost certain(?:ly)?|nearly certain|highly probable|highly improbable|improbable|probabl[ey]|remote chance)\b",
    re.IGNORECASE,
)
_CONFIDENCE_PATTERN = re.compile(
    r"\b(?:(?:low|moderate|high)[- ]confidence|confidence(?:\s+(?:level\s+)?(?:is|of|:))?\s+(?:low|moderate|high))\b",
    re.IGNORECASE,
)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def canonical_term(term: str) -> str | None:
    """Return the ladder term for `term` (accepting the standard's synonyms), or None."""
    key = term.strip().lower()
    if key in _LADDER_ALIASES:
        return _LADDER_ALIASES[key]
    return key if any(key == name for name, _, _ in LIKELIHOOD_LADDER) else None


def band_for(term: str) -> tuple[float, float]:
    """Numeric band for a canonical ladder term."""
    for name, low, high in LIKELIHOOD_LADDER:
        if name == term:
            return low, high
    raise KeyError(term)


def check_likelihood_term(likelihood: dict[str, Any] | None, path: str = "$.judgment.likelihood") -> None:
    """Reject a term outside the ladder, or a term whose band excludes the supplied value."""
    if not likelihood or not likelihood.get("term"):
        return
    term = canonical_term(likelihood["term"])
    if term is None:
        raise ValidationFailure("likelihood_term_not_on_ladder",
                                f"Likelihood term {likelihood['term']!r} is not an ICD 203 ladder term.",
                                f"{path}.term", "Use one ladder term: " + ", ".join(n for n, _, _ in LIKELIHOOD_LADDER) + ".")
    value = likelihood.get("value")
    if value is not None:
        low, high = band_for(term)
        if not (low <= value <= high):
            raise ValidationFailure("likelihood_term_band_mismatch",
                                    f"Value {value} is outside the {term!r} band {low:.2f}-{high:.2f}.",
                                    f"{path}.value", "Align the numeric value and the ladder term; do not mix rows.")


def sentences_mixing_likelihood_and_confidence(text: str) -> list[str]:
    """Sentences that contain both a ladder term and a confidence level."""
    return [s for s in _SENTENCE_SPLIT.split(text) if _TERM_PATTERN.search(s) and _CONFIDENCE_PATTERN.search(s)]


def check_sentence_separation(judgment: dict[str, Any] | None, path: str = "$.judgment") -> None:
    """ICD 203 D.6.e.(2)(b): no sentence carries both a likelihood term and a confidence level."""
    if not judgment:
        return
    fields = {"summary": judgment.get("summary", ""),
              "likelihood.basis": (judgment.get("likelihood") or {}).get("basis", ""),
              "confidence.reasoning": (judgment.get("confidence") or {}).get("reasoning", ""),
              "implications": " ".join(judgment.get("implications", []))}
    for name, text in fields.items():
        offending = sentences_mixing_likelihood_and_confidence(text)
        if offending:
            raise ValidationFailure("likelihood_confidence_same_sentence",
                                    f"A sentence combines a likelihood term and a confidence level: {offending[0]!r}",
                                    f"{path}.{name}", "State likelihood and confidence in separate sentences (ICD 203 D.6.e.(2)(b)).")
