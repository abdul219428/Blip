# Phase 2: Capture Experience — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add config file, multi-line input, smart tags with autocomplete, and theme presets to Blip.

**Architecture:** Single-file app (`blip.py`) grows from ~254 to ~450 lines. New data dicts (`THEMES`, `WINDOW_SIZES`, `SMART_TAGS`), a `BlipConfig` dataclass, and `load_config()` are added at the top. `tk.Entry` is replaced with `tk.Text`. Tag parsing and autocomplete are added to the `Blip` class. All existing behavior preserved.

**Tech Stack:** Python 3, tkinter, pynput, pystray, Pillow, pytest

**Spec:** `docs/superpowers/specs/2026-06-24-capture-experience-design.md`

---

### Task 1: Add THEMES, WINDOW_SIZES, and SMART_TAGS dicts

**Files:**
- Modify: `blip.py:19-28` (replace hardcoded config section)
- Test: `test_blip.py`

- [ ] **Step 1: Write failing tests for themes and window sizes**

Add to `test_blip.py`:

```python
def test_theme_colors():
    """Every theme has all 6 required color keys."""
    from blip import THEMES
    required = {"bg", "fg", "entry_bg", "accent", "muted", "error"}
    assert len(THEMES) == 5
    for name, colors in THEMES.items():
        assert set(colors.keys()) == required, f"Theme '{name}' missing keys"
        for key, val in colors.items():
            assert val.startswith("#"), f"Theme '{name}'.{key} not a hex color"


def test_window_size_presets():
    """Every window size has width, lines, and max_lines."""
    from blip import WINDOW_SIZES
    required = {"width", "lines", "max_lines"}
    assert len(WINDOW_SIZES) == 3
    for name, size in WINDOW_SIZES.items():
        assert set(size.keys()) == required, f"Size '{name}' missing keys"
        assert size["lines"] <= size["max_lines"], f"Size '{name}' lines > max_lines"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest test_blip.py::test_theme_colors test_blip.py::test_window_size_presets -v`
Expected: FAIL — `ImportError` (THEMES / WINDOW_SIZES not defined)

- [ ] **Step 3: Add the three data dicts to blip.py**

Replace the config section (lines 19-28) with:

```python
# ── Data ──────────────────────────────────────────────────────────────────────
THEMES = {
    "tokyo-night": {"bg": "#1a1b26", "fg": "#a9b1d6", "entry_bg": "#24283b", "accent": "#7aa2f7", "muted": "#565f89", "error": "#f7768e"},
    "light":       {"bg": "#faf4ed", "fg": "#575279", "entry_bg": "#f2e9e1", "accent": "#d7827e", "muted": "#9893a5", "error": "#b4637a"},
    "dracula":     {"bg": "#282a36", "fg": "#f8f8f2", "entry_bg": "#44475a", "accent": "#bd93f9", "muted": "#6272a4", "error": "#ff5555"},
    "gruvbox":     {"bg": "#282828", "fg": "#ebdbb2", "entry_bg": "#3c3836", "accent": "#b8bb26", "muted": "#665c54", "error": "#fb4934"},
    "mono":        {"bg": "#0a0a0a", "fg": "#d0d0d0", "entry_bg": "#1a1a1a", "accent": "#d0d0d0", "muted": "#4a4a4a", "error": "#ff3333"},
}

WINDOW_SIZES = {
    "compact": {"width": 320, "lines": 2, "max_lines": 5},
    "default": {"width": 400, "lines": 3, "max_lines": 8},
    "wide":    {"width": 520, "lines": 4, "max_lines": 10},
}

SMART_TAGS = {
    "todo":      "☐",
    "urgent":    "🔴",
    "important": "⭐",
    "idea":      "💡",
}

# ── Config ────────────────────────────────────────────────────────────────────
HOTKEY      = "<ctrl>+<shift>+<space>"
OUTPUT_FILE = Path.home() / "blip.md"
LOG_FILE    = Path.home() / "blip.log"
```

