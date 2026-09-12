# A slice

## Claim ledger

- fallback writers, read off a truncated listing — `rg -n '\.fallback' src` — 2 hits
- fallback files — `rg -ln '\.fallback' src` — 3 files
- a bound that does not hold — `rg -n 'nothing-like-this' src` → ≥1 hit
- through wc — `rg -n '\.fallback' src | wc -l` → 4
- wrapped: `rg -n 'let' src`
  → 5 hits
