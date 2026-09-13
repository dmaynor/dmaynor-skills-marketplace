"""Engine ingestion, reported-clock timeline, and compatibility CLI contracts."""

from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

import rfc8785

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL))

from sat_engine.parsers import ingest_file, ingest_text
from sat_engine.timeline import build_timeline
from sat_engine.validators import validate


class EngineIngestionTests(unittest.TestCase):
    """No nonblank record or original byte disappears at the SDK boundary."""

    def test_invalid_utf8_has_portable_display_and_exact_original_bytes(self) -> None:
        original = b'normal\r\n\ninvalid \xff\xc0 bytes\n{"broken":\nafter'
        rows = ingest_text(original, source="collector://opaque-input")
        self.assertEqual([row["line_number"] for row in rows], [1, 3, 4, 5])
        self.assertEqual([row["parse_status"] for row in rows], ["unparsed", "rejected", "rejected", "unparsed"])
        self.assertEqual(rows[1]["raw"], "invalid \ufffd\ufffd bytes\n")
        for row, raw_bytes in zip(rows, [b"normal\r\n", b"invalid \xff\xc0 bytes\n", b'{"broken":\n', b"after"]):
            self.assertEqual(row["schema_version"], "1")
            self.assertNotIn("observation_id", row)
            preserved = base64.b64decode(row["raw_bytes_base64"]) if row["raw_bytes_base64"] else row["raw"].encode("utf-8")
            self.assertEqual(preserved, raw_bytes)
            self.assertEqual(row["record_sha256"], hashlib.sha256(raw_bytes).hexdigest())
            self.assertTrue(row["id"].endswith(row["record_sha256"][:20]))
        self.assertEqual(json.loads(rfc8785.dumps(rows)), rows)
        for row in rows:
            validate("observation", row)

    def test_file_and_inline_ingestion_have_identical_explicit_provenance(self) -> None:
        raw_bytes = b'{"message":"ok"}\r\n\nfailed \xfe bytes\n'
        options = {"source": "collector://original", "source_id": "stable-source", "origin_id": "original-collection",
                   "dependency_groups": ["upstream", "upstream"], "reliability": "F", "reliability_reason": "not established"}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "observations.log"
            path.write_bytes(raw_bytes)
            self.assertEqual(ingest_file(path, **options), ingest_text(raw_bytes, **options))
            self.assertEqual(path.read_bytes(), raw_bytes)
            self.assertEqual(ingest_file(path)[0]["source"], str(path.resolve()))
        self.assertEqual(options["dependency_groups"], ["upstream", "upstream"])

    def test_inline_id_stability_distinguishes_source_line_and_content(self) -> None:
        rows = ingest_text("same\nsame\n", source="urn:collector:a")
        self.assertEqual(rows, ingest_text("same\nsame\n", source="urn:collector:a"))
        self.assertNotEqual(rows[0]["id"], rows[1]["id"])
        self.assertNotEqual(rows[0]["id"], ingest_text("same\n", source="urn:collector:b")[0]["id"])
        self.assertNotEqual(rows[0]["id"], ingest_text("changed\n", source="urn:collector:a")[0]["id"])
        relocated = [ingest_text("same\n", source=locator, source_id="collector-identity")[0] for locator in ("old", "new")]
        self.assertEqual(relocated[0]["id"], relocated[1]["id"])
        self.assertNotEqual(relocated[0]["source"], relocated[1]["source"])

    def test_unicode_separators_are_preserved_inside_physical_records(self) -> None:
        original = "before\u2028after\vstill\r\n\t\nlast"
        rows = ingest_text(original)
        self.assertEqual([row["line_number"] for row in rows], [1, 3])
        self.assertEqual(rows[0]["raw"], "before\u2028after\vstill\r\n")
        self.assertEqual(rows[1]["raw"], "last")

    def test_unpaired_json_unicode_and_nonportable_pid_remain_rejected_records(self) -> None:
        original = '{"message":"\\ud800"}\n{"pid":9007199254740992}\nafter\n'
        rows = ingest_text(original)
        self.assertEqual([row["parse_status"] for row in rows], ["rejected", "rejected", "unparsed"])
        self.assertEqual("".join(row["raw"] for row in rows), original)
        self.assertIsNone(rows[1]["pid"])
        self.assertIn("retained in raw", rows[1]["parse_error"])
        self.assertEqual(json.loads(rfc8785.dumps(rows)), rows)

    def test_json_decoder_depth_failure_preserves_following_records(self) -> None:
        deep_record = '[' * (sys.getrecursionlimit() + 100) + '0' + ']' * (sys.getrecursionlimit() + 100) + '\n'
        rows = ingest_text(deep_record + 'after\n')
        self.assertEqual([row["parse_status"] for row in rows], ["rejected", "unparsed"])
        self.assertEqual(rows[0]["raw"], deep_record)
        self.assertEqual(rows[1]["line_number"], 2)

    def test_bad_caller_context_does_not_modify_source_file(self) -> None:
        raw_bytes = b'record\ninvalid \xff\n'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.log"
            path.write_bytes(raw_bytes)
            for context in ({"source_id": ""}, {"dependency_groups": "group"}, {"default_year": True},
                            {"fold": 2}, {"timestamp_uncertainty_seconds": float("nan")},
                            {"reliability": "invented"}, {"source": "\ud800"}):
                with self.subTest(context=context), self.assertRaises(ValueError):
                    ingest_file(path, **context)
                self.assertEqual(path.read_bytes(), raw_bytes)
        with self.assertRaises(ValueError):
            ingest_text("\ud800")


