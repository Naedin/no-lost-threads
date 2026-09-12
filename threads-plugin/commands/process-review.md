---
description: Cross-session process review — reads accumulated process-change commits (and, as a fallback, process-doc churn) across sessions to surface reconciliation / structural opportunities the per-session retro structurally can't see, and sweeps stable process/workflow docs for negative-space drift the churn signal can't. First run bootstraps read-only; never auto-fires.
argument-hint: "(no args; bootstraps on first run, else reviews since the process-review-mark tag)"
allowed-tools: Bash, Read, Grep, Glob, Write, Edit, Agent
---

# /threads:process-review — the cross-session process review

The second altitude of the threads family. `/threads:retro` reviews **one session**;
this reviews **across sessions** — the accumulated process changes — hunting patterns no
single session can see: several over-specific local rules that should reconcile into one
structural change, or a larger move to process / repo layout / tooling that no single
slice surfaces.

It reads two streams produced by the repo's own work. **Process-shaped commits** (a
change to *how we work* — a rule, trap, template, command behavior, workflow — not status
flips, feature code, or product edits) are what has **landed**. The **retro log** is what
is **pending**: every finding `/threads:retro` captured and no review has adjudicated yet.
Retro captures; this command lands. That split exists because retro fires at maximum
context — the most expensive moment in a session to apply an edit — while this command
runs fresh by requirement and is the only one that can tell one friction from three of the
same shape.

**Fresh context required.** Like every retro, this can't run anchored to the work it
reviews. Run it in a session that did not do the work under review.

**Nothing silent.** First run is read-only. Writing is gated on recorded consent
(`applyMode`), never inferred per-run. Every run states which tier it ran at and what the
next tier up would buy.

## Config — the single source

The convention lives in `.claude/threads.json` (create on bootstrap; recommend
committing it — conventions are team-visible). Both commands read it; never re-derive a
convention in the moment. Fields:

- `markerPattern` — anchored (BRE) pattern matching a process commit's **subject**. Default
  `^docs(process`. Match subjects only, never whole messages — a commit that merely quotes
  a marker line in its body must not count. Character classes cover real conventions —
  e.g. `^[a-z(]*process[:/)]` spans `docs(process/…`, `process: …` squash subjects, and
  `chore(process): …`. Avoid `\|` alternation — it's a GNU extension in BRE and won't
  travel; character classes are enough. **Editing this field later re-runs the proof**
  (bootstrap step 3).
- `processDocs` — paths that count as process docs (the churn fallback + silent-death
  check read these).
- `workflowDocs` — optional: files that describe one workflow and are expected to
  co-evolve (e.g. a command pipeline). Absent → detected command directories
  (`.claude/commands/` and the like), each directory treated as one set.
- `trigger` — `{ "n": 10, "concentration": 3 }`: the volume backstop and the
  distinct-commit re-touch bar, both over **organic** markers — the ones no review landed
  and that changed something beyond the log and the ledger (Telemetry, below). Read by
  `/threads:retro` for its closing ripeness nudge, which calls a review *ripe* on a key
  recurred since the mark, or on either bar, and never on pending captures alone.
- `applyMode` — `read-only` | `apply-on-approval` | `apply-mechanical`. Starts
  `read-only`. Once the user has approved candidates in two or more reviews, offer **once**
  to ratchet to `apply-on-approval`; once they have approved the mechanical line as a batch
  in two or more reviews, offer **once** to ratchet to `apply-mechanical`, under which a run
  the maintainer is not answering lands the `trim` and `amend` candidates itself and holds
  every other class. The offer says what it ratchets into: the candidates that pass the
  tier's guards (Output) — in a repo whose `invariantDocs` covers most of its process docs,
  that is the command docs and templates, and the offer names them. Record either answer
  here and don't re-ask. The consent is the recorded value, never a run's reading of the
  room; the ladder only goes up by an answer.
- `retroTelemetry` — `true` | `false`: whether a finding landed **straight from a retro**
  (its escape hatch, used only when the user asks to apply on the spot) gets a
  `markerPattern` commit. Unset → retro offers once at its next such moment and records
  the answer here. It has nothing to say about retro's default capture path, which writes
  no commits.
- `ledgerPath` — deferral ledger: what a *review* declined, plus the signal that would
  promote it. Default `.claude/threads-review-ledger.md`.
- `retroLogPath` — retro log: what *sessions* captured and no review has adjudicated yet.
  Default `.claude/threads-retro-log.md`. An append-only stream `/threads:retro` writes;
  `scripts/retro-log.py view` derives each key's state and count from it, and this command
  is its only mutator, through `scripts/retro-log.py compact` and re-keying.
- `invariantDocs` — optional, **ordered** (highest authority first): **the core** — the
  docs that state the repo's authority order and this review's own contract (its
  conventions, its extensions). Read whole at step 0a, every run, before any commit, so
  it is short by construction: a doc belongs here only if it outranks the commit stream
  on *every* run. A domain doc — a traps catalogue, a UI guideline, a testing strategy —
  is not core however true it is: it is read at step 6 when a finding names it (a
  **keyed read**, derived per run from the findings themselves), and the placer reads it
  again for the edit; listing it here reads it once for nothing. Absent → the review has
  no input above the commit stream and says so.
