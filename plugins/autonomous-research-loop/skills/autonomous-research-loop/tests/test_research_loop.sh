#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
test_dir="$(mktemp -d)"
trap 'rm -rf "$test_dir"' EXIT

mkdir -p "$test_dir/bin"
cat > "$test_dir/bin/claude" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
sed -i.bak 's/- \[ \]/- [x]/' "$RESEARCH_STATE_FILE"
rm -f "${RESEARCH_STATE_FILE}.bak"
EOF
chmod +x "$test_dir/bin/claude"

printf '%s\n' '- [ ] bounded task' > "$test_dir/state.md"
printf '%s\n' 'Complete one pending task and update the state file.' > "$test_dir/prompt.md"

(
  cd "$test_dir"
  PATH="$test_dir/bin:$PATH" \
  RESEARCH_STATE_FILE="$test_dir/state.md" \
  RESEARCH_PROMPT_FILE="$test_dir/prompt.md" \
  RESEARCH_LOOP_AUTO_COMMIT=0 \
  "$script_dir/scripts/research-loop.sh" 1 0
)

grep -q -- '- \[x\] bounded task' "$test_dir/state.md"
grep -q '"status":"complete"' "$test_dir/.research-heartbeat"

cat > "$test_dir/bin/claude" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$test_dir/bin/claude"
printf '%s\n' '- [ ] stalled task' > "$test_dir/state.md"

if (
  cd "$test_dir"
  PATH="$test_dir/bin:$PATH" \
  RESEARCH_STATE_FILE="$test_dir/state.md" \
  RESEARCH_PROMPT_FILE="$test_dir/prompt.md" \
  RESEARCH_LOOP_AUTO_COMMIT=0 \
  RESEARCH_LOOP_NO_PROGRESS_LIMIT=2 \
  "$script_dir/scripts/research-loop.sh" 0 0
); then
  printf 'expected no-progress run to fail\n' >&2
  exit 1
fi

grep -q '"status":"no-progress-limit"' "$test_dir/.research-heartbeat"
printf 'research-loop contract test passed\n'
