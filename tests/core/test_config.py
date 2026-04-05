from __future__ import annotations

import json
from pathlib import Path


def test_core_exports_note_and_config_symbols():
    from cogstash.core import CogStashConfig, Note, load_config, parse_notes

    assert CogStashConfig is not None
    assert Note is not None
    assert load_config is not None
    assert parse_notes is not None


def test_load_config_defaults(tmp_path):
    from cogstash.core import CogStashConfig, load_config

    config = load_config(tmp_path / "nonexistent.json")

    assert isinstance(config, CogStashConfig)
    assert config.hotkey == "<ctrl>+<shift>+<space>"
    assert config.theme == "tokyo-night"
    assert config.window_size == "default"
    assert (tmp_path / "nonexistent.json").exists()


def test_load_config_partial(tmp_path):
    from cogstash.core import load_config

    cfg_file = tmp_path / "cogstash.json"
    cfg_file.write_text(json.dumps({"theme": "dracula"}), encoding="utf-8")

    config = load_config(cfg_file)

    assert config.theme == "dracula"
    assert config.hotkey == "<ctrl>+<shift>+<space>"


def test_load_config_malformed(tmp_path):
    from cogstash.core import load_config

    cfg_file = tmp_path / "cogstash.json"
    cfg_file.write_text("{bad json!!!", encoding="utf-8")

    config = load_config(cfg_file)

    assert config.theme == "tokyo-night"


def test_load_config_unknown_theme(tmp_path):
    from cogstash.core import load_config

    cfg_file = tmp_path / "cogstash.json"
    cfg_file.write_text(json.dumps({"theme": "nonexistent"}), encoding="utf-8")

    config = load_config(cfg_file)

    assert config.theme == "tokyo-night"


def test_load_config_unknown_window_size(tmp_path):
    from cogstash.core import load_config

    cfg_file = tmp_path / "cogstash.json"
    cfg_file.write_text(json.dumps({"window_size": "giant"}), encoding="utf-8")

    config = load_config(cfg_file)

    assert config.window_size == "default"


def test_get_default_config_path_uses_home(monkeypatch, tmp_path):
    import cogstash.core as core_mod
    import cogstash.core.config as config_mod

    monkeypatch.setattr(config_mod.Path, "home", lambda: tmp_path)

    assert core_mod.get_default_config_path() == tmp_path / ".cogstash.json"


def test_load_config_custom_tags(tmp_path):
    from cogstash.core import load_config

    cfg_path = tmp_path / "cogstash.json"
    cfg_path.write_text(
        json.dumps({"tags": {"work": {"emoji": "💼", "color": "#4A90D9"}}}),
        encoding="utf-8",
    )

    config = load_config(cfg_path)

    assert config.tags == {"work": {"emoji": "💼", "color": "#4A90D9"}}


def test_load_config_invalid_tag_skipped(tmp_path):
    from cogstash.core import load_config

    cfg_path = tmp_path / "cogstash.json"
    cfg_path.write_text(
        json.dumps(
            {
                "tags": {
                    "good": {"emoji": "✅", "color": "#00FF00"},
                    "bad_no_emoji": {"color": "#FF0000"},
                    "bad_no_color": {"emoji": "❌"},
                    "bad_hex": {"emoji": "❌", "color": "not-hex"},
                }
            }
        ),
        encoding="utf-8",
    )

    config = load_config(cfg_path)

    assert config.tags == {"good": {"emoji": "✅", "color": "#00FF00"}}


def test_config_new_fields_defaults(tmp_path):
    from cogstash.core import load_config

    config = load_config(tmp_path / ".cogstash.json")

    assert config.launch_at_startup is False
    assert config.last_seen_version == ""
    assert config.last_seen_installer_version == ""


def test_config_new_fields_roundtrip(tmp_path):
    from cogstash.core import load_config

    config_path = tmp_path / ".cogstash.json"
    config_path.write_text(
        json.dumps(
            {
                "launch_at_startup": True,
                "last_seen_version": "0.1.0",
                "last_seen_installer_version": "0.1.0",
                "theme": "dracula",
            }
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.launch_at_startup is True
    assert config.last_seen_version == "0.1.0"
    assert config.last_seen_installer_version == "0.1.0"
    assert config.theme == "dracula"


def test_save_config(tmp_path):
    from cogstash.core import CogStashConfig, save_config

    config = CogStashConfig(
        output_file=tmp_path / "notes.md",
        log_file=tmp_path / "cogstash.log",
        theme="dracula",
        window_size="wide",
        last_seen_version="0.2.0",
        last_seen_installer_version="0.2.0",
    )
    config_path = tmp_path / ".cogstash.json"

    save_config(config, config_path)

    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert data["theme"] == "dracula"
    assert data["window_size"] == "wide"
    assert data["last_seen_version"] == "0.2.0"
    assert data["last_seen_installer_version"] == "0.2.0"
    assert data["launch_at_startup"] is False
    assert Path(data["output_file"]) == tmp_path / "notes.md"


def test_valid_theme_and_window_size_sets_match_ui_runtime():
    import cogstash.core.config as config_mod
    import cogstash.ui.app as app_mod

    assert config_mod.VALID_THEMES == set(app_mod.THEMES)
    assert config_mod.VALID_WINDOW_SIZES == set(app_mod.WINDOW_SIZES)


# ── Installer-onboarding state ────────────────────────────────────────────────


def test_config_installer_onboarding_not_shown_for_new_user():
    """should_show_installer_welcome returns False when no version recorded (first-run case)."""
    from unittest.mock import patch

    from cogstash.core.config import CogStashConfig
    from cogstash.ui.install_state import should_show_installer_welcome

    config = CogStashConfig(last_seen_version="", last_seen_installer_version="")
    with patch("cogstash.ui.install_state.is_installed_windows_run", return_value=True):
        assert should_show_installer_welcome(config, "0.4.0") is False


def test_config_installer_onboarding_shown_for_first_installed_launch():
    """should_show_installer_welcome returns True when an existing config has never seen the installed build."""
    from unittest.mock import patch

    from cogstash.core.config import CogStashConfig
    from cogstash.ui.install_state import should_show_installer_welcome

    config = CogStashConfig(last_seen_version="0.4.0", last_seen_installer_version="")
    with patch("cogstash.ui.install_state.is_installed_windows_run", return_value=True):
        assert should_show_installer_welcome(config, "0.4.0") is True


def test_config_installer_onboarding_not_shown_when_version_matches():
    """should_show_installer_welcome returns False when already up to date."""
    from unittest.mock import patch

    from cogstash.core.config import CogStashConfig
    from cogstash.ui.install_state import should_show_installer_welcome

    config = CogStashConfig(last_seen_version="0.4.0", last_seen_installer_version="0.4.0")
    with patch("cogstash.ui.install_state.is_installed_windows_run", return_value=True):
        assert should_show_installer_welcome(config, "0.4.0") is False


def test_config_installer_onboarding_not_shown_for_non_installed_run():
    """should_show_installer_welcome returns False when not running as installed app."""
    from unittest.mock import patch

    from cogstash.core.config import CogStashConfig
    from cogstash.ui.install_state import should_show_installer_welcome

    config = CogStashConfig(last_seen_version="0.3.0", last_seen_installer_version="")
    with patch("cogstash.ui.install_state.is_installed_windows_run", return_value=False):
        assert should_show_installer_welcome(config, "0.4.0") is False