- `capabilityEvidencePath` — optional: a log of findings about *capabilities* — contracts
  and rungs rather than doc sections. Only relevant where the repo builds tooling it also
  uses. It is the one input that can yield a non-doc proposal; without it the funnel is
  doc-churn-shaped end to end. Written by this command alone — no other step in the system
  appends here. Absent → narrate and skip, except in a repo that builds tooling it also
  uses (a `scripts/` dir, hook scripts, checks, a plugin directory), where the narration is
  a question the review asks **once**: set the path, or record `null` here to decline, and
  the question is not asked again. Unset in such a repo, the review's only non-doc input is
  missing and every upstream-bound finding has no store.
- `placerModel` — optional: the model the `finding-placer` spawn runs under, a harness
  short name passed through as given. Absent, the agent file's own pin applies.
- `markTag` — default `process-review-mark`.

**The two files are separate on purpose.** The ledger holds decisions *not* to act and is
read late, as a suppressor. The retro log holds findings already judged worth acting on
and not yet landed — the highest-signal material in a window, read first. One file would
serve two opposite jobs from one read position.

If `.claude/threads.json` is absent, you are in **bootstrap** (below). If present but a
field is missing, use the default above and note it.

## Telemetry — three kinds of marker, one of them counted

A marker commit is one whose subject matches `markerPattern`. Three kinds share the
spelling, and only the first is telemetry:

- **organic** — a process change no review has adjudicated: the retro's escape hatch, a
  rule landed by hand, a slice's process commit. The trigger, step 1's ranking, and the
  tally's headline read these.
- **review** — a commit this command landed: a candidate, its `LANDED` lines, a
  compaction, the ledger rewrite, the mark. **Every commit this command makes carries the
  trailer `Process-Review: <today's date>`** (`git commit --trailer 'Process-Review:
  <date>'`; `land-process-commit.py` preserves it through the cherry-pick). Already
  adjudicated: its sha is a `LANDED` ref, never churn. A review that counts its own
  landings as the next window's churn is ripe on itself the next morning, and spends
  most of its read on what it wrote.
- **bookkeeping** — a commit touching nothing but `retroLogPath`, `ledgerPath`, or
  `capabilityEvidencePath`: a retro's capture, a status line. A status flip changed no
  rule, whatever its subject says.

`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/marker-stream.py count` prints the four numbers
for the window; `list` classifies each marker; `files` ranks the organic commits per file
and counts the files at `trigger.concentration`; `--all` is the tally; `--head
origin/<default>` reads the remote's branch. Every stream read below goes through it,
never a hand-rolled `git log | grep` — subject-first order, the trailer, and the path
test are three ways to get the number wrong by hand. **Until the mark passes the first
trailered landing**, commits the review landed before the trailer existed still read as
organic, so `files` ranks the last untrailered run's churn as if nobody had adjudicated
it; narrate that for the one or two windows it holds, and read those clusters against
the log's `LANDED` refs before ranking them.

## Bootstrap — first run (writes nothing until the user confirms the seed)

No config, **or** the `markTag` tag doesn't exist in the repo → bootstrap. Inspect,
then negotiate with the answers in hand; do not interview blind.

1. **Inspect** (all read-only):
   - Commit-subject style: `git log --format='%s' -50`. Is there an existing prefix
     convention (`docs(...)`, `chore(...)`, Conventional Commits, or plain imperative)?
   - **How changes reach the default branch** — direct commits, or squash-merged PRs
     (subjects ending `(#NN)`)? A squash rewrites branch-side subjects, so markers on
     branch commits die in the squash; the negotiated marker must match what actually
     lands on the default branch, which may be a second spelling.
   - Existing telemetry: does anything already match a plausible marker? Is there already
     a `process-review-mark` tag or a prior home-grown flow? (The **migration case** — a
     repo already running this convention must be *recognized and adopted as-is*, not
     re-converted.)
   - Where process lessons live: `CLAUDE.md`, `.claude/`, a patterns/traps doc, a failure
     catalog, a hooks dir. Glob/read to locate; don't assume a structure.
   - Workflow surface: command directories (`.claude/commands/` or similar) — these
     become the default workflow sets for the staleness sweep.
   - Enhancements present: `gh` on PATH + a GitHub remote? An agent memory store
     (`MEMORY.md`)?
   - Tooling the repo builds and uses: a `scripts/` dir, hook scripts, checks, a plugin
     directory. Present → `capabilityEvidencePath` has a job here, and step 4 asks for it.
2. **Report** what you detected, which inputs you'll use, and which fallback tiers apply.
3. **Negotiate the marker** — propose the default `docs(process/<scope>):`, *or* an
   adaptation fitting the repo's existing style (e.g. a `chore(...)` repo → offer
   `chore(process/...)`). Surface any collision with an existing convention **before**
   adopting. In a squash-lane repo, negotiate a pattern covering the merge-lane spelling
   too. Prefer character classes to `\|` alternation — `\|` is a GNU extension in BRE and
   won't travel. Then **prove it fires**: `marker-stream.py count --all --pattern
   '<the pattern exactly as it will be written to the config>'` against the history, and
   `list` to see one sample subject per lane classified. A marker that fails its own test
   is not adopted.
4. **Confirm `processDocs`** — the one thing inspection can't reliably answer. Ask. Where
   step 1 found tooling, ask for `capabilityEvidencePath` in the same breath: a path, or
   `null` to decline; either is recorded, and the review never asks again.
5. **Seed** (only after confirmation): write `.claude/threads.json`, then re-run the
   step-3 proof reading the pattern back out of the real file; create the retro log at
   `retroLogPath` with a header that **points at** the grammar and never copies it: *the
   grammar is the threads plugin's `retro-log.py` docstring; `python3
   <plugin>/scripts/retro-log.py --help` prints it* — then `## Entries` and nothing after
   them. A copy in the header is a second source nothing refreshes (`compact` keeps the
   header verbatim), so it reads as current while listing the tokens of a version ago;
   the appending agent reads the grammar from `/threads:retro`'s own text, released with
   the script. Propose `<retroLogPath> merge=union` for the repo's
   `.gitattributes`, which is what lets concurrent sessions append, together with a
   `guards` run on the merged tree in the repo's landing step, since a union merge runs
   no pre-commit hook; tag
   `git tag <markTag> HEAD`. Then run one normal pass so the first run delivers value.
   **Migration case:** a repo already keeping a hand-built recurrence log should have it
   adopted as `retroLogPath` if its entries can carry keys, not have a second one started
   beside it.

