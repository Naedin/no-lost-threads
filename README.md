# No Lost Threads

Workflow tooling for AI-assisted coding. This repository is a Claude Code
**plugin marketplace**; its first plugin is **`threads`**, whose first command is
`/threads:retro`.

## `/threads:retro` — a process-retrospective slash command

`/threads:retro` reviews the work in your current session as **process telemetry**.
It focuses on *how* things happened, not whether the code is correct, catching the
meta-issues a session tends to miss about itself: drift, scope leak, ignored user
signals, unverified claims, premature lock-in, mode confusion, and stale workflow
habits.

- **Default (`/threads:retro`):** runs a quick self-pass **and** a fresh-context
  audit — a sub-agent is handed the observable session record (`what was asked → what
  was done → what was said`) and judges the work cold, catching the anchoring-driven
  issues a self-reflection structurally can't see. The cold audit is the headline:
  most retros only self-reflect.
- **Quick (`/threads:retro quick`):** the self-pass alone — a fast reflection while
  context is hot, skipping the sub-agent.

It's a **command, not a skill** — it runs only when you type `/threads:retro`, and
never auto-fires on trigger words.

**Findings are candidates, not changes.** A retro is one agent reviewing work, so its
findings are surfaced in-thread for you to accept, reject, or refine — no working-tree
changes by default. That's deliberate: an agent shouldn't silently rewrite your
process docs on the strength of its own self-review. You decide what gets promoted.

> **Cost note:** the default spawns a sub-agent that reads your whole session
> transcript, so it uses more tokens than a typical command. Use `/threads:retro
> quick` to skip the sub-agent; the audit's model follows your session — nothing is
> hardcoded.

## Install

This repository is a plugin marketplace. In Claude Code:

```
/plugin marketplace add Naedin/no-lost-threads
/plugin install threads@no-lost-threads
```

Then:

```
/threads:retro                     # default: self-pass + fresh-context audit
/threads:retro quick               # self-pass only (skip the sub-agent)
/threads:retro the auth refactor   # narrow the scope
```

(More commands may join the `threads` family over time — they'll all live under the
same `/threads:` prefix, findable by `threads` or by the command name.)

See [`threads-plugin/README.md`](threads-plugin/README.md) for the full command spec.

## License

MIT — see [LICENSE](LICENSE).
