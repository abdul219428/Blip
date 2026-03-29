"""cogstash_browse.py — Browse Window for viewing and filtering past notes.

Card-view UI with search, tag filtering, and mark-done for #todo items.
Opened from the system tray icon. Uses cogstash_search for all data operations.
"""

from __future__ import annotations

import re
import sys
import tkinter as tk
from datetime import datetime, timedelta

from cogstash.app import DEFAULT_SMART_TAGS, THEMES, CogStashConfig, platform_font
from cogstash.search import (
    DEFAULT_TAG_COLORS,
    Note,
    delete_note,
    edit_note,
    filter_by_tag,
    mark_done,
    parse_notes,
    search_notes,
)


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
        self._context_menu: tk.Menu | None = None
        self._notice_label: tk.Label | None = None
        self._notice_after_id: str | None = None

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
        self.search_entry.bind("<Return>", lambda e: self.window.focus_set())

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

        # Mousewheel scrolling — platform-aware bindings
        if sys.platform == "linux":
            def _on_mousewheel_up(e):
                self.canvas.yview_scroll(-3, "units")

            def _on_mousewheel_down(e):
                self.canvas.yview_scroll(3, "units")
            self.canvas.bind("<Button-4>", _on_mousewheel_up)
            self.canvas.bind("<Button-5>", _on_mousewheel_down)
            self.cards_frame.bind("<Button-4>", _on_mousewheel_up)
            self.cards_frame.bind("<Button-5>", _on_mousewheel_down)
            self._on_mousewheel = None
            self._on_mousewheel_up = _on_mousewheel_up
            self._on_mousewheel_down = _on_mousewheel_down
        else:
            def _on_mousewheel(e):
                if sys.platform == "darwin":
                    self.canvas.yview_scroll(-e.delta, "units")
                else:
                    self.canvas.yview_scroll(-1 * (e.delta // 120), "units")
            self.canvas.bind("<MouseWheel>", _on_mousewheel)
            self.cards_frame.bind("<MouseWheel>", _on_mousewheel)
            self._on_mousewheel = _on_mousewheel

        # Footer
        self.footer = tk.Label(
            self.window, bg=t["entry_bg"], fg=t["muted"],
            font=(fnt, 9), anchor="center", pady=4,
        )
        self.footer.pack(fill="x")

    def apply_config(
        self,
        config: CogStashConfig,
        smart_tags: dict[str, str] | None = None,
        tag_colors: dict[str, str] | None = None,
    ) -> None:
        """Refresh the browse window after settings change."""
        query = self.search_var.get()
        self.config = config
        self.theme = THEMES[config.theme]
        self.smart_tags = smart_tags or dict(DEFAULT_SMART_TAGS)
        if tag_colors is not None:
            self.tag_colors = tag_colors
        for child in self.window.winfo_children():
            child.destroy()
        self.search_var = tk.StringVar(value=query)
        self._build_ui()
        self._update_pill_styles()
        self._apply_filters()

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
                check_btn.bind("<Button-1>", lambda e, n=note: (self._on_mark_done(n), None)[1])  # type: ignore[misc,return-value]

        # Note text
        text_display = note.text
        text_font_opts: tuple[str, int] | tuple[str, int, str] = (fnt, 11)
        if note.is_done:
            text_font_opts = (fnt, 11, "overstrike")

        text_label = tk.Label(
            card, text=text_display, bg=card_bg, fg=opacity_fg,
            font=text_font_opts, anchor="w", justify="left", wraplength=400,
        )
        text_label.pack(fill="x", pady=(4, 0))

        # Collect all card widgets for event binding
        card_widgets = [outer, card, top_row, text_label]

        # Tag pills
        if note.tags:
            tags_frame = tk.Frame(card, bg=card_bg)
            tags_frame.pack(fill="x", pady=(4, 0), anchor="w")
            for tag in note.tags:
                color = self.tag_colors.get(tag, t["muted"])
                pill = tk.Label(
                    tags_frame, text=f"#{tag}", bg=t["bg"], fg=color,
                    font=(fnt, 9), padx=4, pady=1,
                )
                pill.pack(side="left", padx=(0, 4))
                card_widgets.append(pill)
            card_widgets.append(tags_frame)

        # Bind mousewheel and right-click context menu on all card widgets
        for widget in card_widgets:
            if sys.platform == "linux":
                widget.bind("<Button-4>", self._on_mousewheel_up)
                widget.bind("<Button-5>", self._on_mousewheel_down)
            else:
                widget.bind("<MouseWheel>", self._on_mousewheel)
            widget.bind("<Button-3>", lambda e, n=note: (self._show_context_menu(e, n), None)[1])  # type: ignore[misc,return-value]

        self._card_frames.append(outer)

    def _on_mark_done(self, note: Note):
        """Mark a todo note as done and refresh the display."""
        assert self.config.output_file is not None, "output_file should be set by __post_init__"
        if mark_done(self.config.output_file, note):
            self._replace_note(note, self._build_updated_note(note, note.text.replace("☐", "☑", 1), is_done=True))
            return
        self._handle_stale_action()

    def _show_context_menu(self, event, note: Note):
        """Show right-click context menu for a note card."""
        self._destroy_context_menu()
        menu = tk.Menu(self.window, tearoff=0)
        self._context_menu = menu
        menu.add_command(label="✏️ Edit", command=lambda: self._run_context_action(self._on_edit, note))
        menu.add_command(label="🗑️ Delete", command=lambda: self._run_context_action(self._on_delete, note))
        menu.add_separator()
        menu.add_command(label="📋 Copy text", command=lambda: self._run_context_action(self._on_copy, note))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _run_context_action(self, action, note: Note):
        """Run a context menu action and clean up the menu afterward."""
        try:
            action(note)
        finally:
            self._destroy_context_menu()

    def _destroy_context_menu(self):
        """Destroy the current context menu if it exists."""
        if self._context_menu is None:
            return
        try:
            self._context_menu.destroy()
        finally:
            self._context_menu = None

    def _on_edit(self, note: Note):
        """Open themed edit dialog for a note."""
        t = self.theme
        fnt = platform_font()

        dialog = tk.Toplevel(self.window)
        dialog.title("Edit Note")
        dialog.configure(bg=t["bg"])
        dialog.geometry("420x220")
        dialog.transient(self.window)
        dialog.grab_set()

        def close_dialog():
            try:
                dialog.grab_release()
            except tk.TclError:
                pass
            dialog.destroy()

        # Header: title + timestamp
        header = tk.Frame(dialog, bg=t["bg"])
        header.pack(fill="x", padx=16, pady=(12, 0))
        tk.Label(
            header, text="Edit Note", bg=t["bg"], fg=t["fg"],
            font=(fnt, 12, "bold"),
        ).pack(side="left")
        tk.Label(
            header, text=note.timestamp.strftime("[%Y-%m-%d %H:%M]"),
            bg=t["bg"], fg=t["muted"], font=(fnt, 10),
        ).pack(side="right")

        # Text area
        text_widget = tk.Text(
            dialog, bg=t["entry_bg"], fg=t["fg"], insertbackground=t["fg"],
            font=(fnt, 11), relief="flat", bd=0, wrap="word",
            highlightthickness=1, highlightbackground=t["muted"],
            highlightcolor=t["accent"],
        )
        text_widget.pack(fill="both", expand=True, padx=16, pady=8)
        text_widget.insert("1.0", note.text)
        text_widget.focus_set()

        # Buttons
        btn_frame = tk.Frame(dialog, bg=t["bg"])
        btn_frame.pack(fill="x", padx=16, pady=(0, 12))

        def save():
            from tkinter import messagebox

            new_text = text_widget.get("1.0", "end-1c").strip()
            if not new_text:
                messagebox.showerror("Error", "Note text cannot be empty.", parent=dialog)
                return
            if edit_note(self.config.output_file, note, new_text):
                self._replace_note(note, self._build_updated_note(note, new_text))
                close_dialog()
            else:
                close_dialog()
                self._handle_stale_action()

        tk.Button(
            btn_frame, text="Cancel", command=close_dialog,
            bg=t["entry_bg"], fg=t["fg"], font=(fnt, 10),
            relief="flat", padx=12, pady=4, cursor="hand2",
        ).pack(side="right", padx=(4, 0))
        tk.Button(
            btn_frame, text="Save", command=save,
            bg=t["accent"], fg=t["bg"], font=(fnt, 10, "bold"),
            relief="flat", padx=12, pady=4, cursor="hand2",
        ).pack(side="right")

        dialog.bind("<Escape>", lambda e: close_dialog())

    def _on_delete(self, note: Note):
        """Delete a note with confirmation dialog."""
        from tkinter import messagebox
        preview = note.text[:50] + ("..." if len(note.text) > 50 else "")
        if messagebox.askyesno(
            "Delete Note",
            f"Delete this note?\n\n\"{preview}\"",
            parent=self.window,
        ):
            assert self.config.output_file is not None, "output_file should be set by __post_init__"
            if delete_note(self.config.output_file, note):
                self._all_notes = [existing for existing in self._all_notes if existing is not note]
                self._apply_filters()
                return
            self._handle_stale_action()

    def _on_copy(self, note: Note):
        """Copy note text to clipboard."""
        self.window.clipboard_clear()
        self.window.clipboard_append(note.text)
        self._show_notice("Copied")

    def _handle_stale_action(self) -> None:
        """Reload notes after an out-of-date edit target and notify the user."""
        self._load_notes()
        self._show_notice("Notes changed on disk — reloaded")

    def _show_notice(self, text: str) -> None:
        """Show a brief non-blocking status notice."""
        if self._notice_after_id is not None:
            self.window.after_cancel(self._notice_after_id)
            self._notice_after_id = None
        if self._notice_label is not None and self._notice_label.winfo_exists():
            self._notice_label.destroy()
        self._notice_label = tk.Label(
            self.window,
            text=text,
            bg=self.theme["accent"],
            fg=self.theme["bg"],
            font=(platform_font(), 9),
            padx=10,
            pady=4,
        )
        self._notice_label.place(relx=0.5, rely=0.94, anchor="center")
        self._notice_after_id = self.window.after(1500, self._clear_notice)

    def _clear_notice(self) -> None:
        """Remove the transient status notice."""
        self._notice_after_id = None
        if self._notice_label is not None and self._notice_label.winfo_exists():
            self._notice_label.destroy()
        self._notice_label = None

    def _replace_note(self, original: Note, updated: Note) -> None:
        """Replace a note in the in-memory list and refresh filtered cards."""
        for index, existing in enumerate(self._all_notes):
            if existing is original:
                self._all_notes[index] = updated
                break
        self._apply_filters()

    def _build_updated_note(self, note: Note, new_text: str, is_done: bool | None = None) -> Note:
        """Return a note copy with updated text-derived fields."""
        tags = list(dict.fromkeys(re.findall(r"(?:^|\s)#(\w+)", new_text)))
        return Note(
            index=note.index,
            timestamp=note.timestamp,
            text=new_text,
            tags=tags,
            is_done=note.is_done if is_done is None else is_done,
            line_number=note.line_number,
        )
