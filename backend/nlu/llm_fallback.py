from __future__ import annotations

import json
import logging

import httpx

from backend.nlu.intent_parser import ParsedIntent

logger = logging.getLogger("abix.nlu.llm")

SYSTEM_PROMPT = """You are the intent parser for ABIX, a voice-controlled desktop assistant.

Given a user's spoken command, return a JSON object with these fields:
- "intent": one of [open_app, close_app, close_window, open_file, create_file, write_to_file, edit_file, delete_file, search_files, run_command, system_info, list_directory, media_play, media_pause, media_next, volume_up, volume_down, volume_mute, semantic_search, unknown]
- "target": the file name, app name, search query, or directory
- "args": an object with additional arguments (e.g. "content" for write_to_file, "command" for run_command, "query" for search/semantic_search)
- "confidence": a number 0-1

Rules:
- "search for X" or "find X" → intent "search_files" with args.query = X
- "find my budget spreadsheet" or "where is the report" → intent "semantic_search" with args.query = X (this searches file CONTENT, not just names)
- "open X" where X is an app name → intent "open_app"
- "open X" where X looks like a file → intent "open_file"
- "delete X" → intent "delete_file"
- "run Y" → intent "run_command" with args.command = Y

Return ONLY valid JSON, no explanation."""

FALLBACK_PROMPT = """Parse this voice command into a JSON intent object.
User said: "{text}"

Return JSON with fields: intent, target, args, confidence.
Only return the JSON object, nothing else."""


class LLMIntentParser:
    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "mistral",
        timeout: float = 10.0,
    ) -> None:
        self._ollama_url = ollama_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient()
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def warm_up(self) -> bool:
        """Send a lightweight request so Ollama loads the model before it's first needed."""
        try:
            client = self._get_client()
            response = await client.post(
                f"{self._ollama_url}/api/chat",
                json={
                    "model": self._model,
                    "messages": [{"role": "user", "content": "hi"}],
                    "stream": False,
                    "options": {"num_predict": 1},
                },
                timeout=self._timeout,
            )
            return response.status_code == 200
        except Exception as e:
            logger.debug("Ollama warm-up failed (will retry lazily on first real request): %s", e)
            return False

    async def parse(self, text: str) -> ParsedIntent | None:
        prompt = FALLBACK_PROMPT.format(text=text)
        try:
            response_text = await self._call_ollama(prompt)
            if response_text is None:
                return None
            return self._parse_response(response_text, text)
        except Exception as e:
            logger.warning("LLM parse failed: %s", e)
            return None

    async def _call_ollama(self, prompt: str) -> str | None:
        url = f"{self._ollama_url}/api/chat"
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 200,
            },
        }
        try:
            client = self._get_client()
            response = await client.post(url, json=payload, timeout=self._timeout)
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")
        except httpx.ConnectError:
            logger.debug("Ollama not running at %s", self._ollama_url)
            return None
        except Exception as e:
            logger.debug("Ollama call failed: %s", e)
            return None

    def _parse_response(self, response_text: str, original_text: str) -> ParsedIntent | None:
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            json_start = text.find("{")
            json_end = text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                try:
                    data = json.loads(text[json_start:json_end])
                except json.JSONDecodeError:
                    logger.debug("Could not parse LLM JSON: %s", text)
                    return None
            else:
                return None

        intent = data.get("intent", "unknown")
        target = data.get("target", "")
        args = data.get("args", {})
        confidence = float(data.get("confidence", 0.7))

        if not isinstance(args, dict):
            args = {}

        if intent == "semantic_search" and not args.get("query"):
            args["query"] = target or original_text
            target = args["query"]

        if intent == "search_files" and not args.get("query"):
            args["query"] = target or original_text

        if intent == "run_command" and not args.get("command"):
            args["command"] = target

        if intent == "write_to_file" and not args.get("content"):
            args["content"] = target

        return ParsedIntent(
            intent=intent,
            target=target or args.get("query", args.get("command", "")),
            args=args,
            confidence=confidence,
            raw_text=original_text,
        )
