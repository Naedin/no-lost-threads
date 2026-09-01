<!-- audience: human -->
# threads: process tooling for Claude Code

A Claude Code plugin for keeping the threads of your work from getting lost. Two
commands, one loop: **`/threads:retro`** reviews a single session, and
**`/threads:process-review`** reads what accumulates across sessions.

## `/threads:retro` — a process retrospective

Reviews the work in your current session as **process telemetry** — *how* the work
happened, not whether the code is correct. It catches the meta-issues a session tends
to miss about itself: drift, scope leak, ignored user signals, unverified claims,
premature lock-in, mode confusion, and stale workflow habits.

**Explicit invocation only.** It's a command, not a skill — it runs only when you type
`/threads:retro`, and never auto-fires on trigger words.

### What it does

- **Fresh-context audit (default):** hands a **fresh-context sub-agent** the observable
  record of the session (`what was asked → what was done → what was said`) and asks it
  to judge the work cold — surfacing the anchoring-driven issues a self-reflection
  structurally can't see. This is the headline: most retros only self-reflect; this one
  reads the session cold. If it can't run (no transcript, no sub-agent), it degrades to
  the self-pass instead of failing.
- **Self-pass:** a fast reflection on the in-scope work while context is hot. Runs as
  part of every pass — and is the *only* detection pass under `/threads:retro quick`.
- **Placement (both modes):** a second sub-agent reads your process docs cold and says
  *where* each finding belongs — amend this section, merge these two, narrow that rule,
  or add new. Deciding that well means reading the target doc, and the context that just
  did the work is the one least able to afford it; left there, "amend" reliably degrades
  into "append." Because retro runs often, this pass is time-boxed by design: it's handed
  your process-doc list rather than rediscovering your repo, and an add it isn't sure
  about is flagged for `/threads:process-review` to reconcile later.
- **Capture, not apply:** findings are appended to a **retro log** in your repo rather
  than landed on the spot. A retro fires at the end of a session, when context is at its
  largest and applying an edit costs the most — and a session that ends with the output
  unread loses everything it found. `/threads:process-review` adjudicates the log later,
  in the fresh context that decision actually wants. If you'd rather land something
  immediately, say so and it lands.
- **"If it recurs" becomes measurable.** The placer gives each finding a short,
  domain-free key and checks it against the log, so *adopt if it recurs* is settled by
  looking rather than by hoping — the second time a friction shows up, retro says so and
  promotes it, citing the first.

**Findings are candidate process changes for you to review.** They're surfaced in-thread for you to
accept, reject, or refine — the placement proposal included. Capturing one isn't adopting
it: the entry changes no rule. The point: an agent reviewing its own work shouldn't
silently rewrite your process docs. *You* decide what gets promoted.

### Usage

```
/threads:retro                      # default: self-pass + fresh-context audit
/threads:retro quick                # skip the audit (placement still runs)
/threads:retro the dedup decision   # narrow the scope
/threads:retro quick this whole planning thread
```

### Cost

The default spawns two sub-agents: one reads your whole session transcript, so it can
use a meaningful number of tokens; the placer reads the named process docs and nothing
else — not your source, tests, or backlog — and runs only when there's something to
place. **`/threads:retro quick`** skips the first. A clean session with no findings
spawns no placer.

The auditor's model follows your session. The placer is pinned to **Sonnet**: it's
handed the docs and the findings, so its job is judgment against text in front of it
rather than open-ended search, and pinning keeps a frequently-run pass cheap. Change
`model:` in `agents/finding-placer.md` if you'd rather it match your session.

## `/threads:process-review` — the cross-session review

One altitude up from retro. Six sessions can each add a slightly-different local rule
that *together* should have been one structural change — and no single session can see
it. `/threads:process-review` reads the accumulated stream of **process-shaped
commits** (changes to *how you work*: rules, traps, templates, workflows) and surfaces
reconciliation and structural candidates, ranked, with the commits that feed each one.

- **First run bootstraps by inspection, read-only.** It reads your repo's existing
  conventions and *negotiates* a marker convention that fits (default
  `docs(process/<scope>):`, adapted to your commit style), proves the pattern fires,
  and asks before writing anything. The negotiated convention lives in
  `.claude/threads.json` — one visible source both commands read.
