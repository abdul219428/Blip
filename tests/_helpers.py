"""Shared non-UI test helpers."""

from __future__ import annotations


class CaptureStream:
    def __init__(self):
        self.parts = []

    def write(self, text):
        self.parts.append(text)
        return len(text)

    def flush(self):
        pass

    def getvalue(self):
        return "".join(self.parts)


class StrictEncodedStream(CaptureStream):
    def __init__(self, encoding: str):
        super().__init__()
        self.encoding = encoding

    def write(self, text):
        text.encode(self.encoding)
        return super().write(text)
