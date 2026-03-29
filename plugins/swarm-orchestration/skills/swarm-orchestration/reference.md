---
parent: SKILL.md
---

# Swarm Orchestration Reference

Detailed API documentation, persistence model, Notion sync, channel implementation, code examples, and file structure.

## Quick Start: Full Session Persistence

### Initialize Session

```bash
# Initialize comprehensive persistence
python3 scripts/swarm_persistence.py init \
  --team {name} \
  --description "Project description" \
  --type development

# Record the user's original request
python3 scripts/swarm_persistence.py add-turn \
  --team {name} \
  --role user \
  --content "User's original request..."
```

### During Session

```bash
# Record assistant responses
python3 scripts/swarm_persistence.py add-turn \
  --team {name} \
  --role assistant \
  --content "Claude's response..."

# Record extended thinking (if available)
python3 scripts/swarm_persistence.py add-thinking \
  --team {name} \
  --content "Thinking content..." \
  --tokens 5000

# Register artifacts as they're created
python3 scripts/swarm_persistence.py add-artifact \
  --team {name} \
  --path /path/to/output/file.py \
  --description "Main implementation"

# Or scan entire output directory
python3 scripts/swarm_persistence.py scan-artifacts \
  --team {name} \
  --dir /mnt/user-data/outputs/project-name
```

### At Session End

```bash
# Set overall summary
python3 scripts/swarm_persistence.py set-summary \
  --team {name} \
  --summary "Completed X, Y, Z. Delivered A, B, C."

# Record final output
python3 scripts/swarm_persistence.py add-output \
  --team {name} \
  --title "Project Deliverables" \
  --content "Summary of what was delivered..." \
  --type report \
  --artifacts ART-0001 ART-0002 ART-0003

# Export everything
python3 scripts/swarm_persistence.py export-full --team {name}
```

### Sync to Notion

```bash
# Generate sync instructions
python3 scripts/notion_sync.py sync --team {name}

# After pushing to Notion, save page IDs
python3 scripts/notion_sync.py save-ids \
  --team {name} \
  --hub-row-id {id} \
  --state-page-id {id} \
  --conversation-page-id {id} \
  --thinking-page-id {id}
```

---

## Persistence Scripts Reference

### swarm_persistence.py (Comprehensive Tracking)

```bash
# Initialize
python3 scripts/swarm_persistence.py init --team NAME --description DESC --type TYPE

# Conversation tracking
python3 scripts/swarm_persistence.py add-turn --team NAME --role user|assistant --content TEXT
python3 scripts/swarm_persistence.py add-thinking --team NAME --content TEXT [--turn N] [--tokens N]

# Artifact management
python3 scripts/swarm_persistence.py add-artifact --team NAME --path FILE [--description DESC]
python3 scripts/swarm_persistence.py scan-artifacts --team NAME --dir PATH [--prefix DESC]
python3 scripts/swarm_persistence.py list-artifacts --team NAME

# Output tracking
python3 scripts/swarm_persistence.py add-output --team NAME --title TITLE --content TEXT --type TYPE [--artifacts IDS...]
python3 scripts/swarm_persistence.py set-summary --team NAME --summary TEXT

# Export
python3 scripts/swarm_persistence.py export-full --team NAME [--format json|pages]
```

### notion_sync.py (Sync Orchestration)

```bash
# Generate sync instructions
python3 scripts/notion_sync.py sync --team NAME [--hub-id ID] [--format json|instructions]

# Check status
python3 scripts/notion_sync.py status --team NAME

# Save page IDs after sync
python3 scripts/notion_sync.py save-ids --team NAME --hub-row-id ID --state-page-id ID ...
```

### notion_persistence.py (Legacy - Still Supported)

```bash
# Session context
python3 scripts/notion_persistence.py set-context --team NAME --prompt "..." --reasoning "..."

# Incremental log sync
python3 scripts/notion_persistence.py sync-logs --team NAME
python3 scripts/notion_persistence.py confirm-sync --team NAME --logs-page-id ID
python3 scripts/notion_persistence.py sync-status --team NAME

# Full export/restore
python3 scripts/notion_persistence.py export --team NAME [--include-logs]
python3 scripts/notion_persistence.py restore --team NAME --file state.md
```

### channel.py (Agent Communication)

