---
name: swarm-orchestration
description: Multi-agent swarm orchestration for complex tasks. TD (Technical Director) decomposes user requests into task lists, delegates to specialized role-based agents (Architect, Programmer, QA, Critic, Security Engineer, Red Team, etc.), and coordinates via shared channel communication. Supports comprehensive Notion persistence for cross-session continuity - captures conversation dialogue, extended thinking, agent communication, artifacts (code/config/docs), and outputs. Use when tasks require parallel specialist work, coordinated implementation pipelines, multi-perspective review, or when user says "save/load project", "sync logs", "team-based", "swarm", "multi-agent", or references existing projects by name.
author: dmaynor
version: 1.0.0
date: 2026-03-29
---

# Swarm Orchestration

Multi-agent orchestration with TD (Technical Director) coordinating specialized agents through shared channel communication.

## Problem

Coordinating multiple AI agents on complex decomposed tasks is error-prone without structured orchestration. Without a clear protocol for task decomposition, agent spawning, inter-agent communication, and result merging, swarm-based workflows produce fragmented outputs, deadlocked dependencies, and lost context between sessions.

## Architecture

```
TD (You) ──┬── Architect         (design)
           ├── Programmer        (implementation)
           ├── QA Engineer       (validation)
           ├── Critic            (adversarial review)
           ├── Security Engineer (hardening)
           ├── Red Team Operator (offensive)
           └── [+ Network, Hardware, CTI, Data, Game-Master]
```

**References:**
- Role definitions: `references/roles.md`
- Message protocol: `references/message-protocol.md`
- Notion persistence: `references/notion-persistence.md`

## Workflow

### 1. Initialize

```javascript
Teammate({ operation: "spawnTeam", team_name: "{project}", description: "{goal}" })
```

### 2. Decompose

Break into discrete tasks. Match ownership to expertise:

```javascript
TaskCreate({ subject: "Design auth", description: "..." })
TaskCreate({ subject: "Implement auth", description: "..." })
TaskUpdate({ taskId: "2", addBlockedBy: ["1"] })
```

### 3. Spawn Agents

```javascript
Task({
  team_name: "{project}",
  name: "programmer",
  subagent_type: "general-purpose",
  prompt: `You are Programmer on team {project}.
ROLE: Implementation. TOOLS: All. AUTONOMY: supervised
PROTOCOL:
1. Read: python3 scripts/channel.py read --team {project}
2. Write: python3 scripts/channel.py write --team {project} --from programmer --content "msg"
3. Address: @td, @architect, @qa, etc.
4. EMIT REASONING in channel before decisions.
Begin by reading channel, then TaskList().`,
  run_in_background: true
})
```

### 4. Monitor

- Read channel: `cat ~/.claude/teams/{project}/channel.jsonl | tail -50`
- Resolve blockers, adjust autonomy, arbitrate conflicts

### 5. Shutdown

```javascript
Teammate({ operation: "requestShutdown", target_agent_id: "programmer", reason: "Complete" })
Teammate({ operation: "cleanup" })
```

---

## Notion Persistence

Container resets between sessions. Persist **everything** to Notion for complete audit trail. See `reference.md` for full API documentation, scripts reference, and Notion page structure.

| Component | What's Captured | Script |
|-----------|-----------------|--------|
| **Request** | Original user prompt | `swarm_persistence.py` |
| **Dialogue** | Full user <> Claude conversation turns | `swarm_persistence.py` |
| **Thinking** | Claude's extended thinking blocks | `swarm_persistence.py` |
| **Agent Logs** | Channel communication between agents | `notion_persistence.py` |
| **Artifacts** | Code, config files, markdown docs | `swarm_persistence.py` |
| **Outputs** | Final deliverables and summaries | `swarm_persistence.py` |

Setup (one-time): Create Swarm Hub database. See `references/notion-persistence.md` for schema.

---

## Autonomy Levels

| Level | Behavior |
|-------|----------|
| `autonomous` | Proceeds without approval |
| `supervised` | Reports decisions, TD can intervene (default) |
| `gated` | Requires TD approval |

---

## Patterns

- **Parallel Review**: Critic + Security + QA review the same artifact concurrently
- **Pipeline**: Architect -> Programmer -> QA -> Critic (via `addBlockedBy` dependencies)
- **Red Team Exercise**: Red Team attacks, Security defends, Game-Master referees

---

## Quick Reference

| Action | Command |
|--------|---------|
| Create team | `Teammate({ operation: "spawnTeam", team_name: "X" })` |
| Create task | `TaskCreate({ subject: "...", description: "..." })` |
| Set dependency | `TaskUpdate({ taskId: "N", addBlockedBy: ["M"] })` |
| Spawn agent | `Task({ team_name: "X", name: "role", prompt: "...", run_in_background: true })` |
| Read channel | `cat ~/.claude/teams/X/channel.jsonl \| tail -50` |
| Shutdown | `Teammate({ operation: "requestShutdown", target_agent_id: "role" })` |
| Init persistence | `python3 scripts/swarm_persistence.py init --team X --description "..."` |
| Export full | `python3 scripts/swarm_persistence.py export-full --team X` |
| Prepare sync | `python3 scripts/notion_sync.py sync --team X` |

---

## Verification

1. TD decomposes the user request into a valid task list: `tasks.json` contains discrete tasks with clear ownership and dependency ordering
2. Agents spawn and communicate: channel.jsonl shows messages from each spawned agent with proper `--from` attribution
3. Blocked tasks respect dependencies: no agent begins work on a task whose `addBlockedBy` predecessors are incomplete
4. Results merge correctly: final output incorporates deliverables from all agents, with no missing or duplicated work
5. Persistence round-trips: `swarm_persistence.py export-full` produces a complete session export, and `notion_sync.py sync` generates valid sync instructions

## Notes

- Full API documentation, persistence script references, Notion page structure, artifact types, channel commands, and file structure details are in `reference.md`
