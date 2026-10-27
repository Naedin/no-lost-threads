#!/usr/bin/env python3
"""
ledger-row.py — write a plan's claim rows by running their commands, so a row's output
line is derived, never authored.

    python3 ledger-row.py add PLAN 'CLAIM' 'COMMAND'
    python3 ledger-row.py add PLAN 'CLAIM' --unverified 'WHAT WOULD SETTLE IT'
    python3 ledger-row.py rerun PLAN

`add` runs COMMAND with bash in the plan's repo root, derives the output line, and writes
`  - CLAIM — `COMMAND` — OUTPUT` under the plan's newest `drafted at` or `gap-checked at`
record; a row under that record with the same command is replaced, not duplicated. Under
a `drafted at` record the record's `<N> sites opened (unverified: <n>)` is recounted from
its rows. No such record is a refusal: the record line is written first.

Every command runs with the plan file itself emptied and restored afterward, so a sweep
over a tree holding the plan never matches the plan's own text — its ledger row quotes
the pattern it searches for.

`rerun` re-runs every command row under the newest `drafted at` record and prints one
line per row — `held`, `differs` with the recorded and the derived output, or
`unverified` — then a count line. It exits 1 when any row differs.

The output line: up to ten lines of output, each a code span, joined by `; ` (a bare
number is one, `3`); more than ten as `<n> lines, first: <code span>`; none as
`no output`; a non-zero exit appended as `(exit <code>)`, with stderr's first line when
stdout is empty. Each line is cut at 160 characters.
"""
import contextlib, os, re, subprocess, sys

RECORD = re.compile(r"^- (drafted at|gap-checked at|reframed at|check held at|go at) ")
TARGET = re.compile(r"^- (drafted at|gap-checked at) ")
COUNT = re.compile(r"— \d+ sites opened \(unverified: \d+\)")
ROW = re.compile(r"^  - (?P<claim>.*?) — (?P<fence>`+) ?(?P<cmd>.+?) ?(?P=fence)(?!`) — (?P<out>.*)$")
UNVERIFIED = re.compile(r"^  - (?P<claim>.*) — unverified: (?P<what>.*)$")
CUT = 160
ALL = 10


def fail(msg, code=2):
    sys.stderr.write("ledger-row: " + msg + "\n")
    raise SystemExit(code)


def cut(line):
    line = line.strip()
    return line if len(line) <= CUT else line[: CUT - 1] + "…"


def root_of(plan):
    d = os.path.dirname(os.path.abspath(plan))
    r = subprocess.run(["git", "-C", d, "rev-parse", "--show-toplevel"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else os.getcwd()


@contextlib.contextmanager
def plan_emptied(plan):
    with open(plan, "rb") as f:
        held = f.read()
    try:
        with open(plan, "wb"):
            pass
        yield
    finally:
        with open(plan, "wb") as f:
            f.write(held)


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
    end = at + 1
    while end < len(lines) and lines[end].startswith("  - "):
        end += 1
    return at, end


def read(plan):
    try:
        with open(plan, encoding="utf-8") as f:
            return f.read().split("\n")
    except OSError as e:
        fail("cannot read %s: %s" % (plan, e))


def add(plan, claim, cmd, unverified):
    lines = read(plan)
    at, end = block(lines, TARGET)
    if at is None:
        fail("%s has no `drafted at` or `gap-checked at` record; write the record line first" % plan)
    if unverified is not None:
        row = "  - %s — unverified: %s" % (claim, unverified)
    else:
        with plan_emptied(plan):
            out = derive(cmd, root_of(plan))
        row = "  - %s — %s — %s" % (claim, span(cmd), out)
    same = None
    for i in range(at + 1, end):
        m, u = ROW.match(lines[i]), UNVERIFIED.match(lines[i])
        if (cmd is not None and m and m.group("cmd") == cmd) or \
           (cmd is None and u and u.group("claim") == claim):
            same = i
    if same is None:
        lines.insert(end, row)
        end += 1
    else:
        lines[same] = row
    if lines[at].startswith("- drafted at "):
        rows = lines[at + 1:end]
        n = sum(1 for l in rows if ROW.match(l) or UNVERIFIED.match(l))
        u = sum(1 for l in rows if UNVERIFIED.match(l))
        new = "— %d sites opened (unverified: %d)" % (n, u)
        if COUNT.search(lines[at]):
            lines[at] = COUNT.sub(new, lines[at], count=1)
    with open(plan, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(row)


def rerun(plan):
    lines = read(plan)
    at, end = block(lines, re.compile(r"^- drafted at "))
    if at is None:
        fail("%s has no `drafted at` record" % plan)
    cwd = root_of(plan)
    rows = [(l, ROW.match(l)) for l in lines[at + 1:end]]
    with plan_emptied(plan):
        now = {m.group("cmd"): derive(m.group("cmd"), cwd) for _, m in rows if m}
    held = differs = unv = other = 0
    for l, m in rows:
        if m:
            if now[m.group("cmd")] == m.group("out").strip():
                held += 1
                print("held       %s" % m.group("cmd"))
            else:
                differs += 1
                print("differs    %s\n  recorded: %s\n  now:      %s" % (m.group("cmd"), m.group("out").strip(), now[m.group("cmd")]))
        elif UNVERIFIED.match(l):
            unv += 1
            print("unverified %s" % UNVERIFIED.match(l).group("claim"))
        else:
            other += 1
            print("unparsed   %s" % l.strip())
    print("rows: %d held, %d differ, %d unverified, %d unparsed" % (held, differs, unv, other))
    raise SystemExit(1 if differs or other else 0)


def main(argv):
    if len(argv) >= 2 and argv[0] == "rerun" and len(argv) == 2:
        return rerun(argv[1])
    if len(argv) == 4 and argv[0] == "add":
        return add(argv[1], argv[2], argv[3], None)
    if len(argv) == 5 and argv[0] == "add" and argv[3] == "--unverified":
        return add(argv[1], argv[2], None, argv[4])
    fail("usage: ledger-row.py add PLAN 'CLAIM' 'COMMAND' | add PLAN 'CLAIM' --unverified 'WHAT' | rerun PLAN")


if __name__ == "__main__":
    main(sys.argv[1:])
