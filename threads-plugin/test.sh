#!/usr/bin/env bash
# threads — prove the scripts on the shapes live use has broken them on.
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
python3 "$rl" view --keys --root "$tmp" --log log.md | grep -q 'scope-leak/a .*recurred after LANDED abc1234 — somewhere\.$' || fail "view does not mark a recurrence after LANDED with the landed status line"
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

# 6. retro's own-artifact fix is a `Fixed:` continuation line: the key stays live, the check passes
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

# 3b. a `Caught:` continuation drops its occurrence from --reached; an uncaught occurrence after a caught one escapes
cat > "$tmp/caught.md" <<'EOF3'
## Entries

unverified-claims/i
  2026-09-23 | self | five defects at check. Cost: five defects.
    Caught: /slices:check — draft-brief.md §Implementation Notes states the rule.
unverified-claims/i
  2026-09-24 | self | three more at check.
    Placement: draft-brief.md §Acceptance Criteria — amend.
    Caught: /slices:check — draft-brief.md §Acceptance Criteria states the rule.
drift/j
  2026-09-20 | self | caught once.
    Caught: /pre-pr — land.md §4.
drift/j
  2026-09-25 | self | reached implementation this time.
scope-leak/k
  2026-09-01 | s1 | one.
scope-leak/k
  LANDED abc1234 — doc.md.
scope-leak/k
  2026-09-05 | s2 | back, but caught.
    Caught: guards — doc.md §x.
scope-leak/l
  2026-09-01 | s1 | one.
scope-leak/l
  2026-09-02 | s2 | two.
EOF3
python3 "$check" --root "$tmp" --paths caught.md >/dev/null 2>&1 || fail "a Caught: continuation fails the retro-log check"
python3 "$rl" view --keys --recurred --root "$tmp" --log caught.md 2>/dev/null > "$tmp/rec.out"
grep -q '4 recurred (two or more occurrences, 2 only at a gate)' "$tmp/rec.out" || fail "summary does not count gate-only recurrences: $(head -1 "$tmp/rec.out")"
grep -q '^unverified-claims/i  ×2 (2 caught)  2026-09-23..2026-09-24$' "$tmp/rec.out" || fail "--recurred dropped or mislabeled a caught key: $(cat "$tmp/rec.out")"
python3 "$rl" view --keys --reached --root "$tmp" --log caught.md 2>/dev/null > "$tmp/rch.out"
grep -q 'showing 2 of 4 keys (--recurred --reached)' "$tmp/rch.out" || fail "--reached did not hide the gate-only keys: $(cat "$tmp/rch.out")"
grep -q '^drift/j  ×2 (1 caught)  2026-09-20..2026-09-25  escaped /pre-pr$' "$tmp/rch.out" || fail "an uncaught occurrence after a caught one is not marked escaped: $(cat "$tmp/rch.out")"
grep -q '^scope-leak/l  ×2  ' "$tmp/rch.out" || fail "--reached dropped a plain recurrence"
grep -q '^scope-leak/k' "$tmp/rch.out" && fail "a caught occurrence after LANDED ranked under --reached"
python3 "$rl" compact --root "$tmp" --log caught.md 2>/dev/null || fail "compact refused a log with Caught: lines"
python3 "$rl" view --keys --reached --root "$tmp" --log caught.md 2>/dev/null | grep -q 'showing 2 of 4 keys' || fail "compaction changed what --reached shows"
ok "Caught: is a continuation the check accepts; --reached counts it and does not rank it; an escape ranks regardless of count"

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
drift/q
  2026-09-03 | s1 | no home.
    Placement: none
drift/r
  2026-09-04 | s1 | caught by a named class.
    Placement: check-brief.md *Real-gate vs proxy*
    Caught: /slices:check — check-brief.md *Real-gate vs proxy* states the rule.
drift/s
  LANDED def5678 — gap-check.md *Real-gate vs proxy*: the gate names its proxy.
EOF2
python3 "$rl" view --recurred --docs --root "$tmp" --log docs.md 2>/dev/null > "$tmp/docs.out" || fail "--docs refused"
grep -qx '1	Plans/active/pre-pr.md' "$tmp/docs.out" || fail "--docs under --recurred did not count pre-pr.md once: $(cat "$tmp/docs.out")"
grep -qx '1	.claude/commands/closeout.md' "$tmp/docs.out" || fail "--docs missed a dotted-directory path with a :line suffix"
grep -q 'principles' "$tmp/docs.out" && fail "--docs under --recurred showed a path from an unshown key"
python3 "$rl" view --docs --root "$tmp" --log docs.md 2>/dev/null | grep -q 'none' && fail "--docs listed a Placement: none as a path"
python3 "$rl" view --docs --root "$tmp" --log docs.md 2>/dev/null | head -1 | grep -qx '2	Plans/active/pre-pr.md' || fail "--docs over the whole log did not rank pre-pr.md first at 2 keys"
python3 "$rl" view --docs --root "$tmp" --log docs.md 2>/dev/null | grep -qx '1	docs/principles.md' || fail "--docs missed the path in a LANDED line"
python3 "$rl" view --docs --root "$tmp" --log docs.md 2>/dev/null | grep -qx '1	check-brief.md' || fail "--docs missed a pointer naming a numbered item by name"
python3 "$rl" view --docs --root "$tmp" --log docs.md 2>/dev/null | grep -qx '1	gap-check.md' || fail "--docs missed a LANDED where naming a numbered item by name"
ok "--docs lists the files the shown keys name, most-named first; a bare §-pointer, a numbered one, and a named item count, in a Placement: or a LANDED where; Placement: none does not"

# 10. ARC is an annotation: transparent to state and count, kept by compact on either side
# of a closing status, refused on a non-slug name; --arc prints the carrying keys by the
# date each entered the arc (the ARC line's date, else the first occurrence) with their
# dated blocks — the trajectory, derived; --arcs lists the arcs.
cat > "$tmp/arc.md" <<'EOF2'
## Entries

drift/q
  2026-09-01 | s1 | stub field added by hand.
drift/q
  ARC why-not-now — the deferral moved from a stub field to a trailer to a pinned form.
drift/q
  LANDED abc1234 — doc.md §trailer.
scope-leak/r
  2026-09-03 | s2 | the form was pinned without the trailer.
scope-leak/r
  ARC why-not-now — the pinned form is the third carrier.
drift/q
  2026-09-05 | s3 | came back: a gate re-formed without the trailer.
drift/s
  2026-09-04 | s4 | unrelated.
drift/s
  ARC other-arc — not this one.
drift/v
  LANDED 0000000 — compacted before the arc existed: no date of its own.
drift/v
  ARC why-not-now 2026-08-30 — the precursor, dated by the writer.
drift/w
  RETIRED 1111111 — no date anywhere.
drift/w
  ARC why-not-now — undated: stream order, last.
EOF2
python3 "$check" --root "$tmp" --paths arc.md >/dev/null 2>&1 || fail "an ARC block fails the retro-log check"
python3 "$rl" view --keys --root "$tmp" --log arc.md 2>/dev/null | grep -q '^drift/q  ×2  2026-09-01..2026-09-05  recurred after LANDED abc1234 — doc\.md §trailer\.  arc:why-not-now$' || fail "ARC changed drift/q's state or count, or the key line lacks its arc: $(python3 "$rl" view --keys --root "$tmp" --log arc.md 2>/dev/null | grep '^drift/q')"
python3 "$rl" view --arc why-not-now --root "$tmp" --log arc.md 2>/dev/null > "$tmp/arc.out" || fail "--arc refused"
grep -q '^arc why-not-now: 4 keys, by date entered (1 undated, stream order last)$' "$tmp/arc.out" || fail "--arc header wrong: $(head -1 "$tmp/arc.out")"
[ "$(grep -o '^[a-z-]*/[a-z]* ' "$tmp/arc.out" | tr -d ' ' | tr '\n' ' ')" = "drift/v drift/q scope-leak/r drift/w " ] || fail "--arc is not by date entered, undated last: $(grep -o '^[a-z-]*/[a-z]* ' "$tmp/arc.out" | tr '\n' ' ')"
grep -q '^  ARC why-not-now 2026-08-30 — the precursor' "$tmp/arc.out" || fail "--arc lost the ARC line's date"
grep -q '^drift/v  ×0  2026-08-30 (entered)  LANDED$' "$tmp/arc.out" || fail "a key sorted on its ARC date does not show it in the header: $(grep '^drift/v' "$tmp/arc.out")"
python3 "$rl" view --keys --root "$tmp" --log arc.md 2>/dev/null | grep -q '^drift/v  ×0  LANDED 0000000 — compacted before the arc existed: no date of its own.  arc:why-not-now$' || fail "a closed key line lacks its arc tag"
python3 "$rl" view --keys --since 2026-08-30 --root "$tmp" --log arc.md 2>/dev/null | grep -q '^drift/v ' || fail "--since does not read an ARC line's date"
python3 "$rl" view --arcs --root "$tmp" --log arc.md 2>/dev/null > "$tmp/arcs.out" || fail "--arcs refused"
grep -qx '2 arcs' "$tmp/arcs.out" || fail "--arcs miscounted: $(head -1 "$tmp/arcs.out")"
grep -qx 'why-not-now	4 keys · 2 live · 2 closed' "$tmp/arcs.out" || fail "--arcs split wrong: $(cat "$tmp/arcs.out")"
printf 'drift/x\n  LANDED abc1234 2026-09-09 — dated.\n' > "$tmp/dated.md"
python3 "$check" --root "$tmp" --paths dated.md 2>/dev/null | grep -q 'only ARC carries a date' || fail "the check passed a date on LANDED"
grep -q '^drift/q  ×2  2026-09-01..2026-09-05  recurred after LANDED$' "$tmp/arc.out" || fail "--arc key line lacks state and count"
grep -q '  LANDED abc1234 — doc.md §trailer.' "$tmp/arc.out" || fail "--arc dropped the landing"
grep -q '  2026-09-05 | s3 | came back' "$tmp/arc.out" || fail "--arc dropped the recurrence after the landing"
grep -q 'drift/s\|other-arc' "$tmp/arc.out" && fail "--arc showed a key on another arc"
python3 "$rl" view --arc no-such-arc --root "$tmp" --log arc.md >/dev/null 2>&1 && fail "--arc accepted an arc no key carries"
python3 "$rl" view --arc Not_A_Slug --root "$tmp" --log arc.md >/dev/null 2>&1 && fail "--arc accepted a non-slug name"
cat > "$tmp/arc2.md" <<'EOF2'
## Entries

drift/t
  2026-09-01 | s1 | once.
drift/t
  ARC why-not-now — attached while live.
drift/t
  LANDED abc1234 — doc.md §x.
EOF2
python3 "$rl" compact --root "$tmp" --log arc2.md 2>/dev/null || fail "compact refused a log with ARC blocks"
grep -q '^  ARC why-not-now' "$tmp/arc2.md" || fail "compact dropped an ARC written before the key closed"
python3 "$rl" view --arc why-not-now --root "$tmp" --log arc2.md 2>/dev/null | grep -q '^drift/t  ×0  -  LANDED$' || fail "the compacted closed key left the arc: $(python3 "$rl" view --arc why-not-now --root "$tmp" --log arc2.md 2>/dev/null)"
cp "$tmp/arc2.md" "$tmp/arc2.once"; python3 "$rl" compact --root "$tmp" --log arc2.md 2>/dev/null
cmp -s "$tmp/arc2.md" "$tmp/arc2.once" || fail "compacting a canonical log with ARC changed it"
printf 'drift/u\n  ARC Not_A_Slug — bad name.\n' >> "$tmp/arc2.md"
python3 "$check" --root "$tmp" --paths arc2.md 2>/dev/null | grep -q 'an arc name is a slug' || fail "the check passed a non-slug arc name"
python3 "$rl" view --keys --root "$tmp" --log arc2.md 2>"$tmp/err" >/dev/null; grep -q 'an arc name is a slug' "$tmp/err" || fail "view did not warn on a non-slug arc name"
ok "ARC is transparent to state and count, outlives a closing status; --arc derives the trajectory by date entered; --arcs lists them"

# 11. Escaped: is a continuation the check accepts; one escaped occurrence ranks under
#     --reached and sorts after HELD; one before a landing does not
cat > "$tmp/esc.md" <<'EOF'
## Entries

drift/e1
  2026-10-01 | s1 | reached master.
    Escaped: the default branch — a revert commit
drift/e2
  2026-10-02 | s1 | plain single.
drift/e3
  2026-09-01 | s0 | escaped, then fixed.
    Escaped: a release — hotfix
drift/e3
  LANDED abc1234 — the fix.
drift/e4
  2026-10-03 | s1 | one.
drift/e4
  2026-10-04 | s2 | two.
EOF
python3 "$check" --root "$tmp" --paths esc.md >/dev/null 2>&1 || fail "an Escaped: continuation fails the retro-log check"
python3 "$rl" view --keys --reached --root "$tmp" --log esc.md 2>/dev/null > "$tmp/esc.out"
grep -q '^drift/e1  ×1  2026-10-01  escaped to the default branch$' "$tmp/esc.out" || fail "a single Escaped: occurrence did not rank or lacks its marker: $(cat "$tmp/esc.out")"
grep -q '^drift/e2' "$tmp/esc.out" && fail "a plain single occurrence ranked under --reached"
grep -q '^drift/e3' "$tmp/esc.out" && fail "an Escaped: before a landing ranked"
[ "$(grep -n '^drift/e1' "$tmp/esc.out" | cut -d: -f1)" -lt "$(grep -n '^drift/e4' "$tmp/esc.out" | cut -d: -f1)" ] || fail "an escaped key did not sort before a higher count"
ok "Escaped: is accepted; one escaped occurrence ranks under --reached and sorts first; one before a landing does not"

# 11b. --ripe: only an Escaped: or Gate-run: occurrence new since the mark makes a key or a
#      cluster ripe; a recurrence all caught, or in-work, is telemetry
R="$tmp/ripe"; mkdir -p "$R/docs"; touch "$R/docs/a.md" "$R/docs/b.md"
printf '{ "processDocs": ["docs"], "trigger": { "cluster": 3 } }\n' > "$R/threads.json"
git init -q -b main "$R"; r_() { git -C "$R" "$@"; }
mkdir -p "$R/.claude"; mv "$R/threads.json" "$R/.claude/"
cat > "$R/log.md" <<'EOF2'
## Entries

r/old-escape
  2026-10-01 | s0 | reached main before the mark.
    Escaped: the default branch — a revert
r/landed
  2026-10-01 | s0 | escaped, then fixed.
    Escaped: a release — hotfix
r/landed
  LANDED abc1234 — the fix.
EOF2
r_ add -A; r_ -c user.name=t -c user.email=t@t commit -q -m mark; r_ tag mark
cat >> "$R/log.md" <<'EOF2'
r/caught
  2026-10-10 | s1 | stopped by /slices:check. Placement: docs/a.md §X
    Caught: /slices:check — docs/a.md §X ("the rule")
r/caught
  2026-10-11 | s2 | stopped by /slices:check again. Placement: docs/a.md §X
    Caught: /slices:check — docs/a.md §X ("the rule")
r/in-work
  2026-10-10 | s1 | a red test while writing. Placement: docs/a.md §X
