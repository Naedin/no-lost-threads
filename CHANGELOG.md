<!-- audience: human -->
# Changelog

Notable changes to this marketplace's plugins (**threads**, **slices**, **checks**), newest
first per plugin. Versions track each plugin's `version` in its
`.claude-plugin/plugin.json` and in
[`marketplace.json`](.claude-plugin/marketplace.json); each release is tagged
`<plugin>--v<version>`.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## threads [0.7.3] — 2026-09-03

### Fixed

- **The ripeness nudge counted the whole retro log as pending.** `/threads:retro` §5 now
  derives pending from the review mark, the same boundary `/threads:process-review`
  adjudicates against, so a clean review is no longer reported as a backlog the next
  day, and a run with nothing pending and no trigger bar met says nothing.

### Changed

- **The retro auditor records what a read prevented.** A claim the session record
  shows revised after a doc read is reported as a `positive/` finding naming the doc,
  so prevented errors reach the retro log as observed corrections instead of leaving no
  trace.

## slices [0.1.3] — 2026-09-03

### Contract

- **`/slices:capture` is template-aware through an optional `stubTemplate` config
  field.** `.claude/slices.json` gains an optional `stubTemplate` path. Absent — every
  current config, this repo's included — capture writes the built-in day-one stub
  byte-for-byte as before. Set, the command starts from the adopter's template and
  *overlays* the invariants it guarantees in every repo: a low-trust banner (present; the
  wording is the template's), the one-concern rule, and the closed `Blocked on:` /
  `Source:` grammars — auto-emitting any the template omits and narrating that it did,
  never refusing. The title form, the banner text, and every other field are the
  adopter's, carried through untouched, so a repo adapts the stub shape through a template
  instead of editing command text and a `/plugin update` never forks it. Benefit: an
  adopter carries local stub fields through config, not a command fork. Adopter-side edit:
  none — the field is additive and opt-in and its absence preserves prior behavior, so no
  adopter holds it and none needed reconciling.

### Added

- **The stub-template format is documented** in `/slices:capture` and the plugin README:
  a template is an ordinary stub skeleton read by structure — heading, banner blockquote,
  the grammar lines, local fields, body. Relationship fields — a `Depends on:`, a
  `Related:` cross-reference to a set of sibling concerns — are local fields the overlay
  carries through; point them at durable slugs (plans, epics), not at sibling stubs, which
  `/slices:draft` deletes on promotion.

## slices [0.1.2] — 2026-09-03

### Contract

- **Stub fields carry a closed grammar, spelled as the reference adopter spells them.**
  `blocked-by` is now `Blocked on: <tokens> — <rationale>` with tokens
  `slice:<plan-basename>`, `signal`, `decision`; `source:` is now `Source: <origin>
  <date> — <detail>` with origin `user`, `repo:<name>`, or `carved:<plan-basename>`.
  Both lines stay optional and mean the same when absent. Benefit of a new spelling:
  none — the side with fewer carriers moved. Adopter-side edit: none for a repo already
  on `Blocked on:`; a repo on `blocked-by` renames the line.

### Added

- **`/slices:check` tests an escalated ruling before recording it.** Step 2 checks the
  ruling against the docs `invariantDocs` names in `.claude/threads.json` (falling back
  to `docs/principles.md` and `docs/direction.md`) and surfaces a conflict instead of
  recording the ruling.
- **A new gap-check failure class.** A ruling or tension that changes a recorded
  decision without naming that decision's own amendment in scope.
- **A stub can say where its observation came from.** The capture contract gains an
  optional `source:` line, next to `blocked-by`, for an observation carried in from
  outside the repo's own sessions: another repo's review or retro, a person's
  report, an issue. Provenance, not trust; the banner still applies. A later reader
  can tell an observation made in the repo from one brought in, which the banner
  alone cannot say. The channel by which an outside observation arrives is not part
  of the line.

## checks [0.1.0] — 2026-09-02

### Added

- **Initial release of `checks`, repo guardrails as scripts behind a gate** — the
  third capability module. One script per check with a stable id, pass and fail
  fixture trees proven by `test.sh`, and exit codes 0 / 1 / 2 meaning pass, findings,
  refused; severity is the rung's, set per check in `.claude/checks.json` as `warn` or
  `block`, so enforcement climbs by config and never by migration. `run.py` maps
  findings through rungs and exits 2 itself when a check cannot run, so a broken gate
  is never a passed one. A git pre-commit adapter exports the index to a temporary
  tree and runs the runner there, judging the commit's content; it is inert when the
  index carries no config. Two checks ship: `anchors` (every in-repo section link
  resolves to an explicit `<a id>` and every relative link target exists;
  heading-derived slugs fail by design) and `war-stories` (narrative provenance in
  process docs); for both, fenced code and code spans are not prose. Installed from
  the marketplace this version is inert — no hook file, no command; the install line
  assumes the plugin lives in the repo's tree.

## threads [0.7.2] — 2026-09-01

### Fixed

- **`/threads:process-review` could not see that its own capability-evidence
  input was short.** `capabilityEvidencePath` had readers and no writer: the
  field appeared three times in the command, all read-side, and nothing pointed
  `finding-placer` at the store either — it is not in `processDocs`. A retro-log
  `Placement:` naming that store was therefore a proposal nothing in the system
  would act on. The failure is invisible from where the review stands: step 0c
  counts the store's own keys, and those counts read identically whether the
  placements addressed to it arrived or not, so a review reports a healthy log
  and a short one the same way — then ranks capability candidates, the funnel's
  only non-doc-shaped output, against the short set. Measured in the reference
  repo before the fix: nine actionable placements named the store and none had
  landed. Step 0c now reconciles the store against 0b's placements and carries
  the fraction, and that fraction is a required field of the
  capability-candidates output, so a run cannot finish its report without having
  looked. Landing the unresolved ones is a completion step; a decline goes in the
  ledger. Stated as a rule rather than a required output it would have been
  another prose route, which is the class of failure it fixes.
- **Retro's log append named a file but not a position in it.** `/threads:retro`
  said to append every finding to the retro log while the log's own contract says
  entries live under `## Entries`. Once a log grows a trailing section, a literal
  end-of-file append lands outside the section that holds entries — where it
  still greps and no longer reads, so the failure is silent to the mechanism that
  ranks recurrence. Retro now appends under `## Entries`, ahead of any trailing
  section, and the bootstrap seeds the same clause into a new repo's log header.

## slices [0.1.1] — 2026-09-01

### Fixed

- **`/slices:capture` failed on a fully-drained inbox.** The command wrote a stub
  into `inboxDir` without ensuring the directory existed. Git tracks no empty
  directories, so draining the last stub deletes the directory and the next
  capture fails with ENOENT — an inbox that has been used is indistinguishable
  from a repo that never had one. Capture now creates `inboxDir` when absent.

## threads [0.7.1] — 2026-09-01

### Fixed

- **`/threads:retro`'s escape hatch could silently inflate the retro log's
  recurrence count.** When a user accepted findings and asked for them to be
  applied on the spot, the escape hatch closed with "the entry still goes in the
  log — appended with its landing noted." By that point capture has already
  happened: the capture step appends unconditionally and is told not to ask
  first. So noting the landing required either editing an existing entry —
  forbidden by name, "not to mark one landed" — or appending a second entry
  under the same key. That same-key append is exactly what the command
  authorizes as the *recurrence* mechanism, so an agent holding "note the
  landing" and "never edit" resolves to the move the document had already
  blessed. Nothing errors and the log stays well-formed; the key's occurrence
  count simply gains a recurrence that never happened, and
  `/threads:process-review` reads that count as the evidence that promotes a
  finding to *adopt now*. The failure is worse than a miscount: it ratchets one
  way, since nothing demotes a promotion, and it is self-confirming, since retro
  reads the log *before* it appends — the session that corrupts the count cannot
  detect what it just did, and the next one inherits it as measured fact. The
  root is that an entry carries two things, occurrence (what the key counts) and
  lifecycle (which has no field), so the escape hatch borrowed the counter.
  Lifecycle now routes to the stream that already owns it: the log entry stays
  exactly as it was appended, the landing is recorded by the marker commit, and
  the review collapses the entry to a pointer at that commit. A same-key append
  is authorized for recurrence and nothing else — stated in the capture rule, in
  the anti-patterns, and in the log header that bootstrap seeds, so the contract
  an appending session reads in-file matches the one in the command. Found by a
  downstream adopter that hit the ambiguity live.

## threads [0.7.0] — 2026-08-31

### Added

- **`invariantDocs`** (optional, ordered) — the docs stating what a repo holds
  true, read at step 0a before any commit is examined. A review that proposes
  process changes without reading the repo's stated invariants is deriving law
  from a commit stream. The output must name what was read, so the step cannot
  quietly stop happening.
- **`capabilityEvidencePath`** (optional) — a log of findings about *capabilities*
  (contracts and rungs) rather than doc sections. Relevant where a repo builds
  tooling it also uses. Every other input is doc-churn-shaped, so without this one
  the funnel's output can only ever be doc edits.

### Changed

- **The funnel now gates on its own first signal.** Steps 1–7 are conditional: if
  nothing recurred after re-keying and no ledger signal fired, the review reports
  and stops. Measurement cost rises with repo size while a fixed-depth funnel's
  yield does not; the first run of this command against its own repo spent seven
  tiers and a sub-agent to reach an answer two greps had already given. `deep`
  overrides the gate.
- **Re-keying now precedes counting.** Keys were re-written at completion and
  counted at step 0, so every ranking decision used a number the re-key later
  invalidated. Measured here: one mis-keyed entry made a four-occurrence class
  read as a one-off, and it was the corpus's only real recurrence.
- Output gained a **capability candidates** section and a statement of the reads
  that sized the run.

## slices [0.1.0] — 2026-08-31

### Added

- **Initial release of `slices`, the day-one slice-pipeline kit** — the second
  capability module, extracted contract-first from the reference pipeline's
  "day one — costs nothing, pays immediately" set. `/slices:capture` files
  one-concern, low-trust stubs (mandatory banner; lifecycle by directory;
  blockers are named checkable conditions or nothing). `/slices:draft` promotes a
  stub into a plan — re-verifying the capture's claims first, carving bundles,
  deleting the stub in the promotion — ending in a review digest of a Shape
  paragraph plus at most five tension points. `/slices:check` spawns a cold
  `gap-checker` sub-agent handed only the plan's path (withholding the drafting
  context is load-bearing), and appends its verdict to the plan's verification
  ledger; no plan is implement-ready until it survives. The two-lane rule and the
  marker-prefix convention ship as stated policy and a pointer to `threads`
  respectively — capabilities compose rather than duplicate. Artifacts are the
  contract: later rungs (banner lint, claim ledger, triage, a landing gate) only
  append to these files, so day-one adoption never sets up a migration.

