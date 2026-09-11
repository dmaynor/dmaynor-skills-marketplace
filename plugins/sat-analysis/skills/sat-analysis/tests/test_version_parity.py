"""Skill version (VERSION, plugin.json, SKILL.md metadata) and engine version (__init__, pyproject, schema consts) each agree."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import tomllib
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sat_engine  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT.parents[1] / ".claude-plugin" / "plugin.json"


class VersionParityTests(unittest.TestCase):
    def test_skill_versions_agree(self) -> None:
        frontmatter = (ROOT / "SKILL.md").read_text().split("---")[1]
        skill = re.search(r"^metadata:\n(?:  .*\n)*?  version:\s*(\S+)", frontmatter, re.M).group(1)
        self.assertEqual(skill, (ROOT / "VERSION").read_text().strip())
        self.assertEqual(skill, json.loads(PLUGIN.read_text())["version"])

    def test_engine_versions_agree(self) -> None:
        project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
        self.assertEqual(project, sat_engine.__version__)
        for name in ("analytic_trace", "engine_result"):
            schema = json.loads((ROOT / "sat_engine" / "resources" / "schemas" / f"{name}.v1.json").read_text())
            self.assertEqual(schema["properties"]["engine_version"]["const"], sat_engine.__version__)


if __name__ == "__main__":
    unittest.main()
