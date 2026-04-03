"""Tests for cogstash.ui.browse — Browse Window UI."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from ui._support import needs_display


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
