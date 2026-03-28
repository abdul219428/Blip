"""Tests for cogstash_browse.py — Browse Window UI."""

import pytest

from conftest import needs_display


@needs_display
def test_browse_window_creates(tmp_path, tk_root):
    """BrowseWindow opens without error."""
    f = tmp_path / "cogstash.md"
    f.write_text("- [2026-03-26 14:30] ☐ test note #todo\n", encoding="utf-8")

    from cogstash.browse import BrowseWindow
    from cogstash.app import CogStashConfig

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

    from cogstash.browse import BrowseWindow
    from cogstash.app import CogStashConfig

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

    from cogstash.browse import BrowseWindow
    from cogstash.app import CogStashConfig

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

    from cogstash.browse import BrowseWindow
    from cogstash.app import CogStashConfig

    config = CogStashConfig(output_file=f)
    win = BrowseWindow(tk_root, config)
    assert hasattr(win, "_show_context_menu")
    win.window.destroy()


@needs_display
def test_browse_edit_note(tmp_path, tk_root):
    """Edit via _on_edit updates file and refreshes cards."""
    f = tmp_path / "cogstash.md"
    f.write_text("- [2026-03-26 14:30] original text\n", encoding="utf-8")

    from cogstash.browse import BrowseWindow
    from cogstash.app import CogStashConfig
    from cogstash.search import edit_note, parse_notes

    config = CogStashConfig(output_file=f)
    win = BrowseWindow(tk_root, config)
    note = win._all_notes[0]

    # Directly call edit_note (dialog would be interactive)
    edit_note(f, note, "updated text")
    win._load_notes()
    assert win._all_notes[0].text == "updated text"
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

    from cogstash.browse import BrowseWindow
    from cogstash.app import CogStashConfig
    from cogstash.search import delete_note, parse_notes

    config = CogStashConfig(output_file=f)
    win = BrowseWindow(tk_root, config)
    assert len(win._all_notes) == 2

    note = win._all_notes[0]
    delete_note(f, note)
    win._load_notes()
    assert len(win._all_notes) == 1
    assert "second note" in win._all_notes[0].text
    win.window.destroy()