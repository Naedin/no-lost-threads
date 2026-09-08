#!/usr/bin/env bash
# guards — prove every check on its fixtures and the runner on its contract.
# Prints one line per case with the expected and observed exit code; exits 1 on
# the first wrong one.
#
# Fixture layout: checks/<id>/fixtures/{pass,fail}/<case>/ is a mini tree handed to
# the check as --root. A case may carry an `args` file, one argument per line,
# appended to the invocation (how a check whose universe is --paths names them).

# Fixtures must not inherit the ambient git config: a global core.excludesFile
# covering a fixture's paths makes `git add -A` stage nothing, and a case asserting
# exit 0 then passes green having judged an empty tree.
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
tmp="$(mktemp -d)" || exit 1
trap 'rm -rf "$tmp"' EXIT

expect() {  # expect <code> <label> <command...>
  local want="$1" label="$2"
  shift 2
  "$@" >/dev/null 2>&1
  local got=$?
  if [ "$got" -eq "$want" ]; then
    printf 'ok    %-52s expected %s observed %s\n' "$label" "$want" "$got"
  else
    printf 'FAIL  %-52s expected %s observed %s\n' "$label" "$want" "$got"
    "$@"
    exit 1
  fi
}

says() {  # says <code> <label> <pattern> <command...> — exit code and stderr both
  local want="$1" label="$2" pat="$3"
  shift 3
  local err
  err="$("$@" 2>&1 >/dev/null)"
  local got=$?
  if [ "$got" -eq "$want" ] && printf '%s' "$err" | grep -q "$pat"; then
    printf 'ok    %-52s\n' "$label"
  else
    printf 'FAIL  %-52s expected %s observed %s\n' "$label" "$want" "$got"
    printf '%s\n' "$err"
    exit 1
  fi
}

mkrepo() {  # mkrepo <dir> — a git repo with the adapter installed as its hook path
  mkdir -p "$1/.claude"
  git -C "$1" init -q
  git -C "$1" config user.email guards@test
  git -C "$1" config user.name guards
  git -C "$1" config core.hooksPath "$here/adapters/git"
}

hook() {  # hook <repo> — run the pre-commit adapter in <repo>, return its own exit
  ( cd "$1" && exec "$here/adapters/git/pre-commit" )
}

run_case() {  # run_case <code> <id> <case dir>
  local want="$1" id="$2" dir="$3" extra=()
  if [ -f "$dir/args" ]; then
    while IFS= read -r line; do extra+=("$line"); done < "$dir/args"
  fi
  expect "$want" "$id $(basename "$(dirname "$dir")")/$(basename "$dir")" \
    python3 "$here/checks/$id/check.py" --root "$dir" ${extra[@]+"${extra[@]}"}
}

