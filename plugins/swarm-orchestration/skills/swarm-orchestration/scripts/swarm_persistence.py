#!/usr/bin/env python3
"""
Swarm Persistence System - Comprehensive Notion Integration

Captures and persists ALL aspects of a swarm session:
- Request: Original user prompt
- Dialogue: Full user ↔ Claude conversation turns
- Thinking: Claude's extended thinking blocks
- Agent Logs: Channel communication between agents
- Output: Final deliverables and summaries
- Artifacts: Code, config files, markdown docs → uploaded to Notion

Usage:
    # Record conversation turn
    python3 swarm_persistence.py add-turn --team X --role user --content "..."
    python3 swarm_persistence.py add-turn --team X --role assistant --content "..."
    
    # Record thinking block
    python3 swarm_persistence.py add-thinking --team X --content "..."
    
    # Register artifact
    python3 swarm_persistence.py add-artifact --team X --name file.py --type code --path /path/to/file
    
    # Export everything for Notion
    python3 swarm_persistence.py export-full --team X
    
    # Generate Notion page structure
    python3 swarm_persistence.py notion-structure --team X
"""

import argparse
import hashlib
import json
import mimetypes
import re
import shutil
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


TEAMS_BASE = Path.home() / ".claude" / "teams"

# Artifact type mappings
ARTIFACT_TYPES = {
    ".py": ("code", "python"),
    ".js": ("code", "javascript"),
    ".ts": ("code", "typescript"),
    ".jsx": ("code", "jsx"),
    ".tsx": ("code", "tsx"),
    ".sh": ("code", "bash"),
    ".bash": ("code", "bash"),
    ".rs": ("code", "rust"),
    ".go": ("code", "go"),
    ".java": ("code", "java"),
    ".c": ("code", "c"),
    ".cpp": ("code", "cpp"),
    ".h": ("code", "c"),
    ".hpp": ("code", "cpp"),
    ".rb": ("code", "ruby"),
    ".sql": ("code", "sql"),
    ".json": ("config", "json"),
    ".yaml": ("config", "yaml"),
    ".yml": ("config", "yaml"),
    ".toml": ("config", "toml"),
    ".ini": ("config", "ini"),
    ".env": ("config", "env"),
    ".md": ("document", "markdown"),
    ".txt": ("document", "text"),
    ".rst": ("document", "rst"),
    ".html": ("document", "html"),
    ".css": ("document", "css"),
    ".xml": ("config", "xml"),
}


def timestamp() -> str:
    """Return current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def date_today() -> str:
    """Return current date as YYYY-MM-DD."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load_json(path: Path) -> dict:
    """Load JSON file, return empty dict if not exists."""
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def save_json(path: Path, data: dict) -> None:
    """Save dict to JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_jsonl(path: Path) -> list[dict]:
    """Load JSONL file, return empty list if not exists."""
    msgs = []
    if path.exists():
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        msgs.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return msgs


def append_jsonl(path: Path, record: dict) -> None:
    """Append record to JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")


def get_team_dir(team_name: str) -> Path:
    """Get team directory path."""
    return TEAMS_BASE / team_name


def ensure_team_structure(team_name: str) -> Path:
    """Ensure team directory structure exists."""
    team_dir = get_team_dir(team_name)
    team_dir.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories
    (team_dir / "artifacts" / "code").mkdir(parents=True, exist_ok=True)
    (team_dir / "artifacts" / "config").mkdir(parents=True, exist_ok=True)
    (team_dir / "artifacts" / "docs").mkdir(parents=True, exist_ok=True)
    
    # Initialize files if not exist
    if not (team_dir / "conversation.jsonl").exists():
        (team_dir / "conversation.jsonl").touch()
    if not (team_dir / "thinking.jsonl").exists():
        (team_dir / "thinking.jsonl").touch()
    if not (team_dir / "outputs.json").exists():
        save_json(team_dir / "outputs.json", {"outputs": [], "summary": ""})
    if not (team_dir / "artifacts" / "manifest.json").exists():
        save_json(team_dir / "artifacts" / "manifest.json", {"artifacts": {}})
    
    return team_dir


@dataclass
class ConversationTurn:
    """A single turn in the user ↔ Claude dialogue."""
    ts: str
    role: str  # "user" or "assistant"
    content: str
    turn_number: int
    metadata: dict = field(default_factory=dict)


