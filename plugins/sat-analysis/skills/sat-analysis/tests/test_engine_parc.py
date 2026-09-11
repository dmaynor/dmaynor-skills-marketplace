"""Opt-in PARC descriptive ranking: disconfirmation-only, explicit weights, ties surfaced, vague guard."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sat_engine.ach import ACHMatrix
from sat_engine.parc import CellWeight, descriptive_ranking, vague_hypotheses, weighted_inconsistency


def matrix(table: dict[str, dict[str, str]], weights: dict[str, tuple[str, str]] | None = None):
    ids = sorted({h for row in table.values() for h in row})
    m = ACHMatrix(title="t")
    for h in ids:
        m.add_hypothesis(h, h)
    for e, row in table.items():
        m.add_evidence(e, e, source="s", reliability="B")
        for h, r in row.items():
            m.rate(e, h, r)
    w = {e: CellWeight(*(weights or {}).get(e, ("3", "M"))) for e in table}
    return m, w


class ParcTests(unittest.TestCase):
    def test_consistency_sum_never_decides(self) -> None:
        m, w = matrix({"E1": {"H1": "++", "H2": "+"}, "E2": {"H1": "++", "H2": "+"},
                       "E3": {"H1": "++", "H2": "+"}, "E4": {"H1": "--", "H2": "-"}})
        self.assertGreater(m.get_scores()["H1"], m.get_scores()["H2"])   # descriptive total favours H1
        self.assertEqual(descriptive_ranking(m, w).order[0], "H2")       # one weak contradiction beats one strong

    def test_weights_are_explicit_and_unjudged_flagged(self) -> None:
        m, w = matrix({"E1": {"H1": "--", "H2": "N"}, "E2": {"H1": "N", "H2": "--"}}, {"E1": ("1", "H"), "E2": ("6", "H")})
        scores, unjudged = weighted_inconsistency(m, w)
        self.assertAlmostEqual(scores["H1"], -4.0)
        self.assertAlmostEqual(scores["H2"], -2 * (2 ** 0.5))
        self.assertEqual(unjudged, ["E2"])
        with self.assertRaises(ValueError):
            weighted_inconsistency(m, {"E1": w["E1"]})

    def test_vague_hypothesis_ranks_first_unguarded_and_is_demoted_guarded(self) -> None:
        m, w = matrix({"E1": {"H1": "++", "H2": "+"}, "E2": {"H1": "++", "H2": "+"},
                       "E3": {"H1": "++", "H2": "+"}, "E4": {"H1": "-", "H2": "+"}})
        self.assertEqual(vague_hypotheses(m), ["H2"])
        self.assertEqual(descriptive_ranking(m, w).order, ["H2", "H1"])
        self.assertEqual(descriptive_ranking(m, w, guard_vague=True).order, ["H1", "H2"])

    def test_full_tie_surfaces_needs_evidence(self) -> None:
        m, w = matrix({"E1": {"H1": "+", "H2": "+"}, "E2": {"H1": "-", "H2": "-"}})
        ranking = descriptive_ranking(m, w)
        self.assertTrue(ranking.heuer_tie_at_top)
        self.assertEqual(ranking.needs_discriminating_evidence, ["H1", "H2"])


if __name__ == "__main__":
    unittest.main()
