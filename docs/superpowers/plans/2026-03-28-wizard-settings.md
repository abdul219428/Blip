# Phase 11: First-Run Wizard & Settings Window — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a graphical first-run wizard, settings window, and "What's New" dialog so users can configure CogStash without editing JSON.

**Architecture:** New `settings.py` module contains all three UI classes (WizardWindow, SettingsWindow, WhatsNewDialog). `app.py` gains two new config fields (`launch_at_startup`, `last_seen_version`), a `save_config()` helper, a tray menu "Settings" item, and startup flow logic to detect first-run vs version-upgrade. Settings.py imports from app.py at module level; app.py lazy-imports settings.py.

**Tech Stack:** tkinter (Toplevel windows, Frame-based pages/tabs), existing THEMES/WINDOW_SIZES dicts, pystray menu update

**Spec:** `docs/superpowers/specs/2026-03-28-wizard-settings-design.md`

---

### Task 1: Config Additions — New Fields + save_config Helper

**Files:**
- Modify: `src/cogstash/app.py:62-145` (CogStashConfig, load_config)
- Test: `tests/test_app.py`

- [ ] **Step 1: Write failing tests for new config fields**

Add to `tests/test_app.py`:

```python
def test_config_new_fields_defaults(tmp_path):
    """Fresh config has launch_at_startup=False and last_seen_version=''."""
    from cogstash.app import load_config
    config = load_config(tmp_path / ".cogstash.json")
    assert config.launch_at_startup is False
    assert config.last_seen_version == ""


def test_config_new_fields_roundtrip(tmp_path):
    """New fields survive write-read cycle."""
    import json
    config_path = tmp_path / ".cogstash.json"
    data = {"launch_at_startup": True, "last_seen_version": "0.1.0", "theme": "dracula"}
    config_path.write_text(json.dumps(data), encoding="utf-8")
    from cogstash.app import load_config
    config = load_config(config_path)
    assert config.launch_at_startup is True
    assert config.last_seen_version == "0.1.0"
    assert config.theme == "dracula"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_app.py::test_config_new_fields_defaults tests/test_app.py::test_config_new_fields_roundtrip -v`
Expected: FAIL (CogStashConfig has no `launch_at_startup` or `last_seen_version`)

- [ ] **Step 3: Add new fields to CogStashConfig**

In `src/cogstash/app.py`, add to the `CogStashConfig` dataclass (after `tags` field):

```python
@dataclass
class CogStashConfig:
    hotkey: str = "<ctrl>+<shift>+<space>"
    output_file: Path | None = None
    log_file: Path | None = None
    theme: str = "tokyo-night"
    window_size: str = "default"
    tags: dict[str, dict[str, str]] | None = None
    launch_at_startup: bool = False
    last_seen_version: str = ""
```

- [ ] **Step 4: Update load_config to handle new fields**

In `load_config()`, add new fields to the `defaults` dict:

```python
defaults = {
    "hotkey": "<ctrl>+<shift>+<space>",
    "output_file": str(Path.home() / "cogstash.md"),
    "log_file": str(Path.home() / "cogstash.log"),
    "theme": "tokyo-night",
    "window_size": "default",
    "launch_at_startup": False,
    "last_seen_version": "",
}
```

And update the return statement to include the new fields:

```python
return CogStashConfig(
    hotkey=merged["hotkey"],
    output_file=output_file,
    log_file=log_file,
    theme=merged["theme"],
    window_size=merged["window_size"],
    tags=tags,
    launch_at_startup=bool(merged.get("launch_at_startup", False)),
    last_seen_version=str(merged.get("last_seen_version", "")),
)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_app.py::test_config_new_fields_defaults tests/test_app.py::test_config_new_fields_roundtrip -v`
Expected: PASS

- [ ] **Step 6: Write failing test for save_config**

Add to `tests/test_app.py`:

```python
def test_save_config(tmp_path):
    """save_config writes config to JSON file."""
    import json
    from cogstash.app import CogStashConfig, save_config
    config = CogStashConfig(theme="dracula", window_size="wide", last_seen_version="0.2.0")
    config_path = tmp_path / ".cogstash.json"
    save_config(config, config_path)
    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert data["theme"] == "dracula"
    assert data["window_size"] == "wide"
    assert data["last_seen_version"] == "0.2.0"
    assert data["launch_at_startup"] is False
```

- [ ] **Step 7: Run test to verify it fails**