@dataclass
class ThinkingBlock:
    """Claude's extended thinking for a turn."""
    ts: str
    turn_number: int
    content: str
    token_count: Optional[int] = None


@dataclass
class Artifact:
    """A file artifact produced during the session."""
    artifact_id: str
    name: str
    artifact_type: str  # code, config, document
    language: str
    path: str  # relative path within team/artifacts/
    size_bytes: int
    created_at: str
    description: str = ""
    checksum: str = ""  # SHA256
    notion_page_id: Optional[str] = None


@dataclass
class Output:
    """A final output/deliverable from the session."""
    output_id: str
    title: str
    output_type: str  # report, code, analysis, etc.
    content: str
    created_at: str
    artifact_refs: list[str] = field(default_factory=list)


# ============================================================================
# CONVERSATION TRACKING
# ============================================================================

def add_conversation_turn(
    team_name: str,
    role: str,
    content: str,
    metadata: Optional[dict] = None
) -> ConversationTurn:
    """Add a conversation turn (user or assistant message)."""
    team_dir = ensure_team_structure(team_name)
    conv_path = team_dir / "conversation.jsonl"
    
    # Get next turn number
    existing = load_jsonl(conv_path)
    turn_number = len(existing) + 1
    
    turn = ConversationTurn(
        ts=timestamp(),
        role=role,
        content=content,
        turn_number=turn_number,
        metadata=metadata or {}
    )
    
    append_jsonl(conv_path, asdict(turn))
    return turn


def get_conversation(team_name: str) -> list[dict]:
    """Get full conversation history."""
    team_dir = get_team_dir(team_name)
    return load_jsonl(team_dir / "conversation.jsonl")


# ============================================================================
# THINKING TRACKING
# ============================================================================

def add_thinking_block(
    team_name: str,
    content: str,
    turn_number: Optional[int] = None,
    token_count: Optional[int] = None
) -> ThinkingBlock:
    """Add a thinking block."""
    team_dir = ensure_team_structure(team_name)
    thinking_path = team_dir / "thinking.jsonl"
    
    # Auto-detect turn number from conversation if not provided
    if turn_number is None:
        conv = get_conversation(team_name)
        turn_number = len(conv) + 1  # Next turn (assistant response)
    
    block = ThinkingBlock(
        ts=timestamp(),
        turn_number=turn_number,
        content=content,
        token_count=token_count
    )
    
    append_jsonl(thinking_path, asdict(block))
    return block


def get_thinking_blocks(team_name: str) -> list[dict]:
    """Get all thinking blocks."""
    team_dir = get_team_dir(team_name)
    return load_jsonl(team_dir / "thinking.jsonl")


# ============================================================================
# ARTIFACT MANAGEMENT
# ============================================================================

