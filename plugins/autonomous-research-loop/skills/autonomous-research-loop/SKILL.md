---
name: autonomous-research-loop
description: |
  Pattern for running Claude Code as an autonomous research agent with restart-with-state
  loops. Use when: (1) long-running research or enumeration that exceeds context limits,
  (2) need autonomous operation for hours/days, (3) systematic task-based work that should
  survive crashes and quota limits. Covers: loop script, state tracking, cron auto-restart,
  heartbeat monitoring, backup, inflight task addition, graceful quota handling.
metadata:
  author: Claude Code
  version: 1.2.0
  date: 2026-03-12
---

# Autonomous Research Loop

## Problem
Long-running research or enumeration tasks exceed Claude Code's context window. Single
sessions degrade over time with autocompact. You need autonomous operation for 12-24+ hours.

## Context / Trigger Conditions
- Research or audit with 20+ discrete tasks
- User wants to leave the agent running unattended
- Work needs to survive crashes, quota limits, and context degradation
- Tasks can be executed independently across fresh sessions

## Solution

### Architecture: Restart-with-State
Instead of one long session, use a loop that:
1. Reads task state from a file (e.g., `RESEARCH_STATE.md`)
2. Picks the next uncompleted task
3. Does the work, writes results, commits
4. Updates state, exits cleanly
5. Loop restarts with a fresh context window

### Key Components

**State file** — Markdown checklist that agents read/write:
- `- [ ]` pending, `- [~]` in progress, `- [x]` done
- In-progress marker prevents duplicate work across iterations

**Loop script** — Bundled Bash wrapper that:
- Launches `claude --print`; permission bypass requires an explicit environment opt-in
- Tracks consecutive failures (3 = stop)
- Stops after two successful iterations that do not reduce the task count
- Backs off on failure (5 min), normal cooldown on success (60s)
- Refuses a dirty tree or `main`/`master` by default
- Commits iteration changes; pushing is disabled unless explicitly configured
- Writes heartbeat file for monitoring
- Uses `caffeinate` to prevent sleep

**Scheduler integration** — Optional and operator-owned. If a cron entry is used,
wrap it in `# BEGIN autonomous-research-loop` and `# END autonomous-research-loop`
markers so the bundled removal script can delete only those entries.

**Backup** — Optional and operator-configured. Require an explicit destination,
verify it is mounted, and test restoration before relying on scheduled copies.

**Inflight task addition** — Edit state file while loop is running.
Next iteration picks up new tasks automatically.

### Launch Pattern
```bash
SKILL_DIR=/path/to/autonomous-research-loop
tmux new-session -d -s research "$SKILL_DIR/scripts/research-loop.sh 0 60"
tmux attach -t research  # optional: watch it work
# Detach: Ctrl-b d
```

The project must contain `RESEARCH_STATE.md` and `RESEARCH_PROMPT.md`. Run from
a clean, dedicated branch. Use environment variables documented by
`scripts/research-loop.sh --help` to change filenames or loop policy.

### Stop Pattern
```bash
tmux kill-session -t research
"$SKILL_DIR/scripts/disable-crons.sh"
```

### Monitoring
- Heartbeat: `cat .research-heartbeat`
- Agent log: `tail agent-monitor.log`
- Git log: `git log --oneline`
- Progress: `cat PROGRESS.md`

## Verification
- `tmux has-session -t research` returns 0
- `ps aux | grep "claude --print"` shows active process
- `.research-heartbeat` updates every iteration
- `git log` shows commits from the agent

## Notes
- `--max-budget-usd` does NOT apply to Claude Max subscription accounts
- The prompt file should instruct the agent to handle SIP blocks gracefully
- Each iteration should aim for 1-3 subtasks, not the whole list
- State file must be committed before the loop starts to avoid merge conflicts
- Logs should be gitignored to avoid bloating the repo
- Automatic commit mode refuses to start unless its log and heartbeat files are ignored
- Do not enable `RESEARCH_LOOP_DANGEROUSLY_SKIP_PERMISSIONS=1` unless the user
  explicitly authorizes unattended mutation and the prompt has concrete safety blocks

## References
- Developed during MacBook Neo (A18 Pro) vulnerability research, 2026-03-12
- Bundled implementation: `scripts/research-loop.sh` and `scripts/disable-crons.sh`
