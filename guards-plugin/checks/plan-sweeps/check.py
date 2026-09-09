#!/usr/bin/env python3
"""plan-sweeps — every backticked `rg …` a plan carries runs, and a malformed one is a
finding.

  check.py --root DIR --paths PATH [--paths PATH]... [--exclude GLOB]...

A sweep written into a plan is a claim that it was run against the tree; one that cannot
have run — a regex `rg` refuses, a path it cannot open — is a stated conclusion with no
measurement behind it. This check takes each code span beginning `rg ` (a single-line
span; fenced blocks are not read), splits it to argv, and runs it with a 20-second bound
in the checkout. Exit 0 and 1 are both sane — a sweep may match or not. Exit 2 is the
finding, with `rg`'s stderr on one line; a sweep that does not finish within the bound is
a finding too, since a plan's sweep is one a reader can re-run.

It executes plan text from a pre-commit hook, so it never uses a shell. A span is split
by `shlex`, must have `rg` as argv[0], and is skipped — never run — when the shell would
act on it: `;`, `|`, `&`, `$`, a redirect, or a glob character outside quotes (the shell
would have expanded a glob; `rg` reads it as a path), or `$` or a backtick inside double
quotes. Inside single quotes nothing expands, so a regex alternation runs. `--pre`,
`--pre-glob`, and `--search-zip` (`-z`) are skipped too: they make `rg` run a program. Skipped spans are counted
on stderr, never reported. A line carrying `<!-- guards-allow: plan-sweeps -->` is not
read: that is how a doc shows a malformed sweep on purpose.

The sweeps run in the checkout, not in the tree under `--root`: the git adapter judges an
export of the index that holds the plans and not the sources they sweep, and hands the
checkout's top level over as `GUARDS_TREE`; absent that, `--root` is the checkout. `rg`
must be on `PATH`, or the check refuses.

Scope: the universe is `--paths` — each entry a root-relative file, or an fnmatch glob
where `*` crosses `/` as in a git pathspec; a literal is tried first, so a name
carrying glob characters still selects the file bearing it, and an entry naming no
file refuses. A glob matches the index listing the git adapter hands over
(`GUARDS_INDEX`), else the tracked files in a git checkout, else every file present; a
file so listed that the tree lacks refuses by name, as the export dropped it. An entry
is normalized (`./docs/*.md` is `docs/*.md`); one outside the root refuses.
`--exclude` removes fnmatch patterns from it and applies after. A glob narrows within
`*.md`.

Findings on stdout, one per line: `<path>:<line>: <message>`.
Exit 0 pass; 1 findings; 2 refused (root missing, a file in scope unreadable, no
files in scope, `rg` not on PATH).
"""
import argparse
import fnmatch
import functools
import os
import pathlib
import posixpath
import re
import shlex
import shutil
import subprocess
import sys

ID = "plan-sweeps"
TIMEOUT = 20
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
SPAN = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)")
UNSAFE = re.compile(r"[\n\r]")
RUNS_A_PROGRAM = ("--pre", "--pre-glob", "--search-zip", "-z")
TREE = os.environ.get("GUARDS_TREE")
ALLOW = f"guards-allow: {ID}"


def spans(text):
    """(line number, span content) for every code span outside a fenced block."""
    fence = None
    for n, line in enumerate(text.splitlines(), 1):
        m = FENCE.match(line)
        if fence is None:
            if m:
                fence = m.group(1)
                continue
            if ALLOW in line:
                continue
            for s in SPAN.finditer(line):
                yield n, s.group(2).strip()
        elif m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) \
                and line.strip() == m.group(1):
            fence = None


def shell_would_act(text):
    """True when the shell would do something to this text that `shlex` does not: a
    pipe, chain, redirect, or background `&` outside quotes; `$` or a glob character
    outside quotes; `$` or a backtick inside double quotes. Inside single quotes nothing
    expands, so a regex alternation `'a|b'` or an anchor `'^x$'` is plain text."""
    quote = None
    for c in text:
        if quote == "'":
            if c == "'":
                quote = None
        elif quote == '"':
            if c == '"':
                quote = None
            elif c in "$`":
                return True
        elif c in "'\"":
            quote = c
        elif c in ";|&<>$`*?[":
            return True
    return quote is not None  # an unclosed quote: the shell would keep reading


def argv_of(span):
    """The argv to run, or None when the span is not a plain `rg` command."""
    if not span.startswith("rg "):
        return None
    if UNSAFE.search(span) or shell_would_act(span):
        return None
    try:
        argv = shlex.split(span)
    except ValueError:
        return None
    if not argv or argv[0] != "rg":
        return None
    for a in argv[1:]:
        if a in RUNS_A_PROGRAM or a.startswith(("--pre=", "--pre-glob=")):
            return None
        if a.startswith("-") and not a.startswith("--") and "z" in a:
            return None  # a short-flag cluster carrying -z
    return argv


def run(argv, cwd):
    """(exit code, rg's stderr in one line) — exit -1 with a message when the bound passed."""
    try:
        r = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                           timeout=TIMEOUT, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return -1, f"did not finish within {TIMEOUT}s"
    lines = [l.strip() for l in r.stderr.splitlines()
             if l.strip() and set(l.strip()) != {"^"}]
    return r.returncode, " · ".join(lines[:4])[:200]


def refuse(msg):
    print(f"{ID}: {msg}", file=sys.stderr)
    sys.exit(2)


INDEX = os.environ.get("GUARDS_INDEX")


def normalize(flag, p):
    """Root-relative POSIX form of a --paths or --exclude entry, so `./docs/*.md`,
    `docs//*.md`, and `docs/./*.md` name what the listing names. An entry reaching
    outside the root refuses."""
    n = posixpath.normpath(p)
    if n in (".", "..") or n.startswith(("../", "/")):
        refuse(f"{flag} {p}: not inside the root")
    return n


