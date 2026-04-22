"""Focused tests for cogstash.ui.settings."""

from __future__ import annotations

import json
import sys
from unittest.mock import patch

import pytest

from ui._support import needs_display


def _collect_label_text(widget):
    texts = []
    for child in widget.winfo_children():
        if child.winfo_class() == "Label":
            texts.append(child.cget("text"))
        texts.extend(_collect_label_text(child))
    return texts


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
def test_settings_shows_hotkey_warning_when_registration_failed(tk_root, tmp_path):
    from cogstash.ui.app import CogStashConfig
    from cogstash.ui.settings import SettingsWindow

    log_file = tmp_path / "cogstash.log"
    warning_text = (
        "Hotkey failed to register: <ctrl>+<shift>+<space>\n"
        "Global capture is unavailable until the issue is fixed and CogStash is restarted.\n"
        f"See the log file for details: {log_file}"
    )

    sw = SettingsWindow(
        tk_root,
        CogStashConfig(log_file=log_file),
        tmp_path / "test.json",
        hotkey_warning=warning_text,
    )
    sw.win.update_idletasks()
    labels = _collect_label_text(sw.tab_frames[0])
    all_text = "\n".join(labels)

    assert sw.win.winfo_height() > 450
    assert "Hotkey failed to register" in all_text
    assert "Global capture is unavailable until the issue is fixed and CogStash is restarted." in all_text
    assert str(log_file) in all_text
    assert "change the hotkey in Settings" not in all_text
    assert "edit the hotkey in Settings" not in all_text

    sw.win.destroy()


@needs_display
def test_settings_hides_hotkey_warning_when_session_is_healthy(tk_root, tmp_path):
    from cogstash.ui.app import CogStashConfig
    from cogstash.ui.settings import SettingsWindow

    sw = SettingsWindow(tk_root, CogStashConfig(), tmp_path / "test.json")
    labels = _collect_label_text(sw.tab_frames[0])

    assert not any("failed to register" in text for text in labels)

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
def test_settings_save_general_persists_hotkey_and_notifies_app(tk_root, tmp_path):
    """Saving General should persist an edited hotkey and notify the app."""
    from cogstash.ui.app import CogStashConfig
    from cogstash.ui.settings import SettingsWindow

    config_path = tmp_path / "test.json"
    calls = []
    sw = SettingsWindow(
        tk_root,
        CogStashConfig(),
        config_path,
        on_config_changed=lambda config: calls.append(config.hotkey),
    )
    sw.hotkey_var.set("<ctrl>+<alt>+h")

    sw._save_general()

    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert sw.config.hotkey == "<ctrl>+<alt>+h"
    assert data["hotkey"] == "<ctrl>+<alt>+h"
    assert calls == ["<ctrl>+<alt>+h"]
    sw.win.destroy()


@needs_display
def test_settings_invalid_hotkey_shows_error_and_does_not_save(tk_root, tmp_path):
    """Saving an invalid hotkey should show an error and leave config untouched."""
    from cogstash.ui.app import CogStashConfig
    from cogstash.ui.settings import SettingsWindow

    config_path = tmp_path / "test.json"
    sw = SettingsWindow(tk_root, CogStashConfig(), config_path)
    sw.hotkey_var.set("not-a-hotkey")

    with patch("tkinter.messagebox.showerror") as error_mock:
        sw._save_general()

    assert sw.config.hotkey == "<ctrl>+<shift>+<space>"
    assert not config_path.exists()
    error_mock.assert_called_once()
    sw.win.destroy()


