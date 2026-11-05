#!/usr/bin/env python3
"""install — wire the git pre-commit adapter from wherever this plugin is installed.

  python3 <plugin>/adapters/git/install.py [--repo DIR] [--print] [--on-missing block|skip]

Writes `<git common dir>/hooks/pre-commit`, shared by every worktree of the clone, calling
the newest installed copy of this adapter, so a plugin update reaches the gate without a
re-install. Newest is the highest `plugin.json` version across this marketplace's `cache/` copies
and the `synced/` ones, when this copy sits in one; otherwise the hook calls this copy. It writes nothing when the repo already has a hook of its own, or sets
`core.hooksPath`: it prints the lines to add to that hook instead, and displaces nothing.
`--print` prints those lines and changes nothing. `--runner` prints lines setting `runner`
to this plugin's `run.py` the same way, naming what was searched when none is found, for a
landing step that runs the gate by hand; bash and zsh both read them.

With no copy found, the lines refuse the commit with exit 2, the adapter's code for a gate that
could not run, where the index carries `.claude/guards.json`, naming what was searched, the
install and `git commit -n`, and pass where it does not, since that repo never opted
in, saying nothing was judged. `--on-missing skip` prints a named skip instead, for a repo
whose contributors commit without the plugin; a re-install passes it again.

Exit 0, including when it only printed the lines; 2 when DIR is not a git checkout.
"""
import argparse, os, re, shlex, stat, subprocess, sys

MARK = "# guards — written by adapters/git/install.py"
HERE = os.path.dirname(os.path.abspath(__file__))
ADAPTER = "adapters/git/pre-commit"
MARKETPLACE = "no-lost-threads"


def git(repo, *args):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def under_home(path):
    """Shell for `path`, through $HOME when it sits there, so a tracked hook fits any machine."""
    home = os.path.expanduser("~")
    if path.startswith(home + os.sep):
        return '"$HOME"/' + shlex.quote(path[len(home) + 1:])
    return shlex.quote(path)


def in_quotes(path):
    """`path` for inside a double-quoted string, through $HOME when it sits there."""
    home = os.path.expanduser("~")
    prefix = ""
    if path.startswith(home + os.sep):
        prefix, path = "$HOME/", path[len(home) + 1:]
    return prefix + re.sub(r'([\\"`$])', r"\\\1", path)


def installed_at(plugin):
    """(plugin root, marketplace) when this copy sits under a plugin root's `cache/` or
    `synced/`, else None. A synced copy names no marketplace, so the lookup takes this repo's."""
    m = re.fullmatch(r"(.+)/cache/([^/]+)/[^/]+/\d+(?:\.\d+)+[0-9A-Za-z.+-]*", plugin)
    if m:
        return m.group(1), m.group(2)
    m = re.fullmatch(r"(.+)/synced/[^/]+/[^/]+", plugin)
    return (m.group(1), MARKETPLACE) if m else None


def locate(plugin, rel):
    """Shell yielding `rel` in this plugin: the copy with the highest manifest version, a
    release above its prereleases, across this marketplace's cache and the synced copies, whose
    paths need not carry a version; else this copy. A copy with no readable version never wins.
    Written for bash 3.2 and zsh too: `find` rather than a glob, which zsh aborts on when
    nothing matches, and a `case` pattern with its leading paren, which bash 3.2 needs inside
    `$(...)`. Empty when no copy is left, and `|| true` keeps that a value under `set -e` and
    `pipefail`, not an exit."""
    at = installed_at(plugin)
    if at is None:
        return under_home(os.path.join(plugin, rel))
    root, market = at
    depth = rel.count("/") + 1
    return (f'$(r={under_home(root)}; {{ find "$r"/cache/{shlex.quote(market)}/guards -maxdepth {depth + 1} '
            f"-type f -path '*/{rel}' || true; "
            f'find "$r"/synced -maxdepth {depth + 2} -type f '
            f"\\( -path '*/guards/{rel}' -o -path '*/guards~*/{rel}' \\) || true; }} 2>/dev/null "
            '| while IFS= read -r f; do '
            f"""v=$(sed -n '/"version"/{{s/.*"version"[^"]*"\\([^"]*\\)".*/\\1/p;q;}}' """
            f'"${{f%/{rel}}}/.claude-plugin/plugin.json" 2>/dev/null || true); '
            'case "$v" in ([0-9]*) ;; (*) continue ;; esac; '
            'case "$v" in (*-*) p=0 ;; (*) p=1 ;; esac; '
            """printf '%s\\t%s\\t%s\\n' "${v%%-*}" "$p" "$f"; done """
            '| sort -V | tail -n 1 | cut -f3- || true)')


def searched(plugin):
    at = installed_at(plugin)
    return f"{in_quotes(at[0])}/cache and /synced" if at else in_quotes(os.path.join(plugin, ADAPTER))


def runner(plugin):
    return (f'runner={locate(plugin, "run.py")}\n'
            f'[ -f "$runner" ] || echo "guards: plugin not found in {searched(plugin)}" >&2\n')


def lines(plugin, on_missing="block"):
    head = (f'guards={locate(plugin, ADAPTER)}\n'
            'if [ -f "$guards" ]; then bash "$guards" || exit $?\n')
    if on_missing == "skip":
        return head + 'else echo "pre-commit: guards skipped, plugin not installed" >&2; fi\n'
    return head + ('elif git ls-files --cached --error-unmatch -- .claude/guards.json >/dev/null 2>&1; then\n'
                   f'  echo "pre-commit: guards plugin not found in {searched(plugin)}, commit refused; install it '
                   '(/plugin install guards@no-lost-threads), or git commit -n skips the pre-commit and commit-msg hooks once" >&2\n'
                   '  exit 2\n'
                   'else echo "pre-commit: guards plugin not found, no .claude/guards.json in the index, nothing judged" >&2; fi\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--print", action="store_true", dest="only_print")
    ap.add_argument("--runner", action="store_true")
    ap.add_argument("--on-missing", choices=["block", "skip"], default="block",
                    help="what the lines do when no copy of the plugin is found (default: block)")
    a = ap.parse_args()
    plugin = os.path.dirname(os.path.dirname(HERE))
    if a.runner:
        sys.stdout.write(runner(plugin))
        return
    block = lines(plugin, a.on_missing)
    if a.only_print:
        sys.stdout.write(block)
        return
    common = git(a.repo, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if not common:
        print(f"guards install: {a.repo} is not a git checkout", file=sys.stderr)
        sys.exit(2)
    hooks_path = git(a.repo, "config", "core.hooksPath")
    hook = os.path.join(common, "hooks", "pre-commit")
    theirs = os.path.isfile(hook) and MARK not in open(hook, encoding="utf-8", errors="replace").read()
    if hooks_path or theirs:
        print(f"guards install: this repo has its own hook ({hooks_path or hook}); nothing written. "
              "Add these lines to it:", file=sys.stderr)
        sys.stdout.write(block)
        return
    os.makedirs(os.path.dirname(hook), exist_ok=True)
    with open(hook, "w", encoding="utf-8") as f:
        f.write("#!/usr/bin/env bash\n" + MARK + "\n" + block)
    os.chmod(hook, os.stat(hook).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"guards install: wrote {hook}; inert until the repo has .claude/guards.json", file=sys.stderr)


if __name__ == "__main__":
    main()
