#!/usr/bin/env python3
"""adherence — the mechanical half of a declared-rule sample: draw the blocks, check the
agents' output, tally the verdicts, count a shape's windows.

  adherence.py draw     [--rule ID] [--seed S] [--since REV] [--head REV] [--blocks FILE]
                        [--config PATH] [--root DIR] [--repo DIR]
  adherence.py flags    MANIFEST JUDGE_OUT
  adherence.py verdicts MANIFEST JUDGE_OUT [REFUTER_OUT]
  adherence.py tally    MANIFEST VERDICTS [--control NAME]
  adherence.py recur    [--rule ID] [--current FILE] [--head REV] [--root DIR]

A mechanical check proves itself at its own gate; a prose rule an agent is supposed to
apply has no gate, and nothing measures whether it holds. A rule declared under
`adherenceRules` in `.claude/threads.json` is sampled instead: a seeded draw of blocks from
the rule's population, one fresh-context judge ruling each block against the tree, one
fresh-context refuter re-checking every non-TRUE verdict. This script is the draw, the
check on what the agents return, and the arithmetic; the judging is the agents'
(`commands/adherence.md`).

A rule:

  {"id": "comment-truth",                      a slug; the Adherence: line names it
   "population": "rg -n ... Sources",          a shell command, run at the root, whose every
                                               output line is `path:line:` (a hit)
   "judgePrompt": "Plans/templates/x.md",      the adopter's judge prompt, from the repo
                                               holding the config
   "n": 20,                                    distinct blocks to draw
   "weighting": "window" | "uniform",          window: only hits in files changed over
                                               <markTag>..<head>; uniform: every hit
   "block": "^\\\\s*(//|/\\\\*|\\\\*)"}               optional regex: a line matching it belongs to
                                               the block around a drawn line (default the
                                               C-family comment leaders shown); a blank or
                                               non-matching line ends the block

The window restriction is the weighting, never the command: the command is the
whole-tree population, so `uniform` stays a one-word change and the command never runs
over an empty or deleted-file window.

Modes:
  draw   the manifest the judge reads. The population's hits are shuffled by the seed and
         walked in order; each hit expands to its whole contiguous block, and a hit whose
         block was already drawn is skipped, so `n` counts distinct blocks and a
         population with fewer than `n` blocks is sampled whole. One header line, then per
         block `== path:start-end` and its lines:
           adherence <id>: <scope> · pop <f>f/<l>l · n <drawn> · seed <s>
         <scope> is `window <since> (<date>, <sha>)..<head>`, `uniform`, or `blocks <file>`.
         The seed defaults to today as YYYYMMDD. `--blocks FILE` replaces the population
         and the draw with a fixed list (`path:line` or `path:start-end`, one per line,
         each expanded to its block) — the calibration read, run with `--root` at a
         checkout pinned to a commit and `--config` naming the adopter's live config.
         Files are read from `--root` (default: the top level of `--repo`, else of the
         cwd); a window's diff and mark are read from `--repo` (default: `--root`), so a
         window over a tree that is not a checkout (one from `git archive`) names its
         repository there. The judge prompt resolves against the repository holding the
         config (so a pinned `--root` beside the live `--config` still finds it), or is
         `--judge-prompt PATH`; a missing one refuses here, before any agent is spawned,
         and stderr names the path the judge is handed:
           adherence: judge prompt <absolute path>
  flags  the judge's output, checked. It is machine-read, so it is held to one form:
           path:start-end  TRUE|DRIFTED|HISTORY  shape|-  — <reason>
         one line per manifest block, each exactly once, the key equal to a manifest
         block's; fields split by whitespace, then an em dash and a non-empty reason; TRUE
         takes `-`, DRIFTED and HISTORY a slug. Blank lines, code-fence lines, and edge
         whitespace are ignored; a `ruled <n>: <T> TRUE, <D> DRIFTED, <H> HISTORY` line
         may appear once and must agree with the lines. Anything else is a defect. Prints
         the non-TRUE lines as given (the refuter's input), nothing when every block is
         TRUE. On any defect, exits 2 with every defect on stderr, one per line — the
         text sent back to the judge.
  verdicts  the file tally reads. Re-checks JUDGE_OUT as `flags` does, then REFUTER_OUT —
         required exactly when there are flags — held to:
           path:start-end  CONFIRMED|OVERTURNED  — <reason>
         one line per flagged block, each exactly once, the key equal to a flagged line's;
         a `re-checked <n>: <C> CONFIRMED, <O> OVERTURNED` line may appear once and must
         agree. Prints one line per manifest block, in manifest order,
           path:start-end JUDGE FINAL shape|-
         FINAL the judge's verdict, or TRUE where the refuter overturned it; shape the
         judge's. Defects refuse as in `flags`.
  tally  the Adherence: line, from the manifest and a verdicts file holding one line per
         manifest block:
           path:start-end  <JUDGE>  <FINAL>  <shape|->
         verdicts TRUE, DRIFTED, HISTORY; FINAL is the verdict after the refuter, TRUE when
         it overturned the judge, and TRUE whenever the judge said TRUE (only non-TRUE
         verdicts are re-checked). <shape> is a slug naming the drift's shape, required
         when FINAL is not TRUE. A block the judge flagged and the refuter overturned is a
         judge false positive. Prints:
           Adherence: <id> <T>/<n> true · <D> drifted · <H> history · <FP> judge FP · pop <f>f/<l>l · seed <s> — shapes: <shape> <path:start>, ...
         (`shapes: none` when every final verdict is TRUE). The rate is a lower bound: a
         drift the judge rules TRUE is never re-checked, so it is never counted.
         `--control NAME` — a run with a mutated judge or refuter — prints the same body
         as `Adherence-control: <id> … · control <NAME>`, which neither `recur` nor the
         trend read (`^Adherence: `) matches, so a control's line is never a window.
  recur  each shape's windows: the `Adherence: <id>` lines in the bodies of commits
         carrying a `Process-Review:` trailer, one window per trailer date, plus
         `--current FILE` (this run's line, not yet committed). One line per shape,
         most windows first:
           <windows>\\t<shape>\\t<dates>\\t<routed|recorded>
         A shape at two or more windows is `routed` — an ordinary review candidate; one
         window is `recorded`.

Exit 2 on a malformed config or rule, a population line that is not `path:line:`, a
population command that fails, a missing mark without --since, a window whose `--repo` is
not a git checkout, agent output with a defect, a verdicts file that does not cover the
manifest exactly, or git failing.
"""
import argparse
import datetime
import json
import pathlib
import random
import re
import subprocess
import sys

