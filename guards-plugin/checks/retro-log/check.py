#!/usr/bin/env python3
"""retro-log — the retro log holds entries in its grammar and nothing else.

  check.py --root DIR [--paths PATH]... [--exclude GLOB]...

The log is an append-only stream that a view derives state from, so every line must
be one the view can read: a key line, an occurrence, a status line, a continuation,
or blank. Under `## Entries`:

  <class>/<shape>[ (uncold)]                  key line, column 0
    YYYY-MM-DD | <source> | <text>            occurrence, continuation lines below it
    LANDED|RETIRED|UPSTREAM|FILED|NOTED|HELD|REOPENED <ref> — <text>   status: one line

Findings: a line that is none of these; a first detail line that is neither an
occurrence nor a status; an unknown status token; a status entry longer than one
line (the narrative belongs in the commit); a status line inside an occurrence entry
(a status is its own entry, key line repeated); a section after the entries.

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

ID = "retro-log"
KEY = re.compile(r"^([a-z][a-z0-9]*(?:-[a-z0-9]+)*/[a-z0-9]+(?:-[a-z0-9]+)*)( \(uncold\))?$")
OCCURRENCE = re.compile(r"^  (\d{4}-\d{2}-\d{2}) \| ([^|]+?) \|\s*(.*)$")
STATUS = re.compile(r"^  (LANDED|RETIRED|UPSTREAM|REOPENED|FILED|NOTED|HELD) (\S+(?: \+ \S+)*)(?:\s+[—-]+\s+(.*))?$")
STATUS_LIKE = re.compile(r"^  ([A-Z][A-Z -]{2,})\b")
DETAIL = re.compile(r"^  ")
HEADING = re.compile(r"^## ")
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


def check(rel, text):
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
    key, first, status_lines = None, True, 0
    for n, line in enumerate(lines[start:], start + 1):
        if not line.strip():
            continue
        if HEADING.match(line):
            out.append((n, "trailing section; the log holds entries only"))
            key = None
            continue
        if KEY.match(line):
            key, first, status_lines = KEY.match(line).group(1), True, 0
            continue
        if not DETAIL.match(line):
            out.append((n, "not a key line, a detail line, or blank"))
            key = None
            continue
        if key is None:
            out.append((n, "detail line with no key above it"))
            continue
        if first:
            first = False
            if STATUS.match(line):
                status_lines = 1
            elif OCCURRENCE.match(line):
                pass
            elif STATUS_LIKE.match(line):
                tok = STATUS_LIKE.match(line).group(1).split()[0]
                if tok in ("LANDED", "RETIRED", "UPSTREAM", "REOPENED", "FILED", "NOTED", "HELD"):
                    out.append((n, f'status line must be "{tok} <ref> — <text>"'))
                else:
                    out.append((n, f'unknown status "{tok}"; '
                                   "use LANDED, RETIRED, UPSTREAM, FILED, NOTED, HELD, or REOPENED"))
            else:
                out.append((n, 'first detail line must be "YYYY-MM-DD | source | text" '
                               'or "STATUS ref — text"'))
        elif status_lines:
            status_lines += 1
            if status_lines == 2:
                out.append((n, f"a status entry is one line ({key}); the narrative is in the commit"))
        elif STATUS.match(line):
            out.append((n, f"status line inside an occurrence entry ({key}); a status is its own "
                           "entry: the key line again, then the status line"))
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
        findings += [(rel, n, msg) for n, msg in check(rel, body)]
    for rel, n, msg in findings:
        print(f"{rel}:{n}: {msg}")
    if findings:
        sys.exit(1)
    print(f"{ID}: {len(files)} files, no findings", file=sys.stderr)


if __name__ == "__main__":
    main()
