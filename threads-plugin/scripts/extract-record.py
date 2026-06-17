#!/usr/bin/env python3
"""
extract-record.py — distill a Claude Code session transcript into a compact
`asked -> did -> said` timeline for the /threads:retro command's fresh-context audit.

HARNESS-SPECIFIC (Claude Code). Requires Python 3.6+. Reads the session transcript
from $CLAUDE_CONFIG_DIR (default ~/.claude) and writes a small, reviewable timeline
to a temp file so a fresh-context sub-agent can judge the work cheaply. The command
invokes it via "${CLAUDE_PLUGIN_ROOT}/scripts/extract-record.py".

Usage:
    python3 extract-record.py [TRANSCRIPT.jsonl]

If TRANSCRIPT is omitted, resolves this session by id ($CLAUDE_CODE_SESSION_ID)
under <config>/projects (worktree-safe — never assumes the project dir). On any
failure it exits non-zero with an actionable message on stderr; the command surfaces
that to the user and falls back to the self-pass.

Writes the timeline to a temp file and prints its path + stats. Drops sub-agent
sidechains, tool-result payloads, and system-reminder turns; caps long turns so a
multi-hundred-KB transcript compresses to a few KB.
"""
import sys, os, json, glob, tempfile


def fail(msg):
    """Exit non-zero with a prefixed, actionable message on stderr."""
    sys.stderr.write("extract-record: " + msg + "\n")
    raise SystemExit(1)


def config_dir():
    # Honor a relocated Claude config dir; default to ~/.claude.
    return os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")


def resolve_transcript():
    if len(sys.argv) > 1:
        path = sys.argv[1]
        if not os.path.isfile(path):
            fail("transcript path not found: " + path)
        return path
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if not sid:
        fail("CLAUDE_CODE_SESSION_ID is not set and no transcript path was given — "
             "this client did not expose the session id. Pass a transcript path as an "
             "argument, or run the self-pass only.")
    base = os.path.join(config_dir(), "projects")
    hits = glob.glob(os.path.join(base, "**", sid + ".jsonl"), recursive=True)
    if not hits:
        fail("no transcript found for session " + sid + " under " + base +
             " — if your Claude data lives elsewhere, set CLAUDE_CONFIG_DIR.")
    return hits[0]


def short(s, n):
    s = " ".join(str(s).split())
    return s[:n] + ("…" if len(s) > n else "")


def main():
    src = resolve_transcript()
    rows = []
    with open(src, encoding="utf-8", errors="replace") as f:
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
        mode="w", encoding="utf-8", suffix=".md", prefix="retro-record-", delete=False)
    with out:
        for tag, body in rows:
            out.write(f"{tag}: {body}\n")
    print(f"source: {src}")
    print(f"record: {out.name} ({os.path.getsize(out.name)} bytes, {len(rows)} events)")


if __name__ == "__main__":
    main()
