#!/usr/bin/env python3
"""checks runner — reads .claude/checks.json at the root, runs each enabled check,
and maps its findings through the check's rung.

  run.py [--root DIR]        DIR defaults to the git top level, else the cwd.

Output: one line per finding on stdout, `<id>: <path>:<line>: <message>`, prefixed
`warn ` when the check's rung is warn. One summary line on stderr names each check
run, its rung, and its finding count.

Exit 0: no block check found anything and no check refused.
Exit 1: a block check found something.
Exit 2: the config is unreadable or malformed, names a check id that does not
        exist, or any check exited 2 — regardless of rung. A gate that cannot run
        is never a passed one.
No config at the root: exit 0, no output.
"""
import argparse
import json
import pathlib
import subprocess
import sys

PLUGIN = pathlib.Path(__file__).resolve().parent
CHECKS = PLUGIN / "checks"
RUNGS = ("warn", "block")


def err(msg):
    print(f"checks: {msg}", file=sys.stderr)


def git_toplevel():
    r = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else "."


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
                    help="repo root holding .claude/checks.json (default: git top level)")
    args = ap.parse_args()
    root = pathlib.Path(args.root or git_toplevel()).resolve()
    config = root / ".claude" / "checks.json"
    if not config.exists():
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

    refused = blocked = False
    summary = []
    for cid, spec in checks.items():
        cmd = [sys.executable, str(CHECKS / cid / "check.py"), "--root", str(root)]
        for p in spec["paths"]:
            cmd += ["--paths", p]
        for g in spec["exclude"]:
            cmd += ["--exclude", g]
        r = subprocess.run(cmd, capture_output=True, text=True)
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
