from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.ws_client import AgentWSServer, ServiceClient
from backend.safety.permissions import PermissionManager
from backend.safety.audit_log import AuditLog
from backend.router.command_router import CommandRouter

logger = logging.getLogger("abix.agent")


def load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    return {}


class AbixAgent:
    def __init__(self) -> None:
        self._config = load_config()
        self._perms = PermissionManager(
            whitelist_path=str(
                Path(__file__).parent.parent / "config" / "whitelist.yaml"
            )
        )
        self._audit = AuditLog(
            db_path=str(
                Path(__file__).parent.parent
                / self._config.get("safety", {}).get("log_path", "data/audit.db")
            )
        )
        self._router = CommandRouter(self._perms, self._audit)
        self._ws_server = AgentWSServer(
            port=self._config.get("ui", {}).get("websocket_port", 8765)
        )
        self._ws_server.set_message_handler(self.handle_user_input)
        self._ws_server.set_on_no_clients(self._shutdown)

        services_cfg = self._config.get("services", {})
        self._stt_client = ServiceClient(
            services_cfg.get("stt", {}).get("url", "http://localhost:8001")
        )
        self._tts_client = ServiceClient(
            services_cfg.get("tts", {}).get("url", "http://localhost:8002")
        )
        self._nlu_client = ServiceClient(
            services_cfg.get("nlu", {}).get("url", "http://localhost:8003")
        )

        self._greeting = self._config.get("agent", {}).get(
            "greeting", "Hi, I'm ABIX — do you need any help?"
        )
        self._state = "idle"
        self._pending_confirmation: dict | None = None
        self._hand_tracking_active = False
        self._hand_tracker = None
        self._virtual_mouse = None
        self._last_speak_time = 0.0

    @staticmethod
    def _strip_wake_word(text: str) -> str:
        wake_phrases = [
            "hi abix",
            "hey abix",
            "hey jarvis",
            "hey a b i x",
            "hi a b i x",
            "abix",
        ]
        lower = text.lower().strip().rstrip(".,!?")
        for phrase in wake_phrases:
            if lower.startswith(phrase):
                rest = text[len(phrase):].strip().lstrip(", ")
                if rest:
                    return rest
                return text
        return text

    @staticmethod
    def _clean_transcript(text: str) -> str:
        import re
        text = text.strip()
        text = re.sub(r'\b(\w+)\s+(?=\1\b)', '', text)
        text = re.sub(r'\b(\w+\s+\w+)\s+(?=\1\b)', '', text)
        text = re.sub(r'[^\x00-\x7F]+', '', text)
        return text.strip()

    async def _update_state(self, state: str) -> None:
        self._state = state
        await self._ws_server.broadcast({
            "type": "state_change",
            "state": state,
        })

    async def _send_caption(self, text: str, role: str = "user") -> None:
        await self._ws_server.broadcast({
            "type": "caption",
            "text": text,
            "role": role,
        })

    async def _speak(self, text: str) -> None:
        logger.info("TTS: '%s'", text)
        await self._update_state("speaking")
        await self._send_caption(text, role="abix")

        try:
            result = await self._tts_client.synthesize(text)
            if "error" not in result and "audio" in result:
                audio_data = result["audio"]
                if audio_data:
                    import io as _io
                    import wave as _wave
                    import sounddevice as sd
                    import time
                    wav_bytes = bytes(audio_data)
                    with _io.BytesIO(wav_bytes) as buf:
                        with _wave.open(buf, "rb") as wf:
                            framerate = wf.getframerate()
                            frames = wf.readframes(wf.getnframes())
                            audio_np = (
                                np.frombuffer(frames, dtype=np.int16)
                                .astype(np.float32)
                                / 32767.0
                            )
                    sd.play(audio_np, samplerate=framerate)
                    self._last_speak_time = time.time()
                    sd.wait()
        except Exception as e:
            logger.warning("TTS playback failed: %s", e)

        await self._update_state("idle")

    async def handle_user_input(self, text: str) -> None:
        text = text.strip()
        if not text:
            return

        if self._pending_confirmation:
            await self._handle_confirmation(text)
            return

        await self._update_state("thinking")
        await self._send_caption(text, role="user")

        cmd = text.lower().strip().rstrip(".")
        if cmd in ("open settings", "show settings", "settings panel"):
            await self._ws_server.broadcast({"type": "ui_action", "action": "open_settings"})
            await self._speak("Opening settings panel.")
            return
        if cmd in ("open shortcuts", "show shortcuts", "shortcuts panel"):
            await self._ws_server.broadcast({"type": "ui_action", "action": "open_shortcuts"})
            await self._speak("Opening shortcuts panel.")
            return
        if cmd in ("close panel", "hide panel"):
            await self._ws_server.broadcast({"type": "ui_action", "action": "close_panel"})
            await self._speak("Closing panel.")
            return
        if cmd in ("minimize", "minimize window"):
            await self._ws_server.broadcast({"type": "ui_action", "action": "minimize"})
            return
        if cmd in ("maximize", "maximize window", "fullscreen"):
            await self._ws_server.broadcast({"type": "ui_action", "action": "maximize"})
            return
        if cmd in ("exit", "quit", "close", "close abix", "shutdown"):
            await self._speak("Goodbye.")
            await self._ws_server.broadcast({"type": "ui_action", "action": "close"})
            return
        if cmd in ("turn on hand tracking", "enable hand tracking", "start hand tracking", "activate hand tracking"):
            await self._toggle_hand_tracking(True)
            return
        if cmd in ("turn off hand tracking", "disable hand tracking", "stop hand tracking", "deactivate hand tracking"):
            await self._toggle_hand_tracking(False)
            return

        result = self._router.route(text)
        logger.info("Router: intent=%s response='%s' needs_confirmation=%s", result.intent.intent, result.response, result.needs_confirmation)

        if result.needs_confirmation:
            self._pending_confirmation = {
                "action": result.pending_action,
                "args": result.pending_args,
                "original_text": text,
            }
            await self._ws_server.broadcast({
                "type": "confirmation_needed",
                "message": result.confirmation_message,
                "action": result.pending_action,
                "args": result.pending_args,
            })
            await self._speak(result.confirmation_message)
            return

        await self._speak(result.response)
        await self._ws_server.broadcast({
            "type": "command_result",
            "success": result.success,
            "response": result.response,
            "intent": result.intent.intent,
            "tier": int(result.tier),
        })

    async def _toggle_hand_tracking(self, enable: bool) -> None:
        if enable:
            if self._hand_tracking_active:
                await self._speak("Hand tracking is already on.")
                return
            try:
                from agent.hand_tracking import HandTracker
                from agent.virtual_mouse import VirtualMouse
                self._hand_tracker = HandTracker()
                self._virtual_mouse = VirtualMouse()
                self._hand_tracking_active = True
                loop = asyncio.get_event_loop()
                loop.run_in_executor(None, self._run_hand_tracking)
                await self._speak("Hand tracking is now on. Move your index finger to control the cursor.")
            except Exception as e:
                logger.error("Failed to start hand tracking: %s", e)
                await self._speak("Could not start hand tracking. Is your camera connected?")
        else:
            if not self._hand_tracking_active:
                await self._speak("Hand tracking is already off.")
                return
            self._hand_tracking_active = False
            self._hand_tracker = None
            self._virtual_mouse = None
            await self._speak("Hand tracking is now off.")

    def _run_hand_tracking(self) -> None:
        import cv2
        cap = cv2.VideoCapture(self._config.get("hand_tracking", {}).get("camera_index", 0))
        try:
            while self._hand_tracking_active and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                landmarks = self._hand_tracker.process_frame(frame) if self._hand_tracker else None
                if landmarks and self._virtual_mouse:
                    self._virtual_mouse.update(landmarks)
        finally:
            cap.release()

    async def _handle_confirmation(self, text: str) -> None:
        text_lower = text.lower().strip()
        pending = self._pending_confirmation
        self._pending_confirmation = None

        if text_lower in ("yes", "y", "confirm", "proceed", "do it"):
            result = self._router.execute_confirmed(
                pending["action"],
                pending["args"],
                pending["original_text"],
            )
            await self._speak(result.response)
            await self._ws_server.broadcast({
                "type": "command_result",
                "success": result.success,
                "response": result.response,
                "intent": result.intent.intent,
                "tier": int(result.tier),
            })
        elif text_lower in ("no", "n", "cancel", "never mind", "stop"):
            await self._speak("OK, cancelled.")
        else:
            await self._speak("I didn't catch that. Say yes to confirm or no to cancel.")

    async def _shutdown(self) -> None:
        logger.info("Shutting down ABIX agent...")
        import os
        os._exit(0)

    async def _greet(self) -> None:
        await self._speak(self._greeting)

    async def run(self) -> None:
        logger.info("Starting ABIX agent...")

        asyncio.create_task(self._ws_server.start())

        await asyncio.sleep(1)

        await self._greet()

        await self._listen_loop()

    async def _listen_loop(self) -> None:
        try:
            from agent.wake_word import VoiceListener
            from agent.audio_capture import AudioCapture
        except Exception as e:
            logger.error("Voice capture unavailable (mic/PortAudio): %s", e)
            logger.info("Agent continues without voice input; typed input still works.")
            return

        agent_cfg = self._config.get("agent", {})
        try:
            listener = VoiceListener(
                sample_rate=agent_cfg.get("audio_sample_rate", 16000),
            )
            capture = AudioCapture(
                sample_rate=agent_cfg.get("audio_sample_rate", 16000),
                duration=agent_cfg.get("listen_duration_seconds", 10),
            )
        except Exception as e:
            logger.error("Could not initialise voice capture: %s", e)
            return

        loop = asyncio.get_event_loop()

        while True:
            try:
                await self._update_state("idle")

                import time
                since_speak = time.time() - self._last_speak_time
                if since_speak < 3.0:
                    await asyncio.sleep(3.0 - since_speak)

                def on_speech_start():
                    asyncio.run_coroutine_threadsafe(
                        self._update_state("listening"), loop
                    )

                audio, sample_rate = await loop.run_in_executor(
                    None, listener.listen_for_utterance, on_speech_start
                )

                if audio.size == 0:
                    continue

                duration_s = audio.size / sample_rate
                if duration_s < 1.5:
                    logger.info("Audio too short (%.1fs), skipping", duration_s)
                    continue

                await self._update_state("thinking")

                wav_bytes = capture.to_wav_bytes(audio, sample_rate)
                result = await self._stt_client.transcribe(wav_bytes)

                transcript = result.get("text", "")
                logger.info("STT transcript: '%s'", transcript)
                if not transcript:
                    continue
                cleaned = self._strip_wake_word(transcript)
                cleaned = self._clean_transcript(cleaned)
                logger.info("After cleanup: '%s'", cleaned)
                if len(cleaned.strip()) < 3:
                    logger.info("Transcript too short, skipping")
                    continue
                await self.handle_user_input(cleaned)
            except Exception as e:
                logger.warning("Listen loop error: %s", e)
                await asyncio.sleep(5)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    agent = AbixAgent()
    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        logger.info("ABIX shutting down")


if __name__ == "__main__":
    main()