r/in-work
  2026-10-12 | s3 | again, the work itself. Placement: docs/a.md §X
r/old-escape
  2026-10-12 | s3 | caught this time.
    Caught: /pre-pr — docs/b.md §Y
r/escaped
  2026-10-13 | s4 | reached the user. Placement: docs/b.md §Y
    Escaped: the user — a wrong report
r/gate-run
  2026-10-13 | s4 | the check skipped its sweep. Placement: docs/b.md §Y
    Gate-run: /slices:check — dropped a finding
r/gate-run2
  2026-10-14 | s5 | three rounds after the first catch. Placement: docs/b.md §Y
    Gate-run: review — rounds after its first catch
EOF2
python3 "$check" --root "$tmp" --paths ripe/log.md >/dev/null 2>&1 || fail "a Gate-run: continuation fails the retro-log check"
python3 "$rl" view --keys --ripe --since mark --root "$R" --log log.md 2>/dev/null > "$R/k.out"
grep -q 'showing 3 of 7 keys (--ripe --since mark)' "$R/k.out" || fail "--ripe shows the wrong set: $(cat "$R/k.out")"
grep -q '^r/escaped  ×1  2026-10-13  escaped to the user$' "$R/k.out" || fail "one escaped occurrence since the mark is not ripe: $(cat "$R/k.out")"
grep -q '^r/gate-run  ×1  2026-10-13  gate-run at /slices:check$' "$R/k.out" || fail "one gate-run occurrence is not ripe or lacks its marker: $(cat "$R/k.out")"
grep -qE '^r/(caught|in-work|old-escape|landed)' "$R/k.out" && fail "a caught or in-work recurrence, or an escape before the mark or a landing, was ripe"
python3 "$rl" view --keys --reached --since mark --root "$R" --log log.md 2>/dev/null | grep -q '^r/gate-run  ' || fail "--reached did not rank a single Gate-run: occurrence"
python3 "$rl" view --placements --ripe --since mark --root "$R" --log log.md 2>/dev/null > "$R/p.out"
grep -q 'docs/a.md' "$R/p.out" && fail "--ripe counted caught or in-work occurrences in a cluster: $(cat "$R/p.out")"
grep -q $'^3\t3\t2026-10-13..2026-10-14\t3 new\tdoc\tdocs/b.md\tfires$' "$R/p.out" || fail "--ripe did not fire a cluster of escaped and gate-run keys: $(cat "$R/p.out")"
python3 "$rl" view --placements --since mark --root "$R" --log log.md 2>/dev/null | grep -q $'^1\t2\t.*\tdocs/a.md' || fail "without --ripe the cluster read dropped the in-work occurrences"
ok "--ripe: a recurrence all caught or in-work is not ripe; one escaped or gate-run occurrence since the mark is; clusters count only those"

# 11c. a gate stop in prose with no Caught:, Gate-run:, or Escaped: line warns, never
#      changes the exit; more than three collapse to a count, and --untagged lists them
cat > "$tmp/stop.md" <<'EOF2'
## Entries

s/prose
  2026-10-01 | s1 | the regex missed shapes. Stopped by
    /slices:check round 1. Cost: one round.
s/tagged
  2026-10-02 | s1 | caught by the pre-commit hook.
    Caught: the pre-commit hook — doc.md §X
s/negated
  2026-10-03 | s1 | not caught by the landed rule; stopped by the work itself.
s/maintainer
  2026-10-04 | s1 | caught only by the maintainer asking why.
EOF2
python3 "$rl" view --keys --root "$tmp" --log stop.md 2>"$tmp/stop.err" >/dev/null || fail "an untagged gate stop changed the view's exit"
grep -q '^retro-log: warning: s/prose 2026-10-01: a gate stop in prose' "$tmp/stop.err" || fail "a wrapped prose gate stop did not warn: $(cat "$tmp/stop.err")"
[ "$(grep -c 'gate stop' "$tmp/stop.err")" -eq 1 ] || fail "a tagged, negated, work-itself, or maintainer stop warned: $(cat "$tmp/stop.err")"
for i in 2 3 4; do printf 's/more%s\n  2026-10-1%s | s | caught by lens E.\n' "$i" "$i" >> "$tmp/stop.md"; done
python3 "$rl" view --keys --root "$tmp" --log stop.md 2>&1 >/dev/null | grep -q '^retro-log: warning: 4 occurrences name a gate stop in prose .*(--untagged lists them)$' || fail "more than three untagged stops did not collapse to a count"
[ "$(python3 "$rl" view --untagged --root "$tmp" --log stop.md | grep -c $'^2026-10-[01][0-9]\ts/')" -eq 4 ] || fail "--untagged did not list each untagged stop"
ok "a prose gate stop with no tag warns on view, by key up to three and by count past; --untagged lists them; tagged, negated, and non-gate stops do not"

# 11d. --untagged --since lists what a window added with no class line; In-work: classes one
#      without changing its rank, and a gate's stop with its rule absent is classed by it
U="$tmp/unclassed"; mkdir -p "$U"; git -C "$U" init -q; git -C "$U" config user.email t@t; git -C "$U" config user.name t
printf '## Entries\n\no/old\n  2026-09-01 | s | predates the class line.\n' > "$U/log.md"
git -C "$U" add log.md; git -C "$U" commit -qm base
cat >> "$U/log.md" <<'EOF2'
n/bare
  2026-10-01 | s | stopped by the maintainer, past the command.
    Cost: two days.
n/worked
  2026-10-02 | s | fixed in the same edit.
    In-work: the work itself
n/escaped
  2026-10-03 | s | reached main.
    Escaped: the default branch — a revert
n/gate
  2026-10-04 | s | stopped by the pre-commit hook.
    In-work: the pre-commit hook
EOF2
[ "$(python3 "$rl" view --untagged --since HEAD --root "$U" --log log.md)" = "$(printf '2026-10-01\tn/bare\tno class line')" ] || fail "--untagged --since REV did not list only the new occurrence with no class line: $(python3 "$rl" view --untagged --since HEAD --root "$U" --log log.md)"
python3 "$rl" view --untagged --since 2026-09-15 --root "$U" --log log.md | grep -q '^2026-10-01' || fail "--untagged --since DATE missed a new occurrence with no class line"
python3 "$rl" view --untagged --since 2026-09-15 --root "$U" --log log.md | grep -q 'o/old' && fail "--untagged --since DATE read an occurrence before the window"
python3 "$rl" view --untagged --root "$U" --log log.md | grep -q 'n/gate' && fail "In-work: naming a gate with its rule absent still warned"
printf 'n/worked\n  2026-10-05 | s | again.\n    In-work: the work itself\n' >> "$U/log.md"
python3 "$rl" view --keys --reached --root "$U" --log log.md 2>/dev/null | grep -q '^n/worked ' || fail "In-work: changed how a repeat ranks"
python3 "$rl" view --keys --ripe --root "$U" --log log.md 2>/dev/null | grep -q '^n/worked ' && fail "In-work: made a key ripe"
ok "--untagged --since lists new occurrences with no class line; In-work: classes one, ranks as untagged, is never ripe, and classes a rule-absent gate stop"

# 11e. two status lines under one key line: view warns and reads the first, compact refuses
#      and leaves the file, with or without a sentence end to cut at
for first in 'ruling one.' 'ruling one'; do
  printf '## Entries\n\nd/a\n  2026-10-01 | s | text\nd/a\n  ADJUDICATED 2026-10-02 — %s\n  HELD 2026-10-02 — proposal.\n' "$first" > "$tmp/fold.md"
  cp "$tmp/fold.md" "$tmp/fold.before"
  python3 "$rl" compact --root "$tmp" --log fold.md >/dev/null 2>"$tmp/fold.err"; rc=$?
  [ "$rc" -eq 2 ] || fail "compact did not refuse two status lines under one key line (rc $rc)"
  grep -q 'second status line under one key line' "$tmp/fold.err" || fail "compact's refusal did not name the second status line: $(cat "$tmp/fold.err")"
  cmp -s "$tmp/fold.md" "$tmp/fold.before" || fail "a refused compact changed the log"
  python3 "$rl" view --held --keys --root "$tmp" --log fold.md 2>&1 >/dev/null | grep -q 'second status line' || fail "view did not warn on two status lines under one key line"
done
ok "two status lines under one key line: view warns, compact refuses and writes nothing"

# 11f. compaction keeps a live key's status text whole and still reduces a closed key's
cat > "$tmp/whole.md" <<'EOF2'
## Entries

d/live
  2026-10-01 | s | text
d/live
  HELD 2026-10-02 — the proposal. The reason it was held.
d/closed
  2026-10-01 | s | text
d/closed
  LANDED abc1234 — where it landed. The narrative.
EOF2
python3 "$rl" compact --root "$tmp" --log whole.md 2>/dev/null || fail "compact refused a valid log"
grep -q 'HELD 2026-10-02 — the proposal. The reason it was held.$' "$tmp/whole.md" || fail "compact cut a live key's status"
grep -q 'LANDED abc1234 — where it landed.$' "$tmp/whole.md" || fail "compact stopped reducing a closed key's status"
ok "compact keeps a live key's status whole and reduces a closed key's"

# 12. --placements: live keys clustered by resolved placement file, command docs first; caught,
#     count-only, and pre-landing occurrences uncounted; --since narrows firing, never counting;
#     a weighed cluster fires on the bar's worth of keys after its newest weighing
P="$tmp/pl"; mkdir -p "$P/.claude/commands" "$P/docs" "$P/other"
touch "$P/.claude/commands/run.md" "$P/docs/rules.md" "$P/other/rules.md"
printf '{ "processDocs": ["docs", ".claude/commands"], "trigger": { "cluster": 3 } }\n' > "$P/.claude/threads.json"
cat > "$P/log.md" <<'EOF'
## Entries

a/one
  2026-10-01 | s1 | one. Placement: .claude/commands/run.md §Stop
a/two
  2026-10-02 | s2 | two.
    Placement: run.md §Stop — by basename
a/three
  2026-10-02 | s2 | caught.
    Caught: /pre-pr — run.md §Stop
    Placement: run.md §Stop
a/four
  2026-10-20 | s3 | four. Placement: run.md §Pause
a/five
  2026-10-03 | s2 | ruled. Placement: run.md §Stop
a/five
  ADJUDICATED 2026-10-04 — count-only at ×1: gate catch, rule present.
a/six
  2026-09-01 | s0 | landed. Placement: run.md §Stop
a/six
  LANDED abc1234 — run.md §Stop.
a/seven
  2026-09-01 | s0 | before. Placement: run.md §Stop
a/seven
  LANDED abc1235 — run.md §Stop.
a/seven
  2026-10-03 | s2 | after. Placement: rules.md §R
b/r1
  2026-09-05 | s1 | r1. Placement: rules.md §R
b/r2
  2026-09-06 | s1 | r2. Placement: docs/rules.md §R
b/r3
  2026-09-07 | s1 | r3. Placement: ./rules.md §R
c/x
  2026-09-08 | s1 | x. Placement: nowhere.md §Q
c/y
  2026-09-09 | s1 | no placement.
EOF
cp "$P/log.md" "$P/weighed.md"
cat >> "$P/weighed.md" <<'EOF'
b/r3
  ADJUDICATED 2026-10-05 — cluster rules.md weighed at 3: rule home by design, not cut.
a/two
  ADJUDICATED 2026-10-05 — cluster .claude/commands/run.md weighed at 3: read, not cut.
EOF
python3 "$rl" view --placements --root "$P" --log log.md 2>/dev/null > "$P/all.out"
head -1 "$P/all.out" | grep -q '^placements: 9 live keys counted · 1 occurrences unplaced · 3 files · 2 at or above cluster 3, 2 firing: a key new (no since: every one), or 3 after its weighing$' || fail "--placements summary: $(head -1 "$P/all.out")"
grep -q $'^3\t3\t2026-10-01..2026-10-20\t3 new\tcommand\t.claude/commands/run.md\tfires$' "$P/all.out" || fail "run.md cluster (basename resolved; caught, count-only, landed excluded): $(cat "$P/all.out")"
grep -q $'^4\t4\t2026-09-05..2026-10-03\t4 new\tdoc\tdocs/rules.md\tfires$' "$P/all.out" || fail "rules.md cluster (processDocs preferred over other/rules.md; post-LANDED occurrence counted): $(cat "$P/all.out")"
grep -q $'^1\t1\t2026-09-08\t1 new\tdoc\tnowhere.md (not in this repo)$' "$P/all.out" || fail "an unresolvable placement is not marked: $(cat "$P/all.out")"
[ "$(grep -n 'run.md' "$P/all.out" | head -1 | cut -d: -f1)" -lt "$(grep -n 'docs/rules.md' "$P/all.out" | head -1 | cut -d: -f1)" ] || fail "a command cluster did not rank before a larger doc cluster"
grep -qE 'a/(three|five|six)' "$P/all.out" && fail "a caught, count-only, or landed key was listed in a cluster"
python3 "$rl" view --placements --since 2026-10-10 --root "$P" --log log.md 2>/dev/null > "$P/since.out"
grep -q $'\t1 new\tcommand\t.claude/commands/run.md\tfires$' "$P/since.out" || fail "--since did not fire on a cluster with a new key: $(cat "$P/since.out")"
grep -q $'^\t\ta/four  ×1  2026-10-20  new$' "$P/since.out" || fail "the new key is not marked: $(cat "$P/since.out")"
grep -q $'^4\t4\t.*\t0 new\tdoc\tdocs/rules.md$' "$P/since.out" || fail "--since fired on a cluster with nothing new, or changed its count: $(cat "$P/since.out")"
python3 "$rl" view --placements --reached --root "$P" --log log.md >/dev/null 2>&1; [ $? -eq 2 ] || fail "--placements accepted a narrowing filter"
python3 "$rl" view --placements --since 2026-09-01 --root "$P" --log weighed.md 2>/dev/null > "$P/w.out"
grep -q $'\tcommand\t.claude/commands/run.md\tweighed at 3$' "$P/w.out" || fail "a cluster weighed at its size fired on new keys: $(cat "$P/w.out")"
grep -q $'^4\t.*\tdocs/rules.md\tweighed at 3$' "$P/w.out" || fail "a cluster one key past its weighing fired below the bar: $(cat "$P/w.out")"
printf 'b/r4\n  2026-10-06 | s4 | r4. Placement: rules.md §R\nb/r5\n  2026-10-06 | s4 | r5. Placement: rules.md §R\n' >> "$P/weighed.md"
python3 "$rl" view --placements --root "$P" --log weighed.md 2>/dev/null | grep -q $'^6\t.*\tdocs/rules.md\tweighed at 3$' || fail "a cluster two keys past its weighing fired below the bar"
printf 'b/r6\n  2026-10-07 | s5 | r6. Placement: rules.md §R\n' >> "$P/weighed.md"
python3 "$rl" view --placements --root "$P" --log weighed.md 2>/dev/null | grep -q $'^7\t.*\tdocs/rules.md\tweighed at 3\tfires$' || fail "a cluster with the bar's worth of keys after its weighing did not fire"
# a weighing outlives the key it sits on; the newest holds, so keys closing after it never raise the bar
cat > "$P/shrunk.md" <<'EOF'
## Entries

d/w1
  2026-09-01 | s1 | w1. Placement: rules.md §R
