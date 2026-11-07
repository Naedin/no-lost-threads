#!/usr/bin/env python3
"""core-diff — each direction doc's window, so the review reads its direction as churn and
not only as authority.

  core-diff.py [summary|diff DOC|self] [--since REV] [--head REV] [--days N] [--root DIR]

The review reads `invariantDocs` whole every run and reports which bore on a ruling. A doc
read whole can still grow unread: a slice PR's squash lands a paragraph in it, no marker
names the change, and eleven weeks later the doc is twice its size and bears on nothing.
This script reads each core doc's own window, the range the marker stream reads.

`windowOnlyDocs` is the second list: docs the review watches as churn but never opens
whole — a doc that bears on no ruling until a finding names it, when the review opens
it. Both lists feed the summary; a path in both is a malformed config.

Modes:
  summary  (default) one header line, then one line per doc, `invariantDocs` in order
           and then `windowOnlyDocs` in order:
             <path>\\t<words at since>\\t<words at head>\\t+<added> -<removed>\\t<commits>\\t<read>
           words are whitespace-split; added and removed count the words on the diff's
           `+` and `-` lines; commits touch the doc in the range; read is `whole` for a
           core doc and `window` for a window-only one. A doc absent at the range start
           reads `-` for its words there.
  diff DOC the doc's diff over the range, as `git diff` prints it, for the hunk-by-hunk
           read: each hunk is classed rule (a predicate, a scope boundary, a named
           exception, a decision-relevant why) or prose (narration, a symbol enumeration,
           a restated why, a worked case restating a rule already present, a tool's own
           behavior restated). The classing
           is the reader's; this prints what it reads.
  self     what the review's own landings did to each file over `--days` days (default
           30) back from its newest run: every commit with a `Process-Review: <date>`
           line in its body, grouped by that date — commits no window reads, since the
           mark moves past them in the run that lands them. A window in days, not runs,
           because a repo reviewed daily spends five runs in a week. One header line, then
           one line per file they touched, most net words first, `retroLogPath`,
           `ledgerPath`, and `capabilityEvidencePath` left out:
             <path>\t<words at head>\t+<added> -<removed>\t<g> grew · <t> trimmed of <n> runs
           A file the review grew in two or more runs and trimmed in none is a growth
           finding against the review itself. `--since` is not read.

The range is `<markTag>..HEAD` (`markTag` from `.claude/threads.json`, default
`process-review-mark`); `--since REV` replaces the start, `--head REV` the end (the
pre-flight reads the remote's default branch). The header names the range and how many
docs have a window:

  core-diff process-review-mark (2026-09-08, ba7d3a35)..origin/main: 6 docs (4 whole, 2 window), 2 with a window

Neither list configured prints one line saying so and exits 0: the command narrates and
skips. Exit 2 when the config is malformed, the mark is missing without --since, the start
is a tag the remote holds elsewhere (`marker-stream.py` names the fetch), a doc is in
neither list, or git fails.
"""
import argparse
import datetime
import importlib.util
import json
import pathlib
import subprocess
import sys

DEFAULT_MARK = "process-review-mark"


