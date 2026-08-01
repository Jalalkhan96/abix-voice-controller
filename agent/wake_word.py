from __future__ import annotations

import logging
from collections import deque
from typing import Callable

import numpy as np
import sounddevice as sd

logger = logging.getLogger("abix.wake_word")

_VAD_THRESHOLD = 0.08
_VAD_PERSISTENCE = 8
_SILENCE_TIMEOUT = 0.6
_MAX_RECORD_SECONDS = 8.0


class VoiceListener:
    def __init__(
        self,
        sample_rate: int = 16000,
        vad_threshold: float = _VAD_THRESHOLD,
    ) -> None:
        self._sample_rate = sample_rate
        self._vad_threshold = vad_threshold
        self._chunk_size = 1280
        self.muted = False

    def listen_for_utterance(
        self,
        on_speech_start: Callable[[], None] | None = None,
        on_level: Callable[[float], None] | None = None,
    ) -> tuple[np.ndarray, int]:
        chunk_size = self._chunk_size
        silence_limit = int(_SILENCE_TIMEOUT * self._sample_rate / chunk_size)
        max_record_chunks = int(_MAX_RECORD_SECONDS * self._sample_rate / chunk_size)
        chunk_buffer: deque = deque(maxlen=_VAD_PERSISTENCE)

        with sd.InputStream(
            samplerate=self._sample_rate,
            channels=1,
            dtype="int16",
            blocksize=chunk_size,
        ) as stream:
            while True:
                audio_chunk, _ = stream.read(chunk_size)
                if self.muted:
                    continue
                audio_np = audio_chunk[:, 0].astype(np.float32) / 32768.0
                rms = float(np.sqrt(np.mean(audio_np ** 2)))
                chunk_buffer.append(audio_np)
                if (len(chunk_buffer) == chunk_buffer.maxlen
                        and all(float(np.sqrt(np.mean(c ** 2))) > self._vad_threshold for c in chunk_buffer)):
                    if on_speech_start is not None:
                        on_speech_start()
                    break

            recorded = list(chunk_buffer)
            silence_chunks = 0

            for _ in range(max_record_chunks - len(recorded)):
                audio_chunk, _ = stream.read(chunk_size)
                if self.muted:
                    recorded = list(chunk_buffer)
                    silence_chunks = 0
                    continue
                audio_np = audio_chunk[:, 0].astype(np.float32) / 32768.0
                recorded.append(audio_np)
                rms = float(np.sqrt(np.mean(audio_np ** 2)))
                if on_level is not None:
                    on_level(min(1.0, rms / (self._vad_threshold * 4)))
                if rms < self._vad_threshold:
                    silence_chunks += 1
                    if silence_chunks >= silence_limit:
                        break
                else:
                    silence_chunks = 0

        audio = (np.concatenate(recorded) * 32767).astype(np.int16)
        return audio, self._sample_rate
