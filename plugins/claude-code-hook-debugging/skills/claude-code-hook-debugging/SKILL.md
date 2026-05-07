---
name: claude-code-hook-debugging
description: |
  Debug Claude Code hook errors (SessionStart, UserPromptSubmit, PreToolUse, PostToolUse).
  Use when: (1) console shows "hook error" with no details, (2) plugin hooks fail silently,
  (3) need to trace which plugin registers which hook event. Covers finding hooks.json across
  plugin cache, diagnosing missing dependencies, and resolving auth/config issues.
author: Claude Code
version: 1.1.0
date: 2026-03-12
---

# Claude Code Hook Debugging

## Problem
Claude Code shows generic "hook error" messages (e.g., "SessionStart:resume hook error",
"UserPromptSubmit hook error") with no stack trace or details, making it unclear which
plugin is failing and why.

## Context / Trigger Conditions
- Console displays `SessionStart:resume hook error` or similar
- Console displays `UserPromptSubmit hook error`
- Console displays `PostToolUse:Write hook blocking error`
- A plugin was recently installed or updated
- Machine is freshly set up and may be missing dependencies

## Solution

### Step 1: Find all hooks registered for the failing event
```bash
# Search all plugin hooks.json files for the event name
grep -r "SessionStart\|UserPromptSubmit\|PreToolUse\|PostToolUse" \
  ~/.claude/plugins/cache/*/hooks/hooks.json
```

### Step 2: Identify which hook commands are registered
```bash
# Read the specific hooks.json files found above
# Look for the "command" field to see what's being executed
cat ~/.claude/plugins/cache/<plugin-name>/*/hooks/hooks.json
```

### Step 3: Test each hook command manually
Run the command from the hooks.json directly in your terminal to see the actual error:
```bash
# Example: if the hook runs "semgrep mcp -k inject-secure-defaults"
semgrep mcp -k inject-secure-defaults
# This will show the real error (command not found, auth missing, etc.)
```

### Step 4: Common root causes
| Symptom | Cause | Fix |
|---------|-------|-----|
| `command not found` | Tool not installed | `brew install <tool>` |
| `No APP_TOKEN found` | Tool needs authentication | Run the tool's login command |
| `Permission denied` | Script not executable | `chmod +x <script>` |
| `blocking error` | Hook is synchronous and failing | Fix or disable the plugin |

### Step 5: Disable a failing plugin
Edit `~/.claude/settings.json` and set the plugin to `false`:
```json
"plugin-name@marketplace": false
```
Changes take effect after `/reload-plugins` or restart.

## Verification
- Restart Claude Code or run `/reload-plugins`
- The hook error messages should no longer appear
- Check hook count in reload output (e.g., "10 hooks" vs previous "14 hooks")

## Notes
- Plugin hooks live in `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/hooks/hooks.json`
- User-level hooks are in `~/.claude/settings.json` under the `hooks` key
- Disabling a plugin mid-session stops future invocations but hooks loaded at startup persist until restart
- The `async: false` flag in hooks.json means the hook blocks — if it fails, it can block Claude's response
