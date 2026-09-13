"""Regenerate golden fixtures through the engine. Run deliberately after an intentional contract change;
inspect `git diff` on the expected files before committing. Hand-authored `independent_expectations` are untouched."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from sat_engine.pipeline import assess  # noqa: E402
from sat_engine.validators import canonical_bytes, loads_json  # noqa: E402

FIXTURES = Path(__file__).resolve().parent

for case_path in sorted(FIXTURES.glob("*.case.json")):
    case = loads_json(case_path.read_bytes())
    result = assess(deepcopy(case["request"]))
    assert result["status"] == "ok", (case_path.name, result["diagnostics"])
    expected_bytes = canonical_bytes(result) + b"\n"
    (FIXTURES / case["expected_result_file"]).write_bytes(expected_bytes)
    case["expected_result_bytes_sha256"] = hashlib.sha256(expected_bytes).hexdigest()
    case["expected_artifact_canonical_sha256"] = {
        kind: hashlib.sha256(canonical_bytes(view)).hexdigest() for kind, view in result["artifacts"].items()}
    case_path.write_text(json.dumps(case, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("regenerated", case_path.name)
