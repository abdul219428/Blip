"""Focused tests for cogstash.ui.app."""

from __future__ import annotations

import importlib
import logging
import sys
from unittest.mock import patch

from _helpers import StrictEncodedStream

from ui._support import needs_display


def _run_main_startup(monkeypatch, tmp_path, listener_cls):
    import types

    import cogstash
    import cogstash.ui.app as app_mod

    warnings: list[tuple[tuple, dict]] = []
    created_apps: list[bool] = []

    class FakeRoot:
        def wait_window(self, _win):
            raise AssertionError("startup test should not enter wizard flow")

        def mainloop(self):
            return None

    class FakeApp:
        def __init__(self, _root, _config):
            created_apps.append(True)
            self.queue = object()

    class FakeGuard:
        def close(self):
            return None

    config = app_mod.CogStashConfig(
        output_file=tmp_path / "notes.md",
        log_file=tmp_path / "cogstash.log",
        hotkey="<ctrl>+<alt>+space>",
        last_seen_version=cogstash.__version__,
        last_seen_installer_version=cogstash.__version__,
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
    monkeypatch.setattr(app_mod.keyboard, "GlobalHotKeys", listener_cls)
    monkeypatch.setattr(app_mod.messagebox, "showwarning", lambda *a, **kw: warnings.append((a, kw)))
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

    return config, capture.getvalue(), warnings, created_apps


@needs_display
def test_show_hide_state(tk_root):
    """show_window and hide_window toggle is_visible correctly."""
    import cogstash.ui.app as app_mod

    app = app_mod.CogStash(tk_root, app_mod.CogStashConfig())

    assert app.is_visible is False
    app.show_window()
    assert app.is_visible is True
    app.hide_window()
    assert app.is_visible is False


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


def test_app_main_shows_hotkey_warning_when_registration_fails(monkeypatch, tmp_path):
    """Startup should warn the user when the configured global hotkey cannot be registered."""

    class FailingListener:
        def __init__(self, _mapping):
            pass

        def start(self):
            raise OSError("hotkey already in use")

    config, _output, warnings, _created_apps = _run_main_startup(monkeypatch, tmp_path, FailingListener)

    assert len(warnings) == 1
    args, kwargs = warnings[0]
    warning_text = kwargs.get("message") if kwargs else None
    if warning_text is None:
        assert len(args) >= 2
        warning_text = args[1]
    assert config.hotkey in warning_text
    assert "capture is unavailable for this session" in warning_text
    assert str(config.log_file) in warning_text
    assert "another app may already be using the shortcut" in warning_text
    assert "platform permissions/accessibility hooks may be blocking registration" in warning_text
    assert "change the hotkey in config for now, then restart CogStash" in warning_text


def test_app_main_continues_startup_after_hotkey_registration_failure(monkeypatch, tmp_path):
    """Startup should still finish after showing the hotkey registration warning."""

    class FailingListener:
        def __init__(self, _mapping):
            pass

        def start(self):
            raise OSError("hotkey already in use")

    _config, output, warnings, created_apps = _run_main_startup(monkeypatch, tmp_path, FailingListener)

    assert len(warnings) == 1
    assert "CogStash is running." in output
    assert created_apps == [True]


def test_app_main_does_not_show_hotkey_warning_when_registration_succeeds(monkeypatch, tmp_path):
    """Healthy startup should not show the hotkey failure warning."""

    class FakeListener:
        def __init__(self, _mapping):
            self.started = False
            self.stopped = False

        def start(self):
            self.started = True

        def stop(self):
            self.stopped = True

    _config, _output, warnings, _created_apps = _run_main_startup(monkeypatch, tmp_path, FakeListener)

    assert warnings == []


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


def test_ui_app_import_falls_back_to_null_handler_when_file_handler_fails(monkeypatch):
    """Importing the UI app should not fail when the default log file is unavailable."""
    import cogstash.ui.app as app_mod

    def fake_file_handler(*_args, **_kwargs):
        raise PermissionError("read-only filesystem")

    monkeypatch.setattr(logging, "FileHandler", fake_file_handler)

    real_reload = importlib.reload
    reloaded = real_reload(app_mod)
    try:
        assert any(isinstance(handler, logging.NullHandler) for handler in reloaded.logger.handlers)
    finally:
        real_reload(app_mod)


def test_app_main_closes_removed_handlers(monkeypatch, tmp_path):
    """main() should close replaced handlers before installing a new configured one."""
    import types

    import cogstash
    import cogstash.ui.app as app_mod

    class FakeOldHandler(logging.Handler):
        def __init__(self):
            super().__init__()
            self.closed_flag = False

        def emit(self, _record):
            return None

        def close(self):
            self.closed_flag = True
            super().close()

    class FakeNewHandler(logging.Handler):
        def emit(self, _record):
            return None

    old_handler = FakeOldHandler()
    app_mod.logger.handlers[:] = [old_handler]

    config = app_mod.CogStashConfig(
        output_file=tmp_path / "notes.md",
        log_file=tmp_path / "cogstash.log",
        last_seen_version=cogstash.__version__,
    )
    windows_mod = types.ModuleType("cogstash.ui.windows")
    windows_mod.WINDOWS_MUTEX_NAME = "Local\\CogStash.Test"
    windows_mod.acquire_single_instance = lambda _name: None

    monkeypatch.setattr(app_mod, "load_config", lambda _path: config)
    monkeypatch.setattr(app_mod.logging, "FileHandler", lambda *_args, **_kwargs: FakeNewHandler())
    monkeypatch.setitem(sys.modules, "cogstash.ui.windows", windows_mod)
    monkeypatch.setattr(app_mod.messagebox, "showinfo", lambda *_args, **_kwargs: None)

    try:
        app_mod.main()
    finally:
        for handler in app_mod.logger.handlers[:]:
            app_mod.logger.removeHandler(handler)
            handler.close()

    assert old_handler.closed_flag is True


def test_app_main_installer_welcome_shown_for_installed_upgrade(monkeypatch, tmp_path):
    """When running as an installed app with a stale version, show the installer welcome dialog."""
    import types

    import cogstash.ui.app as app_mod
    import cogstash.ui.install_state as install_state_mod
    import cogstash.ui.settings as settings_mod

    welcome_calls: list = []

    config = app_mod.CogStashConfig(
        output_file=tmp_path / "notes.md",
        log_file=tmp_path / "cogstash.log",
        last_seen_version="0.3.0",
    )

    class FakeRoot:
        def mainloop(self):
            return None

    class FakeApp:
        def __init__(self, _root, _config):
            self.queue = object()

    class FakeGuard:
        def close(self):
            return None

    class FakeListener:
        def __init__(self, _mapping):
            pass

        def start(self):
            pass

        def stop(self):
            pass

    windows_mod = types.ModuleType("cogstash.ui.windows")
    windows_mod.WINDOWS_MUTEX_NAME = "Local\\CogStash.Test"
    windows_mod.acquire_single_instance = lambda _name: FakeGuard()

    monkeypatch.setattr(app_mod, "load_config", lambda _path: config)
    monkeypatch.setattr(app_mod, "configure_dpi", lambda: None)
    monkeypatch.setattr(app_mod.tk, "Tk", lambda: FakeRoot())
    monkeypatch.setattr(app_mod, "CogStash", FakeApp)
    monkeypatch.setattr(app_mod, "create_tray_icon", lambda _queue, _config: None)
    monkeypatch.setattr(app_mod.keyboard, "GlobalHotKeys", FakeListener)
    monkeypatch.setattr(app_mod, "save_config", lambda _c, _p: None)
    monkeypatch.setattr(install_state_mod, "is_installed_windows_run", lambda: True)
    monkeypatch.setattr(settings_mod, "InstallerWelcomeDialog", lambda *a, **kw: welcome_calls.append(a), raising=False)
    monkeypatch.setitem(sys.modules, "cogstash.ui.windows", windows_mod)

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

    assert len(welcome_calls) == 1, "InstallerWelcomeDialog should have been shown exactly once"


def test_app_main_installer_welcome_shown_for_first_installed_launch(monkeypatch, tmp_path):
    """An installed launch over an existing same-version config should still show the installer welcome once."""
    import types

    import cogstash
    import cogstash.ui.app as app_mod
    import cogstash.ui.install_state as install_state_mod
    import cogstash.ui.settings as settings_mod

    welcome_calls: list = []
    saved_configs: list = []

    config = app_mod.CogStashConfig(
        output_file=tmp_path / "notes.md",
        log_file=tmp_path / "cogstash.log",
        last_seen_version=cogstash.__version__,
        last_seen_installer_version="",
    )

    class FakeRoot:
        def mainloop(self):
            return None

    class FakeApp:
        def __init__(self, _root, _config):
            self.queue = object()

    class FakeGuard:
        def close(self):
            return None

    class FakeListener:
        def __init__(self, _mapping):
            pass

        def start(self):
            pass

        def stop(self):
            pass

    windows_mod = types.ModuleType("cogstash.ui.windows")
    windows_mod.WINDOWS_MUTEX_NAME = "Local\\CogStash.Test"
    windows_mod.acquire_single_instance = lambda _name: FakeGuard()

    monkeypatch.setattr(app_mod, "load_config", lambda _path: config)
    monkeypatch.setattr(app_mod, "configure_dpi", lambda: None)
    monkeypatch.setattr(app_mod.tk, "Tk", lambda: FakeRoot())
    monkeypatch.setattr(app_mod, "CogStash", FakeApp)
    monkeypatch.setattr(app_mod, "create_tray_icon", lambda _queue, _config: None)
    monkeypatch.setattr(app_mod.keyboard, "GlobalHotKeys", FakeListener)
    monkeypatch.setattr(app_mod, "save_config", lambda c, _p: saved_configs.append(c.last_seen_installer_version))
    monkeypatch.setattr(install_state_mod, "is_installed_windows_run", lambda: True)
    monkeypatch.setattr(settings_mod, "InstallerWelcomeDialog", lambda *a, **kw: welcome_calls.append(a), raising=False)
    monkeypatch.setitem(sys.modules, "cogstash.ui.windows", windows_mod)

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

    assert len(welcome_calls) == 1
    assert saved_configs == [cogstash.__version__]
