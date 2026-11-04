import os
import pathlib
import tempfile
import tomllib
import unittest

from cavewall import cards, plugin

ROOT = pathlib.Path(__file__).resolve().parent.parent


class Manifest(unittest.TestCase):
    def setUp(self):
        self.m = tomllib.loads((ROOT / "herdr-plugin.toml").read_text(encoding="utf-8"))

    def test_identity_matches_code(self):
        self.assertEqual(self.m["id"], plugin.PLUGIN_ID)
        self.assertEqual(set(self.m["platforms"]), {"linux", "macos", "windows"})

    def test_board_popup_per_platform(self):
        panes = {p["id"]: p for p in self.m["panes"]}
        for os_name in ("posix", "nt"):
            p = panes[plugin.entrypoint(os_name)]
            self.assertEqual(p["placement"], "popup")
            self.assertEqual(p["command"][-1], "popup")
        self.assertEqual(panes["board"]["command"][0], "python3")
        self.assertEqual(panes["board-windows"]["command"][0], "py")

    def test_open_action_per_platform(self):
        actions = {a["id"]: a for a in self.m["actions"]}
        for os_name in ("posix", "nt"):
            self.assertEqual(actions[plugin.action(os_name)]["command"][-1], "open")


class OpenBoard(unittest.TestCase):
    def test_open_command_targets_active_pane(self):
        cmd = plugin.open_command("posix")
        self.assertEqual(cmd[1:], ["plugin", "pane", "open", "--plugin", plugin.PLUGIN_ID,
                                   "--entrypoint", "board", "--focus"])
        self.assertNotIn("--workspace", cmd)  # herdr: popups target the active pane

    def test_windows_entrypoint(self):
        self.assertIn("board-windows", plugin.open_command("nt"))


class Relay(unittest.TestCase):
    def test_focus_then_remove_then_cleanup_then_reopen(self):
        calls = []
        with tempfile.TemporaryDirectory() as d:
            cards.write_card(d, "s1", {"goal": "x"})
            err = plugin.relay_delete(
                doomed="w9", refuge="w2", force=True, session_ids=["s1"], reopen=True, card_dir=d,
                run=lambda cmd: calls.append(cmd[1:4]) or 0,
                remove=lambda ws, force: calls.append(("remove", ws, force)) or "")
            self.assertEqual(err, "")
            self.assertFalse(os.path.exists(os.path.join(d, "s1.json")))
        self.assertEqual(calls, [["workspace", "focus", "w2"], ("remove", "w9", True),
                                 ["plugin", "pane", "open"]])

    def test_no_reopen_and_no_cleanup_when_remove_fails(self):
        calls = []
        with tempfile.TemporaryDirectory() as d:
            cards.write_card(d, "s1", {"goal": "x"})
            err = plugin.relay_delete(
                doomed="w9", refuge="w2", force=False, session_ids=["s1"], reopen=True, card_dir=d,
                run=lambda cmd: calls.append(cmd[1:4]) or 0,
                remove=lambda ws, force: "dirty")
            self.assertEqual(err, "dirty")
            self.assertTrue(os.path.exists(os.path.join(d, "s1.json")))
        self.assertEqual(calls, [["workspace", "focus", "w2"], ["plugin", "pane", "open"]])

    def test_pane_mode_does_not_reopen(self):
        calls = []
        with tempfile.TemporaryDirectory() as d:
            plugin.relay_delete(doomed="w9", refuge="w2", force=False, session_ids=[], reopen=False,
                                card_dir=d, run=lambda cmd: calls.append(cmd[1:4]) or 0,
                                remove=lambda ws, force: "")
        self.assertNotIn(["plugin", "pane", "open"], calls)


if __name__ == "__main__":
    unittest.main()
