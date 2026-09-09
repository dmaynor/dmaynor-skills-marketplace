#!/usr/bin/env python3
"""Inspect analyst-authored ACH ratings without selecting a causal winner.

The integer totals and rating variance are descriptive heuristics. They are
neither likelihoods nor evidence of causation. See references/data_contract.md.
Requires Python 3.12 or newer; uses only the standard library.
"""

from __future__ import annotations

import argparse
import copy
import html
import json
import math
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TypedDict


RATINGS = {
    "++": {"value": 2, "display": "++", "meaning": "Strongly supports"},
    "+": {"value": 1, "display": "+", "meaning": "Supports"},
    "N": {"value": 0, "display": "N", "meaning": "Evaluated; nondiscriminating"},
    "-": {"value": -1, "display": "-", "meaning": "Contradicts"},
    "--": {"value": -2, "display": "--", "meaning": "Strongly contradicts"},
}
RATING_VALUES = {"++": 2, "+": 1, "N": 0, "-": -1, "--": -2}
RELATIONSHIPS = {
    "unspecified", "exclusive_exhaustive", "exclusive_nonexhaustive", "overlapping"
}
PROBABILITY_TOLERANCE = 1e-9


def _text(value: object, name: str, *, nonempty: bool = False) -> str:
    """Validate a string without silently normalizing supplied evidence."""
    if not isinstance(value, str) or (nonempty and not value.strip()):
        raise ValueError(f"{name} must be {'a nonempty string' if nonempty else 'a string'}")
    return value


def _object(value: object, name: str) -> dict[str, object]:
    """Require a JSON-style object with string keys."""
    if not isinstance(value, dict) or any(not isinstance(k, str) for k in value):
        raise ValueError(f"{name} must be an object with string keys")
    return value


def _probability(value: object, name: str) -> None:
    """Validate optional point probabilities without accepting booleans."""
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite point probability or null")
    if not 0 <= value <= 1 or not math.isfinite(value):
        raise ValueError(f"{name} must be finite and in [0, 1]")


def _markdown(value: str) -> str:
    """Escape supplied text, including table delimiters, HTML and newlines."""
    value = re.sub(r"[\x00-\x1f\x7f]", " ", value)
    value = html.escape(value, quote=True)
    return re.sub(r"([\\`*_{}\[\]()#+.!|~\-])", r"\\\1", value)


@dataclass
class Hypothesis:
    """An analyst-scoped proposition; initial_probability is optional likelihood."""

    id: str
    description: str
    category: str = ""
    initial_probability: float | None = None
    falsifier: str | None = None

    def validate(self) -> None:
        """Reject malformed hypothesis fields."""
        _text(self.id, "hypothesis.id", nonempty=True)
        _text(self.description, f"{self.id}.description")
        _text(self.category, f"{self.id}.category")
        _probability(self.initial_probability, f"{self.id}.initial_probability")
        if self.falsifier is not None:
            _text(self.falsifier, f"{self.id}.falsifier")


@dataclass
class Evidence:
    """Evidence record with explicit observation origin and upstream dependencies.

    An origin identifies a republished observation, not every measurement about
    the same business event. Send and receipt measurements have different origins.
    Reliability is a source assertion, never an arithmetic multiplier. A missing
    rating is distinct from the explicit neutral rating N.
    """

    id: str
    description: str
    source: str = ""
    reliability: str = ""
    ratings: dict[str, str] = field(default_factory=dict)
    origin_id: str | None = None
    dependency_groups: list[str] = field(default_factory=list)

    def validate(self) -> None:
        """Validate local fields; the matrix checks hypothesis references."""
        _text(self.id, "evidence.id", nonempty=True)
        for name in ("description", "source", "reliability"):
            _text(getattr(self, name), f"{self.id}.{name}")
        if self.origin_id is not None:
            _text(self.origin_id, f"{self.id}.origin_id", nonempty=True)
        if not isinstance(self.dependency_groups, list):
            raise ValueError(f"{self.id}.dependency_groups must be an array")
        for group in self.dependency_groups:
            _text(group, f"{self.id}.dependency_groups entry", nonempty=True)
        if len(set(self.dependency_groups)) != len(self.dependency_groups):
            raise ValueError(f"{self.id}.dependency_groups must be unique")
        ratings = _object(self.ratings, f"{self.id}.ratings")
        for hypothesis_id, rating in ratings.items():
            _text(hypothesis_id, f"{self.id}.ratings key", nonempty=True)
            if not isinstance(rating, str) or rating not in RATING_VALUES:
                raise ValueError(f"{self.id}/{hypothesis_id}: invalid rating {rating!r}")


