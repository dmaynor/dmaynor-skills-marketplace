#!/usr/bin/env python3
"""Compare ranking rules on a labeled corpus: descriptive total, PARC, PARC with vague guard.

Advisory only. The shipped corpus is synthetic (`synthetic: true`) and was written
with the true hypothesis carrying the most `++` cells, which favours the descriptive
total by construction. Replace with redacted real cases (known root cause, known
bypass, post-incident forensics) before treating any decision as blocking.

    python3 evaluations/ranking_baselines.py [--corpus evaluations/ranking_corpus] [--out report.json]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sat_engine.ach import ACHMatrix  # noqa: E402
from sat_engine.parc import CellWeight, descriptive_ranking  # noqa: E402

DEMOTE_MARGIN_PP = 5.0


def load(corpus: Path) -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(corpus.glob("*.json"))]


def build(case: dict) -> tuple[ACHMatrix, dict[str, CellWeight]]:
    matrix = ACHMatrix(title=case["case_id"])
    for h in case["hypotheses"]:
        matrix.add_hypothesis(h["id"], h["description"])
    weights = {}
    for e in case["evidence"]:
        matrix.add_evidence(e["id"], e["description"], source=e["id"], reliability=e["reliability"])
        for h, r in e["ratings"].items():
            matrix.rate(e["id"], h, r)
        weights[e["id"]] = CellWeight(e["credibility"], e["relevance"])
    return matrix, weights


def descriptive_total(case: dict) -> list[str]:
    matrix, _ = build(case)
    scores = matrix.get_scores()
    return sorted(scores, key=lambda h: (-scores[h], h))


def parc(case: dict) -> list[str]:
    matrix, weights = build(case)
    return descriptive_ranking(matrix, weights).order


def parc_guarded(case: dict) -> list[str]:
    matrix, weights = build(case)
    return descriptive_ranking(matrix, weights, guard_vague=True).order


SCORERS = {"descriptive_total": descriptive_total, "parc": parc, "parc_guarded": parc_guarded}


def run(corpus: list[dict]) -> dict:
    top1 = {}
    per_case = {}
    for name, scorer in SCORERS.items():
        hits = 0
        for case in corpus:
            first = scorer(case)[0]
            per_case.setdefault(case["case_id"], {})[name] = first
            hits += first == case["ground_truth"]
        top1[name] = 100.0 * hits / len(corpus) if corpus else 0.0
    advisory = all(c.get("synthetic", False) for c in corpus)
    disagreements = {k: v for k, v in per_case.items() if len(set(v.values())) > 1}
    return {"cases": len(corpus), "advisory": advisory, "top1_accuracy_pct": top1,
            "disagreements": disagreements,
            "note": ("Synthetic corpus written with the true hypothesis carrying the most ++ cells; "
                     "descriptive_total is favoured by construction. Not evidence for any rule.") if advisory else "labeled corpus"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=Path(__file__).resolve().parent / "ranking_corpus")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = run(load(args.corpus))
    text = json.dumps(report, indent=2)
    if args.out:
        args.out.write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
