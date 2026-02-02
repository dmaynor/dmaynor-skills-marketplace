#!/usr/bin/env python3
"""
ACH Matrix generator for SAT Analysis.

Generates Analysis of Competing Hypotheses matrices in markdown format.
Supports rating, scoring, sensitivity analysis, and diagnosticity assessment.
"""

import json
import sys
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


# Rating values and display
RATINGS = {
    "++": {"value": 2, "display": "++", "meaning": "Strongly Supports"},
    "+": {"value": 1, "display": "+", "meaning": "Supports"},
    "N": {"value": 0, "display": "N", "meaning": "Neutral"},
    "-": {"value": -1, "display": "-", "meaning": "Contradicts"},
    "--": {"value": -2, "display": "--", "meaning": "Strongly Contradicts"},
}


@dataclass
class Hypothesis:
    """A hypothesis in the ACH matrix."""
    
    id: str
    description: str
    category: str = ""
    initial_probability: Optional[float] = None


@dataclass
class Evidence:
    """A piece of evidence in the ACH matrix."""
    
    id: str
    description: str
    source: str = ""
    reliability: str = ""  # A-F scale
    ratings: dict = field(default_factory=dict)  # hypothesis_id -> rating string


@dataclass
class ACHMatrix:
    """Analysis of Competing Hypotheses matrix."""
    
    title: str = "ACH Analysis"
    hypotheses: list[Hypothesis] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    
    def add_hypothesis(
        self,
        id: str,
        description: str,
        category: str = "",
        initial_probability: Optional[float] = None,
    ) -> Hypothesis:
        """Add a hypothesis to the matrix."""
        h = Hypothesis(
            id=id,
            description=description,
            category=category,
            initial_probability=initial_probability,
        )
        self.hypotheses.append(h)
        return h
    
    def add_evidence(
        self,
        id: str,
        description: str,
        source: str = "",
        reliability: str = "",
    ) -> Evidence:
        """Add evidence to the matrix."""
        e = Evidence(
            id=id,
            description=description,
            source=source,
            reliability=reliability,
        )
        self.evidence.append(e)
        return e
    
    def rate(self, evidence_id: str, hypothesis_id: str, rating: str):
        """Set rating for evidence-hypothesis pair."""
        if rating not in RATINGS:
            raise ValueError(f"Invalid rating: {rating}. Must be one of {list(RATINGS.keys())}")
        
        for e in self.evidence:
            if e.id == evidence_id:
                e.ratings[hypothesis_id] = rating
                return
        
        raise ValueError(f"Evidence not found: {evidence_id}")
    
    def get_scores(self) -> dict[str, int]:
        """Calculate total score for each hypothesis."""
        scores = {h.id: 0 for h in self.hypotheses}
        
        for e in self.evidence:
            for h_id, rating in e.ratings.items():
                if h_id in scores:
                    scores[h_id] += RATINGS[rating]["value"]
        
        return scores
    
    def get_diagnosticity(self) -> dict[str, float]:
        """
        Calculate diagnosticity score for each evidence item.
        Higher = more useful for distinguishing between hypotheses.
        """
        diagnosticity = {}
        
        for e in self.evidence:
            if not e.ratings:
                diagnosticity[e.id] = 0.0
                continue
            
            # Variance in ratings indicates diagnosticity
            values = [RATINGS[r]["value"] for r in e.ratings.values()]
            if len(values) < 2:
                diagnosticity[e.id] = 0.0
                continue
            
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            diagnosticity[e.id] = variance
        
        return diagnosticity
    
    def sensitivity_analysis(self) -> dict:
        """
        Analyze how robust the conclusion is to removing each evidence item.
        """
        base_scores = self.get_scores()
        base_winner = max(base_scores, key=base_scores.get)
        
        results = {
            "base_scores": base_scores,
            "base_winner": base_winner,
            "evidence_impact": {},
            "conclusion_robust": True,
        }
        
        for e in self.evidence:
            # Calculate scores without this evidence
            scores_without = {h.id: 0 for h in self.hypotheses}
            for other_e in self.evidence:
                if other_e.id == e.id:
                    continue
                for h_id, rating in other_e.ratings.items():
                    if h_id in scores_without:
                        scores_without[h_id] += RATINGS[rating]["value"]
            
            winner_without = max(scores_without, key=scores_without.get)
            
            results["evidence_impact"][e.id] = {
                "scores_without": scores_without,
                "winner_without": winner_without,
                "changes_conclusion": winner_without != base_winner,
            }
            
            if winner_without != base_winner:
                results["conclusion_robust"] = False
        
        return results
    
    def to_markdown(self, include_analysis: bool = True) -> str:
        """Generate markdown representation of ACH matrix."""
        lines = [f"## {self.title}\n"]
        
        # Hypotheses summary
        lines.append("### Hypotheses\n")
        for h in self.hypotheses:
            prob = f" ({h.initial_probability:.0%})" if h.initial_probability else ""
            cat = f" [{h.category}]" if h.category else ""
            lines.append(f"- **{h.id}**: {h.description}{cat}{prob}")
        lines.append("")
        
        # Matrix table
        lines.append("### Consistency Matrix\n")
        
        # Header
        h_ids = [h.id for h in self.hypotheses]
        header = "| Evidence |" + "|".join(f" {h_id} " for h_id in h_ids) + "|"
        separator = "|----------|" + "|".join("----" for _ in h_ids) + "|"
        lines.append(header)
        lines.append(separator)
        
        # Evidence rows
        for e in self.evidence:
            cells = []
            for h in self.hypotheses:
                rating = e.ratings.get(h.id, "?")
                cells.append(f" {rating} ")
            
            desc = e.description[:40] + "..." if len(e.description) > 40 else e.description
            lines.append(f"| {e.id}: {desc} |" + "|".join(cells) + "|")
        
        # Score row
        scores = self.get_scores()
        score_cells = [f" **{scores[h.id]:+d}** " for h in self.hypotheses]
        lines.append("|----------|" + "|".join("----" for _ in h_ids) + "|")
        lines.append("| **SCORE** |" + "|".join(score_cells) + "|")
        lines.append("")
        
        # Results
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        lines.append("### Results\n")
        lines.append(f"- **Most Consistent**: {sorted_scores[0][0]} (score: {sorted_scores[0][1]:+d})")
        lines.append(f"- **Least Consistent**: {sorted_scores[-1][0]} (score: {sorted_scores[-1][1]:+d})")
        lines.append("")
        
        if include_analysis:
            # Diagnosticity
            diag = self.get_diagnosticity()
            sorted_diag = sorted(diag.items(), key=lambda x: x[1], reverse=True)
            
            lines.append("### Discriminating Evidence\n")
            lines.append("Evidence most useful for distinguishing hypotheses:\n")
            for e_id, score in sorted_diag[:3]:
                e = next((e for e in self.evidence if e.id == e_id), None)
                if e:
                    lines.append(f"- **{e_id}**: {e.description[:50]} (diagnosticity: {score:.2f})")
            lines.append("")
            
            # Sensitivity
            sensitivity = self.sensitivity_analysis()
            
            lines.append("### Sensitivity Analysis\n")
            
            if sensitivity["conclusion_robust"]:
                lines.append("✓ **Conclusion is robust** - removing any single evidence item does not change the winner.\n")
            else:
                lines.append("⚠ **Conclusion is sensitive** - removing these evidence items changes the winner:\n")
                for e_id, impact in sensitivity["evidence_impact"].items():
                    if impact["changes_conclusion"]:
                        lines.append(f"- Removing **{e_id}** → winner becomes {impact['winner_without']}")
                lines.append("")
        
        return "\n".join(lines)
    
    def to_json(self) -> str:
        """Export matrix as JSON."""
        data = {
            "title": self.title,
            "hypotheses": [
                {
                    "id": h.id,
                    "description": h.description,
                    "category": h.category,
                    "initial_probability": h.initial_probability,
                }
                for h in self.hypotheses
            ],
            "evidence": [
                {
                    "id": e.id,
                    "description": e.description,
                    "source": e.source,
                    "reliability": e.reliability,
                    "ratings": e.ratings,
                }
                for e in self.evidence
            ],
            "scores": self.get_scores(),
            "diagnosticity": self.get_diagnosticity(),
        }
        return json.dumps(data, indent=2)


