#!/usr/bin/env python3
"""install — wire the git pre-commit adapter from wherever this plugin is installed.

  python3 <plugin>/adapters/git/install.py [--repo DIR] [--print]

Writes `<git common dir>/hooks/pre-commit`, shared by every worktree of the clone, calling
the newest installed copy of this adapter, so a plugin update reaches the gate without a
re-install. It writes nothing when the repo already has a hook of its own, or sets
`core.hooksPath`: it prints the lines to add to that hook instead, and displaces nothing.
`--print` prints those lines and changes nothing. `--runner` prints a line setting `runner`
to this plugin's `run.py` the same way, for a landing step that runs the gate by hand.

Exit 0, including when it only printed the lines; 2 when DIR is not a git checkout.
"""
import argparse, os, re, shlex, stat, subprocess, sys

MARK = "# guards — written by adapters/git/install.py"
HERE = os.path.dirname(os.path.abspath(__file__))
ADAPTER = "adapters/git/pre-commit"


def git(repo, *args):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def under_home(path):
    """Shell for `path`, through $HOME when it sits there, so a tracked hook fits any machine."""
    home = os.path.expanduser("~")
    if path.startswith(home + os.sep):
        return '"$HOME"/' + shlex.quote(path[len(home) + 1:])
    return shlex.quote(path)


def locate(plugin, rel):
    """Shell yielding `rel` in this plugin: the newest version when this copy sits in a
    versioned cache directory, else this copy. Empty when no copy is left, and `|| true`
    keeps that a value under `set -e` and `pipefail`, not an exit."""
    parent, version = os.path.split(plugin)
    if re.fullmatch(r"\d+(?:\.\d+)+[0-9A-Za-z.+-]*", version):
        return f'$(ls -d {under_home(parent)}/*/{rel} 2>/dev/null | sort -V | tail -n 1 || true)'
    return under_home(os.path.join(plugin, rel))


def lines(plugin):
    return (f'guards={locate(plugin, ADAPTER)}\n'
            'if [ -f "$guards" ]; then bash "$guards" || exit $?\n'
            'else echo "pre-commit: guards skipped, plugin not installed" >&2; fi\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--print", action="store_true", dest="only_print")
    ap.add_argument("--runner", action="store_true")
    a = ap.parse_args()
    plugin = os.path.dirname(os.path.dirname(HERE))
    if a.runner:
        print(f'runner={locate(plugin, "run.py")}')
        return
    block = lines(plugin)
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
