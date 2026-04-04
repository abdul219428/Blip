"""Focused tests for cogstash.ui.app."""

from __future__ import annotations

import importlib
import logging
import sys
from unittest.mock import patch

from _helpers import StrictEncodedStream

from ui._support import needs_display


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
