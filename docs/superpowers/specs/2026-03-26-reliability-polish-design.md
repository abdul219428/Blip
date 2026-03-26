# Blip Phase 1: Reliability & Polish — Design Spec

**Date:** 2026-03-26
**Status:** Approved

## Problem

Blip is a functional prototype but lacks reliability and polish for daily use:

- No feedback after saving a note (did it work?)
- No error handling on file writes — failures silently crash or are swallowed
- No system tray icon — easy to forget Blip is running
- Font is hardcoded to "Segoe UI" — degrades on macOS and Linux
- No DPI awareness — window appears tiny on HiDPI displays
- No tests

## Approach

Harden the foundation with five targeted improvements plus tests, keeping everything in the single-file architecture (`blip.py` + new `test_blip.py`). One new dependency: `pystray` (with `Pillow`).

## Design

### 1. Save Feedback (Green/Red Border Flash)

Since `overrideredirect(True)` removes the native window border, the root window's background color acts as a visible border (the inner frame has padding creating a 3px gap).

**Success flow:**
1. User presses Enter → `on_submit()` calls `append_note()`
2. `append_note()` returns `True`
3. Root background changes to green (`#a6e3a1`) for 300ms via `root.after()`
4. Background resets → window hides

**Error flow:**
1. `append_note()` catches the exception, logs it, returns `False`
2. Root background changes to red (`#f38ba8`) for 300ms
3. Background resets → window **stays open** so user can retry

### 2. System Tray Icon (pystray)

**Dependencies:** `pystray>=0.19`, `Pillow>=9.0`

**Icon image:** A ⚡ glyph rendered to a 64×64 RGBA PNG at startup using `Pillow.ImageDraw`. No external icon file.

**Menu items:**
- **Blip ⚡** — disabled label (app name)
- **Open blip.md** — opens the notes file in the OS default editor
  - Windows: `os.startfile(path)`
  - macOS: `subprocess.run(["open", path])`
  - Linux: `subprocess.run(["xdg-open", path])`
- **Quit** — posts `"QUIT"` to the app queue → triggers `root.destroy()`

**Thread model:** `pystray.Icon.run()` blocks, so it runs on a daemon thread. It communicates with the tkinter main loop through the existing `queue.Queue` pattern. The `poll_queue` method handles `"QUIT"` in addition to `"SHOW"`.

**Graceful degradation:** If `pystray` fails to create the icon (e.g., no display server on a headless Linux box), log a warning and continue without the tray icon. Blip remains usable via the console.

### 3. Error Handling & Logging

**Logger setup:**
- Uses Python's built-in `logging` module (no new dependency)
- Log file: `~/blip.log` (same directory as `blip.md`)
- Format: `[2026-03-26 17:15] ERROR: Failed to write to blip.md: [Errno 13] Permission denied`
- Level: WARNING and above (don't log routine operations)
- Logger configured at module level with a `FileHandler`

**Error surfaces:**
| Error | Handling |
|-------|----------|
| File write fails (`OSError`, `PermissionError`) | Log error, flash red, keep window open |
| pystray init fails | Log warning, continue without tray |
| pynput hotkey registration fails | Log error, print to console (user needs to see this) |

**`append_note` signature change:**
```python
def append_note(self, text: str) -> bool:
    """Append a timestamped note. Returns True on success, False on error."""
```

### 4. Cross-Platform Fonts

A `platform_font()` function returns the OS-native font family:

| `sys.platform` | Font Family | Rationale |
|-----------------|-------------|-----------|
| `win32` | Segoe UI | Ships with every Windows since Vista |
| `darwin` | Helvetica Neue | Ships with macOS; SF Pro doesn't resolve by name in tkinter |
| `linux` | sans-serif | Resolved by fontconfig (Noto Sans, DejaVu, etc.) |
| Other | TkDefaultFont | Safe tkinter fallback |

Called once at startup. The result is used wherever fonts are specified in `setup_ui()`.

### 5. DPI Awareness

**Windows:** Call `ctypes.windll.shcore.SetProcessDpiAwareness(1)` before creating the `Tk()` root. This prevents Windows from bitmap-scaling the window and ensures crisp text on 4K displays.

**macOS / Linux:** Tkinter handles DPI natively — no extra work needed.

**Implementation:** A `configure_dpi()` function called at the top of `main()`, before `root = tk.Tk()`. Wrapped in try/except so unsupported platforms don't crash.

### 6. Testing

**File:** `test_blip.py` using `pytest`

**Test cases:**

| Test | What it verifies |
|------|-----------------|
| `test_append_note_creates_file` | Creates `blip.md` if it doesn't exist, writes correct format |
| `test_append_note_appends` | Multiple notes are appended, not overwritten |
| `test_append_note_error_handling` | Simulates write failure (read-only path), verifies returns `False` and logs error |
| `test_platform_font` | Returns a string for each mocked `sys.platform` value |
| `test_show_hide_state` | `show_window` / `hide_window` toggle `is_visible` correctly |

**Not tested** (impractical in unit tests):
- Global hotkey registration (requires OS-level hooks)
- System tray icon (requires display server)
- Visual flash animation timing

## Dependencies

**New:**
- `pystray>=0.19`
- `Pillow>=9.0`

**Updated files:**
- `blip.py` — all changes
- `test_blip.py` — new file
- `requirements.txt` — add pystray, Pillow
- `pyproject.toml` — add pystray, Pillow to dependencies

## Out of Scope

- Multi-line input (Phase 2)
- Tags/categories (Phase 2)
- Config file (Phase 2)
- Search/browse (Phase 3)
- Auto-start / installer (Phase 4)
