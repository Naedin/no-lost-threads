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

# 9. --docs derives the files the shown keys name, counted by key, from the filtered view
cat > "$tmp/docs.md" <<'EOF2'
## Entries

drift/n
  2026-09-01 | s1 | one.
    Placement: Plans/active/pre-pr.md §Pins — amend "x".
drift/n
  2026-09-05 | s2 | two (see .claude/commands/closeout.md:12 and docs/direction.md).
drift/o
  2026-09-02 | s1 | once.
    Placement: Plans/active/pre-pr.md §2.
drift/p
  LANDED abc1234 — docs/principles.md §measure.
EOF2
python3 "$rl" view --recurred --docs --root "$tmp" --log docs.md 2>/dev/null > "$tmp/docs.out" || fail "--docs refused"
grep -qx '1	Plans/active/pre-pr.md' "$tmp/docs.out" || fail "--docs under --recurred did not count pre-pr.md once: $(cat "$tmp/docs.out")"
grep -qx '1	.claude/commands/closeout.md' "$tmp/docs.out" || fail "--docs missed a dotted-directory path with a :line suffix"
grep -q 'principles' "$tmp/docs.out" && fail "--docs under --recurred showed a path from an unshown key"
python3 "$rl" view --docs --root "$tmp" --log docs.md 2>/dev/null | head -1 | grep -qx '2	Plans/active/pre-pr.md' || fail "--docs over the whole log did not rank pre-pr.md first at 2 keys"
python3 "$rl" view --docs --root "$tmp" --log docs.md 2>/dev/null | grep -qx '1	docs/principles.md' || fail "--docs missed the path in a LANDED line"
ok "--docs lists the files the shown keys name, most-named first"

# ---- scripts/marker-stream.py: the marker stream classified — organic, review (the
# Process-Review trailer), bookkeeping (log/ledger-only) — so the trigger and the tally
# count what no review has adjudicated.
ms="$here/scripts/marker-stream.py"
M="$tmp/ms"; mkdir -p "$M"
git init -q -b main "$M"; m() { git -C "$M" "$@"; }
m config user.email t@t; m config user.name t
mkdir -p "$M/.claude"
cat > "$M/.claude/threads.json" <<'EOF2'
{ "markerPattern": "^[a-z(]*process[:/)]", "markTag": "process-review-mark",
  "retroLogPath": ".claude/retro-findings.log", "ledgerPath": ".claude/ledger.md",
  "trigger": { "n": 10, "concentration": 2 } }
EOF2
printf '# base\n' > "$M/CLAUDE.md"; printf '## Entries\n' > "$M/.claude/retro-findings.log"; printf '## Live\n' > "$M/.claude/ledger.md"
m add -A; m commit -q -m "base"; m tag process-review-mark
printf 'rule 1\n' >> "$M/CLAUDE.md"; m add -A; m commit -q -m "docs(process/claude): rule 1"
printf 'k/a\n  2026-09-01 | s | x.\n' >> "$M/.claude/retro-findings.log"; printf 'entry\n' >> "$M/.claude/ledger.md"; m add -A; m commit -q -m "docs(process/retro): capture two"
printf 'rule 2\n' >> "$M/CLAUDE.md"; m add -A; m commit -q -m "docs(process/claude): rule 2 — candidate A" -m "Held 2026-09-08, approved." --trailer "Process-Review: 2026-09-09"
printf 'k/b\n  LANDED abc — x.\n' >> "$M/.claude/retro-findings.log"; m add -A; m commit -q -m "docs(process/retro): A LANDED" --trailer "Process-Review: 2026-09-09"
printf 'feature\n' > "$M/f.txt"; m add -A; m commit -q -m "feat: not a marker (docs(process) in the body only)" -m "docs(process/x): quoted"
printf 'rule 3\n' >> "$M/CLAUDE.md"; printf 'z\n' >> "$M/.claude/ledger.md"; m add -A; m commit -q -m "process: a squash subject (#7)"
python3 "$ms" count --root "$M" > "$M/count.out" 2>"$M/err" || fail "marker-stream count failed: $(cat "$M/err")"
grep -q '^5 markers since process-review-mark (20[0-9-]*, [0-9a-f]*)\.\.HEAD: 2 organic · 2 review · 1 bookkeeping$' "$M/count.out" || fail "count line wrong: $(cat "$M/count.out")"
python3 "$ms" list --root "$M" 2>/dev/null > "$M/list.out"
grep -q '^review	.*candidate A$' "$M/list.out" || fail "a trailered candidate landing is not review"
grep -q '^review	.*A LANDED$' "$M/list.out" || fail "trailered bookkeeping is review, not bookkeeping"
grep -q '^bookkeeping	.*capture two$' "$M/list.out" || fail "a log+ledger-only commit is not bookkeeping"
grep -q '^organic	.*squash subject' "$M/list.out" || fail "a ledger+doc commit under the squash spelling is not organic"
grep -q 'not a marker' "$M/list.out" && fail "a body-only mention counted as a marker"
python3 "$ms" files --root "$M" 2>/dev/null > "$M/files.out"
grep -q '^2	CLAUDE.md$' "$M/files.out" || fail "files did not count CLAUDE.md at 2 organic commits: $(cat "$M/files.out")"
grep -q '^1	.claude/ledger.md$' "$M/files.out" || fail "files did not count the ledger's one organic touch"
grep -q '1 at or above concentration 2' "$M/files.out" || fail "files did not name the concentration count: $(cat "$M/files.out")"
python3 "$ms" count --all --root "$M" 2>/dev/null | grep -q '^5 markers since all of HEAD' || fail "--all did not read the whole history"
python3 "$ms" count --since HEAD~3 --root "$M" 2>/dev/null | grep -q "^2 markers" || fail "--since did not replace the mark"
python3 "$ms" count --pattern '^docs(process' --root "$M" 2>/dev/null | grep -q '^4 markers' || fail "--pattern with a bare paren did not override as a BRE"
m tag -d process-review-mark >/dev/null
python3 "$ms" count --root "$M" >/dev/null 2>"$M/err2" && fail "ran with no mark and no --since"
grep -q 'no such rev: process-review-mark' "$M/err2" || fail "a missing mark was not named: $(cat "$M/err2")"
ok "marker-stream: organic / review / bookkeeping classified; files, --all, --since, --pattern; a missing mark refuses"

