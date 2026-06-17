# threads: process tooling for Claude Code

A Claude Code plugin for keeping the threads of your work from getting lost. Its first
command is **`/threads:retro`**.

Built to grow: future commands live under the same `/threads:` namespace, so you can
find them by `threads` (the whole menu) or by the command name (e.g. `retro`).

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
  part of every pass — and is the *only* pass under `/threads:retro quick`.

**Findings are candidate process changes for you to review.** They're surfaced in-thread for you to
accept, reject, or refine. The command biases
toward amending an existing rule over adding a new one (anti-bloat). The point: an agent
reviewing its own work shouldn't silently rewrite your process docs. *You* decide what
gets promoted.

### Usage

```
/threads:retro                      # default: self-pass + fresh-context audit
/threads:retro quick                # self-pass only (skip the sub-agent)
/threads:retro the dedup decision   # narrow the scope
/threads:retro quick this whole planning thread
```

### Cost

The default spawns a sub-agent that reads your whole session transcript, so it can use
a meaningful number of tokens. There are two ways to keep that in
your control: **`/threads:retro quick`** skips the sub-agent entirely, and the
sub-agent's model follows your session (the spawning agent right-sizes it).

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
  .claude-plugin/plugin.json    Plugin manifest
  commands/retro.md             The /threads:retro command (the whole spec lives here)
  scripts/extract-record.py     Transcript → compact timeline (used by the fresh-context audit)
```

## Notes on portability

The command is **repo-agnostic**: it makes no assumptions about where your repo keeps
process docs. It discovers where lessons live (a `CLAUDE.md`, a patterns/traps doc, a
failure catalog, a hooks dir) and proposes landing changes there — or just surfaces
candidates if your repo has no such place.

`scripts/extract-record.py` is the one **harness-specific** piece: it reads Claude
Code's transcript format. The fresh-context audit's *principle* (distill the record to a
compact timeline → hand it to a fresh reviewer) ports to any environment; that script is
one concrete implementation of it.
