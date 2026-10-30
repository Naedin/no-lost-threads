---
description: Promote an inbox stub into a slice plan — re-verify the capture's claims against current code and size its frame first (every shape weighed on value and cost, the record reviewed cold), carve out anything bundled, then write a plan that ends in a review digest (a cold-readable Shape paragraph plus at most five tension points). The stub is deleted in the promotion; the plan is not implement-ready until gap-checked.
argument-hint: "<stub path, or the concern to promote> [frame: <the shape picked at a frame stop>] [frame owner: <orchestrating session>]"
allowed-tools: Bash, Read, Grep, Glob, Write, Edit, Agent
---

# /slices:draft — from low-trust stub to slice plan

**The contracts this command serves:** a capture's claims are **re-verified before
anything is built on them** — a stub is a low-trust artifact and says so on its
face. And a plan is **built for review by a human with limited time**: it ends in
a review digest — one cold-readable **Shape** paragraph, then at most five
**tension points**, each a genuinely contestable decision with the pull in both
directions. The cap is the digest's, never the plan's: the plan's Tensions section
holds every contestable call, compressed, and the digest carries the five that most
need the reviewer. The maintainer reviews the tensions, not the whole plan.

A **slice** is one coherent change argument, independently verifiable, completable
in a single fresh session — carved as large as its coherence requires and bounded only
by the two limits a context has, **overflow** and **self-conflict**; it is split at
whichever binds first, never by habit. If the stub holds more than one argument, this
command carves before it promotes.

## 0. Config

Read `.claude/slices.json` for `inboxDir` and `plansDir` (bootstrap as in
`/slices:capture` if absent — same file, same one question), and for four optional
fields. `draftDir` is where §2 writes the new plan — a repo whose drafted plans live in
a subdirectory (`Plans/active/drafted`) sets it, and `plansDir` stays the root the §1
sweep covers; absent, the plan is written in `plansDir`. `planTemplate` is a path to an
adopter-supplied plan template. `planTemplate` is opt-in:
absent (this repo's own config, and the common case), §2 writes the built-in plan
unchanged; a repo sets it only to carry sections beyond the invariant shape. Bootstrap
never invents one. A `planTemplate` path that does not resolve to a readable file is
narrated and the built-in plan is written — never refuse; the missing template is the
adopter's gap to fill. The third, `draftBrief`, is the path of an
adopter-owned markdown file of the repo's own drafting rules. Its **frame rules** apply
at §1's frame step, each at its own moment there: a **sizing rule** (where this repo's
data lives, how a harm is counted) while the harm is sized, and a **standing-shape rule**
(what the repo decides from the shape the frame leaves standing — an instrument picked
for it, a reference the plan must name) once one shape stands, never at a stop. Its
**section-filling rules** — how this repo enumerates UI states, what its test
plan must route through, which data types trigger a compatibility check — apply in §2 to
the template's local sections. Read it before §1's frame step. An unreadable path is
narrated, the frame is sized on the built-in steps alone, and the sections are filled
from their placeholders.
The fourth, `deleteCommand`, routes every delete this command performs through an
adopter-owned tool (below).

### Every delete

This command deletes docs at four sites: §1's already-closed stub and near-duplicate
loser, §3's promoted stub, §4's MIS-CARVED plan and spin-offs. With no `deleteCommand`,
each is a plain `git rm` (or removing the file, when it was never tracked). With one set,
**none is ever bare**:

```json
"deleteCommand": {
  "withTarget": "scripts/rm-doc.sh {doc} --to {target} --apply",
  "noTarget": "scripts/rm-doc.sh {doc} --unlink --apply"
}
```

- **The target.** Each site names the doc that absorbs the deleted one's references:
  the plan for a promotion, the survivor for a near-duplicate, the restored stub for the
  MIS-CARVED plan and each spin-off, and for an already-closed stub the closer's plan when
  a plan under `plansDir` closed it — none when a commit or source did. A site with a
  target runs `withTarget`, one without runs `noTarget`, with `{doc}` and `{target}`
  substituted as repo-root-relative paths, run from the repo root. A site whose key is
  absent stops there and names the missing key; a delete with a target never runs
  `noTarget`.