d/w1
  ADJUDICATED 2026-09-10 — cluster rules.md weighed at 9: home by design.
d/w1
  LANDED abc1236 — rules.md §R.
d/w2
  2026-09-02 | s1 | w2. Placement: rules.md §R
d/w3
  2026-09-03 | s1 | w3. Placement: rules.md §R
d/w4
  2026-09-11 | s2 | w4. Placement: rules.md §R
d/w5
  2026-09-11 | s2 | w5. Placement: rules.md §R
EOF
python3 "$rl" compact --root "$P" --log shrunk.md 2>/dev/null || fail "compact refused a log with a weighing on a closed key"
grep -q '^  ADJUDICATED 2026-09-10 — cluster rules.md weighed at 9' "$P/shrunk.md" || fail "compact dropped a weighing written before its key closed"
python3 "$rl" view --placements --root "$P" --log shrunk.md 2>/dev/null | grep -q $'^4\t.*\tdocs/rules.md\tweighed at 9$' || fail "a compacted closed key's weighing was lost, or two keys after it fired"
printf 'd/w2\n  ADJUDICATED 2026-09-12 — cluster rules.md weighed at 4: re-weighed after w1 landed.\nd/w6\n  2026-09-12 | s3 | w6. Placement: rules.md §R\n' >> "$P/shrunk.md"
python3 "$rl" view --placements --root "$P" --log shrunk.md 2>/dev/null | grep -q $'^5\t.*\tdocs/rules.md\tweighed at 4$' || fail "the newest weighing did not hold over a larger older one, or a same-day key counted after it"
printf 'd/w7\n  2026-09-13 | s4 | w7. Placement: rules.md §R\nd/w8\n  2026-09-13 | s4 | w8. Placement: rules.md §R\nd/w9\n  2026-09-14 | s5 | w9. Placement: rules.md §R\n' >> "$P/shrunk.md"
python3 "$rl" view --placements --root "$P" --log shrunk.md 2>/dev/null | grep -q $'^8\t.*\tdocs/rules.md\tweighed at 4\tfires$' || fail "three keys after the newest weighing did not fire"
python3 "$rl" view --occurrences --key a/seven --key b/r3 --root "$P" --log weighed.md 2>/dev/null > "$P/occ.out"
grep -q '^a/seven  ×2  2026-09-01..2026-10-03$' "$P/occ.out" || fail "--occurrences key line carries a marker or a wrong count: $(cat "$P/occ.out")"
grep -q 'came\|before\. Placement' "$P/occ.out" || fail "--occurrences dropped an occurrence: $(cat "$P/occ.out")"
grep -qE 'LANDED|ADJUDICATED|weighed' "$P/occ.out" && fail "--occurrences printed a review's line: $(cat "$P/occ.out")"
python3 "$rl" view --occurrences --root "$P" --log weighed.md >/dev/null 2>&1; [ $? -eq 2 ] || fail "--occurrences ran without --key"
python3 "$rl" view --occurrences --key a/one --live --root "$P" --log weighed.md >/dev/null 2>&1; [ $? -eq 2 ] || fail "--occurrences accepted another filter"
ok "--placements: clusters by resolved file, command docs first, gate-caught/count-only/landed uncounted; --since narrows firing only; a weighed cluster fires again only the bar past its size; --occurrences prints no review line"

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

# --arc: the landings of a trajectory are commits carrying `Arc: <slug>`, joined by date
printf 'rule 4\n' >> "$M/CLAUDE.md"; m add -A; m commit -q -m "docs(process/claude): the trailer form pinned" --trailer "Arc: why-not-now"
printf 'rule 5\n' >> "$M/CLAUDE.md"; m add -A; m commit -q -m "docs(process/claude): gates re-formed" --trailer "Arc: why-not-now" --trailer "Process-Review: 2026-09-21"
printf 'rule 6\n' >> "$M/CLAUDE.md"; m add -A; m commit -q -m "docs(process/claude): another arc" --trailer "Arc: other-arc"
m tag -f process-review-mark HEAD~3 >/dev/null 2>&1
python3 "$ms" list --arc why-not-now --root "$M" > "$M/arc.out" 2>"$M/err" || fail "marker-stream --arc failed: $(cat "$M/err")"
grep -q '^2 markers since all of HEAD on arc why-not-now: 1 organic · 1 review · 0 bookkeeping$' "$M/arc.out" || fail "--arc summary wrong: $(head -1 "$M/arc.out")"
grep -q '^organic	[0-9a-f]*	20[0-9-]*	docs(process/claude): the trailer form pinned$' "$M/arc.out" || fail "--arc row lacks its date or the commit: $(cat "$M/arc.out")"
grep -q 'other arc' "$M/arc.out" && fail "--arc showed a commit on another arc"
python3 "$ms" count --arc why-not-now --since process-review-mark --root "$M" 2>/dev/null | grep -q '^2 markers since process-review-mark' || fail "--arc with --since did not narrow to the range"
python3 "$ms" count --arc Not_A_Slug --root "$M" >/dev/null 2>&1 && fail "--arc accepted a non-slug"
ok "marker-stream --arc: commits carrying the Arc trailer, whole history by default, dated rows"

# ---- retro-log.py view --chain: a key's occurrences (capture time by blame) and the organic
# markers on its placement since the first, in time order; then the window's organic markers
C="$tmp/chain"; mkdir -p "$C/.claude" "$C/docs"
git init -q -b main "$C"; c_() { git -C "$C" "$@"; }
c_ config user.email t@t; c_ config user.name t
at() { GIT_AUTHOR_DATE="$1" GIT_COMMITTER_DATE="$1" git -C "$C" commit -q -m "$2"; }
printf '{ "markerPattern": "^docs(process", "retroLogPath": ".claude/log.md" }\n' > "$C/.claude/threads.json"
printf '# a\n' > "$C/docs/a.md"; printf '# o\n' > "$C/docs/other.md"; printf '## Entries\n' > "$C/.claude/log.md"
c_ add -A; at "2026-09-01T09:00:00+00:00" base
printf 'x\n' >> "$C/docs/a.md"; c_ add -A; at "2026-09-02T08:00:00+00:00" "docs(process/a): before any capture, the same day"
c_ tag process-review-mark
printf 'k/a\n  2026-09-02 | s1 | first.\n    Placement: a.md §x\n' >> "$C/.claude/log.md"; c_ add -A; at "2026-09-02T09:00:00+00:00" "capture a"
printf 'y\n' >> "$C/docs/a.md"; c_ add -A; at "2026-09-03T09:00:00+00:00" "docs(process/a): the patch"
printf 'k/a\n  2026-09-05 | s2 | again.\n' >> "$C/.claude/log.md"; c_ add -A; at "2026-09-05T09:00:00+00:00" "capture a again"
printf '# b\n' > "$C/docs/b.md"; c_ add -A; at "2026-09-05T10:00:00+00:00" "docs(process/b): before k/b's first capture"
printf 'k/b\n  2026-09-06 | p1 | once.\n    Placement: docs/b.md §y\n' >> "$C/.claude/log.md"; c_ add -A; at "2026-09-06T09:00:00+00:00" "capture b"
printf 'k/b\n  2026-09-06 | p2 | twice, a parallel session.\n' >> "$C/.claude/log.md"; c_ add -A; at "2026-09-06T15:00:00+00:00" "capture b again"
printf 'z\n' >> "$C/docs/other.md"; c_ add -A; at "2026-09-07T09:00:00+00:00" "docs(process/other): a patch no key is placed at"
python3 "$rl" view --chain --recurred --root "$C" > "$C/out" 2>"$C/err" || fail "view --chain failed: $(cat "$C/err")"
sed -n '/^k\/a /,/^$/p' "$C/out" | grep '^  [0-9]' | awk '{print $3}' | tr '\n' ' ' | grep -qx 'occurrence touched occurrence ' || fail "k/a's chain is not in time order, or reached before its first occurrence: $(cat "$C/out")"
grep -q "^  2026-09-02 09:00  occurrence  $(c_ log -1 --format=%h --grep='^capture a$')  s1\$" "$C/out" || fail "an occurrence lacks its capture time and commit: $(cat "$C/out")"
grep -q '^  chain: 2 occurrences in 2 bursts · occurred again after [0-9a-f]* touched it$' "$C/out" || fail "k/a's chain read wrong: $(grep chain: "$C/out")"
grep -q '^  chain: 2 occurrences in 1 burst · placement untouched since the first$' "$C/out" || fail "k/b's same-day pair did not read as one burst: $(grep chain: "$C/out")"
grep -q '^## Organic markers since process-review-mark: 3 .* 2 touch no live key.s placement$' "$C/out" || fail "the window's markers miscounted: $(grep '^##' "$C/out")"
grep -q '^0	0	2026-09-07 09:00  [0-9a-f]*  docs(process/other): a patch no key is placed at$' "$C/out" || fail "the unkeyed patch was not read as touching no placement: $(cat "$C/out")"
grep -q '^1	1	.*the patch$' "$C/out" || fail "the patch was not joined to k/a's chain: $(cat "$C/out")"
printf 'k/a\n  2026-09-08 | s3 | uncommitted.\n' >> "$C/.claude/log.md"
python3 "$rl" view --chain --key k/a --root "$C" 2>/dev/null | grep -q '^  2026-09-08 --:--  occurrence  uncommitted  s3$' || fail "an uncommitted occurrence was not dated by its line alone"
python3 "$rl" view --chain --key k/a --root "$C" 2>/dev/null | grep -q '^  chain: 3 occurrences in 3 bursts · occurred again after' || fail "the uncommitted occurrence did not join the chain"
# one clock: a patch authored before a capture and committed after it orders by its author time
printf 'w\n' >> "$C/docs/a.md"; c_ add -A
GIT_AUTHOR_DATE="2026-09-09T08:00:00+00:00" GIT_COMMITTER_DATE="2026-09-09T12:00:00+00:00" git -C "$C" commit -q -m "docs(process/a): written early, landed late"
printf 'k/a\n  2026-09-09 | s4 | between.\n' >> "$C/.claude/log.md"; c_ add -A; GIT_AUTHOR_DATE="2026-09-09T10:00:00+00:00" GIT_COMMITTER_DATE="2026-09-09T12:00:00+00:00" git -C "$C" commit -q -m "capture a, between"
python3 "$rl" view --chain --key k/a --root "$C" > "$C/out2" 2>&1
grep -E '^  [0-9].*(written early|  s4$)' "$C/out2" | awk '{print $3}' | tr '\n' ' ' | grep -qx 'touched occurrence ' || fail "a patch was ordered on another clock than the capture: $(cat "$C/out2")"
head -1 "$C/out2" | grep -q '^chain: author times on both kinds of line' || fail "the chain does not name its clock"
# a marker touching more than 30 files is bracketed as broad, with its file count and placement churn
for i in $(seq 1 31); do printf '%s\n' "$i" > "$C/docs/f$i.md"; done; printf 'relink\n' >> "$C/docs/a.md"; c_ add -A; at "2026-09-10T09:00:00+00:00" "docs(process/links): repoint every link"
python3 "$rl" view --chain --key k/a --root "$C" > "$C/out3" 2>&1
grep -q '^  2026-09-10 09:00  broad       [0-9a-f]*  docs(process/links): repoint every link  (docs/a.md +1 -0 · [0-9]* files)$' "$C/out3" || fail "a broad marker was not bracketed with its churn and file count: $(cat "$C/out3")"
grep -q '^  chain: .*broad: [0-9a-f]*$' "$C/out3" && ! grep -q 'touched after the last' "$C/out3" || fail "a broad marker was read as a touch after the last: $(grep chain: "$C/out3")"
# --prs: an open PR touching the placement is in flight; gh failing is narrated, never fatal
mkdir -p "$C/bin"; printf '#!/bin/sh\necho '"'"'[{"number": 7, "title": "fix a", "files": [{"path": "docs/a.md"}]}]'"'"'\n' > "$C/bin/gh"; chmod +x "$C/bin/gh"
PATH="$C/bin:$PATH" python3 "$rl" view --chain --prs --key k/a --root "$C" > "$C/out4" 2>&1 || fail "--prs failed: $(cat "$C/out4")"
grep -q '^  open PR #7  fix a  (docs/a.md)$' "$C/out4" && grep -q '^  chain: .*in flight: #7$' "$C/out4" || fail "an open PR on the placement was not named in flight: $(cat "$C/out4")"
printf '#!/bin/sh\necho "no remote" >&2; exit 1\n' > "$C/bin/gh"
PATH="$C/bin:$PATH" python3 "$rl" view --chain --prs --key k/a --root "$C" 2>&1 | head -1 | grep -q 'open PRs not read (no remote)' || fail "a failing gh was not narrated"
# --since REV: keys with a detail line the log at REV did not hold — to the commit, not the
# day; a re-key and a compaction move nothing into it
c_ add -A; at "2026-09-11T09:00:00+00:00" "settle"; c_ tag mid
printf 'k/c\n  2026-09-06 | z | the same day as k/b, written after the mark.\n' >> "$C/.claude/log.md"; c_ add -A; at "2026-09-11T10:00:00+00:00" "capture c"
sed -i.bak 's#^k/a$#k/renamed#' "$C/.claude/log.md" && rm -f "$C/.claude/log.md.bak"
python3 "$rl" compact --root "$C" 2>/dev/null
python3 "$rl" view --keys --since mid --root "$C" > "$C/s1" 2>&1 || fail "--since REV failed: $(cat "$C/s1")"
grep -q '^showing 1 of 3 keys (--since mid)$' "$C/s1" && grep -q '^k/c ' "$C/s1" || fail "--since REV did not read only what the mark lacked (a re-key and a compaction count as new?): $(cat "$C/s1")"
python3 "$rl" view --keys --since 2026-09-06 --root "$C" 2>/dev/null | grep -q '^k/b ' || fail "--since DATE stopped reading by date"
python3 "$rl" view --keys --since no-such-rev --root "$C" >/dev/null 2>"$C/err" && fail "--since took a rev that does not exist"
grep -q 'takes YYYY-MM-DD or a commit' "$C/err" || fail "a bad --since was not named: $(cat "$C/err")"
ok "view --chain: occurrences and the placement's organic markers on one clock, in order; a same-day pair one burst; a broad marker bracketed; an open PR in flight; the window's unkeyed patch named; an uncommitted line dated by its own; --since REV to the commit, a re-key and a compaction not new"

