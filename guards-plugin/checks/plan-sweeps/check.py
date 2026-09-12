#!/usr/bin/env python3
"""plan-sweeps — every backticked `rg …` a plan carries runs, a malformed one is a finding,
and a count the plan states beside a sweep must be the count the sweep finds.

  check.py --root DIR --paths PATH [--paths PATH]... [--exclude GLOB]...

A sweep written into a plan is a claim that it was run against the tree; one that cannot
have run — a regex `rg` refuses, a path it cannot open — is a stated conclusion with no
measurement behind it. This check takes each code span beginning `rg ` (a single-line
span; fenced blocks are not read), splits it to argv, and runs it with a 20-second bound
in the checkout. Exit 0 and 1 are both sane — a sweep may match or not. Exit 2 is the
finding, with `rg`'s stderr on one line; a sweep that does not finish within the bound is
a finding too, since a plan's sweep is one a reader can re-run.

A number written beside a sweep is a second claim: that the sweep found that many. It is
read when it directly follows the span — after `→`, `—`, `–`, `(`, `:`, `=`, or the word
`returns` / `finds` / `yields` — as an integer, bold or not, with a unit: `hit(s)`,
`match(es)`, `line(s)`, `site(s)`, `occurrence(s)`, `result(s)` count matching lines;
`file(s)` count files with a match; one adjective may sit between (`4 code hits`, `58 call
sites`); after `→` a bare integer, or one followed by `today`, counts lines. `≥N` and `≤N`
are bounds. When the span is the last thing on its line, the next line is read for the
count. A number followed by `:` is an output line (`— 173:    case started(`), one
followed by `→` is a before/after pair (`(4 → 0)`), and neither is a count. A trailing
`| wc -l` on the span is read as a line count of the sweep's output and the sweep runs
without the pipe. The count is taken as the writer saw it: `--count` output summed,
`--files-with-matches` output counted as files; otherwise the sweep is re-run with
`--count` (`--count-matches` under `-o`) or `--files-with-matches`. A stated count the run
does not reproduce is a finding naming both numbers. A count under a heading whose text
begins with an entry of `targetHeadings` (default `Acceptance`) is a target — the state
the tree will have after the change — so its sweep runs but its number is not compared;
the heading is compared without its trailing HTML comment, case-insensitively. The key sits
in this check's own `.claude/guards.json` entry, beside `rung`:

  "plan-sweeps": { "rung": "block", "paths": ["Plans/active/*.md"],
                   "targetHeadings": ["Acceptance", "Exit conditions"] }

It executes plan text from a pre-commit hook, so it never uses a shell. A span is split
by `shlex`, must have `rg` as argv[0], and is skipped — never run — when the shell would
act on it: `;`, `|` (other than the trailing `| wc -l`), `&`, `$`, a redirect, or a glob
character outside quotes (the shell would have expanded a glob; `rg` reads it as a path),
or `$` or a backtick inside double quotes. Inside single quotes nothing expands, so a regex
alternation runs. `--pre`, `--pre-glob`, and `--search-zip` (`-z`) are skipped too: they
make `rg` run a program. Skipped spans are counted on stderr, never reported. A line
carrying `<!-- guards-allow: plan-sweeps -->` is not read: that is how a doc shows a
malformed sweep on purpose.

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
files in scope, `rg` not on PATH, a malformed `targetHeadings`).
"""
import argparse
import fnmatch
import functools
import json
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
HEADING = re.compile(r"^ {0,3}#{1,6}\s+(.*?)\s*#*\s*$")
COMMENT = re.compile(r"<!--.*?-->")
WC = re.compile(r"\s*\|\s*wc\s+-l\s*$")
DEFAULTS = {"targetHeadings": ["Acceptance"]}
LINES = ("hit", "hits", "match", "matches", "line", "lines", "site", "sites",
         "occurrence", "occurrences", "result", "results")
FILES = ("file", "files")
COUNT = re.compile(
    r"^\s*(?P<lead>→|—|–|\(|:|=|returns|finds|yields)\s*\**\s*"
    r"(?P<bound>≥|≤|>=|<=)?\s*(?P<n>\d+)\**"
    r"(?:[ \t]+(?P<w1>[A-Za-z][A-Za-z-]*))?(?:[ \t]+(?P<w2>[A-Za-z][A-Za-z-]*))?"
    r"\**(?P<after>.*)$")
# short flags that take a value: the letters after one in a cluster are the value
TAKES_VALUE = set("efgtTmABCEMrjd")


def heading_text(line):
    """The heading's text with a trailing HTML comment removed, or None."""
    m = HEADING.match(line)
    if not m:
        return None
    return COMMENT.sub("", m.group(1)).strip()


def spans(text, targets=()):
    """(line number, span content, tail, target) for every code span outside a fenced
    block: `tail` is the text after the span up to the next span on the line, or the
    next line when nothing follows the span on its own; `target` is True under a heading
    whose text begins with an entry of `targets`, where a count is the tree's state after
    the change and is not compared."""
    fence, target = None, False
    lines = text.splitlines()
    for i, line in enumerate(lines):
        n = i + 1
        m = FENCE.match(line)
        if fence is None:
            if m:
                fence = m.group(1)
                continue
            h = heading_text(line)
            if h is not None:
                low = h.lower()
                target = any(low.startswith(t.lower()) for t in targets)
                continue
            if ALLOW in line:
                continue
            found = list(SPAN.finditer(line))
            for k, s in enumerate(found):
                end = found[k + 1].start() if k + 1 < len(found) else len(line)
                tail = line[s.end():end]
                if k + 1 == len(found) and not tail.strip("* \t") and i + 1 < len(lines) \
                        and not FENCE.match(lines[i + 1]) and heading_text(lines[i + 1]) is None:
                    nxt = lines[i + 1]
                    tail = nxt[:SPAN.search(nxt).start()] if SPAN.search(nxt) else nxt
                yield n, s.group(2).strip(), tail, target
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
    """(argv to run, via_wc), or None when the span is not a plain `rg` command. A
    trailing `| wc -l` is stripped and remembered: the writer counted the output's lines."""
    if not span.startswith("rg "):
        return None
    via_wc = bool(WC.search(span))
    if via_wc:
        span = WC.sub("", span)
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
        if a.startswith("-") and not a.startswith("--") and "z" in cluster(a):
            return None  # a short-flag cluster carrying -z
    return argv, via_wc