for check in "$here"/checks/*/; do
  id="$(basename "$check")"
  for dir in "$check"fixtures/pass/*/; do run_case 0 "$id" "$dir"; done
  for dir in "$check"fixtures/fail/*/; do run_case 1 "$id" "$dir"; done
  expect 2 "$id refuses: root missing" \
    python3 "$check/check.py" --root "$tmp/no-such-root"
  mkdir -p "$tmp/empty-$id"
  expect 2 "$id refuses: a literal --paths naming no file" \
    python3 "$check/check.py" --root "$tmp/empty-$id" --paths absent.md
  expect 2 "$id refuses: a --paths glob matching nothing" \
    python3 "$check/check.py" --root "$tmp/empty-$id" --paths 'absent/*.md'
done

# The runner: config absent, malformed, unknown id, rungs, and a refused check.
r="$tmp/runner"
mkdir -p "$r/.claude"
expect 0 "runner: no config" python3 "$here/run.py" --root "$r"
says 0 "runner: no config says nothing was judged" "nothing judged" \
  python3 "$here/run.py" --root "$r"

printf '{' > "$r/.claude/guards.json"
expect 2 "runner: malformed config" python3 "$here/run.py" --root "$r"

printf '{"checks": {"no-such-check": {"rung": "warn"}}}' > "$r/.claude/guards.json"
expect 2 "runner: unknown check id" python3 "$here/run.py" --root "$r"

cp -R "$here/checks/anchors/fixtures/fail/dead-anchor/." "$r/"
printf '{"checks": {"anchors": {"rung": "block"}}}' > "$r/.claude/guards.json"
expect 1 "runner: block finding refuses" python3 "$here/run.py" --root "$r"

printf '{"checks": {"anchors": {"rung": "warn"}}}' > "$r/.claude/guards.json"
expect 0 "runner: warn finding passes" python3 "$here/run.py" --root "$r"
python3 "$here/run.py" --root "$r" 2>/dev/null | grep -q '^warn anchors: ' \
  || { echo "FAIL  runner: warn finding is printed with its prefix"; exit 1; }
printf 'ok    %-52s\n' "runner: warn finding is printed with its prefix"

printf '{"checks": {"anchors": {"rung": "warn", "exclude": ["*.md"]}}}' > "$r/.claude/guards.json"
expect 2 "runner: refused check refuses regardless of rung" python3 "$here/run.py" --root "$r"

# --paths: a literal file or an fnmatch glob, `*` crossing `/` as in a git pathspec,
# deduplicated, with --exclude applying after. An entry naming nothing refuses, so a
# scope never narrows in silence.
sc="$tmp/scope"
mkdir -p "$sc/docs"
printf '# Root\n\nA rule and its mechanism.\n' > "$sc/CLAUDE.md"
printf '# A\n\nA rule and its mechanism.\n' > "$sc/docs/a.md"
printf '# B\n\nA rule and its mechanism.\n' > "$sc/docs/b.md"
printf '# Bad\n\nAdded in this session after a redirect.\n' > "$sc/docs/bad.md"
printf 'a rule and its mechanism\n' > "$sc/docs/keep.txt"
ws="$here/checks/war-stories/check.py"

expect 1 "scope: a glob selects the files it matches" \
  python3 "$ws" --root "$sc" --paths 'docs/*.md'
says 0 "scope: a glob's * crosses /" "3 files" \
  python3 "$ws" --root "$sc" --paths '*.md' --exclude docs/bad.md
says 0 "scope: --exclude applies after the glob" "2 files" \
  python3 "$ws" --root "$sc" --paths 'docs/*.md' --exclude docs/bad.md
says 0 "scope: a literal and a glob naming one file select it once" "1 files" \
  python3 "$ws" --root "$sc" --paths CLAUDE.md --paths CLAUDE.md --paths '*.md' \
    --exclude 'docs/*'
says 0 "scope: a glob is not restricted to .md" "1 files" \
  python3 "$ws" --root "$sc" --paths 'docs/*.txt'
says 2 "scope: a literal naming no file names itself" "no such file" \
  python3 "$ws" --root "$sc" --paths CLAUDE.md --paths docs/gone.md
says 2 "scope: a glob matching nothing names itself" "matches no file" \
  python3 "$ws" --root "$sc" --paths 'docs/*.rst'
expect 2 "scope: --exclude emptying the scope refuses" \
  python3 "$ws" --root "$sc" --paths 'docs/*.md' --exclude 'docs/*'

# An entry is matched against the listing's root-relative form, so `./docs/*.md` must
# name what `docs/*.md` names, for --paths and --exclude alike, and an entry that
# reaches outside the root must refuse rather than read past it.
says 0 "scope: a ./ glob names what the listing names" "2 files" \
  python3 "$ws" --root "$sc" --paths './docs/*.md' --exclude './docs/bad.md'
says 0 "scope: a ./ literal and a doubled slash normalize" "2 files" \
  python3 "$ws" --root "$sc" --paths './CLAUDE.md' --paths 'docs//a.md'
says 2 "scope: an entry outside the root refuses" "not inside the root" \
  python3 "$ws" --root "$sc/docs" --paths '../CLAUDE.md'

# $sc above is a plain directory, so its globs exercise the walk. In a git checkout the
# pool is `git ls-files` instead, and only a real checkout can tell the two apart.
scg="$tmp/scope-git"
mkdir -p "$scg/docs"
printf '# A\n\nA rule and its mechanism.\n' > "$scg/docs/tracked.md"
printf '# B\n\nA rule and its mechanism.\n' > "$scg/docs/untracked.md"
printf '# C\n\nA rule and its mechanism.\n' > "$scg/docs/notes[draft].md"
git -C "$scg" init -q
git -C "$scg" add -- 'docs/tracked.md' 'docs/notes[draft].md'
says 0 "scope: in a checkout a glob selects tracked files only" "2 files" \
  python3 "$ws" --root "$scg" --paths 'docs/*.md'
says 0 "scope: a literal wins over reading its brackets as a class" "1 files" \
  python3 "$ws" --root "$scg" --paths 'docs/notes[draft].md'
says 2 "scope: a directory says to name the files under it" "a directory" \
  python3 "$ws" --root "$scg" --paths docs

# A check whose git call fails must refuse. Exiting 1 would reach the runner as
# "this check found something", and at rung warn that reads as a pass.
mkdir -p "$tmp/shim"
cat > "$tmp/shim/git" <<'SHIM'
#!/bin/sh
case "$1" in
  rev-parse) echo "$PWD"; exit 0 ;;
  ls-files)  echo "fatal: index file corrupt" >&2; exit 128 ;;
esac
exit 0
SHIM
chmod +x "$tmp/shim/git"
says 2 "scope: a failing git listing refuses, never exits 1" "ls-files failed" \
  env PATH="$tmp/shim:$PATH" python3 "$ws" --root "$scg" --paths 'docs/*.md'

# A tracked file deleted without `git rm` is still what the glob names; a literal
# naming it refuses, so the glob refuses too, rather than judging what is left.
rm "$scg/docs/tracked.md"
says 2 "scope: a tracked file gone from the tree refuses by name" "docs/tracked.md is tracked" \
  python3 "$ws" --root "$scg" --paths 'docs/*.md'

# Every check carries the scope helper verbatim, and only war-stories' copy is
# exercised above: the copies are held equal here, or a fix lands in one of five.
for c in "$here"/checks/*/check.py; do
  if ! diff -q <(sed -n '/^INDEX = os/,/^    return files$/p' "$ws") \
               <(sed -n '/^INDEX = os/,/^    return files$/p' "$c") >/dev/null; then
    printf 'FAIL  %-52s %s\n' "scope: the helper is identical across checks" "$c"
    exit 1
  fi
