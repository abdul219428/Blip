"""Tests for blip.py."""

import sys
from unittest.mock import patch
from pathlib import Path
import tkinter as tk
import re


def test_platform_font_windows():
    with patch.object(sys, "platform", "win32"):
        from blip import platform_font
        result = platform_font()
        assert result == "Segoe UI"


def test_platform_font_macos():
    with patch.object(sys, "platform", "darwin"):
        from blip import platform_font
        result = platform_font()
        assert result == "Helvetica Neue"


def test_platform_font_linux():
    with patch.object(sys, "platform", "linux"):
        from blip import platform_font
        result = platform_font()
        assert result == "sans-serif"


def test_platform_font_unknown():
    with patch.object(sys, "platform", "freebsd"):
        from blip import platform_font
        result = platform_font()
        assert result == "TkDefaultFont"


def test_append_note_creates_file(tmp_path):
    """append_note creates the file and writes the correct format."""
    import blip as blip_mod

    test_file = tmp_path / "blip.md"
    original = blip_mod.OUTPUT_FILE
    blip_mod.OUTPUT_FILE = test_file

    try:
        root = tk.Tk()
        root.withdraw()
        app = blip_mod.Blip(root)
        result = app.append_note("test note")
        root.destroy()

        assert result is True
        content = test_file.read_text(encoding="utf-8")
        assert "test note" in content
        assert re.match(r"- \[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\] test note\n", content)
    finally:
        blip_mod.OUTPUT_FILE = original


def test_append_note_appends(tmp_path):
    """Multiple notes are appended, not overwritten."""
    import blip as blip_mod

    test_file = tmp_path / "blip.md"
    original = blip_mod.OUTPUT_FILE
    blip_mod.OUTPUT_FILE = test_file

    try:
        root = tk.Tk()
        root.withdraw()
        app = blip_mod.Blip(root)
        app.append_note("first")
        app.append_note("second")
        root.destroy()

        lines = test_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2
        assert "first" in lines[0]
        assert "second" in lines[1]
    finally:
        blip_mod.OUTPUT_FILE = original


def test_append_note_error_handling(tmp_path):
    """append_note returns False and logs on write failure."""
    import blip as blip_mod

    original = blip_mod.OUTPUT_FILE
    blip_mod.OUTPUT_FILE = Path("\\\\nonexistent_server_xyz\\share\\blip.md")

    try:
        root = tk.Tk()
        root.withdraw()
        app = blip_mod.Blip(root)
        result = app.append_note("should fail")
        root.destroy()

        assert result is False
    finally:
        blip_mod.OUTPUT_FILE = original
