"""xRapture — cross-platform tray app for recording and transcribing audio.

The menu-bar (pystray) process owns recording and transcription. The meter widget
runs as a SEPARATE process (widget.py), launched on demand.

Why two processes: on macOS, pystray and tkinter both need the main thread / an
NSApplication, so sharing one process crashes the Cocoa run loop (a GIL/thread-state
fault). Keeping Tk entirely out of this process is what makes the tray stable. The
only other GUI we need here — the file-open dialog — is likewise spawned as a
short-lived child process (filepicker.py).
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path

import pystray
from PIL import Image, ImageDraw
from plyer import notification

from .audio_engine import AudioEngine
from .paths import app_command, child_command
from .settings import load_settings
from .transcriber import Transcriber


def make_icon(active: bool) -> Image.Image:
    """Draw the mic + waveform tray icon.

    pystray needs a raster image, so we render it with Pillow rather than
    rasterising assets/icon.svg (which would pull in a native SVG dependency).
    White reads clearly on the (usually dark) macOS menu bar; red signals live.
    """
    color = (226, 59, 46, 255) if active else (255, 255, 255, 255)
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle((26, 10, 38, 36), radius=6, fill=color)
    draw.arc((20, 18, 44, 42), start=0, end=180, fill=color, width=3)
    draw.line((32, 42, 32, 50), fill=color, width=3)
    draw.line((24, 52, 40, 52), fill=color, width=3)

    bump = 2 if active else 0
    for x, half in ((10, 4), (15, 8), (49, 8), (54, 4)):
        h = half + bump
        draw.line((x, 24 - h, x, 24 + h), fill=color, width=3)

    return img


def open_path(path) -> None:
    """Open a file or folder in the OS default handler."""
    path = str(path)
    # PLATFORM: there is no cross-platform stdlib call to open a path in the
    # file manager / default app, so we branch per OS here.
    if sys.platform == "darwin":
        subprocess.run(["open", path], check=False)
    elif sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]  # PLATFORM: Windows only
    else:
        subprocess.run(["xdg-open", path], check=False)  # PLATFORM: Linux/BSD


class XRaptureApp:
    """The menu-bar process: owns the audio engine, recording, and transcription."""

    def __init__(self):
        self.settings = load_settings()
        self.engine = AudioEngine(self.settings)
        self.transcriber = Transcriber(self.settings.model_size)
        self.last_recordings: list[Path] = []
        self._widget_proc: subprocess.Popen | None = None
        self.icon = pystray.Icon("xRapture", make_icon(False), "xRapture", menu=self._build_menu())

    # --- menu ---
    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem("Open Widget", lambda i, _: self._open_widget()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Start Recording", lambda i, _: self.start_recording(),
                             enabled=lambda _: not self.engine.is_recording),
            pystray.MenuItem("Stop Recording", lambda i, _: self.stop_recording(),
                             enabled=lambda _: self.engine.is_recording),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Transcribe Last Recording", lambda i, _: self._transcribe_last(),
                             enabled=lambda _: bool(self.last_recordings)),
            pystray.MenuItem("Transcribe Audio File…", lambda i, _: self._pick_and_transcribe()),
            pystray.MenuItem("Open Transcripts Folder",
                             lambda i, _: open_path(self.settings.output_folder)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit & Relaunch", lambda i, _: self._relaunch()),
            pystray.MenuItem("Quit", lambda i, _: self._shutdown()),
        )

    # --- widget (separate process, launched on demand) ---
    def _open_widget(self) -> None:
        if self._widget_proc is not None and self._widget_proc.poll() is None:
            return  # already open — don't spawn a second one
        self._widget_proc = subprocess.Popen(child_command("widget"))

    # --- recording ---
    def start_recording(self) -> None:
        # Re-read settings so device/layout changes made in the widget apply.
        self.settings = load_settings()
        self.engine.settings = self.settings
        self.engine.start_recording()
        self.icon.icon = make_icon(True)
        self.icon.update_menu()
        self._notify("xRapture", "Recording started")

    def stop_recording(self) -> None:
        paths = self.engine.stop_recording(self.settings.output_folder)
        self.icon.icon = make_icon(False)
        self.icon.update_menu()
        if not paths:
            self._notify("xRapture", "Recording stopped (no audio captured)")
            return
        self.last_recordings = paths
        self.icon.update_menu()  # enable "Transcribe Last Recording"
        self._notify("xRapture", f"Saved {paths[0].name}")
        if self.settings.auto_transcribe:
            self._transcribe_in_background(paths)

    # --- transcription ---
    def _transcribe_last(self) -> None:
        if self.last_recordings:
            self._transcribe_in_background(self.last_recordings)

    def _pick_and_transcribe(self) -> None:
        """Pick any audio file (via a child-process dialog) and transcribe it.

        The dialog runs in filepicker.py because this process must not create a Tk
        root. faster-whisper decodes via PyAV, so WAV/MP3/M4A/FLAC/… all work; the
        transcript is written next to the chosen file.
        """

        def worker():
            try:
                result = subprocess.run(
                    child_command("filepicker"), capture_output=True, text=True,
                )
                path = result.stdout.strip()
            except Exception as exc:
                self._notify("xRapture", f"File picker failed: {exc}")
                return
            if path:
                self._do_transcribe([Path(path)])

        threading.Thread(target=worker, daemon=True).start()

    def _transcribe_in_background(self, paths: list[Path]) -> None:
        threading.Thread(target=self._do_transcribe, args=(paths,), daemon=True).start()

    def _do_transcribe(self, paths: list[Path]) -> None:
        for wav_path in paths:
            self._notify("xRapture", f"Transcribing {wav_path.name}…")
            proc = self._spawn_progress(wav_path.name)
            try:
                txt_path = self.transcriber.transcribe(
                    wav_path, self.settings.model_size,
                    progress=lambda frac, p=proc: self._send_progress(p, frac),
                )
            except Exception as exc:
                self._close_progress(proc)
                self._notify("xRapture", f"Transcription failed: {exc}")
                continue
            self._close_progress(proc)
            self._notify("xRapture", f"Transcript ready: {txt_path.name}")

    # --- transcription progress window (child process) ---
    def _spawn_progress(self, name: str) -> subprocess.Popen | None:
        try:
            proc = subprocess.Popen(
                child_command("progress", name), stdin=subprocess.PIPE, text=True,
            )
            self._send_progress(proc, -1)  # indeterminate until the model loads
            return proc
        except Exception:
            return None  # progress UI is best-effort; never block transcription

    def _send_progress(self, proc: subprocess.Popen | None, frac: float) -> None:
        if proc is None or proc.stdin is None:
            return
        try:
            proc.stdin.write(f"{frac}\n")
            proc.stdin.flush()
        except (BrokenPipeError, ValueError, OSError):
            pass  # window closed early — ignore

    def _close_progress(self, proc: subprocess.Popen | None) -> None:
        if proc is None or proc.stdin is None:
            return
        try:
            proc.stdin.close()  # EOF tells the window to close
        except Exception:
            pass

    # --- helpers ---
    def _notify(self, title: str, message: str) -> None:
        try:
            notification.notify(title=title, message=message, app_name="xRapture")
        except Exception as exc:  # notifications are best-effort, never fatal
            print(f"[notify] {title}: {message} ({exc})")

    def _teardown(self) -> None:
        if self.engine.is_recording:
            self.stop_recording()
        self.engine.stop_monitoring()
        if self._widget_proc is not None and self._widget_proc.poll() is None:
            self._widget_proc.terminate()
        try:
            self.icon.stop()
        except Exception:
            pass

    def _shutdown(self) -> None:
        self._teardown()

    def _relaunch(self) -> None:
        # Replace this process with a fresh xRapture so newly-installed devices
        # (e.g. BlackHole) appear. Preserves how it was launched.
        self._teardown()
        cmd = app_command()
        os.execv(cmd[0], cmd)

    def run(self) -> None:
        self.icon.run()  # blocks on the menu-bar loop (this process owns no Tk)


def main() -> None:
    XRaptureApp().run()


if __name__ == "__main__":
    main()
