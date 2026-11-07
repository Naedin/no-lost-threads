---
description: Cross-session process review — weighs where residual (what gets caught after the work) concentrates against the repo's direction, with delegates reading the raw incidents, and proposes what to change, replace, or delete. Takes the maintainer's own diagnosis as the run's question. First run bootstraps read-only; never auto-fires.
argument-hint: "[the maintainer's framing, e.g. \"the copy guidelines are broken\"] [deep]"
allowed-tools: Bash, Read, Grep, Glob, Write, Edit, Agent, SendMessage, WebSearch, WebFetch
---

# /threads:process-review — the cross-session process review

"The maintainer" below means whoever decides for this repo, one person or several.

`/threads:retro` reviews one session and captures what it found to the retro log. This
command reads across sessions and lands. It runs fresh by requirement: never in a session
that did the work under review.

**It works at direction altitude.** You, the reviewer, weigh what happened against the
repo's direction and decide what to change. Delegates read the raw incidents and return a
compressed picture: where residual concentrates, what changed near it, and how much
upcoming work runs through it. A finding is evidence about a direction, not a request for
a rule; a context full of incidents answers each one as an incident, one rule apiece.

**Deletion is a neutral move.** Removing a rule, a passage, or a doc needs no more
justification than adding one. A wrong rule is often best answered by deleting it; a
replacement stating its opposite is usually an overcorrection. Several mechanisms each
pushing the same way add up to one too; prefer the simplest sufficient change.

**Nothing silent.** The first run is read-only; writing is gated on recorded consent
(`applyMode`); every run names what it read and what it skipped.

## Argument — the run's question

Text after the command is the **maintainer's framing**: their diagnosis ("the copy
guidelines are broken", "pre-PR catches too late"). It becomes the run's question; the log
is evidence for or against it, never a vote on whether to look. A framing opens the depth
gate by itself, and a framing that names an artifact puts the whole artifact in question,
not its sections one at a time. A framing scopes what the run rules on, not what it
reports: any other opener that fired (a cluster, an escape, a ledger wake) gets one line at
the foot of the decision block, left for the next run. Never measure a framing by asking the maintainer to
produce more of it. With no framing, the question is *what does this window's residual
say*. A bare `deep` runs the full read with no gate.

## Config — the single source

`.claude/threads.json` (created at bootstrap; commit it). Both commands read it; never
re-derive a convention in the moment. A missing field takes its default, noted.

- `markerPattern` — anchored BRE over commit **subjects** only. Default `^docs(process`.
  Use character classes, never `\|` (a GNU extension). Editing it re-runs the bootstrap
  proof.
- `processDocs` — the paths that count as process docs.
- `workflowDocs` — optional sets of files describing one workflow; absent → each detected
  command directory is one set.
- `trigger` — `{ "cluster": 3 }`: the number of live keys placed at one file that fires a
  cluster. Unset → the next review reads the cluster backlog once and records it. (`n` and
  `concentration`, if present, are ignored: they counted rule changes, not residual.)
- `applyMode` — `read-only` | `apply-on-approval` | `apply-mechanical`; starts
  `read-only`. After the maintainer has approved candidates in two reviews, offer once to
  ratchet to `apply-on-approval`; after they have approved the mechanical line as a batch
  in two reviews, offer once to ratchet to `apply-mechanical`, naming which docs its guards
  leave reachable. Record the answer either way; never re-ask, never infer.
- `retroTelemetry` — whether a finding the retro lands on the spot gets a marker commit.
- `ledgerPath` — what a review declined, with its promoting signal. Default
  `.claude/threads-review-ledger.md`.
- `retroLogPath` — what sessions captured. Default `.claude/threads-retro-log.md`.
  Append-only; this command is its only mutator.
- `invariantDocs` — ordered, highest authority first: **the direction** — the docs you
  weigh findings against: the repo's authority order, its process direction and
  objectives, and this review's own contract. Read whole every run. A domain doc (a traps catalogue, a style guide) is not direction however
  true; it is read when a finding names it. Absent → the review has nothing to weigh
  against but the evidence, and says so.
- `windowOnlyDocs` — optional: docs watched as churn and opened only when a finding names
  them, such as a product direction too large to read every run. A path in both lists is
  a malformed config.
- `capabilityEvidencePath` — optional: findings about capabilities (contracts, rungs)
  rather than doc sections, for a repo that ships tooling to others. Unset in such a repo
  → ask once for a path or `null`, record it.
