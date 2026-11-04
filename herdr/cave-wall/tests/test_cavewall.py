import json
import os
import tempfile
import unittest

from cavewall import cards, board


def _jsonl(path, entries):
    with open(path, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")


def user(text):
    return {"type": "user", "message": {"role": "user", "content": text}}


def assistant(text):
    return {"type": "assistant", "message": {"role": "assistant",
            "content": [{"type": "thinking", "thinking": "x"}, {"type": "text", "text": text}]}}


def tool_result():
    return {"type": "user", "message": {"role": "user",
            "content": [{"type": "tool_result", "content": "huge output"}]}}


class TranscriptTail(unittest.TestCase):
    def test_keeps_only_human_and_assistant_text_in_order(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.jsonl")
            _jsonl(p, [user("fix bug 42"), tool_result(), assistant("Done, PR #7 open. Merge?"),
                       {"type": "system", "content": "noise"}])
            tail = cards.transcript_tail(p)
        self.assertEqual(tail, [("user", "fix bug 42"), ("assistant", "Done, PR #7 open. Merge?")])

    def test_skips_local_command_noise(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.jsonl")
            _jsonl(p, [user("<command-name>/clear</command-name>"), user("real ask")])
            self.assertEqual(cards.transcript_tail(p), [("user", "real ask")])

    def test_limits_to_last_n_messages(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.jsonl")
            _jsonl(p, [user(f"m{i}") for i in range(30)])
            tail = cards.transcript_tail(p, max_messages=5)
        self.assertEqual([t for _, t in tail], ["m25", "m26", "m27", "m28", "m29"])

    def test_tolerates_broken_lines(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.jsonl")
            with open(p, "w") as f:
                f.write("{not json\n" + json.dumps(user("ok")) + "\n")
            self.assertEqual(cards.transcript_tail(p), [("user", "ok")])


class ParseCard(unittest.TestCase):
    def test_parses_json_even_inside_code_fence(self):
        raw = 'Here:\n```json\n{"goal":"g","state":"s","next":"n","needs_you":true,"reason":"asked merge?"}\n```'
        c = cards.parse_card(raw)
        self.assertEqual(c["goal"], "g")
        self.assertIs(c["needs_you"], True)

    def test_garbage_gives_none(self):
        self.assertIsNone(cards.parse_card("no json here"))

    def test_missing_fields_get_defaults(self):
        c = cards.parse_card('{"goal":"g"}')
        self.assertEqual(c["state"], "")
        self.assertIs(c["needs_you"], False)


class FindTranscript(unittest.TestCase):
    def test_finds_session_file_in_any_project_folder(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "-home-x-repo"))
            p = os.path.join(d, "-home-x-repo", "abc.jsonl")
            open(p, "w").close()
            self.assertEqual(cards.find_transcript("abc", root=d), p)

    def test_missing_session_gives_none(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(cards.find_transcript("nope", root=d))


class PaintingState(unittest.TestCase):
    def test_painting_while_lock_is_held_by_someone_else(self):
        from cavewall import compat, hook
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(hook.is_painting("s1", d))
            held = compat.try_lock(os.path.join(d, ".s1.lock"))
            self.assertTrue(hook.is_painting("s1", d))
            compat.unlock(held)
            self.assertFalse(hook.is_painting("s1", d))


class EmptySession(unittest.TestCase):
    def test_only_clear_means_empty(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.jsonl")
            _jsonl(p, [user("<local-command-caveat>x"), user("<command-name>/clear</command-name>")])
            self.assertEqual(cards.transcript_tail(p), [])
            self.assertEqual(cards.empty_kind(p), "cleared")

    def test_no_messages_at_all_means_fresh(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.jsonl")
            _jsonl(p, [{"type": "system", "content": "start"}])
            self.assertEqual(cards.empty_kind(p), "fresh")

    def test_real_conversation_is_not_empty(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.jsonl")
            _jsonl(p, [user("<command-name>/clear</command-name>"), user("fix it")])
            self.assertIsNone(cards.empty_kind(p))

    def test_board_shows_empty_session_as_its_own_card(self):
        rows = board.build_rows([agent("s1", title="Claude Code")], {}, [], empty={"s1": "cleared"})
        self.assertIn("cleared", rows[0]["goal"])
        self.assertTrue(rows[0]["has_card"])
        self.assertFalse(rows[0]["needs_you"])


class ResetCard(unittest.TestCase):
    def test_reset_replaces_old_task_card(self):
        with tempfile.TemporaryDirectory() as d:
            cards.write_card(d, "s1", {"goal": "Upgrade to Java 25", "needs_you": True, "reason": "merge?"})
            cards.mark_reset(d, ["s1"], "main")
            c = cards.read_cards(d)["s1"]
        self.assertIn("reset to main", c["goal"])
        self.assertFalse(c["needs_you"])
        self.assertEqual(c["reason"], "")
        self.assertEqual(c["branch"], "main")


class Staleness(unittest.TestCase):
    def test_card_older_than_transcript_is_stale(self):
        self.assertTrue(cards.is_stale(card_mtime=100, transcript_mtime=200))

    def test_small_gap_is_not_stale(self):
        # the transcript gets a few bookkeeping lines right after the card is written
        self.assertFalse(cards.is_stale(card_mtime=100, transcript_mtime=120))

    def test_missing_card_is_not_stale(self):
        self.assertFalse(cards.is_stale(card_mtime=None, transcript_mtime=200))

    def test_repaint_only_settled_real_cards(self):
        self.assertTrue(board.wants_repaint({"status": "idle", "has_card": True, "goal": "x"}, stale=True))
        self.assertFalse(board.wants_repaint({"status": "working", "has_card": True, "goal": "x"}, stale=True))
        self.assertTrue(board.wants_repaint({"status": "done", "has_card": True, "goal": "🧹 reset"}, stale=True))
        self.assertFalse(board.wants_repaint({"status": "idle", "has_card": True, "goal": "x"}, stale=False))


class PromptFocus(unittest.TestCase):
    def test_latest_message_is_marked(self):
        p = cards.build_prompt([("user", "old ask"), ("assistant", "All done. PR #9 open.")], "/x")
        self.assertIn("[LATEST ASSISTANT] All done. PR #9 open.", p)
        self.assertIn("[USER] old ask", p)

    def test_prompt_treats_offers_and_wrap_up_as_done(self):
        self.assertIn("optional offer", cards.PROMPT)
        self.assertIn("wraps up", cards.PROMPT)

    def test_prompt_explains_status_line(self):
        self.assertIn("Implemented:", cards.PROMPT)


DONE = "Implemented: 🟢 Committed: 🟢 Pushed: 🟢 PR: 🟢 (#6) Replied to comments: 🔴"


class Settle(unittest.TestCase):
    def test_finished_task_with_optional_offer_does_not_need_you(self):
        tail = [("user", "update pr"),
                ("assistant", f"Removing it means a force push. Say so and Ugg will do it.\n\n{DONE}")]
        c = cards.settle({"needs_you": True, "reason": "Approve force push", "next": "Your call: force push"}, tail)
        self.assertFalse(c["needs_you"])
        self.assertEqual(c["reason"], "")
        self.assertTrue(c["next"].startswith("optional: "))

    def test_finished_task_with_real_question_still_needs_you(self):
        tail = [("assistant", f"Should I also bump the version?\n\n{DONE}")]
        c = cards.settle({"needs_you": True, "reason": "bump?", "next": "x"}, tail)
        self.assertTrue(c["needs_you"])

    def test_without_status_line_model_decides(self):
        tail = [("assistant", "Say so and Ugg will do it.")]
        self.assertTrue(cards.settle({"needs_you": True, "reason": "r", "next": "n"}, tail)["needs_you"])

    def test_red_implemented_is_not_finished(self):
        tail = [("assistant", "Tests fail.\n\nImplemented: 🔴 Committed: 🔴")]
        self.assertTrue(cards.settle({"needs_you": True, "reason": "r", "next": "n"}, tail)["needs_you"])

    def test_later_user_message_wins(self):
        # the developer already answered: the old status line no longer settles anything
        tail = [("assistant", f"Say so.\n\n{DONE}"), ("user", "yes force push")]
        self.assertTrue(cards.settle({"needs_you": True, "reason": "r", "next": "n"}, tail)["needs_you"])


class TodoLines(unittest.TestCase):
    """Sessions end with 'Open todos:' and 'Optional todos:' lines (CLAUDE.md). They decide, not the model."""
    def tail(self, body):
        return [("user", "go"), ("assistant", f"{body}\n\n{DONE}")]

    def test_open_todo_needs_you_even_without_question_mark(self):
        t = self.tail("Open todos: you rotate the API key\nOptional todos: none")
        c = cards.settle({"needs_you": False, "reason": "", "next": "nothing, done"}, t)
        self.assertTrue(c["needs_you"])
        self.assertEqual(c["reason"], "you rotate the API key")
        self.assertEqual(c["next"], "you rotate the API key")

    def test_only_optional_todo_does_not_need_you(self):
        t = self.tail("Should Ugg also bump it?\nOpen todos: none\nOptional todos: bump version")
        c = cards.settle({"needs_you": True, "reason": "bump?", "next": "x"}, t)
        self.assertFalse(c["needs_you"])
        self.assertEqual(c["reason"], "")
        self.assertEqual(c["next"], "optional: bump version")

    def test_nothing_open_is_done(self):
        t = self.tail("Open todos: none\nOptional todos: none")
        c = cards.settle({"needs_you": True, "reason": "r", "next": "n"}, t)
        self.assertFalse(c["needs_you"])
        self.assertEqual(c["next"], "nothing, done")

    def test_lines_count_without_green_implemented(self):
        t = [("assistant", "Tests fail.\nOpen todos: you fix the flaky DB\nOptional todos: none\n"
                           "Implemented: 🔴")]
        c = cards.settle({"needs_you": False, "reason": "", "next": ""}, t)
        self.assertTrue(c["needs_you"])

    def test_later_user_message_ignores_lines(self):
        t = self.tail("Open todos: you review PR\nOptional todos: none") + [("user", "reviewed")]
        c = cards.settle({"needs_you": False, "reason": "", "next": "n"}, t)
        self.assertFalse(c["needs_you"])


class CardStore(unittest.TestCase):
    def test_write_then_read_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            cards.write_card(d, "sess-1", {"goal": "g"})
            self.assertEqual(cards.read_cards(d)["sess-1"]["goal"], "g")

    def test_read_ignores_corrupt_files(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "bad.json"), "w") as f:
                f.write("{")
            self.assertEqual(cards.read_cards(d), {})


def agent(sid, status="idle", pane="w1:p1", title="t", cwd="/x/repo", **kw):
    a = {"agent": "claude", "agent_status": status, "pane_id": pane, "cwd": cwd,
         "terminal_title_stripped": title, "agent_session": {"value": sid}}
    a.update(kw)
    return a


class BoardRows(unittest.TestCase):
    def test_joins_cards_by_session_id(self):
        rows = board.build_rows([agent("s1")], {"s1": {"goal": "ship it", "needs_you": False}})
        self.assertEqual(rows[0]["goal"], "ship it")
        self.assertEqual(rows[0]["pane_id"], "w1:p1")

    def test_session_without_card_falls_back_to_title(self):
        rows = board.build_rows([agent("s1", title="Error grouping")], {})
        self.assertEqual(rows[0]["goal"], "Error grouping")

    def test_blocked_counts_as_needs_you_even_without_card(self):
        rows = board.build_rows([agent("s1", status="blocked")], {})
        self.assertTrue(rows[0]["needs_you"])

    def test_working_session_never_needs_you(self):
        rows = board.build_rows([agent("s1", status="working")], {"s1": {"needs_you": True}})
        self.assertFalse(rows[0]["needs_you"])

    def test_sort_order_needs_you_then_done_then_working_then_idle(self):
        agents = [agent("idle", status="idle", pane="p1"),
                  agent("work", status="working", pane="p2"),
                  agent("done", status="done", pane="p3"),
                  agent("ask", status="idle", pane="p4")]
        rows = board.build_rows(agents, {"ask": {"needs_you": True}})
        self.assertEqual([r["session_id"] for r in rows], ["ask", "done", "work", "idle"])

    def test_skips_panes_without_claude_session(self):
        rows = board.build_rows([{"agent": "codex", "pane_id": "p", "agent_status": "idle"}], {})
        self.assertEqual(rows, [])

    def test_place_shows_worktree_name(self):
        rows = board.build_rows([agent("s1", cwd="/home/u/.herdr/worktrees/shop-api/bug-549")], {})
        self.assertEqual(rows[0]["place"], "shop-api/bug-549")


def workspace(wid, linked):
    return {"workspace_id": wid, "worktree": {"is_linked_worktree": linked, "checkout_path": "/x"}}


class WorktreeRows(unittest.TestCase):
    def test_row_knows_workspace_and_if_it_is_a_linked_worktree(self):
        rows = board.build_rows([agent("s1", workspace_id="w1"), agent("s2", workspace_id="w2", pane="p2")], {},
                                [workspace("w1", True), workspace("w2", False)])
        by = {r["session_id"]: r for r in rows}
        self.assertEqual(by["s1"]["workspace_id"], "w1")
        self.assertTrue(by["s1"]["is_worktree"])
        self.assertFalse(by["s2"]["is_worktree"])

    def test_unknown_workspace_is_not_a_worktree(self):
        rows = board.build_rows([agent("s1", workspace_id="w9")], {}, [])
        self.assertFalse(rows[0]["is_worktree"])


class BaseMarkAndRepoRoot(unittest.TestCase):
    def _rows(self):
        ws = [{"workspace_id": "w1", "worktree": {"is_linked_worktree": False, "checkout_path": "/p/shop",
                                                    "repo_root": "/p/shop"}},
              {"workspace_id": "w2", "worktree": {"is_linked_worktree": True, "checkout_path": "/h/wt/shop/x",
                                                    "repo_root": "/p/shop"}},
              {"workspace_id": "w3"}]
        agents = [agent("base", workspace_id="w1", pane="p1"), agent("wt", workspace_id="w2", pane="p2"),
                  agent("nogit", workspace_id="w3", pane="p3")]
        return {r["session_id"]: r for r in board.build_rows(agents, {}, ws)}

    def test_kind_marks_base_worktree_and_plain_folder(self):
        by = self._rows()
        self.assertEqual(by["base"]["kind"], "base")
        self.assertEqual(by["wt"]["kind"], "worktree")
        self.assertIsNone(by["nogit"]["kind"])

    def test_worktree_and_base_share_repo_root(self):
        by = self._rows()
        self.assertEqual(by["base"]["repo_root"], "/p/shop")
        self.assertEqual(by["wt"]["repo_root"], "/p/shop")
        self.assertIsNone(by["nogit"]["repo_root"])


class GitFallback(unittest.TestCase):
    def test_base_and_linked_worktree_from_git(self):
        from cavewall import worktree
        with tempfile.TemporaryDirectory() as d:
            repo, wt = os.path.join(d, "repo"), os.path.join(d, "wt")
            os.makedirs(repo)
            _git(repo, "init", "-q", "-b", "main")
            _git(repo, "commit", "-q", "--allow-empty", "-m", "i")
            _git(repo, "worktree", "add", "-q", wt)
            sub = os.path.join(repo, "src")
            os.makedirs(sub)
            self.assertEqual(worktree.git_kind(sub), ("base", os.path.realpath(repo)))
            self.assertEqual(worktree.git_kind(wt), ("worktree", os.path.realpath(repo)))
            self.assertEqual(worktree.git_kind(d), (None, None))

    def test_fill_rows_only_where_herdr_had_nothing(self):
        from cavewall import worktree
        rows = [{"kind": None, "repo_root": None, "checkout": "/a", "is_worktree": False},
                {"kind": "base", "repo_root": "/b", "checkout": "/b", "is_worktree": False}]
        calls = []
        worktree.fill_git_kind(rows, lambda p: calls.append(p) or ("worktree", "/root"))
        self.assertEqual(calls, ["/a"])
        self.assertEqual((rows[0]["kind"], rows[0]["repo_root"], rows[0]["is_worktree"]),
                         ("worktree", "/root", True))


class Refuge(unittest.TestCase):
    def _r(self, sid, ws, kind, root):
        return {"session_id": sid, "workspace_id": ws, "kind": kind, "repo_root": root}

    def test_prefers_base_checkout_of_same_repo(self):
        rows = [self._r("a", "w1", "base", "/p/other"), self._r("b", "w2", "base", "/p/shop"),
                self._r("c", "w3", "worktree", "/p/shop")]
        self.assertEqual(board.refuge(rows, rows[2]), "w2")

    def test_falls_back_to_any_other_workspace(self):
        rows = [self._r("a", "w1", "base", "/p/other"), self._r("c", "w3", "worktree", "/p/shop")]
        self.assertEqual(board.refuge(rows, rows[1]), "w1")

    def test_none_when_it_is_the_only_workspace(self):
        rows = [self._r("c", "w3", "worktree", "/p/shop"), self._r("d", "w3", "worktree", "/p/shop")]
        self.assertIsNone(board.refuge(rows, rows[0]))


class AgentName(unittest.TestCase):
    def test_slug_from_branch(self):
        from cavewall import worktree
        self.assertEqual(worktree.agent_name("Fix/Bug 507!", set()), "fix-bug-507")

    def test_must_start_with_letter_and_fit_32(self):
        from cavewall import worktree
        n = worktree.agent_name("507-" + "x" * 60, set())
        self.assertRegex(n, r"^[a-z][a-z0-9_-]{0,31}$")

    def test_unique_against_live_names(self):
        from cavewall import worktree
        self.assertEqual(worktree.agent_name("fix", {"fix", "fix-2"}), "fix-3")

    def test_empty_gets_default(self):
        from cavewall import worktree
        self.assertRegex(worktree.agent_name("", set()), r"^[a-z][a-z0-9_-]{0,31}$")


class WorktreeRisk(unittest.TestCase):
    def test_clean_worktree_has_no_risk(self):
        from cavewall import worktree
        self.assertEqual(worktree.risks(dirty=0, unpushed=0), [])

    def test_dirty_and_unpushed_are_both_named(self):
        from cavewall import worktree
        self.assertEqual(worktree.risks(dirty=3, unpushed=2),
                         ["3 uncommitted files", "2 unpushed commits"])

    def test_singular_wording(self):
        from cavewall import worktree
        self.assertEqual(worktree.risks(dirty=1, unpushed=1),
                         ["1 uncommitted file", "1 unpushed commit"])

    def test_unknown_state_counts_as_risk(self):
        from cavewall import worktree
        self.assertEqual(worktree.risks(dirty=None, unpushed=0), ["git state unknown"])

    def test_inspect_real_repo(self):
        import subprocess
        from cavewall import worktree
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(["git", "init", "-q", d], check=True)
            open(os.path.join(d, "f"), "w").close()
            dirty, unpushed = worktree.inspect(d)
        self.assertEqual(dirty, 1)
        self.assertEqual(unpushed, 0)


def _git(d, *a):
    import subprocess
    return subprocess.run(["git", "-C", d, "-c", "user.name=t", "-c", "user.email=t@t", *a],
                          check=True, capture_output=True, text=True).stdout.strip()


class ResetMainCheckout(unittest.TestCase):
    def _repo(self, d, default="main"):
        _git(d, "init", "-q", "-b", default)
        with open(os.path.join(d, "f"), "w") as f:
            f.write("base")
        _git(d, "add", "f")
        _git(d, "commit", "-qm", "base")
        _git(d, "checkout", "-qb", "feature")
        with open(os.path.join(d, "f"), "w") as f:
            f.write("dirty")

    def test_resets_dirty_feature_branch_back_to_clean_main(self):
        from cavewall import worktree
        with tempfile.TemporaryDirectory() as d:
            self._repo(d)
            self.assertEqual(worktree.reset_to_default(d), "")
            self.assertEqual(_git(d, "branch", "--show-current"), "main")
            self.assertEqual(_git(d, "status", "--porcelain"), "")
            self.assertIn("feature", _git(d, "branch"))  # branch kept

    def test_untracked_files_do_not_count_for_reset(self):
        from cavewall import worktree
        with tempfile.TemporaryDirectory() as d:
            self._repo(d)
            open(os.path.join(d, "new"), "w").close()
            self.assertEqual(worktree.tracked_changes(d), 1)  # only f, not the untracked "new"

    def test_not_a_repo_is_refused(self):
        from cavewall import worktree
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(worktree.tracked_changes(d))
            self.assertNotEqual(worktree.reset_to_default(d), "")

    def test_falls_back_to_master(self):
        from cavewall import worktree
        with tempfile.TemporaryDirectory() as d:
            self._repo(d, default="master")
            self.assertEqual(worktree.default_branch(d), "master")

    def test_reset_risk_ignores_unpushed_because_branch_is_kept(self):
        from cavewall import worktree
        self.assertEqual(worktree.reset_risks(dirty=2), ["2 uncommitted files"])
        self.assertEqual(worktree.reset_risks(dirty=0), [])


class SafeDrawing(unittest.TestCase):
    def test_put_survives_curses_error_on_overflowing_wide_text(self):
        import curses
        from cavewall import tui

        class Win:
            def getmaxyx(self):
                return (10, 40)

            def addnstr(self, *a):
                raise curses.error("addnwstr() returned ERR")

        tui._put(Win(), 9, 0, " 🪓 digging".ljust(40))  # must not raise

    def test_put_leaves_room_for_wide_characters(self):
        from cavewall import tui
        drawn = []

        class Win:
            def getmaxyx(self):
                return (10, 20)

            def addnstr(self, y, x, text, n, attr=0):
                drawn.append(text[:n])

        tui._put(Win(), 9, 0, "🪓" * 30)
        self.assertLessEqual(tui._cells(drawn[0]), 19)


class CrossPlatform(unittest.TestCase):
    def test_place_of_windows_paths(self):
        self.assertEqual(board.place_of(r"C:\Users\u\.herdr\worktrees\shop-api\bug-549"), "shop-api/bug-549")
        self.assertEqual(board.place_of("C:\\Users\\u\\projects\\web-app\\"), "web-app")

    def test_detach_kwargs_per_os(self):
        from cavewall import compat
        self.assertEqual(compat.detach_kwargs("posix"), {"start_new_session": True})
        win = compat.detach_kwargs("nt")
        self.assertNotIn("start_new_session", win)
        self.assertTrue(win["creationflags"] & 0x00000008)  # DETACHED_PROCESS
        self.assertTrue(win["creationflags"] & 0x08000000)  # CREATE_NO_WINDOW

    def test_exe_resolves_or_falls_back_to_name(self):
        from cavewall import compat
        self.assertTrue(os.path.isabs(compat.exe("git")))
        self.assertEqual(compat.exe("surely-not-a-real-tool-xyz"), "surely-not-a-real-tool-xyz")

    def test_lock_is_exclusive_and_released(self):
        from cavewall import compat
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, ".x.lock")
            self.assertFalse(compat.is_locked(p))
            held = compat.try_lock(p)
            self.assertIsNotNone(held)
            self.assertTrue(compat.is_locked(p))
            self.assertIsNone(compat.try_lock(p))
            compat.unlock(held)
            self.assertFalse(compat.is_locked(p))

    def test_no_posix_only_modules_imported_at_top_level(self):
        import ast
        import pathlib
        root = pathlib.Path(__file__).resolve().parent.parent / "cavewall"
        for f in root.glob("*.py"):
            if f.name == "compat.py":
                continue
            tree = ast.parse(f.read_text(encoding="utf-8"))
            names = {a.name for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))
                     for a in getattr(n, "names", [])} | {getattr(n, "module", None) for n in ast.walk(tree)
                                                         if isinstance(n, ast.ImportFrom)}
            self.assertFalse(names & {"fcntl", "msvcrt"}, f.name)
            self.assertNotIn("os.fork", f.read_text(encoding="utf-8"), f.name)


class CavePainting(unittest.TestCase):
    def test_big_painting_when_lots_of_room(self):
        from cavewall import art
        self.assertIs(art.pick(rows=20, cols=120), art.BIG)

    def test_small_painting_when_little_room(self):
        from cavewall import art
        self.assertIs(art.pick(rows=len(art.SMALL) + 1, cols=60), art.SMALL)

    def test_nothing_when_no_room(self):
        from cavewall import art
        self.assertIsNone(art.pick(rows=1, cols=120))
        self.assertIsNone(art.pick(rows=20, cols=10))

    def test_painting_fits_what_it_claims(self):
        from cavewall import art
        for rows, cols in ((5, 40), (9, 70), (30, 200)):
            p = art.pick(rows, cols)
            if p:
                self.assertLess(len(p), rows)
                self.assertLess(max(map(len, p)), cols)


if __name__ == "__main__":
    unittest.main()
