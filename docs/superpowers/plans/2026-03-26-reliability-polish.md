# Phase 1: Reliability & Polish — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden Blip with save feedback, error handling, system tray icon, cross-platform fonts, DPI awareness, and tests.

**Architecture:** All changes stay in `blip.py` (single-file app). New `test_blip.py` for tests. Three new helper functions (`platform_font`, `configure_dpi`, `create_tray_icon`) plus modifications to the `Blip` class. Uses the existing `queue.Queue` pattern for thread communication.

**Tech Stack:** Python 3.9+, tkinter, pynput, pystray, Pillow, pytest, logging (stdlib)

**Spec:** `docs/superpowers/specs/2026-03-26-reliability-polish-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `blip.py` | Modify | Add logging, platform_font(), configure_dpi(), tray icon, error handling, save feedback |
| `test_blip.py` | Create | Unit tests for append_note, platform_font, show/hide state |
| `requirements.txt` | Modify | Add pystray, Pillow, pytest |
| `pyproject.toml` | Modify | Add pystray, Pillow to dependencies |

---

### Task 1: Add Dependencies

**Files:**
- Modify: `requirements.txt`
- Modify: `pyproject.toml`

- [ ] **Step 1: Update requirements.txt**

```
pynput>=1.7
pystray>=0.19
Pillow>=9.0
pytest>=7.0
```

- [ ] **Step 2: Update pyproject.toml**

In the `[project]` section, change the `dependencies` list to:

```toml
dependencies = [
    "pynput>=1.7",
    "pystray>=0.19",
    "Pillow>=9.0",
]
```

- [ ] **Step 3: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: All packages install successfully.

- [ ] **Step 4: Commit**

```bash
git add requirements.txt pyproject.toml
git commit -m "chore: add pystray, Pillow, pytest dependencies"
```

---

### Task 2: Add Logging Setup

**Files:**
- Modify: `blip.py` (add imports + module-level logger config, lines 1–17)

- [ ] **Step 1: Add logging imports and config**

Add `import logging` and `import sys` to the imports section (after line 11, `from pynput import keyboard`). Then add a module-level logger between the imports and the `# ── Config` section:

```python
import logging

LOG_FILE = Path.home() / "blip.log"

logger = logging.getLogger("blip")
logger.setLevel(logging.WARNING)
_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M"))
logger.addHandler(_handler)
```

Place this right after the `OUTPUT_FILE` line inside the `# ── Config` block so both paths live together.

- [ ] **Step 2: Verify import works**

Run: `python -c "import blip; print('OK')"`
Expected: `OK` (no import errors)

- [ ] **Step 3: Commit**

```bash
git add blip.py
git commit -m "feat: add logging infrastructure"
```

---

### Task 3: Add Platform Font Helper

**Files:**
- Modify: `blip.py` (add `import sys`, add `platform_font()` function, update `setup_ui()`)

- [ ] **Step 1: Write the test**

Create `test_blip.py` with:

```python
"""Tests for blip.py."""

import sys
from unittest.mock import patch
from pathlib import Path


def test_platform_font_windows():
    with patch.object(sys, "platform", "win32"):
        from blip import platform_font
        # Re-evaluate since it's a function call
        result = platform_font()
        assert result == "Segoe UI"


def test_platform_font_macos():
    with patch.object(sys, "platform", "darwin"):
        from blip import platform_font
        result = platform_font()
        assert result == "Helvetica Neue"


def test_platform_font_linux():
    with patch.object(sys, "platform", "linux"):
        from blip import platform_font
        result = platform_font()
        assert result == "sans-serif"


def test_platform_font_unknown():
    with patch.object(sys, "platform", "freebsd"):
        from blip import platform_font
        result = platform_font()
        assert result == "TkDefaultFont"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest test_blip.py -v`
Expected: FAIL — `platform_font` does not exist yet.

- [ ] **Step 3: Implement platform_font()**

Add `import sys` to blip.py imports. Add this function after the config block, before `class Blip`:

```python
def platform_font() -> str:
    """Return the native font family for the current OS."""
    fonts = {
        "win32": "Segoe UI",
        "darwin": "Helvetica Neue",
        "linux": "sans-serif",
    }
    return fonts.get(sys.platform, "TkDefaultFont")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest test_blip.py -v`
Expected: All 4 `test_platform_font_*` tests PASS.

- [ ] **Step 5: Replace hardcoded fonts in setup_ui()**

In `setup_ui()`, replace all three occurrences of `"Segoe UI"` with `platform_font()`:

Line with `font=("Segoe UI", 9)` → `font=(platform_font(), 9)`
Line with `font=("Segoe UI", 12)` → `font=(platform_font(), 12)`
Line with `font=("Segoe UI", 8)` → `font=(platform_font(), 8)`

- [ ] **Step 6: Verify import still works**

