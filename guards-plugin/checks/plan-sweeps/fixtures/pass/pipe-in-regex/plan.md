# A slice

A `|` inside quotes is regex alternation, not a pipe: `rg -n 'fallback|head' src`.
`||` is not a pipe either, and a chain is skipped, never run: `rg -n foo src || tail x`.
