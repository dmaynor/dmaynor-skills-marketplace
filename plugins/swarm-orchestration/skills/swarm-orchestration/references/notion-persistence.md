# Notion Persistence Reference

Comprehensive persistence for swarm projects - captures conversation, thinking, agent logs, artifacts, and outputs.

## Notion Structure

```
🗂️ Swarm Hub (Database)
└── 📄 project-name (Row)
    ├── 📄 project-name - State v{N}         # Session state, findings, config
    ├── 📄 project-name - Conversation       # User ↔ Claude dialogue
    ├── 📄 project-name - Thinking           # Extended thinking blocks
    ├── 📄 project-name - Agent Logs         # Channel communication
    └── 📄 Artifacts/
        ├── 📄 main.py                       # Code files
        ├── 📄 config.yaml                   # Config files
        └── 📄 README.md                     # Documentation
```

## Setup (One-Time)

Create Swarm Hub database:

```javascript
Notion:notion-create-database({
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
})
```

Record the `data_source_id` from response for future operations.

---

## Comprehensive Persistence (New)

The new `swarm_persistence.py` captures everything:

### What Gets Tracked

| Component | Storage | Description |
|-----------|---------|-------------|
| Conversation | `conversation.jsonl` | Every user ↔ Claude turn |
| Thinking | `thinking.jsonl` | Extended thinking blocks with token counts |
| Artifacts | `artifacts/` directory | Code, config, docs with checksums |
| Outputs | `outputs.json` | Final deliverables with artifact links |
| Agent Logs | `channel.jsonl` | Inter-agent communication |

### Initialize Session

```bash
python3 scripts/swarm_persistence.py init \
  --team my-project \
  --description "Building secure auth system" \
  --type development
```

### Track Conversation

```bash
# Record user message
python3 scripts/swarm_persistence.py add-turn \
  --team my-project \
  --role user \
  --content "Build me a secure authentication system with MFA"

# Record assistant response
python3 scripts/swarm_persistence.py add-turn \
  --team my-project \
  --role assistant \
  --content "I'll design a JWT-based auth system with TOTP MFA..."
```

### Track Thinking

```bash
python3 scripts/swarm_persistence.py add-thinking \
  --team my-project \
  --content "Analyzing requirements: need secure session management..." \
  --tokens 5000 \
  --turn 1
```

### Register Artifacts

```bash
# Single file
python3 scripts/swarm_persistence.py add-artifact \
  --team my-project \
  --path /mnt/user-data/outputs/auth/main.py \
  --description "Main authentication module"

# Scan directory for all files
python3 scripts/swarm_persistence.py scan-artifacts \
  --team my-project \
  --dir /mnt/user-data/outputs/auth \
  --prefix "Auth system"
```

### Track Outputs

```bash
python3 scripts/swarm_persistence.py add-output \
  --team my-project \
  --title "Authentication System" \
  --content "Complete JWT auth with TOTP MFA, rate limiting, and tests" \
  --type deliverable \
  --artifacts ART-0001 ART-0002 ART-0003

python3 scripts/swarm_persistence.py set-summary \
  --team my-project \
  --summary "Delivered production-ready auth system with full test coverage"
```

### Export Everything

```bash
# Full export with all pages
python3 scripts/swarm_persistence.py export-full --team my-project

# Returns JSON with:
# - pages: Array of page content ready for Notion
# - stats: Message counts, artifact counts, etc.
```

### Sync to Notion

```bash
# Generate sync instructions
python3 scripts/notion_sync.py sync --team my-project

# Execute Notion tool calls (Claude does this)
# Creates: hub row, state page, conversation page, thinking page, agent logs page, artifact pages

# Save page IDs after sync
python3 scripts/notion_sync.py save-ids \
  --team my-project \
  --hub-row-id abc123 \
  --state-page-id def456 \
  --conversation-page-id ghi789

# Check sync status
python3 scripts/notion_sync.py status --team my-project
```

---

## Legacy Persistence (Still Supported)

The original `notion_persistence.py` for session context and incremental log sync.

### Session Context (Audit Trail)

```bash
# Set original prompt
python3 scripts/notion_persistence.py set-context --team my-project \
  --prompt "Build a secure authentication system"

# Update TD reasoning
python3 scripts/notion_persistence.py set-context --team my-project \
  --reasoning "Decomposing into: design, impl, review tasks..."

# Set final response
python3 scripts/notion_persistence.py set-context --team my-project \
  --response "Authentication system complete with MFA support..."
```

### Incremental Log Sync

