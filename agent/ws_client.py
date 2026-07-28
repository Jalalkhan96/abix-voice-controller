from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Awaitable

import websockets
import websockets.exceptions

logger = logging.getLogger("abix.ws_client")


class ServiceClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    async def health_check(self) -> bool:
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{self._base_url}/health", timeout=5)
                return r.status_code == 200
        except Exception:
            return False

    async def transcribe(self, audio_bytes: bytes) -> dict[str, Any]:
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._base_url}/transcribe",
                    content=audio_bytes,
                    headers={"Content-Type": "audio/wav"},
                    timeout=120,
                )
                return response.json()
        except Exception as e:
            logger.error("STT service error: %s", e)
            return {"error": str(e)}

    async def synthesize(self, text: str) -> dict[str, Any]:
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._base_url}/synthesize",
                    json={"text": text},
                    timeout=30,
                )
                return response.json()
        except Exception as e:
            logger.error("TTS service error: %s", e)
            return {"error": str(e)}

    async def parse_intent(self, text: str) -> dict[str, Any]:
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._base_url}/parse",
                    json={"text": text},
                    timeout=30,
                )
                return response.json()
        except Exception as e:
            logger.error("NLU service error: %s", e)
            return {"error": str(e)}


class AgentWSServer:
    def __init__(self, port: int = 8765) -> None:
        self._port = port
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
