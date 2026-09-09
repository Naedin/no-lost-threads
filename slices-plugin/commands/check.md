---
description: Gap-check a slice plan — a fresh-context sub-agent handed only the plan's path, mandated to break it, never shown the drafting conversation. Re-verifies load-bearing claims against the repo, walks the change from the user's side, hunts standard failure classes, and applies every unambiguous fix in the plan itself; only a product question comes back. No plan is implement-ready until it survives this.
argument-hint: "<plan path, or its name under plansDir>"
allowed-tools: Bash, Read, Grep, Glob, Edit, Agent
---

# /slices:check — the fresh-context gap check

**The contract this command serves:** no draft is implemented until a context that
did not write it — and was deliberately denied the author's framing — has tried to
break it. The author of a draft cannot find its own gaps; fresh context is the
instrument, and **withholding is load-bearing**: the checker receives the plan's
path and nothing else. A summary of *why* the work was carved this way would
re-anchor it.

A **slice** is one coherent change argument, independently verifiable, bounded only by
the two limits a context has — **overflow** and **self-conflict**. The check reads it as
one whole, which is why the checker is handed the file and nothing else.

## 0. Config

Read `.claude/slices.json` when it exists; when it is absent, proceed — this command
writes no config and asks no bootstrap question. Four optional fields matter here:
`draftDir` and `plansDir` resolve a bare plan name — under `draftDir` first when it is
set, then `plansDir` (absent, `Plans`, the same default `/slices:capture`'s bootstrap
proposes); `checkerModel` names the model the
gap-checker runs under, passed through in §1 as an opaque string that this command
never validates; and `checkBrief` is the path of an adopter-owned markdown file of
**local gap classes and user-side lenses** — the repo's own failure classes, its
platform's accessibility rules, its data-format checks — which §1 hands to the checker
beside the plan's path. It is repo rules, not drafting context, so it does not warm the
cold read. A `checkBrief` path that does not resolve to a readable file is narrated and
the check runs on the built-in classes alone. `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` is a boolean flag: when it holds a
true value (`1`, `true`), the harness pins every sub-agent to `CLAUDE_CODE_SUBAGENT_MODEL`
or the session model and removes `model` from the spawn's parameters; any other value,
including a model name, is false. When it is true and `checkerModel` is also set, omit
`model` from the spawn and say in one line that the flag overrides the field.

## 1. Spawn the checker cold

Use the `Agent` tool with this plugin's `gap-checker` agent
(`subagent_type: slices:gap-checker`). Pass **only the plan's path** — e.g. *"Try
to break the slice plan at `<path>`."* — and, when `checkBrief` is set, one more
sentence: *"Also run the local gap classes in `<checkBrief path>`."* No background, no
rationale, no summary of the drafting conversation, no note about what you're unsure
of. Its brief lives in the agent definition, and the plan's own ledger tells it where to
start: the claim rows under a `drafted at` record are re-run verbatim before anything is
hunted, so a claim the drafter measured is checked by its command and not by a second
cold read, and the hunt goes to the sites the rows do not cover. **The checker edits the
plan.** Every defect whose fix is unambiguous is applied in place before the report is
written — the checker holds the freshest adversarial read, and a hand-off would discard
it — so the report that comes back names fixes already landed, and only a product or
priority question is still open.

When `checkerModel` is set and §0's flag is not true, pass it as the spawn's `model`
and say so in one line; when it is absent, omit `model` and say nothing. If the spawn is refused for that
model — at spawn time as the tool's error, or inside the sub-agent as an API error
naming the model — say the model could not be honored and spawn again without it.

If the `Agent` tool or the agent is unavailable, say so and run the checklist
yourself, applying the unambiguous fixes as the checker would — then **narrate the
tier**: a same-context check pays none of the fresh-context premium, and the plan's
ledger entry must say the check was warm.

## 2. Reconcile what comes back

The report ends in one verdict — **FIXED-IN-PLACE**, **NEEDS-DECISION**, or
**MIS-CARVED** — and its findings arrive in two kinds; keep them separate.

**First, read the verdict's vocabulary.** The harness loads an agent definition at
session start and this command's text at its first invocation in the session, so after
a plugin update the two can differ until the session restarts, and nothing in the ledger
can see it. A report that
ends in `holds`, `open`, or `mis-carved`, or that states unambiguous fixes without
applying them, came from an older `gap-checker` than this text. Say so in one line — the
remedy is a session restart — then do the agent's part yourself: apply the unambiguous
fixes with the fold sweep, read `holds` as FIXED-IN-PLACE and `open` as NEEDS-DECISION,
and add `agent-stale` to the record line (§3). Do not re-spawn; the same definition
would answer.

- **Defects** — the plan contradicts the repo, a claim failed re-verification, a
  scope hole, a failure class hit. **The unambiguous ones are already applied** — the
  report lists each with what it changed and the sections its fold sweep reached. There
  is no approval stop: a stop leaves a headless run with a report and no fixes, and every
  edit is in a file under git. Read the applied set and verify the fold: a fix reported
  and a section still enumerating the old consequence — scope, criteria, tensions — is a
  defect you fold now, since a partial fold plants the next check's finding. A fix you
  believe wrong is surfaced as a question with your reasoning, never reverted on your
  own — your context is the one being audited.
