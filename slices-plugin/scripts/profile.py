#!/usr/bin/env python3
"""
profile.py — match a slice's work against the adopter's risk registry, so the scrutiny a
plan gets follows what it touches.

    python3 profile.py match PLAN [--kinds K,...] [--confirm ID:WHY]... [--dismiss ID:WHY]... [--write]
    python3 profile.py match --paths P,... [--kinds K,...]
    python3 profile.py rounds PLAN
    python3 profile.py check
    (each takes --registry PATH and --root DIR)

The registry is `riskRegistry` in `.claude/slices.json`, a JSON file the adopter owns:

    kinds      {id: one line}: the change kinds a drafter may declare on a shape line
    novelty    {roots: [regex], commits: N, check: prose}
    classes    [{id, status, signals: {paths, symbols, kinds}, check: {at, text, rounds},
                 # a symbol is a regex, or {"re": regex, "enters": true}
                 evidence: [ref], retired?: "<ref> — <the evidence it was wrong>"}]

`status` is `active`, `predicted`, or `retired`; a retired class never matches. Dormant is
never stored: a class no plan was profiled into over a window is dormant for that window,
and still matches the moment work touches it. `check.at` is `plan` (gap-check rounds, `rounds`
of them, default 1), `build`, or `pre-pr`; `rounds` is read only for `plan`, and a non-zero
`rounds` elsewhere is a registry error.

`match` reads the work three ways. **Paths**: every path-like token in the file, and every
CamelCase identifier, resolved to tracked files — the file itself, the one tracked file
ending in it, a directory (matched as itself, `<dir>/`, never as every file under it), or a
file whose stem is the identifier; a path that resolves to nothing is new. A class's `paths` regexes are `re.search`ed over the resolved
paths and the new ones. **Symbols**: a class's `symbols` regexes over the file's text.
**Kinds**: `--kinds`, else the kinds the newest `profiled at` record carries, else the
`kinds:` field of the shape the frame record's `drafter's pick` names. A path or a kind
enters the class. **A symbol only suggests it**: a symbol names the topic, not the risk, and
an adopter's vocabulary drifts, so a class matched by symbols alone is `suggested:` and buys
no round until the drafter decides — `--confirm ID:WHY` enters it, `--dismiss ID:WHY` records
why not. A decision the newest record carries is kept on a re-profile unless overridden. A
symbol written `{"re": …, "enters": true}` enters on its own, for vocabulary precise enough.
`--paths` matches a shape's seams with no file, for its cost line.

Novelty: a path under `novelty.roots` (every path when unset) whose directory, or anything
below it, no commit
among the last `novelty.commits` touching those roots touched (all commits when roots are
unset; merges skipped) is novel, as is a declared kind the vocabulary lacks.

The record, which `--write` appends at the end of the plan's ledger section (`## Verification
ledger`, or the heading carrying `<!-- slices: ledger -->`):

    - profiled at <sha>, <date>, slices <version> — classes: <id>, … | unclassified[; predicted: <id>, …][; suggested: <id>, …][; dismissed: <id>, …][; novel: <path|kind>, …]
      - <id> — path: <file> | symbol: <match> | kind: <kind>[ (+<n> more)]
      - <id> — confirmed: <why> | dismissed: <why>
      - novel — path: <dir> | kind: <kind>

`classes:` and `predicted:` are the classes entered, and only they buy rounds.

`rounds` prints the gap-check budget the newest record buys: round 1 is the base, carrying
`novelty.check` when the record names anything novel; then one round per `rounds` of each
matched `plan` class, active then predicted, in registry order, each line `round <r>:
<id> — <check text>`. A plan with no record, or no registry, prints `no profile` and exits 3.

`check` validates the registry: exit 0, or each error on stderr and exit 2.
"""
import argparse, datetime, json, os, re, subprocess, sys