## [0.6.0] — 2026-08-30

### Added

- **A retro log — `adopt-if-it-recurs` finally has a destination.** `/threads:retro`
  named the disposition and stopped there; nothing in the command routed it anywhere, so
  the finding's next carrier was the conversation, which ends. A downstream repo built
  its own log and it failed to fire on **every** occasion, including one where the
  session had already read the doc carrying the convention — evidence that a pointer in a
  linked doc doesn't reach the decision moment. Findings now append to `retroLogPath`
  (new config key, default `.claude/threads-retro-log.md`), and the placer **reads the
  log to make the call**: a carrier you must consult is much harder to skip than one you
  are told to write to afterward. Kept separate from the deferral ledger because the two
  sit at opposite ends of the review funnel — the ledger holds decisions *not* to act and
  is read late as a suppressor, the log holds unlanded work and is read first.
- **Dedup keys, written by `finding-placer`.** Each finding gets one greppable,
  domain-free key naming its *shape*; the slice's own nouns stay in the evidence. The
  placer writes it because the calling session is soaked in the domain and is the worst
  context to abstract away from it — and because, having just grepped the existing keys,
  it phrases new ones in the corpus's register instead of drifting. That convergence is
  what keeps a repo's log matchable, and it's why the class vocabulary ships as a
  **seed rather than a schema**: keys grow into each repo's own frictions with nothing to
  configure. A repeat is a *new entry reusing the same key*, so recurrence is a grep count
  and no writer ever mutates the file. Where the sub-agent is unavailable, the working
  session keys its own finding and flags it `key (uncold)`, so the review re-keys those
  first instead of reading their never-matching as evidence of a one-off.
