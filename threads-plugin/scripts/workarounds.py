#!/usr/bin/env python3
"""workarounds — rules that exist because of a tool's current behavior, each with a probe
or a re-test, so a workaround retires when the tool moves.

  workarounds.py [status|versions|due|record|check] [ID EXIT] [--all] [--id ID]... [--root DIR]

A workaround is a rule, hook, or config line that exists because a tool — the agent
harness, a CLI, an app, a dependency — behaves as it does today. Prose restating that
behavior goes stale the day the tool changes, and nothing says so. The register is
`workaroundsPath` in `.claude/threads.json`, a JSON file the adopter owns:

  {
    "tools": { "<tool>": "<command printing its version>" },
    "workarounds": [
      { "id": "<slug>", "tool": "<tool>", "observed": "<version seen on>",
        "probe": "<command>" | null, "retest": "<how to check by hand>",
        "sites": ["<path>[#anchor]", …], "why": "<one line>" }
    ]
  }

A tool's command must report the copy that actually runs: where one tool ships twice, as a
desktop app and a CLI on PATH, the two can differ, and reading the wrong one judges every
workaround against a version nothing here runs on.

A **probe** reproduces the limitation: exit 0 means it still reproduces, exit 1 means it
no longer does, anything else means the probe could not tell. A behavior no command can
reproduce — the harness refusing an approval, a session tool stranding a sub-agent — has
`probe: null` and a **retest**, the steps a person or an agent takes to see it; it goes
due when its tool moves and is never retired without a recorded re-test. Each workaround
has exactly one of the two. **Sites** are where it lives — a doc section, a hook, a config
file — and what retiring it deletes. A tool's version is the first dotted number its
command prints, else that line.

**This script runs no command.** A tool's version and a probe's answer depend on the shell
they run in — its PATH, the functions the harness injects, its sandbox — and a subprocess
of this script is not the shell the workaround is about. So `versions` and `due` print
shell for the caller to run in its own shell (an agent's own Bash tool), and the answers
come back on stdin. The whole read, in one call:

  w=<plugin>/scripts/workarounds.py
  eval "$(python3 "$w" versions)" | python3 "$w" due | { eval "$(cat)"; } | python3 "$w" record; python3 "$w" status

A version says a tool moved, not what changed, and a probe only tests a limit someone
already wrote down. An optional `changelogs` object catches what neither can, such as a new
capability that would replace a workaround; its terms are the surfaces this repo depends on:

  "changelogs": { "<tool>": { "url": "<plain-text changelog>", "terms": ["<word>", …] } }

Each workaround is in one state, measured against its tool's version as last read:

  live       reproduces at that version: `observed` is it, or a probe or re-test at it said so
  retirable  a probe or re-test at that version said it no longer reproduces: the sites can go
  due        the version moved past `observed` and past the last answer, or the version has
             not been read. A version below an answer is that answer, so a read that flips
             between a desktop app and a CLI re-opens nothing
  broken     the probe at that version could not tell, or the version is unreadable

Answers are per machine, so they are kept outside the tree, in
`<git common dir>/threads/workarounds-state.json`, shared by every worktree.

Modes:
  status    (default) a summary line, then one line per workaround that is not live:
              <state>\\t<id>\\t<tool> <version>\\t<detail>\\t<sites>
  versions  shell printing `<tool>\\t<first line of its version command>` per tool
  due       read `versions`' lines on stdin and record them; print shell running the probe of
            every due workaround (`--all`: every probed one; `--id`: those named), each
            printing `<id>\\t<exit>`. A due re-test is listed in `status`, never run.
  record    read `<id>\\t<exit>` lines on stdin, or one `ID EXIT` pair as arguments — a
            re-test's answer is recorded this way, 0 still reproduces, 1 no longer — at the
            tool's version as last read
  changelogs  shell fetching each tool's changelog and handing it to `changelog`
  changelog TOOL  read that changelog on stdin; print the entries past the version last read
            that match the tool's terms, as `<version>\t<entry>`, and record the newest as
            read. `--since VERSION` reads from there instead. A first read with no `--since`
            sets the baseline and prints no entries.
  check     validate the register: required fields, a probe or a re-test, a declared
            tool, unique ids, sites and a probe script that exist. One finding per line.

Exit 0; 1 when `check` has findings; 3 when no register is configured (narrate and skip);
2 when the register, the repo, or the input cannot be read.
"""
import argparse, datetime, json, os, re, shlex, subprocess, sys

