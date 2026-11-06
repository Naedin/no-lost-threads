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
grep -q '^rerun: 5 held, 0 line-moved, 0 changed, 1 unverified, 0 unparsed$' "$tmp/out" || fail "rerun count wrong: $(tail -1 "$tmp/out")"
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
grep -q '^rerun: 1 held, 0 line-moved, 0 changed, 0 unverified, 0 unparsed$' "$tmp/out" || fail "frame rerun read lines past the record"
ok "a stub's framed record takes rows and reruns them alone"

# 10. the writer refuses a row its reader could not read back, before anything runs
rt="$tmp/Plans/rt.md"
printf -- '- drafted at 0000000, 2026-11-04, slices 0.13.0 — 0 sites opened (unverified: 0)\n' > "$rt"
cp "$rt" "$tmp/rt.before"
heredoc=$'touch ran; cat <<EOF\none\nEOF'
python3 "$lr" add "$rt" 'heredoc' "$heredoc" >/dev/null 2>"$tmp/err" && fail "add took a multi-line command"
grep -q 'a row is one line' "$tmp/err" || fail "multi-line refusal not named: $(cat "$tmp/err")"
python3 "$lr" add "$rt" $'two\nlines' 'true' >/dev/null 2>&1 && fail "add took a multi-line claim"
python3 "$lr" add "$rt" 'empty' '' >/dev/null 2>&1 && fail "add took an empty command"
python3 "$lr" add "$rt" 'edge' ' true' >/dev/null 2>&1 && fail "add took a command the reader would trim"
python3 "$lr" add "$rt" 'see — `a` b' "touch $tmp/ran" >/dev/null 2>&1 && fail "add took a claim the reader would split as a command"
python3 "$lr" add "$rt" 'see — `touch x` — note' --unverified 'open it' >/dev/null 2>&1 && fail "add took an unverified row the reader would run"
[ -e "$tmp/ran" ] || [ -e "$tmp/Plans/ran" ] && fail "a refused row's command ran"
cmp -s "$rt" "$tmp/rt.before" || fail "a refused row changed the plan: $(cat "$rt")"
python3 "$lr" add "$rt" 'the plain dash — is fine, as is `code` in a claim' 'printf "%s\n" one' >/dev/null || fail "add refused a readable claim"
python3 "$lr" add "$rt" 'an escaped newline is one line' $'printf \'%s\\n\' "$(printf $\'a\\nb\')"' >/dev/null || fail "add refused a one-line escaped command"
python3 "$lr" add "$rt" 'a code span — a claim may hold it after' --unverified 'open `it`' >/dev/null || fail "add refused a readable unverified row"
python3 "$lr" rerun "$rt" >"$tmp/out" || fail "rows the writer took did not read back: $(cat "$tmp/out")"
grep -q '^rerun: 2 held, 0 line-moved, 0 changed, 1 unverified, 0 unparsed$' "$tmp/out" || fail "round trip wrong: $(cat "$tmp/out")"
ok "the writer refuses what its reader cannot read back, before running it; what it takes reads back"

# ---- ledgerDir: rows in the doc's rows file, records and one pointer line in the doc
L="$tmp/led"; mkdir -p "$L/.claude" "$L/src" "$L/Plans/inbox" "$L/Plans/done"; git -C "$L" init -q
printf '{ "ledgerDir": "Plans/.ledger" }\n' > "$L/.claude/slices.json"
printf 'a\nload()\nb\n' > "$L/src/s.txt"
lp="$L/Plans/p.md"
printf '# P\n\nThe prose names zqx.\n\n## Verification ledger\n\n- drafted at abc1234, 2026-11-05, slices 0.15.0 — 0 sites opened (unverified: 0)\n' > "$lp"

