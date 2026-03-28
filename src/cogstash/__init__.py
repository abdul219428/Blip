"""CogStash — A global hotkey brain dump."""

from __future__ import annotations

try:
    from importlib.metadata import version

    __version__ = version("cogstash")
except Exception:
    __version__ = "0.0.0-unknown"


def main():
    """Entry point for the cogstash command."""
    from cogstash.app import main as _main

    _main()