Run: `uv run pytest tests/test_app.py::test_save_config -v`
Expected: FAIL (save_config doesn't exist)

- [ ] **Step 8: Implement save_config**

Add to `src/cogstash/app.py` after `load_config()`:

```python
def save_config(config: CogStashConfig, config_path: Path) -> None:
    """Write config to JSON file."""
    data: dict[str, object] = {
        "hotkey": config.hotkey,
        "output_file": str(config.output_file),
        "log_file": str(config.log_file),
        "theme": config.theme,
        "window_size": config.window_size,
        "launch_at_startup": config.launch_at_startup,
        "last_seen_version": config.last_seen_version,
    }
    if config.tags:
        data["tags"] = config.tags
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        logger.error("Failed to save config to %s", config_path, exc_info=True)
```

- [ ] **Step 9: Run test to verify it passes**

Run: `uv run pytest tests/test_app.py::test_save_config -v`
Expected: PASS

- [ ] **Step 10: Run full test suite + lint**

Run: `uv run pytest tests/ -v && uv run ruff check src/ tests/`
Expected: All tests pass, no lint errors.

- [ ] **Step 11: Commit**

```bash
git add src/cogstash/app.py tests/test_app.py
git commit -m "feat: add launch_at_startup, last_seen_version config fields and save_config helper"
```

---

### Task 2: Settings Module Skeleton + Tray Menu Integration

**Files:**
- Create: `src/cogstash/settings.py`
- Modify: `src/cogstash/app.py:226-290` (create_tray_icon), `src/cogstash/app.py:512-526` (poll_queue), `src/cogstash/app.py:528-533` (add _open_settings)
- Test: `tests/test_settings.py`

- [ ] **Step 1: Write failing tests for settings integration**

Create `tests/test_settings.py`:

```python
"""Tests for the settings module."""

from __future__ import annotations

import queue

import pytest

from conftest import needs_display


@needs_display
def test_settings_queue_message(tk_root):
    """SETTINGS message in queue triggers _open_settings."""
    from cogstash.app import CogStashConfig, CogStash

    config = CogStashConfig()
    app = CogStash(tk_root, config)
    app.queue.put("SETTINGS")
    # Process one round of poll_queue
    opened = []
    app._open_settings = lambda: opened.append(True)
    app.poll_queue()
    assert len(opened) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_settings.py::test_settings_queue_message -v`
Expected: FAIL (CogStash has no `_open_settings` method, no "SETTINGS" queue handling)

- [ ] **Step 3: Create settings.py skeleton**

Create `src/cogstash/settings.py`:

```python
"""Settings UI — wizard, settings window, and What's New dialog."""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path

from cogstash.app import (
    CogStashConfig,
    THEMES,
    WINDOW_SIZES,
    DEFAULT_SMART_TAGS,
    platform_font,
    merge_tags,
    save_config,
)


class SettingsWindow:
    """Tab-based settings window accessible from the tray menu."""

    def __init__(self, parent: tk.Tk, config: CogStashConfig, config_path: Path):
        self.parent = parent
        self.config = config
        self.config_path = config_path
        self.win = tk.Toplevel(parent)
        self.win.title("CogStash Settings")
        self.win.geometry("500x450")
        self.win.resizable(False, False)
        self.theme = THEMES[config.theme]
        self.win.configure(bg=self.theme["bg"])
        self.win.transient(parent)
        self.win.focus_force()


class WizardWindow:
    """First-run wizard shown when no config exists."""

    def __init__(self, parent: tk.Tk, config: CogStashConfig, config_path: Path):
        self.parent = parent
        self.config = config
        self.config_path = config_path
        self.win = tk.Toplevel(parent)
        self.win.title("Welcome to CogStash")
        self.win.geometry("520x440")
        self.win.resizable(False, False)
        self.theme = THEMES[config.theme]
        self.win.configure(bg=self.theme["bg"])
        self.win.transient(parent)
        self.win.grab_set()
        self.win.focus_force()


class WhatsNewDialog:
    """Dialog shown once per version upgrade."""

    def __init__(self, parent: tk.Tk, config: CogStashConfig, config_path: Path, version: str):
        self.parent = parent
        self.config = config
        self.config_path = config_path
        self.version = version
        self.win = tk.Toplevel(parent)
        self.win.title("What's New in CogStash")
        self.win.geometry("400x350")
        self.win.resizable(False, False)
        self.theme = THEMES[config.theme]
        self.win.configure(bg=self.theme["bg"])
        self.win.transient(parent)
        self.win.focus_force()
```

- [ ] **Step 4: Add SETTINGS handler to poll_queue and _open_settings to CogStash**

In `src/cogstash/app.py`, modify `poll_queue()`:

```python
def poll_queue(self):
    """Check the queue for messages from the pynput/tray threads."""
    try:
        while True:
            msg = self.queue.get_nowait()
            if msg == "SHOW":
                self.show_window()
            elif msg == "BROWSE":
                self._open_browse()
            elif msg == "SETTINGS":
                self._open_settings()
            elif msg == "QUIT":
                self.root.quit()
                return
    except queue.Empty:
        pass
    self.root.after(100, self.poll_queue)
```

Add `_open_settings()` method after `_open_browse()`:

```python
def _open_settings(self):
    """Open the Settings window (singleton — reuse if already open)."""
    if hasattr(self, "_settings_win") and self._settings_win and self._settings_win.win.winfo_exists():
        self._settings_win.win.lift()
        self._settings_win.win.focus_force()
        return
    from cogstash.settings import SettingsWindow
    self._settings_win = SettingsWindow(self.root, self.config, Path.home() / ".cogstash.json")
```

- [ ] **Step 5: Add "Settings" to tray menu**

In `src/cogstash/app.py`, modify `create_tray_icon()`. Add `open_settings` function and update the menu:

```python
def open_settings():
    app_queue.put("SETTINGS")

menu = pystray.Menu(
    pystray.MenuItem("CogStash ⚡", None, enabled=False),
    pystray.Menu.SEPARATOR,
    pystray.MenuItem(f"Open {config.output_file.name}", lambda: open_notes()),
    pystray.MenuItem("Browse Notes", lambda: browse_notes()),
    pystray.MenuItem("Settings", lambda: open_settings()),
    pystray.Menu.SEPARATOR,
    pystray.MenuItem("Quit", quit_app),
)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_settings.py::test_settings_queue_message -v`
Expected: PASS

- [ ] **Step 7: Run full test suite + lint**

Run: `uv run pytest tests/ -v && uv run ruff check src/ tests/`
Expected: All tests pass, no lint errors.

- [ ] **Step 8: Commit**

```bash
git add src/cogstash/settings.py tests/test_settings.py src/cogstash/app.py
git commit -m "feat: add settings module skeleton and tray menu integration"
```

---

### Task 3: Settings Window — Tab Bar + General Tab

**Files:**
- Modify: `src/cogstash/settings.py` (SettingsWindow class)
- Test: `tests/test_settings.py`

- [ ] **Step 1: Write failing test for settings window tabs**

Add to `tests/test_settings.py`:

```python
@needs_display
def test_settings_window_has_tabs(tk_root):
    """Settings window creates 4 tabs."""
    from cogstash.app import CogStashConfig
    from cogstash.settings import SettingsWindow
    config = CogStashConfig()
    sw = SettingsWindow(tk_root, config, Path("/tmp/test.json"))
    # Just verify it doesn't crash and has tab buttons
    assert hasattr(sw, "tab_buttons")
    assert len(sw.tab_buttons) == 4
    sw.win.destroy()


@needs_display
def test_settings_general_tab_widgets(tk_root):
    """General tab has hotkey label, notes file entry, and launch checkbox."""
    from cogstash.app import CogStashConfig
    from cogstash.settings import SettingsWindow
    from pathlib import Path
    config = CogStashConfig()
    sw = SettingsWindow(tk_root, config, Path("/tmp/test.json"))
    assert hasattr(sw, "notes_file_var")
    assert hasattr(sw, "launch_var")
    sw.win.destroy()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_settings.py::test_settings_window_has_tabs tests/test_settings.py::test_settings_general_tab_widgets -v`
Expected: FAIL

- [ ] **Step 3: Implement tab bar and General tab**

Replace the `SettingsWindow.__init__` in `src/cogstash/settings.py` with full tab bar implementation:

```python
class SettingsWindow:
    """Tab-based settings window accessible from the tray menu."""

    TAB_NAMES = ["General", "Appearance", "Tags", "About"]

    def __init__(self, parent: tk.Tk, config: CogStashConfig, config_path: Path):
        self.parent = parent
        self.config = config
        self.config_path = config_path
        self.win = tk.Toplevel(parent)
        self.win.title("CogStash Settings")
        self.win.geometry("500x450")
        self.win.resizable(False, False)
        self.theme = THEMES[config.theme]
        self.win.configure(bg=self.theme["bg"])
        self.win.transient(parent)
        self.win.focus_force()

        self._build_tab_bar()
        self.content_frame = tk.Frame(self.win, bg=self.theme["bg"])
        self.content_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self._build_general_tab()
        self._build_appearance_tab()
        self._build_tags_tab()
        self._build_about_tab()

        self._show_tab(0)

    def _build_tab_bar(self):
        """Create the tab button bar at the top."""
        t = self.theme
        bar = tk.Frame(self.win, bg=t["entry_bg"])
        bar.pack(fill="x", padx=16, pady=(16, 8))

        self.tab_buttons = []
        self.tab_frames = []
        self._active_tab = 0

        for i, name in enumerate(self.TAB_NAMES):
            btn = tk.Label(
                bar, text=name, bg=t["entry_bg"], fg=t["muted"],
                font=(platform_font(), 10), padx=16, pady=8, cursor="hand2",
            )
            btn.pack(side="left")
            btn.bind("<Button-1>", lambda e, idx=i: self._show_tab(idx))
            self.tab_buttons.append(btn)

    def _show_tab(self, idx: int):
        """Switch to tab at given index."""
        t = self.theme
        for i, btn in enumerate(self.tab_buttons):
            if i == idx:
                btn.configure(bg=t["bg"], fg=t["accent"])
            else:
                btn.configure(bg=t["entry_bg"], fg=t["muted"])
        for frame in self.tab_frames:
            frame.pack_forget()
        if self.tab_frames:
            self.tab_frames[idx].pack(fill="both", expand=True)
        self._active_tab = idx

    def _build_general_tab(self):
        """Build the General settings tab."""
        t = self.theme
        frame = tk.Frame(self.content_frame, bg=t["bg"])
        self.tab_frames.append(frame)

        font_label = (platform_font(), 10)
        font_value = (platform_font(), 10)

        # Section: Hotkey
        tk.Label(frame, text="Hotkey", bg=t["bg"], fg=t["fg"], font=(platform_font(), 11, "bold")).pack(anchor="w", pady=(8, 4))
        tk.Label(frame, text=self.config.hotkey, bg=t["entry_bg"], fg=t["fg"], font=font_value, padx=8, pady=4).pack(anchor="w", padx=(8, 0))
        tk.Label(frame, text="Edit in ~/.cogstash.json to change", bg=t["bg"], fg=t["muted"], font=(platform_font(), 8)).pack(anchor="w", padx=(8, 0), pady=(2, 0))

        # Section: Notes File
        tk.Label(frame, text="Notes File", bg=t["bg"], fg=t["fg"], font=(platform_font(), 11, "bold")).pack(anchor="w", pady=(16, 4))
        notes_frame = tk.Frame(frame, bg=t["bg"])
        notes_frame.pack(fill="x", padx=(8, 0))
        self.notes_file_var = tk.StringVar(value=str(self.config.output_file))
        tk.Entry(notes_frame, textvariable=self.notes_file_var, bg=t["entry_bg"], fg=t["fg"], insertbackground=t["fg"], relief="flat", font=font_value).pack(side="left", fill="x", expand=True, ipady=4)
        tk.Button(notes_frame, text="Browse", command=self._browse_notes_file, bg=t["entry_bg"], fg=t["fg"], relief="flat", font=(platform_font(), 9)).pack(side="left", padx=(8, 0))

        # Section: Launch at Startup
        tk.Label(frame, text="Startup", bg=t["bg"], fg=t["fg"], font=(platform_font(), 11, "bold")).pack(anchor="w", pady=(16, 4))
        self.launch_var = tk.BooleanVar(value=self.config.launch_at_startup)
        tk.Checkbutton(frame, text="Launch CogStash at system startup", variable=self.launch_var, bg=t["bg"], fg=t["fg"], selectcolor=t["entry_bg"], activebackground=t["bg"], activeforeground=t["fg"], font=font_label).pack(anchor="w", padx=(8, 0))

        # Save button
        tk.Button(frame, text="Save", command=self._save_general, bg=t["accent"], fg=t["bg"], relief="flat", font=(platform_font(), 10, "bold"), padx=24, pady=6, cursor="hand2").pack(anchor="e", pady=(24, 0))

    def _browse_notes_file(self):
        """Open file dialog to select notes file."""
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            parent=self.win,
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("Text", "*.txt"), ("All", "*.*")],
            title="Choose notes file location",
        )
        if path:
            self.notes_file_var.set(path)

    def _save_general(self):
        """Save General tab settings to config."""
        self.config.output_file = Path(self.notes_file_var.get()).expanduser()
        self.config.launch_at_startup = self.launch_var.get()
        save_config(self.config, self.config_path)
        self._flash_saved()

    def _flash_saved(self):
        """Briefly show a 'Saved' indicator."""
        lbl = tk.Label(self.win, text="✓ Saved", bg=self.theme["accent"], fg=self.theme["bg"], font=(platform_font(), 9))
        lbl.place(relx=0.5, rely=0.95, anchor="center")
        self.win.after(1500, lbl.destroy)

    def _build_appearance_tab(self):
        """Placeholder — implemented in Task 4."""
        frame = tk.Frame(self.content_frame, bg=self.theme["bg"])
        self.tab_frames.append(frame)

    def _build_tags_tab(self):
        """Placeholder — implemented in Task 5."""
        frame = tk.Frame(self.content_frame, bg=self.theme["bg"])
        self.tab_frames.append(frame)

    def _build_about_tab(self):
        """Placeholder — implemented in Task 6."""
        frame = tk.Frame(self.content_frame, bg=self.theme["bg"])
        self.tab_frames.append(frame)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_settings.py -v`
Expected: PASS

- [ ] **Step 5: Run full test suite + lint**

Run: `uv run pytest tests/ -v && uv run ruff check src/ tests/`
Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add src/cogstash/settings.py tests/test_settings.py
git commit -m "feat: implement settings window tab bar and General tab"
```

---

### Task 4: Settings Window — Appearance Tab (Theme + Window Size)

**Files:**
- Modify: `src/cogstash/settings.py` (SettingsWindow._build_appearance_tab)
- Test: `tests/test_settings.py`

- [ ] **Step 1: Write failing test for appearance tab**

Add to `tests/test_settings.py`:

```python
@needs_display
def test_settings_appearance_tab(tk_root):
    """Appearance tab has theme swatches and window size options."""
    from cogstash.app import CogStashConfig
    from cogstash.settings import SettingsWindow
    from pathlib import Path
    config = CogStashConfig()
    sw = SettingsWindow(tk_root, config, Path("/tmp/test.json"))
    assert hasattr(sw, "selected_theme")
    assert sw.selected_theme.get() == "tokyo-night"
    assert hasattr(sw, "selected_size")
    assert sw.selected_size.get() == "default"
    sw.win.destroy()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_settings.py::test_settings_appearance_tab -v`
Expected: FAIL

- [ ] **Step 3: Implement _build_appearance_tab**

Replace the placeholder `_build_appearance_tab` in `settings.py`:

```python
def _build_appearance_tab(self):
    """Build the Appearance settings tab with theme picker and window size."""
    t = self.theme
    frame = tk.Frame(self.content_frame, bg=t["bg"])
    self.tab_frames.append(frame)

    # Theme section
    tk.Label(frame, text="Theme", bg=t["bg"], fg=t["fg"], font=(platform_font(), 11, "bold")).pack(anchor="w", pady=(8, 8))
    self.selected_theme = tk.StringVar(value=self.config.theme)
    theme_grid = tk.Frame(frame, bg=t["bg"])
    theme_grid.pack(fill="x", padx=(8, 0))

    self._theme_swatches = {}
    for i, (name, colors) in enumerate(THEMES.items()):
        swatch = tk.Frame(theme_grid, bg=colors["bg"], highlightthickness=2,
                          highlightbackground=colors["accent"] if name == self.config.theme else colors["bg"],
                          cursor="hand2", width=80, height=60)
        swatch.grid(row=0, column=i, padx=4, pady=4)
        swatch.grid_propagate(False)
        tk.Label(swatch, text=name.replace("-", "\n"), bg=colors["bg"], fg=colors["fg"],
                 font=(platform_font(), 8)).place(relx=0.5, rely=0.35, anchor="center")
        # Color preview dots
        dot_frame = tk.Frame(swatch, bg=colors["bg"])
        dot_frame.place(relx=0.5, rely=0.75, anchor="center")
        for c in [colors["accent"], colors["fg"], colors["muted"]]:
            tk.Frame(dot_frame, bg=c, width=8, height=8).pack(side="left", padx=1)
        swatch.bind("<Button-1>", lambda e, n=name: self._select_theme(n))
        for child in swatch.winfo_children():
            child.bind("<Button-1>", lambda e, n=name: self._select_theme(n))
        for child in dot_frame.winfo_children():
            child.bind("<Button-1>", lambda e, n=name: self._select_theme(n))
        self._theme_swatches[name] = swatch

    # Window size section
    tk.Label(frame, text="Window Size", bg=t["bg"], fg=t["fg"], font=(platform_font(), 11, "bold")).pack(anchor="w", pady=(20, 8))
    self.selected_size = tk.StringVar(value=self.config.window_size)
    size_frame = tk.Frame(frame, bg=t["bg"])
    size_frame.pack(fill="x", padx=(8, 0))
    for name, props in WINDOW_SIZES.items():
        tk.Radiobutton(
            size_frame, text=f"{name.capitalize()} ({props['width']}px)",
            variable=self.selected_size, value=name,
            bg=t["bg"], fg=t["fg"], selectcolor=t["entry_bg"],
            activebackground=t["bg"], activeforeground=t["fg"],
            font=(platform_font(), 10),
        ).pack(anchor="w", pady=2)

    # Save button
    tk.Button(frame, text="Save", command=self._save_appearance, bg=t["accent"], fg=t["bg"], relief="flat", font=(platform_font(), 10, "bold"), padx=24, pady=6, cursor="hand2").pack(anchor="e", pady=(24, 0))

def _select_theme(self, name: str):
    """Handle theme swatch click."""
    self.selected_theme.set(name)
    for tname, swatch in self._theme_swatches.items():
        colors = THEMES[tname]
        hl = colors["accent"] if tname == name else colors["bg"]
        swatch.configure(highlightbackground=hl)

def _save_appearance(self):
    """Save Appearance tab settings."""
    self.config.theme = self.selected_theme.get()
    self.config.window_size = self.selected_size.get()
    save_config(self.config, self.config_path)
    self._flash_saved()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_settings.py -v`
Expected: PASS

- [ ] **Step 5: Run full test suite + lint**

Run: `uv run pytest tests/ -v && uv run ruff check src/ tests/`
Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add src/cogstash/settings.py tests/test_settings.py
git commit -m "feat: implement settings Appearance tab with theme picker and window size"
```

---

### Task 5: Settings Window — Tags Tab + About Tab

**Files:**
- Modify: `src/cogstash/settings.py` (SettingsWindow._build_tags_tab, _build_about_tab)
- Test: `tests/test_settings.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_settings.py`:

```python
@needs_display
def test_settings_tags_tab(tk_root):
    """Tags tab shows built-in tags."""
    from cogstash.app import CogStashConfig
    from cogstash.settings import SettingsWindow
    from pathlib import Path
    config = CogStashConfig()
    sw = SettingsWindow(tk_root, config, Path("/tmp/test.json"))
    sw._show_tab(2)  # Tags tab
    assert hasattr(sw, "tag_list_frame")
    sw.win.destroy()


@needs_display
def test_settings_about_tab(tk_root):
    """About tab shows version info."""
    from cogstash.app import CogStashConfig
    from cogstash.settings import SettingsWindow
    from pathlib import Path
    config = CogStashConfig()
    sw = SettingsWindow(tk_root, config, Path("/tmp/test.json"))
    sw._show_tab(3)  # About tab
    assert hasattr(sw, "version_label")
    sw.win.destroy()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_settings.py::test_settings_tags_tab tests/test_settings.py::test_settings_about_tab -v`
Expected: FAIL

- [ ] **Step 3: Implement _build_tags_tab**

Replace the placeholder `_build_tags_tab` in `settings.py`:

```python
def _build_tags_tab(self):
    """Build the Tags management tab."""
    t = self.theme
    frame = tk.Frame(self.content_frame, bg=t["bg"])
    self.tab_frames.append(frame)

    tk.Label(frame, text="Tags", bg=t["bg"], fg=t["fg"], font=(platform_font(), 11, "bold")).pack(anchor="w", pady=(8, 8))

    # Scrollable tag list
    self.tag_list_frame = tk.Frame(frame, bg=t["bg"])
    self.tag_list_frame.pack(fill="both", expand=True, padx=(8, 0))

    self._render_tags()

    # Add tag button
    add_frame = tk.Frame(frame, bg=t["bg"])
    add_frame.pack(fill="x", pady=(8, 0))
    tk.Button(add_frame, text="+ Add Custom Tag", command=self._show_add_tag_form, bg=t["entry_bg"], fg=t["fg"], relief="flat", font=(platform_font(), 9), cursor="hand2").pack(anchor="w")

    # Add tag form (hidden initially)
    self._add_tag_frame = tk.Frame(frame, bg=t["entry_bg"])
    self._tag_name_var = tk.StringVar()
    self._tag_emoji_var = tk.StringVar()
    self._tag_color_var = tk.StringVar(value="#ffffff")

    tk.Label(self._add_tag_frame, text="Name:", bg=t["entry_bg"], fg=t["fg"], font=(platform_font(), 9)).grid(row=0, column=0, padx=4, pady=2, sticky="w")
    tk.Entry(self._add_tag_frame, textvariable=self._tag_name_var, bg=t["bg"], fg=t["fg"], insertbackground=t["fg"], relief="flat", font=(platform_font(), 9), width=12).grid(row=0, column=1, padx=4, pady=2)
    tk.Label(self._add_tag_frame, text="Emoji:", bg=t["entry_bg"], fg=t["fg"], font=(platform_font(), 9)).grid(row=0, column=2, padx=4, pady=2, sticky="w")
    tk.Entry(self._add_tag_frame, textvariable=self._tag_emoji_var, bg=t["bg"], fg=t["fg"], insertbackground=t["fg"], relief="flat", font=(platform_font(), 9), width=4).grid(row=0, column=3, padx=4, pady=2)
    tk.Label(self._add_tag_frame, text="Color:", bg=t["entry_bg"], fg=t["fg"], font=(platform_font(), 9)).grid(row=0, column=4, padx=4, pady=2, sticky="w")
    tk.Entry(self._add_tag_frame, textvariable=self._tag_color_var, bg=t["bg"], fg=t["fg"], insertbackground=t["fg"], relief="flat", font=(platform_font(), 9), width=8).grid(row=0, column=5, padx=4, pady=2)
    tk.Button(self._add_tag_frame, text="Add", command=self._add_tag, bg=t["accent"], fg=t["bg"], relief="flat", font=(platform_font(), 9)).grid(row=0, column=6, padx=8, pady=2)

    # Save button
    tk.Button(frame, text="Save", command=self._save_tags, bg=t["accent"], fg=t["bg"], relief="flat", font=(platform_font(), 10, "bold"), padx=24, pady=6, cursor="hand2").pack(anchor="e", pady=(8, 0))

def _render_tags(self):
    """Render the tag list in the tags tab."""
    for child in self.tag_list_frame.winfo_children():
        child.destroy()
    t = self.theme
    smart_tags, tag_colors = merge_tags(self.config)

    for name, emoji in DEFAULT_SMART_TAGS.items():
        row = tk.Frame(self.tag_list_frame, bg=t["bg"])
        row.pack(fill="x", pady=2)
        tk.Label(row, text=f"  {emoji}  #{name}", bg=t["bg"], fg=t["fg"], font=(platform_font(), 10), anchor="w").pack(side="left")
        tk.Label(row, text="Built-in", bg=t["entry_bg"], fg=t["muted"], font=(platform_font(), 8), padx=6, pady=1).pack(side="right")

    if self.config.tags:
        for name, props in self.config.tags.items():
            row = tk.Frame(self.tag_list_frame, bg=t["bg"])
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"  {props['emoji']}  #{name}", bg=t["bg"], fg=t["fg"], font=(platform_font(), 10), anchor="w").pack(side="left")
            color_swatch = tk.Frame(row, bg=props["color"], width=14, height=14)
            color_swatch.pack(side="right", padx=(0, 4))
            color_swatch.pack_propagate(False)
            tk.Button(row, text="✕", command=lambda n=name: self._remove_tag(n), bg=t["bg"], fg=t["error"], relief="flat", font=(platform_font(), 9), cursor="hand2").pack(side="right")

def _show_add_tag_form(self):
    """Show the add-tag form."""
    self._add_tag_frame.pack(fill="x", padx=(8, 0), pady=(4, 0))

def _add_tag(self):
    """Add a new custom tag from the form fields."""
    import re
    name = self._tag_name_var.get().strip().lower()
    emoji = self._tag_emoji_var.get().strip()
    color = self._tag_color_var.get().strip()
    if not name or not emoji or not re.match(r"^#[0-9a-fA-F]{6}$", color):
        return
    if self.config.tags is None:
        self.config.tags = {}
    self.config.tags[name] = {"emoji": emoji, "color": color}
    self._tag_name_var.set("")
    self._tag_emoji_var.set("")
    self._tag_color_var.set("#ffffff")
    self._add_tag_frame.pack_forget()
    self._render_tags()

def _remove_tag(self, name: str):
    """Remove a custom tag."""
    if self.config.tags and name in self.config.tags:
        del self.config.tags[name]
        if not self.config.tags:
            self.config.tags = None
        self._render_tags()

def _save_tags(self):
    """Save Tags tab settings."""
    save_config(self.config, self.config_path)
    self._flash_saved()
```

- [ ] **Step 4: Implement _build_about_tab**

Replace the placeholder `_build_about_tab` in `settings.py`:

```python
def _build_about_tab(self):
    """Build the About tab with version and links."""
    t = self.theme
    frame = tk.Frame(self.content_frame, bg=t["bg"])
    self.tab_frames.append(frame)

    # Version
    from cogstash import __version__
    self.version_label = tk.Label(frame, text=f"CogStash v{__version__}", bg=t["bg"], fg=t["fg"], font=(platform_font(), 14, "bold"))
    self.version_label.pack(pady=(24, 4))
    tk.Label(frame, text="A global hotkey brain dump — press, type, gone.", bg=t["bg"], fg=t["muted"], font=(platform_font(), 10)).pack(pady=(0, 24))

    # Links
    links = [
        ("GitHub Repository", "https://github.com/abdul219428/CogStash"),
        ("Open Notes File", str(self.config.output_file)),
        ("Open Config File", str(self.config_path)),
    ]
    for text, target in links:
        lbl = tk.Label(frame, text=text, bg=t["bg"], fg=t["accent"], font=(platform_font(), 10), cursor="hand2")
        lbl.pack(pady=2)
        lbl.bind("<Button-1>", lambda e, t=target: self._open_link(t))

    # Credits
    tk.Label(frame, text="Built with Python, tkinter, pynput, pystray, Pillow", bg=t["bg"], fg=t["muted"], font=(platform_font(), 9)).pack(pady=(24, 0))

def _open_link(self, target: str):
    """Open a URL or file path."""
    import os
    import subprocess
    if target.startswith("http"):
        import webbrowser
        webbrowser.open(target)
    elif sys.platform == "win32":
        os.startfile(target)
    elif sys.platform == "darwin":
        subprocess.run(["open", target], check=False)
    else:
        subprocess.run(["xdg-open", target], check=False)
```

Note: Add `import sys` to the top of settings.py imports if not already present.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_settings.py -v`
Expected: PASS

- [ ] **Step 6: Run full test suite + lint**

Run: `uv run pytest tests/ -v && uv run ruff check src/ tests/`
Expected: All pass.

- [ ] **Step 7: Commit**

```bash
git add src/cogstash/settings.py tests/test_settings.py
git commit -m "feat: implement settings Tags tab and About tab"
```

---

### Task 6: First-Run Wizard

**Files:**
- Modify: `src/cogstash/settings.py` (WizardWindow class)
- Modify: `src/cogstash/app.py:582-618` (main function — startup flow)
- Test: `tests/test_settings.py`

- [ ] **Step 1: Write failing tests for wizard**

Add to `tests/test_settings.py`:

```python
def test_first_run_detection():
    """last_seen_version=='' means first run."""
    from cogstash.app import CogStashConfig
    config = CogStashConfig()
    assert config.last_seen_version == ""
    # Non-empty means not first run
    config2 = CogStashConfig(last_seen_version="0.1.0")
    assert config2.last_seen_version == "0.1.0"


@needs_display
def test_wizard_saves_config(tk_root, tmp_path):
    """Wizard writes valid config with all fields when completed."""
    import json
    from cogstash.app import CogStashConfig
    from cogstash.settings import WizardWindow
    config = CogStashConfig()
    config_path = tmp_path / ".cogstash.json"
    wiz = WizardWindow(tk_root, config, config_path)
    # Simulate completing the wizard
    wiz._finish()
    assert config_path.exists()
    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert "theme" in data
    assert "last_seen_version" in data
    assert data["last_seen_version"] != ""
    wiz.win.destroy()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_settings.py::test_first_run_detection tests/test_settings.py::test_wizard_saves_config -v`
Expected: first_run_detection may PASS (field already exists), wizard_saves_config FAIL (WizardWindow._finish doesn't exist)

- [ ] **Step 3: Implement WizardWindow with all 5 pages**

Replace the `WizardWindow` class in `settings.py`:

```python
class WizardWindow:
    """First-run wizard shown when no config exists."""

    def __init__(self, parent: tk.Tk, config: CogStashConfig, config_path: Path):
        self.parent = parent
        self.config = config
        self.config_path = config_path
        self.current_page = 0
        self.theme = THEMES[config.theme]

        self.win = tk.Toplevel(parent)
        self.win.title("Welcome to CogStash")
        self.win.geometry("520x440")
        self.win.resizable(False, False)
        self.win.configure(bg=self.theme["bg"])
        self.win.transient(parent)
        self.win.grab_set()
        self.win.focus_force()

        # Content area
        self.content = tk.Frame(self.win, bg=self.theme["bg"])
        self.content.pack(fill="both", expand=True, padx=24, pady=(16, 0))

        # Footer with dots and buttons
        self.footer = tk.Frame(self.win, bg=self.theme["bg"])
        self.footer.pack(fill="x", padx=24, pady=16)

        self.dots_frame = tk.Frame(self.footer, bg=self.theme["bg"])
        self.dots_frame.pack(side="left")
        self._dots = []
        for i in range(5):
            d = tk.Frame(self.dots_frame, width=8, height=8, bg=self.theme["muted"])
            d.pack(side="left", padx=3)
            d.pack_propagate(False)
            self._dots.append(d)

        self.btn_frame = tk.Frame(self.footer, bg=self.theme["bg"])
        self.btn_frame.pack(side="right")

        # Vars for config
        self.notes_file_var = tk.StringVar(value=str(config.output_file))
        self.selected_theme = tk.StringVar(value=config.theme)
        self.selected_size = tk.StringVar(value=config.window_size)

        self._pages = [
            self._page_welcome,
            self._page_theme,
            self._page_tags,
            self._page_tour,
            self._page_done,
        ]
        self._show_page(0)

    def _show_page(self, idx: int):
        """Display the page at given index."""
        self.current_page = idx
        # Clear content
        for child in self.content.winfo_children():
            child.destroy()
        for child in self.btn_frame.winfo_children():
            child.destroy()
        # Update dots
        for i, d in enumerate(self._dots):
            d.configure(bg=self.theme["accent"] if i == idx else self.theme["muted"])
        # Build page
        self._pages[idx]()
        # Buttons
        t = self.theme
        if idx > 0:
            tk.Button(self.btn_frame, text="← Back", command=lambda: self._show_page(idx - 1),
                      bg=t["entry_bg"], fg=t["fg"], relief="flat", font=(platform_font(), 10),
                      padx=12, pady=4, cursor="hand2").pack(side="left", padx=(0, 8))
        if idx < 4:
            tk.Button(self.btn_frame, text="Next →", command=lambda: self._show_page(idx + 1),
                      bg=t["accent"], fg=t["bg"], relief="flat", font=(platform_font(), 10, "bold"),
                      padx=12, pady=4, cursor="hand2").pack(side="left")
        else:
            tk.Button(self.btn_frame, text="Start Using CogStash", command=self._finish,
                      bg=t["accent"], fg=t["bg"], relief="flat", font=(platform_font(), 10, "bold"),
                      padx=16, pady=4, cursor="hand2").pack(side="left")

    def _page_welcome(self):
        """Page 1: Welcome + notes file."""
        t = self.theme
        tk.Label(self.content, text="⚡ Welcome to CogStash", bg=t["bg"], fg=t["fg"],
                 font=(platform_font(), 16, "bold")).pack(pady=(16, 4))
        tk.Label(self.content, text="Press a hotkey, type a thought, and it's saved.", bg=t["bg"],
                 fg=t["muted"], font=(platform_font(), 10)).pack(pady=(0, 24))
        tk.Label(self.content, text="Where should your notes be saved?", bg=t["bg"], fg=t["fg"],
                 font=(platform_font(), 11)).pack(anchor="w", pady=(0, 8))
        notes_frame = tk.Frame(self.content, bg=t["bg"])
        notes_frame.pack(fill="x")
        tk.Entry(notes_frame, textvariable=self.notes_file_var, bg=t["entry_bg"], fg=t["fg"],
                 insertbackground=t["fg"], relief="flat", font=(platform_font(), 10)).pack(
                     side="left", fill="x", expand=True, ipady=6)
        tk.Button(notes_frame, text="Browse", command=self._browse_notes, bg=t["entry_bg"],
                  fg=t["fg"], relief="flat", font=(platform_font(), 9)).pack(side="left", padx=(8, 0))
        tk.Label(self.content, text=f"Hotkey: {self.config.hotkey}", bg=t["bg"], fg=t["muted"],
                 font=(platform_font(), 10)).pack(anchor="w", pady=(16, 0))

    def _browse_notes(self):
        """File dialog for notes file."""
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            parent=self.win, defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("Text", "*.txt"), ("All", "*.*")],
            title="Choose notes file location",
        )
        if path:
            self.notes_file_var.set(path)

    def _page_theme(self):
        """Page 2: Theme + window size."""
        t = self.theme
        tk.Label(self.content, text="Choose Your Theme", bg=t["bg"], fg=t["fg"],
                 font=(platform_font(), 14, "bold")).pack(pady=(8, 12))
        theme_grid = tk.Frame(self.content, bg=t["bg"])
        theme_grid.pack()
        self._wiz_swatches = {}
        for i, (name, colors) in enumerate(THEMES.items()):
            swatch = tk.Frame(theme_grid, bg=colors["bg"], highlightthickness=2,
                              highlightbackground=colors["accent"] if name == self.selected_theme.get() else colors["bg"],
                              cursor="hand2", width=85, height=65)
            swatch.grid(row=0, column=i, padx=4, pady=4)
            swatch.grid_propagate(False)
            tk.Label(swatch, text=name.replace("-", "\n"), bg=colors["bg"], fg=colors["fg"],
                     font=(platform_font(), 8)).place(relx=0.5, rely=0.5, anchor="center")
            swatch.bind("<Button-1>", lambda e, n=name: self._wiz_select_theme(n))
            for child in swatch.winfo_children():
                child.bind("<Button-1>", lambda e, n=name: self._wiz_select_theme(n))
            self._wiz_swatches[name] = swatch

        tk.Label(self.content, text="Window Size", bg=t["bg"], fg=t["fg"],
                 font=(platform_font(), 11, "bold")).pack(anchor="w", pady=(20, 8))
        size_frame = tk.Frame(self.content, bg=t["bg"])
        size_frame.pack(fill="x")
        for name, props in WINDOW_SIZES.items():
            tk.Radiobutton(
                size_frame, text=f"{name.capitalize()} ({props['width']}px)",
                variable=self.selected_size, value=name,
                bg=t["bg"], fg=t["fg"], selectcolor=t["entry_bg"],
                activebackground=t["bg"], activeforeground=t["fg"],
                font=(platform_font(), 10),
            ).pack(anchor="w", pady=2)

    def _wiz_select_theme(self, name: str):
        """Handle theme selection in wizard."""
        self.selected_theme.set(name)
        for tname, swatch in self._wiz_swatches.items():
            colors = THEMES[tname]
            hl = colors["accent"] if tname == name else colors["bg"]
            swatch.configure(highlightbackground=hl)

    def _page_tags(self):
        """Page 3: Tags overview."""
        t = self.theme
        tk.Label(self.content, text="Your Tags", bg=t["bg"], fg=t["fg"],
                 font=(platform_font(), 14, "bold")).pack(pady=(8, 12))
        tk.Label(self.content, text="CogStash uses smart tags to organize your thoughts.", bg=t["bg"],
                 fg=t["muted"], font=(platform_font(), 10)).pack(pady=(0, 12))
        for name, emoji in DEFAULT_SMART_TAGS.items():
            row = tk.Frame(self.content, bg=t["entry_bg"], padx=12, pady=8)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=f"{emoji}  #{name}", bg=t["entry_bg"], fg=t["fg"],
                     font=(platform_font(), 11)).pack(side="left")
        tk.Label(self.content, text="You can add custom tags later in Settings.", bg=t["bg"],
                 fg=t["muted"], font=(platform_font(), 9)).pack(anchor="w", pady=(12, 0))

    def _page_tour(self):
        """Page 4: Quick tutorial."""
        t = self.theme
        tk.Label(self.content, text="Quick Tour", bg=t["bg"], fg=t["fg"],
                 font=(platform_font(), 14, "bold")).pack(pady=(8, 12))
        cards = [
            ("⚡", "Capture", f"Press {self.config.hotkey} anywhere.\nType your thought, press Enter."),
            ("📋", "Browse", "Right-click the tray icon → Browse Notes\nSearch, filter by tags, mark done."),
            ("💻", "CLI", "cogstash recent — last 10 notes\ncogstash search <query>\ncogstash tags"),
        ]
        for emoji, title, desc in cards:
            card = tk.Frame(self.content, bg=t["entry_bg"], padx=12, pady=10)
            card.pack(fill="x", pady=4)
            header = tk.Frame(card, bg=t["entry_bg"])
            header.pack(fill="x")
            tk.Label(header, text=f"{emoji}  {title}", bg=t["entry_bg"], fg=t["fg"],
                     font=(platform_font(), 11, "bold")).pack(side="left")
            tk.Label(card, text=desc, bg=t["entry_bg"], fg=t["muted"],
                     font=(platform_font(), 9), justify="left").pack(anchor="w", pady=(4, 0))

    def _page_done(self):
        """Page 5: Summary / done."""
        t = self.theme
        tk.Label(self.content, text="You're All Set! ⚡", bg=t["bg"], fg=t["fg"],
                 font=(platform_font(), 16, "bold")).pack(pady=(24, 8))
        tk.Label(self.content, text="CogStash will live in your system tray.", bg=t["bg"],
                 fg=t["muted"], font=(platform_font(), 10)).pack(pady=(0, 24))
        summary = tk.Frame(self.content, bg=t["entry_bg"], padx=16, pady=12)
        summary.pack(fill="x")
        items = [
            ("Notes", self.notes_file_var.get()),
            ("Theme", self.selected_theme.get()),
            ("Size", self.selected_size.get()),
            ("Hotkey", self.config.hotkey),
        ]
        for label, value in items:
            row = tk.Frame(summary, bg=t["entry_bg"])
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"{label}:", bg=t["entry_bg"], fg=t["muted"],
                     font=(platform_font(), 10), width=8, anchor="w").pack(side="left")
            tk.Label(row, text=value, bg=t["entry_bg"], fg=t["fg"],
                     font=(platform_font(), 10)).pack(side="left")

    def _finish(self):
        """Save config and close wizard."""
        from cogstash import __version__
        self.config.output_file = Path(self.notes_file_var.get()).expanduser()
        self.config.theme = self.selected_theme.get()
        self.config.window_size = self.selected_size.get()
        self.config.last_seen_version = __version__
        save_config(self.config, self.config_path)
        self.win.grab_release()
        self.win.destroy()