def is_git_root(root):
    r = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=root,
                       capture_output=True, text=True)
    return r.returncode == 0 and pathlib.Path(r.stdout.strip()).resolve() == root


def has_glob(p):
    return any(c in p for c in "*?[")


@functools.lru_cache(maxsize=None)
def index():
    """The index paths the git adapter judges, when it hands them over through
    GUARDS_INDEX — a file, one root-relative path per NUL; empty otherwise. Handed
    over, the universe is this listing rather than the exported tree, so a file the
    export dropped is refused by name instead of walked past. A path is listed once
    however many stages an unmerged index holds for it."""
    if not INDEX:
        return ()
    try:
        raw = pathlib.Path(INDEX).read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as e:
        refuse(f"GUARDS_INDEX unreadable: {e}")
    return tuple(dict.fromkeys(p for p in raw.split("\0") if p))


def listing(root, pattern="*"):
    """Root-relative files under root: the adapter's index listing when handed over,
    else the tracked ones in a git checkout, else every file present. A listed file the
    tree lacks stays listed — `present` names it — where dropping it here would let a
    glob narrow in silence while a literal naming the same file refuses. Refuses if git
    cannot be run or fails: a listing that raised would leave the process exiting 1,
    which the runner reads as findings."""
    if INDEX:
        return [p for p in index() if fnmatch.fnmatch(p, pattern)]
    try:
        rooted = is_git_root(root)
    except OSError as e:
        refuse(f"git not usable at {root}: {e}")
    if not rooted:
        return sorted(p.relative_to(root).as_posix() for p in root.rglob(pattern)
                      if p.is_file() and ".git" not in p.parts)
    try:
        out = subprocess.run(["git", "ls-files", "-z", "--", pattern], cwd=root,
                             capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError) as e:
        refuse(f"git ls-files failed at {root}: {e}")
    return [p for p in out.split("\0") if p]


def select(root, paths, pattern="*"):
    """The files `--paths` names: a literal file, or an fnmatch glob over the check's
    universe, where `*` crosses `/` as in a git pathspec. A literal is tried first, so a
    name carrying glob characters still selects the file bearing it, as a git pathspec
    does. An entry that names nothing refuses — a scope which narrows in silence is the
    failure the gate exists to prevent. A literal the index lists is selected whether or
    not the tree holds it; `present` then names the drop."""
    pool, rels = None, []
    for p in paths:
        if (root / p).is_file() or p in index():
            rels.append(p)
        elif has_glob(p):
            if pool is None:
                pool = listing(root, pattern)
            hit = [r for r in pool if fnmatch.fnmatch(r, p)]
            if not hit:
                refuse(f"--paths {p} matches no file")
            rels += hit
        elif (root / p).is_dir():
            refuse(f"--paths {p}: a directory, name the files under it as {p}/*")
        else:
            refuse(f"--paths {p}: no such file")
    seen = set()
    return [p for p in rels if not (p in seen or seen.add(p))]


def present(root, files):
    """The files in scope, each verified to be in the tree. Under the adapter, listed
    but absent means the export dropped it, and the fix is the export list, never a
    narrower scope; in a checkout it is tracked but deleted without `git rm`. Either
    way the refusal names the file rather than judging what is left."""
    for f in files:
        if f.is_file():
            continue
        rel = f.relative_to(root).as_posix()
        if INDEX:
            refuse(f"the export dropped {rel}, which this check reads; "
                   f'widen "export" in .claude/guards.json')
        refuse(f"{rel} is tracked but not in the tree")
    return files


def universe(root, paths, exclude):
    files = [root / p for p in select(root, paths, "*.md")]
    return present(root, [f for f in files
                          if not any(fnmatch.fnmatch(f.relative_to(root).as_posix(), g)
                                     for g in exclude)])


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True)
    ap.add_argument("--paths", action="append", default=[])
    ap.add_argument("--exclude", action="append", default=[])
    args = ap.parse_args()
    args.paths = [normalize("--paths", p) for p in args.paths]
    args.exclude = [normalize("--exclude", g) for g in args.exclude]

    root = pathlib.Path(args.root).resolve()
    if not root.is_dir():
        refuse(f"root not found: {args.root}")
    if not args.paths:
        refuse("--paths is required: name the plan docs whose sweeps run")
    files = universe(root, args.paths, args.exclude)
    if not files:
        refuse("no files in scope")
    if shutil.which("rg") is None:
        refuse("rg is not on PATH; the sweeps cannot run")
    tree = pathlib.Path(TREE).resolve() if TREE else root
    if not tree.is_dir():
        refuse(f"GUARDS_TREE is not a directory: {TREE}")

    findings, ran, skipped = [], 0, 0
    for f in files:
        rel = f.relative_to(root).as_posix()
        try:
            body = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            refuse(f"unreadable: {rel}: {e}")
        for n, span in spans(body):
            if not span.startswith("rg "):
                continue
            argv = argv_of(span)
            if argv is None:
                skipped += 1
                continue
            ran += 1
            code, first = run(argv, tree)
            if code in (0, 1):
                continue
            what = first if code == -1 else f"rg exited {code}: {first or 'no message'}"
            findings.append((rel, n, f"{what} — `{span}`"))

    for rel, n, msg in findings:
        print(f"{rel}:{n}: {msg}")
    print(f"{ID}: {len(files)} files, {ran} sweeps run, {skipped} skipped, "
          f"{len(findings)} findings", file=sys.stderr)
    if findings:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # never exit 1 on a crash: the runner reads 1 as findings
        refuse(f"{e.__class__.__name__}: {e}")
