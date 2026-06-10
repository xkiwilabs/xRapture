"""Floating meter widget for xRapture — runs as its own process.

A frameless, always-on-top, drag-to-move Tk window showing live level meters for
the microphone and system audio, plus an inline settings panel (the gear) and a
system-audio setup helper. Opened on demand from the tray's "Open Widget"; closed
most of the time. Recording is controlled from the tray, so this window has no
record button — it is for checking levels and changing settings.

Run standalone: ``python widget.py`` (the tray launches it as a subprocess).

Theming note: macOS Aqua ignores ``bg``/``fg`` on native buttons and option menus,
so forcing a dark scheme makes text invisible. This uses a light scheme with the
default native controls, which stays readable on macOS, Windows, and Linux.
"""

from __future__ import annotations

import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from .audio_engine import AudioEngine, db_to_fraction, find_blackhole, list_input_devices
from .settings import load_settings

# light, native-friendly palette
BG = "#f4f4f4"
BAR_BG = "#3a3a3a"      # dark title strip
BAR_FG = "#ffffff"
FG = "#1e1e1e"
MUTED = "#6a6a6a"
ACCENT = "#e23b2e"
TRACK = "#d2d2d2"       # meter track (empty)

METER_W = 184
METER_H = 14
MODELS = ["tiny", "base", "small", "medium"]
LAYOUTS = {
    "stereo_split": "Stereo split (mic L / system R)",
    "mixed_mono": "Mixed mono",
    "separate_files": "Two separate files",
}


def _meter_color(frac: float) -> str:
    if frac < 0.6:
        return "#2fa84f"  # green
    if frac < 0.85:
        return "#e0a52e"  # amber
    return ACCENT  # red — clipping territory