```

- [ ] **Step 4: Update app.py main() for wizard startup flow**

In `src/cogstash/app.py`, modify `main()` to detect first run and show wizard:

```python
def main():
    config_path = Path.home() / ".cogstash.json"
    config = load_config(config_path)

    # Reconfigure logger to use config's log_file
    for h in logger.handlers[:]:
        logger.removeHandler(h)
    _handler = logging.FileHandler(config.log_file, encoding="utf-8")
    _handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M"))
    logger.addHandler(_handler)

    configure_dpi()

    root = tk.Tk()

    # First-run wizard
    if config.last_seen_version == "":
        from cogstash.settings import WizardWindow
        wiz = WizardWindow(root, config, config_path)
        root.wait_window(wiz.win)
        # Reload config after wizard saves it
        config = load_config(config_path)
    else:
        # Check for version upgrade → What's New
        from cogstash import __version__
        if config.last_seen_version != __version__:
            from cogstash.settings import WhatsNewDialog
            WhatsNewDialog(root, config, config_path, __version__)
            config.last_seen_version = __version__
            save_config(config, config_path)

    print(f"CogStash is running. ({config.hotkey} to capture · Ctrl+C to quit)")
    print(f"Notes → {config.output_file}")

    app = CogStash(root, config)

    create_tray_icon(app.queue, config)

    def on_hotkey():
        app.queue.put("SHOW")

    try:
        listener = keyboard.GlobalHotKeys({config.hotkey: on_hotkey})
        listener.start()
    except Exception:
        logger.error("Failed to register global hotkey %s", config.hotkey, exc_info=True)
        print(f"ERROR: Could not register hotkey {config.hotkey}. See {config.log_file} for details.")
        listener = None

    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\nCogStash stopped.")
    finally:
        if listener is not None:
            listener.stop()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_settings.py -v`
Expected: PASS

- [ ] **Step 6: Run full test suite + lint**

Run: `uv run pytest tests/ -v && uv run ruff check src/ tests/`
Expected: All pass.

- [ ] **Step 7: Commit**

```bash
git add src/cogstash/settings.py src/cogstash/app.py tests/test_settings.py
git commit -m "feat: implement first-run wizard with 5-page onboarding flow"
```

---

### Task 7: What's New Dialog

**Files:**
- Modify: `src/cogstash/settings.py` (WhatsNewDialog class)
- Test: `tests/test_settings.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_settings.py`:

```python
def test_whats_new_detection():
    """Version mismatch triggers What's New (but not on first run)."""
    from cogstash.app import CogStashConfig
    from cogstash import __version__
    # First run — no What's New
    config_new = CogStashConfig(last_seen_version="")
    assert config_new.last_seen_version == ""  # wizard, not what's new
    # Version upgrade — show What's New
    config_old = CogStashConfig(last_seen_version="0.0.1")
    assert config_old.last_seen_version != __version__
    # Same version — no What's New
    config_current = CogStashConfig(last_seen_version=__version__)
    assert config_current.last_seen_version == __version__