done
printf 'ok    %-52s\n' "scope: the helper is identical across checks"

# anchors reads markdown, so a glob narrows within that universe instead of dragging
# in files it cannot decode and refusing the whole gate.
an="$here/checks/anchors/check.py"
ab="$tmp/anchors-glob"
mkdir -p "$ab"
printf '<a id="t"></a>\n# T\n' > "$ab/a.md"
printf '\211PNG\r\n\032\n\0\0\0binary' > "$ab/img.png"
says 0 "anchors: a glob stays inside the markdown universe" "1 files" \
  python3 "$an" --root "$ab" --paths '*'

# The git adapter: inert without a config, and its export is judged before the checks
# are. An export that silently matched nothing would pass every commit green.
a="$tmp/adapter"

mkrepo "$a/inert"
printf '# T\n' > "$a/inert/README.md"
git -C "$a/inert" add -A
expect 0 "adapter: no config in the index" hook "$a/inert"
says 0 "adapter: says nothing was judged" "nothing judged" hook "$a/inert"

mkrepo "$a/narrow"
cp -R "$here/checks/anchors/fixtures/pass/clean/." "$a/narrow/"
printf '{"export": ["*.md", ".claude/*"], "checks": {"anchors": {"rung": "block"}}}' \
  > "$a/narrow/.claude/guards.json"
