#!/usr/bin/env python3
"""retro-log — the retro log as an append-only stream, read through a view.

  retro-log.py view [--keys] [--key KEY]... [--held] [--recurred] [--reached] [--live]
                    [--since DATE|REV] [--docs] [--chain [--prs]] [--arc NAME] [--arcs]
                    [--log PATH] [--root DIR]
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
      Caught: <gate> — <where the rule is>        continuation the view reads: a gate
                                                  caught this occurrence before it
                                                  reached implementation, with its rule
                                                  already present at the named place.
                                                  Retro writes it; `--reached` drops such
                                                  occurrences from the recurrence test
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
    ARC <name> [<date>] — <one line>              annotation: the key rides a named
                                                  trajectory. <name> is a slug; the date
                                                  is when the key entered the arc, written
                                                  when the key's own dates cannot say (a
                                                  compacted closed key carries none).
                                                  Changes neither state nor count;
                                                  compaction keeps it, before or after a
                                                  closing status, so the arc outlives
                                                  its keys. Only ARC takes a date after
                                                  its ref

Entries sit under a `## Entries` heading; nothing follows them. The header above it is
free prose that points here (`--help` prints this) and never copies the grammar: a copy
is a second source nothing refreshes, since `compact` keeps the header verbatim. The
log's path is `retroLogPath` in `.claude/threads.json` (default
`.claude/threads-retro-log.md`).

A key's state is its last block in stream order, annotation blocks skipped: an
occurrence, or a REOPENED, FILED, or HELD status, is live; LANDED, RETIRED, UPSTREAM,
NOTED is closed. An occurrence appended after a closing status therefore reopens the
key by itself — the rule landed and the shape came back — and the view says so. The
view lists HELD keys first, each with the date it was held and its age in days.
Compaction keeps every block of a live key, merging only runs of occurrence blocks
under one key line; a status or annotation block keeps its own key line, since a
status inside an occurrence entry is invisible to the grammar. A closed key keeps its
closing status line and any annotation after it. Compacting a canonical log changes
nothing. A key's occurrence count is its dated occurrence lines across every block
that carries the key; an annotation never counts. A live key that recurred after a closing
status shows that status line on its row — `recurred after LANDED <sha> — <where>` — since
it is the landed rule the new occurrence came back past. `view` reads a stream that breaks
the grammar, naming each violation on stderr and reading the offending line as plain
detail; `compact` refuses on one (exit 2), because a rewrite of a stream it cannot
read loses lines. The grammar is the contract; the guards `retro-log` check is its
gate.

The view's filters are the reads the review makes, so a large log is never read
whole: `--held` (the last run's unanswered proposals), `--recurred` (two or more
occurrences, or an occurrence after a closing status — the shape came back with its
rule present, which ranks with the repeats), `--reached` (the ranking read: `--recurred`
counted over the occurrences no gate caught, so a shape a check keeps catching with its
rule present is counted and never ranked — plus any key with a `Caught:` occurrence and
one without, which reached past the gate that had caught it and ranks regardless of
count; the key line says `escaped <gate>`), `--since DATE` (keys with an occurrence,
status, or annotation dated on or after DATE), `--since REV` (keys with a detail line the
log at REV did not hold — what was appended after that commit, to the commit and not to
the day; compaction and re-keying move no line into it: the read for "since the mark"),
`--live` (no closed section). Filters compose; the summary line counts the whole log and names how many keys the filter
shows. Without `--keys` a filtered view carries each shown key's detail, so the
recurred set's bodies are one read; `--key` repeats for a chosen set. `--docs` prints,
instead of the keys, the files the shown keys name in their detail — a `Placement:`, a
`LANDED … — <where>`, a `FILED <stub>` — as `<keys naming it>\t<path>`, most first:
the docs a run should read because its own findings point there, derived from the
filtered view rather than configured. `--chain` prints, instead of the keys, each shown
key's chain: its occurrences and the organic marker commits (`marker-stream.py`'s
classes) that touched a file the key is placed at — a path after `Placement:`, or one its
status lines name — since its first occurrence, in time order on one clock, author time:
an occurrence's is its capture, the commit `git blame -M` names for its line, which
survives compaction and re-keying, and a line not yet committed is dated by its own date
at the start of the day and reads `uncommitted`. Each marker line carries the placement
file's `+added -removed` and the commit's file count; a marker wider than 30 files reads
`broad` — a relink touches every chain — and is kept out of the reading below. Then one
line per key, `<n> occurrences in <b> bursts` — consecutive occurrences within 24 hours
with no marker between are one burst — plus the markers that touched the placement after
the last occurrence and those it occurred again after, or that nothing touched it, and
the broad ones. `--prs` adds the open PRs (`gh pr list`) touching the placement, `in
flight`; when `gh` cannot say, the header says why and the chain is read without them. A
compacted closed key has no occurrence left to order. A file is not a fix: the chain is
what the review reads before ruling a key burst, patched, or unpatched, never the
ruling. It closes with every organic marker since the mark, one line each and
tab-separated: the shown chains it is in, the live keys placed at a file it touched with
a first occurrence on or before it, then `<time>  <sha>  <subject>` — fewest first, and
under a marker in no shown chain its keys named when there are three or fewer. A marker
at zero and zero answers no key, so its recurrence is uncountable. `--arc NAME` prints, instead of the view, every
key carrying `ARC NAME` — its state and count, then its blocks as the stream holds
them, occurrences dated and statuses one line — ordered by the date each key entered
the arc: the ARC line's own date, else the key's first occurrence; a key with neither
comes last in stream order and the header counts those. Stream order alone is file
order, which compaction and re-keying have already moved relative to time. That
output is the trajectory (attempted, landed, recurred, retired, each dated), derived
and never edited, so a ledger watch on a trajectory cites `view --arc NAME` as its
re-derive command; the review attaches `ARC` to the keys an arc rides with and
retires the token when two windows of reading it changed no ruling. `--arcs` lists
every arc in the log with its key count and live/closed split — the write-side aid,
so attaching a key needs no sweep of the whole log. The arc's own landings are
commits, not keys; they carry an `Arc: NAME` trailer and `marker-stream.py list --arc
NAME` joins them.
"""
import argparse
import datetime
import importlib.util
import json
import pathlib
import re
import subprocess
import sys

