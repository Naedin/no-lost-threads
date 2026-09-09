#!/usr/bin/env python3
"""retro-log — the retro log as an append-only stream, read through a view.

  retro-log.py view [--keys] [--key KEY]... [--held] [--recurred] [--live]
                    [--since YYYY-MM-DD] [--log PATH] [--root DIR]
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
    LANDED <sha> — <where it landed, one line>    status line — one physical line,
                                                  however long; a wrapped one reads as
                                                  continuation prose
    RETIRED <date-or-sha> — <why>                 status tokens: LANDED, RETIRED,
    UPSTREAM <ref> — <where>                      UPSTREAM (closed);
    FILED <ref> — <the stub or plan carrying it>  FILED (live: recurrences count
    REOPENED <date-or-sha> — <why>                against the stub); REOPENED (live)
    NOTED <date> — <what worked and why>          NOTED (closed at write: a record,
                                                  never a recurrence)
    HELD <date> — <the proposal, one line>        HELD (live: the review proposed and
                                                  nobody approved; read first). The
                                                  date is the review's; its marker
                                                  commit carries the HELD lines, so a
                                                  sha cannot be the ref
    ADJUDICATED <date> — <the ruling, one line>   annotation: the review's re-rank,
                                                  count-only ruling, or build trigger
                                                  on a key. Changes neither the key's
                                                  state nor its count; the view shows
                                                  it in detail, compaction keeps it

Entries sit under a `## Entries` heading; nothing follows them. The header above it is
free prose that points here (`--help` prints this) and never copies the grammar: a copy
is a second source nothing refreshes, since `compact` keeps the header verbatim. The
log's path is `retroLogPath` in `.claude/threads.json` (default
`.claude/threads-retro-log.md`).

A key's state is its last block in stream order, ADJUDICATED blocks skipped: an
occurrence, or a REOPENED, FILED, or HELD status, is live; LANDED, RETIRED, UPSTREAM,
NOTED is closed. An occurrence appended after a closing status therefore reopens the
key by itself — the rule landed and the shape came back — and the view says so. The
view lists HELD keys first, each with the date it was held and its age in days.
Compaction keeps every block of a live key, merging only runs of occurrence blocks
under one key line; a status or annotation block keeps its own key line, since a
status inside an occurrence entry is invisible to the grammar. A closed key keeps its
closing status line and any annotation after it. Compacting a canonical log changes
nothing. A key's occurrence count is its dated occurrence lines across every block
that carries the key; an annotation never counts. `view` reads a stream that breaks
the grammar, naming each violation on stderr and reading the offending line as plain
detail; `compact` refuses on one (exit 2), because a rewrite of a stream it cannot
read loses lines. The grammar is the contract; the guards `retro-log` check is its
gate.

The view's filters are the reads the review makes, so a large log is never read
whole: `--held` (the last run's unanswered proposals), `--recurred` (two or more
occurrences, or an occurrence after a closing status — the shape came back with its
rule present, which ranks with the repeats), `--since DATE` (keys with an occurrence,
status, or annotation dated on or after DATE), `--live` (no closed section). Filters
compose; the summary line counts the whole log and names how many keys the filter
shows. Without `--keys` a filtered view carries each shown key's detail, so the
recurred set's bodies are one read; `--key` repeats for a chosen set. `--docs` prints,
instead of the keys, the files the shown keys name in their detail — a `Placement:`, a
`LANDED … — <where>`, a `FILED <stub>` — as `<keys naming it>\t<path>`, most first:
the docs a run should read because its own findings point there, derived from the
filtered view rather than configured.
"""
import argparse
import datetime
import json
import pathlib
import re
import subprocess
import sys

