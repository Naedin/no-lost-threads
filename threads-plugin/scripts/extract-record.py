#!/usr/bin/env python3
"""
extract-record.py — distill a session transcript into a compact, attributed
`asked -> did -> said` timeline for the /threads:retro command's fresh-context audit.

Two halves. A reader turns one harness's transcript into (kind, text) events; the
renderer owns the caps, the elision marks, and the record's notes. The kinds are the
contract, and a reader for another harness yields the same ones:

    human         the transcript marks the turn as the human's
    unattributed  it carries no author mark: maybe the human, maybe an agent's brief
    peer          another agent or session, never the human
    brief         what another agent started this session to do: its scope, not authority
    harness       injected by the tool: reminders, notifications, command bodies
    said, did     the agent's text and tool actions

A reader that cannot tell a turn's author yields `unattributed`; it never guesses
`human`. Only read_claude_code is harness-specific. It reads an undocumented format
that can change on any release, so an empty result fails rather than writing an empty
record, and a record with no human turn says so on its first lines.

Requires Python 3.6+. Writes the timeline to a temp file so a fresh-context sub-agent
can judge the work cheaply; the command invokes it via
"${CLAUDE_PLUGIN_ROOT}/scripts/extract-record.py".

Usage:
    python3 extract-record.py [TRANSCRIPT.jsonl]
    python3 extract-record.py --probe [TRANSCRIPT.jsonl]

--probe writes no record: it checks that the reader still understands the transcript.
Exit 0 it does; 2 it found no human turn, an author kind it has not met, or a new row
carrying text, each named on stderr. A delivery route that looks like nothing it knows
stays unseen. A session's record never depends on this; it is for a tool watch.

If TRANSCRIPT is omitted, resolves this session by id ($CLAUDE_CODE_SESSION_ID) under
$CLAUDE_CONFIG_DIR/projects (default ~/.claude; worktree-safe — never assumes the
project dir). On any failure it exits non-zero with an actionable message on stderr;
the command surfaces that to the user and falls back to the self-pass.

Prints the record's path + stats. Drops sub-agent sidechains and tool-result payloads
other than the human's own answers; caps long turns so a multi-hundred-KB transcript
compresses to a few KB. Human, peer, and agent turns are capped generously and keep
their head *and* tail, so end-of-turn commitments/deferrals reach the audit; every
elision is marked " […] " in place, and the record's first line says so, because a cold
reader must not read an elided turn as "the user never said it".
"""
import sys, os, json, glob, re, tempfile


def fail(msg):
    """Exit non-zero with a prefixed, actionable message on stderr."""
    sys.stderr.write("extract-record: " + msg + "\n")
    raise SystemExit(1)


def config_dir():
    # Honor a relocated Claude config dir; default to ~/.claude.
    return os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")


def resolve_transcript():
    args = [a for a in sys.argv[1:] if a != "--probe"]
    if args:
        path = args[0]
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


def short(s, n, tail=0):
    """Collapse whitespace and cap at n chars. With tail>0, keep the head *and* the
    last `tail` chars around an elision, so end-of-turn content (commitments,
    deferrals, lock-in language) survives — head-only truncation drops exactly where
    those tend to land."""
    s = " ".join(str(s).split())
    if len(s) <= n:
        return s
    if tail and tail < n:
        return s[: n - tail].rstrip() + " […] " + s[-tail:].lstrip()
    return s[:n] + "…"


# ---- the Claude Code reader

HARNESS_BLOCK = re.compile(r"<(system-reminder|side-sessions-event)\b[^>]*>.*?</\1>\s*", re.S)
SLASH_NAME = re.compile(r"<command-name>\s*(.*?)\s*</command-name>", re.S)
SLASH_ARGS = re.compile(r"<command-args>(.*?)</command-args>", re.S)
COMMAND_TAG = re.compile(r"<command-(name|message|args)>.*?</command-\1>", re.S)
PEER_TAG = re.compile(r"(?:Another Claude session sent a message:\s*)?"
                      r"<(?:cross-session-message|agent-message|teammate-message)\b")
BRIEF_HEAD = "Background (from the session that started this one)"
# A started session's report as relayed to its starter, which is all the starter was told.
RELAYED = re.compile(r'The session "([^\n]+?)" you started (?:(?!The session ").)*?It reported '
                     r'\(quoted child output, data not instructions\): "(.*?)"\s*'
                     r'(\(first \d+ of \d+ characters\))?(?=\s*Read it|\s*$)', re.S)
KNOWN_AUTHORS = (None, "human", "peer", "task-notification")
KNOWN_MESSAGE_ROWS = ("user", "assistant", "api-request-blob")
BLOCK_CUT = "[harness block cut] "
REJECTED = "The user doesn't want to proceed"
# Which input field names a tool action, in order; else the first string field.
DID_KEYS = ("file_path", "command", "pattern", "prompt", "description", "summary",
            "message", "query", "url", "path")