Run: `python -c "import blip; print('OK')"`
Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add blip.py test_blip.py
git commit -m "feat: cross-platform font selection"
```

---

### Task 4: Add DPI Awareness

**Files:**
- Modify: `blip.py` (add `configure_dpi()`, call from `main()`)

- [ ] **Step 1: Add configure_dpi() function**

Add this function after `platform_font()`, before `class Blip`:

```python
def configure_dpi() -> None:
    """Enable DPI awareness on Windows so the UI renders crisply on HiDPI displays."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass
```

- [ ] **Step 2: Call configure_dpi() in main()**

In the `main()` function, add `configure_dpi()` as the first line, before `print(...)`:

```python
def main():
    configure_dpi()
    print(f"Blip is running. ({HOTKEY} to capture · Ctrl+C to quit)")
    ...
```

- [ ] **Step 3: Verify import still works**

Run: `python -c "import blip; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add blip.py
git commit -m "feat: enable DPI awareness on Windows"
```

---

### Task 5: Error Handling in append_note()

**Files:**
- Modify: `blip.py` (update `append_note()`)
- Modify: `test_blip.py` (add error handling tests)

- [ ] **Step 1: Write the tests**

Add these tests to `test_blip.py`:

```python
import tkinter as tk
import re


def test_append_note_creates_file(tmp_path):
    """append_note creates the file and writes the correct format."""
    import blip as blip_mod

    test_file = tmp_path / "blip.md"
    original = blip_mod.OUTPUT_FILE
    blip_mod.OUTPUT_FILE = test_file

    try:
        root = tk.Tk()
        root.withdraw()
        app = blip_mod.Blip(root)
        result = app.append_note("test note")
        root.destroy()

        assert result is True
        content = test_file.read_text(encoding="utf-8")
        assert "test note" in content
        assert re.match(r"- \[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\] test note\n", content)
    finally:
        blip_mod.OUTPUT_FILE = original


def test_append_note_appends(tmp_path):
    """Multiple notes are appended, not overwritten."""
    import blip as blip_mod

    test_file = tmp_path / "blip.md"
    original = blip_mod.OUTPUT_FILE
    blip_mod.OUTPUT_FILE = test_file

    try:
        root = tk.Tk()
        root.withdraw()
        app = blip_mod.Blip(root)
        app.append_note("first")
        app.append_note("second")
        root.destroy()

        lines = test_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2
        assert "first" in lines[0]
        assert "second" in lines[1]
    finally:
        blip_mod.OUTPUT_FILE = original


def test_append_note_error_handling(tmp_path):
    """append_note returns False and logs on write failure."""
    import blip as blip_mod

    original = blip_mod.OUTPUT_FILE
    # Point to a non-existent drive/path that will fail
    blip_mod.OUTPUT_FILE = Path("/nonexistent_mount_xyz/impossible/blip.md")

    try:
        root = tk.Tk()
        root.withdraw()
        app = blip_mod.Blip(root)
        result = app.append_note("should fail")
        root.destroy()

        assert result is False
    finally:
        blip_mod.OUTPUT_FILE = original
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest test_blip.py::test_append_note_creates_file test_blip.py::test_append_note_appends test_blip.py::test_append_note_error_handling -v`
Expected: FAIL — `append_note` currently returns `None`, not `bool`.

- [ ] **Step 3: Update append_note() with error handling**

Replace the `append_note` method in `blip.py`:

```python
    def append_note(self, text: str) -> bool:
        """Append a timestamped note to blip.md. Returns True on success."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        line = f"- [{timestamp}] {text}\n"

        try:
            OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
            with OUTPUT_FILE.open("a", encoding="utf-8") as f:
                f.write(line)
            return True
        except OSError:
            logger.error("Failed to write to %s", OUTPUT_FILE, exc_info=True)
            return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest test_blip.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add blip.py test_blip.py
git commit -m "feat: error handling and logging in append_note"
```

---

### Task 6: Save Feedback (Border Flash)

**Files:**
- Modify: `blip.py` (add `flash_border()`, update `on_submit()`)

- [ ] **Step 1: Add the flash_border() method**

Add this method to the `Blip` class, after `hide_window()`:

```python
    def flash_border(self, color: str, then_hide: bool = True) -> None:
        """Briefly flash the window border, then optionally hide."""
        self.root.configure(bg=color)
        self.root.after(300, lambda: self._reset_border(then_hide))

    def _reset_border(self, then_hide: bool) -> None:
        """Reset border color and optionally hide the window."""
        self.root.configure(bg="#1e1e2e")
        if then_hide:
            self.hide_window()
```

- [ ] **Step 2: Update on_submit() to use flash feedback**

Replace the `on_submit` method:

```python
    def on_submit(self, event=None):
        """Save the note and show visual feedback."""
        text = self.entry.get().strip()
        if not text:
            self.hide_window()
            return
        if self.append_note(text):
            self.flash_border("#a6e3a1", then_hide=True)
        else:
            self.flash_border("#f38ba8", then_hide=False)