DEFAULT_MARK = "process-review-mark"
DEFAULT_BLOCK = r"^\s*(//|/\*|\*)"
VERDICTS = ("TRUE", "DRIFTED", "HISTORY")
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
HIT = re.compile(r"^(?:\./)?([^:]+):(\d+):")
BLOCK_REF = re.compile(r"^(?:\./)?([^:\s]+):(\d+)(?:-(\d+))?$")


def refuse(msg):
    print(f"adherence: {msg}", file=sys.stderr)
    sys.exit(2)


def git(args, cwd, ok=(0,)):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if r.returncode not in ok:
        refuse(f"git {' '.join(args[:2])} failed: {r.stderr.strip()}")
    return r.stdout


def load_config(path):
    if not path.is_file():
        refuse(f"{path}: no config")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        refuse(f"{path}: malformed ({e})")


def pick_rule(cfg, rule_id, cfg_path):
    rules = cfg.get("adherenceRules")
    if not rules:
        refuse(f"{cfg_path}: no adherenceRules")
    if not isinstance(rules, list) or not all(isinstance(r, dict) for r in rules):
        refuse(f"{cfg_path}: adherenceRules must be a list of rule objects")
    for r in rules:
        rid = r.get("id")
        if not isinstance(rid, str) or not SLUG.match(rid):
            refuse(f"{cfg_path}: a rule's id must be a slug, got {rid!r}")
        if not isinstance(r.get("population"), str) or not r["population"].strip():
            refuse(f"{cfg_path}: rule {rid}: population must be a command")
        if not isinstance(r.get("judgePrompt"), str):
            refuse(f"{cfg_path}: rule {rid}: judgePrompt must be a path")
        n = r.get("n")
        if not isinstance(n, int) or isinstance(n, bool) or n < 1:
            refuse(f"{cfg_path}: rule {rid}: n must be a positive integer")
        if r.get("weighting") not in ("window", "uniform"):
            refuse(f"{cfg_path}: rule {rid}: weighting must be window or uniform")
        try:
            re.compile(r.get("block", DEFAULT_BLOCK))
        except (re.error, TypeError) as e:
            refuse(f"{cfg_path}: rule {rid}: block is not a regex ({e})")
    ids = [r["id"] for r in rules]
    if len(set(ids)) != len(ids):
        refuse(f"{cfg_path}: duplicate rule id")
    if rule_id is None:
        if len(rules) > 1:
            refuse(f"{cfg_path}: {len(rules)} rules — name one with --rule ({', '.join(ids)})")
        return rules[0]
    for r in rules:
        if r["id"] == rule_id:
            return r
    refuse(f"{cfg_path}: no rule {rule_id} ({', '.join(ids)})")


