#!/usr/bin/env python3
"""marker-stream — the marker-commit stream since the mark, classified.

  marker-stream.py [list|count|files] [--since REV] [--all] [--head REV]
                   [--pattern BRE] [--root DIR]

A marker commit is one whose subject matches `markerPattern` in `.claude/threads.json`
(a BRE, anchored, subject only). Not every marker is a process change the review has
yet to see, and counting them as if they were is how the review feeds its own trigger:

  organic      a change to how the repo works that no review has adjudicated — the
               retro's escape hatch, a rule landed by hand, a slice's process commit.
               The trigger and the review's ranking read these and only these.
  review       a commit the review landed — a candidate or its bookkeeping — carrying
               the trailer `Process-Review: <date>` that the review writes on every
               commit it makes. Already adjudicated; its sha is a LANDED ref, not churn.
  bookkeeping  a commit that touched nothing but the log, the ledger, or the capability
               store (`retroLogPath`, `ledgerPath`, `capabilityEvidencePath`): a capture,
               a status line, a compaction. A status flip changed no rule.

Modes:
  list   (default) the summary line, then one line per marker: `<class>\t<sha>\t<subject>`
  count  the summary line only
  files  the summary line, then organic commits per file, `<n>\t<path>`, most first,
         and how many files meet `trigger.concentration` — the retro's concentration read

The range is `<markTag>..HEAD` (the mark from the config, default `process-review-mark`);
`--since REV` replaces the start, `--head REV` the end (the pre-flight reads the remote's
default branch, not the local head), `--all` reads the whole history of the head — the
tally. `--pattern` overrides the config's pattern, for the bootstrap proof. The summary
line names the range, the mark's date, and the four counts:

  36 markers since process-review-mark (2026-09-08, ba7d3a35)..HEAD: 9 organic · 21 review · 6 bookkeeping

Exit 0; 2 when the config is malformed, the mark is missing without --since/--all, or git
fails.
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

TRAILER = "Process-Review"
DEFAULT_PATTERN = "^docs(process"
DEFAULT_MARK = "process-review-mark"


def refuse(msg):
    print(f"marker-stream: {msg}", file=sys.stderr)
    sys.exit(2)


def git(args, cwd):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        refuse(f"git {' '.join(args[:2])} failed: {r.stderr.strip()}")
    return r.stdout


def bre_to_python(pattern):
    """A POSIX BRE as Python re: bare ( ) { } | + ? are literal in BRE and special in
    Python; backslashed ones are the reverse. Character classes are left alone —
    an escaped metacharacter inside a Python class is still that literal."""
    out, i = [], 0
    specials = "(){}|+?"
    while i < len(pattern):
        c = pattern[i]
        if c == "\\" and i + 1 < len(pattern):
            n = pattern[i + 1]
            out.append(n if n in specials else "\\" + n)
            i += 2
            continue
        out.append("\\" + c if c in specials else c)
        i += 1
    return "".join(out)


def config(root):
    cfg = root / ".claude" / "threads.json"
    if not cfg.is_file():
        return {}
    try:
        return json.loads(cfg.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        refuse(f"{cfg}: malformed ({e})")


def commits(root, rng):
    """[(sha, short, subject, trailer, files)] newest first, one git call."""
    fmt = "%x00%H%x1f%h%x1f%s%x1f%(trailers:key=" + TRAILER + ",valueonly)%x1e"
    raw = git(["log", *rng, "--format=" + fmt, "--name-only"], root)
    out = []
    for chunk in raw.split("\x00"):
        if not chunk.strip():
            continue
        head, _, rest = chunk.partition("\x1e")
        sha, short, subject, trailer = (head.split("\x1f") + ["", "", "", ""])[:4]
        files = [l.strip() for l in rest.splitlines() if l.strip()]
        out.append((sha, short, subject, trailer.strip(), files))
    return out


def classify(entries, marker, bookkeeping):
    rows = []
    for sha, short, subject, trailer, files in entries:
        if not marker.search(subject):
            continue
        if trailer:
            cls = "review"
        elif all(f in bookkeeping for f in files):
            cls = "bookkeeping"
        else:
            cls = "organic"
        rows.append((cls, sha, short, subject, files))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", nargs="?", default="list", choices=["list", "count", "files"])
    ap.add_argument("--since", default=None, metavar="REV", help="range start (default: the mark)")
    ap.add_argument("--head", default="HEAD", metavar="REV", help="range end (default: HEAD)")
    ap.add_argument("--all", action="store_true", help="the whole history of --head")
    ap.add_argument("--pattern", default=None, metavar="BRE", help="override markerPattern")
    ap.add_argument("--root", default=None, help="repo root (default: git top level)")
    a = ap.parse_args()

    root = pathlib.Path(a.root or git(["rev-parse", "--show-toplevel"], None).strip()).resolve()
    cfg = config(root)
    pattern = a.pattern or cfg.get("markerPattern") or DEFAULT_PATTERN
    try:
        marker = re.compile(bre_to_python(pattern))
    except re.error as e:
        refuse(f"markerPattern {pattern!r} does not compile: {e}")
    mark = cfg.get("markTag") or DEFAULT_MARK
    bookkeeping = {p for p in (cfg.get("retroLogPath", ".claude/threads-retro-log.md"),
                               cfg.get("ledgerPath", ".claude/threads-review-ledger.md"),
                               cfg.get("capabilityEvidencePath"))
                   if isinstance(p, str) and p}
    concentration = int((cfg.get("trigger") or {}).get("concentration", 3))

    if a.all:
        rng, label = [a.head], f"all of {a.head}"
    else:
        start = a.since or mark
        r = subprocess.run(["git", "rev-parse", "--verify", "--quiet", start + "^{commit}"],
                           cwd=root, capture_output=True, text=True)
        if r.returncode != 0:
            refuse(f"no such rev: {start}" + ("" if a.since else
                   f" — the mark; bootstrap sets it, or pass --since/--all"))
        date = git(["log", "-1", "--format=%ad", "--date=short", start], root).strip()
        short = git(["rev-parse", "--short", start], root).strip()
        rng, label = [f"{start}..{a.head}"], f"{start} ({date}, {short})..{a.head}"

    rows = classify(commits(root, rng), marker, bookkeeping)
    n = {c: sum(1 for r in rows if r[0] == c) for c in ("organic", "review", "bookkeeping")}
    print(f"{len(rows)} markers since {label}: {n['organic']} organic · "
          f"{n['review']} review · {n['bookkeeping']} bookkeeping")
    if a.mode == "count":
        return 0
    if a.mode == "list":
        for cls, sha, short, subject, files in rows:
            print(f"{cls}\t{short}\t{subject}")
        return 0
    per_file = {}
    for cls, sha, short, subject, files in rows:
        if cls != "organic":
            continue
        for f in files:
            per_file.setdefault(f, set()).add(sha)
    ranked = sorted(per_file.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    hot = sum(1 for _, s in ranked if len(s) >= concentration)
    print(f"{len(ranked)} files touched by organic markers; {hot} at or above "
          f"concentration {concentration}")
    for path, shas in ranked:
        print(f"{len(shas)}\t{path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