# ---- scripts/land-process-commit.py: one commit lands on the default branch through the
# adopter's own pre-commit hook, the sha printed is the remote's, the slice branch drops
# its duplicate, and every failure leaves nothing pushed and no worktree behind.
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
lp="$here/scripts/land-process-commit.py"
L="$tmp/land"
mkdir -p "$L"
git init -q --bare -b master "$L/origin.git"
git clone -q "$L/origin.git" "$L/primary" 2>/dev/null
g() { git -C "$L/primary" "$@"; }
g config user.email t@t; g config user.name t; g config core.hooksPath hooks
mkdir -p "$L/primary/hooks"
cat > "$L/primary/hooks/pre-commit" <<'HOOK'
#!/bin/sh
# marks that it ran, in the file LAND_TEST_MARK names; refuses a message carrying REFUSE
[ -n "$LAND_TEST_MARK" ] && echo "ran in $(pwd)" >> "$LAND_TEST_MARK"
if git diff --cached --name-only | grep -q '^refuse\.md$'; then echo "hook: refused" >&2; exit 1; fi
exit 0
HOOK
chmod +x "$L/primary/hooks/pre-commit"
printf '# base\n' > "$L/primary/CLAUDE.md"
g add -A; g commit -q -m "base"; g push -q origin master 2>/dev/null
git -C "$L/origin.git" symbolic-ref HEAD refs/heads/master
g remote set-head origin -a >/dev/null 2>&1
g worktree add -q -b slice "$L/slice" master 2>/dev/null
s() { git -C "$L/slice" "$@"; }
s config user.email t@t; s config user.name t
printf 'feature\n' > "$L/slice/feature.txt"; s add -A; s commit -q -m "feat: a slice"
printf '# base\n\nA process rule.\n' > "$L/slice/CLAUDE.md"; s add -A; s commit -q -m "docs(process/rules): a rule"
proc="$(s rev-parse HEAD)"

