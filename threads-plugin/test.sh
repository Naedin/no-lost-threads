#!/usr/bin/env bash
# threads — prove scripts/retro-log.py on the shapes live use has broken it on.
# One line per case; exits 1 on the first wrong one.
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
rl="$here/scripts/retro-log.py"
check="$here/../guards-plugin/checks/retro-log/check.py"
tmp="$(mktemp -d)" || exit 1
trap 'rm -rf "$tmp"' EXIT
fail() { echo "FAIL  $1"; exit 1; }
ok() { printf 'ok    %s\n' "$1"; }

cat > "$tmp/log.md" <<'EOF'
## Entries

scope-leak/a
  2026-09-01 | s1 | first.
scope-leak/a
  LANDED abc1234 — somewhere.
scope-leak/a
  2026-09-05 | s2 | came back after the landing.
drift/b
  2026-09-02 | s1 | one.
drift/b
  HELD 9f9f9f9 — proposal.
drift/b
  2026-09-03 | s2 | two.
drift/b
  2026-09-04 | s3 | three.
positive/c
  NOTED 2026-09-06 — worked.
EOF

# 1. compact keeps a recurrence after a closing status, and the view says so
python3 "$rl" compact --root "$tmp" --log log.md 2>/dev/null || fail "compact refused a valid log"
grep -q 'came back after the landing' "$tmp/log.md" || fail "compact dropped an occurrence appended after LANDED"
python3 "$rl" view --keys --root "$tmp" --log log.md | grep -q 'scope-leak/a .*recurred after LANDED' || fail "view does not mark a recurrence after LANDED"
ok "recurrence after a closing status survives and is marked"

# 2. a status block keeps its own key line; the compacted log passes the grammar check
[ "$(grep -c '^drift/b$' "$tmp/log.md")" -eq 3 ] || fail "status block lost its key line (drift/b lines: $(grep -c '^drift/b$' "$tmp/log.md"))"
python3 "$check" --root "$tmp" --paths log.md >/dev/null 2>&1 || fail "compacted log fails the retro-log check"
ok "status blocks keep their boundary; compacted log passes the check"

# 3. compaction is idempotent
cp "$tmp/log.md" "$tmp/once.md"
python3 "$rl" compact --root "$tmp" --log log.md 2>/dev/null
cmp -s "$tmp/log.md" "$tmp/once.md" || fail "second compaction changed a canonical log"
ok "compacting a canonical log changes nothing"

# 4. view reads an unrepaired log with warnings; compact refuses
printf 'drift/d\n  ADJUDICATED x — old spelling.\n' >> "$tmp/log.md"
python3 "$rl" view --keys --root "$tmp" --log log.md >/dev/null 2>"$tmp/err" || fail "view refused an unrepaired log"
grep -q 'warning' "$tmp/err" || fail "view gave no warning on an unrepaired log"
python3 "$rl" compact --dry-run --root "$tmp" --log log.md >/dev/null 2>&1 && fail "compact accepted an unrepaired log"
ok "view warns, compact refuses, on an unrepaired log"

# 5. closed keys reduce to one status line; NOTED is closed
python3 "$rl" view --keys --root "$tmp" --log log.md 2>/dev/null | grep -q '^positive/c .*NOTED' || fail "NOTED key not in the closed section"
ok "NOTED closes at write"
echo "all cases passed"
