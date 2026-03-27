"""Tests for blip_browse.py — Browse Window UI."""

import tkinter as tk
import pytest
from pathlib import Path

try:
    _test_root = tk.Tk()
    _test_root.destroy()
    _has_display = True
except tk.TclError:
    _has_display = False

needs_display = pytest.mark.skipif(not _has_display, reason="No display or Tcl unavailable")


@needs_display
def test_browse_window_creates(tmp_path):
    """BrowseWindow opens without error."""
    f = tmp_path / "blip.md"
    f.write_text("- [2026-03-26 14:30] ☐ test note #todo\n", encoding="utf-8")

    from blip_browse import BrowseWindow
    from blip import BlipConfig

    root = tk.Tk()
    root.withdraw()
    config = BlipConfig(output_file=f)
    win = BrowseWindow(root, config)
    assert win.window.winfo_exists()
    win.window.destroy()
    root.destroy()


@needs_display
def test_browse_search_filters(tmp_path):
    """Typing in search box reduces visible cards."""
    f = tmp_path / "blip.md"
    f.write_text(
        "- [2026-03-26 14:30] ☐ buy milk #todo\n"
        "- [2026-03-26 11:20] meeting notes\n",
        encoding="utf-8",
    )

    from blip_browse import BrowseWindow
    from blip import BlipConfig

    root = tk.Tk()
    root.withdraw()
    config = BlipConfig(output_file=f)
    win = BrowseWindow(root, config)
    total_before = len(win._visible_cards)

    win.search_var.set("milk")
    win._on_search()
    total_after = len(win._visible_cards)

    assert total_before == 2
    assert total_after == 1
    win.window.destroy()
    root.destroy()


@needs_display
def test_browse_tag_filter(tmp_path):
    """Tag pill click filters cards."""
    f = tmp_path / "blip.md"
    f.write_text(
        "- [2026-03-26 14:30] ☐ buy milk #todo\n"
        "- [2026-03-26 11:20] ⭐ lunch #important\n",
        encoding="utf-8",
    )

    from blip_browse import BrowseWindow
    from blip import BlipConfig

    root = tk.Tk()
    root.withdraw()
    config = BlipConfig(output_file=f)
    win = BrowseWindow(root, config)

    win._on_tag_filter("todo")
    assert len(win._visible_cards) == 1
    assert win._visible_cards[0].tags == ["todo"]

    win._on_tag_filter(None)  # "All" — clear filter
    assert len(win._visible_cards) == 2
    win.window.destroy()
    root.destroy()