---
description: Retrospective pass — review the work in this conversation as process telemetry (drift, scope leak, ignored user signals, unverified claims, premature lock-in, mode confusion, stale habits). By default a fresh-context sub-agent audits the observable session record cold; a second one places the findings against this repo's process docs and keys them against the retro log, so a recurrence is detected rather than assumed. Findings are captured to that log for `/threads:process-review` to adjudicate, not applied here — except a defect the audit finds in an artifact this session itself wrote or landed, which the retro fixes while the context that can fix it cheaply still exists. `quick` skips the audit, not the placement. Explicit-only; never auto-fires.
argument-hint: "[quick] [optional scope note]"
allowed-tools: Bash, Read, Grep, Glob, Agent
---

# /threads:retro — retrospective pass

Review the work in **this conversation** as process telemetry: *how* it happened, not
whether the code is correct.

**Args (`$ARGUMENTS`):**
- no args → self-pass (§1) + fresh-context audit (§2).
- leading `quick` → skip §2's audit. The self-pass still runs, and its findings are
  still placed (§3) and captured (§4a) — `quick` is not "no sub-agents."
- remaining text → optional **scope note** narrowing focus (e.g. `/threads:retro the
  dedup decision`, `/threads:retro quick this planning thread`). Default scope is the
  full session.

## 1. Self-pass (always)

Reflect on the in-scope work against these prompts:

1. Did anything surface that the plan / framing didn't anticipate?
2. Were the called-out risks (if any) borne out — and were they actually tested?
3. Repeated-trap candidate not yet recorded in this repo's process docs?
4. Did any rule prove stale, conflicting, or missing during the work?
5. Are any repo docs conflicting or confusing? Surface it — don't silently absorb it.

## 2. Fresh-context audit (skipped only with `quick`)

Hand the observable session record to a fresh sub-agent that did not do the work, so
it judges cold without the original context's anchoring.

