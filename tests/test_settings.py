"""Tests for the settings module."""

from __future__ import annotations

from conftest import needs_display


@needs_display
def test_settings_queue_message(tk_root):
    """SETTINGS message in queue triggers _open_settings."""
    from cogstash.app import CogStash, CogStashConfig

    config = CogStashConfig()
    app = CogStash(tk_root, config)
    app.queue.put("SETTINGS")
    # Process one round of poll_queue
    opened = []
    app._open_settings = lambda: opened.append(True)
    app.poll_queue()
    assert len(opened) == 1


@needs_display
def test_settings_window_has_tabs(tk_root, tmp_path):
    """Settings window creates 4 tabs."""
    from cogstash.app import CogStashConfig
    from cogstash.settings import SettingsWindow
    config = CogStashConfig()
    sw = SettingsWindow(tk_root, config, tmp_path / "test.json")
    assert hasattr(sw, "tab_buttons")
    assert len(sw.tab_buttons) == 4
    sw.win.destroy()


@needs_display
def test_settings_general_tab_widgets(tk_root, tmp_path):
    """General tab has hotkey label, notes file entry, and launch checkbox."""
    from cogstash.app import CogStashConfig
    from cogstash.settings import SettingsWindow
    config = CogStashConfig()
    sw = SettingsWindow(tk_root, config, tmp_path / "test.json")
    assert hasattr(sw, "notes_file_var")
    assert hasattr(sw, "launch_var")
    sw.win.destroy()


@needs_display
def test_settings_appearance_tab(tk_root, tmp_path):
    """Appearance tab has theme swatches and window size options."""
    from cogstash.app import CogStashConfig
    from cogstash.settings import SettingsWindow
    config = CogStashConfig()
    sw = SettingsWindow(tk_root, config, tmp_path / "test.json")
    assert hasattr(sw, "selected_theme")
    assert sw.selected_theme.get() == "tokyo-night"
    assert hasattr(sw, "selected_size")
    assert sw.selected_size.get() == "default"
    sw.win.destroy()