class MeterWidget:
    """The floating window; owns its own audio monitoring while open."""

    def __init__(self, root, engine, settings):
        self.root = root
        self.engine = engine
        self.settings = settings
        self.top: tk.Toplevel | None = None
        self._tick_id = None
        self._showing_settings = False
        self._meters: dict[str, tk.Canvas] = {}

    # --- lifecycle ---
    def show(self) -> None:
        if self.top is None:
            self._build()
        self.engine.start_monitoring()
        self._tick()

    def close(self) -> None:
        if self._tick_id is not None:
            self.root.after_cancel(self._tick_id)
            self._tick_id = None
        self.engine.stop_monitoring()
        self.root.quit()  # standalone process: closing the window exits

    # --- construction ---
    def _build(self) -> None:
        top = tk.Toplevel(self.root)
        top.overrideredirect(True)
        top.attributes("-topmost", True)
        top.configure(bg=BG)
        x = (top.winfo_screenwidth() - 240) // 2
        top.geometry(f"+{x}+60")
        self.top = top

        self._title_bar(top)
        self.meter_frame = tk.Frame(top, bg=BG)
        self.settings_frame = tk.Frame(top, bg=BG)
        self._build_meters(self.meter_frame)
        self._build_settings(self.settings_frame)
        self.meter_frame.pack(fill="both", expand=True, padx=12, pady=(2, 12))

    def _title_bar(self, parent) -> None:
        bar = tk.Frame(parent, bg=BAR_BG)
        bar.pack(fill="x")
        title = tk.Label(bar, text="🎙 xRapture", bg=BAR_BG, fg=BAR_FG,
                         font=("Helvetica", 12, "bold"))
        title.pack(side="left", padx=10, pady=6)
        tk.Button(bar, text="✕", command=self.close, highlightbackground=BAR_BG,
                  relief="flat", font=("Helvetica", 12)).pack(side="right", padx=(0, 6))
        tk.Button(bar, text="⚙", command=self._toggle_settings, highlightbackground=BAR_BG,
                  relief="flat", font=("Helvetica", 12)).pack(side="right")
        for w in (bar, title):
            w.bind("<ButtonPress-1>", self._start_move)
            w.bind("<B1-Motion>", self._on_move)

    def _build_meters(self, parent) -> None:
        for key, label in (("mic", "Mic"), ("system", "System")):
            row = tk.Frame(parent, bg=BG)
            row.pack(fill="x", pady=(10, 0))
            tk.Label(row, text=label, bg=BG, fg=MUTED, width=6, anchor="w").pack(side="left")
            canvas = tk.Canvas(row, width=METER_W, height=METER_H, bg=TRACK,
                               highlightthickness=0)
            canvas.pack(side="left")
            self._meters[key] = canvas
        tk.Label(parent, text="Recording is controlled from the menu-bar icon.",
                 bg=BG, fg=MUTED, font=("Helvetica", 9)).pack(anchor="w", pady=(12, 0))

    def _build_settings(self, parent) -> None:
        self._device_options()

        self._model_var = tk.StringVar(value=self.settings.model_size)
        self._mic_var = tk.StringVar(
            value=self._label_for(self.settings.input_device, self._mic_choice, "System default"))
        self._system_var = tk.StringVar(
            value=self._label_for(self.settings.system_device, self._sys_choice, "Auto-detect BlackHole"))
        self._layout_var = tk.StringVar(value=LAYOUTS[self.settings.track_layout])
        self._auto_var = tk.BooleanVar(value=self.settings.auto_transcribe)
        self._folder_var = tk.StringVar(value=str(Path(self.settings["output_folder"])))

        self._row_folder(parent)
        self._row_option(parent, "Model", self._model_var, MODELS)
        self._row_option(parent, "Mic", self._mic_var, list(self._mic_choice))
        self._row_option(parent, "System", self._system_var, list(self._sys_choice))
        self._row_system_setup(parent)
        self._row_option(parent, "Tracks", self._layout_var, list(LAYOUTS.values()))

        tk.Checkbutton(parent, text="Auto-transcribe after recording", variable=self._auto_var,
                       bg=BG, fg=FG, activebackground=BG, highlightthickness=0).pack(
            anchor="w", pady=(8, 0))
        tk.Button(parent, text="Save", command=self._save_settings).pack(anchor="e", pady=(10, 0))

    # --- settings helpers ---
    def _device_options(self) -> None:
        # Display label -> stored value. We store the device NAME (or None for the
        # default/auto choice) because PortAudio indices shift across CoreAudio
        # reshuffles; names survive them.
        self._mic_choice = {"System default": None}
        self._sys_choice = {"Auto-detect BlackHole": None}
        for _index, name in list_input_devices():
            self._mic_choice[name] = name
            self._sys_choice[name] = name

    @staticmethod
    def _label_for(value, choices, default):
        return value if isinstance(value, str) and value in choices else default

    def _row_folder(self, parent) -> None:
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=(10, 0))
        tk.Label(row, text="Folder", bg=BG, fg=MUTED, width=7, anchor="w").pack(side="left")
        tk.Label(row, textvariable=self._folder_var, bg=BG, fg=FG, anchor="w").pack(
            side="left", fill="x", expand=True)
        tk.Button(row, text="Browse", command=self._pick_folder).pack(side="right")

    def _row_option(self, parent, label, var, values) -> None:
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=(8, 0))
        tk.Label(row, text=label, bg=BG, fg=MUTED, width=7, anchor="w").pack(side="left")
        tk.OptionMenu(row, var, *values).pack(side="left", fill="x", expand=True)

    def _row_system_setup(self, parent) -> None:
        """Status line + helper for getting system-audio capture working."""
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=(4, 0))
        tk.Label(row, text="", width=7, bg=BG).pack(side="left")  # align under labels
        self._sys_status = tk.Label(row, text="", bg=BG, fg=MUTED, anchor="w",
                                    font=("Helvetica", 10))
        self._sys_status.pack(side="left", fill="x", expand=True)
        tk.Button(row, text="Set up…", command=self._open_audio_setup).pack(side="right")
        self._refresh_system_status()

    def _refresh_system_status(self) -> None:
        if not hasattr(self, "_sys_status"):
            return
        if find_blackhole() is not None:
            self._sys_status.configure(text="✓ BlackHole detected", fg="#2fa84f")
        else:
            self._sys_status.configure(text="No loopback device — click Set up", fg=MUTED)

    def _open_audio_setup(self) -> None:
        if sys.platform != "darwin":
            messagebox.showinfo(
                "Set up system audio",
                "Windows captures system audio automatically (WASAPI loopback).\n\n"
                "Linux: pick your PulseAudio '.monitor' source as the System device.")
            return
        # PLATFORM: Audio MIDI Setup is the macOS tool for Multi-Output Devices.
        subprocess.run(["open", "-a", "Audio MIDI Setup"], check=False)
        if find_blackhole() is not None:
            steps = (
                "BlackHole is installed. In Audio MIDI Setup (now open):\n\n"
                "1.  Click  +  →  Create Multi-Output Device\n"
                "2.  Tick BOTH your speakers/headphones AND BlackHole 2ch\n"
                "3.  Set that Multi-Output Device as your Mac's Sound Output\n\n"
                "Then set System (above) to BlackHole, or leave it on auto-detect.")
        else:
            steps = (
                "BlackHole isn't installed yet. In Terminal, run:\n\n"
                "    brew install blackhole-2ch\n\n"
                "Then restart the audio daemon ( sudo killall coreaudiod ) or reboot, "
                "reopen this panel, and finish the Multi-Output Device setup.")
        messagebox.showinfo("Set up system audio", steps)

    def _pick_folder(self) -> None:
        chosen = filedialog.askdirectory(initialdir=self._folder_var.get())
        if chosen:
            self._folder_var.set(chosen)

    def _save_settings(self) -> None:
        layout_by_label = {v: k for k, v in LAYOUTS.items()}
        self.settings["output_folder"] = self._folder_var.get()
        self.settings["model_size"] = self._model_var.get()
        self.settings["input_device"] = self._mic_choice[self._mic_var.get()]
        self.settings["system_device"] = self._sys_choice[self._system_var.get()]
        self.settings["track_layout"] = layout_by_label[self._layout_var.get()]
        self.settings["auto_transcribe"] = bool(self._auto_var.get())
        self.settings.save()
        # Reopen monitoring so new device choices take effect in the meters.
        self.engine.stop_monitoring()
        self.engine.start_monitoring()
        self._toggle_settings()  # back to the meters

    # --- interactions ---
    def _toggle_settings(self) -> None:
        self._showing_settings = not self._showing_settings
        if self._showing_settings:
            self._refresh_system_status()
            self.meter_frame.pack_forget()
            self.settings_frame.pack(fill="both", expand=True, padx=12, pady=(2, 12))
        else:
            self.settings_frame.pack_forget()
            self.meter_frame.pack(fill="both", expand=True, padx=12, pady=(2, 12))

    def _start_move(self, event) -> None:
        self._drag = (event.x, event.y)

    def _on_move(self, event) -> None:
        dx, dy = self._drag
        self.top.geometry(
            f"+{self.top.winfo_x() + event.x - dx}+{self.top.winfo_y() + event.y - dy}")

    # --- animation loop ---
    def _tick(self) -> None:
        self._draw_meter("mic", db_to_fraction(self.engine.mic_level),
                         getattr(self.engine, "mic_available", True))
        self._draw_meter("system", db_to_fraction(self.engine.system_level),
                         self.engine.system_available)
        self._tick_id = self.root.after(50, self._tick)

    def _draw_meter(self, key: str, frac: float, available: bool) -> None:
        canvas = self._meters[key]
        canvas.delete("all")
        if not available:
            canvas.create_text(METER_W // 2, METER_H // 2, text="no device", fill=MUTED,
                               font=("Helvetica", 9))
            return
        width = int(frac * METER_W)
        if width > 0:
            canvas.create_rectangle(0, 0, width, METER_H, fill=_meter_color(frac), width=0)


def main() -> None:
    root = tk.Tk()
    root.withdraw()  # only the Toplevel widget is shown
    settings = load_settings()
    engine = AudioEngine(settings)
    widget = MeterWidget(root, engine, settings)
    widget.show()
    root.mainloop()


if __name__ == "__main__":
    main()