The all-time tally (below) doubles as the bootstrap demo: *"your repo already shows N
commits of process-doc churn — here's what this tool does with that."*

## The review — cheap → expensive (never read every diff)

**Pre-flight — one review at a time.** This command is the only mutator of the retro log
and the ledger and it advances a shared tag, and nothing else stops two reviews from running
at once. Before reading anything, `git fetch` and record the two facts a peer run would
move, **on the remote's default branch, never the local head**: `git rev-parse <markTag>`
and `git rev-parse origin/<default>:<retroLogPath>` — a peer lands on the default branch
while this checkout's head sits untouched, so a local read is unchanged in exactly the case
the check exists for. Where the harness exposes a session listing, look: a peer is
identified by its **working directory and branch**, never by a worktree name, which a later
session on another repo can carry — a review on this repo already in flight means stop and
say so. Then, **immediately before the first write** (a log append, the ledger edit,
`compact`, the tag), fetch and re-read both facts. Either moved → a peer landed while this
one ran: **re-derive, then write** — rebase onto `origin/<default>` (the log merges by
union; the ledger is a working file), run the `guards` gate on the rebased tree since a
rebase runs no pre-commit hook, re-read the view, then write. Refuse only on a rebase
conflict or a red gate; a run that has spent its budget is not thrown away for a clean
rebase.

0. **Free — the reads that size the run.** All three are cheap; none is optional where
   configured. Do them before looking at a single commit.

   **0a — the core** (`invariantDocs`, in order). Read them whole. You are about to
   propose changes to how this repo works, and its stated invariants outrank anything
   you will derive from a commit stream. **Name what you read in the output, and which
   of it bore on a ruling** — the economics block carries both numbers. Then read each
   one's **window as churn**: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/core-diff.py` (one
   line per doc — words at the mark and now, words added and removed, commits), and for
   each doc with a window, `core-diff.py diff <doc>`, each hunk classed **rule** (a
   predicate, a scope boundary, a named exception, a decision-relevant why) or **prose**
   (narration, a symbol enumeration, a restated why, a worked case restating a rule
   already present). A slice PR's squash lands a paragraph in a core doc and no marker
   names it; a doc read whole every run can still double unread. A core doc whose window
   is prose-only, or whose prose growth outruns its rule growth, is a **finding** under
   cull, beside the churn findings of step 4: its remedy is a trim, and a trim of an
   enforced doc lands only after a fresh-context read comparing old and new, handed both
   files and the exclusion list (wording, order, examples restating a present rule,
   symbols, generic rationale) and never the trimmer's account, reports zero moved
   predicates. **A core doc that bore on nothing is grounds to ask why — a doc twice its
   size bearing on nothing is the prose finding above — never grounds to leave the
   core**; only a doc that has stopped stating the repo's authority order or this
   review's contract leaves it. Every other doc this run opens is a **keyed read**
   (step 6): named by a finding, read at the moment it bears, never here. No
   `invariantDocs` → narrate and skip.

   **0b — the retro log** (`retroLogPath`). The only already-adjudicated findings in the
   window: a human accepted each one and a cold reader named its shape. Read it through
   the view's filters, never whole — the reads below are the run's reads, in order, and
   each is one tool result at any log size:
   - `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/retro-log.py view --keys --held` — the last
     run's unanswered proposals, each with the date it was held and its age in days. This
     run reports them before anything new, oldest first.
   - `view --keys --recurred` — every key at two or more occurrences, the promotion the
     log exists to make visible.
   - `view --keys --since <the mark's date>` — what this window touched; the re-key sweep
     reads these plus the `(uncold)` ones.
   - `view --key <key>` — one key's detail, for the keys the reads above surfaced.
   `view --keys` alone is every key on one line each and is the read for a small log; past
   a hundred keys it outgrows a tool result, and `view` with detail is the read to avoid at
   any size. The summary line counts the whole log whatever the filter.
   A warning on the view's stderr names a line the grammar cannot read: repair that line
   by hand first — you are the mutator — so `compact` does not refuse on it later.
   - **Re-key first, then count — in that order.** A key written at slice altitude cannot
     match anything, so counting before re-keying yields a number the re-key invalidates,
     after every ranking decision has already been made against it. Read every key as a
     set, rewrite the ones still carrying their session's nouns — a re-key edits the key
     line wherever it appears, the one edit the stream permits, and only this command
     makes it — then `compact`, *then* count from the view. Keys flagged `(uncold)` come
     first, but the sweep is over all of them.
   - **Count occurrences per key** from the view. A key with two or more occurrences is
     the promotion the log exists to make visible — rank those first and carry the count
     as the evidence.
   - **Retro's disposition tag is an input, not a verdict.** You hold the cross-session
     view, which is strictly better standing for ranking than the single session that set
     it — so re-rank freely, in either direction. Record the re-rank and the reason as an
     `ADJUDICATED <date> — <ruling>` line on the key — its own entry, the key line again
     above it — never as continuation prose inside an occurrence, which the grammar reads
     as the occurrence's own text, the size cap counts, and a status-only last block turns
     into an unknown status. An annotation changes neither the key's state nor its count,
     which is what lets a count-only ruling, a build trigger, or a withdrawn re-rank sit on
     the key without moving it. Never silently overwrite the original call.
   - **Empty log, or no `retroLogPath`** → narrate and skip, like any detected input.

   **0c — capability evidence** (`capabilityEvidencePath`), where the repo builds the
   tooling it uses. Entries here name a contract and a rung rather than a doc section, so
   they are the only input that can produce a non-doc proposal. Without it, every input in
   this funnel is doc-churn-shaped and the output can only ever be doc edits. Count keys
   the same way. Absent → narrate and skip; absent **and unset** (no `null` in the config)
   in a repo that builds tooling it uses → the narration is the once-only question in
   Config: ask for a path or a `null`, record the answer, and do not ask again. A store
   that stays unset for the life of an adopter is the funnel silently doc-shaped.

   **Then reconcile it against 0b, and carry the number.** A retro-log `Placement:` may
   name this store, and nothing but this command writes here — so a placement that names
   it has landed only if an entry for it exists. Grep 0b's placements for this path and
   check each against the keys you just counted. **The count of unresolved ones is a
   required field of the capability-candidates output**, including when it is zero. Report
   it as a fraction (landed / named). This is what makes the store's shortfall visible:
   0c's key counts look complete whether or not the placements arrived, so a review that
   reads only 0c reports a healthy log and a short one identically.

