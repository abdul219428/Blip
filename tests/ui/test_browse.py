"""Tests for cogstash.ui.browse — Browse Window UI."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from ui._support import needs_display


def _make_notes_file(tmp_path, contents: str):
    f = tmp_path / "cogstash.md"
    f.write_text(contents, encoding="utf-8")
    return f


def _make_browse_window(tmp_path, tk_root, contents: str):
    from cogstash.ui.app import CogStashConfig
    from cogstash.ui.browse import BrowseWindow

    return BrowseWindow(tk_root, CogStashConfig(output_file=_make_notes_file(tmp_path, contents)))


def _iter_descendant_widgets(widget):
    yield widget
    for child in widget.winfo_children():
        yield from _iter_descendant_widgets(child)


def _collect_widget_texts(widget):
    texts = []
    for child in _iter_descendant_widgets(widget):
        try:
            text = child.cget("text")
        except Exception:
            continue
        if isinstance(text, str) and text:
            texts.append(text)
    return texts


def _find_button_with_text(widget, text: str):
    for child in _iter_descendant_widgets(widget):
        try:
            if child.winfo_class() == "Button" and child.cget("text") == text:
                return child
        except Exception:
            continue
    return None


@needs_display
def test_browse_window_creates(tmp_path, tk_root):
    """BrowseWindow opens without error."""
    f = tmp_path / "cogstash.md"
    f.write_text("- [2026-03-26 14:30] ☐ test note #todo\n", encoding="utf-8")

    from cogstash.ui.app import CogStashConfig
    from cogstash.ui.browse import BrowseWindow

    config = CogStashConfig(output_file=f)
    win = BrowseWindow(tk_root, config)
    assert win.window.winfo_exists()
    win.window.destroy()


@needs_display
def test_browse_window_does_not_force_deiconify_on_create(tmp_path, tk_root):
    """BrowseWindow should not force the toplevel to deiconify during creation."""
    f = tmp_path / "cogstash.md"
    f.write_text("- [2026-03-26 14:30] ☐ test note #todo\n", encoding="utf-8")

    from cogstash.ui.app import CogStashConfig
    from cogstash.ui.browse import BrowseWindow

    with patch("cogstash.ui.browse.tk.Toplevel.deiconify") as deiconify_mock:
        win = BrowseWindow(tk_root, CogStashConfig(output_file=f))

    assert deiconify_mock.call_count == 0
    win.window.destroy()


@needs_display
def test_browse_search_filters(tmp_path, tk_root):
    """Typing in search box reduces visible cards."""
    f = tmp_path / "cogstash.md"
    f.write_text(
        "- [2026-03-26 14:30] ☐ buy milk #todo\n"
        "- [2026-03-26 11:20] meeting notes\n",
        encoding="utf-8",
    )

    from cogstash.ui.app import CogStashConfig
    from cogstash.ui.browse import BrowseWindow

    config = CogStashConfig(output_file=f)
    win = BrowseWindow(tk_root, config)
    total_before = len(win._visible_cards)

    win.search_var.set("milk")
    win._on_search()
    total_after = len(win._visible_cards)

    assert total_before == 2
    assert total_after == 1
    win.window.destroy()


@needs_display
def test_browse_context_menu_commands_remain_callable_after_popup(tmp_path, tk_root):
    """Context menu actions should still be invocable after tk_popup returns."""
    f = tmp_path / "cogstash.md"
    f.write_text("- [2026-03-26 14:30] test note #todo\n", encoding="utf-8")

    from cogstash.ui.app import CogStashConfig
    from cogstash.ui.browse import BrowseWindow

    class FakeMenu:
        last_instance = None

        def __init__(self, *args, **kwargs):
            self.destroyed = False
            self.commands = {}
            self.grab_released = False
            FakeMenu.last_instance = self

        def add_command(self, label, command):
            self.commands[label] = command

        def add_separator(self):
            return None

        def tk_popup(self, x_root, y_root):
            return None

        def grab_release(self):
            self.grab_released = True

        def destroy(self):
            self.destroyed = True

        def invoke(self, label):
            if self.destroyed:
                raise RuntimeError("menu destroyed before command invocation")
            self.commands[label]()

    config = CogStashConfig(output_file=f)
    win = BrowseWindow(tk_root, config)
    event = SimpleNamespace(x_root=10, y_root=10)
    note = win._all_notes[0]

    with patch("cogstash.ui.browse.tk.Menu", FakeMenu):
        with (
            patch.object(win, "_on_edit") as edit_mock,
            patch.object(win, "_on_delete") as delete_mock,
            patch.object(win, "_on_copy") as copy_mock,
        ):
            win._show_context_menu(event, note)
            menu = FakeMenu.last_instance
            assert menu is not None
            menu.invoke("✏️ Edit")

            win._show_context_menu(event, note)
            menu = FakeMenu.last_instance
            assert menu is not None
            menu.invoke("🗑️ Delete")

            win._show_context_menu(event, note)
            menu = FakeMenu.last_instance
            assert menu is not None
            menu.invoke("📋 Copy text")

            edit_mock.assert_called_once_with(note)
            delete_mock.assert_called_once_with(note)
            copy_mock.assert_called_once_with(note)
            assert FakeMenu.last_instance.destroyed is True
    win.window.destroy()


@needs_display
def test_browse_stale_edit_reloads_and_shows_notice(tmp_path, tk_root):
    """Stale note actions should auto-reload notes and show a brief notice."""
    f = tmp_path / "cogstash.md"
    f.write_text("- [2026-03-26 14:30] original text\n", encoding="utf-8")

    from cogstash.ui.app import CogStashConfig
    from cogstash.ui.browse import BrowseWindow

    win = BrowseWindow(tk_root, CogStashConfig(output_file=f))
    note = win._all_notes[0]

    with (
        patch("cogstash.ui.browse.edit_note", return_value=False),
        patch.object(win, "_load_notes") as reload_mock,
        patch.object(win, "_show_notice") as notice_mock,
        patch("tkinter.messagebox.showerror") as error_mock,
    ):
        win._on_edit(note)
        dialog = next(child for child in win.window.winfo_children() if child.winfo_class() == "Toplevel")
        btn_frame = dialog.winfo_children()[-1]
        save_button = next(child for child in btn_frame.winfo_children() if child.cget("text") == "Save")
        save_button.invoke()

    reload_mock.assert_called_once()
    notice_mock.assert_called_once()
    error_mock.assert_not_called()
    win.window.destroy()


@needs_display
def test_browse_filter_summary_hidden_when_no_filters_active(tmp_path, tk_root):
    """No active filters should keep the summary bar hidden."""
    win = _make_browse_window(
        tmp_path,
        tk_root,
        "- [2026-03-26 14:30] install update #todo\n"
        "- [2026-03-26 11:20] planning notes #idea\n",
    )

    try:
        win.window.update_idletasks()

        assert len(win._visible_cards) == 2
        summary_frame = getattr(win, "_filter_summary_frame", None)
        assert summary_frame is not None
        assert not summary_frame.winfo_manager()
    finally:
        win.window.destroy()


@needs_display
def test_browse_apply_filters_renders_cards_before_idletasks_flush(tmp_path, tk_root):
    """Applying filters should rerender cards without forcing an idle-task flush."""
    win = _make_browse_window(
        tmp_path,
        tk_root,
        "- [2026-03-26 14:30] install update #todo\n"
        "- [2026-03-26 11:20] planning notes #idea\n",
    )

    events: list[str] = []
    original_render_cards = win._render_cards

    def _record_render():
        events.append("render")
        original_render_cards()

    try:
        with (
            patch("cogstash.ui.browse.tk.Misc.update_idletasks", side_effect=lambda *_args: events.append("update")),
            patch.object(win, "_render_cards", side_effect=_record_render),
        ):
            win._on_tag_filter("todo")

        assert events == ["render"]
    finally:
        win.window.destroy()


@needs_display
def test_browse_filter_summary_shows_combined_search_and_tag(tmp_path, tk_root):
    """Combined search and tag filters should show one joined summary string."""
    win = _make_browse_window(
        tmp_path,
        tk_root,
        "- [2026-03-26 14:30] install update #todo\n"
        "- [2026-03-26 12:15] install backup #idea\n"
        "- [2026-03-26 11:20] planning notes #todo\n",
    )

    try:
        win.search_var.set("install")
        win._on_search()
        win._on_tag_filter("todo")
        win.window.update_idletasks()

        summary_frame = getattr(win, "_filter_summary_frame", None)
        summary_label = getattr(win, "_filter_summary_label", None)

        assert len(win._visible_cards) == 1
        assert summary_frame is not None
        assert summary_frame.winfo_manager() == "pack"
        assert summary_label is not None
        assert summary_label.cget("text") == 'Filters active: Search: "install" · Tag: todo'
    finally:
        win.window.destroy()


@needs_display
def test_browse_filter_summary_shows_search_only_state(tmp_path, tk_root):
    """Search-only filtering should show the search summary text."""
    win = _make_browse_window(
        tmp_path,
        tk_root,
        "- [2026-03-26 14:30] install update #todo\n"
        "- [2026-03-26 11:20] planning notes #idea\n",
    )

    try:
        win.search_var.set("install")
        win._on_search()
        win.window.update_idletasks()

        summary_frame = getattr(win, "_filter_summary_frame", None)
        summary_label = getattr(win, "_filter_summary_label", None)

        assert len(win._visible_cards) == 1
        assert summary_frame is not None
        assert summary_frame.winfo_manager() == "pack"
        assert summary_label is not None
        assert summary_label.cget("text") == 'Filters active: Search: "install"'
    finally:
        win.window.destroy()


@needs_display
def test_browse_filter_summary_shows_tag_only_state(tmp_path, tk_root):
    """Tag-only filtering should show the tag summary text."""
    win = _make_browse_window(
        tmp_path,
        tk_root,
        "- [2026-03-26 14:30] install update #todo\n"
        "- [2026-03-26 11:20] planning notes #idea\n",
    )

    try:
        win._on_tag_filter("todo")
        win.window.update_idletasks()

        summary_frame = getattr(win, "_filter_summary_frame", None)
        summary_label = getattr(win, "_filter_summary_label", None)

        assert len(win._visible_cards) == 1
        assert summary_frame is not None
        assert summary_frame.winfo_manager() == "pack"
        assert summary_label is not None
        assert summary_label.cget("text") == "Filters active: Tag: todo"
    finally:
        win.window.destroy()


@needs_display
def test_browse_clear_filters_resets_search_tag_and_full_list(tmp_path, tk_root):
    """Clear filters should reset search, tag, and restore the full card list."""
    win = _make_browse_window(
        tmp_path,
        tk_root,
        "- [2026-03-26 14:30] install update #todo\n"
        "- [2026-03-26 12:15] install backup #idea\n"
        "- [2026-03-26 11:20] planning notes #todo\n",
    )

    try:
        win.search_var.set("install")
        win._on_search()
        win._on_tag_filter("todo")
        win.window.update_idletasks()

        summary_frame = getattr(win, "_filter_summary_frame", None)
        clear_filters_button = getattr(win, "_clear_filters_button", None)

        assert len(win._visible_cards) == 1
        assert summary_frame is not None
        assert summary_frame.winfo_manager() == "pack"
        assert clear_filters_button is not None

        clear_filters_button.invoke()
        win.window.update_idletasks()

        summary_frame = getattr(win, "_filter_summary_frame", None)

        assert win.search_var.get() == ""
        assert win._active_tag is None
        assert len(win._visible_cards) == 3
        assert summary_frame is None or not summary_frame.winfo_manager()
    finally:
        win.window.destroy()


@needs_display
def test_browse_clear_filters_cancels_pending_search_before_refresh(tmp_path, tk_root):
    """Clearing filters should cancel any scheduled search before direct refresh."""
    win = _make_browse_window(
        tmp_path,
        tk_root,
        "- [2026-03-26 14:30] install update #todo\n"
        "- [2026-03-26 12:15] install backup #idea\n"
        "- [2026-03-26 11:20] planning notes #todo\n",
    )

    cancelled_ids: list[str] = []

    try:
        win._search_after_id = "search-before-clear"

        with (
            patch.object(win.window, "after", return_value="search-triggered-by-clear"),
            patch.object(win.window, "after_cancel", side_effect=cancelled_ids.append),
        ):
            win._clear_filters()

        assert cancelled_ids == ["search-before-clear", "search-triggered-by-clear"]
    finally:
        win.window.destroy()


@needs_display
def test_browse_filter_empty_state_shows_message_filters_and_clear_action(tmp_path, tk_root):
    """Zero-result filtered views should render a filter-aware empty state in the cards area."""
    win = _make_browse_window(
        tmp_path,
        tk_root,
        "- [2026-03-26 14:30] install update #todo\n"
        "- [2026-03-26 11:20] planning notes #idea\n",
    )

    try:
        win.search_var.set("install")
        win._on_search()
        win._on_tag_filter("idea")
        win.window.update_idletasks()

        empty_state_texts = _collect_widget_texts(win.cards_frame)
        empty_state_clear_button = _find_button_with_text(win.cards_frame, "Clear filters")
        expected_summary = 'Filters active: Search: "install" · Tag: idea'

        assert len(win._visible_cards) == 0
        assert win._filter_summary_label is not None
        assert win._filter_summary_label.cget("text") == expected_summary
        assert "No notes match the current filters." in empty_state_texts
        assert expected_summary in empty_state_texts
        assert empty_state_clear_button is not None
    finally:
        win.window.destroy()


@needs_display
def test_browse_filter_empty_state_stays_distinct_from_unfiltered_empty_state(tmp_path, tk_root):
    """The filtered empty-state wording should not appear when Browse has no notes and no filters."""
    win = _make_browse_window(tmp_path, tk_root, "")

    try:
        win.window.update_idletasks()

        cards_texts = _collect_widget_texts(win.cards_frame)
        summary_frame = getattr(win, "_filter_summary_frame", None)

        assert len(win._visible_cards) == 0
        assert summary_frame is not None
        assert not summary_frame.winfo_manager()
        assert "No notes match the current filters." not in cards_texts
        assert not any(text.startswith("Filters active:") for text in cards_texts)
    finally:
        win.window.destroy()


@needs_display
def test_browse_filter_empty_state_clear_action_restores_full_list(tmp_path, tk_root):
    """Clearing filters from the empty state should restore the unfiltered list."""
    win = _make_browse_window(
        tmp_path,
        tk_root,
        "- [2026-03-26 14:30] install update #todo\n"
        "- [2026-03-26 11:20] planning notes #idea\n",
    )

    try:
        win.search_var.set("install")
        win._on_search()
        win._on_tag_filter("idea")
        win.window.update_idletasks()

        empty_state_clear_button = _find_button_with_text(win.cards_frame, "Clear filters")

        assert len(win._visible_cards) == 0
        assert empty_state_clear_button is not None

        empty_state_clear_button.invoke()
        win.window.update_idletasks()

        assert win.search_var.get() == ""
        assert win._active_tag is None
        assert len(win._visible_cards) == 2
        assert "No notes match the current filters." not in _collect_widget_texts(win.cards_frame)
    finally:
        win.window.destroy()