class Assessment(TypedDict):
    """A descriptive assessment result; winner is always null."""

    status: str
    heuristic_leaders: list[str]
    winner: None
    missing_ratings: list[dict[str, str]]
    caveats: list[str]
    scores: dict[str, int]
    contradictions: dict[str, list[dict[str, object]]]
    contributing_record_count: int


@dataclass
class ACHMatrix:
    """A validated ACH matrix with explicit unresolved states."""

    title: str = "ACH Analysis"
    hypotheses: list[Hypothesis] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    relationship: str = "unspecified"

    def validate(self) -> None:
        """Validate references, duplicates and stated probability relationships.

        Validation also runs before analysis/export because callers may mutate
        the retained dataclass fields. Incremental construction may temporarily
        contain incomplete ratings or an unfinished probability allocation.
        """
        _text(self.title, "title")
        if not isinstance(self.relationship, str) or self.relationship not in RELATIONSHIPS:
            raise ValueError(f"relationship must be one of {sorted(RELATIONSHIPS)}")
        if not isinstance(self.hypotheses, list) or not isinstance(self.evidence, list):
            raise ValueError("hypotheses and evidence must be arrays")
        hypothesis_ids: set[str] = set()
        for hypothesis in self.hypotheses:
            if not isinstance(hypothesis, Hypothesis):
                raise ValueError("hypotheses entries must be Hypothesis objects")
            hypothesis.validate()
            if hypothesis.id in hypothesis_ids:
                raise ValueError(f"Duplicate hypothesis ID: {hypothesis.id}")
            hypothesis_ids.add(hypothesis.id)
        evidence_ids: set[str] = set()
        origin_ratings: dict[str, dict[str, str]] = {}
        for evidence in self.evidence:
            if not isinstance(evidence, Evidence):
                raise ValueError("evidence entries must be Evidence objects")
            evidence.validate()
            if evidence.id in evidence_ids:
                raise ValueError(f"Duplicate evidence ID: {evidence.id}")
            evidence_ids.add(evidence.id)
            unknown = evidence.ratings.keys() - hypothesis_ids
            if unknown:
                raise ValueError(f"{evidence.id}: unknown hypotheses {sorted(unknown)}")
            if evidence.origin_id is not None:
                previous = origin_ratings.setdefault(evidence.origin_id, evidence.ratings)
                if previous != evidence.ratings:
                    raise ValueError(f"Conflicting ratings for origin {evidence.origin_id!r}")
        probabilities = [h.initial_probability for h in self.hypotheses]
        quantified = [p for p in probabilities if p is not None]
        total = math.fsum(quantified)
        exclusive = self.relationship in {"exclusive_exhaustive", "exclusive_nonexhaustive"}
        if exclusive and total > 1 and not math.isclose(
            total, 1, rel_tol=0, abs_tol=PROBABILITY_TOLERANCE
        ):
            raise ValueError("Exclusive probabilities cannot sum above 1")
        if self.relationship == "exclusive_exhaustive" and probabilities and len(quantified) == len(probabilities):
            if not math.isclose(total, 1, rel_tol=0, abs_tol=PROBABILITY_TOLERANCE):
                raise ValueError("Fully quantified exclusive_exhaustive probabilities must sum to 1")

    def add_hypothesis(
        self, id: str, description: str, category: str = "",
        initial_probability: float | None = None, falsifier: str | None = None,
    ) -> Hypothesis:
        """Add a hypothesis, validating its fields and unique identifier."""
        hypothesis = Hypothesis(id, description, category, initial_probability, falsifier)
        hypothesis.validate()
        if any(h.id == id for h in self.hypotheses):
            raise ValueError(f"Duplicate hypothesis ID: {id}")
        self.hypotheses.append(hypothesis)
        return hypothesis

    def add_evidence(
        self, id: str, description: str, source: str = "", reliability: str = "",
        origin_id: str | None = None, dependency_groups: list[str] | None = None,
    ) -> Evidence:
        """Add a record; unknown dependencies remain unknown."""
        if dependency_groups is not None and not isinstance(dependency_groups, list):
            raise ValueError("dependency_groups must be an array")
        evidence = Evidence(id, description, source, reliability, {}, origin_id,
                            [] if dependency_groups is None else list(dependency_groups))
        evidence.validate()
        if any(e.id == id for e in self.evidence):
            raise ValueError(f"Duplicate evidence ID: {id}")
        self.evidence.append(evidence)
        return evidence

    def rate(self, evidence_id: str, hypothesis_id: str, rating: str) -> None:
        """Set a known pair's rating; complete origin conflicts fail on analysis."""
        if not isinstance(rating, str) or rating not in RATING_VALUES:
            raise ValueError(f"Invalid rating: {rating!r}")
        if not any(h.id == hypothesis_id for h in self.hypotheses):
            raise ValueError(f"Hypothesis not found: {hypothesis_id}")
        for evidence in self.evidence:
            if evidence.id == evidence_id:
                evidence.ratings[hypothesis_id] = rating
                return
        raise ValueError(f"Evidence not found: {evidence_id}")

    @staticmethod
    def _observation_key(evidence: Evidence) -> tuple[str, str]:
        """Distinguish original measurements from repeated references to a record."""
        if evidence.origin_id is not None:
            return ("origin", evidence.origin_id)
        observation_id = getattr(evidence, "observation_id", None)
        if observation_id is not None:
            return ("observation", observation_id)
        return ("evidence", evidence.id)

    def _unique_evidence(self) -> list[Evidence]:
        """Return deterministic representatives of established observation origins."""
        representatives: list[Evidence] = []
        origins: set[tuple[str, str]] = set()
        for evidence in sorted(self.evidence, key=lambda e: e.id):
            origin = self._observation_key(evidence)
            if origin in origins:
                continue
            origins.add(origin)
            representatives.append(evidence)
        return representatives

    def get_scores(self) -> dict[str, int]:
        """Return descriptive totals over rated cells, deduplicating explicit origins.

        Missing cells add no rating; they are never interpreted as neutral.
        Consult assessment()['missing_ratings'] before interpreting any total.
        """
        self.validate()
        scores = {h.id: 0 for h in sorted(self.hypotheses, key=lambda h: h.id)}
        for evidence in self._unique_evidence():
            for hypothesis_id, rating in evidence.ratings.items():
                scores[hypothesis_id] += RATING_VALUES[rating]
        return scores

    def get_diagnosticity(self) -> dict[str, float | None]:
        """Return rating variance, not empirical diagnosticity; incomplete rows are null."""
        self.validate()
        variance: dict[str, float | None] = {}
        for evidence in sorted(self.evidence, key=lambda e: e.id):
            if len(evidence.ratings) != len(self.hypotheses) or not self.hypotheses:
                variance[evidence.id] = None
                continue
            # JSON object key order is not semantic; keep floating arithmetic
            # deterministic for equivalent canonical inputs.
            values = [RATING_VALUES[evidence.ratings[hypothesis_id]]
                      for hypothesis_id in sorted(evidence.ratings)]
            mean = sum(values) / len(values)
            variance[evidence.id] = math.fsum((v - mean) ** 2 for v in values) / len(values)
        return variance

    def assessment(self) -> Assessment:
        """Expose coverage, contradictions and heuristic discrimination without causation."""
        scores = self.get_scores()
        missing = [
            {"evidence_id": e.id, "hypothesis_id": h.id}
            for e in sorted(self.evidence, key=lambda e: e.id)
            for h in sorted(self.hypotheses, key=lambda h: h.id)
            if h.id not in e.ratings
        ]
        unique = self._unique_evidence()
        leaders = sorted(h for h, score in scores.items() if score == max(scores.values())) if scores and unique else []
        discriminates = any(len(set(e.ratings.values())) > 1 for e in unique)
        if not self.hypotheses or not unique:
            status = "insufficient_evidence"
        elif missing:
            status = "incomplete"
        elif not discriminates or len(leaders) != 1:
            status = "underdetermined"
        else:
            status = "differentiated"
        caveats = [
            "Scores and rating variance describe analyst-authored ratings; they are not probabilities, causal proof, or confidence.",
            "Coverage and observation validity are not established by matrix completeness; a contradiction rating is not verified falsification.",
            "Missing dependency metadata does not establish independence; source reliability is not used as a numeric weight.",
        ]
        if status != "differentiated":
            caveats.append(f"Assessment is {status}; no differentiated heuristic result is available.")
        if missing:
            caveats.append(f"{len(missing)} evidence/hypothesis ratings are missing, not neutral.")
        if len(unique) != len(self.evidence):
            caveats.append(f"{len(self.evidence) - len(unique)} derivative records share explicit origins or observation references and contribute no additional score.")
        if any(e.dependency_groups for e in self.evidence):
            caveats.append("Shared upstream dependencies are declared; inspect group-removal sensitivity.")
        sources = [e.source for e in self.evidence if e.source.strip()]
        if len(sources) != len(set(sources)):
            caveats.append("Multiple records share a source locator; inspect source-group removal as well as individual records.")
        source_ids = [getattr(e, "source_id", None) for e in self.evidence]
        known_source_ids = [source_id for source_id in source_ids if source_id is not None]
        if len(known_source_ids) != len(set(known_source_ids)):
            caveats.append("Multiple records share an explicit source identity; inspect source-identity group removal.")
        unknown = sorted(e.id for e in self.evidence if e.reliability.strip().casefold() in {"", "f", "unknown", "unrated", "cannot be judged", "?"})
        if unknown:
            caveats.append(f"Source reliability is unknown or unjudged for: {', '.join(unknown)}.")
        if any(not e.source.strip() for e in self.evidence):
            caveats.append("Some evidence lacks a source locator; provenance is incomplete.")
        if self.relationship == "unspecified":
            caveats.append("Hypothesis relationships are unspecified; combined causes and omitted alternatives remain possible.")
        if any(h.initial_probability is None for h in self.hypotheses):
            caveats.append("Unspecified initial probabilities remain unknown and have not been replaced by zero.")
        contradictions: dict[str, list[dict[str, object]]] = {h: [] for h in scores}
        for evidence in unique:
            for hypothesis_id, rating in sorted(evidence.ratings.items()):
                if RATING_VALUES[rating] < 0:
                    aliases = sorted(e.id for e in self.evidence
                                     if self._observation_key(e) == self._observation_key(evidence))
                    contradictions[hypothesis_id].append({
                        "evidence_ids": aliases, "origin_id": evidence.origin_id,
                        "description": evidence.description, "rating": rating,
                    })
        return {
            "status": status, "heuristic_leaders": leaders, "winner": None,
            "missing_ratings": missing, "caveats": caveats, "scores": scores,
            "contradictions": contradictions, "contributing_record_count": len(unique),
        }

    def sensitivity_analysis(self) -> dict[str, object]:
        """Compare complete status/leader outcomes after row and group removals.

        Source- and dependency-group removal includes all derivatives of affected
        origins. Nonblank source locators form source groups; blank locators stay
        unknown and never form one shared group. Matching source text does not
        deduplicate distinct observations. Origin groups are additionally tested;
        namespaced keys prevent collisions.
        Stability describes these removals only, never analytic robustness.
        """
        base = self.assessment()
        base_signature = (base["status"], base["heuristic_leaders"])

        def remove(ids: set[str]) -> dict[str, object]:
            reduced = ACHMatrix(self.title, list(self.hypotheses),
                                [e for e in self.evidence if e.id not in ids], self.relationship)
            result = reduced.assessment()
            changed = (result["status"], result["heuristic_leaders"]) != base_signature
            return {
                "removed_evidence_ids": sorted(ids), "status": result["status"],
                "heuristic_leaders": result["heuristic_leaders"], "winner": None,
                "scores_without": result["scores"], "changes_assessment": changed,
            }

        evidence_impact = {e.id: remove({e.id}) for e in sorted(self.evidence, key=lambda e: e.id)}
        groups: dict[str, tuple[str, str, set[str]]] = {}
        for evidence in self.evidence:
            if evidence.source.strip():
                groups.setdefault(f"source:{evidence.source}", ("source", evidence.source, set()))[2].add(evidence.id)
            source_id = getattr(evidence, "source_id", None)
            if source_id is not None:
                groups.setdefault(f"source_id:{source_id}", ("source", source_id, set()))[2].add(evidence.id)
            for group in evidence.dependency_groups:
                groups.setdefault(f"dependency:{group}", ("dependency", group, set()))[2].add(evidence.id)
            if evidence.origin_id is not None:
                groups.setdefault(f"origin:{evidence.origin_id}", ("origin", evidence.origin_id, set()))[2].add(evidence.id)
        group_impact: dict[str, dict[str, object]] = {}
        for key, (kind, group_id, direct_ids) in sorted(groups.items()):
            affected_origins = {self._observation_key(e) for e in self.evidence if e.id in direct_ids}
            ids = direct_ids | {e.id for e in self.evidence if self._observation_key(e) in affected_origins}
            group_impact[key] = {"kind": kind, "id": group_id, **remove(ids)}
        impacts = [*evidence_impact.values(), *group_impact.values()]
        stable = not any(i["changes_assessment"] for i in impacts) if base["status"] == "differentiated" else None
        return {
            "base_assessment": base, "base_scores": base["scores"], "base_winner": None,
            "evidence_impact": evidence_impact, "group_impact": group_impact,
            "heuristic_stable": stable,
            "caveat": "Stability applies only to tested removals of supplied ratings, not to causal confidence or conclusion robustness.",
        }

    def to_markdown(self, include_analysis: bool = True) -> str:
        """Render complete ratings and visible limitations, escaping supplied text."""
        result = self.assessment()
        lines = [f"## {_markdown(self.title)}", "", "### Hypotheses", ""]
        for h in self.hypotheses:
            probability = "not quantified" if h.initial_probability is None else f"{h.initial_probability:.6g}"
            lines.append(f"- **{_markdown(h.id)}**: {_markdown(h.description)}; initial likelihood: {probability}")
            if h.category:
                lines.append(f"  Category: {_markdown(h.category)}")
            if h.falsifier:
                lines.append(f"  Proposed falsifier (requires validation): {_markdown(h.falsifier)}")
        lines.extend(["", f"Relationship: {_markdown(self.relationship)}", "", "### Consistency matrix", ""])
        if self.hypotheses:
            lines.append("| Evidence | " + " | ".join(_markdown(h.id) for h in self.hypotheses) + " |")
            lines.append("| --- | " + " | ".join("---" for _ in self.hypotheses) + " |")
            for e in self.evidence:
                ratings = " | ".join(e.ratings.get(h.id, "? (missing)") for h in self.hypotheses)
                lines.append(f"| {_markdown(e.id)}: {_markdown(e.description)} | {ratings} |")
            totals = " | ".join(str(result["scores"][h.id]) for h in self.hypotheses)
            lines.append(f"| Descriptive total (explicit origins deduplicated) | {totals} |")
        else:
            lines.append("No hypotheses supplied.")
        lines.extend(["", "N = evaluated and nondiscriminating; ? = missing. Totals are not probabilities.",
                      "", "### Assessment", "", f"- Status: {result['status']}",
                      "- Heuristic leaders: " + (", ".join(_markdown(h) for h in result["heuristic_leaders"]) or "none"),
                      "- Causal winner: not determined by this helper."])
        lines.extend(f"- {_markdown(caveat)}" for caveat in result["caveats"])
        lines.extend(["", "### Evidence provenance", ""])
        for e in self.evidence:
            lines.append(f"- **{_markdown(e.id)}**: source={_markdown(e.source) or 'unknown'}; reliability={_markdown(e.reliability) or 'unknown'}; origin={_markdown(e.origin_id) if e.origin_id is not None else 'unknown'}; dependencies={', '.join(_markdown(g) for g in e.dependency_groups) or 'unknown'}")
        if include_analysis:
            lines.extend(["", "### Contradiction ratings", "", "These are analyst judgments, not independently established falsifications.", ""])
            for h in self.hypotheses:
                contradictions = [e for e in self._unique_evidence() if e.ratings.get(h.id) in {"-", "--"}]
                lines.append(f"- {_markdown(h.id)}: " + ("; ".join(f"{_markdown(e.id)} ({e.ratings[h.id]}): {_markdown(e.description)}" for e in contradictions) or "no contradiction rated"))
            lines.extend(["", "### Rating variance", "", "Descriptive variance only; incomplete rows have no variance estimate.", ""])
            for evidence_id, variance in self.get_diagnosticity().items():
                lines.append(f"- {_markdown(evidence_id)}: {'not evaluated' if variance is None else f'{variance:.3g}'}")
            sensitivity = self.sensitivity_analysis()
            lines.extend(["", "### Sensitivity to removal", "", f"Heuristic stable in tested removals: {sensitivity['heuristic_stable']}", "", str(sensitivity["caveat"]), ""])
            for kind in ("evidence_impact", "group_impact"):
                for key, impact in sensitivity[kind].items():
                    if impact["changes_assessment"]:
                        leaders = ", ".join(_markdown(h) for h in impact["heuristic_leaders"]) or "none"
                        lines.append(f"- Remove {_markdown(key)}: status={impact['status']}; heuristic leaders={leaders}.")
        return "\n".join(lines) + "\n"

    def to_json(self) -> str:
        """Export round-trippable inputs and recomputable derived outputs."""
        self.validate()
        data = {
            "schema_version": "2.0.0", "title": self.title, "relationship": self.relationship,
            "hypotheses": [asdict(h) for h in self.hypotheses],
            "evidence": [asdict(e) for e in self.evidence],
            "scores": self.get_scores(), "diagnosticity": self.get_diagnosticity(),
            "assessment": self.assessment(), "sensitivity": self.sensitivity_analysis(),
        }
        return json.dumps(data, indent=2, allow_nan=False)


