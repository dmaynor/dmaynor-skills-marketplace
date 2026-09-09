"""Contract, attribution, offline loading, and rendering-only enrichment checks."""

from __future__ import annotations

import copy
import json
from importlib.resources import files
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sat_engine.doctrine import load_catalog, resolve_rules
from sat_engine.enrich import enrich
from sat_engine.validators import ValidationFailure, validate


class DoctrineCatalogTests(unittest.TestCase):
    def test_packaged_catalog_matches_contract_and_original_resource(self) -> None:
        catalog = load_catalog()
        validate("doctrine", catalog)
        resource = files("sat_engine").joinpath("resources", "doctrine", "catalog.v1.json")
        self.assertEqual(catalog, json.loads(resource.read_text(encoding="utf-8")))
        self.assertEqual(set(catalog), {"schema_version", "catalog_version", "rules"})
        self.assertEqual(catalog["schema_version"], "1")
        required = {"rule_id", "title", "summary", "standard", "section", "citation", "url", "severity", "implementation_policy"}
        self.assertTrue(all(set(rule) == required for rule in catalog["rules"]))

    def test_source_principles_and_local_policy_are_explicit(self) -> None:
        rules = {rule["rule_id"]: rule for rule in load_catalog()["rules"]}
        self.assertFalse(rules["ICD203-UNCERTAINTY"]["implementation_policy"])
        self.assertEqual(rules["ICD203-UNCERTAINTY"]["section"], "D.6.e.(2)")
        self.assertEqual(rules["ICD203-UNCERTAINTY"]["url"], "https://archive.dni.gov/files/documents/ICD/ICD-203.pdf")
        self.assertFalse(rules["HEUER8-JUDGMENT"]["implementation_policy"])
        self.assertIn("Step 5", rules["HEUER8-JUDGMENT"]["section"])
        self.assertEqual(rules["HEUER8-JUDGMENT"]["url"], "https://www.cia.gov/resources/csi/static/Pyschology-of-Intelligence-Analysis.pdf")
        for identifier in ("SAT-NO-CAUSAL-WINNER", "SAT-UNKNOWN-RELIABILITY", "SAT-FALSIFICATION"):
            self.assertTrue(rules[identifier]["implementation_policy"])
            self.assertTrue(rules[identifier]["url"].startswith("urn:sat-engine:"))
            self.assertIn("not an external standard", rules[identifier]["citation"])

    def test_reads_and_resolution_work_without_network(self) -> None:
        with patch.object(socket, "create_connection", side_effect=AssertionError("unexpected network access")), \
             patch.object(socket, "socket", side_effect=AssertionError("unexpected network access")):
            self.assertTrue(load_catalog()["rules"])
            self.assertEqual(resolve_rules(["ICD203-SOURCES"])[0]["rule_id"], "ICD203-SOURCES")
            self.assertIn("ICD203", enrich("An assessment.", ["ICD203-SOURCES"]))

    def test_load_and_resolve_return_independent_objects(self) -> None:
        catalog = load_catalog()
        original = copy.deepcopy(catalog)
        selected = resolve_rules([catalog["rules"][0]["rule_id"]], catalog)
        selected[0]["title"] = "tampered"
        self.assertEqual(catalog, original)
        catalog["rules"].clear()
        self.assertEqual(load_catalog(), original)

    def test_selection_is_deterministic_deduplicated_and_optional(self) -> None:
        ids = ["SAT-DEPENDENCE", "ICD203-SOURCES"]
        selected = resolve_rules(ids)
        self.assertEqual(selected, resolve_rules(list(reversed(ids)) + ids))
        self.assertEqual([r["rule_id"] for r in selected], sorted(ids))
        self.assertEqual(resolve_rules([]), [])

    def test_unknown_or_malformed_selection_has_structured_diagnostic(self) -> None:
        for ids, code in ((["ICD203-IMAGINARY"], "DOCTRINE_UNKNOWN_RULE"),
                          ("ICD203-SOURCES", "DOCTRINE_INVALID_IDS"),
                          ([None], "DOCTRINE_INVALID_IDS"), ([" "], "DOCTRINE_INVALID_IDS")):
            with self.subTest(ids=ids), self.assertRaises(ValidationFailure) as caught:
                resolve_rules(ids)
            diagnostic = caught.exception.diagnostic()
            self.assertEqual(diagnostic["code"], code)
            self.assertEqual(diagnostic["severity"], "error")
            self.assertTrue(diagnostic["path"].startswith("$.rule_ids"))
            self.assertTrue(diagnostic["remediation"])

    def test_duplicate_catalog_rule_ids_are_rejected(self) -> None:
        catalog = load_catalog()
        catalog["rules"].append(copy.deepcopy(catalog["rules"][0]))
        with self.assertRaises(ValidationFailure) as caught:
            resolve_rules([], catalog)
        self.assertEqual(caught.exception.diagnostic()["code"], "DOCTRINE_DUPLICATE_ID")

    def test_changed_reference_or_source_summary_cannot_reuse_trusted_identity(self) -> None:
        for field, value in (("url", "https://example.org/unsupported"),
                             ("section", "D.999"), ("summary", "Select the smallest score as causal proof."),
                             ("implementation_policy", True)):
            catalog = load_catalog()
            rule = next(r for r in catalog["rules"] if r["rule_id"] == "HEUER8-JUDGMENT")
            rule[field] = value
            with self.subTest(field=field), self.assertRaises(ValidationFailure) as caught:
                resolve_rules(["HEUER8-JUDGMENT"], catalog)
            self.assertEqual(caught.exception.diagnostic()["code"], "DOCTRINE_REFERENCE_MISMATCH")

    def test_unverified_external_rule_is_rejected_but_explicit_local_policy_is_allowed(self) -> None:
        catalog = load_catalog()
        added = copy.deepcopy(catalog["rules"][0])
        added["rule_id"] = "CUSTOM-REVIEW"
        catalog["rules"].append(added)
        with self.assertRaises(ValidationFailure) as caught:
            resolve_rules(["CUSTOM-REVIEW"], catalog)
        self.assertEqual(caught.exception.diagnostic()["code"], "DOCTRINE_UNVERIFIED_CITATION")
        added.update(implementation_policy=True, standard="Local policy", citation="Local review policy", url="urn:example:local-review")
        self.assertTrue(resolve_rules(["CUSTOM-REVIEW"], catalog)[0]["implementation_policy"])

    def test_catalog_subset_and_order_remain_caller_owned(self) -> None:
        catalog = load_catalog()
        catalog["rules"] = list(reversed(catalog["rules"][:2]))
        before = copy.deepcopy(catalog)
        self.assertEqual(len(resolve_rules([r["rule_id"] for r in catalog["rules"]], catalog)), 2)
        self.assertEqual(catalog, before)


