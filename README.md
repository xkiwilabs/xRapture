<div align="center">

# 🎙 xRapture

**Record your mic *and* system audio, then transcribe it locally — no cloud, no API keys.**

A cross-platform menu-bar app for capturing meetings (including the far end of
online calls) and turning them into text with [faster-whisper](https://github.com/SYSTRAN/faster-whisper).
Everything runs on your machine.

[![CI](https://github.com/xkiwilabs/xRapture/actions/workflows/ci.yml/badge.svg)](https://github.com/xkiwilabs/xRapture/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

</div>

---

## Why xRapture

- 🎧 **Captures both sides of a conversation** — your microphone *and* the system
  audio (the other people on the call, a video, anything playing).
- 🔒 **Fully local** — Whisper runs on your machine. No accounts, no uploads, no API keys.
- 📊 **Live level meters** — a floating, draggable widget shows mic + system levels
  so you know it's actually capturing before you hit record.
- ✍️ **Automatic transcripts** — every recording becomes a `.txt` next to its audio.
  You can also transcribe **any existing audio file** (WAV, MP3, M4A, FLAC, …).
- 🖥 **Cross-platform** — one codebase for macOS, Windows, and Linux.

## Quick start

```bash
# 1. Get the code and a virtual environment
git clone https://github.com/xkiwilabs/xRapture.git
cd xRapture
python3 -m venv .venv && source .venv/bin/activate

# 2. tkinter is required and is NOT pip-installable (see docs/installation.md)
brew install python-tk@3.13          # macOS (Homebrew); apt install python3-tk on Debian/Ubuntu

# 3. Install and run
pip install -e .
xrapture
```

A microphone icon appears in your menu bar. Click it → **Start Recording** → **Stop**,
and you'll get a `.wav` + `.txt` in `~/Documents/xRapture/`.

Prefer a clickable app? Build a standalone bundle you can drop in **/Applications**:

```bash
bash packaging/build_app.sh        # → dist/xRapture.app
```

👉 **New here? Start with the [Getting Started guide](docs/getting-started.md).**

## Capturing system audio

Recording your mic works out of the box. Capturing **system audio** (for meetings)
needs a one-time setup, because macOS has no built-in way to record its own output:

- **macOS** — install [BlackHole](https://github.com/ExistentialAudio/BlackHole) and
  route output through a Multi-Output Device.
- **Windows** — works natively via WASAPI loopback; just pick an output device (no
  virtual device needed).
- **Linux** — select your PulseAudio/PipeWire `.monitor` source.

Full walkthrough: **[System Audio Setup](docs/system-audio-setup.md)**. Without it,
xRapture records mic-only and the System meter shows "no device" — nothing breaks.

> **Platform status:** developed and tested on **macOS**. Windows and Linux are
> supported from the same codebase (install via `pip`) but are **less battle-tested** —
> bug reports welcome.

## Documentation

| Guide | What's in it |
|---|---|
| [Getting Started](docs/getting-started.md) | 5-minute first run |
| [Installation](docs/installation.md) | App bundle, pip install, dev setup, per-OS prerequisites |
| [User Guide](docs/user-guide.md) | Every feature: menu, widget, settings, track layouts, file transcription |
| [System Audio Setup](docs/system-audio-setup.md) | BlackHole + Multi-Output Device, plus Windows/Linux |

## How it works

xRapture runs as two cooperating processes (a deliberate design — on macOS the menu
bar and a Tk window can't share one process):

- **Menu-bar process** (`xrapture.app`) — owns audio capture, recording, and
  transcription. No GUI windows.
- **Widget process** (`xrapture.widget`) — the floating meter/settings window,
  launched on demand.

Audio is captured at 48 kHz from the mic and (optionally) a loopback device, metered
in real time, and written per your chosen track layout (stereo split / mixed / separate).
Transcription uses faster-whisper, which decodes any common audio format via PyAV.

## Development

```bash
pip install -e ".[dev]"            # editable install + pytest + pyinstaller
python -m pytest                   # run the test suite
python -m xrapture                 # run from source
```

`tests/check_system_audio.py` is a handy live diagnostic for verifying BlackHole routing.

## Privacy

xRapture never sends audio or transcripts anywhere. Whisper models download once from
Hugging Face on first use and then run entirely offline.

## License

[MIT](LICENSE) © 2026 xKiwiLabs
