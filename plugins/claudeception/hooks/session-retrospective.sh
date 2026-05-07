#!/bin/bash
# claudeception SessionEnd hook
#
# Writes a marker file to ~/.claude/skill-candidates/_pending-retrospective.txt
# noting that the just-ended session may have substantive content worth extracting.
# The user can run /claudeception:claudeception in their next session to process pending
# retrospectives and produce skill candidates.
#
# This hook does NOT call Claude — SessionEnd runs after the session is gone.
# It just leaves a breadcrumb.

set -e

INBOX_DIR="${HOME}/.claude/skill-candidates"
mkdir -p "$INBOX_DIR"

PENDING_FILE="${INBOX_DIR}/_pending-retrospective.txt"
TS=$(date -Iseconds)
SESSION_ID="${CLAUDE_SESSION_ID:-unknown}"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-unknown}"

# Only mark pending if the session transcript suggests substantial work
# Heuristic: transcript file >100KB or session duration suggests engaged work
TRANSCRIPT_DIR="${HOME}/.claude/projects"
SANITIZED_CWD=$(echo "$PROJECT_DIR" | sed 's|/|-|g')
TRANSCRIPT_FILE="${TRANSCRIPT_DIR}/${SANITIZED_CWD}/${SESSION_ID}.jsonl"

if [ -f "$TRANSCRIPT_FILE" ]; then
  size=$(stat -c%s "$TRANSCRIPT_FILE" 2>/dev/null || echo 0)
  if [ "$size" -gt 100000 ]; then
    {
      echo "${TS}  session=${SESSION_ID}  project=${PROJECT_DIR}  size=${size}"
    } >> "$PENDING_FILE"
  fi
fi

exit 0