KEY = re.compile(r"^([a-z][a-z0-9]*(?:-[a-z0-9]+)*/[a-z0-9]+(?:-[a-z0-9]+)*)( \(uncold\))?$")
OCCURRENCE = re.compile(r"^  (\d{4}-\d{2}-\d{2}) \| ([^|]+?) \|\s*(.*)$")
TOKENS = ("LANDED", "RETIRED", "UPSTREAM", "REOPENED", "FILED", "NOTED", "HELD", "ADJUDICATED",
          "ARC")
STATUS = re.compile(r"^  (" + "|".join(TOKENS) + r") (\S+(?: \+ \S+)*)(?: (\d{4}-\d{2}-\d{2}))?"
                    r"(?:\s+[—-]+\s+(.*))?$")
STATUS_LIKE = re.compile(r"^  ([A-Z][A-Z -]{2,})\b")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DETAIL = re.compile(r"^  ")
CAUGHT = re.compile(r"^\s{2,}Caught: (\S.*?)(?:\s+[—-]+\s.*)?$")
HEADING = re.compile(r"^## ")
PATH = re.compile(r"(?<![\w./-])((?:[\w.-]+/)*[\w-][\w.-]*\.(?:md|json|py|sh|ya?ml|toml|txt))"
                  r"(?![\w/])")
