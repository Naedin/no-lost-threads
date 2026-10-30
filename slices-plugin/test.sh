#!/usr/bin/env bash
# slices — prove scripts/ledger-row.py writes and re-runs claim rows.
# One line per case; exits 1 on the first wrong one.
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
lr="$here/scripts/ledger-row.py"
tmp="$(mktemp -d)" || exit 1
trap 'rm -rf "$tmp"' EXIT
fail() { echo "FAIL  $1"; exit 1; }
ok() { printf 'ok    %s\n' "$1"; }

git -C "$tmp" init -q
mkdir -p "$tmp/src" "$tmp/Plans"
printf 'load()\nload()\nsave()\n' > "$tmp/src/store.txt"
seq 1 12 > "$tmp/src/twelve.txt"
plan="$tmp/Plans/p.md"
cat > "$plan" <<'EOF'
# P

## Claim ledger

- drafted at abc1234, 2026-10-27, slices 0.9.0 — 0 sites opened (unverified: 0)

## After
EOF

# 1. a refusal without a record
printf '# Q\n' > "$tmp/Plans/q.md"
python3 "$lr" add "$tmp/Plans/q.md" c 'true' >/dev/null 2>&1 && fail "add wrote into a plan with no record"
ok "no record, no row"

# 2. the output line is derived: many lines, a bare count, no output, the plan's repo root as cwd
python3 "$lr" add "$plan" 'load is called twice' "rg -n 'load' src/store.txt" >/dev/null || fail "add refused"
python3 "$lr" add "$plan" 'two load sites' "rg -c 'load' src/store.txt" >/dev/null
python3 "$lr" add "$plan" 'no delete' "rg -n 'delete' src/store.txt" >/dev/null
grep -qF "  - load is called twice — \`rg -n 'load' src/store.txt\` — \`1:load()\`; \`2:load()\`" "$plan" || fail "listing row not derived: $(cat "$plan")"
python3 "$lr" add "$plan" 'twelve lines' "cat src/twelve.txt" >/dev/null
grep -qF "  - twelve lines — \`cat src/twelve.txt\` — 12 lines, first: \`1\`" "$plan" || fail "long listing not summarized"
grep -qF "  - two load sites — \`rg -c 'load' src/store.txt\` — \`2\`" "$plan" || fail "count row not a code-span number"
grep -qF "  - no delete — \`rg -n 'delete' src/store.txt\` — no output (exit 1)" "$plan" || fail "empty row not derived"
ok "listing, count, and empty output derived from the run in the repo root"

# 3. rows sit under the record, before the next section; the record's count is recounted
python3 "$lr" add "$plan" 'caller of save' --unverified 'open the caller' >/dev/null
[ "$(sed -n '5p' "$plan")" = "- drafted at abc1234, 2026-10-27, slices 0.9.0 — 5 sites opened (unverified: 1)" ] || fail "record not recounted: $(sed -n '5p' "$plan")"
[ "$(sed -n '10p' "$plan")" = "  - caller of save — unverified: open the caller" ] || fail "row not at the end of the record's block"
grep -q '^## After$' "$plan" || fail "next section lost"
ok "rows append under the record and recount it"

# 4. the same command replaces its row; a backtick in the command is fenced
python3 "$lr" add "$plan" 'load is called twice' "rg -n 'load' src/store.txt" >/dev/null
[ "$(grep -c "rg -n 'load'" "$plan")" -eq 1 ] || fail "same command duplicated"
python3 "$lr" add "$plan" 'echo' 'echo `printf x`' >/dev/null
grep -qF "\`\` echo \`printf x\` \`\` — \`x\`" "$plan" || fail "backtick command not fenced"
ok "a re-run row replaces itself; a backtick command is fenced"

