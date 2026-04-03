"""Allow running CogStash with `python -m cogstash`."""

from __future__ import annotations

import sys


def main() -> None:
    if len(sys.argv) > 1:
        from cogstash.cli import cli_main
        from cogstash.cli.windows import prepare_windows_cli_console

        prepare_windows_cli_console()
        cli_main(sys.argv[1:])
        return

    from cogstash.app import main as app_main

    app_main()


if __name__ == "__main__":
    main()
