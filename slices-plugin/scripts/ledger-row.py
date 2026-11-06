#!/usr/bin/env python3
"""
ledger-row.py — write a doc's claim rows by running their commands, so a row's output
line is derived, never authored.

    python3 ledger-row.py add DOC 'CLAIM' 'COMMAND'
    python3 ledger-row.py add DOC 'CLAIM' --unverified 'WHAT WOULD SETTLE IT'
    python3 ledger-row.py rerun DOC
    python3 ledger-row.py show DOC
    python3 ledger-row.py move DOC
    python3 ledger-row.py orphans [--done DIR]...

DOC is a plan, or an inbox stub carrying a frame record (`- framed at …`, slices:draft §1).

Where rows live. A record line (`- drafted at …`, `- gap-checked at …`, `- framed at …`)
stays in the doc; it outlives the plan's readiness and scripts read it. Its rows are dead
once the plan is ready and only this script, the checker, and an adopter's finalize read
them, so with `ledgerDir` set in the repo's `.claude/slices.json` they live in the doc's
rows file, `<ledgerDir>/<doc filename less .md>.rows`, and the doc carries one pointer line,
`- claim rows: `<that path>``, written beside the first record that gets a row. The pointer
is the file's address once written, so a doc renamed later still reaches its rows; the
filename only names a new one. Without `ledgerDir` the rows sit indented under their record
in the doc, as before. Every reader takes both, so a doc drafted before `ledgerDir` was set
still reruns; `move` carries its rows into the file. A row standing in the doc belongs to
the nearest bearing record above it, across other record lines (`changed at`, `go at`, …)
and the pointer; a fence, or any line that is neither, ends the run. A pointer naming a file
that is not there is a refusal for every subcommand that reads rows: the rows were lost or
never staged, and reading on would pass a check that re-ran nothing.

The rows file is a group per record: the record line up to its first ` — `, then
` (<k>)` for the k-th record of the doc with that same head (k > 1), then the record's
rows indented beneath. A group whose record the doc no longer carries is history — a
promoted stub's frame rows under a plan of the same name — and is shown, never rerun.

`add` runs COMMAND with bash in the doc's repo root, derives the output line, and writes
`  - CLAIM — `COMMAND` — OUTPUT` under the doc's newest `drafted at` or `gap-checked at`
record, else under a stub's newest `framed at` record; a row under that record with the
same command is replaced, not duplicated, wherever it sat. Under a `drafted at` record the
record's `<N> sites opened (unverified: <n>)` is recounted from its rows. No such record is
a refusal: the record line is written first. A row `rerun` could not read back as the same
command, or as the same `unverified` row, is a refusal before anything runs: a line break
anywhere in it, an empty command, or a claim whose own ` — ` and code span the reader would
take for the command. A command needing line breaks is written on one line with `$'…\\n…'`.

Every command runs with the doc and its rows file emptied and restored afterward, so a
sweep over a tree holding either never matches the pattern its own row quotes, nor the
doc's prose naming it. Their bytes are held under the repo's git directory first, so a run
killed before restoring is undone by the next run on that doc; a held copy that disagrees
with a doc edited since is a refusal naming both. A second run on a doc another run holds
empty is refused, never left to take the empty doc for the real one.

`rerun` re-runs every command row under the newest `drafted at` record (a stub's newest
`framed at` when it has none) and prints one line per row — `held`; `line-moved`, whose
output differs only in its `<path>:<N>:` line numbers or the order of its lines;
`changed`; each of those two with the recorded and the derived output; `unverified`; or
`unparsed` — then the count line, `rerun: <h> held, <m>
line-moved, <c> changed, <u> unverified, <x> unparsed`, which a record copies as derived. It
exits 1 when any row is line-moved, changed, or unparsed.

`show` prints each record that bears rows (`drafted at`, `gap-checked at`, `framed at`)
with its rows beneath, then any history group; the doc's other records stay in the doc.
`move` carries every row standing in the doc into its rows file, and names each row-shaped
line it left because no bearing record owns it. `orphans` lists, from the repo root, each
pointer naming a missing rows file, each rows file no doc points at or is named for, and
with `--done DIR` each whose doc sits only under DIR — a plan past its readiness, whose rows
are spent; it exits 1 when it lists any.

The output line: up to ten lines of output, each a code span, joined by `; ` (a bare
number is one, `3`); more than ten as `<n> lines, first: <code span>`; none as
`no output`; a non-zero exit appended as `(exit <code>)`, with stderr's first line when
stdout is empty. Each line is cut at 160 characters.
"""
import contextlib, fcntl, functools, hashlib, json, os, re, signal, subprocess, sys, tempfile