- **Stage first.** The doc and the target are `git add`ed whole before the command runs —
  the plan once written, a survivor once the loser's content is folded in, a restored stub
  once its reframing is folded — since a tool that repoints references reads the index.
- **The command owns the references.** With a target it repoints every inbound reference
  at the target, so §1's near-duplicate repoint is its job, not a hand edit. A claim
  row's command is not a reference: it records what ran, and the command leaves every
  ledger and frame row as it stands — a row citing the deleted path is history, and
  `rerun` reads only the newest record's rows. Its output is
  carried into the run's report whatever the exit: a list of mentions it left for review
  is walked like any other finding.
- **Its result is honoured.** Exit 0 with `{doc}` gone from the index and the tree is the
  delete done, its rewrites part of this change. Exit 0 with the doc still present means
  the command did not delete — a dry-run default without its apply flag — and the run
  stops and says so. Any other exit stops the draft at that site: surface the command's
  output verbatim, since the references it refused on are the finding, and report the
  state it left — what was written, what was not deleted. Never fall back to a bare
  delete.

## 1. Audit the premise before drafting on it

**The light lane comes first.** A concern that touches no shipped behavior — a doc, a
config value, a reversible chore, a plugin's own command text — needs no plan. Say so,
and stop here: the stub is implemented directly and the verification that guards landing
still runs. Unsure → draft.

Re-verify the stub's claims against the current tree — with commands and reads, not
recall. A section the stub heads as decided, a list of what a draft owes, and the mechanism
it proposes are claims too, checked against the code and the repo's direction docs. Before treating the concern as new, sweep `plansDir` recursively (inbox, plans,
completed) for its terms with `grep -r` or `rg --no-ignore`, never plain `rg`: a repo's
ignore file can hide its archive from ripgrep, and the sweep then misses a closed concern
in silence. A concern is often already framed under another filename. Then one of five
verdicts:

- **Still real** → carry on.
- **Real, a claim moved** → the concern stands, but a claim it rests on is false or its
  measured instance is stale. Write the claim's current measurement as a `claim moved:`
  row in the frame record (below), whose first input it is.
- **Already closed** → report what closed it (the commit, the plan, the code that now does
  it), delete the stub (§0, *Every delete*), write no plan.
- **Partly closed** → draft the remaining increment only, and say which part had landed.
- **Near-duplicate** → consolidate before drafting: pick the better-framed survivor, fold
  in anything only the loser holds, repoint every inbound link at the survivor, delete the
  loser (§0 — with `deleteCommand` set, its delete onto the survivor does the repoint),
  then draft the survivor. Never leave the loser sitting.

Two more axes, on the surviving claims. **Feasibility:** trace the mechanism end to end
in the source — "X completes via Y" is a claim, walk it — and trace it again for a shape
the frame step stands up that is not the stub's, before the site-opening pass. **Sequencing:** do not inherit
the stub's order; a capability this slice consumes makes its producer an upstream
prerequisite, drafted first, never folded in or deferred downstream.

**Size the frame before the precision work.** Everything after this — the ledger, the
criteria, the cold check — certifies the frame it is handed, and none of it asks whether
that frame is the right size. A stub records the one case someone noticed; its shape is a
claim like any other, settled here by measurement:

- **The value, in one sentence from the user's seat** — who meets this state, what it
  costs them now, what they get. A sentence that needs the stub's vocabulary to make sense
  is not one yet. It is the Shape paragraph's spine.
