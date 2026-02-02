# Message Protocol

Shared channel communication for swarm orchestration.

## Channel Location

```
~/.claude/teams/{team-name}/channel.jsonl
```

Append-only JSON Lines format. All agents read and write to same file.

## Message Schema

```json
{
  "ts": "2026-01-25T23:45:00.000Z",
  "from": "programmer",
  "to": ["@qa", "@critic"],
  "type": "message",
  "reasoning": "Auth module complete. Tests pass locally. Ready for validation.",
  "content": "Implementation of OAuth2 flow complete. Files: app/services/auth/. @qa ready for test suite. @critic please review token handling logic."
}
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `ts` | Yes | ISO 8601 timestamp |
| `from` | Yes | Agent name (e.g., `programmer`, `td`) |
| `to` | No | Array of @handles. Null/omit = broadcast to all |
| `type` | Yes | Message type (see below) |
| `reasoning` | Yes | Why this action/message. Evidence trail. |
| `content` | Yes | The actual message content |

### Message Types

| Type | Purpose | Example |
|------|---------|---------|
| `message` | General communication | Status updates, questions, handoffs |
| `decision` | Announcing a choice | "Chose Redis over Memcached because..." |
| `task` | Task-related action | Claiming, completing, blocking |
| `status` | Progress update | "50% complete on auth module" |
| `request` | Asking for approval/input | "Request @td approval for external dependency" |
| `autonomy` | Autonomy level change | TD updating agent freedom |
| `system` | System events | Shutdown requests, errors |

## Reading Channel

### Bash (simple)

```bash
# Last 50 messages
cat ~/.claude/teams/{team}/channel.jsonl | tail -50

# Messages to specific agent
cat ~/.claude/teams/{team}/channel.jsonl | grep '"@programmer"'

# Messages from specific agent  
cat ~/.claude/teams/{team}/channel.jsonl | grep '"from":"architect"'

# Pretty print with jq
cat ~/.claude/teams/{team}/channel.jsonl | jq -s '.[-20:]'
```

### Using channel.py script

```bash
# All recent messages
python3 scripts/channel.py read --team {team}

# Messages for me
python3 scripts/channel.py read --team {team} --mine

# Since timestamp
python3 scripts/channel.py read --team {team} --since "2026-01-25T23:00:00Z"
```

## Writing Channel

### Bash (direct)

```bash
echo '{"ts":"'$(date -u +%Y-%m-%dT%H:%M:%S.000Z)'","from":"programmer","to":["@qa"],"type":"message","reasoning":"Implementation complete, tests needed.","content":"Auth module ready for testing."}' >> ~/.claude/teams/{team}/channel.jsonl
```

### Using channel.py script

```bash
python3 scripts/channel.py write \
  --team {team} \
  --from programmer \
  --to @qa @critic \
  --type message \
  --reasoning "Implementation complete" \
  --content "Auth module ready for review"
```

## @Mention Conventions

| Handle | Target |
|--------|--------|
| `@td` | Technical Director (leader) |
| `@all` | Broadcast to everyone |
| `@architect` | Architect agent |
| `@programmer` | Programmer agent |
| `@qa` | QA Engineer agent |
| `@critic` | Critic agent |
| `@security` | Security Engineer agent |
| `@redteam` | Red Team Operator agent |
| `@network` | Network Engineer agent |
| `@hardware` | Hardware Engineer agent |
| `@cti` | CTI Agent |
| `@data` | Data Engineer agent |
| `@gm` | Game-Master agent |

## Required Behaviors

### Emit Reasoning

Every agent MUST include `reasoning` field explaining why they're taking an action. This creates the evidence trail.

Bad:
```json
{"content": "Using Redis for caching."}
```

Good:
```json
{
  "reasoning": "Redis preferred over Memcached: need pub/sub for invalidation, persistence for recovery, sorted sets for leaderboard feature.",
  "content": "Decision: Using Redis for caching layer. See architecture.md for details."
}
```

### Acknowledge Receipt

When assigned a task via @mention, acknowledge:

```json
{
  "from": "programmer",
  "to": ["@td"],
  "type": "task",
  "reasoning": "Confirming task receipt to ensure coordination.",
  "content": "ACK: Claimed task #2. Starting implementation."
}
```

### Report Blockers

If blocked, immediately notify:

```json
{
  "from": "programmer",
  "to": ["@td", "@architect"],
  "type": "status",
  "reasoning": "Cannot proceed without API spec. Need @architect input.",
  "content": "BLOCKED: Task #2 needs API endpoint definitions. @architect please provide or clarify scope."
}
```

### Handoff Protocol

When completing work that another agent needs:

```json
{
  "from": "programmer",
  "to": ["@qa", "@critic"],
  "type": "task",
  "reasoning": "Implementation complete, entering validation phase.",
  "content": "HANDOFF: Auth module complete. Files: app/services/auth/. @qa run test suite. @critic review token handling in oauth_provider.py:45-120."
}
```

## Autonomy Updates (TD Only)

TD adjusts agent autonomy via channel:

```json
{
  "from": "td",
  "to": ["@programmer"],
  "type": "autonomy",
  "reasoning": "3 consecutive clean task completions. Earned increased trust.",
  "content": "AUTONOMY_UPDATE: programmer → autonomous. Continue without approval for implementation tasks."
}
```

## System Messages

### Shutdown Request (from TD)

```json
{
  "from": "td",
  "to": ["@programmer"],
  "type": "system",
  "reasoning": "All tasks complete, initiating graceful shutdown.",
  "content": "SHUTDOWN_REQUEST: Please complete current work and confirm ready for shutdown."
}
```

### Shutdown Acknowledgment (from Agent)

```json
{
  "from": "programmer",
  "to": ["@td"],
  "type": "system",
  "reasoning": "No pending work, safe to terminate.",
  "content": "SHUTDOWN_ACK: Ready for shutdown. Final status: 5 tasks completed, 0 pending."
}
```
