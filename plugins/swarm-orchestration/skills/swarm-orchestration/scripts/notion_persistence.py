#!/usr/bin/env python3
"""
Notion Persistence for Swarm Orchestration

Export swarm state to Notion-compatible format and restore from Notion content.
Claude bridges between this script (container) and Notion MCP (connector).

Usage:
    python3 notion_persistence.py export --team my-project
    python3 notion_persistence.py export-logs --team my-project
    python3 notion_persistence.py restore --team my-project --file state.md
    python3 notion_persistence.py restore-logs --team my-project --file logs.md
    python3 notion_persistence.py schema
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


TEAMS_BASE = Path.home() / ".claude" / "teams"


def timestamp() -> str:
    """Return current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def get_sync_state_path(team_name: str) -> Path:
    """Get path to sync state file."""
    return TEAMS_BASE / team_name / "sync_state.json"


def load_sync_state(team_name: str) -> dict:
    """Load sync state (last sync timestamps, page IDs)."""
    path = get_sync_state_path(team_name)
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"last_logs_sync_ts": None, "logs_page_id": None}


def save_sync_state(team_name: str, state: dict) -> None:
    """Save sync state."""
    path = get_sync_state_path(team_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


def sync_logs(team_name: str) -> dict:
    """
    Export only messages since last sync for incremental Notion update.
    
    Returns dict with:
        - markdown: Content to append to Notion logs page
        - new_messages: Count of messages in this batch
        - last_sync_ts: Previous sync timestamp (None if first sync)
        - current_sync_ts: Timestamp for this sync
        - is_first_sync: True if no prior sync
    """
    team_dir = TEAMS_BASE / team_name
    if not team_dir.exists():
        print(f"[ERR] Team not found: {team_dir}", file=sys.stderr)
        sys.exit(1)
    
    sync_state = load_sync_state(team_name)
    last_sync_ts = sync_state.get("last_logs_sync_ts")
    current_sync_ts = timestamp()
    
    channel = load_jsonl(team_dir / "channel.jsonl")
    
    # Filter to messages after last sync
    if last_sync_ts:
        last_dt = datetime.fromisoformat(last_sync_ts.replace("Z", "+00:00"))
        new_messages = [
            m for m in channel
            if datetime.fromisoformat(m.get("ts", "1970-01-01T00:00:00Z").replace("Z", "+00:00")) > last_dt
        ]
    else:
        new_messages = channel
    
    is_first_sync = last_sync_ts is None
    
    if not new_messages:
        return {
            "team_name": team_name,
            "markdown": "",
            "new_messages": 0,
            "last_sync_ts": last_sync_ts,
            "current_sync_ts": current_sync_ts,
            "is_first_sync": is_first_sync,
            "logs_page_id": sync_state.get("logs_page_id")
        }
    
    # Build markdown for append
    if is_first_sync:
        md = f"# {team_name} - Channel Logs\n\n"
        md += f"**Created:** {current_sync_ts}\n\n---\n\n"
    else:
        md = f"\n---\n\n**Sync:** {current_sync_ts} (+{len(new_messages)} messages)\n\n"
    
    # Group by date
    current_date = None
    for msg in new_messages:
        ts = msg.get("ts", "")
        msg_date = ts[:10] if ts else "Unknown"
        
        if msg_date != current_date:
            current_date = msg_date
            md += f"\n## {current_date}\n\n"
        
        sender = msg.get("from", "?")
        to = msg.get("to", ["@all"])
        to_str = ", ".join(to) if isinstance(to, list) and to else "@all"
        msg_type = msg.get("type", "message")
        reasoning = msg.get("reasoning", "")
        content = msg.get("content", "")
        
        md += f"**[{ts[11:19] if len(ts) > 19 else ts}] @{sender} → {to_str}**"
        if msg_type != "message":
            md += f" ({msg_type})"
        md += "\n\n"
        if reasoning:
            md += f"> {reasoning}\n\n"
        md += f"{content}\n\n"
    
    # Raw JSONL for this batch (for restoration)
    md += f"\n<details><summary>Raw batch ({len(new_messages)} messages)</summary>\n\n```jsonl\n"
    for msg in new_messages:
        md += json.dumps(msg) + "\n"
    md += "```\n\n</details>\n"
    
    return {
        "team_name": team_name,
        "markdown": md,
        "new_messages": len(new_messages),
        "last_sync_ts": last_sync_ts,
        "current_sync_ts": current_sync_ts,
        "is_first_sync": is_first_sync,
        "logs_page_id": sync_state.get("logs_page_id")
    }


def confirm_sync(team_name: str, logs_page_id: Optional[str] = None) -> None:
    """
    Confirm sync completed successfully. Updates last_sync_ts.
    Call this AFTER successfully pushing to Notion.
    
    Args:
        team_name: Team name
        logs_page_id: Notion page ID for logs (save for future syncs)
    """
    sync_state = load_sync_state(team_name)
    sync_state["last_logs_sync_ts"] = timestamp()
    if logs_page_id:
        sync_state["logs_page_id"] = logs_page_id
    save_sync_state(team_name, sync_state)
    print(f"[OK] Sync confirmed at {sync_state['last_logs_sync_ts']}")


def get_sync_status(team_name: str) -> dict:
    """Get current sync status for a team."""
    team_dir = TEAMS_BASE / team_name
    if not team_dir.exists():
        return {"error": f"Team not found: {team_name}"}
    
    sync_state = load_sync_state(team_name)
    channel = load_jsonl(team_dir / "channel.jsonl")
    
    last_sync_ts = sync_state.get("last_logs_sync_ts")
    
    if last_sync_ts:
        last_dt = datetime.fromisoformat(last_sync_ts.replace("Z", "+00:00"))
        pending = len([
            m for m in channel
            if datetime.fromisoformat(m.get("ts", "1970-01-01T00:00:00Z").replace("Z", "+00:00")) > last_dt
        ])
    else:
        pending = len(channel)
    
    return {
        "team_name": team_name,
        "total_messages": len(channel),
        "pending_sync": pending,
        "last_sync_ts": last_sync_ts,
        "logs_page_id": sync_state.get("logs_page_id"),
        "synced": last_sync_ts is not None
    }


def load_json(path: Path) -> dict:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def load_jsonl(path: Path) -> list[dict]:
    msgs = []
    if path.exists():
        with open(path) as f:
            for line in f:
                if line.strip():
                    try:
                        msgs.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return msgs


def export_logs(team_name: str) -> dict:
    """Export full channel logs to Notion-ready format."""
    team_dir = TEAMS_BASE / team_name
    if not team_dir.exists():
        print(f"[ERR] Team not found: {team_dir}", file=sys.stderr)
        sys.exit(1)
    
    channel = load_jsonl(team_dir / "channel.jsonl")
    
    # Build markdown for logs page
    md = f"# {team_name} - Channel Logs\n\n"
    md += f"**Exported:** {timestamp()}\n"
    md += f"**Total Messages:** {len(channel)}\n\n---\n\n"
    
    # Group by date for readability
    current_date = None
    for msg in channel:
        ts = msg.get("ts", "")
        msg_date = ts[:10] if ts else "Unknown"
        
        if msg_date != current_date:
            current_date = msg_date
            md += f"\n## {current_date}\n\n"
        
        sender = msg.get("from", "?")
        to = msg.get("to", ["@all"])
        to_str = ", ".join(to) if isinstance(to, list) else str(to)
        msg_type = msg.get("type", "message")
        reasoning = msg.get("reasoning", "")
        content = msg.get("content", "")
        
        md += f"### [{ts[11:19] if len(ts) > 19 else ts}] @{sender} → {to_str}\n\n"
        if msg_type != "message":
            md += f"**Type:** {msg_type}\n\n"
        if reasoning:
            md += f"**Reasoning:** {reasoning}\n\n"
        md += f"{content}\n\n---\n\n"
    
    # Raw JSONL for restoration
    md += "\n## Raw Logs\n\n"
    md += "<details><summary>channel.jsonl</summary>\n\n```jsonl\n"
    for msg in channel:
        md += json.dumps(msg) + "\n"
    md += "```\n\n</details>\n"
    
    return {
        "team_name": team_name,
        "exported_at": timestamp(),
        "message_count": len(channel),
        "markdown": md
    }


def restore_logs(team_name: str, content: str) -> None:
    """Restore channel logs from Notion page content."""
    team_dir = TEAMS_BASE / team_name
    team_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract JSONL from content
    pattern = r'channel\.jsonl.*?```jsonl\s*(.*?)```'
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
    
    if match:
        jsonl_content = match.group(1).strip()
        channel_file = team_dir / "channel.jsonl"
        
        # Parse and validate each line
        valid_msgs = []
        for line in jsonl_content.split("\n"):
            line = line.strip()
            if line:
                try:
                    msg = json.loads(line)
                    valid_msgs.append(msg)
                except json.JSONDecodeError:
                    pass
        
        # Write validated messages
        with open(channel_file, "w") as f:
            for msg in valid_msgs:
                f.write(json.dumps(msg) + "\n")
        
        print(f"[OK] Restored {len(valid_msgs)} messages to channel.jsonl")
    else:
        print("[WARN] No channel.jsonl block found in content", file=sys.stderr)


def export_team(team_name: str, include_full_logs: bool = False) -> dict:
    """
    Export team state to Notion-ready format with session context and versioning.
    
    Includes:
    - Session context (original_prompt, td_reasoning, td_response)
    - Config, Tasks, Agents, Findings
    - Channel summary (last 20) or full logs
    - Version tracking for existing projects
    """
    team_dir = TEAMS_BASE / team_name
    if not team_dir.exists():
        print(f"[ERR] Team not found: {team_dir}", file=sys.stderr)
        sys.exit(1)
    
    config = load_json(team_dir / "config.json")
    tasks_data = load_json(team_dir / "tasks.json")
    agents_data = load_json(team_dir / "agents.json")
    findings_data = load_json(team_dir / "findings.json")
    channel = load_jsonl(team_dir / "channel.jsonl")
    sync_state = load_sync_state(team_name)
    
    tasks = list(tasks_data.get("tasks", {}).values())
    agents = list(agents_data.get("agents", {}).values())
    findings = list(findings_data.get("findings", {}).values())
    
    # Version tracking
    version = config.get("version", 1)
    
    # Build markdown
    md = f"# {team_name} - State (v{version})\n\n**Exported:** {timestamp()}\n\n"
    
    # Session context section (original prompt, TD reasoning, TD response)
    original_prompt = config.get("original_prompt", "")
    td_reasoning = config.get("td_reasoning", "")
    td_response = config.get("td_response", "")
    
    if original_prompt or td_reasoning or td_response:
        md += "---\n\n## Session Context\n\n"
        
        if original_prompt:
            md += "### Original User Prompt\n\n"
            md += f"```\n{original_prompt}\n```\n\n"
        
        if td_reasoning:
            md += "### TD Background Reasoning\n\n"
            # Format multi-line reasoning as blockquote
            reasoning_lines = td_reasoning.split('\n')
            for line in reasoning_lines:
                md += f"> {line}\n"
            md += "\n"
        
        if td_response:
            md += "### TD Final Response\n\n"
            md += f"{td_response}\n\n"
    
    md += "---\n\n"
    
    # Config section (exclude session fields)
    md += "## Config\n\n"
    config_display = {k: v for k, v in config.items() 
                      if k not in ("original_prompt", "td_reasoning", "td_response")}
    md += f"```json\n{json.dumps(config_display, indent=2)}\n```\n\n---\n\n"
    
    # Tasks table
    md += f"## Tasks ({len(tasks)})\n\n| ID | Subject | Status | Assignee |\n|----|---------|--------|----------|\n"
    for t in tasks:
        md += f"| {t.get('task_id','')} | {t.get('subject','')[:40]} | {t.get('status','')} | @{t.get('assignee','-')} |\n"
    
    # Agents table
    md += f"\n---\n\n## Agents ({len(agents)})\n\n| Name | Role | Autonomy | Status |\n|------|------|----------|--------|\n"
    for a in agents:
        md += f"| @{a.get('name','')} | {a.get('role','')} | {a.get('autonomy','')} | {a.get('status','')} |\n"
    
    # Findings table
    if findings:
        md += f"\n---\n\n## Findings ({len(findings)})\n\n| ID | Severity | Title | Resolved |\n|----|----------|-------|----------|\n"
        for f in findings:
            md += f"| {f.get('finding_id','')} | {f.get('severity','')} | {f.get('title','')[:40]} | {'✓' if f.get('resolved') else '✗'} |\n"
    
    # Channel log summary (last 20 for quick view)
    md += f"\n---\n\n## Channel Summary ({len(channel)} total, showing last 20)\n\n"
    for m in channel[-20:]:
        md += f"**[{m.get('ts','')[:19]}] @{m.get('from','?')}**: {m.get('content','')[:150]}\n\n"
    
    if len(channel) > 20:
        md += f"\n*{len(channel) - 20} earlier messages in separate logs page*\n\n"
    
    # Raw state for restoration
    md += "\n---\n\n## Raw State\n\n"
    md += f"<details><summary>tasks.json</summary>\n\n```json\n{json.dumps(tasks_data, indent=2)}\n```\n\n</details>\n\n"
    md += f"<details><summary>agents.json</summary>\n\n```json\n{json.dumps(agents_data, indent=2)}\n```\n\n</details>\n\n"
    md += f"<details><summary>findings.json</summary>\n\n```json\n{json.dumps(findings_data, indent=2)}\n```\n\n</details>\n\n"
    md += f"<details><summary>config.json</summary>\n\n```json\n{json.dumps(config, indent=2)}\n```\n\n</details>\n\n"
    
    # Optionally include full logs in state page
    if include_full_logs:
        md += f"<details><summary>channel.jsonl ({len(channel)} messages)</summary>\n\n```jsonl\n"
        for msg in channel:
            md += json.dumps(msg) + "\n"
        md += "```\n\n</details>\n"
    
    return {
        "team_name": team_name,
        "version": version,
        "exported_at": timestamp(),
        "markdown": md,
        "message_count": len(channel),
        "has_session_context": bool(original_prompt or td_reasoning or td_response),
        "logs_page_id": sync_state.get("logs_page_id"),
        "hub_row": {
            "Project": team_name,
            "Description": config.get("description", ""),
            "Status": "active",
            "Type": config.get("type", "development"),
            "date:Created:start": config.get("created_at", "")[:10] if config.get("created_at") else None,
            "date:Last Active:start": timestamp()[:10]
        }
    }


def set_session_context(team_name: str, original_prompt: str = None, 
                        td_reasoning: str = None, td_response: str = None) -> None:
    """
    Set session context fields in config.
    
    Call this at swarm initialization with the user's original prompt,
    and update td_reasoning/td_response as TD processes the request.
    """
    team_dir = TEAMS_BASE / team_name
    if not team_dir.exists():
        print(f"[ERR] Team not found: {team_dir}", file=sys.stderr)
        sys.exit(1)
    
    config_path = team_dir / "config.json"
    config = load_json(config_path)
    
    if original_prompt is not None:
        config["original_prompt"] = original_prompt
    if td_reasoning is not None:
        config["td_reasoning"] = td_reasoning
    if td_response is not None:
        config["td_response"] = td_response
    
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"[OK] Session context updated for {team_name}")