def cluster(arg):
    """The flag letters of a short-flag cluster, stopping at one that takes a value
    (`-nefoo` is -n, -e foo)."""
    out = ""
    for c in arg[1:]:
        out += c
        if c in TAKES_VALUE:
            break
    return out


def has_flag(argv, short, longs):
    """True when argv carries the short flag (in a cluster too) or a long spelling."""
    for a in argv[1:]:
        if a in longs or (short and a.startswith("-") and not a.startswith("--")
                          and short in cluster(a)):
            return True
    return False


def stated(tail):
    """(bound, n, unit) for a count written in `tail`, or None: `unit` is "lines" or
    "files". A number followed by `:` is an output line, one followed by `→` a
    before/after pair; a bare number counts lines only after `→`."""
    m = COUNT.match(tail)
    if not m:
        return None
    after = m.group("after").lstrip("* \t")
    if after.startswith((":", "→", "/", "–", "-")) and not after.startswith("--"):
        return None
    if after[:1].isdigit():
        return None
    w1 = (m.group("w1") or "").lower()
    w2 = (m.group("w2") or "").lower()
    if w1 in FILES or (w1 not in LINES and w2 in FILES):
        unit = "files"
    elif w1 in LINES or w2 in LINES:
        unit = "lines"
    elif w1 in ("", "today"):  # bare, or `N today`: a line count, after `→` only
        if m.group("lead") != "→":
            return None
        unit = "lines"
    else:
        return None
    return m.group("bound") or "=", int(m.group("n")), unit


def sum_counts(stdout):
    """The total of `--count` output: `path:N` per file, or a bare N for one file."""
    total = 0
    for line in stdout.splitlines():
        tail = line.rsplit(":", 1)[-1].strip()
        if tail.isdigit():
            total += int(tail)
    return total


def measure(argv, via_wc, unit, stdout, cwd):
    """(count, error) — the count the writer would have seen for `unit`, from the
    original run's stdout when it already carries it, else from a re-run with the
    counting flag. `error` is a message when the re-run failed."""
    listing = has_flag(argv, "l", ("--files-with-matches",))
    counted = has_flag(argv, "c", ("--count", "--count-matches"))
    if via_wc or listing or (counted and unit == "files"):
        return len(stdout.splitlines()), None
    if counted:
        return sum_counts(stdout), None
    if unit == "files":
        flag = "--files-with-matches"
    elif has_flag(argv, "o", ("--only-matching",)):
        flag = "--count-matches"
    else:
        flag = "--count"
    code, first, out = run(argv + [flag], cwd)
    if code not in (0, 1):
        what = first if code == -1 else f"rg exited {code}: {first or 'no message'}"
        return None, f"{what} on the count re-run with {flag}"
    return len(out.splitlines()) if unit == "files" else sum_counts(out), None


def holds(bound, n, actual):
    return {"=": actual == n, "≥": actual >= n, ">=": actual >= n,
            "≤": actual <= n, "<=": actual <= n}[bound]


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
            out[key] = v
    return out


def run(argv, cwd):
    """(exit code, rg's stderr in one line, stdout) — exit -1 with a message when the
    bound passed."""
    try:
        r = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                           errors="replace", timeout=TIMEOUT, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return -1, f"did not finish within {TIMEOUT}s", ""
    lines = [l.strip() for l in r.stderr.splitlines()
             if l.strip() and set(l.strip()) != {"^"}]
    return r.returncode, " · ".join(lines[:4])[:200], r.stdout


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

    targets = config(root)["targetHeadings"]
    findings, ran, skipped, compared, uncompared = [], 0, 0, 0, 0
    for f in files:
        rel = f.relative_to(root).as_posix()
        try:
            body = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            refuse(f"unreadable: {rel}: {e}")
        for n, span, tail, target in spans(body, targets):
            if not span.startswith("rg "):
                continue
            parsed = argv_of(span)
            if parsed is None:
                skipped += 1
                continue
            argv, via_wc = parsed
            ran += 1
            code, first, out = run(argv, tree)
            if code not in (0, 1):
                what = first if code == -1 else f"rg exited {code}: {first or 'no message'}"
                findings.append((rel, n, f"{what} — `{span}`"))
                continue
            claim = stated(tail)
            if claim is None:
                continue
            if target:
                uncompared += 1
                continue
            bound, want, unit = claim
            compared += 1
            actual, err = measure(argv, via_wc, unit, out, tree)
            if err:
                findings.append((rel, n, f"{err} — `{span}`"))
            elif not holds(bound, want, actual):
                said = f"{bound if bound != '=' else ''}{want} {unit}"
                findings.append((rel, n, f"states {said}, the sweep finds {actual} — `{span}`"))

    for rel, n, msg in findings:
        print(f"{rel}:{n}: {msg}")
    print(f"{ID}: {len(files)} files, {ran} sweeps run, {skipped} skipped, "
          f"{compared} counts compared, {uncompared} targets not compared, "
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