**The depth gate — decide the run's size here, before step 1.** Steps 1–7 are the
expensive path and they are *conditional*, not automatic:

- **Nothing recurred** in 0b or 0c (no key above one occurrence after re-keying), and no
  ledger signal fired → **stop and say so.** Report the pending captures, the tier, and
  the tally. A repo with no recurrence has bought the complete answer for the price of two
  greps; running the full funnel against it burns wall-clock and tokens to rediscover
  that. This is the expected outcome in a young or healthy repo, not a failed run.
- **Something recurred, or a ledger signal fired** → run the funnel, scoped to what fired.
- **A bare `deep` argument** overrides the gate: the maintainer asked for the sweep.

Measurement cost rises with repo size, so a fixed-depth funnel gets more expensive exactly
as its yield thins. The gate is what keeps the review affordable at scale.
1. **Free** — list the stream: `marker-stream.py list`, then `files` (Telemetry). **The
   organic markers are the stream**; the review's own landings and the bookkeeping
   commits are two counts in the narration and are never ranked — a cluster made of the
   last run's candidate landings is the review looking at itself. This stream is what
   **landed**; step 0 is what is **pending**. Tabulate the organic commits by scope (parse
   `<scope>` from each subject) and by file, counting **distinct commits** (re-touch
   across sessions is the signal, not raw line count).
   - **Fallback tier (no marker commits):** cluster churn on `processDocs` paths instead
     (`git log <markTag>..HEAD --name-only -- <processDocs>`, or full history on the very
     first run). Marker commits are the precise signal; path-churn is the coarse one.
     **Narrate that you're on the fallback and what the marker convention would buy.**
   - **Silent-death check:** marker hits == 0 while `processDocs` churn > 0 → surface
     "your telemetry convention may not be firing" (a narrated tier drop, not silent rot).
     Before concluding it's dead, rule out the measurement itself: `marker-stream.py
     count --all` is the lifetime count, and zero there against a pattern that once
     fired is a pattern edit, not a dead convention. Then check the merge lane: if that
     churn arrived via squash-merged PRs, the markers may be dying in the squash (see
     bootstrap), not missing — the fix is widening the pattern, not re-negotiating the
     convention. Zero marker hits is also simply *expected* in a
     repo whose retros all capture and never use the escape hatch — check step 0 before
     diagnosing anything.
2. **Free** — rank; only clusters above a re-touch bar survive.
3. **Cheap** — read the deferral ledger (`ledgerPath`); don't re-propose what's already
   deferred. The reverse motion is equally required: each entry names a promoting
   signal — check every live signal against this window and **adjudicate the ones that
   fired** (promote, retire, or re-defer with the reason). A deferral whose signal fires
   and sits is the ledger rotting in exactly the way it exists to prevent. (Detected
   upgrade: prior tracker issues, if `gh` + label exist.)
4. **Cheap, detected** — if a memory store is present, read it as a second input:
   commit-churn ∩ memory = high-confidence candidate. Absent → narrate and skip.
5. **Cheap — staleness sweep.** Churn is half the signal; the other failure mode
   generates no telemetry at all: a stable workflow quietly falling behind as the repo
   grows around it. Over `processDocs` ∪ workflow sets (`workflowDocs`, else the
   detected command directories):
   - **Stale-vs-growth** — per file, last substantive touch and commits since
     (`git log -1 --format=%H -- <path>`; `git rev-list --count <that>..HEAD`). Rank by
     growth-since-touch, never raw age: untouched-for-40-commits means nothing in a slow
     repo and a lot in one that just doubled.
   - **Sibling variance** — files in one workflow set describe one workflow and should
     co-evolve. One stage amended recently while its neighbors sat untouched through
     the same growth is drift evidence, with no knowledge of the workflow's semantics.
   - **Reachability** — is each process doc routed from anywhere (a trigger table, a
     command, a hook, another doc)? An orphan nothing points at is the silent-death
     class regardless of freshness.
   Only high-ratio or high-spread survivors advance — and on each survivor, check
   **referent existence** first (do the files, commands, and labels it names still
   exist?): a freshness-only pass on a doc full of dead referents logs "clean" and
   becomes evidence *against* urgency. No workflow surface detected and no
   `workflowDocs` → narrate and skip, like any detected input.
6. **Expensive — hot clusters and staleness survivors only.** **Keyed reads first**: the
   docs this run must open whole are the ones its own findings name, derived, never
   configured, and **bounded** — `retro-log.py view --recurred --since <the mark's date>
   --docs` (the docs the *recurred* keys' placements, landings, and stubs point at;
   never the whole since-mark set, which on a busy repo outweighs the core), each path
   resolved by basename against the `processDocs` trees — a placement writes
   `worktrees.md`, the doc is `Plans/active/worktrees.md` — and a path that resolves to no
   process doc dropped (the flag also returns scripts and stubs, which route a read and
   are not one), plus the docs a **fired** ledger signal names. Read each once, here,
   where a candidate is about to be reasoned against it; a doc named by nothing this run
   is not opened, whatever else the repo holds true. **A hot file from step 1 is never
   opened whole**: it is read as its churn diff (`git show`) or its blamed section; the
   placer is the only whole read of a target, and it reads it for the edit. The
   economics block carries the keyed set's size, so the bound is visible per run. Then
   `git show` the churn diffs; `git blame` the staleness survivors to locate their
   stalest sections,
   weighting load-bearing files (referenced by other process docs, or amended by past
   marker commits). Reason about reconcile-into-one-rule vs a structural process /
   repo / tooling move vs *leave — not yet ripe*. High bar: eagerly proposing grand
   restructures is worse than none. Entries a retro appended fast (`add
   (unconsolidated)`) are expected raw material here — that's the division of labor, not
   a defect to report.
7. **Placement** — for candidates that survive as reconcile-into-X or
   structural-change, the remaining question is *where X lives*, and by this point the
   session is no longer fresh: it has spent its budget on the funnel. Spawn
   `finding-placer` (`subagent_type: threads:finding-placer`) **once, with all
   surviving candidates** — pass each as pattern → evidence → proposal, with your
   ripeness call attached; it returns the target section, the existing text judged
   against, and the concrete edit. When `placerModel` is set, pass it as the spawn's
   `model` and say so; a refused model is narrated and the spawn retried without it.
   **Name the candidate docs**: `processDocs` plus the
   specific files this run surfaced as hot or stale. You already paid for that view, and
   rebuilding it is the placer's largest cost. If the agent or the `Agent` tool is
   unavailable, place here and narrate that the amend-before-add bar was applied by a
   depleted context.

## Output (in-thread; `applyMode` governs whether approved edits are applied)

**Two audiences, two shapes.** Everything from *Pending captures* down is the **record**:
pattern → evidence → proposal per candidate, complete enough that the next run and the
marker commit body can stand on it. The maintainer reads none of it to decide. What they
read is the **decision block**, which opens the output, and **nothing else sits above it** —
no evidence, no placements, no tier narration, no tally.

**Before a row is written, re-measure its premise against the default branch, now.** A
candidate can have landed since it was held, or gone moot on a decision the maintainer took
elsewhere; a row whose premise is stale spends the one attention budget the block exists to
protect. Re-measured and gone → `RETIRED` or `LANDED` in the log, not a row.

The block, in this order:

1. **The table** — one row per candidate that genuinely needs the maintainer: a trade-off, a
   product or policy call, a change hard to reverse. Four columns:
   - **Letter.**
   - **Decision** — one clause naming *the artifact and the motion* ("carve the pin protocol
     into its own routed doc", "retire the four-carrier landing rule"), never the retro key
     or the finding's pattern; the maintainer does not carry the key vocabulary between
     sessions.
   - **Recommend** — one word: approve, retire, split, or fold.
   - **Why** — one or two sentences, each resting on something *this run measured* (an
     occurrence count, a signal that fired, a landed commit, a filed/built ratio), with the
     reversibility stated when it bears. Never the candidate's rationale restated.
   A row without a recommendation hands the maintainer the review's own work; a row the
   maintainer cannot answer from the row alone belongs in the record instead.
2. **One sentence**: *Mechanical, land on your word:* followed by the letters.
3. **One line** naming what happens next if every row is answered as recommended.

Held candidates are rows or letters like any other, with their age from `view --held` in
the Why when it bears; the ageing detail goes in the record.

Every candidate carries a **class** so the block and the log can sort it without re-reading
it: `trim` (a net removal, or a cross-reference clause into existing text), `amend` (wording
inside an existing rule, a consolidation), `rule` (a new rule or bullet), `carve` (a new doc,
a split with its routing), `config` (a field in a config file), `tooling` (a script, a check,
a capability), `motion` (a backlog motion — a stub filed, a field re-formed, a plan moved or
deleted — which is not a doc edit at all). `trim` and `amend` are the mechanical sentence by
default; the rest are rows. The class predicts where judgment is likely; it groups, it does
not gate — a `rule` the maintainer waves through is still a row, answered in a word.

**The record**, below the block:

- **Pending captures** from step 0, led by any key with more than one occurrence — the
  finding, its occurrence count with dates, the placement retro already proposed, and your
  ranking (with the re-rank noted where it differs from retro's). Each already carries an
  accepted finding and a proposed edit, so these need the least work to land.
- **Structural candidates**, ranked most-supported first. Each: the **pattern**, the
  feeding **commit refs** (or churned files, on the fallback), related memories if any,
  and a concrete proposal — reconcile-into-X / structural-change / *leave* — with the
  placement from step 7 (the **amend-before-add** bar lives in
  `agents/finding-placer.md`). **Split-with-routing is a sanctioned outcome**: when a
  hot doc's growth is a coherent cluster its charter doesn't cover, carving it out is
  the amendment — but a split without a routing change (whatever sends readers to the
  new home at the decision moment) is incomplete, and the unrouted half is where it
  fails. **Narrate the *why*** — the relatable failure each local was patching.
- **Drift candidates (staleness)** — file or workflow set, plus the evidence: last
  touch vs repo growth since, sibling spread, and the stalest sections when blame ran.
  **Staleness alone proposes scrutiny, never a change** — an untouched doc may simply
  be *done*; the ask is *read this against current repo shape*. It escalates to a
  concrete proposal only with an intersecting signal (churn in the area the doc
  governs, a memory, an accepted retro finding that brushed it).
- **Taxonomy health** — a one-line note *only* when a scope-token signal holds across
  several cycles (dead / overloaded / co-occurring pair / `misc` pressure). Bias-to-keep.
- **Capability candidates** (where `capabilityEvidencePath` exists) — findings whose
  implication is a contract change, a rung promotion, or a new capability, not a doc edit.
  Rank by rung implication and occurrence. These are the proposals the doc-churn inputs
  structurally cannot reach, so report them even when the doc-side funnel found more.
  **Lead with 0c's reconciliation fraction** (placements landed / placements naming the
  store). Below 100%, the funnel's only non-doc input is short by that many findings and
  every ranking here was made without them.
- **The reads that sized the run** — name the `invariantDocs` you actually read and what
  in them bore on this run, each doc's window from `core-diff.py` with its hunks classed
  rule / prose, plus the depth-gate decision and what triggered it. A run that
  stopped at the gate says so plainly: that is a complete review, not a truncated one.
- **Tier narration** — which tier this run used; what the next tier up would buy.
- **Tally** — all-time: `marker-stream.py count --all` (derived, never stored). The
  organic figure is the headline; the review and bookkeeping figures say how much of
  the stream is the loop's own weight.
- **Review economics** — the closing block, and the one place the review's own conduct
  goes. Numbers first, one line each, every one from a command this run already ran:
  core docs read / core docs that bore on a ruling (count and words); **core prose
  growth** — per core doc with a window, words added classed prose / words added, from
  `core-diff.py` and the hunk read (a doc bearing on nothing and growing in prose is a
  cull finding, not a question); keyed docs opened
  whole / keyed docs that bore (count and words — a keyed set larger than the core is
  the bound in step 6 failing); markers read — organic / review / bookkeeping; keys read (the
  view's summary line) / keys that recurred; this run's own landing errors (a wrong
  anchor, a mistyped literal, a repaired commit — count and shas); the run's size where
  the harness shows it (tool calls, wall clock). Then **questions to the maintainer**,
  never findings: *what should the next run stop reading?* — a ledger watch that has
  not woken in several windows, a class of capture the retro should stop appending (a
  core doc that bore on nothing is not on this list: 0a asks why, and the answer is a
  trim or nothing) — and any miss of this run's own, phrased as the question
  it raises. **The review's own misses are lines here and an `Economics:` line beside
  `Tally:` in the marker commit body, never keys in the log it maintains**: keying the
  review's conduct into the stream it is trying to shrink feeds the count it measures.
  The maintainer answers in the thread; an answer that changes a config field or a doc
  lands as this run's marker commit.

Nothing is applied without recorded consent. Under `read-only`, present candidates only.
Under `apply-on-approval`, land each **approved** edit as its own `<markerPattern>` commit —
never folded into unrelated work. Under `apply-mechanical`, the same, and a run the
maintainer is not answering lands the mechanical line — `trim` and `amend` only, each its
own marker commit, landed first and cited second like any other, **with its `LANDED` line
written** (a landing with no status line is re-proposed by the next run) — and reports it
as *landed* with the shas rather than *land on your word*; every row is still `HELD`. The
class is what the placer assigned against the text it read, and it is necessary, not
sufficient: a candidate lands unanswered only if **every** guard below passes, and one
failing guard holds it whatever its class says.

- **Docs only.** Every file it touches is a doc in `processDocs`; a required companion edit
  anywhere else — a script, a config, a budget table a doc's growth forces — holds the
  whole candidate.
- **Additive only.** Inserted sentences or a cross-reference clause; a deletion or rewrite
  of an existing rule sentence, a consolidation included, holds — a net-negative diff
  removes prose the maintainer never saw go.
- **Live and never landed.** The key is live and carries no `LANDED`, `REOPENED`, or
  `FILED` block; a shape recurring with its rule present is an application failure the
  log counts, and a key filed against a stub is filed so prose stops accreting.
- **Not a watched section.** The target section is named in no Live ledger entry; step 3
  already reads the ledger, so the check is free.
- **Whole or not at all.** A candidate that edits several files lands whole or holds
  whole; one protected file holds the set, since a pointer landed alone points at text
  that does not exist.
- **Not protected.** No file in `invariantDocs`, nothing still referenced deleted, and no
  placer call of `add (unconsolidated)`.

**A landing is a text match, not a paraphrase — under every tier.** The anchor is the
placer's on-disk quote with its line numbers, wrapped as the file wraps it; an anchor that
does not match verbatim is a placement to send back, never a sentence to re-find by
meaning. A value written into a data literal — a number in a budget table, a field in a
config — is asserted to be of the literal's type before the write (`[0-9]+` for a count):
a parsed value is a claim about the emitted form, and a wrong one lands as an exemption
the literal's own checker cannot see. Both are clean-judgment errors, and both are cheaper
as a check at the write than as an executor sub-agent between judgment and landing.

## On completion

- **Every commit this run makes carries the trailer `Process-Review: <today's date>`** —
  candidate landings, the log and ledger bookkeeping, the mark's own commit — so the next
  run counts none of it as churn (Telemetry). `git commit --trailer 'Process-Review:
  <date>'`; `land-process-commit.py` carries it through the cherry-pick unchanged.

