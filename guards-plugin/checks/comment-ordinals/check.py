#!/usr/bin/env python3
"""comment-ordinals — no numbered plan anchor in a code comment.

  check.py --root DIR [--paths PATH]... [--exclude GLOB]...

A plan's numbered items — acceptance criterion 3, implementation note 7, section 4 —
are renumbered as the plan is edited and the plan itself is retired, so a code comment
citing one by number points at nothing a reader of the code can open. The comment
names the symbol or the §"Named section" it depends on, or states the contract itself.

A finding is a leading comment line — its first non-blank characters the file's comment
marker — carrying one of three tags, and only these (`Slice 4`, `Risk 2`, or a doc named
beside `rule 8` is not one): `§` then a digit (`§4`, `§ 4`), `AC`
then a digit after at most one space or hyphen with no word character before it (`AC3`,
`AC-3`, `AC 3`; `HVAC3` is not one), or `Impl-Note` then a number (`Impl-Note 7`,
`Impl. note #7`, `ImplNote7`). A comment trailing code and a docstring are not read;
neither are bare letter-and-digit tags (`T4`, `D7`), which are legitimate case ids.

Comment markers by file: `//`, `///`, `/*`, or a block interior `*` in `.swift`, `.c`,
`.h`, `.cc`, `.cpp`, `.hpp`, `.m`, `.mm`, `.js`, `.jsx`, `.mjs`, `.cjs`, `.ts`, `.tsx`,
`.go`, `.rs`, `.java`, `.kt`, `.kts`, `.scala`, `.cs`, `.dart`; `#` in `.sh`, `.bash`,
`.zsh`, `.ksh`, `.py`, `.rb`, `.pl`, `.pm`, `.awk`; in a file with no extension, the
marker its shebang's interpreter takes (`sh`, `bash`, `zsh`, `ksh`, `dash`, `python`,
`ruby`, `perl`, `awk` take `#`; `node` takes `//`).

A line carrying `guards-allow: comment-ordinals`, as plain text in the file's own
comment syntax, is not read — per line, never a file-wide exemption.

Scope: without `--paths`, every file with one of the extensions above, taken from the
index listing the git adapter hands over (`GUARDS_INDEX`), else the tracked files in a
git checkout, else every file present; a file with no extension enters only by name.
`--paths` narrows it — each entry a root-relative file, or an fnmatch glob where `*`
crosses `/` as in a git pathspec; a literal is tried first, and an entry naming no file
refuses. A glob stays inside the universe: a hit with another extension, or with none
and no known shebang, is dropped, and a dropped hit with no extension is named on
stderr, since nothing about its name says it went unread; a literal naming such a file
refuses, since the check cannot read it. A listed file the tree lacks refuses by name, as the export dropped it.
An entry is normalized (`./src/*.swift` is `src/*.swift`); one outside the root
refuses. `--exclude` removes fnmatch patterns and applies after.

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

ID = "comment-ordinals"
ALLOW = f"guards-allow: {ID}"
SLASH = re.compile(r"^\s*(?:///?|/\*|\*)")
HASH = re.compile(r"^\s*#")
EXTENSIONS = dict.fromkeys(
    "swift c h cc cpp hpp m mm js jsx mjs cjs ts tsx go rs java kt kts scala cs dart"
    .split(), SLASH)
EXTENSIONS.update(dict.fromkeys("sh bash zsh ksh py rb pl pm awk".split(), HASH))
INTERPRETER = re.compile(r"(sh|bash|zsh|ksh|dash|python[0-9.]*|ruby|perl|awk)|(node)")
TAG = re.compile(r"§\s?[0-9]|(?<![A-Za-z0-9_])AC[\s-]?[0-9]"
                 r"|Impl\.?[\s-]?[Nn]ote\s*#?[0-9]")


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


def shebang(f):
    """The comment marker a file's shebang interpreter takes, or None."""
    try:
        with open(f, "rb") as fh:
            first = fh.readline(256).decode("latin-1")
    except OSError as e:
        refuse(f"unreadable: {f}: {e}")
    if not first.startswith("#!"):
        return None
    words = first[2:].split()
    prog = posixpath.basename(words[0]) if words else ""
    if prog == "env":
        rest = [w for w in words[1:] if not w.startswith("-") and "=" not in w]
        prog = rest[0] if rest else ""
    m = INTERPRETER.fullmatch(prog)
    return None if not m else HASH if m.group(1) else SLASH


def comment_marker(root, rel):
    """The file's comment-marker pattern: by extension, else by shebang when it has
    none. A file with no extension must be in the tree to be read, so a dropped one
    refuses by name here as `present` would."""
    ext = posixpath.splitext(posixpath.basename(rel))[1]
    if ext:
        return EXTENSIONS.get(ext[1:])
    return shebang(present(root, [root / rel])[0])


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
    if args.paths:
        rels = select(root, args.paths)
    else:
        rels = [r for r in listing(root)
                if EXTENSIONS.get(posixpath.splitext(r)[1][1:])]
    rels = [r for r in rels if not any(fnmatch.fnmatch(r, g) for g in args.exclude)]
    scoped = []
    for rel in rels:
        marker = comment_marker(root, rel)
        if marker:
            scoped.append((rel, marker))
        elif rel in args.paths:
            refuse(f"--paths {rel}: no comment syntax known for it — an extension "
                   f"this check reads, or a shebang naming its interpreter")
        elif not posixpath.splitext(posixpath.basename(rel))[1]:
            print(f"{ID}: {rel}: not read, no extension and no known shebang",
                  file=sys.stderr)
    present(root, [root / rel for rel, _ in scoped])
    if not scoped:
        refuse("no files in scope")

    findings = []
    for rel, marker in scoped:
        try:
            body = (root / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            refuse(f"unreadable: {rel}: {e}")
        for n, line in enumerate(body.splitlines(), 1):
            m = marker.match(line)
            if not m or ALLOW in line:
                continue
            for t in TAG.finditer(line, m.end()):
                findings.append((rel, n, f'numbered plan anchor "{t.group()}" in a '
                                 f'comment (cite a symbol or a §"Named section", '
                                 f'never a number)'))

    for rel, n, msg in findings:
        print(f"{rel}:{n}: {msg}")
    if findings:
        sys.exit(1)
    print(f"{ID}: {len(scoped)} files, no findings", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # never exit 1 on a crash: the runner reads 1 as findings
        refuse(f"{e.__class__.__name__}: {e}")
