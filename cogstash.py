"""
cogstash.py — A global hotkey brain dump — press, type, gone.
Hotkey: Ctrl + Shift + Space
Enter  → appends timestamped note to cogstash.md
Escape → hides window
"""

from __future__ import annotations

import tkinter as tk
from datetime import datetime
from pathlib import Path
import queue
from pynput import keyboard
import logging
import os
import subprocess
import sys
import threading
import json
import re
from dataclasses import dataclass

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

DEFAULT_SMART_TAGS = {
    "todo":      "☐",
    "urgent":    "🔴",
    "important": "⭐",
    "idea":      "💡",
}

# ── Validation ────────────────────────────────────────────────────────────────
_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

# ── Config ────────────────────────────────────────────────────────────────────
HOTKEY      = "<ctrl>+<shift>+<space>"
OUTPUT_FILE = Path.home() / "cogstash.md"
LOG_FILE    = Path.home() / "cogstash.log"

logger = logging.getLogger("cogstash")
logger.setLevel(logging.WARNING)
_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M"))
logger.addHandler(_handler)


@dataclass
class CogStashConfig:
    hotkey: str = "<ctrl>+<shift>+<space>"
    output_file: Path = None
    log_file: Path = None
    theme: str = "tokyo-night"
    window_size: str = "default"
    tags: dict[str, dict[str, str]] | None = None

    def __post_init__(self):
        if self.output_file is None:
            self.output_file = Path.home() / "cogstash.md"
        if self.log_file is None:
            self.log_file = Path.home() / "cogstash.log"


def load_config(config_path: Path) -> CogStashConfig:
    """Load config from JSON file, merging with defaults."""
    defaults = {
        "hotkey": "<ctrl>+<shift>+<space>",
        "output_file": str(Path.home() / "cogstash.md"),
        "log_file": str(Path.home() / "cogstash.log"),
        "theme": "tokyo-night",
        "window_size": "default",
    }

    if not config_path.exists():
        logger.warning("No config file found — creating %s with defaults", config_path)
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(json.dumps(defaults, indent=2), encoding="utf-8")
        except OSError:
            logger.warning("Could not create config file %s", config_path, exc_info=True)
        return CogStashConfig()

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Bad config file %s: %s — using defaults", config_path, e)
        return CogStashConfig()

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

    # Parse and validate custom tags
    raw_tags = data.get("tags", {})
    valid_tags = {}
    if isinstance(raw_tags, dict):
        for name, props in raw_tags.items():
            if not isinstance(props, dict):
                logger.warning("Tag '%s': expected object, skipping", name)
                continue
            emoji = props.get("emoji")
            color = props.get("color")
            if not emoji:
                logger.warning("Tag '%s': missing emoji, skipping", name)
                continue
            if not color or not _HEX_RE.match(color):
                logger.warning("Tag '%s': missing or invalid color, skipping", name)
                continue
            valid_tags[name] = {"emoji": emoji, "color": color}
    tags = valid_tags if valid_tags else None

    return CogStashConfig(
        hotkey=merged["hotkey"],
        output_file=output_file,
        log_file=log_file,
        theme=merged["theme"],
        window_size=merged["window_size"],
        tags=tags,
    )


def merge_tags(config: CogStashConfig) -> tuple[dict[str, str], dict[str, str]]:
    """Merge built-in tags with user-defined tags. Returns (smart_tags, tag_colors)."""
    from cogstash_search import DEFAULT_TAG_COLORS
    smart_tags = dict(DEFAULT_SMART_TAGS)
    tag_colors = dict(DEFAULT_TAG_COLORS)
    if config.tags:
        for name, props in config.tags.items():
            smart_tags[name] = props["emoji"]
            tag_colors[name] = props["color"]
    return smart_tags, tag_colors


_TAG_RE = re.compile(r"(?:^|\s)#(\w+)")


def parse_smart_tags(text: str) -> str:
    """Prepend smart-tag emojis to text. Tags stay inline for searchability."""
    matches = _TAG_RE.findall(text)
    seen = []
    for tag in matches:
        tag_lower = tag.lower()
        if tag_lower in DEFAULT_SMART_TAGS and tag_lower not in seen:
            seen.append(tag_lower)
    if not seen:
        return text
    prefix = " ".join(DEFAULT_SMART_TAGS[t] for t in seen)
    return f"{prefix} {text}"


def platform_font() -> str:
    """Return the native font family for the current OS."""
    fonts = {
        "win32": "Segoe UI",
        "darwin": "Helvetica Neue",
        "linux": "sans-serif",
    }
    return fonts.get(sys.platform, "TkDefaultFont")


