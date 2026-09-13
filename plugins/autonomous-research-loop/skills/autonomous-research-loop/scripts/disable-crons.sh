#!/usr/bin/env bash
set -euo pipefail

begin_marker="# BEGIN autonomous-research-loop"
end_marker="# END autonomous-research-loop"

if ! command -v crontab >/dev/null 2>&1; then
  printf 'error: crontab executable not found\n' >&2
  exit 127
fi

current="$(crontab -l 2>/dev/null || true)"
if [[ -z "$current" ]]; then
  printf 'No crontab entries found.\n'
  exit 0
fi

begin_count="$(printf '%s\n' "$current" | grep -Fxc "$begin_marker" || true)"
end_count="$(printf '%s\n' "$current" | grep -Fxc "$end_marker" || true)"
if [[ "$begin_count" -ne "$end_count" ]]; then
  printf 'error: cron block markers are unbalanced; refusing to modify crontab\n' >&2
  exit 2
fi

filtered="$(printf '%s\n' "$current" | awk -v begin="$begin_marker" -v end="$end_marker" '
  $0 == begin { inside = 1; next }
  $0 == end { inside = 0; next }
  !inside { print }
')"

if [[ "$filtered" == "$current" ]]; then
  printf 'No autonomous-research-loop cron block found.\n'
  exit 0
fi

if [[ -n "$filtered" ]]; then
  printf '%s\n' "$filtered" | crontab -
else
  crontab -r
fi
printf 'Removed autonomous-research-loop cron block; unrelated entries were preserved.\n'
