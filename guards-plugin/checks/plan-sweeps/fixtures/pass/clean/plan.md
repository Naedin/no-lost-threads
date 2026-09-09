# A slice

## Acceptance

- [ ] the symbol is gone — verified by: `rg -n 'targetPrograms|LegacyPlan' src --glob '*.swift'`
- [ ] no hit at all — verified by: `rg -c 'nothing-like-this' src`
- [ ] anchored — verified by: `rg -n '^let role = \.fallback$' src/a.swift`
- prose mentioning rg -E outside a span is not read
