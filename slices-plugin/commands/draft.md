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
directions. The maintainer reviews the tensions, not the whole plan.

A **slice** is one coherent change argument, independently verifiable, completable
in a single fresh session — carved as large as its coherence requires and bounded only
by the two limits a context has, **overflow** and **self-conflict**; it is split at
whichever binds first, never by habit. If the stub holds more than one argument, this
command carves before it promotes.

## 0. Config

Read `.claude/slices.json` for `inboxDir` and `plansDir` (bootstrap as in
`/slices:capture` if absent — same file, same one question), and for `planTemplate` —
**optional** — a path to an adopter-supplied plan template. `planTemplate` is opt-in:
absent (this repo's own config, and the common case), §2 writes the built-in plan
unchanged; a repo sets it only to carry sections beyond the invariant shape. Bootstrap
never invents one. A `planTemplate` path that does not resolve to a readable file is
narrated and the built-in plan is written — never refuse; the missing template is the
adopter's gap to fill.

## 1. Audit the premise before drafting on it

Re-verify the stub's claims against the current tree — with commands and reads,
not recall. Is the concern still real? Already closed? Partly closed? A stub whose
premise died gets reported and deleted, not drafted; a stub that bundles several
concerns gets carved into separate stubs first, and exactly one is promoted.

**The split test.** A second concern is bundled only when it brings its own dependency,
its own verification run, or an independently useful landing boundary; a concern that
shares all three with the slice is the same change argument, and a split that can name
none of the three is not made. A *verification run* is a distinct harness, fixture set,
or tooling — not a distinct acceptance criterion inside the same session. A doc
amendment the change itself requires is part of its argument whatever commit carries
it.

## 2. Write the plan

One markdown file in `plansDir`, named for the slice. The plan's shape has two owners,
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

<at most five decisions made in this plan that are genuinely contestable, each
with the pull in both directions — this section is what gets reviewed>

## Verification ledger

<appended by /slices:check and by later hardening rungs; leave as-is when drafting>
- (none yet)
```

### `planTemplate` is set — overlay the invariants onto it

Read the file at `planTemplate` and **start from it**. Resolve each invariant section
in this order, auto-emitting any the template lacks and saying so (§4). **Never refuse
a template.** Read it by structure, not a mini-language:

- **The title.** The template's H1 is the title, its placeholder replaced by the slice
  title, as the stub overlay does with `<concern>`.
- **By role marker first.** A template spells an invariant in its own words by marking
  the role on the heading line — `## Summary <!-- slices: shape -->`. The roles are
  exactly `shape`, `scope`, `acceptance`, `tensions`. The marker is **consumed, never
  written**: resolve the role from it and write the heading without it; an HTML comment
  in a template is a note to its maintainer and is not copied into the plan. A marker
  naming any other role — `ledger`, `status`, a misspelling — is ignored for that
  heading, which is then local, and the run says so.
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
- **The ledger and the status line take no marker and have fixed places.** The
  `**Status: draft …**` line is written immediately under the H1, before any template
  block — a template with no H1 gets `# <slice title>` prepended first, as the stub
  overlay does; the `## Verification ledger` scaffold — its three fixed lines — is
  written at end of file. A template heading that is exactly `## Verification ledger`
  is the scaffold's place instead: resolved there, its body replaced by the scaffold's
  two fixed lines, narrated when it is not the last section. Any other template heading
  naming the ledger or the status is local; when it carries a marker, the ignored marker
  is narrated, and an unmarked one — the adopter's own `## Claim ledger`, `## Status` —
  passes in silence.
- **Fill.** Under a resolved heading write slices' body shape — the Shape paragraph,
  `- In:` / `- Out:`, `- [ ] … — verified by:` criteria, multi-line tensions — replacing
  only the placeholder text between headings. Sub-headings under a resolved heading are
  structure, carried through: write slices' body under the sub-heading that names its
  item (Scope's In and Out under an adopter's `### In scope` / `### Out of scope`), and
  under the resolved heading otherwise.
- **Every local section** is carried through with its placeholder body untouched.
  Filling it is the adopter's own commands' job — a local ledger, a sizing check, a
  status table each have a writer that is not this command — so the overlay never
  writes into one.

The result is the adopter's plan with every invariant guaranteed present. An adopter
adds a section by editing their template, never this command.

### Both branches

Every acceptance criterion names the exact command or observation that will verify
it — a criterion that can't say how it's checked isn't one yet. The `Verification
ledger` section ships empty by design: later rungs (the gap check's record, an
eventual claim ledger) *append* to it, so the plan format never migrates.

## 3. Promote — delete the stub

The stub is deleted in the same change that creates the plan. Provenance rides in
the plan (one line naming the stub it came from); the low-trust artifact doesn't.
Amend the stub instead only when drafting revealed the premise needs reframing —
that's a capture update, not a promotion.

## 4. Close with the digest

End in-thread with the review digest — the Shape paragraph and the tension points,
verbatim from the plan — and one pointer: run `/slices:check` before implementing.
When a `planTemplate` was used and an invariant had to be auto-emitted, a marker was
ignored, or a duplicate spelling was written, say so in one line each, so the adopter
learns their template has a gap to fill.
Do not begin implementing in this session's flow unless the user says so; the
check exists precisely because this context just wrote the plan.

## Anti-patterns

- **Drafting on unverified stub claims.** The audit (§1) is the point.
- **A plan with no tensions.** Zero contestable decisions means either the slice
  is trivial or the contestable calls were made silently. Say which.
- **More than five tensions** — that's the whole plan re-litigated, which is the
  reading cost the digest exists to remove.
- **Promoting a bundle.** One slice per plan; carve first.
- **Leaving the stub behind** as a stale twin of the plan.
