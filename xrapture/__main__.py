"""Entry point with role dispatch.

``xrapture`` (or ``python -m xrapture``) with no arguments runs the menu-bar app.
``--role {widget,filepicker,progress}`` runs one of the child UI processes. This
single dispatch is what lets the multi-process design work inside a frozen
PyInstaller app, where children re-launch the same executable with ``--role``
(see ``paths.child_command``).
"""

from __future__ import annotations

import sys


def main() -> None:
    argv = sys.argv[1:]
    if argv and argv[0] == "--role":
        role = argv[1] if len(argv) > 1 else ""
        rest = argv[2:]
        if role == "widget":
            from .widget import main as run
            run()
        elif role == "filepicker":
            from .filepicker import main as run
            run()
        elif role == "progress":
            from .progress import main as run
            run(rest[0] if rest else "audio")
        elif role == "selftest":
            _selftest()
        else:
            sys.exit(f"xrapture: unknown role {role!r}")
        return
    from .app import main as run_app
    run_app()


def _selftest() -> None:
    """Import every heavy dependency and exit — verifies a frozen build is intact.

    Run ``xrapture --role selftest`` (or the app binary with that flag) after a
    PyInstaller build to confirm the ML/audio stack bundled correctly.
    """
    import importlib

    for module in ("faster_whisper", "ctranslate2", "av", "sounddevice",
                   "numpy", "PIL", "pystray", "tkinter"):
        importlib.import_module(module)
    from plyer import notification  # noqa: F401
    from .audio_engine import list_input_devices
    list_input_devices()  # exercises PortAudio
    print("selftest OK")


if __name__ == "__main__":
    main()
