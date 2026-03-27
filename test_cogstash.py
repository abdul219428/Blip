"""Tests for cogstash.py."""

import sys
from unittest.mock import patch
from pathlib import Path
import re
import json
import pytest

from conftest import needs_display


def test_platform_font_windows():
    with patch.object(sys, "platform", "win32"):
        from cogstash import platform_font
        result = platform_font()
        assert result == "Segoe UI"


def test_platform_font_macos():
    with patch.object(sys, "platform", "darwin"):
        from cogstash import platform_font
        result = platform_font()
        assert result == "Helvetica Neue"


def test_platform_font_linux():
    with patch.object(sys, "platform", "linux"):
        from cogstash import platform_font
        result = platform_font()
        assert result == "sans-serif"


def test_platform_font_unknown():
    with patch.object(sys, "platform", "freebsd"):
        from cogstash import platform_font
        result = platform_font()
        assert result == "TkDefaultFont"


@needs_display
def test_append_note_creates_file(tmp_path, tk_root):
    """append_note creates the file and writes the correct format."""
    import cogstash as cogstash_mod

    test_file = tmp_path / "cogstash.md"
    app = cogstash_mod.CogStash(tk_root, cogstash_mod.CogStashConfig(output_file=test_file))
    result = app.append_note("test note")

    assert result is True
    content = test_file.read_text(encoding="utf-8")
    assert "test note" in content
    assert re.match(r"- \[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\] test note\n", content)


@needs_display
def test_append_note_appends(tmp_path, tk_root):
    """Multiple notes are appended, not overwritten."""
    import cogstash as cogstash_mod

    test_file = tmp_path / "cogstash.md"
    app = cogstash_mod.CogStash(tk_root, cogstash_mod.CogStashConfig(output_file=test_file))
    app.append_note("first")
    app.append_note("second")

    lines = test_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    assert "first" in lines[0]
    assert "second" in lines[1]


@needs_display
def test_append_note_error_handling(tmp_path, tk_root):
    """append_note returns False and logs on write failure."""
    import cogstash as cogstash_mod

    app = cogstash_mod.CogStash(tk_root, cogstash_mod.CogStashConfig(output_file=Path("\\\\nonexistent_server_xyz\\share\\cogstash.md")))
    result = app.append_note("should fail")

    assert result is False


@needs_display
def test_show_hide_state(tk_root):
    """show_window and hide_window toggle is_visible correctly."""
    import cogstash as cogstash_mod

    app = cogstash_mod.CogStash(tk_root, cogstash_mod.CogStashConfig())

    assert app.is_visible is False

    app.show_window()
    assert app.is_visible is True

    app.hide_window()
    assert app.is_visible is False


def test_theme_colors():
    """Every theme has all 6 required color keys."""
    from cogstash import THEMES
    required = {"bg", "fg", "entry_bg", "accent", "muted", "error"}
    assert len(THEMES) == 5
    for name, colors in THEMES.items():
        assert set(colors.keys()) == required, f"Theme '{name}' missing keys"
        for key, val in colors.items():
            assert val.startswith("#"), f"Theme '{name}'.{key} not a hex color"


def test_window_size_presets():
    """Every window size has width, lines, and max_lines."""
    from cogstash import WINDOW_SIZES
    required = {"width", "lines", "max_lines"}
    assert len(WINDOW_SIZES) == 3
    for name, size in WINDOW_SIZES.items():
        assert set(size.keys()) == required, f"Size '{name}' missing keys"
        assert size["lines"] <= size["max_lines"], f"Size '{name}' lines > max_lines"


def test_load_config_defaults(tmp_path):
    """No config file → returns default CogStashConfig."""
    from cogstash import load_config, CogStashConfig
    config = load_config(tmp_path / "nonexistent.json")
    assert isinstance(config, CogStashConfig)
    assert config.hotkey == "<ctrl>+<shift>+<space>"
    assert config.theme == "tokyo-night"
    assert config.window_size == "default"
    # Config file should be created with defaults
    assert (tmp_path / "nonexistent.json").exists()


def test_load_config_partial(tmp_path):
    """Partial JSON → missing keys filled from defaults."""
    from cogstash import load_config
    cfg_file = tmp_path / "cogstash.json"
    cfg_file.write_text(json.dumps({"theme": "dracula"}), encoding="utf-8")
    config = load_config(cfg_file)
    assert config.theme == "dracula"
    assert config.hotkey == "<ctrl>+<shift>+<space>"  # filled from default


def test_load_config_malformed(tmp_path):
    """Bad JSON → warning logged, defaults returned."""
    from cogstash import load_config
    cfg_file = tmp_path / "cogstash.json"
    cfg_file.write_text("{bad json!!!", encoding="utf-8")
    config = load_config(cfg_file)
    assert config.theme == "tokyo-night"  # all defaults


