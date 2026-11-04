"""Curses board: every Claude session in herdr, the ones waiting on you on top. Enter jumps there."""
try:
    import curses
except ImportError:  # Windows: pip install windows-curses
    raise SystemExit("cave wall needs curses. On Windows run: py -m pip install windows-curses")
import datetime
import os
import subprocess
import textwrap
import time
import unicodedata

from cavewall import art, board, cards, compat, hook, plugin, worktree

ICON = {"needs_you": "!", "done": "✓", "working": "~", "idle": "·", "blocked": "!", "unknown": "?"}
FRAME_MS, RELOAD_S = art.FRAME_MS, 3  # the painting sets the pace; herdr is asked every 3 s
HELP = " ↑↓/jk move  ⏎ jump  n new worktree  s seed card  d done  ⌂ = base checkout  r refresh  q quit "


def _ask(stdscr, text, attr):
    """Show a one-line question at the bottom, wait for one key."""
    h, w = stdscr.getmaxyx()
    _put(stdscr, h - 1, 0, text.ljust(w), attr | curses.A_BOLD)
    stdscr.refresh()
    stdscr.timeout(-1)
    try:
        return stdscr.getch()
    finally:
        stdscr.timeout(3000)


def _cursor(visibility):
    try:
        curses.curs_set(visibility)
    except curses.error:
        pass


def _input(stdscr, prompt):
    """One-line text input at the bottom. Enter returns the text, Esc returns None."""
    h, w = stdscr.getmaxyx()
    text = ""
    _cursor(1)
    stdscr.timeout(-1)
    try:
        while True:
            _put(stdscr, h - 1, 0, f" {prompt}{text}".ljust(w), curses.color_pair(4) | curses.A_BOLD)
            stdscr.move(h - 1, min(w - 2, len(prompt) + len(text) + 1))
            stdscr.refresh()
            k = stdscr.get_wch()
            if k in ("\n", "\r", curses.KEY_ENTER):
                return text.strip()
            if k == "\x1b":
                return None
            if k in (curses.KEY_BACKSPACE, "\x7f", "\b"):
                text = text[:-1]
            elif isinstance(k, str) and k.isprintable():
                text += k
    finally:
        _cursor(0)
        stdscr.timeout(3000)


def _new_worktree(stdscr, row):
    """New worktree of the row's repo (works from base or worktree rows) with Claude started in it."""
    if not row["repo_root"]:
        return None, f"{row['place']} is not a git checkout. Ugg no dig here."
    repo = os.path.basename(row["repo_root"])
    branch = _input(stdscr, f"New worktree of {repo} from origin/main. Branch (empty = auto, Esc cancels): ")
    if branch is None:
        return None, "cancelled"
    h, w = stdscr.getmaxyx()
    _put(stdscr, h - 1, 0, f" 🪓 digging new worktree in {repo}, starting Claude…".ljust(w), curses.A_BOLD)
    stdscr.refresh()
    taken = {a.get("name") for a in board.herdr_agents() if a.get("name")}
    return worktree.create_with_agent(row["repo_root"], branch, taken)


def _seed(row):
    """Write this session's card now, in a detached process that outlives the popup."""
    sid = row["session_id"]
    if hook.is_painting(sid):
        return f"already painting {row['place']}…"
    t = cards.find_transcript(sid)
    if not t:
        return f"no transcript yet for {row['place']}"
    kind = cards.empty_kind(t)
    if kind:
        return f"{row['place']} is {kind}, nothing to paint yet"
    hook.spawn_refresh(sid, t, row["checkout"] or "")
    return f"painting card for {row['place']}… (~5s, keeps going if you close)"


def _reset(stdscr, row, rows):
    """Main checkout: never delete it, put it back on a clean default branch instead."""
    path = row["checkout"]
    sharing = [r for r in rows if r["checkout"] == path and not r["is_worktree"]]
    changed = worktree.tracked_changes(path)
    if changed is None:
        return f"{row['place']} is not a git repo. Ugg no touch."
    target = worktree.default_branch(path)
    danger = worktree.reset_risks(changed)
    what = f"Main checkout {row['place']}: reset --hard and checkout {target}"
    what += f" (shared by {len(sharing)} sessions)?" if len(sharing) > 1 else "?"
    if any(r["status"] == "working" for r in sharing):
        danger.append("Claude is working there")
    if danger:
        k = _ask(stdscr, f" ⚠ {what} LOSES {', '.join(danger)}! Shift+Y to do it, any key cancels ",
                 curses.color_pair(1))
        if k != ord("Y"):
            return "cancelled"
    elif _ask(stdscr, f" {what} y/N ", curses.color_pair(3)) not in (ord("y"), ord("Y")):
        return "cancelled"
    err = worktree.reset_to_default(path)
    if err:
        return f"failed: {err}"
    cards.mark_reset(cards.CARD_DIR, [r["session_id"] for r in sharing], target)
    return f"{row['place']} clean on {target} (old branch kept)"


EXIT = object()  # returned by actions after which the board must quit
_POPUP = [False]  # set by run(): popup boards get reopened by the relay


