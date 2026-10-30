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

# ---- scripts/profile.py: the risk registry, matched against what a plan touches
pf="$here/scripts/profile.py"
R="$tmp/risk"; mkdir -p "$R/.claude" "$R/src/policy" "$R/src/math" "$R/src/old" "$R/src/ui" "$R/Plans"
git -C "$R" init -q; r_() { git -C "$R" "$@"; }; r_ config user.email t@t; r_ config user.name t
printf '{ "riskRegistry": ".claude/risk.json" }\n' > "$R/.claude/slices.json"
cat > "$R/.claude/risk.json" <<'EOF'
{
  "kinds": { "lifecycle-axis": "a new state or ordering rule", "new-surface": "a new screen" },
  "novelty": { "roots": ["^src/"], "commits": 2, "check": "Name what the area resembles." },
  "classes": [
    { "id": "state-machine", "status": "active",
      "signals": { "paths": ["^src/policy/"], "symbols": ["\\bsnooze\\w*"], "kinds": ["lifecycle-axis"] },
      "check": { "at": "plan", "text": "Tabulate axes x states.", "rounds": 2 }, "evidence": ["#1"] },
    { "id": "numeric", "status": "active",
      "signals": { "paths": ["^src/math/"], "symbols": [], "kinds": [] },
      "check": { "at": "build", "text": "Boundary tests.", "rounds": 0 }, "evidence": [] },
    { "id": "copy", "status": "predicted",
      "signals": { "paths": ["Copy\\.txt$"], "symbols": [], "kinds": ["new-surface"] },
      "check": { "at": "plan", "text": "Read the copy." }, "evidence": [] },
    { "id": "gone", "status": "retired", "retired": "#9 — never fired right",
      "signals": { "paths": ["^src/"], "symbols": [], "kinds": [] },
      "check": { "at": "plan", "text": "x" }, "evidence": [] }
  ]
}
EOF
printf 'a\n' > "$R/src/old/Legacy.txt"; r_ add -A; r_ commit -q -m old
for i in 1 2; do printf '%s\n' "$i" >> "$R/src/policy/PauseRule.txt"; printf '%s\n' "$i" > "$R/src/math/Dose.txt"; printf '%s\n' "$i" > "$R/src/ui/HomeCopy.txt"; r_ add -A; r_ commit -q -m "code $i"; done
for i in 1 2 3; do printf '%s\n' "$i" > "$R/notes.md"; r_ add -A; r_ commit -q -m "docs $i"; done

# 1. check validates; rounds outside a plan check, an unknown kind, and a bad regex refuse
python3 "$pf" check --root "$R" | grep -q '^.claude/risk.json: 4 classes, 2 kinds$' || fail "check refused a valid registry"
sed 's/"rounds": 0/"rounds": 1/' "$R/.claude/risk.json" > "$R/.claude/bad.json"
python3 "$pf" check --root "$R" --registry .claude/bad.json 2>"$R/err" && fail "check passed rounds on a build check"
grep -q 'only a plan check buys rounds' "$R/err" || fail "rounds refusal not named: $(cat "$R/err")"
sed 's/"kinds": \["new-surface"\]/"kinds": ["nope"]/; s/"\^src\/math\/"/"(unclosed"/' "$R/.claude/risk.json" > "$R/.claude/bad.json"
python3 "$pf" check --root "$R" --registry .claude/bad.json 2>"$R/err"; grep -q 'kind nope is not in the kinds vocabulary' "$R/err" && grep -q "signals.paths '(unclosed'" "$R/err" || fail "kind or regex refusal not named: $(cat "$R/err")"
ok "profile check: a valid registry passes; rounds off a plan check, an unknown kind, a bad regex refuse"

# 2. match: a file by path, a file by its stem, a directory as itself, a symbol, a kind; retired never; predicted apart
cat > "$R/Plans/p.md" <<'EOF'
# P

Touches src/math/Dose.txt and the PauseRule, and a snoozed state. A new src/fresh/Thing.txt.

## Verification ledger

- drafted at abc1234, 2026-10-30, slices 0.12.0 — 0 sites opened (unverified: 0)

## After
EOF
python3 "$pf" match "$R/Plans/p.md" --kinds new-surface,odd-kind > "$R/m" || fail "match failed: $(cat "$R/m")"
head -1 "$R/m" | grep -q ' — classes: state-machine, numeric; predicted: copy; novel: src/fresh, odd-kind$' || fail "record line wrong: $(head -1 "$R/m")"
grep -q '^  - state-machine — path: src/policy/PauseRule.txt$' "$R/m" || fail "a CamelCase identifier did not resolve to its file"
grep -q '^  - state-machine — symbol: snoozed$' "$R/m" || fail "a symbol did not match"
grep -q '^  - numeric — path: src/math/Dose.txt$' "$R/m" || fail "a cited path did not match"
grep -q '^  - copy — kind: new-surface$' "$R/m" || fail "a declared kind did not join its class"
grep -q 'gone' "$R/m" && fail "a retired class matched"
grep -q 'novel — path: src/old\|novel — path: src/math' "$R/m" && fail "a recently touched directory read novel"
printf 'See src/old/ for the legacy.\n' > "$R/Plans/o.md"
python3 "$pf" match "$R/Plans/o.md" | head -1 | grep -q ' — classes: unclassified; novel: src/old$' || fail "a directory untouched by the last root commits did not read novel, or docs commits counted: $(python3 "$pf" match "$R/Plans/o.md")"
ok "profile match: path, stem, directory, symbol and kind signals; retired never; predicted apart; novelty counts only root commits"

