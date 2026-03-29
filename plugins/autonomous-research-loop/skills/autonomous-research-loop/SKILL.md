---
name: autonomous-research-loop
description: |
  Pattern for running Claude Code as an autonomous research agent with restart-with-state
  loops. Use when: (1) long-running research or enumeration that exceeds context limits,
  (2) need autonomous operation for hours/days, (3) systematic task-based work that should
  survive crashes and quota limits. Covers: loop script, state tracking, cron auto-restart,
  heartbeat monitoring, backup, inflight task addition, graceful quota handling.
author: Claude Code
version: 1.0.0
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

**Loop script** — Bash wrapper that:
- Launches `claude --print --dangerously-skip-permissions`
- Tracks consecutive failures (3 = stop)
- Backs off on failure (5 min), normal cooldown on success (60s)
- Commits uncommitted work before/after each iteration
- Pushes to remote every N iterations
- Writes heartbeat file for monitoring
- Uses `caffeinate` to prevent sleep

**Cron auto-restart** — Every 5 min, check if loop is running:
- If tmux session exists → log status
- If tmux session missing + tasks remain → restart in tmux

**Backup** — Cron rsync to external drive every 15 min

**Inflight task addition** — Edit state file while loop is running.
Next iteration picks up new tasks automatically.

### Launch Pattern
```bash
tmux new-session -d -s research './scripts/research-loop.sh 0 60'
tmux attach -t research  # optional: watch it work
# Detach: Ctrl-b d
```

### Stop Pattern
```bash
tmux kill-session -t research
./scripts/disable-crons.sh
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

## References
- Developed during MacBook Neo (A18 Pro) vulnerability research, 2026-03-12
- See: ~/code/apple-vuln-research/scripts/ for reference implementation