git -C "$a/narrow" add -A
expect 0 "adapter: a narrow export judges a clean tree" hook "$a/narrow"

mkrepo "$a/finding"
cp -R "$here/checks/anchors/fixtures/fail/dead-anchor/." "$a/finding/"
printf '{"export": ["*.md", ".claude/*"], "checks": {"anchors": {"rung": "block"}}}' \
  > "$a/finding/.claude/guards.json"
git -C "$a/finding" add -A
expect 1 "adapter: a narrow export still sees the finding" hook "$a/finding"
expect 1 "adapter: git commit refuses on a block finding" \
  git -C "$a/finding" commit -q -m refused

mkrepo "$a/drops-guards"
printf '# T\n' > "$a/drops-guards/README.md"
printf '{"export": ["*.md"], "checks": {"anchors": {"rung": "block"}}}' \
  > "$a/drops-guards/.claude/guards.json"
git -C "$a/drops-guards" add -A
expect 2 "adapter: an export dropping guards.json refuses" hook "$a/drops-guards"
says 2 "adapter: names the config the export dropped" "dropped .claude/guards.json" \
  hook "$a/drops-guards"

# A pathspec git rejects must be reported as itself. Without pipefail the pipeline
# reads only checkout-index's status, the export comes out empty, and the config-drop
# guard misattributes it to a list that is merely too narrow.
mkrepo "$a/bad-pathspec"
printf '# T\n' > "$a/bad-pathspec/README.md"
printf '{"export": [":(nosuchmagic)*.md", ".claude/*"], "checks": {"anchors": {"rung": "block"}}}' \
  > "$a/bad-pathspec/.claude/guards.json"
git -C "$a/bad-pathspec" add -A
says 2 "adapter: a pathspec git rejects is named as the cause" "check the pathspecs" \
  hook "$a/bad-pathspec"

mkrepo "$a/drops-threads"
printf '# T\n' > "$a/drops-threads/README.md"
printf '{"retroLogPath": ".claude/log.md"}' > "$a/drops-threads/.claude/threads.json"
printf '{"export": ["*.md", ".claude/guards.json"], "checks": {"anchors": {"rung": "block"}}}' \
  > "$a/drops-threads/.claude/guards.json"
git -C "$a/drops-threads" add -A
expect 2 "adapter: an export dropping threads.json refuses" hook "$a/drops-threads"

# The export is never a scope. A check takes its universe from the index listing the
# adapter hands over, so an export that half-covers a paths glob, drops a literal, drops
# a file in a default universe, or drops a discovered log refuses naming the file — a
# walk of the exported tree would judge the survivors and pass. A dropped file that
# exclude removes is not in scope and passes.
mkrepo "$a/half"
mkdir -p "$a/half/docs"
printf '# Good\n\nA rule and its mechanism.\n' > "$a/half/docs/good.md"
printf '# Bad\n\nAdded in this session after a redirect.\n' > "$a/half/docs/bad.md"
printf '<a id="t"></a>\n# T\n' > "$a/half/README.md"
printf '{"retroLogPath": "docs/log.md"}' > "$a/half/.claude/threads.json"
printf 'nothing\n' > "$a/half/docs/log.md"
half() {  # half <config json> — stage it and run the hook
  printf '%s' "$1" > "$a/half/.claude/guards.json"
  git -C "$a/half" add -A
  hook "$a/half"
}
says 2 "adapter: an export half-covering a paths glob refuses" "dropped docs/bad.md" \
  half '{"export": ["docs/good.md", ".claude/*"], "checks": {"war-stories": {"rung": "block", "paths": ["docs/*.md"]}}}'
