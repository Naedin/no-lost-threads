# A slice

## Claim ledger

- drafted at abc1234, 2026-09-11 — 6 sites opened (unverified: 0)
  - the role lives — `rg -n 'let role' src/a.swift` — 1:let role = .fallback
  - fallback writers — `rg -n '\.fallback' src` — 3 hits
  - fallback files — `rg -ln '\.fallback' src` — 2 files
  - fallback files, counted from a line sweep — `rg -n '\.fallback' src` → 2 files
  - per-file counts summed — `rg -c '\.fallback' src` → 3 hits
  - per-file counts as files — `rg -c '\.fallback' src` → 2 files
  - matches, not lines — `rg -o 'fallback' src/a.swift` → 2 matches
  - bare after the arrow — `rg -n 'targetPrograms' src` → 1
  - today — `rg -n 'targetPrograms' src` → 1 today; the tests after
  - bold — `rg -n 'nothing-like-this' src` → **0 hits** (exit 1)
  - a bound — `rg -n '\.fallback' src` → ≥1 hit
  - an adjective — `rg -n '\.fallback' src` → 3 code hits, all in src
  - two words — `rg -n '\.fallback' src` — 3 call sites
  - in parentheses (`rg -n 'let' src` — 3 hits): every declaration
  - counted through wc — `rg -n '\.fallback' src | wc -l` → 3
  - a before/after pair is not a count — `rg -n 'let' src` → no hits after (3 → 0)
  - a line number is not a count — `rg -n 'let other' src/a.swift` — 2:let other = .fallback
  - a number with a trailing colon in prose — `rg -n 'let' src` — 9: nine is not a count either
  - a count not directly adjacent is not read — `rg -n 'let' src` finds the declarations, 40 of them

## Scope

The census, wrapped so the count starts the next line: `rg -n '\.fallback' src`
→ 3 hits, every one a writer.

Two spans on one line, each with its own count: `rg -n 'let' src` → 3 hits and `rg -ln 'let' src` → 2 files.

## Acceptance Criteria <!-- slices: acceptance -->

1. Retired: `rg -n '\.fallback' src` → 0 hits, exit 1. Liveness pair: `rg -n 'let' src` → ≥1 hit.
2. Files: `rg -ln '\.fallback' src` → 0 files.
