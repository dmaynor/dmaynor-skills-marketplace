---
name: claudeception
description: Run a retrospective on the current session — identify methodology that should be extracted as new skills or catalogued in the research log
argument-hint: "[--mode auto|interactive] [--dest research-log|candidates|marketplace]"
allowed-tools: Read Write Edit Bash Glob Grep Skill TodoWrite
---

# Claudeception — session retrospective

**Arguments:** $ARGUMENTS

Parse arguments:
- `--mode auto` — non-interactive, write candidates without asking. Default: `interactive`.
- `--dest research-log` — write to `~/raptor-research-log/<date>-skill-candidates.md`. Default.
- `--dest candidates` — write to `~/.claude/skill-candidates/<topic>.md` (one file per candidate).
- `--dest marketplace` — scaffold full plugin in `~/code/dmaynor-skills-marketplace/plugins/<name>/` (requires interactive mode for confirmation).

Invoke the `claudeception` skill to:

1. **Review the current session's work** — scan the conversation history for:
   - Methodology development (multi-step processes, audit pipelines, sweep strategies)
   - Cross-vendor / cross-target patterns identified
   - Non-obvious investigation techniques
   - Tool integration knowledge that took experimentation
   - Anti-patterns recognized

2. **Apply the skill's quality criteria** — only extract candidates that meet:
   - Reusable beyond this session
   - Non-trivial (required investigation, not just doc lookup)
   - Specific enough to operationalize
   - Verified at least once in this session's work

3. **Check for existing skills** — search the marketplace and installed skill caches; mark candidates that should `update existing` rather than `create new`.

4. **Write output to the destination** based on `--dest`:
   - `research-log`: append a dated section listing candidates with one-paragraph justification each
   - `candidates`: one markdown file per candidate, with frontmatter (name, description, justification, status: draft)
   - `marketplace`: full plugin scaffold (only with explicit user confirmation per candidate)

5. **Report back** — summary of what was caught, what was deferred, what was filtered out as not-skill-worthy.

If `--mode auto` is set: don't ask the user any questions, just produce output. Useful for SessionEnd hooks.

If `--mode interactive` (default): show candidates as a table, ask which to extract.
