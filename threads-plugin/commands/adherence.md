---
description: Sample whether a declared prose rule holds — a seeded draw of blocks, one fresh-context judge, one refuter over every non-TRUE verdict, and one Adherence line. Runs as a phase of /threads:process-review; standalone for a baseline window or a calibration set, writing nothing to the repo.
argument-hint: "[<rule-id>] [--since REV] [--head REV] [--seed S] [--blocks FILE --root DIR] [--repo DIR] [--config PATH] [--judge-prompt PATH] [--refuter-mandate PATH]"
allowed-tools: Bash, Read, Grep, Glob, Write, Agent, SendMessage
---

# /threads:adherence — sample a declared rule

A lint proves itself at its own gate. A prose rule an agent is supposed to apply — *a code
comment states only what the code in view makes true* — has no gate, and nothing measures
whether it holds; the review sees its failures only when a retro happens to notice one.
This command measures it: a seeded draw from the rule's population, judged cold, the
flagged verdicts re-checked cold, and one line of counts a later run can trend.

`/threads:process-review` runs this procedure as its step 0d, once per rule, every run.
Invoked directly it is the same procedure with nothing landed: no commit, no log line, no
tag moved — for a **baseline** over one window, and for a **calibration** over a fixed
block list in a checkout pinned to a commit.

## Config — `adherenceRules` in `.claude/threads.json`

```json
"adherenceRules": [
  {
    "id": "comment-truth",
    "population": "rg -n --type swift '^\\s*///?\\s*\\S.{30,}' Sources",
    "judgePrompt": "Plans/templates/adherence-comment-truth.md",
    "n": 20,
    "weighting": "window"
  }
]
```

- `id` — a slug; the `Adherence:` line names it.
- `population` — a shell command run at the repo root whose every output line is a
  `path:line:` hit. It is the **whole-tree** population: the window is the weighting's
  job, so the command never runs over an empty or deleted-file window, and `uniform` stays
  a one-word change.
- `judgePrompt` — the adopter's prompt, from the repo holding the config: the rule, what each verdict means
  for it, any shape checklist with slugs — examples to look for first, never the whole
  space, since a checklist-bounded judge misses the drift no one has named yet. The judge
  reads it first and it wins over the judge's own brief.