# 1. lands: the hook fired in the throwaway, stdout is the remote's sha, the branch dropped the duplicate
mark="$L/mark"; : > "$mark"
landed="$(cd "$L/slice" && LAND_TEST_MARK="$mark" python3 "$lp" "$proc" 2>"$L/err1")" || fail "landing failed: $(cat "$L/err1")"
remote="$(git -C "$L/origin.git" rev-parse refs/heads/master)"
[ "$landed" = "$remote" ] || fail "stdout ($landed) is not the remote's sha ($remote)"
[ "$(wc -l < <(printf '%s\n' "$landed"))" -eq 1 ] || fail "stdout carried more than the sha"
grep -q 'ran in .*land-process-commit-' "$mark" || fail "the pre-commit hook did not run in the throwaway worktree"
[ "$(git -C "$L/origin.git" log -1 --format=%s master)" = "docs(process/rules): a rule" ] || fail "the remote's tip is not the process commit"
[ "$(git -C "$L/origin.git" log --format=%s master | wc -l | tr -d ' ')" -eq 2 ] || fail "the remote got more than one commit"
grep -q 'patch identical' "$L/err1" || fail "byte-identity line missing"
[ "$(s rev-list --count origin/master..HEAD)" -eq 1 ] || fail "the slice branch kept the duplicate ($(s rev-list --count origin/master..HEAD) ahead)"
[ "$(s log -1 --format=%s)" = "feat: a slice" ] || fail "the slice branch's tip is not the feature commit"
[ "$(g worktree list | wc -l | tr -d ' ')" -eq 2 ] || fail "a throwaway worktree was left behind: $(g worktree list)"
ok "land-process-commit: lands through the hook, prints the remote's sha, drops the duplicate"

# 2. already landed by patch: refuses, nothing pushed
(cd "$L/slice" && python3 "$lp" "$proc" >/dev/null 2>"$L/err2") && fail "landed a patch the remote already holds"
grep -q 'already on origin/master' "$L/err2" || fail "already-landed refusal not named: $(cat "$L/err2")"
ok "land-process-commit: a patch already upstream is refused"

# 3. a red hook: nothing pushed, no worktree left
printf 'x\n' > "$L/slice/refuse.md"; s add -A; s -c core.hooksPath=/dev/null commit -q -m "docs(process/x): refused"
bad="$(s rev-parse HEAD)"; before="$(git -C "$L/origin.git" rev-parse master)"
(cd "$L/slice" && python3 "$lp" "$bad" >"$L/out3" 2>"$L/err3") && fail "landed past a red hook"
[ -s "$L/out3" ] && fail "printed a sha though nothing was pushed"
grep -q 'hook refused' "$L/err3" || fail "red hook not named: $(cat "$L/err3")"
grep -q 'hook: refused' "$L/err3" || fail "the hook's own output was not surfaced"
[ "$(git -C "$L/origin.git" rev-parse master)" = "$before" ] || fail "the remote moved on a red hook"
[ "$(g worktree list | wc -l | tr -d ' ')" -eq 2 ] || fail "a worktree was left after a red hook"
s reset -q --hard HEAD^
ok "land-process-commit: a red hook pushes nothing and leaves no worktree"

# 4. a conflict: master moved on the same lines
g merge -q --ff-only origin/master
printf '# base\n\nA different rule.\n' > "$L/primary/CLAUDE.md"; g add -A; g commit -q -m "docs(process/rules): other"; g push -q origin master 2>/dev/null
printf '# base\n\nA third rule.\n' > "$L/slice/CLAUDE.md"; s add -A; s commit -q -m "docs(process/rules): conflicting"
conf="$(s rev-parse HEAD)"; before="$(git -C "$L/origin.git" rev-parse master)"
(cd "$L/slice" && python3 "$lp" "$conf" >"$L/out4" 2>"$L/err4") && fail "landed through a conflict"
[ -s "$L/out4" ] && fail "printed a sha on a conflict"
grep -q 'conflicts; nothing pushed' "$L/err4" || fail "conflict not named: $(cat "$L/err4")"
[ "$(git -C "$L/origin.git" rev-parse master)" = "$before" ] || fail "the remote moved on a conflict"
[ "$(g worktree list | wc -l | tr -d ' ')" -eq 2 ] || fail "a worktree was left after a conflict"
ok "land-process-commit: a cherry-pick conflict fails loud and pushes nothing"

# 5. tracked changes refuse when a rebase would follow; --no-rebase lifts it; --branch names the target
printf 'dirty\n' >> "$L/slice/feature.txt"
(cd "$L/slice" && python3 "$lp" "$conf" >/dev/null 2>"$L/err5") && fail "ran on a dirty tree"
grep -q 'tracked changes' "$L/err5" || fail "dirty tree not named: $(cat "$L/err5")"
s checkout -q -- feature.txt
(cd "$L/slice" && python3 "$lp" "$conf" --branch nosuch >/dev/null 2>"$L/err5b") && fail "landed on a branch the remote lacks"
ok "land-process-commit: a dirty tree refuses; --branch is honored"
echo "all cases passed"