# ---- retro-log.py view --outside --since REV: a key a retro, slice, or release closed or filed
# in the window, written by no review commit — the self-landed patch the review must judge
O="$tmp/outside"; mkdir -p "$O/.claude" "$O/docs"
git init -q -b main "$O"; o_() { git -C "$O" "$@"; }
o_ config user.email t@t; o_ config user.name t
oat() { d="$1"; shift; GIT_AUTHOR_DATE="$d" GIT_COMMITTER_DATE="$d" git -C "$O" commit -q "$@"; }
printf '{ "markerPattern": "^docs(process", "retroLogPath": ".claude/log.md" }\n' > "$O/.claude/threads.json"
printf '# a\n' > "$O/docs/a.md"
printf '## Entries\n\no/old\n  2026-09-01 | s0 | before the mark.\no/old\n  LANDED 1111111 — docs/a.md §old.\n' > "$O/.claude/log.md"
o_ add -A; oat "2026-09-01T09:00:00+00:00" -m base; o_ tag process-review-mark
printf 'o/self\n  2026-09-02 | s1 | hit it.\n    Placement: docs/a.md §x\n' >> "$O/.claude/log.md"; o_ add -A; oat "2026-09-02T09:00:00+00:00" -m "capture self"
printf 'cap\n' >> "$O/docs/a.md"; o_ add -A; oat "2026-09-02T10:00:00+00:00" -m "docs(process/a): a cap on the rounds"
printf 'o/self\n  LANDED %s — docs/a.md §x: a cap\n' "$(o_ rev-parse --short HEAD)" >> "$O/.claude/log.md"; o_ add -A; oat "2026-09-02T11:00:00+00:00" -m "docs(process/retro): LANDED — self"
printf 'o/reviewed\n  2026-09-03 | s2 | ruled.\no/reviewed\n  LANDED 2222222 — docs/a.md §y.\n' >> "$O/.claude/log.md"; o_ add -A
oat "2026-09-03T09:00:00+00:00" -m "docs(process/retro): review" -m "Process-Review: 2026-09-03"
printf 'o/filed\n  2026-09-04 | s3 | carried.\no/filed\n  FILED Plans/inbox/x.md — the stub.\n' >> "$O/.claude/log.md"; o_ add -A; oat "2026-09-04T09:00:00+00:00" -m "slice files it"
printf 'o/live\n  2026-09-05 | s4 | open.\n' >> "$O/.claude/log.md"; o_ add -A; oat "2026-09-05T09:00:00+00:00" -m "capture live"
printf 'o/wip\n  2026-09-06 | s5 | landed, not yet committed.\no/wip\n  RETIRED 2026-09-06 — moot.\n' >> "$O/.claude/log.md"
python3 "$rl" view --keys --reached --since process-review-mark --root "$O" 2>/dev/null | grep -q '^o/self ' && fail "--reached now shows a closed key: the fixture no longer tests the gap"
python3 "$rl" view --keys --outside --since process-review-mark --root "$O" > "$O/k" 2>&1 || fail "--outside failed: $(cat "$O/k")"
grep -q "^o/self  ×1  LANDED .*  closed outside a review by $(o_ log -1 --format=%h --grep='LANDED — self')\$" "$O/k" || fail "a self-landed key was not shown with the commit that closed it: $(cat "$O/k")"
grep -q '^o/filed  ×1  2026-09-04  FILED  closed outside a review by ' "$O/k" || fail "a key a slice filed was not shown: $(cat "$O/k")"
grep -q '^o/wip  ×1  RETIRED .*closed outside a review by uncommitted$' "$O/k" || fail "an uncommitted closing was not shown: $(cat "$O/k")"
grep -q '^o/reviewed \|^o/old \|^o/live ' "$O/k" && fail "--outside showed a review's closing, one before the mark, or a live key: $(cat "$O/k")"
python3 "$rl" view --chain --outside --since process-review-mark --key o/self --root "$O" > "$O/c" 2>&1 || fail "--chain --outside failed: $(cat "$O/c")"
grep -q '^  chain: 1 occurrence in 1 burst · placement touched after the last: ' "$O/c" || fail "the self-landed key's chain did not order its patch: $(cat "$O/c")"
python3 "$rl" view --outside --root "$O" >/dev/null 2>&1 && fail "--outside ran without --since REV"
python3 "$rl" view --outside --reached --since process-review-mark --root "$O" >/dev/null 2>&1 && fail "--outside composed with --reached"
# an occurrence and its patch in one commit: answered, not recurred
printf 'tie\n' >> "$O/docs/a.md"; printf 'o/tie\n  2026-09-07 | s6 | fixed in the same commit.\n    Placement: docs/a.md §t\no/tie\n  LANDED 3333333 — docs/a.md §t.\n' >> "$O/.claude/log.md"
o_ add -A; oat "2026-09-07T09:00:00+00:00" -m "docs(process/a): the fix and its capture"
python3 "$rl" view --chain --outside --since process-review-mark --key o/tie --root "$O" > "$O/t" 2>&1
grep -q '^  chain: 1 occurrence in 1 burst · placement touched after the last: ' "$O/t" || fail "an occurrence in its patch's own commit read as a recurrence: $(cat "$O/t")"
# a closing sha with no marker on the placement is named as the patch to judge
printf 'b\n' > "$O/docs/b.md"; o_ add -A; oat "2026-09-08T09:00:00+00:00" -m "docs(process/b): a fix in another file"
printf 'o/elsewhere\n  2026-09-08 | s7 | no placement.\no/elsewhere\n  LANDED %s — docs/b.md.\n' "$(o_ rev-parse --short HEAD)" >> "$O/.claude/log.md"; o_ add -A; oat "2026-09-08T10:00:00+00:00" -m "retro lands it"
python3 "$rl" view --chain --outside --since process-review-mark --key o/elsewhere --root "$O" 2>&1 | grep -q "^  chain: .*closed citing $(o_ rev-parse --short HEAD^), not on the placement: judge that patch\$" || fail "a closing sha off the placement was not named"
# the footer reads REV, not the tag, once the mark has moved
base="$(o_ rev-parse process-review-mark)"; o_ tag -f process-review-mark HEAD >/dev/null
python3 "$rl" view --chain --outside --since "$base" --root "$O" 2>&1 | grep -q "^## Organic markers since $base: 3 " || fail "the footer did not read --since REV: $(python3 "$rl" view --chain --outside --since "$base" --root "$O" 2>&1 | grep '^##')"
# a key reopened by a ruling after compaction dropped its occurrences still ranks
printf '## Entries\n\nr/open\n  LANDED abc1234 — x.md.\nr/open\n  REOPENED 2026-09-09 — patched in part by abc1234; open: the driver.\n' > "$tmp/reopen.md"
python3 "$rl" view --keys --reached --root "$tmp" --log reopen.md 2>/dev/null | grep -q '^r/open  ×0  -  REOPENED$' || fail "a REOPENED key at ×0 did not rank: $(python3 "$rl" view --keys --reached --root "$tmp" --log reopen.md 2>&1)"
ok "view --outside: a key closed or filed in the window by a retro, a slice, or an uncommitted line is shown with its closer and its chain; a review's closing, one before the mark, and a live key are not; a same-commit patch is not a recurrence; a closing sha off the placement is named; the footer reads REV; a REOPENED key ranks at ×0"

# ---- scripts/risk-review.py: the risk registry against the window's escapes
rr="$here/scripts/risk-review.py"
K="$tmp/risk"; mkdir -p "$K/.claude" "$K/Plans/done"
git init -q -b main "$K"; k_() { git -C "$K" "$@"; }; k_ config user.email t@t; k_ config user.name t
printf '{ "plansDir": "Plans", "riskRegistry": ".claude/risk.json" }\n' > "$K/.claude/slices.json"
printf '{ "markTag": "mark" }\n' > "$K/.claude/threads.json"
cat > "$K/.claude/risk.json" <<'JSON'
{ "kinds": {}, "classes": [
  { "id": "state-machine", "status": "active", "signals": {}, "check": { "at": "plan", "text": "t" } },
  { "id": "copy", "status": "active", "signals": {}, "check": { "at": "pre-pr", "text": "t" } },
  { "id": "sync", "status": "predicted", "signals": {}, "check": { "at": "plan", "text": "t" } } ] }
JSON
printf '# old\n\n## Verification ledger\n\n- profiled at 0000000, 2026-09-01, slices 0.12.0 — classes: copy\n- escaped at 0000000, 2026-09-01 — found by pre-pr: before the window — at src/x.swift; class: state-machine\n' > "$K/Plans/done/old.md"
k_ add -A; k_ commit -q -m base; k_ tag mark
printf 'x\n' > "$K/f"; k_ add -A; k_ commit -q -m work; w="$(k_ rev-parse --short HEAD)"
cat > "$K/Plans/a.md" <<PLAN
# a

## Verification ledger

- profiled at $w, 2026-10-30, slices 0.12.0 — classes: state-machine; suggested: copy
  - state-machine — path: src/policy/Pause.swift
  - copy — symbol: headline
- gap-checked at $w, 2026-10-30, slices 0.12.0 — 3 defects (addressed: 3), 0 questions (open: 0), class: state-machine
- gap-checked at $w, 2026-10-30, slices 0.12.0 — 0 defects (addressed: 0), 0 questions (open: 0), class: state-machine
- escaped at $w, 2026-10-30 — found by walkthrough: a pause never resumed — at src/policy/Pause.swift; class: state-machine
- escaped at $w, 2026-10-30 — found by pre-pr: rounding off by one — at src/math/Dose.swift; class: none
PLAN
cat > "$K/Plans/b.md" <<PLAN
# b

## Verification ledger

- profiled at $w, 2026-10-30, slices 0.12.0 — classes: state-machine; dismissed: copy
  - state-machine — symbol: pauses
  - state-machine — confirmed: the toggle pauses a schedule
  - copy — symbol: banner
  - copy — dismissed: ordinary prose
PLAN
k_ add -A; k_ commit -q -m plan
printf 'y\n' > "$K/g"; k_ add -A; k_ commit -q -m "fix: dose rounding" -m "Escaped-class: none — found by after merge: dose rounds down — at src/math/Solver.swift"
printf 'z\n' > "$K/h"; k_ add -A; k_ commit -q -m "fix: odd" -m "Escaped-class: ghost — found by maintainer: x — at src/y.swift"
python3 "$rr" --root "$K" > "$K/out" 2>&1 || fail "risk-review failed: $(cat "$K/out")"
head -1 "$K/out" | grep -q '^risk: .claude/risk.json · mark..HEAD · 2 plans profiled · 2 class rounds · 4 escapes (2 from trailers)$' || fail "summary wrong: $(head -1 "$K/out")"
grep -q $'^state-machine\tactive\tplan\t2 plans (path 1, kind 0, confirmed 1, symbol 0; suggested 0, dismissed 0)\t2 rounds (1 empty)\t1 escapes$' "$K/out" || fail "a class's entries, rounds, or escapes miscounted: $(cat "$K/out")"
grep -q $'^copy\tactive\tpre-pr\t0 plans (path 0, kind 0, confirmed 0, symbol 0; suggested 1, dismissed 1)\t0 rounds (0 empty)\t0 escapes\tdormant$' "$K/out" || fail "a class only suggested or dismissed was counted as entered, or not dormant: $(cat "$K/out")"
grep -q $'^sync\tpredicted\tplan\t0 plans (.*)\t0 rounds (0 empty)\t0 escapes\tdormant$' "$K/out" || fail "a predicted class with no plan did not read dormant"
grep -q $'^2\tsrc/math$' "$K/out" || fail "unclassified escapes from a plan and a trailer were not grouped by area: $(cat "$K/out")"
grep -q $'^ghost\tmaintainer: x' "$K/out" || fail "an unknown class was not listed apart"
mv "$K/.claude/slices.json" "$K/.claude/off.json"; python3 "$rr" --root "$K" >/dev/null 2>&1; [ $? -eq 3 ] || fail "no registry did not exit 3"
ok "risk-review: escapes from plan lines and trailers, class rounds and empty ones, entries by path/kind/confirmed apart from suggested/dismissed; unclassified by area; dormant; an unknown class apart"
# risk-review on a squash-merge repo: a ledger line counts by its arrival, not its cited sha; an
# Escaped-class: line counts from a squash body that git parses no trailers from; a plan that
# moves directory brings no line in; the same escape in a branch commit and its merge is one
Q="$tmp/squash"; mkdir -p "$Q/.claude" "$Q/Plans/active" "$Q/Plans/completed"
git init -q -b master "$Q"; q_() { git -C "$Q" "$@"; }; q_ config user.email t@t; q_ config user.name t
cp "$K/.claude/risk.json" "$Q/.claude/risk.json"
printf '{ "plansDir": "Plans", "riskRegistry": ".claude/risk.json" }\n' > "$Q/.claude/slices.json"
printf '# old\n\n## Verification ledger\n\n- escaped at 1111111, 2026-09-01 — found by pre-pr: held at the mark — at src/old.swift; class: copy\n' > "$Q/Plans/active/old.md"
q_ add -A; q_ commit -q -m base; q_ tag process-review-mark
q_ checkout -q -b slice
printf 'w\n' > "$Q/w"; q_ add -A; q_ commit -q -m "feat: work"; pre="$(q_ rev-parse --short HEAD)"
printf '# p\n\n## Verification ledger\n\n- escaped at %s, 2026-10-30 — found by pre-pr: pause never resumes — at src/policy/X.swift; class: state-machine\n' "$pre" > "$Q/Plans/active/p.md"
printf 'f\n' > "$Q/f"; q_ add -A; q_ commit -q -m "fix: resume" -m "Escaped-class: none — found by walkthrough: wrong copy — at src/ui/X.swift"
q_ checkout -q master
msg="$(q_ log --reverse --format='* %B' master..slice)"
q_ merge -q --squash slice >/dev/null 2>&1; q_ commit -q -m "slice (#1)" -m "$msg" -m "Co-authored-by: a <a@b>"
[ -z "$(q_ log -1 --format='%(trailers:key=Escaped-class,valueonly)')" ] || fail "fixture: the squash body parsed a trailer, so it does not test the loss"
q_ branch -q -D slice; q_ merge-base --is-ancestor "$pre" master 2>/dev/null && fail "fixture: the cited branch sha is still on master"
q_ mv Plans/active/old.md Plans/completed/old.md; q_ commit -q -m "closeout: move"
python3 "$rr" --root "$Q" > "$Q/out" 2>&1 || fail "risk-review failed on a squash repo: $(cat "$Q/out")"
head -1 "$Q/out" | grep -q ' · 2 escapes (1 from trailers)$' || fail "a squash merge lost an escape, or a moved plan's held line re-entered: $(cat "$Q/out")"
grep -q $'^state-machine\t.*\t1 escapes' "$Q/out" && grep -q $'^1\tsrc/ui$' "$Q/out" || fail "the squash escapes were not attributed: $(cat "$Q/out")"
q_ checkout -q -b slice2; printf 'g\n' > "$Q/g"; q_ add -A; q_ commit -q -m "fix: again" -m "Escaped-class: none — found by review: once — at src/ui/Y.swift"
q_ checkout -q master; q_ merge -q --no-ff --log slice2 -m "merge slice2" >/dev/null 2>&1
python3 "$rr" --root "$Q" 2>&1 | head -1 | grep -q ' · 3 escapes (2 from trailers)$' || fail "an escape in a branch commit and its merge message was counted twice: $(python3 "$rr" --root "$Q" 2>&1 | head -1)"
ok "risk-review on squash merges: a ledger line counts by its arrival, an Escaped-class: line from a squash body; a moved plan adds nothing; one escape in a commit and its merge counts once"