- `adherenceRules` — optional: prose rules sampled each run; the schema is
  [`commands/adherence.md`](adherence.md).
- `workaroundsPath` — optional: the workaround register (`scripts/workarounds.py --help`).
- `placerModel` — optional model for the `finding-placer` spawn.
- `retroPlacement` — `"full"` (default) or `"keys"` (retro keys without placing; this
  command places).
- `markTag` — default `process-review-mark`.

The ledger and the log are separate on purpose: the ledger holds decisions not to act,
read as a suppressor; the log holds findings, read first.

## Telemetry — residual, and the rule changes beside it

**Residual** is what gets caught after the work is done: maintainer corrections, review and
gate findings, escapes. In the log it is every occurrence classed escaped, gate-run, or
caught; in-work occurrences are the work itself. Residual is read **as a rate per stretch
of work** and **to diagnose, never as a target**. Its causes vary: a new area of work, a
recent rule change, a model or harness change, the artifact, chance. Untangling them takes
enough work to have run through the suspect territory.

**Residual concentrating in one artifact's territory while its rules are followed makes
that artifact the suspect.** "Rule present and read, output still wrong" is the tell.

**Marker commits are the rule changes**, the "what changed near it" for every
concentration, never residual. Three kinds share the subject pattern: **organic** (a
process change no review adjudicated), **review** (a commit this command made; every one
carries the trailer `Process-Review: <date>`), and **bookkeeping** (touching only the log,
the ledger, or the capability store). Only organic markers are read as change.
`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/marker-stream.py` (`count`, `list`, `files`,
`--all`, `--head origin/<default>`) is the only stream read; a hand-rolled `git log |
grep` counts all three kinds.

## Bootstrap — first run, read-only until the seed is confirmed

No config, or no `markTag` tag → bootstrap. Inspect first, then ask only what inspection
cannot answer.

1. **Inspect.** Subject style (`git log --format=%s -50`); how changes reach the default
   branch (a squash rewrites branch subjects, so the marker must match what lands); an
   existing marker convention, mark tag, or hand-built log to adopt as-is; where process
   lessons and direction live; command directories; `gh` and a memory store; tooling
   shipped to others.
2. **Report** what you found and which inputs and fallbacks apply.
3. **Negotiate the marker**, default `docs(process/<scope>):` or one fitting the repo's
   style, covering the squash spelling. **Prove it fires**: `marker-stream.py count --all
   --pattern '<the pattern as it will be written>'`, and `list` for one sample per lane.
4. **Confirm `processDocs` and `invariantDocs`.** Ask which docs state the repo's direction;
   ask for `capabilityEvidencePath` where step 1 found tooling.
5. **Seed** after confirmation: write the config and re-run the proof from the file; create
   the retro log with a header that points at the grammar (`retro-log.py --help`), never
   copies it, then `## Entries`; propose `<retroLogPath> merge=union` in `.gitattributes`
   with a `guards` run on the merged tree in the landing step; `git tag <markTag> HEAD`;
   then run one normal pass.

## The review

**Pre-flight — one review at a time.** This command is the only mutator of the log and the
ledger and moves a shared tag. `git fetch`, then
`git fetch origin +refs/tags/<markTag>:refs/tags/<markTag>` (a peer moves the mark by
force-push, which a plain fetch never takes), and record `git rev-parse <markTag>` and
`git rev-parse origin/<default>:<retroLogPath>`. Where the harness lists sessions, a review
of this repo (same working directory and branch) already running means stop and say so; a
read-only run, which writes nothing, goes on and names the peer in the record.
Immediately before the first write, fetch and re-read both; if either moved, rebase onto
`origin/<default>`, run the repo's commit gate on the rebased tree, re-read, then write.
Refuse only on a conflict or a red gate.

### 1. The direction and the question