# 11. add writes the row to the rows file; the doc keeps its record, recounted, and a pointer
python3 "$lr" add "$lp" 'load sits at line 2' "rg -n 'load' src/s.txt" >/dev/null || fail "add refused under ledgerDir"
python3 "$lr" add "$lp" 'no plan names zqx' "rg -l zqx Plans" >/dev/null
python3 "$lr" add "$lp" 'the caller' --unverified 'open it' >/dev/null
lf="$L/Plans/.ledger/p.rows"
[ -f "$lf" ] || fail "no rows file at $lf"
grep -q '^  - ' "$lp" && fail "a row was written into the doc: $(cat "$lp")"
grep -qF -- '- drafted at abc1234, 2026-11-05, slices 0.15.0 — 3 sites opened (unverified: 1)' "$lp" || fail "record not recounted from the file: $(cat "$lp")"
[ "$(tail -1 "$lp")" = '- claim rows: `Plans/.ledger/p.rows`' ] || fail "pointer not after the record: $(cat "$lp")"
[ "$(grep -c '^- claim rows:' "$lp")" -eq 1 ] || fail "pointer written twice"
grep -qF -- "- drafted at abc1234, 2026-11-05, slices 0.15.0" "$lf" || fail "group header missing: $(cat "$lf")"
grep -qF "\`rg -l zqx Plans\` — no output (exit 1)" "$lf" || fail "a sweep matched its doc's prose or its rows file: $(cat "$lf")"
ok "under ledgerDir the rows go to the rows file; the doc keeps the recounted record and one pointer"

# 12. a check-side row takes its own group; rerun reads the drafted group; show interleaves
printf -- '- gap-checked at def5678, 2026-11-05, slices 0.15.0 — 0 defects (addressed: 0), 0 questions (open: 0)\n' >> "$lp"
python3 "$lr" add "$lp" 'one load' "rg -c load src/s.txt" >/dev/null
grep -qF -- "- gap-checked at def5678, 2026-11-05, slices 0.15.0" "$lf" || fail "no gap-checked group"
python3 "$lr" rerun "$lp" >"$tmp/out" || fail "file rows did not hold: $(cat "$tmp/out")"
grep -q '^rerun: 2 held, 0 line-moved, 0 changed, 1 unverified, 0 unparsed$' "$tmp/out" || fail "rerun read the wrong group: $(cat "$tmp/out")"
python3 "$lr" show "$lp" > "$tmp/out"
[ "$(sed -n '1p;5p' "$tmp/out" | cut -c1-14 | tr '\n' '|')" = "- drafted at a|- gap-checked |" ] || fail "show not interleaved: $(cat "$tmp/out")"
ok "a check-side row gets its record's group; rerun reads the drafted group; show puts rows under records"

# 13. rerun tells a shifted line number from a broken claim
printf 'top\na\nload()\nb\n' > "$L/src/s.txt"
python3 "$lr" rerun "$lp" >"$tmp/out" && fail "a line-moved row exited 0"
grep -q '^line-moved' "$tmp/out" || fail "a shifted line read as changed: $(cat "$tmp/out")"
printf 'a\nload()\nb\n' > "$L/src/s.txt"; printf 'load()\n' > "$L/src/t.txt"
python3 "$lr" add "$lp" 'two files load' "rg -n --sort path load src/s.txt src/t.txt" >/dev/null
python3 - "$lf" <<'PY'
import re, sys
p = sys.argv[1]; lines = open(p).read().split("\n")
row = next(l for l in lines if "two files load" in l); lines.remove(row)
a, b = re.findall(r"`src/[st]\.txt:\d+:load\(\)`", row)
lines.insert(lines.index(next(l for l in lines if l.startswith("- drafted at"))) + 1, row.replace(a + "; " + b, b + "; " + a))
open(p, "w").write("\n".join(lines))
PY
python3 "$lr" rerun "$lp" >"$tmp/out"
grep -q '^line-moved rg -n --sort path load src/s.txt src/t.txt' "$tmp/out" || fail "hits in another order read as changed: $(cat "$tmp/out")"
grep -v 'two files load' "$lf" > "$tmp/lf" && mv "$tmp/lf" "$lf"
printf 'a\nb\n' > "$L/src/s.txt"
python3 "$lr" rerun "$lp" >"$tmp/out"
grep -q '^changed' "$tmp/out" || fail "a vanished site read as line-moved: $(cat "$tmp/out")"
grep -q '^rerun: 1 held, 0 line-moved, 1 changed, 1 unverified, 0 unparsed$' "$tmp/out" || fail "counts wrong: $(tail -1 "$tmp/out")"
printf 'a\nload()\nb\n' > "$L/src/s.txt"
ok "rerun classifies held, line-moved, and changed, and counts each"