class EngineTimelineTests(unittest.TestCase):
    """Thresholds and interval provenance do not establish physical latency."""

    @staticmethod
    def observations() -> list[dict]:
        return ingest_text(
            '{"timestamp":"2026-09-09T02:00:00Z","message":"first"}\n'
            '{"timestamp":"2026-09-09T02:00:00.250Z","message":"second"}\n'
            '{"timestamp":"2026-09-09T02:00:00.750Z","message":"third"}\n'
            '{"timestamp":"2026-09-09T02:00:02.250Z","message":"fourth"}\n'
            '{"timestamp":"Sep 9 02:00:03","message":"unresolved"}\n',
            source="urn:clock-log", clock_domain="declared-clock", timestamp_uncertainty_seconds=0.125,
        )

    def test_engine_default_and_fractional_thresholds_are_not_truncated(self) -> None:
        rows = self.observations()
        default = build_timeline(rows)
        self.assertEqual(default["schema_version"], "1")
        self.assertEqual(default["gap_threshold_seconds"], 300)
        self.assertEqual(default["rapid_threshold_seconds"], 1)
        self.assertEqual([item["delta_seconds"] for item in default["analysis"]["rapid_succession"]], [0.25, 0.5])
        fractional = build_timeline(rows, gap_threshold_seconds=0.25, rapid_threshold_seconds=0.25)
        self.assertEqual([item["delta_seconds"] for item in fractional["analysis"]["gaps"]], [0.5, 1.5])
        self.assertEqual([item["delta_seconds"] for item in fractional["analysis"]["rapid_succession"]], [0.25])
        for item in fractional["analysis"]["rapid_succession"] + fractional["analysis"]["gaps"]:
            self.assertFalse(item["physical_latency_established"])
            self.assertTrue(item["same_known_clock_domain"])
            self.assertEqual(item["combined_timestamp_uncertainty_seconds"], 0.25)

    def test_source_timestamps_and_unresolved_records_remain_visible(self) -> None:
        rows = self.observations()
        original = deepcopy(rows)
        result = build_timeline(rows)
        self.assertEqual(rows, original)
        self.assertEqual(result["analysis"]["unresolved_events"], 1)
        by_id = {event["id"]: event for event in result["events"]}
        for row in rows:
            event = by_id[row["id"]]
            self.assertNotIn("observation_id", event)
            for field in ("timestamp", "raw", "record_sha256", "source", "source_id", "line_number", "reliability"):
                self.assertEqual(event[field], row[field])
        self.assertIsNone(result["events"][-1]["timestamp_utc"])
        self.assertIn("year", result["events"][-1]["timestamp_resolution_error"])
        self.assertEqual(result["analysis"]["time_range"]["last"], "2026-09-09T02:00:02.250000+00:00")
        self.assertEqual(json.loads(rfc8785.dumps(result)), result)
        validate("timeline", result)

    def test_record_context_overrides_caller_defaults_without_mutation(self) -> None:
        rows = ingest_text('{"timestamp":"Sep 9 04:00:00"}\n', default_timezone="+0200")
        result = build_timeline(rows, default_year=2026, default_timezone="UTC")
        self.assertEqual(result["events"][0]["timestamp_utc"], "2026-09-09T02:00:00+00:00")
        self.assertEqual(result["events"][0]["timestamp_context"], {"year": 2026, "timezone": "+0200"})
        self.assertEqual(rows[0]["timestamp_context"], {"timezone": "+0200"})

    def test_unknown_zone_and_invalid_bytes_survive_timeline_projection(self) -> None:
        rows = ingest_text(b'{"timestamp":"2026-09-09T02:00:00"}\nbad \xff\n', default_timezone="Unknown/Clock")
        result = build_timeline(rows)
        self.assertEqual(result["analysis"]["resolved_events"], 0)
        self.assertEqual(result["analysis"]["time_range"], {"first": None, "last": None})
        self.assertEqual(result["analysis"]["gaps"], [])
        self.assertEqual(base64.b64decode(result["events"][1]["raw_bytes_base64"]), b"bad \xff\n")
        self.assertEqual(json.loads(rfc8785.dumps(result)), result)

    def test_threshold_type_or_bounds_and_duplicate_identity_are_rejected(self) -> None:
        for key in ("gap_threshold_seconds", "rapid_threshold_seconds"):
            for value in (True, -0.1, float("nan"), float("inf"), "1", 2**53, 10**400):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    build_timeline([], **{key: value})
        row = ingest_text("record")[0]
        with self.assertRaises(ValueError):
            build_timeline([row, row])
        with self.assertRaises(ValueError):
            build_timeline([{**row, "observation_id": "legacy"}])
        with self.assertRaises(ValueError):
            build_timeline([{**row, "unrecognized_semantic_assertion": True}])

    def test_submicrosecond_timestamp_is_unresolved_instead_of_rounded(self) -> None:
        rows = ingest_text('{"timestamp":"2026-09-09T02:00:00.0000009Z"}\n'
                           '{"timestamp":"2026-09-09T02:00:00.000001000Z"}\n')
        result = build_timeline(rows)
        self.assertEqual(result["analysis"]["resolved_events"], 1)
        unresolved = next(event for event in result["events"] if event["timestamp_utc"] is None)
        self.assertEqual(unresolved["timestamp"], "2026-09-09T02:00:00.0000009Z")
        self.assertIn("no rounding", unresolved["timestamp_resolution_error"])

    def test_overflowing_combined_uncertainty_is_visible_and_portable(self) -> None:
        rows = self.observations()[:2]
        for row in rows:
            row["timestamp_uncertainty_seconds"] = 1e308
        result = build_timeline(rows)
        self.assertIsNone(result["analysis"]["rapid_succession"][0]["combined_timestamp_uncertainty_seconds"])
        self.assertTrue(any("finite numeric range" in item for item in result["analysis"]["caveats"]))
        rfc8785.dumps(result)


