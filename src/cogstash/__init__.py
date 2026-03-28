"""CogStash — A global hotkey brain dump."""

from __future__ import annotations

try:
    from importlib.metadata import version

    __version__ = version("cogstash")
except Exception:
    __version__ = "0.0.0-unknown"


def main():
    """Entry point for the cogstash command."""
    import sys

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        # Handle --version before importing app (which pulls in pynput/tkinter)
        if arg in ("--version", "-V"):
            print(f"cogstash {__version__}")
            return
        # CLI subcommands — delegate without loading GUI stack
        if arg in ("recent", "search", "tags", "add", "edit", "delete", "export", "stats", "config"):
            from cogstash.cli import cli_main

            cli_main(sys.argv[1:])
            return

    from cogstash.app import main as _main

    _main()