def increment_version(team_name: str) -> int:
    """
    Increment the version number in config. Returns new version.
    
    Call this before saving when a project already exists in Notion.
    """
    team_dir = TEAMS_BASE / team_name
    if not team_dir.exists():
        print(f"[ERR] Team not found: {team_dir}", file=sys.stderr)
        sys.exit(1)
    
    config_path = team_dir / "config.json"
    config = load_json(config_path)
    
    current = config.get("version", 1)
    new_version = current + 1
    config["version"] = new_version
    
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"[OK] Version incremented: v{current} -> v{new_version}")
    return new_version


def restore_team(team_name: str, content: str, include_logs: bool = False) -> None:
    """Restore team state from Notion page content."""
    team_dir = TEAMS_BASE / team_name
    team_dir.mkdir(parents=True, exist_ok=True)
    (team_dir / "artifacts").mkdir(exist_ok=True)
    
    def extract_json(content: str, marker: str) -> Optional[dict]:
        pattern = rf'{marker}.*?```json\s*(.*?)```'
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        return None
    
    for name in ["tasks", "agents", "findings", "config"]:
        data = extract_json(content, f"{name}.json")
        if data:
            with open(team_dir / f"{name}.json", "w") as f:
                json.dump(data, f, indent=2)
            print(f"[OK] {name}.json")
    
    # Restore logs if present and requested
    if include_logs:
        pattern = r'channel\.jsonl.*?```jsonl\s*(.*?)```'
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            jsonl_content = match.group(1).strip()
            valid_msgs = []
            for line in jsonl_content.split("\n"):
                line = line.strip()
                if line:
                    try:
                        valid_msgs.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            
            with open(team_dir / "channel.jsonl", "w") as f:
                for msg in valid_msgs:
                    f.write(json.dumps(msg) + "\n")
            print(f"[OK] channel.jsonl ({len(valid_msgs)} messages)")
    
    # Initialize channel if not restored
    if not (team_dir / "channel.jsonl").exists():
        msg = {"ts": timestamp(), "from": "td", "to": ["@all"], "type": "system",
               "reasoning": "Restored from Notion", "content": f"RESTORED: {team_name}"}
        with open(team_dir / "channel.jsonl", "w") as f:
            f.write(json.dumps(msg) + "\n")
        print("[OK] channel.jsonl (initialized)")
    
    print(f"\n[DONE] {team_dir}")


