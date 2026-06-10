# Installing xRapture

xRapture is a cross-platform menu-bar app that records your microphone **and**
system audio and transcribes it locally with [faster-whisper](https://github.com/SYSTRAN/faster-whisper).
No API keys, no cloud — everything runs on your machine.

Pick the install method that suits you:

- [Standalone macOS app](#a-standalone-macos-app-no-terminal) — drag-and-drop, no terminal.
- [pip install from source](#b-pip-install-from-source-the-xrapture-cli) — gives you the `xrapture` CLI.
- [Developer setup](#c-developer-setup) — clone, editable install, run the tests.

Whichever you choose, read [Prerequisites](#prerequisites) first — **tkinter** in
particular is not pip-installable and must be present.

## Prerequisites

- **Python 3.11+** recommended (xRapture is developed on 3.13). *Only needed for the
  pip / developer installs — the standalone `.app` bundles its own Python.*
- **tkinter** — the floating meter widget uses it. tkinter is **not pip-installable**:

  | Platform | How to get tkinter |
  |---|---|
  | macOS (Homebrew) | `brew install python-tk@3.13` |
  | Debian / Ubuntu | `sudo apt install python3-tk` |
  | python.org installer | Already included |

- **Linux only** — two extra system packages:
  - PortAudio for audio capture: `sudo apt install libportaudio2`
  - A tray backend (AppIndicator): `libayatana-appindicator` (or your distro's equivalent)

> Match your tkinter version to the Python you'll run xRapture with. If you use
> Python 3.13, install `python-tk@3.13`.

## A. Standalone macOS app (no terminal)

The easiest way to run xRapture on macOS — no Python or terminal needed once it's built.

1. Build the app bundle from the repo root:

   ```bash
   bash packaging/build_app.sh
   ```

   This produces **`dist/xRapture.app`**.

2. Drag `dist/xRapture.app` into your **/Applications** folder.

3. Launch it like any other Mac app (double-click, or Spotlight).

On first launch macOS will prompt for **Microphone** permission — grant it. To also
capture meeting/system audio, follow the [System Audio Setup](system-audio-setup.md)
guide.

> Continue to the [Getting Started](getting-started.md) walkthrough once it's running.

## B. pip install from source (the `xrapture` CLI)

This installs xRapture as a normal Python package and gives you an `xrapture`
command you can run from any directory.

1. Make sure [tkinter](#prerequisites) is installed for your Python.

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   ```

3. Install xRapture from the source checkout:

   ```bash
   pip install -e .
   ```

4. Run it:

   ```bash
   xrapture
   ```

   Or equivalently:

   ```bash
   python -m xrapture
   ```

A microphone icon appears in your tray / menu bar. Head to
[Getting Started](getting-started.md).

## C. Developer setup

For working on xRapture itself.

1. Clone the repo and `cd` into it.

2. Install [tkinter](#prerequisites) (and, on Linux, PortAudio + a tray backend).

3. Create a virtual environment and install with the dev extras:

   ```bash
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -e ".[dev]"
   ```

   The `[dev]` extra pulls in the test/dev tooling on top of the runtime deps.

4. Run the tests (no audio hardware required for the unit tests):

   ```bash
   python -m pytest
   ```

   There are also helper scripts in `tests/`:

   - `tests/smoke_widget.py` — flashes the meter widget with fake levels.
   - `tests/check_system_audio.py` — verifies system audio is reaching BlackHole
     (see [System Audio Setup](system-audio-setup.md)).

5. Run the app from source:

   ```bash
   xrapture          # or: python -m xrapture
   ```

## Where to next

- [Getting Started](getting-started.md) — your first recording in 5 minutes.
- [User Guide](user-guide.md) — every feature, setting, and menu item.
- [System Audio Setup](system-audio-setup.md) — capture meetings and system playback.
