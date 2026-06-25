# Changelog

Notable changes to the **threads** plugin, newest first. Versions track the plugin
`version` in
[`plugin.json`](threads-plugin/.claude-plugin/plugin.json) and
[`marketplace.json`](.claude-plugin/marketplace.json); each release is tagged
`threads--v<version>`.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed

- **`/threads:retro`'s fresh-context audit now sees far more of each agent turn.** The
  extractor that builds the session record capped agent text at 700 characters and kept
  only the head — which dropped the tail of long turns, where commitments, deferrals, and
  lock-in language tend to land, and discarded roughly half of all agent text before the
  cold reviewer saw it. The cap is now 2,500 characters, and over-cap turns retain their
  head **and** tail. The audit reads more completely; the record stays a few KB.
- **The fresh-context audit now flags self-perpetuating closure language.** When an agent
  turn closes a question with markers like *decided / deferred / for v1 / by-design* that
  the evidence hadn't earned and the user hadn't locked, the auditor surfaces it for a
  second look — such markers tend to get accepted once and never revisited.

## [0.2.0] — 2026-06-24

- `/threads:retro` reviews the current session as process telemetry. The default runs a
  self-pass plus a **fresh-context audit** — a read-only `retro-auditor` sub-agent that
  judges the session's observable record cold. `/threads:retro quick` runs the self-pass
  alone and skips the sub-agent.