- `n` — distinct blocks per draw. A population with fewer blocks is sampled whole.
- `weighting` — `window` (only hits in files changed over `<markTag>..<head>`: the rate
  of what the window's review let through) or `uniform` (every hit: the stock).
- `block` — optional regex; a line matching it joins the drawn line's block, a blank or
  non-matching line ends it. Default `^\s*(//|/\*|\*)`; a `#`-comment language sets its own.

`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/adherence.py --help` is the script's contract.

## Arguments

- `<rule-id>` — required when more than one rule is declared.
- `--since REV` / `--head REV` — the window, for a `window` rule (default: the mark to
  `HEAD`). The blocks are read from the working tree, so the checkout sits at `--head`.
- `--seed S` — default today as `YYYYMMDD`; a recorded seed reproduces a draw.
- `--blocks FILE --root DIR` — calibration: a fixed list (`path:line` or
  `path:start-end`, one per line, each expanded to its block) replaces the population and
  the draw, and the judge and refuter read the tree at `DIR`. Pin `DIR` without touching
  the adopter's worktrees: `git -C <repo> archive <commit> | tar -x -C <DIR>`.
- `--repo DIR` — the git checkout a `window` rule's diff and mark are read from, when
  `--root` is not one (a pinned tree); the files are still read at `--root`. Default
  `--root`.
- `--config PATH` — the `threads.json` to read the rule from, when `--root` is a pinned
  tree whose own config predates the rule.
- `--judge-prompt PATH` — replaces the rule's `judgePrompt` for this run.
- `--refuter-mandate PATH` — handed to the refuter as its mandate file, replacing its
  *show-it-true* paragraph. The two overrides exist for the calibration's mutation
  controls (a judge told to rule every block TRUE; a refuter told to confirm every drift);
  a run using either says so on its first line of output and tallies with
  `--control <the override file's stem>`, so its line reads `Adherence-control:`, which
  neither `recur` nor the trend read counts.

## Procedure

Work in a scratch directory outside the repo; nothing here writes to the tree. The
agents' replies are machine-read: write each to its file exactly as returned — never
edited, completed, or assembled by hand — and let the script check it.

1. **Draw.** `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/adherence.py draw [--rule ID] [--seed S]
   [--since REV] [--head REV] [--blocks FILE] [--config PATH] [--root DIR] [--repo DIR]
   [--judge-prompt PATH] > <scratch>/manifest.txt`. Its stderr names the judge prompt it
   checked exists — the path steps 2 and 3 hand the agents.
   A refusal (a population line that is not `path:line:`, a missing mark, a malformed
   rule, a judge prompt not on disk) is reported as it reads and the rule is skipped — never re-run with a hand-edited
   population. A manifest at `n 0` is a window with nothing to sample: report it and skip
   2–4.
2. **Judge — once, fresh context.** Spawn `threads:adherence-judge` with the judge prompt
   path, the manifest path, and the root, all absolute. One judge rules every block; a
   second judge per block would trade the one context that sees the draw whole for
   nothing. Write its reply to `<scratch>/judge.txt`, then `adherence.py flags <manifest>
   <scratch>/judge.txt > <scratch>/flags.txt`. A refusal lists every defect: send that
   text to the **same** judge (SendMessage) asking for its whole output again in the exact
   form, overwrite `judge.txt`, and re-run `flags`. A second refusal fails the rule's run:
   report the refusal and record no line.
3. **Refute — once, fresh context, the flags only.** `flags.txt` empty → skip. Otherwise
   spawn `threads:adherence-refuter` with the judge prompt path, the root, the mandate
   file when one was given, and `flags.txt`'s lines verbatim; write its reply to
   `<scratch>/refuter.txt`. The judge's TRUE verdicts are never re-checked, which is why
   the rate is a **lower bound**: a drift the judge rules TRUE is never counted.
4. **Tally.** `adherence.py verdicts <manifest> <scratch>/judge.txt [<scratch>/refuter.txt]
   > <scratch>/verdicts.txt` — the refuter's file exactly when step 3 ran. A refusal of the
   refuter's output takes the same one retry with the same refuter; a second fails the
   rule's run. Then `adherence.py tally <manifest> <scratch>/verdicts.txt` (`--control
   <name>` for a control run). It prints the line:

   ```
   Adherence: <id> <T>/<n> true · <D> drifted · <H> history · <FP> judge FP · pop <f>f/<l>l · seed <s> — shapes: <shape> <path:line>, …
   ```

   A block the judge flagged and the refuter overturned counts TRUE and once in `judge FP`.
5. **Recurrence.** `adherence.py recur --rule <id> --current <the line in a file>` counts
   each shape's windows across the `Adherence:` lines of past review commits (read by the
   `Process-Review:` trailer, so a commit merely quoting the line is not a window). A shape
   at two or more windows is `routed`: an ordinary review candidate — a lint class where a
   pattern can catch it at a measured false-positive rate, a line in a review prompt
   otherwise. A shape in one window is `recorded` and nothing more.

## Output

- **The line**, first, as `tally` printed it — or the refusal, or `n 0`.
- **Per block**: `path:start-end`, the judge's verdict and shape, the final verdict, and
  the citation that decided it — every block, TRUE included, so a reader can audit the
  judge's reading and not only its flags.
- **Recurrence**: `recur`'s routed shapes, then its recorded ones.
- Standalone: one closing sentence saying nothing was committed and the mark did not move.

**What the adopter does with a verified drift** — fix it in the run, file it, or only
record it — is the adopter's rule, stated in its own process-review extensions; this
command measures and reports.
