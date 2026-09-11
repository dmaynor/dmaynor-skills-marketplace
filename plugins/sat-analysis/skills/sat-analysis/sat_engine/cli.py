"""Unified, offline CLI over the same validated SAT engine used by Python clients."""

from __future__ import annotations

import argparse
import ctypes
import errno
from importlib.resources import files
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any

from . import __version__
from .enrich import enrich
from .parsers import ingest_file
from .pipeline import assess, verify_artifacts
from .rendering import render_markdown
from .validators import SCHEMA_KINDS, ValidationFailure, loads_json, validate


def _read_json(path: Path) -> Any:
    """Read the actual supplied bytes through the strict JSON boundary."""
    return loads_json(path.read_bytes())


def _json(value: object) -> str:
    """Emit readable standard JSON, without nonfinite extensions."""
    return json.dumps(value, ensure_ascii=True, indent=2, allow_nan=False) + "\n"


def _artifacts(value: object) -> dict[str, Any]:
    """Accept either a successful result envelope or the artifact object itself."""
    if isinstance(value, dict) and "artifacts" in value:
        validate("engine_result", value)
        if value["status"] != "ok":
            raise ValidationFailure("invalid_result", "An invalid analysis has no verified artifact set.")
        value = value["artifacts"]
    verify_artifacts(value)
    return value