PATHLIKE = re.compile(r"(?<![\w./-])((?:[\w.-]+/)+[\w.-]*|[\w-]+\.(?:swift|py|sh|md|json|ya?ml|toml|ts|tsx|js|kt|java|go|rs|c|h|m|mm|sql))(?![\w/])")
IDENT = re.compile(r"\b([A-Z][a-z0-9]+(?:[A-Z][A-Za-z0-9]*)+)\b")
RECORD = re.compile(r"^- profiled at ")
LEDGER = re.compile(r"^#+ .*(Verification ledger|<!-- slices: ledger -->)")
KIND_ROW = re.compile(r"^  - \S+ — kind: ([\w-]+)")
DECISION_ROW = re.compile(r"^  - (\S+) — (confirmed|dismissed): (.*)$")
SLUG = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
STATUSES = ("active", "predicted", "retired")
ATS = ("plan", "build", "pre-pr")
SHOWN = 3


def fail(msg, code=2):
    sys.stderr.write("profile: " + msg + "\n")
    raise SystemExit(code)


def git(root, *args):
    r = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def toplevel(start):
    return git(start, "rev-parse", "--show-toplevel").strip() or os.getcwd()


def registry_path(root, explicit):
    if explicit:
        return os.path.join(root, explicit)
    try:
        with open(os.path.join(root, ".claude", "slices.json"), encoding="utf-8") as f:
            p = json.load(f).get("riskRegistry")
    except (OSError, ValueError):
        p = None
    return os.path.join(root, p) if p else None


def errors(reg):
    out = []
    if not isinstance(reg, dict):
        return ["the registry is not a JSON object"]
    kinds = reg.get("kinds") or {}
    if not isinstance(kinds, dict):
        out.append("kinds is not an object")
        kinds = {}
    nov = reg.get("novelty") or {}
    for rx in nov.get("roots") or []:
        try:
            re.compile(rx)
        except re.error as e:
            out.append(f"novelty.roots {rx!r}: {e}")
    if "commits" in nov and not (isinstance(nov["commits"], int) and nov["commits"] > 0):
        out.append("novelty.commits is not a positive integer")
    seen = set()
    for i, c in enumerate(reg.get("classes") or []):
        cid = c.get("id") if isinstance(c, dict) else None
        where = f"class {cid or i}"
        if not isinstance(cid, str) or not SLUG.match(cid):
            out.append(f"{where}: id is not a slug")
        elif cid in seen:
            out.append(f"{where}: id repeats")
        seen.add(cid)
        if not isinstance(c, dict):
            continue
        if c.get("status") not in STATUSES:
            out.append(f"{where}: status is not one of {', '.join(STATUSES)}")
        if c.get("status") == "retired" and not c.get("retired"):
            out.append(f"{where}: retired with no `retired` evidence line")
        sig = c.get("signals") or {}
        for field in ("paths", "symbols"):
            for rx in sig.get(field) or []:
                if field == "symbols" and isinstance(rx, dict):
                    if set(rx) - {"re", "enters"} or not isinstance(rx.get("enters", False), bool):
                        out.append(f"{where}: a symbol object takes `re` and a boolean `enters`")
                    rx = rx.get("re")
                if not isinstance(rx, str):
                    out.append(f"{where}: signals.{field} holds a non-regex {rx!r}")
                    continue
                try:
                    re.compile(rx)
                except re.error as e:
                    out.append(f"{where}: signals.{field} {rx!r}: {e}")
        for k in sig.get("kinds") or []:
            if k not in kinds:
                out.append(f"{where}: kind {k} is not in the kinds vocabulary")
        chk = c.get("check") or {}
        if chk.get("at") not in ATS:
            out.append(f"{where}: check.at is not one of {', '.join(ATS)}")
        if not chk.get("text"):
            out.append(f"{where}: check.text is empty")
        r = chk.get("rounds", 1 if chk.get("at") == "plan" else 0)
        if not isinstance(r, int) or r < 0:
            out.append(f"{where}: check.rounds is not a non-negative integer")
        elif r and chk.get("at") != "plan":
            out.append(f"{where}: check.rounds is {r} at {chk.get('at')}; only a plan check buys rounds")
    return out


