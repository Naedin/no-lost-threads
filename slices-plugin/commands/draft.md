---
description: Promote an inbox stub into a slice plan — re-verify the capture's claims against current code first, carve out anything bundled, then write a plan that ends in a review digest (a cold-readable Shape paragraph plus at most five tension points). The stub is deleted in the promotion; the plan is not implement-ready until gap-checked.
argument-hint: "<stub path, or the concern to promote>"
allowed-tools: Bash, Read, Grep, Glob, Write, Edit
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
`/slices:capture` if absent — same file, same one question), and for three optional
fields. `draftDir` is where §2 writes the new plan — a repo whose drafted plans live in
a subdirectory (`Plans/active/drafted`) sets it, and `plansDir` stays the root the §1
sweep covers; absent, the plan is written in `plansDir`. `planTemplate` is a path to an
adopter-supplied plan template. `planTemplate` is opt-in:
absent (this repo's own config, and the common case), §2 writes the built-in plan
unchanged; a repo sets it only to carry sections beyond the invariant shape. Bootstrap
never invents one. A `planTemplate` path that does not resolve to a readable file is
narrated and the built-in plan is written — never refuse; the missing template is the
adopter's gap to fill. A second optional field, `draftBrief`, is the path of an
adopter-owned markdown file of **section-filling rules** — how this repo enumerates UI
states, what its test plan must route through, which data types trigger a compatibility
check. Read it before §2 and apply it when filling the template's local sections. An
unreadable path is narrated and the sections are filled from their placeholders alone.

## 1. Audit the premise before drafting on it

**The light lane comes first.** A concern that touches no shipped behavior — a doc, a
config value, a reversible chore, a plugin's own command text — needs no plan. Say so,
and stop here: the stub is implemented directly and the verification that guards landing
still runs. Unsure → draft.

Re-verify the stub's claims against the current tree — with commands and reads, not
recall. Before treating the concern as new, sweep `plansDir` recursively (inbox, plans,
completed) for its terms with `grep -r` or `rg --no-ignore`, never plain `rg`: a repo's
ignore file can hide its archive from ripgrep, and the sweep then misses a closed concern
in silence. A concern is often already framed under another filename. Then one of four
verdicts:

- **Still real** → carry on.
- **Already closed** → report what closed it (the commit, the plan, the code that now does
  it), delete the stub, write no plan.
- **Partly closed** → draft the remaining increment only, and say which part had landed.
- **Near-duplicate** → consolidate before drafting: pick the better-framed survivor, fold
  in anything only the loser holds, repoint every inbound link at the survivor, delete the
  loser, then draft the survivor. Never leave the loser sitting.

Two more axes, on the surviving claims. **Feasibility:** trace the mechanism end to end
in the source — "X completes via Y" is a claim, walk it. **Sequencing:** do not inherit
the stub's order; a capability this slice consumes makes its producer an upstream
prerequisite, drafted first, never folded in or deferred downstream.

**Every artifact the draft names is opened at draft time** — a symbol, a file, a test, a
precedent ("as Y does"), a rule — and cited at file-and-line or section. A claim recalled
from memory is a gap. A "behavior X is unchanged" sentence is a negative claim: name the
test that pins it and walk the case where the new mechanism and the old path meet.

**The site-opening pass writes the ledger.** Before the plan is written, list every
production symbol, file, test, and site the draft will name; open each one with a command
(`rg -n`, `git grep`, `sed -n`, a test run) and keep the command and one line of its
output. Those pairs are the plan's **claim rows** — `<claim> — \`<generating command>\` —
<one line of its output>` — and §2 writes them into the ledger under a `drafted at` record
line. A site the pass could not open is a row marked `unverified: <what would settle it>`,
never a sentence in the body. The rows are what `/slices:check` re-runs before it hunts,
so write each to be re-run: the exact command, verbatim, against the current tree. The
rule in prose failed to hold on its own; the rows are the same rule with a row to show
for it.

A stub that bundles several concerns gets carved into separate stubs first, and exactly
one is promoted.

**The split test.** A second concern is bundled only when it brings its own dependency,
its own verification run, or an independently useful landing boundary; a concern that
shares all three with the slice is the same change argument, and a split that can name
none of the three is not made. A *verification run* is a distinct harness, fixture set,
or tooling — not a distinct acceptance criterion inside the same session. A doc
amendment the change itself requires is part of its argument whatever commit carries
it.

**A deferral written into the plan is a stub, not a sentence.** Any "until X lands", "a
later slice may absorb this", or "interim shape" note the draft writes about something it
ships becomes its own stub in the same change, `Blocked on: slice:<X> — <why>` when a
named slice clears it. A sentence in the plan body is found by nobody; a stub is found by
the next triage.

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
- Out:

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
- drafted at <short commit sha>, <date>, slices <version> — <N> sites opened (unverified: <n>)
  - <claim> — `<generating command>` — <one line of its output>
  - <claim> — unverified: <what would settle it>
```

`<version>` is the `version` field of `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json`,
read at write time, as `/slices:check` reads it for its own line; `slices ?` when the file
cannot be read. The record's sha is the baseline the rows were measured against.

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
is a question for the check, not a tension. The `Verification ledger` section holds the
site-opening pass's rows under a `drafted at` record when the plan is written: the gap
check *appends* to it — its own record line and rows — so the plan format never
migrates, and a draft-time row is re-run rather than re-hunted.

## 3. Promote — delete the stub

The stub is deleted in the same change that creates the plan. Provenance rides in
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
this draft shipped with. If the check returns **MIS-CARVED**, the plan does not stand: restore the stub with
the check's reframing folded in, delete the plan and any spin-offs that only made sense
under the carve, and say so — the stub is the tracker again.
When a `planTemplate` was used and an invariant had to be auto-emitted, a marker was
ignored, or a duplicate spelling was written, say so in one line each, so the adopter
learns their template has a gap to fill.
Do not begin implementing in this session's flow unless the user says so; the
check exists precisely because this context just wrote the plan.

## Anti-patterns

- **Drafting on unverified stub claims.** The audit (§1) is the point.
- **A plan with no tensions.** Zero contestable decisions means either the slice
  is trivial or the contestable calls were made silently. Say which.
- **More than five tensions in the digest** — that's the whole plan re-litigated in
  chat, the reading cost the digest exists to remove. The plan's section is uncapped;
  the digest is the filter, and omitting a tension from the section to fit the digest is
  the inverse failure.
- **Promoting a bundle.** One slice per plan; carve first.
- **Leaving the stub behind** as a stale twin of the plan.
