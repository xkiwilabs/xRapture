"""Settings persistence for xRapture.

Loads and saves user settings to ``settings.json`` in the per-user config
directory (so it works even when the app is a read-only bundle). Missing or
unknown keys fall back to ``DEFAULTS`` so a partial or older file still loads.
"""

from __future__ import annotations

import json
from pathlib import Path

from .paths import config_dir

SETTINGS_PATH = config_dir() / "settings.json"

DEFAULTS = {
    "output_folder": "~/Documents/xRapture",
    "model_size": "base",
    "auto_transcribe": True,
    # Mic device by NAME (stable across CoreAudio reshuffles); null = system default.
    # Legacy integer indices are still accepted but resolved/validated at open time.
    "input_device": None,
    # System-audio capture by device NAME (e.g. "BlackHole 2ch"). null = auto-detect.
    "system_device": None,
    # How mic + system audio are written: stereo_split | mixed_mono | separate_files
    "track_layout": "stereo_split",
}


class Settings:
    """Dict-backed settings with disk persistence and sensible defaults."""

    def __init__(self, values: dict | None = None):
        # Start from defaults, then overlay only recognised keys.
        self._values = dict(DEFAULTS)
        if values:
            self._values.update({k: v for k, v in values.items() if k in DEFAULTS})

    def __getitem__(self, key):
        return self._values[key]

    def __setitem__(self, key, value):
        self._values[key] = value

    def get(self, key, default=None):
        return self._values.get(key, default)

    @property
    def output_folder(self) -> Path:
        """Resolved (``~`` expanded) output folder, created if missing."""
        folder = Path(self._values["output_folder"]).expanduser()
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    @property
    def model_size(self) -> str:
        return self._values["model_size"]

    @property
    def auto_transcribe(self) -> bool:
        return bool(self._values["auto_transcribe"])

    @property
    def input_device(self):
        return self._values["input_device"]

    @property
    def system_device(self):
        return self._values["system_device"]

    @property
    def track_layout(self) -> str:
        return self._values["track_layout"]

    def as_dict(self) -> dict:
        return dict(self._values)

    def save(self) -> None:
        SETTINGS_PATH.write_text(json.dumps(self._values, indent=2))


def load_settings() -> Settings:
    """Load settings from disk, creating a defaults file if none exists."""
    if SETTINGS_PATH.exists():
        try:
            values = json.loads(SETTINGS_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            # Corrupt or unreadable — fall back to defaults rather than crash.
            values = {}
        return Settings(values)

    settings = Settings()
    settings.save()  # write a starter file so users can find and edit it
    return settings
