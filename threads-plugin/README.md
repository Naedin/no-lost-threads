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
  immediately, say so and it lands. The one thing retro fixes unasked is a defect in an
  artifact the session itself wrote or landed — the moment it is found is the cheapest
  the fix will ever be, and a wrong artifact is the next reader's premise; the process
  lesson behind it is still captured.
- **Capture has a bar.** A finding is appended when it cost the session something, when
  it matches a key already in the log, or when it is severe on its face. A nil-cost
  friction that matches nothing is reported and not appended (say *append it* to
  override), and what worked is reported and never appended: every key the log carries
  is read by every later review until it recurs, and the review ranks by recurrence, so
  a key that can never rank is pure read cost.
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
rather than open-ended search, and pinning keeps a frequently-run pass cheap. To run it
on another model, set `placerModel` in `.claude/threads.json` (a harness short name such
as `"opus"`); both commands pass it to the placer spawn. Never edit the installed agent
file — it lives in the plugin cache and `/plugin update` overwrites it.

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
  retro — what's pending, whether anything recurred since the last review, and what's
  churned — delivered at closeout, when the backlog has just grown and opening a new
  thread is the natural next move. No hooks ship: a nudge at session start would compete
  with the task you just asked for. It always points you at a *fresh* session, since the
  review can't run in the one it reviews. Never urgent, never acted on unprompted. *Ripe*
  means a key recurred or the organic process commits crossed a bar; pending captures
  alone never make a review ripe.
- **The review does not count itself.** Every commit the review lands carries a
  `Process-Review: <date>` trailer, and a commit that touched only the log or the ledger
  is bookkeeping; `scripts/marker-stream.py` classifies the stream into organic, review,
  and bookkeeping, and only the organic commits feed the trigger and the ranking. Without
  that, a review that lands twenty commits makes the next morning's review look ripe on
  its own output.
- **It reads a small core, then only what its findings name.** `invariantDocs` is the
  handful of docs stating your repo's authority order and the review's own conventions,
  read every run. Every other doc is opened whole only when a recurred key or a fired
  ledger signal points at it (`retro-log.py view --recurred --docs` derives the list from
  the log), at the moment it bears; a doc the window's churn points at is read as its
  diff, and the placer is the only whole read of an edit's target.
- **It closes with its own economics**, as questions to you: what it read against what
  bore on a ruling, how much of the marker stream was its own weight, how many keys it
  carried against how many recurred, and its own landing errors — and the standing
  question, *what should the next run stop reading?* Its own misses go there, never into
  the log it is trying to keep small.
- **Nothing silent.** Applying anything requires recorded consent (`applyMode`,
  starting `read-only`, ratcheting by an answer to `apply-on-approval` and then to
  `apply-mechanical`, where a run nobody is answering lands wording amendments and trims
  itself and holds everything else); every run states which inputs it used and what the
  next tier up would buy.

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
  scripts/retro-log.py            The retro log's view (state and counts per key) and compaction
  scripts/marker-stream.py        The marker-commit stream since the mark, classified organic / review / bookkeeping
  scripts/land-process-commit.py  Land one marker commit on the default branch from a slice branch, through the repo's own hook
```

**The retro log is an append-only stream, read through a view.** Sessions append; a
recurrence is the same key with a new dated line, a landing is the key with one `LANDED
<sha>` line, and `.gitattributes` merges the file by union so concurrent sessions never
conflict. `python3 <plugin>/scripts/retro-log.py view --keys` derives each key's state and
occurrence count, and its filters (`--held`, `--recurred`, `--since <date>`, `--live`) are
the reads the review makes, so a log of a few hundred keys is never read whole; a held
proposal shows the date it was held and its age. The review's ruling on a key — a re-rank,
a count-only call — is an `ADJUDICATED <date>` line that changes neither state nor count.
`compact` is the review's one rewrite. The `guards` plugin's `retro-log`
and `review-ledger` checks hold both files to their grammar.

**A marker commit survives the squash by landing on its own.** A squash merge collapses
a slice branch into one subject, so a `docs(process/<scope>)` commit made on the branch
never reaches the stream the review reads. `python3 <plugin>/scripts/land-process-commit.py
<sha>` lands that one commit direct on the default branch from wherever the branch is
checked out: a throwaway worktree at `origin/<default>`, `git cherry-pick --no-commit`
then `git commit -C <sha>` so the repo's own pre-commit hook fires (a plain cherry-pick
runs no hook), a patch-identity check, the push, and on stdout exactly one line — the sha
re-read from the remote, the only one a log or ledger line may cite. The slice branch is
then rebased so the duplicate drops. A conflict, a red hook, or a refused push fails loud
with nothing pushed. The default branch comes from `--branch`, `defaultBranch` in
`.claude/threads.json`, or `refs/remotes/origin/HEAD`.

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
