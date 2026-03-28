"""Tests for the settings module."""

from __future__ import annotations

from conftest import needs_display


@needs_display
def test_settings_queue_message(tk_root):
    """SETTINGS message in queue triggers _open_settings."""
    from cogstash.app import CogStash, CogStashConfig

    config = CogStashConfig()
    app = CogStash(tk_root, config)
    app.queue.put("SETTINGS")
    # Process one round of poll_queue
    opened = []
    app._open_settings = lambda: opened.append(True)
    app.poll_queue()
    assert len(opened) == 1
