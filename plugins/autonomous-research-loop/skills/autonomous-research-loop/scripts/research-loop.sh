#!/usr/bin/env bash
set -u

usage() {
  cat <<'EOF'
Usage: research-loop.sh [max_iterations] [cooldown_seconds]

Run one fresh Claude Code process per iteration until the state file has no
pending or in-progress checklist items. A max_iterations value of 0 means no
iteration limit.

Environment:
  RESEARCH_STATE_FILE              State checklist (default: RESEARCH_STATE.md)
  RESEARCH_PROMPT_FILE             Agent prompt (default: RESEARCH_PROMPT.md)
  RESEARCH_LOOP_LOG                Combined log (default: agent-monitor.log)
  RESEARCH_LOOP_FAILURE_LIMIT      Consecutive failures before stop (default: 3)
  RESEARCH_LOOP_FAILURE_BACKOFF    Seconds after failure (default: 300)
  RESEARCH_LOOP_NO_PROGRESS_LIMIT  Successful no-progress runs before stop (default: 2)
  RESEARCH_LOOP_AUTO_COMMIT        Commit loop changes: 1 or 0 (default: 1)
  RESEARCH_LOOP_PUSH_EVERY         Push every N successful iterations (default: 0)
  RESEARCH_LOOP_ALLOW_DIRTY        Permit a dirty initial tree: 1 or 0 (default: 0)
  RESEARCH_LOOP_ALLOW_PROTECTED_BRANCH
                                   Permit main/master: 1 or 0 (default: 0)
  RESEARCH_LOOP_DANGEROUSLY_SKIP_PERMISSIONS
                                   Pass Claude's bypass flag: 1 or 0 (default: 0)
EOF
}

is_nonnegative_integer() {
  [[ "$1" =~ ^[0-9]+$ ]]
}

max_iterations="${1:-0}"
cooldown_seconds="${2:-60}"
state_file="${RESEARCH_STATE_FILE:-RESEARCH_STATE.md}"
prompt_file="${RESEARCH_PROMPT_FILE:-RESEARCH_PROMPT.md}"
log_file="${RESEARCH_LOOP_LOG:-agent-monitor.log}"
heartbeat_file="${RESEARCH_LOOP_HEARTBEAT:-.research-heartbeat}"
failure_limit="${RESEARCH_LOOP_FAILURE_LIMIT:-3}"
failure_backoff="${RESEARCH_LOOP_FAILURE_BACKOFF:-300}"
no_progress_limit="${RESEARCH_LOOP_NO_PROGRESS_LIMIT:-2}"
auto_commit="${RESEARCH_LOOP_AUTO_COMMIT:-1}"
push_every="${RESEARCH_LOOP_PUSH_EVERY:-0}"
allow_dirty="${RESEARCH_LOOP_ALLOW_DIRTY:-0}"
allow_protected="${RESEARCH_LOOP_ALLOW_PROTECTED_BRANCH:-0}"
skip_permissions="${RESEARCH_LOOP_DANGEROUSLY_SKIP_PERMISSIONS:-0}"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

for value in "$max_iterations" "$cooldown_seconds" "$failure_limit" "$failure_backoff" "$no_progress_limit" "$push_every"; do
  if ! is_nonnegative_integer "$value"; then
    printf 'error: numeric arguments and limits must be non-negative integers\n' >&2
    exit 2
  fi
done

if [[ "$failure_limit" -eq 0 || "$no_progress_limit" -eq 0 ]]; then
  printf 'error: failure and no-progress limits must be at least 1\n' >&2
  exit 2
fi

if [[ ! -f "$state_file" || ! -f "$prompt_file" ]]; then
  printf 'error: required files not found: %s and %s\n' "$state_file" "$prompt_file" >&2
  exit 2
fi

if ! command -v claude >/dev/null 2>&1; then
  printf 'error: claude executable not found in PATH\n' >&2
  exit 127
fi

