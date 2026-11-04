"""herdr plugin glue: open the board popup, and the delete relay that survives its own popup.

herdr closes every pane of a closed workspace, a popup opened from it included, and plugin popups
can only target the active pane. So deleting the workspace the board was opened from runs as a
detached relay: focus a safe workspace, remove, clean cards, open the board again there.
"""
import os
import subprocess
import sys

from cavewall import cards, compat

PLUGIN_ID = "ugg.cavewall"


def entrypoint(os_name=os.name):
    return "board-windows" if os_name == "nt" else "board"


def action(os_name=os.name):
    return "open-windows" if os_name == "nt" else "open"


def _herdr():
    return os.environ.get("HERDR_BIN_PATH") or compat.exe("herdr")


def open_command(os_name=os.name):
    return [_herdr(), "plugin", "pane", "open", "--plugin", PLUGIN_ID,
            "--entrypoint", entrypoint(os_name), "--focus"]


def _run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, timeout=30).returncode
    except (OSError, subprocess.TimeoutExpired):
        return 1


def open_board(run=_run):
    return run(open_command())


def relay_delete(doomed, refuge, force, session_ids, reopen, card_dir=None, run=_run, remove=None):
    """Returns error text or ''. The board is reopened even when removal fails, to show the state."""
    if remove is None:
        from cavewall import worktree
        remove = worktree.remove
    run([_herdr(), "workspace", "focus", refuge])
    err = remove(doomed, force)
    if not err:
        for sid in session_ids:
            try:
                os.remove(os.path.join(card_dir or cards.CARD_DIR, f"{sid}.json"))
            except OSError:
                pass
    if reopen:
        run(open_command())
    return err


def spawn_relay(doomed, refuge, force, session_ids, reopen):
    """Run relay_delete in a detached process: the calling board is about to be closed by herdr."""
    subprocess.Popen(
        [sys.executable, "-m", "cavewall", "relay", doomed, refuge, "1" if force else "0",
         "1" if reopen else "0", *session_ids],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        **compat.detach_kwargs())


def relay_main(argv):
    doomed, refuge, force, reopen, *sids = argv
    relay_delete(doomed, refuge, force == "1", sids, reopen == "1")
