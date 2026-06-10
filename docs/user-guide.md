# User Guide

A complete reference for everything xRapture does. New here? Try the
[Getting Started](getting-started.md) walkthrough first.

## The tray menu

xRapture lives entirely in the menu bar / system tray. Click the microphone icon to
open the menu:

```
🎙 xRapture
─────────────────
🪟 Open Widget
─────────────────
▶ Start Recording
⏹ Stop Recording
─────────────────
✍ Transcribe Last Recording
🎞 Transcribe Audio File…
📁 Open Transcripts Folder
─────────────────
↻ Quit & Relaunch
✕ Quit
```

| Item | What it does |
|---|---|
| **Open Widget** | Opens the floating meter widget (closed by default). |
| **Start Recording** | Captures mic + system audio to a timestamped WAV. The tray icon turns **red** and you get a notification. |
| **Stop Recording** | Stops capture and writes the file(s). If auto-transcribe is on, transcription starts immediately. |
| **Transcribe Last Recording** | Runs Whisper on the most recent recording and writes a `.txt` next to it. |
| **Transcribe Audio File…** | Opens a file picker to transcribe **any** audio file (see [below](#transcribing-external-files)). |
| **Open Transcripts Folder** | Opens your output folder in the system file manager. |
| **Quit & Relaunch** | Restarts the app (see [Quit & Relaunch](#quit--relaunch)). |
| **Quit** | Exits xRapture. |

## The meter widget

The widget is a small, frameless, **always-on-top** window you open from the tray's
**Open Widget** item. It runs as its own process (on macOS, the menu bar and a Tk
window can't share one process), so opening or closing it never interrupts recording.

What it shows:

- **Live level meters** for your **mic** and **system audio** — green → amber → red as
  levels rise. Use them to confirm audio is reaching xRapture before you record.
- A **gear** that flips to an inline **settings panel** (see [Settings](#settings)).
- A **system-audio setup helper** to guide loopback configuration.

Notes:

- **Drag anywhere** to reposition it; it stays on top of other windows.
- There is **no record button** — recording is controlled from the tray menu. The
  widget is for checking levels and changing settings.
- If no system-audio loopback device is found, the **System meter shows "no device"**
  and xRapture records mic-only. See [System Audio Setup](system-audio-setup.md).

## Settings

Change settings in the widget's gear panel, or edit `settings.json` directly.

Settings live at:

| Platform | Location |
|---|---|
| macOS | `~/Library/Application Support/xRapture/settings.json` |
| Linux | XDG config dir (e.g. `~/.config/xRapture/settings.json`) |
| Windows | `%APPDATA%\xRapture\settings.json` |

| Key | Type | Default | Description |
|---|---|---|---|
| `output_folder` | string | `~/Documents/xRapture` | Where recordings and transcripts are saved. |
| `model_size` | string | `base` | Whisper model: `tiny`, `base`, `small`, `medium`. |
| `auto_transcribe` | bool | `true` | Transcribe automatically when recording stops. |
| `input_device` | name or `null` | `null` | Mic device **name** (`null` = system default). |
| `system_device` | name or `null` | `null` | System-audio device **name** (`null` = auto-detect BlackHole). |
| `track_layout` | string | `stereo_split` | How mic + system are written. See [Track layouts](#track-layouts). |

> Devices are stored by **name**, not by index — audio-device indices can shift (for
> example after installing BlackHole), so a name survives the reshuffle. If a saved
> device is gone, xRapture falls back to the default rather than crashing.

The tray re-reads `settings.json` before each recording, so edits made in the widget
apply to your next recording without restarting.

## Track layouts

`track_layout` controls how the mic and system audio are combined into output file(s):

| Value | Result |
|---|---|
| `stereo_split` *(default)* | One stereo WAV: **mic on the left** channel, **system audio on the right**. Keeps the two sources separable while staying a single file. |
| `mixed_mono` | One mono WAV with mic and system summed together. |
| `separate_files` | Two WAV files — one for the mic, one for the system audio. |

For transcription this rarely matters (Whisper downmixes to mono anyway), but
`stereo_split` and `separate_files` are handy if you want to process the speaker and
the meeting audio separately later.

## Recordings and where files are saved

- Recordings are timestamped WAVs: **`xrapture_YYYY-MM-DD_HH-MM-SS.wav`**.
- Transcripts are plain-text **`.txt`** files written **next to** the audio they came
  from.
- Everything goes to your `output_folder` (`~/Documents/xRapture` by default).

## Transcribing external files

**Transcribe Audio File…** lets you transcribe audio recorded outside xRapture.

1. Tray → **Transcribe Audio File…** — a native file picker opens.
2. Choose any common audio file — **WAV, MP3, M4A, FLAC, OGG, AAC** and more are
   supported (decoded via PyAV).
3. xRapture transcribes it and writes the `.txt` **next to the source file** (not in
   your xRapture output folder).

## The progress window

Any time a transcription runs — whether from a recording or a picked file — a small
**progress window** appears:

- **Indeterminate** (a moving bar) while the Whisper model loads.
- A **real percentage** as it works through the audio.

It closes itself when transcription finishes.

## Model sizes and the accuracy trade-off

`model_size` selects the Whisper model. Larger models are more accurate but slower and
use more memory:

| Model | Speed | Accuracy | Good for |
|---|---|---|---|
| `tiny` | Fastest | Lowest | Quick drafts, clean audio, low-power machines. |
| `base` *(default)* | Fast | Good | A solid everyday balance. |
| `small` | Slower | Better | Noisier audio or accents. |
| `medium` | Slowest | Best | When accuracy matters most. |

The model weights **download automatically on first use** and are cached afterwards,
so only the first transcription with a given size pays the download cost.

## Quit & Relaunch

xRapture's audio library only enumerates devices **at startup**. If you install a new
audio device while xRapture is running — most commonly **BlackHole** during
[System Audio Setup](system-audio-setup.md) — it won't be picked up until you restart.

**Quit & Relaunch** restarts the app cleanly so newly-installed devices appear. Use it
right after installing BlackHole or creating a Multi-Output Device.

## Related

- [System Audio Setup](system-audio-setup.md) — capture meetings and system playback.
- [Installation](installation.md) — install methods and prerequisites.
