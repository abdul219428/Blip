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


def test_load_config_invalid_hotkey_type_falls_back_to_default(tmp_path, caplog):
    from cogstash.core import load_config

    cfg_file = tmp_path / "cogstash.json"
    cfg_file.write_text(json.dumps({"hotkey": []}), encoding="utf-8")

    with caplog.at_level("WARNING", logger="cogstash"):
        config = load_config(cfg_file)

    assert config.hotkey == "<ctrl>+<shift>+<space>"
    assert "Invalid hotkey" in caplog.text


def test_load_config_invalid_output_file_type_falls_back_to_default(tmp_path, caplog):
    from cogstash.core import load_config

    cfg_file = tmp_path / "cogstash.json"
    cfg_file.write_text(json.dumps({"output_file": []}), encoding="utf-8")

    with caplog.at_level("WARNING", logger="cogstash"):
        config = load_config(cfg_file)

    assert config.output_file == Path.home() / "cogstash.md"
    assert "Invalid output_file" in caplog.text


def test_load_config_invalid_log_file_type_falls_back_to_default(tmp_path, caplog):
    from cogstash.core import load_config

    cfg_file = tmp_path / "cogstash.json"
    cfg_file.write_text(json.dumps({"log_file": {"bad": True}}), encoding="utf-8")

    with caplog.at_level("WARNING", logger="cogstash"):
        config = load_config(cfg_file)

    assert config.log_file == Path.home() / "cogstash.log"
    assert "Invalid log_file" in caplog.text


def test_load_config_null_path_values_fall_back_to_defaults(tmp_path, caplog):
    from cogstash.core import load_config

    cfg_file = tmp_path / "cogstash.json"
    cfg_file.write_text(json.dumps({"output_file": None, "log_file": None}), encoding="utf-8")

    with caplog.at_level("WARNING", logger="cogstash"):
        config = load_config(cfg_file)

    assert config.output_file == Path.home() / "cogstash.md"
    assert config.log_file == Path.home() / "cogstash.log"
    assert "Invalid output_file" in caplog.text
    assert "Invalid log_file" in caplog.text


def test_load_config_launch_at_startup_true_round_trips(tmp_path):
    from cogstash.core import load_config

    cfg_file = tmp_path / "cogstash.json"
    cfg_file.write_text(json.dumps({"launch_at_startup": True}), encoding="utf-8")

    config = load_config(cfg_file)

    assert config.launch_at_startup is True


def test_load_config_invalid_launch_at_startup_string_falls_back_to_default(tmp_path, caplog):
    from cogstash.core import load_config

    cfg_file = tmp_path / "cogstash.json"
    cfg_file.write_text(json.dumps({"launch_at_startup": "false"}), encoding="utf-8")

    with caplog.at_level("WARNING", logger="cogstash"):
        config = load_config(cfg_file)

    assert config.launch_at_startup is False
    assert "Invalid launch_at_startup" in caplog.text


def test_load_config_invalid_launch_at_startup_object_falls_back_to_default(tmp_path, caplog):
    from cogstash.core import load_config

    cfg_file = tmp_path / "cogstash.json"
    cfg_file.write_text(json.dumps({"launch_at_startup": {"bad": True}}), encoding="utf-8")

    with caplog.at_level("WARNING", logger="cogstash"):
        config = load_config(cfg_file)

    assert config.launch_at_startup is False
    assert "Invalid launch_at_startup" in caplog.text


def test_load_config_invalid_launch_at_startup_null_falls_back_to_default(tmp_path, caplog):
    from cogstash.core import load_config

    cfg_file = tmp_path / "cogstash.json"
    cfg_file.write_text(json.dumps({"launch_at_startup": None}), encoding="utf-8")

    with caplog.at_level("WARNING", logger="cogstash"):
        config = load_config(cfg_file)

    assert config.launch_at_startup is False
    assert "Invalid launch_at_startup" in caplog.text


def test_load_config_non_object_json_list_falls_back_to_defaults(tmp_path, caplog):
    from cogstash.core import load_config

    cfg_file = tmp_path / "cogstash.json"
    cfg_file.write_text("[]", encoding="utf-8")

    with caplog.at_level("WARNING", logger="cogstash"):
        config = load_config(cfg_file)

    assert config.theme == "tokyo-night"
    assert config.output_file == Path.home() / "cogstash.md"
    assert "top-level JSON value must be an object" in caplog.text


