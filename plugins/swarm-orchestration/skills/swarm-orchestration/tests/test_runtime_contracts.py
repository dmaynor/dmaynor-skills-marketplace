"""Regression tests for swarm storage and Notion synchronization contracts."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import notion_sync  # noqa: E402
import swarm_persistence  # noqa: E402


class RuntimeContractTests(unittest.TestCase):
    """Verify fail-safe storage and parent-ID behavior."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.teams_base = Path(self.temporary_directory.name)
        self.base_patch = patch.object(swarm_persistence, "TEAMS_BASE", self.teams_base)
        self.base_patch.start()
        self.addCleanup(self.base_patch.stop)

    def initialize_team(self, name: str = "test-team") -> Path:
        """Create the minimum durable state needed for a full export."""
        team_dir = swarm_persistence.ensure_team_structure(name)
        (team_dir / "config.json").write_text(
            json.dumps({"description": "test", "version": 1}), encoding="utf-8"
        )
        return team_dir

    def test_team_name_rejects_path_traversal(self) -> None:
        """Team state cannot escape the configured base directory."""
        with self.assertRaises(ValueError):
            swarm_persistence.get_team_dir("../../escape")

    def test_first_sync_emits_only_hub_creation(self) -> None:
        """A missing hub ID defers every child operation."""
        self.initialize_team()

        plan = notion_sync.prepare_sync("test-team", "data-source")

        self.assertTrue(plan["requires_hub_row_id"])
        self.assertEqual([operation["op"] for operation in plan["operations"]], ["create_hub_row"])
        self.assertNotIn("$hub_row_id", json.dumps(plan))

    def test_first_sync_requires_explicit_destination(self) -> None:
        """A first sync cannot fall through to an author-specific database."""
        self.initialize_team()

        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(ValueError, "first sync requires"):
                notion_sync.prepare_sync("test-team")

    def test_second_sync_uses_concrete_hub_parent(self) -> None:
        """Saved hub IDs are copied into every child creation operation."""
        team_dir = self.initialize_team()
        (team_dir / "notion_sync.json").write_text(
            json.dumps({"hub_row_id": "hub-page-123", "artifact_page_ids": {}}),
            encoding="utf-8",
        )

        plan = notion_sync.prepare_sync("test-team", "data-source")

        self.assertFalse(plan["requires_hub_row_id"])
        create_children = [
            operation
            for operation in plan["operations"]
            if operation["op"].startswith("create_")
            and operation["op"] != "create_hub_row"
        ]
        self.assertGreater(len(create_children), 0)
        for operation in create_children:
            self.assertEqual(operation["params"]["parent"]["page_id"], "hub-page-123")
        self.assertNotIn("$hub_row_id", json.dumps(plan))


if __name__ == "__main__":
    unittest.main()
