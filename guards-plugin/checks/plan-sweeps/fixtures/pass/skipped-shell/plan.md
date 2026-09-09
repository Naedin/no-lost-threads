# A slice

A chain is skipped, never run: `rg -E src; echo $?` and `rg -n foo src | wc -l` and
`rg -n foo src > out.txt` and `rg -n "$PATTERN" src` and `rg -n foo src/*.swift` and
`rg -n --pre cat foo src` and `rg -nz foo src`. A span not beginning `rg ` is not a
sweep: `git grep -E`. A fenced block is not read:

```
rg -E
```
