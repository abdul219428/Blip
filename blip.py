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
import sys

# ── Config ────────────────────────────────────────────────────────────────────
HOTKEY      = "<ctrl>+<shift>+<space>"
OUTPUT_FILE = Path.home() / "blip.md"
LOG_FILE = Path.home() / "blip.log"

logger = logging.getLogger("blip")
logger.setLevel(logging.WARNING)
_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M"))
logger.addHandler(_handler)
# ─────────────────────────────────────────────────────────────────────────────


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
        """Check the queue for messages from the pynput listener thread."""
        try:
            while True:
                msg = self.queue.get_nowait()
                if msg == "SHOW":
                    self.show_window()
        except queue.Empty:
            pass
        finally:
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

    def on_submit(self, event=None):
        """Save the note and hide the UI."""
        text = self.entry.get().strip()
        if text:
            self.append_note(text)
        self.hide_window()

    def append_note(self, text: str) -> None:
        """Append a timestamped note to blip.md."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        line = f"- [{timestamp}] {text}\n"

        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with OUTPUT_FILE.open("a", encoding="utf-8") as f:
            f.write(line)


def main():
    configure_dpi()
    print(f"Blip is running. ({HOTKEY} to capture · Ctrl+C to quit)")
    print(f"Notes → {OUTPUT_FILE}")

    root = tk.Tk()
    app = Blip(root)

    def on_hotkey():
        app.queue.put("SHOW")

    listener = keyboard.GlobalHotKeys({HOTKEY: on_hotkey})
    listener.start()

    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\nBlip stopped.")
    finally:
        listener.stop()


if __name__ == "__main__":
    main()
