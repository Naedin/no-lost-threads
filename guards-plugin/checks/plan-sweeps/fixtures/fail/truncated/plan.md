# A slice

## Claim ledger

- fallback writers are doc comments only — `rg -n '\.fallback' src | head -20`
- a count off the tail — `rg -n 'let' src | sort | tail -n 3 | wc -l` → 3
- by path — `rg -n 'let' src|/usr/bin/head`