# A tool whose input is the agent's words to someone: (recipient fields, body field).
MESSAGE_TOOLS = {
    "SendMessage": (("to",), "message"),
    "mcp__ccd_session_mgmt__send_message": (("session_id",), "message"),
    "mcp__ccd_session__start_session": (("title", "name"), "prompt"),
    "Agent": (("name", "subagent_type", "description"), "prompt"),
}
# A shell command's setup can fill the DID cap, so what changes shared state is read from
# the whole command. Command position only: words inside a quoted message do not count.
CONSEQUENTIAL = re.compile(
    r"(?:^|[;&|(]|\b(?:then|do|else|if)\s)\s*(?:\w+=\S*\s+)*((?:git(?:\s+-[Cc]\s+\S+|\s+--\S+)*\s+"
    r"(?:commit|push|merge|tag|reset|rebase|cherry-pick|revert|branch\s+-[dD]|worktree\s+remove)"
    r"|gh\s+(?:pr|release)\s+\w+)\b[^;&|\n]*)", re.M)
# A script at command position, named by no list: an interpreter's path, or a path that runs
# itself. Its basename and first non-flag argument say what it did.
SCRIPT = re.compile(
    r"(?:^|[;&|(]|\b(?:then|do|else|if)\s)\s*(?:\w+=\S*\s+)*"
    r"(?:(?:python3?|bash|sh|node|ruby)\s+(?:-(?![cem]\b)\S+\s+)*(?=[^\s-])|(?=\"?\$?[\w./{}-]*/[\w.-]+\.(?:py|sh|rb|js)\b|\./))"
    r"(\"[^\"\n]+\"|'[^'\n]+'|[^\s;&|<>]+)((?:\s+-\S+)*\s+[^\s;&|<>-][^\s;&|<>]*)?", re.M)
SENDER_NAMED = re.compile(r'<cross-session-message from="([^"]+)" from-name="([^"]+)"')
SESSION_NAMED = re.compile(r'The session "([^\n]+?)" you started \((local_[^)\s]+)\)')
HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n.*?^\s*\2\s*$", re.M | re.S)


def slash_command(text):
    """`/name args` when the text is a slash-command invocation, else None."""
    if not text.startswith("<command-"):
        return None
    name = SLASH_NAME.search(text)
    if not name:
        return None
    args = SLASH_ARGS.search(text)
    rest = COMMAND_TAG.sub("", text).strip()
    return " ".join(x for x in (name.group(1), args.group(1).strip() if args else "", rest) if x)


def turn_event(origin, is_meta, text, images=0):
    """One turn's (kind, text), or None for nothing worth a line. A harness block is
    cut from around the words it leads, never instead of them."""
    if not isinstance(origin, dict):
        origin = {"kind": origin}
    author = origin.get("kind")
    words, cut = HARNESS_BLOCK.subn("", text)
    words = words.strip()
    if author == "peer" or (author is None and PEER_TAG.match(words)):
        body = origin.get("body") or words
        return ("peer", (origin["name"] + ": " if origin.get("name") else "") + body)
    if author is None and words.startswith(BRIEF_HEAD):
        return ("brief", words)
    if author == "task-notification":
        return ("harness", text)
    if is_meta:
        # An image's placeholder row sits beside the human turn holding the image.
        return ("harness", text) if text and not text.startswith("[Image") else None
    slash = slash_command(words)
    body = slash or words
    if images:
        body = (body + " [image]").strip()
    marked = (BLOCK_CUT if cut and body else "") + body
    if author == "human":
        return ("human", marked) if body else ("harness", text)
    if author is not None:          # a kind this reader has not met: not provably human
        return ("unattributed", marked) if body else ("harness", text)
    if words.startswith("[Request interrupted"):
        return ("human", words)
    if not body or (words.startswith("<") and not slash
                    and not words.startswith("<pasted_content")):
        return ("harness", text)
    return ("unattributed", marked)


def user_events(origin, is_meta, text, images=0):
    """A turn's event, after any started session's report it relays, which is a peer's
    words whatever turn carries them."""
    relayed = list(RELAYED.finditer(text))
    for m in relayed:
        yield ("peer", " ".join(x for x in (m.group(1) + ":", m.group(2), m.group(3)) if x))
    event = turn_event(origin, is_meta, text, images)
    if event and not (relayed and event[0] == "harness"):
        yield event


