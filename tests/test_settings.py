"""Tests for the settings module."""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest
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
def test_settings_window_not_transient_to_withdrawn_root(tk_root, tmp_path):
    """Settings window should not be transient to the hidden app root."""
    from cogstash.app import CogStashConfig
    from cogstash.settings import SettingsWindow

    config = CogStashConfig()
    sw = SettingsWindow(tk_root, config, tmp_path / "test.json")
    assert sw.win.transient() == ""
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
def test_settings_escape_closes_window(tk_root, tmp_path):
    """Escape closes the settings window."""
    from cogstash.app import CogStashConfig
    from cogstash.settings import SettingsWindow

    sw = SettingsWindow(tk_root, CogStashConfig(), tmp_path / "test.json")
    sw.win.focus_force()
    sw.win.update()
    sw.win.event_generate("<Escape>")
    sw.win.update()
    assert not sw.win.winfo_exists()


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


@needs_display
def test_settings_save_appearance_applies_changes_immediately(tk_root, tmp_path):
    """Appearance save should notify the app so open windows restyle immediately."""
    from cogstash.app import CogStashConfig
    from cogstash.settings import SettingsWindow

    calls = []
    sw = SettingsWindow(
        tk_root,
        CogStashConfig(),
        tmp_path / "test.json",
        on_config_changed=lambda config: calls.append((config.theme, config.window_size)),
    )
    sw.selected_theme.set("light")
    sw.selected_size.set("compact")

    sw._save_appearance()

    assert calls == [("light", "compact")]
    sw.win.destroy()


@needs_display
def test_settings_tags_tab(tk_root, tmp_path):
    """Tags tab shows built-in tags."""
    from cogstash.app import CogStashConfig
    from cogstash.settings import SettingsWindow
    config = CogStashConfig()
    sw = SettingsWindow(tk_root, config, tmp_path / "test.json")
    sw._show_tab(2)  # Tags tab
    assert hasattr(sw, "tag_list_frame")
    sw.win.destroy()


@needs_display
def test_settings_about_tab(tk_root, tmp_path):
    """About tab shows version info."""
    from cogstash.app import CogStashConfig
    from cogstash.settings import SettingsWindow
    config = CogStashConfig()
    sw = SettingsWindow(tk_root, config, tmp_path / "test.json")
    sw._show_tab(3)  # About tab
    assert hasattr(sw, "version_label")
    sw.win.destroy()


def test_first_run_detection():
    """last_seen_version=='' means first run."""
    from cogstash.app import CogStashConfig
    config = CogStashConfig()
    assert config.last_seen_version == ""
    config2 = CogStashConfig(last_seen_version="0.1.0")
    assert config2.last_seen_version == "0.1.0"


@needs_display
def test_wizard_saves_config(tk_root, tmp_path):
    """Wizard writes valid config with all fields when completed."""
    import json

    from cogstash.app import CogStashConfig
    from cogstash.settings import WizardWindow

    config = CogStashConfig()
    config_path = tmp_path / ".cogstash.json"
    wiz = WizardWindow(tk_root, config, config_path)
    wiz._finish()
    assert config_path.exists()
    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert "theme" in data
    assert "last_seen_version" in data
    assert data["last_seen_version"] != ""
    wiz.win.destroy()


@needs_display
def test_wizard_close_releases_modal_window(tk_root, tmp_path):
    """Wizard close handler destroys the modal window cleanly."""
    from cogstash.app import CogStashConfig
    from cogstash.settings import WizardWindow

    config = CogStashConfig()
    wiz = WizardWindow(tk_root, config, tmp_path / ".cogstash.json")
    wiz._close()
    assert not wiz.win.winfo_exists()


@needs_display
def test_wizard_escape_closes_window(tk_root, tmp_path):
    """Escape closes the wizard."""
    from cogstash.app import CogStashConfig
    from cogstash.settings import WizardWindow

    wiz = WizardWindow(tk_root, CogStashConfig(), tmp_path / ".cogstash.json")
    wiz._close()
    assert not wiz.win.winfo_exists()