VERSION = re.compile(r"\d+(?:\.\d+)+[0-9A-Za-z.+-]*")
NAME = re.compile(r"^[A-Za-z0-9._-]+$")
REQUIRED = ("id", "tool", "observed", "sites")
OPTIONAL = ("probe", "retest", "why")


def refuse(msg, code=2):
    print(f"workarounds: {msg}", file=sys.stderr)
    sys.exit(code)


def git(root, *args):
    r = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)
    if r.returncode != 0:
        refuse(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout.strip()


def load(path, what):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except OSError as e:
        refuse(f"{what} unreadable: {e}")
    except ValueError as e:
        refuse(f"{what} is not JSON: {e}")


def register(root):
    cfg = os.path.join(root, ".claude", "threads.json")
    rel = (load(cfg, ".claude/threads.json") if os.path.isfile(cfg) else {}).get("workaroundsPath")
    if not rel:
        print("workarounds: no workaroundsPath in .claude/threads.json; read skipped")
        sys.exit(3)
    reg = load(os.path.join(root, rel), rel)
    if not isinstance(reg, dict) or not isinstance(reg.get("tools", {}), dict) \
            or not isinstance(reg.get("workarounds", []), list):
        refuse(f"{rel}: expected an object with a `tools` object and a `workarounds` list")
    reg.setdefault("tools", {})
    reg.setdefault("workarounds", [])
    return rel, reg


def findings(root, reg):
    out, seen, tools = [], set(), reg["tools"]
    for t, cmd in tools.items():
        if not NAME.match(t):
            out.append(f"tool {t}: a tool name is letters, digits, `.`, `_`, `-`")
        if not isinstance(cmd, str) or not cmd.strip():
            out.append(f"tool {t}: its version command must be a non-empty string")
    logs = reg.get("changelogs", {})
    if not isinstance(logs, dict):
        out.append("`changelogs` must be an object")
        logs = {}
    for t, spec in logs.items():
        if t not in tools:
            out.append(f"changelog {t}: tool is not in `tools`")
        if not (isinstance(spec, dict) and isinstance(spec.get("url"), str) and spec["url"]
                and isinstance(spec.get("terms"), list) and spec["terms"]
                and all(isinstance(x, str) and x for x in spec["terms"])):
            out.append(f"changelog {t}: needs a `url` and a non-empty list of `terms`")
    for n, w in enumerate(reg["workarounds"], 1):
        if not isinstance(w, dict):
            out.append(f"workaround {n}: not an object")
            continue
        wid = w.get("id") or f"#{n}"
        for k in REQUIRED:
            if not w.get(k):
                out.append(f"{wid}: no `{k}`")
        if w.get("id") and not NAME.match(str(w["id"])):
            out.append(f"{wid}: an id is letters, digits, `.`, `_`, `-`")
        for k in w:
            if k not in REQUIRED + OPTIONAL:
                out.append(f"{wid}: unknown field `{k}`")
        probe, retest = w.get("probe"), w.get("retest")
        if bool(probe) == bool(retest):
            out.append(f"{wid}: needs a `probe` or, with `probe: null`, a `retest` — exactly one;"
                       " a workaround neither can check is not admitted")
        if wid in seen:
            out.append(f"{wid}: id used twice")
        seen.add(wid)
        if w.get("tool") and w["tool"] not in tools:
            out.append(f"{wid}: tool {w['tool']} is not in `tools`")
        sites = w.get("sites") or []
        if not isinstance(sites, list) or not all(isinstance(s, str) for s in sites):
            out.append(f"{wid}: `sites` must be a list of paths")
            sites = []
        for s in sites:
            if not os.path.exists(os.path.join(root, s.split("#", 1)[0])):
                out.append(f"{wid}: site {s}: no such path")
        if isinstance(probe, str) and probe.strip():
            try:
                words = shlex.split(probe)
            except ValueError as e:
                out.append(f"{wid}: probe does not parse: {e}")
                continue
            # the script is the first word naming a path: `sh probes/x.sh`, `probes/x.sh`
            first = next((x for x in words if "/" in x and not x.startswith("-")), "")
            if first and not os.path.isabs(first) and not os.path.exists(os.path.join(root, first)):
                out.append(f"{wid}: probe script {first}: no such file")
    return out


def state_path(root):
    common = git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    return os.path.join(common, "threads", "workarounds-state.json")


def save(path, state):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")


def not_past(now, answered):
    """True when a version read is at or below one already answered. The copy that runs can
    differ by surface, and reading an older one has not moved the tool."""
    a, b = version_key(now), version_key(answered or "")
    return bool(a and b) and a <= b


def classify(w, now, results):
    """(state, detail) for one workaround at its tool's version as last read."""
    if now is None:
        return "due", "version not read"
    if now == "":
        return "broken", "version unreadable"
    r = results.get(w["id"])
    if r and not_past(now, r.get("version")):
        now = r["version"]
    if not r or r.get("version") != now:
        if not_past(now, w["observed"]):
            return "live", f"observed at {w['observed']}"
        how = f"re-test: {w['retest']}" if not w.get("probe") else "probe"
        return "due", f"observed at {w['observed']}, nothing answered at {now} — {how}"
    if r["exit"] == 0:
        return "live", f"reproduced at {now} on {r['date']}"
    if r["exit"] == 1:
        return "retirable", f"stopped reproducing at {now} on {r['date']} (observed at {w['observed']})"
    return "broken", f"probe at {now} on {r['date']}: exit {r['exit']}"


def pairs(lines, what):
    out = []
    for n, l in enumerate(lines, 1):
        if not l.strip():
            continue
        k, sep, v = l.rstrip("\n").partition("\t")
        if not sep:
            refuse(f"{what} line {n}: expected `<name>\\t<value>`: {l.strip()!r}")
        out.append((k, v))
    return out


def version_key(v):
    return tuple(int(x) for x in re.findall(r"\d+", v))


def changelog_mode(a, root, reg):
    logs = reg.get("changelogs", {})
    q = shlex.quote
    if a.mode == "changelogs":
        for t, spec in logs.items():
            print(f"curl -fsSL {q(spec['url'])} | python3 {q(os.path.abspath(__file__))} "
                  f"changelog {q(t)} --root {q(root)}")
        return
    if len(a.answer) != 1 or a.answer[0] not in logs:
        refuse(f"changelog takes one tool with a `changelogs` entry; have: {', '.join(logs) or 'none'}")
    tool = a.answer[0]
    terms = [t.lower() for t in logs[tool]["terms"]]
    sections, current = [], None
    for line in sys.stdin:
        m = re.match(r"#+\s*\[?v?(\d+(?:\.\d+)+)", line)
        if m:
            current = m.group(1)
            sections.append((current, []))
        elif current and line.lstrip().startswith(("- ", "* ")):
            sections[-1][1].append(" ".join(line.split())[2:])
    if not sections:
        refuse(f"changelog {tool}: no versions on stdin; nothing recorded")
    spath = state_path(root)
    state = load(spath, spath) if os.path.isfile(spath) else {}
    read = state.setdefault("changelogRead", {})
    newest = max((v for v, _ in sections), key=version_key)
    since = a.since or read.get(tool)
    if not since:
        read[tool] = newest
        save(spath, state)
        print(f"changelog {tool}: baseline set at {newest}; pass --since VERSION to read further back")
        return
    fresh = sorted((s for s in sections if version_key(s[0]) > version_key(since)), key=lambda s: version_key(s[0]))
    hits = [(v, e) for v, entries in fresh for e in entries if any(t in e.lower() for t in terms)]
    for v, e in hits:
        print(f"{v}\t{e}")
    total = sum(len(entries) for _, entries in fresh)
    print(f"changelog {tool}: {since} to {newest}, {len(hits)} of {total} entries match")
    read[tool] = newest
    save(spath, state)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", nargs="?", default="status", choices=("status", "versions", "due", "record", "check", "changelogs", "changelog"))
    ap.add_argument("answer", nargs="*", help="record: ID EXIT; changelog: TOOL")
    ap.add_argument("--since", default=None, help="changelog: read past this version")
    ap.add_argument("--all", action="store_true", help="due: every probed workaround, not only the due ones")
    ap.add_argument("--id", action="append", default=[], help="due: only this workaround (repeatable)")
    ap.add_argument("--root", default=None, help="repo root (default: git top level)")
    a = ap.parse_args()
    root = os.path.abspath(a.root) if a.root else git(os.getcwd(), "rev-parse", "--show-toplevel")
    rel, reg = register(root)
    bad = findings(root, reg)
    if a.mode == "check":
        for f in bad:
            print(f"{rel}: {f}")
        print(f"workarounds: {len(reg['workarounds'])} in {rel}, {len(bad)} findings", file=sys.stderr)
        sys.exit(1 if bad else 0)
    if bad:
        refuse(f"{rel} is malformed ({bad[0]}); run `workarounds.py check`")
    by_id = {w["id"]: w for w in reg["workarounds"]}
    for i in a.id:
        if i not in by_id:
            refuse(f"--id {i}: no such workaround in {rel}")

    if a.mode in ("changelogs", "changelog"):
        return changelog_mode(a, root, reg)

    # stdin first: in the one-call read, `record` starts beside `due`, and its input ends only
    # once `due` has written the versions it must load
    got = []
    if a.mode == "due":
        got = pairs(sys.stdin.readlines(), "versions")
    elif a.mode == "record":
        if a.answer and len(a.answer) != 2:
            refuse("record takes ID EXIT, or lines on stdin")
        got = [tuple(a.answer)] if a.answer else pairs(sys.stdin.readlines(), "record")
    spath = state_path(root)
    state = load(spath, spath) if os.path.isfile(spath) else {}
    versions, results = state.setdefault("versions", {}), state.setdefault("results", {})
    today = datetime.date.today().isoformat()
    q = shlex.quote

    if a.mode == "versions":
        for t, cmd in reg["tools"].items():
            print(f"( cd {q(root)} && printf '%s\\t%s\\n' {q(t)} \"$( ( {cmd} ) 2>/dev/null </dev/null | head -n 1)\" )")
        return

    if a.mode == "due":
        for t, line in got:
            if t not in reg["tools"]:
                refuse(f"versions: unknown tool {t}")
            m = VERSION.search(line)
            versions[t] = {"version": m.group(0) if m else line.strip(), "date": today}
        save(spath, state)
        for w in reg["workarounds"]:
            if not w.get("probe"):
                continue
            now = versions.get(w["tool"], {}).get("version")
            chosen = w["id"] in a.id if a.id else (a.all or classify(w, now, results)[0] == "due")
            if chosen and now:
                print(f"( cd {q(root)} && ( {w['probe']} ) >/dev/null 2>&1 </dev/null; printf '%s\\t%s\\n' {q(w['id'])} \"$?\" )")
        return

    if a.mode == "record":
        for wid, code in got:
            if wid not in by_id:
                refuse(f"record: no such workaround {wid}")
            if not re.fullmatch(r"\d+", code.strip()):
                refuse(f"record: {wid}: exit {code!r} is not a number")
            now = versions.get(by_id[wid]["tool"], {}).get("version")
            if not now:
                refuse(f"record: {wid}: the version of {by_id[wid]['tool']} has not been read; run `due` first")
            results[wid] = {"version": now, "exit": int(code), "date": today}
        save(spath, state)
        print(f"workarounds: recorded {len(got)}", file=sys.stderr)
        return

    rows, counts = [], {"live": 0, "retirable": 0, "due": 0, "broken": 0}
    for w in reg["workarounds"]:
        now = versions.get(w["tool"], {}).get("version")
        s, detail = classify(w, now, results)
        counts[s] += 1
        if s != "live":
            rows.append(f"{s}\t{w['id']}\t{w['tool']} {now or '?'}\t{detail}\t{', '.join(w['sites'])}")
    tools = ", ".join(f"{t} {versions.get(t, {}).get('version') or '?'}" for t in reg["tools"]) or "no tools"
    print(f"workarounds {rel}: {len(reg['workarounds'])} — " + " · ".join(f"{k} {v}" for k, v in counts.items())
          + f"; {tools}")
    for r in sorted(rows):
        print(r)


if __name__ == "__main__":
    main()
