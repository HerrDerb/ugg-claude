# Open in VS Code

Herdr plugin that opens VS Code on the working directory of the focused pane.
It uses the pane's foreground cwd, so a `cd` in the shell or the folder of an
agent like Claude running in the pane is respected.

## Install

```bash
herdr plugin link /path/to/herdr/open-code
```

Then bind a key in `~/.config/herdr/config.toml` and run `herdr server reload-config`:

```toml
[[keys.command]]
key = "ctrl+alt+o"
type = "plugin_action"
command = "ugg.opencode.open"          # on Windows: "ugg.opencode.open-windows"
description = "open pane folder in VS Code"
```

Needs `code` on the PATH (`code.cmd` on Windows) and Python 3.

## Tests

```bash
python3 -m unittest discover -s tests -t .
```