def from_json(data: object) -> ACHMatrix:
    """Load validated inputs; known derived output fields are always recomputed."""
    data = _object(data, "matrix")
    allowed = {"schema_version", "title", "relationship", "hypotheses", "evidence",
               "scores", "diagnosticity", "assessment", "sensitivity"}
    if extra := data.keys() - allowed:
        raise ValueError(f"Unknown matrix fields: {sorted(extra)}")
    if data.get("schema_version", "2.0.0") != "2.0.0":
        raise ValueError("Unsupported schema_version")
    hypotheses = data.get("hypotheses", [])
    evidence = data.get("evidence", [])
    if not isinstance(hypotheses, list) or not isinstance(evidence, list):
        raise ValueError("hypotheses and evidence must be arrays")
    parsed_hypotheses: list[Hypothesis] = []
    parsed_evidence: list[Evidence] = []
    for index, item in enumerate(hypotheses):
        item = _object(item, f"hypotheses[{index}]")
        if item.keys() - {"id", "description", "category", "initial_probability", "falsifier"}:
            raise ValueError(f"Unknown hypothesis fields at index {index}")
        if not {"id", "description"} <= item.keys():
            raise ValueError(f"hypotheses[{index}] requires id and description")
        parsed_hypotheses.append(Hypothesis(**item))
    for index, item in enumerate(evidence):
        item = _object(item, f"evidence[{index}]")
        if item.keys() - {"id", "description", "source", "reliability", "ratings", "origin_id", "dependency_groups"}:
            raise ValueError(f"Unknown evidence fields at index {index}")
        if not {"id", "description"} <= item.keys():
            raise ValueError(f"evidence[{index}] requires id and description")
        parsed_evidence.append(Evidence(**item))
    matrix = ACHMatrix(data.get("title", "ACH Analysis"), parsed_hypotheses,
                       parsed_evidence, data.get("relationship", "unspecified"))
    matrix.validate()
    return matrix


