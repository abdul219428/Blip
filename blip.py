"""
blip.py — A global hotkey brain dump — press, type, gone.
Hotkey: Ctrl + Shift + Space
Enter  → appends timestamped note to blip.md
Escape → hides window
"""

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

logger = logging.getLogger("blip")
logger.setLevel(logging.WARNING)
_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M"))
logger.addHandler(_handler)


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


def create_tray_icon(app_queue: queue.Queue) -> None:
    """Create and run a system tray icon on a daemon thread."""
    try:
        import pystray
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        logger.warning("pystray or Pillow not installed — skipping tray icon")
        return

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

    thread = threading.Thread(target=icon.run, daemon=True)
    thread.start()


class Blip:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.queue = queue.Queue()
        self.is_visible = False

        self.setup_ui()
        self.root.withdraw()

        self.root.after(100, self.poll_queue)

    def setup_ui(self):
        """Initialize the borderless window and its widgets."""
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#1e1e2e")

        padding = 12
        frame = tk.Frame(self.root, bg="#1e1e2e", padx=padding, pady=padding)
        frame.pack()

        tk.Label(
            frame,
            text="⚡  Blip",
            bg="#1e1e2e",
            fg="#cdd6f4",
            font=(platform_font(), 9),
            anchor="w",
        ).pack(fill="x", pady=(0, 6))

        self.entry = tk.Entry(
            frame,
            width=60,
            bg="#313244",
            fg="#cdd6f4",
            insertbackground="#cdd6f4",
            relief="flat",
            font=(platform_font(), 12),
        )
        self.entry.pack(ipady=6)

        tk.Label(
            frame,
            text="Enter to save · Esc to cancel",
            bg="#1e1e2e",
            fg="#585b70",
            font=(platform_font(), 8),
            anchor="w",
        ).pack(fill="x", pady=(4, 0))

        self.entry.bind("<Return>", self.on_submit)
        self.entry.bind("<Escape>", self.hide_window)

        self.root.update_idletasks()
        w = self.root.winfo_reqwidth()
        h = self.root.winfo_reqheight()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"+{(sw - w) // 2}+{(sh - h) // 3}")

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

    def show_window(self):
        """Reveal the window, clear past text, and steal focus."""
        if not self.is_visible:
            self.is_visible = True
            self.root.deiconify()
            self.entry.delete(0, tk.END)
            self.entry.focus_force()

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
        self.root.configure(bg="#1e1e2e")
        if then_hide:
            self.hide_window()

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


if __name__ == "__main__":
    main()
