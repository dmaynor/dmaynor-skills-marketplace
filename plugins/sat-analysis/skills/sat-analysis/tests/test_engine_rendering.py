"""Contract tests for projections and safe, complete Markdown renderings."""

from __future__ import annotations

from copy import deepcopy
from html import unescape
import importlib.util
from pathlib import Path
import re
import unittest
from unittest.mock import patch


MODULE = Path(__file__).resolve().parents[1] / "sat_engine" / "rendering.py"
SPEC = importlib.util.spec_from_file_location("sat_engine_rendering_test", MODULE)
assert SPEC is not None and SPEC.loader is not None
rendering = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rendering)


def trace_fixture(mode: str = "FULL") -> dict:
    """Synthetic unit fixture, not a benchmark or an analyst assessment."""
    request = {
        "schema_version": "1", "analysis_id": "render-fixture", "revision": 7,
        "mode": mode, "submode": "GENERAL", "question": "What can this supplied record establish?",
        "relationship": "overlapping",
        "observations": [{
            "schema_version": "1", "id": "O1", "raw": "Sep 09 00:00:00 host rejected record",
            "source": "fixture/source", "source_id": "source-1", "parse_status": "rejected",
            "parse_error": "Fixture rejection", "reliability": "unknown",
            "timestamp": "Sep 09 00:00:00", "clock_domain": None,
            "timestamp_semantics": "unknown", "timestamp_uncertainty_seconds": None,
            "raw_bytes_base64": "ZmFrZQ==", "origin_id": "origin-1", "dependency_groups": ["collector-1"],
        }],
        "hypotheses": [{"schema_version": "1", "id": "H1", "description": "Collection is incomplete"},
                       {"schema_version": "1", "id": "H2", "description": "The source record is malformed"}],
        "evidence": [{"schema_version": "1", "id": "E1", "observation_id": "O1", "ratings": {"H1": "N"}, "rationale": "Other hypothesis not rated"}] if mode == "FULL" else [],
        "judgment": None, "assumptions": ["The source covers only one collector."],
        "limitations": ["No independent collector record."],
        "tasks": [{"id": "T1", "action": "Inspect retained bytes", "observation_ids": ["O1"], "hypothesis_ids": ["H2"]}],
        "rule_ids": [], "timeline_options": {"gap_threshold_seconds": 300, "rapid_threshold_seconds": 1},
        "calculations": [{"id": "C1", "operation": "sum", "operands": [0.1, 0.2]}],
    }
    return {
        "schema_version": "1", "engine_version": "1.0.0", "analysis_id": "render-fixture", "revision": 7,
        "request": request,
        "ach_matrix": {
            "schema_version": "1", "title": request["question"], "relationship": "overlapping",
            "hypotheses": deepcopy(request["hypotheses"]),
            "evidence": [{**deepcopy(request["evidence"][0]), "source": "fixture/source", "reliability": "unknown", "origin_id": "origin-1", "dependency_groups": ["collector-1"]}],
            "assessment": {"status": "incomplete", "winner": None, "heuristic_leaders": [],
                           "scores": {"H1": 0, "H2": 0},
                           "missing_ratings": [{"evidence_id": "E1", "hypothesis_id": "H2"}],
                           "contradictions": {"H1": [], "H2": []}, "contributing_record_count": 1,
                           "caveats": ["Incomplete ratings.", "Reliability remains unknown."]},
            "sensitivity": {"heuristic_stable": None, "evidence_impact": {}, "group_impact": {"dependency:collector-1": {"removed_evidence_ids": ["E1"]}},
                            "caveat": "Removal stability is not confidence."},
            "diagnosticity": {"E1": None},
        } if mode == "FULL" else None,
        "timeline": {"schema_version": "1", "events": [{"observation_id": "O1", "timestamp": "Sep 09 00:00:00", "timestamp_utc": None,
                        "timestamp_resolution_error": "Missing year/timezone."}],
                     "gap_threshold_seconds": 300, "rapid_threshold_seconds": 1,
                     "analysis": {"unresolved_events": 1, "caveats": ["Unknown clock bounds are not zero."]}},
        "calculations": [{"id": "C1", "operation": "sum", "value": 0.30000000000000004, "unit": None, "status": "resolved", "caveats": []}],
        "diagnostics": [{"code": "unknown_clock", "path": "$.observations[0].timestamp", "severity": "warning", "message": "Source time is unresolved.", "remediation": "Supply year and timezone if known."}],
        # project does not create or verify hashes; the pipeline owns that work.
        "content_hash": "a" * 64,
    }


