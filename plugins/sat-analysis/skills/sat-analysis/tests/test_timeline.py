"""Reported-clock ordering, unresolved context, and measurement-limit checks."""

from __future__ import annotations

import sys
import subprocess
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from timeline import Timeline, from_observations_json, parse_timestamp, resolve_timestamp


class TimestampTests(unittest.TestCase):
    """Require explicit calendar/zone context and normalize to aware UTC."""

    def test_equivalent_zoned_formats_normalize_identically(self) -> None:
        expected = datetime(2026, 9, 9, 4, 0, tzinfo=UTC)
        for timestamp in ("2026-09-09T04:00:00Z", "2026-09-09T00:00:00-04:00", "09/Sep/2026:06:00:00 +0200"):
            self.assertEqual(parse_timestamp(timestamp), expected)

    def test_missing_year_or_zone_never_uses_defaults(self) -> None:
        self.assertIsNone(parse_timestamp("2026-09-09T04:00:00"))
        self.assertIsNone(parse_timestamp("Sep 9 04:00:00"))
        self.assertIsNone(parse_timestamp("Sep 9 04:00:00", default_year=2026))
        self.assertIsNone(parse_timestamp("Sep 9 04:00:00", default_timezone="UTC"))
        self.assertEqual(parse_timestamp("Sep 9 04:00:00", default_year=2026, default_timezone="UTC"), datetime(2026, 9, 9, 4, tzinfo=UTC))

    def test_explicit_offset_overrides_fallback_zone(self) -> None:
        self.assertEqual(parse_timestamp("2026-09-09T04:00:00Z", default_timezone="-0700"), datetime(2026, 9, 9, 4, tzinfo=UTC))

    def test_unknown_and_unsupported_timestamp_stay_unresolved(self) -> None:
        for value in (None, "", "unknown", "2026-09-09", "1788933600", "not a time", "2026-02-30T00:00:00Z"):
            with self.subTest(value=value):
                dt, reason = resolve_timestamp(value)
                self.assertIsNone(dt)
                self.assertIsNotNone(reason)

    def test_dst_ambiguity_and_nonexistent_time_remain_visible(self) -> None:
        overlap = "2026-11-01T01:30:00"
        dt, reason = resolve_timestamp(overlap, default_timezone="America/New_York")
        self.assertIsNone(dt)
        self.assertIn("ambiguous", reason or "")
        first = parse_timestamp(overlap, default_timezone="America/New_York", fold=0)
        second = parse_timestamp(overlap, default_timezone="America/New_York", fold=1)
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        assert first is not None and second is not None
        self.assertEqual((second - first).total_seconds(), 3600)
        dt, reason = resolve_timestamp("2026-03-08T02:30:00", default_timezone="America/New_York")
        self.assertIsNone(dt)
        self.assertIn("does not exist", reason or "")