TARGET = re.compile(r"^- (drafted at|gap-checked at) ")
FRAME = re.compile(r"^- framed at ")
BEARS = re.compile(r"^- (drafted at|gap-checked at|framed at) ")
COUNT = re.compile(r"— \d+ sites opened \(unverified: \d+\)")
ROW = re.compile(r"^  - (?P<claim>.*?) — (?P<fence>`+) ?(?P<cmd>.+?) ?(?P=fence)(?!`) — (?P<out>.*)$")
UNVERIFIED = re.compile(r"^  - (?P<claim>.*) — unverified: (?P<what>.*)$")
POINTER = re.compile(r"^- claim rows: `(?P<path>[^`]+)`\s*$")
RECORD = re.compile(r"^- [a-z][a-z -]*? at [0-9a-f?]{7,40}, \d{4}-\d{2}-\d{2}\b")
SUMMARY = re.compile(r"^\d+ lines, first: ")
FENCE = re.compile(r"^\s*(```|~~~)")
LINE_NO = re.compile(r"(`+ ?)((?:[^`:\s]+:)?)\d+:")
SPANS = re.compile(r"(`+)(.+?)\1(?!`)")
CUT = 160
ALL = 10


def fail(msg, code=2):
    sys.stderr.write("ledger-row: " + msg + "\n")
    raise SystemExit(code)


def cut(line):
    line = line.strip()
    return line if len(line) <= CUT else line[: CUT - 1] + "…"


