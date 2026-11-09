import importlib.util
import json
import os
import pathlib
import tempfile
import unittest

_spec = importlib.util.spec_from_file_location(
    "install", pathlib.Path(__file__).resolve().parent.parent / "install.py")
install = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(install)

CMD = "/opt/cave-wall/cavewall.sh hook"


class MergeHook(unittest.TestCase):
    def test_adds_stop_hook_to_empty_settings(self):
        s = install.merge_hook({}, CMD)
        self.assertEqual(s["hooks"]["Stop"], [{"hooks": [{"type": "command", "command": CMD, "timeout": 10}]}])

    def test_keeps_other_hooks_and_settings(self):
        other = {"hooks": [{"type": "command", "command": "notify-send done"}]}
        s = install.merge_hook({"model": "opus", "hooks": {"Stop": [other], "SessionStart": [1]}}, CMD)
        self.assertEqual(s["model"], "opus")
        self.assertEqual(s["hooks"]["SessionStart"], [1])
        self.assertIn(other, s["hooks"]["Stop"])
        self.assertEqual(len(s["hooks"]["Stop"]), 2)

    def test_idempotent_and_replaces_old_cavewall_entry(self):
        old = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "cavewall hook"}]}]}}
        s = install.merge_hook(install.merge_hook(old, CMD), CMD)
        cmds = [h["command"] for e in s["hooks"]["Stop"] for h in e["hooks"]]
        self.assertEqual(cmds, [CMD])

    def test_unmerge_removes_only_cavewall(self):
        keep = {"hooks": [{"type": "command", "command": "notify-send done"}]}
        s = install.unmerge_hook(install.merge_hook({"hooks": {"Stop": [keep]}}, CMD))
        self.assertEqual(s["hooks"]["Stop"], [keep])


class HookCommand(unittest.TestCase):
    def test_windows_path_survives_bash(self):
        # Claude Code runs hooks via bash on Windows: backslashes get eaten
        cmd = install.hook_command(r"C:\Users\Me\.local\share\cave-wall\cavewall.cmd")
        self.assertEqual(cmd, '"C:/Users/Me/.local/share/cave-wall/cavewall.cmd" hook')

    def test_path_with_spaces_is_quoted(self):
        cmd = install.hook_command("/home/a b/cave-wall/cavewall.sh")
        self.assertEqual(cmd, '"/home/a b/cave-wall/cavewall.sh" hook')


class HerdrKey(unittest.TestCase):
    def test_appends_block_once(self):
        t = install.add_herdr_key('theme = "x"\n', "/opt/cw popup")
        t2 = install.add_herdr_key(t, "/opt/cw popup")
        self.assertEqual(t, t2)
        self.assertIn('[[keys.command]]', t)
        self.assertIn('command = "/opt/cw popup"', t)
        self.assertIn('key = "ctrl+alt+w"', t)

    def test_replaces_old_cavewall_block_keeps_others(self):
        old = ('[[keys.command]]\nkey = "prefix+alt+g"\ntype = "popup"\ncommand = "lazygit"\n\n'
               '[[keys.command]]\nkey = "prefix+a"\ntype = "popup"\ncommand = "/old/cavewall popup"\n'
               'description = "cave wall: all Claude sessions"\n')
        t = install.add_herdr_key(old, "/new/cw popup")
        self.assertIn('command = "lazygit"', t)
        self.assertNotIn("/old/cavewall", t)
        self.assertEqual(t.count("cave wall"), 1)

    def test_windows_path_is_escaped_for_toml(self):
        t = install.add_herdr_key("", r"C:\cw\cavewall.cmd popup")
        self.assertIn(r'command = "C:\\cw\\cavewall.cmd popup"', t)

    def test_remove_block(self):
        t = install.remove_herdr_key(install.add_herdr_key('theme = "x"\n', "/opt/cw popup"))
        self.assertNotIn("cave wall", t)
        self.assertIn('theme = "x"', t)


class InstallEndToEnd(unittest.TestCase):
    def test_install_twice_then_uninstall_in_fake_home(self):
        with tempfile.TemporaryDirectory() as home:
            herdr_cfg = os.path.join(home, ".config", "herdr", "config.toml")
            os.makedirs(os.path.dirname(herdr_cfg))
            with open(herdr_cfg, "w") as f:
                f.write('theme = "x"\n')
            for _ in range(2):
                install.install(home=home, herdr_config=herdr_cfg, quiet=True)
            settings = json.load(open(os.path.join(home, ".claude", "settings.json")))
            cmds = [h["command"] for e in settings["hooks"]["Stop"] for h in e["hooks"]]
            self.assertEqual(len(cmds), 1)
            self.assertTrue(os.path.exists(install.launcher_path(home)))
            self.assertEqual(open(herdr_cfg).read().count("cave wall"), 1)
            install.uninstall(home=home, herdr_config=herdr_cfg, quiet=True)
            settings = json.load(open(os.path.join(home, ".claude", "settings.json")))
            self.assertEqual(settings["hooks"].get("Stop", []), [])
            self.assertNotIn("cave wall", open(herdr_cfg).read())
            self.assertFalse(os.path.lexists(install.launcher_path(home)))


if __name__ == "__main__":
    unittest.main()