# 5. rerun: held exits 0; a moved tree differs and exits 1
python3 "$lr" rerun "$plan" >"$tmp/out" || fail "rerun of a fresh ledger did not hold: $(cat "$tmp/out")"
grep -q '^rows: 5 held, 0 differ, 1 unverified, 0 unparsed$' "$tmp/out" || fail "rerun count wrong: $(tail -1 "$tmp/out")"
printf 'load()\n' >> "$tmp/src/store.txt"
python3 "$lr" rerun "$plan" >"$tmp/out" && fail "rerun held over a moved tree"
grep -q '^  now:      `3`$' "$tmp/out" || fail "rerun did not show the derived output"
ok "rerun holds a fresh ledger and catches a moved one"

# 6. a gap-checked record takes the rows after it; the drafted record and its count stay
printf -- '- gap-checked at def5678, 2026-10-27, slices 0.9.0 — 1 defects (addressed: 1), 0 questions (open: 0)\n' > "$tmp/rec"
awk -v rec="$(cat "$tmp/rec")" '/^## After$/{print rec; print ""} {print}' "$plan" > "$tmp/p2" && mv "$tmp/p2" "$plan"
python3 "$lr" add "$plan" 'three load sites' "rg -c 'load' src/store.txt" >/dev/null
grep -A1 '^- gap-checked at' "$plan" | grep -qF "  - three load sites — \`rg -c 'load' src/store.txt\` — \`3\`" || fail "row not under the gap-checked record"
grep -qF -- '— 6 sites opened (unverified: 1)' "$plan" || fail "drafted record changed by a check-side row"
ok "a check-side row goes under the newest gap-checked record"

# 7. a sweep over the plan's own directory never matches the plan's own row
sw="$tmp/Plans/s.md"
printf -- '- drafted at 0000000, 2026-10-27, slices 0.9.0 — 0 sites opened (unverified: 0)\n' > "$sw"
python3 "$lr" add "$sw" 'no plan names zqx' "rg -n 'zqx' Plans" >/dev/null
cp "$sw" "$tmp/before"
grep -qF "\`rg -n 'zqx' Plans\` — no output (exit 1)" "$sw" || fail "sweep matched the plan itself"
python3 "$lr" rerun "$sw" >"$tmp/out" || fail "sweep row differs on rerun: $(cat "$tmp/out")"
cmp -s "$sw" "$tmp/before" || fail "plan not restored after rerun"
ok "a sweep over the plan's directory excludes the plan and restores it"

# 8. a row off the writer's form is unparsed and fails rerun
printf -- '- drafted at 0000000, 2026-10-27, slices 0.9.0 — 1 sites opened (unverified: 0)\n  - hand — rg x — one hit\n' > "$tmp/Plans/h.md"
python3 "$lr" rerun "$tmp/Plans/h.md" >"$tmp/out" && fail "rerun passed a row off the writer's form"
grep -q '^unparsed' "$tmp/out" || fail "hand-written row not named"
ok "a row off the writer's form is named and fails rerun"

# 9. a stub's frame record takes rows and reruns; the lines after it are not rows
st="$tmp/Plans/stub.md"
printf -- '# S\n\n## Frame\n\n- framed at 0000000, 2026-10-29, slices 0.11.0\n- value: a sentence\n- shape A: x\n' > "$st"
python3 "$lr" add "$st" 'two load sites' "rg -c 'load' src/store.txt" >/dev/null || fail "add refused a framed record"
[ "$(sed -n '6p' "$st")" = "  - two load sites — \`rg -c 'load' src/store.txt\` — \`3\`" ] || fail "frame row not under the record: $(cat "$st")"
grep -q '^- value: a sentence$' "$st" || fail "frame lines after the record lost"
python3 "$lr" rerun "$st" >"$tmp/out" || fail "frame rerun did not hold: $(cat "$tmp/out")"
grep -q '^rows: 1 held, 0 differ, 0 unverified, 0 unparsed$' "$tmp/out" || fail "frame rerun read lines past the record"
ok "a stub's framed record takes rows and reruns them alone"