def read_lines(root, path, cache):
    if path not in cache:
        f = root / path
        try:
            cache[path] = f.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as e:
            refuse(f"{path}: unreadable at {root} ({e.strerror})")
    return cache[path]


def expand(lines, lineno, block_re):
    """The 1-based inclusive span of the contiguous block around `lineno`."""
    if not 1 <= lineno <= len(lines):
        return None
    i = lineno - 1
    if not block_re.search(lines[i]):
        return lineno, lineno
    start = end = i
    while start > 0 and lines[start - 1].strip() and block_re.search(lines[start - 1]):
        start -= 1
    while end + 1 < len(lines) and lines[end + 1].strip() and block_re.search(lines[end + 1]):
        end += 1
    return start + 1, end + 1


def population(rule, root):
    r = subprocess.run(rule["population"], shell=True, cwd=root, capture_output=True, text=True)
    out = r.stdout.splitlines()
    if r.returncode not in (0, 1) or (r.returncode == 1 and out):
        refuse(f"rule {rule['id']}: population command exited {r.returncode}: "
               f"{r.stderr.strip()[:200]}")
    hits, bad = [], []
    for line in out:
        m = HIT.match(line)
        if not m:
            bad.append(line)
            continue
        hits.append((m.group(1), int(m.group(2))))
    if bad:
        refuse(f"rule {rule['id']}: {len(bad)} population line(s) are not `path:line:` — "
               f"first: {bad[0][:120]!r}")
    return hits


