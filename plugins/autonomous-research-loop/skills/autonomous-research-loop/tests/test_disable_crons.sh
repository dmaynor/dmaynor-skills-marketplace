#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
test_dir="$(mktemp -d)"
trap 'rm -rf "$test_dir"' EXIT
mkdir -p "$test_dir/bin"

cat > "$test_dir/bin/crontab" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
case "${1:-}" in
  -l)
    cat "$CRON_STORE"
    ;;
  -)
    cat > "$CRON_STORE"
    ;;
  -r)
    : > "$CRON_STORE"
    ;;
  *)
    exit 2
    ;;
esac
EOF
chmod +x "$test_dir/bin/crontab"

cat > "$test_dir/crontab" <<'EOF'
0 2 * * * /usr/local/bin/unrelated-backup
# BEGIN autonomous-research-loop
*/5 * * * * /tmp/restart-research-loop
# END autonomous-research-loop
EOF

PATH="$test_dir/bin:$PATH" CRON_STORE="$test_dir/crontab" \
  "$script_dir/scripts/disable-crons.sh"

grep -q 'unrelated-backup' "$test_dir/crontab"
if grep -q 'autonomous-research-loop\|restart-research-loop' "$test_dir/crontab"; then
  printf 'marked cron block was not completely removed\n' >&2
  exit 1
fi

cat > "$test_dir/crontab" <<'EOF'
0 2 * * * /usr/local/bin/unrelated-backup
# BEGIN autonomous-research-loop
*/5 * * * * /tmp/restart-research-loop
EOF
cp "$test_dir/crontab" "$test_dir/crontab.before"

if PATH="$test_dir/bin:$PATH" CRON_STORE="$test_dir/crontab" \
  "$script_dir/scripts/disable-crons.sh"; then
  printf 'expected unbalanced markers to fail\n' >&2
  exit 1
fi

cmp "$test_dir/crontab.before" "$test_dir/crontab"
printf 'disable-crons contract test passed\n'