Keep the logger setup unchanged below this.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest test_blip.py::test_theme_colors test_blip.py::test_window_size_presets -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest test_blip.py -v`
Expected: All existing tests still pass (8 old + 2 new = 10)

- [ ] **Step 6: Commit**

```bash
git add blip.py test_blip.py
git commit -m "feat: add THEMES, WINDOW_SIZES, and SMART_TAGS dicts"
```

---

### Task 2: Add BlipConfig dataclass and load_config()

**Files:**
- Modify: `blip.py` (add dataclass + function after the data dicts, before the logger)
- Test: `test_blip.py`

- [ ] **Step 1: Write failing tests for config loading**

Add to `test_blip.py`:

```python
import json


def test_load_config_defaults(tmp_path):
    """No config file → returns default BlipConfig."""
    from blip import load_config, BlipConfig
    config = load_config(tmp_path / "nonexistent.json")
    assert isinstance(config, BlipConfig)
    assert config.hotkey == "<ctrl>+<shift>+<space>"
    assert config.theme == "tokyo-night"
    assert config.window_size == "default"
    # Config file should be created with defaults
    assert (tmp_path / "nonexistent.json").exists()


def test_load_config_partial(tmp_path):
    """Partial JSON → missing keys filled from defaults."""
    from blip import load_config
    cfg_file = tmp_path / "blip.json"
    cfg_file.write_text(json.dumps({"theme": "dracula"}), encoding="utf-8")
    config = load_config(cfg_file)
    assert config.theme == "dracula"
    assert config.hotkey == "<ctrl>+<shift>+<space>"  # filled from default


def test_load_config_malformed(tmp_path):
    """Bad JSON → warning logged, defaults returned."""
    from blip import load_config
    cfg_file = tmp_path / "blip.json"
    cfg_file.write_text("{bad json!!!", encoding="utf-8")
    config = load_config(cfg_file)
    assert config.theme == "tokyo-night"  # all defaults


def test_load_config_unknown_theme(tmp_path):
    """Unknown theme → falls back to tokyo-night."""
    from blip import load_config
    cfg_file = tmp_path / "blip.json"
    cfg_file.write_text(json.dumps({"theme": "nonexistent"}), encoding="utf-8")
    config = load_config(cfg_file)
    assert config.theme == "tokyo-night"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest test_blip.py::test_load_config_defaults test_blip.py::test_load_config_partial test_blip.py::test_load_config_malformed test_blip.py::test_load_config_unknown_theme -v`
Expected: FAIL — `ImportError` (load_config / BlipConfig not defined)

- [ ] **Step 3: Implement BlipConfig and load_config**

Add after the `LOG_FILE` line and before the logger setup in `blip.py`:

```python
from dataclasses import dataclass


@dataclass
class BlipConfig:
    hotkey: str = "<ctrl>+<shift>+<space>"
    output_file: Path = None
    log_file: Path = None
    theme: str = "tokyo-night"
    window_size: str = "default"

    def __post_init__(self):
        if self.output_file is None:
            self.output_file = Path.home() / "blip.md"
        if self.log_file is None:
            self.log_file = Path.home() / "blip.log"


