<!-- audience: human -->
# Changelog

Notable changes to this marketplace's plugins (**threads**, **slices**, **guards**), newest
first per plugin. Versions track each plugin's `version` in its
`.claude-plugin/plugin.json` and in
[`marketplace.json`](.claude-plugin/marketplace.json); each release is tagged
`<plugin>--v<version>`.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## threads [0.14.0] — 2026-09-09

### Contract

- **`invariantDocs` is the core, not the list of everything true.** The field now names the docs that state the repo's authority order and the review's own contract — read whole at step 0a, every run, and short by construction. A domain doc is a *keyed read*: opened whole at step 6 only when a *recurred* key or a *fired* ledger signal names it (`retro-log.py view --recurred --since <date> --docs` derives the list from the log, kept to `processDocs` members), and read by the placer again for the edit; a file the window's churn names is read as its diff or blamed section, never whole, and the economics block reports the keyed set's words so the bound is visible. Measured on the reference adopter: 26 docs / 75,849 prose words read at step 0, 8 docs / 26,716 words bore on any ruling; the whole since-mark keyed set would have been 11 docs / 44,678 words, twice the trimmed core, which is why the bound is recurred-and-fired only. Adopter-side edit: trim `invariantDocs` to the core (the reference adopter's went from 26 entries to 6, 21,534 words); nothing else moves.
- **Every commit the review lands carries the trailer `Process-Review: <date>`** — candidate landings, log and ledger bookkeeping, the mark's own commit. `scripts/marker-stream.py` classifies the marker stream into *organic* (no trailer, touched something beyond `retroLogPath` / `ledgerPath` / `capabilityEvidencePath`), *review* (trailered), and *bookkeeping* (log/ledger-only); the trigger, step 1's ranking, and the tally's headline read the organic set only. Measured on the reference adopter's last window: 46 markers, 8 organic — the review was ripe on its own output every morning. Adopter-side edit: none; commits landed before this carry no trailer and stay organic in the history. The retro's ripeness nudge reads the same classification and calls a review *ripe* on a key recurred since the mark or an organic bar, never on pending captures alone.
- **A Live ledger entry may be dormant**: one `wake: <condition>` line (a key occurrence, a path touched, a date), and the entry is re-measured — its `last checked` rewritten — only on a run where the wake holds; other runs read the wake line and nothing else of it. The `guards` `review-ledger` check's docstring names the line; its caps are unchanged. Adopter-side edit: none required; a watch that has not fired in several windows is the candidate.
- **`/threads:retro` no longer writes `NOTED`.** A positive is reported and never appended: nothing downstream reads it, since the review ranks by recurrence and a `NOTED` key closes at write. The grammar keeps the token for existing entries. Adopter-side edit: none.

### Added

- **`scripts/marker-stream.py [list|count|files] [--since REV] [--head REV] [--all] [--pattern BRE]`** — the marker stream since the mark, classified; `files` ranks the organic commits per file and counts the files at `trigger.concentration`; `--all` is the tally; `--pattern` converts the config's BRE (bare parens literal) so the bootstrap proof and the script agree. `test.sh` proves the three classes, a body-only mention not counting, the file ranking, `--all`, `--since`, `--pattern`, and a missing mark refusing.
- **`retro-log.py view --docs`** — the files the shown keys name in their detail (`Placement:`, `LANDED … — <where>`, `FILED <stub>`), `<keys naming it>\t<path>`, most-named first; composes with every filter. `test.sh` proves it under `--recurred` and whole.
- **The review closes with a review-economics block**, questions to the maintainer: core docs read against those that bore, keyed docs likewise, markers organic / review / bookkeeping, keys read against keys recurred, the run's own landing errors, its size where the harness shows it, and *what should the next run stop reading?* An `Economics:` line rides the marker commit body beside `Tally:`. The review's own misses go there and into the commit body, never as keys into the log it maintains.
- **`/threads:retro` has a capture bar**: a finding is appended when its cost was spent, when it matches a key already in the log, or when it is severe on its face; a nil-cost unmatched finding is listed *below the bar* with the reason and not appended (the user can override). Cost is a required field of every finding, stated in the unit it was spent in, and *nil* is a valid value. Measured on the reference adopter: 219 keys, 97 live, 3 recurred, 37 positives, 34 occurrence lines appended on one day.

### Changed

- **A landing is a text match, under every tier.** The placer returns the existing text as it sits on disk — `path:first-last`, verbatim, wrapped as the file wraps it — and the landing step asserts the type of any value it writes into a data literal (`[0-9]+` for a count) before the write. Both were the landing errors the reference adopter measured under `apply-on-approval` (an anchor quoted unwrapped; a parsed word written into three numeric budget rows and pushed); both were clean-judgment errors, and both are held at the write rather than by an executor sub-agent between judgment and landing. The workshop's execution-sub-agent deferral is re-deferred on that narrower signal.
- **`land-process-commit.py`'s dirty-tree refusal** says how many files, that the rebase after the push is what needs the clean tree, that a commit the hook just refused has left its changes here with no commit to land yet, and that `--no-rebase` lands the sha and leaves the branch alone.
- **`/threads:process-review` step 1 and the tally read `marker-stream.py`**, never a hand-rolled `git log | grep`; the silent-death check rules out the measurement with `count --all`.

## threads [0.13.0] — 2026-09-08

### Added

- **`scripts/land-process-commit.py <sha>`** — lands one marker commit direct on the default branch from a slice branch: fetch; `git worktree add --detach` at `origin/<default>`; `git cherry-pick --no-commit` then `git commit -C <sha>`, so the adopter's own pre-commit hook judges the commit where a plain cherry-pick runs no hook; a patch-id check against the original; push; the sha re-read from the remote is the only line on stdout, so "push before citing a sha" is enforced by the tool rather than remembered; the worktree removed; the slice branch rebased so the duplicate drops. A cherry-pick conflict, a red hook, a patch that came out different, or a refused push exits 1 with nothing pushed; a rebase that fails after the push exits 3 with the sha already printed. Default branch from `--branch`, `defaultBranch` in `.claude/threads.json`, or `refs/remotes/<remote>/HEAD`. `test.sh` proves the landing through a hook, the printed sha against `ls-remote`, the dropped duplicate, and each failure leaving no worktree and no push. `/threads:process-review` §On completion names it under land-first-cite-second.

## threads [0.12.0] — 2026-09-08

### Contract

- **The retro log's header points at the grammar and never copies it.** Bootstrap seeds a header saying the grammar is the threads plugin's `retro-log.py` docstring and that `--help` prints it, then `## Entries`. A copy in the header was a second source nothing refreshed: `compact` keeps the header verbatim and retro never compacts, so every adopter's copy read as current while listing the tokens of a version ago. The appending agent reads the grammar from `/threads:retro`'s own text, which ships with the script. Adopter-side edit: replace the grammar block in the log's header with the pointer sentence; the entries are untouched.

## threads [0.11.1] — 2026-09-08

### Fixed

- **`apply-mechanical` lands on the guards, never on class alone.** Six guards, all required: docs in `processDocs` only (a companion script, config, or budget edit holds the candidate); additive only (a deletion, rewrite, or consolidation of an existing rule sentence holds); the key live and never `LANDED`, `REOPENED`, or `FILED`; the target section named in no Live ledger entry; a multi-file candidate lands whole or holds whole; nothing in `invariantDocs`, nothing still referenced deleted, no `add (unconsolidated)`. Measured against one adopter's mechanical set, five landed candidates would have slipped the 0.11.0 guard set. The autonomous landing writes its `LANDED` lines under land-first-cite-second, and the ratchet offer names what the tier will actually reach in that repo.

## threads [0.11.0] — 2026-09-08

### Contract

- **`HELD` is keyed on the review's date, not its marker sha** — `HELD <date> — <letter, class, proposal>`. The marker commit is the commit that carries the HELD lines, so its sha cannot be cited by them; the date names it (`git log --grep <markerPattern> --since/--until`). The view shows each held key's date and age in days. Adopter-side edit: a doc stating the grammar as `HELD <review-sha>` says `HELD <date>`; existing sha-keyed lines stay valid (the ref is any token) and simply carry no age.
- **`ADJUDICATED <date> — <ruling>` is the review's annotation on a key** — a re-rank, a count-only ruling at a key whose rule is present, a build trigger on a filed stub, a withdrawn re-rank. Its own entry under the key line, one physical line; it changes neither the key's state nor its occurrence count, `compact` keeps it (on a closed key too, after the closing status), and `view --key` shows it. Before this the only vehicles were an occurrence (which counts) and a status (which moves state), so rulings were written as continuation prose, where the size cap counted them and a status-only last block read them as an unknown status. Adopter-side edit: a ruling written as continuation prose inside an occurrence is moved to its own `ADJUDICATED` entry — the review does it as its mutation, with `compact` after. The migration is lossy for a key that had already closed: a compaction before this release reduced it to its status line, and the prose ruling went with the occurrence it sat in; the commit body of that review still has it.

### Added

- **`view` filters are the review's reads** — `--held` (unanswered proposals, with age), `--recurred` (two or more occurrences, or an occurrence after a closing status: the shape back with its rule present ranks with the repeats), `--since <date>` (keys with an occurrence, status, or annotation on or after), `--live` (no closed section). They compose; the summary line counts the whole log and says how many keys the filter shows; without `--keys` a filtered view carries detail, so the recurred set's bodies are one read. `--key` repeats. `/threads:process-review` step 0b names these reads in order and reserves bare `--keys` for a small log — at two hundred keys the whole listing exceeds one tool result.
- **Pre-flight: one review at a time.** The review fetches and records the mark and the log blob **on the remote's default branch** before reading (a peer lands there while the local head sits untouched), identifies a peer session by working directory and branch (never a worktree name, which another repo's session can carry) where the harness exposes a listing, and re-reads both facts immediately before its first write; either moved → rebase, run the gate on the rebased tree, re-read, then write; refuse only on a conflict or a red gate.
- **Land first, cite second.** `LANDED` shas and any sha the ledger cites are written after the landing commits are pushed, each read back from the remote by subject in a commit of its own, since the landing rebase rewrites a branch-side sha.
- **The output opens with a decision block for the maintainer, and nothing sits above it.** A four-column table — Letter · Decision (the artifact and the motion, never the retro key) · Recommend (approve / retire / split / fold) · Why (one or two sentences resting on what the run measured, reversibility stated when it bears) — one row per candidate that genuinely needs a judgment; then one sentence *Mechanical, land on your word:* with the letters; then one line naming what happens next if answered as recommended. Every row's premise is re-measured against the default branch before it is written. The record (pattern → evidence → proposal, placements, tier, tally) follows for the commit body and the next run. Every candidate carries a class — `trim`, `amend`, `rule`, `carve`, `config`, `tooling`, `motion` — and `trim`/`amend` are mechanical by default; the class groups, it does not gate. The record (pattern → evidence → proposal) still follows, for the commit body and the next run.
- **`applyMode: apply-mechanical`** — the third tier, offered once after the maintainer has approved the mechanical line as a batch in two or more reviews and recorded like the others. Under it a run the maintainer is not answering lands the `trim` and `amend` candidates itself, each its own marker commit, landed first and cited second, and reports them as landed; every other class is still `HELD`, an `invariantDocs` file is never edited unanswered, and an `add (unconsolidated)` placement is a row whatever its class. The approval queue was measured as the bottleneck; this is the part of it that never needed a person.
- **Bootstrap asks for `capabilityEvidencePath`** where inspection finds tooling the repo builds and uses (`scripts/`, hooks, checks, a plugin dir); a later run in such a repo with the field unset asks once, and `null` records a decline. A store unset for an adopter's whole life leaves the funnel doc-shaped with no one ever asked.

