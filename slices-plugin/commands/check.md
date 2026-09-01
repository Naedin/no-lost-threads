---
description: Gap-check a slice plan — a fresh-context sub-agent handed only the plan's path, mandated to break it, never shown the drafting conversation. Re-verifies load-bearing claims against the repo, walks the change from the user's side, then hunts standard failure classes. No plan is implement-ready until it survives this.
argument-hint: "<plan path>"
allowed-tools: Bash, Read, Grep, Glob, Edit, Agent
---

# /slices:check — the fresh-context gap check

**The contract this command serves:** no draft is implemented until a context that
did not write it — and was deliberately denied the author's framing — has tried to
break it. The author of a draft cannot find its own gaps; fresh context is the
instrument, and **withholding is load-bearing**: the checker receives the plan's
path and nothing else. A summary of *why* the work was carved this way would
re-anchor it.

## 1. Spawn the checker cold

Use the `Agent` tool with this plugin's `gap-checker` agent
(`subagent_type: slices:gap-checker`). Pass **only the plan's path** — e.g. *"Try
to break the slice plan at `<path>`."* No background, no rationale, no summary of
the drafting conversation, no note about what you're unsure of. Its brief lives in
the agent definition.

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

A clean report is a first-class outcome. Don't pressure the checker for findings,
and don't pad its clean verdict with your own.

## 3. Record the check in the plan

Append one line to the plan's `## Verification ledger` section **immediately —
before fixes are discussed or approved, whatever the verdict**. The line records
that the check ran, not that its findings were resolved; a record gated on an
approval leaves no trace when the approval never comes (measured in a headless
run: full report delivered, ledger still empty). Update the counts afterward by
appending a further line if fixes land — never rewrite existing lines:

```
- gap-checked at <short commit sha>, <date> — <N> defects (addressed: <n>), <M> questions (open: <m>)[, warm-context]
```

When every defect is addressed and no question remains open, flip the plan's
status line from draft to **`Status: checked — implement-ready.`** Open questions
keep it a draft; name each open question and who has to answer it.

## Anti-patterns

- **Handing the checker anything beyond the path.** Context is contamination here.
- **Arguing the checker out of a finding** because you remember the drafting
  reasoning. That reasoning is exactly what's being audited.
- **Silently resolving an escalated question**, or downgrading a defect to a
  question to avoid an edit.
- **Skipping the ledger line.** The check that leaves no record didn't happen, as
  far as any future session can tell.
