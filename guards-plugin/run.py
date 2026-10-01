#!/usr/bin/env python3
"""guards runner — reads .claude/guards.json at the root, runs each enabled check,
and maps its findings through the check's rung.

  run.py [--root DIR] [--diff-range RANGE]
                             DIR defaults to the git top level, else the cwd.

--diff-range hands the checks the diff of RANGE in DIR's checkout (any range
`git diff` takes, e.g. `origin/main...HEAD`) as GUARDS_DIFF, written the way the git
adapter writes the staged diff. A check that judges a claim when it is written then
judges the lines the range adds or changes, where a run without it is the audit read
of every standing claim; the other checks read the whole tree either way.

Output: one line per finding on stdout, `<id>: <path>:<line>: <message>`, prefixed
`warn ` when the check's rung is warn. One summary line on stderr names each check
run, its rung, and its finding count.

Exit 0: no block check found anything and no check refused.
Exit 1: a block check found something.
Exit 2: the config is unreadable or malformed, names a check id that does not
        exist, --diff-range is a range git cannot diff, or any check exited 2 —
        regardless of rung. A gate that cannot run
        is never a passed one.
No config at the root: exit 0 and one stderr line saying nothing was judged — a
run that judged nothing never reads as a run that passed.
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import tempfile

PLUGIN = pathlib.Path(__file__).resolve().parent
CHECKS = PLUGIN / "checks"
RUNGS = ("warn", "block")


def err(msg):
    print(f"guards: {msg}", file=sys.stderr)


def git_toplevel():
    r = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else "."


def range_diff(root, rng):
    """The diff of rng in root's checkout, written as the git adapter writes the staged
    diff — -U0, a moved file read as moved, prefixes pinned, a non-ASCII path left raw —
    or ValueError carrying git's message."""
    r = subprocess.run(
        ["git", "-C", str(root), "-c", "core.quotePath=false", "diff", "-U0", "-M",
         "--no-color", "--no-ext-diff", "--no-textconv",
         "--src-prefix=a/", "--dst-prefix=b/", rng, "--"],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise ValueError(r.stderr.strip() or f"git diff exited {r.returncode}")
    return r.stdout


def load_config(path):
    """{id: {rung, paths, exclude}} in config order, or ValueError naming the defect."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as e:
        raise ValueError(f"unreadable: {e}")
    except json.JSONDecodeError as e:
        raise ValueError(f"malformed JSON: {e}")
    if not isinstance(data, dict) or not isinstance(data.get("checks"), dict):
        raise ValueError('malformed: the top level must be {"checks": {...}}')
    out = {}
    for cid, spec in data["checks"].items():
        if not isinstance(spec, dict) or spec.get("rung") not in RUNGS:
            raise ValueError(f'malformed: "{cid}" needs "rung": "warn" or "block"')
        for key in ("paths", "exclude"):
            v = spec.get(key, [])
            if not (isinstance(v, list) and all(isinstance(x, str) for x in v)):
                raise ValueError(f'malformed: "{cid}".{key} must be a list of strings')
        out[cid] = {"rung": spec["rung"],
                    "paths": spec.get("paths", []),
                    "exclude": spec.get("exclude", [])}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=None,
                    help="repo root holding .claude/guards.json (default: git top level)")
    ap.add_argument("--diff-range", default=None, metavar="RANGE",
                    help="hand the checks the diff of RANGE as GUARDS_DIFF")
    args = ap.parse_args()
    root = pathlib.Path(args.root or git_toplevel()).resolve()
    config = root / ".claude" / "guards.json"
    if not config.exists():
        err(f"no .claude/guards.json at {root}, nothing judged")
        return 0

    try:
        checks = load_config(config)
    except ValueError as e:
        err(f"{config.relative_to(root).as_posix()}: {e}")
        return 2
    missing = [cid for cid in checks if not (CHECKS / cid / "check.py").is_file()]
    for cid in missing:
        err(f"no such check: {cid}")
    if missing:
        return 2

    if args.diff_range is None:
        return run_checks(root, checks, None)
    try:
        diff = range_diff(root, args.diff_range)
    except ValueError as e:
        err(f"--diff-range {args.diff_range}: {e}")
        return 2
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", prefix="guards-diff-",
                                     suffix=".diff") as f:
        f.write(diff)
        f.flush()
        return run_checks(root, checks, dict(os.environ, GUARDS_DIFF=f.name))


def run_checks(root, checks, env):
    refused = blocked = False
    summary = []
    for cid, spec in checks.items():
        cmd = [sys.executable, str(CHECKS / cid / "check.py"), "--root", str(root)]
        for p in spec["paths"]:
            cmd += ["--paths", p]
        for g in spec["exclude"]:
            cmd += ["--exclude", g]
        r = subprocess.run(cmd, capture_output=True, text=True, env=env)
        findings = [line for line in r.stdout.splitlines() if line.strip()]
        if r.returncode == 1:
            prefix = "warn " if spec["rung"] == "warn" else ""
            for line in findings:
                print(f"{prefix}{cid}: {line}")
            if spec["rung"] == "block":
                blocked = True
            summary.append(f"{cid} {spec['rung']} {len(findings)} findings")
        elif r.returncode == 0:
            summary.append(f"{cid} {spec['rung']} 0 findings")
        else:
            refused = True
            sys.stderr.write(r.stderr)
            err(f"{cid}: refused (exit {r.returncode})")
            summary.append(f"{cid} {spec['rung']} refused")
    if summary:
        err("; ".join(summary))
    return 2 if refused else 1 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