def _home_workspace():
    """Workspace this board lives in: a popup belongs to the workspace it was opened from."""
    import json
    try:
        ctx = json.loads(os.environ.get("HERDR_PLUGIN_CONTEXT_JSON") or "{}")
    except ValueError:
        ctx = {}
    return (ctx.get("workspace_id") or os.environ.get("HERDR_ACTIVE_WORKSPACE_ID")
            or os.environ.get("HERDR_WORKSPACE_ID") or board.focused_workspace())


def _delete(stdscr, row, rows):
    """Confirm and remove the row's worktree and close its terminal. Returns a status message."""
    if not row["is_worktree"]:
        return _reset(stdscr, row, rows)
    dirty, unpushed = worktree.inspect(row["checkout"])
    danger = worktree.risks(dirty, unpushed)
    n = sum(r["workspace_id"] == row["workspace_id"] for r in rows)
    what = f"Delete worktree {row['place']}"
    what += f" [{row['branch']}]" if row["branch"] else ""
    what += f", close terminal, kill {n} session{'s' if n != 1 else ''}?"
    if danger:
        k = _ask(stdscr, f" ⚠ {what} LOSES {', '.join(danger)}! Shift+Y to force, any key cancels ",
                 curses.color_pair(1))
        if k != ord("Y"):
            return "cancelled"
    elif _ask(stdscr, f" {what} y/N ", curses.color_pair(3)) not in (ord("y"), ord("Y")):
        return "cancelled"
    if row["workspace_id"] == _home_workspace():
        # herdr closes this board together with its workspace: hand the job to a detached relay
        safe = board.refuge(rows, row)
        if not safe:
            return "it is the only workspace; closing it would close the board too. Ugg wait."
        plugin.spawn_relay(row["workspace_id"], safe, bool(danger),
                           [r["session_id"] for r in rows if r["workspace_id"] == row["workspace_id"]],
                           reopen=_POPUP[0])
        return EXIT
    err = worktree.remove(row["workspace_id"], force=bool(danger))
    if err:
        return f"failed: {err}"
    for r in rows:
        if r["workspace_id"] == row["workspace_id"]:
            try:
                os.remove(os.path.join(cards.CARD_DIR, f"{r['session_id']}.json"))
            except OSError:
                pass
    return f"smashed {row['place']} (branch kept)"


def _age(ts):
    if not ts:
        return "no card"
    try:
        s = (datetime.datetime.now() - datetime.datetime.fromisoformat(ts)).total_seconds()
    except ValueError:
        return "?"
    return f"{int(s // 60)}m" if s < 3600 else f"{int(s // 3600)}h" if s < 86400 else f"{int(s // 86400)}d"


_last_repaint = {}  # session id -> time of our last auto repaint, so a failing one is not retried every 3s


def _repaint_stale(rows, per_round=3, cooldown=120):
    """Sessions started before the Stop hook existed never repaint themselves; the board does it."""
    now, started = time.time(), 0
    for r in rows:
        sid = r["session_id"]
        if started >= per_round or now - _last_repaint.get(sid, 0) < cooldown or hook.is_painting(sid):
            continue
        t = cards.find_transcript(sid)
        try:
            card_m = os.path.getmtime(os.path.join(cards.CARD_DIR, f"{sid}.json"))
        except OSError:
            card_m = None
        if t and board.wants_repaint(r, cards.is_stale(card_m, os.path.getmtime(t))):
            _last_repaint[sid] = now
            hook.spawn_refresh(sid, t, r["checkout"] or "")
            started += 1


def _load():
    try:
        agents, have = board.herdr_agents(), cards.read_cards(cards.CARD_DIR)
        empty = {}
        for a in agents:
            sid = (a.get("agent_session") or {}).get("value")
            if sid and sid not in have:
                t = cards.find_transcript(sid)
                kind = cards.empty_kind(t) if t else "fresh"
                if kind:
                    empty[sid] = kind
        rows = board.build_rows(agents, have, board.herdr_workspaces(), empty)
        worktree.fill_git_kind(rows)
        _repaint_stale(rows)
        return rows, ""
    except Exception as e:  # herdr gone or busy: keep the screen alive
        return [], f"herdr unavailable: {e}"


def _cells(text):
    """Terminal width of text: wide characters such as emoji take two cells."""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


def _fit(text, cells):
    out, used = [], 0
    for c in text:
        cw = 2 if unicodedata.east_asian_width(c) in "WF" else 1
        if used + cw > cells:
            break
        out.append(c)
        used += cw
    return "".join(out)


def _put(win, y, x, text, attr=0):
    """Draw clipped to the screen; never let a curses edge case kill the board."""
    h, w = win.getmaxyx()
    if not (0 <= y < h and x < w):
        return
    text = _fit(text, max(0, w - x - 1))
    try:
        win.addnstr(y, x, text, len(text), attr)
    except curses.error:
        pass


