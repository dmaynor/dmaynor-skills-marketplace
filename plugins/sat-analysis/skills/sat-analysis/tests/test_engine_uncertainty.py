"""ICD 203 ladder terms and likelihood/confidence sentence separation."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sat_engine.doctrine import load_catalog
from sat_engine.pipeline import assess
from sat_engine.uncertainty import (canonical_term, check_likelihood_term, check_sentence_separation,
                                    sentences_mixing_likelihood_and_confidence)
from sat_engine.validators import ValidationFailure, loads_json

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "engine"


def _fix_request() -> dict:
    return deepcopy(loads_json((FIXTURES / "full_fix_arithmetic.case.json").read_bytes())["request"])


class LadderTermTests(unittest.TestCase):
    def test_synonyms_map_to_ladder(self) -> None:
        self.assertEqual(canonical_term("probable"), "likely")
        self.assertEqual(canonical_term("Almost Certainly"), "almost certain")
        self.assertIsNone(canonical_term("moderately likely"))

    def test_off_ladder_term_rejected(self) -> None:
        with self.assertRaises(ValidationFailure) as ctx:
            check_likelihood_term({"proposition": "p", "value": 0.6, "basis": "b", "term": "quite likely"})
        self.assertEqual(ctx.exception.code, "likelihood_term_not_on_ladder")

    def test_band_mismatch_rejected_and_match_accepted(self) -> None:
        with self.assertRaises(ValidationFailure) as ctx:
            check_likelihood_term({"proposition": "p", "value": 0.9, "basis": "b", "term": "likely"})
        self.assertEqual(ctx.exception.code, "likelihood_term_band_mismatch")
        check_likelihood_term({"proposition": "p", "value": 0.7, "basis": "b", "term": "likely"})
        check_likelihood_term({"proposition": "p", "value": None, "basis": "b", "term": "unlikely"})


class SentenceSeparationTests(unittest.TestCase):
    def test_mixed_sentence_detected(self) -> None:
        mixed = "We assess the fix is likely complete with moderate confidence."
        self.assertEqual(sentences_mixing_likelihood_and_confidence(mixed), [mixed])
        separate = "We assess the fix is likely complete. Confidence is moderate given a single trial."
        self.assertEqual(sentences_mixing_likelihood_and_confidence(separate), [])

    def test_judgment_fields_checked(self) -> None:
        with self.assertRaises(ValidationFailure) as ctx:
            check_sentence_separation({"summary": "It is very likely a race, and we have high confidence in that."})
        self.assertEqual(ctx.exception.code, "likelihood_confidence_same_sentence")

    def test_pipeline_rejects_mixed_summary_and_accepts_separated(self) -> None:
        request = _fix_request()
        request["judgment"]["summary"] = "The fix is likely complete with high confidence."
        result = assess(request)
        self.assertEqual(result["status"], "invalid")
        self.assertEqual(result["diagnostics"][0]["code"], "likelihood_confidence_same_sentence")
        request["judgment"]["summary"] = "The fix is likely complete. Confidence is high."
        request["judgment"]["likelihood"] = {"proposition": "fix is complete", "value": 0.7, "basis": "trial", "term": "likely"}
        self.assertEqual(assess(request)["status"], "ok")


class CatalogAdditionsTests(unittest.TestCase):
    def test_research_rules_present_with_pinpoints(self) -> None:
        rules = {r["rule_id"]: r for r in load_catalog()["rules"]}
        self.assertEqual(rules["ICD203-LIKELIHOOD-CONFIDENCE-SENTENCE"]["section"], "D.6.e.(2)(b)")
        self.assertEqual(rules["ICD203-LIKELIHOOD-TERMS"]["section"], "D.6.e.(2)(a)")
        for rule_id in ("MANDEL-COHERENTIZE", "KM2020-PSEUDODIAGNOSTIC", "EVID-ACH-NOT-A-DEBIASER", "NATO-INFORMATION-CREDIBILITY"):
            self.assertIn(rule_id, rules)
        self.assertEqual(load_catalog()["catalog_version"], "1.1.0")


if __name__ == "__main__":
    unittest.main()