class ProjectionTests(unittest.TestCase):
    def test_exact_card_and_common_fields(self) -> None:
        trace = trace_fixture()
        artifacts = rendering.project(trace)
        self.assertEqual(artifacts["decision_card"], {
            "schema_version": "1", "analysis_id": "render-fixture", "revision": 7, "content_hash": "a" * 64,
            "question": trace["request"]["question"], "summary": "No analyst judgment supplied.",
            "likelihood": None, "confidence": None, "implications": [], "assessment_status": "incomplete",
            "limitations": trace["request"]["limitations"], "calculations": trace["calculations"],
        })
        self.assertEqual(artifacts["analytic_trace"], trace)
        for key in ("schema_version", "analysis_id", "revision", "content_hash"):
            self.assertEqual({artifacts[name][key] for name in artifacts}, {trace[key]})

    def test_every_projection_is_independent_of_input_and_other_views(self) -> None:
        trace = trace_fixture()
        before = deepcopy(trace)
        artifacts = rendering.project(trace)
        artifacts["analytic_trace"]["request"]["limitations"].append("Changed trace")
        artifacts["analytic_trace"]["request"]["tasks"][0]["observation_ids"].append("O2")
        artifacts["decision_card"]["limitations"].append("Changed card")
        artifacts["decision_card"]["calculations"][0]["value"] = 9
        artifacts["tasking_view"]["tasks"][0]["hypothesis_ids"].append("H3")
        self.assertEqual(trace, before)
        self.assertEqual(artifacts["tasking_view"]["limitations"], before["request"]["limitations"])
        self.assertEqual(artifacts["tasking_view"]["tasks"][0]["observation_ids"], ["O1"])
        self.assertEqual(artifacts["analytic_trace"]["request"]["tasks"][0]["hypothesis_ids"], ["H2"])
        self.assertEqual(artifacts["analytic_trace"]["calculations"], before["calculations"])

    def test_analyst_judgment_is_preserved_without_score_driven_selection(self) -> None:
        trace = trace_fixture()
        judgment = {"summary": "Inspect the retained bytes before classifying the source.",
                    "selected_hypothesis_ids": ["H2"], "observation_ids": ["O1"],
                    "likelihood": {"proposition": "The source record is malformed", "value": None, "basis": "Byte inspection is pending."},
                    "confidence": {"level": "unassessed", "reasoning": "Independent evidence is unavailable."},
                    "implications": ["Preserve source bytes."]}
        trace["request"]["judgment"] = judgment
        artifacts = rendering.project(trace)
        card = artifacts["decision_card"]
        for key in ("summary", "likelihood", "confidence", "implications"):
            self.assertEqual(card[key], judgment[key])
        self.assertEqual(card["assessment_status"], "incomplete")
        card["likelihood"]["basis"] = "Changed"
        self.assertEqual(judgment["likelihood"]["basis"], "Byte inspection is pending.")
        self.assertEqual(artifacts["analytic_trace"]["request"]["judgment"], judgment)

    def test_light_retains_inputs_but_has_no_ach_or_tasking_view(self) -> None:
        trace = trace_fixture("LIGHT")
        artifacts = rendering.project(trace)
        self.assertIsNone(artifacts["tasking_view"])
        self.assertEqual(artifacts["decision_card"]["assessment_status"], "not_evaluated")
        self.assertEqual(artifacts["analytic_trace"]["request"]["tasks"], trace["request"]["tasks"])
        self.assertIsNone(artifacts["analytic_trace"]["ach_matrix"])