def _pigments():
    """Curses attributes for the painting: (fg, bg) pairs, 256 colours or the basic 8."""
    attrs, many = {}, getattr(curses, "COLORS", 8) >= 256
    for n, (name, (fg, bg, fg8, bg8)) in enumerate(art.PALETTE.items(), 20):
        try:
            if many:
                curses.init_pair(n, fg, bg)
            else:
                curses.init_pair(n, getattr(curses, "COLOR_" + fg8.upper()), getattr(curses, "COLOR_" + bg8.upper()))
            attrs[name] = curses.color_pair(n)
        except curses.error:
            attrs[name] = 0
    return attrs


def free_area(h, shown):
    """Rows between the session list and the separator line (h - 7) over the details."""
    return 2 + shown + 1, h - 8


def _paint(stdscr, top, bottom, w, paint):
    cells = art.scene(bottom - top + 1, w, int(time.monotonic() * 1000 / FRAME_MS))
    if not cells:
        return
    y0 = bottom - len(cells) + 1
    for i, row in enumerate(cells):
        x = 0
        while x < len(row):  # one addstr per run of the same colour
            ch, col = row[x]
            end = x
            while end < len(row) and row[end][1] == col:
                end += 1
            text = "".join(c for c, _ in row[x:end])
            _put(stdscr, y0 + i, x, text, paint.get(col, 0))  # blanks too: they are the rock
            x = end


def run(stdscr, close_on_jump=False):
    _POPUP[0] = close_on_jump
    for setup in (lambda: curses.curs_set(0), curses.use_default_colors):
        try:
            setup()  # not every terminal (e.g. some Windows consoles) supports these
        except curses.error:
            pass
    for i, c in enumerate((curses.COLOR_RED, curses.COLOR_GREEN, curses.COLOR_YELLOW, curses.COLOR_CYAN), 1):
        curses.init_pair(i, c, -1)
    color = {"needs_you": 1, "done": 2, "working": 3, "blocked": 1}
    paint = _pigments()
    stdscr.timeout(FRAME_MS)  # animation tick; herdr is asked only every RELOAD_S
    sel, rows, err = 0, *_load()
    loaded = time.monotonic()
    msg = ""
    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        need = sum(r["needs_you"] for r in rows)
        _put(stdscr, 0, 0, f" 🪨 cave wall  {len(rows)} sessions  {need} need you ", curses.A_BOLD)
        if err:
            _put(stdscr, 1, 1, err, curses.color_pair(1))
        sel = max(0, min(sel, len(rows) - 1))
        list_h = max(3, h - 8)
        top = max(0, sel - list_h + 1)
        for i, r in enumerate(rows[top:top + list_h]):
            idx = top + i
            key = "needs_you" if r["needs_you"] else r["status"]
            attr = curses.color_pair(color.get(key, 0))
            if idx == sel:
                attr |= curses.A_REVERSE
            age = "painting" if hook.is_painting(r["session_id"]) else _age(r["updated_at"])
            mark = "⌂" if r["kind"] == "base" else " "
            line = f" {ICON.get(key, '?')} {mark} {r['place'][:28]:<28} {age:>8}  {r['goal']}"
            _put(stdscr, 2 + i, 0, line.ljust(w), attr)
        free_top, free_bottom = free_area(h, min(len(rows), list_h))
        _paint(stdscr, free_top, free_bottom, w, paint)
        if rows:
            r = rows[sel]
            y = h - 6
            _put(stdscr, y - 1, 0, "─" * w, curses.A_DIM)
            details = [("state", r["state"]), ("next", r["next"]),
                       ("YOU", r["reason"]), ("where", " ".join(x for x in (r["branch"], r["pr"]) if x))]
            for label, val in details:
                if not val or y >= h - 1:
                    continue
                for j, chunk in enumerate(textwrap.wrap(val, max(10, w - 9))[:2]):
                    _put(stdscr, y, 0, f" {label if j == 0 else '':<6} {chunk}",
                         curses.color_pair(1) | curses.A_BOLD if label == "YOU" else 0)
                    y += 1
        _put(stdscr, h - 1, 0, f" {msg} " if msg else HELP, curses.A_BOLD if msg else curses.A_DIM)
        stdscr.refresh()

        k = stdscr.getch()
        if k == -1 and time.monotonic() - loaded < RELOAD_S:
            continue  # just the next picture of the hunt
        msg = ""  # a message lives until the next key or reload
        if k in (ord("q"), 27):
            return
        if k in (curses.KEY_DOWN, ord("j")):
            sel += 1
        elif k in (curses.KEY_UP, ord("k")):
            sel -= 1
        elif k in (curses.KEY_ENTER, 10, 13) and rows:
            board.focus(rows[sel]["pane_id"])
            if close_on_jump:
                return
        elif k == ord("n") and rows:
            pane, msg = _new_worktree(stdscr, rows[sel])
            if pane:
                board.focus(pane)
                if close_on_jump:
                    return
        elif k == ord("s") and rows:
            msg = _seed(rows[sel])
        elif k == ord("d") and rows:
            msg = _delete(stdscr, rows[sel], rows)
            if msg is EXIT:
                return
        rows, err = _load()
        loaded = time.monotonic()


def main(close_on_jump=False):
    curses.wrapper(run, close_on_jump)
