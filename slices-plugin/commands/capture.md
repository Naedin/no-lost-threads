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

Read `.claude/slices.json`. Use `inboxDir` for where the stub lands and
`stubTemplate` — **optional** — for a path to an adopter-supplied stub template.
`stubTemplate` is opt-in: when it is absent (this repo's own config, and the common
case) §2 writes the built-in stub unchanged; a repo sets it only to carry fields beyond
the invariant shape. If the config file is absent, this is first use — bootstrap
minimally, by inspection:

- If the repo already has an inbox-shaped home (a `Plans/inbox/`, a `backlog/`, a
  todo directory), propose adopting it as-is. Recognize, don't re-convert.
- Otherwise propose the default: `Plans/inbox/`.
- Confirm in one question, then write `.claude/slices.json` (e.g.
  `{ "inboxDir": "Plans/inbox", "plansDir": "Plans" }`) and continue. Recommend
  committing it — conventions are team-visible. Never re-ask on later runs.

Bootstrap never invents a `stubTemplate`; its absence is the correct config for a repo
that wants the built-in stub.

## 1. One concern, deduped

Grep the inbox (filenames and stub titles) for the concern's seam before minting a
new file. **Amend an existing stub rather than duplicating it** — a second
observation of the same concern strengthens the stub's evidence; it doesn't earn a
sibling. If the argument bundles two concerns, split them: one stub each.

## 2. Write the stub

A small markdown file in `inboxDir`, kebab-case filename from the concern. **Create
`inboxDir` if it is absent** — git tracks no empty directories, so an inbox drained to
its last stub is indistinguishable from a repo that never had one, and the write fails.

The stub's shape has two owners. The **invariant** elements are this command's and hold
in every repo: a low-trust banner (its *presence*, not its wording), the one-concern
rule, and the closed `Blocked on:` / `Source:` grammars. Everything else — extra leading
fields, the title form, the banner's exact text — is **local**; an adopter carries it in
an optional `stubTemplate` so `/plugin update` never forks the command. Which branch you
take depends only on whether `stubTemplate` was set in §0.

### No `stubTemplate` — the built-in stub

Write exactly this shape. Nothing here changes when a repo has no template:

```markdown
> **Low-trust capture.** Unverified claims recorded in passing — re-verify before
> building on anything here. One concern per stub; amend rather than duplicate.

# <one-line concern>

- Blocked on: <tokens> — <rationale — omit this line entirely if nothing blocks>
- Source: <origin> <YYYY-MM-DD> — <detail — omit when the observation is this repo's own session>

<what was noticed, where, and why it might matter — a few lines. The slice's own
nouns belong here: files, symbols, the moment it surfaced.>
```

### `stubTemplate` is set — overlay the invariants onto it

Read the file at `stubTemplate` and **start from it**, then ensure each invariant is
present, auto-emitting any the template omits and saying so (§3). **Never refuse a
template** — a missing invariant is filled, not a hard stop; capture is the hot path.
Read the template by structure, not a mini-language:

- **Title** — the template's `#` heading, with the concern substituted for a `<concern>`
  placeholder in it. A template with no heading gets `# <one-line concern>` prepended.
  The heading's form is the adopter's (e.g. `# Inbox — <concern>`, title-first); the
  built-in default is `# <one-line concern>`.
- **Banner** — a leading `>` blockquote. **Presence is invariant; the text is the
  template's.** Keep the template's wording verbatim; when the template has none, emit
  the built-in banner (above the body) and narrate the auto-emit. Honor the template's
  placement — a title-first template keeps its banner below the title and above the body.
- **`Blocked on:` and `Source:`** — apply the *same closed grammars as the built-in
  path* (below), whether or not the template spells the lines. The template cannot
  redefine the token sets or the omission rules: a line it names still follows the
  grammar, and a line it omits is still emitted when the concern needs one.
- **Every other `- Field:` line, and the freeform body** — **local**, carried through.
  Fill a field's value when the concern gives you one; otherwise keep the template's
  placeholder — a stub is low-trust, and the adopter's portfolio keys (an epic, a
  priority, a dependency) are filled later, not on the capture hot path. The observation
  goes in the template's body region. An HTML comment in the template is a note to its
  maintainer and is not copied into the stub.

The result is the adopter's stub with every invariant guaranteed present. An adopter
adds a field by editing their template, never this command.

### The grammars, shared by both branches

A banner is mandatory either way — every future reader, human or agent, is told up
front that these are captures, not decisions. The built-in path fixes the banner's
text; the template path fixes only its presence, so an adopter may reword it but never
drop it.

`Blocked on` is a closed grammar, not prose: tokens `slice:<plan-basename>`, `signal`,
`decision`, comma-separated before the ` — `, with the rationale after it (`none` means
the same as omitting the line). **"Not now" is not a blocker** — if the gate condition
can't be named checkably, drop the line.

`Source` is provenance, not trust. An observation carried in from outside this
repo's own sessions is still a low-trust capture, and the banner already says so;
the line exists so a later reader can tell an observation made here from one
brought in, and so the origins can be counted. Origin is one of `user`,
`repo:<name>`, or `carved:<plan-basename>`, then the date, then ` — ` and the
detail (the command, the window, the doc). How it arrived is not part of the line.

## 3. Confirm and return

One line: what was filed (or amended) and where. When a `stubTemplate` was used and an
invariant had to be auto-emitted — a missing banner, a grammar line the template didn't
carry — say so on that line, so the adopter learns their template has a gap to fill.
Then stop — the point of capture is that the current task continues. Promotion to a plan
is `/slices:draft`'s job, later, deliberately.

## Anti-patterns

- **Derailing into the concern.** Capture is not triage, drafting, or fixing.
- **Two concerns in one stub**, or a vague stub no one could pick up cold.
- **Inventing a status field, a priority ladder, or readiness metadata** in the
  built-in stub. Directory is lifecycle; everything else drifts. An adopter's own
  leading fields, carried by a `stubTemplate`, are the exception — carry them
  through, don't strip them.
- **A `Blocked on` that means "not now."** Name the checkable gate or drop it.
- **Minting a duplicate** because grepping the inbox felt slower than writing.
- **Editing this command to add an adopter's field.** Extra fields live in a
  `stubTemplate`; a command edit is overwritten by the next `/plugin update`.
