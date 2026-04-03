"""Tests for cogstash.py."""

import re
import sys
from unittest.mock import patch

from conftest import StrictEncodedStream
from ui._support import needs_display


def test_platform_font_windows():
    from cogstash.app import platform_font
    with patch.object(sys, "platform", "win32"):
        result = platform_font()
        assert result == "Segoe UI"


def test_platform_font_macos():
    from cogstash.app import platform_font
    with patch.object(sys, "platform", "darwin"):
        result = platform_font()
        assert result == "Helvetica Neue"


def test_platform_font_linux():
    from cogstash.app import platform_font
    with patch.object(sys, "platform", "linux"):
        result = platform_font()
        assert result == "sans-serif"


def test_platform_font_unknown():
    from cogstash.app import platform_font
    with patch.object(sys, "platform", "freebsd"):
        result = platform_font()
        assert result == "TkDefaultFont"


@needs_display
def test_append_note_creates_file(tmp_path, tk_root):
    """append_note creates the file and writes the correct format."""
    import cogstash.app as cogstash_mod

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
    import cogstash.app as cogstash_mod

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
    import cogstash.app as cogstash_mod

    test_file = tmp_path / "cogstash.md"
    app = cogstash_mod.CogStash(tk_root, cogstash_mod.CogStashConfig(output_file=test_file))
    with patch("cogstash.core.notes.Path.open", side_effect=OSError("mock write failure")):
        result = app.append_note("should fail")

    assert result is False


@needs_display
def test_show_hide_state(tk_root):
    """show_window and hide_window toggle is_visible correctly."""
    import cogstash.app as cogstash_mod

    app = cogstash_mod.CogStash(tk_root, cogstash_mod.CogStashConfig())

    assert app.is_visible is False

    app.show_window()
    assert app.is_visible is True

    app.hide_window()
    assert app.is_visible is False


def test_theme_colors():
    """Every theme has all 6 required color keys."""
    from cogstash.app import THEMES
    required = {"bg", "fg", "entry_bg", "accent", "muted", "error"}
    assert len(THEMES) == 5
    for name, colors in THEMES.items():
        assert set(colors.keys()) == required, f"Theme '{name}' missing keys"
        for key, val in colors.items():
            assert val.startswith("#"), f"Theme '{name}'.{key} not a hex color"


def test_window_size_presets():
    """Every window size has width, lines, and max_lines."""
    from cogstash.app import WINDOW_SIZES
    required = {"width", "lines", "max_lines"}
    assert len(WINDOW_SIZES) == 3
    for name, size in WINDOW_SIZES.items():
        assert set(size.keys()) == required, f"Size '{name}' missing keys"
        assert size["lines"] <= size["max_lines"], f"Size '{name}' lines > max_lines"


def test_parse_tags_smart():
    """Smart tags get emoji prefixes prepended to text."""
    from cogstash.app import parse_smart_tags
    result = parse_smart_tags("Review PR #42 #todo #urgent")
    assert result.startswith("☐ 🔴 ")
    assert "Review PR #42 #todo #urgent" in result


def test_parse_tags_dedup():
    """Duplicate smart tags produce only one emoji prefix."""
    from cogstash.app import parse_smart_tags
    result = parse_smart_tags("do thing #todo and also #todo")
    # Should have exactly one ☐, not two
    assert result.count("☐") == 1


def test_parse_tags_url_safe():
    """URL fragments are not matched as tags."""
    from cogstash.app import parse_smart_tags
    result = parse_smart_tags("see http://example.com#section for details")
    # No emoji should be prepended — #section is not a standalone tag
    assert not result.startswith("☐")
    assert not result.startswith("🔴")
    assert not result.startswith("⭐")
    assert not result.startswith("💡")


@needs_display
def test_multiline_format(tmp_path, tk_root):
    """Multi-line text uses indented continuation lines."""
    import cogstash.app as cogstash_mod

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
    import cogstash.app as cogstash_mod

    test_file = tmp_path / "cogstash.md"
    app = cogstash_mod.CogStash(tk_root, cogstash_mod.CogStashConfig(output_file=test_file))
    result = app.append_note("   \n  \n  ")

    assert result is False
    assert not test_file.exists()