- **The harm, sized.** A stub's *may*, *can*, or *sometimes* is measured before anything
  is designed against it: how often the state arises and what it costs, by running the
  mechanism over the inputs that vary or by counting in the repo's own data, the
  `draftBrief`'s sizing rules (§0) saying where that lives and how it is counted. The
  measurement is a claim row like any other, so its command stays runnable: a probe
  written for it never lands in the product tree, and **the command is its source** — a
  self-contained `python3 -I -c '…'` or `bash -c '…'`, never a reference to a probe kept
  in the stub or the plan, since the writer empties that file while the command runs. A harm that cannot be sized is an `unverified:` row
  naming what would size it, never a premise. A count over a grid the repo built — a
  golden matrix, a fixture sweep — sizes **reach** (which states the change touches), not
  **prevalence** (how often users meet them); the claim says which it is. A row that
  characterizes its hits — a bucket, a label, a split — is written after reading the hits
  behind each bucket, as the site-opening pass requires (below).
- **What changed since capture.** A stub's shape was last stated at the newest commit
  that changed it (`git log -1 --no-merges --format=%h -- <stub>`; a merge only carries
  an edit made elsewhere). Two rows from that sha, each hit
  read: `since capture: code` — `git log --oneline <sha>..HEAD -- <files>`, the files
  defining what the stub names (a symbol mapped to its file); and `since capture: plans`
  — the same log over the stubs and plans the stub links, plus those under `plansDir`
  that name this stub (`grep -rl <stub filename> <plansDir>`). A hit that supplies a
  shape — a pattern now shipped, a neighbour's shape now settled — is a candidate below.
  No hits is a row too.
- **A declared block.** A `Blocked on:` the stub already carries is a row: open or
  cleared, by the condition it names. It does not stop the frame step; each shape's cost
  line says whether the shape needs what the blocker delivers (a mechanism dependency) or
  only follows it in sequence.
- **The neighbouring states.** Walk outward from the stub's case: each surface the change
  touches shown alone, beside the others, and not at all; every legitimate answer the user
  has to what the change asks of them — accept, decline, put off, ignore — and who is right
  to give each, which sizes how many users the stub's case leaves out; what undoes the
  trigger a week on. Walk today's behaviour in the same states: it is what a shape can
  regress.
- **The shapes, weighed on value and cost.** The candidates are the stub's shape; **doing
  less**; a **split by risk** — the safest piece that carries most of the value first, the
  rest a stub behind it; every **neighbour shape** the stub names or the since-capture row
  turned up — a neighbour stub's or plan's shape, an existing pattern — that would make this
  one smaller; and any other delivery of as much value with less surface. A neighbour's
  shape is a candidate here, never an Out item settled as that neighbour's decision; Scope
  may put it Out only after this weighing rejects it. Each shape carries two lines. **Value**:
  its user outcome, and what of the value sentence it gives up. **Cost**: the seams it
  touches; each mechanism it needs that does not exist yet, by name; the user states it
  must specify, counted from the walk; and each regression against shipped behaviour in a
  state the user can be in, from the walk of today's behaviour — `none` when the walk found
  none. **A shape is never chosen on value alone.** A shape that delivers as much value at
  less cost overturns the stub's; when value and cost point to different shapes — the stub's
  buys more, a cheaper one keeps most of it with fewer new mechanisms, states, or
  regressions — the trade is a product call, not the drafter's.

**Write the frame record, then have it reviewed cold.** Every frame step ends by writing
the frame into the stub as a capture update — a `## Frame` section, the one edit this
command makes to a stub it does not promote:

```markdown
## Frame

- framed at <short sha>, <date>, slices <version>
  - <claim> — `<generating command>` — <its output line>
- value: <the sentence>
- states walked: <each state the walk reached, `; `-separated, today's behaviour in each>
- shape A: <the shape> — mechanism: <how it works: what it derives or decides, from what, through which existing machinery> — value: <its user outcome; what it gives up> — cost: <seams>; new: <mechanisms, or none>; states: <n, of those walked>; regresses: <each, by state, or none>
- shape B: …
- drafter's pick: <shape> — <one line: why, on value and cost>
```