@needs_display
def test_whats_new_dialog_creates(tk_root, tmp_path):
    """WhatsNewDialog opens without error."""
    from cogstash.app import CogStashConfig
    from cogstash.settings import WhatsNewDialog
    from cogstash import __version__
    config = CogStashConfig(last_seen_version="0.0.1")
    dialog = WhatsNewDialog(tk_root, config, tmp_path / ".cogstash.json", __version__)
    assert dialog.win.winfo_exists()
    dialog.win.destroy()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_settings.py::test_whats_new_detection tests/test_settings.py::test_whats_new_dialog_creates -v`
Expected: May partially fail (WhatsNewDialog is currently a skeleton)

- [ ] **Step 3: Implement WhatsNewDialog**

Replace the `WhatsNewDialog` class in `settings.py`:

```python
WHATS_NEW: dict[str, dict[str, list[tuple[str, str]]]] = {
    "0.2.0": {
        "title": "CogStash 0.2.0",
        "items": [
            ("new", "First-run wizard for easy setup"),
            ("new", "Settings window — configure from tray menu"),
            ("new", "What's New dialog on version upgrade"),
            ("improved", "Theme and window size live preview"),
            ("improved", "Custom tag management via GUI"),
        ],
    },
}

BADGE_COLORS = {
    "new": "#4ade80",       # green
    "improved": "#60a5fa",  # blue
    "fixed": "#fb923c",     # orange
}


