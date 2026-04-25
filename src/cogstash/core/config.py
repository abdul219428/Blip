from __future__ import annotations

import json
import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
_DEFAULT_HOTKEY = "<ctrl>+<shift>+<space>"
_DEFAULT_THEME = "tokyo-night"
_DEFAULT_WINDOW_SIZE = "default"
# Keep this in sync with THEMES in cogstash.ui.ui_shared. tests/core/test_config.py guards the key set.
VALID_THEMES = {"tokyo-night", "light", "dracula", "gruvbox", "mono"}
# Keep this in sync with WINDOW_SIZES in cogstash.ui.ui_shared. tests/core/test_config.py guards the key set.
VALID_WINDOW_SIZES = {"compact", "default", "wide"}

logger = logging.getLogger("cogstash")


@dataclass
class CogStashConfig:
    hotkey: str = _DEFAULT_HOTKEY
    output_file: Path | None = None
    log_file: Path | None = None
    theme: str = _DEFAULT_THEME
    window_size: str = _DEFAULT_WINDOW_SIZE
    tags: dict[str, dict[str, str]] | None = None
    launch_at_startup: bool = False
    last_seen_version: str = ""
    last_seen_installer_version: str = ""

    def __post_init__(self) -> None:
        if self.output_file is None:
            self.output_file = Path.home() / "cogstash.md"
        if self.log_file is None:
            self.log_file = Path.home() / "cogstash.log"


def get_default_config_path() -> Path:
    """Return the default config file path."""
    return Path.home() / ".cogstash.json"


def to_pretty_json(data: object) -> str:
    """Serialize data as readable UTF-8-safe JSON."""
    return json.dumps(data, indent=2, ensure_ascii=False)


def write_json_file(path: Path, data: object) -> None:
    """Write JSON data using the shared serialization contract."""
    path.write_text(to_pretty_json(data), encoding="utf-8")


def _validated_path_value(merged: dict[str, object], *, key: str, default: str) -> Path:
    """Return a config path field or a safe default when the stored value is invalid."""
    raw_value = merged.get(key, default)
    if not isinstance(raw_value, str):
        logger.warning("Invalid %s value %r — falling back to %s", key, raw_value, default)
        raw_value = default
    return Path(raw_value).expanduser()


def _validated_string_value(merged: dict[str, object], *, key: str, default: str) -> str:
    """Return a config string field or a safe default when the stored value is invalid."""
    raw_value = merged.get(key, default)
    if not isinstance(raw_value, str):
        logger.warning("Invalid %s value %r — falling back to %s", key, raw_value, default)
        return default
    return raw_value


def _validated_bool_value(merged: dict[str, object], *, key: str, default: bool) -> bool:
    """Return a config boolean field or a safe default when the stored value is invalid."""
    raw_value = merged.get(key, default)
    if not isinstance(raw_value, bool):
        logger.warning("Invalid %s value %r — falling back to %s", key, raw_value, default)
        return default
    return raw_value


def load_config(config_path: Path) -> CogStashConfig:
    """Load config from JSON file, merging with defaults."""
    default_output_file = str(Path.home() / "cogstash.md")
    default_log_file = str(Path.home() / "cogstash.log")
    defaults = {
        "hotkey": _DEFAULT_HOTKEY,
        "output_file": default_output_file,
        "log_file": default_log_file,
        "theme": _DEFAULT_THEME,
        "window_size": _DEFAULT_WINDOW_SIZE,
        "launch_at_startup": False,
        "last_seen_version": "",
        "last_seen_installer_version": "",
    }

    if not config_path.exists():
        logger.warning("No config file found — creating %s with defaults", config_path)
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            write_json_file(config_path, defaults)
        except OSError:
            logger.warning("Could not create config file %s", config_path, exc_info=True)
        return CogStashConfig()

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Bad config file %s: %s — using defaults", config_path, e)
        return CogStashConfig()

    if not isinstance(data, Mapping):
        logger.warning("Bad config file %s: top-level JSON value must be an object — using defaults", config_path)
        return CogStashConfig()

    merged = {**defaults, **data}

    if merged["theme"] not in VALID_THEMES:
        logger.warning("Unknown theme '%s' — falling back to %s", merged["theme"], _DEFAULT_THEME)
        merged["theme"] = _DEFAULT_THEME

    if merged["window_size"] not in VALID_WINDOW_SIZES:
        logger.warning("Unknown window_size '%s' — falling back to %s", merged["window_size"], _DEFAULT_WINDOW_SIZE)
        merged["window_size"] = _DEFAULT_WINDOW_SIZE

    raw_tags = data.get("tags", {})
    valid_tags: dict[str, dict[str, str]] = {}
    if isinstance(raw_tags, dict):
        for name, props in raw_tags.items():
            if not isinstance(props, dict):
                logger.warning("Tag '%s': expected object, skipping", name)
                continue
            emoji = props.get("emoji")
            color = props.get("color")
            if not emoji:
                logger.warning("Tag '%s': missing emoji, skipping", name)
                continue
            if not color or not _HEX_RE.match(color):
                logger.warning("Tag '%s': missing or invalid color, skipping", name)
                continue
            valid_tags[name] = {"emoji": emoji, "color": color}

    return CogStashConfig(
        hotkey=_validated_string_value(merged, key="hotkey", default=_DEFAULT_HOTKEY),
        output_file=_validated_path_value(merged, key="output_file", default=default_output_file),
        log_file=_validated_path_value(merged, key="log_file", default=default_log_file),
        theme=merged["theme"],
        window_size=merged["window_size"],
        tags=valid_tags if valid_tags else None,
        launch_at_startup=_validated_bool_value(merged, key="launch_at_startup", default=False),
        last_seen_version=str(merged.get("last_seen_version", "")),
        last_seen_installer_version=str(merged.get("last_seen_installer_version", "")),
    )


def save_config(config: CogStashConfig, config_path: Path) -> None:
    """Write config to JSON file."""
    data: dict[str, object] = {
        "hotkey": config.hotkey,
        "output_file": str(config.output_file),
        "log_file": str(config.log_file),
        "theme": config.theme,
        "window_size": config.window_size,
        "launch_at_startup": config.launch_at_startup,
        "last_seen_version": config.last_seen_version,
        "last_seen_installer_version": config.last_seen_installer_version,
    }
    if config.tags:
        data["tags"] = config.tags
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        write_json_file(config_path, data)
    except OSError:
        logger.error("Failed to save config to %s", config_path, exc_info=True)


__all__ = [
    "CogStashConfig",
    "VALID_THEMES",
    "VALID_WINDOW_SIZES",
    "get_default_config_path",
    "load_config",
    "save_config",
    "to_pretty_json",
    "write_json_file",
]
