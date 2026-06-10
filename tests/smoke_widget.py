"""Smoke test: construct the widget, drive it with a fake engine, tear down.

Verifies Tk construction, meter drawing, and the settings panel without real
audio. A small window flashes on screen briefly.

Run: .venv/bin/python tests/smoke_widget.py
"""

import sys
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from xrapture.audio_engine import LEVEL_FLOOR_DB  # noqa: E402
from xrapture.settings import load_settings  # noqa: E402
from xrapture.widget import MeterWidget  # noqa: E402


class FakeEngine:
    """Minimal stand-in exposing exactly what the widget reads/calls."""

    def __init__(self):
        self.mic_level = -20.0
        self.system_level = LEVEL_FLOOR_DB
        self.system_available = False

    def start_monitoring(self):
        pass

    def stop_monitoring(self):
        pass


def main():
    root = tk.Tk()
    root.withdraw()
    engine = FakeEngine()

    widget = MeterWidget(root, engine, load_settings())
    widget.show()

    # animate the mic meter across levels
    for level in (-60.0, -30.0, -12.0, -3.0, 0.0):
        engine.mic_level = level
        root.update()

    # open settings panel (builds device menus + system-setup helper), then back
    widget._toggle_settings()
    root.update()
    assert widget._showing_settings
    widget._toggle_settings()
    root.update()
    assert not widget._showing_settings

    widget.close()
    root.update()
    root.destroy()
    print("SMOKE PASS: widget builds, meters draw, settings panel toggles")


if __name__ == "__main__":
    main()