@needs_display
def test_settings_test_hotkey_shows_success_for_valid_input(tk_root, tmp_path, monkeypatch):
    """Test Hotkey should confirm valid hotkey syntax and guidance."""
    from cogstash.ui.app import CogStashConfig
    from cogstash.ui.settings import SettingsWindow

    sw = SettingsWindow(tk_root, CogStashConfig(), tmp_path / "test.json")
    sw.hotkey_var.set("<ctrl>+<alt>+h")

    class FakeHotKey:
        @staticmethod
        def parse(value):
            assert value == "<ctrl>+<alt>+h"
            return ["parsed"]

    monkeypatch.setattr("cogstash.ui.settings.keyboard.HotKey", FakeHotKey)

    with patch("tkinter.messagebox.showinfo") as info_mock:
        sw._test_hotkey()

    info_mock.assert_called_once()
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


@needs_display
def test_wizard_finish_persists_edited_hotkey(tk_root, tmp_path):
    """Finishing the wizard should persist an edited hotkey."""
    from cogstash.ui.app import CogStashConfig
    from cogstash.ui.settings import WizardWindow

    config = CogStashConfig()
    config_path = tmp_path / ".cogstash.json"
    wiz = WizardWindow(tk_root, config, config_path)
    wiz.hotkey_var.set("<ctrl>+<alt>+h")

    wiz._finish()

    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert data["hotkey"] == "<ctrl>+<alt>+h"
    wiz.win.destroy()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
def test_startup_shortcut_path():
    """get_startup_shortcut_path returns valid Windows startup path."""
    from cogstash.ui.install_state import get_startup_shortcut_path

    path = get_startup_shortcut_path()
    assert "Startup" in str(path) or "startup" in str(path)
    assert str(path).endswith(".bat")


@needs_display
def test_settings_startup_script_state_reflects_disk(tk_root, tmp_path, monkeypatch):
    """Startup checkbox must reflect actual on-disk script presence, not just config value."""
    import cogstash.ui.install_state as state_mod
    from cogstash.ui.app import CogStashConfig
    from cogstash.ui.settings import SettingsWindow

    # Disk has the startup script but config says False (e.g. installer created .bat, config not yet synced)
    monkeypatch.setattr(state_mod, "startup_script_exists", lambda: True)
    monkeypatch.setattr("sys.platform", "win32")

    config = CogStashConfig(launch_at_startup=False)
    config_path = tmp_path / "test.json"
    sw = SettingsWindow(tk_root, config, config_path)

    assert sw.launch_var.get() is True, "checkbox should reflect disk state (True), not config (False)"
    assert config.launch_at_startup is True, "config should self-heal to the on-disk startup state"
    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert data["launch_at_startup"] is True, "self-healed startup state should be persisted to config"
    sw.win.destroy()


@needs_display
def test_wizard_records_installed_version_for_installed_runs(tk_root, tmp_path, monkeypatch):
    """Completing the full wizard on an installed build should also record the installed version marker."""
    import cogstash
    import cogstash.ui.install_state as state_mod
    from cogstash.ui.app import CogStashConfig
    from cogstash.ui.settings import WizardWindow

    monkeypatch.setattr(state_mod, "is_installed_windows_run", lambda: True)

    config = CogStashConfig()
    config_path = tmp_path / ".cogstash.json"
    wiz = WizardWindow(tk_root, config, config_path)
    wiz._finish()

    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert data["last_seen_version"] == cogstash.__version__
    assert data["last_seen_installer_version"] == cogstash.__version__
    wiz.win.destroy()


@needs_display
def test_installer_welcome_dialog_does_not_claim_path_is_changeable_in_settings(tk_root, tmp_path):
    """Installer welcome copy should not imply PATH can be changed from Settings."""
    from cogstash.ui.app import CogStashConfig
    from cogstash.ui.settings import InstallerWelcomeDialog

    dialog = InstallerWelcomeDialog(tk_root, CogStashConfig(), tmp_path / ".cogstash.json", "0.4.0")
    labels = [child.cget("text") for child in dialog.win.winfo_children() if child.winfo_class() == "Label"]

    assert any("PATH option is available during installation." in text for text in labels)
    assert not any("PATH can be changed by re-running the installer" in text for text in labels)
    assert not any("Startup and PATH settings can be changed in Settings" in text for text in labels)

    dialog.win.destroy()
