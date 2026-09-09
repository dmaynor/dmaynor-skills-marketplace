"""CLI integration tests against real requests, projections, and portable files."""

from __future__ import annotations

import base64
from contextlib import redirect_stderr, redirect_stdout
import hashlib
from importlib.resources import files
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from sat_engine import assess, validate, verify_artifacts
from sat_engine import cli
from sat_engine.validators import SCHEMA_KINDS


SKILL = Path(__file__).resolve().parents[1]


def request_fixture(mode: str = "FULL") -> dict:
    """Explicit synthetic inputs; no stored or mocked engine result."""
    return {
        "schema_version": "1", "analysis_id": "cli-integration", "revision": 3,
        "mode": mode, "submode": "GENERAL",
        "question": "What can the supplied status record establish?",
        "observations": [{
            "schema_version": "1", "id": "O1", "raw": "Sep 09 08:00:00 host status unavailable",
            "source": "synthetic.log", "parse_status": "unparsed", "timestamp": "Sep 09 08:00:00",
            "reliability": "unknown",
        }],
        "hypotheses": [
            {"schema_version": "1", "id": "H1", "description": "The service stopped."},
            {"schema_version": "1", "id": "H2", "description": "The collection is incomplete."},
        ],
        "evidence": [{"schema_version": "1", "id": "E1", "observation_id": "O1", "ratings": {"H1": "N"}}]
        if mode == "FULL" else [],
        "calculations": [{"id": "C1", "operation": "sum", "operands": [2, 3], "unit": "records"}],
        "tasks": [{"id": "T1", "action": "Inspect independent collection", "observation_ids": ["O1"],
                   "hypothesis_ids": ["H2"]}],
        "limitations": ["No independent source supplied."],
    }


class EngineCLIIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "request.json"
        # Noncanonical whitespace makes an accidental rewrite observable.
        self.original = (json.dumps(request_fixture(), indent=3) + "\n\n").encode("utf-8")
        self.source.write_bytes(self.original)

    def invoke(self, *arguments: object) -> tuple[int, object]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = cli.main([str(argument) for argument in arguments])
        self.assertEqual(stderr.getvalue(), "")
        # Parsing the whole stdout also rejects chatter or extra JSON documents.
        return status, json.loads(stdout.getvalue())

    def assert_invalid(self, status: int, result: dict, code: str | None = None) -> None:
        self.assertEqual(status, 2)
        validate("engine_result", result)
        self.assertEqual(result["status"], "invalid")
        self.assertIsNone(result["artifacts"])
        self.assertTrue(result["diagnostics"])
        self.assertTrue(all(item["severity"] == "error" for item in result["diagnostics"]))
        if code is not None:
            self.assertIn(code, [item["code"] for item in result["diagnostics"]])

    def assert_complete_artifact_files(self, output: Path, artifacts: dict) -> None:
        names = {f"{name}.{suffix}" for name, value in artifacts.items() if value is not None
                 for suffix in ("json", "md")}
        self.assertEqual({item.name for item in output.iterdir()}, names)
        restored = {}
        for name, value in artifacts.items():
            if value is None:
                restored[name] = None
                continue
            restored[name] = json.loads((output / f"{name}.json").read_bytes())
            self.assertEqual(restored[name], value)
            validate(name, restored[name])
            markdown = (output / f"{name}.md").read_text(encoding="utf-8")
            self.assertIn(value["content_hash"], markdown)
            self.assertIn("Engine diagnostics", markdown)
            self.assertIn("No independent source supplied", markdown)
            self.assertTrue(markdown.endswith("\n"))
        verify_artifacts(restored)

    def generated_result_file(self) -> Path:
        status, result = self.invoke("assess", self.source)
        self.assertEqual(status, 0)
        result_path = self.root / "result.json"
        result_path.write_text(json.dumps(result), encoding="utf-8")
        return result_path

    def output_commands(self, output: Path, result_path: Path) -> list[tuple[object, ...]]:
        return [("assess", self.source, "--output", output),
                ("render", result_path, "--output", output),
                ("export-contracts", "--output", output)]

    def test_assess_full_writes_complete_verified_json_and_markdown(self) -> None:
        output = self.root / "nested" / "assessment"
        status, result = self.invoke("assess", self.source, "--output", output)
        self.assertEqual(status, 0)
        validate("engine_result", result)
        self.assertEqual(result, assess(request_fixture()))
        self.assert_complete_artifact_files(output, result["artifacts"])
        card = result["artifacts"]["decision_card"]
        self.assertEqual(card["assessment_status"], "incomplete")
        self.assertEqual(card["calculations"][0]["value"], 5)
        self.assertEqual(card["summary"], "No analyst judgment supplied.")
        self.assertIsNone(card["likelihood"])
        self.assertIn("Unassigned", (output / "tasking_view.md").read_text())
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_assess_light_writes_only_card_and_trace(self) -> None:
        original = (json.dumps(request_fixture("LIGHT"), indent=1) + "\n").encode()
        self.source.write_bytes(original)
        output = self.root / "light"
        status, result = self.invoke("assess", self.source, "--output", output)
        self.assertEqual(status, 0)
        self.assertIsNone(result["artifacts"]["tasking_view"])
        self.assertIsNone(result["artifacts"]["analytic_trace"]["ach_matrix"])
        self.assertEqual(result["artifacts"]["decision_card"]["assessment_status"], "not_evaluated")
        self.assert_complete_artifact_files(output, result["artifacts"])
        self.assertEqual(self.source.read_bytes(), original)

    def test_render_accepts_real_result_and_artifacts_with_identical_complete_files(self) -> None:
        assessed = self.root / "assessed"
        status, result = self.invoke("assess", self.source, "--output", assessed)
        self.assertEqual(status, 0)
        for label, value in (("result", result), ("artifacts", result["artifacts"])):
            with self.subTest(input=label):
                source = self.root / f"{label}.json"
                original = (json.dumps(value, indent=1) + "\n\n").encode()
                source.write_bytes(original)
                output = self.root / f"rendered-{label}"
                status, manifest = self.invoke("render", source, "--output", output)
                self.assertEqual(status, 0)
                self.assertEqual(manifest["status"], "ok")
                self.assertEqual(set(manifest["files"]), {item.name for item in assessed.iterdir()})
                self.assert_complete_artifact_files(output, result["artifacts"])
                for name in manifest["files"]:
                    self.assertEqual((output / name).read_bytes(), (assessed / name).read_bytes())
                self.assertEqual(source.read_bytes(), original)

    def test_export_contracts_matches_all_packaged_schema_and_doctrine_bytes(self) -> None:
        output = self.root / "portable"
        status, manifest = self.invoke("export-contracts", "--output", output)
        self.assertEqual(status, 0)
        expected = {f"schemas/{kind}.v1.json" for kind in SCHEMA_KINDS} | {"doctrine/catalog.v1.json"}
        self.assertEqual(len(expected), 12)
        self.assertEqual(set(manifest["files"]), expected)
        self.assertEqual({str(path.relative_to(output)) for path in output.rglob("*") if path.is_file()}, expected)
        packaged = files("sat_engine").joinpath("resources")
        for name in expected:
            with self.subTest(resource=name):
                exported = (output / name).read_bytes()
                self.assertEqual(exported, packaged.joinpath(*name.split("/")).read_bytes())
                json.loads(exported)

    def test_strict_json_failures_exit_two_without_outputs_or_source_changes(self) -> None:
        cases = {
            "duplicate_key": b'{"mode":"FULL","mo\\u0064e":"LIGHT"}',
            "nonfinite_number": b'{"nested":[1e400]}',
            "invalid_json": b'{"question":"invalid \xff bytes"}',
            "invalid_unicode": b'{"question":"\\ud800"}',
            "nonportable_number": b'{"revision":9007199254740992}',
        }
        for code, original in cases.items():
            self.source.write_bytes(original)
            for command in ("assess", "validate", "render"):
                with self.subTest(code=code, command=command):
                    output = self.root / "must-not-exist"
                    arguments = [command, self.source]
                    if command != "validate":
                        arguments += ["--output", output]
                    self.assert_invalid(*self.invoke(*arguments), code=code)
                    self.assertFalse(output.exists())
                    self.assertEqual(self.source.read_bytes(), original)
                    self.assertFalse(list(self.root.glob(".sat-stage-*")))

    def test_nonfinite_json_constants_and_syntax_errors_are_machine_readable_failures(self) -> None:
        for original in (b"NaN", b"Infinity", b"-Infinity", b'{"unfinished":}', b"{}{}"):
            with self.subTest(original=original):
                self.source.write_bytes(original)
                self.assert_invalid(*self.invoke("assess", self.source))
                self.assertEqual(self.source.read_bytes(), original)

    def test_semantically_invalid_request_is_refused_by_assess_and_validate(self) -> None:
        request = request_fixture()
        request["evidence"][0]["observation_id"] = "not-supplied"
        original = json.dumps(request).encode()
        self.source.write_bytes(original)
        for command in ("assess", "validate"):
            with self.subTest(command=command):
                arguments = [command, self.source]
                output = self.root / "invalid-assessment"
                if command == "assess":
                    arguments += ["--output", output]
                self.assert_invalid(*self.invoke(*arguments))
                self.assertFalse(output.exists())
                self.assertEqual(self.source.read_bytes(), original)

    def test_validate_recomputes_generated_request_result_artifacts_and_trace(self) -> None:
        result_path = self.generated_result_file()
        result = json.loads(result_path.read_bytes())
        for kind, value in (("analysis_request", request_fixture()), ("engine_result", result),
                            ("artifacts", result["artifacts"]),
                            ("analytic_trace", result["artifacts"]["analytic_trace"])):
            with self.subTest(kind=kind):
                source = self.root / f"validate-{kind}.json"
                original = json.dumps(value).encode()
                source.write_bytes(original)
                status, report = self.invoke("validate", source, "--kind", kind)
                self.assertEqual(status, 0)
                self.assertEqual(report["status"], "valid")
                self.assertEqual(report["kind"], kind)
                self.assertIn("not factual truth", report["scope"])
                self.assertEqual(source.read_bytes(), original)

    def test_render_and_validate_reject_stale_projection_from_real_assessment(self) -> None:
        result_path = self.generated_result_file()
        result = json.loads(result_path.read_bytes())
        result["artifacts"]["decision_card"]["summary"] = "A stale independently edited conclusion."
        original = json.dumps(result).encode()
        result_path.write_bytes(original)
        output = self.root / "stale-render"
        self.assert_invalid(*self.invoke("render", result_path, "--output", output))
        self.assert_invalid(*self.invoke("validate", result_path, "--kind", "engine_result"))
        self.assertFalse(output.exists())
        self.assertEqual(result_path.read_bytes(), original)

    def test_render_and_validate_reject_forged_computed_results(self) -> None:
        result_path = self.generated_result_file()
        artifacts = json.loads(result_path.read_bytes())["artifacts"]
        # Keep duplicated numeric projections consistent with one another, while
        # contradicting the supplied operands. Verification must recompute them.
        for name in ("analytic_trace", "decision_card"):
            artifacts[name]["calculations"][0]["value"] = 999
        original = json.dumps(artifacts).encode()
        result_path.write_bytes(original)
        output = self.root / "forged-render"
        self.assert_invalid(*self.invoke("render", result_path, "--output", output))
        self.assert_invalid(*self.invoke("validate", result_path, "--kind", "artifacts"))
        trace_path = self.root / "forged-trace.json"
        trace_path.write_text(json.dumps(artifacts["analytic_trace"]), encoding="utf-8")
        self.assert_invalid(*self.invoke("validate", trace_path, "--kind", "analytic_trace"))
        self.assertFalse(output.exists())
        self.assertEqual(result_path.read_bytes(), original)

    def test_render_invalid_result_refuses_to_create_an_artifact_directory(self) -> None:
        request = request_fixture()
        request["question"] = ""
        result = assess(request)
        self.assertEqual(result["status"], "invalid")
        source = self.root / "invalid-result.json"
        original = json.dumps(result).encode()
        source.write_bytes(original)
        output = self.root / "invalid-render"
        self.assert_invalid(*self.invoke("render", source, "--output", output), code="invalid_result")
        self.assertFalse(output.exists())
        self.assertEqual(source.read_bytes(), original)

    def test_all_directory_outputs_refuse_existing_empty_and_nonempty_directories(self) -> None:
        result_path = self.generated_result_file()
        for populated in (False, True):
            output = self.root / f"existing-{populated}"
            output.mkdir()
            if populated:
                (output / "keep.bin").write_bytes(b"existing\x00data\xff")
            original_inode = output.stat().st_ino
            snapshot = {item.name: item.read_bytes() for item in output.iterdir()}
            for arguments in self.output_commands(output, result_path):
                with self.subTest(command=arguments[0], populated=populated):
                    self.assert_invalid(*self.invoke(*arguments), code="output_exists")
                    self.assertEqual(output.stat().st_ino, original_inode)
                    self.assertEqual({item.name: item.read_bytes() for item in output.iterdir()}, snapshot)
                    self.assertFalse(list(self.root.glob(".sat-stage-*")))
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_all_directory_outputs_refuse_live_and_dangling_symlinks(self) -> None:
        result_path = self.generated_result_file()
        for live in (True, False):
            target = self.root / f"target-{live}"
            if live:
                target.mkdir()
                (target / "keep.txt").write_bytes(b"untouched")
            output = self.root / f"link-{live}"
            output.symlink_to(target, target_is_directory=True)
            for arguments in self.output_commands(output, result_path):
                with self.subTest(command=arguments[0], live=live):
                    self.assert_invalid(*self.invoke(*arguments), code="output_exists")
                    self.assertTrue(output.is_symlink())
                    self.assertEqual(output.readlink(), target)
                    self.assertEqual(target.exists(), live)
                    if live:
                        self.assertEqual(list(target.iterdir()), [target / "keep.txt"])
                        self.assertEqual((target / "keep.txt").read_bytes(), b"untouched")
                    self.assertFalse(list(self.root.glob(".sat-stage-*")))

    def test_all_directory_outputs_clean_partial_files_after_write_failure(self) -> None:
        result_path = self.generated_result_file()
        output = self.root / "interrupted"
        real_write = Path.write_bytes
        for arguments in self.output_commands(output, result_path):
            successful_writes = []

            def fail_second_write(path: Path, data: bytes) -> int:
                if successful_writes:
                    raise OSError("injected disk failure after one complete file")
                count = real_write(path, data)
                successful_writes.append(path)
                return count

            with self.subTest(command=arguments[0]), patch.object(Path, "write_bytes", new=fail_second_write):
                status, result = self.invoke(*arguments)
            self.assert_invalid(status, result, "io_or_input_error")
            self.assertIn("injected disk failure", result["diagnostics"][0]["message"])
            self.assertEqual(len(successful_writes), 1)
            self.assertFalse(successful_writes[0].exists())
            self.assertFalse(output.exists())
            self.assertFalse(list(self.root.glob(".sat-stage-*")))
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_publication_failure_removes_staging_and_leaves_source_unchanged(self) -> None:
        output = self.root / "unpublished"
        with patch.object(cli, "_publish_directory", side_effect=OSError("injected publication failure")):
            status, result = self.invoke("assess", self.source, "--output", output)
        self.assert_invalid(status, result, "io_or_input_error")
        self.assertFalse(output.exists())
        self.assertFalse(list(self.root.glob(".sat-stage-*")))
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_directory_created_at_publication_is_never_overwritten(self) -> None:
        output = self.root / "concurrent-output"
        real_publish = cli._publish_directory
        created_inode = []

        def create_directory_before_publication(staging: Path, destination: Path) -> None:
            destination.mkdir()
            created_inode.append(destination.stat().st_ino)
            return real_publish(staging, destination)

        with patch.object(cli, "_publish_directory", new=create_directory_before_publication):
            status, result = self.invoke("assess", self.source, "--output", output)
        self.assertEqual(len(created_inode), 1)
        self.assert_invalid(status, result)
        self.assertEqual(output.stat().st_ino, created_inode[0])
        self.assertEqual(list(output.iterdir()), [])
        self.assertFalse(list(self.root.glob(".sat-stage-*")))

    @unittest.skipUnless(os.name == "posix", "Unsupported POSIX publication branch")
    def test_unsupported_publication_fails_closed_and_cleans_complete_staging(self) -> None:
        output = self.root / "unsupported-publication"
        with patch.object(cli.sys, "platform", "unsupported-test-platform"):
            status, result = self.invoke("assess", self.source, "--output", output)
        self.assert_invalid(status, result, "atomic_publication_unavailable")
        self.assertFalse(output.exists())
        self.assertFalse(list(self.root.glob(".sat-stage-*")))
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_ingest_preserves_invalid_bytes_provenance_and_source_file(self) -> None:
        source = self.root / "source.log"
        records = [b'{"timestamp":"2026-09-09T08:00:00Z","message":"started"}\r\n', b"invalid \xff bytes\n"]
        original = records[0] + b"\n" + records[1]
        source.write_bytes(original)
        status, observations = self.invoke("ingest", source, "--source-id", "collector-A",
                                           "--dependency-group", "shared-upstream",
                                           "--clock-domain", "clock-A",
                                           "--timestamp-semantics", "reported",
                                           "--timestamp-uncertainty-seconds", "0.25")
        self.assertEqual(status, 0)
        self.assertEqual(len(observations), 2)
        self.assertEqual([row["line_number"] for row in observations], [1, 3])
        self.assertEqual(observations[1]["parse_status"], "rejected")
        for observation, raw in zip(observations, records):
            validate("observation", observation)
            preserved = (base64.b64decode(observation["raw_bytes_base64"])
                         if observation["raw_bytes_base64"] else observation["raw"].encode())
            self.assertEqual(preserved, raw)
            self.assertEqual(observation["record_sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(observation["source_id"], "collector-A")
            self.assertEqual(observation["dependency_groups"], ["shared-upstream"])
            self.assertEqual(observation["clock_domain"], "clock-A")
            self.assertEqual(observation["timestamp_uncertainty_seconds"], 0.25)
        self.assertEqual(source.read_bytes(), original)

    def test_missing_input_is_a_json_error_with_exit_two(self) -> None:
        absent = self.root / "missing.json"
        for command in ("ingest", "assess", "validate", "render"):
            with self.subTest(command=command):
                arguments = [command, absent]
                if command == "render":
                    arguments += ["--output", self.root / "missing-render"]
                self.assert_invalid(*self.invoke(*arguments), code="io_or_input_error")
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_python_module_runs_real_assess_and_error_exit_codes(self) -> None:
        environment = os.environ.copy()
        # Explicit search paths let this smoke test run from a clean working
        # directory while respecting dependencies supplied by the test runner.
        environment["PYTHONPATH"] = os.pathsep.join(
            [str(SKILL)] + [str(Path(entry).resolve()) for entry in sys.path if entry]
        )
        output = self.root / "subprocess-output"
        completed = subprocess.run(
            [sys.executable, "-m", "sat_engine", "assess", str(self.source), "--output", str(output)],
            cwd=self.root, env=environment, capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        self.assertEqual(completed.stderr, "")
        result = json.loads(completed.stdout)
        self.assert_complete_artifact_files(output, result["artifacts"])
        malformed = self.root / "malformed.json"
        malformed.write_bytes(b'{"duplicate":1,"duplicate":2}')
        failed = subprocess.run(
            [sys.executable, "-m", "sat_engine", "assess", str(malformed)],
            cwd=self.root, env=environment, capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(failed.stderr, "")
        self.assert_invalid(failed.returncode, json.loads(failed.stdout), "duplicate_key")
        self.assertEqual(self.source.read_bytes(), self.original)


if __name__ == "__main__":
    unittest.main()