- **Land first, cite second.** A sha written before its commit is on the default branch is
  a sha the landing rebase rewrites. Every `LANDED <sha>` line, and every sha the ledger
  cites, is written *after* the landing commits are pushed, with each sha read back from
  the remote by subject (`git log origin/<default> --grep '<the candidate's subject>'`),
  in a commit of its own. Never cite a branch-side sha. From a slice branch, a marker
  commit that must not wait for a squash lands by itself through
  `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/land-process-commit.py <sha>`: a throwaway
  worktree at the remote's default branch, cherry-pick then `git commit -C` so the
  repo's own pre-commit hook judges it, push, and the only thing on stdout is the sha
  re-read from the remote — the one to cite; the slice branch is rebased so the
  duplicate drops.
- Advance the mark: `git tag -f <markTag> <commit>` — where `<commit>` is an
  **ancestor of the default branch**, after any approved edits have landed there. `HEAD`
  is only right when that's where you are; a branch tip that a squash or rebase later
  orphans takes the mark with it, and the next window re-reads everything this one
  covered as new.
- **Propagate it — the mark is shared state, not a local bookmark.** A local advance alone
  leaves every other clone measuring from a stale mark, so every later review re-reads
  commits this one already covered. If the tag is published on the remote
  (`git ls-remote --tags origin refs/tags/<markTag>` returns a hit), push the advance:
  `git push -f origin refs/tags/<markTag>`. If it isn't on the remote it's local-only —
  leave it that way; don't publish it as a side effect of a review. (`origin` here means
  whatever the repo's remote is actually called; no remote → nothing to do.)