Write the `- framed at` line first, then every row — premise corrections, the harm, the
since-capture logs, the declared block — through the writer, as the ledger's are (§1's
site-opening pass): `ledger-row.py add <stub> '<claim>' '<command>'` writes under a stub's
`framed at` record, and `rerun <stub>` re-runs them.
Then the record goes to a context that has not read the drafting rationale: use the
`Agent` tool with this plugin's `frame-checker` agent (`subagent_type:
slices:frame-checker`), passing **only the stub's path** — *"Review the frame record in
`<path>`."* — plus, when `draftBrief` is set, *"Its sizing rules are in `<draftBrief
path>`."* — and *"The row re-runner is `${CLAUDE_PLUGIN_ROOT}/scripts/ledger-row.py`."*,
the variable expanded. Nothing else: not the invocation's brief, not the premise audit's
narration, not what you are unsure of; the record is the whole argument, as the plan is to
`/slices:check`. When `checkerModel` is set, pass it as the spawn's `model` unless
`CLAUDE_CODE_SUBAGENT_MODEL_FORCE` is true, and spawn again without it if it is refused.
When the agent type is not loaded but the `Agent` tool is, spawn a general-purpose agent
whose prompt is the body of `${CLAUDE_PLUGIN_ROOT}/agents/frame-checker.md` followed by
the same brief: still cold. A spawn the harness runs in the background is waited on: nothing
below runs until its report is in, and a turn may end in between. The checker re-runs the rows, runs its own since-capture and neighbour
sweep, walks today's behaviour for regressions, and **edits the record in place** — a
missed shape added, a cost line corrected — then ends in **STANDS** `<shape>` (value and
cost agree on one shape) or **CONTESTED** (more than one stands, or value and cost point
apart). Then re-read the corrected record and rewrite your pick line when a correction
took away its reason; a pick still resting on a refuted row is the anchoring this review
exists to remove. Append the review's line last, `- reviewed: cold, <verdict>[, <shape>]`.
With no `Agent` tool, review the record yourself against the checker's brief, say the
review was warm, and write `- reviewed: warm, …`.

Then one of two outcomes:

- **The shape stands** → it is the plan's frame, written as its first tension (§2): the
  shape taken, each other shape with its value and cost lines, the states it covers and
  the ones it leaves out, the harm cited by its row, who picked it, and the review's
  verdict. The `draftBrief`'s standing-shape rules (§0) run on it now, before the
  site-opening pass, so what they decide is decided once on the frame and not on the stub,
  and whatever they name is opened with the rest. A shape stands only when:
  - **this draft has a frame owner** (an orchestrating session — `frame owner:` in the
    invocation, or the session whose message asked for this draft; §2) and the frame owner
    picked it against this record: the invocation's `frame:` names it and the stub carries
    the record (re-entry, below). With a frame owner, the pick **always** follows the
    record and never precedes it: a first invocation with no record, `frame:` or not, ends
    in a frame stop, whatever the review said; or
  - **the user is the frame owner**, the review says STANDS, and the shape it stands on is
    the stub's or one the user agreed — named in `frame:`, or recorded in the stub as
    theirs. An agreed shape that is not the stub's is sized like the stub's was — the harm
    rows run against it, the walk run on it — before the record is written.
- **Otherwise a frame stop**: CONTESTED, or STANDS on a shape nobody agreed, or a frame
  owner who has not picked against this record → no ledger, no plan, and no
  standing-shape rule runs. The record stays in the stub. Present the shapes in-thread —
  each with its value and cost lines, the drafter's pick, the review's verdict — and
  return: the command's closing message is the pick request, to whichever session invoked
it, which relays it when it is not the frame owner itself. What a caller does at the
  stop — a prototype, a commit — runs after this command does. The Out-item dependency
  test (below) stops here too, whenever it finds a dependency another seam owns.

**Re-entry after a frame stop.** The invocation names the picked shape as `frame:
<shape>`, and the stub carries the `## Frame` record. The record's rows are **read, not
re-sized**, when `git log --oneline <its sha>..HEAD -- <the paths its rows cite>` is
empty; a row whose cited paths moved is re-run, and only that row, and the since-capture
row is re-run from the record's sha. Neither the walk nor the cold review runs again on a
shape the record presents, its mechanism included. A pick that is not one — a shape the
record lacks, or a `frame:` that adds mechanism its shape's line does not carry — is
weighed and walked like the others, written into the record, and reviewed cold again
before it stands. The picked shape stands — the first outcome
above — unless a re-run row, the since-capture hits, or that walk overturns it, which is a
frame stop again, naming the rows or the states that moved. A pick to block on
a dependency writes the stub's `Blocked on:` line and drafts nothing. A stub carrying a
`## Frame` record invoked with no `frame:` is a stop still waiting on its pick: re-run only
the rows whose cited paths moved, present the record's shapes again, and return. The premise audit
above still runs, since the stub's other claims are not the frame's; the record's rows
go into the ledger under the `drafted at` line through the writer (§1), each command
carrying its probe with it.

