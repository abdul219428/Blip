# CogStash ⚡

A tiny Python utility for quickly capturing thoughts with a global hotkey.

**Press `Ctrl + Shift + Space` → type your thought → hit `Enter`. Done.**

Notes are appended (with a timestamp) to `~/cogstash.md`.

---

## Requirements

- Python 3.9+
- Windows, macOS, or Linux
- `tkinter` (included with most Python installations)
- [`pynput`](https://pypi.org/project/pynput/)

## Cross-platform behavior

CogStash runs on any PC that has Python 3.9+ with `tkinter` available:

- **Windows**: notes are written to your user home folder, for example `C:\Users\alice\cogstash.md`
- **macOS**: notes are written to your user home folder, for example `/Users/alice/cogstash.md`
- **Linux**: notes are written to your user home folder, for example `/home/alice/cogstash.md`

On macOS, you may also need to allow accessibility permissions so the global hotkey can be captured.

## Installation

```bash
# Clone the repo
git clone https://github.com/abdul219428/CogStash.git
cd CogStash

# Install dependencies
pip install -r requirements.txt
```

Or install as a command-line tool:

```bash
pip install .
```

## Usage

```bash
python cogstash.py
# or, if installed via pip:
cogstash
```

| Key | Action |
|-----|--------|
| `Ctrl + Shift + Space` | Open the capture window |
| `Enter` | Save note and close window |
| `Escape` | Dismiss window without saving |

Notes are written to `~/cogstash.md` in the format:

```
- [2024-01-15 09:30] Remember to buy milk
```

## Configuration

Edit the constants at the top of `cogstash.py`:

| Constant | Default | Description |
|----------|---------|-------------|
| `HOTKEY` | `<ctrl>+<shift>+<space>` | Global hotkey combination |
| `OUTPUT_FILE` | `~/cogstash.md` | Path to the notes file |