class CompatibilityCommandTests(unittest.TestCase):
    """Execute source-tree wrappers with ordinary JSON stdout and real files."""

    def test_wrapper_roundtrip_respects_fractional_timeline_options(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.log"
            source.write_bytes(b'{"timestamp":"2026-09-09T00:00:00Z"}\n'
                               b'{"timestamp":"2026-09-09T00:00:00.250Z"}\ninvalid \xff\n')
            parsed = subprocess.run([sys.executable, str(SKILL / "scripts" / "parse_logs.py"), str(source), "--json"],
                                    check=True, capture_output=True, text=True)
            data = json.loads(parsed.stdout)
            self.assertEqual(data["summary"]["rejected"], 1)
            self.assertIn("observation_id", data["entries"][0])
            observations = Path(directory) / "observations.json"
            observations.write_text(parsed.stdout)
            completed = subprocess.run([sys.executable, str(SKILL / "scripts" / "timeline.py"), str(observations), "--json",
                                        "--gap-threshold-seconds", "0.125", "--rapid-threshold-seconds", "0.25"],
                                       check=True, capture_output=True, text=True)
            timeline = json.loads(completed.stdout)
            self.assertEqual(timeline["analysis"]["gaps"][0]["delta_seconds"], 0.25)
            self.assertEqual(timeline["analysis"]["rapid_succession"][0]["delta_seconds"], 0.25)
            self.assertEqual(timeline["analysis"]["unresolved_events"], 1)
            self.assertFalse(timeline["analysis"]["gaps"][0]["physical_latency_established"])
            invalid_options = subprocess.run([sys.executable, str(SKILL / "scripts" / "timeline.py"), str(observations),
                                              "--json", "--rapid-threshold-seconds", "nan"], capture_output=True, text=True)
            self.assertEqual(invalid_options.returncode, 2)
            self.assertEqual(invalid_options.stdout, "")
            self.assertEqual(observations.read_text(), parsed.stdout)


if __name__ == "__main__":
    unittest.main()