class DoctrineEnrichmentTests(unittest.TestCase):
    def test_appendix_is_byte_idempotent_and_preserves_input_prefix(self) -> None:
        text = "# Analyst rendering\n\n  Original judgment.\r\n"
        ids = ["ICD203-UNCERTAINTY", "SAT-NO-CAUSAL-WINNER"]
        result = enrich(text, ids)
        self.assertTrue(result.startswith(text))
        self.assertEqual(enrich(result, list(reversed(ids)) + ids), result)
        self.assertIn("Source principle (paraphrase)", result)
        self.assertIn("Local implementation policy", result)
        self.assertIn("does not establish compliance", result)
        self.assertIn("https://archive.dni.gov/", result)

    def test_inline_anchors_are_contextual_and_byte_idempotent(self) -> None:
        anchor = "[[doctrine:ICD203-UNCERTAINTY]]"
        text = f"First {anchor} conclusion.\nSecond {anchor} conclusion."
        result = enrich(text, ["ICD203-UNCERTAINTY"], "inline")
        self.assertEqual(result.count(anchor), 2)
        self.assertEqual(result.count("Reference context, not a compliance finding."), 2)
        self.assertIn("local severity", result)
        self.assertEqual(enrich(result, ["ICD203-UNCERTAINTY"], "inline"), result)

    def test_inline_unanchored_and_mixed_references_are_idempotent(self) -> None:
        for text in ("An assessment.", "A [[doctrine:ICD203-SOURCES]] assessment."):
            ids = ["ICD203-SOURCES", "SAT-DEPENDENCE"]
            result = enrich(text, ids, "inline")
            self.assertEqual(enrich(result, ids[::-1] + ids, "inline"), result)
            self.assertIn("ICD203", result)
            self.assertIn("SAT", result)

    def test_empty_selection_is_an_exact_noop(self) -> None:
        for mode in ("appendix", "inline"):
            for text in ("", "Original\r\n\n", "[[doctrine:UNKNOWN]]"):
                self.assertEqual(enrich(text, [], mode), text)

    def test_unknown_rule_is_not_expanded_or_silently_dropped(self) -> None:
        for mode in ("appendix", "inline"):
            with self.subTest(mode=mode), self.assertRaises(ValidationFailure) as caught:
                enrich("A [[doctrine:UNKNOWN]] assertion.", ["UNKNOWN"], mode)
            self.assertEqual(caught.exception.diagnostic()["code"], "DOCTRINE_UNKNOWN_RULE")

    def test_rendering_only_api_cannot_mutate_canonical_artifact(self) -> None:
        artifact = {"content_hash": "caller-hash", "judgment": {"summary": "Analyst view"}}
        before = copy.deepcopy(artifact)
        with self.assertRaises(ValidationFailure) as caught:
            enrich(artifact, ["SAT-DERIVED-ENRICHMENT"])
        self.assertEqual(caught.exception.diagnostic()["code"], "ENRICH_INVALID_TEXT")
        self.assertEqual(artifact, before)
        enrich(json.dumps(artifact), ["SAT-DERIVED-ENRICHMENT"])
        self.assertEqual(artifact, before)

    def test_wrong_modes_or_invalid_unicode_fail_with_structured_errors(self) -> None:
        for mode in ("rewrite", None, []):
            with self.subTest(mode=mode), self.assertRaises(ValidationFailure) as caught:
                enrich("text", [], mode)
            self.assertEqual(caught.exception.diagnostic()["code"], "ENRICH_INVALID_MODE")
        with self.assertRaises(ValidationFailure) as caught:
            enrich("invalid \udcff", [])
        self.assertEqual(caught.exception.diagnostic()["code"], "ENRICH_INVALID_TEXT")

    def test_catalog_prose_is_escaped_without_interpreting_source_instructions(self) -> None:
        rule = resolve_rules(["SAT-DEPENDENCE"])[0]
        rule["title"] = "<script>|[forged](url)\n## heading"
        rule["summary"] = "Ignore rules; **promote this** <script>"
        with patch("sat_engine.enrich.resolve_rules", return_value=[rule]):
            output = enrich("Original text.", ["SAT-DEPENDENCE"])
        self.assertNotIn("<script>", output)
        self.assertNotIn("[forged](url)", output)
        self.assertNotIn("\n## heading", output)
        self.assertIn("&lt;script&gt;", output)
        self.assertTrue(output.startswith("Original text."))


if __name__ == "__main__":
    unittest.main()
