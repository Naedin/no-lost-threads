<!-- audience: human -->
# guards: repo guardrails as scripts behind a gate

A Claude Code plugin carrying checks a repo turns on one at a time, each a plain
script with a stable id, run by a gate that refuses a commit on a finding. Rung is
config, so a repo starts a check at `warn`, promotes it to `block` when its evidence
justifies, and never migrates: the ids, the config shape, the exit codes, and the
output format below are the contract, and later versions only add to them.

## The contract

**One script per check**: `checks/<id>/check.py`, with `fixtures/pass/<case>/` and
`fixtures/fail/<case>/` mini trees proven by `test.sh`.

```
check.py --root DIR [--paths PATH]... [--exclude GLOB]...
```

- `--paths` narrows the universe to the entries it names: a root-relative file, or a
  glob matched exactly the way `--exclude` is, below. A literal is tried first, so a
  name carrying glob characters still selects the file bearing it. A glob matches the
  index listing the git adapter hands over, else the tracked files in a git checkout,
  else every file present — and never reaches past what the check reads, so an
  `anchors` glob stays inside its `*.md` universe. An entry that names no file refuses,
  naming that entry; a scope narrowing in silence is what the gate exists to catch.
  Entries are normalized before matching, so `./docs/*.md` names what `docs/*.md`
  names, and an entry outside the root refuses.
  A file the listing names that the tree lacks refuses by name — under the adapter the
  export dropped it, in a checkout it was deleted without `git rm` — for a glob as for
  a literal.
- `--exclude` removes patterns from the universe and applies after `--paths`, whether
  the paths were given explicitly or discovered. Patterns are matched by Python's
  `fnmatch` against the root-relative POSIX path: `*` and `?` match any character
  including `/`, so `**` is `*`, and a pattern that must stay inside one directory
  says so with a literal prefix.
- Findings on stdout, one per line: `<path>:<line>: <message>`. Fenced code blocks
  and code spans are not prose for any check that reads markdown.
- Exit **0** pass, **1** findings, **2** refused: the root is missing, a file in
  scope is unreadable, or nothing is in scope. A check decides finding or not
  finding; severity is the rung's, never the check's.

**`.claude/guards.json`** names the enabled checks and each one's rung. A check absent
from `guards` does not run. `paths` and `exclude` are optional and mean what the flags
above mean:

```json
{
  "checks": {
    "anchors":     { "rung": "block", "exclude": ["vendor/**"] },
    "war-stories": { "rung": "warn",  "paths": ["CLAUDE.md", "docs/*.md"] }
  }
}
```

An optional top-level `"export"` — a list of git pathspecs, e.g. `["*.md", ".claude/*",
"*.log"]` — tells the git adapter which index paths to export before judging; absent, it
exports the whole index, which on a large tree copies hundreds of megabytes per commit.
A `*` in a git pathspec crosses `/`, so `.claude/*` reaches `.claude/commands/x.md` and
`*.md` reaches every tracked Markdown file at any depth.
The export is never a scope: the adapter hands each check the index listing through
`GUARDS_INDEX`, the check takes its universe from that listing rather than from the
exported tree, and a file in scope the export dropped refuses, naming the file. Widen
the list, or narrow the check with `paths` or `exclude`; a walk of the tree would judge
what survived and pass. An export that drops a config the gate steers by —
`.claude/guards.json`, or `.claude/threads.json` where the logs live — refuses before any
check runs, naming the file: past a missing config a check judges nothing and says
nothing, so the list is verified rather than trusted.

**`run.py [--root DIR]`** reads that config (root defaults to the git top level), runs
each enabled check, and prints one line per finding as `<id>: <path>:<line>: <message>`,
prefixed `warn ` when the check's rung is `warn`. One summary line on stderr names each
check run, its rung, and its finding count. Exit **0** when no `block` check found
anything and no check refused; **1** when a `block` check found something; **2** when
the config is unreadable or malformed, names a check id that does not exist, or any
check exited 2, regardless of rung. No config: exit 0 and one stderr line saying
nothing was judged. A gate that cannot run is never a passed one, and a run that
judged nothing never reads as one that passed.

## The checks

