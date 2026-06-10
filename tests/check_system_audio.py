"""Live check: is system audio actually reaching BlackHole?

Play some audio (music / a YouTube video), make sure your Mac's Sound Output is the
**Multi-Output Device**, then run this. The level should rise well above the floor
if routing works; if it stays at the floor, audio isn't flowing into BlackHole.

Run: .venv/bin/python tests/check_system_audio.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sounddevice as sd  # noqa: E402

from xrapture.audio_engine import find_blackhole, rms_db  # noqa: E402


def main() -> int:
    dev = find_blackhole()
    if dev is None:
        print("No BlackHole device found — install it first.")
        return 1

    try:
        out = sd.query_devices(kind="output")
        print(f"Current Sound Output: {out['name']}")
        if "multi-output" not in out["name"].lower():
            print("  ⚠ Output is NOT a Multi-Output Device — BlackHole will stay silent.")
    except Exception:
        pass

    print(f"\nCapturing BlackHole (device {dev}) for 6s — make sure audio is playing…\n")
    latest = {"db": -60.0}

    def cb(indata, frames, t, status):
        latest["db"] = rms_db(indata.reshape(-1))

    stream = sd.InputStream(samplerate=48000, channels=2, dtype="int16", device=dev, callback=cb)
    stream.start()
    peak = -120.0
    for _ in range(12):
        time.sleep(0.5)
        peak = max(peak, latest["db"])
        bar = "#" * int(max(0, (latest["db"] + 60) / 3))
        print(f"  {latest['db']:6.1f} dBFS  {bar}")
    stream.stop()
    stream.close()

    print(f"\npeak: {peak:.1f} dBFS")
    if peak > -50:
        print("PASS — system audio IS reaching BlackHole. xRapture will capture it.")
        return 0
    print("FAIL — BlackHole is silent. Your Sound Output isn't going through the")
    print("Multi-Output Device, or BlackHole isn't a member of it / drift correction is off.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
