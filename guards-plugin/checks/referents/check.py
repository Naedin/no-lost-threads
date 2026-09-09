#!/usr/bin/env python3
"""referents — a backticked name that nothing in the repo answers to.

  check.py --root DIR --paths PATH [--paths PATH]... [--exclude GLOB]...

A link is resolved by `anchors`; this check resolves the referents a doc names without
linking: a script by path, a slash command by name, an environment knob by prefix. Each
is read only inside a code span — prose path fragments (`/tmp`, `/dev`) never match —
and resolved against the index listing the git adapter hands over, so an export
narrower than the tree is not a missing file. Three classes:

- **script** — a word in a span beginning `<dir>/` for a `scriptDirs` entry (default
  `scripts`), with or without `./`: `scripts/lint-docs.sh --staged`. Resolves when the
  listing holds that path, a path under it, or, for a name carrying `*`, any match. A
  word carrying `<`, `>`, or an ellipsis is a placeholder and is not read.
- **command** — a span that is `/name` or `/name …`, the name `[a-z][a-z0-9-]*` with an
  optional `prefix:` part. Resolves when `<dir>/name.md` is in the listing for a
  `commandDirs` entry (default `.claude/commands`), or the name is in `knownCommands`
  (an entry ending `:` is a prefix — `threads:` answers `/threads:retro`; any other
  entry is the whole name — `code-review`).
- **env knob** — a word in a span beginning with an `envPrefixes` entry, followed by
  `[A-Z0-9_]*`; a bare prefix counts. Resolves when the token occurs in any file of the
  code tree — every indexed file that is not markdown, read through `git grep --cached`
  in the checkout (`GUARDS_TREE` under the adapter, else `--root`), or a walk of a root
  that is not a checkout. With no `envPrefixes` the class is off.

The classes are configured in this check's own entry in `.claude/guards.json`, beside
`rung`:

  "referents": { "rung": "warn", "paths": ["CLAUDE.md", "docs/*.md"],
                 "knownCommands": ["threads:", "slices:", "code-review"],
                 "envPrefixes": ["MYAPP_"] }

A line carrying `<!-- guards-allow: referents -->` is not read: that is how a doc names
an illustrative `scripts/foo.sh` or a deliberately wrong knob.

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
files in scope, a malformed config entry).
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

ID = "referents"
ALLOW = f"guards-allow: {ID}"
TREE = os.environ.get("GUARDS_TREE")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
SPAN = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)")
COMMAND = re.compile(r"^/([a-z][a-z0-9-]*(?::[a-z][a-z0-9-]*)?)(?=\s|$)")
NAME = re.compile(r"[a-z][a-z0-9-]*(?::[a-z][a-z0-9-]*)?$")
DEFAULTS = {"scriptDirs": ["scripts"], "commandDirs": [".claude/commands"],
            "knownCommands": [], "envPrefixes": []}


def spans(text):
    """(line number, span content) for every code span outside a fenced block, on a
    line not carrying the allow marker."""
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


def refuse(msg):
    print(f"{ID}: {msg}", file=sys.stderr)
    sys.exit(2)


def config(root):
    """This check's own entry in .claude/guards.json, defaults filled; a key that is not
    a list of strings refuses. No config, or no entry: the defaults."""
    out = dict(DEFAULTS)
    path = root / ".claude" / "guards.json"
    if not path.is_file():
        return out
    try:
        spec = json.loads(path.read_text(encoding="utf-8")).get("checks", {}).get(ID, {})
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, AttributeError) as e:
        refuse(f".claude/guards.json unreadable: {e}")
    if not isinstance(spec, dict):
        return out
    for key in DEFAULTS:
        if key in spec:
            v = spec[key]
            if not (isinstance(v, list) and all(isinstance(x, str) for x in v)):
                refuse(f'.claude/guards.json: "{ID}".{key} must be a list of strings')
            out[key] = [posixpath.normpath(x) if key.endswith("Dirs") else x for x in v]
    return out


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


class Resolver:
    """Existence against the listing, and knob content against the code tree."""

    def __init__(self, root, cfg):
        self.root, self.cfg = root, cfg
        self.paths = set(listing(root))
        self.dirs = {posixpath.dirname(p) for p in self.paths}
        self.dirs |= {d[:i] for d in list(self.dirs) for i in range(len(d)) if d[i] == "/"}
        self.tree = pathlib.Path(TREE).resolve() if TREE else root
        self._knob = {}

    def path_exists(self, rel):
        if "*" in rel or "?" in rel:
            return any(fnmatch.fnmatch(p, rel) for p in self.paths)
        return rel in self.paths or rel in self.dirs

    def script(self, word):
        """The script dir path a word names, or None."""
        w = word[2:] if word.startswith("./") else word
        for d in self.cfg["scriptDirs"]:
            if w.startswith(d + "/") and len(w) > len(d) + 1:
                return w.rstrip(".,;:)")
        return None

    def command_exists(self, name):
        for d in self.cfg["commandDirs"]:
            if f"{d}/{name}.md" in self.paths:
                return True
        for k in self.cfg["knownCommands"]:
            if (k.endswith(":") and name.startswith(k)) or name == k:
                return True
        return False

    def knob_exists(self, token):
        if token in self._knob:
            return self._knob[token]
        found = self._grep(token)
        self._knob[token] = found
        return found

    def _grep(self, token):
        try:
            rooted = is_git_root(self.tree)
        except OSError:
            rooted = False
        if rooted:
            r = subprocess.run(["git", "grep", "--cached", "-q", "-I", "-F", "-e", token,
                                "--", ".", ":(exclude)*.md"],
                               cwd=self.tree, capture_output=True, text=True)
            if r.returncode in (0, 1):
                return r.returncode == 0
            refuse(f"git grep failed at {self.tree}: {r.stderr.strip()}")
        for rel in self.paths:
            if rel.endswith(".md"):
                continue
            f = self.tree / rel
            try:
                if f.is_file() and token in f.read_text(encoding="utf-8", errors="ignore"):
                    return True
            except OSError:
                continue
        return False


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
        refuse("--paths is required: name the docs whose referents resolve")
    files = universe(root, args.paths, args.exclude)
    if not files:
        refuse("no files in scope")
    cfg = config(root)
    rs = Resolver(root, cfg)
    if TREE and not rs.tree.is_dir():
        refuse(f"GUARDS_TREE is not a directory: {TREE}")
    knob = [re.compile(r"(?<![A-Za-z0-9_])" + re.escape(p) + r"[A-Z0-9_]*")
            for p in cfg["envPrefixes"]]

    findings = []
    for f in files:
        rel = f.relative_to(root).as_posix()
        try:
            body = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            refuse(f"unreadable: {rel}: {e}")
        for n, span in spans(body):
            m = COMMAND.match(span)
            if m and not rs.command_exists(m.group(1)):
                findings.append((rel, n, f"command /{m.group(1)}: no command file "
                                         f"and no known command or prefix"))
            for word in span.split():
                if any(c in word for c in "<>…") or "..." in word:
                    continue  # a placeholder, not a name
                s = rs.script(word)
                if s and not rs.path_exists(s):
                    findings.append((rel, n, f"script {s}: no such file"))
            for rx in knob:
                for t in rx.findall(span):
                    if not rs.knob_exists(t):
                        findings.append((rel, n, f"env knob {t}: not in the code tree"))

    for rel, n, msg in sorted(set(findings), key=lambda x: (x[0], x[1], x[2])):
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
