#!/usr/bin/env bash
# checks — prove every check on its fixtures and the runner on its contract.
# Prints one line per case with the expected and observed exit code; exits 1 on
# the first wrong one.
#
# Fixture layout: checks/<id>/fixtures/{pass,fail}/<case>/ is a mini tree handed to
# the check as --root. A case may carry an `args` file, one argument per line,
# appended to the invocation (how a check whose universe is --paths names them).

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
  expect 2 "$id refuses: no files in scope" \
    python3 "$check/check.py" --root "$tmp/empty-$id" --paths absent.md
done

# The runner: config absent, malformed, unknown id, rungs, and a refused check.
r="$tmp/runner"
mkdir -p "$r/.claude"
expect 0 "runner: no config" python3 "$here/run.py" --root "$r"

printf '{' > "$r/.claude/checks.json"
expect 2 "runner: malformed config" python3 "$here/run.py" --root "$r"

printf '{"checks": {"no-such-check": {"rung": "warn"}}}' > "$r/.claude/checks.json"
expect 2 "runner: unknown check id" python3 "$here/run.py" --root "$r"

cp -R "$here/checks/anchors/fixtures/fail/dead-anchor/." "$r/"
printf '{"checks": {"anchors": {"rung": "block"}}}' > "$r/.claude/checks.json"
expect 1 "runner: block finding refuses" python3 "$here/run.py" --root "$r"

printf '{"checks": {"anchors": {"rung": "warn"}}}' > "$r/.claude/checks.json"
expect 0 "runner: warn finding passes" python3 "$here/run.py" --root "$r"
python3 "$here/run.py" --root "$r" 2>/dev/null | grep -q '^warn anchors: ' \
  || { echo "FAIL  runner: warn finding is printed with its prefix"; exit 1; }
printf 'ok    %-52s\n' "runner: warn finding is printed with its prefix"

printf '{"checks": {"anchors": {"rung": "warn", "exclude": ["*.md"]}}}' > "$r/.claude/checks.json"
expect 2 "runner: refused check refuses regardless of rung" python3 "$here/run.py" --root "$r"

echo "all cases passed"
