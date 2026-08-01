from __future__ import annotations

import logging
from pathlib import Path

import yaml
from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware

from backend.safety.auth_token import get_or_create_token
from backend.safety.permissions import PermissionManager
from backend.safety.audit_log import AuditLog
from backend.router.command_router import CommandRouter

logger = logging.getLogger("abix.backend")
logging.basicConfig(level=logging.INFO)

def _load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    return {}


_config = _load_config()

app = FastAPI(title="ABIX Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_config.get("backend", {}).get("cors_origins", ["http://localhost:9080"]),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
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
_auth_token = get_or_create_token()

_ui_clients: set[WebSocket] = set()


def require_token(x_abix_token: str = Header(default="")) -> None:
    if x_abix_token != _auth_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing X-Abix-Token")


async def broadcast_to_ui(message: dict) -> None:
    global _ui_clients
    import json
    data = json.dumps(message)
    disconnected: set[WebSocket] = set()
    for ws in list(_ui_clients):
        try:
            await ws.send_text(data)
        except Exception:
            disconnected.add(ws)
    _ui_clients -= disconnected


@app.post("/command", dependencies=[Depends(require_token)])
async def execute_command(request: dict) -> dict:
    text = request.get("text", "")
    if not text:
        return {"error": "No text provided"}

    result = await _router.route(text)
    return {
        "intent": result.intent.intent,
        "target": result.intent.target,
        "tier": int(result.tier),
        "success": result.success,
        "response": result.response,
        "needs_confirmation": result.needs_confirmation,
        "confirmation_message": result.confirmation_message,
    }


@app.post("/confirm", dependencies=[Depends(require_token)])
async def confirm_command(request: dict) -> dict:
    result = await _router.execute_confirmed(
        request.get("action", ""),
        request.get("args", {}),
        request.get("original_text", ""),
    )
    return {
        "intent": result.intent.intent,
        "success": result.success,
        "response": result.response,
    }


@app.get("/history", dependencies=[Depends(require_token)])
async def get_history(limit: int = 50) -> list[dict]:
    return _audit.get_recent(limit)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        first = await websocket.receive_json()
    except Exception:
        await websocket.close(code=1008)
        return
    if first.get("type") != "auth" or first.get("token") != _auth_token:
        await websocket.send_json({"type": "auth_result", "success": False})
        await websocket.close(code=1008)
        return
    await websocket.send_json({"type": "auth_result", "success": True})

    _ui_clients.add(websocket)
    logger.info("UI connected via /ws (%d total)", len(_ui_clients))
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "command":
                text = data.get("text", "")
                result = await _router.route(text)
                await websocket.send_json({
                    "type": "command_result",
                    "intent": result.intent.intent,
                    "success": result.success,
                    "response": result.response,
                    "needs_confirmation": result.needs_confirmation,
                    "confirmation_message": result.confirmation_message,
                })
            elif data.get("type") == "confirm":
                result = await _router.execute_confirmed(
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