# 14. a run killed while holding the files empty is undone by the next run
cp "$lp" "$tmp/lp.before"; cp "$lf" "$tmp/lf.before"
python3 "$lr" add "$lp" 'slow' 'sleep 5' >/dev/null 2>&1 & k=$!
sleep 1; [ -s "$lp" ] && fail "doc not held empty while its command ran"
python3 "$lr" rerun "$lp" >/dev/null 2>"$tmp/err"; [ $? -eq 2 ] || fail "a second run went ahead while the first held the doc"
grep -q 'another ledger-row run' "$tmp/err" || fail "concurrent refusal not named: $(cat "$tmp/err")"
python3 "$lr" show "$lp" >/dev/null 2>&1 && fail "show read a doc another run holds empty"
kill -9 "$k"; wait "$k" 2>/dev/null
[ -s "$lp" ] && fail "a SIGKILL left the doc whole, so the case proves nothing"
python3 "$lr" rerun "$lp" >/dev/null
cmp -s "$lp" "$tmp/lp.before" || fail "the killed run's doc not restored: $(cat "$lp")"
cmp -s "$lf" "$tmp/lf.before" || fail "the killed run's rows file not restored"
python3 -I -c 'import importlib.util as u,sys;s=u.spec_from_file_location("lr",sys.argv[1]);m=u.module_from_spec(s);s.loader.exec_module(m);sys.exit(m.moved_only("12 lines, first: `a:1:x`","12 lines, first: `a:2:x`"))' "$lr" || fail "a summarized listing read as line-moved"
ok "a killed run's emptied doc and rows file come back on the next run; a concurrent run refuses"

# 15. a renamed doc follows its pointer; a promoted stub's group of the same name is history
git -C "$L" mv -f Plans/p.md Plans/renamed.md 2>/dev/null || mv "$lp" "$L/Plans/renamed.md"
python3 "$lr" rerun "$L/Plans/renamed.md" >"$tmp/out" || fail "renamed doc lost its rows: $(cat "$tmp/out")"
sp="$L/Plans/inbox/feat.md"
printf '# S\n\n## Frame\n\n- framed at 0000000, 2026-11-05, slices 0.15.0\n- value: v\n' > "$sp"
python3 "$lr" add "$sp" 'one load' "rg -c load src/s.txt" >/dev/null
[ "$(sed -n '6p' "$sp")" = '- claim rows: `Plans/.ledger/feat.rows`' ] || fail "stub pointer not under its record: $(cat "$sp")"
rm "$sp"; fp="$L/Plans/feat.md"
printf '# F\n\n- drafted at 1111111, 2026-11-05, slices 0.15.0 — 0 sites opened (unverified: 0)\n' > "$fp"
python3 "$lr" add "$fp" 'one load' "rg -c load src/s.txt" >/dev/null
python3 "$lr" rerun "$fp" >"$tmp/out" || fail "plan beside a history group did not hold: $(cat "$tmp/out")"
grep -q '^rerun: 1 held' "$tmp/out" || fail "rerun read the stub's frame group"
python3 "$lr" show "$fp" | grep -q '^history' || fail "the stub's frame group not shown as history"
ok "a renamed doc follows its pointer; a promoted stub's frame rows stay as history, never rerun"

# 16. move carries an inline ledger into the file; orphans lists rows no doc owns or that are spent
mp="$L/Plans/old.md"
printf -- '- drafted at 2222222, 2026-11-01, slices 0.14.0 — 2 sites opened (unverified: 1)\n  - one load — `rg -c load src/s.txt` — `1`\n  - x — unverified: y\n- gap-checked at 3333333, 2026-11-02, slices 0.14.0 — 0 defects (addressed: 0), 0 questions (open: 0)\n  - one load again — `rg -c load src/s.txt` — `1`\n' > "$mp"
python3 "$lr" rerun "$mp" >/dev/null || fail "inline rows unread under ledgerDir"
python3 "$lr" move "$mp" | grep -q '^3 rows moved' || fail "move miscounted"
grep -q '^  - ' "$mp" && fail "rows left in the doc after move"
[ "$(sed -n '2p' "$mp")" = '- claim rows: `Plans/.ledger/old.rows`' ] || fail "move's pointer misplaced: $(cat "$mp")"
python3 "$lr" rerun "$mp" | grep -q '^rerun: 1 held, 0 line-moved, 0 changed, 1 unverified' || fail "moved rows did not rerun"
printf '# stray\n- drafted at 0, 2026-01-01\n' > "$L/Plans/.ledger/gone.rows"
mv "$mp" "$L/Plans/done/old.md"
(cd "$L" && python3 "$lr" orphans --done Plans/done) >"$tmp/out" && fail "orphans exited 0 with orphans"
grep -q '^orphan     Plans/.ledger/gone.rows' "$tmp/out" || fail "an ownerless rows file not listed: $(cat "$tmp/out")"
grep -q '^spent      Plans/.ledger/old.rows' "$tmp/out" || fail "a done doc's rows not listed"
grep -q 'renamed.rows\|p.rows\|feat.rows' "$tmp/out" && fail "an owned rows file listed: $(cat "$tmp/out")"
ok "move empties an inline ledger into the file; orphans lists ownerless and spent rows files"

