from __future__ import annotations

import io
import logging
import tempfile
from pathlib import Path

import numpy as np
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("abix.tts")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="ABIX TTS Service")

_model = None
_model_lock = None


def get_model():
    global _model
    if _model is None:
        try:
            import piper
            model_path = Path("/models")
            voice_files = list(model_path.glob("*.onnx")) if model_path.exists() else []
            if voice_files:
                _model = piper.PiperVoice.load(str(voice_files[0]))
                logger.info("Loaded Piper model: %s", voice_files[0].name)
            else:
                raise FileNotFoundError("No .onnx model found in /models")
        except Exception as e:
            logger.warning("Piper not available, using pyttsx3 fallback: %s", e)
            _model = "pyttsx3"
    return _model


@app.on_event("startup")
async def startup():
    try:
        get_model()
        logger.info("TTS service ready")
    except Exception as e:
        logger.warning("Could not pre-load TTS model: %s", e)


@app.post("/synthesize")
async def synthesize(request: Request):
    try:
        body = await request.json()
        text = body.get("text", "")

        model = get_model()

        if model == "pyttsx3":
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", 150)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
            engine.save_to_file(text, tmp_path)
            engine.runAndWait()
            with open(tmp_path, "rb") as f:
                audio_bytes = f.read()
            Path(tmp_path).unlink(missing_ok=True)
            return JSONResponse({"audio": list(audio_bytes), "format": "wav"})

        import piper
        import wave
        wav_buffer = io.BytesIO()
        audio_array = model.synthesize(text)

        def _chunk_to_pcm(chunk):
            b = getattr(chunk, "audio_int16_bytes", None)
            if b is not None:
                return bytes(b)
            arr = getattr(chunk, "audio_int16_array", None)
            if arr is not None:
                return np.asarray(arr).astype(np.int16).tobytes()
            return b""

        if hasattr(audio_array, "astype"):
            pcm = audio_array.astype(np.int16).tobytes()
        else:
            pcm = b"".join(_chunk_to_pcm(c) for c in audio_array)
        with wave.open(wav_buffer, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(22050)
            wf.writeframes(pcm)
        wav_bytes = wav_buffer.getvalue()
        return JSONResponse({"audio": list(wav_bytes), "format": "wav"})

    except Exception as e:
        logger.exception("Synthesis error")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "tts"}
