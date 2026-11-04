"""Read a Claude Code transcript, turn its tail into a short 'where was I' card, store cards."""
import glob
import json
import os
import re
import tempfile

CARD_DIR = os.path.expanduser(os.environ.get("CAVEWALL_DIR", "~/.claude/cavewall"))

_NOISE = ("<command-name>", "<local-command", "<command-message>", "<system-reminder>", "Caveat:")


def _text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content
                         if isinstance(b, dict) and b.get("type") == "text")
    return ""


def transcript_tail(path, max_messages=12, max_chars=1500):
    """Last human/assistant text messages as (role, text). Tool calls and results are dropped."""
    out = []
    try:
        f = open(path, encoding="utf-8", errors="replace")
    except OSError:
        return out
    with f:
        for line in f:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            role = d.get("type")
            if role not in ("user", "assistant") or d.get("isSidechain"):
                continue
            text = _text_of((d.get("message") or {}).get("content")).strip()
            if not text or text.startswith(_NOISE):
                continue
            out.append((role, text[-max_chars:]))
    return out[-max_messages:]


PROMPT = """You maintain a status card for one of many parallel Claude Code sessions a developer runs.
The developer reads the card to switch context fast. Be terse, concrete, no filler, no dashes.
Return ONLY a JSON object with these keys:
  "goal":      what the developer wants from this session, max 10 words
  "state":     where it stands right now, max 15 words (name PRs, tests, branches)
  "next":      the very next action and who does it, max 12 words
  "needs_you": true if the session is waiting for the developer (a question, a decision,
               a review, a failing step only they can fix), else false
  "reason":    if needs_you, what exactly they must answer or do, max 15 words, else ""

Rules:
- The message marked LATEST decides "state", "next" and "needs_you". Older messages only explain
  the goal. Todos and questions that the latest message shows as finished or answered are gone.
- If the latest assistant message reports finished work and asks nothing, set needs_you false and
  next to "nothing, done" or to what others still do (e.g. "CI running", "awaiting review").
- A closing status line like "Implemented: 🟢 Committed: 🟢 Pushed: 🟢 PR: 🟢 Replied to comments: 🔴"
  is a report, not a question. A red dot there means "not done or not needed", never a todo for the
  developer by itself. Put the PR number into "state".
- needs_you is true only if the latest assistant message asks the developer something or says they
  must act. An optional offer ("say X if you want", "I can also do Y") is not a question: needs_you false.
- If the developer's latest message wraps up the session ("done", "we good", "thanks, that's it"),
  the session is finished: needs_you false, next "nothing, done".

Session folder: {cwd}
Recent conversation (oldest first):
{conversation}
"""


def build_prompt(tail, cwd):
    last_assistant = max((i for i, (r, _) in enumerate(tail) if r == "assistant"), default=-1)
    convo = "\n\n".join(
        f"[{'LATEST ' if i == last_assistant else ''}{r.upper()}] {t}" for i, (r, t) in enumerate(tail))
    return PROMPT.format(cwd=cwd, conversation=convo)


_FINISHED = re.compile(r"Implemented:\s*🟢")


def settle(card, tail):
    """Fixed rule after the model: a finished task (status line 'Implemented: 🟢') whose closing
    message asks nothing (no '?') does not need the developer, even if it offers an extra."""
    if not tail or tail[-1][0] != "assistant":
        return card  # the developer spoke last: the model's reading stands
    last = tail[-1][1]
    if _FINISHED.search(last) and "?" not in last and card.get("needs_you"):
        card = dict(card, needs_you=False, reason="")
        if card.get("next") and not card["next"].startswith("optional: "):
            card["next"] = "optional: " + card["next"]
    return card


def is_stale(card_mtime, transcript_mtime, grace=60):
    """Card misses newer conversation (grace absorbs bookkeeping lines written after a turn)."""
    return card_mtime is not None and transcript_mtime - card_mtime > grace


_FIELDS = {"goal": "", "state": "", "next": "", "needs_you": False, "reason": ""}


def parse_card(raw):
    m = re.search(r"\{.*\}", raw or "", re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    card = {k: data.get(k, v) for k, v in _FIELDS.items()}
    card["needs_you"] = card["needs_you"] is True
    return card


def empty_kind(path):
    """'cleared' (only /clear so far), 'fresh' (nothing yet) or None (real conversation)."""
    if transcript_tail(path, max_messages=1):
        return None
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return "cleared" if "<command-name>/clear</command-name>" in f.read() else "fresh"
    except OSError:
        return "fresh"


EMPTY_CARDS = {
    "fresh": "🌱 fresh start, no task yet",
    "cleared": "🧹 cleared, ready for a new hunt",
}


def mark_reset(directory, session_ids, branch):
    """After a main checkout reset, its sessions' old task cards are no longer true."""
    import datetime
    for sid in session_ids:
        write_card(directory, sid, {
            "goal": f"🧹 reset to {branch}, ready for a new hunt", "state": "", "next": "",
            "needs_you": False, "reason": "", "branch": branch, "pr": "",
            "updated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        })


def find_transcript(session_id, root=os.path.expanduser("~/.claude/projects")):
    found = glob.glob(os.path.join(root, "*", f"{glob.escape(session_id)}.jsonl"))
    return found[0] if found else None


def write_card(directory, session_id, card):
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(card, f)
    os.replace(tmp, os.path.join(directory, f"{session_id}.json"))


def read_cards(directory):
    cards = {}
    try:
        names = os.listdir(directory)
    except OSError:
        return cards
    for name in names:
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(directory, name), encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            continue
        if isinstance(data, dict):
            cards[name[:-5]] = data
    return cards