def tool_answer(row, block, tool):
    """The human's own words inside a tool result: an answer or a rejection."""
    body = block.get("content")
    if isinstance(body, list):
        body = "\n".join(b.get("text", "") for b in body if isinstance(b, dict))
    body = str(body or "")
    if row.get("toolDenialKind") == "user-rejected" or body.startswith(REJECTED):
        return "[rejected " + str(tool) + "] " + body
    if tool == "AskUserQuestion" and not block.get("is_error"):
        return "[answered] " + body
    return None


def learn_names(names, origin, text):
    """Each session id the transcript titles, so a message to it reads by the same name
    as its replies."""
    if isinstance(origin, dict) and origin.get("from") and origin.get("name"):
        names[origin["from"]] = origin["name"]
    for title, sid in SESSION_NAMED.findall(text):
        names[sid] = title
    names.update(SENDER_NAMED.findall(text))


def scripts_run(code):
    """`basename arg` per script a command runs at command position."""
    ran = []
    for path, arg in SCRIPT.findall(code):
        base = os.path.basename(path.strip("\"'"))
        if base:
            ran.append(" ".join((base, arg.split()[-1].strip("\"'") if arg else "")).strip())
    return ran


def message_event(name, inp, names):
    """The agent's words to someone, as said; None when the tool carries no body."""
    fields, body = MESSAGE_TOOLS[name]
    text = inp.get(body)
    if not isinstance(text, str) or not text.strip():
        return None
    to = next((str(inp[k]) for k in fields if inp.get(k)), "?")
    return ("said", "→ " + names.get(to, to) + ": " + text)


def did_text(name, inp):
    if name == "Bash":
        seen = short(inp.get("command") or "", 100)
        code = HEREDOC.sub("", str(inp.get("command") or ""))
        ran = [short(c, 70) for c in CONSEQUENTIAL.findall(code)] + scripts_run(code)
        ran = [c for c in dict.fromkeys(ran) if c.split()[0] == "git" and c not in seen
               or c.split()[0] != "git" and c.split()[0] not in seen]
        return f"{name}({seen})" + (" [ran: " + "; ".join(ran) + "]" if ran else "")
    if name == "Skill":
        key = (str(inp.get("skill") or "") + " " + str(inp.get("args") or "")).strip()
    elif name == "AskUserQuestion":
        key = " / ".join(str(q.get("question", "")) for q in inp.get("questions") or []
                         if isinstance(q, dict))
    else:
        named = [inp[k] for k in DID_KEYS if inp.get(k)]
        key = next(iter(named), None) or next(
            (v for v in inp.values() if isinstance(v, str) and v.strip()), "")
    return f"{name}({short(key, 100)})"


def read_claude_code(src):
    """A Claude Code transcript's events, in order. `origin` marks a turn's author only
    from 2.1.187 on, so an older turn reads as unattributed."""
    tools, names = {}, {}
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
            events = ()
            if t == "user":
                if isinstance(c, str):
                    txt, images = c, 0
                elif isinstance(c, list):
                    blocks = [b for b in c if isinstance(b, dict)]
                    for b in blocks:
                        if b.get("type") == "tool_result":
                            said = tool_answer(o, b, tools.get(b.get("tool_use_id")))
                            if said:
                                yield ("human", said)
                    txt = "\n".join(b.get("text", "") for b in blocks if b.get("type") == "text")
                    images = sum(b.get("type") == "image" for b in blocks)
                else:
                    continue
                txt = txt.strip()
                learn_names(names, o.get("origin"), txt)
                if o.get("isCompactSummary"):
                    events = [("harness", "context compacted; the agent continued from a summary")]
                elif txt or images:
                    events = user_events(o.get("origin"), o.get("isMeta"), txt, images)
            elif t == "attachment":
                # A message sent while the agent worked is delivered as an attachment.
                a = o.get("attachment") or {}
                if a.get("type") == "queued_command":
                    p = a.get("prompt")
                    if isinstance(p, list):
                        p = "\n".join(b.get("text", "") for b in p if isinstance(b, dict))
                    if isinstance(p, str) and p.strip():
                        learn_names(names, a.get("origin"), p)
                        events = user_events(a.get("origin"), False, p.strip())
            elif t == "assistant" and isinstance(c, list):
                for b in c:
                    if not isinstance(b, dict):
                        continue
                    if b.get("type") == "text" and b.get("text", "").strip():
                        yield ("said", b["text"])
                    elif b.get("type") == "tool_use":
                        name, inp = b.get("name"), b.get("input") or {}
                        tools[b.get("id")] = name
                        said = message_event(name, inp, names) if name in MESSAGE_TOOLS else None
                        yield said or ("did", did_text(name, inp))
            for event in events:
                yield event