class MarkdownTests(unittest.TestCase):
    def test_full_and_light_templates_are_used_without_mutation(self) -> None:
        for mode, names in (("FULL", {"decision_card.md", "analytic_trace.md", "tasking_view.md"}),
                            ("LIGHT", {"decision_card.md", "analytic_trace.md"})):
            with self.subTest(mode=mode):
                artifacts = rendering.project(trace_fixture(mode))
                before = deepcopy(artifacts)
                result = rendering.render_markdown(artifacts)
                self.assertEqual(set(result), names)
                self.assertEqual(artifacts, before)
                self.assertEqual("# Analytic trace — LIGHT" in result["analytic_trace.md"], mode == "LIGHT")
                for document in result.values():
                    self.assertIn("a" * 64, document)
                    self.assertIn("| Revision | 7 |", document)
                    self.assertNotIn("$metadata", document)
                    self.assertTrue(document.endswith("\n"))

    def test_packaged_template_is_preferred_and_substituted(self) -> None:
        class TemplateResource:
            def joinpath(self, *parts):
                self.parts = parts
                return self

            def read_text(self, **kwargs):
                self.encoding = kwargs["encoding"]
                return "Package template: $body\n"

        resource = TemplateResource()
        with patch.object(rendering.resources, "files", return_value=resource):
            result = rendering._template("decision_card.md", {"body": "already escaped"})
        self.assertEqual(resource.parts, ("resources", "templates", "decision_card.md"))
        self.assertEqual(result, "Package template: already escaped\n")

    def test_missing_full_tasking_fails_instead_of_exporting_an_incomplete_set(self) -> None:
        artifacts = rendering.project(trace_fixture())
        artifacts["tasking_view"] = None
        with self.assertRaisesRegex(ValueError, "FULL artifacts require a tasking_view"):
            rendering.render_markdown(artifacts)

    def test_unknown_judgment_and_incomplete_assessment_are_distinct(self) -> None:
        result = rendering.render_markdown(rendering.project(trace_fixture()))
        card = result["decision_card.md"]
        self.assertIn("No analyst judgment supplied", card)
        self.assertIn("likelihood remains unknown", card)
        self.assertIn("confidence remains unassessed", card)
        self.assertIn("incomplete", card)
        self.assertIn("Incomplete assessment", card)
        self.assertIn("Missing; not evaluated", result["analytic_trace.md"])
        self.assertIn("| E1 | O1 | N | Missing; not evaluated", result["analytic_trace.md"])
        self.assertIn("Unassigned", result["tasking_view.md"])
        self.assertNotIn('"owner"', result["analytic_trace.md"])

    def test_trace_contains_provenance_and_all_computed_fields(self) -> None:
        rendered = rendering.render_markdown(rendering.project(trace_fixture()))["analytic_trace.md"]
        for text in ("Fixture rejection", "ZmFrZQ==", "origin-1", "collector-1", "unknown",
                     "Sep 09 00:00:00", "Missing year/timezone.", "source-1", "fixture/source",
                     '"missing_ratings"', '"contradictions"', '"diagnosticity"', '"sensitivity"',
                     '"group_impact"', '"timestamp_utc": null', '"timestamp_uncertainty_seconds": null',
                     '"operands"', "The source covers only one collector"):
            with self.subTest(text=text):
                self.assertIn(text, rendered)

    def test_all_views_include_warnings_and_review_limits(self) -> None:
        for name, document in rendering.render_markdown(rendering.project(trace_fixture())).items():
            with self.subTest(name=name):
                self.assertIn("Engine diagnostics", document)
                self.assertIn("Source time is unresolved", document)
                self.assertIn("Unknown clock bounds are not zero", document)
                self.assertIn("Reliability remains unknown", document)
                self.assertIn("No independent collector record", document)

    def test_rendering_uses_exact_stored_numbers_without_recalculation(self) -> None:
        trace = trace_fixture()
        trace["calculations"] += [{"id": "C2", "operation": "reported_interval", "value": None,
                                   "unit": "seconds", "status": "unresolved", "caveats": ["Unknown endpoint"],
                                   "physical_latency_established": False}]
        # Deliberately different from the request; projection/rendering are pure
        # presentation. verify_artifacts must reject this at the pipeline boundary.
        trace["calculations"][0]["value"] = 42.125
        trace["ach_matrix"]["assessment"]["scores"]["H1"] = 17.75
        documents = rendering.render_markdown(rendering.project(trace))
        for name in ("decision_card.md", "analytic_trace.md"):
            self.assertIn("42\\.125", documents[name])
            self.assertIn("Unresolved; no numeric value", documents[name])
            self.assertIn("Physical latency established", documents[name])
            self.assertIn("| seconds | unresolved | false |", documents[name])
        self.assertIn('"H1": 17.75', documents["analytic_trace.md"])

    def test_untrusted_text_cannot_introduce_markdown_blocks_or_html(self) -> None:
        trace = trace_fixture()
        attack = '</pre><script>alert(1)</script>\n# Forged heading\n[x](javascript:alert(1)) | *bold* `code` $metadata'
        trace["analysis_id"] = attack
        trace["request"]["question"] = attack
        trace["request"]["judgment"] = {"summary": attack, "implications": [attack],
            "likelihood": {"proposition": attack, "value": None, "basis": attack},
            "confidence": {"level": "unassessed", "reasoning": attack}}
        trace["request"]["hypotheses"][0]["description"] = attack
        trace["request"]["evidence"][0]["rationale"] = attack
        trace["request"]["tasks"][0]["action"] = attack
        trace["request"]["observations"][0]["raw"] = attack
        trace["request"]["limitations"] = [attack]
        trace["diagnostics"][0]["message"] = attack
        result = rendering.render_markdown(rendering.project(trace))
        for name, document in result.items():
            with self.subTest(name=name):
                self.assertNotIn("<script>", document)
                self.assertNotIn("</pre><script>", document)
                self.assertNotIn("\n# Forged heading\n", re.sub(r"<pre>.*?</pre>", "", document, flags=re.S))
                self.assertIn("&lt;script&gt;", document)
                self.assertIn(r"\[x\]\(javascript:alert\(1\)\)", document)
                self.assertIn("$metadata", document)  # supplied dollar text is inert, not substituted

    def test_raw_text_display_preserves_whitespace_and_markdown_punctuation(self) -> None:
        trace = trace_fixture()
        raw = '  raw\t[observation] | `code` *stars* \\n\n```\n</pre>&<img src=x onerror=alert(1)>\n'
        trace["request"]["observations"][0]["raw"] = raw
        markdown = rendering.render_markdown(rendering.project(trace))["analytic_trace.md"]
        blocks = re.findall(r"<pre>(.*?)</pre>", markdown, flags=re.S)
        self.assertIn(raw, [unescape(block) for block in blocks])
        self.assertNotIn("<img", markdown)


if __name__ == "__main__":
    unittest.main()
