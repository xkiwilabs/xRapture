"""Filesystem and subprocess helpers that must behave both for a normal Python
run and inside a frozen PyInstaller app.

Two things differ when frozen:

* settings can't live next to the (read-only, bundled) source — they go to a
  per-user config directory instead;
* child UI processes (widget / file picker / progress) can't be launched as
  ``python some_script.py`` — ``sys.executable`` is the app itself, so children
  re-launch it with a ``--role`` flag (dispatched in ``__main__``).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "xRapture"


def config_dir() -> Path:
    """Per-user config directory, created if missing.

    macOS: ``~/Library/Application Support/xRapture``; Windows: ``%APPDATA%/xRapture``;
    Linux/other: ``$XDG_CONFIG_HOME/xrapture`` (or ``~/.config/xrapture``).
    """
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    folder = base / (APP_NAME if sys.platform != "linux" else APP_NAME.lower())
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_command() -> list[str]:
    """Command that starts a fresh menu-bar app (used by Quit & Relaunch)."""
    return [sys.executable] if _frozen() else [sys.executable, "-m", "xrapture"]


def child_command(role: str, *extra: str) -> list[str]:
    """Command that launches a child UI process in the given ``role``.

    Works frozen (re-run the app binary with ``--role``) or not (``python -m
    xrapture --role ...``).
    """
    if _frozen():
        return [sys.executable, "--role", role, *extra]
    return [sys.executable, "-m", "xrapture", "--role", role, *extra]
