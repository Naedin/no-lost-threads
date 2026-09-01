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
- `trigger` — `{ "n": 10, "concentration": 3 }` (volume backstop; distinct-commit
  re-touch bar). Read by `/threads:retro` to decide whether its closing ripeness nudge
  fires.
- `applyMode` — `read-only` | `apply-on-approval`. Starts `read-only`. Once the user
  has approved candidates in two or more reviews, offer **once** to ratchet up; record
  either answer here and don't re-ask.
- `retroTelemetry` — `true` | `false`: whether a finding landed **straight from a retro**
  (its escape hatch, used only when the user asks to apply on the spot) gets a
  `markerPattern` commit. Unset → retro offers once at its next such moment and records
  the answer here. It has nothing to say about retro's default capture path, which writes
  no commits.
- `ledgerPath` — deferral ledger: what a *review* declined, plus the signal that would
  promote it. Default `.claude/threads-review-ledger.md`.
- `retroLogPath` — retro log: what *sessions* captured and no review has adjudicated yet.
  Default `.claude/threads-retro-log.md`. Written append-only by `/threads:retro`; this
  command is its only mutator.
- `invariantDocs` — optional, **ordered** (highest authority first): the docs stating what
  this repo holds true. Read at step 0a, before any commit. Absent → the review has no
  input above the commit stream and says so.
- `capabilityEvidencePath` — optional: a log of findings about *capabilities* — contracts
  and rungs rather than doc sections. Only relevant where the repo builds tooling it also
  uses. It is the one input that can yield a non-doc proposal; without it the funnel is
  doc-churn-shaped end to end. Absent → narrate and skip.
- `markTag` — default `process-review-mark`.

**The two files are separate on purpose.** The ledger holds decisions *not* to act and is
read late, as a suppressor. The retro log holds findings already judged worth acting on
and not yet landed — the highest-signal material in a window, read first. One file would
serve two opposite jobs from one read position.

If `.claude/threads.json` is absent, you are in **bootstrap** (below). If present but a
field is missing, use the default above and note it.

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
2. **Report** what you detected, which inputs you'll use, and which fallback tiers apply.
3. **Negotiate the marker** — propose the default `docs(process/<scope>):`, *or* an
   adaptation fitting the repo's existing style (e.g. a `chore(...)` repo → offer
   `chore(process/...)`). Surface any collision with an existing convention **before**
   adopting. In a squash-lane repo, negotiate a pattern covering the merge-lane spelling
   too. Prefer character classes to `\|` alternation — `\|` is a GNU extension in BRE and
   won't travel. Then **prove it fires**: run the grep against one sample subject per
   lane, using the pattern exactly as it will be written to the config. A marker that
   fails its own grep test is not adopted.
4. **Confirm `processDocs`** — the one thing inspection can't reliably answer. Ask.
5. **Seed** (only after confirmation): write `.claude/threads.json`, then re-run the
   step-3 proof reading the pattern back out of the real file; create the retro log at
   `retroLogPath` with a header stating its entry contract (one greppable, domain-free key
   line per entry, detail indented beneath, a same-key entry meaning a recurrence and
   nothing else — see step 0 of the review); tag
   `git tag <markTag> HEAD`. Then run one normal pass so the first run delivers value.
   **Migration case:** a repo already keeping a hand-built recurrence log should have it
   adopted as `retroLogPath` if its entries can carry keys, not have a second one started
   beside it.

The all-time tally (below) doubles as the bootstrap demo: *"your repo already shows N
commits of process-doc churn — here's what this tool does with that."*

## The review — cheap → expensive (never read every diff)

