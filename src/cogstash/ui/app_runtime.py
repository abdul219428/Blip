"""Runtime boundary for CogStash UI queue and background integrations."""

from __future__ import annotations

import logging
import queue
import sys
import threading
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from types import SimpleNamespace
from typing import Callable

from cogstash.core import CogStashConfig
from cogstash.ui import windows_runtime

try:
    from pynput import keyboard
except Exception:  # pragma: no cover - exercised only when dependency is absent
    keyboard = SimpleNamespace(GlobalHotKeys=None, HotKey=SimpleNamespace(parse=lambda _value: None))

logger = logging.getLogger("cogstash")


class AppCommand(str, Enum):
    """Commands that background UI integrations can send to the Tk thread."""

    SHOW = "SHOW"
    BROWSE = "BROWSE"
    SETTINGS = "SETTINGS"
    QUIT = "QUIT"


@dataclass
class AppRuntimeHandles:
    """Resources that need coordinated shutdown."""

    tray_icon: object | None = None
    hotkey_listener: object | None = None


def enqueue_command(app_queue: queue.Queue[AppCommand], command: AppCommand) -> None:
    """Put a runtime command onto the shared UI queue."""

    app_queue.put(command)


def drain_app_queue(
    app_queue: queue.Queue[object],
    *,
    on_show: Callable[[], None],
    on_browse: Callable[[], None],
    on_settings: Callable[[], None],
    on_quit: Callable[[], None],
) -> bool:
    """Drain pending commands and dispatch them through explicit callbacks.

    Returns False when QUIT is observed so the caller can stop rescheduling the
    poll loop.
    """

    while True:
        try:
            command = app_queue.get_nowait()
        except queue.Empty:
            return True

        if command is AppCommand.SHOW:
            on_show()
        elif command is AppCommand.BROWSE:
            on_browse()
        elif command is AppCommand.SETTINGS:
            on_settings()
        elif command is AppCommand.QUIT:
            on_quit()
            return False
        else:
            logger.warning("Ignoring unknown app command: %r", command)


def start_hotkey_listener(
    app_queue: queue.Queue[AppCommand],
    hotkey: str,
):
    """Start the global hotkey listener that enqueues the SHOW command."""

    if not hasattr(keyboard, "GlobalHotKeys") or keyboard.GlobalHotKeys is None:
        raise RuntimeError("pynput keyboard hotkeys are unavailable")

    listener = keyboard.GlobalHotKeys({hotkey: lambda: enqueue_command(app_queue, AppCommand.SHOW)})
    listener.start()
    return listener


def _create_tray_image(theme: dict[str, str]):
    """Build the tray icon image, using the bundled asset when available."""

    from PIL import Image, ImageDraw, ImageFont

    def hex_to_rgba(hex_color: str) -> tuple[int, int, int, int]:
        value = hex_color.lstrip("#")
        return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4)) + (255,)

    img = None
    if getattr(sys, "frozen", False):
        bundle_dir = Path(getattr(sys, "_MEIPASS", "."))
        icon_path = bundle_dir / "assets" / "cogstash_icon.png"
        if icon_path.exists():
            img = Image.open(icon_path).resize((64, 64))

    if img is None:
        img = Image.new("RGBA", (64, 64), hex_to_rgba(theme["bg"]))
        draw = ImageDraw.Draw(img)
        try:
            font: ImageFont.FreeTypeFont | ImageFont.ImageFont = ImageFont.truetype("arial", 40)
        except OSError:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), "⚡", font=font)
        x = (64 - (bbox[2] - bbox[0])) // 2 - bbox[0]
        y = (64 - (bbox[3] - bbox[1])) // 2 - bbox[1]
        draw.text((x, y), "⚡", fill=hex_to_rgba(theme["fg"]), font=font)

    return img


def start_tray_icon(
    app_queue: queue.Queue[AppCommand],
    config: CogStashConfig,
    *,
    themes: dict[str, dict[str, str]],
):
    """Start the system tray icon on a daemon thread, if dependencies exist."""

    try:
        import pystray
    except ImportError:
        logger.warning("pystray or Pillow not installed — skipping tray icon")
        return None

    theme = themes[config.theme]
    img = _create_tray_image(theme)

    def open_notes() -> None:
        assert config.output_file is not None, "output_file should be set by __post_init__"
        windows_runtime.open_target_in_shell(str(config.output_file))

    def browse_notes() -> None:
        enqueue_command(app_queue, AppCommand.BROWSE)

    def open_settings() -> None:
        enqueue_command(app_queue, AppCommand.SETTINGS)

    def quit_app(icon) -> None:
        icon.stop()
        enqueue_command(app_queue, AppCommand.QUIT)

    assert config.output_file is not None, "output_file should be set by __post_init__"
    menu = pystray.Menu(
        pystray.MenuItem("CogStash ⚡", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(f"Open {config.output_file.name}", lambda: open_notes()),
        pystray.MenuItem("Browse Notes", lambda: browse_notes()),
        pystray.MenuItem("Settings", lambda: open_settings()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", quit_app),
    )

    icon = pystray.Icon("cogstash", img, "CogStash", menu)
    threading.Thread(target=icon.run, daemon=True).start()
    return icon


def start_runtime(
    app_queue: queue.Queue[AppCommand],
    config: CogStashConfig,
    *,
    themes: dict[str, dict[str, str]],
) -> AppRuntimeHandles:
    """Start runtime integrations and return their shutdown handles."""

    return AppRuntimeHandles(tray_icon=start_tray_icon(app_queue, config, themes=themes))


def shutdown_runtime(handles: AppRuntimeHandles) -> None:
    """Stop runtime integrations if they were started."""

    if handles.tray_icon is not None:
        handles.tray_icon.stop()
    if handles.hotkey_listener is not None:
        handles.hotkey_listener.stop()
