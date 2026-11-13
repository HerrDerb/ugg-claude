import json
import unittest

from opencode import main as oc


def fake_herdr(panes, focused):
    """Stand-in for the herdr CLI: answers `pane get <id>` and `pane current`."""
    def run(args):
        if args[:2] == ["pane", "get"]:
            pane = panes.get(args[2])
        elif args[:2] == ["pane", "current"]:
            pane = panes.get(focused)
        else:
            raise AssertionError(f"unexpected herdr call {args}")
        return None if pane is None else {"result": {"pane": pane}}
    return run


PANES = {
    "w1:p1": {"pane_id": "w1:p1", "cwd": "/home/u", "foreground_cwd": "/home/u/repo"},
    "w1:p2": {"pane_id": "w1:p2", "cwd": "/srv/other", "foreground_cwd": None},
}


class TargetDir(unittest.TestCase):
    def test_uses_pane_from_plugin_context(self):
        ctx = json.dumps({"focused_pane_id": "w1:p2", "focused_pane_cwd": "/stale"})
        self.assertEqual(oc.target_dir(ctx, fake_herdr(PANES, "w1:p1")), "/srv/other")

    def test_prefers_foreground_cwd_so_a_cd_inside_the_shell_counts(self):
        self.assertEqual(oc.target_dir("{}", fake_herdr(PANES, "w1:p1")), "/home/u/repo")

    def test_falls_back_to_focused_pane_when_context_is_missing_or_broken(self):
        self.assertEqual(oc.target_dir("not json", fake_herdr(PANES, "w1:p1")), "/home/u/repo")

    def test_none_when_herdr_knows_no_pane(self):
        self.assertIsNone(oc.target_dir("{}", fake_herdr({}, "w1:p9")))


class Launch(unittest.TestCase):
    def test_runs_code_with_the_dir_detached(self):
        calls = []
        oc.launch("/home/u/repo", spawn=calls.append, platform="linux")
        self.assertEqual(calls, [["code", "/home/u/repo"]])

    def test_windows_calls_the_cmd_shim(self):
        calls = []
        oc.launch("C:\\src\\repo", spawn=calls.append, platform="win32")
        self.assertEqual(calls, [["code.cmd", "C:\\src\\repo"]])


class Detach(unittest.TestCase):
    def test_posix_starts_a_new_session(self):
        self.assertEqual(oc.detach_kwargs("linux"), {"start_new_session": True})

    def test_windows_uses_detached_process_flags(self):
        flags = oc.detach_kwargs("win32")["creationflags"]
        self.assertTrue(flags & 0x00000008)  # DETACHED_PROCESS
        self.assertTrue(flags & 0x00000200)  # CREATE_NEW_PROCESS_GROUP


if __name__ == "__main__":
    unittest.main()
