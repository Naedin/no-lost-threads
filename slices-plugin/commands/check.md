---
description: Gap-check a slice plan — a fresh-context sub-agent handed only the plan's path, mandated to break it, never shown the drafting conversation. Re-verifies load-bearing claims against the repo, walks the change from the user's side, then hunts standard failure classes. No plan is implement-ready until it survives this.
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
writes no config and asks no bootstrap question. Two optional fields matter here:
`plansDir` resolves a bare plan name (absent, a bare name resolves under `Plans`, the
same default `/slices:capture`'s bootstrap proposes), and `checkerModel` names the model the
gap-checker runs under, passed through in §1 as an opaque string that this command
never validates. `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` is a boolean flag: when it holds a
true value (`1`, `true`), the harness pins every sub-agent to `CLAUDE_CODE_SUBAGENT_MODEL`
or the session model and removes `model` from the spawn's parameters; any other value,
including a model name, is false. When it is true and `checkerModel` is also set, omit
`model` from the spawn and say in one line that the flag overrides the field.

## 1. Spawn the checker cold

Use the `Agent` tool with this plugin's `gap-checker` agent
(`subagent_type: slices:gap-checker`). Pass **only the plan's path** — e.g. *"Try
to break the slice plan at `<path>`."* No background, no rationale, no summary of
the drafting conversation, no note about what you're unsure of. Its brief lives in
the agent definition.

When `checkerModel` is set and §0's flag is not true, pass it as the spawn's `model`
and say so in one line; when it is absent, omit `model` and say nothing. If the spawn is refused for that
model — at spawn time as the tool's error, or inside the sub-agent as an API error
naming the model — say the model could not be honored and spawn again without it.

If the `Agent` tool or the agent is unavailable, say so and run the checklist
yourself — then **narrate the tier**: a same-context check pays none of the
fresh-context premium, and the plan's ledger entry must say the check was warm.

## 2. Reconcile what comes back

Findings arrive in two kinds; keep them separate:

- **Defects** — the plan contradicts the repo, a claim failed re-verification, a
  scope hole, a failure class hit. Where the fix is unambiguous, propose the edit
  and apply it to the plan on the user's approval.
- **Questions** — anything hinging on a product or priority call. Surface these to
  the user verbatim; **never silently resolve a judgment call the checker
  escalated.** It escalated it because the call isn't yours.
- **Before an escalated question's ruling is recorded**, check it against
  `invariantDocs` in `.claude/threads.json` (absent → `docs/principles.md` and
  `docs/direction.md`). On conflict, cite the doc and surface the conflict to the
  user instead of recording the ruling.

A clean report is a first-class outcome. Don't pressure the checker for findings,
and don't pad its clean verdict with your own.

## 3. Record the check in the plan

Append one line to the plan's `## Verification ledger` section **immediately —
before fixes are discussed or approved, whatever the verdict**. The section may be
absent — a plan another drafter wrote; then create it at end of file as `/slices:draft`'s
scaffold with the record in place of the placeholder — the heading, a blank line, then
`<appended by /slices:check and by later hardening rungs; leave as-is when drafting>`,
then the record — and say you created it. The line records
that the check ran, not that its findings were resolved; a record gated on an
approval leaves no trace when the approval never comes (measured in a headless
run: full report delivered, ledger still empty). Update the counts afterward by
appending a further line if fixes land — never rewrite existing lines. The first
append into a drafted scaffold replaces its `- (none yet)` placeholder; that, and the
creation above, are the only writes into the ledger that are not appends:

```
- gap-checked at <short commit sha>, <date> — <N> defects (addressed: <n>), <M> questions (open: <m>)[, warm-context]
```

When every defect is addressed and no question remains open, flip the plan's
status line from draft to **`Status: checked — implement-ready.`** Open questions
keep it a draft; name each open question and who has to answer it. A plan with no
`**Status:**` line — another drafter's — gets the verdict in-thread and nothing
flipped; **never write the line into it**: its top of file is the adopter's, and
slices' readiness guard is a line only `/slices:draft` emits.

## Anti-patterns

- **Handing the checker anything beyond the path.** Context is contamination here.
- **Arguing the checker out of a finding** because you remember the drafting
  reasoning. That reasoning is exactly what's being audited.
- **Silently resolving an escalated question**, or downgrading a defect to a
  question to avoid an edit.
- **Skipping the ledger line.** The check that leaves no record didn't happen, as
  far as any future session can tell.
