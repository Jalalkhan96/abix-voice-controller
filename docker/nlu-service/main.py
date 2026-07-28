from __future__ import annotations

import sys
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.nlu.intent_parser import parse

logger = logging.getLogger("abix.nlu")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="ABIX NLU Service")


@app.post("/parse")
async def parse_intent(request: Request):
    try:
        body = await request.json()
        text = body.get("text", "")
        result = parse(text)
        return JSONResponse({
            "intent": result.intent,
            "target": result.target,
            "args": result.args,
            "confidence": result.confidence,
            "raw_text": result.raw_text,
        })
    except Exception as e:
        logger.exception("Parse error")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "nlu"}