```bash
# Check pending messages
python3 scripts/notion_persistence.py sync-status --team my-project

# Export only new messages since last sync
python3 scripts/notion_persistence.py sync-logs --team my-project

# After pushing to Notion, confirm sync
python3 scripts/notion_persistence.py confirm-sync \
  --team my-project \
  --logs-page-id abc123
```

### Version Management

```bash
# Increment version before saving existing project
python3 scripts/notion_persistence.py increment-version --team my-project

# Export with version number
python3 scripts/notion_persistence.py export --team my-project
```

### Full Export/Restore

```bash
# Export state (last 20 messages in summary)
python3 scripts/notion_persistence.py export --team my-project

# Export with full logs
python3 scripts/notion_persistence.py export --team my-project --include-logs

# Restore from Notion content
python3 scripts/notion_persistence.py restore --team my-project --file state.md
```

---

## Artifact Types

Auto-detected based on file extension:

| Extension | Type | Language |
|-----------|------|----------|
| `.py` | code | python |
| `.js`, `.mjs`, `.cjs` | code | javascript |
| `.ts`, `.tsx` | code | typescript |
| `.jsx` | code | javascript |
| `.sh`, `.bash` | code | bash |
| `.rs` | code | rust |
| `.go` | code | go |
| `.java` | code | java |
| `.c`, `.h` | code | c |
| `.cpp`, `.hpp`, `.cc` | code | cpp |
| `.rb` | code | ruby |
| `.php` | code | php |
| `.swift` | code | swift |
| `.kt` | code | kotlin |
| `.scala` | code | scala |
| `.sql` | code | sql |
| `.r`, `.R` | code | r |
| `.lua` | code | lua |
| `.pl`, `.pm` | code | perl |
| `.hs` | code | haskell |
| `.ex`, `.exs` | code | elixir |
| `.clj` | code | clojure |
| `.vue` | code | vue |
| `.svelte` | code | svelte |
| `.json` | config | json |
| `.yaml`, `.yml` | config | yaml |
| `.toml` | config | toml |
| `.ini`, `.cfg` | config | ini |
| `.env`, `.env.*` | config | plain text |
| `.xml` | config | xml |
| `.conf` | config | plain text |
| `.md` | document | markdown |
| `.txt` | document | plain text |
| `.rst` | document | plain text |
| `.html`, `.htm` | document | html |
| `.css`, `.scss`, `.sass`, `.less` | document | css |
| `.csv`, `.tsv` | document | plain text |
| `.log` | document | plain text |

---

## Container State Files

```
~/.claude/teams/{name}/
├── config.json              # Team config, session context, version
├── tasks.json               # Task tracking
├── agents.json              # Agent state
├── findings.json            # Security findings
├── channel.jsonl            # Agent communication
├── conversation.jsonl       # User ↔ Claude dialogue (NEW)
├── thinking.jsonl           # Extended thinking (NEW)
├── outputs.json             # Final deliverables (NEW)
├── notion_sync.json         # Sync state - page IDs (NEW)
├── sync_state.json          # Legacy sync state
└── artifacts/               # (NEW)
    ├── manifest.json        # Artifact registry
    ├── code/                # Code files
    ├── config/              # Config files
    └── docs/                # Documentation
```

### config.json Schema

```json
{
  "team_name": "project-name",
  "description": "Project description",
  "type": "development",
  "created_at": "2026-01-26T10:00:00.000Z",
  "version": 1,
  "original_prompt": "User's original request...",
  "td_reasoning": "TD's analysis and planning...",
  "td_response": "Final synthesized response..."
}
```

### artifacts/manifest.json Schema

```json
{
  "artifacts": {
    "ART-0001": {
      "artifact_id": "ART-0001",
      "original_path": "/mnt/user-data/outputs/auth/main.py",
      "filename": "main.py",
      "artifact_type": "code",
      "language": "python",
      "description": "Main authentication module",
      "size_bytes": 15432,
      "checksum": "sha256:abc123...",
      "created_at": "2026-01-26T10:00:00.000Z",
      "stored_path": "code/main.py"
    }
  },
  "next_id": 2
}
```

---

## Troubleshooting

**Export fails**: Verify team exists with `ls ~/.claude/teams/{name}/`

**Restore fails**: Check content contains `<details>` blocks with JSON

**Logs not restoring**: Ensure content has `channel.jsonl` block with ```jsonl fence

**Notion errors**: Verify page IDs, check permissions

**Sync shows 0 pending but messages exist**: Check timestamps are valid ISO format

**Large artifacts**: Files >100KB are truncated in export with `[truncated]` marker

**Artifact not found**: Use `list-artifacts` to see registered artifacts
