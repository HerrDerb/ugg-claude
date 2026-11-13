"""Open VS Code on the working directory of the focused herdr pane."""
import json
import os
import shutil
import subprocess
import sys


def _herdr(args):
    """Run a herdr CLI command and return its parsed JSON, or None on any failure."""
    exe = os.environ.get("HERDR_BIN_PATH") or shutil.which("herdr") or "herdr"
    try:
        out = subprocess.run([exe, *args], capture_output=True, text=True, timeout=5)
        return json.loads(out.stdout) if out.returncode == 0 else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def target_dir(ctx_json, herdr=_herdr):
    """Dir of the pane the action was fired on, else the focused pane.

    foreground_cwd wins over cwd: it follows a `cd` inside the shell and the
    cwd of an agent like Claude running in the pane.
    """
    try:
        pane_id = (json.loads(ctx_json or "{}") or {}).get("focused_pane_id")
    except (ValueError, AttributeError):
        pane_id = None
    resp = herdr(["pane", "get", pane_id] if pane_id else ["pane", "current"])
    pane = ((resp or {}).get("result") or {}).get("pane") or {}
    return pane.get("foreground_cwd") or pane.get("cwd")


DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200


def detach_kwargs(platform=sys.platform):
    """Popen options so VS Code outlives this short-lived action."""
    if platform == "win32":
        return {"creationflags": DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def _spawn(argv):
    subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, **detach_kwargs())


def launch(path, spawn=_spawn, platform=sys.platform):
    # On Windows `code` is a batch shim; CreateProcess needs the .cmd name.
    spawn(["code.cmd" if platform == "win32" else "code", path])


def main():
    path = target_dir(os.environ.get("HERDR_PLUGIN_CONTEXT_JSON"))
    if not path:
        print("open-code: no pane cwd found", file=sys.stderr)
        return 1
    launch(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