- **A ripeness nudge at the end of `/threads:retro`** — what's pending, how old, what's
  churned since the mark, in one sentence, always pointing at a fresh session and never
  offering to run the review in the current one.

### Changed

- **Retro captures; process-review lands.** Retro fired at the largest context a session
  ever has — the most expensive possible moment to apply an edit, since it invalidates
  the cache behind the whole session — and a session that ended with the output unread
  lost everything it found. Findings are now appended and adjudicated later by
  `/threads:process-review`, which runs in fresh context by requirement and is the only
  reader that can tell one friction from three of the same shape. The punch list is still
  presented in-thread, and a user who asks for an immediate landing still gets one.
  Consequences: retro now writes to the working tree by default (one append — capture is
  not adoption, and the entry takes no effect), and `retroTelemetry` narrows to the
  land-now hatch.
- **Retro's disposition is an input to the review, not a verdict.** Process-review reads
  the log first, ranks keys with more than one occurrence, and may re-rank with the
  reason recorded. The placer still can't touch a disposition; it reports a match as a
  fact and the caller revises its own call.
- **Retirement re-keys before it retires.** An entry that never recurred is either
  one-off or *keyed too specifically to ever match*, and volume can't tell those apart —
  so a fixed age threshold would delete the evidence that keying is broken and leave a log
  that looks healthy while deduping nothing. The review reads every key at once, which
  makes it the only context that can spot the difference. No fixed N, for the same reason
  staleness never proposes a rewrite on age alone.
