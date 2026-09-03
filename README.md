<!-- audience: human -->
# No Lost Threads

Workflow tooling for AI-assisted coding. This repository is a Claude Code
**plugin marketplace** carrying growable workflow capabilities — adopt what your
repo's scale warrants; each hardens in place without migrations. Three plugins so
far: **`threads`** (process learning — `/threads:retro` reviews a single session
as process telemetry, `/threads:process-review` reads what accumulates across
sessions), **`slices`** (the day-one slice pipeline — capture, draft,
gap-check), and **`checks`** (repo guardrails — plain scripts with stable ids
behind a pre-commit gate, each check's rung set by config).

## `/threads:retro` — a process-retrospective slash command

`/threads:retro` reviews the work in your current session as **process telemetry**.
It focuses on *how* things happened, not whether the code is correct, catching the
meta-issues a session tends to miss about itself: drift, scope leak, ignored user
signals, unverified claims, premature lock-in, mode confusion, and stale workflow
habits.

- **Default (`/threads:retro`):** runs a quick self-pass **and** a fresh-context
  audit. A sub-agent is handed the observable session record (`what was asked → what
  was done → what was said`) and judges the work cold, catching the anchoring-driven
  issues a self-reflection structurally can't see.
- **Quick (`/threads:retro quick`):** skips the cold audit. The self-pass still runs.
- **Placement (both modes):** a second sub-agent reads your process docs cold and says
  *where* each finding belongs — amend, merge, narrow, or add new. Judging that needs a
  context with the budget to actually read the target doc, which the session that just
  did the work doesn't have. It's time-boxed, since retro runs often;
  `/threads:process-review` is what reconciles across sessions later.
- **Capture (both modes):** findings are appended to a **retro log** in your repo rather
  than applied on the spot. A retro runs when context is largest, which is the most
  expensive point at which to apply an edit, and an unread punch list is a lost one. The
  same sub-agent gives each finding a short, domain-free key and checks it against the
  log, so *adopt if it recurs* is settled by looking rather than left open.
  `/threads:process-review` adjudicates the log later, in fresh context.

Currently, this is only a command. It runs when you type `/threads:retro`, and
never auto-fires on trigger words.

**The command includes instructions to not auto-adopt changes.** A retro is one agent reviewing work, so its
findings are surfaced in-thread for you to accept, reject, or refine — capturing one isn't adopting it. That's deliberate: an agent shouldn't silently rewrite your
process docs on the strength of its own self-review. You decide what's actually important to your own process.

> **Cost note:** the default spawns two sub-agents — one reads your whole session
> transcript, so it uses more tokens than a typical command; the placer reads only your
> process docs, and only when there's something to place. `/threads:retro quick` skips
> the first.

## `/threads:process-review` — the cross-session review

Per-session retros have a structural blind spot: six sessions can each add a
slightly-different local rule that *together* should have been one structural change,
and no single session can see it. `/threads:process-review` reads what retros captured
and haven't landed, plus the accumulated stream of process-shaped commits (falling back to
process-doc churn if you have no such convention yet), and surfaces reconciliation and
structural candidates for you to accept or reject. A **staleness sweep** covers the opposite failure: stable workflow
docs — a command pipeline, a long-standing rule — that quietly fell behind as the repo
grew around them, which churn-based signals structurally can't see.

Its first run **bootstraps by inspection**: it reads your repo's existing conventions,
negotiates a commit marker that fits them, and writes nothing until you confirm. You
never have to remember the meta-review: `/threads:retro` closes with one line on whether
a review looks ripe — at closeout, when the backlog has just grown and starting a fresh
thread is the natural next move.

See [`threads-plugin/README.md`](threads-plugin/README.md) for the full loop.

## `slices` — the day-one pipeline kit

Three explicit-only commands carrying the smallest slice-pipeline habits that pay
immediately: **`/slices:capture`** files a one-concern, low-trust stub the moment
work is discovered; **`/slices:draft`** promotes a stub into a plan that
re-verifies the capture's claims and ends in a review digest (shape + at most
five tension points); **`/slices:check`** hands the plan to a fresh-context
adversary told only its path — no plan is implement-ready until it survives. The
artifacts are the contract, so later hardening (lint, ledgers, gates) only
appends to them. Full spec: [`slices-plugin/README.md`](slices-plugin/README.md).

## `checks` — repo guardrails behind a gate

One script per check, with a stable id, fixtures, and exit codes meaning pass,
findings, refused. `.claude/checks.json` names the checks a repo has turned on and
each one's rung, `warn` or `block`, so enforcement climbs by config and never by
migration. A git pre-commit adapter judges the index and is inert in a repo with
no config. Two checks ship: `anchors` (every in-repo section link resolves to an
explicit anchor; every relative link target exists) and `war-stories` (narrative
provenance in process docs). Installed from the marketplace, this version is
inert; the gate installs from a checkout that carries the plugin. Full contract:
[`checks-plugin/README.md`](checks-plugin/README.md).

## Install

This repository is a plugin marketplace. In Claude Code:

```
/plugin marketplace add Naedin/no-lost-threads
/plugin install threads@no-lost-threads
/plugin install slices@no-lost-threads
/plugin install checks@no-lost-threads
```

Then:

```
/threads:retro                     # default: self-pass + fresh-context audit
/threads:retro quick               # skip the audit (placement still runs)
/threads:retro the auth refactor   # narrow the scope
/threads:process-review            # cross-session review; first run bootstraps
```

See [`threads-plugin/README.md`](threads-plugin/README.md) for the full command spec.

## License

MIT — see [LICENSE](LICENSE).