# 3. --write appends at the end of the ledger section; a re-profile reads its kinds from the record
python3 "$pf" match "$R/Plans/p.md" --kinds lifecycle-axis --write >/dev/null || fail "--write refused"
awk '/^## Verification ledger/{s=1} /^## After/{s=0} s' "$R/Plans/p.md" | grep -q '^- profiled at .* — classes: state-machine, numeric; novel: src/fresh$' || fail "record not written inside the ledger: $(cat "$R/Plans/p.md")"
tail -2 "$R/Plans/p.md" | head -1 | grep -q '^$' && tail -1 "$R/Plans/p.md" | grep -q '^## After$' || fail "the next section was disturbed: $(cat "$R/Plans/p.md")"
python3 "$pf" match "$R/Plans/p.md" | grep -q '^  - state-machine — kind: lifecycle-axis$' || fail "a re-profile did not read its kinds from the record"
printf -- '## Frame\n\n- shape A: do it — kinds: new-surface — value: v\n- shape B: less — kinds: none — value: v\n- drafter'"'"'s pick: shape A — why\n' > "$R/Plans/stub.md"
python3 "$pf" match "$R/Plans/stub.md" | grep -q '^  - copy — kind: new-surface$' || fail "a stub's picked shape's kinds were not read"
ok "profile --write: inside the ledger section; kinds from the record, else the picked shape"

# 4. rounds: the base round, novelty's check in it, then each plan class's rounds; none without a record
python3 "$pf" rounds "$R/Plans/p.md" > "$R/r"
[ "$(cat "$R/r")" = "$(printf 'round 1: base — novel: src/fresh — Name what the area resembles.\nround 2: state-machine — Tabulate axes x states.\nround 3: state-machine — Tabulate axes x states.')" ] || fail "rounds budget wrong: $(cat "$R/r")"
python3 "$pf" rounds "$R/Plans/o.md" >/dev/null; [ $? -eq 3 ] || fail "rounds without a record did not exit 3"
mv "$R/.claude/slices.json" "$R/.claude/off.json"
python3 "$pf" match "$R/Plans/p.md" | grep -q 'no riskRegistry' || fail "no registry was not narrated"
mv "$R/.claude/off.json" "$R/.claude/slices.json"
ok "profile rounds: base plus each plan class's rounds; build checks buy none; no record or registry exits 3"

# 5. a symbol alone suggests a class and buys no round; a decision enters or dismisses it and survives a re-profile
printf '# S\n\nA snooze toggle in prose only.\n\n## Verification ledger\n\n- drafted at abc1234, 2026-10-30, slices 0.12.0 — 0 sites opened (unverified: 0)\n' > "$R/Plans/s.md"
python3 "$pf" match "$R/Plans/s.md" --kinds '' --write | head -1 | grep -q ' — classes: unclassified; suggested: state-machine$' || fail "a symbol-only match entered its class: $(python3 "$pf" match "$R/Plans/s.md" --kinds '' | head -1)"
python3 "$pf" rounds "$R/Plans/s.md" | grep -q '^round 2' && fail "a suggested class bought a round"
python3 "$pf" match "$R/Plans/s.md" --dismiss 'state-machine:ordinary UI prose' --write > "$R/d"
head -1 "$R/d" | grep -q ' — classes: unclassified; dismissed: state-machine$' && grep -q '^  - state-machine — dismissed: ordinary UI prose$' "$R/d" || fail "a dismissal was not recorded: $(cat "$R/d")"
python3 "$pf" match "$R/Plans/s.md" | head -1 | grep -q 'dismissed: state-machine$' || fail "a re-profile dropped the recorded dismissal"
python3 "$pf" match "$R/Plans/s.md" --confirm 'state-machine:the toggle pauses a schedule' --write > "$R/c"
head -1 "$R/c" | grep -q ' — classes: state-machine$' && grep -q '^  - state-machine — confirmed: the toggle pauses a schedule$' "$R/c" || fail "a confirmation did not enter the class: $(cat "$R/c")"
python3 "$pf" rounds "$R/Plans/s.md" | grep -q '^round 2: state-machine' || fail "a confirmed class bought no round"
python3 "$pf" match "$R/Plans/s.md" --confirm nope:x >/dev/null 2>&1 && fail "--confirm took a class the registry lacks"
python3 "$pf" match "$R/Plans/s.md" --dismiss state-machine >/dev/null 2>&1 && fail "--dismiss took no reason"
sed 's/"symbols": \["\\\\bsnooze\\\\w\*"\]/"symbols": [{"re": "\\\\bsnooze\\\\w*", "enters": true}]/' "$R/.claude/risk.json" > "$R/.claude/enters.json"
grep -q '"enters": true' "$R/.claude/enters.json" || fail "fixture: the enters registry was not written"
printf 'A snooze toggle.\n' > "$R/Plans/e.md"
python3 "$pf" match "$R/Plans/e.md" --registry .claude/enters.json --kinds '' | head -1 | grep -q ' — classes: state-machine$' || fail "a symbol marked enters did not enter: $(python3 "$pf" match "$R/Plans/e.md" --registry .claude/enters.json --kinds '')"
ok "profile suggest: a symbol alone suggests and buys no round; --confirm enters, --dismiss records why, both survive a re-profile; enters:true enters"