**Every artifact the draft names is opened at draft time** — a symbol, a file, a test, a
precedent ("as Y does"), a rule — and cited at file-and-line or section. A claim recalled
from memory is a gap. A "behavior X is unchanged" sentence is a negative claim: name the
test that pins it and walk the case where the new mechanism and the old path meet.

**The site-opening pass writes the ledger.** Before the plan is written, list every
production symbol, file, test, and site the draft will name; open each one with a command
(`rg -n`, `git grep`, `sed -n`, a test run). Those are the plan's **claim rows** —
`<claim> — \`<generating command>\` — <its output line>` — and a row is written only by
running its command through the writer, never typed:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ledger-row.py add <plan> '<claim>' '<command>'
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ledger-row.py add <plan> '<claim>' --unverified '<what would settle it>'
```

It runs the command in the plan's repo root, derives the output line (up to ten output
lines, each a code span, joined by `; `; more as `<n> lines, first: <line>`; none as
`no output`; a non-zero exit appended), and writes the row under the plan's newest `drafted at`
record, recounting that record's sites; the same command again replaces its row. So §2
writes the plan with its `drafted at` record and no rows, and the rows follow through the
writer — the output line comes from the run, never from memory of an earlier one, and a
row off the writer's form is the visible exception `/slices:check` names first. Every
command runs with the plan file itself emptied, so a sweep over a tree that holds the
plan never matches the pattern its own row quotes. A row's command
is one whole command: a run piped through `head` or `tail` is not a row, and two probes
are two rows. A characterization
of the hits — `doc comments only`, `all 12 sites`, `none outside Tests` — belongs in the
claim, written after reading every hit the command returns, never a sample; a read that
contradicts it rewrites the claim, never narrows the command to fit it. **A count is a row
of its own.** A number the plan states about a set of sites, anywhere in it — a Note's
"all six tests", a test plan's "the 21 existing cases", a claim's "two consumers" — comes
from a command that counts (`rg -c <file>`, `… | wc -l`), never from tallying a listing,
and the writer records it as a bare number: `<claim> — \`rg -c '@Test' <file>\` —
\`21\``. The prose that uses the count repeats that number. A site the pass could not open
is an `unverified` row, never a sentence in the body. The rows are what `/slices:check`
re-runs before it hunts, against the current tree.

A stub that bundles several concerns gets carved into separate stubs first, and exactly
one is promoted.

**The split test.** A second concern is carved into its own stub when it brings any one
of its own dependency, its own verification run, or an independently useful landing
boundary; a concern that shares all three with the slice is the same change argument and
stays bundled, and a split that can name none of the three is not made. A *verification
run* is a distinct harness, fixture set, or tooling — not a distinct acceptance criterion
inside the same session. A landing boundary is *independently useful* when the piece,
landed alone with nothing after it, is worth landing: a user meets the change or a
process uses it. A doc amendment the change itself requires is part of its argument
whatever commit carries it. The test separates arguments; one argument too large for a
session is split by the size bound above — overflow or self-conflict — not by this test.

**A deferral written into the plan is a stub, not a sentence.** Any "until X lands", "a
later slice may absorb this", or "interim shape" note the draft writes about something it
ships becomes its own stub in the same change, `Blocked on: slice:<X> — <why>` when a
named slice clears it. A sentence in the plan body is found by nobody; a stub is found by
the next triage.