def root_of(doc):
    d = os.path.dirname(os.path.abspath(doc))
    r = subprocess.run(["git", "-C", d, "rev-parse", "--show-toplevel"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else os.getcwd()


def ledger_dir(root):
    try:
        with open(os.path.join(root, ".claude", "slices.json"), encoding="utf-8") as f:
            d = json.load(f).get("ledgerDir")
    except (OSError, ValueError, AttributeError):
        return None
    return d.strip("/") if isinstance(d, str) and d.strip("/") else None


def rows_path(doc, root, lines):
    """The doc's rows file, or None when rows sit in the doc. A pointer naming a file that
    is not there is a refusal: the rows were lost or never staged, and reading on would
    pass a check that re-ran nothing."""
    for l in lines:
        m = POINTER.match(l)
        if m:
            path = os.path.join(root, m.group("path"))
            if not os.path.exists(path):
                fail("%s points at %s, which is missing; restore it (`git log --all -- %s`) or drop the pointer line"
                     % (doc, m.group("path"), m.group("path")))
            return path
    d = ledger_dir(root)
    if d is None:
        return None
    stem = os.path.basename(doc)
    stem = stem[:-3] if stem.endswith(".md") else stem
    return os.path.join(root, d, stem + ".rows")


# ---- holding a file empty while a command runs

@functools.lru_cache(maxsize=None)
def held_dir(root):
    r = subprocess.run(["git", "-C", root, "rev-parse", "--absolute-git-dir"],
                       capture_output=True, text=True)
    base = r.stdout.strip() if r.returncode == 0 else tempfile.gettempdir()
    return os.path.join(base, "slices-held")


def held_copy(root, path):
    return os.path.join(held_dir(root), hashlib.sha1(os.path.abspath(path).encode()).hexdigest())


def lock(root, path):
    """An exclusive lock on the doc's held copy, or a refusal while another run holds it."""
    os.makedirs(held_dir(root), exist_ok=True)
    fd = os.open(held_copy(root, path) + ".lock", os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        fail("another ledger-row run is holding %s empty; wait for it to finish" % path)
    return fd


def recover(root, paths):
    """Undo a run killed while it held these files empty."""
    for p in filter(None, paths):
        h = held_copy(root, p)
        if not os.path.exists(h):
            continue
        fd = lock(root, p)
        try:
            with open(h, "rb") as f:
                held = f.read()
            now = open(p, "rb").read() if os.path.exists(p) else b""
            if now and now != held:
                fail("%s changed since a killed run held it; its earlier bytes are at %s — compare, keep one, delete that copy" % (p, h))
            with open(p, "wb") as f:
                f.write(held)
            os.remove(h)
        finally:
            os.close(fd)


@contextlib.contextmanager
def emptied(root, paths):
    paths = [p for p in paths if p and os.path.exists(p)]
    held, fds = {}, []
    try:
        for p in paths:
            fds.append(lock(root, p))
        for p in paths:
            with open(p, "rb") as f:
                held[p] = f.read()
            with open(held_copy(root, p), "wb") as f:
                f.write(held[p])
        for p in paths:
            with open(p, "wb"):
                pass
        yield
    finally:
        for p in held:
            with open(p, "wb") as f:
                f.write(held[p])
            os.remove(held_copy(root, p))
        for fd in fds:
            os.close(fd)


def on_signal(signum, _frame):
    raise SystemExit(128 + signum)


# ---- rows

def derive(cmd, cwd):
    try:
        r = subprocess.run(["bash", "-c", cmd], cwd=cwd, capture_output=True,
                           text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return "no output (timed out after 300s)"
    lines = [l for l in r.stdout.splitlines() if l.strip()]
    if not lines:
        out = "no output"
    elif len(lines) <= ALL:
        out = "; ".join(span(cut(l)) for l in lines)
    else:
        out = "%d lines, first: %s" % (len(lines), span(cut(lines[0])))
    if r.returncode != 0:
        out += " (exit %d)" % r.returncode
        err = [l for l in r.stderr.splitlines() if l.strip()]
        if not lines and err:
            out += ": " + span(cut(err[0]))
    return out


def span(cmd):
    longest = max((len(m) for m in re.findall(r"`+", cmd)), default=0)
    fence = "`" * (longest + 1)
    pad = " " if cmd.startswith("`") or cmd.endswith("`") else ""
    return fence + pad + cmd + pad + fence


def block(lines, kind):
    """(record index, end index) of the newest record matching kind, rows in between."""
    at = max((i for i, l in enumerate(lines) if kind.match(l)), default=None)
    if at is None:
        return None, None
    return at, rows_end(lines, at)


def rows_end(lines, at):
    end = at + 1
    while end < len(lines) and lines[end].startswith("  - "):
        end += 1
    return end


def attributed(lines):
    """{bearing record index: [row line indexes]} for the rows standing in the doc. A row
    belongs to the nearest bearing record above it across other record lines (`changed at`,
    `go at`, …) and the pointer; under a record that bears none, only a line in a row's form
    counts, so a `profiled at` record's own lines stay its. A fence, or any other line,
    ends the run."""
    out, cur, bearing, fenced = {}, None, False, False
    for i, l in enumerate(lines):
        if FENCE.match(l):
            fenced, cur = not fenced, None
        elif fenced:
            continue
        elif BEARS.match(l):
            cur, bearing = i, True
            out[i] = []
        elif RECORD.match(l) or POINTER.match(l):
            bearing = False
        elif l.startswith("  - ") and cur is not None:
            if bearing or ROW.match(l) or UNVERIFIED.match(l):
                out[cur].append(i)
        else:
            cur = None
    return out


def inline_rows(lines, at):
    return [lines[i] for i in attributed(lines).get(at, [])]


def key_of(lines, at):
    """The record's group header in a rows file."""
    head = lines[at].split(" — ", 1)[0].rstrip()
    k = sum(1 for i in attributed(lines[:at + 1]) if lines[i].split(" — ", 1)[0].rstrip() == head)
    return head if k == 1 else "%s (%d)" % (head, k)


def read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().split("\n")
    except OSError as e:
        fail("cannot read %s: %s" % (path, e))


def write(path, lines):
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def groups_of(path):
    """[(header, [rows])] of a rows file, in file order; [] when there is none."""
    if not path or not os.path.exists(path):
        return []
    out = []
    for l in read(path):
        if l.startswith("- "):
            out.append((l, []))
        elif l.startswith("  - ") and out:
            out[-1][1].append(l)
        elif l.strip() and not l.startswith("#"):
            fail("%s: a line neither a group header nor a row: %s" % (path, l))
    return out


def write_groups(path, doc, root, groups):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = ["# claim rows of %s — written by slices' ledger-row.py; `ledger-row.py show <doc>` reads them beside their records"
             % os.path.relpath(os.path.abspath(doc), root)]
    for header, rows in groups:
        lines += [header] + rows
    write(path, lines + [""])


def group_rows(groups, key):
    return next((rows for h, rows in groups if h == key), [])


def same_row(line, cmd, claim):
    m, u = ROW.match(line), UNVERIFIED.match(line)
    return (cmd is not None and m and m.group("cmd") == cmd) or \
           (cmd is None and u and u.group("claim") == claim)


def refusal(claim, cmd, unverified):
    """Why rerun could not read this row back, or None."""
    if any("\n" in t or "\r" in t for t in (claim, cmd or "", unverified or "")):
        return "a row is one line; write a multi-line command with $'…\\n…', or as two rows"
    if unverified is not None:
        row = "  - %s — unverified: %s" % (claim, unverified)
        u = UNVERIFIED.match(row)
        if ROW.match(row) or not u or u.group("claim") != claim:
            return "rerun would read this row as a command; reword the claim without ` — ` before a code span"
        return None
    m = ROW.match("  - %s — %s — x" % (claim, span(cmd)))
    if not m or m.group("cmd") != cmd or m.group("claim") != claim:
        return "rerun would not read this command back; a command is non-empty with no edge spaces, and a claim has no ` — ` before a code span"
    return None


def point(doc_lines, at, root, path):
    """Write the doc's pointer line after the record's rows, once."""
    if any(POINTER.match(l) for l in doc_lines):
        return
    doc_lines.insert(rows_end(doc_lines, at), "- claim rows: `%s`" % os.path.relpath(path, root))


def recount(doc_lines, at, file_rows):
    if not doc_lines[at].startswith("- drafted at "):
        return
    rows = inline_rows(doc_lines, at) + file_rows
    n = sum(1 for l in rows if ROW.match(l) or UNVERIFIED.match(l))
    u = sum(1 for l in rows if UNVERIFIED.match(l))
    if COUNT.search(doc_lines[at]):
        doc_lines[at] = COUNT.sub("— %d sites opened (unverified: %d)" % (n, u), doc_lines[at], count=1)


def add(doc, claim, cmd, unverified):
    why = refusal(claim, cmd, unverified)
    if why:
        fail("%s: %s" % (doc, why))
    root, lines, path = opened(doc)
    at, end = block(lines, TARGET)
    if at is None:
        at, end = block(lines, FRAME)
    if at is None:
        fail("%s has no `drafted at`, `gap-checked at`, or `framed at` record; write the record line first" % doc)
    if unverified is not None:
        row = "  - %s — unverified: %s" % (claim, unverified)
    else:
        with emptied(root, [doc, path]):
            out = derive(cmd, root)
        row = "  - %s — %s — %s" % (claim, span(cmd), out)
    inline = [i for i in attributed(lines).get(at, []) if same_row(lines[i], cmd, claim)]
    if path is None:
        if inline:
            lines[inline[-1]] = row
        else:
            lines.insert(end, row)
        recount(lines, at, [])
        write(doc, lines)
        print(row)
        return
    for i in reversed(inline):
        del lines[i]
    key = key_of(lines, at)
    groups = groups_of(path)
    if not any(h == key for h, _ in groups):
        groups.append((key, []))
    rows = group_rows(groups, key)
    same = [i for i, l in enumerate(rows) if same_row(l, cmd, claim)]
    if same:
        rows[same[-1]] = row
    else:
        rows.append(row)
    write_groups(path, doc, root, groups)
    point(lines, at, root, path)
    recount(lines, at, rows)
    write(doc, lines)
    print(row)


def opened(doc):
    """(root, lines, rows path), after undoing a killed run: the doc first, since its
    pointer names the rows file."""
    root = root_of(doc)
    recover(root, [doc])
    lines = read(doc)
    path = rows_path(doc, root, lines)
    recover(root, [path])
    return root, lines, path


def moved_only(recorded, now):
    """Equal once line numbers are dropped and the output lines are taken in any order. A
    summarized listing shows one line of many, so it is never only moved."""
    if SUMMARY.match(recorded) or SUMMARY.match(now):
        return False
    def norm(out):
        out = LINE_NO.sub(r"\1\2", out)
        return sorted(m.group(2).strip() for m in SPANS.finditer(out)), SPANS.sub("", out)
    return norm(recorded) == norm(now)


def rerun(doc):
    root, lines, path = opened(doc)
    at, end = block(lines, re.compile(r"^- drafted at "))
    if at is None:
        at, end = block(lines, FRAME)
    if at is None:
        fail("%s has no `drafted at` or `framed at` record" % doc)
    rows = [(l, ROW.match(l)) for l in inline_rows(lines, at) + group_rows(groups_of(path), key_of(lines, at))]
    with emptied(root, [doc, path]):
        now = {m.group("cmd"): derive(m.group("cmd"), root) for _, m in rows if m}
    held = moved = changed = unv = other = 0
    for l, m in rows:
        if m:
            rec, cur = m.group("out").strip(), now[m.group("cmd")]
            if cur == rec:
                held += 1
                print("held       %s" % m.group("cmd"))
            elif moved_only(rec, cur):
                moved += 1
                print("line-moved %s\n  recorded: %s\n  now:      %s" % (m.group("cmd"), rec, cur))
            else:
                changed += 1
                print("changed    %s\n  recorded: %s\n  now:      %s" % (m.group("cmd"), rec, cur))
        elif UNVERIFIED.match(l):
            unv += 1
            print("unverified %s" % UNVERIFIED.match(l).group("claim"))
        else:
            other += 1
            print("unparsed   %s" % l.strip())
    print("rerun: %d held, %d line-moved, %d changed, %d unverified, %d unparsed" % (held, moved, changed, unv, other))
    raise SystemExit(1 if moved or changed or other else 0)


def show(doc):
    root, lines, path = opened(doc)
    groups = groups_of(path)
    keys = set()
    for at, l in enumerate(lines):
        if BEARS.match(l):
            key = key_of(lines, at)
            keys.add(key)
            print(l)
            for r in inline_rows(lines, at) + group_rows(groups, key):
                print(r)
    rest = [(h, r) for h, r in groups if h not in keys]
    if rest:
        print("\nhistory — groups in %s whose record this doc no longer carries:" % os.path.relpath(path, root))
        for h, r in rest:
            print(h)
            for x in r:
                print(x)


def move(doc):
    root, lines, path = opened(doc)
    if path is None:
        fail("%s: no `ledgerDir` in .claude/slices.json, so its rows already sit where they belong" % doc)
    groups = groups_of(path)
    moved, first, gone = 0, None, []
    for at, idx in attributed(lines).items():
        if not idx:
            continue
        key = key_of(lines, at)
        if not any(h == key for h, _ in groups):
            groups.append((key, []))
        rows = group_rows(groups, key)
        for r in (lines[i] for i in idx):
            m, u = ROW.match(r), UNVERIFIED.match(r)
            cmd = m.group("cmd") if m else None
            claim = u.group("claim") if u and not m else None
            if (m or u) and any(same_row(x, cmd, claim) for x in rows):
                continue
            rows.append(r)
        gone += idx
        moved += len(idx)
        first = at if first is None else first
    for i in sorted(gone, reverse=True):
        del lines[i]
    if not moved:
        print("no rows stand in %s" % doc)
        return
    groups.sort(key=lambda g: next((i for i, l in enumerate(lines) if BEARS.match(l) and key_of(lines, i) == g[0]), len(lines)))
    write_groups(path, doc, root, groups)
    point(lines, first, root, path)
    write(doc, lines)
    print("%d rows moved to %s" % (moved, os.path.relpath(path, root)))
    fenced = False
    for i, l in enumerate(lines):
        if FENCE.match(l):
            fenced = not fenced
        elif not fenced and (ROW.match(l) or UNVERIFIED.match(l)):
            print("left       line %d: under no record that bears rows: %s" % (i + 1, cut(l)))


def orphans(done):
    root = root_of(os.path.join(os.getcwd(), "x"))
    d = ledger_dir(root)
    if d is None:
        fail("no `ledgerDir` in .claude/slices.json")
    r = subprocess.run(["git", "-C", root, "ls-files", "-co", "--exclude-standard", "*.md"],
                       capture_output=True, text=True)
    docs = [p for p in r.stdout.splitlines() if p]
    pointed, found = {}, 0
    for p in docs:
        try:
            with open(os.path.join(root, p), encoding="utf-8") as f:
                for l in f:
                    m = POINTER.match(l.rstrip("\n"))
                    if m:
                        rel = os.path.normpath(m.group("path"))
                        pointed.setdefault(rel, []).append(p)
                        if not os.path.exists(os.path.join(root, rel)):
                            found += 1
                            print("missing    %s — %s points at it" % (rel, p))
                        break
        except (OSError, UnicodeDecodeError):
            continue
    done = [x.strip("/") + "/" for x in done]
    names = os.listdir(os.path.join(root, d)) if os.path.isdir(os.path.join(root, d)) else []
    for name in sorted(names):
        if not name.endswith(".rows"):
            continue
        rel = os.path.normpath(os.path.join(d, name))
        owners = pointed.get(rel) or [p for p in docs if os.path.basename(p) == name[:-5] + ".md"]
        if not owners:
            found += 1
            print("orphan     %s — no doc points at it or is named for it" % rel)
        elif done and all(any(o.startswith(x) for x in done) for o in owners):
            found += 1
            print("spent      %s — its doc is past ready: %s" % (rel, ", ".join(owners)))
    print("orphans: %d" % found)
    raise SystemExit(1 if found else 0)


def main(argv):
    for s in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(s, on_signal)
    if len(argv) == 2 and argv[0] in ("rerun", "show", "move"):
        return {"rerun": rerun, "show": show, "move": move}[argv[0]](argv[1])
    if len(argv) == 4 and argv[0] == "add":
        return add(argv[1], argv[2], argv[3], None)
    if len(argv) == 5 and argv[0] == "add" and argv[3] == "--unverified":
        return add(argv[1], argv[2], None, argv[4])
    if argv and argv[0] == "orphans" and len(argv) % 2 == 1 and all(a == "--done" for a in argv[1::2]):
        return orphans(argv[2::2])
    fail("usage: ledger-row.py add DOC 'CLAIM' 'COMMAND' | add DOC 'CLAIM' --unverified 'WHAT' | rerun DOC | show DOC | move DOC | orphans [--done DIR]...")


if __name__ == "__main__":
    main(sys.argv[1:])