def cmd_draw(a):
    root = pathlib.Path(a.root or git(["rev-parse", "--show-toplevel"], a.repo).strip()).resolve()
    repo = pathlib.Path(a.repo).resolve() if a.repo else root
    cfg_path = pathlib.Path(a.config).resolve() if a.config else root / ".claude" / "threads.json"
    cfg = load_config(cfg_path)
    rule = pick_rule(cfg, a.rule, cfg_path)
    block_re = re.compile(rule.get("block", DEFAULT_BLOCK))
    if a.judge_prompt:
        prompt = pathlib.Path(a.judge_prompt).resolve()
    else:
        prompt = pathlib.Path(rule["judgePrompt"])
        if not prompt.is_absolute():
            prompt = (cfg_path.parent.parent / prompt).resolve()
    if not prompt.is_file():
        refuse(f"rule {rule['id']}: judge prompt {prompt}: no such file"
               + ("" if a.judge_prompt else " (judgePrompt resolves against the repo holding "
                  "the config; pass --judge-prompt PATH to name another)"))
    print(f"adherence: judge prompt {prompt}", file=sys.stderr)
    cache, blocks = {}, []

    if a.blocks:
        seed = "-"
        scope = f"blocks {a.blocks}"
        refs = []
        for raw in pathlib.Path(a.blocks).read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw or raw.startswith("#"):
                continue
            m = BLOCK_REF.match(raw)
            if not m:
                refuse(f"{a.blocks}: not `path:line` or `path:start-end`: {raw!r}")
            refs.append((m.group(1), int(m.group(2))))
        pop_files, pop_lines = len({p for p, _ in refs}), len(refs)
        order = refs
        limit = len(refs)
    else:
        seed = a.seed if a.seed is not None else int(datetime.date.today().strftime("%Y%m%d"))
        hits = population(rule, root)
        if rule["weighting"] == "window":
            since = a.since or cfg.get("markTag") or DEFAULT_MARK
            if subprocess.run(["git", "rev-parse", "--git-dir"], cwd=repo,
                              capture_output=True).returncode != 0:
                refuse(f"{repo}: not a git checkout — a window reads its diff and mark there; "
                       f"pass --repo DIR")
            if subprocess.run(["git", "rev-parse", "--verify", "-q", f"{since}^{{commit}}"],
                              cwd=repo, capture_output=True).returncode != 0:
                refuse(f"no such rev: {since}" + ("" if a.since else " (the mark; pass --since REV)"))
            changed = set(git(["diff", "--name-only", f"{since}..{a.head}"], repo).splitlines())
            hits = [h for h in hits if h[0] in changed]
            date, short = git(["log", "-1", "--format=%cs %h", since], repo).split()
            scope = f"window {since} ({date}, {short})..{a.head}"
        else:
            scope = "uniform"
        pop_files, pop_lines = len({p for p, _ in hits}), len(hits)
        order = sorted(hits)
        random.Random(seed).shuffle(order)
        limit = rule["n"]

    seen = set()
    for path, lineno in order:
        if len(blocks) >= limit:
            break
        span = expand(read_lines(root, path, cache), lineno, block_re)
        if span is None:
            refuse(f"{path}:{lineno}: past the end of the file at {root}")
        if (path, span) in seen:
            continue
        seen.add((path, span))
        blocks.append((path, span))

    print(f"adherence {rule['id']}: {scope} · pop {pop_files}f/{pop_lines}l · "
          f"n {len(blocks)} · seed {seed}")
    for path, (s, e) in blocks:
        print(f"== {path}:{s}-{e}")
        for line in cache[path][s - 1:e]:
            print(line)


HEADER = re.compile(r"^adherence (\S+): .* · pop (\d+)f/(\d+)l · n (\d+) · seed (\S+)$")


def read_manifest(path):
    text = pathlib.Path(path).read_text(encoding="utf-8").splitlines()
    if not text or not HEADER.match(text[0]):
        refuse(f"{path}: first line is not an adherence header")
    rid, pf, pl, n, seed = HEADER.match(text[0]).groups()
    blocks = [l[3:] for l in text[1:] if l.startswith("== ")]
    if len(blocks) != int(n):
        refuse(f"{path}: header says n {n}, found {len(blocks)} blocks")
    return rid, pf, pl, n, seed, blocks


JUDGE = {"who": "judge", "verdicts": VERDICTS, "fields": 3,
         "form": "path:start-end  TRUE|DRIFTED|HISTORY  shape|-  — <reason>",
         "summary": re.compile(r"^ruled (\d+): (\d+) TRUE, (\d+) DRIFTED, (\d+) HISTORY$"),
         "summary_form": "ruled <n>: <T> TRUE, <D> DRIFTED, <H> HISTORY", "prefix": "ruled"}