- **Land the placements 0c counted as unresolved.** A retro-log `Placement:` naming
  `capabilityEvidencePath` is a proposal nothing else in the system will act on. Append
  each in that store's own entry format, or record a decline in the ledger with the
  reason; then the entries you just landed become collapse candidates below. Under
  `read-only`, propose the appends rather than making them. Zero unresolved → nothing to
  do, and 0c already said so.
- **Maintain the retro log (`retroLogPath`) — you are its only mutator.** Retro appends
  and never edits, so everything below is yours, and nothing else in the system will do
  it. Under `read-only`, propose these rather than applying them. The `guards`
  `retro-log` check is the shape gate; run it after.
  - **A finding that landed** gets the key + one `LANDED <sha> — <where>` line appended,
    if the landing session did not append it. **A retirement** is the key + one
    `RETIRED <date> — <why>` line; **one that must land elsewhere** is `UPSTREAM <ref>`;
    **one routed to a stub or plan** is `FILED <ref>` — the key stays live, so a further
    occurrence counts against the stub instead of vanishing into a closed key.
  - **A candidate this run proposed and held** (an autonomous run, or one the user did
    not answer) is `HELD <today's date> — <letter, class, the proposal in one line>` on
    its key, and the lines ride **this run's marker commit** — the date is the ref because
    a commit cannot cite its own sha, and that date names the marker commit (`git log
    --grep '<markerPattern>' --since <date> --until <date+1>`). HELD is its own state:
    nothing owns the proposal and nothing picks it up until someone approves, which is
    why the view lists HELD keys first, with their age, and the next run reports them
    before anything else. A held candidate keyed to nothing goes in the ledger's Live with
    *promoting signal: approval*. Approved → `LANDED`; declined → `RETIRED` with the
    reason. A held proposal that lives only in a commit body is lost to the next run.
  - **A ruling on a key that moves nothing** — a re-rank, a count-only call at a key whose
    rule is present, a build trigger on a filed stub, a re-rank withdrawn — is
    `ADJUDICATED <today's date> — <the ruling in one line>` on the key: its own entry,
    never continuation prose inside an occurrence. It changes neither the state nor the
    count, `compact` keeps it, and `view --key` shows it, so the next run reads the ruling
    where the key is instead of in a commit body.
  - **Then compact:** `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/retro-log.py compact` — one
    block per key, closed keys reduced to their status line. It is the only rewrite of
    the file and it is deterministic; a violation it refuses on is repaired by hand first.
  - **Re-key before you retire.** Entries flagged `key (uncold)` were keyed by the
    session that did the work, which is the context least able to write a domain-free
    key — re-key those first, and never read their failure to match as evidence of a
    one-off. Beyond the flagged ones: an entry that never recurred is either genuinely
    one-off *or keyed too specifically to ever match* — volume can't tell those apart,
    and retiring blindly deletes the only evidence that keying is broken, leaving a log
    that looks healthy and dedups nothing. You read every key at once, which makes you
    the one context that can spot a key still carrying the nouns of the slice that
    produced it. Rewrite those at the right altitude instead of dropping them.
  - **Retirement is a judgment, not a threshold.** The question is *would a future review
    act differently without this entry?* — decided the way staleness is, bias-to-keep. No
    fixed age is right for both a repo capturing twice a month and one capturing several
    times a day.
  - **Note any key-quality drift in one line** when it holds across the corpus (keys too
    specific to ever match, or so broad they'd match anything). It is the health signal
    for the whole dedup mechanism.
- Update the ledger (`ledgerPath`) — a working file the review reads in full every run,
  so it holds current state and never a window's narrative. Three sections, each entry a
  top-level bullet; the `guards` `review-ledger` check is the gate:
  - **Live** — what was deferred, why, its **promoting signal**, and one
    `last checked: <date> — <state>` line, rewritten in place each run; each entry at most
    12 lines — the cap is per entry, the section has none.
    A dated window line (`09-04: no fire`) is the failure — the state replaces the old
    state, it does not follow it. The gate for any entry: *would a future review act
    differently without it?* A Live entry may be **dormant**: it carries one `wake:
    <condition>` line — a key occurrence in the since-mark view, a path in the window's
    organic stream, a date — and is re-measured, its `last checked` rewritten, only on a
    run where the wake holds; otherwise the run reads the wake line and nothing else of
    it. The promoting signal stays as written; the wake is the one-line proxy the run
    tests first. An entry whose signal has not fired for several windows and whose
    measurement costs more than a line is the case for it.
  - **Falsifications** — kept whole; their job is stopping a repeat.
  - **Resolved** — a pointer at the landing commit, at most 3 lines; the commit body
    keeps the story.
  - **This run's narrative** — what fired, what was held, the counts — goes in the body
    of this run's own `<markerPattern>` commit, never into the ledger.
  - A number recorded in the ledger carries its **generating command**, not just its
    value — a later run re-measures instead of reconciling stale figures under
    similar labels.
- If a tracker issue filed this review (detected tier), close it with a completion note.

## Anti-patterns

- **Writing anything on the first run**, or writing at all under `read-only`.
- **Dictating a convention** the repo didn't agree to — negotiate, prove it fires, record
  it once.
- **Re-deriving the marker** in the moment instead of reading the config.
- **Eager grand restructures** — a meta-review that over-proposes is worse than none.
- **Treating stale as broken** — staleness alone never earns a rewrite proposal, only a
  scrutiny note; bias-to-keep applies double on the negative-space side.
- **Reading every diff** — respect the funnel; only hot clusters get `git show`, only
  staleness survivors get `git blame`.
- **Retiring retro-log entries on age alone**, or retiring one that is merely mis-keyed —
  re-key first; blind retirement hides the failure it should surface.
- **Writing a window's narrative into the ledger**, or editing a log line other than a key
  being re-keyed. The commit body is the narrative's home; the stream is append-only.
- **Treating retro's disposition as settled.** You have better standing to rank than the
  session that set it; use it, and record the re-rank.
- **Counting keys before re-keying them** — the count is then invalidated by your own
  later re-key, after it has already set the ranking.
- **Judging `capabilityEvidencePath` from its own contents alone.** A store nothing else
  writes reads as healthy whether or not the placements addressed to it arrived; the
  reconciliation against 0b is the only thing that can tell those apart.
- **Running the full funnel against a corpus with no recurrence** — the gate exists
  because measurement cost rises with repo size while a fixed funnel's yield does not.
- **Silent fallback** — always narrate the tier and its upgrade path.
- **Writing while a peer review is in flight**, or without re-reading the mark and the log
  blob right before the first write — the pre-flight exists because this command is the
  one mutator and nothing else serializes it.
- **Landing on class alone under `apply-mechanical`** — the class admits a candidate to
  the guards, it never lands one; an amend that drags a script edit, deletes a sentence,
  sits on a landed or filed key, touches a watched section, or lands half of a pair is
  held however small it looks, and an invariant doc is never edited unanswered.
- **Handing the maintainer the record.** Pattern → evidence → proposal per candidate is
  for the commit body and the next run; a person gets the decision block, and a wording
  amendment listed as a decision is the row that hides the real one.
- **A row named by its key, missing its recommendation, or resting on a stale premise** —
  the Decision names the artifact and the motion, the Recommend column is never empty, and
  every premise is re-measured against the default branch before the row is written.
- **Citing a sha the commit cannot know, or one a rebase will rewrite** — the date keys
  `HELD`; a `LANDED` sha is read back from the remote after the push; and a ruling is an
  `ADJUDICATED` line, never continuation prose.
- **Checking the local head for a peer's landing**, or refusing on a clean rebase — the
  pre-flight reads the remote's default branch and re-derives.
- **Counting the review's own landings, or log-only bookkeeping, as the window's churn**
  — the trailer and the path test exist so the trigger measures what no review has seen;
  a hand-rolled `git log | grep` counts all three kinds and the loop feeds itself.
- **Reading a domain doc at step 0 because a config lists it.** The core is the authority
  order and this review's contract; everything else is a keyed read at step 6, opened
  because a finding named it.
- **Re-finding an anchor by meaning, or writing a parsed value into a literal unchecked**
  — a mismatch goes back to the placer, a non-number never reaches the file.
- **Keying the review's own conduct into the log.** It goes in the economics block and
  the commit body, as a question to the maintainer; the log is the substrate this
  command is trying to keep small.