@dataclass
class _ObservedEvidence(Evidence):
    """Internal helper adapter; canonical evidence contains only analyst ratings.

    These fields are derived from the referenced observation, never independently
    supplied on an engine evidence record. Legacy Evidence stays compatible.
    """

    observation_id: str | None = None
    source_id: str | None = None


def compute_matrix(request: dict[str, object]) -> dict[str, object]:
    """Compute a schema-family-1 matrix from explicit analyst inputs.

    Observation records own provenance. Evidence records may add ratings and a
    rationale, but cannot replace an observation's source, reliability, origin,
    or dependencies. Repeated references to one observation contribute once,
    just as explicitly declared derivative copies do. Distinct observations
    sharing a source remain separate contributions and share a removal group.

    All derived fields are freshly computed. The engine does not convert totals
    or stability into likelihood, confidence, falsification, or a causal winner.
    Schema dependencies are loaded only here, keeping the compatibility helper
    and its CLI usable with the Python standard library.
    """
    from .validators import ValidationFailure, validate

    if not isinstance(request, dict):
        raise ValidationFailure("ach.invalid_input", "Analysis request must be an object")
    data = copy.deepcopy(request)
    # The engine boundary has one schema family; omitted nested versions receive
    # its explicit version marker without repairing any supplied invalid value.
    for kind in ("observations", "hypotheses", "evidence"):
        records = data.get(kind, [])
        if isinstance(records, list):
            for record in records:
                if isinstance(record, dict):
                    record.setdefault("schema_version", "1")
    validate("analysis_request", data)

    def indexed(kind: str) -> dict[str, dict[str, object]]:
        records: dict[str, dict[str, object]] = {}
        for index, record in enumerate(data.get(kind, [])):
            if record["id"] in records:
                raise ValidationFailure(
                    "ach.duplicate_id", f"Duplicate {kind} ID: {record['id']}",
                    path=f"$.{kind}[{index}].id",
                    remediation="Assign each distinct record a unique nonempty ID.",
                )
            records[record["id"]] = record
        return records

    observations = indexed("observations")
    hypotheses = indexed("hypotheses")
    evidence = indexed("evidence")
    matrix = ACHMatrix(title=data["question"], relationship=data.get("relationship", "unspecified"))
    for hypothesis in hypotheses.values():
        matrix.hypotheses.append(Hypothesis(
            id=hypothesis["id"], description=hypothesis["description"],
            category=hypothesis.get("category", ""),
            initial_probability=hypothesis.get("initial_probability"),
            falsifier=hypothesis.get("falsifier"),
        ))

    observation_ratings: dict[str, dict[str, str]] = {}
    for index, record in enumerate(evidence.values()):
        reference = record["observation_id"]
        if reference not in observations:
            raise ValidationFailure(
                "ach.unknown_observation", f"Unknown observation ID: {reference}",
                path=f"$.evidence[{index}].observation_id",
                remediation="Reference an observation supplied in the analysis request.",
            )
        unknown = record["ratings"].keys() - hypotheses.keys()
        if unknown:
            raise ValidationFailure(
                "ach.unknown_hypothesis", f"Unknown hypothesis IDs: {sorted(unknown)}",
                path=f"$.evidence[{index}].ratings",
                remediation="Rate only hypotheses supplied in the analysis request.",
            )
        if data["mode"] == "LIGHT" and record["ratings"]:
            raise ValidationFailure(
                "ach.light_ratings", "LIGHT analysis cannot contain evidence ratings",
                path=f"$.evidence[{index}].ratings",
                remediation="Use FULL mode for a rated ACH matrix.",
            )
        previous = observation_ratings.setdefault(reference, record["ratings"])
        if previous != record["ratings"]:
            raise ValidationFailure(
                "ach.conflicting_ratings", f"Conflicting ratings for observation {reference!r}",
                path=f"$.evidence[{index}].ratings",
                remediation="Resolve the conflicting judgments about the same observation explicitly.",
            )
        observation = observations[reference]
        matrix.evidence.append(_ObservedEvidence(
            id=record["id"], description=observation["raw"],
            source=observation["source"],
            reliability=observation.get("reliability", "unknown"),
            ratings=copy.deepcopy(record["ratings"]),
            origin_id=observation.get("origin_id"),
            dependency_groups=list(observation.get("dependency_groups", [])),
            observation_id=reference, source_id=observation.get("source_id"),
        ))
    try:
        matrix.validate()
        result = {
            "schema_version": "1", "title": matrix.title,
            "relationship": matrix.relationship,
            "hypotheses": list(hypotheses.values()),
            "evidence": list(evidence.values()),
            "assessment": matrix.assessment(),
            "sensitivity": matrix.sensitivity_analysis(),
            "diagnosticity": matrix.get_diagnosticity(),
        }
    except ValueError as exc:
        raise ValidationFailure(
            "ach.invalid_input", str(exc),
            remediation="Correct the reported hypothesis, provenance, or rating conflict without fabricating missing values.",
        ) from exc
    validate("ach_matrix", result)
    return result


