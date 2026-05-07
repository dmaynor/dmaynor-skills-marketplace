#!/bin/bash
# claudeception UserPromptSubmit hook
#
# After a session has accumulated substantial work, inject a one-line nudge
# into Claude's context reminding it to evaluate for extractable knowledge
# at session end. Only nudges when there are pending retrospectives or when
# the current transcript is large.
#
# Output goes to stdout — Claude Code wraps it as additional context for
# the next prompt.

set -e

INBOX_DIR="${HOME}/.claude/skill-candidates"
PENDING_FILE="${INBOX_DIR}/_pending-retrospective.txt"
SESSION_ID="${CLAUDE_SESSION_ID:-}"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-}"

# Track when this hook last fired so we only nudge periodically
STATE_DIR="${INBOX_DIR}/.state"
mkdir -p "$STATE_DIR"
STATE_FILE="${STATE_DIR}/${SESSION_ID}-last-nudge"

now=$(date +%s)
last_nudge=0
if [ -f "$STATE_FILE" ]; then
  last_nudge=$(cat "$STATE_FILE")
fi

# Only nudge once per 30 minutes of session activity
if [ $((now - last_nudge)) -lt 1800 ]; then
  exit 0
fi

# Check transcript size as a proxy for "session has done substantive work"
TRANSCRIPT_DIR="${HOME}/.claude/projects"
SANITIZED_CWD=$(echo "$PROJECT_DIR" | sed 's|/|-|g')
TRANSCRIPT_FILE="${TRANSCRIPT_DIR}/${SANITIZED_CWD}/${SESSION_ID}.jsonl"

if [ ! -f "$TRANSCRIPT_FILE" ]; then
  exit 0
fi

size=$(stat -c%s "$TRANSCRIPT_FILE" 2>/dev/null || echo 0)

# Nudge threshold: 200KB of transcript suggests substantive work
if [ "$size" -lt 200000 ]; then
  exit 0
fi

# Update state and emit nudge
echo "$now" > "$STATE_FILE"

cat <<'EOF'
[claudeception] Session has accumulated substantive work. Before context gets compacted or the session ends, consider whether anything done so far meets the skill-extraction bar (novel methodology, cross-target pattern, non-obvious investigation technique). If yes, run /claudeception:claudeception to capture it. If no, ignore this and continue.
EOF

exit 0
