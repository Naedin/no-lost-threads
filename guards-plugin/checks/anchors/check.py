#!/usr/bin/env python3
"""anchors — every in-repo section link resolves to an explicit anchor, and every
relative link target exists.

  check.py --root DIR [--paths PATH]... [--exclude GLOB]...

Two properties over every markdown file in scope:
  1. Every `](path#frag)` whose path names a file in scope resolves to an explicit
     `<a id="frag">` in that file. Heading-derived slugs fail by design — sections
     carry an explicit anchor and are referenced by it, so rewording a heading cannot
     break an inbound link.
  2. Every relative `](path)` target exists on disk.
External links (`://`) are skipped. Fenced code blocks and code spans are not prose.

Scope: `--paths` narrows the universe to the listed root-relative files (a listed
path absent from the tree is skipped); without it, the universe is every tracked
`*.md` under the root when the root is a git checkout, else every `*.md` under it.
`--exclude` removes fnmatch patterns from the universe and applies after `--paths`.

Findings on stdout, one per line: `<path>:<line>: <message>`.
Exit 0 pass; 1 findings; 2 refused (root missing, a file in scope unreadable, no
files in scope).
"""
import argparse
import fnmatch
import pathlib
import re
import subprocess
import sys

ID = "anchors"
REF = re.compile(r"\]\(([^)#\s]*)(?:#([^)\s]+))?\)")
ANCHOR = re.compile(r'<a id="([^"]+)">')
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


def is_git_root(root):
    r = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=root,
                       capture_output=True, text=True)
    return r.returncode == 0 and pathlib.Path(r.stdout.strip()).resolve() == root


def universe(root, paths, exclude):
    if paths:
        files = [root / p for p in paths if (root / p).is_file()]
    elif is_git_root(root):
        out = subprocess.run(["git", "ls-files", "--", "*.md"], cwd=root,
                             capture_output=True, text=True, check=True).stdout
        files = [root / p for p in out.splitlines() if (root / p).is_file()]
    else:
        files = sorted(p for p in root.rglob("*.md") if ".git" not in p.parts)
    return [f for f in files
            if not any(fnmatch.fnmatch(f.relative_to(root).as_posix(), g) for g in exclude)]


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
    files = universe(root, args.paths, args.exclude)
    if not files:
        refuse("no files in scope")

    text = {}
    for f in files:
        try:
            text[f.resolve()] = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            refuse(f"unreadable: {f.relative_to(root)}: {e}")
    anchors = {f: set(ANCHOR.findall(body)) for f, body in text.items()}

    findings = []
    for src, body in text.items():
        rel = src.relative_to(root).as_posix()
        for n, line in prose_lines(body):
            for target, frag in REF.findall(line):
                if "://" in target:
                    continue
                if target and not (src.parent / target).exists():
                    findings.append((rel, n, f"missing link target {target}"))
                    continue
                if not frag:
                    continue
                dst = (src.parent / target).resolve() if target else src
                if dst not in anchors:
                    continue  # a fragment into a file outside the scope
                if frag not in anchors[dst]:
                    findings.append((rel, n, f"dead anchor {target or src.name}#{frag}"))

    for rel, n, msg in sorted(set(findings)):
        print(f"{rel}:{n}: {msg}")
    if findings:
        sys.exit(1)
    print(f"{ID}: {len(files)} files, no findings", file=sys.stderr)


if __name__ == "__main__":
    main()