def load_config(config_path: Path) -> BlipConfig:
    """Load config from JSON file, merging with defaults."""
    defaults = {
        "hotkey": "<ctrl>+<shift>+<space>",
        "output_file": str(Path.home() / "blip.md"),
        "log_file": str(Path.home() / "blip.log"),
        "theme": "tokyo-night",
        "window_size": "default",
    }

    if not config_path.exists():
        logger.info("No config file found — creating %s with defaults", config_path)
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(json.dumps(defaults, indent=2), encoding="utf-8")
        except OSError:
            logger.warning("Could not create config file %s", config_path, exc_info=True)
        return BlipConfig()

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Bad config file %s: %s — using defaults", config_path, e)
        return BlipConfig()

    merged = {**defaults, **data}

    # Validate theme
    if merged["theme"] not in THEMES:
        logger.warning("Unknown theme '%s' — falling back to tokyo-night", merged["theme"])
        merged["theme"] = "tokyo-night"

    # Validate window_size
    if merged["window_size"] not in WINDOW_SIZES:
        logger.warning("Unknown window_size '%s' — falling back to default", merged["window_size"])
        merged["window_size"] = "default"

    # Expand ~ paths
    output_file = Path(merged["output_file"]).expanduser()
    log_file = Path(merged["log_file"]).expanduser()

    return BlipConfig(
        hotkey=merged["hotkey"],
        output_file=output_file,
        log_file=log_file,
        theme=merged["theme"],
        window_size=merged["window_size"],
    )
```

Also add `import json` at the top of `blip.py` (with the other imports).

Note: The logger is used inside `load_config`, but the logger is defined right after this code. Move the logger setup **before** `load_config` so it's available. The order should be:
1. Data dicts (THEMES, WINDOW_SIZES, SMART_TAGS)
2. HOTKEY, OUTPUT_FILE, LOG_FILE constants (kept as fallback defaults)
3. Logger setup
4. BlipConfig dataclass + load_config()

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest test_blip.py::test_load_config_defaults test_blip.py::test_load_config_partial test_blip.py::test_load_config_malformed test_blip.py::test_load_config_unknown_theme -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest test_blip.py -v`
Expected: All 14 tests pass

- [ ] **Step 6: Commit**

```bash
git add blip.py test_blip.py
git commit -m "feat: add BlipConfig dataclass and load_config()"
```

---

### Task 3: Add parse_smart_tags() function

**Files:**
- Modify: `blip.py` (add function after `load_config`)
- Test: `test_blip.py`

- [ ] **Step 1: Write failing tests for tag parsing**

Add to `test_blip.py`:

```python
def test_parse_tags_smart():
    """Smart tags get emoji prefixes prepended to text."""
    from blip import parse_smart_tags
    result = parse_smart_tags("Review PR #42 #todo #urgent")
    assert result.startswith("☐ 🔴 ")
    assert "Review PR #42 #todo #urgent" in result


def test_parse_tags_dedup():
    """Duplicate smart tags produce only one emoji prefix."""
    from blip import parse_smart_tags
    result = parse_smart_tags("do thing #todo and also #todo")
    # Should have exactly one ☐, not two
    assert result.count("☐") == 1


def test_parse_tags_url_safe():
    """URL fragments are not matched as tags."""
    from blip import parse_smart_tags
    result = parse_smart_tags("see http://example.com#section for details")
    # No emoji should be prepended — #section is not a standalone tag
    assert not result.startswith("☐")
    assert not result.startswith("🔴")
    assert not result.startswith("⭐")
    assert not result.startswith("💡")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest test_blip.py::test_parse_tags_smart test_blip.py::test_parse_tags_dedup test_blip.py::test_parse_tags_url_safe -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement parse_smart_tags**

Add to `blip.py` after `load_config`:

```python
import re

_TAG_RE = re.compile(r"(?:^|\s)#(\w+)")


def parse_smart_tags(text: str) -> str:
    """Prepend smart-tag emojis to text. Tags stay inline for searchability."""
    matches = _TAG_RE.findall(text)
    seen = []
    for tag in matches:
        tag_lower = tag.lower()
        if tag_lower in SMART_TAGS and tag_lower not in seen:
            seen.append(tag_lower)
    if not seen:
        return text
    prefix = " ".join(SMART_TAGS[t] for t in seen)
    return f"{prefix} {text}"
```

Add `import re` to the imports at the top of the file.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest test_blip.py::test_parse_tags_smart test_blip.py::test_parse_tags_dedup test_blip.py::test_parse_tags_url_safe -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest test_blip.py -v`
Expected: All 17 tests pass

- [ ] **Step 6: Commit**

