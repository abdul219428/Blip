"""
cogstash.py — A global hotkey brain dump — press, type, gone.
Hotkey: Ctrl + Shift + Space
Enter  → appends timestamped note to cogstash.md
Escape → hides window
"""

from __future__ import annotations

import logging
import queue
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from typing import Any

from cogstash.core import (
    DEFAULT_SMART_TAGS,
    CogStashConfig,
    append_note_to_file,
    get_default_config_path,
    load_config,
    merge_tags,
    save_config,
)
from cogstash.core import parse_smart_tags as _parse_smart_tags
from cogstash.ui import app_runtime, windows_runtime
from cogstash.ui.ui_shared import THEMES, WINDOW_SIZES, platform_font

parse_smart_tags = _parse_smart_tags

# ── Config ────────────────────────────────────────────────────────────────────
LOG_FILE    = Path.home() / "cogstash.log"

logger = logging.getLogger("cogstash")
logger.setLevel(logging.WARNING)


def _create_log_handler(log_file: Path) -> logging.Handler:
    """Create a file-backed log handler, falling back safely when the path is unavailable."""
    try:
        handler: logging.Handler = logging.FileHandler(log_file, encoding="utf-8")
    except OSError:
        handler = logging.NullHandler()
    else:
        handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M"))
    return handler


logger.addHandler(_create_log_handler(LOG_FILE))


def _build_hotkey_failure_warning(config: CogStashConfig) -> str:
    """Build user-facing guidance for a failed global hotkey registration."""
    return (
        f"The configured global hotkey failed to register: {config.hotkey}\n\n"
        "Global capture is unavailable for the rest of this session; fix the issue and restart "
        "CogStash to re-enable it.\n\n"
        "Likely causes:\n"
        "- another app may already be using the shortcut\n"
        "- platform permissions/accessibility hooks may be blocking registration\n\n"
        f"See the log file for technical details: {config.log_file}\n"
        "If needed, change the hotkey in config for now, then restart CogStash."
    )


def configure_dpi() -> None:
    """Compatibility forwarder for UI Windows runtime DPI setup."""
    windows_runtime.configure_dpi()


class CogStash:
    def __init__(self, root: tk.Tk, config: CogStashConfig, config_path: Path | None = None):
        self.root = root
        self.config = config
        self.config_path = config_path or get_default_config_path()
        self.hotkey_warning: str | None = None
        self.queue: queue.Queue[app_runtime.AppCommand] = queue.Queue()
        self.is_visible = False
        self.theme = THEMES[config.theme]
        self.win_size = WINDOW_SIZES[config.window_size]
        self._browse_windows: list[Any] = []

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
        self.frame = tk.Frame(self.root, bg=t["bg"], padx=padding, pady=padding)
        self.frame.pack()

        self.title_label = tk.Label(
            self.frame, text="⚡  CogStash", bg=t["bg"], fg=t["fg"],
            font=(platform_font(), 9), anchor="w",
        )
        self.title_label.pack(fill="x", pady=(0, 6))

        self.text = tk.Text(
            self.frame, width=self.win_size["width"] // 7,
            height=self.win_size["lines"],
            bg=t["entry_bg"], fg=t["fg"], insertbackground=t["fg"],
            relief="flat", font=(platform_font(), 12),
            wrap="word", undo=True,
        )
        self.text.pack(ipady=6)

        self.hint_label = tk.Label(
            self.frame,
            text="Enter to save · Shift+Enter for new line · Esc to cancel",
            bg=t["bg"], fg=t["muted"],
            font=(platform_font(), 8), anchor="w",
        )
        self.hint_label.pack(fill="x", pady=(4, 0))

        # Tag hints footer
        tag_hints = "  ".join(f"{emoji} #{name}" for name, emoji in DEFAULT_SMART_TAGS.items())
        self.tag_hints_label = tk.Label(
            self.frame, text=tag_hints, bg=t["bg"], fg=t["muted"],
            font=(platform_font(), 8), anchor="w",
        )
        self.tag_hints_label.pack(fill="x", pady=(2, 0))

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
        smart_tags, _ = merge_tags(self.config)
        matches = [
            (name, emoji) for name, emoji in smart_tags.items()
            if name.startswith(fragment)
        ]

        # Hide if no matches, or if fragment is already a complete exact tag name
        if not matches or (len(matches) == 1 and matches[0][0] == fragment):
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
        should_continue = app_runtime.drain_app_queue(
            self.queue,
            on_show=self.show_window,
            on_browse=self._open_browse,
            on_settings=self._open_settings,
            on_quit=self.root.quit,
        )
        if should_continue:
            self.root.after(100, self.poll_queue)

    def _open_browse(self):
        """Open the Browse Notes window."""
        from cogstash.ui.browse import BrowseWindow
        smart_tags, tag_colors = merge_tags(self.config)
        browse_window = BrowseWindow(self.root, self.config, smart_tags, tag_colors)
        self._browse_windows.append(browse_window)

    def _open_settings(self):
        """Open the Settings window (singleton — reuse if already open)."""
        if hasattr(self, "_settings_win") and self._settings_win and self._settings_win.win.winfo_exists():
            self._settings_win.win.lift()
            self._settings_win.win.focus_force()
            return
        from cogstash.ui.settings import SettingsWindow
        self._settings_win = SettingsWindow(
            self.root,
            self.config,
            self.config_path,
            on_config_changed=self._on_config_changed,
            hotkey_warning=self.hotkey_warning,
        )

    def _on_config_changed(self, config: CogStashConfig) -> None:
        """Apply config changes to already-open windows."""
        self.config = config
        self.theme = THEMES[config.theme]
        self.win_size = WINDOW_SIZES[config.window_size]
        self.root.configure(bg=self.theme["bg"])
        self.frame.configure(bg=self.theme["bg"])
        self.title_label.configure(bg=self.theme["bg"], fg=self.theme["fg"])
        self.text.configure(
            width=self.win_size["width"] // 7,
            height=max(int(self.text.cget("height")), self.win_size["lines"]),
            bg=self.theme["entry_bg"],
            fg=self.theme["fg"],
            insertbackground=self.theme["fg"],
        )
        self.hint_label.configure(bg=self.theme["bg"], fg=self.theme["muted"])
        self.tag_hints_label.configure(bg=self.theme["bg"], fg=self.theme["muted"])
        self._prune_browse_windows()
        smart_tags, tag_colors = merge_tags(config)
        for browse_window in self._browse_windows:
            browse_window.apply_config(config, smart_tags, tag_colors)

    def _prune_browse_windows(self) -> None:
        """Drop closed browse windows from tracking."""
        self._browse_windows = [
            browse_window for browse_window in self._browse_windows
            if browse_window.window.winfo_exists()
        ]

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
        smart_tags, _ = merge_tags(self.config)
        assert self.config.output_file is not None, "output_file should be set by __post_init__"
        return append_note_to_file(text, self.config.output_file, smart_tags)


