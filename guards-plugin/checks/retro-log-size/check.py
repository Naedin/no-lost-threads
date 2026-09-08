#!/usr/bin/env python3
"""retro-log-size — an occurrence in the retro log fits in eight lines.

  check.py --root DIR [--paths PATH]... [--exclude GLOB]...

The grammar lets an occurrence carry continuation lines without bound, and that is
where a log grows past what any reader opens. An occurrence is the cited moment, the
cost, and the placement: eight lines at most, counted from its dated line through its
last continuation. The narrative that does not fit belongs in the commit, the stub, or
the plan the placement names.

A separate check from `retro-log` so a repo can hold the grammar at `block` while its
existing entries come under the cap at `warn`.

Scope: `--paths` names the log(s), root-relative. With no `--paths`, the log is
discovered — `retroLogPath` in `.claude/threads.json`, default
`.claude/threads-retro-log.md`. `--exclude` removes fnmatch patterns after.

Findings on stdout, one per line: `<path>:<line>: <message>`.
Exit 0 pass; 1 findings; 2 refused (root missing, unreadable, no files in scope).
"""
import argparse
import fnmatch
import json
import pathlib
import re
import sys

ID = "retro-log-size"
CAP = 8
KEY = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*/[a-z0-9]+(?:-[a-z0-9]+)*(?: \(uncold\))?$")
OCCURRENCE = re.compile(r"^  (\d{4}-\d{2}-\d{2}) \| ([^|]+?) \|\s*(.*)$")
DETAIL = re.compile(r"^  ")
ENTRIES = "## Entries"


def refuse(msg):
    print(f"{ID}: {msg}", file=sys.stderr)
    sys.exit(2)


def discover(root):
    cfg = root / ".claude" / "threads.json"
    rel = ".claude/threads-retro-log.md"
    if cfg.is_file():
        try:
            rel = json.loads(cfg.read_text(encoding="utf-8")).get("retroLogPath", rel)
        except (json.JSONDecodeError, AttributeError, OSError):
            refuse(f"{cfg.relative_to(root).as_posix()}: malformed")
    return [rel]


def check(text):
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == ENTRIES:
            start = i + 1
            break
    if start is None:
        for i, line in enumerate(lines):
            if KEY.match(line):
                start = i
                break
        else:
            return []
    out = []
    key, occ_start, occ_lines = None, None, 0

    def close():
        if occ_start is not None and occ_lines > CAP:
            out.append((occ_start, f"occurrence is {occ_lines} lines (cap {CAP}) under {key}; "
                                   "the moment, the cost, the placement — the rest goes where "
                                   "the placement points"))

    for n, line in enumerate(lines[start:], start + 1):
        if KEY.match(line):
            close()
            key, occ_start, occ_lines = line.split(" ")[0], None, 0
            continue
        if OCCURRENCE.match(line):
            close()
            occ_start, occ_lines = n, 1
            continue
        if DETAIL.match(line) and occ_start is not None:
            occ_lines += 1
    close()
    return out


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
