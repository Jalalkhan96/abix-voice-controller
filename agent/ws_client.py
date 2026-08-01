from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Callable, Awaitable

import httpx
import websockets
import websockets.exceptions

logger = logging.getLogger("abix.ws_client")

_FAILURE_THRESHOLD = 3
_COOLDOWN_SECONDS = 20


class ServiceClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._client: httpx.AsyncClient | None = None
        self._failure_count = 0
        self._cooldown_until = 0.0

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient()
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _breaker_open(self) -> bool:
        return time.monotonic() < self._cooldown_until

    def _record_failure(self) -> None:
        self._failure_count += 1
        if self._failure_count >= _FAILURE_THRESHOLD:
            self._cooldown_until = time.monotonic() + _COOLDOWN_SECONDS
            logger.warning(
                "%s: %d consecutive failures, pausing calls for %ds",
                self._base_url, self._failure_count, _COOLDOWN_SECONDS,
            )

    def _record_success(self) -> None:
        self._failure_count = 0
        self._cooldown_until = 0.0

    async def health_check(self) -> bool:
        try:
            client = self._get_client()
            r = await client.get(f"{self._base_url}/health", timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    async def transcribe(self, audio_bytes: bytes, language: str = "en") -> dict[str, Any]:
        if self._breaker_open():
            return {"error": "Service unavailable (circuit open)"}
        try:
            client = self._get_client()
            response = await client.post(
                f"{self._base_url}/transcribe",
                params={"language": language},
                content=audio_bytes,
                headers={"Content-Type": "audio/wav"},
                timeout=120,
            )
            self._record_success()
            return response.json()
        except Exception as e:
            logger.error("STT service error: %s", e)
            self._record_failure()
            return {"error": str(e)}

    async def synthesize(self, text: str, voice_prefix: str | None = None) -> dict[str, Any]:
        if self._breaker_open():
            return {"error": "Service unavailable (circuit open)"}
        try:
            client = self._get_client()
            response = await client.post(
                f"{self._base_url}/synthesize",
                json={"text": text, "voice_prefix": voice_prefix},
                timeout=30,
            )
            self._record_success()
            return response.json()
        except Exception as e:
            logger.error("TTS service error: %s", e)
            self._record_failure()
            return {"error": str(e)}

    async def parse_intent(self, text: str) -> dict[str, Any]:
        if self._breaker_open():
            return {"error": "Service unavailable (circuit open)"}
        try:
            client = self._get_client()
            response = await client.post(
                f"{self._base_url}/parse",
                json={"text": text},
                timeout=30,
            )
            self._record_success()
            return response.json()
        except Exception as e:
            logger.error("NLU service error: %s", e)
            self._record_failure()
            return {"error": str(e)}


class AgentWSServer:
    def __init__(self, port: int = 8765, token: str | None = None) -> None:
        self._port = port
        self._token = token
        self._clients: set = set()
        self._message_handler: Callable[[str], Awaitable[None]] | None = None
        self._on_no_clients: Callable[[], Awaitable[None]] | None = None

    def set_message_handler(self, handler: Callable[[str], Awaitable[None]]) -> None:
        self._message_handler = handler

    def set_on_no_clients(self, handler: Callable[[], Awaitable[None]]) -> None:
        self._on_no_clients = handler

    async def broadcast(self, message: dict[str, Any]) -> None:
        if not self._clients:
            return
        data = json.dumps(message)
        disconnected: set = set()
        for ws in list(self._clients):
            try:
                await ws.send(data)
            except (websockets.exceptions.ConnectionClosed, Exception):
                disconnected.add(ws)
        self._clients -= disconnected

    async def start(self) -> None:
        async def handler(websocket):
            if self._token is not None:
                try:
                    first_raw = await asyncio.wait_for(websocket.recv(), timeout=10)
                    first = json.loads(first_raw)
                except Exception:
                    await websocket.close(code=1008)
                    return
                if first.get("type") != "auth" or first.get("token") != self._token:
                    await websocket.send(json.dumps({"type": "auth_result", "success": False}))
                    await websocket.close(code=1008)
                    return
                await websocket.send(json.dumps({"type": "auth_result", "success": True}))

            self._clients.add(websocket)
            logger.info("UI client connected (%d total)", len(self._clients))
            try:
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        msg_type = data.get("type")
                        if msg_type == "user_input" and self._message_handler:
                            text = data.get("text", "")
                            asyncio.create_task(self._message_handler(text))
                        elif msg_type == "shortcut_list":
                            from backend.modules.shortcuts import ShortcutManager
                            sm = ShortcutManager()
                            await websocket.send(json.dumps({
                                "type": "shortcut_list",
                                "shortcuts": sm.get_all(),
                            }))
                        elif msg_type == "shortcut_add":
                            from backend.modules.shortcuts import ShortcutManager
                            sm = ShortcutManager()
                            result = sm.add(
                                data.get("keyword", ""),
                                data.get("browser", "brave-browser"),
                                data.get("url", ""),
                                data.get("description", ""),
                            )
                            await websocket.send(json.dumps({
                                "type": "shortcut_result",
                                "message": result,
                                "shortcuts": sm.get_all(),
                            }))
                        elif msg_type == "shortcut_update":
                            from backend.modules.shortcuts import ShortcutManager
                            sm = ShortcutManager()
                            result = sm.update(
                                data.get("keyword", ""),
                                browser=data.get("browser"),
                                url=data.get("url"),
                                description=data.get("description"),
                            )
                            await websocket.send(json.dumps({
                                "type": "shortcut_result",
                                "message": result,
                                "shortcuts": sm.get_all(),
                            }))
                        elif msg_type == "shortcut_delete":
                            from backend.modules.shortcuts import ShortcutManager
                            sm = ShortcutManager()
                            result = sm.delete(data.get("keyword", ""))
                            await websocket.send(json.dumps({
                                "type": "shortcut_result",
                                "message": result,
                                "shortcuts": sm.get_all(),
                            }))
                        elif msg_type == "custom_command_list":
                            from backend.modules.custom_commands import CustomCommandManager, AVAILABLE_INTENTS
                            cm = CustomCommandManager()
                            await websocket.send(json.dumps({
                                "type": "custom_command_list",
                                "commands": cm.get_all(),
                                "available_intents": AVAILABLE_INTENTS,
                            }))
                        elif msg_type == "custom_command_add":
                            from backend.modules.custom_commands import CustomCommandManager
                            cm = CustomCommandManager()
                            result = cm.add(
                                data.get("trigger", ""),
                                data.get("intent", ""),
                                data.get("argument", ""),
                                data.get("description", ""),
                            )
                            await websocket.send(json.dumps({
                                "type": "custom_command_result",
                                "message": result,
                                "commands": cm.get_all(),
                            }))
                        elif msg_type == "custom_command_update":
                            from backend.modules.custom_commands import CustomCommandManager
                            cm = CustomCommandManager()
                            result = cm.update(
                                data.get("trigger", ""),
                                intent=data.get("intent"),
                                argument=data.get("argument"),
                                description=data.get("description"),
                            )
                            await websocket.send(json.dumps({
                                "type": "custom_command_result",
                                "message": result,
                                "commands": cm.get_all(),
                            }))
                        elif msg_type == "custom_command_delete":
                            from backend.modules.custom_commands import CustomCommandManager
                            cm = CustomCommandManager()
                            result = cm.delete(data.get("trigger", ""))
                            await websocket.send(json.dumps({
                                "type": "custom_command_result",
                                "message": result,
                                "commands": cm.get_all(),
                            }))
                        elif msg_type == "get_settings":
                            from backend.modules.settings_store import get_editable
                            await websocket.send(json.dumps({
                                "type": "settings",
                                "settings": get_editable(),
                            }))
                        elif msg_type == "update_settings":
                            from backend.modules.settings_store import update
                            updated = update(data.get("fields", {}))
                            await websocket.send(json.dumps({
                                "type": "settings",
                                "settings": updated,
                                "message": "Settings saved. Restart ABIX to apply.",
                            }))
                        elif msg_type == "shutdown" and self._on_no_clients:
                            asyncio.create_task(self._on_no_clients())
                    except json.JSONDecodeError:
                        pass
            except websockets.exceptions.ConnectionClosed:
                pass
            finally:
                self._clients.discard(websocket)
                remaining = len(self._clients)
                logger.info("UI client disconnected (%d remaining)", remaining)
                if remaining == 0 and self._on_no_clients:
                    asyncio.create_task(self._on_no_clients())

        server = await websockets.serve(handler, "0.0.0.0", self._port)
        logger.info("WebSocket server started on port %d", self._port)
        await server.wait_closed()
