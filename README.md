# ugg-claude

🪨🍖 **Ugg no Claude.** Ugg talk simple, Ugg think big.

This repo hold Ugg — a Claude Code persona and config. Two rock, one job: make Claude
talk like caveman, teach like professor.

## What in cave

| Rock | Job |
| --- | --- |
| `CLAUDE.md` | Ugg brain. Caveman voice + teaching mandate Claude must follow. |
| `settings.json` | Claude Code settings: model, theme, plugins, status line. |
| `README.md` | This rock. You read now. |

## Ugg brain (`CLAUDE.md`)

Two instruction live here:

1. **Voice** — short word, wacky punchline, happy Ugg. Caveman mouth, future-man mind.
2. **Teacher** — Ugg not just do work, Ugg make human *understand* work. Ugg keep running
   checklist, ask human to say back her understanding, quiz her, drill the *why* behind
   the why. Session no end till human master list.

Rule two do the heavy lift. Voice just make it fun.

## Settings (`settings.json`)

```json
{
  "model": "opus[1m]",
  "theme": "dark",
  "statusLine": { "type": "command", "command": "…" }
}
```

- `model: opus[1m]` — Opus with 1M-token context. Big mammoth memory.
- `theme: dark` — cave dark.
- `rust-analyzer-lsp` — Rust language server plugin.
- `statusLine` — bash one-liner. Read JSON on stdin, `jq` out model name and current
  dir, print dim `[Opus 5] ugg-claude`. Need `jq` on PATH or status line go silent.

## Use Ugg

Claude Code read `CLAUDE.md` from repo root by itself — clone repo, open Claude Code in it,
Ugg wake up.

```bash
git clone <this-repo> && cd ugg-claude
claude
```

Want Ugg everywhere, not just here? Copy brain to home cave:

```bash
cp CLAUDE.md ~/.claude/CLAUDE.md
```

⚠️ **Settings not auto-load from here.** Claude Code look for project settings in
`.claude/settings.json`, not root `settings.json`. Root file is a *template* — copy it
where Claude Code look:

```bash
mkdir -p .claude && cp settings.json .claude/settings.json   # this project only
# or, for every project:
cp settings.json ~/.claude/settings.json
```

`model`, `theme`, and `statusLine` are user-level taste anyway — home cave (`~/.claude/`)
usually right place for them.

## Ugg anthem

> Rock hard. Word short. Brain big.
> Ugg no give fish — Ugg teach spear. 🍖
