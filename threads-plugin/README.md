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
  override), and what worked is reported and never appended: the review ranks by
  recurrence, and a positive never recurs.
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

`retroPlacement: "keys"` in `.claude/threads.json` makes retro's placer key the findings
against the log and read no process doc; the retro records a `file §section` pointer, and
`/threads:process-review` places the findings that survive it. Under either mode `quick`
still only skips the audit.

## `/threads:process-review` — the cross-session review

One altitude up from retro. Six sessions can each add a slightly different local rule
that together should have been one structural change, or one deletion, and no single
session can see it. `/threads:process-review` reads what accumulated across sessions and
proposes what to change, replace, or delete.

- **It starts from your diagnosis when you have one.** `/threads:process-review the copy
  guidelines are broken` makes that the run's question, and the retro log is evidence for
  or against it. Without one, the question is what the window's residual says.
- **It reads residual, not rule churn.** Residual is what gets caught after the work is
  done: your corrections, review and gate findings, escapes. It is read as a rate per
  stretch of work, to diagnose, never as a target. Residual piling up in one doc's
  territory while its rules are followed makes the doc the suspect. Process commits are
  read beside it as what changed near it.
- **It works at direction altitude.** A delegate (`evidence-reader`) reads the raw
  incidents: the log through its view, each key's chain, the process-commit stream, the
  risk registry, and docs nothing routes to or that point at nothing. It returns a
  compressed picture of where residual concentrates, what changed near it (a rule change,
  a tool version, a new area of work), and how much upcoming work runs through it. The
  reviewer weighs that against the docs you name as your direction (`invariantDocs`) and
  decides: act now, let more work narrow the cause, or leave.
- **It asks whether the approach is wrong before patching.** For each doc it acts on,
  `structure-explorer` proposes different shapes for the doc's job, after checking how
  others solve the same problem. The review names the largest option and its cost beside
  the one it recommends, and a replacement reaches you whole, never cut back into patches.
- **Deletion costs no more than addition.** A wrong rule is answered by deleting it. Under
  `apply-mechanical`, a named deletion lands unanswered just as an addition does.
- **You read one block.** The output opens with the decisions that need you: a table when
  there are several, a short paragraph when there is one call about a whole doc. The record
  below it is for the commit body and the next run, and nothing that could change your
  answer is only there.
- **It samples whether a prose rule holds** (`adherenceRules`; `/threads:adherence` runs the
  sample standalone), and **retires workarounds when their tool moves** (`workaroundsPath`,
  each workaround carrying a probe or a re-test).
- **First run bootstraps by inspection, read-only**, negotiating a commit marker that fits
  your style and proving it fires. Every commit the review lands carries a
  `Process-Review: <date>` trailer, so it never reads its own output as change.
- **Nothing silent.** Applying anything requires recorded consent (`applyMode`, starting
  `read-only`, ratcheting by an answer to `apply-on-approval` and then `apply-mechanical`).

`/threads:retro` feeds the loop: what it captures is the review's evidence, and it closes
with a one-line nudge when a review looks ripe (a finding escaped or a gate misran since
the last review, or a doc's cluster of such findings grew). Retro captures;
process-review lands.

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
  commands/process-review.md      The /threads:process-review command — bootstrap, the review, output
  agents/retro-auditor.md         Read-only sub-agent for the fresh-context audit (its brief)
  agents/finding-placer.md        Read-only sub-agent that sites findings in your process docs (both commands)
  agents/evidence-reader.md       Read-only sub-agent that reads the window's incidents and returns where residual concentrates
  agents/structure-explorer.md    Read-only sub-agent that asks whether a doc's whole approach is the problem
  commands/adherence.md           The /threads:adherence command — a declared rule's sample (a review phase, or standalone)
  agents/adherence-judge.md       Read-only sub-agent that rules each drawn block against the tree
  agents/adherence-refuter.md     Read-only sub-agent that tries to show each flagged block true
  scripts/adherence.py            The sample's draw, its agents' output checked, its tally line, each shape's windows
  scripts/extract-record.py       Transcript → compact timeline (used by the fresh-context audit)
  scripts/retro-log.py            The retro log's view (state and counts per key) and compaction
  scripts/marker-stream.py        The marker-commit stream since the mark, classified organic / review / bookkeeping
  scripts/land-process-commit.py  Land one marker commit on the default branch from a slice branch, through the repo's own hook
  scripts/risk-review.py          The slices risk registry against the window's escapes, per class and unclassified by area
  scripts/workarounds.py          The workaround register: shell that reads each tool's version and probes the moved ones, and what is retirable
```

**The retro log is an append-only stream, read through a view.** Sessions append; a
recurrence is the same key with a new dated line, a landing is the key with one `LANDED
<sha>` line, and `.gitattributes` merges the file by union so concurrent sessions never
conflict. `python3 <plugin>/scripts/retro-log.py view --keys` derives each key's state and
occurrence count, and its filters (`--held`, `--recurred`, `--since <date or the mark>`, `--live`) are
the reads the review makes, so a log of a few hundred keys is never read whole; a held
proposal shows the date it was held and its age. The review's ruling on a key — a re-rank,
a count-only call — is an `ADJUDICATED <date>` line that changes neither state nor count.
A trajectory — several keys that are one arc of attempts, landings, and recurrences — is
an `ARC <name> [<date>]` line on each key it rides with, and `view --arc <name>` prints
those keys by the date each entered, with their dated blocks: the arc's history derived
from the log, never narrated again, and the re-derive command a ledger watch on the arc
cites; `view --arcs` lists them. The arc's own landings are commits carrying an `Arc:
<name>` trailer, which `marker-stream.py list --arc <name>` prints dated.
`compact` is the review's one rewrite. Past a re-key, the review's only in-place edits are
a class line the log's own text contradicts and a status line's where whose target moved,
so `--reached` can read what the text says; sessions append and never edit. The `guards`
plugin's `retro-log` and `review-ledger` checks hold both files to their grammar.

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

The audit's record is portable; the plugin is not. The commands and agents are Claude Code
plugin files that spawn Claude Code sub-agents. `scripts/extract-record.py` splits a
harness-specific reader from a renderer: a reader yields `(kind, text)` events, and the kinds
(`human`, `unattributed`, `peer`, `brief`, `harness`, `said`, `did`) are what the auditor's brief
relies on. Supporting another harness's transcripts takes one reader, which yields
`unattributed` for any turn whose author it cannot tell. The only reader today parses Claude
Code's undocumented JSONL. A session with no events fails to the self-pass; a record with no
human turn says so.

`/threads:process-review` needs **git** and **Python 3**, plus network access only to fetch
the remote it compares against. Its conventions are
deliberately not hardcoded: the marker pattern, process-doc paths, the log locations,
thresholds, and write consent all live in your repo's `.claude/threads.json`, negotiated
at bootstrap rather than dictated. The retro log's *vocabulary* isn't configured at all —
keys are written by an agent that has just read your existing ones, so the classes your
repo uses grow out of your own frictions. Enhancements (an agent memory store, a tracker
for review issues) are detected if present, never required.