REFUTER = {"who": "refuter", "verdicts": ("CONFIRMED", "OVERTURNED"), "fields": 2,
           "form": "path:start-end  CONFIRMED|OVERTURNED  — <reason>",
           "summary": re.compile(r"^re-checked (\d+): (\d+) CONFIRMED, (\d+) OVERTURNED$"),
           "summary_form": "re-checked <n>: <C> CONFIRMED, <O> OVERTURNED",
           "prefix": "re-checked"}
KEY = re.compile(r"^\S+:\d+-\d+$")
REASON = re.compile(r"^(.*?)\s+—(?:\s+(.*))?$")


def check_output(path, spec, keys):
    """Hold an agent's output to its one form. Returns ({key: (verdict, shape, line)},
    defects); `keys` are the blocks it must rule, each exactly once."""
    rows, seen, counts, defects, summaries = {}, {}, {}, [], []
    what = "manifest block" if spec is JUDGE else "flagged block"
    for i, raw in enumerate(pathlib.Path(path).read_text(encoding="utf-8").splitlines(), 1):
        s = raw.strip()
        if not s or s.startswith("```"):
            continue
        at = f"line {i} `{s[:100]}`"
        if s.split()[0] == spec["prefix"]:
            m = spec["summary"].match(s)
            if not m:
                defects.append(f"{at}: a summary line reads `{spec['summary_form']}`")
            else:
                summaries.append((at, [int(x) for x in m.groups()]))
            continue
        m = REASON.match(s)
        if not m:
            defects.append(f"{at}: no em dash and reason after the fields — "
                           f"want `{spec['form']}`")
            continue
        fields, reason = m.group(1).split(), (m.group(2) or "").strip()
        probs = []
        if any("·" in f for f in fields):
            probs.append("`·` is not a separator — fields are split by whitespace")
        if len(fields) != spec["fields"]:
            probs.append(f"{len(fields)} field(s) before the em dash, want {spec['fields']}")
        key = fields[0] if fields else ""
        if key in keys:
            if key in seen:
                probs.append(f"`{key}` already ruled at line {seen[key]}")
            else:
                seen[key] = i
        elif key in VERDICTS + REFUTER["verdicts"] or key in ("UPHELD", "REFUTED"):
            probs.append("starts with the verdict — the block key comes first")
            fields = fields[1:2] + fields[:1] + fields[2:]
        elif not KEY.match(key):
            probs.append(f"first field `{key}` is not a block key `path:start-end`")
        else:
            near = [k for k in keys if k.rsplit("/", 1)[-1] == key.rsplit("/", 1)[-1]]
            probs.append(f"`{key}` is not a {what}"
                         + (f" — copy the key exactly: `{near[0]}`" if near else ""))
        verdict = fields[1] if len(fields) > 1 else ""
        if len(fields) == spec["fields"]:
            if verdict not in spec["verdicts"]:
                probs.append(f"verdict `{verdict}` is not one of {', '.join(spec['verdicts'])}")
            else:
                counts[verdict] = counts.get(verdict, 0) + 1
        shape = fields[2] if spec is JUDGE and len(fields) == 3 else "-"
        if spec is JUDGE and verdict in VERDICTS and len(fields) == 3:
            if verdict == "TRUE" and shape != "-":
                probs.append(f"a TRUE verdict takes `-` as its shape, got `{shape}`")
            if verdict != "TRUE" and not SLUG.match(shape):
                probs.append(f"a {verdict} verdict names its shape as a kebab-case slug, "
                             f"got `{shape}`")
        if not reason:
            probs.append("empty reason — every line cites what decides it")
        if probs:
            defects.append(f"{at}: " + "; ".join(probs) + f" — want `{spec['form']}`")
        else:
            rows[key] = (verdict, shape, s)
    for k in keys:
        if k not in seen:
            defects.append(f"missing `{k}`: no line rules this {what}")
    if len(summaries) > 1:
        defects.append(f"{len(summaries)} summary lines — at most one")
    elif summaries:
        at, (n, *parts) = summaries[0]
        want = [counts.get(v, 0) for v in spec["verdicts"]]
        if n != sum(want) or parts != want:
            read = ", ".join(f"{c} {v}" for c, v in zip(want, spec["verdicts"]))
            defects.append(f"{at}: disagrees with the lines, which read "
                           f"`{spec['prefix']} {sum(want)}: {read}`")
    return rows, defects