```bash
git add blip.py test_blip.py
git commit -m "feat: add parse_smart_tags() with emoji prefixes"
```

---

### Task 4: Update append_note for multi-line format

**Files:**
- Modify: `blip.py` — `Blip.append_note()` method
- Test: `test_blip.py`

- [ ] **Step 1: Write failing tests for multi-line format and empty submit**

Add to `test_blip.py`:

```python
def test_multiline_format(tmp_path):
    """Multi-line text uses indented continuation lines."""
    import blip as blip_mod

    test_file = tmp_path / "blip.md"
    original = blip_mod.OUTPUT_FILE
    blip_mod.OUTPUT_FILE = test_file

    try:
        root = tk.Tk()
        root.withdraw()
        app = blip_mod.Blip(root)
        result = app.append_note("line one\nline two\nline three")
        root.destroy()

        assert result is True
        content = test_file.read_text(encoding="utf-8")
        lines = content.strip().split("\n")
        assert len(lines) == 3
        assert lines[0].startswith("- [")
        assert lines[0].endswith("] line one")
        assert lines[1] == "  line two"
        assert lines[2] == "  line three"
    finally:
        blip_mod.OUTPUT_FILE = original


def test_empty_submit_ignored(tmp_path):
    """Whitespace-only text is not saved."""
    import blip as blip_mod

    test_file = tmp_path / "blip.md"
    original = blip_mod.OUTPUT_FILE
    blip_mod.OUTPUT_FILE = test_file

    try:
        root = tk.Tk()
        root.withdraw()
        app = blip_mod.Blip(root)
        result = app.append_note("   \n  \n  ")
        root.destroy()

        assert result is False
        assert not test_file.exists()
    finally:
        blip_mod.OUTPUT_FILE = original
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest test_blip.py::test_multiline_format test_blip.py::test_empty_submit_ignored -v`
Expected: FAIL — multi-line format doesn't match, empty text still writes

- [ ] **Step 3: Update append_note method**

Replace the `append_note` method in `blip.py`:

```python
def append_note(self, text: str) -> bool:
    """Append a timestamped note to output file. Returns True on success."""
    text = text.strip()
    if not text:
        return False

    # Truncate very long notes
    if len(text) > 10_000:
        text = text[:10_000]

    text = parse_smart_tags(text)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = text.split("\n")
    first = f"- [{timestamp}] {lines[0]}\n"
    rest = "".join(f"  {line}\n" for line in lines[1:])

    try:
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with OUTPUT_FILE.open("a", encoding="utf-8") as f:
            f.write(first + rest)
        return True
    except OSError:
        logger.error("Failed to write to %s", OUTPUT_FILE, exc_info=True)
        return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest test_blip.py::test_multiline_format test_blip.py::test_empty_submit_ignored -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest test_blip.py -v`
Expected: All 19 tests pass

- [ ] **Step 6: Commit**

```bash
git add blip.py test_blip.py
git commit -m "feat: multi-line note format with smart tags"
```

---

### Task 5: Wire config into main() and replace hardcoded values

**Files:**
- Modify: `blip.py` — `main()`, `Blip.__init__()`, `create_tray_icon()`

This task replaces all hardcoded constants (colors, widths, paths) with config-driven values. No new tests — existing tests cover behavior; this task wires config through at the application level.

- [ ] **Step 1: Update Blip.__init__ to accept config**

Change `Blip.__init__` signature to accept config:

```python
class Blip:
    def __init__(self, root: tk.Tk, config: BlipConfig):
        self.root = root
        self.config = config
        self.queue = queue.Queue()
        self.is_visible = False
        self.theme = THEMES[config.theme]
        self.win_size = WINDOW_SIZES[config.window_size]

        self.setup_ui()
        self.root.withdraw()
        self.root.after(100, self.poll_queue)
```

- [ ] **Step 2: Update setup_ui to use theme and window_size**

