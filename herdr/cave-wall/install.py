"""Install cave wall for the current user on Linux, macOS or Windows.

    python3 install.py              (Windows: py install.py)
    python3 install.py --uninstall

Does three things, each safe to repeat:
  1. a `cavewall` launcher in ~/.local/bin (symlink; a .cmd on Windows)
  2. the Stop hook in ~/.claude/settings.json (backup written first)
  3. the ctrl+alt+w popup key in herdr's config.toml (backup written first)
"""
import argparse
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WINDOWS = os.name == "nt"
LAUNCHER = os.path.join(HERE, "cavewall.cmd" if WINDOWS else "cavewall.sh")
MARK = "cave wall: all Claude sessions"  # identifies our herdr block


def launcher_path(home):
    return os.path.join(home, ".local", "bin", "cavewall.cmd" if WINDOWS else "cavewall")


def _is_ours(hook):
    return "cavewall" in str(hook.get("command", ""))


def unmerge_hook(settings):
    stop = settings.get("hooks", {}).get("Stop", [])
    kept = []
    for entry in stop:
        hooks = [h for h in entry.get("hooks", []) if not _is_ours(h)]
        if hooks:
            kept.append(dict(entry, hooks=hooks))
    if "hooks" in settings:
        settings["hooks"]["Stop"] = kept
    return settings


def merge_hook(settings, command):
    settings = unmerge_hook(settings)
    settings.setdefault("hooks", {}).setdefault("Stop", []).append(
        {"hooks": [{"type": "command", "command": command, "timeout": 10}]})
    return settings


def remove_herdr_key(text):
    """Drop every [[keys.command]] block that is ours; a block runs until the next [table] header."""
    blocks, cur = [], []
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith("[") and cur:
            blocks.append(cur)
            cur = []
        cur.append(line)
    if cur:
        blocks.append(cur)
    kept = [b for b in blocks
            if not (b[0].strip() == "[[keys.command]]" and (MARK in "".join(b) or "cavewall" in "".join(b)))]
    out = "".join("".join(b) for b in kept)
    return out.rstrip("\n") + "\n" if out.strip() else ""


def add_herdr_key(text, command, kind="popup"):
    """kind 'plugin_action' (preferred) or 'popup' (fallback when the plugin cannot be linked)."""
    text = remove_herdr_key(text)
    cmd = command.replace("\\", "\\\\").replace('"', '\\"')
    block = (f'\n[[keys.command]]\nkey = "ctrl+alt+w"\ntype = "{kind}"\n'
             f'command = "{cmd}"\ndescription = "{MARK}"\n')
    if kind == "popup":
        block += 'width = "90%"\nheight = "85%"\n'
    return text.rstrip("\n") + "\n" + block


PLUGIN_ID = "ugg.cavewall"


def _herdr(args):
    """Run a herdr CLI command, return its exit code (127 when herdr is missing)."""
    import subprocess
    exe = shutil.which("herdr")
    if not exe:
        return 127
    return subprocess.run([exe, *args], capture_output=True, timeout=30).returncode


def link_plugin(herdr=_herdr):
    """Link this folder as herdr plugin (relink so a moved checkout is picked up). True on success."""
    herdr(["plugin", "unlink", PLUGIN_ID])
    return herdr(["plugin", "link", HERE]) == 0


def default_herdr_config(home):
    if WINDOWS:
        base = os.environ.get("APPDATA", os.path.join(home, "AppData", "Roaming"))
        return os.path.join(base, "herdr", "config.toml")
    return os.path.join(home, ".config", "herdr", "config.toml")


def _backup(path, quiet):
    if os.path.exists(path):
        shutil.copy2(path, path + ".bak-cavewall")
        if not quiet:
            print(f"  backup  {path}.bak-cavewall")


def _say(quiet, *a):
    if not quiet:
        print(*a)


def hook_command(launcher):
    # absolute path: hooks may run without ~/.local/bin on PATH.
    # Claude Code runs hooks through bash, also on Windows (Git Bash), where
    # backslashes are escape characters: use forward slashes and quote.
    return f'"{launcher.replace(chr(92), "/")}" hook'