- **`markerPattern` loses its byte constraints**, and bootstrap's two-reader proof
  collapses to one reader. Both existed only because the hook re-read the config through
  a sed capture. Patterns written under the old rule keep working.

### Removed

- **The SessionStart nudge hook** (`hooks/hooks.json`,
  `scripts/process-review-hook.sh`), and with it the sentinel, the mark-stamp, and the
  worktree-scope machinery. The plugin now ships no hooks at all. Measured in a live
  adopter repo: delivery **proven in 19 sessions**, relayed in **1** — and that one at a
  mid-session lull, not the mandated first response. The other 18 opening turns were
  uniformly task-acquisition. Mandating the relay had already replaced a discretionary
  version that never fired, so this is not a wording problem: an instruction that must
  beat the user's own request at the moment they make it will lose, and mandating it only
  makes the failure quieter, since the emission log then records 19 successes. Emission
  was the wrong end of the pipe to measure. The nudge moves to retro time, where it is
  command output and the transcript is the record.

## [0.5.2] — 2026-08-12

### Fixed

- **`/threads:process-review`'s step-1 recipe could never match.** The command doc's
  "Free" tier piped `git log --format='%h %s'` into a grep whose `markerPattern` is
  anchored to the subject start, so the hash prefix defeated the anchor and the count
  was zero on every repo — presenting as the silent-death tier's false positive ("your
  telemetry convention may not be firing") even with marker commits present. The recipe
  — and the design spec's `--grep` variant, which matched commit *bodies* in violation
  of the subject-only rule — now uses the hook's subject-first shape,
  `--format='%s%x09%h'`, and the silent-death check says to rule out the measurement
  itself before diagnosing the convention. The session-start hook was never affected.
  Found by a downstream repo's review run, which hit the false positive live.

## [0.5.1] — 2026-08-05

### Changed

- **`finding-placer` is time-boxed.** Shipped in 0.5.0 it was unbounded in three ways,
  and on a real repo it ran past five minutes and 200k tokens without finishing: it
  rediscovered the process-doc layout from scratch each run, it read source and backlog
  files to size the rules it was placing, and `add — last resort` set a bar (*no host
  exists anywhere*) that can only be met by surveying the whole repo. Now: **callers hand
  it the candidate docs** (`processDocs` from `.claude/threads.json`, plus the hot/stale
  files process-review already surfaced) instead of making a cold agent re-derive them;
  placement is fenced to siting the lesson, never measuring or re-wording it; and the
  amend bar is *a host is visible in what you read*, with an unsure add returned as `add
  (unconsolidated)`. Retro runs often enough that speed is a correctness property —
  `/threads:process-review` already reconciles across sessions, so an add that should
  have been an amend is recoverable at the altitude built for it.
- **`finding-placer` is pinned to Sonnet** (`model:` in its definition) rather than
  inheriting the session. With the map handed to it and the scope fenced, the work is
  judgment against text already in front of it, not open-ended search. The auditor still
  follows the session — it reads a whole transcript cold, which is the harder read.

## [0.5.0] — 2026-08-04

### Added

- **A placement sub-agent (`finding-placer`), shared by both commands.** Amend-before-add
  was stated in `/threads:retro` but executed by the context that did the work — which
  can't afford to re-read the target section, so "amend" reliably degraded into "append"
  (measured in a live adopter repo: a culled doc back at its word budget in four days,
  mostly appended worked-cases). Surviving findings now go to a fresh read-only sub-agent
  that reads the target docs and returns amend / merge / narrow / add-as-last-resort,
  with the existing text quoted and the edit specified — *before* approval, so what you
  approve is the fully-specified change. Retro spawns it in both modes; process-review
  spawns it after its expensive tier, whose session is fresh by mandate but not by then.