def configure_dpi() -> None:
    """Enable DPI awareness on Windows so the UI renders crisply on HiDPI displays."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass


def create_tray_icon(app_queue: queue.Queue, config: CogStashConfig) -> None:
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

    def browse_notes():
        app_queue.put("BROWSE")

    menu = pystray.Menu(
        pystray.MenuItem("CogStash ⚡", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(f"Open {config.output_file.name}", lambda: open_notes()),
        pystray.MenuItem("Browse Notes", lambda: browse_notes()),
        pystray.MenuItem("Quit", quit_app),
    )

    icon = pystray.Icon("cogstash", img, "CogStash", menu)
    thread = threading.Thread(target=icon.run, daemon=True)
    thread.start()


class CogStash:
    def __init__(self, root: tk.Tk, config: CogStashConfig):
        self.root = root
        self.config = config
        self.queue = queue.Queue()
        self.is_visible = False
        self.theme = THEMES[config.theme]
        self.win_size = WINDOW_SIZES[config.window_size]

        self.setup_ui()
        self.root.withdraw()
        self.root.after(100, self.poll_queue)

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
            frame, text="⚡  CogStash", bg=t["bg"], fg=t["fg"],
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
        tag_hints = "  ".join(f"{emoji} #{name}" for name, emoji in DEFAULT_SMART_TAGS.items())
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
        """Escape dismisses autocomplete first, then the window."""
        if self.autocomplete_popup:
            self.hide_autocomplete()
            return "break"
        self.hide_window()
        return "break"

    def _on_key_release(self, event=None):
        """Check if we should show/update/hide the autocomplete popup, and grow widget."""
        self._grow_text_widget()

        # Skip autocomplete logic for navigation/control keys
        if event and event.keysym in ("Up", "Down", "Tab", "Escape"):
            return

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
            (name, emoji) for name, emoji in DEFAULT_SMART_TAGS.items()
            if name.startswith(fragment)
        ]

        if not matches:
            self.hide_autocomplete()
            return

        self.show_autocomplete(matches, hash_idx, cursor_pos)

    def hide_autocomplete(self):
        """Destroy the autocomplete popup if it exists."""
        if self.autocomplete_popup:
            # Unbind navigation keys
            self.text.unbind("<Up>")
            self.text.unbind("<Down>")
            self.text.unbind("<Tab>")
            self.autocomplete_popup.destroy()
            self.autocomplete_popup = None

    def _ac_confirm(self, event=None):
        """Insert the selected autocomplete tag."""
        if not self.autocomplete_popup:
            return
        name, _ = self._ac_matches[self._ac_selected]
        self._insert_tag(name)
        return "break"

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

    def poll_queue(self):
        """Check the queue for messages from the pynput/tray threads."""
        try:
            while True:
                msg = self.queue.get_nowait()
                if msg == "SHOW":
                    self.show_window()
                elif msg == "BROWSE":
                    self._open_browse()
                elif msg == "QUIT":
                    self.root.quit()
                    return
        except queue.Empty:
            pass
        self.root.after(100, self.poll_queue)

    def _open_browse(self):
        """Open the Browse Notes window."""
        from cogstash_browse import BrowseWindow
        BrowseWindow(self.root, self.config)

    def show_window(self):
        """Reveal the window, clear past text, and steal focus."""
        if not self.is_visible:
            self.is_visible = True
            self.root.deiconify()
            self.text.delete("1.0", tk.END)
            self.text.configure(height=self.win_size["lines"])
            self.text.focus_force()

    def hide_window(self, event=None):
        """Hide the window without destroying it."""
        if self.is_visible:
            self.is_visible = False
            self.root.withdraw()

    def flash_border(self, color: str, then_hide: bool = True) -> None:
        """Briefly flash the window border, then optionally hide."""
        self.root.configure(bg=color)
        self.root.after(300, lambda: self._reset_border(then_hide))

    def _reset_border(self, then_hide: bool) -> None:
        """Reset border color and optionally hide the window."""
        self.root.configure(bg=self.theme["bg"])
        if then_hide:
            self.hide_window()

    def on_submit(self, event=None):
        """Save the note and show visual feedback."""
        # If autocomplete is open, Enter confirms the selection instead of saving
        if self.autocomplete_popup:
            return self._ac_confirm(event)
        text = self.text.get("1.0", "end-1c").strip()
        if not text:
            return "break"
        self.hide_autocomplete()
        if self.append_note(text):
            self.flash_border(self.theme["accent"], then_hide=True)
        else:
            self.flash_border(self.theme["error"], then_hide=False)
        return "break"

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


def main():
    # CLI subcommands — delegate before loading GUI
    if len(sys.argv) > 1 and sys.argv[1] in ("recent", "search", "tags"):
        from cogstash_cli import cli_main
        cli_main(sys.argv[1:])
        return

    config = load_config(Path.home() / ".cogstash.json")

    # Reconfigure logger to use config's log_file
    for h in logger.handlers[:]:
        logger.removeHandler(h)
    _handler = logging.FileHandler(config.log_file, encoding="utf-8")
    _handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M"))
    logger.addHandler(_handler)

    configure_dpi()
    print(f"CogStash is running. ({config.hotkey} to capture · Ctrl+C to quit)")
    print(f"Notes → {config.output_file}")

    root = tk.Tk()
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


if __name__ == "__main__":
    main()
