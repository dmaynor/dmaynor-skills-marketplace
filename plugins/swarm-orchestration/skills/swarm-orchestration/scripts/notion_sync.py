#!/usr/bin/env python3
"""
Notion Sync Orchestrator for Swarm Persistence

This script prepares the exact Notion API calls Claude should make.
Claude reads this output and executes the Notion MCP tools.

Usage:
    python3 notion_sync.py sync --team my-project --hub-id <swarm-hub-data-source-id>
    python3 notion_sync.py status --team my-project
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Import from swarm_persistence
sys.path.insert(0, str(Path(__file__).parent))
from swarm_persistence import (
    export_full,
    get_team_dir,
    load_json,
    save_json,
    timestamp,
    get_artifacts,
    get_artifact_content,
)


SWARM_HUB_DATA_SOURCE = "722ecbf3-0bee-46a4-b196-4b507d6b3d9f"


def get_notion_sync_state(team_name: str) -> dict:
    """Get Notion sync state for a team."""
    team_dir = get_team_dir(team_name)
    state_path = team_dir / "notion_sync.json"
    if state_path.exists():
        return load_json(state_path)
    return {
        "hub_row_id": None,
        "state_page_id": None,
        "conversation_page_id": None,
        "thinking_page_id": None,
        "agents_page_id": None,
        "artifact_page_ids": {},
        "last_sync_at": None,
        "sync_version": 0
    }


def save_notion_sync_state(team_name: str, state: dict) -> None:
    """Save Notion sync state."""
    team_dir = get_team_dir(team_name)
    save_json(team_dir / "notion_sync.json", state)


def prepare_sync(team_name: str, hub_data_source_id: str = None) -> dict:
    """
    Prepare sync operations for Claude to execute via Notion MCP.
    
    Returns a dict with:
    - operations: List of Notion operations to execute
    - pages_content: Full page content for each page
    """
    hub_id = hub_data_source_id or SWARM_HUB_DATA_SOURCE
    
    export = export_full(team_name)
    sync_state = get_notion_sync_state(team_name)
    
    operations = []
    pages_content = {}
    
    # =====================================================================
    # OPERATION 1: Create/Update Hub Row
    # =====================================================================
    hub_row = export["hub_row"]
    
    if sync_state.get("hub_row_id"):
        # Update existing row
        operations.append({
            "op": "update_hub_row",
            "tool": "Notion:notion-update-page",
            "params": {
                "data": {
                    "page_id": sync_state["hub_row_id"],
                    "command": "update_properties",
                    "properties": {
                        "Description": hub_row["Description"],
                        "Status": hub_row["Status"],
                        "Type": hub_row["Type"],
                        "date:Last Active:start": hub_row["date:Last Active:start"]
                    }
                }
            },
            "description": f"Update hub row for {team_name}"
        })
    else:
        # Create new row
        operations.append({
            "op": "create_hub_row",
            "tool": "Notion:notion-create-pages",
            "params": {
                "parent": {"data_source_id": hub_id},
                "pages": [{
                    "properties": hub_row
                }]
            },
            "description": f"Create hub row for {team_name}",
            "save_id_as": "hub_row_id"
        })
    
    # =====================================================================
    # OPERATION 2+: Create/Update Child Pages
    # =====================================================================
    
    page_type_map = {
        "state": "state_page_id",
        "conversation": "conversation_page_id",
        "thinking": "thinking_page_id",
        "agents": "agents_page_id"
    }
    
    for page in export["pages"]:
        page_type = page["type"]
        page_id_key = page_type_map.get(page_type)
        
        # Store content for Claude to use
        content_key = f"{page_type}_content"
        pages_content[content_key] = page["content"]
        
        if page_type == "artifact":
            # Artifacts are handled separately
            art_id = page.get("artifact_id")
            existing_id = sync_state.get("artifact_page_ids", {}).get(art_id)
            
            if existing_id:
                operations.append({
                    "op": f"update_artifact_{art_id}",
                    "tool": "Notion:notion-update-page",
                    "params": {
                        "data": {
                            "page_id": existing_id,
                            "command": "replace_content",
                            "new_str": page["content"]
                        }
                    },
                    "description": f"Update artifact page: {page['title']}"
                })
            else:
                operations.append({
                    "op": f"create_artifact_{art_id}",
                    "tool": "Notion:notion-create-pages",
                    "params": {
                        "parent": {"page_id": "$hub_row_id"},  # Placeholder
                        "pages": [{
                            "properties": {"title": page["title"]},
                            "content": page["content"]
                        }]
                    },
                    "description": f"Create artifact page: {page['title']}",
                    "save_id_as": f"artifact_{art_id}_id"
                })
        elif page_id_key:
            existing_id = sync_state.get(page_id_key)
            
            if existing_id:
                operations.append({
                    "op": f"update_{page_type}",
                    "tool": "Notion:notion-update-page",
                    "params": {
                        "data": {
                            "page_id": existing_id,
                            "command": "replace_content",
                            "new_str": page["content"]
                        }
                    },
                    "description": f"Update {page_type} page"
                })
            else:
                operations.append({
                    "op": f"create_{page_type}",
                    "tool": "Notion:notion-create-pages",
                    "params": {
                        "parent": {"page_id": "$hub_row_id"},  # Placeholder
                        "pages": [{
                            "properties": {"title": page["title"]},
                            "content": page["content"]
                        }]
                    },
                    "description": f"Create {page_type} page",
                    "save_id_as": page_id_key
                })
    
    return {
        "team_name": team_name,
        "export_version": export["version"],
        "stats": export["stats"],
        "operations": operations,
        "pages_content": pages_content,
        "current_sync_state": sync_state,
        "hub_data_source_id": hub_id
    }


def generate_claude_instructions(team_name: str, hub_data_source_id: str = None) -> str:
    """
    Generate step-by-step instructions for Claude to execute Notion sync.
    
    This is the main output - Claude reads and executes these instructions.
    """
    sync_plan = prepare_sync(team_name, hub_data_source_id)
    
    instructions = f"""# Notion Sync Instructions for {team_name}

