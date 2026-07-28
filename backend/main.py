from __future__ import annotations

import logging
from pathlib import Path

import yaml
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.safety.permissions import PermissionManager
from backend.safety.audit_log import AuditLog
from backend.router.command_router import CommandRouter

logger = logging.getLogger("abix.backend")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="ABIX Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    return {}


_config = _load_config()
_perms = PermissionManager(
    whitelist_path=str(Path(__file__).parent.parent / "config" / "whitelist.yaml")
)
_audit = AuditLog(
    db_path=str(
        Path(__file__).parent.parent
        / _config.get("safety", {}).get("log_path", "data/audit.db")
    )
)
_router = CommandRouter(_perms, _audit)

_ui_clients: set[WebSocket] = set()


async def broadcast_to_ui(message: dict) -> None:
    import json
    data = json.dumps(message)
    disconnected: set[WebSocket] = set()
    for ws in list(_ui_clients):
        try:
            await ws.send_text(data)
        except Exception:
            disconnected.add(ws)
    _ui_clients -= disconnected


@app.post("/command")
async def execute_command(request: dict) -> dict:
    text = request.get("text", "")
    if not text:
        return {"error": "No text provided"}

    result = _router.route(text)
    return {
        "intent": result.intent.intent,
        "target": result.intent.target,
        "tier": int(result.tier),
        "success": result.success,
        "response": result.response,
        "needs_confirmation": result.needs_confirmation,
        "confirmation_message": result.confirmation_message,
    }


@app.post("/confirm")
async def confirm_command(request: dict) -> dict:
    result = _router.execute_confirmed(
        request.get("action", ""),
        request.get("args", {}),
        request.get("original_text", ""),
    )
    return {
        "intent": result.intent.intent,
        "success": result.success,
        "response": result.response,
    }


@app.get("/history")
async def get_history(limit: int = 50) -> list[dict]:
    return _audit.get_recent(limit)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    _ui_clients.add(websocket)
    logger.info("UI connected via /ws (%d total)", len(_ui_clients))
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "command":
                text = data.get("text", "")
                result = _router.route(text)
                await websocket.send_json({
                    "type": "command_result",
                    "intent": result.intent.intent,
                    "success": result.success,
                    "response": result.response,
                    "needs_confirmation": result.needs_confirmation,
                    "confirmation_message": result.confirmation_message,
                })
            elif data.get("type") == "confirm":
                result = _router.execute_confirmed(
                    data.get("action", ""),
                    data.get("args", {}),
                    data.get("original_text", ""),
                )
                await websocket.send_json({
                    "type": "command_result",
                    "intent": result.intent.intent,
                    "success": result.success,
                    "response": result.response,
                })
    except WebSocketDisconnect:
        pass
    finally:
        _ui_clients.discard(websocket)
        logger.info("UI disconnected from /ws (%d remaining)", len(_ui_clients))