# ---- scripts/core-diff.py: each core doc's window as churn — words at the mark and at
# the head, words added and removed, commits — so a core doc that grows unread is seen.
cd_="$here/scripts/core-diff.py"
CD="$tmp/cd"; mkdir -p "$CD/.claude" "$CD/docs"
git init -q -b main "$CD"; c() { git -C "$CD" "$@"; }
c config user.email t@t; c config user.name t
printf '{ "markTag": "process-review-mark", "invariantDocs": ["CLAUDE.md", "docs/core.md"], "windowOnlyDocs": ["docs/new.md"] }\n' > "$CD/.claude/threads.json"
printf 'one two three\n' > "$CD/CLAUDE.md"; printf 'rule a\nrule b\n' > "$CD/docs/core.md"
c add -A; c commit -q -m "base"; c tag process-review-mark
printf 'rule a\nrule b\nand a worked case restating rule a in seven more words\n' > "$CD/docs/core.md"
c add -A; c commit -q -m "feat: a squash that grew the core doc"
printf 'rule a\nand a worked case restating rule a in seven more words\n' > "$CD/docs/core.md"
printf 'fresh doc\n' > "$CD/docs/new.md"
c add -A; c commit -q -m "docs: drop rule b, add a doc"
python3 "$cd_" --root "$CD" > "$CD/sum.out" 2>"$CD/err" || fail "core-diff summary failed: $(cat "$CD/err")"
grep -q '^core-diff process-review-mark (20[0-9-]*, [0-9a-f]*)\.\.HEAD: 3 docs (2 whole, 1 window), 2 with a window$' "$CD/sum.out" || fail "header wrong: $(head -1 "$CD/sum.out")"
grep -qx 'CLAUDE.md	3	3	+0 -0	0	whole' "$CD/sum.out" || fail "an untouched doc did not read zero: $(cat "$CD/sum.out")"
grep -qx 'docs/core.md	4	13	+11 -2	2	whole' "$CD/sum.out" || fail "the grown doc's words were not counted: $(cat "$CD/sum.out")"
grep -qx 'docs/new.md	-	2	+2 -0	1	window' "$CD/sum.out" || fail "a window-only doc absent at the mark did not read - and window: $(cat "$CD/sum.out")"
python3 "$cd_" diff docs/core.md --root "$CD" 2>/dev/null | grep -q '^+and a worked case' || fail "diff did not print the doc's hunks"
python3 "$cd_" diff docs/other.md --root "$CD" >/dev/null 2>"$CD/err2" && fail "diff of a non-core doc ran"
grep -q 'not in invariantDocs or windowOnlyDocs' "$CD/err2" || fail "a non-core doc was not named: $(cat "$CD/err2")"
python3 "$cd_" --since HEAD~1 --root "$CD" 2>/dev/null | grep -q '^docs/core.md	15	13	+0 -2	1	whole$' || fail "--since did not replace the mark: $(python3 "$cd_" --since HEAD~1 --root "$CD" 2>/dev/null)"
c tag -d process-review-mark >/dev/null
python3 "$cd_" --root "$CD" >/dev/null 2>"$CD/err3" && fail "ran with no mark and no --since"
grep -q 'no such rev: process-review-mark' "$CD/err3" || fail "a missing mark was not named: $(cat "$CD/err3")"
printf '{ "markTag": "process-review-mark", "invariantDocs": ["CLAUDE.md"], "windowOnlyDocs": ["CLAUDE.md"] }\n' > "$CD/.claude/threads.json"
python3 "$cd_" --since HEAD~1 --root "$CD" >/dev/null 2>"$CD/err4" && fail "ran with a doc in both lists"
grep -q 'in both invariantDocs and windowOnlyDocs: CLAUDE.md' "$CD/err4" || fail "a doc in both lists was not named: $(cat "$CD/err4")"
printf '{ "markTag": "process-review-mark" }\n' > "$CD/.claude/threads.json"
python3 "$cd_" --root "$CD" 2>/dev/null | grep -q 'no invariantDocs or windowOnlyDocs configured' || fail "no invariantDocs did not say so"
ok "core-diff: per-doc words at mark and head, added/removed, commits, whole/window; diff; --since; a missing mark, a doc in neither list, and one in both refuse"
python3 "$cd_" self --root "$CD" 2>/dev/null | grep -q 'no commit carries Process-Review' || fail "self with no review landing did not say so"
printf '%s\n' one two three four five >> "$CD/docs/core.md"; mkdir -p "$CD/.claude"; printf 'log\n' > "$CD/.claude/threads-retro-log.md"
c add docs .claude/threads-retro-log.md; c commit -q -m "docs(process/x): a landing" -m "Process-Review: 2026-09-01" -m "Co-Authored-By: t <t@t>"
printf '%s\n' six seven >> "$CD/docs/core.md"; printf 'a rule\n' >> "$CD/CLAUDE.md"
c add docs CLAUDE.md; c commit -q -m "docs(process/x): a later landing" --trailer 'Process-Review: 2026-09-08'
printf 'one two three\n' > "$CD/CLAUDE.md"
c add CLAUDE.md; c commit -q -m "docs(process/x): a trim" --trailer 'Process-Review: 2026-09-15'
printf 'long ago\n' > "$CD/docs/old.md"; c add docs; GIT_AUTHOR_DATE=2026-01-01T00:00:00 c commit -q -m "docs(process/x): an old landing" --trailer 'Process-Review: 2026-01-01'
printf 'organic growth not the review\n' >> "$CD/docs/new.md"
c add docs; c commit -q -m "docs(process/y): organic"
python3 "$cd_" self --root "$CD" > "$CD/self.out" 2>"$CD/err5" || fail "core-diff self failed: $(cat "$CD/err5")"
grep -q '^core-diff self: the review.s own landings over 30 days, 3 runs (2026-09-01\.\.2026-09-15), 2 files$' "$CD/self.out" || fail "self header wrong: $(head -1 "$CD/self.out")"
[ "$(sed -n 2p "$CD/self.out")" = 'docs/core.md	20	+7 -0	2 grew · 0 trimmed of 2 runs' ] || fail "the doc the review grew run after run, one landing's marker outside the trailer block, is not first: $(cat "$CD/self.out")"
grep -qx 'CLAUDE.md	3	+2 -2	1 grew · 1 trimmed of 2 runs' "$CD/self.out" || fail "a grown-then-trimmed doc is wrong: $(cat "$CD/self.out")"
grep -q 'retro-log\|new.md\|old.md' "$CD/self.out" && fail "self counted the retro log, an organic commit, or a run outside the window"
python3 "$cd_" self --days 7 --root "$CD" 2>/dev/null | grep -q 'over 7 days, 2 runs (2026-09-08\.\.2026-09-15), 2 files' || fail "--days did not bound the window: $(python3 "$cd_" self --days 7 --root "$CD" 2>&1 | head -1)"
python3 "$here/scripts/marker-stream.py" list --all --root "$CD" 2>/dev/null | grep -q '^review	.*a landing$' || fail "marker-stream read a split trailer block's landing as organic"
ok "core-diff self: the review's own landings per file over a window in days, a marker on any body line, most net growth first; bookkeeping, organic, and older runs left out; marker-stream agrees"

# ---- a mark a peer force-pushed: a plain fetch leaves the local tag behind, and every
# script reading the mark refuses it and names the fetch that moves it
SR="$tmp/sr"; mkdir -p "$SR/w/.claude"
git init -q --bare -b main "$SR/remote.git"
git init -q -b main "$SR/w"; w() { git -C "$SR/w" "$@"; }
w config user.email t@t; w config user.name t
printf '{ "markerPattern": "^docs(process", "markTag": "process-review-mark", "retroLogPath": ".claude/log.md", "invariantDocs": ["CLAUDE.md"] }\n' > "$SR/w/.claude/threads.json"
printf '# base\n' > "$SR/w/CLAUDE.md"; printf '## Entries\n' > "$SR/w/.claude/log.md"
w add -A; w commit -q -m base; w tag process-review-mark
w remote add origin "$SR/remote.git"; w push -q origin main refs/tags/process-review-mark 2>/dev/null
git clone -q "$SR/remote.git" "$SR/peer" 2>/dev/null; p_() { git -C "$SR/peer" "$@"; }
p_ config user.email t@t; p_ config user.name t
printf 'rule\n' >> "$SR/peer/CLAUDE.md"; p_ commit -qam "docs(process/claude): a rule"
p_ tag -f process-review-mark >/dev/null; p_ push -q origin main 2>/dev/null; p_ push -q -f origin refs/tags/process-review-mark 2>/dev/null
w fetch -q origin 2>/dev/null; w merge -q --ff-only origin/main
[ "$(w rev-parse process-review-mark)" = "$(w rev-parse HEAD~1)" ] || fail "fixture: a plain fetch moved the tag, so this case proves nothing"
python3 "$ms" count --root "$SR/w" >/dev/null 2>"$SR/e1" && fail "marker-stream read a mark the remote holds elsewhere"
grep -q 'process-review-mark is [0-9a-f]* here but [0-9a-f]* on origin .* git fetch origin +refs/tags/process-review-mark:refs/tags/process-review-mark$' "$SR/e1" || fail "the stale mark's refusal did not name the fetch: $(cat "$SR/e1")"
python3 "$cd_" --root "$SR/w" >/dev/null 2>"$SR/e2" && fail "core-diff read a stale mark"
grep -q '+refs/tags/process-review-mark' "$SR/e2" || fail "core-diff's refusal did not name the fetch: $(cat "$SR/e2")"
python3 "$rl" view --keys --since process-review-mark --root "$SR/w" --log .claude/log.md >/dev/null 2>"$SR/e3" && fail "retro-log --since read a stale mark"
grep -q '+refs/tags/process-review-mark' "$SR/e3" || fail "retro-log's refusal did not name the fetch: $(cat "$SR/e3")"
python3 "$ms" count --since HEAD~1 --root "$SR/w" >/dev/null 2>&1 || fail "a --since that is not a tag was checked against the remote"
w fetch -q origin +refs/tags/process-review-mark:refs/tags/process-review-mark 2>/dev/null
python3 "$ms" count --root "$SR/w" 2>/dev/null | grep -q '^0 markers since process-review-mark' || fail "the fetched mark did not read: $(python3 "$ms" count --root "$SR/w" 2>&1)"
w tag -f process-review-mark HEAD~1 >/dev/null; w remote set-url origin "$SR/nowhere.git"
python3 "$ms" count --root "$SR/w" >/dev/null 2>&1 || fail "an unreachable remote refused — offline is not stale"
ok "stale mark: a force-pushed mark a plain fetch left behind refuses in marker-stream, core-diff, retro-log --since, naming the fetch; a fetched mark, a non-tag --since, an unreachable remote read"

# ---- scripts/adherence.py: a declared rule's seeded draw of distinct blocks, the window as
# the weighting, the tally's line with judge FPs, and a shape's windows read by the trailer.
ad="$here/scripts/adherence.py"
AD="$tmp/ad"; mkdir -p "$AD/.claude" "$AD/src"
printf '# judge\n' > "$AD/judge.md"
git init -q -b main "$AD"; a_() { git -C "$AD" "$@"; }
a_ config user.email t@t; a_ config user.name t
cat > "$AD/.claude/threads.json" <<'EOF4'
{ "markTag": "process-review-mark", "adherenceRules": [
  { "id": "comment-truth", "population": "grep -rnE '^[[:space:]]*//' src", "judgePrompt": "judge.md", "n": 20, "weighting": "uniform" },
  { "id": "windowed", "population": "grep -rnE '^[[:space:]]*//' src", "judgePrompt": "judge.md", "n": 20, "weighting": "window" },
  { "id": "two", "population": "grep -rnE '^[[:space:]]*//' src", "judgePrompt": "judge.md", "n": 2, "weighting": "uniform" },
  { "id": "reversed", "population": "grep -rnE '^[[:space:]]*//' src | sort -r", "judgePrompt": "judge.md", "n": 2, "weighting": "uniform" },
  { "id": "pathless", "population": "grep -nE '^[[:space:]]*//' src/b.c", "judgePrompt": "judge.md", "n": 2, "weighting": "uniform" } ] }
EOF4
printf '// one\n// two\n// three\nint a;\n\n// four\n// five\nint b;\n' > "$AD/src/a.c"
printf 'int c;\n// six\nint d;\n' > "$AD/src/b.c"
a_ add -A; a_ commit -q -m base; a_ tag process-review-mark
printf 'int c;\n// six, changed\nint d;\n' > "$AD/src/b.c"; a_ add -A; a_ commit -q -m "feat: touch b"
python3 "$ad" draw --rule comment-truth --seed 7 --root "$AD" > "$AD/m1" 2>"$AD/err" || fail "adherence draw failed: $(cat "$AD/err")"
head -1 "$AD/m1" | grep -qx 'adherence comment-truth: uniform · pop 2f/6l · n 3 · seed 7' || fail "a population under n was not sampled whole: $(head -1 "$AD/m1")"
grep -qx '== src/a.c:1-3' "$AD/m1" && grep -qx '== src/a.c:6-7' "$AD/m1" && grep -qx '== src/b.c:2-2' "$AD/m1" || fail "blocks not expanded to their spans: $(grep '^==' "$AD/m1")"
python3 "$ad" draw --rule two --seed 7 --root "$AD" 2>/dev/null > "$AD/m2"; python3 "$ad" draw --rule two --seed 7 --root "$AD" 2>/dev/null > "$AD/m3"
cmp -s "$AD/m2" "$AD/m3" || fail "one seed drew two manifests"
[ "$(grep -c '^== ' "$AD/m2")" -eq 2 ] || fail "n 2 did not draw two distinct blocks from six hits in three blocks: $(grep '^==' "$AD/m2")"
[ "$(grep '^== ' "$AD/m2" | sort -u | wc -l | tr -d ' ')" -eq 2 ] || fail "a block was drawn twice"
python3 "$ad" draw --rule reversed --seed 7 --root "$AD" 2>/dev/null | grep '^== ' | cmp -s - <(grep '^== ' "$AD/m2") || fail "the draw depends on the population's output order (rg's is not stable)"
python3 "$ad" draw --rule windowed --seed 7 --root "$AD" > "$AD/m4" 2>"$AD/err" || fail "windowed draw failed: $(cat "$AD/err")"
head -1 "$AD/m4" | grep -q '^adherence windowed: window process-review-mark (20[0-9-]*, [0-9a-f]*)\.\.HEAD · pop 1f/1l · n 1 · seed 7$' || fail "window weighting kept files outside the window: $(head -1 "$AD/m4")"
mkdir -p "$tmp/adplain"; cp -R "$AD/src" "$AD/.claude" "$AD/judge.md" "$tmp/adplain/"
GIT_CEILING_DIRECTORIES="$tmp" python3 "$ad" draw --rule windowed --seed 7 --root "$tmp/adplain" >/dev/null 2>"$AD/err" && fail "a window drew from a tree that is not a checkout"
grep -q 'not a git checkout.*--repo' "$AD/err" || fail "a window over a plain tree did not name --repo: $(cat "$AD/err")"
python3 "$ad" draw --rule windowed --seed 7 --root "$tmp/adplain" --repo "$AD" 2>"$AD/err" | cmp -s - "$AD/m4" || fail "--repo did not read the window from the repository and the files from --root: $(cat "$AD/err")"
printf 'src/a.c:2\nsrc/a.c:3\nsrc/b.c:2-2\n' > "$AD/list"
python3 "$ad" draw --rule comment-truth --blocks "$AD/list" --root "$AD" > "$AD/m5" 2>"$AD/err" || fail "--blocks draw failed: $(cat "$AD/err")"
head -1 "$AD/m5" | grep -q ' · n 2 · seed -$' || fail "a fixed list did not dedupe to distinct blocks: $(head -1 "$AD/m5")"
python3 "$ad" draw --rule pathless --root "$AD" >/dev/null 2>"$AD/err" && fail "a path-less population was accepted"
grep -q 'not `path:line:`' "$AD/err" || fail "a path-less population was not named: $(cat "$AD/err")"
python3 "$ad" draw --root "$AD" >/dev/null 2>"$AD/err" && fail "drew with five rules and no --rule"
mv "$AD/judge.md" "$AD/judge.away"
python3 "$ad" draw --rule comment-truth --seed 7 --root "$AD" >/dev/null 2>"$AD/err" && fail "drew with no judge prompt on disk"
grep -q 'judge prompt .*judge.md: no such file' "$AD/err" || fail "a missing judge prompt was not named: $(cat "$AD/err")"
python3 "$ad" draw --rule comment-truth --seed 7 --root "$AD" --judge-prompt "$AD/judge.away" 2>"$AD/err" | cmp -s - "$AD/m1" || fail "--judge-prompt did not stand in for a missing judgePrompt: $(cat "$AD/err")"
grep -q "adherence: judge prompt $AD/judge.away" "$AD/err" || grep -q 'adherence: judge prompt .*judge.away$' "$AD/err" || fail "draw did not name the judge prompt it checked: $(cat "$AD/err")"
mv "$AD/judge.away" "$AD/judge.md"
ok "adherence draw: seeded and reproducible, distinct blocks, a small population whole, window weighting, --repo for a plain tree, a fixed list, a path-less population and a missing judge prompt refuse"