Replace all hardcoded colors with `self.theme[...]` references. Replace `tk.Entry` with `tk.Text`. Update hint text. Add tag hints footer:

```python
def setup_ui(self):
    """Initialize the borderless window and its widgets."""
    t = self.theme
    self.root.overrideredirect(True)
    self.root.attributes("-topmost", True)
    self.root.configure(bg=t["bg"])

    padding = 12
    frame = tk.Frame(self.root, bg=t["bg"], padx=padding, pady=padding)
    frame.pack()

    tk.Label(
        frame, text="⚡  Blip", bg=t["bg"], fg=t["fg"],
        font=(platform_font(), 9), anchor="w",
    ).pack(fill="x", pady=(0, 6))

    self.text = tk.Text(
        frame, width=self.win_size["width"] // 7,
        height=self.win_size["lines"],
        bg=t["entry_bg"], fg=t["fg"], insertbackground=t["fg"],
        relief="flat", font=(platform_font(), 12),
        wrap="word", undo=True,
    )
    self.text.pack(ipady=6)

    self.hint_label = tk.Label(
        frame,
        text="Enter to save · Shift+Enter for new line · Esc to cancel",
        bg=t["bg"], fg=t["muted"],
        font=(platform_font(), 8), anchor="w",
    )
    self.hint_label.pack(fill="x", pady=(4, 0))

    # Tag hints footer
    tag_hints = "  ".join(f"{emoji} #{name}" for name, emoji in SMART_TAGS.items())
    tk.Label(
        frame, text=tag_hints, bg=t["bg"], fg=t["muted"],
        font=(platform_font(), 8), anchor="w",
    ).pack(fill="x", pady=(2, 0))

    # Keybindings
    self.text.bind("<Return>", self.on_submit)
    self.text.bind("<Shift-Return>", self._insert_newline)
    self.text.bind("<Escape>", self._on_escape)
    self.text.bind("<KeyRelease>", self._on_key_release)

    self.autocomplete_popup = None

    self.root.update_idletasks()
    w = self.root.winfo_reqwidth()
    h = self.root.winfo_reqheight()
    sw = self.root.winfo_screenwidth()
    sh = self.root.winfo_screenheight()
    self.root.geometry(f"+{(sw - w) // 2}+{(sh - h) // 3}")
```

- [ ] **Step 3: Add keybinding helper methods and autocomplete stubs**

These stubs prevent `AttributeError` until Task 6 replaces them with full implementations:

```python
def _insert_newline(self, event=None):
    """Insert a newline at cursor position."""
    self.text.insert(tk.INSERT, "\n")
    self._grow_text_widget()
    return "break"

def _grow_text_widget(self):
    """Grow the text widget height as content grows, up to max_lines."""
    content = self.text.get("1.0", "end-1c")
    line_count = max(content.count("\n") + 1, self.win_size["lines"])
    new_height = min(line_count, self.win_size["max_lines"])
    self.text.configure(height=new_height)

def _on_escape(self, event=None):
    """Stub — dismiss window. Task 6 adds autocomplete-first logic."""
    self.hide_window()
    return "break"

def _on_key_release(self, event=None):
    """Stub — no-op. Task 6 adds autocomplete trigger logic."""
    pass

def hide_autocomplete(self):
    """Stub — no-op when no popup exists. Task 6 adds full implementation."""
    if self.autocomplete_popup:
        self.autocomplete_popup.destroy()
        self.autocomplete_popup = None
```

- [ ] **Step 4: Update on_submit for Text widget**

```python
def on_submit(self, event=None):
    """Save the note and show visual feedback."""
    text = self.text.get("1.0", "end-1c").strip()
    if not text:
        return "break"
    self.hide_autocomplete()
    if self.append_note(text):
        self.flash_border(self.theme["accent"], then_hide=True)
    else:
        self.flash_border(self.theme["error"], then_hide=False)
    return "break"
```

- [ ] **Step 5: Update show_window, hide_window, flash_border, _reset_border**