**Step 2a — extract the record.** Run the bundled extractor; it resolves this
session's transcript, distills it to a compact `asked → did → said` timeline, and
prints the path:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/extract-record.py"
```

**If it fails, surface why — then fall back to the self-pass; never hard-fail or
fabricate a record.** Don't degrade silently: tell the user (a) what failed, (b) the
fix, (c) that detection is falling back to the self-pass — placement (§3) still runs.
Read the command's stderr and match:
- **`python3: command not found`** (or similar) → Python 3 isn't installed / on
  `PATH`, and the audit needs it. Suggest installing Python 3 (on Windows the
  interpreter may be `python` or `py`), or using `/threads:retro quick` to skip the
  audit deliberately.
- **`CLAUDE_CODE_SESSION_ID is not set`** → this client didn't expose the session id,
  so the transcript can't be auto-located. Note they can pass a transcript path to the
  script directly if they know it.
- **`no transcript found … set CLAUDE_CONFIG_DIR`** → their Claude data dir is
  non-default; suggest setting `CLAUDE_CONFIG_DIR`.

Likewise, if the `Agent` tool or the `retro-auditor` agent isn't available (Step 2b),
fall back the same way.

**Step 2b — spawn the sub-agent.** Use the `Agent` tool with the `retro-auditor` agent
(this plugin's read-only auditor; `subagent_type: threads:retro-auditor`). Its brief
lives in the agent definition — pass it only the printed record path, e.g. *"Audit the
observable session record at `<RECORD>`."* If the session was clean it should return
*"nothing material"* — do not pressure it for findings.

**Step 2c — reconcile, don't concatenate.** Two sets arrive; the user gets one list.
Fold them yourself — presenting both raw offloads your job onto the reader.

Tag each surviving finding by source: `[both]` when the self-pass and the audit found it
independently, else `[self]` or `[audit]`. Carry the tag through §4 — one word of reading
cost, and over runs it's the only record of whether the audit earns its spawn.

**Rank `[both]` first.** Independent corroboration from an anchored and an unanchored
reader is the strongest signal available here.

**You don't get to overrule the cold read on your own work.** Where the audit flags
something the self-pass cleared, that disagreement *is* the finding: carry it as
`[disputed]` with both readings and let the user settle it. Dropping it because you
already considered it is precisely the anchoring the audit exists to catch.

## 3. Placement (whenever there's a punch list)

A finding says *what* was learned. Where it lands is a separate judgment that requires
reading the target doc — and this context, having done the work, is the worst-placed one
to pay for that. Hand it off.

Spawn `finding-placer` (`subagent_type: threads:finding-placer`) **once, with all surviving
findings** — batched, not per-finding, so it can catch two findings that are one lesson.
When `placerModel` is set in `.claude/threads.json`, pass it as the spawn's `model` and say
so in one line; if the harness refuses that model, say so and spawn again without it.
Pass each as **issue → evidence → cost → suggested fix**, plus your **adopt now / adopt
if it recurs** call. That call needs the session, so it starts with you — but pass it as
*provisional*: step 3b can settle it with evidence you don't have.

**Hand it the map.** Name the candidate process docs — `processDocs` from
`.claude/threads.json` when it's there, else the homes this session's work already went
past. Rediscovering the repo cold is the placer's single largest cost, and you're not
cold. It still reads what it places against; it just shouldn't hunt for it.

**Hand it the key list too.** Run
`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/retro-log.py view --keys` — one line per key with
its occurrence count and state, derived from `retroLogPath` in `.claude/threads.json` —
and pass that output with the brief. A warning on its stderr names a line the grammar
cannot read; the view still renders, and the line is the adopter's to repair (the
`guards` `retro-log` check says where) — never yours, and never in this session. The log
itself is not a process doc and nothing is ever *placed* there; the placer matches
against the list and greps the log only for a hit's detail.

### 3b. Keys and recurrence — what comes back

The placer returns, per finding, a **key**: one short, greppable, domain-free line naming
the finding's *shape*, with the slice's own nouns left in the evidence where they belong.
It writes the key rather than you, for the same reason it does placement — you are soaked
in this session's domain and are the worst-placed context to abstract away from it, and it
has just read the existing keys, so its phrasing lands in the corpus's register instead of
drifting off on its own.

It also reports whether that key **already exists in the log**. Act on that:

- **Key already present → the condition named by *adopt-if-it-recurs* has now been
  observed.** Promote the finding to *adopt now* and cite the prior entries as the
  evidence. This is why the log is read before the call and not only written after it:
  the disposition is settled by observation rather than left open.
- **No match → leave the call as it stands.** The placer is told to prefer no-match when
  unsure, because a miss costs one more window while a false match lands a rule nobody
  needed. Don't second-guess a no-match into a match.

A reported match is a **fact**, not the placer overruling you — it never touches the
disposition itself. You revise your own call on new evidence.

Retro runs often, so the placer is deliberately speed-biased: it places against the homes
you name, and flags `add (unconsolidated)` rather than proving no home exists anywhere.
Carry that flag into the output — `/threads:process-review` is where those reconcile
across sessions. An add that should have been an amend is recoverable there; a retro too
slow to run isn't.

Skip only when there's nothing to place. If the agent or the `Agent` tool is
unavailable, place and key them here but **narrate the tier** — say the placements were
made in the context that did the work, so the amend-before-add bar went unpaid, and mark
the keys **`key (uncold)`**. You are the context least able to write a domain-free key,
so assume yours carry this session's nouns; the flag is what tells
`/threads:process-review` to re-key them rather than read their never-matching as
evidence of a one-off. Grep the log yourself before minting one — a match you can find is
still worth finding.

## 4. Output

Two outcomes, **both first-class**:

- **"No retro changes recommended."** Correct for clean work — do not invent findings
  because the command ran. State it and stop.
- **A punch list** of candidate doc / pattern / trap / guardrail / agent-guidance
  edits, **in-thread**, and **captured to the retro log** (§4a) rather than applied. The
  one exception is a defect in an artifact this session produced (§4b): that is fixed,
  logged in its entry, and leads the list. If a process proposal is large enough that
  diffs aid review, present the *what* first, then the staged *how* on approval; a §4b
  fix is not size-gated.

Each finding: **`[source]` `key` issue → evidence (cite the event) → cost → placement**,
where placement is `finding-placer`'s proposal — target section, the existing text it was
judged against, and the edit. **Cost is what was spent**, in the unit it was spent in — a
gate run, a round trip, a wrong artifact on the default branch, a reversed decision,
minutes — and *nil* is a valid answer: the capture bar (§4a) reads it. Any rejected alternative and any `add (unconsolidated)` flag
ride with it, as does any recurrence match from §3b. Under `quick` there's one source, so
every finding is `[self]` — tag them anyway; the format shouldn't change with the mode.

### Amend before you add

The bar lives in `finding-placer`'s brief — the context that can afford to apply it. Two
things stay here:

- Findings are candidates for a human to accept, reject, or refine — **never
  auto-adopted**, placement proposal included. Capturing one is not adopting it: the log
  entry changes no rule and takes no effect. A §4b fix adopts nothing either: it brings
  an artifact back to what the session had already decided.
- Bias toward *adopt-if-it-recurs* for one-off frictions; reserve *adopt now* for
  recurring or high-severity patterns. That's a session judgment: you have the session,
  the placer doesn't. §3b can promote the call on evidence; nothing demotes it.

## 4a. Capture — append to the retro log

**Capture is the default destination for a process finding, both dispositions.** This
is the largest context the session will have, so it is the most expensive point at which
to apply a process edit — one whose target doc has to be read cold — and an unread punch
list is a lost one. (A defect in this session's own artifact is the opposite case: the
context is what makes the fix cheap. That is §4b.) An append is cheap, always completes, and
survives the session; `/threads:process-review` adjudicates the log later, in the fresh
context that work requires.

**Capture has a bar.** A finding is appended when at least one holds:

- its **cost was spent** — something the session actually paid (a gate run, a round trip,
  a wrong artifact landed, a decision reversed), not a risk that did not materialize;
- it **matches a key already in the log** (§3b) — a recurrence is the log's whole product
  and is always written, whatever it cost this time;
- it is **severe or irreversible** on its face.

A nil-cost, unmatched finding — a friction noticed and measured before it cost anything, a
near miss a doc already covers — goes in the punch list under *below the bar* with the
reason, and is not appended; the user can say *append it*. Every single-occurrence key is
carried at read cost by every review until it recurs or is retired, so the bar is what
keeps the substrate readable: the dedup design is right, the volume feeding it is what the
bar limits. **A positive is never appended.** It stays in the report — a prevented error
shown as an observed correction is worth the reader's line — and nothing downstream reads
it: the review ranks by recurrence, and a `NOTED` key closes at write and counts nothing.
The grammar keeps `NOTED` for the entries already in adopters' logs; retro writes none.

Read `retroLogPath` from `.claude/threads.json` (default `.claude/threads-retro-log.md`).

- **Config present** → append every surviving finding **under the log's `## Entries`
  heading, ahead of any trailing section** — never a bare end-of-file append; a log that
  has grown a trailing section puts one outside the section that holds entries, where it
  still greps and no longer reads. Then **say what you appended and where**, in one line.
  Don't ask first — the user ran a retro, and capture is what it produces — and don't
  write silently either.