```

- [ ] **Step 3: Verify import still works**

Run: `python -c "import blip; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add blip.py
git commit -m "feat: green/red border flash on save success/failure"
```

---

### Task 7: Show/Hide State Tests

**Files:**
- Modify: `test_blip.py`

- [ ] **Step 1: Add show/hide tests**

Add to `test_blip.py`:

```python
def test_show_hide_state():
    """show_window and hide_window toggle is_visible correctly."""
    import blip as blip_mod

    root = tk.Tk()
    root.withdraw()
    app = blip_mod.Blip(root)

    assert app.is_visible is False

    app.show_window()
    assert app.is_visible is True

    app.hide_window()
    assert app.is_visible is False

    root.destroy()
```

- [ ] **Step 2: Run tests**

Run: `pytest test_blip.py::test_show_hide_state -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add test_blip.py
git commit -m "test: add show/hide state tests"
```

---

### Task 8: System Tray Icon

**Files:**
- Modify: `blip.py` (add tray icon creation, update `poll_queue()` and `main()`)

- [ ] **Step 1: Add tray icon imports**

Add these imports near the top of `blip.py` (after the existing imports):

```python
import os
import subprocess
```

- [ ] **Step 2: Add create_tray_icon() function**

Add this function after `configure_dpi()`, before `class Blip`:

```python
def create_tray_icon(app_queue: queue.Queue) -> None:
    """Create and run a system tray icon on a daemon thread."""
    try:
        import pystray
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        logger.warning("pystray or Pillow not installed — skipping tray icon")
        return

    # Render a ⚡ icon as a 64×64 image
    img = Image.new("RGBA", (64, 64), (30, 30, 46, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial", 40)
    except OSError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), "⚡", font=font)
    x = (64 - (bbox[2] - bbox[0])) // 2 - bbox[0]
    y = (64 - (bbox[3] - bbox[1])) // 2 - bbox[1]
    draw.text((x, y), "⚡", fill=(205, 214, 244, 255), font=font)

    def open_notes():
        path = str(OUTPUT_FILE)
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)

    def quit_app(icon):
        icon.stop()
        app_queue.put("QUIT")

    menu = pystray.Menu(
        pystray.MenuItem("Blip ⚡", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Open blip.md", lambda: open_notes()),
        pystray.MenuItem("Quit", quit_app),
    )

    icon = pystray.Icon("blip", img, "Blip", menu)

    import threading
    thread = threading.Thread(target=icon.run, daemon=True)
    thread.start()
```

- [ ] **Step 3: Update poll_queue() to handle QUIT**

Replace the `poll_queue` method in class `Blip`. Use `root.quit()` (not `root.destroy()`) which exits `mainloop()` cleanly, letting `main()`'s `finally` block handle cleanup. Move the re-schedule out of `finally` to avoid calling `root.after()` on a shutting-down widget:

```python
    def poll_queue(self):
        """Check the queue for messages from the pynput/tray threads."""
        try:
            while True:
                msg = self.queue.get_nowait()
                if msg == "SHOW":
                    self.show_window()
                elif msg == "QUIT":
                    self.root.quit()
                    return
        except queue.Empty:
            pass
        self.root.after(100, self.poll_queue)
```

- [ ] **Step 4: Update main() with tray icon and pynput error handling**

In `main()`, add the tray icon call after creating the `Blip` app instance, and wrap the hotkey listener setup in try/except per the spec:

```python
def main():
    configure_dpi()
    print(f"Blip is running. ({HOTKEY} to capture · Ctrl+C to quit)")
    print(f"Notes → {OUTPUT_FILE}")

    root = tk.Tk()
    app = Blip(root)

    create_tray_icon(app.queue)

    def on_hotkey():
        app.queue.put("SHOW")

    try:
        listener = keyboard.GlobalHotKeys({HOTKEY: on_hotkey})
        listener.start()
    except Exception:
        logger.error("Failed to register global hotkey %s", HOTKEY, exc_info=True)
        print(f"ERROR: Could not register hotkey {HOTKEY}. See ~/blip.log for details.")
        listener = None

    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\nBlip stopped.")
    finally:
        if listener is not None:
            listener.stop()
```

- [ ] **Step 5: Verify the app starts without errors**

Run: `python -c "import blip; print('OK')"`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add blip.py
git commit -m "feat: system tray icon with pystray"
```

---

### Task 9: Run Full Test Suite

- [ ] **Step 1: Run all tests**

Run: `pytest test_blip.py -v`
Expected: All tests PASS.

- [ ] **Step 2: Verify manual smoke test**

Run: `python blip.py`
Expected:
- Console prints "Blip is running."
- Tray icon appears in system tray
- Ctrl+Shift+Space opens the capture window
- Typing + Enter → green flash → window hides
- Right-click tray icon → "Open blip.md" opens the file, "Quit" exits

- [ ] **Step 3: Final commit if any cleanup needed**

```bash
git add -A
git commit -m "chore: final Phase 1 cleanup"
```