```python
def show_window(self):
    """Reveal the window, clear past text, and steal focus."""
    if not self.is_visible:
        self.is_visible = True
        self.root.deiconify()
        self.text.delete("1.0", tk.END)
        self.text.configure(height=self.win_size["lines"])
        self.text.focus_force()

def flash_border(self, color: str, then_hide: bool = True) -> None:
    """Briefly flash the window border, then optionally hide."""
    self.root.configure(bg=color)
    self.root.after(300, lambda: self._reset_border(then_hide))

def _reset_border(self, then_hide: bool) -> None:
    """Reset border color and optionally hide the window."""
    self.root.configure(bg=self.theme["bg"])
    if then_hide:
        self.hide_window()
```

- [ ] **Step 6: Update create_tray_icon to accept config**

Change signature to `create_tray_icon(app_queue: queue.Queue, config: BlipConfig)`. Replace `OUTPUT_FILE` reference with `config.output_file`. Update tray icon colors to use theme:

```python
def create_tray_icon(app_queue: queue.Queue, config: BlipConfig) -> None:
    """Create and run a system tray icon on a daemon thread."""
    try:
        import pystray
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        logger.warning("pystray or Pillow not installed — skipping tray icon")
        return

    theme = THEMES[config.theme]
    # Parse hex color to RGBA tuple
    def hex_to_rgba(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (255,)

    img = Image.new("RGBA", (64, 64), hex_to_rgba(theme["bg"]))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial", 40)
    except OSError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), "⚡", font=font)
    x = (64 - (bbox[2] - bbox[0])) // 2 - bbox[0]
    y = (64 - (bbox[3] - bbox[1])) // 2 - bbox[1]
    draw.text((x, y), "⚡", fill=hex_to_rgba(theme["fg"]), font=font)

    def open_notes():
        path = str(config.output_file)
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
        pystray.MenuItem(f"Open {config.output_file.name}", lambda: open_notes()),
        pystray.MenuItem("Quit", quit_app),
    )

    icon = pystray.Icon("blip", img, "Blip", menu)
    thread = threading.Thread(target=icon.run, daemon=True)
    thread.start()
```

- [ ] **Step 7: Update main() to load config and pass it through**

```python
def main():
    config = load_config(Path.home() / ".blip.json")

    # Reconfigure logger to use config's log_file
    global LOG_FILE, OUTPUT_FILE
    LOG_FILE = config.log_file
    OUTPUT_FILE = config.output_file
    for h in logger.handlers[:]:
        logger.removeHandler(h)
    _handler = logging.FileHandler(config.log_file, encoding="utf-8")
    _handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M"))
    logger.addHandler(_handler)

    configure_dpi()
    print(f"Blip is running. ({config.hotkey} to capture · Ctrl+C to quit)")
    print(f"Notes → {config.output_file}")

    root = tk.Tk()
    app = Blip(root, config)

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
        print("\nBlip stopped.")
    finally:
        if listener is not None:
            listener.stop()
```

- [ ] **Step 8: Update append_note to use self.config.output_file**

Replace the `OUTPUT_FILE` references in `append_note` with `self.config.output_file`:

```python
def append_note(self, text: str) -> bool:
    """Append a timestamped note to output file. Returns True on success."""
    text = text.strip()
    if not text:
        return False
    if len(text) > 10_000:
        text = text[:10_000]

    text = parse_smart_tags(text)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = text.split("\n")
    first = f"- [{timestamp}] {lines[0]}\n"
    rest = "".join(f"  {line}\n" for line in lines[1:])
    output_file = self.config.output_file

    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with output_file.open("a", encoding="utf-8") as f:
            f.write(first + rest)
        return True
    except OSError:
        logger.error("Failed to write to %s", output_file, exc_info=True)
        return False
```

- [ ] **Step 9: Fix existing tests to pass config**

