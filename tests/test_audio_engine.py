"""Unit tests for the pure audio helpers — no audio hardware required.

Run: .venv/bin/python tests/test_audio_engine.py
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from xrapture.audio_engine import (  # noqa: E402
    LEVEL_FLOOR_DB,
    combine_tracks,
    db_to_fraction,
    resolve_device,
    resolve_input_device,
    rms_db,
    write_wav,
)

DEVICES = [(2, "USB audio CODEC"), (3, "Logitech BRIO"), (4, "BlackHole 2ch")]


def test_resolve_none_falls_back():
    assert resolve_input_device(None, DEVICES) is None


def test_resolve_name_to_current_index():
    # A name resolves to whatever index it currently holds (stable across reshuffles).
    assert resolve_input_device("BlackHole 2ch", DEVICES) == 4
    assert resolve_input_device("Logitech BRIO", DEVICES) == 3


def test_resolve_unknown_name_falls_back():
    assert resolve_input_device("Some Unplugged Mic", DEVICES) is None


def test_resolve_stale_index_falls_back():
    # Index 1 is not an input-capable device here → fall back rather than crash.
    assert resolve_input_device(1, DEVICES) is None


def test_resolve_valid_index_kept():
    assert resolve_input_device(4, DEVICES) == 4


def test_resolve_device_generic_over_any_list():
    # resolve_device works for any device list — e.g. Windows output devices
    # used as the WASAPI loopback source.
    outputs = [(0, "Speakers (Realtek)"), (1, "Headphones")]
    assert resolve_device("Headphones", outputs) == 1
    assert resolve_device("Speakers (Realtek)", outputs) == 0
    assert resolve_device("Gone", outputs) is None
    assert resolve_device(None, outputs) is None


def test_rms_db_silence_hits_floor():
    assert rms_db(np.zeros(1000, dtype=np.int16)) == LEVEL_FLOOR_DB
    assert rms_db(np.array([], dtype=np.int16)) == LEVEL_FLOOR_DB


def test_rms_db_full_scale_is_zero():
    full = np.full(1000, 32767, dtype=np.int16)
    assert abs(rms_db(full)) < 0.1  # ~0 dBFS


def test_rms_db_half_scale_is_about_minus_six():
    half = np.full(1000, 16384, dtype=np.int16)
    assert -7.0 < rms_db(half) < -5.0  # ~ -6 dBFS


def test_db_to_fraction_bounds():
    assert db_to_fraction(LEVEL_FLOOR_DB) == 0.0
    assert db_to_fraction(-200.0) == 0.0
    assert db_to_fraction(0.0) == 1.0
    assert db_to_fraction(5.0) == 1.0
    assert abs(db_to_fraction(LEVEL_FLOOR_DB / 2) - 0.5) < 1e-9


def test_combine_stereo_split():
    mic = np.full(100, 1000, dtype=np.int16)
    system = np.full(100, 2000, dtype=np.int16)
    tracks = combine_tracks(mic, system, "stereo_split")
    assert len(tracks) == 1
    suffix, audio = tracks[0]
    assert suffix == "" and audio.shape == (100, 2)
    assert audio[0, 0] == 1000 and audio[0, 1] == 2000  # mic=L, system=R


def test_combine_mixed_mono_averages_without_overflow():
    mic = np.full(100, 30000, dtype=np.int16)
    system = np.full(100, 30000, dtype=np.int16)
    tracks = combine_tracks(mic, system, "mixed_mono")
    assert len(tracks) == 1
    _, audio = tracks[0]
    assert audio.shape == (100, 1)
    assert audio[0, 0] == 30000  # averaged, not overflowed/clipped


def test_combine_separate_files():
    mic = np.full(100, 1000, dtype=np.int16)
    system = np.full(80, 2000, dtype=np.int16)
    tracks = combine_tracks(mic, system, "separate_files")
    assert [s for s, _ in tracks] == ["_mic", "_system"]
    # Trimmed to the shorter stream so the two files stay frame-aligned.
    assert all(audio.shape == (80, 1) for _, audio in tracks)


def test_combine_mic_only_degrades_to_mono():
    mic = np.full(100, 1000, dtype=np.int16)
    tracks = combine_tracks(mic, None, "stereo_split")
    assert len(tracks) == 1 and tracks[0][1].shape == (100, 1)


def test_combine_downmixes_multichannel_system():
    mic = np.full(50, 0, dtype=np.int16)
    system = np.full((50, 2), 0, dtype=np.int16)
    system[:, 0] = 1000
    system[:, 1] = 3000
    _, audio = combine_tracks(mic, system, "stereo_split")[0]
    assert audio[0, 1] == 2000  # (1000 + 3000) / 2


def test_write_wav_roundtrip(tmp_path_factory=None):
    import tempfile
    import wave

    audio = np.stack(
        [np.full(200, 1000, dtype=np.int16), np.full(200, -1000, dtype=np.int16)],
        axis=1,
    )
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "t.wav"
        write_wav(path, audio)
        with wave.open(str(path)) as wf:
            assert wf.getnchannels() == 2
            assert wf.getframerate() == 48000
            assert wf.getnframes() == 200


def run():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"\n{len(tests)} passed")


if __name__ == "__main__":
    run()
