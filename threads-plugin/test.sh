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
printf 'drift/d\n  RERANKED x — old spelling.\n' >> "$tmp/log.md"
python3 "$rl" view --keys --root "$tmp" --log log.md >/dev/null 2>"$tmp/err" || fail "view refused an unrepaired log"
grep -q 'warning' "$tmp/err" || fail "view gave no warning on an unrepaired log"
python3 "$rl" compact --dry-run --root "$tmp" --log log.md >/dev/null 2>&1 && fail "compact accepted an unrepaired log"
ok "view warns, compact refuses, on an unrepaired log"

# 5. closed keys reduce to one status line; NOTED is closed
python3 "$rl" view --keys --root "$tmp" --log log.md 2>/dev/null | grep -q '^positive/c .*NOTED' || fail "NOTED key not in the closed section"
ok "NOTED closes at write"

# 6. a §4b artifact fix is a `Fixed:` continuation line: the key stays live, the check passes
cat > "$tmp/fixed.md" <<'EOF'
## Entries

scope-leak/e
  2026-09-08 | retro | claimed the slice decides nothing.
    Placement: doc.md §section — amend "x".
    Fixed: Plans/inbox/stub.md — 99faec68
EOF
python3 "$check" --root "$tmp" --paths fixed.md >/dev/null 2>&1 || fail "a Fixed: continuation line fails the retro-log check"
python3 "$rl" view --keys --root "$tmp" --log fixed.md 2>/dev/null | grep -q '^scope-leak/e .*×1' || fail "a Fixed: line closed or lost the key"
python3 "$rl" view --keys --root "$tmp" --log fixed.md 2>/dev/null | grep -q '^scope-leak/e .*LANDED' && fail "a Fixed: line read as a status"
ok "an artifact fix inside the occurrence keeps the lesson live"

# 7. an ADJUDICATED block changes neither state nor count, survives compaction on a live
#    and on a closed key, and never sits inside an occurrence
cat > "$tmp/adj.md" <<'EOF2'
## Entries

drift/f
  2026-09-01 | s1 | one.
drift/f
  2026-09-05 | s2 | two.
drift/f
  ADJUDICATED 2026-09-08 — count-only at ×2 with the rule present; no new text.
scope-leak/g
  2026-09-02 | s1 | once.
scope-leak/g
  LANDED abc1234 — doc.md §x.
scope-leak/g
  ADJUDICATED 2026-09-08 — the landing stands; the 09-07 re-rank to adopt-now is withdrawn.
mode-confusion/h
  2026-09-03 | s1 | once.
mode-confusion/h
  FILED Plans/inbox/h.md — carried by the stub.
mode-confusion/h
  ADJUDICATED 2026-09-08 — build-fired at a third window.
EOF2
python3 "$check" --root "$tmp" --paths adj.md >/dev/null 2>&1 || fail "an ADJUDICATED block fails the retro-log check"
python3 "$rl" view --keys --root "$tmp" --log adj.md 2>/dev/null | grep -q '^drift/f  ×2  2026-09-01..2026-09-05$' || fail "ADJUDICATED changed drift/f's state or count"
python3 "$rl" view --keys --root "$tmp" --log adj.md 2>/dev/null | grep -q '^scope-leak/g  ×1  LANDED abc1234' || fail "ADJUDICATED after LANDED reopened the key"
python3 "$rl" view --keys --root "$tmp" --log adj.md 2>/dev/null | grep -q '^mode-confusion/h  ×1  2026-09-03  FILED$' || fail "ADJUDICATED after FILED changed the state"
python3 "$rl" view --key drift/f --root "$tmp" --log adj.md 2>/dev/null | grep -q 'ADJUDICATED 2026-09-08 — count-only' || fail "the key's detail does not show its adjudication"
python3 "$rl" compact --root "$tmp" --log adj.md 2>/dev/null || fail "compact refused a log with ADJUDICATED blocks"
[ "$(grep -c '^  ADJUDICATED' "$tmp/adj.md")" -eq 3 ] || fail "compact dropped an ADJUDICATED block ($(grep -c '^  ADJUDICATED' "$tmp/adj.md") of 3 kept)"
[ "$(grep -c '^scope-leak/g$' "$tmp/adj.md")" -eq 2 ] || fail "a closed key did not reduce to its status line plus its adjudication"
python3 "$check" --root "$tmp" --paths adj.md >/dev/null 2>&1 || fail "compacted log with ADJUDICATED blocks fails the check"
printf 'drift/i\n  2026-09-08 | s1 | once.\n  ADJUDICATED 2026-09-08 — inside the occurrence.\n' >> "$tmp/adj.md"
python3 "$check" --root "$tmp" --paths adj.md 2>/dev/null | grep -q 'status line inside an occurrence entry' || fail "an ADJUDICATED line inside an occurrence passed the check"
ok "ADJUDICATED is transparent to state and count, kept by compact, refused inside an occurrence"

