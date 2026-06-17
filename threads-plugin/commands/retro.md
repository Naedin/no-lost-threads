---
description: Retrospective pass — review the work in this conversation as process telemetry (drift, scope leak, ignored user signals, unverified claims, premature lock-in, mode confusion, stale habits). By default it runs a fresh-context sub-agent that audits the observable session record cold; `quick` runs a self-pass only. Explicit-only; never auto-fires.
argument-hint: "[quick] [optional scope note]"
allowed-tools: Bash, Read, Grep, Glob, Agent
---

# /threads:retro — retrospective pass

Review the work in **this conversation** as process telemetry: *how* it happened, not
whether the code is correct.

**Args (`$ARGUMENTS`):**
- no args → run **both** the self-pass (§1) and the fresh-context audit (§2).
- leading `quick` → **self-pass only**; skip §2.
- remaining text → optional **scope note** narrowing focus (e.g. `/threads:retro the
  dedup decision`, `/threads:retro quick this planning thread`). Default scope is the
  full session.

## 1. Self-pass (always)

Reflect on the in-scope work against these prompts:

1. Did anything surface that the plan / framing didn't anticipate?
2. Were the called-out risks (if any) borne out — and were they actually tested?
3. Repeated-trap candidate not yet recorded in this repo's process docs?
4. Did any rule prove stale, conflicting, or missing during the work?
5. Are any repo docs conflicting or confusing? Surface it — don't silently absorb it.

## 2. Fresh-context audit (skipped only with `quick`)

Hand the observable session record to a fresh sub-agent that did not do the work, so
it judges cold without the original context's anchoring.

**If it can't run, fall back — don't fail.** If the record can't be resolved (no
session id, transcript not found) or no sub-agent is available, run the self-pass
alone, say so plainly, and continue to Output. Never fabricate a record.

**Step 2a — extract the record.** Run the bundled extractor; it resolves this
session's transcript, distills it to a compact `asked → did → said` timeline, and
prints the path:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/extract-record.py"
```

If it errors or finds no transcript, take the fallback above.

**Step 2b — spawn the sub-agent** via the `Agent` tool (general-purpose). Give it the
printed record path and this brief verbatim. If the session was clean it should
return *"nothing material"* — do not pressure it for findings:

> You are auditing the observable record of a Claude Code session with **fresh
> context** — you did not do this work, so you carry none of its anchoring. Read the
> timeline at `<RECORD>` (USER = user turns, SAID = the agent's text outputs, DID =
> its tool actions, in order). It is the full sequence of what was asked → done →
> said; an agent's private reasoning is not in the record, so don't infer it or claim
> to have caught it. Judge the work **cold**, hunting the meta-issues a session tends
> to miss about itself:
> - **Drift** — did the delivered work answer what the user actually asked, or quietly substitute a different, easier question?
> - **Ignored / overridden user signals** — did the user correct, redirect, or constrain, and was it honored?
> - **Unverified claims** — facts asserted (especially load-bearing ones) with no preceding action that checked them.
> - **Motivated deferral / scope-cutting** — something dropped or punted with a rationale the evidence doesn't support.
> - **Circular or wasted work** — re-reading, re-deriving, or redoing what was already settled.
> - **Premature lock-in** — committing to a direction before the evidence justified it.
> - **Over / under-asking** — asking the user something answerable from the code, or failing to surface a genuinely user-owned decision.
> Cite the specific USER/SAID/DID events as evidence. If the session is clean, say so
> plainly — do not pad. Your reply IS the report (raw findings, no preamble).

**Step 2c — merge** the sub-agent's findings with the self-pass before presenting.

## 3. Output

Two outcomes, **both first-class**:

- **"No retro changes recommended."** Correct for clean work — do not invent findings
  because the command ran. State it and stop.
- **A punch list** of candidate doc / pattern / trap / guardrail / agent-guidance
  edits, **in-thread**, **no working-tree changes by default**. If a proposal is large
  enough that diffs aid review, present the *what* first, then the staged *how* on
  approval.

Each finding: **issue → evidence (cite the event) → cost → suggested fix**, plus the
**consolidation considered** (below).

### Amend before you add

Findings are candidates for a human to accept, reject, or refine — never auto-adopted.
Before proposing a new rule, find where process lessons live in this repo (a
`CLAUDE.md`, a patterns or traps doc, a failure catalog, a hooks dir); don't assume a
structure, and if there's none, just surface the candidates for the human to place.
Then bias, in order:

1. **Amend** an existing entry when the lesson shares a meta-principle with it.
2. **Merge** adjacent entries when one combined entry is more findable.
3. **Remove or narrow** a rule the work showed has aged out or never fired.
4. **Add a new entry** — last resort.

State the consolidation you considered (even when "new entry is right"). Bias toward
*adopt-if-it-recurs* for one-off frictions; reserve *adopt now* for recurring or
high-severity patterns.

## Anti-patterns

- **Reviewing the code instead of the process.** If you spot a bug, capture it
  elsewhere — don't pivot the retro.
- **Inventing findings on clean work.** "No changes recommended" is the goal-state.
- **Claiming to have caught internal reasoning.** You only see the observable record.
- **Auto-adopting findings**, or **adding a new rule when an existing one could absorb
  the lesson.** Amend first; let the human promote.
- **Vague findings** with no cited moment, and **only fault-finding** — record what
  worked, too.
