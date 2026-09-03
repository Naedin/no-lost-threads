---
description: File a one-concern, low-trust stub the moment work is discovered — a bug noticed in passing, a scope cut, an idea — without derailing the current task. Checks the inbox for an existing stub on the same seam and amends rather than duplicates. Seconds, mid-anything.
argument-hint: "<the concern, in a phrase or a sentence>"
allowed-tools: Bash, Read, Grep, Glob, Write, Edit
---

# /slices:capture — file a stub

**The contract this command serves:** work discovered mid-task is captured
immediately as **one pickable concern**, self-disclosing as low-trust, without
derailing the task at hand. Lifecycle is expressed by directory, never by mutable
status metadata. A dropped claim gets re-discovered; a wrong gate rots invisibly —
so a blocker is a **named, checkable condition** or it is omitted entirely; the field spellings are the reference adopter's, verbatim.

Speed is a correctness property here. This runs mid-anything: one grep, one write,
one confirmation line, back to work.

## 0. Config

Read `.claude/slices.json`. If present, use `inboxDir`. If absent, this is first
use — bootstrap minimally, by inspection:

- If the repo already has an inbox-shaped home (a `Plans/inbox/`, a `backlog/`, a
  todo directory), propose adopting it as-is. Recognize, don't re-convert.
- Otherwise propose the default: `Plans/inbox/`.
- Confirm in one question, then write `.claude/slices.json` (e.g.
  `{ "inboxDir": "Plans/inbox", "plansDir": "Plans" }`) and continue. Recommend
  committing it — conventions are team-visible. Never re-ask on later runs.

## 1. One concern, deduped

Grep the inbox (filenames and stub titles) for the concern's seam before minting a
new file. **Amend an existing stub rather than duplicating it** — a second
observation of the same concern strengthens the stub's evidence; it doesn't earn a
sibling. If the argument bundles two concerns, split them: one stub each.

## 2. Write the stub

A small markdown file in `inboxDir`, kebab-case filename from the concern. **Create
`inboxDir` if it is absent** — git tracks no empty directories, so an inbox drained to
its last stub is indistinguishable from a repo that never had one, and the write fails.
Shape:

```markdown
> **Low-trust capture.** Unverified claims recorded in passing — re-verify before
> building on anything here. One concern per stub; amend rather than duplicate.

# <one-line concern>

- Blocked on: <tokens> — <rationale — omit this line entirely if nothing blocks>
- Source: <origin> <YYYY-MM-DD> — <detail — omit when the observation is this repo's own session>

<what was noticed, where, and why it might matter — a few lines. The slice's own
nouns belong here: files, symbols, the moment it surfaced.>
```

The banner is mandatory — every future reader, human or agent, is told up front
that these are captures, not decisions. `Blocked on` is a closed grammar, not
prose: tokens `slice:<plan-basename>`, `signal`, `decision`, comma-separated before
the ` — `, with the rationale after it (`none` means the same as omitting the line).
**"Not now" is not a blocker** — if the gate condition can't be named checkably, drop
the line.

`Source` is provenance, not trust. An observation carried in from outside this
repo's own sessions is still a low-trust capture, and the banner already says so;
the line exists so a later reader can tell an observation made here from one
brought in, and so the origins can be counted. Origin is one of `user`,
`repo:<name>`, or `carved:<plan-basename>`, then the date, then ` — ` and the
detail (the command, the window, the doc). How it arrived is not part of the line.

## 3. Confirm and return

One line: what was filed (or amended) and where. Then stop — the point of capture
is that the current task continues. Promotion to a plan is `/slices:draft`'s job,
later, deliberately.

## Anti-patterns

- **Derailing into the concern.** Capture is not triage, drafting, or fixing.
- **Two concerns in one stub**, or a vague stub no one could pick up cold.
- **A status field, a priority ladder, readiness metadata.** Directory is
  lifecycle; everything else drifts.
- **A `Blocked on` that means "not now."** Name the checkable gate or drop it.
- **Minting a duplicate** because grepping the inbox felt slower than writing.
