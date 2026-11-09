"""Join herdr's live agent list with the stored cards into sorted board rows."""
import json
import os
import subprocess

from cavewall import compat

# lower = higher on the board
_RANK = {"needs_you": 0, "done": 1, "working": 2, "blocked": 0, "idle": 3, "unknown": 3}


def place_of(cwd):
    parts = (cwd or "").replace("\\", "/").rstrip("/").split("/")
    if "worktrees" in parts:
        i = parts.index("worktrees")
        if parts[i - 1:i] == [".herdr"] and len(parts) > i + 2:
            return f"{parts[i + 1]}/{parts[i + 2]}"
    return parts[-1] if parts else "?"


def _kind(wt):
    """'base' (main checkout), 'worktree' (linked) or None (not a git checkout)."""
    if not wt or not wt.get("repo_root"):
        return None
    return "worktree" if wt.get("is_linked_worktree") else "base"


def build_rows(agents, cards, workspaces=(), empty=None):
    from cavewall.cards import EMPTY_CARDS
    empty = empty or {}
    linked = {w.get("workspace_id"): w.get("worktree") or {} for w in workspaces}
    rows = []
    for a in agents:
        sid = (a.get("agent_session") or {}).get("value")
        if a.get("agent") != "claude" or not sid:
            continue
        status = a.get("agent_status", "unknown")
        card = cards.get(sid) or ({"goal": EMPTY_CARDS[empty[sid]]} if sid in empty else {})
        needs_you = status == "blocked" or (status != "working" and card.get("needs_you") is True)
        rows.append({
            "session_id": sid,
            "pane_id": a.get("pane_id"),
            "workspace_id": a.get("workspace_id"),
            "is_worktree": linked.get(a.get("workspace_id"), {}).get("is_linked_worktree") is True,
            "kind": _kind(linked.get(a.get("workspace_id"))),
            "repo_root": (linked.get(a.get("workspace_id")) or {}).get("repo_root"),
            "checkout": linked.get(a.get("workspace_id"), {}).get("checkout_path") or a.get("cwd"),
            "status": status,
            "place": place_of(a.get("cwd")),
            "goal": card.get("goal") or a.get("terminal_title_stripped") or "",
            "state": card.get("state", ""),
            "next": card.get("next", ""),
            "reason": card.get("reason", "") if needs_you else ("approval dialog open" if status == "blocked" else ""),
            "needs_you": needs_you,
            "pr": card.get("pr", ""),
            "branch": card.get("branch", ""),
            "updated_at": card.get("updated_at"),
            "has_card": bool(card),
        })
    rows.sort(key=lambda r: (0 if r["needs_you"] else _RANK.get(r["status"], 3), r["place"]))
    return rows


def wants_repaint(row, stale):
    """Repaint stale real cards of settled sessions; a working session gets its card from the hook."""
    return stale and row["has_card"] and row["status"] != "working"


def refuge(rows, doomed):
    """Workspace to move focus to before closing doomed's workspace: its repo's base checkout,
    else any other workspace. herdr hangs up every pane of a closed focused workspace,
    which includes a popup opened from it."""
    others = [r for r in rows if r["workspace_id"] != doomed["workspace_id"]]
    for r in others:
        if r["kind"] == "base" and r["repo_root"] and r["repo_root"] == doomed["repo_root"]:
            return r["workspace_id"]
    return others[0]["workspace_id"] if others else None


def focused_workspace():
    try:
        out = subprocess.run([compat.exe("herdr"), "workspace", "list"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5)
        return next((w["workspace_id"] for w in json.loads(out.stdout)["result"]["workspaces"]
                     if w.get("focused")), None)
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired):
        return None


def herdr_agents():
    out = subprocess.run([compat.exe("herdr"), "agent", "list"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5)
    return json.loads(out.stdout)["result"]["agents"]


def herdr_workspaces():
    out = subprocess.run([compat.exe("herdr"), "workspace", "list"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5)
    return json.loads(out.stdout)["result"]["workspaces"]


def focus(pane_id):
    subprocess.run([compat.exe("herdr"), "agent", "focus", pane_id], capture_output=True, timeout=5)