class WhatsNewDialog:
    """Dialog shown once per version upgrade."""

    def __init__(self, parent: tk.Tk, config: CogStashConfig, config_path: Path, version: str):
        self.parent = parent
        self.config = config
        self.config_path = config_path
        self.version = version
        self.theme = THEMES[config.theme]
        t = self.theme

        self.win = tk.Toplevel(parent)
        self.win.title("What's New in CogStash")
        self.win.geometry("400x350")
        self.win.resizable(False, False)
        self.win.configure(bg=t["bg"])
        self.win.transient(parent)
        self.win.focus_force()

        tk.Label(self.win, text=f"What's New in CogStash", bg=t["bg"], fg=t["fg"],
                 font=(platform_font(), 14, "bold")).pack(pady=(20, 4))
        tk.Label(self.win, text=f"v{version}", bg=t["bg"], fg=t["muted"],
                 font=(platform_font(), 10)).pack(pady=(0, 16))

        # Find items for this version (or show generic message)
        items = WHATS_NEW.get(version, {}).get("items", [])
        if items:
            list_frame = tk.Frame(self.win, bg=t["bg"])
            list_frame.pack(fill="both", expand=True, padx=24)
            for badge_type, text in items:
                row = tk.Frame(list_frame, bg=t["bg"])
                row.pack(fill="x", pady=3)
                badge_color = BADGE_COLORS.get(badge_type, t["muted"])
                tk.Label(row, text=f" {badge_type.upper()} ", bg=badge_color, fg="#000000",
                         font=(platform_font(), 7, "bold"), padx=4, pady=1).pack(side="left", padx=(0, 8))
                tk.Label(row, text=text, bg=t["bg"], fg=t["fg"],
                         font=(platform_font(), 10)).pack(side="left")
        else:
            tk.Label(self.win, text="Thanks for updating!", bg=t["bg"], fg=t["muted"],
                     font=(platform_font(), 10)).pack(pady=16)

        tk.Button(self.win, text="Got it", command=self.win.destroy, bg=t["accent"], fg=t["bg"],
                  relief="flat", font=(platform_font(), 10, "bold"), padx=24, pady=6,
                  cursor="hand2").pack(pady=(16, 20))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_settings.py -v`
Expected: PASS

- [ ] **Step 5: Run full test suite + lint**

Run: `uv run pytest tests/ -v && uv run ruff check src/ tests/`
Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add src/cogstash/settings.py tests/test_settings.py
git commit -m "feat: implement What's New dialog with version-based content"
```

