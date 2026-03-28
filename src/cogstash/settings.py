"""Settings UI — wizard, settings window, and What's New dialog."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

from cogstash.app import (
    THEMES,
    WINDOW_SIZES,
    CogStashConfig,
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
        """Placeholder — implemented in Task 5."""
        frame = tk.Frame(self.content_frame, bg=self.theme["bg"])
        self.tab_frames.append(frame)

    def _build_about_tab(self):
        """Placeholder — implemented in Task 6."""
        frame = tk.Frame(self.content_frame, bg=self.theme["bg"])
        self.tab_frames.append(frame)


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
