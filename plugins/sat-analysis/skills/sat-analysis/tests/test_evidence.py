"""Evidence integrity regressions, including parser-to-timeline CLI coverage."""

from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from parse_logs import (entries_to_observations_table, parse_apache_line, parse_json_line,
                        parse_log_file, parse_syslog_line, summarize_entries)
from timeline import from_observations_json


class EvidenceIntegrityTests(unittest.TestCase):
    """Check evidence survives ingestion without becoming invented observation."""

    def test_oversized_syslog_pid_is_rejected_without_losing_following_records(self) -> None:
        limit = sys.get_int_max_str_digits()
        if limit == 0:
            self.skipTest("runtime integer conversion limit is disabled")
        malformed = "Sep 9 01:02:03 host app[" + "1" * (limit + 1) + "]: event\n"
        self.assertEqual(parse_syslog_line(malformed).parse_status, "rejected")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pid.log"
            path.write_text(malformed + "after\n")
            entries = list(parse_log_file(path))
        self.assertEqual([entry.parse_status for entry in entries], ["rejected", "unparsed"])
        self.assertEqual([entry.line_number for entry in entries], [1, 2])
        self.assertEqual(entries[0].raw, malformed)
        self.assertEqual(entries[0].record_sha256, hashlib.sha256(malformed.encode()).hexdigest())
        self.assertIn("PID", entries[0].parse_error or "")
        self.assertEqual(entries[1].raw, "after\n")

    def test_file_parser_contains_field_extraction_errors_per_record(self) -> None:
        original_parser = parse_syslog_line

        def extraction_fault(line: str, source: str):
            if line == "bad field\n":
                raise ValueError("field conversion failed")
            return original_parser(line, source)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fault.log"
            path.write_text("bad field\nafter\n")
            with patch("parse_logs.parse_syslog_line", side_effect=extraction_fault):
                entries = list(parse_log_file(path))
        self.assertEqual([entry.parse_status for entry in entries], ["rejected", "unparsed"])
        self.assertEqual(entries[0].raw, "bad field\n")
        self.assertEqual(entries[1].line_number, 2)
        self.assertIn("field conversion failed", entries[0].parse_error or "")

    def test_every_nonblank_record_survives_with_physical_line_and_bytes(self) -> None:
        raw = b'  opaque 192.0.2.1 record  \r\n\n{"message": "ok"}\n{"broken":\ninvalid \xff bytes\n'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.log"
            path.write_bytes(raw)
            entries = list(parse_log_file(path))
        self.assertEqual([e.line_number for e in entries], [1, 3, 4, 5])
        self.assertEqual([e.parse_status for e in entries], ["unparsed", "parsed", "rejected", "rejected"])
        self.assertEqual(entries[0].raw, '  opaque 192.0.2.1 record  \r\n')
        self.assertEqual(base64.b64decode(entries[-1].raw_bytes_base64 or ""), b'invalid \xff bytes\n')
        self.assertEqual(entries[-1].raw.encode("utf-8", "surrogateescape"), b'invalid \xff bytes\n')
        self.assertEqual(entries[0].record_sha256, hashlib.sha256(raw.splitlines(keepends=True)[0]).hexdigest())
        summary = summarize_entries(entries)
        self.assertEqual([summary[key] for key in ("total", "parsed", "unparsed", "rejected")], [4, 1, 1, 2])
        roundtrip = json.loads(json.dumps([asdict(entry) for entry in entries], ensure_ascii=True))
        self.assertEqual(roundtrip[-1]["raw"], entries[-1].raw)
        exported = from_observations_json(roundtrip).to_json_dict()["events"]
        invalid = next(event for event in exported if event["line_number"] == 5)
        self.assertEqual(base64.b64decode(invalid["raw_bytes_base64"]), b"invalid \xff bytes\n")

    def test_source_qualified_ids_are_stable_distinct_and_content_bound(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = [Path(tmp) / name / "auth.log" for name in ("a", "b")]
            for path in paths:
                path.parent.mkdir()
                path.write_text("same\nsame\n")
            first = list(parse_log_file(paths[0]))
            second = list(parse_log_file(paths[1]))
            self.assertEqual([e.observation_id for e in first], [e.observation_id for e in parse_log_file(paths[0])])
            self.assertEqual(len({e.observation_id for e in first + second}), 4)
            self.assertNotEqual(first[0].source, second[0].source)
            paths[0].write_text("changed\nsame\n")
            self.assertNotEqual(first[0].observation_id, next(parse_log_file(paths[0])).observation_id)
            explicit = list(parse_log_file(paths[0], source_id="collector-A", dependency_groups=["COL-2", "COL-2"]))
            self.assertTrue(explicit[0].observation_id.startswith("collector-A:"))
            self.assertEqual(explicit[0].dependency_groups, ["COL-2"])
            self.assertIsNone(explicit[0].origin_id)

    def test_generic_mentions_do_not_become_source_roles(self) -> None:
        entry = parse_syslog_line("Sep  9 01:02:03 host app: destination 192.0.2.5 IPv6 2001:db8::2\n")
        self.assertEqual(entry.parse_status, "parsed")
        self.assertIsNone(entry.src_ip)
        self.assertIsNone(entry.dst_ip)
        self.assertEqual(entry.address_mentions, ["192.0.2.5", "2001:db8::2"])
        self.assertNotIn("source_address=", entries_to_observations_table([entry]))

    def test_ssh_roles_require_recognized_message_and_process(self) -> None:
        message = "Sep  9 01:02:03 host sshd[22]: Failed password for invalid user root from 2001:db8::2 port 22 ssh2\n"
        entry = parse_syslog_line(message)
        self.assertEqual((entry.src_ip, entry.src_port, entry.action), ("2001:db8::2", 22, "ssh_auth_fail"))
        self.assertEqual(entry.tags, ["authentication", "ssh"])
        self.assertNotIn("2001:db8::2", entry.address_mentions)
        ordinary = parse_syslog_line(message.replace("sshd[22]", "app[22]"))
        self.assertIsNone(ordinary.src_ip)
        self.assertIsNone(ordinary.action)

    def test_access_request_contents_are_not_attack_labels(self) -> None:
        line = '192.0.2.1 - - [09/Sep/2026:01:02:03 +0000] "GET /../file?x=javascript: HTTP/1.1" 404 2 "-" "client"\n'
        entry = parse_apache_line(line)
        self.assertEqual(entry.parse_status, "parsed")
        self.assertEqual(entry.tags, ["web"])
        self.assertEqual(entry.raw, line)
        self.assertEqual(entry.src_ip, "192.0.2.1")

    def test_bad_json_field_duplicate_alias_or_nonobject_is_rejected(self) -> None:
        for line in ('{"pid": "oops"}', '[]', '{"src_ip": "999.2.3.4"}',
                     '{"src_port": true}', '{"message": "one", "message": "two"}',
                     '{"timestamp": NaN}', '{"src_ip": "192.0.2.1", "source_ip": "192.0.2.2"}'):
            with self.subTest(line=line):
                entry = parse_json_line(line)
                self.assertEqual(entry.parse_status, "rejected")
                self.assertEqual(entry.raw, line)
                self.assertIsNotNone(entry.parse_error)

    def test_json_message_address_is_untyped_but_explicit_fields_have_roles(self) -> None:
        entry = parse_json_line('{"message": "destination 192.0.2.2", "src_ip": "192.0.2.1", "dst_port": 443}')
        self.assertEqual(entry.src_ip, "192.0.2.1")
        self.assertIsNone(entry.dst_ip)
        self.assertEqual(entry.dst_port, 443)
        self.assertEqual(entry.address_mentions, ["192.0.2.2"])

    def test_json_parser_envelope_preserves_failed_records_in_timeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.log"
            path.write_text('{"timestamp":"2026-09-09T02:00:00Z", "message":"a"}\n{"broken":\n')
            entries = list(parse_log_file(path))
        timeline = from_observations_json({"entries": [asdict(entry) for entry in entries], "summary": summarize_entries(entries)})
        result = timeline.to_json_dict()
        self.assertEqual(len(result["events"]), 2)
        rejected = next(event for event in result["events"] if event["parse_status"] == "rejected")
        self.assertEqual(rejected["raw"], entries[1].raw)
        self.assertEqual(rejected["record_sha256"], entries[1].record_sha256)
        self.assertEqual(result["analysis"]["unresolved_events"], 1)

    def test_summary_uses_utc_order_and_excludes_unresolved_timestamps(self) -> None:
        entries = [parse_json_line(json.dumps({"timestamp": time})) for time in
                   ("2026-09-09T02:00:00Z", "2026-09-08T22:30:00-04:00", "Sep 9 00:00:00", "2026-09-09T23:00:00")]
        summary = summarize_entries(entries)
        self.assertEqual(summary["time_range"], {"first": "2026-09-09T02:00:00+00:00", "last": "2026-09-09T02:30:00+00:00"})
        self.assertEqual(summary["unresolved_timestamps"], 2)

    def test_cli_outputs_pure_json_and_roundtrips_to_timeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "source.log"
            log.write_text("Sep  9 01:02:03 host app: ordinary\nmalformed\n")
            parsed = subprocess.run([sys.executable, str(SCRIPTS / "parse_logs.py"), str(log), "syslog", "--output-format", "json", "--year", "2026", "--timezone", "UTC"], check=True, capture_output=True, text=True)
            data = json.loads(parsed.stdout)
            self.assertEqual(data["entries"][0]["timestamp_context"], {"year": 2026, "timezone": "UTC"})
            observations = Path(tmp) / "observations.json"
            observations.write_text(parsed.stdout)
            built = subprocess.run([sys.executable, str(SCRIPTS / "timeline.py"), str(observations), "--output-format", "json"], check=True, capture_output=True, text=True)
            result = json.loads(built.stdout)
            self.assertEqual(result["analysis"]["resolved_events"], 1)
            self.assertEqual(result["analysis"]["unresolved_events"], 1)

    def test_markdown_escapes_source_content(self) -> None:
        entry = parse_syslog_line("<script>|[click](url) **event**\n", "evil|source")
        table = entries_to_observations_table([entry])
        self.assertIn("&lt;script&gt;\\|", table)
        self.assertIn("\\[click\\]", table)
        self.assertNotIn("<script>", table)
        self.assertIn("evil\\|source", table)


if __name__ == "__main__":
    unittest.main()