# 8. HELD keys carry their date and age; the filters are the review's reads
cat > "$tmp/held.md" <<'EOF2'
## Entries

drift/j
  2026-09-01 | s1 | one.
drift/j
  HELD 2026-09-07 — candidate A: doc.md §x gains a clause.
drift/k
  2026-09-02 | s1 | one.
drift/k
  2026-09-06 | s2 | two.
drift/l
  2026-09-03 | s1 | once.
drift/m
  LANDED abc1234 — doc.md §y.
drift/m
  2026-09-08 | s3 | came back.
EOF2
python3 "$rl" view --keys --root "$tmp" --log held.md --today 2026-09-09 2>/dev/null | grep -q '^drift/j  ×1  2026-09-01  HELD since 2026-09-07 (2d)$' || fail "a date-keyed HELD does not show its age"
python3 "$rl" view --keys --held --root "$tmp" --log held.md 2>/dev/null > "$tmp/held.out" || fail "--held refused"
grep -q '^showing 1 of 4 keys (--held)$' "$tmp/held.out" || fail "--held did not name what it shows"
grep -q '^drift/j ' "$tmp/held.out" || fail "--held omitted the held key"
grep -q '^drift/k \|^## Closed' "$tmp/held.out" && fail "--held showed an unheld key or the closed section"
python3 "$rl" view --keys --recurred --root "$tmp" --log held.md 2>/dev/null > "$tmp/rec.out"
grep -q '^drift/k ' "$tmp/rec.out" || fail "--recurred missed the key at ×2"
grep -q '^drift/m .*recurred after LANDED' "$tmp/rec.out" || fail "--recurred missed a key that came back after LANDED"
grep -q '^drift/j \|^drift/l ' "$tmp/rec.out" && fail "--recurred kept a key that never recurred"
python3 "$rl" view --recurred --root "$tmp" --log held.md 2>/dev/null | grep -q '  2026-09-08 | s3 | came back.' || fail "a filtered view without --keys carries no detail"
python3 "$rl" view --key drift/j --key drift/l --keys --root "$tmp" --log held.md 2>/dev/null | grep -c '^drift/' | grep -qx 2 || fail "--key does not repeat"
python3 "$rl" view --key drift/j --key drift/zz --root "$tmp" --log held.md >/dev/null 2>&1 && fail "--key accepted a key the log lacks"
python3 "$rl" view --keys --since 2026-09-07 --root "$tmp" --log held.md 2>/dev/null > "$tmp/since.out"
grep -q '^drift/j ' "$tmp/since.out" || fail "--since missed a key whose HELD date qualifies"
grep -q '^drift/m ' "$tmp/since.out" || fail "--since missed a key whose occurrence qualifies"
grep -q '^drift/k \|^drift/l ' "$tmp/since.out" && fail "--since kept a key touched only before the date"
python3 "$rl" view --keys --live --root "$tmp" --log held.md 2>/dev/null | grep -q '^## Closed' && fail "--live printed the closed section"
python3 "$rl" view --keys --since 09-07 --root "$tmp" --log held.md >/dev/null 2>&1 && fail "--since accepted a malformed date"
ok "HELD shows its age; --held, --recurred, --since, --live narrow the read; --key repeats"
echo "all cases passed"
