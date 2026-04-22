"""Focused runtime-contract tests for cogstash.ui.app_runtime."""

from __future__ import annotations

import queue
from types import SimpleNamespace


def test_drain_queue_dispatches_supported_commands():
    import cogstash.ui.app_runtime as runtime

    app_queue: queue.Queue[runtime.AppCommand] = queue.Queue()
    app_queue.put(runtime.AppCommand.SHOW)
    app_queue.put(runtime.AppCommand.BROWSE)
    app_queue.put(runtime.AppCommand.SETTINGS)
    app_queue.put(runtime.AppCommand.QUIT)

    events: list[str] = []

    should_continue = runtime.drain_app_queue(
        app_queue,
        on_show=lambda: events.append("show"),
        on_browse=lambda: events.append("browse"),
        on_settings=lambda: events.append("settings"),
        on_quit=lambda: events.append("quit"),
    )

    assert events == ["show", "browse", "settings", "quit"]
    assert should_continue is False


def test_drain_queue_ignores_unknown_commands():
    import cogstash.ui.app_runtime as runtime

    app_queue: queue.Queue[object] = queue.Queue()
    app_queue.put("UNKNOWN")

    events: list[str] = []

    should_continue = runtime.drain_app_queue(
        app_queue,
        on_show=lambda: events.append("show"),
        on_browse=lambda: events.append("browse"),
        on_settings=lambda: events.append("settings"),
        on_quit=lambda: events.append("quit"),
    )

    assert events == []
    assert should_continue is True


def test_drain_queue_rejects_legacy_string_commands():
    import cogstash.ui.app_runtime as runtime

    app_queue: queue.Queue[object] = queue.Queue()
    app_queue.put("SHOW")

    events: list[str] = []

    should_continue = runtime.drain_app_queue(
        app_queue,
        on_show=lambda: events.append("show"),
        on_browse=lambda: events.append("browse"),
        on_settings=lambda: events.append("settings"),
        on_quit=lambda: events.append("quit"),
    )

    assert events == []
    assert should_continue is True


def test_drain_queue_handles_empty_queue():
    import cogstash.ui.app_runtime as runtime

    app_queue: queue.Queue[runtime.AppCommand] = queue.Queue()

    should_continue = runtime.drain_app_queue(
        app_queue,
        on_show=lambda: None,
        on_browse=lambda: None,
        on_settings=lambda: None,
        on_quit=lambda: None,
    )

    assert should_continue is True


def test_register_hotkey_listener_enqueues_show_command(monkeypatch):
    import cogstash.ui.app_runtime as runtime

    app_queue: queue.Queue[runtime.AppCommand] = queue.Queue()
    hotkey = "<ctrl>+<alt>+space"

    class FakeListener:
        def __init__(self, mapping):
            self.mapping = dict(mapping)
            self.started = False

        def start(self):
            self.started = True

    monkeypatch.setattr(runtime.keyboard, "GlobalHotKeys", FakeListener)

    listener = runtime.start_hotkey_listener(app_queue, hotkey)

    assert list(listener.mapping.keys()) == [hotkey]
    hotkey_callback = listener.mapping[hotkey]
    hotkey_callback()

    assert listener.started is True
    assert app_queue.get_nowait() is runtime.AppCommand.SHOW


def test_start_tray_icon_enqueues_shared_commands(monkeypatch):
    import sys

    import cogstash.ui.app_runtime as runtime

    app_queue: queue.Queue[runtime.AppCommand] = queue.Queue()
    created_items: list[SimpleNamespace] = []

    class FakeMenuItem:
        def __init__(self, label, command, enabled=True):
            self.label = label
            self.command = command
            self.enabled = enabled

    class FakeMenu:
        SEPARATOR = object()

        def __call__(self, *items):
            created_items.append(SimpleNamespace(items=items))
            return items

    class FakeIcon:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            self.started = False
            self.stopped = False

        def run(self):
            self.started = True

        def stop(self):
            self.stopped = True

    fake_pystray = SimpleNamespace(Menu=FakeMenu(), MenuItem=FakeMenuItem, Icon=FakeIcon)
    monkeypatch.setitem(sys.modules, "pystray", fake_pystray)
    monkeypatch.setattr(runtime, "_create_tray_image", lambda _theme: object())

    icon = runtime.start_tray_icon(
        app_queue,
        runtime.CogStashConfig(),
        themes={"tokyo-night": {"bg": "#000000", "fg": "#ffffff"}},
    )

    menu_items = created_items[0].items
    browse_item = menu_items[3]
    settings_item = menu_items[4]
    quit_item = menu_items[6]

    browse_item.command()
    assert app_queue.get_nowait() is runtime.AppCommand.BROWSE

    settings_item.command()
    assert app_queue.get_nowait() is runtime.AppCommand.SETTINGS

    quit_item.command(icon)
    assert icon.stopped is True
    assert app_queue.get_nowait() is runtime.AppCommand.QUIT


def test_start_runtime_returns_shutdown_safe_handles(monkeypatch):
    import cogstash.ui.app_runtime as runtime

    tray_icon = SimpleNamespace(stop=lambda: None)
    monkeypatch.setattr(runtime, "start_tray_icon", lambda *_args, **_kwargs: tray_icon)

    handles = runtime.start_runtime(
        queue.Queue(),
        runtime.CogStashConfig(),
        themes={"tokyo-night": {"bg": "#000000", "fg": "#ffffff"}},
    )

    assert handles.tray_icon is tray_icon
    assert handles.hotkey_listener is None

    runtime.shutdown_runtime(handles)


def test_shutdown_runtime_stops_listener_and_tray():
    import cogstash.ui.app_runtime as runtime

    stopped: list[str] = []

    class FakeStopHandle:
        def __init__(self, name: str):
            self.name = name

        def stop(self):
            stopped.append(self.name)

    runtime.shutdown_runtime(
        runtime.AppRuntimeHandles(
            tray_icon=FakeStopHandle("tray"),
            hotkey_listener=FakeStopHandle("hotkey"),
        )
    )

    assert set(stopped) == {"tray", "hotkey"}
    assert len(stopped) == 2


def test_shutdown_runtime_tolerates_missing_handles():
    import cogstash.ui.app_runtime as runtime

    runtime.shutdown_runtime(runtime.AppRuntimeHandles())
