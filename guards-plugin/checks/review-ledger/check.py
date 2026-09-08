#!/usr/bin/env python3
"""review-ledger — the deferral ledger holds current state, never a window's narrative.

  check.py --root DIR [--paths PATH]... [--exclude GLOB]...

The review reads the ledger in full every run, so it carries only what a future
review acts on: three sections, each entry a top-level bullet.

  ## Live …            what was deferred, why, its promoting signal, and one
                       `last checked: <date> — <state>` line; each entry at most
                       12 lines
  ## Falsifications …  kept whole; no cap
  ## Resolved …        a pointer at the landing commit; at most 3 lines

Findings: any other section (a per-window review log belongs in the review's own
marker commit); a dated window line inside a Live entry (`09-04: no fire`,
`Re-deferred 2026-09-02:`) — the state is rewritten in place, not accreted; a Live
entry over 12 lines; a Resolved entry over 3 lines. Both caps are per entry; the
sections have no cap of their own.

Scope: `--paths` names the ledger(s) — each entry a root-relative file, or an fnmatch
glob where `*` crosses `/` as in a git pathspec; a literal is tried first, so a name
carrying glob characters still selects the file bearing it, and an entry naming no
file refuses. A glob matches the index listing the git adapter hands over
(`GUARDS_INDEX`), else the tracked files in a git checkout, else every file present; a
file so listed that the tree lacks refuses by name, as the export dropped it. An entry
is normalized (`./docs/*.md` is `docs/*.md`); one outside the root refuses. With no
`--paths`, it is discovered — `ledgerPath` in `.claude/threads.json`, default
`.claude/threads-review-ledger.md`. `--exclude` removes fnmatch patterns after.

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

ID = "review-ledger"
H2 = re.compile(r"^## (.*)$")
BULLET = re.compile(r"^- ")
WINDOW = re.compile(r"(?<![\w-])(?:20\d\d-)?\d\d-\d\d[a-z]?:")
SECTIONS = ("live", "falsifications", "resolved")
LIVE_CAP, RESOLVED_CAP = 12, 3


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
    rel = ".claude/threads-review-ledger.md"
    if cfg.is_file():
        try:
            rel = json.loads(cfg.read_text(encoding="utf-8")).get("ledgerPath", rel)
        except (json.JSONDecodeError, AttributeError, OSError):
            refuse(f"{cfg.relative_to(root).as_posix()}: malformed")
    return [rel]


def section_of(title):
    t = title.strip().lower()
    for s in SECTIONS:
        if t.startswith(s):
            return s
    return None


def check(text):
    out = []
    section = None
    entry_start, entry_lines, entry_windows = None, 0, []

    def close():
        if entry_start is None:
            return
        if section == "live":
            for n in entry_windows:
                out.append((n, "per-window line; rewrite the state in place and keep one "
                               "`last checked: <date> — <state>` line"))
            if entry_lines > LIVE_CAP:
                out.append((entry_start, f"live entry is {entry_lines} lines (cap {LIVE_CAP}): "
                                         "what, why, promoting signal, last checked"))
        elif section == "resolved" and entry_lines > RESOLVED_CAP:
            out.append((entry_start, f"resolved entry is {entry_lines} lines (cap {RESOLVED_CAP}); "
                                     "a pointer at the landing commit, the narrative lives there"))

    for n, line in enumerate(text.splitlines(), 1):
        m = H2.match(line)
        if m:
            close()
            entry_start, entry_lines, entry_windows = None, 0, []
            section = section_of(m.group(1))
            if section is None:
                out.append((n, f'section "{m.group(1).strip()}" is not Live, Falsifications, or '
                               "Resolved; a window's narrative belongs in the review's marker commit"))
            continue
        if section is None:
            continue
        if BULLET.match(line):
            close()
            entry_start, entry_lines, entry_windows = n, 0, []
        if entry_start is None or not line.strip():
            continue
        entry_lines += 1
        if section == "live" and WINDOW.search(line):
            entry_windows.append(n)
    close()
    return sorted(out)


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