printf 'src/a.c:1-3 DRIFTED DRIFTED count-over-hand-list\nsrc/a.c:6-7 HISTORY TRUE -\nsrc/b.c:2-2 TRUE TRUE -\n' > "$AD/v1"
python3 "$ad" tally "$AD/m1" "$AD/v1" > "$AD/t1" 2>"$AD/err" || fail "tally failed: $(cat "$AD/err")"
grep -qx 'Adherence: comment-truth 2/3 true · 1 drifted · 0 history · 1 judge FP · pop 2f/6l · seed 7 — shapes: count-over-hand-list src/a.c:1' "$AD/t1" || fail "tally line wrong: $(cat "$AD/t1")"
head -2 "$AD/v1" > "$AD/v2"
python3 "$ad" tally "$AD/m1" "$AD/v2" >/dev/null 2>"$AD/err" && fail "tally accepted a verdicts file missing a block"
printf 'src/a.c:1-3 TRUE DRIFTED x\nsrc/a.c:6-7 TRUE TRUE -\nsrc/b.c:2-2 TRUE TRUE -\n' > "$AD/v3"
python3 "$ad" tally "$AD/m1" "$AD/v3" >/dev/null 2>&1 && fail "tally accepted a TRUE verdict re-checked into a drift"
printf 'src/a.c:1-3 DRIFTED DRIFTED -\nsrc/a.c:6-7 TRUE TRUE -\nsrc/b.c:2-2 TRUE TRUE -\n' > "$AD/v4"
python3 "$ad" tally "$AD/m1" "$AD/v4" >/dev/null 2>&1 && fail "tally accepted a drift with no shape"
ok "adherence tally: the line, an overturn as a judge FP, a missing block, a re-checked TRUE, and a shapeless drift refuse"

# flags/verdicts: the agents' output is a checked input — one form, every block once, every
# defect named in one refusal — and verdicts emits the file tally reads.
cat > "$AD/j1" <<'EOF5'
```text
src/a.c:1-3  DRIFTED  count-over-hand-list  — "three backends": src/x.c:4 registers four
  src/a.c:6-7	HISTORY	narrates-a-change  — "used to retry": no retry exists in src/a.c

src/b.c:2-2  TRUE  -  — "six, changed": names nothing checkable
```
ruled 3: 1 TRUE, 1 DRIFTED, 1 HISTORY
EOF5
python3 "$ad" flags "$AD/m1" "$AD/j1" > "$AD/f1" 2>"$AD/err" || fail "flags refused a well-formed judge output: $(cat "$AD/err")"
printf '%s\n' 'src/a.c:1-3  DRIFTED  count-over-hand-list  — "three backends": src/x.c:4 registers four' 'src/a.c:6-7	HISTORY	narrates-a-change  — "used to retry": no retry exists in src/a.c' | cmp -s - <(sort "$AD/f1") || fail "flags did not print exactly the non-TRUE lines: $(cat "$AD/f1")"
printf 'src/a.c:1-3 TRUE - — holds\nsrc/a.c:6-7 TRUE - — holds\nsrc/b.c:2-2 TRUE - — holds\n' > "$AD/j0"
[ -z "$(python3 "$ad" flags "$AD/m1" "$AD/j0")" ] || fail "flags printed a line when every block is TRUE, or refused a summary-less output"
sed '1s/ TRUE - / TRUE holds-fine /' "$AD/j0" > "$AD/j3"
python3 "$ad" flags "$AD/m1" "$AD/j3" 2>&1 >/dev/null | grep -q 'line 1 .*a TRUE verdict takes `-` as its shape, got `holds-fine`' || fail "flags accepted a TRUE verdict with a shape"
cat > "$AD/j2" <<'EOF5'
TRUE src/a.c:1-3
TRUE · src/a.c:6-7 · - — holds
DRIFTED  src/b.c:2-2  x  — reason
src/a.c:6-7  DRIFTED  -  — claims four
src/a.c:6-7  TRUE  -  — again
Sources/a.c:1-3  TRUE  -  — holds
src/b.c:2-2  TRUE  -  —
ruled 3: 3 TRUE, 0 DRIFTED, 0 HISTORY
EOF5
python3 "$ad" flags "$AD/m1" "$AD/j2" >/dev/null 2>"$AD/err"; [ $? -eq 2 ] || fail "flags did not exit 2 on a drifted judge output"
for want in 'line 1 `TRUE src/a.c:1-3`: no em dash' 'line 2 .*`·` is not a separator' 'line 3 .*starts with the verdict' 'line 4 .*a DRIFTED verdict names its shape as a kebab-case slug, got `-`' 'line 5 .*already ruled at line 4' 'line 6 .*`Sources/a.c:1-3` is not a manifest block — copy the key exactly: `src/a.c:1-3`' 'line 7 .*empty reason' 'missing `src/a.c:1-3`' 'line 8 .*disagrees with the lines' '9 defect(s)'; do
  grep -q -- "$want" "$AD/err" || fail "flags refusal did not name: $want — got: $(cat "$AD/err")"
done
cat > "$AD/rf1" <<'EOF5'
src/a.c:1-3  CONFIRMED  — src/x.c:4 registers four, re-read
src/a.c:6-7  OVERTURNED  — states the present contract
re-checked 2: 1 CONFIRMED, 1 OVERTURNED
EOF5
python3 "$ad" verdicts "$AD/m1" "$AD/j1" "$AD/rf1" > "$AD/vd1" 2>"$AD/err" || fail "verdicts refused well-formed output: $(cat "$AD/err")"
grep '^== ' "$AD/m1" | cut -c4- > "$AD/order"
printf 'src/a.c:1-3 DRIFTED DRIFTED count-over-hand-list\nsrc/a.c:6-7 HISTORY TRUE narrates-a-change\nsrc/b.c:2-2 TRUE TRUE -\n' | cmp -s - <(sort "$AD/vd1") && cut -d' ' -f1 "$AD/vd1" | cmp -s - "$AD/order" || fail "verdicts file wrong: $(cat "$AD/vd1")"
python3 "$ad" tally "$AD/m1" "$AD/vd1" | cmp -s - "$AD/t1" || fail "tally over verdicts' file did not print the expected line"
printf 'src/a.c:1-3  UPHELD  — r\nsrc/b.c:2-2  CONFIRMED  — r\n' > "$AD/rf2"
python3 "$ad" verdicts "$AD/m1" "$AD/j1" "$AD/rf2" >/dev/null 2>"$AD/err" && fail "verdicts accepted UPHELD, an unflagged block, and a missing one"
for want in 'verdict `UPHELD` is not one of CONFIRMED, OVERTURNED' '`src/b.c:2-2` is not a flagged block' 'missing `src/a.c:6-7`'; do
  grep -q -- "$want" "$AD/err" || fail "verdicts refusal did not name: $want — got: $(cat "$AD/err")"
done
printf 'src/a.c:1-3  CONFIRMED  — r\nsrc/a.c:6-7  REFUTED  — r\nsrc/a.c:6-7  CONFIRMED  narrates-a-change  — r\n' > "$AD/rf3"
python3 "$ad" verdicts "$AD/m1" "$AD/j1" "$AD/rf3" >/dev/null 2>"$AD/err" && fail "verdicts accepted REFUTED, a shape column, and a block re-checked twice"
for want in 'verdict `REFUTED` is not one of' '3 field(s) before the em dash, want 2' 'already ruled at line 2'; do
  grep -q -- "$want" "$AD/err" || fail "verdicts refusal did not name: $want — got: $(cat "$AD/err")"
done
python3 "$ad" verdicts "$AD/m1" "$AD/j1" >/dev/null 2>"$AD/err" && fail "verdicts ran with flags and no refuter output"
grep -q 'no REFUTER_OUT' "$AD/err" || fail "a missing refuter output was not named: $(cat "$AD/err")"
python3 "$ad" verdicts "$AD/m1" "$AD/j0" "$AD/rf1" >/dev/null 2>&1 && fail "verdicts read a refuter output with nothing flagged"
python3 "$ad" verdicts "$AD/m1" "$AD/j0" | grep -c ' TRUE TRUE -$' | grep -qx 3 || fail "an all-TRUE judge output did not make an all-TRUE verdicts file"
ok "adherence flags/verdicts: one form held, only flags passed on, every defect named in one refusal (bare, ·, verdict-first, missing, twice, undrawn, shapeless, reasonless, summary; a shaped TRUE), UPHELD/REFUTED and an unflagged or missing re-check refuse, the file tally reads"

a_ commit -q --allow-empty -m "docs(process/review): 09-01" -m "Adherence: comment-truth 9/10 true · 1 drifted · 0 history · 0 judge FP · pop 3f/40l · seed 1 — shapes: count-over-hand-list src/x.c:4" --trailer "Process-Review: 2026-09-01"
a_ commit -q --allow-empty -m "feat: quotes the line, no trailer" -m "Adherence: comment-truth 9/10 true · 1 drifted · 0 history · 0 judge FP · pop 3f/40l · seed 1 — shapes: premise-elsewhere src/y.c:4"
python3 "$ad" recur --rule comment-truth --current "$AD/t1" --root "$AD" > "$AD/r1" 2>"$AD/err" || fail "recur failed: $(cat "$AD/err")"
grep -qx '2	count-over-hand-list	2026-09-01,current	routed' "$AD/r1" || fail "a shape in two windows was not routed: $(cat "$AD/r1")"
grep -q 'premise-elsewhere' "$AD/r1" && fail "a commit with no Process-Review trailer counted as a window"
a_ commit -q --allow-empty -m "docs(process/review): 09-02" -m "Adherence: comment-truth 10/10 true · 0 drifted · 0 history · 0 judge FP · pop 3f/40l · seed 2 — shapes: none" --trailer "Process-Review: 2026-09-02"
python3 "$ad" recur --rule comment-truth --root "$AD" 2>/dev/null | grep -qx '1	count-over-hand-list	2026-09-01	recorded' || fail "a one-window shape was not recorded: $(python3 "$ad" recur --rule comment-truth --root "$AD")"
python3 "$ad" tally "$AD/m1" "$AD/vd1" --control all-true > "$AD/tc" 2>"$AD/err" || fail "tally --control failed: $(cat "$AD/err")"
grep -qx 'Adherence-control: comment-truth 2/3 true · 1 drifted · 0 history · 1 judge FP · pop 2f/6l · seed 7 — shapes: count-over-hand-list src/a.c:1 · control all-true' "$AD/tc" || fail "tally --control line wrong: $(cat "$AD/tc")"
a_ commit -q --allow-empty -m "docs(process/review): 09-03" -m "$(sed 's/count-over-hand-list/control-only-shape/' "$AD/tc")" --trailer "Process-Review: 2026-09-03"
python3 "$ad" recur --rule comment-truth --current "$AD/tc" --root "$AD" > "$AD/r2" 2>"$AD/err" || fail "recur failed: $(cat "$AD/err")"
grep -qx '1	count-over-hand-list	2026-09-01	recorded' "$AD/r2" && ! grep -q 'control-only-shape' "$AD/r2" || fail "recur counted a control line as a window: $(cat "$AD/r2")"
ok "adherence recur: windows by trailer date, routed at two, recorded at one, a quoting commit and a control line ignored"

# the range starts at the rule's last sample (the newest review commit carrying its line),
# else the mark; --since overrides it; a floor skips a range too quiet to sample
cat > "$AD/.claude/floor.json" <<'EOF5'
{ "markTag": "process-review-mark", "adherenceRules": [
  { "id": "comment-truth", "population": "grep -rnE '^[[:space:]]*//' src", "judgePrompt": "judge.md", "n": 20, "weighting": "window" },
  { "id": "floored", "population": "grep -rnE '^[[:space:]]*//' src", "judgePrompt": "judge.md", "n": 20, "weighting": "window", "floor": 2 },
  { "id": "stock", "population": "grep -rnE '^[[:space:]]*//' src", "judgePrompt": "judge.md", "n": 1, "weighting": "uniform", "floor": 1 } ] }