Update the test helpers that create `Blip(root)` to pass `Blip(root, BlipConfig())`. Also update tests that patch `blip_mod.OUTPUT_FILE` to instead pass a config with `output_file=test_file`:

```python
# In test_append_note_creates_file, test_append_note_appends, test_append_note_error_handling,
# test_multiline_format, test_empty_submit_ignored, and test_show_hide_state:
# Replace:  app = blip_mod.Blip(root)
# With:     app = blip_mod.Blip(root, blip_mod.BlipConfig(output_file=test_file))
# And remove the OUTPUT_FILE patching (original/finally blocks)
```

For `test_show_hide_state`, just use `blip_mod.Blip(root, blip_mod.BlipConfig())`.

For `test_append_note_error_handling`, use:
```python
app = blip_mod.Blip(root, blip_mod.BlipConfig(output_file=Path("\\\\nonexistent_server_xyz\\share\\blip.md")))
```

- [ ] **Step 10: Run full test suite**

Run: `python -m pytest test_blip.py -v`
Expected: All 19 tests pass

- [ ] **Step 11: Commit**

```bash
git add blip.py test_blip.py
git commit -m "feat: wire BlipConfig through app, replace hardcoded values"
```

---

### Task 6: Add tag autocomplete popup

**Files:**
- Modify: `blip.py` — replace stub methods `_on_key_release`, `_on_escape`, `hide_autocomplete` with full implementations, add `show_autocomplete`, `_ac_navigate`, `_ac_confirm`, `_click_autocomplete`, `_insert_tag` methods to `Blip` class

No new unit tests for this task — autocomplete is a UI interaction feature that requires tkinter event simulation. The existing tag parsing tests cover the logic. Manual testing is needed.

- [ ] **Step 1: Replace stub methods with full autocomplete implementation**

Replace the stub `_on_escape`, `_on_key_release`, and `hide_autocomplete` methods (from Task 5) with full implementations. Add new methods for autocomplete UI:

```python
def _on_escape(self, event=None):
    """Escape dismisses autocomplete first, then the window."""
    if self.autocomplete_popup:
        self.hide_autocomplete()
        return "break"
    self.hide_window()
    return "break"

def _on_key_release(self, event=None):
    """Check if we should show/update/hide the autocomplete popup."""
    # Get text from cursor backwards to find # trigger
    cursor_pos = self.text.index(tk.INSERT)
    line_start = self.text.index(f"{cursor_pos} linestart")
    line_text = self.text.get(line_start, cursor_pos)

    # Find the last # in the current line segment
    hash_idx = line_text.rfind("#")
    if hash_idx == -1 or (hash_idx > 0 and line_text[hash_idx - 1] not in (" ", "\t")):
        self.hide_autocomplete()
        return

    # Text after the #
    fragment = line_text[hash_idx + 1:].lower()

    # Filter matching smart tags
    matches = [
        (name, emoji) for name, emoji in SMART_TAGS.items()
        if name.startswith(fragment)
    ]

    if not matches:
        self.hide_autocomplete()
        return

    self.show_autocomplete(matches, hash_idx, cursor_pos)

def show_autocomplete(self, matches, hash_idx, cursor_pos):
    """Show or update the autocomplete popup near the cursor."""
    self.hide_autocomplete()
    t = self.theme

    popup = tk.Toplevel(self.root)
    popup.overrideredirect(True)
    popup.attributes("-topmost", True)
    popup.configure(bg=t["entry_bg"])
    self.autocomplete_popup = popup
    self._ac_matches = matches
    self._ac_selected = 0
    self._ac_hash_idx = hash_idx

    # Position near cursor
    try:
        bbox = self.text.bbox(cursor_pos)
        if bbox:
            x = self.text.winfo_rootx() + bbox[0]
            y = self.text.winfo_rooty() + bbox[1] + bbox[3] + 4
        else:
            x = self.text.winfo_rootx()
            y = self.text.winfo_rooty() + self.text.winfo_height()
    except tk.TclError:
        x = self.text.winfo_rootx()
        y = self.text.winfo_rooty() + self.text.winfo_height()

    popup.geometry(f"+{x}+{y}")

    self._ac_labels = []
    for i, (name, emoji) in enumerate(matches):
        bg = t["accent"] if i == 0 else t["entry_bg"]
        fg = t["bg"] if i == 0 else t["fg"]
        lbl = tk.Label(
            popup, text=f" {emoji} #{name} ", bg=bg, fg=fg,
            font=(platform_font(), 10), anchor="w",
        )
        lbl.pack(fill="x", padx=2, pady=1)
        lbl.bind("<Button-1>", lambda e, idx=i: self._click_autocomplete(idx))
        self._ac_labels.append(lbl)

    # Bind navigation keys on the text widget
    self.text.bind("<Up>", self._ac_navigate)
    self.text.bind("<Down>", self._ac_navigate)
    self.text.bind("<Tab>", self._ac_confirm)

def _ac_navigate(self, event):
    """Navigate autocomplete selection with arrow keys."""
    if not self.autocomplete_popup:
        return
    t = self.theme
    old = self._ac_selected
    if event.keysym == "Up":
        self._ac_selected = max(0, self._ac_selected - 1)
    elif event.keysym == "Down":
        self._ac_selected = min(len(self._ac_matches) - 1, self._ac_selected + 1)

    # Update highlight
    self._ac_labels[old].configure(bg=t["entry_bg"], fg=t["fg"])
    self._ac_labels[self._ac_selected].configure(bg=t["accent"], fg=t["bg"])
    return "break"

def _ac_confirm(self, event=None):
    """Insert the selected autocomplete tag."""
    if not self.autocomplete_popup:
        return
    name, _ = self._ac_matches[self._ac_selected]
    self._insert_tag(name)
    return "break"

def _click_autocomplete(self, idx):
    """Handle clicking an autocomplete option."""
    name, _ = self._ac_matches[idx]
    self._insert_tag(name)

def _insert_tag(self, tag_name):
    """Replace the #fragment with the full tag name."""
    # Delete from the # to the cursor
    cursor_pos = self.text.index(tk.INSERT)
    line_start = self.text.index(f"{cursor_pos} linestart")
    line_text = self.text.get(line_start, cursor_pos)
    hash_idx = line_text.rfind("#")
    delete_from = f"{line_start}+{hash_idx}c"
    self.text.delete(delete_from, cursor_pos)
    self.text.insert(delete_from, f"#{tag_name}")
    self.hide_autocomplete()

def hide_autocomplete(self):
    """Destroy the autocomplete popup if it exists."""
    if self.autocomplete_popup:
        # Unbind navigation keys
        self.text.unbind("<Up>")
        self.text.unbind("<Down>")
        self.text.unbind("<Tab>")
        self.autocomplete_popup.destroy()
        self.autocomplete_popup = None
```

- [ ] **Step 2: Run full test suite**

Run: `python -m pytest test_blip.py -v`
Expected: All 19 tests still pass

- [ ] **Step 3: Commit**

```bash
git add blip.py
git commit -m "feat: add tag autocomplete popup with keyboard navigation"
```

---

### Task 7: Final integration test and cleanup

**Files:**
- Modify: `blip.py` (any final cleanup)

- [ ] **Step 1: Run full test suite**

Run: `python -m pytest test_blip.py -v`
Expected: All 19 tests pass

- [ ] **Step 2: Verify blip.py is valid Python**

Run: `python -c "import blip; print('OK —', len(open('blip.py').readlines()), 'lines')"`
Expected: `OK — ~400-450 lines`

- [ ] **Step 3: Verify key imports work**

Run: `python -c "from blip import load_config, parse_smart_tags, THEMES, WINDOW_SIZES, SMART_TAGS; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit if any cleanup was needed**

```bash
git add -A
git commit -m "chore: Phase 2 final cleanup"
```