def create_empty_matrix(
    hypotheses: list[tuple[str, str]], evidence: list[tuple[str, str]],
    title: str = "ACH Analysis",
) -> ACHMatrix:
    """Create an explicitly unrated matrix for incremental analysis."""
    matrix = ACHMatrix(title=title)
    for hypothesis_id, description in hypotheses:
        matrix.add_hypothesis(hypothesis_id, description)
    for evidence_id, description in evidence:
        matrix.add_evidence(evidence_id, description)
    matrix.validate()
    return matrix


def interactive_rating(matrix: ACHMatrix) -> ACHMatrix:
    """Prompt for analyst ratings; blank input preserves a missing cell."""
    matrix.validate()
    print(matrix.title)
    for hypothesis in matrix.hypotheses:
        print(f"{hypothesis.id}: {hypothesis.description}")
    for evidence in matrix.evidence:
        print(f"{evidence.id}: {evidence.description}")
        for hypothesis in matrix.hypotheses:
            while True:
                rating = input(f"Rate {hypothesis.id} [++/+/N/-/--; blank leaves unchanged]: ").strip()
                if not rating:
                    break
                if rating in RATING_VALUES:
                    matrix.rate(evidence.id, hypothesis.id, rating)
                    break
                print("Invalid rating.")
    matrix.validate()
    return matrix


