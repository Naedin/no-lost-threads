# Docs

Run `scripts/run.sh --apply` or `./scripts/run.sh`, then `/go`, `/go now`,
`/threads:retro`, and `/code-review high`. The knob `MYAPP_MODE=lab scripts/run.sh`
and the bare prefix `MYAPP_` both occur in code; `MYAPP_LANE` too. A prose path
/tmp/x or scripts/gone.sh is not read; a span `scripts/<name>.sh` is a placeholder,
`scripts/…` too, and `scripts/*.sh` matches. Not a command: `/tmp/look.png`.
A fenced block is not read:

```
scripts/gone.sh
```

Directory: `scripts/`? No — `.claude/commands` is a dir; so is `scripts`.
