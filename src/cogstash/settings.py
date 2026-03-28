"""Settings UI — wizard, settings window, and What's New dialog."""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path

from cogstash.app import (
    DEFAULT_SMART_TAGS,
    THEMES,
    WINDOW_SIZES,
    CogStashConfig,
    merge_tags,
    platform_font,
    save_config,
)


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

        # Section: Hotkey
        tk.Label(frame, text="Hotkey", bg=t["bg"], fg=t["fg"],
                 font=(platform_font(), 11, "bold")).pack(anchor="w", pady=(8, 4))
        tk.Label(frame, text=self.config.hotkey, bg=t["entry_bg"], fg=t["fg"],
                 font=(platform_font(), 10), padx=8, pady=4).pack(anchor="w", padx=(8, 0))
        tk.Label(frame, text="Edit in ~/.cogstash.json to change", bg=t["bg"], fg=t["muted"],
                 font=(platform_font(), 8)).pack(anchor="w", padx=(8, 0), pady=(2, 0))

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
        self.launch_var = tk.BooleanVar(value=self.config.launch_at_startup)
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
        self.config.output_file = Path(self.notes_file_var.get()).expanduser()
        self.config.launch_at_startup = self.launch_var.get()
        save_config(self.config, self.config_path)
        self._flash_saved()

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
        self._flash_saved()

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

        # Info label about restart
        tk.Label(frame, text="Theme and window size changes take effect after restart.",
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

        tk.Label(self._add_tag_frame, text="Name:", bg=t["entry_bg"], fg=t["fg"],
                 font=(platform_font(), 9)).grid(row=0, column=0, padx=4, pady=2, sticky="w")
        tk.Entry(self._add_tag_frame, textvariable=self._tag_name_var, bg=t["bg"], fg=t["fg"],
                 insertbackground=t["fg"], relief="flat", font=(platform_font(), 9),
                 width=12).grid(row=0, column=1, padx=4, pady=2)
        tk.Label(self._add_tag_frame, text="Emoji:", bg=t["entry_bg"], fg=t["fg"],
                 font=(platform_font(), 9)).grid(row=0, column=2, padx=4, pady=2, sticky="w")
        tk.Entry(self._add_tag_frame, textvariable=self._tag_emoji_var, bg=t["bg"], fg=t["fg"],
                 insertbackground=t["fg"], relief="flat", font=(platform_font(), 9),
                 width=4).grid(row=0, column=3, padx=4, pady=2)
        tk.Label(self._add_tag_frame, text="Color:", bg=t["entry_bg"], fg=t["fg"],
                 font=(platform_font(), 9)).grid(row=0, column=4, padx=4, pady=2, sticky="w")
        tk.Entry(self._add_tag_frame, textvariable=self._tag_color_var, bg=t["bg"], fg=t["fg"],
                 insertbackground=t["fg"], relief="flat", font=(platform_font(), 9),
                 width=8).grid(row=0, column=5, padx=4, pady=2)
        tk.Button(self._add_tag_frame, text="Add", command=self._add_tag,
                  bg=t["accent"], fg=t["bg"], relief="flat",
                  font=(platform_font(), 9)).grid(row=0, column=6, padx=8, pady=2)

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
