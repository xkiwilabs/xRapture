"""Audio capture engine for xRapture.

Owns up to two live input streams — the microphone and a system-audio device
(e.g. BlackHole) — and serves two jobs at once:

* **Metering:** while monitoring, each stream's callback computes an RMS level
  (in dBFS) that the widget polls to animate its meters.
* **Recording:** while recording, the same callbacks tee their frames into
  per-source buffers, which are combined on stop according to ``track_layout``.

Streams run on PortAudio's own callback threads, so the UI stays responsive.
``sounddevice`` is imported lazily so the pure helpers (and their tests) don't
require PortAudio to be present.
"""

from __future__ import annotations

import threading
import wave
from datetime import datetime
from pathlib import Path

import numpy as np

# 48 kHz mono per source: the common CoreAudio rate that both typical mics and
# BlackHole accept, so the two streams share a rate and combine without resampling.
SAMPLE_RATE = 48000
SAMPLE_WIDTH = 2  # bytes per int16 sample
FULL_SCALE = 32768.0  # |int16| max, for dBFS
LEVEL_FLOOR_DB = -60.0  # quietest level the meters show


# --------------------------------------------------------------------------- #
# Pure helpers (no audio hardware needed — unit tested directly)
# --------------------------------------------------------------------------- #
def rms_db(samples: np.ndarray, floor_db: float = LEVEL_FLOOR_DB) -> float:
    """Return the RMS level of int16 ``samples`` in dBFS, clamped to ``floor_db``."""
    if samples.size == 0:
        return floor_db
    x = samples.astype(np.float64)
    rms = np.sqrt(np.mean(x * x))
    if rms <= 0:
        return floor_db
    return max(20.0 * np.log10(rms / FULL_SCALE), floor_db)


def db_to_fraction(db: float, floor_db: float = LEVEL_FLOOR_DB) -> float:
    """Map a dBFS level to a 0..1 meter fill fraction."""
    if db <= floor_db:
        return 0.0
    if db >= 0.0:
        return 1.0
    return (db - floor_db) / (0.0 - floor_db)


