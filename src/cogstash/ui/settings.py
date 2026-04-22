"""Settings UI — wizard, settings window, and What's New dialog."""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from pynput import keyboard

from cogstash.core import DEFAULT_SMART_TAGS, CogStashConfig, merge_tags, save_config
from cogstash.ui.app import (
    THEMES,
    WINDOW_SIZES,
    logger,
    platform_font,
)
from cogstash.ui.install_state import get_startup_shortcut_path


def validate_hotkey(value: str) -> tuple[bool, str | None]:
    """Validate a pynput GlobalHotKeys hotkey string."""
    hotkey = value.strip()
    if not hotkey:
        return False, "Hotkey is required."
    try:
        keyboard.HotKey.parse(hotkey)
    except Exception:
        return False, (
            "Enter a valid global hotkey like <ctrl>+<shift>+<space> or "
            "<ctrl>+<alt>+h."
        )
    return True, None


def set_launch_at_startup(enable: bool) -> None:
    """Enable or disable launch at system startup (Windows only)."""
    if sys.platform != "win32":
        return
    shortcut_path = get_startup_shortcut_path()
    if enable:
        exe = sys.executable
        if getattr(sys, "frozen", False):
            exe = sys.argv[0]
            content = f'@echo off\nstart "" "{exe}"\n'
        else:
            content = f'@echo off\nstart "" "{exe}" -m cogstash.ui\n'
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