def test_merge_tags_builtin_defaults():
    """merge_tags with no custom tags returns built-in defaults."""
    from cogstash.app import DEFAULT_SMART_TAGS, CogStashConfig, merge_tags
    from cogstash.search import DEFAULT_TAG_COLORS
    config = CogStashConfig()
    smart, colors = merge_tags(config)
    assert smart == DEFAULT_SMART_TAGS
    assert colors == DEFAULT_TAG_COLORS


def test_merge_tags_add_new():
    """Custom tag merges alongside built-ins."""
    from cogstash.app import CogStashConfig, merge_tags
    config = CogStashConfig(tags={"work": {"emoji": "💼", "color": "#4A90D9"}})
    smart, colors = merge_tags(config)
    assert smart["work"] == "💼"
    assert colors["work"] == "#4A90D9"
    assert "todo" in smart  # built-in still present


def test_merge_tags_override_builtin():
    """User can override a built-in tag's emoji and color."""
    from cogstash.app import CogStashConfig, merge_tags
    config = CogStashConfig(tags={"todo": {"emoji": "✅", "color": "#00FF00"}})
    smart, colors = merge_tags(config)
    assert smart["todo"] == "✅"
    assert colors["todo"] == "#00FF00"


def test_parse_smart_tags_custom():
    """parse_smart_tags uses custom tags when provided."""
    from cogstash.app import parse_smart_tags
    custom = {"work": "💼", "todo": "☐"}
    result = parse_smart_tags("meeting notes #work", smart_tags=custom)
    assert result.startswith("💼")
    assert "#work" in result


def test_parse_smart_tags_default():
    """parse_smart_tags still works with defaults when no param given."""
    from cogstash.app import parse_smart_tags
    result = parse_smart_tags("buy milk #todo")
    assert result.startswith("☐")


def test_append_note_to_file(tmp_path):
    """append_note_to_file writes a timestamped note."""
    from cogstash.app import append_note_to_file
    out = tmp_path / "notes.md"
    result = append_note_to_file("hello world", out)
    assert result is True
    content = out.read_text(encoding="utf-8")
    assert "hello world" in content
    assert content.startswith("- [")


def test_append_note_to_file_smart_tags(tmp_path):
    """append_note_to_file applies smart tag emojis."""
    from cogstash.app import append_note_to_file
    out = tmp_path / "notes.md"
    custom = {"work": "💼"}
    append_note_to_file("meeting #work", out, smart_tags=custom)
    content = out.read_text(encoding="utf-8")
    assert "💼" in content


def test_append_note_to_file_multiline(tmp_path):
    """Multi-line notes get 2-space indented continuation."""
    from cogstash.app import append_note_to_file
    out = tmp_path / "notes.md"
    append_note_to_file("line one\nline two\nline three", out)
    content = out.read_text(encoding="utf-8")
    assert "  line two\n" in content
    assert "  line three\n" in content


def test_append_note_to_file_empty(tmp_path):
    """Empty text returns False and writes nothing."""
    from cogstash.app import append_note_to_file
    out = tmp_path / "notes.md"
    result = append_note_to_file("  ", out)
    assert result is False
    assert not out.exists()


def test_main_dispatches_version(monkeypatch, capsys):
    """main() handles --version before GUI launch."""
    import cogstash

    monkeypatch.setattr("sys.argv", ["cogstash", "--version"])
    cogstash.main()
    captured = capsys.readouterr()
    assert "cogstash" in captured.out.lower() and "0." in captured.out


def test_main_dispatches_version_with_cp1252_stdout(monkeypatch):
    """--version should not crash when packaged stdout cannot encode Unicode."""
    import cogstash

    capture = StrictEncodedStream("cp1252")
    monkeypatch.setattr("sys.argv", ["cogstash", "--version"])
    monkeypatch.setattr("sys.stdout", capture)
    monkeypatch.setattr(cogstash, "__version__", "0.0.0 → dev")

    cogstash.main()

    assert capture.getvalue().startswith("cogstash 0.0.0")