KEY = re.compile(r"^([a-z][a-z0-9]*(?:-[a-z0-9]+)*/[a-z0-9]+(?:-[a-z0-9]+)*)( \(uncold\))?$")
OCCURRENCE = re.compile(r"^  (\d{4}-\d{2}-\d{2}) \| ([^|]+?) \|\s*(.*)$")
TOKENS = ("LANDED", "RETIRED", "UPSTREAM", "REOPENED", "FILED", "NOTED", "HELD", "ADJUDICATED")
STATUS = re.compile(r"^  (" + "|".join(TOKENS) + r") (\S+(?: \+ \S+)*)(?:\s+[—-]+\s+(.*))?$")
STATUS_LIKE = re.compile(r"^  ([A-Z][A-Z -]{2,})\b")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DETAIL = re.compile(r"^  ")
HEADING = re.compile(r"^## ")
PATH = re.compile(r"(?<![\w./-])((?:[\w.-]+/)*[\w-][\w.-]*\.(?:md|json|py|sh|ya?ml|toml|txt))"
                  r"(?![\w/])")
CLOSED = {"LANDED", "RETIRED", "UPSTREAM", "NOTED"}
ANNOTATION = "ADJUDICATED"
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
    def ref(self):
        m = STATUS.match(self.lines[0]) if self.lines else None
        return m.group(2) if m else None

    @property
    def dates(self):
        return [OCCURRENCE.match(l).group(1) for l in self.lines if OCCURRENCE.match(l)]

    @property
    def touched(self):
        """Every date this block carries: occurrence dates, or a date-shaped ref."""
        if self.status:
            return [self.ref] if DATE.match(self.ref or "") else []
        return self.dates


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
                if tok in TOKENS:
                    violations.append(f"line {n}: status line must be \"{tok} <ref> — <text>\"")
                else:
                    violations.append(
                        f"line {n}: unknown status \"{tok}\"; use " + ", ".join(TOKENS[:-1])
                        + f", or {TOKENS[-1]}")
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


def deciding(blocks_for_key):
    """The blocks that carry state: everything but annotations."""
    return [b for b in blocks_for_key if b.status != ANNOTATION]


def state(blocks_for_key):
    """The last deciding block: its status, or None for an occurrence."""
    bs = deciding(blocks_for_key)
    return bs[-1].status if bs else None


def recurred_after(blocks_for_key):
    """The closing status an occurrence came after, or None."""
    closed = None
    for b in deciding(blocks_for_key):
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


def held_marker(blocks_for_key, today):
    """`HELD since <date> (<n>d)` when the ref is a date, else `HELD <ref>`."""
    held = [b for b in deciding(blocks_for_key) if b.status == "HELD"][-1]
    ref = held.ref
    if DATE.match(ref):
        try:
            age = (today - datetime.date.fromisoformat(ref)).days
            return f"  HELD since {ref} ({age}d)"
        except ValueError:
            pass
    return f"  HELD {ref}"


