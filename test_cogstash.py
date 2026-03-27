"""Tests for blip.py."""

import sys
from unittest.mock import patch
from pathlib import Path
import tkinter as tk
import re
import json
import pytest

# Skip tkinter-dependent tests when display/Tcl is unavailable
try:
    _test_root = tk.Tk()
    _test_root.destroy()
    _has_display = True
except tk.TclError:
    _has_display = False

needs_display = pytest.mark.skipif(not _has_display, reason="No display or Tcl unavailable")


def test_platform_font_windows():
    with patch.object(sys, "platform", "win32"):
        from blip import platform_font
        result = platform_font()
        assert result == "Segoe UI"


def test_platform_font_macos():
    with patch.object(sys, "platform", "darwin"):
        from blip import platform_font
        result = platform_font()
        assert result == "Helvetica Neue"


def test_platform_font_linux():
    with patch.object(sys, "platform", "linux"):
        from blip import platform_font
        result = platform_font()
        assert result == "sans-serif"


def test_platform_font_unknown():
    with patch.object(sys, "platform", "freebsd"):
        from blip import platform_font
        result = platform_font()
        assert result == "TkDefaultFont"


@needs_display
def test_append_note_creates_file(tmp_path):
    """append_note creates the file and writes the correct format."""
    import blip as blip_mod

    test_file = tmp_path / "blip.md"
    root = tk.Tk()
    root.withdraw()
    app = blip_mod.Blip(root, blip_mod.BlipConfig(output_file=test_file))
    result = app.append_note("test note")
    root.destroy()

    assert result is True
    content = test_file.read_text(encoding="utf-8")
    assert "test note" in content
    assert re.match(r"- \[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\] test note\n", content)


@needs_display
def test_append_note_appends(tmp_path):
    """Multiple notes are appended, not overwritten."""
    import blip as blip_mod

    test_file = tmp_path / "blip.md"
    root = tk.Tk()
    root.withdraw()
    app = blip_mod.Blip(root, blip_mod.BlipConfig(output_file=test_file))
    app.append_note("first")
    app.append_note("second")
    root.destroy()

    lines = test_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    assert "first" in lines[0]
    assert "second" in lines[1]


@needs_display
def test_append_note_error_handling(tmp_path):
    """append_note returns False and logs on write failure."""
    import blip as blip_mod

    root = tk.Tk()
    root.withdraw()
    app = blip_mod.Blip(root, blip_mod.BlipConfig(output_file=Path("\\\\nonexistent_server_xyz\\share\\blip.md")))
    result = app.append_note("should fail")
    root.destroy()

    assert result is False


@needs_display
def test_show_hide_state():
    """show_window and hide_window toggle is_visible correctly."""
    import blip as blip_mod

    root = tk.Tk()
    root.withdraw()
    app = blip_mod.Blip(root, blip_mod.BlipConfig())

    assert app.is_visible is False

    app.show_window()
    assert app.is_visible is True

    app.hide_window()
    assert app.is_visible is False

    root.destroy()


def test_theme_colors():
    """Every theme has all 6 required color keys."""
    from blip import THEMES
    required = {"bg", "fg", "entry_bg", "accent", "muted", "error"}
    assert len(THEMES) == 5
    for name, colors in THEMES.items():
        assert set(colors.keys()) == required, f"Theme '{name}' missing keys"
        for key, val in colors.items():
            assert val.startswith("#"), f"Theme '{name}'.{key} not a hex color"


def test_window_size_presets():
    """Every window size has width, lines, and max_lines."""
    from blip import WINDOW_SIZES
    required = {"width", "lines", "max_lines"}
    assert len(WINDOW_SIZES) == 3
    for name, size in WINDOW_SIZES.items():
        assert set(size.keys()) == required, f"Size '{name}' missing keys"
        assert size["lines"] <= size["max_lines"], f"Size '{name}' lines > max_lines"


def test_load_config_defaults(tmp_path):
    """No config file → returns default BlipConfig."""
    from blip import load_config, BlipConfig
    config = load_config(tmp_path / "nonexistent.json")
    assert isinstance(config, BlipConfig)
    assert config.hotkey == "<ctrl>+<shift>+<space>"
    assert config.theme == "tokyo-night"
    assert config.window_size == "default"
    # Config file should be created with defaults
    assert (tmp_path / "nonexistent.json").exists()


def test_load_config_partial(tmp_path):
    """Partial JSON → missing keys filled from defaults."""
    from blip import load_config
    cfg_file = tmp_path / "blip.json"
    cfg_file.write_text(json.dumps({"theme": "dracula"}), encoding="utf-8")
    config = load_config(cfg_file)
    assert config.theme == "dracula"
    assert config.hotkey == "<ctrl>+<shift>+<space>"  # filled from default


def test_load_config_malformed(tmp_path):
    """Bad JSON → warning logged, defaults returned."""
    from blip import load_config
    cfg_file = tmp_path / "blip.json"
    cfg_file.write_text("{bad json!!!", encoding="utf-8")
    config = load_config(cfg_file)
    assert config.theme == "tokyo-night"  # all defaults


def test_load_config_unknown_theme(tmp_path):
    """Unknown theme → falls back to tokyo-night."""
    from blip import load_config
    cfg_file = tmp_path / "blip.json"
    cfg_file.write_text(json.dumps({"theme": "nonexistent"}), encoding="utf-8")
    config = load_config(cfg_file)
    assert config.theme == "tokyo-night"


def test_parse_tags_smart():
    """Smart tags get emoji prefixes prepended to text."""
    from blip import parse_smart_tags
    result = parse_smart_tags("Review PR #42 #todo #urgent")
    assert result.startswith("☐ 🔴 ")
    assert "Review PR #42 #todo #urgent" in result


def test_parse_tags_dedup():
    """Duplicate smart tags produce only one emoji prefix."""
    from blip import parse_smart_tags
    result = parse_smart_tags("do thing #todo and also #todo")
    # Should have exactly one ☐, not two
    assert result.count("☐") == 1


def test_parse_tags_url_safe():
    """URL fragments are not matched as tags."""
    from blip import parse_smart_tags
    result = parse_smart_tags("see http://example.com#section for details")
    # No emoji should be prepended — #section is not a standalone tag
    assert not result.startswith("☐")
    assert not result.startswith("🔴")
    assert not result.startswith("⭐")
    assert not result.startswith("💡")


@needs_display
def test_multiline_format(tmp_path):
    """Multi-line text uses indented continuation lines."""
    import blip as blip_mod

    test_file = tmp_path / "blip.md"
    root = tk.Tk()
    root.withdraw()
    app = blip_mod.Blip(root, blip_mod.BlipConfig(output_file=test_file))
    result = app.append_note("line one\nline two\nline three")
    root.destroy()

    assert result is True
    content = test_file.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    assert len(lines) == 3
    assert lines[0].startswith("- [")
    assert lines[0].endswith("] line one")
    assert lines[1] == "  line two"
    assert lines[2] == "  line three"


@needs_display
def test_empty_submit_ignored(tmp_path):
    """Whitespace-only text is not saved."""
    import blip as blip_mod

    test_file = tmp_path / "blip.md"
    root = tk.Tk()
    root.withdraw()
    app = blip_mod.Blip(root, blip_mod.BlipConfig(output_file=test_file))
    result = app.append_note("   \n  \n  ")
    root.destroy()

    assert result is False
    assert not test_file.exists()