Read `invariantDocs` whole, in order. These are what every finding is weighed against.
State the run's question (the framing, or the default) and the objective it bears on, in
the repo's own words where the direction names its objectives. Read each direction doc's
window too: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/core-diff.py` (one line per doc), and for
a doc with a window `core-diff.py diff <doc>`, each hunk classed **rule** (a predicate, a
scope, a decision-relevant why) or **prose** (narration, a restated rule or why, a tool's
behavior restated). Prose outrunning rules is a growth finding; two rules disagreeing at
one moment, a conflict; a rule stated where its reader never arrives, a reach finding.
`core-diff.py self` gives this command's own landings over 30 days: a file the review grew
in two runs and trimmed in none is a growth finding against the review.

### 2. The evidence — delegated

Spawn `evidence-reader` (`subagent_type: threads:evidence-reader`), handed the repo root,
`${CLAUDE_PLUGIN_ROOT}` resolved to its absolute path, the run's question, the objective it
bears on and its constraint (maintainer attention: you will write them a short block),
`markTag`, `retroLogPath`, `trigger.cluster`, `capabilityEvidencePath`, and the default
branch. Never hand it your own leaning. It reads the log, the chains, the marker stream,
the risk registry, and the capability store, and returns the picture: residual as a rate,
its concentrations with what changed near each and its exposure, how the evidence bears on
the question, the held proposals, and the log lines to write. No `Agent` tool → do its
procedure here (its file is `${CLAUDE_PLUGIN_ROOT}/agents/evidence-reader.md`) and narrate
that the incidents were read at reviewer altitude.

Two reads stay here, each one call:

- **Workarounds** (`workaroundsPath`), in your own Bash tool, since a version depends on
  the shell: `w=${CLAUDE_PLUGIN_ROOT}/scripts/workarounds.py; eval "$(python3 "$w"
  versions)" | python3 "$w" due | { eval "$(cat)"; } | python3 "$w" record; python3 "$w"
  status`, and `eval "$(python3 "$w" changelogs)"` where the register has `changelogs`. A
  read-only run drops `| python3 "$w" record`: the probes still run and print their
  answers, and nothing is written.
  A retirable workaround is a named deletion of its sites' text and its entry; a due
  re-test is a row quoting its steps; a broken probe is a `tooling` candidate. A tool
  version that moved is a cause to set beside the residual near what it governs.
- **Adherence** (`adherenceRules`), two sub-agent passes per rule above its `floor`: the
  procedure in [`commands/adherence.md`](adherence.md) §Procedure. Its `Adherence:` line
  goes to the record and the marker body; a shape `recur` routes is a candidate.

### 3. The depth gate

Go on only if one holds: a framing was given; a concentration came back; a key escaped or
ran a gate wrong since the mark; a cluster fired; a held proposal awaits; a workaround is
retirable, broken, or due; a ledger signal fired (read the ledger now, `ledgerPath`, and
adjudicate every signal that fired: promote, retire, or re-defer with the reason); or
`deep`. Otherwise **stop and say so**: the pending captures, the residual rate, the
adherence lines. A window with no concentration has bought the complete answer for the
price of step 2. The marker body carries `Opened: <framing | concentration | escape |
cluster | held | workaround | ledger | deep> — <what>`, so a later run can test which
openers led to landings that held.

### 4. Weigh each concentration against the direction

**The cases, blind first.** The picture holds no verbatim occurrence and no cause
guess. Before asking for them, write in the record, per concentration you will rule on,
your hypothesis of its cause and its fix and one line on what would change your mind. Then
resume the same reader (`SendMessage` to its agent id) asking for its held cases and its
cause guess; until then they are not in your context. The marker body carries `Blind: <the
concentration> — <hypothesis> — cases changed the ruling: yes, what | no`. Rule on what
the cases show, not on the hypothesis. The cases not arriving (no way to resume the reader,
a refusal, an answer cut off) means the step did not run: the `Blind:` line says so and
why, and you rule without the cases. Never read the occurrences yourself to stand in for
them; that puts the incidents back in your context, which the reader exists to prevent. This step is kept or dropped on its `Blind:` lines over several runs;
never harden it.

For each concentration, in order of residual weighted by exposure, decide among:

- **act now** — residual is concentrated, its likely cause is the artifact, and upcoming
  work runs through it heavily;
- **let more work narrow the cause** — the cause could still be a new area, a recent rule
  change, a model or harness change, or chance, and exposure is low enough to wait; the
  ledger gets a watch naming what would settle it;
- **leave** — the residual is a gate working with its rule present.

For an artifact you act on, the first question is **whether its approach is wrong**, not
which sentence to patch. Spawn `structure-explorer` (`subagent_type:
threads:structure-explorer`), one per artifact you act on, in parallel. Hand it the
artifact, its job (who runs it, when, what its failing costs), the objective and the
constraint the run serves (maintainer attention among them, so no structure it proposes
puts the maintainer in its own loop), the framing if one names it, and the occurrences as
`retro-log.py view --occurrences --key <k>` prints them. Never this run's leaning.

**Outside practice before a design settles.** Before any candidate that adds a rule,
replaces an artifact, carves a doc, or builds tooling is written, check how others handle
the same problem and what changed in the tools and models since the artifact was written:
open the pages (a search snippet is not a source), prefer primary sources, date and name
each. structure-explorer does this for its artifact; do it yourself for any other such
candidate. What comes back is adapted, modified, or discarded on this repo's terms, never
adopted whole, and never counted as an occurrence. The marker body carries
`Outside: <question> — <pages opened> — <changed a ruling: yes, what | no>`.

**Name the largest option before cutting.** For each artifact you act on, state the most
ambitious answer (rewrite the doc from a positive brief, re-author every string) and the
pure deletion (what goes, with nothing written in its place), each with its cost, beside
the one you recommend. A largest option that adds machinery is weighed against the
deletion first. The maintainer may want the larger
one; they cannot pick what was never put to them.

**Recommend the smallest sufficient option.** Waiting, the deletion, and the largest option
are weighed at the same weight; none is the default. A wait argues it is sufficient: the
count, the rule's state, and the named trigger that would make it act. Every mechanism in the
recommendation answers something this window measured. A part that answers nothing measured
(a threshold moved, an outcome split three ways, a second check beside the first) is left
out and named in the record as not taken. A recommendation that bundles an unsupported part
is the stacking a review exists to stop.

### 5. Place

For candidates that edit existing docs, spawn `finding-placer` (`subagent_type:
threads:finding-placer`) once with all of them, each as pattern → evidence → proposal,
naming the candidate docs (`processDocs` plus the files this run surfaced); pass
`placerModel` as the spawn's `model` when set. A `replace` candidate is not placed: its
target is the artifact itself. No `Agent` tool → place here and say so.

## Output

**Two audiences.** The maintainer reads the **decision block**, which opens the output with
nothing above it. Everything else is the **record**, for the marker commit body and the
next run. **Nothing that could change the maintainer's answer is only in the record.**

**Before anything goes in the block, re-measure its premise** against the default branch
now and the open PRs: a candidate can have landed, be building on a branch, or have gone
moot. Gone → `LANDED` or `RETIRED` in the log, not in the block.

**A run with no framing opens with its question answered**: a short reading, at direction
level, of what the window's residual says against the objectives in the direction docs,
before any decision. **The block flexes to what the run found.** Several independent decisions read as a table:
letter, the decision (the artifact and the motion, never a retro key), a
recommendation, and a why resting on what this run measured. One whole-artifact call reads
as a short paragraph: the diagnosis, the approach recommended, the largest option and its
cost, and what the residual and exposure say. Keep a whole-approach answer whole: never
cut a replacement back into patches to fit a table. Then one line, *Mechanical, land on
your word:* with the letters, and one line on what happens next if every recommendation is
taken. Held proposals from the last run lead, with their age.

Each candidate carries a **class** so the block and the log sort it: `delete` (a named
removal of whole sentences, entries, sections, or files, nothing written in their place),
`trim` (rewording toward less), `amend` (wording inside a rule, a consolidation), `rule` (a
new rule), `replace` (the artifact's approach is wrong: rewrite it or swap it for another
shape), `carve` (a new doc or a split, with its routing), `config`, `tooling` (a script, a
check at a stated rung, measured by running it over the tree and history), `motion` (a
backlog move). A doc admits only this repo's own decisions: a cause in a tool's behavior,
or a rule a hook or check already enforces, is `tooling`, `config`, or a register entry,
never prose restating it.

**The record**, below the block: per concentration, the picture's line and your ruling with
its reason; the structures structure-explorer returned, the one chosen and the ones
rejected; outside sources; the direction docs read and which bore on a ruling, with each
window's rule/prose split; the depth-gate decision; adherence; the tally
(`marker-stream.py count --all`); and the residual rate. Then any question for the maintainer, each carrying the
review's recommended answer and the default it acts on absent a reply; a question that
could move a decision is worked before the block is written, not asked under it. The
review's own misses go here and in the marker body, never as keys in the log.

## Applying

Nothing is applied without recorded consent. Under `read-only`, present only. An approved
`tooling`, `carve`, `replace`, or `motion` candidate that fits one pass may be built in the
run; the block says which. Under `apply-on-approval`, land each approved candidate as its
own marker commit. Under `apply-mechanical`, a run the maintainer is not answering also
lands the mechanical line, each as its own commit with its `LANDED` line written, and
reports it as landed with the shas; every other candidate is `HELD`. A candidate is
mechanical only if every guard passes:

- **Docs only** — every file is in `processDocs`; a companion edit elsewhere holds it.
- **An addition or a named deletion** — inserted sentences, a cross-reference clause, or the
  removal of whole sentences, entries, or sections the candidate names, with nothing
  written in their place. A rewrite or a consolidation holds.
- **Live and never landed** — the key carries no `LANDED`, `REOPENED`, or `FILED` block.
- **Not watched** — no Live ledger entry names the section.
- **Whole** — a multi-file candidate lands whole or holds whole.
- **Not protected** — nothing in `invariantDocs`; nothing deleted that is still referenced;
  no placer call of `add (unconsolidated)`.

A rewording of an enforced doc lands only after a fresh-context read compares old and new,
handed both files and never the trimmer's account; each rule it reports moved is checked
against where its reader arrives, restored if lost. A named deletion needs no such read:
its diff is the whole of it.

**A landing is a text match.** The anchor is the placer's on-disk quote, wrapped as the
file wraps it; one that does not match verbatim goes back to the placer. A value written
into a data literal is asserted to be of the literal's type first.

## On completion

- **Every commit carries `Process-Review: <today's date>`** (`git commit --trailer`;
  `land-process-commit.py` keeps it), so the next run reads none of it as change.
