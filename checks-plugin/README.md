# checks: repo guardrails as scripts behind a gate

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

- `--paths` narrows the universe to the listed root-relative files; a listed path
  absent from the tree is skipped.
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

**`.claude/checks.json`** names the enabled checks and each one's rung. A check absent
from `checks` does not run. `paths` and `exclude` are optional and mean what the flags
above mean:

```json
{
  "checks": {
    "anchors":     { "rung": "block", "exclude": ["vendor/**"] },
    "war-stories": { "rung": "warn",  "paths": ["CLAUDE.md", "docs/process.md"] }
  }
}
```

**`run.py [--root DIR]`** reads that config (root defaults to the git top level), runs
each enabled check, and prints one line per finding as `<id>: <path>:<line>: <message>`,
prefixed `warn ` when the check's rung is `warn`. One summary line on stderr names each
check run, its rung, and its finding count. Exit **0** when no `block` check found
anything and no check refused; **1** when a `block` check found something; **2** when
the config is unreadable or malformed, names a check id that does not exist, or any
check exited 2, regardless of rung. No config: exit 0, no output. A gate that cannot
run is never a passed one.

## The checks

| id | finds | universe without `paths` |
|---|---|---|
| `anchors` | a `](path#frag)` whose `frag` is not an explicit `<a id="frag">` in the target (heading-derived slugs fail by design); a relative `](path)` whose target does not exist. External links are skipped. | every tracked `*.md` under the root when the root is a git checkout, else every `*.md` under it |
| `war-stories` | narrative provenance in prose: `this session`, `maintainer:`, `user:`, `had to say/redirect/point/stop`, `emergency`, `was caught by`, `never arrived`. A rule states its mechanism and its rung; the incident goes in the commit message. | none; `paths` is required |

## The gate

`adapters/git/pre-commit` exports the index to a temporary tree with
`git checkout-index` and runs `run.py` there, so the gate judges the commit's content
and a cross-file check sees every target file. Its exit is the runner's exit. When the
index carries no `.claude/checks.json` it exits 0 with no output, so the adapter is
inert in a repo that never opted in.

Install, from a checkout that carries this plugin in its tree:

```
git config core.hooksPath checks-plugin/adapters/git
```

That install line assumes the plugin lives in the repo. Installed from the
marketplace, this version is inert: it ships no hook file and no command, and the
adapter it carries is not wired to anything. The Claude blocking-hook adapter, and a
`--vendor` option that copies a check into the adopting repo for a frozen gate, are the
versions after this one.

## Proving a check

```
bash checks-plugin/test.sh
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
