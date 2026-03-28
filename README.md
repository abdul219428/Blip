# CogStash ⚡

A global hotkey brain dump — press, type, gone.

**Press `Ctrl + Shift + Space` → type your thought → hit `Enter`. Done.**

Notes are timestamped and appended to `~/cogstash.md`. Browse them later in
a card-based UI, or query from the command line.

<!-- TODO: add screenshot of capture window -->

---

## Features

- ⌨️ **Global hotkey** — capture thoughts from any app without switching windows
- 🏷️ **Smart tags** — `#todo`, `#urgent`, `#important`, `#idea` with emoji prefixes
- 🔤 **Autocomplete** — type `#` and pick a tag from the popup
- 🎨 **Themes** — 5 built-in color schemes (tokyo-night, light, dracula, gruvbox, mono)
- 🗂️ **Browse window** — card view with live search, tag filtering, and mark-done
- 💻 **CLI commands** — `recent`, `search`, `tags` with ANSI-colored output
- 🖥️ **System tray** — runs quietly in the background with a tray icon menu
- 🌍 **Cross-platform** — Windows, macOS, and Linux

---

## Requirements

- Python 3.9+
- `tkinter` (included with most Python installations)
- [`pynput`](https://pypi.org/project/pynput/) — global hotkey listener
- [`pystray`](https://pypi.org/project/pystray/) + [`Pillow`](https://pypi.org/project/Pillow/) — system tray icon

All dependencies are installed automatically via [`uv`](https://docs.astral.sh/uv/).

---

## Installation

```bash
# Clone the repo
git clone https://github.com/abdul219428/CogStash.git
cd CogStash

# Install uv (if not already installed)
# Windows: winget install astral-sh.uv
# macOS/Linux: curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

Or install as a command-line tool:

```bash
uv pip install .
```

---

## Quick Start

```bash
# Run directly with uv
uv run cogstash

# Or, if installed globally:
cogstash
```

CogStash starts in the system tray. Press the hotkey to capture a note:

| Key | Action |
|-----|--------|
| `Ctrl + Shift + Space` | Open the capture window |
| `Enter` | Save note and close window |
| `Shift + Enter` | Insert a new line (multi-line note) |
| `Escape` | Dismiss window without saving |

Notes are written to `~/cogstash.md` in this format:

```
- [2026-03-27 14:30] Remember to buy milk
- [2026-03-27 14:31] ☐ Review pull request #42 #todo
- [2026-03-27 14:32] 💡 What if we cached the API response? #idea
  Could save 200ms per request on the hot path.
  Worth benchmarking with production traffic.
```

Multi-line notes use 2-space indented continuation lines.

---

## Smart Tags

Type `#` in the capture window to trigger autocomplete. Four built-in tags
are recognized with special emoji prefixes:

| Tag | Prefix | Purpose |
|-----|--------|---------|
| `#todo` | ☐ | Actionable task (can be marked done later) |
| `#urgent` | 🔴 | Needs immediate attention |
| `#important` | ⭐ | High-value note |
| `#idea` | 💡 | Creative thought or suggestion |

Tags can appear anywhere in the note text. Multiple tags per note are supported.

---

## CLI Commands

CogStash includes a command-line interface for querying notes without opening
the GUI.

### `cogstash recent`

Show the most recent notes (newest first).

```bash
cogstash recent            # last 20 notes (default)
cogstash recent --limit 5  # last 5 notes
```

### `cogstash search`

Full-text search across all notes. Case-insensitive, multi-word AND matching.

```bash
cogstash search "buy milk"        # notes containing "buy" AND "milk"
cogstash search "todo" --limit 10 # limit results
```

### `cogstash tags`

List all tags with usage counts, sorted by frequency.

```bash
cogstash tags
```

Example output:

```
  todo         12
  idea          7
  urgent        3
  important     2
```

> **Note:** Output is ANSI-colored when writing to a terminal. Colors are
> automatically disabled when piping to a file or another command.

---

## Browse Window

Open the Browse window from the system tray icon → **"Browse Notes"**.

<!-- TODO: add screenshot of browse window -->

**Features:**

- 📇 **Card view** — each note displayed as a card with colored left border
- 🔍 **Live search** — filter notes as you type (200ms debounce)
- 🏷️ **Tag filter pills** — click All, #todo, #urgent, #important, or #idea
- ✅ **Mark done** — check off `#todo` items (☐ → ☑, with strikethrough)
- 📅 **Date headers** — notes grouped by TODAY, YESTERDAY, or date label
- 📊 **Footer** — shows total note count and open todo count

---

## Themes

CogStash ships with 5 color themes. Set your preference in the config file.

| Theme | Description |
|-------|-------------|
| `tokyo-night` | Dark blue-gray (default) |
| `light` | Clean white background |
| `dracula` | Dark purple palette |
| `gruvbox` | Warm retro dark theme |
| `mono` | Minimalist gray-on-black |

### Window Sizes

| Preset | Width |
|--------|-------|
| `compact` | 320 px |
| `default` | 400 px |
| `wide` | 520 px |

---

## Configuration

CogStash reads settings from `~/.cogstash.json`. The file is created
automatically on first run with default values.

| Key | Default | Description |
|-----|---------|-------------|
| `hotkey` | `<ctrl>+<shift>+<space>` | Global hotkey combination |
| `output_file` | `~/cogstash.md` | Path to the notes file |
| `log_file` | `~/cogstash.log` | Path to the log file |
| `theme` | `tokyo-night` | Color theme |
| `window_size` | `default` | Capture window size preset |

Example config:

```json
{
  "hotkey": "<ctrl>+<shift>+<space>",
  "theme": "dracula",
  "window_size": "wide"
}
```

Only include the keys you want to override — missing keys use defaults.

---

## Cross-Platform Notes

CogStash runs on any system with Python 3.9+ and `tkinter`:

| OS | Notes file location |
|----|---------------------|
| Windows | `C:\Users\<you>\cogstash.md` |
| macOS | `/Users/<you>/cogstash.md` |
| Linux | `/home/<you>/cogstash.md` |

**macOS:** You may need to grant accessibility permissions for the global
hotkey to work. Go to System Settings → Privacy & Security → Accessibility
and add your terminal or Python.

**Linux:** Requires an X11 or Wayland session with `tkinter` support.
Some minimal desktop environments may need `python3-tk` installed separately.

---

## Development

```bash
# Install with dev dependencies (ruff, mypy, pytest, etc.)
uv sync --extra dev

# Run tests
uv run pytest

# Lint
uv run ruff check src/ tests/

# Type check
uv run mypy src/
```

---

## License

<!-- TODO: add license -->