class SettingsWindow:
    """Tab-based settings window accessible from the tray menu."""

    TAB_NAMES = ["General", "Appearance", "Tags", "About"]

    def __init__(
        self,
        parent: tk.Tk,
        config: CogStashConfig,
        config_path: Path,
        on_config_changed=None,
        hotkey_warning: str | None = None,
    ):
        self.parent = parent
        self.config = config
        self.config_path = config_path
        self.on_config_changed = on_config_changed
        self.hotkey_warning = hotkey_warning
        self.win = tk.Toplevel(parent)
        self.win.title("CogStash Settings")
        window_height = 520 if hotkey_warning else 450
        self.win.geometry(f"500x{window_height}")
        self.win.resizable(False, False)
        self.theme = THEMES[config.theme]
        self.win.configure(bg=self.theme["bg"])
        if parent.state() != "withdrawn":
            self.win.transient(parent)
        self.win.lift()
        self.win.focus_force()
        self.win.bind("<Escape>", lambda e: self.win.destroy())

        self._active_tab = 0
        self._build_ui()

    def _build_ui(self) -> None:
        """Build or rebuild the window UI from the current config."""
        self._build_tab_bar()
        self.content_frame = tk.Frame(self.win, bg=self.theme["bg"])
        self.content_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self._build_general_tab()
        self._build_appearance_tab()
        self._build_tags_tab()
        self._build_about_tab()

        self._show_tab(self._active_tab)

    def _rebuild_ui(self) -> None:
        """Rebuild the settings window after theme changes."""
        self.theme = THEMES[self.config.theme]
        self.win.configure(bg=self.theme["bg"])
        for child in self.win.winfo_children():
            child.destroy()
        self._build_ui()

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

        # Section: Hotkey
        tk.Label(frame, text="Hotkey", bg=t["bg"], fg=t["fg"],
                 font=(platform_font(), 11, "bold")).pack(anchor="w", pady=(8, 4))
        self.hotkey_var = tk.StringVar(value=self.config.hotkey)
        hotkey_frame = tk.Frame(frame, bg=t["bg"])
        hotkey_frame.pack(fill="x", padx=(8, 0))
        tk.Entry(
            hotkey_frame,
            textvariable=self.hotkey_var,
            bg=t["entry_bg"],
            fg=t["fg"],
            insertbackground=t["fg"],
            relief="flat",
            font=(platform_font(), 10),
        ).pack(side="left", fill="x", expand=True, ipady=4)
        tk.Button(
            hotkey_frame,
            text="Test Hotkey",
            command=self._test_hotkey,
            bg=t["entry_bg"],
            fg=t["fg"],
            relief="flat",
            font=(platform_font(), 9),
            cursor="hand2",
        ).pack(side="left", padx=(8, 0))
        tk.Label(
            frame,
            text="Use pynput format, for example <ctrl>+<shift>+<space>.",
            bg=t["bg"],
            fg=t["muted"],
            font=(platform_font(), 8),
        ).pack(anchor="w", padx=(8, 0), pady=(2, 0))
        if self.hotkey_warning:
            warning_frame = tk.Frame(
                frame,
                bg=t["entry_bg"],
                highlightbackground=t["error"],
                highlightcolor=t["error"],
                highlightthickness=1,
            )
            warning_frame.pack(fill="x", padx=(8, 0), pady=(10, 0))
            tk.Label(
                warning_frame,
                text="⚠ Hotkey Warning",
                bg=t["entry_bg"],
                fg=t["error"],
                font=(platform_font(), 10, "bold"),
            ).pack(anchor="w", padx=10, pady=(10, 4))
            tk.Label(
                warning_frame,
                text=self.hotkey_warning,
                bg=t["entry_bg"],
                fg=t["fg"],
                justify="left",
                wraplength=420,
                font=(platform_font(), 9),
            ).pack(anchor="w", padx=10, pady=(0, 10))

        # Section: Notes File
        tk.Label(frame, text="Notes File", bg=t["bg"], fg=t["fg"],
                 font=(platform_font(), 11, "bold")).pack(anchor="w", pady=(16, 4))
        notes_frame = tk.Frame(frame, bg=t["bg"])
        notes_frame.pack(fill="x", padx=(8, 0))
        self.notes_file_var = tk.StringVar(value=str(self.config.output_file))
        tk.Entry(notes_frame, textvariable=self.notes_file_var, bg=t["entry_bg"], fg=t["fg"],
                 insertbackground=t["fg"], relief="flat", font=(platform_font(), 10)).pack(
                     side="left", fill="x", expand=True, ipady=4)
        tk.Button(notes_frame, text="Browse", command=self._browse_notes_file,
                  bg=t["entry_bg"], fg=t["fg"], relief="flat",
                  font=(platform_font(), 9)).pack(side="left", padx=(8, 0))

        # Section: Launch at Startup
        tk.Label(frame, text="Startup", bg=t["bg"], fg=t["fg"],
                 font=(platform_font(), 11, "bold")).pack(anchor="w", pady=(16, 4))
        # Reflect actual on-disk state so installer-created scripts are visible immediately.
        if sys.platform == "win32":
            from cogstash.ui.install_state import startup_script_exists  # lazy — keeps install_state optional

            startup_state = startup_script_exists()
        else:
            startup_state = self.config.launch_at_startup
        if self.config.launch_at_startup != startup_state:
            self.config.launch_at_startup = startup_state
            save_config(self.config, self.config_path)
        self.launch_var = tk.BooleanVar(value=startup_state)
        tk.Checkbutton(frame, text="Launch CogStash at system startup",
                       variable=self.launch_var, bg=t["bg"], fg=t["fg"],
                       selectcolor=t["entry_bg"], activebackground=t["bg"],
                       activeforeground=t["fg"],
                       font=(platform_font(), 10)).pack(anchor="w", padx=(8, 0))

        # Save button
        tk.Button(frame, text="Save", command=self._save_general,
                  bg=t["accent"], fg=t["bg"], relief="flat",
                  font=(platform_font(), 10, "bold"), padx=24, pady=6,
                  cursor="hand2").pack(anchor="e", pady=(24, 0))

    def _browse_notes_file(self):
        """Open file dialog to select notes file."""
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            parent=self.win, defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("Text", "*.txt"), ("All", "*.*")],
            title="Choose notes file location",
        )
        if path:
            self.notes_file_var.set(path)

    def _save_general(self):
        """Save General tab settings to config."""
        hotkey = self.hotkey_var.get().strip()
        is_valid, error = validate_hotkey(hotkey)
        if not is_valid:
            messagebox.showerror("Invalid Hotkey", error, parent=self.win)
            return
        self.config.hotkey = hotkey
        self.config.output_file = Path(self.notes_file_var.get()).expanduser()
        new_launch = self.launch_var.get()
        if new_launch != self.config.launch_at_startup:
            set_launch_at_startup(new_launch)
        self.config.launch_at_startup = new_launch
        save_config(self.config, self.config_path)
        self._flash_saved()
        if self.on_config_changed is not None:
            self.on_config_changed(self.config)

    def _test_hotkey(self) -> None:
        """Validate the currently entered hotkey and explain how it applies."""
        hotkey = self.hotkey_var.get().strip()
        is_valid, error = validate_hotkey(hotkey)
        if not is_valid:
            messagebox.showerror("Invalid Hotkey", error, parent=self.win)
            return
        messagebox.showinfo(
            "Hotkey Looks Valid",
            (
                f"Hotkey syntax looks valid: {hotkey}\n\n"
                "Save your changes to use it for future launches. If CogStash is already "
                "running with a different global hotkey, restart the app to rebind capture."
            ),
            parent=self.win,
        )

    def _flash_saved(self):
        """Briefly show a 'Saved' indicator."""
        lbl = tk.Label(self.win, text="✓ Saved", bg=self.theme["accent"], fg=self.theme["bg"],
                       font=(platform_font(), 9))
        lbl.place(relx=0.5, rely=0.95, anchor="center")
        self.win.after(1500, lbl.destroy)

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
        self._rebuild_ui()
        self._flash_saved()
        if self.on_config_changed is not None:
            self.on_config_changed(self.config)

    def _build_appearance_tab(self):
        """Build the Appearance settings tab with theme picker and window size."""
        t = self.theme
        frame = tk.Frame(self.content_frame, bg=t["bg"])
        self.tab_frames.append(frame)

        # Theme section
        tk.Label(frame, text="Theme", bg=t["bg"], fg=t["fg"],
                 font=(platform_font(), 11, "bold")).pack(anchor="w", pady=(8, 8))
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
        tk.Label(frame, text="Window Size", bg=t["bg"], fg=t["fg"],
                 font=(platform_font(), 11, "bold")).pack(anchor="w", pady=(20, 8))
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

        # Info label about live updates
        tk.Label(frame, text="Theme updates immediately. Window size applies on the next capture.",
                 bg=t["bg"], fg=t["muted"], font=(platform_font(), 8)).pack(anchor="w", padx=(8, 0), pady=(12, 0))

        # Save button
        tk.Button(frame, text="Save", command=self._save_appearance,
                  bg=t["accent"], fg=t["bg"], relief="flat",
                  font=(platform_font(), 10, "bold"), padx=24, pady=6,
                  cursor="hand2").pack(anchor="e", pady=(12, 0))

    def _build_tags_tab(self):
        """Build the Tags management tab."""
        t = self.theme
        frame = tk.Frame(self.content_frame, bg=t["bg"])
        self.tab_frames.append(frame)

        tk.Label(frame, text="Tags", bg=t["bg"], fg=t["fg"],
                 font=(platform_font(), 11, "bold")).pack(anchor="w", pady=(8, 8))

        # Scrollable tag list
        self.tag_list_frame = tk.Frame(frame, bg=t["bg"])
        self.tag_list_frame.pack(fill="both", expand=True, padx=(8, 0))

        self._render_tags()

        # Add tag button
        add_frame = tk.Frame(frame, bg=t["bg"])
        add_frame.pack(fill="x", pady=(8, 0))
        tk.Button(add_frame, text="+ Add Custom Tag", command=self._show_add_tag_form,
                  bg=t["entry_bg"], fg=t["fg"], relief="flat",
                  font=(platform_font(), 9), cursor="hand2").pack(anchor="w")

        # Add tag form (hidden initially)
        self._add_tag_frame = tk.Frame(frame, bg=t["entry_bg"])
        self._tag_name_var = tk.StringVar()
        self._tag_emoji_var = tk.StringVar()
        self._tag_color_var = tk.StringVar(value="#ffffff")
        self._tag_error_label: tk.Label | None = None

        tk.Label(self._add_tag_frame, text="Name:", bg=t["entry_bg"], fg=t["fg"],
                 font=(platform_font(), 9)).grid(row=0, column=0, padx=4, pady=2, sticky="w")
        self._tag_name_entry = tk.Entry(
            self._add_tag_frame,
            textvariable=self._tag_name_var,
            bg=t["bg"],
            fg=t["fg"],
            insertbackground=t["fg"],
            relief="flat",
            font=(platform_font(), 9),
            width=12,
        )
        self._tag_name_entry.grid(row=0, column=1, padx=4, pady=2)
        tk.Label(self._add_tag_frame, text="Emoji:", bg=t["entry_bg"], fg=t["fg"],
                 font=(platform_font(), 9)).grid(row=0, column=2, padx=4, pady=2, sticky="w")
        self._tag_emoji_entry = tk.Entry(
            self._add_tag_frame,
            textvariable=self._tag_emoji_var,
            bg=t["bg"],
            fg=t["fg"],
            insertbackground=t["fg"],
            relief="flat",
            font=(platform_font(), 9),
            width=4,
        )
        self._tag_emoji_entry.grid(row=0, column=3, padx=4, pady=2)
        tk.Label(self._add_tag_frame, text="Color:", bg=t["entry_bg"], fg=t["fg"],
                 font=(platform_font(), 9)).grid(row=0, column=4, padx=4, pady=2, sticky="w")
        self._tag_color_entry = tk.Entry(
            self._add_tag_frame,
            textvariable=self._tag_color_var,
            bg=t["bg"],
            fg=t["fg"],
            insertbackground=t["fg"],
            relief="flat",
            font=(platform_font(), 9),
            width=8,
        )
        self._tag_color_entry.grid(row=0, column=5, padx=4, pady=2)
        tk.Button(self._add_tag_frame, text="Add", command=self._add_tag,
                  bg=t["accent"], fg=t["bg"], relief="flat",
                  font=(platform_font(), 9)).grid(row=0, column=6, padx=8, pady=2)
        for entry in (self._tag_name_entry, self._tag_emoji_entry, self._tag_color_entry):
            entry.bind("<Return>", lambda e: self._add_tag())

        # Save button
        tk.Button(frame, text="Save", command=self._save_tags,
                  bg=t["accent"], fg=t["bg"], relief="flat",
                  font=(platform_font(), 10, "bold"), padx=24, pady=6,
                  cursor="hand2").pack(anchor="e", pady=(8, 0))

    def _build_about_tab(self):
        """Build the About tab with version and links."""
        t = self.theme
        frame = tk.Frame(self.content_frame, bg=t["bg"])
        self.tab_frames.append(frame)

        # Version
        from cogstash import __version__
        self.version_label = tk.Label(frame, text=f"CogStash v{__version__}", bg=t["bg"], fg=t["fg"],
                                      font=(platform_font(), 14, "bold"))
        self.version_label.pack(pady=(24, 4))
        tk.Label(frame, text="A global hotkey brain dump — press, type, gone.",
                 bg=t["bg"], fg=t["muted"], font=(platform_font(), 10)).pack(pady=(0, 24))

        # Links
        links = [
            ("GitHub Repository", "https://github.com/abdul219428/CogStash"),
            ("Open Notes File", str(self.config.output_file)),
            ("Open Config File", str(self.config_path)),
        ]
        for text, target in links:
            lbl = tk.Label(frame, text=text, bg=t["bg"], fg=t["accent"],
                           font=(platform_font(), 10), cursor="hand2")
            lbl.pack(pady=2)
            lbl.bind("<Button-1>", lambda e, t=target: self._open_link(t))

        # Credits
        tk.Label(frame, text="Built with Python, tkinter, pynput, pystray, Pillow",
                 bg=t["bg"], fg=t["muted"], font=(platform_font(), 9)).pack(pady=(24, 0))

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

    def _render_tags(self):
        """Render the tag list in the tags tab."""
        for child in self.tag_list_frame.winfo_children():
            child.destroy()
        t = self.theme
        smart_tags, tag_colors = merge_tags(self.config)

        for name, emoji in DEFAULT_SMART_TAGS.items():
            row = tk.Frame(self.tag_list_frame, bg=t["bg"])
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"  {emoji}  #{name}", bg=t["bg"], fg=t["fg"],
                     font=(platform_font(), 10), anchor="w").pack(side="left")
            tk.Label(row, text="Built-in", bg=t["entry_bg"], fg=t["muted"],
                     font=(platform_font(), 8), padx=6, pady=1).pack(side="right")

        if self.config.tags:
            for name, props in self.config.tags.items():
                row = tk.Frame(self.tag_list_frame, bg=t["bg"])
                row.pack(fill="x", pady=2)
                tk.Label(row, text=f"  {props['emoji']}  #{name}", bg=t["bg"], fg=t["fg"],
                         font=(platform_font(), 10), anchor="w").pack(side="left")
                color_swatch = tk.Frame(row, bg=props["color"], width=14, height=14)
                color_swatch.pack(side="right", padx=(0, 4))
                color_swatch.pack_propagate(False)
                tk.Button(row, text="✕", command=lambda n=name: self._remove_tag(n),
                          bg=t["bg"], fg=t["error"], relief="flat",
                          font=(platform_font(), 9), cursor="hand2").pack(side="right")

    def _show_add_tag_form(self):
        """Show the add-tag form."""
        self._add_tag_frame.pack(fill="x", padx=(8, 0), pady=(4, 0))
        self._tag_name_entry.focus_set()

    def _add_tag(self):
        """Add a new custom tag from the form fields."""
        import re
        name = self._tag_name_var.get().strip().lower()
        emoji = self._tag_emoji_var.get().strip()
        color = self._tag_color_var.get().strip()
        if self._tag_error_label is not None and self._tag_error_label.winfo_exists():
            self._tag_error_label.destroy()
        if not name or not emoji or not re.match(r"^#[0-9a-fA-F]{6}$", color):
            self._tag_error_label = tk.Label(
                self._add_tag_frame,
                text="Invalid tag input. Name, emoji, and #RRGGBB color are required.",
                bg=self.theme["entry_bg"],
                fg=self.theme["error"],
                font=(platform_font(), 8),
            )
            self._tag_error_label.grid(row=1, column=0, columnspan=7, padx=4, pady=(2, 0), sticky="w")
            return
        if self.config.tags is None:
            self.config.tags = {}
        self.config.tags[name] = {"emoji": emoji, "color": color}
        self._tag_name_var.set("")
        self._tag_emoji_var.set("")
        self._tag_color_var.set("#ffffff")
        self._add_tag_frame.pack_forget()
        self._tag_error_label = None
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
        if self.on_config_changed is not None:
            self.on_config_changed(self.config)


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
        self.win.protocol("WM_DELETE_WINDOW", self._close)
        self.win.focus_force()
        self.win.bind("<Escape>", lambda e: self._close())

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

        self.notes_file_var = tk.StringVar(value=str(config.output_file))
        self.hotkey_var = tk.StringVar(value=config.hotkey)
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
        for child in self.content.winfo_children():
            child.destroy()
        for child in self.btn_frame.winfo_children():
            child.destroy()
        for i, d in enumerate(self._dots):
            d.configure(bg=self.theme["accent"] if i == idx else self.theme["muted"])
        self._pages[idx]()
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
        tk.Label(self.content, text="Choose your capture hotkey", bg=t["bg"], fg=t["fg"],
                 font=(platform_font(), 11)).pack(anchor="w", pady=(16, 8))
        hotkey_frame = tk.Frame(self.content, bg=t["bg"])
        hotkey_frame.pack(fill="x")
        tk.Entry(
            hotkey_frame,
            textvariable=self.hotkey_var,
            bg=t["entry_bg"],
            fg=t["fg"],
            insertbackground=t["fg"],
            relief="flat",
            font=(platform_font(), 10),
        ).pack(side="left", fill="x", expand=True, ipady=6)
        tk.Button(
            hotkey_frame,
            text="Test Hotkey",
            command=self._test_hotkey,
            bg=t["entry_bg"],
            fg=t["fg"],
            relief="flat",
            font=(platform_font(), 9),
        ).pack(side="left", padx=(8, 0))
        tk.Label(
            self.content,
            text="Use pynput format, for example <ctrl>+<shift>+<space>.",
            bg=t["bg"],
            fg=t["muted"],
            font=(platform_font(), 9),
        ).pack(anchor="w", pady=(8, 0))

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
            hl = colors["accent"] if name == self.selected_theme.get() else colors["bg"]
            swatch = tk.Frame(theme_grid, bg=colors["bg"], highlightthickness=2,
                              highlightbackground=hl, cursor="hand2", width=85, height=65)
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
            ("⚡", "Capture", f"Press {self.hotkey_var.get()} anywhere.\nType your thought, press Enter."),
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
            ("Hotkey", self.hotkey_var.get()),
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
        from cogstash.ui.install_state import is_installed_windows_run
        hotkey = self.hotkey_var.get().strip()
        is_valid, error = validate_hotkey(hotkey)
        if not is_valid:
            messagebox.showerror("Invalid Hotkey", error, parent=self.win)
            return
        self.config.hotkey = hotkey
        self.config.output_file = Path(self.notes_file_var.get()).expanduser()
        self.config.theme = self.selected_theme.get()
        self.config.window_size = self.selected_size.get()
        self.config.last_seen_version = __version__
        if is_installed_windows_run():
            self.config.last_seen_installer_version = __version__
        save_config(self.config, self.config_path)
        self._close()

    def _test_hotkey(self) -> None:
        """Validate the currently entered wizard hotkey and explain next steps."""
        hotkey = self.hotkey_var.get().strip()
        is_valid, error = validate_hotkey(hotkey)
        if not is_valid:
            messagebox.showerror("Invalid Hotkey", error, parent=self.win)
            return
        messagebox.showinfo(
            "Hotkey Looks Valid",
            (
                f"Hotkey syntax looks valid: {hotkey}\n\n"
                "Finish setup to save it. The new hotkey will be used when CogStash starts."
            ),
            parent=self.win,
        )

    def _close(self):
        """Close the wizard and release its modal grab."""
        try:
            self.win.grab_release()
        except tk.TclError:
            pass
        self.win.destroy()


