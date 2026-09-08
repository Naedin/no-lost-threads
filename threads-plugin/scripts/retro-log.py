#!/usr/bin/env python3
"""retro-log — the retro log as an append-only stream, read through a view.

  retro-log.py view [--keys | --key KEY] [--log PATH] [--root DIR]
  retro-log.py compact [--dry-run] [--log PATH] [--root DIR]

The log is append-only so that concurrent sessions merge by union; every state
change is therefore an append, never an edit, and the current state of a key is
derived by reading the stream. `view` derives it. `compact` rewrites the stream to
its canonical form and is the review's mutation — one key block per key, closed
keys reduced to their final status line — which is why the review is the only
caller that may run it against the file.

The entry grammar (the guards `retro-log` check enforces the same one):

  <class>/<shape>[ (uncold)]                      key line, column 0
    YYYY-MM-DD | <source> | <text>                occurrence; continuation lines
      ...more text, any indent of two or more     follow it freely
    LANDED <sha> — <where it landed, one line>    status line — exactly one line
    RETIRED <date-or-sha> — <why>                 status tokens: LANDED, RETIRED,
    UPSTREAM <ref> — <where>                      UPSTREAM (closed);
    FILED <ref> — <the stub or plan carrying it>  FILED (live: recurrences count
    REOPENED <date-or-sha> — <why>                against the stub); REOPENED (live)
    NOTED <date> — <what worked and why>          NOTED (closed at write: a record,
                                                  never a recurrence)
    HELD <review-sha> — <the proposal, one line>  HELD (live: the review proposed and
                                                  nobody approved; read first)

Entries sit under a `## Entries` heading; nothing follows them. The log's path is
`retroLogPath` in `.claude/threads.json` (default `.claude/threads-retro-log.md`).

A key's state is its last block in stream order: an occurrence, or a REOPENED,
FILED, or HELD status, is live; LANDED, RETIRED, UPSTREAM, NOTED is closed. An
occurrence appended after a closing status therefore reopens the key by itself — the
rule landed and the shape came back — and the view says so. The view lists HELD keys
first. Compaction keeps every block of a live key, merging only runs of occurrence
blocks under one key line; a status block keeps its own key line, since a status
inside an occurrence entry is invisible to the grammar. Compacting a canonical log
changes nothing. Its occurrence count is its dated lines across every block that
carries the key. `view` reads a stream that breaks the grammar, naming each
violation on stderr and reading the offending line as plain detail; `compact`
refuses on one (exit 2), because a rewrite of a stream it cannot read loses lines.
The grammar is the contract; the guards `retro-log` check is its gate.
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

KEY = re.compile(r"^([a-z][a-z0-9]*(?:-[a-z0-9]+)*/[a-z0-9]+(?:-[a-z0-9]+)*)( \(uncold\))?$")
OCCURRENCE = re.compile(r"^  (\d{4}-\d{2}-\d{2}) \| ([^|]+?) \|\s*(.*)$")
STATUS = re.compile(r"^  (LANDED|RETIRED|UPSTREAM|REOPENED|FILED|NOTED|HELD) (\S+(?: \+ \S+)*)(?:\s+[—-]+\s+(.*))?$")
STATUS_LIKE = re.compile(r"^  ([A-Z][A-Z -]{2,})\b")
DETAIL = re.compile(r"^  ")
HEADING = re.compile(r"^## ")
CLOSED = {"LANDED", "RETIRED", "UPSTREAM", "NOTED"}
ENTRIES = "## Entries"


def refuse(msgs):
    for m in msgs:
        print(f"retro-log: {m}", file=sys.stderr)
    sys.exit(2)


def git_toplevel():
    r = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else "."


def locate(root, explicit):
    if explicit:
        return root / explicit
    cfg = root / ".claude" / "threads.json"
    rel = ".claude/threads-retro-log.md"
    if cfg.is_file():
        try:
            rel = json.loads(cfg.read_text(encoding="utf-8")).get("retroLogPath", rel)
        except (json.JSONDecodeError, AttributeError):
            refuse([f"{cfg}: malformed"])
    return root / rel


class Block:
    """One appended entry: a key line and its detail lines."""

    def __init__(self, key, uncold, line_no):
        self.key, self.uncold, self.line_no = key, uncold, line_no
        self.lines = []          # detail lines, verbatim

    @property
    def status(self):
        m = STATUS.match(self.lines[0]) if self.lines else None
        return m.group(1) if m else None

    @property
    def dates(self):
        return [OCCURRENCE.match(l).group(1) for l in self.lines if OCCURRENCE.match(l)]


def parse(text):
    """(header lines, blocks, violations). Violations are strings naming the line."""
    lines = text.splitlines()
    header, blocks, violations = [], [], []
    start = None
    for i, line in enumerate(lines):
        if line.strip() == ENTRIES:
            start = i + 1
            header = lines[:i]
            break
    if start is None:
        for i, line in enumerate(lines):
            if KEY.match(line):
                start = i
                header = lines[:i]
                break
        else:
            return lines, [], []
    cur = None
    for n, line in enumerate(lines[start:], start + 1):
        if not line.strip():
            continue
        if HEADING.match(line):
            violations.append(f"line {n}: trailing section; the log holds entries only")
            cur = None
            continue
        m = KEY.match(line)
        if m:
            cur = Block(m.group(1), bool(m.group(2)), n)
            blocks.append(cur)
            continue
        if not DETAIL.match(line):
            violations.append(f"line {n}: not a key line, a detail line, or blank")
            if cur is not None:
                cur.lines.append("  " + line)
            continue
        if cur is None:
            violations.append(f"line {n}: detail line with no key above it")
            continue
        if not cur.lines:
            if STATUS.match(line):
                pass
            elif OCCURRENCE.match(line):
                pass
            elif STATUS_LIKE.match(line):
                tok = STATUS_LIKE.match(line).group(1).split()[0]
                if tok in ("LANDED", "RETIRED", "UPSTREAM", "REOPENED", "FILED", "NOTED", "HELD"):
                    violations.append(f"line {n}: status line must be \"{tok} <ref> — <text>\"")
                else:
                    violations.append(
                        f"line {n}: unknown status \"{tok}\"; "
                        "use LANDED, RETIRED, UPSTREAM, FILED, NOTED, HELD, or REOPENED")
            else:
                violations.append(
                    f"line {n}: first detail line must be \"YYYY-MM-DD | source | text\" "
                    "or \"STATUS ref — text\"")
        elif not cur.status and STATUS.match(line):
            violations.append(
                f"line {n}: status line inside an occurrence entry ({cur.key}); a status is its "
                "own entry: the key line again, then the status line")
        cur.lines.append(line)
    for b in blocks:
        if not b.lines:
            violations.append(f"line {b.line_no}: key with no detail ({b.key})")
    return header, blocks, violations


def keys_in_order(blocks):
    out = {}
    for b in blocks:
        out.setdefault(b.key, []).append(b)
    return out


def state(blocks_for_key):
    """The last block decides: its status, or None for an occurrence."""
    return blocks_for_key[-1].status


def recurred_after(blocks_for_key):
    """The closing status an occurrence came after, or None."""
    closed = None
    for b in blocks_for_key:
        if b.status in CLOSED:
            closed = b.status
        elif not b.status and closed:
            return closed
    return None


def one_line(block):
    """A status block reduced to one line: joined, cut at the first sentence end."""
    text = " ".join(l.strip() for l in block.lines)
    m = STATUS.match("  " + text)
    if not m:
        return "  " + text
    tail = m.group(3) or ""
    cut = tail.find(". ")
    if cut != -1:
        tail = tail[:cut + 1]
    return f"  {m.group(1)} {m.group(2)}" + (f" — {tail}" if tail else "")


def render_view(blocks, keys_only, only=None):
    by_key = keys_in_order(blocks)
    if only is not None:
        by_key = {k: v for k, v in by_key.items() if k == only}
        if not by_key:
            refuse([f"no such key: {only}"])
    live, closed = [], []
    for key, bs in by_key.items():
        st = state(bs)
        dates = sorted(d for b in bs for d in b.dates)
        rec = (key, bs, st, dates)
        (closed if st in CLOSED else live).append(rec)
    live.sort(key=lambda r: (r[2] != "HELD", -len(r[3]), r[3][0] if r[3] else ""))
    recurred = sum(1 for r in live + closed if len(r[3]) >= 2)
    n_closed = {s: sum(1 for r in closed if r[2] == s) for s in sorted(CLOSED)}
    out = [f"{len(by_key)} keys · {len(live)} live · "
           + " · ".join(f"{v} {k.lower()}" for k, v in n_closed.items())
           + f" · {recurred} recurred (two or more occurrences)"]
    out.append("")
    out.append(f"## Live ({len(live)}) — HELD first, then most occurrences")
    for key, bs, st, dates in live:
        span = f"{dates[0]}..{dates[-1]}" if len(dates) > 1 else (dates[0] if dates else "-")
        flag = " (uncold)" if any(b.uncold for b in bs) else ""
        marker = f"  {st}" if st in ("REOPENED", "FILED", "HELD") else ""
        again = recurred_after(bs)
        if again:
            marker += f"  recurred after {again}"
        out.append(f"{key}{flag}  ×{len(dates)}  {span}{marker}")
        if not keys_only:
            for b in bs:
                out.extend(b.lines if not b.status else [one_line(b)])
    out.append("")
    out.append(f"## Closed ({len(closed)})")
    for key, bs, st, dates in closed:
        last = [b for b in bs if b.status][-1]
        out.append(f"{key}  ×{len(dates)}  {one_line(last).strip()}")
    return "\n".join(out) + "\n"


def render_compact(header, blocks):
    out = list(header)
    while out and not out[-1].strip():
        out.pop()
    out += ["", ENTRIES, ""]
    for key, bs in keys_in_order(blocks).items():
        st = state(bs)
        uncold = any(b.uncold for b in bs)
        key_line = key + (" (uncold)" if uncold else "")
        if st in CLOSED:
            out += [key_line, one_line(bs[-1])]
            continue
        open_run = False
        for b in bs:
            if b.status:
                out += [key_line, one_line(b)]
                open_run = False
            else:
                if not open_run:
                    out.append(key_line)
                    open_run = True
                out.extend(b.lines)
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["view", "compact"])
    ap.add_argument("--keys", action="store_true", help="view: keys and counts only, no detail")
    ap.add_argument("--key", default=None, help="view: one key, with its detail")
    ap.add_argument("--dry-run", action="store_true", help="compact: report, write nothing")
    ap.add_argument("--log", default=None, help="log path, root-relative (default: retroLogPath)")
    ap.add_argument("--root", default=None, help="repo root (default: git top level)")
    args = ap.parse_args()
    root = pathlib.Path(args.root or git_toplevel()).resolve()
    path = locate(root, args.log)
    if not path.is_file():
        refuse([f"no log at {path}"])
    text = path.read_text(encoding="utf-8")
    header, blocks, violations = parse(text)
    if args.mode == "view":
        for v in violations:
            print(f"retro-log: warning: {v}", file=sys.stderr)
        sys.stdout.write(render_view(blocks, args.keys, args.key))
        return 0
    if violations:
        refuse(violations + [f"{len(violations)} violations; repair by hand, then rerun"])
    new = render_compact(header, blocks)
    before, after = text.count("\n"), new.count("\n")
    by_key = keys_in_order(blocks)
    closed = sum(1 for bs in by_key.values() if state(bs) in CLOSED)
    print(f"retro-log: {len(blocks)} blocks → {len(by_key)} keys ({closed} closed); "
          f"{before} → {after} lines" + (" (dry run)" if args.dry_run else ""), file=sys.stderr)
    if not args.dry_run and new != text:
        path.write_text(new, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