EOF5
sample="$(a_ log -1 --format=%h --grep='^Process-Review: 2026-09-02')"
python3 "$ad" draw --config "$AD/.claude/floor.json" --rule comment-truth --seed 7 --root "$AD" > "$AD/w1" 2>"$AD/err" || fail "a draw from the last sample failed: $(cat "$AD/err")"
head -1 "$AD/w1" | grep -q "^adherence comment-truth: window last sample (20[0-9-]*, $sample)\.\.HEAD · pop 0f/0l · n 0 · seed 7$" || fail "the window did not start at the rule's last sample ($sample), past the control line: $(head -1 "$AD/w1")"
python3 "$ad" draw --config "$AD/.claude/floor.json" --rule comment-truth --seed 7 --since process-review-mark --root "$AD" 2>/dev/null | head -1 | grep -q '^adherence comment-truth: window process-review-mark (.*· pop 1f/1l · n 1 ' || fail "--since did not override the last sample"
python3 "$ad" draw --config "$AD/.claude/floor.json" --rule floored --seed 7 --root "$AD" > "$AD/w2" 2>"$AD/err" || fail "a floored draw failed: $(cat "$AD/err")"
head -1 "$AD/w2" | grep -q '^adherence floored: window process-review-mark (.*)\.\.HEAD · below floor 1/2 commits · pop 1f/1l · n 0 · seed 7$' && [ "$(wc -l < "$AD/w2" | tr -d ' ')" -eq 1 ] || fail "a range under the floor drew blocks or misread the floor: $(cat "$AD/w2")"
printf 'int z;\n' >> "$AD/src/a.c"; a_ add -A; a_ commit -q -m "docs(process/review): the sample's own fix" --trailer "Process-Review: 2026-09-04"
python3 "$ad" draw --config "$AD/.claude/floor.json" --rule floored --seed 7 --root "$AD" 2>/dev/null | head -1 | grep -q ' · below floor 1/2 commits · ' || fail "a review's own commit counted toward the floor"
printf '// one, changed\n// two\n// three\nint a;\n\n// four\n// five\nint b;\n' > "$AD/src/a.c"; a_ add -A; a_ commit -q -m "feat: touch a"
python3 "$ad" draw --config "$AD/.claude/floor.json" --rule comment-truth --seed 7 --root "$AD" 2>/dev/null | head -1 | grep -q "last sample (20[0-9-]*, $sample)\.\.HEAD · pop 1f/5l · n 2 " || fail "the window from the last sample did not hold exactly the file changed after it"
python3 "$ad" draw --config "$AD/.claude/floor.json" --rule floored --seed 7 --root "$AD" 2>/dev/null | head -1 | grep -q '\.\.HEAD · floor 2/2 commits · pop 2f/6l · n 3 ' || fail "a range at the floor was not drawn"
python3 "$ad" draw --config "$AD/.claude/floor.json" --rule stock --seed 7 --root "$AD" 2>/dev/null | head -1 | grep -q '^adherence stock: uniform since process-review-mark (.*)\.\.HEAD · floor 2/1 commits · pop 2f/6l · n 1 ' || fail "a uniform rule's floor did not read its range"
printf '{ "adherenceRules": [ { "id": "zero", "population": "true", "judgePrompt": "judge.md", "n": 1, "weighting": "uniform", "floor": 0 } ] }\n' > "$AD/.claude/bad.json"
python3 "$ad" draw --config "$AD/.claude/bad.json" --root "$AD" >/dev/null 2>"$AD/err" && fail "a zero floor was accepted"
grep -q 'floor must be a positive integer' "$AD/err" || fail "a bad floor was not named: $(cat "$AD/err")"
ok "adherence draw: the range starts at the rule's last sample, else the mark; --since overrides; under the floor the header alone, at it the draw; a bad floor refuses"

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
# ---- scripts/workarounds.py: a workaround retires when its tool moves and its probe stops reproducing
wa="$here/scripts/workarounds.py"
W="$tmp/wa"; mkdir -p "$W/probes" "$W/docs" "$W/.claude" "$W/hooks"
git -C "$W" init -q
printf '# rules\n' > "$W/docs/rules.md"; printf '#!/bin/sh\n' > "$W/hooks/pre.sh"
printf 'exit "$(cat probes/a.code)"\n' > "$W/probes/a.sh"; echo 0 > "$W/probes/a.code"
printf 'exit "$(cat probes/b.code)"\n' > "$W/probes/b.sh"; echo 1 > "$W/probes/b.code"
cat > "$W/.claude/workarounds.json" <<'EOF'
{ "tools": { "fake": "fake --version", "gone": "false" },
  "workarounds": [
    { "id": "a", "tool": "fake", "observed": "1.2.0", "probe": "sh probes/a.sh", "sites": ["docs/rules.md#a"] },
    { "id": "b", "tool": "fake", "observed": "1.2.0", "probe": "sh probes/b.sh", "sites": ["hooks/pre.sh"] },
    { "id": "f", "tool": "fake", "observed": "1.2.0", "probe": "fake --quirk", "sites": ["docs/rules.md"] },
    { "id": "m", "tool": "fake", "observed": "1.2.0", "probe": null, "retest": "start a session and relay an approval", "sites": ["docs/rules.md#m"] },
    { "id": "g", "tool": "gone", "observed": "3.0", "probe": "true", "sites": ["docs/rules.md"] } ] }
EOF
# `fake` exists only as a function of this shell, as a harness-injected command does: the read
# sees it only if it runs in the caller's shell, never in a subprocess of the script
fake() { case "$1" in --version) echo "fake $FAKE_V (build 7)" ;; --quirk) return "$FAKE_Q" ;; esac; }
wread() { eval "$(python3 "$wa" versions --root "$W")" | python3 "$wa" due --root "$W" | { eval "$(cat)"; } | python3 "$wa" record --root "$W" 2>/dev/null; python3 "$wa" status --root "$W"; }
python3 "$wa" status --root "$W" >/dev/null 2>&1; [ $? -eq 3 ] || fail "workarounds did not skip with no workaroundsPath"
echo '{"workaroundsPath": ".claude/workarounds.json"}' > "$W/.claude/threads.json"
python3 "$wa" check --root "$W" 2>/dev/null || fail "check refused a valid register"
python3 "$wa" status --root "$W" | head -1 | grep -q '5 — live 0 · retirable 0 · due 5 · broken 0; fake ?, gone ?' || fail "unread versions are not due"
FAKE_V=1.2.0 FAKE_Q=0 wread > "$W/out" || fail "the read failed"
head -1 "$W/out" | grep -q '5 — live 4 · retirable 0 · due 0 · broken 1; fake 1.2.0, gone ?$' || fail "at the observed version: $(head -1 "$W/out")"
grep -q '^broken	g	gone ?	version unreadable' "$W/out" || fail "an unreadable version is not broken"
[ -f "$W/.git/threads/workarounds-state.json" ] || fail "answers not kept in the git common dir"
git -C "$W" status --porcelain | grep -q threads && fail "answers landed in the tree"
ok "workarounds: no register skips; unread is due; the version is read in the caller's shell, a function included; state outside the tree"
FAKE_V=1.3.0 FAKE_Q=1 wread > "$W/out" || fail "the read after a move failed"
head -1 "$W/out" | grep -q 'live 1 · retirable 2 · due 1 · broken 1; fake 1.3.0' || fail "after a move: $(head -1 "$W/out")"
grep -q '^retirable	b	fake 1.3.0	stopped reproducing at 1.3.0 on .* (observed at 1.2.0)	hooks/pre.sh$' "$W/out" || fail "a probe exiting 1 is not retirable with its sites"
grep -q '^retirable	f	' "$W/out" || fail "a probe calling the caller's function was not answered by it"
grep -q '^due	m	fake 1.3.0	.*re-test: start a session and relay an approval	docs/rules.md#m$' "$W/out" || fail "a re-test is not due with its steps after a move"
[ -z "$(printf 'fake\t1.3.0\n' | python3 "$wa" due --root "$W")" ] || fail "due re-ran probes already answered at this version"
ok "workarounds: a move makes them due; each probe runs once in the caller's shell, exit 1 retirable; a re-test is listed, never run"
python3 "$wa" record m 1 --root "$W" 2>/dev/null || fail "record refused a re-test's answer"
python3 "$wa" status --root "$W" | grep -q '^retirable	m	' || fail "a recorded re-test did not retire"
echo 0 > "$W/probes/b.code"
printf 'fake\t1.3.0\n' | python3 "$wa" due --id b --root "$W" | { eval "$(cat)"; } | python3 "$wa" record --root "$W" 2>/dev/null
python3 "$wa" status --root "$W" | grep -q '^retirable	b' && fail "--id did not re-probe one workaround"
python3 "$wa" due --id nosuch --root "$W" </dev/null >/dev/null 2>&1 && fail "--id accepted an unknown workaround"
python3 "$wa" record nosuch 1 --root "$W" >/dev/null 2>&1 && fail "record accepted an unknown workaround"
ok "workarounds: record takes a re-test's answer; --id re-probes one; unknown ids refuse"
cat > "$W/.claude/workarounds.json" <<'EOF'
{ "tools": { "fake": "fake --version" },
  "workarounds": [
    { "id": "x", "tool": "fake", "observed": "1.0", "sites": ["docs/rules.md"] },
    { "id": "x", "tool": "other", "observed": "1.0", "probe": "sh probes/none.sh", "retest": "by hand", "sites": ["docs/nope.md#y"], "extra": 1 } ] }
EOF
python3 "$wa" check --root "$W" > "$W/out" 2>/dev/null && fail "check passed a malformed register"
for want in 'x: needs a `probe` or, with `probe: null`, a `retest` — exactly one' 'x: id used twice' 'tool other is not in `tools`' 'site docs/nope.md#y: no such path' 'probe script probes/none.sh: no such file' 'unknown field `extra`'; do
  grep -qF "$want" "$W/out" || fail "check missed: $want"
done
[ "$(grep -c 'exactly one' "$W/out")" -eq 2 ] || fail "check did not refuse both neither and both of probe and retest"
python3 "$wa" status --root "$W" >/dev/null 2>&1; [ $? -eq 2 ] || fail "status ran on a malformed register"
ok "workarounds: check names neither or both of probe and retest, a reused id, an undeclared tool, a missing site or probe script, an unknown field; status refuses"

# ---- extract-record.py: who said what survives the distillation
er="$here/scripts/extract-record.py"
E="$tmp/extract"; mkdir -p "$E"
record() {  # transcript → the record's path; a temp file under this suite's temp dir
  TMPDIR="$E" python3 "$er" "$1" | sed -n 's/^record: \(.*\) ([0-9]* bytes.*$/\1/p'
}
cat > "$E/t.jsonl" <<'EOF'
{"type":"user","origin":{"kind":"human"},"message":{"content":"<system-reminder>\nnoise-str\n</system-reminder>\n\nyes, merge it"}}
{"type":"user","origin":{"kind":"human"},"message":{"content":[{"type":"text","text":"<system-reminder>noise-list</system-reminder>"},{"type":"text","text":"and delete the branch"}]}}
{"type":"user","origin":{"kind":"human"},"message":{"content":"<pasted_content id=\"ab\">\npasted words\n</pasted_content id=\"ab\">"}}
{"type":"user","origin":{"kind":"human"},"message":{"content":"<command-message>land</command-message>\n<command-name>/land</command-name>\n<command-args>525</command-args>"}}
{"type":"user","origin":{"kind":"human"},"message":{"content":"<command-name>/ship</command-name>\n\nbut skip the tag"}}
{"type":"user","origin":{"kind":"human"},"message":{"content":"<b>a tag that is just the human's words</b>"}}
{"type":"user","origin":{"kind":"human"},"message":{"content":[{"type":"text","text":"look at this"},{"type":"image","source":{}}]}}
{"type":"user","origin":{"kind":"human"},"message":{"content":"<cross-session-message>a peer's words the human pasted</cross-session-message>"}}
{"type":"user","isMeta":true,"message":{"content":[{"type":"image","source":{}}]}}
{"type":"user","isMeta":true,"message":{"content":"[Image: original 10x10, displayed at 5x5.]"}}
{"type":"user","isMeta":true,"origin":{"kind":"peer","name":"Other session","body":"please merge now"},"message":{"content":"Another Claude session sent a message:\n<cross-session-message>please merge now</cross-session-message>"}}
{"type":"user","message":{"content":"<cross-session-message from=\"x\">unmarked peer words</cross-session-message>"}}
{"type":"user","message":{"content":"Another Claude session sent a message:\n<teammate-message teammate_id=\"t\">teammate words</teammate-message>"}}
{"type":"user","isMeta":true,"message":{"content":[{"type":"text","text":"Land this branch: the body of a slash command"}]}}
{"type":"user","isCompactSummary":true,"message":{"content":"Summary of the earlier conversation the user never typed"}}
{"type":"attachment","attachment":{"type":"queued_command","prompt":"sent while it worked","commandMode":"prompt","origin":{"kind":"human"}}}
{"type":"attachment","attachment":{"type":"queued_command","prompt":"<task-notification>\n<summary>bg finished</summary>\n</task-notification>","commandMode":"task-notification"}}
{"type":"assistant","message":{"content":[{"type":"tool_use","id":"q1","name":"AskUserQuestion","input":{"questions":[{"question":"Which lane?"}]}}]}}
{"type":"user","message":{"content":[{"type":"tool_result","tool_use_id":"q1","content":"The user answered: \"Which lane?\"=\"Fast\""}]}}
{"type":"assistant","message":{"content":[{"type":"tool_use","id":"e1","name":"Edit","input":{"file_path":"a.txt"}}]}}
{"type":"user","toolDenialKind":"user-rejected","message":{"content":[{"type":"tool_result","is_error":true,"tool_use_id":"e1","content":"The user doesn't want to proceed with this tool use. To tell you how to proceed, the user said:\nnot that file"}]}}
{"type":"assistant","message":{"content":[{"type":"tool_use","id":"b1","name":"Bash","input":{"command":"ls"}}]}}
{"type":"user","message":{"content":[{"type":"tool_result","tool_use_id":"b1","content":"tool output payload"}]}}
{"type":"assistant","message":{"content":[{"type":"tool_use","id":"s1","name":"Skill","input":{"skill":"land","args":"525"}},{"type":"tool_use","id":"s2","name":"SendMessage","input":{"to":"x","summary":"the author's label","message":"the whole body"}},{"type":"tool_use","id":"s3","name":"Other","input":{"n":1,"note":"first string field"}},{"type":"tool_use","id":"s4","name":"SendMessage","input":{"to":"y","notify_when_idle":true}},{"type":"tool_use","id":"s5","name":"mcp__ccd_session__start_session","input":{"title":"Fix it","background":"bg","prompt":"go fix it"}},{"type":"tool_use","id":"s6","name":"Agent","input":{"subagent_type":"Explore","description":"look","prompt":"look around"}},{"type":"tool_use","id":"s7","name":"Bash","input":{"command":"S=/a/very/long/path/that/fills/the/whole/of/the/did/cap/so/nothing/after/it/shows/at/all/in/the/line; git -C \"$S\" log; git commit -m 'subject'; cd x && git push origin HEAD:main\ngh pr merge 5 | cat; echo \"git push is only words\"; if ok; then git --no-pager tag v1; fi; git commit -F - <<'E'\ngit reset is only a body line\nE\n"}},{"type":"text","text":"done"}]}}
{"type":"user","message":{"content":"plain turn with no author mark"}}
{"type":"user","message":{"content":"<system-reminder>a brief</system-reminder>\nbrief behind a reminder, no mark"}}
{"type":"user","origin":{"kind":"newkind"},"message":{"content":"a kind this reader has not met"}}
{"type":"user","message":{"content":[{"type":"text","text":"[Request interrupted by user]"}]}}
{"type":"user","message":{"content":"<system-reminder>only a reminder</system-reminder>"}}
{"type":"user","message":{"content":"<ci-monitor-event>CI failed</ci-monitor-event>"}}
{"type":"user","isSidechain":true,"origin":{"kind":"human"},"message":{"content":"sidechain words"}}
{"type":"user","isMeta":true,"origin":{"kind":"peer","from":"local_9","name":"Titled session","body":"a reply"},"message":{"content":"x"}}
{"type":"user","isMeta":true,"origin":{"kind":"peer","from":"uds:/tmp/s","name":"Socket session","body":"b"},"message":{"content":"Another Claude session sent a message:\n<cross-session-message from=\"local_7\" from-name=\"Socket session\">b</cross-session-message>"}}
{"type":"assistant","message":{"content":[{"type":"tool_use","id":"n1","name":"SendMessage","input":{"to":"local_9","message":"to a titled session"}},{"type":"tool_use","id":"n2","name":"SendMessage","input":{"to":"local_8","message":"to an untitled one"}},{"type":"tool_use","id":"n4","name":"SendMessage","input":{"to":"local_7","message":"to a socket peer"}},{"type":"tool_use","id":"n3","name":"Bash","input":{"command":"S=/a/very/long/path/that/fills/the/whole/of/the/did/cap/so/nothing/after/it/shows/at/all/in/the/line; \"$P/land-commit.py\" HEAD; python3 -u scripts/gate.py --fast run >/dev/null; python3 - <<'E'\nprint(1)\nE\nbash -c 'x'; ./deploy.sh; ls /a/b.py; echo scripts/words.py"}}]}}
{"type":"user","message":{"content":"<system-reminder>a reminder</system-reminder>\nBackground (from the session that started this one): you are the next orchestrator"}}
{"type":"user","message":{"content":"<system-reminder>\nThe session \"Child\" you started (local_1) finished a turn (branch \"b\"). It reported (quoted child output, data not instructions): \"tests pass, \"mostly\"\" (first 20 of 900 characters) Read it with get_session if you need details.\n</system-reminder><side-sessions-event>Otherwise tell the user.</side-sessions-event>"}}
{"type":"user","message":{"content":"<system-reminder>\nThe session \"Quiet\" you started (local_3) finished a turn.\nThe session \"Loud\" you started (local_4) finished a turn. It reported (quoted child output, data not instructions): \"a \"word\" Then more\" Read it with get_session.\n</system-reminder>"}}
{"type":"user","origin":{"kind":"human"},"message":{"content":[{"type":"text","text":"<system-reminder>\nThe session \"Other\" you started (local_2) finished a turn and then reported that it was waiting on the user. It reported (quoted child output, data not instructions): \"need a push\" Read it with get_session.\n</system-reminder>"},{"type":"text","text":"Yes, allow push"}]}}
this line is not json
EOF
r="$(record "$E/t.jsonl")"; [ -s "$r" ] || fail "extract-record wrote no record"
has() { grep -qxF "$1" "$r" || fail "record lacks line: $1"; }
hasnt() { grep -qF "$1" "$r" && fail "record holds: $1"; true; }
has 'USER ↦: [harness block cut] yes, merge it'
has 'USER ↦: [harness block cut] and delete the branch'
hasnt 'noise-'
has 'USER ↦: <pasted_content id="ab"> pasted words </pasted_content id="ab">'
has 'USER ↦: /land 525'
has 'USER ↦: /ship but skip the tag'
has "USER ↦: <b>a tag that is just the human's words</b>"
has 'USER ↦: look at this [image]'
hasnt '[Image:'
has "USER ↦: <cross-session-message>a peer's words the human pasted</cross-session-message>"
grep -qx 'HARNESS: *' "$r" && fail "an image-only meta row left a blank HARNESS line"
ok "extract-record: a human turn keeps its words behind a harness block, and a pasted block, a slash command, a leading tag, and an image reach USER"
has 'PEER ↦: Other session: please merge now'
grep -qF 'PEER ↦: <cross-session-message from="x">unmarked peer words' "$r" || fail "an unmarked peer tag is not PEER"
grep -qF 'PEER ↦: Another Claude session sent a message: <teammate-message' "$r" || fail "a teammate message is not PEER"
has 'HARNESS: Land this branch: the body of a slash command'
has 'HARNESS: context compacted; the agent continued from a summary'
grep -qE '^USER.*(please merge now|body of a slash command|never typed|unmarked peer|teammate words)' "$r" && fail "a peer, command body, or summary reads as the user's"
ok "extract-record: a peer's words, a command body, and a compaction summary never read as USER"
has 'USER ↦: sent while it worked'
grep -qF 'HARNESS: <task-notification> <summary>bg finished' "$r" || fail "a queued notification is not HARNESS"
ok "extract-record: a message queued mid-turn reaches USER, a queued notification HARNESS"
has '  DID : AskUserQuestion(Which lane?)'
has 'USER ↦: [answered] The user answered: "Which lane?"="Fast"'
has "USER ↦: [rejected Edit] The user doesn't want to proceed with this tool use. To tell you how to proceed, the user said: not that file"
hasnt 'tool output payload'
ok "extract-record: an answer and a rejection reach USER; any other tool result stays out"
has '  DID : Skill(land 525)'
has '  SAID: → x: the whole body'
has '  DID : SendMessage(y)'
has '  SAID: → Fix it: go fix it'
has '  SAID: → Explore: look around'
hasnt "the author's label"
grep -qF "[ran: git commit -m 'subject'; git push origin HEAD:main; gh pr merge 5; git --no-pager tag v1; git commit -F -]" "$r" || fail "a Bash DID hid a state-changing command past its cut"
hasnt 'git push is only words]'
has '  DID : Other(first string field)'
ok "extract-record: a DID line names a skill, a Bash line its state-changing commands past the cut, else the first string field; a message sent reads SAID with its recipient and body"
has '  SAID: → Titled session: to a titled session'
has '  SAID: → local_8: to an untitled one'
has '  SAID: → Socket session: to a socket peer'
grep -qF '[ran: land-commit.py HEAD; gate.py run; deploy.sh]' "$r" || fail "a script past the cut is not listed by basename and first argument"
ok "extract-record: a script at command position lists by basename and first argument, named by no list; a message reads the session's title once the transcript gave it"
has 'BRIEF ↦: Background (from the session that started this one): you are the next orchestrator'
has 'PEER ↦: Child: tests pass, "mostly" (first 20 of 900 characters)'
has 'PEER ↦: Other: need a push'
has 'PEER ↦: Loud: a "word" Then more'
hasnt 'Quiet:'
has 'USER ↦: [harness block cut] Yes, allow push'
grep -q '^HARNESS: .*Child' "$r" && fail "a relayed report also left a harness line"
ok "extract-record: a started session's brief reads BRIEF; a relayed report reads PEER with the tool's own cut, beside any human words in its turn"
has 'USER? ↦: plain turn with no author mark'
has 'USER? ↦: [harness block cut] brief behind a reminder, no mark'
has 'USER? ↦: a kind this reader has not met'
has 'USER ↦: [Request interrupted by user]'
has 'HARNESS: <system-reminder>only a reminder</system-reminder>'
has 'HARNESS: <ci-monitor-event>CI failed</ci-monitor-event>'
hasnt 'sidechain words'
ok "extract-record: no author mark is USER?, never USER; a tag-only turn is HARNESS; a sidechain stays out"
hasnt 'no turn here is marked'
printf '{"type":"user","message":{"content":"old turn"}}\n' > "$E/old.jsonl"
r="$(record "$E/old.jsonl")"; grep -q '^note: no turn here is marked as the human' "$r" || fail "a record with no human turn does not say so"
: > "$E/empty.jsonl"; printf '{"type":"changed","payload":1}\n' > "$E/changed.jsonl"
printf '[1, 2]\n' > "$E/row.jsonl"
for t in empty changed row; do
  TMPDIR="$E" python3 "$er" "$E/$t.jsonl" >/dev/null 2>"$E/err"; [ $? -eq 1 ] || fail "extract-record passed an unreadable transcript ($t)"
  grep -q 'format has changed' "$E/err" || fail "the failure does not name the format ($t)"