**Every Out item answers the dependency test before it is written:** *which in-scope
surface is wrong, or hands the user a chore, without this?* Walk the slice's own copy,
behavior, and timing against the item's absence. Copy that hands the user something to
remember, track, or time — "test after 8 PM", "check back tomorrow", "keep an eye on" — is
the tell that a capability was deferred, and copy rules that forbid promising an unshipped
capability only make it quieter, since the copy is then written as instructions and every
string check still passes. The answer is recorded on the item's line, so a reader sees it,
in one of three forms, and only these go Out:

- `- Out: <item> — without it: none` — no surface needs it; a deferral, to a stub as above.
  A neighbour's shape goes Out only after the frame's weighing rejected it as a candidate;
  one the weighing never saw sends the draft back to the frame step.
- `- Out: <item> — without it: none (refinement: <what improves>)` — a surface behaves
  differently without it but stays correct and honest, and its copy asks the user to
  carry nothing.
- `- Out: <item> — without it: <surface> (limit: <why no capability exists>)` — no
  capability in any seam's reach could supply it (the system cannot observe or reach what
  it needs), so no slice removes the chore. The surface still owes copy that keeps the
  chore to the moment it matters. A limit is a claim: when a capability that would supply
  it is merely unbuilt, it is a dependency.

Any other answer makes the item a **dependency**, never Out:

- **Inside the slice's reach** — what it needs lives in code this slice may change and the
  split test (below) names nothing of its own → pulled into Scope's In, the call written as
  a tension.
- **Another seam owns it** — a capability whose code, plan, or stub is not this slice's,
  or pulling it in brings its own dependency, verification run, or landing boundary → the
  slice cannot meet it alone, and that is not the drafter's call. **A frame stop**, and no
  plan is written: the `## Frame` record carries the dependency as a row, `- dependency: <item>
  — needed by: <the in-scope surface> — owned by: <the seam, by path>`, and presents two
  shapes — pull it in, or block on it, where the producer is drafted first (the sequencing
  rule above) and this stub takes `Blocked on: slice:<its plan>`. The frame owner (§2's
  `frame owner:`, or the user) picks. Routing the item to a stub and drafting on is the
  failure this stop exists to prevent: the slice ships a surface that quietly hands the
  user the deferred chore.

## 2. Write the plan

One markdown file in `draftDir` — `plansDir` when it is unset — named for the slice. The
plan's shape has two owners,
under the same overlay contract `/slices:capture` uses for the stub. The **fixed
invariant** sections are this command's and hold in every repo: `## Shape`, `## Scope`,
`## Acceptance`, `## Tensions`, the `## Verification ledger` scaffold, and the
`**Status:**` readiness guard. Everything else — leading metadata, a sizing check, a
test plan, the adopter's own ledgers — is **local**, carried by an optional
`planTemplate` so `/plugin update` never forks the command. Which branch you take
depends only on whether `planTemplate` was set in §0.

### No `planTemplate` — the built-in plan

Write exactly this shape. Nothing here changes when a repo has no template:

```markdown
# <slice title>

**Status: draft — not implement-ready until it survives `/slices:check`.**

## Shape

<one cold-readable paragraph: what changes, why now, what its user gets>

## Scope

- In:
- Out: <item> — without it: none

## Acceptance

- [ ] <criterion> — verified by: `<the exact command or observation>`

## Tensions

<every decision made in this plan that is genuinely contestable, one compressed entry
each, stated as the call taken, with the pull in both directions and the lever — what
overriding it costs: a cheap re-carve, or a reshaped slice. No cap: compress entries,
never omit one. This section is what gets reviewed; the digest (§4) carries the five
that most need the reviewer>

## Verification ledger

<the drafter's claim rows sit under its record line; /slices:check and later hardening rungs append>
- drafted at <short commit sha>, <date>, slices <version> — <N> sites opened (unverified: <n>)[, frame owner: <session>]
  - <claim> — `<generating command>` — <its output line>
  - <claim> — unverified: <what would settle it>
```

The record is written with `0 sites opened (unverified: 0)`, and the rows under it come
from `ledger-row.py add`, which keeps the counts (§1).