def test_app_main_startup_output_is_cp1252_safe(monkeypatch, tmp_path):
    """Startup status output should not crash on a cp1252-packaged console."""
    import types

    import cogstash
    import cogstash.ui.app as app_mod

    class FakeRoot:
        def wait_window(self, _win):
            raise AssertionError("startup test should not enter wizard flow")

        def mainloop(self):
            return None

    class FakeListener:
        def __init__(self, _mapping):
            self.started = False
            self.stopped = False

        def start(self):
            self.started = True

        def stop(self):
            self.stopped = True

    class FakeApp:
        def __init__(self, _root, _config):
            self.queue = object()

    class FakeGuard:
        def close(self):
            return None

    config = app_mod.CogStashConfig(
        output_file=tmp_path / "notes.md",
        log_file=tmp_path / "cogstash.log",
        last_seen_version=cogstash.__version__,
    )
    capture = StrictEncodedStream("cp1252")
    windows_mod = types.ModuleType("cogstash.ui.windows")
    windows_mod.WINDOWS_MUTEX_NAME = "Local\\CogStash.Test"
    windows_mod.acquire_single_instance = lambda _name: FakeGuard()

    monkeypatch.setattr(app_mod, "load_config", lambda _path: config)
    monkeypatch.setattr(app_mod, "configure_dpi", lambda: None)
    monkeypatch.setattr(app_mod.tk, "Tk", lambda: FakeRoot())
    monkeypatch.setattr(app_mod, "CogStash", FakeApp)
    monkeypatch.setattr(app_mod, "create_tray_icon", lambda _queue, _config: None)
    monkeypatch.setattr(app_mod.keyboard, "GlobalHotKeys", FakeListener)
    monkeypatch.setattr(
        app_mod.messagebox,
        "showinfo",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("startup test should not show duplicate-instance dialog")),
    )
    monkeypatch.setitem(sys.modules, "cogstash.ui.windows", windows_mod)
    monkeypatch.setattr("sys.stdout", capture)

    original_handlers = app_mod.logger.handlers[:]
    try:
        app_mod.main()
    finally:
        for handler in [h for h in app_mod.logger.handlers[:] if h not in original_handlers]:
            app_mod.logger.removeHandler(handler)
            try:
                handler.close()
            except Exception:
                pass
        for handler in original_handlers:
            if handler not in app_mod.logger.handlers:
                app_mod.logger.addHandler(handler)

    output = capture.getvalue()
    assert "CogStash is running." in output
    assert "Notes" in output
    assert str(config.output_file) in output


def test_app_main_refuses_duplicate_instance_before_startup(monkeypatch, tmp_path):
    """A second GUI launch should stop before creating another root/tray instance."""
    import types

    import cogstash
    import cogstash.ui.app as app_mod

    config = app_mod.CogStashConfig(
        output_file=tmp_path / "notes.md",
        log_file=tmp_path / "cogstash.log",
        last_seen_version=cogstash.__version__,
    )

    windows_mod = types.ModuleType("cogstash.ui.windows")
    windows_mod.WINDOWS_MUTEX_NAME = "Local\\CogStash.Test"
    windows_mod.acquire_single_instance = lambda _name: None

    monkeypatch.setattr(app_mod, "load_config", lambda _path: config)
    monkeypatch.setattr(app_mod, "configure_dpi", lambda: None)
    monkeypatch.setattr(app_mod.tk, "Tk", lambda: (_ for _ in ()).throw(AssertionError("should not create root")))
    monkeypatch.setitem(sys.modules, "cogstash.ui.windows", windows_mod)

    original_handlers = app_mod.logger.handlers[:]
    try:
        with patch("cogstash.ui.app.messagebox.showinfo"):
            app_mod.main()
    finally:
        for handler in [h for h in app_mod.logger.handlers[:] if h not in original_handlers]:
            app_mod.logger.removeHandler(handler)
            try:
                handler.close()
            except Exception:
                pass
        for handler in original_handlers:
            if handler not in app_mod.logger.handlers:
                app_mod.logger.addHandler(handler)


def test_app_reexports_core_helpers():
    import cogstash.app as app_mod
    import cogstash.core as core_mod

    assert app_mod.DEFAULT_SMART_TAGS is core_mod.DEFAULT_SMART_TAGS
    assert app_mod.CogStashConfig is core_mod.CogStashConfig
    assert app_mod.append_note_to_file is core_mod.append_note_to_file
    assert app_mod.get_default_config_path is core_mod.get_default_config_path
    assert app_mod.load_config is core_mod.load_config
    assert app_mod.save_config is core_mod.save_config
    assert app_mod.merge_tags is core_mod.merge_tags