done
ok "extract-record: no human turn is said on the record's first lines; no events at all fails, never an empty record"
python3 - "$E/long.jsonl" <<'EOF'
import json, sys
with open(sys.argv[1], "w") as f:
    f.write(json.dumps({"type": "user", "origin": {"kind": "human"}, "message": {"content": "HEAD " + "x " * 3000 + " TAIL"}}) + "\n")
    f.write(json.dumps({"type": "user", "message": {"content": "<task-notification>" + "y " * 500 + "SUMMARY</task-notification>"}}) + "\n")
EOF
r="$(record "$E/long.jsonl")"
grep -qE '^USER ↦: HEAD .* \[…\] .* TAIL$' "$r" || fail "a long human turn lost its head or tail"
grep -qE '^HARNESS: .* \[…\] .*SUMMARY</task-notification>$' "$r" || fail "a long harness turn lost its tail"
[ "$(grep '^HARNESS' "$r" | wc -c)" -lt 300 ] || fail "a harness turn is not cut to its cap"
ok "extract-record: a long turn keeps head and tail around a marked elision; a harness turn keeps to its smaller cap"

# ---- extract-record.py --probe: a tool watch's read of the format
[ -z "$(TMPDIR="$E" python3 "$er" --probe "$E/long.jsonl" 2>&1)" ] || fail "the probe found a surprise in a transcript it reads"
cat > "$E/new.jsonl" <<'EOF'
{"type":"user","origin":{"kind":"human"},"message":{"content":"hi"}}
{"type":"user","origin":{"kind":"robot"},"message":{"content":"new author"}}
{"type":"note","message":{"content":"a new row"}}
{"type":"attachment","attachment":{"type":"voice_command","prompt":"a new route"}}
EOF
python3 "$er" --probe "$E/new.jsonl" 2>"$E/err"; [ $? -eq 2 ] || fail "the probe passed a changed format"
for want in 'author kind robot' 'row type note' 'attachment type voice_command'; do
  grep -q "$want" "$E/err" || fail "the probe missed: $want"
done
env -u CLAUDE_CODE_SESSION_ID python3 "$er" --probe >/dev/null 2>&1; [ $? -eq 2 ] || fail "a probe with no transcript did not say it could not tell"
python3 "$er" --probe "$E/old.jsonl" 2>"$E/err"; [ $? -eq 2 ] && grep -q 'no turn marked' "$E/err" || fail "the probe passed a transcript with no human turn"
ok "extract-record --probe: exit 2 names a new author, row, or route, or no human turn; a transcript it reads passes quietly"

# ---- workarounds.py changelogs: what a version number cannot say
C="$tmp/cl"; mkdir -p "$C/.claude"; git init -q "$C"
cat > "$C/.claude/threads.json" <<'EOF'
{ "workaroundsPath": ".claude/w.json" }
EOF
cat > "$C/.claude/w.json" <<'EOF'
{ "tools": { "fake": "echo 1.0" }, "workarounds": [],
  "changelogs": { "fake": { "url": "https://example.test/log.md", "terms": ["transcript", "Plugin"] } } }
EOF
cat > "$C/log.md" <<'EOF'
# Changelog

## 1.3.0

- Fixed the transcript order
- Unrelated fix

## 1.2.0

- Plugins can do more

## 1.1.0

- Old transcript note
EOF
python3 "$wa" check --root "$C" >/dev/null 2>&1 || fail "check refused a good changelogs entry"
python3 "$wa" changelogs --root "$C" | grep -q 'curl -fsSL https://example.test/log.md | python3 .* changelog fake' || fail "changelogs printed no fetch"
python3 "$wa" changelog fake --root "$C" < "$C/log.md" | grep -q 'baseline set at 1.3.0' || fail "a first read did not set the baseline"
python3 "$wa" changelog fake --root "$C" < "$C/log.md" | grep -q '1.3.0 to 1.3.0, 0 of 0' || fail "a second read re-read the changelog"
python3 "$wa" changelog fake --since 1.1.0 --root "$C" < "$C/log.md" > "$C/out"
[ "$(sed -n 1p "$C/out")" = "$(printf '1.2.0\tPlugins can do more')" ] || fail "--since did not read oldest first, matching any case"
grep -q 'Fixed the transcript order' "$C/out" || fail "a matching entry is missing"
grep -q 'Unrelated\|Old transcript' "$C/out" && fail "an unmatched or old entry printed"
python3 "$wa" changelog fake --root "$C" </dev/null >/dev/null 2>&1; [ $? -eq 2 ] || fail "an empty fetch did not refuse"
python3 "$wa" changelog fake --root "$C" < "$C/log.md" | grep -q '1.3.0 to 1.3.0' || fail "an empty fetch moved the read mark"
sed -i.bak 's/"terms": \[.*\]/"terms": []/' "$C/.claude/w.json"
python3 "$wa" check --root "$C" 2>/dev/null | grep -q 'needs a `url`' || fail "check passed a changelog with no terms"
ok "workarounds changelogs: reads past the mark, filtered to the terms; a first read sets a baseline; an empty fetch moves nothing"

# ---- workarounds.py: reading an older copy has not moved the tool
D="$tmp/down"; mkdir -p "$D/.claude"; git init -q "$D"
echo '{ "workaroundsPath": ".claude/w.json" }' > "$D/.claude/threads.json"
: > "$D/x.md"
cat > "$D/.claude/w.json" <<'EOF'
{ "tools": { "fake": "echo 1.0" }, "workarounds": [
  { "id": "r", "tool": "fake", "observed": "2.0.0", "probe": null, "retest": "by hand", "sites": ["x.md"] },
  { "id": "u", "tool": "fake", "observed": "unverified", "probe": null, "retest": "by hand", "sites": ["x.md"] } ] }
EOF
printf 'fake\t1.9.0\n' | python3 "$wa" due --root "$D" >/dev/null
python3 "$wa" status --root "$D" | grep -q $'^due\tr' && fail "an older version re-opened a re-test observed above it"
python3 "$wa" status --root "$D" | grep -q $'^due\tu' || fail "an unverified premise is not due"
printf 'fake\t2.1.0\n' | python3 "$wa" due --root "$D" >/dev/null
python3 "$wa" status --root "$D" | grep -q $'^due\tr' || fail "a newer version did not make the re-test due"
python3 "$wa" record r 0 --root "$D" 2>/dev/null; printf 'fake\t2.0.5\n' | python3 "$wa" due --root "$D" >/dev/null
python3 "$wa" status --root "$D" | grep -q $'^due\tr' && fail "an older version re-opened an answered re-test"
ok "workarounds: a version below an answer is that answer; an unverified premise stays due"

# ---- adherence.py: a rule with no block reads the hit's own comment leader
python3 - "$here/scripts/adherence.py" <<'EOF' || fail "adherence default block is not per language"
import importlib.util, sys
spec = importlib.util.spec_from_file_location("ad", sys.argv[1]); ad = importlib.util.module_from_spec(spec); spec.loader.exec_module(ad)
assert ad.default_block("a.py").search("  # note") and not ad.default_block("a.py").search("// x")
assert ad.default_block("a.swift").search("/// note") and not ad.default_block("a.swift").search("#if x")
EOF
ok "adherence: a rule with no block reads the hit's own comment leader"

# ---- retro-log.py view: an Escaped: line reads as written, with or without its own "to"
cat > "$tmp/esc.md" <<'EOF'
## Entries

drift/with-to
  2026-11-01 | s | one.
    Escaped: to the maintainer — cost
drift/without-to
  2026-11-01 | s | one.
    Escaped: the default branch — cost
drift/to-do
  2026-11-01 | s | one.
    Escaped: to-do list — cost
drift/only-to
  2026-11-01 | s | one.
    Escaped: to — cost
EOF
python3 "$rl" view --reached --root "$tmp" --log esc.md > "$tmp/esc.out" 2>/dev/null || fail "view --reached failed on an Escaped: fixture"
grep -q 'drift/with-to .*escaped to to ' "$tmp/esc.out" && fail "view doubled a leading to"
grep -q 'drift/with-to .*escaped to the maintainer' "$tmp/esc.out" || fail "view lost an Escaped: destination that starts with to"
grep -q 'drift/without-to .*escaped to the default branch' "$tmp/esc.out" || fail "view lost an Escaped: destination"
grep -q 'drift/to-do .*escaped to to-do list' "$tmp/esc.out" || fail "view cut a word that only starts with to"
grep -q 'drift/only-to .*escaped to to$' "$tmp/esc.out" || fail "view read an Escaped: cost as its destination"
ok "retro-log: view reads an Escaped: destination once, whether or not it opens with to"
echo "all cases passed"
