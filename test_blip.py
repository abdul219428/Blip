"""Tests for blip.py."""

import sys
from unittest.mock import patch
from pathlib import Path


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
