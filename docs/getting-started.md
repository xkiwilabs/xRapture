# Getting Started

Welcome! This is a 5-minute walkthrough from launch to your first transcript. If you
haven't installed xRapture yet, start with the [Installation guide](installation.md).

By the end you'll have recorded a short clip and found its transcript.

## 1. Launch xRapture

- **Standalone macOS app:** double-click **xRapture** in /Applications.
- **CLI install:** run `xrapture` (or `python -m xrapture`) in your terminal.

A microphone icon appears in your **menu bar / system tray**. That little icon is the
whole app — there's no main window.

## 2. Grant microphone permission (first launch on macOS)

The first time you record, macOS asks for **Microphone** access. Click **OK / Allow**.
xRapture can't record without it.

> If you missed the prompt, enable it later under **System Settings → Privacy &
> Security → Microphone**.

## 3. (Optional) Open the meter widget

Click the tray icon and choose **Open Widget**. A small floating window appears with
live level meters for your mic and system audio. Talk, and watch the **mic** meter
move — that confirms your microphone is working before you commit to a recording.

The widget is always-on-top and you can drag it anywhere. It's optional: close it any
time. (Recording is controlled from the tray menu, not the widget.)

> Want to capture meeting / system audio too? That needs a one-time setup —
> see [System Audio Setup](system-audio-setup.md). Without it, xRapture happily
> records mic-only and the System meter just shows "no device".

## 4. Record from the tray

1. Click the tray icon → **Start Recording**. The icon turns **red** and you get a
   start notification.
2. Say a few sentences.
3. Click the tray icon → **Stop Recording**. You get a stop notification.

Your audio is saved as a timestamped WAV like
`xrapture_2026-06-10_14-32-05.wav` in your output folder
(`~/Documents/xRapture` by default).

## 5. Find your transcript

With **auto-transcribe** on (the default), xRapture runs Whisper as soon as you stop.
A small **progress window** appears while it works — indeterminate while the model
loads on first use, then a real percentage.

When it finishes, the transcript is a `.txt` file written **right next to the WAV**,
e.g. `xrapture_2026-06-10_14-32-05.txt`.

Open the folder quickly via the tray: **Open Transcripts Folder**.

> The Whisper model downloads automatically the first time you transcribe, so the
> very first run takes a little longer. After that it's cached.

## That's it!

You've recorded and transcribed locally — no cloud involved. From here:

- [System Audio Setup](system-audio-setup.md) — capture online meetings and anything
  playing on your machine.
- [User Guide](user-guide.md) — every menu item, setting, and the track-layout and
  model-size options.