```bash
# Read channel
python3 scripts/channel.py read --team NAME [--mine HANDLE] [--since TS] [--last N]

# Write to channel
python3 scripts/channel.py write --team NAME --from AGENT --reasoning WHY --content MSG [--to @HANDLES]

# Initialize channel
python3 scripts/channel.py init --team NAME
```

---

## Notion Page Structure

When persisted to Notion, each project creates:

```
Swarm Hub (Database)
└── project-name (Row)
    ├── project-name - State v{N}         # Session state, findings, stats
    ├── project-name - Conversation       # User <> Claude dialogue
    ├── project-name - Thinking           # Extended thinking blocks
    ├── project-name - Agent Logs         # Channel communication
    └── project-name - Artifacts/
        ├── main.py                       # Individual artifact pages
        ├── config.yaml
        └── README.md
```

---

## Artifact Types

The persistence system auto-detects file types:

| Extension | Type | Language |
|-----------|------|----------|
| `.py` | code | python |
| `.js`, `.ts`, `.jsx`, `.tsx` | code | javascript/typescript |
| `.sh`, `.bash` | code | bash |
| `.rs`, `.go`, `.java`, `.c`, `.cpp` | code | respective |
| `.json`, `.yaml`, `.yml`, `.toml` | config | respective |
| `.md`, `.txt`, `.rst`, `.html` | document | respective |

---

## Full Command Reference

| Action | Command |
|--------|---------|
| Create team | `Teammate({ operation: "spawnTeam", team_name: "X" })` |
| Create task | `TaskCreate({ subject: "...", description: "..." })` |
| Set dependency | `TaskUpdate({ taskId: "N", addBlockedBy: ["M"] })` |
| Spawn agent | `Task({ team_name: "X", name: "role", prompt: "...", run_in_background: true })` |
| Read channel | `cat ~/.claude/teams/X/channel.jsonl \| tail -50` |
| Shutdown | `Teammate({ operation: "requestShutdown", target_agent_id: "role" })` |
| **Init persistence** | `python3 scripts/swarm_persistence.py init --team X --description "..."` |
| **Add turn** | `python3 scripts/swarm_persistence.py add-turn --team X --role user --content "..."` |
| **Add thinking** | `python3 scripts/swarm_persistence.py add-thinking --team X --content "..."` |
| **Add artifact** | `python3 scripts/swarm_persistence.py add-artifact --team X --path /path/to/file` |
| **Scan artifacts** | `python3 scripts/swarm_persistence.py scan-artifacts --team X --dir /path` |
| **Add output** | `python3 scripts/swarm_persistence.py add-output --team X --title "..." --content "..."` |
| **Set summary** | `python3 scripts/swarm_persistence.py set-summary --team X --summary "..."` |
| **Export full** | `python3 scripts/swarm_persistence.py export-full --team X` |
| **Prepare sync** | `python3 scripts/notion_sync.py sync --team X` |
| **Save sync IDs** | `python3 scripts/notion_sync.py save-ids --team X --hub-row-id {id}` |
| Set context | `python3 scripts/notion_persistence.py set-context --team X --prompt "..."` |
| Sync logs | `python3 scripts/notion_persistence.py sync-logs --team X` |
| Confirm sync | `python3 scripts/notion_persistence.py confirm-sync --team X --logs-page-id {id}` |
| Sync status | `python3 scripts/notion_persistence.py sync-status --team X` |
| Increment ver | `python3 scripts/notion_persistence.py increment-version --team X` |
| Save state | `python3 scripts/notion_persistence.py export --team X` |
| Load state | `python3 scripts/notion_persistence.py restore --team X --file state.md` |

---

## File Structure

```
~/.claude/teams/{team-name}/
├── config.json              # Team configuration
├── tasks.json               # Task tracking
├── agents.json              # Agent state
├── findings.json            # Security findings (if applicable)
├── channel.jsonl            # Agent communication log
├── conversation.jsonl       # User <> Claude dialogue
├── thinking.jsonl           # Claude thinking blocks
├── outputs.json             # Final deliverables
├── notion_sync.json         # Sync state (page IDs, timestamps)
├── sync_state.json          # Legacy sync state
└── artifacts/
    ├── manifest.json        # Artifact registry
    ├── code/                # Code files
    ├── config/              # Config files
    └── docs/                # Documentation
```
