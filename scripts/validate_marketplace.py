#!/usr/bin/env python3
"""Validate marketplace structure and portable Agent Skills metadata."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGINS = ROOT / "plugins"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
ALLOWED_FRONTMATTER = {
    "allowed-tools",
    "compatibility",
    "description",
    "license",
    "metadata",
    "name",
}
LIFECYCLES = {"active", "experimental", "legacy", "archived"}
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


@dataclass(frozen=True)
class SkillMetadata:
    name: str
    version: str | None
    lifecycle: str


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def frontmatter(path: Path, errors: list[str]) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        fail(errors, f"{path.relative_to(ROOT)}: missing opening frontmatter")
        return "", text
    try:
        header, body = text[4:].split("\n---\n", 1)
    except ValueError:
        fail(errors, f"{path.relative_to(ROOT)}: unterminated frontmatter")
        return "", text
    return header, body


def scalar(header: str, key: str, *, indent: int = 0) -> str | None:
    prefix = " " * indent
    match = re.search(rf"^{re.escape(prefix + key)}:\s*([^|>].*)$", header, re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip().strip('"\'')


def parse_skill(path: Path, errors: list[str]) -> SkillMetadata:
    header, body = frontmatter(path, errors)
    keys = {
        match.group(1)
        for match in re.finditer(r"^([A-Za-z][A-Za-z0-9-]*):", header, re.MULTILINE)
    }
    unexpected = sorted(keys - ALLOWED_FRONTMATTER)
    if unexpected:
        fail(errors, f"{path.relative_to(ROOT)}: unsupported frontmatter {unexpected}")

    name = scalar(header, "name") or ""
    if not NAME_RE.fullmatch(name):
        fail(errors, f"{path.relative_to(ROOT)}: invalid or missing skill name {name!r}")
    if path.parent.name != name:
        fail(errors, f"{path.relative_to(ROOT)}: directory/name mismatch ({path.parent.name!r} != {name!r})")
    if "description" not in keys:
        fail(errors, f"{path.relative_to(ROOT)}: missing description")
    if not body.strip():
        fail(errors, f"{path.relative_to(ROOT)}: empty instructions")

    lifecycle = scalar(header, "lifecycle", indent=2) or "active"
    if lifecycle not in LIFECYCLES:
        fail(errors, f"{path.relative_to(ROOT)}: invalid lifecycle {lifecycle!r}")
    return SkillMetadata(
        name=name,
        version=scalar(header, "version", indent=2),
        lifecycle=lifecycle,
    )


def validate_links(path: Path, errors: list[str]) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    for target in LINK_RE.findall(text):
        clean = target.split("#", 1)[0].strip()
        if not clean or "://" in clean or clean.startswith(("#", "mailto:")):
            continue
        if not (path.parent / clean).resolve().exists():
            fail(errors, f"{path.relative_to(ROOT)}: broken local link {target!r}")


def main() -> int:
    errors: list[str] = []
    catalog = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    entries = catalog.get("plugins", [])
    names = [entry.get("name") for entry in entries]
    if len(names) != len(set(names)):
        fail(errors, "marketplace contains duplicate plugin names")

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    registered = {str(name): entry for name, entry in zip(names, entries, strict=True)}
    seen_skills: dict[str, SkillMetadata] = {}

    for skill_path in sorted(PLUGINS.glob("*/skills/*/SKILL.md")):
        metadata = parse_skill(skill_path, errors)
        seen_skills[skill_path.parents[2].name] = metadata

    for plugin_dir in sorted(path for path in PLUGINS.iterdir() if path.is_dir()):
        plugin_name = plugin_dir.name
        metadata = seen_skills.get(plugin_name)
        if metadata is None:
            fail(errors, f"{plugin_name}: missing SKILL.md")
            continue
        entry = registered.get(plugin_name)
        manifest_path = plugin_dir / ".claude-plugin" / "plugin.json"

        if entry is None:
            if metadata.lifecycle not in {"experimental", "archived"}:
                fail(errors, f"{plugin_name}: unregistered {metadata.lifecycle} plugin")
            continue
        if metadata.lifecycle == "archived":
            fail(errors, f"{plugin_name}: archived plugin remains registered")
        if not manifest_path.exists():
            fail(errors, f"{plugin_name}: registered plugin has no manifest")
            continue

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("name") != plugin_name:
            fail(errors, f"{plugin_name}: manifest name mismatch")
        entry_version = entry.get("version")
        manifest_version = manifest.get("version")
        if entry_version != manifest_version:
            fail(errors, f"{plugin_name}: marketplace/manifest version mismatch")
        if metadata.version and metadata.version != manifest_version:
            fail(errors, f"{plugin_name}: skill/manifest version mismatch")
        if f"`{plugin_name}`" not in readme:
            fail(errors, f"{plugin_name}: missing from README plugin table")

    missing_dirs = sorted(set(registered) - set(seen_skills))
    for plugin_name in missing_dirs:
        fail(errors, f"{plugin_name}: registered plugin directory or skill missing")

    for markdown in ROOT.rglob("*.md"):
        if ".git" not in markdown.parts:
            validate_links(markdown, errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"Validation failed with {len(errors)} error(s).", file=sys.stderr)
        return 1
    print(f"Validated {len(seen_skills)} skills and {len(registered)} registered plugins.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