CLOSED = {"LANDED", "RETIRED", "UPSTREAM", "NOTED"}
ANNOTATIONS = {"ADJUDICATED", "ARC"}
SLUG = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
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
        self.nums = []           # their 1-based line numbers in the file

    @property
    def status(self):
        m = STATUS.match(self.lines[0]) if self.lines else None
        return m.group(1) if m else None

    @property
    def ref(self):
        m = STATUS.match(self.lines[0]) if self.lines else None
        return m.group(2) if m else None

    @property
    def arc(self):
        return self.ref if self.status == "ARC" else None

    @property
    def arc_date(self):
        m = STATUS.match(self.lines[0]) if self.lines else None
        return m.group(3) if m and m.group(1) == "ARC" else None

    @property
    def dates(self):
        return [OCCURRENCE.match(l).group(1) for l in self.lines if OCCURRENCE.match(l)]

    @property
    def occurrences(self):
        """(date, gate-or-None) per dated line; a `Caught:` continuation binds to the
        dated line above it."""
        out = []
        for l in self.lines:
            m = OCCURRENCE.match(l)
            if m:
                out.append([m.group(1), None])
                continue
            c = CAUGHT.match(l)
            if c and out:
                out[-1][1] = c.group(1).strip()
        return [tuple(o) for o in out]

    @property
    def touched(self):
        """Every date this block carries: occurrence dates, or a date-shaped ref."""
        if self.status:
            if self.arc_date:
                return [self.arc_date]
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
                cur.nums.append(n)
            continue
        if cur is None:
            violations.append(f"line {n}: detail line with no key above it")
            continue
        if not cur.lines:
            if STATUS.match(line):
                sm = STATUS.match(line)
                if sm.group(1) == "ARC" and not SLUG.match(sm.group(2)):
                    violations.append(f"line {n}: an arc name is a slug, not \"{sm.group(2)}\"")
                if sm.group(3) and sm.group(1) != "ARC":
                    violations.append(f"line {n}: only ARC carries a date after its ref")
            elif OCCURRENCE.match(line):
                pass
            elif STATUS_LIKE.match(line):
                tok = STATUS_LIKE.match(line).group(1).split()[0]
                if tok == "ARC":
                    violations.append(f"line {n}: an arc name is a slug: \"ARC <name> — <text>\"")
                    cur.lines.append(line)
                    cur.nums.append(n)
                    continue
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
        cur.nums.append(n)
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
    return [b for b in blocks_for_key if b.status not in ANNOTATIONS]


def state(blocks_for_key):
    """The last deciding block: its status, or None for an occurrence."""
    bs = deciding(blocks_for_key)
    return bs[-1].status if bs else None


def recurred_after(blocks_for_key, uncaught=False):
    """The closing status an occurrence came after, or None. With `uncaught`, only an
    occurrence no gate caught reopens."""
    closed = None
    for b in deciding(blocks_for_key):
        if b.status in CLOSED:
            closed = b.status
        elif not b.status and closed:
            if not uncaught or any(g is None for _, g in b.occurrences):
                return closed
    return None


def reopened_by(blocks_for_key):
    """The closing status block an occurrence came after, or None: the landed rule a
    reopened key's line must show, since its row sits in Live and carries no status."""
    closed = None
    for b in deciding(blocks_for_key):
        if b.status in CLOSED:
            closed = b
        elif not b.status and closed:
            return closed
    return None


def caught_split(blocks_for_key):
    """(uncaught dates, caught (date, gate)) across the key's occurrence blocks."""
    free, caught = [], []
    for b in blocks_for_key:
        for d, g in b.occurrences:
            (caught if g else free).append((d, g) if g else d)
    return sorted(free), caught


def reached(blocks_for_key):
    """Under --reached: the key ranks when its uncaught occurrences recur, an uncaught
    one follows a closing status, or an uncaught one follows a caught one in the stream
    (it escaped the gate). Returns the escaped gate, True, or False."""
    gate = None
    for b in blocks_for_key:
        for _, g in b.occurrences:
            if g:
                gate = g
            elif gate:
                return gate
    free, _ = caught_split(blocks_for_key)
    if len(free) >= 2 or recurred_after(blocks_for_key, uncaught=True):
        return True
    return False


