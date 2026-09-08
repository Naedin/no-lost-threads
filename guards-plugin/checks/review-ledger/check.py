#!/usr/bin/env python3
"""review-ledger — the deferral ledger holds current state, never a window's narrative.

  check.py --root DIR [--paths PATH]... [--exclude GLOB]...

The review reads the ledger in full every run, so it carries only what a future
review acts on: three sections, each entry a top-level bullet.

  ## Live …            what was deferred, why, its promoting signal, and one
                       `last checked: <date> — <state>` line; at most 12 lines
  ## Falsifications …  kept whole; no cap
  ## Resolved …        a pointer at the landing commit; at most 3 lines

Findings: any other section (a per-window review log belongs in the review's own
marker commit); a dated window line inside a Live entry (`09-04: no fire`,
`Re-deferred 2026-09-02:`) — the state is rewritten in place, not accreted; a Live
entry over 12 lines; a Resolved entry over 3 lines.

Scope: `--paths` names the ledger(s), root-relative. With no `--paths`, it is
discovered — `ledgerPath` in `.claude/threads.json`, default
`.claude/threads-review-ledger.md`. `--exclude` removes fnmatch patterns after.

Findings on stdout, one per line: `<path>:<line>: <message>`.
Exit 0 pass; 1 findings; 2 refused (root missing, unreadable, no files in scope).
"""
import argparse
import fnmatch
import json
import pathlib
import re
import sys

ID = "review-ledger"
H2 = re.compile(r"^## (.*)$")
BULLET = re.compile(r"^- ")
WINDOW = re.compile(r"(?<![\w-])(?:20\d\d-)?\d\d-\d\d[a-z]?:")
SECTIONS = ("live", "falsifications", "resolved")
LIVE_CAP, RESOLVED_CAP = 12, 3


def refuse(msg):
    print(f"{ID}: {msg}", file=sys.stderr)
    sys.exit(2)


def discover(root):
    cfg = root / ".claude" / "threads.json"
    rel = ".claude/threads-review-ledger.md"
    if cfg.is_file():
        try:
            rel = json.loads(cfg.read_text(encoding="utf-8")).get("ledgerPath", rel)
        except (json.JSONDecodeError, AttributeError, OSError):
            refuse(f"{cfg.relative_to(root).as_posix()}: malformed")
    return [rel]


def section_of(title):
    t = title.strip().lower()
    for s in SECTIONS:
        if t.startswith(s):
            return s
    return None


def check(text):
    out = []
    section = None
    entry_start, entry_lines, entry_windows = None, 0, []

    def close():
        if entry_start is None:
            return
        if section == "live":
            for n in entry_windows:
                out.append((n, "per-window line; rewrite the state in place and keep one "
                               "`last checked: <date> — <state>` line"))
            if entry_lines > LIVE_CAP:
                out.append((entry_start, f"live entry is {entry_lines} lines (cap {LIVE_CAP}): "
                                         "what, why, promoting signal, last checked"))
        elif section == "resolved" and entry_lines > RESOLVED_CAP:
            out.append((entry_start, f"resolved entry is {entry_lines} lines (cap {RESOLVED_CAP}); "
                                     "a pointer at the landing commit, the narrative lives there"))

    for n, line in enumerate(text.splitlines(), 1):
        m = H2.match(line)
        if m:
            close()
            entry_start, entry_lines, entry_windows = None, 0, []
            section = section_of(m.group(1))
            if section is None:
                out.append((n, f'section "{m.group(1).strip()}" is not Live, Falsifications, or '
                               "Resolved; a window's narrative belongs in the review's marker commit"))
            continue
        if section is None:
            continue
        if BULLET.match(line):
            close()
            entry_start, entry_lines, entry_windows = n, 0, []
        if entry_start is None or not line.strip():
            continue
        entry_lines += 1
        if section == "live" and WINDOW.search(line):
            entry_windows.append(n)
    close()
    return sorted(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True)
    ap.add_argument("--paths", action="append", default=[])
    ap.add_argument("--exclude", action="append", default=[])
    args = ap.parse_args()
    root = pathlib.Path(args.root).resolve()
    if not root.is_dir():
        refuse(f"root not found: {args.root}")
    paths = args.paths or discover(root)
    files = [root / p for p in paths if (root / p).is_file()]
    files = [f for f in files
             if not any(fnmatch.fnmatch(f.relative_to(root).as_posix(), g) for g in args.exclude)]
    if not files:
        refuse("no files in scope")
    findings = []
    for f in files:
        rel = f.relative_to(root).as_posix()
        try:
            body = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            refuse(f"unreadable: {rel}: {e}")
        findings += [(rel, n, msg) for n, msg in check(body)]
    for rel, n, msg in findings:
        print(f"{rel}:{n}: {msg}")
    if findings:
        sys.exit(1)
    print(f"{ID}: {len(files)} files, no findings", file=sys.stderr)


if __name__ == "__main__":
    main()