0. **Free — the reads that size the run.** All three are cheap; none is optional where
   configured. Do them before looking at a single commit.

   **0a — the repo's own invariants** (`invariantDocs`, in order). Read them. You are
   about to propose changes to how this repo works, and its stated invariants outrank
   anything you will derive from a commit stream. **Name what you read in the output** —
   a step whose result nothing carries is a step that will quietly stop happening. No
   `invariantDocs` → narrate and skip.

   **0b — the retro log** (`retroLogPath`). The only already-adjudicated findings in the
   window: a human accepted each one and a cold reader named its shape.
   - **Re-key first, then count — in that order.** A key written at slice altitude cannot
     match anything, so counting before re-keying yields a number the re-key invalidates,
     after every ranking decision has already been made against it. Read every key as a
     set, rewrite the ones still carrying their session's nouns, *then* count. Entries
     flagged `key (uncold)` come first, but the sweep is over all of them.
   - **Count occurrences per key.** Entries sharing a key are the *same finding
     recurring*; the log is append-only, so a repeat is extra entries rather than an
     edited one. A key appearing more than once is the promotion the log exists to make
     visible — rank those first and carry the occurrence count as the evidence.
   - **Retro's disposition tag is an input, not a verdict.** You hold the cross-session
     view, which is strictly better standing for ranking than the single session that set
     it — so re-rank freely, in either direction. Record the re-rank and the reason; never
     silently overwrite the original call.
   - **Empty log, or no `retroLogPath`** → narrate and skip, like any detected input.

   **0c — capability evidence** (`capabilityEvidencePath`), where the repo builds the
   tooling it uses. Entries here name a contract and a rung rather than a doc section, so
   they are the only input that can produce a non-doc proposal. Without it, every input in
   this funnel is doc-churn-shaped and the output can only ever be doc edits. Count keys
   the same way. Absent → narrate and skip.

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
1. **Free** — list the stream, matching the marker on the **subject** only (it's a subject
   prefix — a body mention must not count): `git log <markTag>..HEAD --format='%s%x09%h' |
   grep '<markerPattern>'` — subject first, hash after the tab. (`%h %s` order puts the
   hash where the anchor looks and matches nothing on any repo, which then presents as the
   silent-death tier below.) This stream is what **landed**; step 0 is what is **pending**. Then `git show --no-patch
   --name-only --format= <those hashes>` for the by-file view. Tabulate by scope (parse
   `<scope>` from each subject) and by file, counting **distinct commits** (re-touch across
   sessions is the signal, not raw line count).
   - **Fallback tier (no marker commits):** cluster churn on `processDocs` paths instead
     (`git log <markTag>..HEAD --name-only -- <processDocs>`, or full history on the very
     first run). Marker commits are the precise signal; path-churn is the coarse one.
     **Narrate that you're on the fallback and what the marker convention would buy.**
   - **Silent-death check:** marker hits == 0 while `processDocs` churn > 0 → surface
     "your telemetry convention may not be firing" (a narrated tier drop, not silent rot).
     Before concluding it's dead, rule out the measurement itself: an anchored grep run
     over hash-prefixed lines is zero on every repo — re-run subject-first. Then check
     the merge lane: if that churn arrived via squash-merged PRs, the markers may be
     dying in the squash (see bootstrap), not missing — the fix is widening the pattern,
     not re-negotiating the convention. Zero marker hits is also simply *expected* in a
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
6. **Expensive — hot clusters and staleness survivors only** — `git show` the churn
   diffs; `git blame` the staleness survivors to locate their stalest sections,
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
   against, and the concrete edit. **Name the candidate docs**: `processDocs` plus the
   specific files this run surfaced as hot or stale. You already paid for that view, and
   rebuilding it is the placer's largest cost. If the agent or the `Agent` tool is
   unavailable, place here and narrate that the amend-before-add bar was applied by a
   depleted context.

## Output (in-thread; `applyMode` governs whether approved edits are applied)

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
- **The reads that sized the run** — name the `invariantDocs` you actually read and what
  in them bore on this run, plus the depth-gate decision and what triggered it. A run that
  stopped at the gate says so plainly: that is a complete review, not a truncated one.
- **Tier narration** — which tier this run used; what the next tier up would buy.
- **Tally** — all-time process improvements (subjects only, same as step 1):
  `git log HEAD --format='%s' | grep -c '<markerPattern>'` (derived, never stored).

Nothing is applied without approval. Under `read-only`, present candidates only. Under
`apply-on-approval`, land each **approved** edit as its own `<markerPattern>` commit —
never folded into unrelated work.

## On completion

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
- **Maintain the retro log (`retroLogPath`) — you are its only mutator.** Retro appends
  and never edits, so everything below is yours, and nothing else in the system will do
  it. Under `read-only`, propose these rather than applying them.
  - **Entries whose findings landed** collapse to a pointer at the landing commit, the
    same motion the ledger uses.
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
- Update the ledger (`ledgerPath`) — it is a working file the review reads in full every
  run, not an archive, so an append-only ledger accelerates per-window:
  - New deferrals carry what + why + **promoting signal** + date. The gate for any
    entry: *would a future review act differently without it?* If not, it doesn't go in.
  - An entry whose promotion **landed** collapses to a pointer at the landing commit;
    the commit body keeps the story.
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
- **Treating retro's disposition as settled.** You have better standing to rank than the
  session that set it; use it, and record the re-rank.
- **Counting keys before re-keying them** — the count is then invalidated by your own
  later re-key, after it has already set the ranking.
- **Running the full funnel against a corpus with no recurrence** — the gate exists
  because measurement cost rises with repo size while a fixed funnel's yield does not.
- **Silent fallback** — always narrate the tier and its upgrade path.
