#!/usr/bin/env python3
"""anchors — every in-repo section link resolves to an explicit anchor, and every
relative link target exists.

  check.py --root DIR [--paths PATH]... [--exclude GLOB]...

Two properties over every markdown file in scope:
  1. Every `](path#frag)` whose path names a file in scope resolves to an explicit
     `<a id="frag">` in that file. Heading-derived slugs fail by design — sections
     carry an explicit anchor and are referenced by it, so rewording a heading cannot
     break an inbound link.
  2. Every relative `](path)` target exists: in the tree, or in the index listing the
     git adapter hands over, since an export narrower than the link graph is not a
     broken link.
External links (`://`) are skipped. Fenced code blocks and code spans are not prose.

Scope: `--paths` narrows the universe — each entry a root-relative file, or an fnmatch
glob where `*` crosses `/` as in a git pathspec; a literal is tried first, so a name
carrying glob characters still selects the file bearing it, and an entry naming no
file refuses. A glob matches the index listing the git adapter hands over
(`GUARDS_INDEX`), else the tracked files in a git checkout, else every file present; a
file so listed that the tree lacks refuses by name, as the export dropped it. An entry
is normalized (`./docs/*.md` is `docs/*.md`); one outside the root refuses. A glob
matches within this check's `*.md` universe, never past it. Without `--paths`, the
universe is every tracked `*.md` under the root when the root is a git checkout, else
every `*.md` under it. `--exclude` removes fnmatch patterns from the universe and
applies after `--paths`.

Findings on stdout, one per line: `<path>:<line>: <message>`.
Exit 0 pass; 1 findings; 2 refused (root missing, a file in scope unreadable, no
files in scope).
"""
import argparse
import fnmatch
import functools
import os
import pathlib
import posixpath
import re
import subprocess
import sys

ID = "anchors"
REF = re.compile(r"\]\(([^)#\s]*)(?:#([^)\s]+))?\)")
ANCHOR = re.compile(r'<a id="([^"]+)">')
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
RUN = re.compile(r"`+")


def strip_spans(line):
    """Blank every code span: a backtick run closed by a run of the same length."""
    out, i = [], 0
    while True:
        m = RUN.search(line, i)
        if not m:
            out.append(line[i:])
            return "".join(out)
        n = len(m.group())
        close = re.compile(f"(?<!`)`{{{n}}}(?!`)").search(line, m.end())
        if not close:
            out.append(line[i:m.end()])
            i = m.end()
            continue
        out.append(line[i:m.start()])
        i = close.end()


def prose_lines(text):
    """(line number, line) for every prose line: fences skipped, spans blanked."""
    fence = None
    for n, line in enumerate(text.splitlines(), 1):
        m = FENCE.match(line)
        if fence is None:
            if m:
                fence = m.group(1)
                continue
            yield n, strip_spans(line)
        elif m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) \
                and line.strip() == m.group(1):
            fence = None


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


@functools.lru_cache(maxsize=None)
def indexed():
    """The index listing as a set of files and the set of directories holding them,
    for a link target the exported tree lacks."""
    files = set(index())
    dirs = {d for p in files for d in pathlib.PurePosixPath(p).parents}
    return files, {d.as_posix() for d in dirs}


def target_exists(root, src, target):
    """The link target is in the tree, or the index lists it as a file or a directory."""
    if (src.parent / target).exists():
        return True
    if not INDEX:
        return False
    here = src.parent.relative_to(root).as_posix()
    rel = posixpath.normpath(posixpath.join(here, target))
    files, dirs = indexed()
    return rel in files or rel in dirs


def universe(root, paths, exclude):
    files = [root / p for p in (select(root, paths, "*.md") if paths
                                else listing(root, "*.md"))]
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
    files = universe(root, args.paths, args.exclude)
    if not files:
        refuse("no files in scope")

    text = {}
    for f in files:
        try:
            text[f.resolve()] = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            refuse(f"unreadable: {f.relative_to(root)}: {e}")
    anchors = {f: set(ANCHOR.findall(body)) for f, body in text.items()}

    findings = []
    for src, body in text.items():
        rel = src.relative_to(root).as_posix()
        for n, line in prose_lines(body):
            for target, frag in REF.findall(line):
                if "://" in target:
                    continue
                if target and not target_exists(root, src, target):
                    findings.append((rel, n, f"missing link target {target}"))
                    continue
                if not frag:
                    continue
                dst = (src.parent / target).resolve() if target else src
                if dst not in anchors:
                    continue  # a fragment into a file outside the scope
                if frag not in anchors[dst]:
                    findings.append((rel, n, f"dead anchor {target or src.name}#{frag}"))

    for rel, n, msg in sorted(set(findings)):
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
