#!/usr/bin/env python3
"""risk-review — the risk registry against what the window's work escaped, and what its
class rounds found.

  risk-review.py [--since REV] [--root DIR]

The registry is `riskRegistry` in `.claude/slices.json`, the slices plugin's; its schema is
`slices-plugin/scripts/profile.py --help`. This reads four things the slices plugin writes
and joins them over the window since REV (default `markTag`):

  profiled at <sha>, … — classes: <id>, … | unclassified[; predicted: …][; suggested: …][; dismissed: …][; novel: …]
      the newest one in each plan under `plansDir` (`.claude/slices.json`, default `Plans`),
      with the rows under it: how each class was entered
  gap-checked at <sha>, … — <N> defects …, class: <id>
      a class round; `0 defects` is an empty round
  escaped at <sha>, <date> — found by <stage>: <defect> — at <path>; class: <id> | none
      a plan-ledger line
  Escaped-class: <id | none> — found by <stage>: <defect> — at <path>
      a line in the body of a commit in `<REV>..HEAD`, a trailer or not, each text once

A ledger line is in the window when no plan under `plansDir` held it at REV: the line's own
arrival, never the sha it cites, which may name a branch commit a squash merge left off the
default branch. A plan moving directory brings no line into the window. An `Escaped-class:`
line is read anywhere in a body because a squash merge's message concatenates the branch's
messages, so git parses none of their trailers; the same text twice, a branch commit and its
merge, is one escape.

A plan entered a class by `path` when a path row names it, else by `kind`, else `confirmed`
(a suggestion the drafter took), else `symbol` (one the registry marks `enters`); a class it
was only `suggested` or `dismissed` is counted apart and never entered. An escape counts
against the class it names, as its finder judged it; one naming `none` is unclassified, and
those are grouped by the directory of `at <path>`: the add read. An escape naming an id the
registry lacks is listed apart.

Output: a summary line; `## Classes`, one row per class —
`<id>\\t<status>\\t<at>\\t<plans> plans (path <p>, kind <k>, confirmed <c>, symbol <s>; suggested
<g>, dismissed <d>)\\t<r> rounds (<e> empty)\\t<escapes> escapes[\\tdormant]` with its escapes
under it — where a class no plan in the window entered, active or predicted, is `dormant` (a
state derived here, never stored); `## Unclassified by area`, `<n>\\t<dir>`, most first, each
escape under it; `## Unknown class`, when any.

Exit 0; 3 when no registry is configured (narrate and skip); 2 when it or the window cannot
be read.
"""
import argparse, json, os, re, subprocess, sys

PROFILE = re.compile(r"^- profiled at (\S+), .*? — classes: (.*)$")
ROUND = re.compile(r"^- gap-checked at (\S+), .*? — (\d+) defects?\b.*\bclass: ([a-z0-9-]+)")
ESCAPE = re.compile(r"^- escaped at (\S+), (\S+) — found by ([^:]+): (.*) — at (\S+); class: (\S+)\s*$")
TRAILER = re.compile(r"^(\S+) — found by ([^:]+): (.*) — at (\S+)\s*$")
ENTRY = ("path", "kind", "confirmed", "symbol")


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


def fields(head):
    """{field: [ids]} from a profile line's tail: classes, predicted, suggested, dismissed."""
    out, parts = {}, head.split("; ")
    out["classes"] = [i.strip() for i in parts[0].split(",") if i.strip() not in ("", "unclassified")]
    for p in parts[1:]:
        name, _, ids = p.partition(": ")
        out[name] = [i.strip() for i in ids.split(",") if i.strip()]
    return out


def entries(head, rows):
    """{class: how it was entered | 'suggested' | 'dismissed'} for one profile record."""
    f, out = fields(head), {}
    for cid in f.get("classes", []) + f.get("predicted", []):
        how = {r.split(" — ", 1)[1].split(":", 1)[0] for r in rows
               if r.startswith(f"  - {cid} — ")}
        out[cid] = next((e for e in ENTRY if e in how), "symbol")
    for name in ("suggested", "dismissed"):
        for cid in f.get(name, []):
            out[cid] = name
    return out


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
    plans_rel = slices.get("plansDir") or "Plans"
    plans_dir = os.path.join(root, plans_rel)
    held = {l.strip() for l in git(root, "grep", "-h", "-E", "^- (profiled|gap-checked|escaped) at ",
                                     since, "--", plans_rel, check=False).splitlines()}

    def inside(line):
        return line.strip() not in held

    profiled, escapes, rounds = {}, [], []
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
            for i, l in enumerate(lines):
                m = PROFILE.match(l)
                if m:
                    j = i + 1
                    while j < len(lines) and lines[j].startswith("  - "):
                        j += 1
                    newest = (m, lines[i + 1:j])
                r = ROUND.match(l)
                if r and inside(l):
                    rounds.append((r.group(3), int(r.group(2)), rel))
                e = ESCAPE.match(l)
                if e and inside(l):
                    escapes.append((e.group(6), e.group(3).strip(), e.group(4), e.group(5), rel))
            if newest and inside(newest[0].group(0)):
                profiled[rel] = entries(newest[0].group(2), newest[1])
    log = git(root, "log", "--format=%x00%h%x1f%B", f"{since}..HEAD")
    n_trailer, seen = 0, set()
    for chunk in log.split("\x00"):
        sha, _, body = chunk.partition("\x1f")
        for v in body.splitlines():
            v = re.sub(r"^[*\s-]*", "", v).strip()
            if not v.startswith("Escaped-class: ") or v in seen:
                continue
            m = TRAILER.match(v[len("Escaped-class: "):])
            if m:
                seen.add(v)
                n_trailer += 1
                escapes.append((m.group(1), m.group(2).strip(), m.group(3), m.group(4), f"commit {sha.strip()}"))

    classes = [c for c in reg.get("classes") or [] if isinstance(c, dict)]
    known = {c.get("id") for c in classes}
    out = [f"risk: {slices['riskRegistry']} · {since}..HEAD · {len(profiled)} plans profiled · "
           f"{len(rounds)} class rounds · {len(escapes)} escapes ({n_trailer} from trailers)", "", "## Classes"]
    for c in classes:
        cid, st = c.get("id"), c.get("status")
        how = [e[cid] for e in profiled.values() if cid in e]
        n = {k: how.count(k) for k in ENTRY + ("suggested", "dismissed")}
        entered = sum(n[k] for k in ENTRY)
        mine = [e for e in escapes if e[0] == cid]
        ran = [r for r in rounds if r[0] == cid]
        row = (f"{cid}\t{st}\t{(c.get('check') or {}).get('at')}\t{entered} plans ("
               + ", ".join(f"{k} {n[k]}" for k in ENTRY)
               + f"; suggested {n['suggested']}, dismissed {n['dismissed']})"
               + f"\t{len(ran)} rounds ({sum(1 for r in ran if r[1] == 0)} empty)\t{len(mine)} escapes")
        if st in ("active", "predicted") and not entered:
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
