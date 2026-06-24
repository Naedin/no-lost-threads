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

**Step 2a — extract the record.** Run the bundled extractor; it resolves this
session's transcript, distills it to a compact `asked → did → said` timeline, and
prints the path:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/extract-record.py"
```

**If it fails, surface why — then fall back to the self-pass; never hard-fail or
fabricate a record.** Don't degrade silently: tell the user (a) what failed, (b) the
fix, (c) that you're running the self-pass only. Read the command's stderr and match:
- **`python3: command not found`** (or similar) → Python 3 isn't installed / on
  `PATH`, and the audit needs it. Suggest installing Python 3 (on Windows the
  interpreter may be `python` or `py`), or using `/threads:retro quick` to skip the
  audit deliberately.
- **`CLAUDE_CODE_SESSION_ID is not set`** → this client didn't expose the session id,
  so the transcript can't be auto-located. Note they can pass a transcript path to the
  script directly if they know it.
- **`no transcript found … set CLAUDE_CONFIG_DIR`** → their Claude data dir is
  non-default; suggest setting `CLAUDE_CONFIG_DIR`.

Likewise, if the `Agent` tool or the `retro-auditor` agent isn't available (Step 2b),
fall back the same way.

**Step 2b — spawn the sub-agent.** Use the `Agent` tool with the `retro-auditor` agent
(this plugin's read-only auditor; `subagent_type: threads:retro-auditor`). Its brief
lives in the agent definition — pass it only the printed record path, e.g. *"Audit the
observable session record at `<RECORD>`."* If the session was clean it should return
*"nothing material"* — do not pressure it for findings.

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