- **No config** → the cross-session loop isn't bootstrapped here, so there is nowhere to
  capture. Present the punch list and, in one line, mention `/threads:process-review` can
  set it up. **Don't create the config or the log yourself** — bootstrap belongs to that
  command.

**Append only. Never edit or remove an existing line.** The log is a stream that
concurrent sessions merge by union (the adopter sets `merge=union` on it in
`.gitattributes`), and union merge is only correct when nobody edits a line already
there. Every change of state is therefore itself an append, and the current state of a
key is derived from the stream — `scripts/retro-log.py view` derives it; the grammar is
that script's docstring (`--help` prints it), the log's header only points at it, and this
block is the copy that ships with the script:

```
<class>/<shape>[ (uncold)]                    key line, column 0
  YYYY-MM-DD | <source> | <text>              an occurrence; continuation lines below it
  LANDED <sha> — <where it landed>            status lines. Each is ONE physical line,
  FILED <ref> — <the stub carrying it>        however long — a wrapped one reads as
  NOTED <date> — <what worked and why>        continuation prose and the guard refuses it.
  HELD <date> — <proposal>                    LANDED: applied. FILED: live; a recurrence
                                              counts against the stub. NOTED: a record,
                                              closed at write, never counted — readable,
                                              no longer written (§4a). HELD: the review
                                              proposed, nobody approved; listed first
  ADJUDICATED <date> — <ruling>               the review's annotation on a key — a re-rank,
                                              a count-only ruling; changes neither state
                                              nor count. The review writes it; retro never
```

A long status line stays on one line, so a `LANDED` entry looks like this and never like
a paragraph:

```
scope-leak/edit-landed-without-exercising-the-sibling-path
  LANDED 9f60e91e — .claude/commands/land.md §4: the sibling carrier is amended in the same commit as the primary, and the commit names both; the second carrier was the one the rule kept missing.
```

- **A new finding** → key line + one occurrence line, continuations to **eight lines at
  most**: the cited moment, the cost, the placement (`Placement: file §section — amend
  "…"`). What does not fit goes where the placement points; the `guards`
  `retro-log-size` check holds the cap.
- **A finding whose artifact was fixed under §4b** → the ordinary key + occurrence, with
  one continuation line `Fixed: <artifact> — <sha>`. It counts against the eight, so
  compress the moment or the cost to make room — never the placement. No status line:
  the artifact is corrected, the lesson is still open, and a status line would close it.
  §4b runs before this append, so the sha exists when the line is written.