def _json_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject duplicate JSON keys instead of overwriting analyst inputs."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"Non-finite JSON constant: {value}")


def _example() -> ACHMatrix:
    matrix = create_empty_matrix(
        [("H1", "Transport degradation"), ("H2", "Telemetry calculation artifact"),
         ("H3", "Both transport degradation and inflated telemetry")],
        [("E1", "Independent dispatch transaction arrived late"),
         ("E2", "Reported delay exceeds the independent observation")],
        "Example: real delay with telemetry inflation",
    )
    matrix.relationship = "overlapping"
    for evidence_id, ratings in {"E1": {"H1": "+", "H2": "N", "H3": "+"},
                                 "E2": {"H1": "N", "H2": "+", "H3": "+"}}.items():
        for hypothesis_id, rating in ratings.items():
            matrix.rate(evidence_id, hypothesis_id, rating)
    return matrix


def main(argv: list[str] | None = None) -> int:
    """Run legacy create/example commands with Markdown or JSON output."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("create", "example"))
    parser.add_argument("json_file", nargs="?", type=Path)
    parser.add_argument("--output-format", "--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args(argv)
    if args.command == "create" and args.json_file is None:
        parser.error("create requires a JSON file")
    if args.command == "example" and args.json_file is not None:
        parser.error("example does not accept a JSON file")
    try:
        if args.command == "example":
            matrix = _example()
        else:
            data = json.loads(args.json_file.read_text(encoding="utf-8"),
                              object_pairs_hook=_json_pairs, parse_constant=_reject_constant)
            matrix = from_json(data)
        print(matrix.to_json() if args.output_format == "json" else matrix.to_markdown(), end="\n")
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"ach_matrix: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