`<version>` is the `version` field of `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json`,
read at write time, as `/slices:check` reads it for its own line; `slices ?` when the file
cannot be read. The record's sha is the baseline the rows were measured against.
`frame owner:` names the session that started this draft — the invocation's `frame owner:`,
else the one whose message asked for it — by the handle a later session can reach it at; a draft the user started omits
it, and the user is the frame owner. `/slices:check` sends its hand-up there when a round
stops.
A re-draft — a carve drafted again from its stub, or a plan whose file already carries a
ledger — appends its `drafted at` record after the records already there, never above them.
The newest `drafted at` is the frame baseline `/slices:check` counts rounds, no-decay, and
`touched:` from, so the earlier records stay as history without being read as this
document's rounds.

### `planTemplate` is set — overlay the invariants onto it

Read the file at `planTemplate` and **start from it**. Resolve each invariant section
in this order, auto-emitting any the template lacks and saying so (§4). **Never refuse
a template.** Read it by structure, not a mini-language:

- **The title.** The template's H1 is the title, its placeholder replaced by the slice
  title, as the stub overlay does with `<concern>`.
- **By role marker first.** A template spells an invariant in its own words by marking
  the role on the heading line — `## Summary <!-- slices: shape -->`. The roles are
  exactly `shape`, `scope`, `acceptance`, `tensions`, and `ledger`. The marker is
  **consumed, never written**: resolve the role from it and write the heading without
  it; an HTML comment in a template is a note to its maintainer and is not copied into
  the plan. A marker naming any other role — `status`, a misspelling — is ignored for
  that heading, which is then local, and the run says so.
- **Then by slices' own heading.** A heading line that is exactly `## Shape`,
  `## Scope`, `## Acceptance`, or `## Tensions` is that invariant; a heading that merely
  contains the word — `## Acceptance Criteria`, `## Draft tensions` — is not, and
  resolves only by marker.
- **Auto-emit the rest.** An invariant neither rule resolves is written in slices' own
  spelling after the last of Shape, Scope, Acceptance, and Tensions the template does
  carry — directly after the `**Status:**` line when it carries none of them — and
  narrated. A
  template with no markers therefore gets slices' spelling beside its own — a
  `## Summary` and a `## Shape` both present — and the narration names the duplicate
  and the marker syntax that resolves it.
- **The status line takes no marker and has a fixed place.** The `**Status: draft …**`
  line is written immediately under the H1, before any template block — a template with
  no H1 gets `# <slice title>` prepended first, as the stub overlay does. **The ledger
  has a fixed place unless the template names one.** The `## Verification ledger`
  scaffold — the heading, the note line, the `drafted at` record, the claim rows — is
  written at end of file. A template heading that is exactly `## Verification ledger`,
  or one carrying `<!-- slices: ledger -->` — an adopter's `## Claim ledger` that its
  own finalize step reads — is the scaffold's place instead: resolved there, its body
  replaced by the scaffold's note, record, and rows, narrated when it is not the last
  section. Any other template heading naming the ledger or the status is local; when it
  carries a marker naming no role, the ignored marker is narrated, and an unmarked one —
  `## Status`, an unmarked `## Claim ledger` — passes in silence and is filled as its
  placeholder says.
- **Fill.** Under a resolved heading write slices' body shape — the Shape paragraph,
  `- In:` / `- Out:`, `- [ ] … — verified by:` criteria, multi-line tensions — replacing
  only the placeholder text between headings. Sub-headings under a resolved heading are
  structure, carried through: write slices' body under the sub-heading that names its
  item (Scope's In and Out under an adopter's `### In scope` / `### Out of scope`), and
  under the resolved heading otherwise.
- **Every local section is filled too — a plan is drafted whole or not at all.** Its
  placeholder is the instruction: fill it as the placeholder and the `draftBrief` (§0)
  say, from the code you read in §1, with the same discipline as the invariants (every
  named artifact opened, every command run). The one exception is a section whose
  placeholder names another writer or says to omit it at draft time — a ledger another
  command appends, a status table a closeout fills, a section the template itself says to
  drop when nothing qualifies. Those are carried through untouched or omitted as told, and
  the run says which. A local section you could not fill from the evidence at hand is left
  with its placeholder and named in §4, never silently.

