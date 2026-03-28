"""CogStash — A global hotkey brain dump."""

from __future__ import annotations

try:
    from importlib.metadata import version

    __version__ = version("cogstash")
except Exception:
    __version__ = "0.0.0-unknown"


def main() -> None:
    """Entry point for the cogstash command."""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] in ("--version", "-V"):
        from cogstash._output import safe_print

        safe_print(f"cogstash {__version__}")
        return

    from cogstash.__main__ import main as entry_main

    entry_main()
