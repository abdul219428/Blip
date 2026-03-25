# Blip ⚡

A tiny Python utility for quickly capturing thoughts with a global hotkey.

**Press `Ctrl + Shift + Space` → type your thought → hit `Enter`. Done.**

Notes are appended (with a timestamp) to `~/blip.md`.

---

## Requirements

- Python 3.9+
- Windows, macOS, or Linux
- `tkinter` (included with most Python installations)
- [`pynput`](https://pypi.org/project/pynput/)

## Cross-platform behavior

Blip runs on any PC that has Python 3.9+ with `tkinter` available:

- **Windows**: notes are written to your user home folder, for example `C:\Users\alice\blip.md`
- **macOS**: notes are written to your user home folder, for example `/Users/alice/blip.md`
- **Linux**: notes are written to your user home folder, for example `/home/alice/blip.md`

On macOS, you may also need to allow accessibility permissions so the global hotkey can be captured.

## Installation

```bash
# Clone the repo
git clone https://github.com/abdul219428/Blip.git
cd Blip

# Install dependencies
pip install -r requirements.txt
```

Or install as a command-line tool:

```bash
pip install .
```

## Usage

```bash
python blip.py
# or, if installed via pip:
blip
```

| Key | Action |
|-----|--------|
| `Ctrl + Shift + Space` | Open the capture window |
| `Enter` | Save note and close window |
| `Escape` | Dismiss window without saving |

Notes are written to `~/blip.md` in the format:

```
- [2024-01-15 09:30] Remember to buy milk
```

## Configuration

Edit the constants at the top of `blip.py`:

| Constant | Default | Description |
|----------|---------|-------------|
| `HOTKEY` | `<ctrl>+<shift>+<space>` | Global hotkey combination |
| `OUTPUT_FILE` | `~/blip.md` | Path to the notes file |