# 17. a pointer naming a missing rows file is a refusal, never an empty pass; orphans lists it
np="$L/Plans/nofile.md"
printf -- '- drafted at 4444444, 2026-11-05, slices 0.15.0 — 1 sites opened (unverified: 0)\n- claim rows: `Plans/.ledger/nofile.rows`\n' > "$np"
for c in rerun show; do
  python3 "$lr" $c "$np" >/dev/null 2>"$tmp/err"; [ $? -eq 2 ] || fail "$c passed a pointer to a missing file"
  grep -q 'which is missing' "$tmp/err" || fail "$c refusal not named: $(cat "$tmp/err")"
done
python3 "$lr" add "$np" 'one load' "rg -c load src/s.txt" >/dev/null 2>&1 && fail "add restarted a missing rows file"
[ -e "$L/Plans/.ledger/nofile.rows" ] && fail "add created the missing rows file"
(cd "$L" && python3 "$lr" orphans) >"$tmp/out" && fail "orphans exited 0 over a missing rows file"
grep -q '^missing    Plans/.ledger/nofile.rows — Plans/nofile.md points at it' "$tmp/out" || fail "missing rows file not listed: $(cat "$tmp/out")"
rm "$np"
ok "a pointer to a missing rows file refuses rerun, show, and add; orphans lists it"

# 18. a row past a non-bearing record still belongs to the bearing record above; profile lines stay
ap="$L/Plans/across.md"
cat > "$ap" <<'EOF'
## Verification ledger

```
  - example — `rg x` — `1`
```

- drafted at 5555555, 2026-11-01, slices 0.14.0 — 1 sites opened (unverified: 0)
  - one load — `rg -c load src/s.txt` — `1`
- gap-checked at 6666666, 2026-11-02, slices 0.14.0 — 0 defects (addressed: 0), 0 questions (open: 0)
- changed at 7777777, 2026-11-02 — drafter: a fold
  - s holds a — `rg -c a src/s.txt` — `1`
- profiled at 7777777, 2026-11-02, slices 0.14.0 — classes: copy
  - copy — path: src/s.txt

  - stray — `rg -c b src/s.txt` — `1`
EOF
python3 "$lr" show "$ap" > "$tmp/out"
sed -n '/^- gap-checked/,$p' "$tmp/out" | grep -q 's holds a' || fail "a row past changed at not shown under its record: $(cat "$tmp/out")"
python3 "$lr" move "$ap" > "$tmp/out"
grep -q '^2 rows moved' "$tmp/out" || fail "move miscounted across a non-bearing record: $(cat "$tmp/out")"
grep -q '^left       line .*stray' "$tmp/out" || fail "a row under no bearing record not reported: $(cat "$tmp/out")"
grep -q 'example' "$tmp/out" && fail "a fenced example reported as a row"
grep -qF '  - s holds a' "$ap" && fail "the row past changed at stayed inline"
grep -qF '  - copy — path: src/s.txt' "$ap" || fail "a profiled record's line was moved"
grep -qF '  - example — `rg x` — `1`' "$ap" || fail "a fenced example was moved"
grep -A1 '^- gap-checked at 6666666' "$L/Plans/.ledger/across.rows" | grep -q 's holds a' || fail "the row not in its record's group: $(cat "$L/Plans/.ledger/across.rows")"
ok "a row past a non-bearing record belongs to the bearing record above; profile lines, fences, and strays stay, strays named"

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

# 6. only the paths a plan changes enter; a path it cites suggests; rows and commands are neither
cat > "$R/Plans/c.md" <<'EOF'
# C

Reads src/policy/PauseRule.txt and calls src/math/Dose.txt to report on them.

## Changed Files

Generating sweep: `rg -n 'x' src/policy/ src/math/`.

- `src/ui/HomeCopy.txt`

## Claim ledger <!-- slices: ledger -->

- drafted at abc1234, 2026-11-04, slices 0.13.0 — 1 sites opened (unverified: 0)
  - snoozed sits in Dose — `rg -n snoozed src/math/Dose.txt` — no output (exit 1)