### Changed

- **The ledger's 12-line cap is stated per entry** in the command text, as the check already applied it.
- `test.sh` proves the annotation's transparency and compaction, the held age, and each filter.

## threads [0.10.0] — 2026-09-08

### Changed

- **`/threads:retro` fixes a defect in this session's own artifact instead of offering to** (§4b). When the audit's evidence is a `file:line` in something the session wrote or landed, the fix needs no decision the user has not taken, and the landing's gate can check it, the retro names the fix, applies it, lands it through the lane the fix qualifies for with no marker, and records it as a `Fixed: <artifact> — <sha>` continuation line inside the lesson's occurrence — never a `LANDED` status, which would close the lesson's key with its placement unapplied. The fix and its landing precede the log append so the sha exists; the line counts against the eight. Provenance is per statement, a choice owned by the artifact's next reader is recorded rather than presented, a file an open branch moves is a finding, and the size gate applies to process proposals only. `test.sh` proves a `Fixed:` continuation line passes the `retro-log` check and leaves the key live. "Don't pivot the retro" and "capture is the default" now name the feature work and the process finding they were written for. The auditor brief tells a file-evidenced finding apart from a moment-evidenced one.
- **A status line is one physical line, however long** — the grammar block in the command and the script header say so and show a long `NOTED` unwrapped; the `retro-log` check already refused a wrapped one.
- **`extract-record.py` keeps the head and tail of a long user turn**, as it did for agent turns, marks every elision, and heads the record with a note saying so; the auditor brief says an elided turn cannot ground a negative attribution finding.

### Fixed

- **`compact` kept a status block inside an occurrence entry**, merging every block of a key under one key line, which the grammar reads as continuation prose and the `retro-log` check refuses; a status block now keeps its own key line, and compacting a canonical log changes nothing.
- **`compact` dropped occurrences appended after a closing status.** A key's state is now its last block: an occurrence after `LANDED` reopens the key, `view` marks it `recurred after LANDED`, and compaction keeps every block.
- **`test.sh`** proves both shapes, idempotence, and the view-warns/compact-refuses split; the workshop's pre-land runs every plugin's suite.

## threads [0.9.0] — 2026-09-07

### Contract

