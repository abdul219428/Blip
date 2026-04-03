from __future__ import annotations

import sys
import types

import pytest

from cogstash.core import CogStashConfig


def test_cli_main_uses_core_config(monkeypatch, tmp_path, capsys):
    import cogstash.cli.main as main_mod

    config_path = tmp_path / "cogstash.json"
    notes_path = tmp_path / "notes.md"
    config = CogStashConfig(output_file=notes_path)
    calls: dict[str, object] = {}

    app_stub = types.ModuleType("cogstash.app")

    def _fail(name: str):
        raise AssertionError(f"cli_main should not access cogstash.app.{name}")

    app_stub.__getattr__ = _fail
    monkeypatch.setitem(sys.modules, "cogstash.app", app_stub)
    monkeypatch.setattr(main_mod, "get_default_config_path", lambda: config_path)
    def fake_load_config(path):
        calls["loaded_path"] = path
        return config

    monkeypatch.setattr(main_mod, "load_config", fake_load_config)
    monkeypatch.setattr(main_mod, "merge_tags", lambda loaded: ({}, {}))

    main_mod.cli_main(["recent"])

    output = capsys.readouterr().out
    assert "No notes found." in output
    assert calls["loaded_path"] == config_path


def test_cli_package_main_help_smoke():
    import cogstash.cli.__main__ as cli_module_main

    with pytest.raises(SystemExit) as exc:
        cli_module_main.main(["--help"])

    assert exc.value.code == 0