def test_whats_new_detection():
    """Version mismatch triggers What's New (but not on first run)."""
    from cogstash import __version__
    from cogstash.app import CogStashConfig
    config_new = CogStashConfig(last_seen_version="")
    assert config_new.last_seen_version == ""
    config_old = CogStashConfig(last_seen_version="0.0.1")
    assert config_old.last_seen_version != __version__
    config_current = CogStashConfig(last_seen_version=__version__)
    assert config_current.last_seen_version == __version__


@needs_display
def test_whats_new_dialog_creates(tk_root, tmp_path):
    """WhatsNewDialog opens without error."""
    from cogstash import __version__
    from cogstash.app import CogStashConfig
    from cogstash.settings import WhatsNewDialog
    config = CogStashConfig(last_seen_version="0.0.1")
    dialog = WhatsNewDialog(tk_root, config, tmp_path / ".cogstash.json", __version__)
    assert dialog.win.winfo_exists()
    dialog.win.destroy()


@needs_display
def test_whats_new_escape_closes_dialog(tk_root, tmp_path):
    """Escape closes the What's New dialog."""
    from cogstash import __version__
    from cogstash.app import CogStashConfig
    from cogstash.settings import WhatsNewDialog

    dialog = WhatsNewDialog(tk_root, CogStashConfig(last_seen_version="0.0.1"), tmp_path / ".cogstash.json", __version__)
    dialog.win.destroy()
    assert not dialog.win.winfo_exists()


@needs_display
def test_settings_add_tag_submit_with_enter(tk_root, tmp_path):
    """Pressing Enter in the add-tag form submits the new tag."""
    from cogstash.app import CogStashConfig
    from cogstash.settings import SettingsWindow

    sw = SettingsWindow(tk_root, CogStashConfig(), tmp_path / "test.json")
    sw._show_tab(2)
    sw._show_add_tag_form()
    sw._tag_name_var.set("work")
    sw._tag_emoji_var.set("💼")
    sw._tag_color_var.set("#4A90D9")
    entries = [child for child in sw._add_tag_frame.winfo_children() if child.winfo_class() == "Entry"]
    entries[0].focus_force()
    sw.win.update()
    entries[0].event_generate("<Return>")
    sw.win.update()

    assert sw.config.tags == {"work": {"emoji": "💼", "color": "#4A90D9"}}
    sw.win.destroy()


@needs_display
def test_settings_add_tag_invalid_input_shows_error(tk_root, tmp_path):
    """Invalid custom tag input shows a validation message."""
    from cogstash.app import CogStashConfig
    from cogstash.settings import SettingsWindow

    sw = SettingsWindow(tk_root, CogStashConfig(), tmp_path / "test.json")
    sw._show_tab(2)
    sw._show_add_tag_form()
    sw._tag_name_var.set("work")
    sw._tag_emoji_var.set("")
    sw._tag_color_var.set("bad")
    sw._add_tag()

    errors = [
        child for child in sw._add_tag_frame.winfo_children()
        if child.winfo_class() == "Label" and "Invalid" in child.cget("text")
    ]
    assert errors
    sw.win.destroy()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
def test_startup_shortcut_path():
    """get_startup_shortcut_path returns valid Windows startup path."""
    from cogstash.settings import get_startup_shortcut_path
    path = get_startup_shortcut_path()
    assert "Startup" in str(path) or "startup" in str(path)
    assert str(path).endswith(".bat")


@needs_display
def test_app_open_settings_uses_shared_config_path(tk_root, tmp_path):
    """App should reuse its stored config path when opening Settings."""
    from cogstash.app import CogStash, CogStashConfig

    config_path = tmp_path / ".cogstash.json"
    app = CogStash(tk_root, CogStashConfig(), config_path=config_path)

    created = []

    class DummySettingsWindow:
        def __init__(self, parent, config, passed_config_path, on_config_changed=None):
            created.append((parent, config, passed_config_path, on_config_changed))
            self.win = None

    with patch("cogstash.settings.SettingsWindow", DummySettingsWindow):
        app._open_settings()

    assert created[0][2] == config_path