def compute_checksum(file_path: Path) -> str:
    """Compute SHA256 checksum of file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def detect_artifact_type(file_path: Path) -> tuple[str, str]:
    """Detect artifact type and language from file extension."""
    suffix = file_path.suffix.lower()
    return ARTIFACT_TYPES.get(suffix, ("document", "text"))


def add_artifact(
    team_name: str,
    source_path: str,
    name: Optional[str] = None,
    artifact_type: Optional[str] = None,
    language: Optional[str] = None,
    description: str = "",
    copy_file: bool = True
) -> Artifact:
    """
    Register and optionally copy an artifact file.
    
    Args:
        team_name: Team/project name
        source_path: Path to the source file
        name: Override filename (defaults to source filename)
        artifact_type: Override type detection (code, config, document)
        language: Override language detection
        description: Human description of the artifact
        copy_file: If True, copy file to team artifacts dir
    
    Returns:
        Artifact record
    """
    team_dir = ensure_team_structure(team_name)
    source = Path(source_path)
    
    if not source.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")
    
    # Detect or use provided type/language
    detected_type, detected_lang = detect_artifact_type(source)
    art_type = artifact_type or detected_type
    art_lang = language or detected_lang
    
    # Determine destination
    file_name = name or source.name
    type_subdir = {"code": "code", "config": "config", "document": "docs"}.get(art_type, "docs")
    dest_rel = f"artifacts/{type_subdir}/{file_name}"
    dest_path = team_dir / dest_rel
    
    # Copy file if requested
    if copy_file:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest_path)
        size = dest_path.stat().st_size
        checksum = compute_checksum(dest_path)
    else:
        size = source.stat().st_size
        checksum = compute_checksum(source)
        dest_rel = str(source)  # Use original path
    
    # Load manifest and generate ID
    manifest_path = team_dir / "artifacts" / "manifest.json"
    manifest = load_json(manifest_path)
    artifacts = manifest.get("artifacts", {})
    
    artifact_id = f"ART-{len(artifacts) + 1:04d}"
    
    artifact = Artifact(
        artifact_id=artifact_id,
        name=file_name,
        artifact_type=art_type,
        language=art_lang,
        path=dest_rel,
        size_bytes=size,
        created_at=timestamp(),
        description=description,
        checksum=checksum
    )
    
    artifacts[artifact_id] = asdict(artifact)
    manifest["artifacts"] = artifacts
    save_json(manifest_path, manifest)
    
    return artifact


def get_artifacts(team_name: str) -> dict[str, dict]:
    """Get all artifacts from manifest."""
    team_dir = get_team_dir(team_name)
    manifest = load_json(team_dir / "artifacts" / "manifest.json")
    return manifest.get("artifacts", {})


def get_artifact_content(team_name: str, artifact_id: str) -> Optional[str]:
    """Read artifact file content (text files only)."""
    team_dir = get_team_dir(team_name)
    manifest = load_json(team_dir / "artifacts" / "manifest.json")
    artifacts = manifest.get("artifacts", {})
    
    if artifact_id not in artifacts:
        return None
    
    art = artifacts[artifact_id]
    path = team_dir / art["path"] if not art["path"].startswith("/") else Path(art["path"])
    
    if path.exists():
        try:
            return path.read_text()
        except UnicodeDecodeError:
            return None  # Binary file
    return None


# ============================================================================
# OUTPUT MANAGEMENT
# ============================================================================

def add_output(
    team_name: str,
    title: str,
    content: str,
    output_type: str = "report",
    artifact_refs: Optional[list[str]] = None
) -> Output:
    """Add a final output/deliverable."""
    team_dir = ensure_team_structure(team_name)
    outputs_path = team_dir / "outputs.json"
    
    data = load_json(outputs_path)
    outputs = data.get("outputs", [])
    
    output_id = f"OUT-{len(outputs) + 1:04d}"
    
    output = Output(
        output_id=output_id,
        title=title,
        output_type=output_type,
        content=content,
        created_at=timestamp(),
        artifact_refs=artifact_refs or []
    )
    
    outputs.append(asdict(output))
    data["outputs"] = outputs
    save_json(outputs_path, data)
    
    return output


def set_output_summary(team_name: str, summary: str) -> None:
    """Set the overall output summary."""
    team_dir = get_team_dir(team_name)
    outputs_path = team_dir / "outputs.json"
    
    data = load_json(outputs_path)
    data["summary"] = summary
    save_json(outputs_path, data)


def get_outputs(team_name: str) -> dict:
    """Get outputs data."""
    team_dir = get_team_dir(team_name)
    return load_json(team_dir / "outputs.json")


# ============================================================================
# FULL EXPORT FOR NOTION
# ============================================================================

def export_full(team_name: str) -> dict:
    """
    Export complete session state for Notion persistence.
    
    Returns dict with:
    - pages: List of Notion pages to create
    - hub_row: Data for Swarm Hub database row
    """
    team_dir = get_team_dir(team_name)
    if not team_dir.exists():
        raise FileNotFoundError(f"Team not found: {team_name}")
    
    # Load all data
    config = load_json(team_dir / "config.json")
    tasks = load_json(team_dir / "tasks.json")
    agents = load_json(team_dir / "agents.json")
    findings = load_json(team_dir / "findings.json")
    channel = load_jsonl(team_dir / "channel.jsonl")
    conversation = load_jsonl(team_dir / "conversation.jsonl")
    thinking = load_jsonl(team_dir / "thinking.jsonl")
    outputs = load_json(team_dir / "outputs.json")
    artifacts = get_artifacts(team_name)
    
    version = config.get("version", 1)
    ts = timestamp()
    
    pages = []
    
    # =========== PAGE 1: Main State Page ===========
    state_md = f"# {team_name} - Session State (v{version})\n\n"
    state_md += f"**Exported:** {ts}\n\n---\n\n"
    
    # Session Context
    state_md += "## Session Context\n\n"
    if config.get("original_prompt"):
        state_md += "### Original Request\n\n"
        state_md += f"```\n{config['original_prompt']}\n```\n\n"
    
    if config.get("description"):
        state_md += f"**Description:** {config['description']}\n\n"
    
    # Output Summary
    if outputs.get("summary"):
        state_md += "### Output Summary\n\n"
        state_md += f"{outputs['summary']}\n\n"
    
    state_md += "---\n\n"
    
    # Final Outputs
    output_list = outputs.get("outputs", [])
    if output_list:
        state_md += f"## Final Outputs ({len(output_list)})\n\n"
        for out in output_list:
            state_md += f"### {out['title']}\n\n"
            state_md += f"**Type:** {out['output_type']} | **Created:** {out['created_at'][:19]}\n\n"
            # Truncate long content
            content = out['content']
            if len(content) > 2000:
                state_md += f"{content[:2000]}\n\n*[truncated - see full output page]*\n\n"
            else:
                state_md += f"{content}\n\n"
            if out.get('artifact_refs'):
                state_md += f"**Artifacts:** {', '.join(out['artifact_refs'])}\n\n"
        state_md += "---\n\n"
    
    # Artifacts Summary
    if artifacts:
        state_md += f"## Artifacts ({len(artifacts)})\n\n"
        state_md += "| ID | Name | Type | Language | Size |\n"
        state_md += "|-----|------|------|----------|------|\n"
        for art_id, art in artifacts.items():
            size_kb = art['size_bytes'] / 1024
            state_md += f"| {art_id} | {art['name']} | {art['artifact_type']} | {art['language']} | {size_kb:.1f}KB |\n"
        state_md += "\n---\n\n"
    
    # Findings (if any)
    findings_list = list(findings.get("findings", {}).values())
    if findings_list:
        state_md += f"## Findings ({len(findings_list)})\n\n"
        state_md += "| ID | Severity | Title | Status |\n"
        state_md += "|----|----------|-------|--------|\n"
        for f in findings_list:
            status = "✓ Resolved" if f.get("resolved") else "✗ Open"
            state_md += f"| {f.get('finding_id','')} | {f.get('severity','')} | {f.get('title','')[:50]} | {status} |\n"
        state_md += "\n---\n\n"
    
    # Quick Stats
    state_md += "## Session Stats\n\n"
    state_md += f"- **Conversation Turns:** {len(conversation)}\n"
    state_md += f"- **Thinking Blocks:** {len(thinking)}\n"
    state_md += f"- **Agent Messages:** {len(channel)}\n"
    state_md += f"- **Artifacts Produced:** {len(artifacts)}\n"
    state_md += f"- **Final Outputs:** {len(output_list)}\n\n"
    
    # Raw state for restoration
    state_md += "---\n\n## Raw State\n\n"
    state_md += f"\u25b6 config.json\n```json\n{json.dumps(config, indent=2)}\n```\n\n"
    
    pages.append({
        "type": "state",
        "title": f"{team_name} - State v{version}",
        "content": state_md
    })
    
    # =========== PAGE 2: Conversation Log ===========
    if conversation:
        conv_md = f"# {team_name} - Conversation Log\n\n"
        conv_md += f"**Turns:** {len(conversation)}\n\n---\n\n"
        
        for turn in conversation:
            role_icon = "👤" if turn["role"] == "user" else "🤖"
            conv_md += f"## Turn {turn['turn_number']} - {role_icon} {turn['role'].title()}\n\n"
            conv_md += f"*{turn['ts'][:19]}*\n\n"
            conv_md += f"{turn['content']}\n\n---\n\n"
        
        # Raw for restoration
        conv_md += "\n\u25b6 Raw JSONL\n```jsonl\n"
        for turn in conversation:
            conv_md += json.dumps(turn) + "\n"
        conv_md += "```\n"
        
        pages.append({
            "type": "conversation",
            "title": f"{team_name} - Conversation",
            "content": conv_md
        })
    
    # =========== PAGE 3: Thinking Log ===========
    if thinking:
        think_md = f"# {team_name} - Thinking Log\n\n"
        think_md += f"**Blocks:** {len(thinking)}\n\n---\n\n"
        
        for block in thinking:
            think_md += f"## Turn {block['turn_number']} Thinking\n\n"
            think_md += f"*{block['ts'][:19]}*"
            if block.get('token_count'):
                think_md += f" | ~{block['token_count']} tokens"
            think_md += "\n\n"
            
            # Truncate very long thinking
            content = block['content']
            if len(content) > 5000:
                think_md += f"{content[:5000]}\n\n*[truncated - {len(content)} chars total]*\n\n"
            else:
                think_md += f"{content}\n\n"
            think_md += "---\n\n"
        
        pages.append({
            "type": "thinking",
            "title": f"{team_name} - Thinking",
            "content": think_md
        })
    
    # =========== PAGE 4: Agent Logs ===========
    if channel:
        agent_md = f"# {team_name} - Agent Logs\n\n"
        agent_md += f"**Messages:** {len(channel)}\n\n---\n\n"
        
        current_date = None
        for msg in channel:
            msg_date = msg.get("ts", "")[:10]
            if msg_date != current_date:
                current_date = msg_date
                agent_md += f"\n## {current_date}\n\n"
            
            ts = msg.get("ts", "")
            sender = msg.get("from", "?")
            to = msg.get("to", ["@all"])
            to_str = ", ".join(to) if isinstance(to, list) else str(to)
            msg_type = msg.get("type", "message")
            reasoning = msg.get("reasoning", "")
            content = msg.get("content", "")
            
            agent_md += f"**[{ts[11:19]}] @{sender} → {to_str}**"
            if msg_type != "message":
                agent_md += f" ({msg_type})"
            agent_md += "\n\n"
            if reasoning:
                agent_md += f"> {reasoning}\n\n"
            
            # Truncate long messages
            if len(content) > 1000:
                agent_md += f"{content[:1000]}\n\n*[truncated]*\n\n"
            else:
                agent_md += f"{content}\n\n"
        
        # Raw for restoration
        agent_md += "\n---\n\n\u25b6 Raw JSONL\n```jsonl\n"
        for msg in channel:
            agent_md += json.dumps(msg) + "\n"
        agent_md += "```\n"
        
        pages.append({
            "type": "agents",
            "title": f"{team_name} - Agent Logs",
            "content": agent_md
        })
    
    # =========== PAGES 5+: Individual Artifacts ===========
    for art_id, art in artifacts.items():
        content = get_artifact_content(team_name, art_id)
        if content:
            art_md = f"# {art['name']}\n\n"
            art_md += f"**ID:** {art_id} | **Type:** {art['artifact_type']} | **Language:** {art['language']}\n"
            art_md += f"**Size:** {art['size_bytes']} bytes | **Created:** {art['created_at'][:19]}\n"
            if art.get('description'):
                art_md += f"\n**Description:** {art['description']}\n"
            art_md += f"\n**Checksum (SHA256):** `{art.get('checksum', 'N/A')[:16]}...`\n\n"
            art_md += "---\n\n"
            art_md += f"```{art['language']}\n{content}\n```\n"
            
            pages.append({
                "type": "artifact",
                "artifact_id": art_id,
                "title": art['name'],
                "content": art_md,
                "language": art['language']
            })
    
    # Hub row data
    hub_row = {
        "Project": team_name,
        "Description": config.get("description", "")[:200],
        "Status": "active",
        "Type": config.get("type", "development"),
        "date:Created:start": config.get("created_at", "")[:10] or date_today(),
        "date:Last Active:start": date_today()
    }
    
    return {
        "team_name": team_name,
        "version": version,
        "exported_at": ts,
        "pages": pages,
        "hub_row": hub_row,
        "stats": {
            "conversation_turns": len(conversation),
            "thinking_blocks": len(thinking),
            "agent_messages": len(channel),
            "artifacts": len(artifacts),
            "outputs": len(output_list),
            "findings": len(findings_list)
        }
    }


def generate_notion_structure(team_name: str) -> str:
    """
    Generate instructions for creating Notion page structure.
    
    Returns markdown with exact tool calls for Claude to execute.
    """
    export = export_full(team_name)
    
    instructions = f"""# Notion Persistence Instructions for {team_name}