---

### Task 8: Launch at Startup (Windows)

**Files:**
- Modify: `src/cogstash/settings.py` (add startup shortcut helpers)
- Test: `tests/test_settings.py`

- [ ] **Step 1: Write failing test for startup shortcut**

Add to `tests/test_settings.py`:

```python
import sys

@pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
def test_startup_shortcut_path():
    """get_startup_shortcut_path returns valid Windows startup path."""
    from cogstash.settings import get_startup_shortcut_path
    path = get_startup_shortcut_path()
    assert "Startup" in str(path) or "startup" in str(path)
    assert str(path).endswith(".lnk") or str(path).endswith(".bat")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_settings.py::test_startup_shortcut_path -v`
Expected: FAIL (function doesn't exist)

- [ ] **Step 3: Implement startup shortcut helpers**

Add to `src/cogstash/settings.py`:

```python
def get_startup_shortcut_path() -> Path:
    """Get the path where the startup shortcut/script should be placed (Windows)."""
    import os
    startup_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    return startup_dir / "CogStash.bat"


def set_launch_at_startup(enable: bool) -> None:
    """Enable or disable launch at system startup (Windows only)."""
    if sys.platform != "win32":
        return
    shortcut_path = get_startup_shortcut_path()
    if enable:
        # Create a .bat file that launches cogstash
        exe = sys.executable
        if getattr(sys, "frozen", False):
            exe = sys.argv[0]  # The frozen executable itself
            content = f'@echo off\nstart "" "{exe}"\n'
        else:
            content = f'@echo off\nstart "" "{exe}" -m cogstash\n'
        try:
            shortcut_path.parent.mkdir(parents=True, exist_ok=True)
            shortcut_path.write_text(content, encoding="utf-8")
        except OSError:
            logger.error("Failed to create startup shortcut", exc_info=True)
    else:
        try:
            if shortcut_path.exists():
                shortcut_path.unlink()
        except OSError:
            logger.error("Failed to remove startup shortcut", exc_info=True)
```

Add `logger` import at the top of settings.py:

```python
from cogstash.app import (
    CogStashConfig,
    THEMES,
    WINDOW_SIZES,
    DEFAULT_SMART_TAGS,
    platform_font,
    merge_tags,
    save_config,
    logger,
)
```

Then wire `set_launch_at_startup` into `_save_general()`:

```python
def _save_general(self):
    """Save General tab settings to config."""
    self.config.output_file = Path(self.notes_file_var.get()).expanduser()
    new_launch = self.launch_var.get()
    if new_launch != self.config.launch_at_startup:
        set_launch_at_startup(new_launch)
    self.config.launch_at_startup = new_launch
    save_config(self.config, self.config_path)
    self._flash_saved()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_settings.py -v`
Expected: PASS

- [ ] **Step 5: Run full test suite + lint**

Run: `uv run pytest tests/ -v && uv run ruff check src/ tests/`
Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add src/cogstash/settings.py tests/test_settings.py
git commit -m "feat: add launch-at-startup support for Windows"
```

---

### Task 9: Integration Test + Push

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All tests pass (100 existing + ~10 new ≈ 110+).

- [ ] **Step 2: Run lint + type check**

Run: `uv run ruff check src/ tests/ && uv run mypy src/cogstash/`
Expected: All clean.

- [ ] **Step 3: Manual smoke test**

Run: `uv run cogstash` and verify:
1. If first run (delete `~/.cogstash.json` first): wizard appears
2. After wizard: app runs normally with tray icon
3. Right-click tray → Settings opens the settings window
4. All 4 tabs work (General, Appearance, Tags, About)
5. Save works in each tab

- [ ] **Step 4: Push to main**

```bash
git push origin main
```

- [ ] **Step 5: Update __init__.py CLI dispatch**

Add "settings" as a potential future CLI subcommand (optional — for `cogstash settings` to open settings from terminal). In `src/cogstash/__init__.py`, the existing dispatch already routes unknown args to app, so no change needed. But verify the Settings tray menu path works end-to-end.

- [ ] **Step 6: Verify CI passes**

Check GitHub Actions CI workflow passes with the new code.
