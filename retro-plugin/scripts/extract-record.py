#!/usr/bin/env python3
"""
extract-record.py — distill a Claude Code session transcript into a compact
`asked -> did -> said` timeline for the /retro command's fresh-context audit (its default pass).

HARNESS-SPECIFIC (Claude Code). This turns a raw session record into a small,
reviewable timeline so a fresh-context sub-agent can judge the work cheaply. The
/retro command invokes it via "${CLAUDE_PLUGIN_ROOT}/scripts/extract-record.py".

Usage:
    python3 extract-record.py [TRANSCRIPT.jsonl]

If TRANSCRIPT is omitted, resolves this session by id ($CLAUDE_CODE_SESSION_ID)
under ~/.claude/projects (worktree-safe — never assumes the project dir).

Writes the timeline to a temp file and prints its path + stats. Drops sub-agent
sidechains, tool-result payloads, and system-reminder turns; caps long turns so a
multi-hundred-KB transcript compresses to a few KB.
"""
import sys, os, json, glob, tempfile


def resolve_transcript():
    if len(sys.argv) > 1:
        return sys.argv[1]
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if not sid:
        sys.exit("no transcript path given and CLAUDE_CODE_SESSION_ID is unset")
    hits = glob.glob(os.path.expanduser(f"~/.claude/projects/**/{sid}.jsonl"),
                     recursive=True)
    if not hits:
        sys.exit(f"no transcript found for session {sid}")
    return hits[0]


def short(s, n):
    s = " ".join(str(s).split())
    return s[:n] + ("…" if len(s) > n else "")


def main():
    src = resolve_transcript()
    rows = []
    with open(src) as f:
        for line in f:
            try:
                o = json.loads(line)
            except Exception:
                continue
            if o.get("isSidechain"):          # sub-agent turns live elsewhere
                continue
            t = o.get("type")
            c = (o.get("message") or {}).get("content")
            if t == "user":
                txt = c if isinstance(c, str) else (
                    "\n".join(b.get("text", "") for b in c
                              if isinstance(b, dict) and b.get("type") == "text")
                    if isinstance(c, list) else "")
                txt = txt.strip()
                if txt and not txt.startswith("<"):   # drop system-reminder / tool-result-only turns
                    rows.append(("USER ↦", short(txt, 1200)))
            elif t == "assistant" and isinstance(c, list):
                for b in c:
                    if not isinstance(b, dict):
                        continue
                    if b.get("type") == "text" and b.get("text", "").strip():
                        rows.append(("  SAID", short(b["text"], 700)))
                    elif b.get("type") == "tool_use":
                        inp = b.get("input") or {}
                        key = (inp.get("file_path") or inp.get("command")
                               or inp.get("pattern") or inp.get("prompt")
                               or inp.get("description") or "")
                        rows.append(("  DID ", f"{b.get('name')}({short(key, 100)})"))

    out = tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", prefix="retro-record-", delete=False)
    with out:
        for tag, body in rows:
            out.write(f"{tag}: {body}\n")
    print(f"source: {src}")
    print(f"record: {out.name} ({os.path.getsize(out.name)} bytes, {len(rows)} events)")


if __name__ == "__main__":
    main()