Execute the following steps to persist this swarm session to Notion:

## Step 1: Create/Update Hub Row

```
Notion:notion-create-pages({{
  parent: {{ data_source_id: "722ecbf3-0bee-46a4-b196-4b507d6b3d9f" }},  // Swarm Hub
  pages: [{{
    properties: {json.dumps(export['hub_row'], indent=4)}
  }}]
}})
```

## Step 2: Create Child Pages

For each page in the export, create as child of the hub row:

"""
    
    for i, page in enumerate(export['pages'], 1):
        instructions += f"""### Page {i}: {page['title']}

**Type:** {page['type']}

```
Notion:notion-create-pages({{
  parent: {{ page_id: "<hub_row_page_id>" }},
  pages: [{{
    properties: {{ title: "{page['title']}" }},
    content: "<see export content>"
  }}]
}})
```

"""
    
    instructions += f"""
## Export Stats

- Conversation Turns: {export['stats']['conversation_turns']}
- Thinking Blocks: {export['stats']['thinking_blocks']}
- Agent Messages: {export['stats']['agent_messages']}
- Artifacts: {export['stats']['artifacts']}
- Outputs: {export['stats']['outputs']}
- Findings: {export['stats']['findings']}
"""
    
    return instructions


# ============================================================================
# AUTO-DETECT ARTIFACTS FROM DIRECTORY
# ============================================================================

def scan_and_register_artifacts(
    team_name: str,
    source_dir: str,
    description_prefix: str = ""
) -> list[Artifact]:
    """
    Scan a directory and register all supported files as artifacts.
    
    Args:
        team_name: Team name
        source_dir: Directory to scan
        description_prefix: Prefix for artifact descriptions
    
    Returns:
        List of registered Artifact objects
    """
    source = Path(source_dir)
    if not source.exists():
        raise FileNotFoundError(f"Directory not found: {source_dir}")
    
    registered = []
    
    for file_path in source.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in ARTIFACT_TYPES:
            # Skip hidden files and common noise
            if file_path.name.startswith("."):
                continue
            if "__pycache__" in str(file_path):
                continue
            if "node_modules" in str(file_path):
                continue
            
            rel_name = file_path.relative_to(source)
            desc = f"{description_prefix} {rel_name}" if description_prefix else str(rel_name)
            
            try:
                artifact = add_artifact(
                    team_name=team_name,
                    source_path=str(file_path),
                    description=desc.strip()
                )
                registered.append(artifact)
            except Exception as e:
                print(f"[WARN] Failed to register {file_path}: {e}", file=sys.stderr)
    
    return registered


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Swarm Persistence System",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="cmd")
    
    # Add conversation turn
    turn_cmd = sub.add_parser("add-turn", help="Add conversation turn")
    turn_cmd.add_argument("--team", required=True)
    turn_cmd.add_argument("--role", required=True, choices=["user", "assistant"])
    turn_cmd.add_argument("--content", help="Turn content (or use --file)")
    turn_cmd.add_argument("--file", help="Read content from file")
    
    # Add thinking block
    think_cmd = sub.add_parser("add-thinking", help="Add thinking block")
    think_cmd.add_argument("--team", required=True)
    think_cmd.add_argument("--content", help="Thinking content (or use --file)")
    think_cmd.add_argument("--file", help="Read content from file")
    think_cmd.add_argument("--turn", type=int, help="Associated turn number")
    think_cmd.add_argument("--tokens", type=int, help="Token count")
    
    # Add artifact
    art_cmd = sub.add_parser("add-artifact", help="Register artifact")
    art_cmd.add_argument("--team", required=True)
    art_cmd.add_argument("--path", required=True, help="Source file path")
    art_cmd.add_argument("--name", help="Override filename")
    art_cmd.add_argument("--type", help="Override type (code, config, document)")
    art_cmd.add_argument("--language", help="Override language")
    art_cmd.add_argument("--description", default="", help="Description")
    art_cmd.add_argument("--no-copy", action="store_true", help="Don't copy file")
    
    # Scan directory for artifacts
    scan_cmd = sub.add_parser("scan-artifacts", help="Scan directory and register all artifacts")
    scan_cmd.add_argument("--team", required=True)
    scan_cmd.add_argument("--dir", required=True, help="Directory to scan")
    scan_cmd.add_argument("--prefix", default="", help="Description prefix")
    
    # Add output
    out_cmd = sub.add_parser("add-output", help="Add final output")
    out_cmd.add_argument("--team", required=True)
    out_cmd.add_argument("--title", required=True)
    out_cmd.add_argument("--content", help="Output content (or use --file)")
    out_cmd.add_argument("--file", help="Read content from file")
    out_cmd.add_argument("--type", default="report", help="Output type")
    out_cmd.add_argument("--artifacts", nargs="*", help="Artifact IDs")
    
    # Set summary
    sum_cmd = sub.add_parser("set-summary", help="Set output summary")
    sum_cmd.add_argument("--team", required=True)
    sum_cmd.add_argument("--summary", help="Summary text (or use --file)")
    sum_cmd.add_argument("--file", help="Read summary from file")
    
    # Export full
    exp_cmd = sub.add_parser("export-full", help="Export everything for Notion")
    exp_cmd.add_argument("--team", required=True)
    exp_cmd.add_argument("--format", choices=["json", "pages"], default="json")
    
    # Generate Notion structure
    struct_cmd = sub.add_parser("notion-structure", help="Generate Notion creation instructions")
    struct_cmd.add_argument("--team", required=True)
    
    # List artifacts
    list_cmd = sub.add_parser("list-artifacts", help="List registered artifacts")
    list_cmd.add_argument("--team", required=True)
    
    # Init team
    init_cmd = sub.add_parser("init", help="Initialize team structure")
    init_cmd.add_argument("--team", required=True)
    init_cmd.add_argument("--description", default="")
    init_cmd.add_argument("--type", default="development")
    
    args = parser.parse_args()
    
    if args.cmd == "add-turn":
        content = args.content
        if args.file:
            content = Path(args.file).read_text()
        if not content:
            content = sys.stdin.read()
        
        turn = add_conversation_turn(args.team, args.role, content)
        print(json.dumps(asdict(turn), indent=2))
    
    elif args.cmd == "add-thinking":
        content = args.content
        if args.file:
            content = Path(args.file).read_text()
        if not content:
            content = sys.stdin.read()
        
        block = add_thinking_block(args.team, content, args.turn, args.tokens)
        print(json.dumps(asdict(block), indent=2))
    
    elif args.cmd == "add-artifact":
        artifact = add_artifact(
            team_name=args.team,
            source_path=args.path,
            name=args.name,
            artifact_type=args.type,
            language=args.language,
            description=args.description,
            copy_file=not args.no_copy
        )
        print(json.dumps(asdict(artifact), indent=2))
    
    elif args.cmd == "scan-artifacts":
        artifacts = scan_and_register_artifacts(args.team, args.dir, args.prefix)
        print(json.dumps([asdict(a) for a in artifacts], indent=2))
    
    elif args.cmd == "add-output":
        content = args.content
        if args.file:
            content = Path(args.file).read_text()
        if not content:
            content = sys.stdin.read()
        
        output = add_output(args.team, args.title, content, args.type, args.artifacts)
        print(json.dumps(asdict(output), indent=2))
    
    elif args.cmd == "set-summary":
        summary = args.summary
        if args.file:
            summary = Path(args.file).read_text()
        if not summary:
            summary = sys.stdin.read()
        
        set_output_summary(args.team, summary)
        print(f"[OK] Summary set for {args.team}")
    
    elif args.cmd == "export-full":
        export = export_full(args.team)
        if args.format == "json":
            print(json.dumps(export, indent=2))
        else:
            for page in export['pages']:
                print(f"\n{'='*60}")
                print(f"PAGE: {page['title']}")
                print(f"{'='*60}\n")
                print(page['content'])
    
    elif args.cmd == "notion-structure":
        print(generate_notion_structure(args.team))
    
    elif args.cmd == "list-artifacts":
        artifacts = get_artifacts(args.team)
        if artifacts:
            print(f"{'ID':<12} {'Name':<30} {'Type':<10} {'Lang':<12} {'Size':<10}")
            print("-" * 80)
            for art_id, art in artifacts.items():
                size = f"{art['size_bytes']/1024:.1f}KB"
                print(f"{art_id:<12} {art['name']:<30} {art['artifact_type']:<10} {art['language']:<12} {size:<10}")
        else:
            print("No artifacts registered")
    
    elif args.cmd == "init":
        team_dir = ensure_team_structure(args.team)
        config_path = team_dir / "config.json"
        if not config_path.exists():
            config = {
                "team_name": args.team,
                "description": args.description,
                "type": args.type,
                "created_at": timestamp(),
                "version": 1
            }
            save_json(config_path, config)
        print(f"[OK] Initialized {team_dir}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
