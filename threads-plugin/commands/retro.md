---
description: Retrospective pass — review the work in this conversation as process telemetry (drift, scope leak, ignored user signals, unverified claims, premature lock-in, mode confusion, stale habits). By default a fresh-context sub-agent audits the observable session record cold; a second one places the findings against this repo's process docs and keys them against the retro log, so a recurrence is detected rather than assumed. Findings are captured to that log for `/threads:process-review` to adjudicate, not applied here. `quick` skips the audit, not the placement. Explicit-only; never auto-fires.
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
Pass each as **issue → evidence → cost → suggested fix**, plus your **adopt now / adopt
if it recurs** call. That call needs the session, so it starts with you — but pass it as
*provisional*: step 3b can settle it with evidence you don't have.

**Hand it the map.** Name the candidate process docs — `processDocs` from
`.claude/threads.json` when it's there, else the homes this session's work already went
past. Rediscovering the repo cold is the placer's single largest cost, and you're not
cold. It still reads what it places against; it just shouldn't hunt for it.

**Name the retro log too** — `retroLogPath` from `.claude/threads.json` (default
`.claude/threads-retro-log.md`). It is not a process doc and nothing is ever *placed*
there; the placer reads it to key the findings, per below.

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
  edits, **in-thread**, and **captured to the retro log** (§4a) rather than applied. If a
  proposal is large enough that diffs aid review, present the *what* first, then the
  staged *how* on approval.

Each finding: **`[source]` `key` issue → evidence (cite the event) → cost → placement**,
where placement is `finding-placer`'s proposal — target section, the existing text it was
judged against, and the edit. Any rejected alternative and any `add (unconsolidated)` flag
ride with it, as does any recurrence match from §3b. Under `quick` there's one source, so
every finding is `[self]` — tag them anyway; the format shouldn't change with the mode.

### Amend before you add

The bar lives in `finding-placer`'s brief — the context that can afford to apply it. Two
things stay here:

- Findings are candidates for a human to accept, reject, or refine — **never
  auto-adopted**, placement proposal included. Capturing one is not adopting it: the log
  entry changes no rule and takes no effect.
- Bias toward *adopt-if-it-recurs* for one-off frictions; reserve *adopt now* for
  recurring or high-severity patterns. That's a session judgment: you have the session,
  the placer doesn't. §3b can promote the call on evidence; nothing demotes it.

## 4a. Capture — append to the retro log

**Capture is the default destination for every finding, both dispositions.** This is the
largest context the session will have, so it is the most expensive point at which to apply
an edit, and an unread punch list is a lost one. An append is cheap, always completes, and
survives the session; `/threads:process-review` adjudicates the log later, in the fresh
context that work requires.

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

**Append only. Never edit or remove an existing entry, ever** — not to mark one landed,
not to tidy, not to collapse a duplicate. Parallel slices mean concurrent retros against
one repo, and two sessions rewriting the log at once silently drop each other's work.
Recurrence — and *only* recurrence — is recorded by appending a *new* entry that reuses
the *same key*, so a repeat never requires touching what's already there. That key line is
the occurrence count `/threads:process-review` reads as evidence, so a same-key append
made for any other reason reports a recurrence that never happened. Compaction,
retirement, and re-keying all belong to `/threads:process-review`, which is single-session
by requirement and holds the write tools for it.

Each entry: the key line, greppable and on its own, with the detail indented beneath it.
Follow the shape of entries already in the log; if it's empty, its header states the
contract. Carry any `key (uncold)` flag from §3 into the entry.

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

The log entry stays exactly as §4a appended it. The landing is recorded by the `<marker>`
commit, and `/threads:process-review` is what later collapses a landed entry to a pointer
at it — never a second entry under the same key, which that review counts as a recurrence,
and never an edit to the one already there. Under `retroTelemetry: false` the user
declined the marker commit, so the landing is untracked by their own choice; don't
improvise a substitute in the log.

## 5. Ripeness nudge — one line, at the end

The log has just grown, and at closeout *opening a new thread* is an available next move.
Read `.claude/threads.json`; skip this step entirely if there's no config, no `markTag`
tag, or nothing accrued.

Measure — cheap, all local git plus one file read:

- **Pending** — entries in the retro log, and roughly how old the oldest is.
- **Volume** — marker commits since the mark: `git log <markTag>..HEAD --format='%s%x09%h'
  | grep '<markerPattern>'`, subject-first so the anchored pattern tests the subject.
- **Concentration** — any file touched by `trigger.concentration` or more of those
  commits.

Say something only when pending entries exist, or a `trigger` bar is met. Then **one
sentence, teasing the finding rather than the count** — *"nine findings are pending, the
oldest about six weeks, and one doc has churned across four process commits since the last
review."*

**Point at a fresh thread, and never offer to run it here.** `/threads:process-review`
requires a context that did not do the work under review, and this one just did. Say they
may want to open a new session for it and leave the decision with them.

Nothing is stored: ripeness is recomputed from the mark and the log every time, with no
sentinel and no anti-nag state. Retro is explicit and comparatively rare, so a ripe
backlog earns a sentence on each run.

## Anti-patterns

- **Reviewing the code instead of the process.** If you spot a bug, capture it
  elsewhere — don't pivot the retro.
- **Inventing findings on clean work.** "No changes recommended" is the goal-state.
- **Claiming to have caught internal reasoning.** You only see the observable record.
- **Auto-adopting findings**, or **adding a new rule when an existing one could absorb
  the lesson.** Amend first; let the human promote.
- **Concatenating the two finding sets** and leaving the user to reconcile them.
- **Placing findings in this context** when the placer was available.
- **Editing or removing an existing log entry**, or reusing a key for anything but a
  recurrence. Append-only has no exceptions; a concurrent retro is why, and the key line
  is a counter.
- **Capturing silently.** Say what was appended and where — a write nobody was told about
  is the same failure as a nudge nobody heard.
- **Applying edits because the findings look good.** Capture is the default; landing now
  happens only when the user asks for it.
- **Offering to run `/threads:process-review` in this session.** It requires a context
  that didn't do the work, and this one did.
- **Vague findings** with no cited moment, and **only fault-finding** — record what
  worked, too.
