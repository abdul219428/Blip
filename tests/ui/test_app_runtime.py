"""Focused runtime-contract tests for cogstash.ui.app_runtime."""

from __future__ import annotations

import queue


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

    class FakeListener:
        def __init__(self, mapping):
            self.mapping = dict(mapping)
            self.started = False

        def start(self):
            self.started = True

    monkeypatch.setattr(runtime.keyboard, "GlobalHotKeys", FakeListener)

    listener = runtime.start_hotkey_listener(app_queue, "<ctrl>+<alt>+space")

    hotkey_callback = next(iter(listener.mapping.values()))
    hotkey_callback()

    assert listener.started is True
    assert app_queue.get_nowait() is runtime.AppCommand.SHOW


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