def test_load_config_non_object_json_string_falls_back_to_defaults(tmp_path, caplog):
    from cogstash.core import load_config

    cfg_file = tmp_path / "cogstash.json"
    cfg_file.write_text('"hello"', encoding="utf-8")

    with caplog.at_level("WARNING", logger="cogstash"):
        config = load_config(cfg_file)

    assert config.theme == "tokyo-night"
    assert "top-level JSON value must be an object" in caplog.text


def test_load_config_non_object_json_number_falls_back_to_defaults(tmp_path, caplog):
    from cogstash.core import load_config

    cfg_file = tmp_path / "cogstash.json"
    cfg_file.write_text("42", encoding="utf-8")

    with caplog.at_level("WARNING", logger="cogstash"):
        config = load_config(cfg_file)

    assert config.theme == "tokyo-night"
    assert "top-level JSON value must be an object" in caplog.text


def test_load_config_non_object_json_null_falls_back_to_defaults(tmp_path, caplog):
    from cogstash.core import load_config

    cfg_file = tmp_path / "cogstash.json"
    cfg_file.write_text("null", encoding="utf-8")

    with caplog.at_level("WARNING", logger="cogstash"):
        config = load_config(cfg_file)

    assert config.theme == "tokyo-night"
    assert "top-level JSON value must be an object" in caplog.text


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


def test_to_pretty_json_preserves_unicode_and_indent():
    from cogstash.core.config import to_pretty_json

    payload = {"tags": {"focus": {"emoji": "cafe ☕", "color": "#ABCDEF"}}}

    assert to_pretty_json(payload) == '{\n  "tags": {\n    "focus": {\n      "emoji": "cafe ☕",\n      "color": "#ABCDEF"\n    }\n  }\n}'


def test_load_config_creates_default_file_with_shared_json_format(tmp_path):
    from cogstash.core import load_config
    from cogstash.core.config import to_pretty_json

    config_path = tmp_path / ".cogstash.json"

    load_config(config_path)

    expected = {
        "hotkey": "<ctrl>+<shift>+<space>",
        "output_file": str(Path.home() / "cogstash.md"),
        "log_file": str(Path.home() / "cogstash.log"),
        "theme": "tokyo-night",
        "window_size": "default",
        "launch_at_startup": False,
        "last_seen_version": "",
        "last_seen_installer_version": "",
    }
    assert config_path.read_text(encoding="utf-8") == to_pretty_json(expected)


def test_save_config_writes_pretty_json_with_unicode(tmp_path):
    from cogstash.core import CogStashConfig, save_config

    config = CogStashConfig(
        output_file=tmp_path / "notes.md",
        log_file=tmp_path / "cogstash.log",
        tags={"focus": {"emoji": "cafe ☕", "color": "#ABCDEF"}},
    )
    config_path = tmp_path / ".cogstash.json"

    save_config(config, config_path)

    written = config_path.read_text(encoding="utf-8")
    assert '"emoji": "cafe ☕"' in written
    assert "\n  " in written
    assert "\\u2615" not in written


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


def test_is_installed_windows_run_requires_marker(monkeypatch, tmp_path):
    import cogstash.ui.install_state as state_mod

    exe_dir = tmp_path / "portable"
    exe_dir.mkdir()
    exe_path = exe_dir / "CogStash.exe"
    exe_path.write_text("exe", encoding="utf-8")

    monkeypatch.setattr(state_mod.sys, "platform", "win32")
    monkeypatch.setattr(state_mod.sys, "frozen", True, raising=False)
    monkeypatch.setattr(state_mod.sys, "executable", str(exe_path))

    assert state_mod.is_installed_windows_run() is False


def test_is_installed_windows_run_true_with_marker(monkeypatch, tmp_path):
    import cogstash.ui.install_state as state_mod

    exe_dir = tmp_path / "installed"
    exe_dir.mkdir()
    exe_path = exe_dir / "CogStash.exe"
    exe_path.write_text("exe", encoding="utf-8")
    (exe_dir / ".cogstash-installed").write_text("installed", encoding="utf-8")

    monkeypatch.setattr(state_mod.sys, "platform", "win32")
    monkeypatch.setattr(state_mod.sys, "frozen", True, raising=False)
    monkeypatch.setattr(state_mod.sys, "executable", str(exe_path))

    assert state_mod.is_installed_windows_run() is True
