"""cogstash_browse.py — Browse Window for viewing and filtering past notes.

Card-view UI with search, tag filtering, and mark-done for #todo items.
Opened from the system tray icon. Uses cogstash_search for all data operations.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from datetime import datetime, timedelta
from pathlib import Path

from cogstash import THEMES, DEFAULT_SMART_TAGS, CogStashConfig, platform_font
from cogstash_search import parse_notes, search_notes, filter_by_tag, mark_done, DEFAULT_TAG_COLORS, Note


class BrowseWindow:
    """Toplevel window for browsing and filtering notes."""

    def __init__(self, root: tk.Tk, config: CogStashConfig,
                 smart_tags: dict[str, str] | None = None,
                 tag_colors: dict[str, str] | None = None):
        self.root = root
        self.config = config
        self.theme = THEMES[config.theme]
        self.smart_tags = smart_tags or dict(DEFAULT_SMART_TAGS)
        self.tag_colors = tag_colors or dict(DEFAULT_TAG_COLORS)
        self._all_notes: list[Note] = []
        self._visible_cards: list[Note] = []
        self._active_tag: str | None = None
        self._card_frames: list[tk.Frame] = []

        self.window = tk.Toplevel(root)
        self.window.title("CogStash — Browse Notes")
        self.window.configure(bg=self.theme["bg"])
        self.window.geometry("480x520")
        self.window.minsize(360, 300)

        self.search_var = tk.StringVar()
        self._build_ui()
        self._load_notes()

        self.window.bind("<Escape>", lambda e: self.window.destroy())

    def _build_ui(self):
        t = self.theme
        fnt = platform_font()

        # Top bar frame
        top = tk.Frame(self.window, bg=t["entry_bg"], padx=8, pady=6)
        top.pack(fill="x")

        # Search entry
        self.search_entry = tk.Entry(
            top, textvariable=self.search_var, bg=t["bg"], fg=t["fg"],
            insertbackground=t["fg"], font=(fnt, 11),
            relief="flat", bd=0, highlightthickness=1,
            highlightbackground=t["muted"], highlightcolor=t["accent"],
        )
        self.search_entry.pack(fill="x", pady=(0, 6))
        self.search_entry.insert(0, "")
        self.search_var.trace_add("write", lambda *_: self._schedule_search())

        # Tag filter pills
        pills_frame = tk.Frame(top, bg=t["entry_bg"])
        pills_frame.pack(fill="x")

        self._pill_buttons: dict[str | None, tk.Label] = {}
        # "All" pill
        all_pill = tk.Label(
            pills_frame, text="All", bg=t["accent"], fg=t["bg"],
            font=(fnt, 9, "bold"), padx=8, pady=2, cursor="hand2",
        )
        all_pill.pack(side="left", padx=(0, 4))
        all_pill.bind("<Button-1>", lambda e: self._on_tag_filter(None))
        self._pill_buttons[None] = all_pill

        for tag, emoji in self.smart_tags.items():
            color = self.tag_colors.get(tag, t["muted"])
            pill = tk.Label(
                pills_frame, text=f"{emoji} {tag}", bg=t["bg"], fg=t["fg"],
                font=(fnt, 9), padx=6, pady=2, cursor="hand2",
                highlightthickness=1, highlightbackground=t["muted"],
            )
            pill.pack(side="left", padx=(0, 4))
            pill.bind("<Button-1>", lambda e, tg=tag: self._on_tag_filter(tg))
            self._pill_buttons[tag] = pill

        # Scrollable card area
        container = tk.Frame(self.window, bg=t["bg"])
        container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(container, bg=t["bg"], highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.cards_frame = tk.Frame(self.canvas, bg=t["bg"])

        self.cards_frame.bind(
            "<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas_window = self.canvas.create_window((0, 0), window=self.cards_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Mousewheel scrolling (bound to canvas and cards_frame, not globally)
        def _on_mousewheel(e):
            self.canvas.yview_scroll(-1 * (e.delta // 120), "units")
        self.canvas.bind("<MouseWheel>", _on_mousewheel)
        self.cards_frame.bind("<MouseWheel>", _on_mousewheel)
        self._on_mousewheel = _on_mousewheel  # stored for binding on card children

        # Footer
        self.footer = tk.Label(
            self.window, bg=t["entry_bg"], fg=t["muted"],
            font=(fnt, 9), anchor="center", pady=4,
        )
        self.footer.pack(fill="x")

    def _on_canvas_resize(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _load_notes(self):
        self._all_notes = parse_notes(self.config.output_file)
        self._apply_filters()

    def _schedule_search(self):
        """Debounce search by 200ms."""
        if hasattr(self, "_search_after_id"):
            self.window.after_cancel(self._search_after_id)
        self._search_after_id = self.window.after(200, self._on_search)

    def _on_search(self, *_args):
        self._apply_filters()

    def _on_tag_filter(self, tag: str | None):
        """Toggle tag filter. None = show all."""
        self._active_tag = tag
        self._update_pill_styles()
        self._apply_filters()

    def _update_pill_styles(self):
        t = self.theme
        fnt = platform_font()
        for tag_key, pill in self._pill_buttons.items():
            if tag_key == self._active_tag:
                pill.configure(bg=t["accent"], fg=t["bg"], font=(fnt, 9, "bold"))
            else:
                pill.configure(bg=t["bg"], fg=t["fg"], font=(fnt, 9))

    def _apply_filters(self):
        """Apply search query + tag filter, then re-render cards."""
        notes = self._all_notes
        query = self.search_var.get().strip()
        if query:
            notes = search_notes(notes, query)
        if self._active_tag:
            notes = filter_by_tag(notes, self._active_tag)

        self._visible_cards = notes
        self._render_cards()

    def _render_cards(self):
        """Clear and re-render all visible cards."""
        for widget in self.cards_frame.winfo_children():
            widget.destroy()
        self._card_frames.clear()

        t = self.theme
        fnt = platform_font()
        notes = self._visible_cards
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        current_date = None

        for note in reversed(notes):  # newest first
            note_date = note.timestamp.date()
            if note_date != current_date:
                current_date = note_date
                if note_date == today:
                    header_text = "TODAY"
                elif note_date == yesterday:
                    header_text = "YESTERDAY"
                else:
                    header_text = note_date.strftime("%b %d").upper()

                header = tk.Label(
                    self.cards_frame, text=header_text, bg=t["bg"],
                    fg=t["muted"], font=(fnt, 9), anchor="w", pady=4, padx=12,
                )
                header.pack(fill="x")

            self._render_card(note, fnt)

        # Footer
        open_todos = sum(1 for n in self._all_notes if "todo" in n.tags and not n.is_done)
        self.footer.configure(text=f"{len(self._visible_cards)} notes · {open_todos} open todos · Esc close")

    def _render_card(self, note: Note, fnt: str):
        """Render a single note card."""
        t = self.theme

        # Determine left border color
        border_color = t["muted"]
        for tag in note.tags:
            if tag in self.tag_colors:
                border_color = self.tag_colors[tag]
                break

        opacity_fg = t["muted"] if note.is_done else t["fg"]
        card_bg = t["entry_bg"]

        # Card outer frame (provides colored left border)
        outer = tk.Frame(self.cards_frame, bg=border_color, padx=0, pady=0)
        outer.pack(fill="x", padx=12, pady=(0, 6))

        # Card inner frame
        card = tk.Frame(outer, bg=card_bg, padx=10, pady=8)
        card.pack(fill="x", padx=(3, 0))  # 3px left border

        # Top row: time + checkbox
        top_row = tk.Frame(card, bg=card_bg)
        top_row.pack(fill="x")

        time_str = note.timestamp.strftime("%H:%M")
        tk.Label(
            top_row, text=time_str, bg=card_bg, fg=t["muted"], font=(fnt, 9),
        ).pack(side="left")

        if "todo" in note.tags:
            check_text = "☑" if note.is_done else "☐"
            check_btn = tk.Label(
                top_row, text=check_text, bg=card_bg, fg=opacity_fg,
                font=(fnt, 14), cursor="hand2",
            )
            check_btn.pack(side="right")
            if not note.is_done:
                check_btn.bind("<Button-1>", lambda e, n=note: self._on_mark_done(n))

        # Note text
        text_display = note.text
        text_font_opts = (fnt, 11)
        if note.is_done:
            text_font_opts = (fnt, 11, "overstrike")

        text_label = tk.Label(
            card, text=text_display, bg=card_bg, fg=opacity_fg,
            font=text_font_opts, anchor="w", justify="left", wraplength=400,
        )
        text_label.pack(fill="x", pady=(4, 0))

        # Tag pills
        if note.tags:
            tags_frame = tk.Frame(card, bg=card_bg)
            tags_frame.pack(fill="x", pady=(4, 0), anchor="w")
            for tag in note.tags:
                color = self.tag_colors.get(tag, t["muted"])
                tk.Label(
                    tags_frame, text=f"#{tag}", bg=t["bg"], fg=color,
                    font=(fnt, 9), padx=4, pady=1,
                ).pack(side="left", padx=(0, 4))

        # Bind mousewheel on card and all children for smooth scrolling
        for widget in (outer, card, top_row, text_label):
            widget.bind("<MouseWheel>", self._on_mousewheel)

        self._card_frames.append(outer)

    def _on_mark_done(self, note: Note):
        """Mark a todo note as done and refresh the display."""
        if mark_done(self.config.output_file, note):
            self._load_notes()