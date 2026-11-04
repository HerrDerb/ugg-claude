"""Safety check and removal of a herdr-linked git worktree plus its workspace (terminal)."""
import subprocess

from cavewall import compat


def _git(path, *args):
    r = subprocess.run(["git", "-C", path, *args], capture_output=True, text=True, timeout=10)
    return r.returncode, r.stdout


def inspect(path):
    """(uncommitted files, commits on no remote). None means git could not tell."""
    try:
        code, out = _git(path, "status", "--porcelain")
        dirty = len(out.splitlines()) if code == 0 else None
        if _git(path, "rev-parse", "--verify", "-q", "HEAD")[0] != 0:
            return dirty, 0  # no commits yet, nothing to lose but the files
        code, out = _git(path, "rev-list", "--count", "HEAD", "--not", "--remotes")
        unpushed = int(out.strip()) if code == 0 else None
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None, None
    return dirty, unpushed


def _n(count, word):
    return f"{count} {word}{'' if count == 1 else 's'}"


def risks(dirty, unpushed):
    if dirty is None or unpushed is None:
        return ["git state unknown"]
    out = []
    if dirty:
        out.append(_n(dirty, "uncommitted file"))
    if unpushed:
        out.append(_n(unpushed, "unpushed commit"))
    return out


def tracked_changes(path):
    """Changed tracked files (what reset --hard throws away). None if not a git repo."""
    try:
        code, out = _git(path, "status", "--porcelain", "--untracked-files=no")
    except (OSError, subprocess.TimeoutExpired):
        return None
    return len(out.splitlines()) if code == 0 else None


def reset_risks(dirty):
    """Resetting a main checkout loses only uncommitted changes; the old branch stays."""
    return risks(dirty, 0)


def default_branch(path):
    code, out = _git(path, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if code == 0 and out.strip():
        return out.strip().split("/", 1)[-1]
    for name in ("main", "master"):
        if _git(path, "rev-parse", "--verify", "-q", f"refs/heads/{name}")[0] == 0:
            return name
    return "main"


def reset_to_default(path):
    """git reset --hard, then check out the default branch. Returns error text or ''."""
    try:
        for args in (("reset", "--hard", "-q"), ("checkout", "-q", default_branch(path))):
            r = subprocess.run(["git", "-C", path, *args], capture_output=True, text=True, timeout=30)
            if r.returncode != 0:
                return (r.stderr or r.stdout).strip()[:200] or f"git {args[0]} failed"
    except (OSError, subprocess.TimeoutExpired) as e:
        return str(e)
    return ""


def git_kind(path):
    """Ask git itself: ('base'|'worktree', repo root) or (None, None) outside a repo."""
    import os
    try:
        code, out = _git(path, "rev-parse", "--path-format=absolute", "--git-dir", "--git-common-dir")
    except (OSError, subprocess.TimeoutExpired):
        return None, None
    if code != 0 or len(out.split()) != 2:
        return None, None
    git_dir, common = (os.path.realpath(p) for p in out.split())
    root = os.path.dirname(common)
    return ("base" if git_dir == common else "worktree"), root


def fill_git_kind(rows, probe=git_kind):
    """herdr knows git info only for some workspaces; fill the gaps from git, once per folder."""
    seen = {}
    for r in rows:
        if r["kind"] is None and r["checkout"]:
            if r["checkout"] not in seen:
                seen[r["checkout"]] = probe(r["checkout"])
            r["kind"], r["repo_root"] = seen[r["checkout"]]
            r["is_worktree"] = r["kind"] == "worktree"


def agent_name(text, taken):
    """herdr agent name: [a-z][a-z0-9_-]{0,31}, unique among live agents."""
    import re
    slug = re.sub(r"[^a-z0-9_-]+", "-", text.lower()).strip("-_")
    if not slug or not slug[0].isalpha():
        slug = f"wt-{slug}" if slug else "wt"
    slug = slug[:28].rstrip("-_")
    name, n = slug, 2
    while name in taken:
        name, n = f"{slug}-{n}", n + 1
    return name


def create_with_agent(repo_root, branch, taken_names):
    """New herdr worktree from fresh origin/<default>, Claude started in it.
    Returns (pane_id, message); pane_id is None on failure."""
    import json
    default = default_branch(repo_root)
    fetched = subprocess.run(["git", "-C", repo_root, "fetch", "-q", "origin", default],
                             capture_output=True, timeout=60).returncode == 0
    cmd = [compat.exe("herdr"), "worktree", "create", "--cwd", repo_root, "--no-focus",
           "--base", f"origin/{default}" if fetched else default]
    if branch:
        cmd += ["--branch", branch]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    try:
        res = json.loads(r.stdout)["result"]
    except (ValueError, KeyError):
        return None, f"worktree create failed: {(r.stderr or r.stdout).strip()[:160]}"
    pane = res["root_pane"]["pane_id"]
    made = res["worktree"]["branch"]
    name = agent_name(branch or made.split("/")[-1], taken_names)
    a = subprocess.run([compat.exe("herdr"), "agent", "start", name, "--kind", "claude", "--pane", pane, "--timeout", "60000"],
                       capture_output=True, text=True, timeout=90)
    base = f"origin/{default}" if fetched else f"{default} (fetch failed, local)"
    if a.returncode == 0:
        return pane, f"new worktree {made} from {base}, Claude ready"
    if "agent_not_ready" in a.stdout + a.stderr:
        return pane, f"new worktree {made} from {base}, Claude waits for folder trust"
    return pane, f"worktree {made} made, Claude start failed: {(a.stderr or a.stdout).strip()[:120]}"


def remove(workspace_id, force):
    """Remove the checkout, then close the workspace if herdr left it open. Returns error text or ''."""
    cmd = [compat.exe("herdr"), "worktree", "remove", "--workspace", workspace_id] + (["--force"] if force else [])
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return (r.stderr or r.stdout).strip()[:200] or "worktree remove failed"
    if subprocess.run([compat.exe("herdr"), "workspace", "get", workspace_id], capture_output=True, timeout=5).returncode == 0:
        subprocess.run([compat.exe("herdr"), "workspace", "close", workspace_id], capture_output=True, timeout=10)
    return ""