def load(root, explicit):
    path = registry_path(root, explicit)
    if not path:
        return None, None
    try:
        with open(path, encoding="utf-8") as f:
            reg = json.load(f)
    except OSError as e:
        fail(f"riskRegistry {os.path.relpath(path, root)} cannot be read: {e}")
    except ValueError as e:
        fail(f"riskRegistry {os.path.relpath(path, root)} is not JSON: {e}")
    errs = errors(reg)
    if errs:
        fail("\n".join(f"{os.path.relpath(path, root)}: {e}" for e in errs))
    return reg, path


def resolve(tracked, tokens, idents):
    """(resolved tracked paths, new paths): each token as a file, a tracked file ending in
    it, or a directory as `<dir>/`; each identifier as a file whose stem it is."""
    by_stem = {}
    for f in tracked:
        by_stem.setdefault(os.path.splitext(os.path.basename(f))[0], []).append(f)
    found, new = set(), set()
    for t in tokens:
        t = re.sub(r"^(?:\.\.?/)+", "", t.rstrip(".,;:"))
        if not t:
            continue
        hit = [f for f in tracked if f == t or f.endswith("/" + t)]
        if not hit and "/" in t:
            # a directory is matched as itself, never expanded to every file under it
            d = "/" + t.rstrip("/") + "/"
            hit = {("/" + f)[1:("/" + f).index(d) + len(d)] for f in tracked if d in "/" + f}
        if hit:
            found.update(hit)
        elif "/" in t:
            new.add(t)
    for i in idents:
        found.update(by_stem.get(i, []))
    return found, new


def recent_dirs(root, roots, n):
    """The directories touched by the newest n non-merge commits that touch a path under
    roots (every commit when roots is empty)."""
    rx = [re.compile(r) for r in roots]
    p = subprocess.Popen(["git", "-C", root, "log", "--no-merges", "--format=%x00", "--name-only"],
                         stdout=subprocess.PIPE, text=True)
    dirs, count, cur = set(), 0, []

    def take(files):
        nonlocal count
        files = [f for f in files if not rx or any(r.search(f) for r in rx)]
        if files:
            count += 1
            dirs.update(os.path.dirname(f) for f in files)

    try:
        for line in p.stdout:
            if line.startswith("\x00"):
                take(cur)
                cur = []
                if count >= n:
                    break
            elif line.strip():
                cur.append(line.strip())
        else:
            take(cur)
    finally:
        p.kill()
        p.wait()
    return dirs


def picked_kinds(text):
    m = re.search(r"^- drafter's pick: (?:shape )?([A-Za-z0-9()]+)", text, re.M)
    if not m:
        return []
    shape = re.search(r"^- shape " + re.escape(m.group(1)) + r":.*?\bkinds: ([^—\n]+)", text, re.M)
    if not shape:
        return []
    return [k.strip() for k in shape.group(1).split(",") if k.strip() and k.strip() != "none"]


def newest_rows(lines):
    at = max((i for i, l in enumerate(lines) if RECORD.match(l)), default=None)
    if at is None:
        return None
    i = at + 1
    while i < len(lines) and lines[i].startswith("  - "):
        i += 1
    return lines[at + 1:i]


def recorded_kinds(lines):
    rows = newest_rows(lines)
    if rows is None:
        return None
    return list(dict.fromkeys(m.group(1) for m in map(KIND_ROW.match, rows) if m))


def recorded_decisions(lines):
    """{id: (confirmed|dismissed, why)} from the newest record."""
    return {m.group(1): (m.group(2), m.group(3)) for m in map(DECISION_ROW.match, newest_rows(lines) or []) if m}