WHATS_NEW: dict[str, dict[str, list[tuple[str, str]]]] = {
    "0.2.0": {
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
    "new": "#4ade80",
    "improved": "#60a5fa",
    "fixed": "#fb923c",
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
        self.win.bind("<Escape>", lambda e: self.win.destroy())

        tk.Label(self.win, text="What's New in CogStash", bg=t["bg"], fg=t["fg"],
                 font=(platform_font(), 14, "bold")).pack(pady=(20, 4))
        tk.Label(self.win, text=f"v{version}", bg=t["bg"], fg=t["muted"],
                 font=(platform_font(), 10)).pack(pady=(0, 16))

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


class InstallerWelcomeDialog:
    """Lightweight welcome dialog shown once after an installed-Windows upgrade with existing config.

    Informs the user they are now running the installed CogStash, highlights
    installer-specific features (startup at boot, CLI/PATH), and does NOT
    force the full first-run wizard.
    """

    def __init__(self, parent: tk.Tk, config: CogStashConfig, config_path: Path, version: str):
        self.parent = parent
        self.config = config
        self.config_path = config_path
        self.version = version
        self.theme = THEMES[config.theme]
        t = self.theme

        self.win = tk.Toplevel(parent)
        self.win.title("CogStash Updated")
        self.win.geometry("420x340")
        self.win.resizable(False, False)
        self.win.configure(bg=t["bg"])
        self.win.transient(parent)
        self.win.focus_force()
        self.win.bind("<Escape>", lambda e: self.win.destroy())

        tk.Label(
            self.win, text="⚡ CogStash Updated", bg=t["bg"], fg=t["fg"],
            font=(platform_font(), 14, "bold"),
        ).pack(pady=(20, 4))
        tk.Label(
            self.win, text=f"v{version} — installed edition",
            bg=t["bg"], fg=t["muted"], font=(platform_font(), 10),
        ).pack(pady=(0, 16))

        info_frame = tk.Frame(self.win, bg=t["entry_bg"], padx=16, pady=12)
        info_frame.pack(fill="x", padx=24)

        bullets = [
            ("⚡", "Hotkey capture is ready — press it anywhere"),
            ("🖥️", "Startup at boot — optional during installation or later in Settings"),
            ("💻", "CLI available if you chose the PATH option during installation"),
        ]
        for emoji, text in bullets:
            row = tk.Frame(info_frame, bg=t["entry_bg"])
            row.pack(fill="x", pady=3)
            tk.Label(row, text=emoji, bg=t["entry_bg"], fg=t["fg"],
                     font=(platform_font(), 11), width=3).pack(side="left")
            tk.Label(row, text=text, bg=t["entry_bg"], fg=t["fg"],
                     font=(platform_font(), 9), anchor="w").pack(side="left", fill="x", expand=True)

        tk.Label(
            self.win, text="Startup can be changed in Settings → General. The PATH option is available during installation.",
            bg=t["bg"], fg=t["muted"], font=(platform_font(), 8), wraplength=370,
        ).pack(pady=(12, 0), padx=24)

        tk.Button(
            self.win, text="Got it", command=self.win.destroy,
            bg=t["accent"], fg=t["bg"], relief="flat",
            font=(platform_font(), 10, "bold"), padx=24, pady=6, cursor="hand2",
        ).pack(pady=(16, 20))
