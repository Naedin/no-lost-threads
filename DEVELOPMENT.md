# Contributing

## Local development

This repo is a plugin marketplace; the plugin lives in `threads-plugin/`. When the
plugin is installed via `/plugin install`, Claude Code keeps a **cached copy** under
`~/.claude/plugins/cache/no-lost-threads/threads/<version>/` and runs *that* — **editing
files in `threads-plugin/` does not change what the installed copy executes.**

To test working-tree changes, load the plugin straight from disk:

```bash
cd /path/to/no-lost-threads
claude --plugin-dir ./threads-plugin
```

`--plugin-dir` (confirmed in Claude Code 2.1.x via `claude --help`) loads the plugin
from the filesystem for that session, so your edits are what runs — no commit, push, or
reinstall needed.

To pick up edits made *during* a running session, relaunch with the flag (the guaranteed
path); `/reload-plugins` may reload commands and agents without a full restart. New files
(e.g. a new `agents/*.md`) are discovered the same way.

**Don't hand-edit the cache.** Editing files under `~/.claude/plugins/cache/...` is
unsupported: it's overwritten on update and never syncs back to git. Use `--plugin-dir`.

## How the plugin is wired

- **Commands** — auto-discovered from `threads-plugin/commands/*.md`; no manifest entry
  needed.
- **Agents** — auto-discovered from `threads-plugin/agents/*.md`. The agent's `name:`
  frontmatter field is its handle.
- **`subagent_type`** — reference a plugin agent as `<plugin>:<agent-name>`. This plugin
  is named `threads` (see `threads-plugin/.claude-plugin/plugin.json`), so
  `agents/retro-auditor.md` (`name: retro-auditor`) is spawned as
  `threads:retro-auditor`.

## Before you call a plugin change "done"

Editing the source is not the same as running it. A change to a command, agent, or
script isn't done until:

1. **It loads** — `claude --plugin-dir ./threads-plugin` starts with no plugin load
   errors.
2. **The changed path has actually been exercised** — for a command that spawns an
   agent, run it and confirm the agent is reachable under its `threads:<name>` handle,
   not merely that the file parses.

The trap this guards against: the installed cache can keep running the *old* behavior
while your working tree looks correct, so a change can appear complete and tested when
neither is true.

## Releasing

The marketplace install (`/plugin install threads@no-lost-threads`) pulls from git, not
your working tree. To ship a change to installed users:

1. Commit and push to `main`.
2. Bump `version` in **both** `threads-plugin/.claude-plugin/plugin.json` and the plugin
   entry in `.claude-plugin/marketplace.json` (the `claude plugin tag` step below enforces
   that these agree).
3. Tag the release: `claude plugin tag --push ./threads-plugin`. This creates and pushes a
   `threads--v<version>` git tag and validates the two manifests are in sync. (The tag is
   release hygiene — Claude Code resolves versions from `marketplace.json` on the default
   branch, not from tags — but it gives each release a clean ref and a sanity check.)

### How users actually receive the update

Marketplace clones are **pull-based and manual** — Claude Code does *not* auto-refresh
them, so a stale clone keeps advertising the old version and no "update available" appears.
There is no author-side way to push an update or a notification. An installed user picks up
a new version in **two** steps, in order:

```bash
claude plugin marketplace update no-lost-threads   # refresh the marketplace clone first
claude plugin update threads@no-lost-threads        # then update the plugin (restart to apply)
```

Skipping the first step is the common trap: `/plugin update` alone finds nothing new
because the local marketplace clone still points at the old commit.
