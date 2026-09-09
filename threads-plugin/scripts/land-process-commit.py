#!/usr/bin/env python3
"""
land-process-commit.py — land one commit from a slice branch direct on the default
branch, through the adopter's own pre-commit hook, and print the sha the remote holds.

Usage:
    python3 land-process-commit.py <sha> [--remote origin] [--branch <name>]
                                         [--no-rebase] [--root DIR]

A `docs(process/<scope>)` commit is the review's telemetry: /threads:process-review reads
the marker-commit stream, and a squash merge erases it. So the commit lands on the
default branch by itself, from wherever the slice branch is checked out:

  1. fetch <remote> <branch>; refuse when the commit's patch is already there
  2. git worktree add --detach <tmp> <remote>/<branch>
  3. in it: git cherry-pick --no-commit <sha>, then git commit -C <sha> — a plain
     cherry-pick runs no hook; a commit runs the adopter's own pre-commit hook, so the
     commit is judged by the gate the repo already has, with no per-adopter config here
  4. the new commit's patch-id must equal the original's, or nothing is pushed
  5. git push <remote> HEAD:<branch>
  6. re-read <remote>/<branch> — the landed sha is on the remote, or it is not printed
  7. remove the worktree; rebase the slice branch onto <remote>/<branch> (the
     duplicate patch drops), or fast-forward when the current branch is <branch>

stdout carries exactly one line: the landed sha, as read back from the remote after the
push — the only sha a log or ledger line may cite. Everything else is on stderr.

Exit 0: landed and rebased. Exit 1: nothing pushed — a cherry-pick conflict, a red hook,
a patch that came out different, a refused push (fetch and rerun), or a refusal below.
Exit 3: landed (the sha is on stdout) but the rebase afterward failed and was aborted;
rebase by hand.

Refuses: a sha that is not one commit with one parent; a tree with tracked changes when
it would rebase (--no-rebase lifts it); no default branch — give --branch, or set
"defaultBranch" in .claude/threads.json, or `git remote set-head <remote> -a` so
`refs/remotes/<remote>/HEAD` names it.
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import tempfile


def err(msg):
    print(f"land-process-commit: {msg}", file=sys.stderr)


def git(*args, cwd=None, check=True, quiet=False):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                       stdin=subprocess.DEVNULL)
    if check and r.returncode != 0:
        if not quiet:
            sys.stderr.write(r.stdout)
            sys.stderr.write(r.stderr)
        raise subprocess.CalledProcessError(r.returncode, ["git", *args], r.stdout, r.stderr)
    return r


def out(*args, cwd=None):
    return git(*args, cwd=cwd).stdout.strip()


def default_branch(root, remote, flag):
    if flag:
        return flag
    cfg = pathlib.Path(root) / ".claude" / "threads.json"
    if cfg.is_file():
        try:
            v = json.loads(cfg.read_text(encoding="utf-8")).get("defaultBranch")
            if isinstance(v, str) and v:
                return v
        except (OSError, ValueError):
            pass
    r = git("symbolic-ref", "--quiet", f"refs/remotes/{remote}/HEAD", cwd=root, check=False)
    prefix = f"refs/remotes/{remote}/"
    if r.returncode == 0 and r.stdout.strip().startswith(prefix):
        return r.stdout.strip()[len(prefix):]
    return None


def patch_id(rev, cwd):
    p = git("diff-tree", "-p", "--no-commit-id", rev, cwd=cwd).stdout
    r = subprocess.run(["git", "patch-id", "--stable"], cwd=cwd, input=p,
                       capture_output=True, text=True)
    return r.stdout.split()[0] if r.stdout.split() else ""


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sha")
    ap.add_argument("--remote", default="origin")
    ap.add_argument("--branch", default=None, help="the default branch (see above)")
    ap.add_argument("--no-rebase", action="store_true",
                    help="leave the current branch alone after the push")
    ap.add_argument("--root", default=None, help="a checkout of the repo (default: cwd)")
    a = ap.parse_args()

    root = a.root or os.getcwd()
    try:
        root = out("rev-parse", "--show-toplevel", cwd=root)
    except subprocess.CalledProcessError:
        err(f"not a git checkout: {root}")
        return 1

    try:
        sha = out("rev-parse", "--verify", "--quiet", f"{a.sha}^{{commit}}", cwd=root)
    except subprocess.CalledProcessError:
        err(f"no such commit: {a.sha}")
        return 1
    parents = out("rev-list", "--parents", "-n", "1", sha, cwd=root).split()[1:]
    if len(parents) != 1:
        err(f"{sha[:10]} has {len(parents)} parents; land one ordinary commit")
        return 1
    subject = out("log", "-1", "--format=%s", sha, cwd=root)

    branch = default_branch(root, a.remote, a.branch)
    if not branch:
        err(f"no default branch known for {a.remote}: give --branch, set "
            f'"defaultBranch" in .claude/threads.json, or `git remote set-head {a.remote} -a`')
        return 1
    upstream = f"{a.remote}/{branch}"

    current = out("rev-parse", "--abbrev-ref", "HEAD", cwd=root)
    rebase = not a.no_rebase and current != "HEAD"
    dirty = out("status", "--porcelain", "--untracked-files=no", cwd=root)
    if rebase and dirty:
        n = len(dirty.splitlines())
        err(f"tracked changes in the tree ({n} file{'s' if n != 1 else ''}); the rebase after "
            f"the push needs a clean tree. If the pre-commit hook just refused a commit, these "
            f"are its changes and there is no commit to land yet: fix, commit, then rerun with "
            f"the new sha. Otherwise commit or set them aside first, or pass --no-rebase to "
            f"land {sha[:10]} and leave this branch alone.")
        return 1

    try:
        git("fetch", "--quiet", a.remote, branch, cwd=root)
    except subprocess.CalledProcessError:
        err(f"fetch {a.remote} {branch} failed")
        return 1
    # `git cherry` marks a commit whose patch upstream already holds with `-`.
    cherry = out("cherry", upstream, sha, f"{sha}^", cwd=root)
    if cherry.startswith("-"):
        err(f"{sha[:10]} ({subject}) is already on {upstream} by patch; nothing to land")
        return 1

    tmp = tempfile.mkdtemp(prefix="land-process-commit-")
    landed = None
    try:
        git("worktree", "add", "--quiet", "--detach", tmp, upstream, cwd=root)
        try:
            git("cherry-pick", "--no-commit", sha, cwd=tmp)
        except subprocess.CalledProcessError:
            git("cherry-pick", "--abort", cwd=tmp, check=False)
            err(f"cherry-pick of {sha[:10]} onto {upstream} conflicts; nothing pushed")
            return 1
        try:
            git("commit", "--quiet", "-C", sha, cwd=tmp)
        except subprocess.CalledProcessError:
            err(f"the pre-commit hook refused {sha[:10]} on {upstream}, or there was "
                f"nothing to commit; nothing pushed")
            return 1
        new = out("rev-parse", "HEAD", cwd=tmp)
        same = patch_id(sha, tmp) == patch_id(new, tmp)
        if not same:
            err(f"the landed patch differs from {sha[:10]} (a hook rewrote it, or the "
                f"pick fuzzed); nothing pushed")
            return 1
        err(f"patch identical to {sha[:10]}: {subject}")
        try:
            git("push", "--quiet", a.remote, f"HEAD:refs/heads/{branch}", cwd=tmp)
        except subprocess.CalledProcessError:
            err(f"push to {upstream} refused (a race?); fetch and rerun — nothing landed")
            return 1
        remote_tip = out("ls-remote", a.remote, f"refs/heads/{branch}", cwd=tmp).split()
        remote_tip = remote_tip[0] if remote_tip else ""
        git("fetch", "--quiet", a.remote, branch, cwd=root)
        on_remote = remote_tip == new or git("merge-base", "--is-ancestor", new, upstream,
                                             cwd=root, check=False).returncode == 0
        if not on_remote:
            err(f"pushed, but {a.remote} {branch} does not hold {new[:10]} on re-read; "
                f"not citing it")
            return 1
        landed = new
        if remote_tip != new:
            err(f"{upstream} has moved past the landing to {remote_tip[:10]}")
    finally:
        git("worktree", "remove", "--force", tmp, cwd=root, check=False)
        git("worktree", "prune", cwd=root, check=False)

    print(landed)
    sys.stdout.flush()
    err(f"landed on {upstream}: {landed}")

    if not rebase:
        return 0
    if current == branch:
        r = git("merge", "--ff-only", upstream, cwd=root, check=False)
        if r.returncode != 0:
            err(f"fast-forward of {branch} to {upstream} failed; do it by hand")
            return 3
        err(f"{branch} fast-forwarded to {upstream}")
        return 0
    r = git("rebase", "--quiet", upstream, cwd=root, check=False)
    if r.returncode != 0:
        git("rebase", "--abort", cwd=root, check=False)
        err(f"rebase of {current} onto {upstream} failed and was aborted; rebase by hand")
        return 3
    left = out("rev-list", "--count", f"{upstream}..HEAD", cwd=root)
    err(f"{current} rebased onto {upstream}; {left} commits remain on it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