def from_json(data: dict) -> ACHMatrix:
    """Load ACH matrix from JSON data."""
    matrix = ACHMatrix(title=data.get("title", "ACH Analysis"))
    
    for h in data.get("hypotheses", []):
        matrix.add_hypothesis(
            id=h["id"],
            description=h["description"],
            category=h.get("category", ""),
            initial_probability=h.get("initial_probability"),
        )
    
    for e in data.get("evidence", []):
        ev = matrix.add_evidence(
            id=e["id"],
            description=e["description"],
            source=e.get("source", ""),
            reliability=e.get("reliability", ""),
        )
        ev.ratings = e.get("ratings", {})
    
    return matrix


def create_empty_matrix(
    hypotheses: list[tuple[str, str]],
    evidence: list[tuple[str, str]],
    title: str = "ACH Analysis",
) -> ACHMatrix:
    """
    Create empty matrix structure for manual rating.
    
    Args:
        hypotheses: List of (id, description) tuples
        evidence: List of (id, description) tuples
        title: Matrix title
    
    Returns:
        ACHMatrix with structure but no ratings
    """
    matrix = ACHMatrix(title=title)
    
    for h_id, h_desc in hypotheses:
        matrix.add_hypothesis(id=h_id, description=h_desc)
    
    for e_id, e_desc in evidence:
        matrix.add_evidence(id=e_id, description=e_desc)
    
    return matrix