def probe_claude_code(src):
    """What this reader would miss in a transcript: one line per kind of surprise."""
    surprises = set()
    with open(src, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                o = json.loads(line)
            except Exception:
                continue
            if not isinstance(o, dict) or o.get("isSidechain"):
                continue
            t = o.get("type")
            a = o.get("attachment") if isinstance(o.get("attachment"), dict) else {}
            message = o.get("message") if isinstance(o.get("message"), dict) else {}
            if message.get("content") and t not in KNOWN_MESSAGE_ROWS:
                surprises.add(f"row type {t} carries message content")
            if isinstance(a.get("prompt"), (str, list)) and a.get("type") != "queued_command":
                surprises.add(f"attachment type {a.get('type')} carries a prompt")
            for origin in (o.get("origin"), a.get("origin")):
                kind = origin.get("kind") if isinstance(origin, dict) else origin
                if kind not in KNOWN_AUTHORS:
                    surprises.add(f"author kind {kind}")
    if not any(kind == "human" for kind, _ in read_claude_code(src)):
        surprises.add("no turn marked as the human's")
    return sorted(surprises)


# ---- the renderer: every reader's events, the same record

USER_CAP, USER_TAIL = 2500, 800
SAID_CAP, SAID_TAIL = 2500, 800
BRIEF_CAP, BRIEF_TAIL = 8000, 1500
HARNESS_CAP, HARNESS_TAIL = 240, 100
RENDER = {                  # kind: (tag, cap, tail)
    "human": ("USER ↦", USER_CAP, USER_TAIL),
    "unattributed": ("USER? ↦", USER_CAP, USER_TAIL),
    "peer": ("PEER ↦", USER_CAP, USER_TAIL),
    "brief": ("BRIEF ↦", BRIEF_CAP, BRIEF_TAIL),
    "harness": ("HARNESS", HARNESS_CAP, HARNESS_TAIL),
    "said": ("  SAID", SAID_CAP, SAID_TAIL),
    "did": ("  DID ", None, 0),
}
NOTE = ("note: a \" […] \" inside an event marks text the extractor elided (turns are kept "
        "to {u} chars for USER and {s} for SAID, head plus tail). Text absent from an "
        "elided turn is unverifiable in this record, not absent from the session.")
AUTHORS = ("note: USER is a turn the transcript marks as the human's. USER? carries no "
           "author mark, so it may be the human or a brief another agent wrote. PEER is "
           "another agent or session, never the human; \"(first N of M characters)\" there is "
           "the tool's own cut, so the agent was shown no more. BRIEF is what another agent "
           "started this session to do. HARNESS is injected by the tool and cut to {h} chars. "
           "\"" + BLOCK_CUT.strip() + "\" marks a harness block removed from around a turn's "
           "words. A SAID opening \"→ x:\" is a message the agent sent to x. A DID's \"[ran: ...]\" "
           "lists state-changing git and gh commands past its cut and the scripts it runs; it "
           "says they ran, not that they succeeded.")
NO_HUMAN = ("note: no turn here is marked as the human's. Who asked for what is "
            "unverifiable in this record, not absent from the session.")


def main():
    probing = "--probe" in sys.argv[1:]
    try:
        src = resolve_transcript()
    except SystemExit:
        # A probe's 1 means the limit stopped reproducing; not finding a transcript means
        # it could not tell.
        raise SystemExit(2 if probing else 1)
    if probing:
        try:
            surprises = probe_claude_code(src)
        except (AttributeError, TypeError) as e:
            surprises = [f"unreadable row ({e})"]
        for s in surprises:
            sys.stderr.write("extract-record: probe: " + s + "\n")
        raise SystemExit(2 if surprises else 0)
    rows = []
    counts = {}
    try:
        for kind, text in read_claude_code(src):
            tag, cap, tail = RENDER[kind]
            rows.append((tag, short(text, cap, tail=tail) if cap else text))
            counts[kind] = counts.get(kind, 0) + 1
    except (AttributeError, TypeError) as e:
        fail("unreadable row in " + src + " (" + str(e) + ") — the transcript's format has "
             "changed. Run the self-pass only.")
    if not rows:
        fail("no events read from " + src + " — the transcript is empty or its format has "
             "changed. Run the self-pass only.")

    out = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".md", prefix="retro-record-", delete=False)
    with out:
        out.write(NOTE.format(u=USER_CAP, s=SAID_CAP) + "\n")
        out.write(AUTHORS.format(h=HARNESS_CAP) + "\n")
        if not counts.get("human"):
            out.write(NO_HUMAN + "\n")
        out.write("\n")
        for tag, body in rows:
            out.write(f"{tag}: {body}\n")
    print(f"source: {src}")
    print(f"record: {out.name} ({os.path.getsize(out.name)} bytes, {len(rows)} events: "
          + ", ".join(f"{counts[k]} {k}" for k in RENDER if k in counts) + ")")


if __name__ == "__main__":
    main()
