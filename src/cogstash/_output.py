from __future__ import annotations

import sys


def stream_supports_color(stream: object | None) -> bool:
    """Return True when a stream safely reports interactive TTY support."""
    if stream is None:
        return False
    isatty = getattr(stream, "isatty", None)
    if not callable(isatty):
        return False
    try:
        return bool(isatty())
    except Exception:
        return False


def stream_is_interactive(stream: object | None) -> bool:
    """Return True when stdin-like streams can be treated as interactive."""
    return stream_supports_color(stream)


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
