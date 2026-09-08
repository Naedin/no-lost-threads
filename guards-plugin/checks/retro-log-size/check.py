#!/usr/bin/env python3
"""retro-log-size — an occurrence in the retro log fits in eight lines.

  check.py --root DIR [--paths PATH]... [--exclude GLOB]...

The grammar lets an occurrence carry continuation lines without bound, and that is
where a log grows past what any reader opens. An occurrence is the cited moment, the
cost, and the placement: eight lines at most, counted from its dated line through its
last continuation. The narrative that does not fit belongs in the commit, the stub, or
the plan the placement names.

A separate check from `retro-log` so a repo can hold the grammar at `block` while its
existing entries come under the cap at `warn`.

Scope: `--paths` names the log(s) — each entry a root-relative file, or an fnmatch
glob where `*` crosses `/` as in a git pathspec; a literal is tried first, so a name
carrying glob characters still selects the file bearing it, and an entry naming no
file refuses. A glob matches the index listing the git adapter hands over
(`GUARDS_INDEX`), else the tracked files in a git checkout, else every file present; a
file so listed that the tree lacks refuses by name, as the export dropped it. An entry
is normalized (`./docs/*.md` is `docs/*.md`); one outside the root refuses. With no
`--paths`, the log is discovered — `retroLogPath` in `.claude/threads.json`, default
`.claude/threads-retro-log.md`. `--exclude` removes fnmatch patterns after.

Findings on stdout, one per line: `<path>:<line>: <message>`.
Exit 0 pass; 1 findings; 2 refused (root missing, unreadable, no files in scope).
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

ID = "retro-log-size"
CAP = 8
KEY = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*/[a-z0-9]+(?:-[a-z0-9]+)*(?: \(uncold\))?$")
OCCURRENCE = re.compile(r"^  (\d{4}-\d{2}-\d{2}) \| ([^|]+?) \|\s*(.*)$")
DETAIL = re.compile(r"^  ")
ENTRIES = "## Entries"


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


def discover(root):
    cfg = root / ".claude" / "threads.json"
    rel = ".claude/threads-retro-log.md"
    if cfg.is_file():
        try:
            rel = json.loads(cfg.read_text(encoding="utf-8")).get("retroLogPath", rel)
        except (json.JSONDecodeError, AttributeError, OSError):
            refuse(f"{cfg.relative_to(root).as_posix()}: malformed")
    return [rel]


def check(text):
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == ENTRIES:
            start = i + 1
            break
    if start is None:
        for i, line in enumerate(lines):
            if KEY.match(line):
                start = i
                break
        else:
            return []
    out = []
    key, occ_start, occ_lines = None, None, 0

    def close():
        if occ_start is not None and occ_lines > CAP:
            out.append((occ_start, f"occurrence is {occ_lines} lines (cap {CAP}) under {key}; "
                                   "the moment, the cost, the placement — the rest goes where "
                                   "the placement points"))

    for n, line in enumerate(lines[start:], start + 1):
        if KEY.match(line):
            close()
            key, occ_start, occ_lines = line.split(" ")[0], None, 0
            continue
        if OCCURRENCE.match(line):
            close()
            occ_start, occ_lines = n, 1
            continue
        if DETAIL.match(line) and occ_start is not None:
            occ_lines += 1
    close()
    return out


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
    rels = (select(root, args.paths) if args.paths
            else [p for p in discover(root)
                  if (root / p).is_file() or p in index()])
    files = [root / p for p in rels]
    files = present(root, [f for f in files
                           if not any(fnmatch.fnmatch(f.relative_to(root).as_posix(), g)
                                      for g in args.exclude)])
    if not files:
        refuse("no files in scope")
    findings = []
    for f in files:
        rel = f.relative_to(root).as_posix()
        try:
            body = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            refuse(f"unreadable: {rel}: {e}")
        findings += [(rel, n, msg) for n, msg in check(body)]
    for rel, n, msg in findings:
        print(f"{rel}:{n}: {msg}")
    if findings:
        sys.exit(1)
    print(f"{ID}: {len(files)} files, no findings", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # never exit 1 on a crash: the runner reads 1 as findings
        refuse(f"{e.__class__.__name__}: {e}")