## After
EOF
python3 "$pf" match "$R/Plans/c.md" --kinds '' > "$R/m" || fail "match failed: $(cat "$R/m")"
head -1 "$R/m" | grep -q ' — classes: unclassified; predicted: copy; suggested: state-machine, numeric$' || fail "a cited path entered its class, or a row counted: $(cat "$R/m")"
grep -q '^  - state-machine — cited: src/policy/PauseRule.txt$' "$R/m" || fail "a cited path was not named: $(cat "$R/m")"
grep -q 'symbol: snoozed' "$R/m" && fail "a symbol in a ledger row suggested a class"
python3 "$pf" match "$R/Plans/c.md" --kinds '' --dismiss 'state-machine:reads it only' | head -1 | grep -q 'dismissed: state-machine' || fail "a cited-path suggestion could not be dismissed"
printf '# B\n\nSee src/policy/PauseRule.txt.\n\n## Scope\n\n- In: `src/math/Dose.txt`\n- Out: src/fresh/Thing.txt — without it: none\n  and src/old/Legacy.txt too\n\n## After\n\nsrc/ui/HomeCopy.txt\n' > "$R/Plans/b.md"
python3 "$pf" match "$R/Plans/b.md" --kinds '' > "$R/m"
head -1 "$R/m" | grep -q ' — classes: numeric; suggested: state-machine, copy$' || fail "built-in Scope's In not read: $(cat "$R/m")"
grep -q 'src/fresh\|src/old' "$R/m" && fail "an Out item entered or read novel: $(cat "$R/m")"
printf '# H\n\n## Scope\n### In scope\n1. `src/math/Dose.txt`\n### Out of scope\n- Out: src/policy/PauseRule.txt — without it: none\n## Next\n' > "$R/Plans/h.md"
python3 "$pf" match "$R/Plans/h.md" --kinds '' | head -1 | grep -q ' — classes: numeric; suggested: state-machine$' || fail "an Out sub-heading entered: $(python3 "$pf" match "$R/Plans/h.md" --kinds '')"
printf '# M\n\n## Scope\n\n- changed at src/math/Dose.txt, the entry\n\n## Files changed\n\n`src/ui/x.md` `rg -n x src/policy/ y`\n\n```\n# not a heading\n```\n\n- `src/math/Dose.txt`\n' > "$R/Plans/m.md"
python3 "$pf" match "$R/Plans/m.md" --kinds '' | head -1 | grep -q ' — classes: numeric' || fail "a path past a fenced comment did not enter: $(python3 "$pf" match "$R/Plans/m.md" --kinds '')"
python3 "$pf" match "$R/Plans/m.md" --kinds '' | grep -q 'path: src/policy' && fail "a command after another span entered its class"
printf '# E\n\n## Changed Files\n\n## Scope\n\n- In: `src/math/Dose.txt`\n- changed at src/policy/PauseRule.txt, the entry\n' > "$R/Plans/e2.md"
python3 "$pf" match "$R/Plans/e2.md" --kinds '' | head -1 | grep -q ' — classes: state-machine, numeric' || fail "an empty Changed Files blocked Scope, or a prose bullet read as a record: $(python3 "$pf" match "$R/Plans/e2.md" --kinds '')"
ok "profile paths: Changed Files, else Scope's In; Out, ledger rows and commands never enter; a cited path suggests; a file with neither reads whole"

# 7. match prints the plan checks the work bears on, never into the record
python3 "$pf" match --paths src/policy/PauseRule.txt,src/math/Dose.txt --kinds new-surface --root "$R" > "$R/m"
grep -q '^plan check — state-machine: Tabulate axes x states\.$' "$R/m" || fail "an entered class's plan check not printed: $(cat "$R/m")"
grep -q '^plan check — copy: Read the copy\.$' "$R/m" || fail "a predicted class's plan check not printed: $(cat "$R/m")"
grep -q 'Boundary tests' "$R/m" && fail "a build check printed as a plan check"
python3 "$pf" match "$R/Plans/c.md" --kinds '' | grep -q '^plan check (suggested) — state-machine: ' || fail "a suggestion's check not marked suggested"
python3 "$pf" match "$R/Plans/c.md" --kinds '' --write >/dev/null
grep -q '^plan check' "$R/Plans/c.md" && fail "a plan check reached the record"
python3 "$pf" match "$R/Plans/c.md" --kinds '' --dismiss 'state-machine:reads it only' | grep -q '^plan check.*state-machine' && fail "a dismissed class's check was printed"
ok "profile match: prints plan checks for what the work bears on, suggestions marked, never into the record"