- **Retro findings carry their detection source.** The self-pass and the cold audit are
  reconciled, not concatenated: findings are tagged `[self]` / `[audit]` / `[both]`
  (`[both]` ranks first), and an audit finding the self-pass had cleared surfaces as
  `[disputed]` rather than being settled by the anchored party. Across runs the tags are
  the record of whether the audit earns its spawn.
- **The review adjudicates promoting signals.** The ledger step said "don't re-propose
  what's deferred" but never the reverse motion: every live signal is now checked
  against the window, and the fired ones adjudicated — promote, retire, or re-defer
  with the reason.
- **Staleness sweep: reachability and referent-existence checks.** A doc nothing routes
  to is the silent-death class regardless of freshness, and a staleness survivor is
  checked for dead referents before "clean" can count as evidence against urgency.

### Changed

- **`/threads:retro quick` means "skip the audit," not "self-pass only."** Placement
  still runs — `quick` selects the detection source, not a lower quality tier.
- **The marker convention must survive both its readers, and the squash.** Bootstrap
  probes how changes reach the default branch (a squash rewrites branch-side subjects,
  silently killing markers) and negotiates a pattern covering the merge-lane spelling;
  the silent-death check looks at the merge lane before declaring the convention dead.
  `markerPattern` must be backslash-free and class-based: the hook extracts it with a
  naive sed capture, not a JSON decoder, so a JSON-escaped backslash reaches grep as
  dead bytes — measured live, where a widened pattern passed its JSON-decoded proof
  while the hook matched nothing. The prove-it-fires gate now runs through each
  consumer's own reader chain, and editing the pattern later re-runs it.
- **The deferral ledger gains lifecycle rules.** It is a working file read in full every
  run, so append-only accelerates per-window: entries are gated on *would a future
  review act differently without it*, collapse to a pointer once their promotion lands,
  and record numbers with their generating command.
- **The mark advances at an ancestor of the default branch,** after landing — not at
  `HEAD`, which a squash or rebase can orphan, taking the review window with it.
- **Split-with-routing is a sanctioned structural outcome** when a hot doc's growth is a
  coherent cluster its charter doesn't cover — and incomplete without the routing change.

## [0.4.2] — 2026-07-26

### Fixed

- **The process-review nudge now actually reaches you — for real this time.** 0.4.1 moved
  the trigger to a `SessionStart` hook so a live turn could carry it. It reached the
  *agent* and stopped there: the payload asked the agent to relay the nudge "when it will
  not cut across what the user is doing", which at session start — the moment you've just
  arrived with a task in mind — is essentially never true. A live adopter repo fired four
  nudges across three days and every one was correctly suppressed by a well-behaved agent.
  The payload now **mandates** a one-sentence relay in the agent's first response before it
  continues with your request, and names the single legitimate exception (your first
  message *is* `/threads:process-review`). It still never acts on the nudge unprompted.
- **A repo with ten worktrees gets one nudge, not ten.** The re-nudge sentinel lived in the
  per-worktree git dir, so every fresh worktree started at `last=0` and nudged on its first
  ripe session — cadence tracked *worktree creation* rather than backlog ripeness, which on
  a heavy-worktree workflow is both too chatty (every new worktree) and too quiet (a
  long-lived checkout silent for a full doubling). The sentinel and the `threads-nudge.log`
  breadcrumb now live in the **common** git dir, shared by every linked worktree, because a
  ripe backlog is a property of the repo. Upgrading orphans the old per-worktree sentinels;
  expect one re-nudge, then correct cadence. The mark stamp is unchanged and still does its
  job across *clones*.
- **`/threads:process-review` now propagates the mark tag it advances.** Completion ran
  `git tag -f <markTag> HEAD` with no push. Where the tag is published on the remote — as
  it is in any repo that has ever run `git push --tags` — the advance stayed local, so
  every other clone kept measuring from a stale mark and every later review re-read ground
  an earlier one had already covered (observed two reviews stale in a live adopter repo).
  Completion now pushes the advance when the tag exists on the remote, and leaves a
  local-only tag local — a review never publishes a tag as a side effect.

## [0.4.1] — 2026-07-20

### Fixed

- **The process-review nudge now actually reaches you.** The trigger shipped as a `Stop`
  hook emitting `systemMessage` — which fired and emitted correct JSON on every qualifying
  stop, but was never seen: a `Stop` hook runs after the turn ends, with no live turn to
  attach a user-visible message to, so the nudge was dropped. It now runs as a
  **`SessionStart`** hook and hands the agent the nudge as `additionalContext`, surfaced
  at the agent's discretion at the start of a fresh session — which also fits the "fresh
  session, never mid-draft" intent better than firing at stop ever did. It fires on a
  fresh start or `/clear`, and stays quiet on resume or a mid-thread compaction.