def _write_directory(destination: Path, contents: dict[str, bytes]) -> None:
    """Build complete output privately and publish without replacing existing data."""
    destination = destination.absolute()
    if destination.exists() or destination.is_symlink():
        raise ValidationFailure("output_exists", f"Output already exists: {destination}",
                                remediation="Select a new output directory; existing results are not overwritten.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".sat-stage-", dir=destination.parent))
    try:
        for name, content in contents.items():
            relative = Path(name)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValidationFailure("invalid_output_path", "Generated output path escapes its directory.")
            path = staging / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        if destination.exists() or destination.is_symlink():
            raise ValidationFailure("output_exists", "Output directory appeared before publication.")
        _publish_directory(staging, destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def _publish_directory(staging: Path, destination: Path) -> None:
    """Atomically publish without replacing even a concurrently created directory.

    Plain POSIX rename replaces an existing empty directory. Linux requires
    renameat2(RENAME_NOREPLACE); Windows rename already rejects an existing path.
    Unsupported platforms fail closed rather than weakening the guarantee.
    """
    try:
        if os.name == "nt":
            os.rename(staging, destination)
            return
        if not sys.platform.startswith("linux"):
            raise ValidationFailure("atomic_publication_unavailable",
                "This platform has no supported atomic directory publication adapter.",
                remediation="Use the SDK or JSON stdout; directory publication requires Linux or Windows.")
        libc = ctypes.CDLL(None, use_errno=True)
        rename = getattr(libc, "renameat2", None)
        if rename is None:
            raise ValidationFailure("atomic_publication_unavailable",
                "The C runtime does not provide renameat2.", remediation="Use the SDK or JSON stdout.")
        rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        # Absolute paths ignore directory descriptors; 1 is RENAME_NOREPLACE.
        if rename(-100, os.fsencode(staging.absolute()), -100, os.fsencode(destination.absolute()), 1):
            code = ctypes.get_errno()
            if code in (errno.ENOSYS, errno.EINVAL, errno.EOPNOTSUPP):
                raise ValidationFailure("atomic_publication_unavailable",
                    "The kernel or filesystem does not support no-replace publication.",
                    remediation="Use the SDK or JSON stdout.")
            raise OSError(code, os.strerror(code), str(destination))
    except OSError as exc:
        if exc.errno in (errno.EEXIST, errno.ENOTEMPTY):
            raise ValidationFailure("output_exists", "Output appeared before publication.",
                remediation="Select a new output directory; existing results are not overwritten.") from exc
        raise


def _artifact_files(artifacts: dict[str, Any]) -> dict[str, bytes]:
    """Create both machine-readable projections and their verified renderings."""
    verify_artifacts(artifacts)
    contents = {name: text.encode("utf-8") for name, text in render_markdown(artifacts).items()}
    for key, value in artifacts.items():
        if value is not None:
            contents[f"{key}.json"] = _json(value).encode("utf-8")
    return contents


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=f"sat {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    ingest = commands.add_parser("ingest", help="Preserve logs as schema-shaped observations.")
    ingest.add_argument("path", type=Path)
    ingest.add_argument("--format", default="auto", choices=("auto", "syslog", "apache", "nginx", "json", "windows"))
    ingest.add_argument("--source-id")
    ingest.add_argument("--dependency-group", action="append", default=[])
    ingest.add_argument("--year", type=int)
    ingest.add_argument("--timezone")
    ingest.add_argument("--fold", type=int, choices=(0, 1))
    ingest.add_argument("--clock-domain")
    ingest.add_argument("--timestamp-semantics", default="unknown")
    ingest.add_argument("--timestamp-uncertainty-seconds", type=float)
    analysis = commands.add_parser("assess", help="Compute an analysis from explicit analyst inputs.")
    analysis.add_argument("path", type=Path)
    analysis.add_argument("--output", type=Path, help="New directory for the complete JSON/Markdown artifact set.")
    check = commands.add_parser("validate", help="Validate structure; recompute complete artifacts or requests.")
    check.add_argument("path", type=Path)
    check.add_argument("--kind", choices=(*SCHEMA_KINDS, "artifacts"), default="analysis_request")
    render = commands.add_parser("render", help="Verify a result and render its complete artifact set.")
    render.add_argument("path", type=Path)
    render.add_argument("--output", type=Path, required=True)
    citations = commands.add_parser("enrich", help="Render offline doctrine citations into a derived document.")
    citations.add_argument("path", type=Path)
    citations.add_argument("--rule", action="append", default=[])
    citations.add_argument("--mode", choices=("appendix", "inline"), default="appendix")
    coherent = commands.add_parser("coherentize", help="Coherentize raw probability elicitations before authoring a request.")
    coherent.add_argument("vectors", help="JSON: one vector [p1, p2, ...] or several [[...], [...]] to aggregate.")
    export = commands.add_parser("export-contracts", help="Export the packaged contracts for other implementations.")
    export.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Return exit 2 for failed operations; never treat diagnostics as success."""
    args = _parser().parse_args(argv)
    try:
        match args.command:
            case "ingest":
                observations = ingest_file(args.path, log_format=args.format,
                    source_id=args.source_id, dependency_groups=args.dependency_group,
                    default_year=args.year, default_timezone=args.timezone, fold=args.fold,
                    clock_domain=args.clock_domain, timestamp_semantics=args.timestamp_semantics,
                    timestamp_uncertainty_seconds=args.timestamp_uncertainty_seconds)
                for observation in observations:
                    validate("observation", observation)
                print(_json(observations), end="")
            case "assess":
                result = assess(_read_json(args.path))
                if result["status"] == "ok" and args.output is not None:
                    _write_directory(args.output, _artifact_files(result["artifacts"]))
                print(_json(result), end="")
                return 0 if result["status"] == "ok" else 2
            case "validate":
                value = _read_json(args.path)
                if args.kind == "artifacts":
                    verify_artifacts(value)
                else:
                    validate(args.kind, value)
                    if args.kind == "analysis_request":
                        result = assess(value)
                        if result["status"] != "ok":
                            print(_json(result), end="")
                            return 2
                    elif args.kind == "engine_result" and value["status"] == "ok":
                        verify_artifacts(value["artifacts"])
                    elif args.kind == "analytic_trace":
                        result = assess(value["request"])
                        if result["status"] != "ok" or result["artifacts"]["analytic_trace"] != value:
                            raise ValidationFailure("artifact_mismatch", "Trace differs from recomputed inputs.")
                print(_json({"status": "valid", "kind": args.kind,
                    "scope": "Structure and applicable deterministic constraints; not factual truth of analyst claims."}), end="")
            case "render":
                artifacts = _artifacts(_read_json(args.path))
                contents = _artifact_files(artifacts)
                _write_directory(args.output, contents)
                print(_json({"status": "ok", "output": str(args.output), "files": sorted(contents)}), end="")
            case "enrich":
                print(enrich(args.path.read_text(encoding="utf-8"), args.rule, mode=args.mode), end="")
            case "coherentize":
                from .coherence import IncoherentElicitation, aggregate, check_and_project
                raw = json.loads(args.vectors)
                try:
                    if raw and isinstance(raw[0], list):
                        runs = [check_and_project(v) for v in raw]
                        output = {"runs": runs, "aggregate": aggregate(raw), "n_runs": len(raw),
                                  "method": "equal_weight_linop"}
                    else:
                        output = check_and_project(raw)
                except IncoherentElicitation as exc:
                    print(json.dumps({"status": "invalid", "error": str(exc)}), file=sys.stderr)
                    return 2
                print(json.dumps(output, indent=2))
                return 0
            case "export-contracts":
                root = files("sat_engine").joinpath("resources")
                contents = {}
                for folder in ("schemas", "doctrine"):
                    for resource in root.joinpath(folder).iterdir():
                        if resource.name.endswith(".json"):
                            contents[f"{folder}/{resource.name}"] = resource.read_bytes()
                _write_directory(args.output, contents)
                print(_json({"status": "ok", "output": str(args.output), "files": sorted(contents)}), end="")
    except (ValidationFailure, OSError, UnicodeError, ValueError) as exc:
        diagnostic = exc if isinstance(exc, ValidationFailure) else ValidationFailure("io_or_input_error", str(exc))
        print(_json({"schema_version": "1", "engine_version": __version__, "status": "invalid",
                     "diagnostics": [diagnostic.diagnostic()], "artifacts": None}), end="")
        return 2
    return 0