def render_docs(shown):
    """The files the shown keys' detail lines name, `<keys naming it>\\t<path>`."""
    by_path = {}
    for key, bs, st, dates in shown:
        for b in bs:
            for l in b.lines:
                for p in set(PATH.findall(l)):
                    p = re.sub(r"^(?:\.\.?/)+", "", p)   # a link relative to the log's dir
                    by_path.setdefault(p, set()).add(key)
    ranked = sorted(by_path.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    return "".join(f"{len(ks)}\t{p}\n" for p, ks in ranked)


def render_view(blocks, keys_only, only=None, held=False, recurred=False,
                live_only=False, since=None, today=None, docs=False):
    today = today or datetime.date.today()
    by_key = keys_in_order(blocks)
    if only:
        missing = [k for k in only if k not in by_key]
        if missing:
            refuse([f"no such key: {k}" for k in missing])
        by_key = {k: v for k, v in by_key.items() if k in only}
    live, closed = [], []
    for key, bs in by_key.items():
        st = state(bs)
        dates = sorted(d for b in bs for d in b.dates)
        rec = (key, bs, st, dates)
        (closed if st in CLOSED else live).append(rec)
    live.sort(key=lambda r: (r[2] != "HELD", -len(r[3]), r[3][0] if r[3] else ""))
    n_recurred = sum(1 for r in live + closed if len(r[3]) >= 2)
    n_closed = {s: sum(1 for r in closed if r[2] == s) for s in sorted(CLOSED)}
    n_held = sum(1 for r in live if r[2] == "HELD")

    def keep(rec):
        key, bs, st, dates = rec
        if held and st != "HELD":
            return False
        if recurred and len(dates) < 2 and not recurred_after(bs):
            return False
        if since and not any(d >= since for b in bs for d in b.touched):
            return False
        return True

    filtered = held or recurred or since
    shown_live = [r for r in live if keep(r)]
    shown_closed = [] if (live_only or held) else [r for r in closed if keep(r)]
    if docs:
        return render_docs(shown_live + shown_closed)
    out = [f"{len(by_key)} keys · {len(live)} live · {n_held} held · "
           + " · ".join(f"{v} {k.lower()}" for k, v in n_closed.items())
           + f" · {n_recurred} recurred (two or more occurrences)"]
    if filtered:
        crit = " ".join(f for f, on in (("--held", held), ("--recurred", recurred),
                                        (f"--since {since}", since)) if on)
        out.append(f"showing {len(shown_live) + len(shown_closed)} of {len(by_key)} keys ({crit})")
    out.append("")
    out.append(f"## Live ({len(shown_live)}{'' if not filtered else f' of {len(live)}'})"
               " — HELD first, then most occurrences")
    for key, bs, st, dates in shown_live:
        span = f"{dates[0]}..{dates[-1]}" if len(dates) > 1 else (dates[0] if dates else "-")
        flag = " (uncold)" if any(b.uncold for b in bs) else ""
        if st == "HELD":
            marker = held_marker(bs, today)
        elif st in ("REOPENED", "FILED"):
            marker = f"  {st}"
        else:
            marker = ""
        again = recurred_after(bs)
        if again:
            marker += f"  recurred after {again}"
        out.append(f"{key}{flag}  ×{len(dates)}  {span}{marker}")
        if not keys_only:
            for b in bs:
                out.extend(b.lines if not b.status else [one_line(b)])
    if not (live_only or held):
        out.append("")
        out.append(f"## Closed ({len(shown_closed)}{'' if not filtered else f' of {len(closed)}'})")
        for key, bs, st, dates in shown_closed:
            last = [b for b in deciding(bs) if b.status][-1]
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
            closing = max(i for i, b in enumerate(bs) if b.status != ANNOTATION)
            out += [key_line, one_line(bs[closing])]
            for b in bs[closing + 1:]:
                out += [key_line, one_line(b)]
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
    ap.add_argument("--key", action="append", default=None, metavar="KEY",
                    help="view: this key with its detail; repeatable")
    ap.add_argument("--held", action="store_true", help="view: HELD keys only, with their age")
    ap.add_argument("--recurred", action="store_true",
                    help="view: keys with two or more occurrences, or one after a closing status")
    ap.add_argument("--live", action="store_true", help="view: live keys only, no closed section")
    ap.add_argument("--docs", action="store_true",
                    help="view: the files the shown keys name, `<keys>\\t<path>`, instead of the keys")
    ap.add_argument("--since", default=None, metavar="YYYY-MM-DD",
                    help="view: keys with an occurrence, status, or annotation dated on or after")
    ap.add_argument("--today", default=None, help=argparse.SUPPRESS)
    ap.add_argument("--dry-run", action="store_true", help="compact: report, write nothing")
    ap.add_argument("--log", default=None, help="log path, root-relative (default: retroLogPath)")
    ap.add_argument("--root", default=None, help="repo root (default: git top level)")
    args = ap.parse_args()
    for flag, val in (("--since", args.since), ("--today", args.today)):
        if val and not DATE.match(val):
            refuse([f"{flag} takes YYYY-MM-DD, not {val}"])
    root = pathlib.Path(args.root or git_toplevel()).resolve()
    path = locate(root, args.log)
    if not path.is_file():
        refuse([f"no log at {path}"])
    text = path.read_text(encoding="utf-8")
    header, blocks, violations = parse(text)
    if args.mode == "view":
        for v in violations:
            print(f"retro-log: warning: {v}", file=sys.stderr)
        today = datetime.date.fromisoformat(args.today) if args.today else None
        sys.stdout.write(render_view(blocks, args.keys, args.key, held=args.held,
                                     recurred=args.recurred, live_only=args.live,
                                     since=args.since, today=today, docs=args.docs))
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
