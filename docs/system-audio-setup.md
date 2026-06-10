# System Audio Setup

xRapture can record **system audio** — the sound your computer plays — alongside your
microphone. That's what lets it capture online meetings, calls, and anything else
playing on your machine.

How you enable it depends on your platform:

- [macOS](#macos-blackhole--multi-output-device) — needs a one-time BlackHole setup.
- [Windows](#windows) — works natively, no setup.
- [Linux](#linux) — pick a PulseAudio `.monitor` source.

> Without a loopback device, nothing breaks: the **System meter shows "no device"** and
> xRapture records **mic-only**.

## macOS: BlackHole + Multi-Output Device

macOS has no built-in way to record its own output, so xRapture reads it from a
**virtual loopback device** called [BlackHole](https://github.com/ExistentialAudio/BlackHole).
You route your sound through both your real speakers/headphones **and** BlackHole at
once — you keep hearing audio while xRapture captures a copy of it.

This is a one-time setup.

### 1. Install BlackHole

```bash
brew install blackhole-2ch
```

After installing, **Quit & Relaunch** xRapture from the tray so it sees the new device
(audio devices are only enumerated at startup).

### 2. Create a Multi-Output Device

1. Open **Audio MIDI Setup** (in /Applications/Utilities, or search Spotlight).
2. Click the **＋** in the bottom-left → **Create Multi-Output Device**.
3. In the new device, tick **both**:
   - Your real output — **Built-in Output / your speakers / your headphones**
   - **BlackHole 2ch**
4. Set your **real output** as the **Primary / clock device** (the "Master Device"
   column). This is the device the others sync to.
5. Enable **Drift Correction** on the **BlackHole 2ch** row. This keeps BlackHole in
   sync with your real output.

> **Why Primary + Drift Correction matter:** the Primary device is the clock everything
> follows; drift correction on BlackHole keeps it aligned so the captured copy doesn't
> slowly slip out of sync.

### 3. Route your Mac's sound through it

Set the **Multi-Output Device** as your Mac's **Sound Output**:

- **System Settings → Sound → Output → Multi-Output Device**, or
- Option-click the volume icon in the menu bar and pick it there.

> **Heads up — volume keys:** while a Multi-Output Device is your output, the hardware
> **volume keys stop working** (a macOS quirk, not an xRapture bug). Adjust volume in
> the app you're playing from, or switch output back to your speakers when you're done
> recording.

### 4. Confirm xRapture sees it

In xRapture, leave **System** on **"Auto-detect BlackHole"** (the default
`system_device` value of `null`). xRapture finds BlackHole by name automatically.

Open the widget (**tray → Open Widget**), play some audio, and watch the **System**
meter move. If it does, you're set.

## Windows

No virtual device needed. xRapture uses **WASAPI loopback** to capture whatever an
**output device** is playing.

- Leave **System** on **"Auto-detect (system output)"** to capture your default
  playback device, **or** pick a specific output (e.g. *Speakers* / *Headphones*)
  from the **System** dropdown in the widget's settings.
- Play some audio and watch the **System** meter move.

> Windows support is implemented but **less battle-tested than macOS**. If loopback
> fails to open, the meter shows "no device" and xRapture keeps recording mic-only —
> please open an issue with your device details.

## Linux

Each output has a **`.monitor` source** (PulseAudio/PipeWire) that mirrors what's
playing — that's the system-audio tap.

- Leave **System** on **"Auto-detect (monitor)"** (xRapture picks a source whose name
  contains *monitor*), **or** choose your monitor source (e.g. *Monitor of Built-in
  Audio*) from the **System** dropdown.
- Install the Linux prerequisites from the
  [Installation guide](installation.md#prerequisites) — PortAudio **and** a tray
  backend. On GNOME (default Ubuntu), the menu-bar icon needs the
  [AppIndicator extension](https://extensions.gnome.org/extension/615/appindicator-support/)
  plus `gir1.2-ayatanaappindicator3-0.1`, or the tray icon won't appear.

> Linux support is implemented but **less battle-tested than macOS**.

## Troubleshooting

### "System meter shows no device"

xRapture couldn't find a loopback device at startup.

- **macOS:** Is BlackHole installed (`brew list blackhole-2ch`)? If you installed it
  while xRapture was running, use **Quit & Relaunch** — devices are only detected at
  startup.
- **Windows:** Pick an output device as **System** (or auto-detect). If it still
  fails, your default output may not be a WASAPI endpoint — choose a specific one.
- **Linux:** Is a PulseAudio/PipeWire `.monitor` source selected as `system_device`?
- This is non-fatal — xRapture still records mic-only.

### Meter stays flat (no device error, but no level)

The loopback device exists, but no audio is reaching it. On macOS this almost always
means **your sound output isn't actually going through the Multi-Output Device**:

- Confirm your Mac's **Sound Output** is set to the **Multi-Output Device** (not your
  speakers directly).
- Confirm **BlackHole 2ch is ticked** as a member of that Multi-Output Device.
- Confirm **Drift Correction** is enabled on BlackHole and your real output is the
  **Primary** device.
- Make sure audio is actually playing while you check.

### Diagnose it from the terminal

xRapture ships a diagnostic that captures BlackHole for a few seconds and tells you
whether system audio is reaching it:

```bash
python tests/check_system_audio.py
```

Play some audio (music or a video) with your Mac's output set to the Multi-Output
Device, then run it. It prints the current Sound Output, warns if it isn't a
Multi-Output Device, shows a live level bar, and ends with **PASS** (audio is reaching
BlackHole) or **FAIL** (it's silent — your output isn't routed through the Multi-Output
Device, BlackHole isn't a member, or drift correction is off).

## Related

- [User Guide](user-guide.md) — the meter widget, settings, and track layouts.
- [Getting Started](getting-started.md) — your first recording.