def refuse_defects(mode, path, spec, defects):
    each = "manifest" if spec is JUDGE else "flagged"
    print(f"adherence {mode}: {path}: the {spec['who']}'s output refused, {len(defects)} "
          f"defect(s). It is machine-read: one line per {each} block, exactly "
          f"`{spec['form']}`, then optionally `{spec['summary_form']}`.", file=sys.stderr)
    for d in defects:
        print(d, file=sys.stderr)
    sys.exit(2)


def cmd_flags(a):
    blocks = read_manifest(a.manifest)[5]
    rows, defects = check_output(a.judge_out, JUDGE, blocks)
    if defects:
        refuse_defects("flags", a.judge_out, JUDGE, defects)
    for b in blocks:
        if rows[b][0] != "TRUE":
            print(rows[b][2])


def cmd_verdicts(a):
    blocks = read_manifest(a.manifest)[5]
    rows, defects = check_output(a.judge_out, JUDGE, blocks)
    if defects:
        refuse_defects("verdicts", a.judge_out, JUDGE, defects)
    flagged = [b for b in blocks if rows[b][0] != "TRUE"]
    if flagged and not a.refuter_out:
        refuse(f"{len(flagged)} non-TRUE verdict(s) and no REFUTER_OUT — every flag is re-checked")
    if not flagged and a.refuter_out:
        refuse("no non-TRUE verdicts, so nothing was re-checked — drop REFUTER_OUT")
    refuted = {}
    if flagged:
        refuted, defects = check_output(a.refuter_out, REFUTER, flagged)
        if defects:
            refuse_defects("verdicts", a.refuter_out, REFUTER, defects)
    for b in blocks:
        judge, shape, _ = rows[b]
        final = "TRUE" if judge == "TRUE" or refuted[b][0] == "OVERTURNED" else judge
        print(f"{b} {judge} {final} {shape}")