def interactive_rating(matrix: ACHMatrix) -> ACHMatrix:
    """Interactively prompt for ratings."""
    print(f"\n{matrix.title}")
    print("=" * len(matrix.title))
    print("\nHypotheses:")
    for h in matrix.hypotheses:
        print(f"  {h.id}: {h.description}")
    
    print("\nRating scale: ++ (strongly supports), + (supports), N (neutral), - (contradicts), -- (strongly contradicts)")
    print()
    
    for e in matrix.evidence:
        print(f"\nEvidence {e.id}: {e.description}")
        for h in matrix.hypotheses:
            while True:
                rating = input(f"  Rate for {h.id} [++/+/N/-/--]: ").strip()
                if rating in RATINGS:
                    matrix.rate(e.id, h.id, rating)
                    break
                print("  Invalid rating. Use: ++, +, N, -, --")
    
    return matrix


def main():
    """CLI interface for ACH matrix operations."""
    if len(sys.argv) < 2:
        print("Usage: ach_matrix.py <command> [args]")
        print("\nCommands:")
        print("  create <json_file>  - Create matrix from JSON definition")
        print("  example             - Show example matrix")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "example":
        # Create example matrix
        matrix = ACHMatrix(title="Example: SSH Authentication Anomaly")
        
        matrix.add_hypothesis("H1", "External attacker brute force", "Malicious External")
        matrix.add_hypothesis("H2", "Authorized penetration test", "Non-Mal Authorized")
        matrix.add_hypothesis("H3", "Admin forgot password", "Non-Mal Authorized")
        matrix.add_hypothesis("H4", "Insider using external IP", "Malicious Internal")
        matrix.add_hypothesis("H5", "Automated scanner", "System Artifact")
        
        matrix.add_evidence("E1", "53 failed attempts in 3 min")
        matrix.add_evidence("E2", "2-second intervals (automated)")
        matrix.add_evidence("E3", "Successful auth after failures")
        matrix.add_evidence("E4", "Cron job created: /tmp/.x")
        matrix.add_evidence("E5", "Hidden file naming (.x)")
        matrix.add_evidence("E6", "43-second total session")
        
        # Rate the matrix
        ratings = {
            ("E1", "H1"): "++", ("E1", "H2"): "+", ("E1", "H3"): "+", ("E1", "H4"): "+", ("E1", "H5"): "++",
            ("E2", "H1"): "++", ("E2", "H2"): "+", ("E2", "H3"): "--", ("E2", "H4"): "+", ("E2", "H5"): "++",
            ("E3", "H1"): "++", ("E3", "H2"): "+", ("E3", "H3"): "++", ("E3", "H4"): "+", ("E3", "H5"): "+",
            ("E4", "H1"): "++", ("E4", "H2"): "+", ("E4", "H3"): "--", ("E4", "H4"): "++", ("E4", "H5"): "-",
            ("E5", "H1"): "++", ("E5", "H2"): "N", ("E5", "H3"): "--", ("E5", "H4"): "++", ("E5", "H5"): "-",
            ("E6", "H1"): "++", ("E6", "H2"): "+", ("E6", "H3"): "--", ("E6", "H4"): "++", ("E6", "H5"): "+",
        }
        
        for (e_id, h_id), rating in ratings.items():
            matrix.rate(e_id, h_id, rating)
        
        print(matrix.to_markdown())
    
    elif command == "create":
        if len(sys.argv) < 3:
            print("Usage: ach_matrix.py create <json_file>")
            sys.exit(1)
        
        filepath = Path(sys.argv[2])
        with open(filepath) as f:
            data = json.load(f)
        
        matrix = from_json(data)
        print(matrix.to_markdown())
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