- **Land first, cite second.** `LANDED <sha>` and any sha the ledger cites are written
  after the push, each sha read back from the remote by subject, in a commit of its own.
  From a slice branch, a marker commit lands alone through
  `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/land-process-commit.py <sha>`, which prints the
  remote's sha to cite.
- **Write the evidence-reader's log lines**, after the pre-flight re-check: re-keys first
  (a re-key edits the key line wherever it appears), then status lines, each as its own
  entry under its key, never prose inside an occurrence:
  - `LANDED <sha> — <file §section>`, `RETIRED <date> — <why>`, `UPSTREAM <ref>`,
    `FILED <ref>` (the key stays live), `REOPENED <date> — patched in part by <sha>; open:
    <the cost driver>`. A where names a section, never a number alone.
  - `HELD <date> — <letter, class, the proposal>` for a candidate proposed and not
    answered; the date names this run's marker commit. A held candidate keyed to nothing
    goes in the ledger with *promoting signal: approval*.
  - `ADJUDICATED <date> — <ruling>` for a ruling that moves nothing (a re-rank, a burst, a
    partial patch, a cluster weighed: `cluster <path> weighed at <n>: <ruling>`).
  - `ARC <slug> [<date>] — <one line>` for one judgment across several keys; `view --arc`
    reads the trajectory, and a commit moving an arc carries `Arc: <slug>`.
  - A correction edits one line in place, in two cases only: a class line the log's own
    text contradicts, and a status line whose target moved (`new.md §X (was old.md §Y)`,
    or `(removed)`).
  Then `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/retro-log.py compact`, and the `guards`
  `retro-log` check where the repo runs it. A union merge can keep both sides of a
  corrected last line; the check names it and the repair keeps the correction.
- **Retire a key by judgment, never by age**: would a future review act differently
  without it? Re-key a mis-keyed one before retiring it.
- **The capability store**: append each retro-log placement naming it that has no entry,
  or record the decline in the ledger.
- **The ledger** holds current state, never a window's narrative; the `review-ledger` check
  is its gate. **Live** — each entry what was deferred, why, its promoting signal, and one
  `last checked: <date> — <state>` line rewritten in place; a dormant
  entry carries one `wake: <condition>` line and is re-measured only when it holds.
  **Falsifications** — kept whole. **Resolved** — a pointer to the landing commit. A number recorded carries its generating command.
- **Record `trigger.cluster`** (default 3) in the config when it was unset, so the backlog
  is read once.
- **The run's narrative** — what fired, what was held, the counts, `Opened:`, `Outside:`,
  `Adherence:`, `Blind:`, `Tally:` — goes in this run's marker commit body.
- **Advance the mark** to an ancestor of the default branch, after the landings: first
  `retro-log.py view --keys --since <the commit the log was read at>`, and give any line
  this run did not write the re-key sweep and a line in the record. Then
  `git tag -f <markTag> <commit>`, and `git push -f origin refs/tags/<markTag>` if the
  remote already holds the tag; a local-only tag stays local.