def marker_stream():
    path = pathlib.Path(__file__).with_name("marker-stream.py")
    spec = importlib.util.spec_from_file_location("marker_stream", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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


def own_growth(root, cfg, head, days):
    if days < 1:
        refuse("--days must be 1 or more")
    ms = marker_stream()
    skip = {cfg.get("retroLogPath") or ".claude/threads-retro-log.md",
            cfg.get("ledgerPath") or ".claude/threads-review-ledger.md",
            cfg.get("capabilityEvidencePath")}
    by_run = {}
    for sha, _, _, trailer, files, *_ in ms.commits(root, [head]):
        if trailer:
            by_run.setdefault(trailer.splitlines()[0].strip(), []).append(sha)
    if not by_run:
        print(f"core-diff self: no commit carries {ms.TRAILER}: — the review has landed nothing")
        return
    newest = max(by_run)
    try:
        start = (datetime.date.fromisoformat(newest[:10]) - datetime.timedelta(days=days)).isoformat()
    except ValueError:
        refuse(f"{ms.TRAILER}: {newest!r} is not a date")
    dates = sorted((d for d in by_run if d[:10] >= start), reverse=True)
    per = {}
    for d in dates:
        for sha in by_run[d]:
            out = git(["show", "--format=", "--no-renames", sha], root)
            for chunk in out.split("\ndiff --git ")[0:]:
                m = chunk.split("\n", 1)[0]
                path = m.rsplit(" b/", 1)[-1] if " b/" in m else None
                if not path or path in skip:
                    continue
                added, removed = changed_words(chunk)
                runs_of = per.setdefault(path, {})
                ra, rr = runs_of.get(d, (0, 0))
                runs_of[d] = (ra + added, rr + removed)
    rows = []
    for path, rs in per.items():
        added = sum(x for x, _ in rs.values())
        removed = sum(y for _, y in rs.values())
        grew = sum(1 for x, y in rs.values() if x > y)
        trimmed = sum(1 for x, y in rs.values() if x < y)
        now = words_at(root, head, path)
        rows.append((added - removed, f"{path}\t{'-' if now is None else now}\t+{added} -{removed}"
                                      f"\t{grew} grew · {trimmed} trimmed of {len(rs)} runs"))
    print(f"core-diff self: the review's own landings over {days} days, {len(dates)} runs "
          f"({dates[-1]}..{dates[0]}), {len(rows)} files")
    print("\n".join(r for _, r in sorted(rows, key=lambda x: (-x[0], x[1]))))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", nargs="?", default="summary", choices=["summary", "diff", "self"])
    ap.add_argument("doc", nargs="?", default=None, help="the doc, for `diff`")
    ap.add_argument("--since", default=None, metavar="REV", help="range start (default: the mark)")
    ap.add_argument("--head", default="HEAD", metavar="REV", help="range end (default: HEAD)")
    ap.add_argument("--days", type=int, default=30, metavar="N", help="self: N days back from the newest review run")
    ap.add_argument("--root", default=None, help="repo root (default: git top level)")
    a = ap.parse_args()

    root = pathlib.Path(a.root or git(["rev-parse", "--show-toplevel"], None).strip()).resolve()
    cfg = config(root)
    lists = {}
    for field in ("invariantDocs", "windowOnlyDocs"):
        val = cfg.get(field) or []
        if not isinstance(val, list) or not all(isinstance(d, str) for d in val):
            refuse(f".claude/threads.json: {field} must be a list of paths")
        lists[field] = val
    both = [d for d in lists["windowOnlyDocs"] if d in lists["invariantDocs"]]
    if both:
        refuse(".claude/threads.json: in both invariantDocs and windowOnlyDocs: "
               + ", ".join(both) + " (a doc is read whole or as its window, not both)")
    core, window = lists["invariantDocs"], lists["windowOnlyDocs"]
    if a.mode == "self":
        return own_growth(root, cfg, a.head, a.days)
    docs = core + window
    if not docs:
        print("core-diff: no invariantDocs or windowOnlyDocs configured — nothing to read as churn")
        return
    since = a.since or cfg.get("markTag") or DEFAULT_MARK
    if subprocess.run(["git", "rev-parse", "--verify", "-q", f"{since}^{{commit}}"],
                      cwd=root, capture_output=True).returncode != 0:
        refuse(f"no such rev: {since}" + ("" if a.since else " (the mark; pass --since REV)"))
    stale = marker_stream().stale_tag(root, since)
    if stale:
        refuse(stale)
    if a.mode == "diff":
        if not a.doc:
            refuse("diff needs the doc's path")
        if a.doc not in docs:
            refuse(f"{a.doc} is not in invariantDocs or windowOnlyDocs")
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
                    f"\t+{added} -{removed}\t{commits}\t{'whole' if d in core else 'window'}")
    print(f"core-diff {since} ({date}, {short})..{a.head}: {len(docs)} docs "
          f"({len(core)} whole, {len(window)} window), {windowed} with a window")
    print("\n".join(rows))


if __name__ == "__main__":
    main()