- **A recurrence** → the *same key* again + a new occurrence line. The occurrence count
  is the dated lines under a key, so an occurrence appended for any other reason reports
  a recurrence that never happened.
- **A finding the user applied in this session** (the escape hatch below) → the key +
  one `LANDED <sha> — <where>` line, one physical line and nothing else; the narrative is
  in the commit.

**Every append is a whole entry that begins with a key line.** Never add continuation
lines to an entry already in the file, even the last one: a union merge orders one
side's lines after the other's, so continuation lines appended on a branch land under
whatever block another session appended on the default branch, silently. A union merge
also runs no pre-commit hook, so the adopter's landing step runs the `guards` checks on
the merged tree before the push; that is where a merged stream is judged.

Compaction, re-keying, and retirement belong to `/threads:process-review`, which is
single-session by requirement. Carry any `key (uncold)` flag from §3 into the key line.

### The escape hatch — landing straight from retro

If the user accepts findings **and explicitly asks you to apply them now**, do it; the
cost is theirs to spend. The edit is already specified (§3): **apply it, don't re-derive
it.** If applying reveals the placement was wrong, stop and say so;
don't quietly substitute a different edit. Then check `.claude/threads.json`:

- `retroTelemetry: true` → land each applied process change as its own commit matching
  the config's `markerPattern` (default `docs(process/<scope>): <subject>`), never folded
  into unrelated work. That commit stream is the *landed* half of what
  `/threads:process-review` reads.