def match(reg, root, text, paths, kinds, decisions):
    tracked = [l for l in git(root, "ls-files").splitlines() if l]
    tokens = PATHLIKE.findall(text) + list(paths)
    found, new = resolve(tracked, tokens, IDENT.findall(text))
    every = sorted(found | new)
    hits, predicted, suggested, dismissed = {}, {}, {}, {}
    for c in reg.get("classes") or []:
        if c["status"] == "retired":
            continue
        sig = c.get("signals") or {}
        entering, merely = [], []
        for rx in sig.get("paths") or []:
            entering += [f"path: {p}" for p in every if re.search(rx, p)]
        entering += [f"kind: {k}" for k in kinds if k in (sig.get("kinds") or [])]
        for sym in sig.get("symbols") or []:
            rx, enters = (sym["re"], sym.get("enters", False)) if isinstance(sym, dict) else (sym, False)
            (entering if enters else merely).extend(f"symbol: {m.group(0)}" for m in re.finditer(rx, text, re.I))
        rows = list(dict.fromkeys(entering + merely))
        verdict, why = decisions.get(c["id"], (None, None))
        if verdict == "confirmed":
            rows.append(f"confirmed: {why}")
        elif not entering and merely:
            if verdict == "dismissed":
                dismissed[c["id"]] = rows + [f"dismissed: {why}"]
            else:
                suggested[c["id"]] = rows
            continue
        if entering or verdict == "confirmed":
            (predicted if c["status"] == "predicted" else hits)[c["id"]] = rows
    nov = reg.get("novelty") or {}
    roots = nov.get("roots") or []
    under = [p for p in every if not roots or any(re.search(r, p) for r in roots)]
    novel = []
    if under:
        recent = recent_dirs(root, roots, nov.get("commits", 300))
        dirs = {p.rstrip("/") if p.endswith("/") else os.path.dirname(p) for p in under}
        novel += [f"path: {d}" for d in sorted(dirs)
                  if not any(r == d or r.startswith(d + "/") for r in recent)]
    vocab = reg.get("kinds") or {}
    novel += [f"kind: {k}" for k in kinds if k not in vocab]
    return hits, predicted, suggested, dismissed, novel


def version():
    try:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               ".claude-plugin", "plugin.json"), encoding="utf-8") as f:
            return json.load(f).get("version", "?")
    except (OSError, ValueError):
        return "?"


def record(root, hits, predicted, suggested, dismissed, novel):
    sha = git(root, "rev-parse", "--short", "HEAD").strip() or "?"
    head = (f"- profiled at {sha}, {datetime.date.today().isoformat()}, slices {version()} — "
            f"classes: {', '.join(hits) or 'unclassified'}")
    for name, group in (("predicted", predicted), ("suggested", suggested), ("dismissed", dismissed)):
        if group:
            head += f"; {name}: {', '.join(group)}"
    if novel:
        head += f"; novel: {', '.join(n.split(': ', 1)[1] for n in novel)}"
    rows = []
    for group in (hits, predicted, suggested, dismissed):
        for cid, rs in group.items():
            # kind and decision rows are all kept: a re-profile reads them back
            kept = [r for r in rs if r.split(": ", 1)[0] in ("kind", "confirmed", "dismissed")]
            other = [r for r in rs if r not in kept]
            for r in other[:SHOWN] + kept:
                rows.append(f"  - {cid} — {r}")
            if len(other) > SHOWN:
                rows[-1 - len(kept)] += f" (+{len(other) - SHOWN} more)"
    rows += [f"  - novel — {n}" for n in novel]
    return [head] + rows