def cmd_tally(a):
    rid, pf, pl, n, seed, blocks = read_manifest(a.manifest)
    rows = {}
    for i, raw in enumerate(pathlib.Path(a.verdicts).read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip() or raw.startswith("#"):
            continue
        parts = raw.split()
        if len(parts) != 4:
            refuse(f"{a.verdicts}:{i}: want `block JUDGE FINAL shape|-`, got {raw!r}")
        block, judge, final, shape = parts
        if judge not in VERDICTS or final not in VERDICTS:
            refuse(f"{a.verdicts}:{i}: verdicts are {', '.join(VERDICTS)}")
        if judge == "TRUE" and final != "TRUE":
            refuse(f"{a.verdicts}:{i}: a TRUE verdict is never re-checked, so it stays TRUE")
        if final != "TRUE" and not SLUG.match(shape):
            refuse(f"{a.verdicts}:{i}: a {final} verdict names its shape as a slug")
        if block in rows:
            refuse(f"{a.verdicts}:{i}: {block} ruled twice")
        rows[block] = (judge, final, shape)
    missing = [b for b in blocks if b not in rows]
    extra = [b for b in rows if b not in blocks]
    if missing or extra:
        refuse(f"{a.verdicts}: does not cover the manifest — "
               f"{len(missing)} unruled ({', '.join(missing[:3])}), "
               f"{len(extra)} not drawn ({', '.join(extra[:3])})")
    count = {v: sum(1 for b in blocks if rows[b][1] == v) for v in VERDICTS}
    fp = sum(1 for b in blocks if rows[b][0] != "TRUE" and rows[b][1] == "TRUE")
    shapes = [f"{rows[b][2]} {b.rsplit('-', 1)[0]}" for b in blocks if rows[b][1] != "TRUE"]
    if a.control is not None and not re.match(r"^\S+$", a.control):
        refuse(f"--control names the control in one word, got {a.control!r}")
    print(f"{'Adherence-control' if a.control else 'Adherence'}: {rid} {count['TRUE']}/{n} "
          f"true · {count['DRIFTED']} drifted · {count['HISTORY']} history · {fp} judge FP · "
          f"pop {pf}f/{pl}l · seed {seed} — shapes: {', '.join(shapes) or 'none'}"
          + (f" · control {a.control}" if a.control else ""))


LINE = re.compile(r"^Adherence: (\S+) .* — shapes: (.*)$")


def shapes_of(line):
    m = LINE.match(line.strip())
    if not m or m.group(2).strip() == "none":
        return m.group(1) if m else None, []
    return m.group(1), [s.strip().split()[0] for s in m.group(2).split(",") if s.strip()]


def cmd_recur(a):
    root = pathlib.Path(a.root or git(["rev-parse", "--show-toplevel"], None).strip()).resolve()
    log = git(["log", a.head, "--grep=^Process-Review: ",
               "--format=%x00%(trailers:key=Process-Review,valueonly,separator=%x2c)%x01%b"], root)
    windows = {}
    for rec in log.split("\x00")[1:]:
        date, _, body = rec.partition("\x01")
        date = date.strip().split(",")[0].strip() or "?"
        for line in body.splitlines():
            rid, shapes = shapes_of(line)
            if rid and (a.rule is None or rid == a.rule):
                for s in shapes:
                    windows.setdefault(s, set()).add(date)
    if a.current:
        for line in pathlib.Path(a.current).read_text(encoding="utf-8").splitlines():
            rid, shapes = shapes_of(line)
            if rid and (a.rule is None or rid == a.rule):
                for s in shapes:
                    windows.setdefault(s, set()).add("current")
    if not windows:
        print("adherence recur: no shapes recorded")
        return
    for s, dates in sorted(windows.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        print(f"{len(dates)}\t{s}\t{','.join(sorted(dates))}\t"
              f"{'routed' if len(dates) >= 2 else 'recorded'}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    d = sub.add_parser("draw")
    d.add_argument("--rule", default=None)
    d.add_argument("--seed", type=int, default=None)
    d.add_argument("--since", default=None, metavar="REV", help="window start (default: the mark)")
    d.add_argument("--head", default="HEAD", metavar="REV", help="window end (default: HEAD)")
    d.add_argument("--blocks", default=None, metavar="FILE", help="a fixed block list, no draw")
    d.add_argument("--config", default=None, metavar="PATH",
                   help="threads.json (default: <root>/.claude/threads.json)")
    d.add_argument("--root", default=None, help="the tree to read (default: git top level)")
    d.add_argument("--repo", default=None, metavar="DIR",
                   help="the git checkout the window's diff and mark are read from "
                        "(default: --root)")
    d.add_argument("--judge-prompt", default=None, metavar="PATH",
                   help="replaces the rule's judgePrompt; checked to exist")
    f = sub.add_parser("flags")
    f.add_argument("manifest")
    f.add_argument("judge_out")
    v = sub.add_parser("verdicts")
    v.add_argument("manifest")
    v.add_argument("judge_out")
    v.add_argument("refuter_out", nargs="?", default=None)
    t = sub.add_parser("tally")
    t.add_argument("manifest")
    t.add_argument("verdicts")
    t.add_argument("--control", default=None, metavar="NAME",
                   help="a control run: print Adherence-control:, never a window")
    r = sub.add_parser("recur")
    r.add_argument("--rule", default=None)
    r.add_argument("--current", default=None, metavar="FILE", help="this run's Adherence: line")
    r.add_argument("--head", default="HEAD", metavar="REV")
    r.add_argument("--root", default=None)
    a = ap.parse_args()
    {"draw": cmd_draw, "flags": cmd_flags, "verdicts": cmd_verdicts, "tally": cmd_tally,
     "recur": cmd_recur}[a.mode](a)


if __name__ == "__main__":
    main()