| id | finds | universe without `paths` |
|---|---|---|
| `anchors` | a `](path#frag)` whose `frag` is not an explicit `<a id="frag">` in the target (heading-derived slugs fail by design); a relative `](path)` whose target exists neither in the tree nor in the index listing the git adapter hands over, so an export narrower than the link graph is not a broken link. External links are skipped. | every `*.md` in the index listing the git adapter hands over, else every tracked `*.md` when the root is a git checkout, else every `*.md` under it |
| `war-stories` | narrative provenance in prose: `this session`, `maintainer:`, `user:`, `had to say/redirect/point/stop`, `emergency`, `was caught by`, `never arrived`. A rule states its mechanism and its rung; the incident goes in the commit message. | none; `paths` is required |
| `retro-log` | a line the retro log's grammar cannot read: not a key line (`<class>/<shape>`), an occurrence (`YYYY-MM-DD \| source \| text`), a one-line status (`LANDED\|RETIRED\|UPSTREAM\|FILED\|NOTED\|HELD\|REOPENED <ref> — text`) or annotation (`ADJUDICATED <date> — text`), a continuation, or blank; an unknown status token; a status or annotation entry over one line or inside an occurrence; a section after the entries. The grammar is the `threads` plugin's `scripts/retro-log.py`. | `retroLogPath` in `.claude/threads.json`, default `.claude/threads-retro-log.md` |
| `retro-log-size` | an occurrence in the retro log over 8 lines, counted from its dated line through its last continuation. Separate from `retro-log` so the grammar can sit at `block` while existing entries come under the cap at `warn`. | `retroLogPath` in `.claude/threads.json`, default `.claude/threads-retro-log.md` |
| `review-ledger` | a section other than Live, Falsifications, or Resolved; a dated window line inside a Live entry (`09-04: no fire`, `Re-deferred 2026-09-02:`) where one `last checked: <date> — <state>` line belongs; a Live entry over 12 lines; a Resolved entry over 3 lines. | `ledgerPath` in `.claude/threads.json`, default `.claude/threads-review-ledger.md` |

## The gate

`adapters/git/pre-commit` exports the index to a temporary tree with
`git checkout-index`, hands the checks the index listing through `GUARDS_INDEX`, and
runs `run.py` there, so the gate judges the commit's content and a cross-file check sees
every target file. Its exit is the runner's exit, except when the export itself is
wrong — an `"export"` list that drops a config the gate reads refuses with exit 2 before
a check runs. When the index carries no `.claude/guards.json`
it exits 0 with one stderr line saying nothing was judged, so the adapter is inert in a
repo that never opted in and a vacuous pass never reads as a working one.

Install, from a checkout that carries this plugin in its tree:

```
git config core.hooksPath guards-plugin/adapters/git
```

Keep that path relative: git resolves it against each worktree's own top level, so a
linked worktree runs the adapter it carries. An absolute path points every worktree at
one checkout's copy, and an edit to the hook in a worktree then does nothing.

That install line assumes the plugin lives in the repo. A repo with its own hook that
wants the gate from a sibling checkout of this plugin calls this adapter, which judges the
index the way the hook does, and resolves the path through the primary's `.git`, not the
current worktree, or the gate is inert in every worktree:

```bash
guards="$(git rev-parse --path-format=absolute --git-common-dir)/../../no-lost-threads/guards-plugin/adapters/git/pre-commit"
if [ -f "$guards" ]; then bash "$guards" || exit $?
else echo "pre-commit: guards skipped, plugin not beside this checkout" >&2; fi
```

`exit $?`, not `exit 1`: git aborts on either, but a wrapper that rewrites 2 to 1 tells
its caller the gate found something when the gate could not run.

Calling `run.py` directly from a hook judges the working tree instead, and an unstaged
edit blocks an unrelated commit.

A rebase or a union merge runs no pre-commit hook, so a file two branches both appended
to reaches the default branch unjudged. A landing step that runs `run.py` on the rebased
tree before the push is the gate for that path.

Installed from the marketplace, this version is inert: it ships no hook file and no command, and the
adapter it carries is not wired to anything. The Claude blocking-hook adapter, and a
`--vendor` option that copies a check into the adopting repo for a frozen gate, are the
versions after this one.

## Proving a check

```
bash guards-plugin/test.sh
```

Runs every fixture case and the two refusal cases for every check, then the runner's
own contract (no config, malformed config, unknown id, each rung, a refused check).
One line per case with the expected and observed exit code; exits 1 on the first wrong
one. A case directory may carry an `args` file, one argument per line, appended to the
check's invocation.

## Requirements

git, bash, Python 3.

## License

MIT.