says 2 "adapter: an export dropping a paths literal refuses" "dropped docs/bad.md" \
  half '{"export": ["docs/good.md", ".claude/*"], "checks": {"war-stories": {"rung": "block", "paths": ["docs/good.md", "docs/bad.md"]}}}'
says 2 "adapter: an export dropping a default-universe file refuses" "dropped README.md" \
  half '{"export": ["docs/*", ".claude/*"], "checks": {"anchors": {"rung": "block"}}}'
says 2 "adapter: an export dropping a discovered log refuses" "dropped docs/log.md" \
  half '{"export": ["docs/good.md", ".claude/*"], "checks": {"retro-log": {"rung": "block"}}}'
expect 0 "adapter: a dropped file exclude removes is out of scope" \
  half '{"export": ["docs/*", ".claude/*"], "checks": {"anchors": {"rung": "block", "exclude": ["README.md"]}}}'

# An export narrower than the link graph is not a broken link: anchors resolves a
# relative target against the index listing when the tree lacks it, and still reports
# a target that is in neither.
mkrepo "$a/links"
mkdir -p "$a/links/docs/img"
printf 'x' > "$a/links/docs/img/d.png"
printf '# T\n\nSee [the diagram](img/d.png), [its folder](img/), and [a note](note.txt).\n' > "$a/links/docs/a.md"
printf 'n\n' > "$a/links/docs/note.txt"
printf '{"export": ["*.md", ".claude/*"], "checks": {"anchors": {"rung": "block"}}}' \
  > "$a/links/.claude/guards.json"
git -C "$a/links" add -A
expect 0 "adapter: a link target the export dropped resolves by the index" hook "$a/links"
git -C "$a/links" rm -q --cached docs/note.txt
expect 1 "adapter: a link target in neither tree nor index is a finding" hook "$a/links"

# A linked worktree. A plain `git init` fixture cannot see either property below:
# in one, every path collapses onto the primary, so a wrong one still resolves.
w="$tmp/worktree"
mkrepo "$w/main"
cp -R "$here/checks/anchors/fixtures/pass/clean/." "$w/main/"
printf '{"export": ["*.md", ".claude/*"], "checks": {"anchors": {"rung": "block"}}}' \
  > "$w/main/.claude/guards.json"
git -C "$w/main" add -A
git -C "$w/main" commit -q -m base 2>/dev/null || { echo "FAIL  worktree: base commit"; exit 1; }
git -C "$w/main" worktree add -q "$w/side" -b side
cp -R "$here/checks/anchors/fixtures/fail/dead-anchor/." "$w/side/"
git -C "$w/side" add -A
expect 1 "worktree: the adapter judges the linked worktree's index" hook "$w/side"
expect 0 "worktree: the primary's index is untouched by it" hook "$w/main"

# The install line is `core.hooksPath guards-plugin/adapters/git`, relative: git
# resolves it against each worktree's own top level, so a worktree runs the adapter it
# carries. An absolute path would run the primary's copy from every worktree.
for wt in main side; do
  mkdir -p "$w/$wt/hooks"
  printf '#!/bin/sh\necho %s > "%s/ran"\nexit 1\n' "$wt" "$w" > "$w/$wt/hooks/pre-commit"
  chmod +x "$w/$wt/hooks/pre-commit"
done
git -C "$w/main" config core.hooksPath hooks
printf 'x\n' > "$w/side/marker.md"
git -C "$w/side" add -- marker.md
git -C "$w/side" commit -q -m x 2>/dev/null
if [ "$(cat "$w/ran" 2>/dev/null)" = side ]; then
  printf 'ok    %-52s\n' "worktree: a relative hooksPath runs its own hook"
else
  printf 'FAIL  %-52s ran %s\n' "worktree: a relative hooksPath runs its own hook" \
    "$(cat "$w/ran" 2>/dev/null)"
  exit 1
fi

echo "all cases passed"