def one_line(block):
    """A status block reduced to one line: joined, cut at the first sentence end."""
    text = " ".join(l.strip() for l in block.lines)
    m = STATUS.match("  " + text)
    if not m:
        return "  " + text
    tail = m.group(4) or ""
    cut = tail.find(". ")
    if cut != -1:
        tail = tail[:cut + 1]
    return (f"  {m.group(1)} {m.group(2)}" + (f" {m.group(3)}" if m.group(3) else "")
            + (f" — {tail}" if tail else ""))


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


BURST = datetime.timedelta(hours=24)
BROAD = 30      # files: a commit wider than this touched the placement as one of many
FEW = 3
BLAME_HEAD = re.compile(r"^([0-9a-f]{40}) \d+ (\d+)")


def marker_stream():
    path = pathlib.Path(__file__).with_name("marker-stream.py")
    spec = importlib.util.spec_from_file_location("marker_stream", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def capture_times(root, log):
    """{line number: (short sha, aware datetime)}: the commit that wrote each committed
    line and its author time, by `git blame -M`; a line not yet committed is absent."""
    r = subprocess.run(["git", "blame", "-M", "--line-porcelain", "--", str(log.relative_to(root))],
                       cwd=root, capture_output=True, text=True)
    out, cur = {}, None
    if r.returncode != 0:
        return out
    for line in r.stdout.splitlines():
        m = BLAME_HEAD.match(line)
        if m:
            cur = {"sha": m.group(1), "n": int(m.group(2))}
        elif cur is not None and line.startswith("author-time "):
            cur["t"] = int(line.split()[1])
        elif cur is not None and line.startswith("author-tz "):
            tz = line.split()[1]
            off = datetime.timedelta(hours=int(tz[1:3]), minutes=int(tz[3:5]))
            cur["tz"] = datetime.timezone(-off if tz.startswith("-") else off)
        elif line.startswith("\t") and cur is not None:
            if set(cur["sha"]) != {"0"} and "t" in cur:
                out[cur["n"]] = (cur["sha"],
                                 datetime.datetime.fromtimestamp(cur["t"], cur.get("tz")))
            cur = None
    full = sorted({sha for sha, _ in out.values()})
    if full:
        r = subprocess.run(["git", "log", "--no-walk=unsorted", "--format=%H %h", *full],
                           cwd=root, capture_output=True, text=True)
        short = dict(l.split() for l in r.stdout.splitlines()) if r.returncode == 0 else {}
        out = {n: (short.get(sha, sha[:8]), t) for n, (sha, t) in out.items()}
    return out


def lines_at(root, log, rev):
    """The stripped detail lines the log held at `rev`: what `--since REV` reads as old.
    Compaction moves lines and re-keying edits key lines, neither of which makes a detail
    line new; a log absent at `rev` holds none."""
    if subprocess.run(["git", "rev-parse", "--verify", "-q", rev + "^{commit}"], cwd=root,
                      capture_output=True).returncode != 0:
        refuse([f"--since takes YYYY-MM-DD or a commit, not {rev}"])
    r = subprocess.run(["git", "show", f"{rev}:{log.relative_to(root).as_posix()}"], cwd=root,
                       capture_output=True, text=True)
    if r.returncode != 0:
        return set()
    return {l.strip() for b in parse(r.stdout)[1] for l in b.lines}


def placed_paths(bs):
    """The files a key is placed at: the paths after `Placement:` in its occurrences, and
    those its status lines name (a LANDED's where, a FILED stub)."""
    out = set()
    for b in bs:
        texts = b.lines[:1] if b.status in TOKENS and b.status not in ANNOTATIONS else [
            l.split("Placement:", 1)[1] for l in b.lines if "Placement:" in l]
        for t in texts:
            out |= {re.sub(r"^(?:\.\.?/)+", "", p) for p in PATH.findall(t)}
    return out


def touching(files, named):
    """The files a commit touched that a key names: the same path, or one ending in it."""
    return sorted({f for f in files for n in named if f == n or f.endswith("/" + n)})


def stamp(t, exact):
    return t.strftime("%Y-%m-%d %H:%M") if exact else t.strftime("%Y-%m-%d") + " --:--"


def placement_churn(root, sha, files):
    """`<path> +a -b` for each placement file a commit touched."""
    r = subprocess.run(["git", "show", "--no-renames", "--numstat", "--format=", sha, "--", *files],
                       cwd=root, capture_output=True, text=True)
    out = []
    for line in r.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            out.append(f"{parts[2]} +{parts[0]} -{parts[1]}")
    return out or files


def open_prs(root):
    """([(number, title, files)], None) for the open PRs, or ([], why) when gh cannot say."""
    try:
        r = subprocess.run(["gh", "pr", "list", "--state", "open", "--limit", "200",
                            "--json", "number,title,files"], cwd=root, capture_output=True,
                           text=True)
    except OSError:
        return [], "gh not on PATH"
    if r.returncode != 0:
        return [], (r.stderr.strip().splitlines() or ["gh failed"])[0]
    try:
        return [(p["number"], p["title"], [f["path"] for f in p.get("files") or []])
                for p in json.loads(r.stdout or "[]")], None
    except (ValueError, KeyError, TypeError) as e:
        return [], f"gh output unreadable ({e})"


def render_chain(shown, blocks, root, log, prs=False):
    """Each shown key's occurrences and the organic markers touching a file it is placed at
    since its first occurrence, in time order, with the chain read; then the window's
    organic markers, each with the shown chains it appears in and the live keys placed at a
    file it touched, named when there are few enough to check by hand."""
    ms = marker_stream()
    cfg, marker, mark, bookkeeping = ms.stream_config(root)
    times = capture_times(root, log)
    occs = {}
    for key, bs, st, dates in shown:
        rows = []
        for b in bs:
            if b.status:
                continue
            gate = dict(b.occurrences)
            for line, n in zip(b.lines, b.nums):
                m = OCCURRENCE.match(line)
                if not m:
                    continue
                sha, t = times.get(n, (None, None))
                exact = t is not None
                if not exact:
                    t = datetime.datetime.fromisoformat(m.group(1)).astimezone()
                rows.append((t, exact, sha, m.group(2).strip(), gate.get(m.group(1))))
        occs[key] = sorted(rows, key=lambda r: r[0])
    firsts = [r[0][0] for r in occs.values() if r]
    stream = []
    if firsts:
        since = min(firsts).isoformat()          # a bare date is today's time of day to git
        stream = [r for r in ms.classify(ms.commits(root, [f"--since={since}", "HEAD"]),
                                         marker, bookkeeping) if r[0] == "organic"]
    pulls, why = open_prs(root) if prs else ([], None)
    out = [f"chain: author times on both kinds of line; a marker touching more than {BROAD} "
           "files is bracketed as broad — its placement hunk is read before it is ruled a fix"
           + ("" if not prs else f"; open PRs: {len(pulls)}" if why is None
              else f"; open PRs not read ({why})"), ""]
    joined, churn = {}, {}
    for key, bs, st, dates in shown:
        rows, placed = occs[key], placed_paths(bs)
        out.append(f"{key}  ×{len(dates)}" + (f"  {st}" if st else ""))
        if not rows:
            out += ["  chain: no occurrence in the log to order — a compacted closed key; "
                    "rule its chain before its status line is compacted", ""]
            continue
        first, last = rows[0][0], rows[-1][0]
        pats = []
        for cls, sha, short, subject, files, date, time in stream:
            t = datetime.datetime.fromisoformat(time)
            hit = touching(files, placed)
            if hit and t >= first:
                if sha not in churn:
                    churn[sha] = placement_churn(root, sha, hit)
                pats.append((t, short, subject, hit, len(files) > BROAD, len(files), sha))
                joined[short] = joined.get(short, 0) + 1
        events = sorted([(r[0], 0, r) for r in rows] + [(p[0], 1, p) for p in pats],
                        key=lambda e: (e[0], e[1]))
        bursts, prev = 0, None
        for t, kind, e in events:
            if kind == 1:
                _, short, subject, hit, broad, n, sha = e
                if not broad:
                    prev = None
                out.append(f"  {stamp(t, True)}  {'broad  ' if broad else 'touched'}     {short}  "
                           f"{subject}  ({'; '.join(churn[sha])} · {n} file{'s' * (n != 1)})")
                continue
            if prev is None or t - prev > BURST:
                bursts += 1
            prev = t
            _, exact, sha, source, gate = e
            out.append(f"  {stamp(t, exact)}  occurrence  {sha or 'uncommitted'}  {source}"
                       + (f"  caught: {gate}" if gate else ""))
        flight = [(n, title, touching(files, placed)) for n, title, files in pulls
                  if touching(files, placed)]
        for n, title, hit in flight:
            out.append(f"  open PR #{n}  {title}  ({', '.join(hit)})")
        scoped = [p for p in pats if not p[4]]
        after = [p[1] for p in scoped if p[0] > last]
        between = [p[1] for p in scoped if p[0] <= last]
        broad = [p[1] for p in pats if p[4]]
        parts = [f"{len(rows)} occurrence{'s' * (len(rows) != 1)} in {bursts} "
                 f"burst{'s' * (bursts != 1)}"]
        if after:
            parts.append(f"placement touched after the last: {', '.join(after)}")
        if between:
            parts.append(f"occurred again after {', '.join(between)} touched it")
        if not scoped:
            parts.append("placement untouched since the first"
                         + (" but by broad markers" if broad else ""))
        if broad:
            parts.append(f"broad: {', '.join(broad)}")
        if flight:
            parts.append(f"in flight: {', '.join(f'#{n}' for n, _, _ in flight)}")
        out += ["  chain: " + " · ".join(parts), ""]
    r = subprocess.run(["git", "rev-parse", "--verify", "-q", mark + "^{commit}"],
                       cwd=root, capture_output=True, text=True)
    if r.returncode != 0:
        out.append(f"## Organic markers since the mark: no mark {mark}; read skipped")
    else:
        window = [r for r in ms.classify(ms.commits(root, [f"{mark}..HEAD"]), marker, bookkeeping)
                  if r[0] == "organic"]
        live = [(k, bs) for k, bs in keys_in_order(blocks).items() if state(bs) not in CLOSED]
        placed = {}
        for r in window:
            placed[r[2]] = [k for k, bs in live if touching(r[4], placed_paths(bs))
                            and any(d <= r[5] for b in bs for d in b.dates)]
        rows = sorted(window, key=lambda r: (joined.get(r[2], 0), len(placed[r[2]]), r[6]))
        out.append(f"## Organic markers since {mark}: {len(window)} — shown chains · live keys "
                   f"placed at a file it touched; {sum(1 for r in window if not placed[r[2]])} "
                   "touch no live key's placement")
        for cls, sha, short, subject, files, date, time in rows:
            ks = placed[short]
            out.append(f"{joined.get(short, 0)}\t{len(ks)}\t"
                       f"{stamp(datetime.datetime.fromisoformat(time), True)}  {short}  {subject}"
                       + (f"  (broad: {len(files)} files)" if len(files) > BROAD else ""))
            if 0 < len(ks) <= FEW and not joined.get(short):
                out.extend(f"\t\t  {k}" for k in ks)
    return "\n".join(out) + "\n"


def entered(bs, name):
    """The date a key entered an arc: its ARC line's date, else its first occurrence."""
    dated = [b.arc_date for b in bs if b.arc == name and b.arc_date]
    if dated:
        return dated[-1]
    dates = sorted(d for b in bs for d in b.dates)
    return dates[0] if dates else None


def render_arcs(blocks):
    """Every arc in the log: `<slug>\\t<keys> keys · <live> live · <closed> closed`."""
    by_key = keys_in_order(blocks)
    arcs = {}
    for key, bs in by_key.items():
        for name in dict.fromkeys(b.arc for b in bs if b.arc):
            arcs.setdefault(name, []).append(state(bs) in CLOSED)
    out = [f"{len(arcs)} arcs"]
    for name, closed in sorted(arcs.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        n_closed = sum(closed)
        out.append(f"{name}\t{len(closed)} keys · {len(closed) - n_closed} live · {n_closed} closed")
    return "\n".join(out) + "\n"


def render_arc(blocks, name):
    """Every key carrying `ARC name`, by the date it entered the arc, each with its
    blocks as the stream holds them: the trajectory, derived."""
    by_key = keys_in_order(blocks)
    carrying = [k for k, bs in by_key.items() if any(b.arc == name for b in bs)]
    if not carrying:
        refuse([f"no key carries ARC {name}"])
    when = {k: entered(by_key[k], name) for k in carrying}
    order = sorted(carrying, key=lambda k: (when[k] is None, when[k] or "",
                                            min(b.line_no for b in by_key[k])))
    undated = sum(1 for k in carrying if when[k] is None)
    out = [f"arc {name}: {len(order)} keys, by date entered"
           + (f" ({undated} undated, stream order last)" if undated else "")]
    for key in order:
        bs = by_key[key]
        st = state(bs)
        dates = sorted(d for b in bs for d in b.dates)
        span = (f"{dates[0]}..{dates[-1]}" if len(dates) > 1
                else dates[0] if dates
                else f"{when[key]} (entered)" if when[key] else "-")
        marker = f"  {st}" if st else ""
        again = recurred_after(bs)
        if again:
            marker += f"  recurred after {again}"
        out += ["", f"{key}  ×{len(dates)}  {span}{marker}"]
        for b in bs:
            out.extend(b.lines if not b.status else [one_line(b)])
    return "\n".join(out) + "\n"


def arc_tags(bs):
    return "".join(f"  arc:{a}" for a in dict.fromkeys(b.arc for b in bs if b.arc))


def render_view(blocks, keys_only, only=None, held=False, recurred=False,
                live_only=False, since=None, today=None, docs=False, past_gate=False,
                chain=None, since_old=None):
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
    n_gated = sum(1 for r in live + closed if len(r[3]) >= 2 and not reached(r[1]))
    n_closed = {s: sum(1 for r in closed if r[2] == s) for s in sorted(CLOSED)}
    n_held = sum(1 for r in live if r[2] == "HELD")

    def keep(rec):
        key, bs, st, dates = rec
        if held and st != "HELD":
            return False
        if past_gate:
            if not reached(bs):
                return False
        elif recurred and len(dates) < 2 and not recurred_after(bs):
            return False
        if since_old is not None:
            if all(l.strip() in since_old for b in bs for l in b.lines):
                return False
        elif since and not any(d >= since for b in bs for d in b.touched):
            return False
        return True

    recurred = recurred or past_gate
    filtered = held or recurred or since
    shown_live = [r for r in live if keep(r)]
    shown_closed = [] if (live_only or held) else [r for r in closed if keep(r)]
    if docs:
        return render_docs(shown_live + shown_closed)
    if chain:
        return render_chain(shown_live + shown_closed, blocks, *chain)
    out = [f"{len(by_key)} keys · {len(live)} live · {n_held} held · "
           + " · ".join(f"{v} {k.lower()}" for k, v in n_closed.items())
           + f" · {n_recurred} recurred (two or more occurrences"
           + (f", {n_gated} only at a gate" if n_gated else "") + ")"]
    if filtered:
        crit = " ".join(f for f, on in (("--held", held), ("--recurred", recurred),
                                        ("--reached", past_gate),
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
        again = reopened_by(bs)
        if again:
            marker += f"  recurred after {one_line(again).strip()}"
        free, caught = caught_split(bs)
        count = f"×{len(dates)}" + (f" ({len(caught)} caught)" if caught else "")
        esc = reached(bs)
        if isinstance(esc, str):
            marker += f"  escaped {esc}"
        marker += arc_tags(bs)
        out.append(f"{key}{flag}  {count}  {span}{marker}")
        if not keys_only:
            for b in bs:
                out.extend(b.lines if not b.status else [one_line(b)])
    if not (live_only or held):
        out.append("")
        out.append(f"## Closed ({len(shown_closed)}{'' if not filtered else f' of {len(closed)}'})")
        for key, bs, st, dates in shown_closed:
            last = [b for b in deciding(bs) if b.status][-1]
            out.append(f"{key}  ×{len(dates)}  {one_line(last).strip()}{arc_tags(bs)}")
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
            closing = max(i for i, b in enumerate(bs) if b.status not in ANNOTATIONS)
            out += [key_line, one_line(bs[closing])]
            for b in bs[:closing]:       # an arc outlives the key's closing
                if b.status == "ARC":
                    out += [key_line, one_line(b)]
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
    ap.add_argument("--reached", action="store_true",
                    help="view: --recurred over the occurrences no gate caught (a `Caught:` line "
                         "drops one), plus any key that escaped a gate that had caught it")
    ap.add_argument("--live", action="store_true", help="view: live keys only, no closed section")
    ap.add_argument("--docs", action="store_true",
                    help="view: the files the shown keys name, `<keys>\\t<path>`, instead of the keys")
    ap.add_argument("--chain", action="store_true",
                    help="view: each shown key's occurrences and the organic markers touching "
                         "its placement, in time order, with the chain read")
    ap.add_argument("--prs", action="store_true",
                    help="view --chain: also the open PRs touching each key's placement (gh)")
    ap.add_argument("--arc", default=None, metavar="NAME",
                    help="view: every key carrying `ARC NAME`, by date entered, with detail")
    ap.add_argument("--arcs", action="store_true",
                    help="view: every arc in the log with its key count and live/closed split")
    ap.add_argument("--since", default=None, metavar="DATE|REV",
                    help="view: keys with an occurrence, status, or annotation dated on or after "
                         "DATE, or with a detail line the log at REV did not hold")
    ap.add_argument("--today", default=None, help=argparse.SUPPRESS)
    ap.add_argument("--dry-run", action="store_true", help="compact: report, write nothing")
    ap.add_argument("--log", default=None, help="log path, root-relative (default: retroLogPath)")
    ap.add_argument("--root", default=None, help="repo root (default: git top level)")
    args = ap.parse_args()
    if args.today and not DATE.match(args.today):
        refuse([f"--today takes YYYY-MM-DD, not {args.today}"])
    root = pathlib.Path(args.root or git_toplevel()).resolve()
    path = locate(root, args.log)
    if not path.is_file():
        refuse([f"no log at {path}"])
    since_old = None
    if args.since and not DATE.match(args.since):
        since_old = lines_at(root, path, args.since)
    text = path.read_text(encoding="utf-8")
    header, blocks, violations = parse(text)
    if args.mode == "view":
        for v in violations:
            print(f"retro-log: warning: {v}", file=sys.stderr)
        if args.arcs:
            sys.stdout.write(render_arcs(blocks))
            return 0
        if args.arc:
            if not SLUG.match(args.arc):
                refuse([f"--arc takes a slug, not {args.arc}"])
            sys.stdout.write(render_arc(blocks, args.arc))
            return 0
        today = datetime.date.fromisoformat(args.today) if args.today else None
        sys.stdout.write(render_view(blocks, args.keys, args.key, held=args.held,
                                     recurred=args.recurred, live_only=args.live,
                                     since=args.since, today=today, docs=args.docs,
                                     past_gate=args.reached,
                                     chain=(root, path, args.prs) if args.chain else None,
                                     since_old=since_old))
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