- **No telemetry yet?** It falls back to clustering churn on your process docs across
  existing history, so the first run has material on day one — and tells you what the
  marker convention would sharpen.
- **A staleness sweep covers the negative space.** Churn only surfaces what changed;
  stable workflow docs (a command pipeline in `.claude/commands/`, a long-standing
  rule) can quietly fall behind a growing repo without generating any telemetry. The
  review ranks process and workflow docs by growth-since-last-touch and by whether
  siblings that should co-evolve did, then git-blames the survivors to point at their
  stalest sections. Staleness alone earns a scrutiny note, never a rewrite proposal.
- **It reads what's pending first.** Findings captured by `/threads:retro` are the only
  already-adjudicated material in a window — you accepted each one — so the review leads
  with them, ranks any key that shows up more than once, and is free to re-rank what a
  single session called urgent now that it can see across sessions.
- **`/threads:retro` tells you when a review looks ripe.** One sentence at the end of a
  retro — what's pending, how old, and what's churned since the last review — delivered at
  closeout, when the backlog has just grown and opening a new thread is the natural next
  move. No hooks ship: a nudge at session start would compete with the task you just
  asked for. It always points you at a *fresh* session, since the review can't run in the
  one it reviews. Never urgent, never acted on unprompted.
- **Nothing silent.** Applying anything requires recorded consent (`applyMode`,
  starting `read-only`); every run states which inputs it used and what the next tier
  up would buy.

`/threads:retro` feeds this loop from both ends: findings it captures are the pending
stream, and anything you do land straight from a retro becomes a marker commit — the
landed stream. Retro captures; process-review lands.

## Install

This is a standard Claude Code plugin. Either:

- **Drop-in:** copy this `threads-plugin/` directory into your plugins location, or
- **Marketplace/git:** add the repo hosting it as a plugin marketplace and install
  `threads`.

Once installed, `/threads:retro` is available in any repo.

## Requirements

The fresh-context audit shells out to **`python3`** (3.6+) to distill the session
transcript, which it reads from `~/.claude/projects` (or `$CLAUDE_CONFIG_DIR`). If
`python3` is missing or the transcript can't be located, `/threads:retro` reports the
reason and the fix, then runs the self-pass instead of failing — it never silently
drops the audit. The self-pass needs nothing beyond Claude Code itself.

## Layout

```
threads-plugin/
  .claude-plugin/plugin.json      Plugin manifest
  commands/retro.md               The /threads:retro command — flow, args, and output
  commands/process-review.md      The /threads:process-review command — bootstrap, funnel, output
  agents/retro-auditor.md         Read-only sub-agent for the fresh-context audit (its brief)
  agents/finding-placer.md        Read-only sub-agent that sites findings in your process docs (both commands)
  scripts/extract-record.py       Transcript → compact timeline (used by the fresh-context audit)
```

No hooks ship, and nothing runs on a schedule or at session start: both commands are
explicit-only.

## Notes on portability

The command is **repo-agnostic**: it makes no assumptions about where your repo keeps
process docs. It discovers where lessons live (a `CLAUDE.md`, a patterns/traps doc, a
failure catalog, a hooks dir) and proposes landing changes there — or just surfaces
candidates if your repo has no such place.

`scripts/extract-record.py` is the one **harness-specific** piece: it reads Claude
Code's transcript format. The fresh-context audit's *principle* (distill the record to a
compact timeline → hand it to a fresh reviewer) ports to any environment; that script is
one concrete implementation of it.

`/threads:process-review` needs only **git** — no `jq`, no network. Its conventions are
deliberately not hardcoded: the marker pattern, process-doc paths, the log locations,
thresholds, and write consent all live in your repo's `.claude/threads.json`, negotiated
at bootstrap rather than dictated. The retro log's *vocabulary* isn't configured at all —
keys are written by an agent that has just read your existing ones, so the classes your
repo uses grow out of your own frictions. Enhancements (an agent memory store, a tracker
for review issues) are detected if present, never required.