- `retroTelemetry: false` → don't mark; respect the recorded answer and don't re-ask.
- Config exists but the field is unset → offer **once** ("want this landed as a
  `<marker>` commit? That's what feeds `/threads:process-review`") and record either
  answer in the config.

Then record the landing in the log as §4a says: the key + one `LANDED <sha> — <where>`
line appended under it, never an edit to the entry already there, and never a second
occurrence line. Under `retroTelemetry: false` the user declined the marker commit; the
status line still goes in, pointing at whatever commit carried the edit.

## 4b. A defect in this session's own artifact — fix it, then capture the lesson

Sometimes the audit's evidence is not a moment in the record but a **file:line in
something this session wrote or landed**: a stub whose exit evidence contradicts itself,
a hedge the user voiced transcribed as a decision taken, a fix named mid-session that
reached no stub. That is two deliverables, and capture is the lane for only one of them.
The **process lesson** (the shape that let it happen) is a finding: key it, place it,
capture it under §4a as usual. The **artifact** is wrong now, on a branch or on the
default branch, and a wrong artifact is the next reader's premise. This session holds the
whole measurement; a fresh one re-derives it. The §4a cost argument runs the other way.

Fix the artifact in the retro when all three hold:

- **Provenance, per statement** — the defective lines are this session's: written in
  this session's commits or working-tree edits, and untouched since by anyone else
  (`git blame` on the lines, or a diff against the session's commit). Having changed the
  file elsewhere is not provenance over a defect in it, and a file another author has
  since rewritten is theirs. A file an open branch or PR moves, deletes, or rewrites is
  also theirs: a finding here, and a note to whoever owns that motion, never a fix.
- **No open decision of the user's** — the edit follows from the finding's evidence and
  needs no call the user has not made. A choice that belongs to the artifact's next
  reader (a drafter, a slice) is *recorded* in the artifact as a choice with its owner,
  which is a specified edit; only a choice that is the user's makes the defect one to
  present instead of fix.
- **Same gate** — whatever checked the artifact when it landed (the adopter's landing
  step, the `guards` run) can check the fix the same way. "Fix it" means the artifact the
  finding cites, never the source it describes; a source edit fails this gate in an
  adopter whose docs lane rejects source, and correctly.

Then **say what you are about to fix and where, one line per artifact, and fix it.** Don't
ask — the edit is specified by the finding and this is its cheapest moment; don't do it
silently either. If the original is not yet committed, the fix rides in the working tree
with it. If it landed, land the fix through the lane the fix itself qualifies for — a
docs-only fix takes the docs lane even when the original went through a code PR — as one
commit naming the artifacts. That commit is not a process change and takes no
`markerPattern` marker; the log append goes wherever the adopter's capture normally goes.

Log the fix **inside the lesson's occurrence, never as a status line**: the finding is
keyed and captured under §4a like any other, and one of its continuation lines reads
`Fixed: <artifact> — <sha>`. A `LANDED` line would close the key, and the view would then
report a lesson as landed whose placement nobody applied. The artifact is corrected; the
lesson stays open until `/threads:process-review` lands or retires it.

**Order: fix and land first, append second.** §4a's append comes after this step, however
the sections are numbered, so the fix's sha exists when the line is written. Where there
is no sha — the append rides in the same commit as the fix, or the fix is still
uncommitted — write `Fixed: <artifact> — rides this capture`; the line is detail, and the
path alone still greps.

When any of the three fails, the defect still **leads the punch list**, as a defect with
the edit specified — it outranks a process finding because it is live.

## 5. Ripeness nudge — one line, at the end

The log has just grown, and at closeout *opening a new thread* is an available next move.
Read `.claude/threads.json`; skip this step entirely if there's no config, no `markTag`
tag, or nothing accrued.

Measure — three commands, all local:

- **Pending** — key lines appended to the retro log since the mark. The mark is the
  adjudication boundary `/threads:process-review` advances, so it is the one thing both
  commands share, and pending is derived from it and nothing else:
  `git diff <markTag> -- <retroLogPath> | grep -cE '^\+[a-z][a-z0-9-]*/'`, against the
  working tree so this run's own appends count. Oldest: the date on the first such line.
  **Never count the whole file** — a whole-file count is the lifetime total, and reporting
  it as pending calls a clean review a backlog.
- **Recurred since the mark** — `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/retro-log.py view
  --keys --recurred --since <the mark's date>` (`git log -1 --format=%ad --date=short
  <markTag>`). A key at two or more occurrences, or back after its rule landed, is what
  opens the review's depth gate.
- **Volume and concentration** — `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/marker-stream.py
  files`: the **organic** markers since the mark and how many files `trigger.concentration`
  or more of them touched. The review's own landings (the `Process-Review:` trailer) and
  commits that touched only the log and the ledger are classified out — counting them is
  how a review comes out ripe on its own output the next morning.

**Ripe** means one of: a key recurred since the mark; organic markers at or above
`trigger.n`; a file at or above `trigger.concentration`. Pending captures alone are not
ripe — they are the substrate waiting to recur, and a review run on volume pays for the
funnel to learn that nothing recurred. Say something only when pending is non-zero or a
bar is met; when neither holds, say nothing — the review is current, and a nudge with
nothing behind it is the same failure as one nobody heard. Then **one sentence, naming
ripe or not ripe and teasing the finding rather than the count**, and telling this
session's appends apart from older unreviewed ones — *"six findings are pending, all from
this session, none recurred: not ripe"* is a different report from *"nine findings are
pending, one key recurred since the last review, and one doc has churned across four
organic process commits,"* and only the second is a backlog.

**Point at a fresh thread, and never offer to run it here.** `/threads:process-review`
requires a context that did not do the work under review, and this one just did. Say they
may want to open a new session for it and leave the decision with them.

Nothing is stored: ripeness is recomputed from the mark and the log every time, with no
sentinel and no anti-nag state. Retro is explicit and comparatively rare, so a ripe
backlog earns a sentence on each run.

## Anti-patterns

- **Reviewing the feature work instead of the process.** A bug in the code under
  review is captured elsewhere — don't pivot the retro. A defect in an artifact this
  session itself produced is §4b, not a pivot.
- **Inventing findings on clean work.** "No changes recommended" is the goal-state.
- **Claiming to have caught internal reasoning.** You only see the observable record.
- **Auto-adopting findings**, or **adding a new rule when an existing one could absorb
  the lesson.** Amend first; let the human promote.
- **Concatenating the two finding sets** and leaving the user to reconcile them.
- **Placing findings in this context** when the placer was available.
- **Editing or removing an existing log line.** Union merge is why; a state change is an
  appended status line, a repeat is an appended occurrence, and nothing else reuses a key.
- **Capturing silently.** Say what was appended and where — a write nobody was told about
  is the same failure as a nudge nobody heard.
- **Pointing at a defect in your own artifact and offering to fix it.** "Say the word"
  costs the user a turn to buy an edit this session already has; §4b names it and fixes
  it.
- **Applying process edits because the findings look good.** Capture is the default for
  a process finding; a rule lands from retro only when the user asks (the escape hatch).
  The §4b own-artifact fix is the one edit the retro applies unasked, and it names the
  fix first.
- **Offering to run `/threads:process-review` in this session.** It requires a context
  that didn't do the work, and this one did.
- **Vague findings** with no cited moment, and **only fault-finding** — report what
  worked, too; it is reported, never appended.
- **Appending below the bar.** A nil-cost finding that matches nothing is a line in the
  report, not a key the next review carries; a positive is never a key at all.
- **Calling a review ripe on pending captures**, or on a marker count that includes the
  last review's own landings — ripe is a recurrence since the mark or an organic bar.
