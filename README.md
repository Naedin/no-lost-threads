# No Lost Threads

Workflow tooling for AI-assisted coding. This repository is a Claude Code
**plugin marketplace**; its first plugin is `retro`.

## `retro` — a process-retrospective slash command

`/retro` reviews the work in your current session as **process telemetry**. It focuses on *how* things happened, not whether the code is correct. It catches the meta-issues a session
tends to miss about itself: drift, scope leak, ignored user signals, unverified
claims, premature lock-in, mode confusion, and stale workflow habits.

- **Default (`/retro`):** runs a quick self-pass **and** a fresh-context audit — a
  sub-agent is handed the observable session record (`what was asked → what was done
  → what was said`) and judges the work cold, catching the anchoring-driven issues a
  self-reflection structurally can't see. The cold audit is the headline: most retros
  only self-reflect.
- **Quick (`/retro quick`):** the self-pass alone — a fast reflection while context
  is hot, skipping the sub-agent.

It's a **command, not a skill** — it runs only when you type `/retro`, and never
auto-fires on trigger words. Findings are always candidates surfaced in-thread for
you to accept, reject, or refine; no working-tree changes by default.

## Install

This repository is a plugin marketplace. In Claude Code:

```
/plugin marketplace add Naedin/no-lost-threads
/plugin install retro@no-lost-threads
```

Then:

```
/retro                      # default: self-pass + fresh-context audit
/retro quick                # self-pass only (skip the sub-agent)
/retro the auth refactor    # narrow the scope
```

See [`retro-plugin/README.md`](retro-plugin/README.md) for the full command spec.

## License

MIT — see [LICENSE](LICENSE).
