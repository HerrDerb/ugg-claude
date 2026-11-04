"""cavewall [board|popup|seed|hook]   (popup: Enter jumps and closes, for a herdr popup key)"""
import sys
from concurrent.futures import ThreadPoolExecutor

from cavewall import board, cards, hook, tui


def seed():
    """Write a card now for every live session that has none (new sessions get one on their next turn)."""
    have = cards.read_cards(cards.CARD_DIR)
    todo = []
    for a in board.herdr_agents():
        sid = (a.get("agent_session") or {}).get("value")
        if a.get("agent") != "claude" or not sid or sid in have:
            continue
        t = cards.find_transcript(sid)
        if t:
            todo.append((sid, t, a.get("cwd") or ""))
    print(f"seeding {len(todo)} cards…")
    with ThreadPoolExecutor(4) as pool:
        for sid, t, cwd in todo:
            pool.submit(hook.refresh, sid, t, cwd)
    print("done")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "board"
    if cmd == "refresh":
        return hook.refresh(*sys.argv[2:5])
    {"board": tui.main, "popup": lambda: tui.main(close_on_jump=True), "seed": seed, "hook": hook.main}.get(cmd, lambda: print(__doc__))()


if __name__ == "__main__":
    main()