- **`FILED <ref>` status** — a finding routed to a stub or plan. The key stays live in the view (a further occurrence counts against the stub) where `RETIRED` would have hidden it. Adopter-side edit: a line that meant "filed, count against it" takes `FILED`, not `RETIRED`.
- **`NOTED <date>` status** — a positive record, closed at write and never counted; `/threads:retro` writes a what-worked finding as key + `NOTED` and no occurrence. Adopter-side edit: append `NOTED` under existing record-only keys so `compact` closes them.
- **An occurrence is at most eight lines** — the moment, the cost, the placement; `/threads:retro` writes to that shape and the `guards` `retro-log-size` check holds it, at whatever rung the adopter sets. Adopter-side edit: none required; existing entries over the cap show as findings at `warn`.
- **Every append is a whole entry beginning with a key line** — never continuation lines onto an entry already in the file; under union merge those land under another session's block. A union merge runs no hook, so the adopter's landing step runs the `guards` checks on the merged tree before the push (the reference adopter's land-docs does). Adopter-side edit: add that run to the landing step.
- **`HELD <review-sha>` status** — a proposal the review made and nobody approved: its own live state, listed first in the view, reported first by the next run, then `LANDED` or `RETIRED`. A held candidate keyed to nothing goes in the ledger's Live with *promoting signal: approval*. An autonomous run's output reaches the next run through the view, never only through a commit body.

## threads [0.8.1] — 2026-09-07

### Fixed

- **`retro-log.py view` reads a log that breaks the grammar**, naming each violation on stderr and rendering the rest, so `/threads:retro` still hands the placer the key list in an adopter that has not yet repaired its log; `compact` alone refuses.

## threads [0.8.0] — 2026-09-07

### Contract

- **The retro log is an append-only stream in a fixed grammar, read through a view.** A key line (`<class>/<shape>`), `YYYY-MM-DD | <source> | <text>` occurrence lines with free continuations, and one-line status lines `LANDED | RETIRED | UPSTREAM | REOPENED <ref> — <text>`; entries under `## Entries` with nothing after. A state change is an appended status line — a finding applied in-session is the key plus `LANDED <sha>` — and a recurrence is an appended occurrence under the same key; nothing edits an existing line, which is what makes `merge=union` correct. New `scripts/retro-log.py`: `view [--keys | --key K]` derives each key's state and occurrence count; `compact` is the review's only rewrite (one block per key, closed keys to their status line; refuses, naming the lines, on anything the grammar cannot read). Adopter-side edit: bring the log to the grammar and run `compact`; set `<retroLogPath> merge=union` in `.gitattributes` if not already set.
- **The ledger holds current state.** Three sections — Live, Falsifications, Resolved. A Live entry carries what, why, the promoting signal, and one `last checked: <date> — <state>` line rewritten in place each run, at most 12 lines; Resolved is a pointer at most 3 lines; a run's narrative goes in its own marker commit body. Adopter-side edit: cut per-window sections into git history and fold dated window lines into last-checked lines.

### Changed

- **`/threads:retro`** hands the placer the key list from `view --keys`; the placer matches against it and greps the log only for a hit's detail. The escape hatch records a landing as a status line. The pending count greps the grammar's key shape.
- **`/threads:process-review`** reads the log through the view, re-keys, compacts, then counts; maintains the log by appending status lines and running `compact`; bootstrap's header states the grammar and proposes `merge=union`. Both `guards` checks named as the gates.

## guards [Unreleased]

### Changed

- **`review-ledger`** names the optional `wake: <condition>` line a dormant Live entry carries (threads: re-measured only on a run where the wake holds). The check's caps and findings are unchanged; the line counts toward the entry's 12.

## guards [0.7.0] — 2026-09-08

### Added

- **`plan-sweeps`** — every single-line code span beginning `rg ` in a plan is split to argv without a shell and run in the checkout with a 20-second bound; `rg` exiting 2 (a malformed regex, a path it cannot open) or not finishing is a finding, exit 0 and 1 are both sane. A span the shell would act on — `;`, `|`, `&`, `$`, a redirect, a glob character outside quotes, `$` or a backtick inside double quotes — or one carrying `--pre`, `--pre-glob`, or `--search-zip` is skipped, never run, and counted on stderr; inside single quotes nothing expands, so a regex alternation runs. Measured on one adopter's three drafted plans: 40 sweeps, 30 run, 10 skipped, 0 findings; its process docs carry two illustrative `rg -E` / `rg -r` fragments, which the allow marker covers. `paths` is required.
- **`referents`** — a name a code span carries that nothing answers to: a script under `scriptDirs` (default `scripts`) the index does not hold, a `/command` with no `<commandDirs>/<name>.md` (default `.claude/commands`) and no `knownCommands` match (an entry ending `:` is a prefix), a word beginning with an `envPrefixes` entry that occurs in no non-markdown indexed file (`git grep --cached` in the checkout). Spans only, so prose `/tmp` never matches; `<…>` and ellipsis words are placeholders. Measured on one adopter: two illustrative referents (the allow marker) and one real drift, a `/plan` that names no command, twice. Ships at `warn` by recommendation; `paths` is required. The `gh` label class was measured at zero population and would put a network call in a pre-commit hook, so it is not built.
- **A check's own keys in `.claude/guards.json`** — a check reads what it needs beyond a scope from its own entry, beside `rung`; the runner's contract is unchanged.
- **`<!-- guards-allow: <id> -->`** on a line exempts that line from the check with that id, for a doc that shows a malformed sweep or names an illustrative script on purpose. Per line, per check.
- **The git adapter exports `GUARDS_TREE`**, the checkout's top level, beside `GUARDS_INDEX`, so a check can run something in the checkout the export does not hold; `test.sh` proves a sweep runs there and a referent resolves by the index.

## guards [0.6.0] — 2026-09-08

### Changed

- **`retro-log`** accepts the `ADJUDICATED <date> — <text>` annotation (threads: the review's ruling on a key), one line and its own entry like a status; one inside an occurrence entry is refused as a status there is. The unknown-status message lists it.
- **`review-ledger`** states its Live and Resolved caps as per entry; the check always applied them so.

## guards [0.5.0] — 2026-09-08

### Added

- **`"export"` in `.claude/guards.json`** — git pathspecs the git adapter exports before judging, instead of the whole index. Absent, unchanged. An export that drops a config the gate steers by — `.claude/guards.json`, or `.claude/threads.json` where the logs live — refuses with exit 2 before any check runs, naming the file. Past a missing config a check judges nothing and says nothing, so an export is verified rather than trusted.

### Changed

- **`run.py` handed a root with no `.claude/guards.json`** says so on stderr and still exits 0, so a run that judged nothing never reads as one that passed.
- **`test.sh` proves the git adapter**, not only the checks and the runner: inert without a config, a narrow export that judges a clean tree and still catches a finding, an export dropping either config refusing, and an export dropping a file in a check's scope refusing by name. The scope helper every check carries is held byte-identical across the five, since only one copy is exercised. A linked-worktree case covers what a plain `git init` fixture cannot: the adapter judging that worktree's own index rather than the primary's, and the install line's relative `core.hooksPath` running the hook the worktree carries. In a one-level repo a wrong path still resolves, so the case has to be a real worktree to pin either. A git-checkout fixture pins the `git ls-files` half of glob resolution, which the walk-branch cases cannot see; `says` asserts the exit code alongside the message; the suite neutralizes the ambient git config, under which a fixture could stage nothing and assert exit 0 over an empty tree; and each fix above carries a case that fails when the fix is reverted.
- **`paths` takes a glob**, matched the way `exclude` already is — Python `fnmatch` over the root-relative path, so `*` crosses `/` as in a git pathspec. A process-doc set is `["CLAUDE.md", "Plans/active/*.md"]` rather than a hand-listed copy that goes stale the next time a doc is added. Literal entries are unchanged.
- **An entry in `paths` that names no file refuses (exit 2), naming the entry.** It used to be skipped, so a typo or a moved file narrowed the universe and the check reported a pass over whatever was left — the same silent narrowing as an export that matched nothing. Adopter-side edit: a config carrying a stale literal path now refuses instead of judging less than it claims.
- **README** — keep `core.hooksPath` relative, which git resolves against each worktree's own top level; an absolute path points every worktree at one checkout's copy. A `*` in a git pathspec crosses `/`, which is what makes `.claude/*` sufficient.

### Fixed

- **A check whose `git` call failed exited 1, which the runner reads as findings.** `anchors` has shipped this since it began listing with `git ls-files`: an unreadable index, or `git` absent from `PATH`, raised out of the check, and Python's exit 1 became "this check found something" — at rung `warn`, a check that died with a traceback reported clean and the commit passed. Every check now maps an unexpected exception to exit 2, and the runner carries a refusal upward regardless of rung.
- **The export pipeline read only `git checkout-index`'s status**, so a pathspec `git` rejects emptied the export while the pipeline reported success; the config-drop guard then blamed a list that was merely too narrow. The pipeline runs under `pipefail` and names the pathspec as the cause.
- **An export that half-covered a check's scope passed over what survived.** A check listed its universe by walking the exported tree, so `paths: ["docs/*.md"]` under `export: ["docs/good.md"]` judged one file and reported clean while `run.py` on the same checkout found the other — the silent narrowing the gate exists to catch, reachable from the config alone. The adapter now hands every check the index listing through `GUARDS_INDEX`; a check takes its universe from that listing and refuses on a file in scope the tree lacks, naming it and the list, for a glob, a literal, a default universe, and a discovered log alike. `export` is a copy budget, never a scope; `paths` and `exclude` narrow a check.
- **`anchors` reported a link target the export dropped as missing.** Property 2 tested the exported tree, so under `export: ["*.md"]` every link to an image or a text file was a finding and the commit refused. A target now resolves against the tree or the index listing, as a file or a directory; one in neither is still a finding.
- **A glob skipped a tracked file deleted without `git rm`** while a literal naming the same file refused, so `run.py` on a working tree judged less than the index claims for one spelling of the scope and not the other. The listing keeps the file and the check refuses naming it. The adapter, which judges the index, is unaffected.
- **A `paths` or `exclude` entry beginning `./` matched nothing**: the listing is root-relative and the entry was matched as written, so `./docs/good.md` selected the file as a literal while `./docs/*.md` refused as "matches no file". Entries are normalized before matching, and one reaching outside the root refuses instead of being read.
- **A `paths` entry was matched as a glob before being tried as a literal**, so a tracked file whose name carries `[` refused as "matches no file" though `git` itself matches it. Literals are tried first, as a git pathspec does.
- **An `anchors` glob reached past markdown**, so `paths: ["docs/*"]` pulled in a PNG, failed to decode it, and refused every commit. A glob now narrows within the check's own universe.
- **A directory in `paths` refused with "no such file"** though it exists; it now says to name the files under it.
- **The README's sibling-checkout hook snippet ended `|| exit 1`**, rewriting the adapter's exit 2 to 1 and telling the wrapper's caller the gate found something when the gate could not run. It ends `|| exit $?`. An adopter that copied the snippet has this in its own hook.

## guards [0.4.0] — 2026-09-07

### Changed

- **README** — wiring the gate from a sibling checkout calls the git adapter (judges the index, not the working tree) and resolves the path through `--git-common-dir`, so it fires in worktrees, and says so on stderr when it skips.
- **`retro-log`** accepts the `FILED`, `NOTED`, and `HELD` statuses.
- **Git adapter** says on stderr when the index carries no config and nothing was judged, so a vacuous pass never reads as a working one.
- **README** names the path no hook judges — a rebase or union merge — and the landing-step run that gates it.
- **`retro-log-size`** — an occurrence over eight lines; a separate id so the cap can run at `warn` beside the grammar at `block`.

## guards [0.3.0] — 2026-09-07

### Added

- **`retro-log`** — the retro log's grammar; discovers `retroLogPath` from `.claude/threads.json`.
- **`review-ledger`** — the ledger's shape; discovers `ledgerPath` from `.claude/threads.json`.

## slices [0.3.1] — 2026-09-09

### Contract

- **The gap-checker applies its own fixes.** The `gap-checker` agent gains `Edit` and applies every unambiguous or code-derivable defect to the plan in place before it reports, running the fold sweep for each; a fix hinging on a product or priority call stays a question, and nothing is applied on `MIS-CARVED`. `/slices:check` has no approval stop — the report lists each applied fix and the sections it reached, the command verifies the fold and surfaces only questions. Measured in the reference adopter: sessions run autonomously, and a stop for approval is a stall with no fixes landed. The ledger record line and the `**Status:**` flip stay the command's. Adopter-side edit: none.
- **Verdict tokens are `FIXED-IN-PLACE`, `NEEDS-DECISION`, `MIS-CARVED`** — previously `holds`, `open`, `mis-carved`. Adopted from the reference adopter's wrapper, whose readers already parse them. Adopter-side edit: none unless a reader parsed the old tokens.
- **The Tensions cap moves from the plan to the digest.** The plan's `## Tensions` section holds every contestable call, compressed, never omitted; the in-thread digest carries at most five, ranked by how much the maintainer's judgment could move them. A plan read cold by a later session needs every tension; the five were only ever for the human's read. Adopter-side edit: none.
- **`draftDir`** in `.claude/slices.json` — optional; where `/slices:draft` writes a new plan and where `/slices:check` resolves a bare plan name first. `plansDir` stays the root the dedup sweeps cover. Absent → `plansDir`, as before.
- **The ledger record line is kept as the grammar** — `- drafted at <sha>, <date>, slices <version> — …` and `- gap-checked at …` — over a single refreshed `Verified at:` field: each record carries the plugin version that wrote it and the sha its rows were measured against, and the newest record's sha is the plan's baseline. A reader that wants one commit takes the last `at <sha>` in the section.

### Changed

- **The dedup sweeps run with `grep -r` or `rg --no-ignore`** in `/slices:capture`, `/slices:draft`, and the gap-checker's landed-premise class. A repo's ignore file can hide its archive from plain `rg`, and the sweep then misses a closed concern in silence.
- **`/slices:check` detects a stale gap-checker.** The harness loads agent definitions at session start and command text at invocation, so after a plugin update a session runs new command text against the old agent until it restarts. A report in the old vocabulary (`holds` / `open` / `mis-carved`), or one stating unambiguous fixes without applying them, is narrated as a stale agent; the command applies the fixes itself and the record line carries `agent-stale` after any `warm-context`. Measured in the reference adopter's first run on 0.3.0: command text 0.3.0, agent 0.2.0, verdict `open`, six one-line fixes stated and none applied, a record line that could not show it. Command text is cached per session too — loaded at the skill's first invocation — so a running session follows a plugin update on neither side until it restarts; the README states the rule.
- **The README sizes the `checkBrief`**: the cold check's cost scales with the draft's rows and the brief's classes. Measured in the reference adopter: one check of a one-constant slice ran 44 tool uses (21 ledger re-runs, 14 brief classes, the built-ins) for 132k tokens over 9.3 minutes.

## slices [0.2.0] — 2026-09-08

### Contract

- **The claim ledger is written at draft time.** `/slices:draft` runs a site-opening pass before the plan is written — every production symbol, file, test, and site the plan will name is opened with a command — and writes the pairs as claim rows under a `- drafted at <sha>, <date>, slices <version> — <N> sites opened (unverified: <n>)` record in the `## Verification ledger`; a site it could not open is an `unverified` row. `/slices:check` and its gap-checker re-run those rows verbatim first, report a row that moved as a defect, and append only rows the draft did not hold. Measured in one adopter: the prose rule ("every named site is opened at draft time") recurred seven times in five days with the rule present, and the one draft that measured its claims before writing held on all three while its thirteen gaps were unopened sites. Adopter-side edit: a plan template whose own ledger section says "written by the check, not the drafter" says the drafter writes it and the check re-runs it; the `- (none yet)` placeholder in already-drafted plans is still replaced by the check's first append.
- **`ledger` is a template marker role.** A template heading carrying `<!-- slices: ledger -->` — an adopter's `## Claim ledger` its finalize step already reads — is the scaffold's place: the drafter's record and rows are written there and the check appends there, so a repo that wraps `/slices:draft` carries its own ledger name. Previously `ledger` was named as an ignored role. Adopter-side edit: none unless a template wants the section seated; then the marker on that heading.

## slices [0.1.5] — 2026-09-07

### Contract

- **`/slices:draft` fills the template's local sections.** Previously carried through as placeholders for the adopter's own commands to fill; now filled from their placeholder text and the optional **`draftBrief`** file in `.claude/slices.json` — an adopter-owned file of section-filling rules. A section whose placeholder names another writer or says omit-at-draft is still left alone. A plan is drafted whole; an adopter's draft command reduces to orient, call `/slices:draft`, do its own bookkeeping. Adopter-side edit: none.
- **`checkBrief`** in `.claude/slices.json` — optional path to an adopter-owned file of local gap classes and user-side lenses; `/slices:check` hands it to the cold checker beside the plan's path, and the checker runs those classes after the built-in ones. This is the hook that lets a repo with its own gap-check wrap `/slices:check` instead of running two checkers. Absent → unchanged behavior. Adopter-side edit: none.
- **Claim rows in the ledger.** Under its record line, `/slices:check` now appends one indented row per load-bearing claim the checker verified — the claim, the generating command, one line of output — and one per claim it could not, marked `unverified`. The record line itself gains `slices <version>` after the date. Both additive; a reader that only parsed the record line still can. Adopter-side edit: none, though a repo with its own claim ledger can now read this section instead.

### Added

- **`/slices:draft`** — a light-lane check before anything else (a concern touching no shipped behavior needs no plan); a near-duplicate verdict that consolidates before drafting, and a dedup sweep over inbox, plans, and completed; feasibility and sequencing axes on the surviving claims; every artifact the draft names is opened at draft time; a deferral written into the plan body becomes a stub in the same change; a criterion's command is one you ran, and a negative criterion carries a liveness condition; tension entries state the lever (what overriding costs); runs `/slices:check` on the new plan in the same session without being asked, and handles a mis-carved verdict.
- **`/slices:check`** — a **mis-carved** verdict (a shape problem, not gaps: back to a stub, never repaired in place); a folded fix sweeps the plan body; when findings keep coming after the plan should be done, stop folding and fix the problem one layer down; an escalated question carries the agent's own recommendation.
- **Gap-checker** — new classes: a special case layered on shared infrastructure where a structural fix is the right altitude; a deferral premise a since-landed change falsified; a hazard analysed in one direction only; boundary states and resumption in the user walk; runnable mechanisms run in both polarities. Reports claim rows and a three-way verdict.
- **`/slices:capture`** — a stub about a plugin command's behavior names the plugin and version observed; the dedup grep covers plans and completed, not only the inbox.
- **README** — a change to a plugin's own command text takes the light lane: edit, run once, commit.

## slices [0.1.4] — 2026-09-06

### Contract

- **`/slices:draft` and `/slices:check` are template- and config-aware through two
  optional fields.** `.claude/slices.json` gains `planTemplate` and `checkerModel`.
  Absent — every current config, this repo's and the reference adopter's included — both
  commands behave as before: the built-in plan block is unchanged, read identical to the
  0.1.3 text. Set, `draft` starts from the adopter's plan template and overlays the fixed
  invariants — `## Shape`, `## Scope`, `## Acceptance`, `## Tensions`, the
  `## Verification ledger` scaffold at end of file, and the `**Status:**` readiness line
  under the title — resolving each by a role marker on the template's own heading
  (`## Summary <!-- slices: shape -->`; roles `shape`, `scope`, `acceptance`, `tensions`;
  the marker is read and dropped, never written), then by an exact slices heading, then
  auto-emitting what neither resolves and saying so, never refusing. Local sections are
  carried through with their placeholders untouched, sub-headings included; a template's
  H1 is the title. `check` reads `checkerModel` and passes it to the gap-checker spawn as
  given, narrating it; a refused model is narrated and the check runs on the default;
  under a true `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` the spawn omits `model` and says the
  flag overrode the field. `check` creates the `## Verification ledger` at end of file
  when a plan another drafter wrote has none, and never writes a `**Status:**` line into
  such a plan — the verdict stays in-thread. Benefit: an adopter carries its own plan
  sections through a template and pins the checker's model through config, so a
  `/plugin update` never forks either command. Adopter-side edit: none — both fields are
  additive and opt-in, their absence preserves prior behavior, and no adopter holds
  either.

### Added

- **The split test.** `/slices:draft`'s carve step and the gap-checker's "bundled second
  concern" class carry one rule: a second concern is bundled only when it brings its own
  dependency, its own verification run (a distinct harness, fixture set, or tooling), or
  an independently useful landing boundary; sharing all three is one change argument.
- **The slice definition names its two limits.** Both commands state a slice as one
  coherent change argument, independently verifiable, bounded by overflow and
  self-conflict — never split by habit.
- **`/slices:check` resolves a bare plan name** under `plansDir`, or `Plans` when there is
  no config.

## threads [0.7.4] — 2026-09-07

- **`placerModel`** in `.claude/threads.json` pins the `finding-placer`'s model; both commands pass it to the spawn, and a refused model falls back to the agent's default. The README no longer tells adopters to edit the cached agent file.

## threads [0.7.3] — 2026-09-03

### Fixed

- **The ripeness nudge counted the whole retro log as pending.** `/threads:retro` §5 now
  derives pending from the review mark, the same boundary `/threads:process-review`
  adjudicates against, so a clean review is no longer reported as a backlog the next
  day, and a run with nothing pending and no trigger bar met says nothing.

### Changed

- **The retro auditor records what a read prevented.** A claim the session record
  shows revised after a doc read is reported as a `positive/` finding naming the doc,
  so prevented errors reach the retro log as observed corrections instead of leaving no
  trace.

## slices [0.1.3] — 2026-09-03

### Contract

- **`/slices:capture` is template-aware through an optional `stubTemplate` config
  field.** `.claude/slices.json` gains an optional `stubTemplate` path. Absent — every
  current config, this repo's included — capture writes the built-in day-one stub
  byte-for-byte as before. Set, the command starts from the adopter's template and
  *overlays* the invariants it guarantees in every repo: a low-trust banner (present; the
  wording is the template's), the one-concern rule, and the closed `Blocked on:` /
  `Source:` grammars — auto-emitting any the template omits and narrating that it did,
  never refusing. The title form, the banner text, and every other field are the
  adopter's, carried through untouched, so a repo adapts the stub shape through a template
  instead of editing command text and a `/plugin update` never forks it. Benefit: an
  adopter carries local stub fields through config, not a command fork. Adopter-side edit:
  none — the field is additive and opt-in and its absence preserves prior behavior, so no
  adopter holds it and none needed reconciling.

### Added

- **The stub-template format is documented** in `/slices:capture` and the plugin README:
  a template is an ordinary stub skeleton read by structure — heading, banner blockquote,
  the grammar lines, local fields, body. Relationship fields — a `Depends on:`, a
  `Related:` cross-reference to a set of sibling concerns — are local fields the overlay
  carries through; point them at durable slugs (plans, epics), not at sibling stubs, which
  `/slices:draft` deletes on promotion.

## slices [0.1.2] — 2026-09-03

### Contract

- **Stub fields carry a closed grammar, spelled as the reference adopter spells them.**
  `blocked-by` is now `Blocked on: <tokens> — <rationale>` with tokens
  `slice:<plan-basename>`, `signal`, `decision`; `source:` is now `Source: <origin>
  <date> — <detail>` with origin `user`, `repo:<name>`, or `carved:<plan-basename>`.
  Both lines stay optional and mean the same when absent. Benefit of a new spelling:
  none — the side with fewer carriers moved. Adopter-side edit: none for a repo already
  on `Blocked on:`; a repo on `blocked-by` renames the line.

### Added

- **`/slices:check` tests an escalated ruling before recording it.** Step 2 checks the
  ruling against the docs `invariantDocs` names in `.claude/threads.json` (falling back
  to `docs/principles.md` and `docs/direction.md`) and surfaces a conflict instead of
  recording the ruling.
- **A new gap-check failure class.** A ruling or tension that changes a recorded
  decision without naming that decision's own amendment in scope.
- **A stub can say where its observation came from.** The capture contract gains an
  optional `source:` line, next to `blocked-by`, for an observation carried in from
  outside the repo's own sessions: another repo's review or retro, a person's
  report, an issue. Provenance, not trust; the banner still applies. A later reader
  can tell an observation made in the repo from one brought in, which the banner
  alone cannot say. The channel by which an outside observation arrives is not part
  of the line.

## guards [0.2.0] — 2026-09-07

- **Renamed from `checks` to `guards`.** The plugin directory is `guards-plugin/`, the config is `.claude/guards.json`, the install is `guards@no-lost-threads`, and the hook path is `guards-plugin/adapters/git`. Check ids, the config's shape, and the exit codes are unchanged. The name no longer collides with `/slices:check`.

## checks [0.1.0] — 2026-09-02

### Added

- **Initial release of `checks`, repo guardrails as scripts behind a gate** — the
  third capability module. One script per check with a stable id, pass and fail
  fixture trees proven by `test.sh`, and exit codes 0 / 1 / 2 meaning pass, findings,
  refused; severity is the rung's, set per check in `.claude/guards.json` as `warn` or
  `block`, so enforcement climbs by config and never by migration. `run.py` maps
  findings through rungs and exits 2 itself when a check cannot run, so a broken gate
  is never a passed one. A git pre-commit adapter exports the index to a temporary
  tree and runs the runner there, judging the commit's content; it is inert when the
  index carries no config. Two checks ship: `anchors` (every in-repo section link
  resolves to an explicit `<a id>` and every relative link target exists;
  heading-derived slugs fail by design) and `war-stories` (narrative provenance in
  process docs); for both, fenced code and code spans are not prose. Installed from
  the marketplace this version is inert — no hook file, no command; the install line
  assumes the plugin lives in the repo's tree.

## threads [0.7.2] — 2026-09-01

### Fixed

- **`/threads:process-review` could not see that its own capability-evidence
  input was short.** `capabilityEvidencePath` had readers and no writer: the
  field appeared three times in the command, all read-side, and nothing pointed
  `finding-placer` at the store either — it is not in `processDocs`. A retro-log
  `Placement:` naming that store was therefore a proposal nothing in the system
  would act on. The failure is invisible from where the review stands: step 0c
  counts the store's own keys, and those counts read identically whether the
  placements addressed to it arrived or not, so a review reports a healthy log
  and a short one the same way — then ranks capability candidates, the funnel's
  only non-doc-shaped output, against the short set. Measured in the reference
  repo before the fix: nine actionable placements named the store and none had
  landed. Step 0c now reconciles the store against 0b's placements and carries
  the fraction, and that fraction is a required field of the
  capability-candidates output, so a run cannot finish its report without having
  looked. Landing the unresolved ones is a completion step; a decline goes in the
  ledger. Stated as a rule rather than a required output it would have been
  another prose route, which is the class of failure it fixes.
- **Retro's log append named a file but not a position in it.** `/threads:retro`
  said to append every finding to the retro log while the log's own contract says
  entries live under `## Entries`. Once a log grows a trailing section, a literal
  end-of-file append lands outside the section that holds entries — where it
  still greps and no longer reads, so the failure is silent to the mechanism that
  ranks recurrence. Retro now appends under `## Entries`, ahead of any trailing
  section, and the bootstrap seeds the same clause into a new repo's log header.

## slices [0.1.1] — 2026-09-01

### Fixed

- **`/slices:capture` failed on a fully-drained inbox.** The command wrote a stub
  into `inboxDir` without ensuring the directory existed. Git tracks no empty
  directories, so draining the last stub deletes the directory and the next
  capture fails with ENOENT — an inbox that has been used is indistinguishable
  from a repo that never had one. Capture now creates `inboxDir` when absent.

## threads [0.7.1] — 2026-09-01

### Fixed

- **`/threads:retro`'s escape hatch could silently inflate the retro log's
  recurrence count.** When a user accepted findings and asked for them to be
  applied on the spot, the escape hatch closed with "the entry still goes in the
  log — appended with its landing noted." By that point capture has already
  happened: the capture step appends unconditionally and is told not to ask
  first. So noting the landing required either editing an existing entry —
  forbidden by name, "not to mark one landed" — or appending a second entry
  under the same key. That same-key append is exactly what the command
  authorizes as the *recurrence* mechanism, so an agent holding "note the
  landing" and "never edit" resolves to the move the document had already
  blessed. Nothing errors and the log stays well-formed; the key's occurrence
  count simply gains a recurrence that never happened, and
  `/threads:process-review` reads that count as the evidence that promotes a
  finding to *adopt now*. The failure is worse than a miscount: it ratchets one
  way, since nothing demotes a promotion, and it is self-confirming, since retro
  reads the log *before* it appends — the session that corrupts the count cannot
  detect what it just did, and the next one inherits it as measured fact. The
  root is that an entry carries two things, occurrence (what the key counts) and
  lifecycle (which has no field), so the escape hatch borrowed the counter.
  Lifecycle now routes to the stream that already owns it: the log entry stays
  exactly as it was appended, the landing is recorded by the marker commit, and
  the review collapses the entry to a pointer at that commit. A same-key append
  is authorized for recurrence and nothing else — stated in the capture rule, in
  the anti-patterns, and in the log header that bootstrap seeds, so the contract
  an appending session reads in-file matches the one in the command. Found by a
  downstream adopter that hit the ambiguity live.

## threads [0.7.0] — 2026-08-31

### Added

- **`invariantDocs`** (optional, ordered) — the docs stating what a repo holds
  true, read at step 0a before any commit is examined. A review that proposes
  process changes without reading the repo's stated invariants is deriving law
  from a commit stream. The output must name what was read, so the step cannot
  quietly stop happening.
- **`capabilityEvidencePath`** (optional) — a log of findings about *capabilities*
  (contracts and rungs) rather than doc sections. Relevant where a repo builds
  tooling it also uses. Every other input is doc-churn-shaped, so without this one
  the funnel's output can only ever be doc edits.

### Changed

- **The funnel now gates on its own first signal.** Steps 1–7 are conditional: if
  nothing recurred after re-keying and no ledger signal fired, the review reports
  and stops. Measurement cost rises with repo size while a fixed-depth funnel's
  yield does not; the first run of this command against its own repo spent seven
  tiers and a sub-agent to reach an answer two greps had already given. `deep`
  overrides the gate.
- **Re-keying now precedes counting.** Keys were re-written at completion and
  counted at step 0, so every ranking decision used a number the re-key later
  invalidated. Measured here: one mis-keyed entry made a four-occurrence class
  read as a one-off, and it was the corpus's only real recurrence.
- Output gained a **capability candidates** section and a statement of the reads
  that sized the run.

## slices [0.1.0] — 2026-08-31

### Added

- **Initial release of `slices`, the day-one slice-pipeline kit** — the second
  capability module, extracted contract-first from the reference pipeline's
  "day one — costs nothing, pays immediately" set. `/slices:capture` files
  one-concern, low-trust stubs (mandatory banner; lifecycle by directory;
  blockers are named checkable conditions or nothing). `/slices:draft` promotes a
  stub into a plan — re-verifying the capture's claims first, carving bundles,
  deleting the stub in the promotion — ending in a review digest of a Shape
  paragraph plus at most five tension points. `/slices:check` spawns a cold
  `gap-checker` sub-agent handed only the plan's path (withholding the drafting
  context is load-bearing), and appends its verdict to the plan's verification
  ledger; no plan is implement-ready until it survives. The two-lane rule and the
  marker-prefix convention ship as stated policy and a pointer to `threads`
  respectively — capabilities compose rather than duplicate. Artifacts are the
  contract: later rungs (banner lint, claim ledger, triage, a landing gate) only
  append to these files, so day-one adoption never sets up a migration.

## [0.6.0] — 2026-08-30

### Added

- **A retro log — `adopt-if-it-recurs` finally has a destination.** `/threads:retro`
  named the disposition and stopped there; nothing in the command routed it anywhere, so
  the finding's next carrier was the conversation, which ends. A downstream repo built
  its own log and it failed to fire on **every** occasion, including one where the
  session had already read the doc carrying the convention — evidence that a pointer in a
  linked doc doesn't reach the decision moment. Findings now append to `retroLogPath`
  (new config key, default `.claude/threads-retro-log.md`), and the placer **reads the
  log to make the call**: a carrier you must consult is much harder to skip than one you
  are told to write to afterward. Kept separate from the deferral ledger because the two
  sit at opposite ends of the review funnel — the ledger holds decisions *not* to act and
  is read late as a suppressor, the log holds unlanded work and is read first.
- **Dedup keys, written by `finding-placer`.** Each finding gets one greppable,
  domain-free key naming its *shape*; the slice's own nouns stay in the evidence. The
  placer writes it because the calling session is soaked in the domain and is the worst
  context to abstract away from it — and because, having just grepped the existing keys,
  it phrases new ones in the corpus's register instead of drifting. That convergence is
  what keeps a repo's log matchable, and it's why the class vocabulary ships as a
  **seed rather than a schema**: keys grow into each repo's own frictions with nothing to
  configure. A repeat is a *new entry reusing the same key*, so recurrence is a grep count
  and no writer ever mutates the file. Where the sub-agent is unavailable, the working
  session keys its own finding and flags it `key (uncold)`, so the review re-keys those
  first instead of reading their never-matching as evidence of a one-off.
- **A ripeness nudge at the end of `/threads:retro`** — what's pending, how old, what's
  churned since the mark, in one sentence, always pointing at a fresh session and never
  offering to run the review in the current one.

### Changed

- **Retro captures; process-review lands.** Retro fired at the largest context a session
  ever has — the most expensive possible moment to apply an edit, since it invalidates
  the cache behind the whole session — and a session that ended with the output unread
  lost everything it found. Findings are now appended and adjudicated later by
  `/threads:process-review`, which runs in fresh context by requirement and is the only
  reader that can tell one friction from three of the same shape. The punch list is still
  presented in-thread, and a user who asks for an immediate landing still gets one.
  Consequences: retro now writes to the working tree by default (one append — capture is
  not adoption, and the entry takes no effect), and `retroTelemetry` narrows to the
  land-now hatch.
- **Retro's disposition is an input to the review, not a verdict.** Process-review reads
  the log first, ranks keys with more than one occurrence, and may re-rank with the
  reason recorded. The placer still can't touch a disposition; it reports a match as a
  fact and the caller revises its own call.
- **Retirement re-keys before it retires.** An entry that never recurred is either
  one-off or *keyed too specifically to ever match*, and volume can't tell those apart —
  so a fixed age threshold would delete the evidence that keying is broken and leave a log
  that looks healthy while deduping nothing. The review reads every key at once, which
  makes it the only context that can spot the difference. No fixed N, for the same reason
  staleness never proposes a rewrite on age alone.
- **`markerPattern` loses its byte constraints**, and bootstrap's two-reader proof
  collapses to one reader. Both existed only because the hook re-read the config through
  a sed capture. Patterns written under the old rule keep working.

### Removed

- **The SessionStart nudge hook** (`hooks/hooks.json`,
  `scripts/process-review-hook.sh`), and with it the sentinel, the mark-stamp, and the
  worktree-scope machinery. The plugin now ships no hooks at all. Measured in a live
  adopter repo: delivery **proven in 19 sessions**, relayed in **1** — and that one at a
  mid-session lull, not the mandated first response. The other 18 opening turns were
  uniformly task-acquisition. Mandating the relay had already replaced a discretionary
  version that never fired, so this is not a wording problem: an instruction that must
  beat the user's own request at the moment they make it will lose, and mandating it only
  makes the failure quieter, since the emission log then records 19 successes. Emission
  was the wrong end of the pipe to measure. The nudge moves to retro time, where it is
  command output and the transcript is the record.

## [0.5.2] — 2026-08-12

### Fixed

- **`/threads:process-review`'s step-1 recipe could never match.** The command doc's
  "Free" tier piped `git log --format='%h %s'` into a grep whose `markerPattern` is
  anchored to the subject start, so the hash prefix defeated the anchor and the count
  was zero on every repo — presenting as the silent-death tier's false positive ("your
  telemetry convention may not be firing") even with marker commits present. The recipe
  — and the design spec's `--grep` variant, which matched commit *bodies* in violation
  of the subject-only rule — now uses the hook's subject-first shape,
  `--format='%s%x09%h'`, and the silent-death check says to rule out the measurement
  itself before diagnosing the convention. The session-start hook was never affected.
  Found by a downstream repo's review run, which hit the false positive live.

## [0.5.1] — 2026-08-05

### Changed

- **`finding-placer` is time-boxed.** Shipped in 0.5.0 it was unbounded in three ways,
  and on a real repo it ran past five minutes and 200k tokens without finishing: it
  rediscovered the process-doc layout from scratch each run, it read source and backlog
  files to size the rules it was placing, and `add — last resort` set a bar (*no host
  exists anywhere*) that can only be met by surveying the whole repo. Now: **callers hand
  it the candidate docs** (`processDocs` from `.claude/threads.json`, plus the hot/stale
  files process-review already surfaced) instead of making a cold agent re-derive them;
  placement is fenced to siting the lesson, never measuring or re-wording it; and the
  amend bar is *a host is visible in what you read*, with an unsure add returned as `add
  (unconsolidated)`. Retro runs often enough that speed is a correctness property —
  `/threads:process-review` already reconciles across sessions, so an add that should
  have been an amend is recoverable at the altitude built for it.
- **`finding-placer` is pinned to Sonnet** (`model:` in its definition) rather than
  inheriting the session. With the map handed to it and the scope fenced, the work is
  judgment against text already in front of it, not open-ended search. The auditor still
  follows the session — it reads a whole transcript cold, which is the harder read.

## [0.5.0] — 2026-08-04

### Added

- **A placement sub-agent (`finding-placer`), shared by both commands.** Amend-before-add
  was stated in `/threads:retro` but executed by the context that did the work — which
  can't afford to re-read the target section, so "amend" reliably degraded into "append"
  (measured in a live adopter repo: a culled doc back at its word budget in four days,
  mostly appended worked-cases). Surviving findings now go to a fresh read-only sub-agent
  that reads the target docs and returns amend / merge / narrow / add-as-last-resort,
  with the existing text quoted and the edit specified — *before* approval, so what you
  approve is the fully-specified change. Retro spawns it in both modes; process-review
  spawns it after its expensive tier, whose session is fresh by mandate but not by then.
- **Retro findings carry their detection source.** The self-pass and the cold audit are
  reconciled, not concatenated: findings are tagged `[self]` / `[audit]` / `[both]`
  (`[both]` ranks first), and an audit finding the self-pass had cleared surfaces as
  `[disputed]` rather than being settled by the anchored party. Across runs the tags are
  the record of whether the audit earns its spawn.
- **The review adjudicates promoting signals.** The ledger step said "don't re-propose
  what's deferred" but never the reverse motion: every live signal is now checked
  against the window, and the fired ones adjudicated — promote, retire, or re-defer
  with the reason.
- **Staleness sweep: reachability and referent-existence checks.** A doc nothing routes
  to is the silent-death class regardless of freshness, and a staleness survivor is
  checked for dead referents before "clean" can count as evidence against urgency.

### Changed

- **`/threads:retro quick` means "skip the audit," not "self-pass only."** Placement
  still runs — `quick` selects the detection source, not a lower quality tier.
- **The marker convention must survive both its readers, and the squash.** Bootstrap
  probes how changes reach the default branch (a squash rewrites branch-side subjects,
  silently killing markers) and negotiates a pattern covering the merge-lane spelling;
  the silent-death check looks at the merge lane before declaring the convention dead.
  `markerPattern` must be backslash-free and class-based: the hook extracts it with a
  naive sed capture, not a JSON decoder, so a JSON-escaped backslash reaches grep as
  dead bytes — measured live, where a widened pattern passed its JSON-decoded proof
  while the hook matched nothing. The prove-it-fires gate now runs through each
  consumer's own reader chain, and editing the pattern later re-runs it.
- **The deferral ledger gains lifecycle rules.** It is a working file read in full every
  run, so append-only accelerates per-window: entries are gated on *would a future
  review act differently without it*, collapse to a pointer once their promotion lands,
  and record numbers with their generating command.
- **The mark advances at an ancestor of the default branch,** after landing — not at
  `HEAD`, which a squash or rebase can orphan, taking the review window with it.
- **Split-with-routing is a sanctioned structural outcome** when a hot doc's growth is a
  coherent cluster its charter doesn't cover — and incomplete without the routing change.

## [0.4.2] — 2026-07-26

### Fixed

- **The process-review nudge now actually reaches you — for real this time.** 0.4.1 moved
  the trigger to a `SessionStart` hook so a live turn could carry it. It reached the
  *agent* and stopped there: the payload asked the agent to relay the nudge "when it will
  not cut across what the user is doing", which at session start — the moment you've just
  arrived with a task in mind — is essentially never true. A live adopter repo fired four
  nudges across three days and every one was correctly suppressed by a well-behaved agent.
  The payload now **mandates** a one-sentence relay in the agent's first response before it
  continues with your request, and names the single legitimate exception (your first
  message *is* `/threads:process-review`). It still never acts on the nudge unprompted.
- **A repo with ten worktrees gets one nudge, not ten.** The re-nudge sentinel lived in the
  per-worktree git dir, so every fresh worktree started at `last=0` and nudged on its first
  ripe session — cadence tracked *worktree creation* rather than backlog ripeness, which on
  a heavy-worktree workflow is both too chatty (every new worktree) and too quiet (a
  long-lived checkout silent for a full doubling). The sentinel and the `threads-nudge.log`
  breadcrumb now live in the **common** git dir, shared by every linked worktree, because a
  ripe backlog is a property of the repo. Upgrading orphans the old per-worktree sentinels;
  expect one re-nudge, then correct cadence. The mark stamp is unchanged and still does its
  job across *clones*.
- **`/threads:process-review` now propagates the mark tag it advances.** Completion ran
  `git tag -f <markTag> HEAD` with no push. Where the tag is published on the remote — as
  it is in any repo that has ever run `git push --tags` — the advance stayed local, so
  every other clone kept measuring from a stale mark and every later review re-read ground
  an earlier one had already covered (observed two reviews stale in a live adopter repo).
  Completion now pushes the advance when the tag exists on the remote, and leaves a
  local-only tag local — a review never publishes a tag as a side effect.

## [0.4.1] — 2026-07-20

### Fixed

- **The process-review nudge now actually reaches you.** The trigger shipped as a `Stop`
  hook emitting `systemMessage` — which fired and emitted correct JSON on every qualifying
  stop, but was never seen: a `Stop` hook runs after the turn ends, with no live turn to
  attach a user-visible message to, so the nudge was dropped. It now runs as a
  **`SessionStart`** hook and hands the agent the nudge as `additionalContext`, surfaced
  at the agent's discretion at the start of a fresh session — which also fits the "fresh
  session, never mid-draft" intent better than firing at stop ever did. It fires on a
  fresh start or `/clear`, and stays quiet on resume or a mid-thread compaction.
- **The re-nudge guard no longer goes stale across worktrees.** State is per-worktree but
  the mark tag is shared, so completing a review in one worktree advanced the mark for all
  while resetting only its own sentinel — leaving sibling worktrees able to suppress a
  state that was freshly ripe against the new mark. The sentinel is now stamped with the
  mark it was measured against (`<mark-sha> <count>`); when the mark advances, a sibling's
  stale stamp reads as `last=0` and re-nudges against the new baseline. Backward-compatible
  (a legacy bare-number sentinel also reads as `last=0`).

### Changed

- **The trigger counts commit _subjects_, not whole messages.** `git log --grep` matched
  the marker pattern anywhere in a commit message, so a commit whose body quoted a
  `docs(process/…)` line inflated both the volume count and the concentration tally. Both
  the hook and the `/threads:process-review` command's own counts (stream listing, tally)
  are now subject-only, so the counts (and the "N since last review" tease) are exact.
- **Each emitted nudge is logged** to `threads-nudge.log` in the per-worktree git dir
  (auto-ignored), so "did it fire, and what did it say" is observable without depending on
  UI surfacing — the diagnosis a silent surfacing failure used to make expensive.

## [0.4.0] — 2026-07-16

### Added

- **`/threads:process-review` gains a staleness sweep** — the negative-space
  complement to its churn signal. Stable workflow docs (a command pipeline, a
  long-standing rule) can fall behind a growing repo without ever generating
  telemetry, so the review now also ranks process docs and workflow sets by
  growth-since-last-touch and by sibling co-evolution variance (one pipeline stage
  amended while its neighbors sat untouched), then git-blames the survivors to point
  at their stalest sections, weighted toward load-bearing files. Staleness alone
  proposes scrutiny, never a change; a concrete proposal requires an intersecting
  signal (churn, a memory, an accepted retro finding). New optional config field
  `workflowDocs` declares files expected to co-evolve; absent, detected command
  directories (`.claude/commands/`) each form a set — repos with no workflow surface
  skip the sweep with a narrated tier note, like any detected input.

## [0.3.0] — 2026-07-02

### Added

- **`/threads:process-review`** — the cross-session review. Reads the accumulated
  stream of process-shaped commits (or process-doc churn as a day-one fallback) and
  surfaces reconciliation / structural candidates no single session can see. First run
  bootstraps by inspection: it negotiates a marker convention fitting the repo's
  existing commit style (proving the pattern fires before adopting it) and writes
  nothing until confirmed. Conventions live in `.claude/threads.json` — one visible
  source. Applying anything requires recorded consent (`applyMode`, starts
  `read-only`).
- **A Stop-hook trigger** ships with the plugin: no analysis, one local git command per
  session stop, no network. Nudges when accumulation looks ripe (same file re-touched
  across several process commits) or crosses a volume backstop, and escalates instead
  of nagging — a re-nudge only after accumulation roughly doubles.

### Changed

- **`/threads:retro` feeds the loop:** when the user accepts findings and has them
  applied, retro offers (once, recorded in `.claude/threads.json`) to land them as
  marker commits — the telemetry `/threads:process-review` reads.

## [0.2.1] — 2026-06-25

### Changed

- **`/threads:retro`'s fresh-context audit now sees far more of each agent turn.** The
  extractor that builds the session record capped agent text at 700 characters and kept
  only the head — which dropped the tail of long turns, where commitments, deferrals, and
  lock-in language tend to land, and discarded roughly half of all agent text before the
  cold reviewer saw it. The cap is now 2,500 characters, and over-cap turns retain their
  head **and** tail. The audit reads more completely; the record stays a few KB.
- **The fresh-context audit now flags self-perpetuating closure language.** When an agent
  turn closes a question with markers like *decided / deferred / for v1 / by-design* that
  the evidence hadn't earned and the user hadn't locked, the auditor surfaces it for a
  second look — such markers tend to get accepted once and never revisited.

## [0.2.0] — 2026-06-24

- `/threads:retro` reviews the current session as process telemetry. The default runs a
  self-pass plus a **fresh-context audit** — a read-only `retro-auditor` sub-agent that
  judges the session's observable record cold. `/threads:retro quick` runs the self-pass
  alone and skips the sub-agent.
