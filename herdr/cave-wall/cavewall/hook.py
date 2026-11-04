"""Claude Code Stop hook: return at once, refresh the session's card in a detached child.

The card is written by a cheap headless model (haiku) that reads only the transcript tail,
so the working session spends no tokens and never waits.
"""
import datetime
import json
import os
import subprocess
import sys

from cavewall import cards, compat

GUARD = "CAVEWALL_INNER"  # set for the inner `claude -p`, so its own Stop hook does nothing
MODEL = os.environ.get("CAVEWALL_MODEL", "haiku")


def _run(cmd, cwd, timeout):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def ask_model(prompt):
    env = dict(os.environ, **{GUARD: "1"})
    os.makedirs(cards.CARD_DIR, exist_ok=True)
    try:
        r = subprocess.run(
            [compat.exe("claude"), "-p", "--model", MODEL, "--no-session-persistence",
             "--setting-sources", "", "--system-prompt",
             "You write terse JSON status cards. Output only JSON.", ],
            input=prompt, cwd=cards.CARD_DIR, env=env,
            capture_output=True, text=True, timeout=120)
        return r.stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def is_painting(session_id, directory=None):
    """True while some process holds this session's refresh lock."""
    return compat.is_locked(os.path.join(directory or cards.CARD_DIR, f".{session_id}.lock"))


def spawn_refresh(session_id, transcript, cwd):
    """Run refresh in its own detached process, so closing the board does not kill it."""
    subprocess.Popen(
        [sys.executable, "-m", "cavewall", "refresh", session_id, transcript, cwd],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        **compat.detach_kwargs())


def refresh(session_id, transcript, cwd):
    lock_path = os.path.join(cards.CARD_DIR, f".{session_id}.lock")
    os.makedirs(cards.CARD_DIR, exist_ok=True)
    lock = compat.try_lock(lock_path)
    if lock is None:
        return  # another refresh runs; it re-checks the transcript before it exits
    try:
        while True:
            mtime = os.path.getmtime(transcript)
            tail = cards.transcript_tail(transcript)
            if not tail:
                return
            card = cards.parse_card(ask_model(cards.build_prompt(tail, cwd)))
            card = cards.settle(card, tail) if card else card
            if card:
                card.update(
                    cwd=cwd,
                    branch=_run([compat.exe("git"), "branch", "--show-current"], cwd, 5),
                    pr=_run([compat.exe("gh"), "pr", "view", "--json", "url", "-q", ".url"], cwd, 15),
                    updated_at=datetime.datetime.now().isoformat(timespec="seconds"),
                )
                cards.write_card(cards.CARD_DIR, session_id, card)
            if os.path.getmtime(transcript) <= mtime:
                return  # nothing new arrived while we summarised
    finally:
        compat.unlock(lock)


def main():
    if os.environ.get(GUARD):
        return
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return
    sid, transcript = event.get("session_id"), event.get("transcript_path")
    if not sid or not transcript or event.get("agent_id"):
        return  # subagent stops are not session turns
    cwd = event.get("cwd") or os.getcwd()
    spawn_refresh(sid, transcript, cwd)  # detached: Claude Code continues immediately


if __name__ == "__main__":
    main()
