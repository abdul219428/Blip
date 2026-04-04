from __future__ import annotations

import sys


def safe_print(*args: object, sep: str = " ", end: str = "\n", file: object | None = None) -> None:
    """Print text while degrading unencodable characters instead of crashing."""
    stream = sys.stdout if file is None else file
    if stream is None:
        return

    text = sep.join(str(arg) for arg in args) + end
    write = getattr(stream, "write", None)
    if not callable(write):
        raise AttributeError("Output stream does not support write().")

    try:
        write(text)
    except UnicodeEncodeError:
        encoding = getattr(stream, "encoding", None) or "ascii"
        try:
            fallback = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
        except LookupError:
            fallback = text.encode("ascii", errors="replace").decode("ascii")
        write(fallback)

    flush = getattr(stream, "flush", None)
    if callable(flush):
        flush()


__all__ = ["safe_print"]