class TimelineIntegrityTests(unittest.TestCase):
    """No unknown clock value becomes an endpoint or physical latency claim."""

    def test_cli_rejects_duplicate_json_fields_before_evidence_is_overwritten(self) -> None:
        cases = (
            ('{"entries":[{"id":"a"}],"entries":[]}', "duplicate JSON field: entries"),
            ('[{"id":"a","timestamp":"2026-09-09T04:00:00Z","timestamp":"2026-09-09T05:00:00Z"}]', "duplicate JSON field: timestamp"),
            ('[{"id":"a","timestamp_context":{"fold":NaN}}]', "non-finite JSON constant: NaN"),
        )
        script = Path(__file__).resolve().parents[1] / "scripts" / "timeline.py"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "observations.json"
            for raw, expected_error in cases:
                with self.subTest(raw=raw):
                    path.write_text(raw)
                    result = subprocess.run([sys.executable, str(script), str(path), "--output-format", "json"], capture_output=True, text=True)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(expected_error, result.stderr)
                    self.assertEqual(result.stdout, "")

    def test_unresolved_events_cannot_become_chronological_endpoints(self) -> None:
        timeline = Timeline()
        timeline.add_event("2026-09-09T04:00:10Z", "b", "later")
        timeline.add_event("Sep 9 00:00:00", "u", "unresolved", actor="crew")
        timeline.add_event("2026-09-09T00:00:00-04:00", "a", "earlier")
        self.assertEqual(timeline.get_time_range(), ("2026-09-09T04:00:00+00:00", "2026-09-09T04:00:10+00:00"))
        self.assertEqual([event.observation_id for event in timeline.events], ["a", "b", "u"])
        actor = timeline.analyze_sequences()["actors"]["crew"]
        self.assertIsNone(actor["first"])
        self.assertIsNone(actor["last"])
        self.assertEqual(actor["unresolved"], 1)

    def test_all_unresolved_timeline_has_no_range_or_gaps(self) -> None:
        timeline = Timeline()
        timeline.add_event("Sep 9 04:00:00", "a", "unresolved")
        timeline.add_event(None, "b", "missing")
        self.assertEqual(timeline.get_time_range(), (None, None))
        self.assertEqual(timeline.get_gaps(), [])
        self.assertEqual(len(timeline.to_json_dict()["events"]), 2)

    def test_intervals_expose_clock_and_uncertainty_limits(self) -> None:
        timeline = Timeline()
        timeline.add_event("2026-09-09T04:00:00Z", "a", "first", clock_domain="clock-a")
        timeline.add_event("2026-09-09T04:10:00Z", "b", "second", clock_domain="clock-b")
        result = timeline.analyze_sequences()
        gap = result["gaps"][0]
        self.assertEqual(gap["delta_seconds"], 600)
        self.assertEqual(gap["kind"], "reported_clock_interval")
        self.assertFalse(gap["same_known_clock_domain"])
        self.assertFalse(gap["physical_latency_established"])
        self.assertIsNone(gap["combined_timestamp_uncertainty_seconds"])
        self.assertTrue(any("completeness" in warning for warning in result["caveats"]))
        self.assertIn("Reported-clock gaps", timeline.to_markdown())

    def test_same_clock_uncertainty_is_explicit_not_a_latency_proof(self) -> None:
        timeline = Timeline()
        for identifier, seconds, bound in (("a", "00", 0.2), ("b", "02", 0.3)):
            timeline.add_event(f"2026-09-09T04:00:{seconds}Z", identifier, "event", clock_domain="same", timestamp_uncertainty_seconds=bound)
        interval = timeline.analyze_sequences()["rapid_succession"][0]
        self.assertEqual(interval["combined_timestamp_uncertainty_seconds"], 0.5)
        self.assertTrue(interval["same_known_clock_domain"])
        self.assertFalse(interval["physical_latency_established"])

    def test_json_context_is_preserved_and_record_context_wins(self) -> None:
        timeline = from_observations_json([{"observation_id": "a", "timestamp": "Sep 9 04:00:00", "timestamp_context": {"year": 2026, "timezone": "+0200"}}], default_timezone="UTC")
        record = timeline.to_json_dict()["events"][0]
        self.assertEqual(record["timestamp"], "Sep 9 04:00:00")
        self.assertEqual(record["timestamp_utc"], "2026-09-09T02:00:00+00:00")
        self.assertEqual(record["timestamp_context"], {"year": 2026, "timezone": "+0200"})

    def test_bad_observation_identity_or_shape_is_rejected(self) -> None:
        for observations in ([None], [{}], [{"id": "a"}, {"id": "a"}], {"unexpected": []},
                             [{"id": "a", "tags": "authentication"}],
                             [{"id": "a", "actor": ["crew"]}],
                             [{"id": "a", "parse_status": []}]):
            with self.subTest(observations=observations):
                with self.assertRaises(ValueError):
                    from_observations_json(observations)

    def test_negative_nonfinite_or_boolean_uncertainty_is_rejected(self) -> None:
        for bound in (-1, float("nan"), float("inf"), True):
            with self.subTest(bound=bound):
                with self.assertRaises(ValueError):
                    Timeline().add_event(None, "a", "event", timestamp_uncertainty_seconds=bound)

    def test_markdown_does_not_render_embedded_html_or_forged_cells(self) -> None:
        timeline = Timeline()
        timeline.add_event(None, "a|b", "<script>**x**[click](url)\nnext", source="s|r")
        rendered = timeline.to_markdown()
        self.assertNotIn("<script>", rendered)
        self.assertIn("a\\|b", rendered)
        self.assertIn("\\[click\\]", rendered)
        self.assertIn("\\nnext", rendered)


if __name__ == "__main__":
    unittest.main()
