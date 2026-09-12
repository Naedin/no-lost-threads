#!/usr/bin/env python3
"""core-diff — each core doc's window, so step 0a reads the core as churn and not only
as authority.

  core-diff.py [summary|diff DOC] [--since REV] [--head REV] [--root DIR]

Step 0a reads `invariantDocs` whole every run and reports which bore on a ruling. A doc
read whole can still grow unread: a slice PR's squash lands a paragraph in it, no marker
names the change, and eleven weeks later the doc is twice its size and bears on nothing —
which the economics block then reports as grounds to stop reading it, when the question
was why. This script reads each core doc's own window, the range the marker stream reads.

Modes:
  summary  (default) one header line, then one line per doc in `invariantDocs` order:
             <path>\\t<words at since>\\t<words at head>\\t+<added> -<removed>\\t<commits>
           words are whitespace-split; added and removed count the words on the diff's
           `+` and `-` lines; commits touch the doc in the range. A doc absent at the
           range start reads `-` for its words there.
  diff DOC the doc's diff over the range, as `git diff` prints it, for the hunk-by-hunk
           read: each hunk is classed rule (a predicate, a scope boundary, a named
           exception, a decision-relevant why) or prose (narration, a symbol enumeration,
           a restated why, a worked case restating a rule already present). The classing
           is the reader's; this prints what it reads.

The range is `<markTag>..HEAD` (`markTag` from `.claude/threads.json`, default
`process-review-mark`); `--since REV` replaces the start, `--head REV` the end (the
pre-flight reads the remote's default branch). The header names the range and how many
docs have a window:

  core-diff process-review-mark (2026-09-08, ba7d3a35)..origin/main: 6 docs, 2 with a window

No `invariantDocs` prints one line saying so and exits 0: the command narrates and skips.
Exit 2 when the config is malformed, the mark is missing without --since, a doc is not in
`invariantDocs`, or git fails.
"""
import argparse
import json
import pathlib
import subprocess
import sys

DEFAULT_MARK = "process-review-mark"


def refuse(msg):
    print(f"core-diff: {msg}", file=sys.stderr)
    sys.exit(2)


def git(args, cwd, ok=(0,)):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if r.returncode not in ok:
        refuse(f"git {' '.join(args[:2])} failed: {r.stderr.strip()}")
    return r.stdout


def config(root):
    cfg = root / ".claude" / "threads.json"
    if not cfg.is_file():
        return {}
    try:
        return json.loads(cfg.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        refuse(f"{cfg}: malformed ({e})")


def words_at(root, rev, path):
    """Whitespace-split word count of `path` at `rev`, or None when absent there."""
    r = subprocess.run(["git", "show", f"{rev}:{path}"], cwd=root,
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None
    return len(r.stdout.split())


def changed_words(diff):
    added = removed = 0
    for line in diff.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            added += len(line[1:].split())
        elif line.startswith("-"):
            removed += len(line[1:].split())
    return added, removed


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", nargs="?", default="summary", choices=["summary", "diff"])
    ap.add_argument("doc", nargs="?", default=None, help="the doc, for `diff`")
    ap.add_argument("--since", default=None, metavar="REV", help="range start (default: the mark)")
    ap.add_argument("--head", default="HEAD", metavar="REV", help="range end (default: HEAD)")
    ap.add_argument("--root", default=None, help="repo root (default: git top level)")
    a = ap.parse_args()

    root = pathlib.Path(a.root or git(["rev-parse", "--show-toplevel"], None).strip()).resolve()
    cfg = config(root)
    docs = cfg.get("invariantDocs") or []
    if not isinstance(docs, list) or not all(isinstance(d, str) for d in docs):
        refuse(".claude/threads.json: invariantDocs must be a list of paths")
    if not docs:
        print("core-diff: no invariantDocs configured — nothing to read as churn")
        return
    since = a.since or cfg.get("markTag") or DEFAULT_MARK
    if subprocess.run(["git", "rev-parse", "--verify", "-q", f"{since}^{{commit}}"],
                      cwd=root, capture_output=True).returncode != 0:
        refuse(f"no such rev: {since}" + ("" if a.since else " (the mark; pass --since REV)"))
    if a.mode == "diff":
        if not a.doc:
            refuse("diff needs the doc's path")
        if a.doc not in docs:
            refuse(f"{a.doc} is not in invariantDocs")
        sys.stdout.write(git(["diff", f"{since}..{a.head}", "--", a.doc], root))
        return

    date, short = git(["log", "-1", "--format=%cs %h", since], root).split()
    rows, windowed = [], 0
    for d in docs:
        diff = git(["diff", f"{since}..{a.head}", "--", d], root)
        added, removed = changed_words(diff)
        commits = git(["rev-list", "--count", f"{since}..{a.head}", "--", d], root).strip()
        before, after = words_at(root, since, d), words_at(root, a.head, d)
        if diff.strip():
            windowed += 1
        rows.append(f"{d}\t{'-' if before is None else before}\t{'-' if after is None else after}"
                    f"\t+{added} -{removed}\t{commits}")
    print(f"core-diff {since} ({date}, {short})..{a.head}: {len(docs)} docs, "
          f"{windowed} with a window")
    print("\n".join(rows))


if __name__ == "__main__":
    main()
