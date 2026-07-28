from __future__ import annotations

import io
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("abix.stt")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="ABIX STT Service")

_model = None


def get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        model_path = "/models"
        model_dir = Path(model_path)
        if not model_dir.exists():
            model_dir = Path("/models")
        _model = WhisperModel("small", device="cpu", compute_type="int8")
        logger.info("Loaded Whisper model")
    return _model


@app.on_event("startup")
async def startup():
    try:
        get_model()
        logger.info("STT service ready")
    except Exception as e:
        logger.warning("Could not pre-load model: %s", e)


@app.post("/transcribe")
async def transcribe(request: Request):
    try:
        body = await request.body()
        audio_bytes = body

        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        model = get_model()
        segments, info = model.transcribe(
            tmp_path,
            language="en",
            beam_size=5,
            best_of=5,
            vad_filter=True,
            temperature=0.0,
            condition_on_previous_text=False,
            no_speech_threshold=0.6,
            compression_ratio_threshold=2.4,
        )
        text = " ".join(segment.text for segment in segments).strip()
        logger.info("Transcribed (%.2f%% %s): %s", info.language_probability * 100, info.language, text)

        Path(tmp_path).unlink(missing_ok=True)

        return JSONResponse({
            "text": text,
            "language": info.language,
            "confidence": info.language_probability,
        })
    except Exception as e:
        logger.exception("Transcription error")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "stt"}
