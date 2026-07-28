from __future__ import annotations

import io
import wave
import logging
import numpy as np
import sounddevice as sd

logger = logging.getLogger("abix.audio_capture")


class AudioCapture:
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        duration: float = 10.0,
    ) -> None:
        self._sample_rate = sample_rate
        self._channels = channels
        self._duration = duration

    def record(self) -> tuple[np.ndarray, int]:
        logger.info("Recording for %.1f seconds...", self._duration)
        audio = sd.rec(
            int(self._duration * self._sample_rate),
            samplerate=self._sample_rate,
            channels=self._channels,
            dtype="int16",
        )
        sd.wait()
        logger.info("Recording complete")
        return audio[:, 0], self._sample_rate

    def to_wav_bytes(self, audio: np.ndarray, sample_rate: int = 16000) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio.astype(np.int16).tobytes())
        return buf.getvalue()

    def get_amplitude(self, audio: np.ndarray) -> float:
        return float(np.sqrt(np.mean(audio.astype(np.float32) ** 2)))