def install(home, herdr_config, quiet=False, herdr=_herdr):
    # 1. launcher
    link = launcher_path(home)
    os.makedirs(os.path.dirname(link), exist_ok=True)
    if os.path.lexists(link):
        os.remove(link)
    if WINDOWS:
        with open(link, "w") as f:
            f.write(f'@echo off\r\ncall "{LAUNCHER}" %*\r\n')
    else:
        os.symlink(LAUNCHER, link)
    _say(quiet, f"  launcher {link}")

    # 2. Stop hook
    settings_path = os.path.join(home, ".claude", "settings.json")
    os.makedirs(os.path.dirname(settings_path), exist_ok=True)
    settings = {}
    if os.path.exists(settings_path):
        with open(settings_path, encoding="utf-8") as f:
            settings = json.load(f)
        _backup(settings_path, quiet)
    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(merge_hook(settings, hook_command(LAUNCHER)), f, indent=2)
        f.write("\n")
    _say(quiet, f"  hook     {settings_path} (new sessions pick it up; the board repaints old ones)")

    # 3. herdr key
    if herdr_config and os.path.exists(herdr_config):
        with open(herdr_config, encoding="utf-8") as f:
            text = f.read()
        _backup(herdr_config, quiet)
        if link_plugin(herdr):
            act = "open-windows" if WINDOWS else "open"
            new_text, how = add_herdr_key(text, f"{PLUGIN_ID}.{act}", kind="plugin_action"), "plugin"
        else:
            new_text, how = add_herdr_key(text, f"{LAUNCHER} popup"), "plain popup (plugin link failed)"
        with open(herdr_config, "w", encoding="utf-8") as f:
            f.write(new_text)
        _say(quiet, f"  key      ctrl+alt+w ({how}) in {herdr_config} (run: herdr server reload-config)")
    else:
        _say(quiet, f"  key      skipped, herdr config not found at {herdr_config}")

    if not quiet:
        _check_deps()


def uninstall(home, herdr_config, quiet=False, herdr=_herdr):
    link = launcher_path(home)
    if os.path.lexists(link):
        os.remove(link)
    settings_path = os.path.join(home, ".claude", "settings.json")
    if os.path.exists(settings_path):
        with open(settings_path, encoding="utf-8") as f:
            settings = json.load(f)
        _backup(settings_path, quiet)
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(unmerge_hook(settings), f, indent=2)
            f.write("\n")
    if herdr_config and os.path.exists(herdr_config):
        with open(herdr_config, encoding="utf-8") as f:
            text = f.read()
        _backup(herdr_config, quiet)
        with open(herdr_config, "w", encoding="utf-8") as f:
            f.write(remove_herdr_key(text))
    herdr(["plugin", "unlink", PLUGIN_ID])
    _say(quiet, "  removed launcher, hook, key and plugin link. Cards stay in ~/.claude/cavewall (delete by hand).")


def _check_deps():
    for tool in ("herdr", "claude", "git"):
        if not shutil.which(tool):
            print(f"  ⚠ {tool} not found on PATH")
    if not shutil.which("gh"):
        print("  · gh not found: cards will have no PR link (optional)")
    try:
        import curses  # noqa: F401
    except ImportError:
        print("  ⚠ curses missing. On Windows: py -m pip install windows-curses")
    bin_dir = os.path.dirname(launcher_path(os.path.expanduser("~")))
    if bin_dir not in os.environ.get("PATH", "").split(os.pathsep):
        print(f"  ⚠ {bin_dir} is not on PATH; add it to run `cavewall` by name")


def main():
    p = argparse.ArgumentParser(description="Install cave wall (herdr board for Claude sessions)")
    p.add_argument("--uninstall", action="store_true")
    p.add_argument("--herdr-config", help="path to herdr config.toml (default: OS standard location)")
    a = p.parse_args()
    home = os.path.expanduser("~")
    cfg = a.herdr_config or default_herdr_config(home)
    (uninstall if a.uninstall else install)(home, cfg)


if __name__ == "__main__":
    sys.exit(main())
