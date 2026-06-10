"""Transcription for xRapture using faster-whisper.

The Whisper model is loaded lazily on first use — loading is slow and the
weights download on first run — then cached. Changing the model size reloads
on the next transcription.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from faster_whisper import WhisperModel


class Transcriber:
    """Wraps a faster-whisper model and writes transcripts beside WAV files."""

    def __init__(self, model_size: str = "base"):
        self._model_size = model_size
        self._model: WhisperModel | None = None

    def _ensure_model(self, model_size: str) -> WhisperModel:
        # (Re)load when there is no model yet or the requested size changed.
        if self._model is None or model_size != self._model_size:
            # CPU + int8 keeps this portable and dependency-light; GPU users can
            # change device/compute_type here without affecting callers.
            self._model = WhisperModel(model_size, device="cpu", compute_type="int8")
            self._model_size = model_size
        return self._model

    def transcribe(self, wav_path: Path, model_size: str | None = None, progress=None) -> Path:
        """Transcribe ``wav_path`` and write a ``.txt`` beside it.

        ``progress`` is an optional callback receiving a 0..1 fraction as
        transcription advances (derived from segment end times vs. total
        duration). Returns the path to the written transcript.
        """
        wav_path = Path(wav_path)
        model = self._ensure_model(model_size or self._model_size)

        # faster-whisper is lazy: work happens as we consume the segment
        # generator, so we can report progress per segment along the way.
        segments, info = model.transcribe(str(wav_path))
        duration = getattr(info, "duration", 0) or 0
        parts = []
        for segment in segments:
            parts.append(segment.text)
            if progress is not None and duration > 0:
                progress(min(segment.end / duration, 1.0))
        if progress is not None:
            progress(1.0)
        text = "".join(parts).strip()

        txt_path = wav_path.with_suffix(".txt")
        header = (
            f"Transcript of {wav_path.name}\n"
            f"Generated {datetime.now():%Y-%m-%d %H:%M}\n"
            f"{'-' * 40}\n\n"
        )
        txt_path.write_text(header + text + "\n")
        return txt_path
