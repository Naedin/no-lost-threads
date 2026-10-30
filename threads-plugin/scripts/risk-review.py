#!/usr/bin/env python3
"""risk-review — the risk registry against what the window's work escaped.

  risk-review.py [--since REV] [--root DIR]

The registry is `riskRegistry` in `.claude/slices.json`, the slices plugin's; its schema is
`slices-plugin/scripts/profile.py --help`. This reads three things the slices plugin writes
and joins them over the window `<REV>..HEAD` (REV defaults to `markTag`):

  profiled at <sha>, … — classes: <id>, … | unclassified[; predicted: …][; novel: …]
      the newest one in each plan under `plansDir` (`.claude/slices.json`, default `Plans`),
      in the window when its sha is
  escaped at <sha>, <date> — found by <stage>: <defect> — at <path>; class: <id> | none
      a plan-ledger line, in the window when its sha is
  Escaped-class: <id | none> — found by <stage>: <defect> — at <path>
      a commit trailer on a fix with no plan, in the window when its commit is

An escape counts against the class it names, as its finder judged it; one naming `none` is
unclassified, and those are grouped by the directory of `at <path>`:
the add read. An escape naming an id the registry lacks is listed apart.

Output: a summary line; `## Classes`, one row per class —
`<id>\\t<status>\\t<at>\\t<plans> plans\\t<escapes> escapes[\\tdormant]` with its escapes under
it — where a class no plan in the window was profiled into, active or predicted, is
`dormant` (a state derived here, never stored); `## Unclassified by area`, `<n>\\t<dir>`, most
first, each escape under it; `## Unknown class`, when any.

Exit 0; 3 when no registry is configured (narrate and skip); 2 when it or the window cannot
be read.
"""
import argparse, json, os, re, subprocess, sys

PROFILE = re.compile(r"^- profiled at (\S+), .*? — classes: ([^;]+)(?:; predicted: ([^;]+))?")
ESCAPE = re.compile(r"^- escaped at (\S+), (\S+) — found by ([^:]+): (.*) — at (\S+); class: (\S+)\s*$")
TRAILER = re.compile(r"^(\S+) — found by ([^:]+): (.*) — at (\S+)\s*$")


def refuse(msg, code=2):
    print(f"risk-review: {msg}", file=sys.stderr)
    sys.exit(code)


def git(root, *args, check=True):
    r = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)
    if r.returncode != 0 and check:
        refuse(f"git {' '.join(args[:2])} failed: {r.stderr.strip()}")
    return r.stdout


def config(root, name):
    try:
        with open(os.path.join(root, ".claude", name), encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        return {}
    except ValueError as e:
        refuse(f".claude/{name} is not JSON: {e}")


def ids(names):
    return [n.strip() for n in (names or "").split(",") if n.strip() and n.strip() != "unclassified"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", default=None, metavar="REV", help="window start (default: markTag)")
    ap.add_argument("--root", default=None, help="repo root (default: git top level)")
    a = ap.parse_args()
    root = os.path.abspath(a.root) if a.root else git(os.getcwd(), "rev-parse", "--show-toplevel").strip()
    slices = config(root, "slices.json")
    if not slices.get("riskRegistry"):
        print("risk-review: no riskRegistry in .claude/slices.json; read skipped")
        sys.exit(3)
    try:
        with open(os.path.join(root, slices["riskRegistry"]), encoding="utf-8") as f:
            reg = json.load(f)
    except (OSError, ValueError) as e:
        refuse(f"riskRegistry {slices['riskRegistry']}: {e}")
    since = a.since or config(root, "threads.json").get("markTag") or "process-review-mark"
    if not git(root, "rev-parse", "--verify", "-q", since + "^{commit}", check=False).strip():
        refuse(f"no commit {since}")
    window = git(root, "rev-list", f"{since}..HEAD").split()

    def inside(sha):
        return any(full.startswith(sha) for full in window) if len(sha) >= 4 else False

    plans_dir = os.path.join(root, slices.get("plansDir") or "Plans")
    profiled, escapes = {}, []
    for d, _, files in os.walk(plans_dir):
        for name in sorted(files):
            if not name.endswith(".md"):
                continue
            path = os.path.join(d, name)
            rel = os.path.relpath(path, root)
            try:
                lines = open(path, encoding="utf-8").read().splitlines()
            except OSError:
                continue
            newest = None
            for l in lines:
                m = PROFILE.match(l)
                if m:
                    newest = m
                e = ESCAPE.match(l)
                if e and inside(e.group(1)):
                    escapes.append((e.group(6), e.group(3).strip(), e.group(4), e.group(5), rel))
            if newest and inside(newest.group(1)):
                profiled[rel] = ids(newest.group(2)) + ids(newest.group(3))
    log = git(root, "log", "--format=%x00%h%x1f%(trailers:key=Escaped-class,valueonly)", f"{since}..HEAD")
    n_trailer = 0
    for chunk in log.split("\x00"):
        sha, _, vals = chunk.partition("\x1f")
        for v in vals.splitlines():
            m = TRAILER.match(v.strip())
            if m:
                n_trailer += 1
                escapes.append((m.group(1), m.group(2).strip(), m.group(3), m.group(4), f"commit {sha.strip()}"))

    classes = [c for c in reg.get("classes") or [] if isinstance(c, dict)]
    known = {c.get("id") for c in classes}
    out = [f"risk: {slices['riskRegistry']} · {since}..HEAD · {len(profiled)} plans profiled · "
           f"{len(escapes)} escapes ({n_trailer} from trailers)", "", "## Classes"]
    for c in classes:
        cid, st = c.get("id"), c.get("status")
        plans = [p for p, cs in profiled.items() if cid in cs]
        mine = [e for e in escapes if e[0] == cid]
        row = f"{cid}\t{st}\t{(c.get('check') or {}).get('at')}\t{len(plans)} plans\t{len(mine)} escapes"
        if st in ("active", "predicted") and not plans:
            row += "\tdormant"
        out.append(row)
        out += [f"\t{stage}: {what} — at {where} ({src})" for _, stage, what, where, src in mine]
    unclassified = [e for e in escapes if e[0] == "none"]
    areas = {}
    for e in unclassified:
        areas.setdefault(os.path.dirname(e[3]) or e[3], []).append(e)
    out += ["", f"## Unclassified by area ({len(unclassified)})"]
    for area, es in sorted(areas.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        out.append(f"{len(es)}\t{area}")
        out += [f"\t{stage}: {what} — at {where} ({src})" for _, stage, what, where, src in es]
    unknown = [e for e in escapes if e[0] != "none" and e[0] not in known]
    if unknown:
        out += ["", f"## Unknown class ({len(unknown)})"]
        out += [f"{cls}\t{stage}: {what} — at {where} ({src})" for cls, stage, what, where, src in unknown]
    print("\n".join(out))


if __name__ == "__main__":
    main()