def combine_tracks(
    mic: np.ndarray | None,
    system: np.ndarray | None,
    layout: str,
) -> list[tuple[str, np.ndarray]]:
    """Combine mono mic/system int16 buffers into output track(s).

    Returns a list of ``(filename_suffix, audio)`` where ``audio`` is a 2-D
    int16 array shaped ``(frames, channels)``. Channels are trimmed to equal
    length. If only one source is present the layout degrades gracefully to a
    single mono track.
    """
    mic = _as_mono(mic)
    system = _as_mono(system)

    # Degenerate cases: only one source actually captured anything.
    if system is None and mic is None:
        return []
    if system is None:
        return [("", mic.reshape(-1, 1))]
    if mic is None:
        return [("", system.reshape(-1, 1))]

    n = min(len(mic), len(system))  # align by start, trim to the shorter stream
    mic, system = mic[:n], system[:n]

    if layout == "mixed_mono":
        # Average to avoid int16 overflow/clipping when summing two sources.
        mixed = ((mic.astype(np.int32) + system.astype(np.int32)) // 2).astype(np.int16)
        return [("", mixed.reshape(-1, 1))]
    if layout == "separate_files":
        return [("_mic", mic.reshape(-1, 1)), ("_system", system.reshape(-1, 1))]
    # default: stereo_split — mic on the left channel, system on the right
    return [("", np.stack([mic, system], axis=1))]


def _as_mono(buffer: np.ndarray | None) -> np.ndarray | None:
    """Flatten a captured buffer to a 1-D mono int16 array (downmixing if needed)."""
    if buffer is None or buffer.size == 0:
        return None
    if buffer.ndim == 1:
        return buffer
    if buffer.shape[1] == 1:
        return buffer.reshape(-1)
    # Downmix multi-channel (e.g. BlackHole stereo) by averaging channels.
    return buffer.astype(np.int32).mean(axis=1).astype(np.int16)


def write_wav(path: Path, audio: np.ndarray, rate: int = SAMPLE_RATE) -> None:
    """Write a 2-D ``(frames, channels)`` int16 array to a WAV file."""
    channels = audio.shape[1] if audio.ndim == 2 else 1
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(rate)
        wf.writeframes(np.ascontiguousarray(audio).tobytes())


# --------------------------------------------------------------------------- #
# Device discovery
# --------------------------------------------------------------------------- #
def list_input_devices() -> list[tuple[int, str]]:
    """Return ``(index, name)`` for every device that can capture audio."""
    import sounddevice as sd

    devices = []
    for index, info in enumerate(sd.query_devices()):
        if info["max_input_channels"] > 0:
            devices.append((index, info["name"]))
    return devices


def find_blackhole() -> int | None:
    """Return the index of a BlackHole-style loopback device, if present."""
    for index, name in list_input_devices():
        if "blackhole" in name.lower():
            return index
    return None


def resolve_input_device(value, devices=None):
    """Resolve a stored device setting to a current input-device index.

    ``value`` may be a device **name** (preferred — stable across CoreAudio
    reshuffles), a legacy integer index, or ``None``. Returns the matching index
    among input-capable devices, or ``None`` to fall back to the default. A stale
    index or an unplugged device name resolves to ``None`` rather than erroring —
    device indices are NOT stable, which is why names are preferred.
    """
    if value is None:
        return None
    if devices is None:
        devices = list_input_devices()
    if isinstance(value, int):
        return value if any(i == value for i, _ in devices) else None
    for index, name in devices:
        if name == value:
            return index
    return None


def _input_channels(device, default: int = 1, cap: int = 2) -> int:
    """Channels to open for ``device``, clamped to ``cap`` (1 mic / 2 system)."""
    import sounddevice as sd

    try:
        info = sd.query_devices(device, "input")
        return max(1, min(int(info["max_input_channels"]), cap))
    except Exception:
        return default


# --------------------------------------------------------------------------- #
# The engine
# --------------------------------------------------------------------------- #
class AudioEngine:
    """Live mic + system capture with metering and track-aware recording."""

    def __init__(self, settings):
        self.settings = settings
        self._mic = _Source(channels=1)
        self._system = _Source(channels=2)
        self._lock = threading.Lock()
        self._monitoring = False
        self._recording = False
        self._record_start = 0.0  # frame count → seconds, clock-free
        self._record_frames = 0
        self.mic_available = True
        self.system_available = False
        self.last_error: str | None = None

    # --- public level readouts (read by the widget) ---
    @property
    def mic_level(self) -> float:
        return self._mic.level

    @property
    def system_level(self) -> float:
        return self._system.level

    @property
    def is_recording(self) -> bool:
        return self._recording

    def recording_seconds(self) -> float:
        return self._record_frames / SAMPLE_RATE if self._recording else 0.0

    # --- monitoring ---
    def start_monitoring(self) -> None:
        with self._lock:
            self._monitoring = True
            self._open_streams()

    def stop_monitoring(self) -> None:
        with self._lock:
            self._monitoring = False
            self._close_streams_if_idle()

    # --- recording ---
    def start_recording(self) -> None:
        with self._lock:
            self._mic.reset_buffer()
            self._system.reset_buffer()
            self._record_frames = 0
            self._recording = True
            self._open_streams()  # works even if the widget (monitoring) is closed

    def stop_recording(self, output_folder: Path) -> list[Path]:
        with self._lock:
            if not self._recording:
                return []
            self._recording = False
            mic_audio = self._mic.collect()
            system_audio = self._system.collect() if self.system_available else None
            self._close_streams_if_idle()

        tracks = combine_tracks(mic_audio, system_audio, self.settings.track_layout)
        if not tracks:
            return []

        base = f"xrapture_{datetime.now():%Y-%m-%d_%H-%M-%S}"
        paths = []
        for suffix, audio in tracks:
            path = output_folder / f"{base}{suffix}.wav"
            write_wav(path, audio)
            paths.append(path)
        return paths

    # --- stream lifecycle (caller holds self._lock) ---
    def _open_streams(self) -> None:
        import sounddevice as sd

        devices = list_input_devices()

        # Mic — a missing/stale device is non-fatal: fall back and keep going so a
        # bad saved index can't crash the whole engine (it used to: PaError -9998).
        if not self._mic.is_open:
            mic_device = resolve_input_device(self.settings.input_device, devices)
            try:
                self._mic.open(sd, mic_device, self._on_mic)  # None = system default
                self.mic_available = True
            except Exception as exc:
                self.mic_available = False
                self.last_error = f"mic device unavailable: {exc}"
                print(f"[audio_engine] {self.last_error}")

        # System — null means auto-detect BlackHole; otherwise resolve the saved name.
        sysval = self.settings.system_device
        device = find_blackhole() if sysval is None else resolve_input_device(sysval, devices)
        if device is not None and not self._system.is_open:
            channels = _input_channels(device, default=2, cap=2)
            try:
                self._system.channels = channels
                self._system.open(sd, device, self._on_system)
                self.system_available = True
                self.last_error = None
            except Exception as exc:
                # No system audio is non-fatal: the mic still records.
                self.system_available = False
                self.last_error = f"system device unavailable: {exc}"
                print(f"[audio_engine] {self.last_error}")
        else:
            self.system_available = device is not None and self._system.is_open

    def _close_streams_if_idle(self) -> None:
        if self._monitoring or self._recording:
            return
        self._mic.close()
        self._system.close()

    # --- stream callbacks (PortAudio threads) ---
    def _on_mic(self, indata, frames, time_info, status):
        self._mic.level = rms_db(indata)
        if self._recording:
            self._mic.append(indata)
            # Frame count drives the elapsed timer without touching the clock.
            self._record_frames += frames

    def _on_system(self, indata, frames, time_info, status):
        self._system.level = rms_db(_as_mono(indata))
        if self._recording:
            self._system.append(indata)


class _Source:
    """One input stream plus its level and recording buffer."""

    def __init__(self, channels: int):
        self.channels = channels
        self.level = LEVEL_FLOOR_DB
        self._stream = None
        self._frames: list[np.ndarray] = []
        self._buf_lock = threading.Lock()

    @property
    def is_open(self) -> bool:
        return self._stream is not None

    def open(self, sd, device, callback) -> None:
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=self.channels,
            dtype="int16",
            device=device,
            callback=callback,
        )
        self._stream.start()

    def close(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self.level = LEVEL_FLOOR_DB

    def reset_buffer(self) -> None:
        with self._buf_lock:
            self._frames = []

    def append(self, indata) -> None:
        with self._buf_lock:
            # Copy: PortAudio reuses the indata buffer after the callback returns.
            self._frames.append(indata.copy())

    def collect(self) -> np.ndarray | None:
        with self._buf_lock:
            frames = self._frames
            self._frames = []
        if not frames:
            return None
        return np.concatenate(frames, axis=0)