- **MIS-CARVED** — the checker reports that the findings are a shape problem, not
  gaps: the premise is wrong, the slice has grown past one coherent change, or it is
  superseded. It applied nothing; do not force in-place repairs onto a bad shape. Record
  the check (§3), say so, and stop; the plan goes back to a stub with the reframing
  folded in, which is `/slices:draft`'s to do or the user's to decline.
- **Questions** (the verdict is **NEEDS-DECISION**) — anything hinging on a product or
  priority call. Surface these to
  the user verbatim, with your own code-side recommendation attached — a bare relay
  is not resolving the call; **never silently resolve a judgment call the checker
  escalated.** It escalated it because the call isn't yours.
- **Before an escalated question's ruling is recorded**, check it against
  `invariantDocs` in `.claude/threads.json` (absent → `docs/principles.md` and
  `docs/direction.md`). On conflict, cite the doc and surface the conflict to the
  user instead of recording the ruling.

If a plan keeps coming back with findings after a round when you think it should be
done, stop folding them and ask whether you are solving the wrong problem one layer
down — a doc the plan restates, a term nobody defined, a contract being designed in
prose. Fix that instead, then check again.

A clean report is a first-class outcome. Don't pressure the checker for findings,
and don't pad its clean verdict with your own.

## 3. Record the check in the plan

Append one line to the plan's `## Verification ledger` section **as soon as the report
arrives, whatever the verdict — before any question is put to the user**. The section may be
absent — a plan another drafter wrote; then create it at end of file as `/slices:draft`'s
scaffold with the record in place of the drafter's — the heading, a blank line, then
`<the drafter's claim rows sit under its record line; /slices:check and later hardening rungs append>`,
then the record — and say you created it. A template may seat the section under its own
heading (`<!-- slices: ledger -->`); the record goes where the `drafted at` line is. The
line records
that the check ran, not that its questions were answered; a record gated on an
answer leaves no trace when the answer never comes (measured in a headless
run: full report delivered, ledger still empty). Update the counts afterward by
appending a further line when an answer is folded in — never rewrite existing lines. A drafter's
`drafted at` record and its rows stay as written; a plan drafted before the rows existed
carries a `- (none yet)` placeholder, and the first append replaces it. That, and the
creation above, are the only writes into the ledger that are not appends:

```
- gap-checked at <short commit sha>, <date>, slices <version> — <N> defects (addressed: <n>), <M> questions (open: <m>)[, warm-context][, agent-stale]
```

`warm-context` when the checklist ran in this context (§1); `agent-stale` when the
report's vocabulary showed an agent definition older than this text (§2). Each names a
check that paid less than the record's version promises, for the next reader.

`<version>` is the `version` field of `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json`,
read at write time (`grep '"version"' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json"`),
so a later reader can tell which copy of this command wrote the line — an installed release
or a working tree loaded with `--plugin-dir`. `${CLAUDE_PLUGIN_ROOT}` is the root of the
copy running now; never read another copy's manifest, and never a cache path found by
searching. When the file cannot be read, write `slices ?` rather than omitting the field.

**Under the record line, the claim rows** — one indented row per load-bearing claim the
checker verified, carrying the probe and not only the verdict, in the checker's own
report order. A draft-time row the checker re-ran and found unchanged is not copied
again; a row whose output moved, or that the drafter marked `unverified` and the checker
settled, is written under the check's record with its new output:

```
  - <claim> — `<generating command>` — <one line of its output>
  - <claim> — unverified: <what would settle it>
```

The record's commit sha is the baseline these rows were measured against, and the
newest record line's sha is the plan's baseline as a whole — a reader that wants one
commit takes the last `at <sha>` in the section. A later
session deciding whether the plan still holds re-runs only the rows whose cited paths
moved since that sha (`git log --oneline <sha>..HEAD -- <paths the rows cite>`), and runs
every `unverified` row before implementing. A bare "verified" with no command is a row
that cannot be re-run; do not write one.

On **FIXED-IN-PLACE**, flip the plan's
status line from draft to **`Status: checked — implement-ready.`** **NEEDS-DECISION**
keeps it a draft; name each open question and who has to answer it, and flip the line
only once the answers are folded in. **MIS-CARVED**
never flips it. A plan with no
`**Status:**` line — another drafter's — gets the verdict in-thread and nothing
flipped; **never write the line into it**: its top of file is the adopter's, and
slices' readiness guard is a line only `/slices:draft` emits.

## Anti-patterns

- **Handing the checker anything beyond the path.** Context is contamination here.
- **Arguing the checker out of a finding** because you remember the drafting
  reasoning. That reasoning is exactly what's being audited.
- **Silently resolving an escalated question**, or downgrading a defect to a
  question to avoid an edit.
- **Holding the checker's fixes for approval**, or reverting one from memory of the
  drafting. A doubt about an applied fix is a question to the user.
- **Skipping the ledger line.** The check that leaves no record didn't happen, as
  far as any future session can tell.