- **The re-nudge guard no longer goes stale across worktrees.** State is per-worktree but
  the mark tag is shared, so completing a review in one worktree advanced the mark for all
  while resetting only its own sentinel — leaving sibling worktrees able to suppress a
  state that was freshly ripe against the new mark. The sentinel is now stamped with the
  mark it was measured against (`<mark-sha> <count>`); when the mark advances, a sibling's
  stale stamp reads as `last=0` and re-nudges against the new baseline. Backward-compatible
  (a legacy bare-number sentinel also reads as `last=0`).

### Changed

- **The trigger counts commit _subjects_, not whole messages.** `git log --grep` matched
  the marker pattern anywhere in a commit message, so a commit whose body quoted a
  `docs(process/…)` line inflated both the volume count and the concentration tally. Both
  the hook and the `/threads:process-review` command's own counts (stream listing, tally)
  are now subject-only, so the counts (and the "N since last review" tease) are exact.
- **Each emitted nudge is logged** to `threads-nudge.log` in the per-worktree git dir
  (auto-ignored), so "did it fire, and what did it say" is observable without depending on
  UI surfacing — the diagnosis a silent surfacing failure used to make expensive.

## [0.4.0] — 2026-07-16

### Added

- **`/threads:process-review` gains a staleness sweep** — the negative-space
  complement to its churn signal. Stable workflow docs (a command pipeline, a
  long-standing rule) can fall behind a growing repo without ever generating
  telemetry, so the review now also ranks process docs and workflow sets by
  growth-since-last-touch and by sibling co-evolution variance (one pipeline stage
  amended while its neighbors sat untouched), then git-blames the survivors to point
  at their stalest sections, weighted toward load-bearing files. Staleness alone
  proposes scrutiny, never a change; a concrete proposal requires an intersecting
  signal (churn, a memory, an accepted retro finding). New optional config field
  `workflowDocs` declares files expected to co-evolve; absent, detected command
  directories (`.claude/commands/`) each form a set — repos with no workflow surface
  skip the sweep with a narrated tier note, like any detected input.

## [0.3.0] — 2026-07-02

### Added

- **`/threads:process-review`** — the cross-session review. Reads the accumulated
  stream of process-shaped commits (or process-doc churn as a day-one fallback) and
  surfaces reconciliation / structural candidates no single session can see. First run
  bootstraps by inspection: it negotiates a marker convention fitting the repo's
  existing commit style (proving the pattern fires before adopting it) and writes
  nothing until confirmed. Conventions live in `.claude/threads.json` — one visible
  source. Applying anything requires recorded consent (`applyMode`, starts
  `read-only`).
- **A Stop-hook trigger** ships with the plugin: no analysis, one local git command per
  session stop, no network. Nudges when accumulation looks ripe (same file re-touched
  across several process commits) or crosses a volume backstop, and escalates instead
  of nagging — a re-nudge only after accumulation roughly doubles.

### Changed

- **`/threads:retro` feeds the loop:** when the user accepts findings and has them
  applied, retro offers (once, recorded in `.claude/threads.json`) to land them as
  marker commits — the telemetry `/threads:process-review` reads.

## [0.2.1] — 2026-06-25

### Changed

- **`/threads:retro`'s fresh-context audit now sees far more of each agent turn.** The
  extractor that builds the session record capped agent text at 700 characters and kept
  only the head — which dropped the tail of long turns, where commitments, deferrals, and
  lock-in language tend to land, and discarded roughly half of all agent text before the
  cold reviewer saw it. The cap is now 2,500 characters, and over-cap turns retain their
  head **and** tail. The audit reads more completely; the record stays a few KB.
- **The fresh-context audit now flags self-perpetuating closure language.** When an agent
  turn closes a question with markers like *decided / deferred / for v1 / by-design* that
  the evidence hadn't earned and the user hadn't locked, the auditor surfaces it for a
  second look — such markers tend to get accepted once and never revisited.

## [0.2.0] — 2026-06-24

- `/threads:retro` reviews the current session as process telemetry. The default runs a
  self-pass plus a **fresh-context audit** — a read-only `retro-auditor` sub-agent that
  judges the session's observable record cold. `/threads:retro quick` runs the self-pass
  alone and skips the sub-agent.