git_repo=0
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git_repo=1
  branch="$(git branch --show-current)"
  if [[ -z "$branch" ]]; then
    printf 'error: refusing to run from a detached HEAD\n' >&2
    exit 2
  fi
  if [[ "$allow_protected" != "1" && ( "$branch" == "main" || "$branch" == "master" ) ]]; then
    printf 'error: refusing to run on protected branch %s\n' "$branch" >&2
    exit 2
  fi
  if [[ "$allow_dirty" != "1" && -n "$(git status --porcelain)" ]]; then
    printf 'error: refusing to start with a dirty working tree\n' >&2
    exit 2
  fi
  if [[ "$auto_commit" == "1" ]]; then
    for generated_file in "$log_file" "$heartbeat_file"; do
      if ! git check-ignore -q -- "$generated_file"; then
        printf 'error: automatic commits require %s to be gitignored\n' "$generated_file" >&2
        exit 2
      fi
    done
  fi
fi

has_remaining_tasks() {
  grep -Eq '^[[:space:]]*-[[:space:]]*\[( |~)\]' "$state_file"
}

remaining_task_count() {
  grep -Ec '^[[:space:]]*-[[:space:]]*\[( |~)\]' "$state_file" || true
}

write_heartbeat() {
  local status="$1"
  local iteration="$2"
  printf '{"timestamp":"%s","iteration":%s,"status":"%s"}\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$iteration" "$status" > "$heartbeat_file"
}

commit_changes() {
  local iteration="$1"
  if [[ "$git_repo" -ne 1 || "$auto_commit" != "1" ]]; then
    return 0
  fi
  if [[ -z "$(git status --porcelain)" ]]; then
    return 0
  fi
  git add -A
  git commit -m "research: autonomous iteration ${iteration}"
}

iteration=0
consecutive_failures=0
consecutive_no_progress=0
write_heartbeat "starting" "$iteration"

while has_remaining_tasks; do
  if [[ "$max_iterations" -gt 0 && "$iteration" -ge "$max_iterations" ]]; then
    write_heartbeat "iteration-limit" "$iteration"
    exit 0
  fi

  iteration=$((iteration + 1))
  tasks_before="$(remaining_task_count)"
  write_heartbeat "running" "$iteration"
  printf '[%s] starting iteration %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$iteration" | tee -a "$log_file"

  claude_args=(--print)
  if [[ "$skip_permissions" == "1" ]]; then
    claude_args+=(--dangerously-skip-permissions)
  fi

  prompt="$(cat "$prompt_file")"
  if command -v caffeinate >/dev/null 2>&1; then
    caffeinate -i claude "${claude_args[@]}" "$prompt" >> "$log_file" 2>&1
  else
    claude "${claude_args[@]}" "$prompt" >> "$log_file" 2>&1
  fi
  agent_status=$?

  if [[ "$agent_status" -eq 0 ]]; then
    if ! commit_changes "$iteration" >> "$log_file" 2>&1; then
      write_heartbeat "commit-failed" "$iteration"
      exit 1
    fi
    consecutive_failures=0
    tasks_after="$(remaining_task_count)"
    if [[ "$tasks_after" -ge "$tasks_before" ]]; then
      consecutive_no_progress=$((consecutive_no_progress + 1))
      if [[ "$consecutive_no_progress" -ge "$no_progress_limit" ]]; then
        printf '[%s] stopping after %s successful iterations without task-count progress\n' \
          "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$consecutive_no_progress" | tee -a "$log_file" >&2
        write_heartbeat "no-progress-limit" "$iteration"
        exit 1
      fi
    else
      consecutive_no_progress=0
    fi
    if [[ "$git_repo" -eq 1 && "$push_every" -gt 0 && $((iteration % push_every)) -eq 0 ]]; then
      if ! git push >> "$log_file" 2>&1; then
        write_heartbeat "push-failed" "$iteration"
        exit 1
      fi
    fi
    if has_remaining_tasks; then
      write_heartbeat "cooldown" "$iteration"
      sleep "$cooldown_seconds"
    fi
  else
    consecutive_failures=$((consecutive_failures + 1))
    printf '[%s] iteration %s failed with status %s (%s/%s)\n' \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$iteration" "$agent_status" \
      "$consecutive_failures" "$failure_limit" | tee -a "$log_file" >&2
    if [[ "$consecutive_failures" -ge "$failure_limit" ]]; then
      write_heartbeat "failure-limit" "$iteration"
      exit "$agent_status"
    fi
    write_heartbeat "backoff" "$iteration"
    sleep "$failure_backoff"
  fi
done

write_heartbeat "complete" "$iteration"
printf '[%s] no remaining tasks\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$log_file"