def _reconfigure_logger(log_file: Path) -> None:
    """Replace active log handlers so the UI app writes to the configured log file."""
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
    logger.addHandler(_create_log_handler(log_file))


def _bootstrap_app_config() -> tuple[Path, CogStashConfig]:
    """Load config and reconfigure logging for the current session."""
    config_path = get_default_config_path()
    config = load_config(config_path)
    assert config.log_file is not None, "log_file should be set by __post_init__"
    _reconfigure_logger(config.log_file)
    return config_path, config


def _show_already_running_dialog() -> None:
    """Tell the user another GUI instance is already active."""
    try:
        messagebox.showinfo("CogStash", "CogStash is already running in the system tray.")
    except tk.TclError:
        pass


def _run_startup_dialog_flow(root: tk.Tk, config: CogStashConfig, config_path: Path) -> CogStashConfig:
    """Run first-launch and version-based dialogs, returning the active config afterward."""
    if config.last_seen_version == "":
        from cogstash.ui.settings import WizardWindow

        wizard = WizardWindow(root, config, config_path)
        root.wait_window(wizard.win)
        return load_config(config_path)

    from cogstash import __version__
    from cogstash.ui.install_state import should_show_installer_welcome

    if should_show_installer_welcome(config, __version__):
        from cogstash.ui.settings import InstallerWelcomeDialog

        InstallerWelcomeDialog(root, config, config_path, __version__)
        config.last_seen_version = __version__
        config.last_seen_installer_version = __version__
        save_config(config, config_path)
    elif config.last_seen_version != __version__:
        from cogstash.ui.settings import WhatsNewDialog

        WhatsNewDialog(root, config, config_path, __version__)
        config.last_seen_version = __version__
        save_config(config, config_path)
    return config


def _announce_startup(config: CogStashConfig, safe_print: Any) -> None:
    """Print the standard startup status lines."""
    safe_print(f"CogStash is running. ({config.hotkey} to capture · Ctrl+C to quit)")
    safe_print(f"Notes → {config.output_file}")

def _start_runtime_integrations(
    app: CogStash,
    config: CogStashConfig,
    safe_print: Any,
) -> app_runtime.AppRuntimeHandles:
    """Start tray/hotkey integrations and surface the existing warning flow on failure."""
    runtime_handles = app_runtime.start_runtime(app.queue, config, themes=THEMES)

    try:
        runtime_handles.hotkey_listener = app_runtime.start_hotkey_listener(app.queue, config.hotkey)
    except Exception:
        app.hotkey_warning = _build_hotkey_failure_warning(config)
        logger.error("Failed to register global hotkey %s", config.hotkey, exc_info=True)
        safe_print(f"ERROR: Could not register hotkey {config.hotkey}. See {config.log_file} for details.")
        try:
            messagebox.showwarning("CogStash Hotkey Warning", app.hotkey_warning)
        except tk.TclError:
            pass
    return runtime_handles


def _shutdown_app(runtime_handles: app_runtime.AppRuntimeHandles, instance_guard: Any) -> None:
    """Stop background resources before the process exits."""
    app_runtime.shutdown_runtime(runtime_handles)
    instance_guard.close()


def main():
    from cogstash.core.output import safe_print
    from cogstash.ui.windows import WINDOWS_MUTEX_NAME, acquire_single_instance

    config_path, config = _bootstrap_app_config()

    instance_guard = acquire_single_instance(WINDOWS_MUTEX_NAME)
    if instance_guard is None:
        logger.warning("CogStash is already running; refusing to launch a second GUI instance.")
        _show_already_running_dialog()
        return

    configure_dpi()

    root = tk.Tk()
    config = _run_startup_dialog_flow(root, config, config_path)
    _announce_startup(config, safe_print)

    app = CogStash(root, config, config_path)

    runtime_handles = _start_runtime_integrations(app, config, safe_print)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        safe_print("\nCogStash stopped.")
    finally:
        _shutdown_app(runtime_handles, instance_guard)


if __name__ == "__main__":
    main()
