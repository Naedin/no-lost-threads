# retro — a process-retrospective slash command

A Claude Code plugin that adds **`/retro`**: a retrospective pass that reviews the
work in your current session as **process telemetry** — *how* the work happened, not
whether the code is correct. It catches the meta-issues a session tends to miss about
itself: drift, scope leak, ignored user signals, unverified claims, premature
lock-in, mode confusion, and stale workflow habits.

**Explicit invocation only.** This is a command, not a skill — it runs only when you
type `/retro`. It never auto-fires on trigger words.

## What it does

- **Fresh-context audit (default, `/retro`):** hands a **fresh-context sub-agent**
  the observable record of the session (`what was asked → what was done → what was
  said`) and asks it to judge the work cold — surfacing the anchoring-driven issues a
  self-reflection structurally can't see. This is the headline: most retros only
  self-reflect; this one reads the session cold. If it can't run (no transcript, no
  sub-agent), it degrades to the self-pass instead of failing.
- **Self-pass:** a fast reflection on the in-scope work while context is hot. Runs as
  part of every pass — and is the *only* pass under `/retro quick`.

Findings are always **candidates** surfaced in-thread for you to accept, reject, or
refine — no working-tree changes by default, and it biases toward amending an
existing rule over adding a new one (anti-bloat).

## Usage

```
/retro                      # default: self-pass + fresh-context audit
/retro quick                # self-pass only (skip the sub-agent)
/retro the dedup decision   # narrow the scope
/retro quick this whole planning thread
```

## Install

This is a standard Claude Code plugin. Either:

- **Drop-in:** copy this `retro-plugin/` directory into your plugins location, or
- **Marketplace/git:** add the repo hosting it as a plugin marketplace and install
  `retro`.

Once installed, the `/retro` command is available in any repo.

## Requirements

The fresh-context audit shells out to `python3` to distill the session transcript. If
`python3` isn't on `PATH`, `/retro` degrades to the self-pass instead of failing. The
self-pass needs nothing beyond Claude Code itself.

## Layout

```
retro-plugin/
  .claude-plugin/plugin.json    Plugin manifest
  commands/retro.md             The /retro command (the whole spec lives here)
  scripts/extract-record.py     Transcript → compact timeline (used by the fresh-context audit)
```

## Notes on portability

The command is **repo-agnostic**: it makes no assumptions about where your repo keeps
process docs. It discovers where lessons live (a `CLAUDE.md`, a patterns/traps doc, a
failure catalog, a hooks dir) and proposes landing changes there — or just surfaces
candidates if your repo has no such place.

`scripts/extract-record.py` is the one **harness-specific** piece: it reads Claude
Code's transcript format. The fresh-context audit's *principle* (distill the record to a compact
timeline → hand it to a fresh reviewer) ports to any environment; that script is one
concrete implementation of it.
