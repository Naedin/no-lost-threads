<!-- audience: human -->
# slices: the day-one pipeline kit

A Claude Code plugin carrying the day-one form of a slice pipeline: the smallest
set of habits that pays immediately in an AI-assisted repo, shipped as three
commands whose artifacts are designed to stay stable as the repo later hardens.

The unit of work is a **slice**: one coherent change argument, independently
verifiable, completable in a single fresh session.

## The three commands

- **`/slices:capture <concern>`** — file a one-concern stub in the inbox the
  moment work is discovered, without derailing the current task. Stubs carry a
  mandatory low-trust banner: they are captures, not decisions. Lifecycle is
  expressed by directory, never by status metadata; a blocker is a named,
  checkable condition or nothing; a `source:` line names where an observation
  came from when that is not this repo's own session.
- **`/slices:draft <stub>`** — promote a stub into a slice plan. The capture's
  claims are re-verified against current code before anything is built on them;
  bundled concerns are carved into separate stubs; the stub is deleted in the
  promotion. The plan ends in a **review digest** — a cold-readable Shape
  paragraph plus at most five tension points — so a human with limited time
  reviews the contestable decisions, not the whole plan.
- **`/slices:check <plan>`** — the fresh-context gap check. A sub-agent that did
  not write the plan, handed **only its path** (withholding the drafting context
  is load-bearing), tries to break it: re-verifies load-bearing claims at
  file-and-line, walks the change from the user's side, then hunts standard
  failure classes. No plan is implement-ready until it survives; every check
  leaves a ledger line in the plan.

Two policies ship as stated rules rather than machinery, deliberately:

- **The two-lane rule.** Full drafting and checking for changes to shipped
  behavior; low-risk work (docs, reversible chores) may skip the front of the
  pipeline — but whatever verification guards landing is **never** skipped.
- **Process telemetry** belongs to the [`threads`](../threads-plugin/README.md)
  plugin (marker commits, retro capture, cross-session review). The kits compose;
  neither duplicates the other.

## Config

`.claude/slices.json`, written on first use after one confirmation — a repo that
already has an inbox- or plans-shaped home gets it adopted as-is, not
re-converted:

```json
{ "inboxDir": "Plans/inbox", "plansDir": "Plans" }
```

### Carrying extra stub fields — an optional template

A repo whose stubs need fields beyond the invariant shape — an epic, a priority, a
dependency, or its own title form or banner wording — points an optional
`stubTemplate` at a markdown template instead of editing the command, so a later
`/plugin update` never forks it:

```json
{ "inboxDir": "Plans/inbox", "plansDir": "Plans", "stubTemplate": "Plans/templates/stub.md" }
```

`/slices:capture` starts from that template and **overlays** the invariants it
guarantees in every repo — a low-trust banner (present; the wording is yours), the
one-concern rule, and the closed `Blocked on:` / `Source:` grammars — auto-emitting
any your template omits and saying it did, never refusing. Everything else in the
template is carried through untouched. With no `stubTemplate`, capture writes the
built-in day-one stub, so the template is pure opt-in.

A template is an ordinary stub skeleton, read by structure: the `#` heading is the
title (put `<concern>` where the concern goes), a leading `>` blockquote is your
banner, `- Blocked on:` / `- Source:` follow the kit's grammar, and any other
`- Field:` line and the trailing prose are yours. Relationship fields — a
`Depends on:`, a `Related:` cross-reference to a set of sibling concerns — are
ordinary local fields the overlay carries through; point them at durable slugs (a
plan, an epic), not at sibling stubs, which `/slices:draft` deletes on promotion, and
amend rather than cross-reference two captures of the *same* concern. For example:

```markdown
# Inbox — <concern>

> ⚠️ **Low-trust capture** — unverified, likely stale. Re-verify before acting.

- Epic: <epic, or —>
- Priority: <p0–p3, or —>
- Depends on: <slice, or —>
- Related: <durable plan/epic slug(s), comma-separated, or —>
- Blocked on: <tokens> — <rationale — omit when nothing blocks>
- Source: <origin> <YYYY-MM-DD> — <detail — omit for this repo's own session>

<what was noticed, where, and why it might matter.>
```

## How this hardens — and why adopting it early is safe

The kit is **rung one** of each capability it carries, and its artifacts are the
contract: stub files with their banner and header, plan files with their
sections, the ledger line a check appends. Later hardening — lint that enforces
the banner, a claim ledger behind the gap check, triage over the inbox, a landing
gate — *adds* checks and appends to these same artifacts. Growth is monotonic:
adopting the kit on day one never sets up a migration, because nothing a later
rung ships changes what these files are.

## Requirements

Claude Code with sub-agent support (for `/slices:check`; the command narrates and
degrades to a warm-context check without it). No other dependencies: no scripts,
no hooks, nothing at session start. All three commands are explicit-only.

## Layout

```
slices-plugin/
  .claude-plugin/plugin.json      Plugin manifest
  commands/capture.md             /slices:capture — file a one-concern stub
  commands/draft.md               /slices:draft — stub → plan with review digest
  commands/check.md               /slices:check — fresh-context gap check
  agents/gap-checker.md           Read-only cold adversary (its brief)
```
