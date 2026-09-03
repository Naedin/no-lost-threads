#!/usr/bin/env python3
"""war-stories — no narrative provenance in the docs an agent reads as premise.

  check.py --root DIR --paths PATH [--paths PATH]... [--exclude GLOB]...

A rule states its mechanism and its rung; the incident that produced it belongs in
the commit message and the low-trust logs. This check matches the retelling
vocabulary — a session, a person's turn, a redirect, an emergency, a message that
never arrived — in prose. Counts and present-tense properties are structure, not
retelling, and are not matched. Fenced code blocks and code spans are not prose.

Scope: the universe is `--paths`, root-relative files (a listed path absent from the
tree is skipped). `--exclude` removes fnmatch patterns from it and applies after.

Findings on stdout, one per line: `<path>:<line>: <message>`.
Exit 0 pass; 1 findings; 2 refused (root missing, a file in scope unreadable, no
files in scope).
"""
import argparse
import fnmatch
import pathlib
import re
import sys

ID = "war-stories"
NARRATIVE = re.compile(
    r"this session|maintainer:|user:|had to (?:say|redirect|point|stop)|emergency"
    r"|was caught by|never arrived", re.IGNORECASE)
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
RUN = re.compile(r"`+")


def strip_spans(line):
    """Blank every code span: a backtick run closed by a run of the same length."""
    out, i = [], 0
    while True:
        m = RUN.search(line, i)
        if not m:
            out.append(line[i:])
            return "".join(out)
        n = len(m.group())
        close = re.compile(f"(?<!`)`{{{n}}}(?!`)").search(line, m.end())
        if not close:
            out.append(line[i:m.end()])
            i = m.end()
            continue
        out.append(line[i:m.start()])
        i = close.end()


def prose_lines(text):
    """(line number, line) for every prose line: fences skipped, spans blanked."""
    fence = None
    for n, line in enumerate(text.splitlines(), 1):
        m = FENCE.match(line)
        if fence is None:
            if m:
                fence = m.group(1)
                continue
            yield n, strip_spans(line)
        elif m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) \
                and line.strip() == m.group(1):
            fence = None


def refuse(msg):
    print(f"{ID}: {msg}", file=sys.stderr)
    sys.exit(2)


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
    files = [root / p for p in args.paths if (root / p).is_file()]
    files = [f for f in files
             if not any(fnmatch.fnmatch(f.relative_to(root).as_posix(), g)
                        for g in args.exclude)]
    if not files:
        refuse("no files in scope")

    findings = []
    for f in files:
        rel = f.relative_to(root).as_posix()
        try:
            body = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            refuse(f"unreadable: {rel}: {e}")
        for n, line in prose_lines(body):
            for m in NARRATIVE.finditer(line):
                findings.append((rel, n, f'narrative provenance "{m.group()}"'))

    for rel, n, msg in findings:
        print(f"{rel}:{n}: {msg}")
    if findings:
        sys.exit(1)
    print(f"{ID}: {len(files)} files, no findings", file=sys.stderr)


if __name__ == "__main__":
    main()
