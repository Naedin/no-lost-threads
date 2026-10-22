#!/usr/bin/env python3
"""deferral-trailer — a stub a landing range adds is named by a `Why-not-now:` trailer
on some commit in the range.

  check.py --root DIR --paths PATH [--paths PATH]... [--exclude GLOB]...

An inbox stub is a deferral: work someone decided not to do now. Adding one is that
decision, and the trailer is where the range says why — a reader of the history finds
it on the commit, not by diffing the inbox. A PR gate can read the trailer; a landing
that never opens a PR is judged here, from the range `run.py --diff-range` hands over
as `GUARDS_RANGE`.

In scope is every file `--paths` names (required; the stubs, e.g. `Plans/inbox/*.md`)
less `--exclude`. Over the range's diff (`A...B` from their merge base, `A..B` from A,
a single rev to HEAD; renames followed), a stub added, copied, or renamed in from
outside the scope needs a trailer. A stub modified, renamed within the scope, or
deleted needs none: no diff tells a deferral from a rewording or a consolidation, so
triage reshapes stubs freely. A new stub git pairs with a deleted one as a rename
within the scope is a reshape by the same reading.

A trailer names a stub when its value is the stub's basename without `.md`, alone or
followed by whitespace (`Why-not-now: feat-x — the reason`). It may sit on any commit
in the range. The key is `trailerKey` in this check's own `.claude/guards.json` entry,
default `Why-not-now`; git matches it case-insensitively.

Without `GUARDS_RANGE` — the git adapter's pre-commit run, where the commit message
does not exist yet — nothing is judged: exit 0 with one stderr line saying so.

Findings on stdout, one per line: `<path>:1: added with no <key>: trailer naming
<basename>`.
Exit 0 pass; 1 findings; 2 refused (root missing, no `--paths`, an entry naming no
file, a range git cannot read, a malformed `trailerKey`).
"""
import argparse
import fnmatch
import functools
import json
import os
import pathlib
import posixpath
import re
import subprocess
import sys

ID = "deferral-trailer"
KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*$")
RANGE = os.environ.get("GUARDS_RANGE")


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


def trailer_key(root):
    """`trailerKey` from this check's own entry in .claude/guards.json, default
    Why-not-now; one that is not a trailer token refuses."""
    path = root / ".claude" / "guards.json"
    if not path.is_file():
        return "Why-not-now"
    try:
        spec = json.loads(path.read_text(encoding="utf-8")).get("checks", {}).get(ID, {})
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, AttributeError) as e:
        refuse(f".claude/guards.json unreadable: {e}")
    key = spec.get("trailerKey", "Why-not-now") if isinstance(spec, dict) else "Why-not-now"
    if not (isinstance(key, str) and KEY.match(key)):
        refuse(f'.claude/guards.json: "{ID}".trailerKey must be a trailer token')
    return key


def git(root, *argv):
    r = subprocess.run(["git", "-C", str(root), "-c", "core.quotePath=false", *argv],
                       capture_output=True, text=True)
    if r.returncode != 0:
        refuse(f"GUARDS_RANGE {RANGE}: git {argv[0]}: {r.stderr.strip()}")
    return r.stdout


def bounds(root, rng):
    """(diff base, tip, excluded rev) for the range as `git diff` reads it."""
    if "..." in rng:
        a, b = rng.split("...", 1)
        a, b = a or "HEAD", b or "HEAD"
        return git(root, "merge-base", a, b).strip(), b, a
    if ".." in rng:
        a, b = rng.split("..", 1)
        a, b = a or "HEAD", b or "HEAD"
        return a, b, a
    return rng, "HEAD", rng


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
        refuse("--paths is required: name the stubs, e.g. Plans/inbox/*.md")
    present(root, [root / p for p in select(root, args.paths)])
    key = trailer_key(root)
    if not RANGE:
        print(f"{ID}: no GUARDS_RANGE (run.py --diff-range), nothing judged", file=sys.stderr)
        return

    def scoped(p):
        return (any(p == e or fnmatch.fnmatch(p, e) for e in args.paths)
                and not any(fnmatch.fnmatch(p, g) for g in args.exclude))

    base, tip, excluded = bounds(root, RANGE)
    fields = git(root, "diff", "-M", "--name-status", "-z", base, tip, "--").split("\0")
    added = []
    i = 0
    while i < len(fields) and fields[i]:
        status = fields[i]
        if status[0] in "RC":
            src, dst = fields[i + 1], fields[i + 2]
            i += 3
        else:
            src = dst = fields[i + 1]
            i += 2
        if scoped(dst) and (status[0] in "AC" or (status[0] == "R" and not scoped(src))):
            added.append(dst)

    values = git(root, "log", f"--format=%(trailers:key={key},valueonly,unfold)",
                 tip, "--not", excluded, "--").splitlines()
    values = [v.strip() for v in values if v.strip()]
    findings = []
    for path in added:
        stem = posixpath.basename(path)[:-3] if path.endswith(".md") else posixpath.basename(path)
        if not any(v == stem or re.match(re.escape(stem) + r"\s", v) for v in values):
            findings.append(f"{path}:1: added with no {key}: trailer naming {stem}")
    for f in findings:
        print(f)
    if findings:
        sys.exit(1)
    print(f"{ID}: {len(added)} stubs added in {RANGE}, each named",
          file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # never exit 1 on a crash: the runner reads 1 as findings
        refuse(f"{e.__class__.__name__}: {e}")
