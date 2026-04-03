from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> None:
    from . import cli_main
    from .windows import prepare_windows_cli_console

    prepare_windows_cli_console()
    cli_main(sys.argv[1:] if argv is None else argv)


if __name__ == "__main__":
    main()
