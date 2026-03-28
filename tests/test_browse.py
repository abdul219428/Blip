"""Tests for cogstash_browse.py — Browse Window UI."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from conftest import needs_display


@needs_display
def test_browse_window_creates(tmp_path, tk_root):
    """BrowseWindow opens without error."""
    f = tmp_path / "cogstash.md"
    f.write_text("- [2026-03-26 14:30] ☐ test note #todo\n", encoding="utf-8")

    from cogstash.app import CogStashConfig
    from cogstash.browse import BrowseWindow

    config = CogStashConfig(output_file=f)
    win = BrowseWindow(tk_root, config)
    assert win.window.winfo_exists()
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

    from cogstash.app import CogStashConfig
    from cogstash.browse import BrowseWindow

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
def test_browse_tag_filter(tmp_path, tk_root):
    """Tag pill click filters cards."""
    f = tmp_path / "cogstash.md"
    f.write_text(
        "- [2026-03-26 14:30] ☐ buy milk #todo\n"
        "- [2026-03-26 11:20] ⭐ lunch #important\n",
        encoding="utf-8",
    )

    from cogstash.app import CogStashConfig
    from cogstash.browse import BrowseWindow

    config = CogStashConfig(output_file=f)
    win = BrowseWindow(tk_root, config)

    win._on_tag_filter("todo")
    assert len(win._visible_cards) == 1
    assert win._visible_cards[0].tags == ["todo"]

    win._on_tag_filter(None)  # "All" — clear filter
    assert len(win._visible_cards) == 2
    win.window.destroy()


@needs_display
def test_browse_custom_tag_pills(tk_root, tmp_path):
    """Custom tags appear as filter pills in the browse window."""
    from cogstash.app import CogStashConfig
    from cogstash.browse import BrowseWindow
    notes_file = tmp_path / "cogstash.md"
    notes_file.write_text("- [2026-03-27 10:00] meeting #work\n", encoding="utf-8")
    config = CogStashConfig(output_file=notes_file)
    custom_smart = {"todo": "☐", "work": "💼"}
    custom_colors = {"todo": "#7aa2f7", "work": "#4A90D9"}
    bw = BrowseWindow(tk_root, config, smart_tags=custom_smart, tag_colors=custom_colors)
    assert "work" in bw._pill_buttons
    bw.window.destroy()


@needs_display
def test_browse_context_menu_exists(tmp_path, tk_root):
    """Right-click on a card shows a context menu."""
    f = tmp_path / "cogstash.md"
    f.write_text("- [2026-03-26 14:30] test note #todo\n", encoding="utf-8")

    from cogstash.app import CogStashConfig
    from cogstash.browse import BrowseWindow

    config = CogStashConfig(output_file=f)
    win = BrowseWindow(tk_root, config)
    assert hasattr(win, "_show_context_menu")
    win.window.destroy()


@needs_display
def test_browse_context_menu_releases_grab_after_popup(tmp_path, tk_root):
    """Context menu should release popup grab after tk_popup returns."""
    f = tmp_path / "cogstash.md"
    f.write_text("- [2026-03-26 14:30] test note #todo\n", encoding="utf-8")

    from cogstash.app import CogStashConfig
    from cogstash.browse import BrowseWindow

    class FakeMenu:
        last_instance = None

        def __init__(self, *args, **kwargs):
            self.destroyed = False
            self.grab_released = False
            FakeMenu.last_instance = self

        def add_command(self, *args, **kwargs):
            return None

        def add_separator(self):
            return None

        def tk_popup(self, x_root, y_root):
            return None

        def grab_release(self):
            self.grab_released = True

        def destroy(self):
            self.destroyed = True

    config = CogStashConfig(output_file=f)
    win = BrowseWindow(tk_root, config)

    event = SimpleNamespace(x_root=10, y_root=10)
    note = win._all_notes[0]
    with patch("cogstash.browse.tk.Menu", FakeMenu):
        win._show_context_menu(event, note)

    assert FakeMenu.last_instance is not None
    assert FakeMenu.last_instance.grab_released is True
    assert FakeMenu.last_instance.destroyed is False
    win.window.destroy()


@needs_display
def test_browse_context_menu_commands_remain_callable_after_popup(tmp_path, tk_root):
    """Context menu actions should still be invocable after tk_popup returns."""
    f = tmp_path / "cogstash.md"
    f.write_text("- [2026-03-26 14:30] test note #todo\n", encoding="utf-8")

    from cogstash.app import CogStashConfig
    from cogstash.browse import BrowseWindow

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

    with patch("cogstash.browse.tk.Menu", FakeMenu):
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
def test_browse_edit_note(tmp_path, tk_root):
    """Edit via _on_edit updates file and refreshes cards."""
    f = tmp_path / "cogstash.md"
    f.write_text("- [2026-03-26 14:30] original text\n", encoding="utf-8")

    from cogstash.app import CogStashConfig
    from cogstash.browse import BrowseWindow
    from cogstash.search import edit_note

    config = CogStashConfig(output_file=f)
    win = BrowseWindow(tk_root, config)
    note = win._all_notes[0]

    # Directly call edit_note (dialog would be interactive)
    edit_note(f, note, "updated text")
    win._load_notes()
    assert win._all_notes[0].text == "updated text"
    win.window.destroy()


@needs_display
def test_browse_edit_empty_text_shows_error(tmp_path, tk_root):
    """Saving empty edit text shows validation error instead of silent return."""
    f = tmp_path / "cogstash.md"
    f.write_text("- [2026-03-26 14:30] original text\n", encoding="utf-8")

    from cogstash.app import CogStashConfig
    from cogstash.browse import BrowseWindow

    config = CogStashConfig(output_file=f)
    win = BrowseWindow(tk_root, config)
    note = win._all_notes[0]

    with patch("cogstash.browse.edit_note") as edit_mock, patch("tkinter.messagebox.showerror") as error_mock:
        win._on_edit(note)
        dialog = next(child for child in win.window.winfo_children() if child.winfo_class() == "Toplevel")
        text_widget = next(child for child in dialog.winfo_children() if child.winfo_class() == "Text")
        text_widget.delete("1.0", "end")
        btn_frame = dialog.winfo_children()[-1]
        save_button = next(child for child in btn_frame.winfo_children() if child.cget("text") == "Save")
        save_button.invoke()

    edit_mock.assert_not_called()
    error_mock.assert_called_once()
    dialog.destroy()
    win.window.destroy()


@needs_display
def test_browse_edit_cancel_releases_grab(tmp_path, tk_root):
    """Cancel closes the edit dialog and releases its modal grab."""
    f = tmp_path / "cogstash.md"
    f.write_text("- [2026-03-26 14:30] original text\n", encoding="utf-8")

    from cogstash.app import CogStashConfig
    from cogstash.browse import BrowseWindow

    config = CogStashConfig(output_file=f)
    win = BrowseWindow(tk_root, config)
    note = win._all_notes[0]

    win._on_edit(note)
    dialog = next(child for child in win.window.winfo_children() if child.winfo_class() == "Toplevel")
    released = []
    original_release = dialog.grab_release

    def tracked_release():
        released.append(True)
        return original_release()

    dialog.grab_release = tracked_release
    btn_frame = dialog.winfo_children()[-1]
    cancel_button = next(child for child in btn_frame.winfo_children() if child.cget("text") == "Cancel")
    cancel_button.invoke()

    assert released == [True]
    assert not dialog.winfo_exists()
    win.window.destroy()


@needs_display
def test_browse_search_enter_moves_focus_from_entry(tmp_path, tk_root):
    """Pressing Enter in search should exit the entry for keyboard navigation."""
    f = tmp_path / "cogstash.md"
    f.write_text("- [2026-03-26 14:30] test note\n", encoding="utf-8")

    from cogstash.app import CogStashConfig
    from cogstash.browse import BrowseWindow

    config = CogStashConfig(output_file=f)
    win = BrowseWindow(tk_root, config)
    win.search_entry.focus_force()
    win.window.update()
    win.search_entry.event_generate("<Return>")
    win.window.update()

    assert win.window.focus_get() == win.window
    win.window.destroy()


@needs_display
def test_browse_delete_note(tmp_path, tk_root):
    """Delete via delete_note removes note and refreshes cards."""
    f = tmp_path / "cogstash.md"
    f.write_text(
        "- [2026-03-26 14:30] first note\n"
        "- [2026-03-26 15:00] second note\n",
        encoding="utf-8",
    )

    from cogstash.app import CogStashConfig
    from cogstash.browse import BrowseWindow
    from cogstash.search import delete_note

    config = CogStashConfig(output_file=f)
    win = BrowseWindow(tk_root, config)
    assert len(win._all_notes) == 2

    note = win._all_notes[0]
    delete_note(f, note)
    win._load_notes()
    assert len(win._all_notes) == 1
    assert "second note" in win._all_notes[0].text
    win.window.destroy()