The result is the adopter's whole plan with every invariant guaranteed present. An
adopter adds a section by editing their template, adds a filling rule by editing their
brief, and never edits this command.

### Both branches

Every acceptance criterion names the exact command or observation that will verify
it — a criterion that can't say how it's checked isn't one yet. A command written into
a criterion is one you ran against the current tree, verbatim, and walked every hit of;
a negative criterion ("output contains no X") pairs with a liveness condition — the exit
code or a positive line proving the command ran — or an aborted command satisfies it by
printing nothing. A tension entry states the call taken, the pull each way, and the
lever: what overriding it costs. Tensions are decided, never open; anything unresolved
is a question for the check, not a tension. The Tensions section opens with the frame (§1). The `Verification ledger` section holds the
site-opening pass's rows under a `drafted at` record when the plan is written: the gap
check *appends* to it — its own record line and rows — so the plan format never
migrates, and a draft-time row is re-run rather than re-hunted.

## 3. Promote — delete the stub

The stub is deleted in the same change that creates the plan, once the plan is written
— with `deleteCommand` set, onto the plan as its target (§0). Provenance rides in
the plan (one line naming the stub it came from); the low-trust artifact doesn't.
Amend the stub instead only when drafting revealed the premise needs reframing —
that's a capture update, not a promotion.

## 4. Close with the digest

End in-thread with the review digest — the Shape paragraph verbatim from the plan, then
at most five tension points, ranked by how much the maintainer's judgment could move
them; the rest ride the plan's section only. The cap is the digest's: a later session
cold-reading the plan needs every tension, and a human with limited time needs the five
that matter. Then run `/slices:check` on the plan in this same session
without being asked; a plan is not done drafting until a fresh context has tried to break
it. Invoke it as a skill; if the harness cannot load it that way, follow
`${CLAUDE_PLUGIN_ROOT}/commands/check.md` directly — the same plugin root this command
runs from, never an installed copy elsewhere on disk, so the check that runs is the one
this draft shipped with. If the check returns **MIS-CARVED**, the plan does not stand: restore the stub from the
last commit that carries it, with the check's reframing folded in, delete the plan and any
spin-offs that only made sense under the carve — each onto the restored stub (§0) — and
say so: the stub is the tracker again.
If the check **stops** (its §2 *Stop before folding*), the plan stands as a draft at the
round's baseline and the hand-up has gone to the frame owner: fold nothing and check
nothing further until its answer comes back.
When a `planTemplate` was used and an invariant had to be auto-emitted, a marker was
ignored, or a duplicate spelling was written, say so in one line each, so the adopter
learns their template has a gap to fill.
Do not begin implementing in this session's flow unless the user says so; the
check exists precisely because this context just wrote the plan.

## Anti-patterns

- **Drafting on unverified stub claims.** The audit (§1) is the point.
- **Designing inside the stub's one case.** The frame is sized (§1) before the ledger is
  spent on it; a cold check that finds it too narrow has thrown that ledger away.
- **Picking the frame on value alone.** The higher-value shape always wins that
  comparison; the convergence cost and the regressions it carries are what the cheaper
  shape avoids, and the trade is the frame owner's.
- **A plan with no tensions.** Zero contestable decisions means either the slice
  is trivial or the contestable calls were made silently. Say which.
- **More than five tensions in the digest** — that's the whole plan re-litigated in
  chat, the reading cost the digest exists to remove. The plan's section is uncapped;
  the digest is the filter, and omitting a tension from the section to fit the digest is
  the inverse failure.
- **Promoting a bundle.** One slice per plan; carve first.
- **An Out item the slice leans on.** An item without which an in-scope surface is wrong
  or hands the user a chore is a dependency (§1), pulled in or stopped on, never deferred —
  unless no capability could supply it, which is a named limit.
- **Leaving the stub behind** as a stale twin of the plan.