**Generated:** {timestamp()}
**Version:** {sync_plan['export_version']}

## Session Stats
- Conversation Turns: {sync_plan['stats']['conversation_turns']}
- Thinking Blocks: {sync_plan['stats']['thinking_blocks']}
- Agent Messages: {sync_plan['stats']['agent_messages']}
- Artifacts: {sync_plan['stats']['artifacts']}
- Outputs: {sync_plan['stats']['outputs']}
- Findings: {sync_plan['stats']['findings']}

## Execution Steps

Execute these Notion tool calls in order. Save returned page IDs for subsequent operations.

"""
    
    for i, op in enumerate(sync_plan['operations'], 1):
        instructions += f"""### Step {i}: {op['description']}

**Tool:** `{op['tool']}`
"""
        if op.get('save_id_as'):
            instructions += f"**Save result page ID as:** `{op['save_id_as']}`\n"
        
        # Format params for readability
        params_json = json.dumps(op['params'], indent=2)
        instructions += f"""
```json
{params_json}
```

"""
    
    instructions += f"""
## After Sync Complete

Update sync state by calling:
```
python3 /home/claude/swarm_persistence.py ...
```

Or manually update `~/.claude/teams/{team_name}/notion_sync.json` with the page IDs returned from Notion.
"""
    
    return instructions


def main():
    parser = argparse.ArgumentParser(description="Notion Sync Orchestrator")
    sub = parser.add_subparsers(dest="cmd")
    
    # Sync command
    sync_cmd = sub.add_parser("sync", help="Prepare sync operations")
    sync_cmd.add_argument("--team", required=True)
    sync_cmd.add_argument("--hub-id", help="Override Swarm Hub data source ID")
    sync_cmd.add_argument("--format", choices=["json", "instructions"], default="instructions")
    
    # Status command
    status_cmd = sub.add_parser("status", help="Show sync status")
    status_cmd.add_argument("--team", required=True)
    
    # Save IDs command (after sync)
    save_cmd = sub.add_parser("save-ids", help="Save page IDs after sync")
    save_cmd.add_argument("--team", required=True)
    save_cmd.add_argument("--hub-row-id", help="Hub row page ID")
    save_cmd.add_argument("--state-page-id", help="State page ID")
    save_cmd.add_argument("--conversation-page-id", help="Conversation page ID")
    save_cmd.add_argument("--thinking-page-id", help="Thinking page ID")
    save_cmd.add_argument("--agents-page-id", help="Agents page ID")
    save_cmd.add_argument("--artifact", nargs=2, action="append", metavar=("ART_ID", "PAGE_ID"),
                         help="Artifact ID and page ID pair")
    
    args = parser.parse_args()
    
    if args.cmd == "sync":
        if args.format == "json":
            result = prepare_sync(args.team, args.hub_id)
            print(json.dumps(result, indent=2))
        else:
            print(generate_claude_instructions(args.team, args.hub_id))
    
    elif args.cmd == "status":
        state = get_notion_sync_state(args.team)
        print(json.dumps(state, indent=2))
    
    elif args.cmd == "save-ids":
        state = get_notion_sync_state(args.team)
        
        if args.hub_row_id:
            state["hub_row_id"] = args.hub_row_id
        if args.state_page_id:
            state["state_page_id"] = args.state_page_id
        if args.conversation_page_id:
            state["conversation_page_id"] = args.conversation_page_id
        if args.thinking_page_id:
            state["thinking_page_id"] = args.thinking_page_id
        if args.agents_page_id:
            state["agents_page_id"] = args.agents_page_id
        
        if args.artifact:
            if "artifact_page_ids" not in state:
                state["artifact_page_ids"] = {}
            for art_id, page_id in args.artifact:
                state["artifact_page_ids"][art_id] = page_id
        
        state["last_sync_at"] = timestamp()
        state["sync_version"] = state.get("sync_version", 0) + 1
        
        save_notion_sync_state(args.team, state)
        print(json.dumps(state, indent=2))
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
