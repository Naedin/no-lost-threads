# A slice

## Claim ledger

- all four writers — `rg -n '\.fallback' src` — `a.swift:1–2`, `:4`, `b.swift:1`
- the same four, other spellings — `rg -n '\.fallback' src` — `src/a.swift:1/2/4`; `b.swift:1: let third = .fallback`
- the same four, a bare line number — `rg -n '\.fallback' src` — `a.swift:1`, `2`, `4`, `b.swift:1`
- the same four, by file — `rg -n '\.fallback' src` → `a` × 3, `b.swift`
- the same four, the listing wrapped — `rg -n '\.fallback' src` — `a.swift:1,2,4`,
  `b.swift:1`
- only these, the plan's own lines not counted — `rg -n 'fallback' src plan.md` — `a.swift:1,2,4`, `b.swift:1`
- a witness, no population stated — `rg -n '\.fallback' src` — `a.swift:1`
- a pH-only word, and a quantifier (all of them) inside a parenthetical — `rg -n '\.fallback' src` — `a.swift:1`
- two writers, but a count sweep lists no lines — `rg -c '\.fallback' src` — `a.swift:1`
- two writers, the listing not directly after the sweep — `rg -n '\.fallback' src` — see `a.swift:1`

## Acceptance Criteria

1. Only one writer remains — `rg -n '\.fallback' src` — `a.swift:1`