def print_schema():
    """Print Notion database schema."""
    print("""Notion:notion-create-database({
  title: [{ type: "text", text: { content: "Swarm Hub" } }],
  properties: {
    "Project": { type: "title", title: {} },
    "Description": { type: "rich_text", rich_text: {} },
    "Status": { type: "select", select: { options: [
      { name: "active", color: "green" },
      { name: "paused", color: "yellow" },
      { name: "complete", color: "blue" },
      { name: "archived", color: "gray" }
    ]}},
    "Type": { type: "select", select: { options: [
      { name: "security-assessment", color: "red" },
      { name: "development", color: "blue" },
      { name: "prompt-workbench", color: "purple" },
      { name: "exercise", color: "orange" }
    ]}},
    "Created": { type: "date", date: {} },
    "Last Active": { type: "date", date: {} }
  }
})""")


def main():
    parser = argparse.ArgumentParser(description="Notion Persistence")
    sub = parser.add_subparsers(dest="cmd")
    
    # Export state
    exp = sub.add_parser("export", help="Export team state")
    exp.add_argument("--team", required=True)
    exp.add_argument("--format", choices=["markdown", "json"], default="json")
    exp.add_argument("--include-logs", action="store_true", help="Include full channel logs in export")
    
    # Export logs only
    exp_logs = sub.add_parser("export-logs", help="Export channel logs separately")
    exp_logs.add_argument("--team", required=True)
    exp_logs.add_argument("--format", choices=["markdown", "json"], default="json")
    
    # Sync logs (incremental)
    sync_cmd = sub.add_parser("sync-logs", help="Export only new messages since last sync")
    sync_cmd.add_argument("--team", required=True)
    sync_cmd.add_argument("--format", choices=["markdown", "json"], default="json")
    
    # Confirm sync completed
    confirm_cmd = sub.add_parser("confirm-sync", help="Confirm sync completed (updates last_sync_ts)")
    confirm_cmd.add_argument("--team", required=True)
    confirm_cmd.add_argument("--logs-page-id", help="Notion page ID for logs")
    
    # Sync status
    status_cmd = sub.add_parser("sync-status", help="Show sync status")
    status_cmd.add_argument("--team", required=True)
    
    # Restore state
    res = sub.add_parser("restore", help="Restore team state")
    res.add_argument("--team", required=True)
    res.add_argument("--content", help="Notion content (or use --file)")
    res.add_argument("--file", help="File with Notion content")
    res.add_argument("--include-logs", action="store_true", help="Also restore channel logs from content")
    
    # Restore logs only
    res_logs = sub.add_parser("restore-logs", help="Restore channel logs separately")
    res_logs.add_argument("--team", required=True)
    res_logs.add_argument("--content", help="Notion content (or use --file)")
    res_logs.add_argument("--file", help="File with Notion content")
    
    # Set session context
    ctx_cmd = sub.add_parser("set-context", help="Set session context (prompt, reasoning, response)")
    ctx_cmd.add_argument("--team", required=True)
    ctx_cmd.add_argument("--prompt", help="Original user prompt")
    ctx_cmd.add_argument("--reasoning", help="TD background reasoning")
    ctx_cmd.add_argument("--response", help="TD final response")
    ctx_cmd.add_argument("--prompt-file", help="Read prompt from file")
    ctx_cmd.add_argument("--reasoning-file", help="Read reasoning from file")
    ctx_cmd.add_argument("--response-file", help="Read response from file")
    
    # Increment version
    ver_cmd = sub.add_parser("increment-version", help="Increment version number before saving existing project")
    ver_cmd.add_argument("--team", required=True)
    
    # Schema
    sub.add_parser("schema", help="Print Notion database schema")
    
    args = parser.parse_args()
    
    if args.cmd == "export":
        result = export_team(args.team, include_full_logs=args.include_logs)
        print(result["markdown"] if args.format == "markdown" else json.dumps(result, indent=2))
    
    elif args.cmd == "export-logs":
        result = export_logs(args.team)
        print(result["markdown"] if args.format == "markdown" else json.dumps(result, indent=2))
    
    elif args.cmd == "sync-logs":
        result = sync_logs(args.team)
        print(result["markdown"] if args.format == "markdown" else json.dumps(result, indent=2))
    
    elif args.cmd == "confirm-sync":
        confirm_sync(args.team, logs_page_id=args.logs_page_id)
    
    elif args.cmd == "sync-status":
        result = get_sync_status(args.team)
        print(json.dumps(result, indent=2))
    
    elif args.cmd == "restore":
        content = ""
        if args.file:
            content = open(args.file).read()
        elif args.content:
            content = args.content
        else:
            content = sys.stdin.read()
        if not content:
            print("[ERR] No content", file=sys.stderr)
            sys.exit(1)
        restore_team(args.team, content, include_logs=args.include_logs)
    
    elif args.cmd == "restore-logs":
        content = ""
        if args.file:
            content = open(args.file).read()
        elif args.content:
            content = args.content
        else:
            content = sys.stdin.read()
        if not content:
            print("[ERR] No content", file=sys.stderr)
            sys.exit(1)
        restore_logs(args.team, content)
    
    elif args.cmd == "set-context":
        prompt = args.prompt
        reasoning = args.reasoning
        response = args.response
        
        # Read from files if specified
        if args.prompt_file:
            prompt = open(args.prompt_file).read()
        if args.reasoning_file:
            reasoning = open(args.reasoning_file).read()
        if args.response_file:
            response = open(args.response_file).read()
        
        set_session_context(args.team, original_prompt=prompt, 
                           td_reasoning=reasoning, td_response=response)
    
    elif args.cmd == "increment-version":
        new_ver = increment_version(args.team)
        print(json.dumps({"team_name": args.team, "version": new_ver}))
    
    elif args.cmd == "schema":
        print_schema()
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
