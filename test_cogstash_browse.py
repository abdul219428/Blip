"""Tests for cogstash_browse.py — Browse Window UI."""

import pytest

from conftest import needs_display


@needs_display
def test_browse_window_creates(tmp_path, tk_root):
    """BrowseWindow opens without error."""
    f = tmp_path / "cogstash.md"
    f.write_text("- [2026-03-26 14:30] ☐ test note #todo\n", encoding="utf-8")

    from cogstash_browse import BrowseWindow
    from cogstash import CogStashConfig

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

    from cogstash_browse import BrowseWindow
    from cogstash import CogStashConfig

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

    from cogstash_browse import BrowseWindow
    from cogstash import CogStashConfig

    config = CogStashConfig(output_file=f)
    win = BrowseWindow(tk_root, config)

    win._on_tag_filter("todo")
    assert len(win._visible_cards) == 1
    assert win._visible_cards[0].tags == ["todo"]

    win._on_tag_filter(None)  # "All" — clear filter
    assert len(win._visible_cards) == 2
    win.window.destroy()