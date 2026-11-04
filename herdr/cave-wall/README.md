# Cave wall

A board in [herdr](https://herdr.dev) that shows every Claude Code session you run in parallel,
with a short "where was I" card for each one. Sessions that wait for you are listed first.

```
 🪨 cave wall  29 sessions  6 need you
 ! ⌂ shop-api                       4m  Ship retry fix for payment webhook via PR
 ! ⌂ web-app                       12m  Bump Java 21 to 25 and get it merged
 ✓   shop-api/bug-549               1h  Find root cause of bug 549
 ~   docs/worktree-calm-field       now Rewrite install guide
 ·   infra                          2h  🧹 cleared, ready for a new hunt
 ────────────────────────────────────────────────────────────────
 state  PR #2653 open, tests green, CI pending
 next   CI running, then verify tag on dev
 ↑↓/jk move  ⏎ jump  n new worktree  s seed card  d done  ⌂ = base checkout
```

## How it works

- **Card writer.** A Claude Code `Stop` hook runs after every finished turn. It returns at once
  and starts a detached `claude -p --model haiku` that reads the end of the transcript and writes
  a card (goal, state, next step, needs you) to `~/.claude/cavewall/<session>.json`.
- **Board.** Joins `herdr agent list` with the cards by session id. It also repaints cards that
  are older than their transcript, which covers sessions started before the hook existed.
- **Todo lines.** If the last answer ends with `Open todos: 🟢 none | 🔴 ...` and `Optional todos: 🟢 none | 🟠 ...` lines
  (the repo `CLAUDE.md` asks for them), they decide "needs you" and "next" outright, no guessing.
  Without them the board reads the `Implemented: 🟢` status line and looks for a `?`.
- **Painting.** Free space under the list becomes a cave wall in caveman painting style: bare
  rock under a flickering torch, red ochre, charcoal and chalk, handprints. A 30 s story plays on
  it: a mammoth and her baby walk in, hunters throw, the mammoth chases them off the wall, walks
  home, and the hunters sneak back to dance and scratch a wacky anthem into the rock.
  4 pictures a second; herdr is still asked every 3 s. Small cast when space is tight.
- **Empty sessions** (fresh or only `/clear`) get a 🌱 or 🧹 card without a model call.

## Keys

| Key | Does |
| --- | --- |
| `↑↓` / `jk` | move |
| `Enter` | jump to the session's pane (closes the popup) |
| `n` | new worktree of the row's repo from fresh `origin/main`, with Claude started in it. Works on a base checkout or a worktree row. Empty branch name = herdr picks one |
| `s` | write this session's card now |
| `d` | done. Worktree: delete it and close its terminal. Base checkout: `git reset --hard` and check out the default branch (branch kept). Asks first; needs capital `Y` when something would be lost |
| `r` / `q` | refresh / quit |

`⌂` marks a base checkout, as opposed to a worktree.

## Install

Needs Python 3 (standard library only), `git`, `herdr` and the `claude` CLI. `gh` is optional
and adds the PR link to cards. Runs on Linux, macOS and Windows.

```bash
python3 install.py            # Windows: py install.py
herdr server reload-config
```

The installer is safe to run again and writes `.bak-cavewall` backups first. It sets up:

1. a `cavewall` launcher in `~/.local/bin`
2. the `Stop` hook in `~/.claude/settings.json`
3. links this folder as herdr plugin `ugg.cavewall` (`herdr-plugin.toml`) and binds `ctrl+alt+w`
   to its `open` action. Falls back to a plain popup key if the link fails.

On Windows also run `py -m pip install windows-curses`.

Remove everything again with `python3 install.py --uninstall`.

Already running Claude sessions do not load new hooks; the board repaints their cards instead.

## Things to know

- **Cost:** one small haiku call per finished turn, in every session (the hook is global).
- **Privacy:** cards are plain JSON in `~/.claude/cavewall/` and can contain project context.
  The transcript tail goes to Anthropic, as in normal Claude use.
- **`d` is destructive** by design. Read the prompt before you press `Y`.
- **Deleting the board's own workspace:** herdr closes every pane of a closed workspace, the
  board popup included, and plugin popups can only open on the active pane. So a detached relay
  focuses a safe workspace (the repo's base checkout if open), removes the worktree, cleans the
  cards and opens the board again there.
- Settings: `CAVEWALL_MODEL` (default `haiku`), `CAVEWALL_DIR` (default `~/.claude/cavewall`).

## Develop

```bash
python3 -m unittest
```
