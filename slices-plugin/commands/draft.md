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
in a single fresh session. If the stub holds more than one, this command carves
before it promotes.

## 0. Config

Read `.claude/slices.json` for `inboxDir` and `plansDir` (bootstrap as in
`/slices:capture` if absent — same file, same one question).

## 1. Audit the premise before drafting on it

Re-verify the stub's claims against the current tree — with commands and reads,
not recall. Is the concern still real? Already closed? Partly closed? A stub whose
premise died gets reported and deleted, not drafted; a stub that bundles several
concerns gets carved into separate stubs first, and exactly one is promoted.

## 2. Write the plan

One markdown file in `plansDir`, named for the slice. Template:

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