def write(plan, lines, block):
    at = next((i for i, l in enumerate(lines) if LEDGER.match(l)), None)
    if at is None:
        fail(f"{plan} has no ledger section (`## Verification ledger` or `<!-- slices: ledger -->`)")
    end = next((i for i in range(at + 1, len(lines)) if re.match(r"^#+ ", lines[i])), len(lines))
    while end > at + 1 and not lines[end - 1].strip():
        end -= 1
    lines[end:end] = block
    with open(plan, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def rounds(reg, lines):
    at = max((i for i, l in enumerate(lines) if RECORD.match(l)), default=None)
    if reg is None or at is None:
        print("no profile")
        raise SystemExit(3)
    head = lines[at]
    def field(name):
        m = re.search(name + r": ([^;]+)", head)
        return [] if not m else [x.strip() for x in m.group(1).split(",") if x.strip() != "unclassified"]
    classes, predicted, novel = field("classes"), field("predicted"), field("novel")
    nov = (reg.get("novelty") or {}).get("check")
    print("round 1: base" + (f" — novel: {', '.join(novel)} — {nov}" if novel and nov else ""))
    r = 2
    for status, named in (("active", classes), ("predicted", predicted)):
        for c in reg.get("classes") or []:
            chk = c.get("check") or {}
            if c["id"] in named and chk.get("at") == "plan":
                for _ in range(chk.get("rounds", 1)):
                    print(f"round {r}: {c['id']} — {chk['text']}")
                    r += 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["match", "rounds", "check"])
    ap.add_argument("plan", nargs="?")
    ap.add_argument("--paths", default=None, help="match: a shape's seams, comma-separated, with no file")
    ap.add_argument("--kinds", default=None, help="match: the declared change kinds, comma-separated")
    ap.add_argument("--confirm", action="append", default=[], metavar="ID:WHY",
                    help="match: enter a suggested class, with the drafter's reason; repeatable")
    ap.add_argument("--dismiss", action="append", default=[], metavar="ID:WHY",
                    help="match: decline a suggested class, with the reason; repeatable")
    ap.add_argument("--write", action="store_true", help="match PLAN: append the record to its ledger")
    ap.add_argument("--registry", default=None, help="registry path, root-relative (default: riskRegistry)")
    ap.add_argument("--root", default=None, help="repo root (default: the plan's git top level)")
    a = ap.parse_args()
    start = os.path.dirname(os.path.abspath(a.plan)) if a.plan else os.getcwd()
    root = os.path.abspath(a.root) if a.root else toplevel(start)
    reg, path = load(root, a.registry)
    if a.mode == "check":
        if reg is None:
            fail("no riskRegistry in .claude/slices.json", 3)
        print(f"{os.path.relpath(path, root)}: {len(reg.get('classes') or [])} classes, "
              f"{len(reg.get('kinds') or {})} kinds")
        return
    if a.mode == "match" and not a.plan and a.paths is None:
        fail("match takes a PLAN or --paths")
    lines = []
    if a.plan:
        try:
            with open(a.plan, encoding="utf-8") as f:
                lines = f.read().split("\n")
        except OSError as e:
            fail(f"cannot read {a.plan}: {e}")
    if a.mode == "rounds":
        return rounds(reg, lines)
    if reg is None:
        print("no riskRegistry in .claude/slices.json: no profile; the check runs as it does without one")
        raise SystemExit(3)
    text = "\n".join(lines)
    if a.kinds is not None:
        kinds = [k.strip() for k in a.kinds.split(",") if k.strip()]
    else:
        kinds = recorded_kinds(lines)
        if kinds is None:
            kinds = picked_kinds(text)
    decisions = recorded_decisions(lines)
    known = {c.get("id") for c in reg.get("classes") or []}
    for verdict, flag, given in (("confirmed", "--confirm", a.confirm), ("dismissed", "--dismiss", a.dismiss)):
        for d in given:
            cid, sep, why = d.partition(":")
            if not sep or not why.strip():
                fail(f"{flag} takes ID:WHY, not {d!r}")
            if cid.strip() not in known:
                fail(f"no class {cid.strip()} in the registry")
            decisions[cid.strip()] = (verdict, why.strip())
    paths = [p.strip() for p in (a.paths or "").split(",") if p.strip()]
    block = record(root, *match(reg, root, text, paths, kinds, decisions))
    if a.write:
        if not a.plan:
            fail("--write takes a PLAN")
        write(a.plan, lines, block)
    print("\n".join(block))


if __name__ == "__main__":
    main()
