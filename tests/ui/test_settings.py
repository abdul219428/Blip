"""Focused tests for cogstash.ui.settings."""

from __future__ import annotations

import json
import sys

import pytest

from ui._support import needs_display


@needs_display
def test_settings_window_has_tabs(tk_root, tmp_path):
    """Settings window creates 4 tabs."""
    from cogstash.ui.app import CogStashConfig
    from cogstash.ui.settings import SettingsWindow

    sw = SettingsWindow(tk_root, CogStashConfig(), tmp_path / "test.json")
    assert hasattr(sw, "tab_buttons")
    assert len(sw.tab_buttons) == 4
    sw.win.destroy()


@needs_display
def test_settings_save_appearance_applies_changes_immediately(tk_root, tmp_path):
    """Appearance save should notify the app so open windows restyle immediately."""
    from cogstash.ui.app import CogStashConfig
    from cogstash.ui.settings import SettingsWindow

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
def test_wizard_saves_config(tk_root, tmp_path):
    """Wizard writes valid config with all fields when completed."""
    from cogstash.ui.app import CogStashConfig
    from cogstash.ui.settings import WizardWindow

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


@pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
def test_startup_shortcut_path():
    """get_startup_shortcut_path returns valid Windows startup path."""
    from cogstash.ui.settings import get_startup_shortcut_path

    path = get_startup_shortcut_path()
    assert "Startup" in str(path) or "startup" in str(path)
    assert str(path).endswith(".bat")