def test_load_config_unknown_theme(tmp_path):
    """Unknown theme → falls back to tokyo-night."""
    from cogstash import load_config
    cfg_file = tmp_path / "cogstash.json"
    cfg_file.write_text(json.dumps({"theme": "nonexistent"}), encoding="utf-8")
    config = load_config(cfg_file)
    assert config.theme == "tokyo-night"


def test_parse_tags_smart():
    """Smart tags get emoji prefixes prepended to text."""
    from cogstash import parse_smart_tags
    result = parse_smart_tags("Review PR #42 #todo #urgent")
    assert result.startswith("☐ 🔴 ")
    assert "Review PR #42 #todo #urgent" in result


def test_parse_tags_dedup():
    """Duplicate smart tags produce only one emoji prefix."""
    from cogstash import parse_smart_tags
    result = parse_smart_tags("do thing #todo and also #todo")
    # Should have exactly one ☐, not two
    assert result.count("☐") == 1


def test_parse_tags_url_safe():
    """URL fragments are not matched as tags."""
    from cogstash import parse_smart_tags
    result = parse_smart_tags("see http://example.com#section for details")
    # No emoji should be prepended — #section is not a standalone tag
    assert not result.startswith("☐")
    assert not result.startswith("🔴")
    assert not result.startswith("⭐")
    assert not result.startswith("💡")


@needs_display
def test_multiline_format(tmp_path, tk_root):
    """Multi-line text uses indented continuation lines."""
    import cogstash as cogstash_mod

    test_file = tmp_path / "cogstash.md"
    app = cogstash_mod.CogStash(tk_root, cogstash_mod.CogStashConfig(output_file=test_file))
    result = app.append_note("line one\nline two\nline three")

    assert result is True
    content = test_file.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    assert len(lines) == 3
    assert lines[0].startswith("- [")
    assert lines[0].endswith("] line one")
    assert lines[1] == "  line two"
    assert lines[2] == "  line three"


@needs_display
def test_empty_submit_ignored(tmp_path, tk_root):
    """Whitespace-only text is not saved."""
    import cogstash as cogstash_mod

    test_file = tmp_path / "cogstash.md"
    app = cogstash_mod.CogStash(tk_root, cogstash_mod.CogStashConfig(output_file=test_file))
    result = app.append_note("   \n  \n  ")

    assert result is False
    assert not test_file.exists()


def test_merge_tags_builtin_defaults():
    """merge_tags with no custom tags returns built-in defaults."""
    from cogstash import merge_tags, DEFAULT_SMART_TAGS, CogStashConfig
    from cogstash_search import DEFAULT_TAG_COLORS
    config = CogStashConfig()
    smart, colors = merge_tags(config)
    assert smart == DEFAULT_SMART_TAGS
    assert colors == DEFAULT_TAG_COLORS


def test_merge_tags_add_new():
    """Custom tag merges alongside built-ins."""
    from cogstash import merge_tags, CogStashConfig
    config = CogStashConfig(tags={"work": {"emoji": "💼", "color": "#4A90D9"}})
    smart, colors = merge_tags(config)
    assert smart["work"] == "💼"
    assert colors["work"] == "#4A90D9"
    assert "todo" in smart  # built-in still present


def test_merge_tags_override_builtin():
    """User can override a built-in tag's emoji and color."""
    from cogstash import merge_tags, CogStashConfig
    config = CogStashConfig(tags={"todo": {"emoji": "✅", "color": "#00FF00"}})
    smart, colors = merge_tags(config)
    assert smart["todo"] == "✅"
    assert colors["todo"] == "#00FF00"


def test_load_config_custom_tags(tmp_path):
    """Config with tags key loads custom tags into CogStashConfig."""
    from cogstash import load_config
    cfg_path = tmp_path / "cogstash.json"
    cfg_path.write_text(json.dumps({
        "tags": {"work": {"emoji": "💼", "color": "#4A90D9"}}
    }), encoding="utf-8")
    config = load_config(cfg_path)
    assert config.tags == {"work": {"emoji": "💼", "color": "#4A90D9"}}


def test_load_config_invalid_tag_skipped(tmp_path):
    """Tags missing emoji or color are skipped."""
    from cogstash import load_config
    cfg_path = tmp_path / "cogstash.json"
    cfg_path.write_text(json.dumps({
        "tags": {
            "good": {"emoji": "✅", "color": "#00FF00"},
            "bad_no_emoji": {"color": "#FF0000"},
            "bad_no_color": {"emoji": "❌"},
            "bad_hex": {"emoji": "❌", "color": "not-hex"},
        }
    }), encoding="utf-8")
    config = load_config(cfg_path)
    assert "good" in config.tags
    assert "bad_no_emoji" not in config.tags
    assert "bad_no_color" not in config.tags
    assert "bad_hex" not in config.tags
