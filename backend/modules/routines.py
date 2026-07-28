from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("abix.routines")


@dataclass
class RoutineStep:
    command: str
    delay_ms: int = 0
    condition: str | None = None


@dataclass
class Routine:
    name: str
    trigger_phrase: str
    steps: list[RoutineStep]
    description: str = ""
    repeat_count: int = 1
    created_at: str = ""
    last_run: str = ""


@dataclass
class MacroEntry:
    timestamp: str
    transcript: str
    intent: str
    response: str
    success: bool


class RoutineManager:
    def __init__(self, data_dir: str = "data") -> None:
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._routines_file = self._data_dir / "routines.json"
        self._macros_file = self._data_dir / "macros.json"
        self._routines: dict[str, Routine] = {}
        self._macros: list[MacroEntry] = []
        self._recording: list[MacroEntry] | None = None
        self._load_routines()
        self._load_macros()

    def _load_routines(self) -> None:
        if not self._routines_file.exists():
            return
        try:
            with open(self._routines_file) as f:
                data = json.load(f)
            for name, routine_data in data.items():
                steps = [RoutineStep(**s) for s in routine_data.get("steps", [])]
                self._routines[name] = Routine(
                    name=name,
                    trigger_phrase=routine_data.get("trigger_phrase", ""),
                    steps=steps,
                    description=routine_data.get("description", ""),
                    repeat_count=routine_data.get("repeat_count", 1),
                    created_at=routine_data.get("created_at", ""),
                    last_run=routine_data.get("last_run", ""),
                )
        except Exception as e:
            logger.warning("Failed to load routines: %s", e)

    def _save_routines(self) -> None:
        data = {}
        for name, routine in self._routines.items():
            data[name] = {
                "trigger_phrase": routine.trigger_phrase,
                "steps": [{"command": s.command, "delay_ms": s.delay_ms, "condition": s.condition} for s in routine.steps],
                "description": routine.description,
                "repeat_count": routine.repeat_count,
                "created_at": routine.created_at,
                "last_run": routine.last_run,
            }
        with open(self._routines_file, "w") as f:
            json.dump(data, f, indent=2)

    def _load_macros(self) -> None:
        if not self._macros_file.exists():
            return
        try:
            with open(self._macros_file) as f:
                data = json.load(f)
            self._macros = [MacroEntry(**entry) for entry in data]
        except Exception as e:
            logger.warning("Failed to load macros: %s", e)

    def _save_macros(self) -> None:
        data = [
            {
                "timestamp": m.timestamp,
                "transcript": m.transcript,
                "intent": m.intent,
                "response": m.response,
                "success": m.success,
            }
            for m in self._macros[-500:]
        ]
        with open(self._macros_file, "w") as f:
            json.dump(data, f, indent=2)

    def create_routine(
        self,
        name: str,
        trigger_phrase: str,
        steps: list[str],
        description: str = "",
        repeat_count: int = 1,
    ) -> str:
        routine_steps = [RoutineStep(command=cmd) for cmd in steps]
        now = datetime.now(timezone.utc).isoformat()
        routine = Routine(
            name=name,
            trigger_phrase=trigger_phrase.lower(),
            steps=routine_steps,
            description=description,
            repeat_count=repeat_count,
            created_at=now,
        )
        self._routines[name] = routine
        self._save_routines()
        return f"Created routine '{name}' with {len(steps)} steps. Say '{trigger_phrase}' to run it."

    def delete_routine(self, name: str) -> str:
        if name in self._routines:
            del self._routines[name]
            self._save_routines()
            return f"Deleted routine '{name}'"
        return f"Routine '{name}' not found"

    def list_routines(self) -> str:
        if not self._routines:
            return "No routines saved."
        lines = ["Saved routines:"]
        for name, r in self._routines.items():
            lines.append(f"  - {name} (\"{r.trigger_phrase}\") — {len(r.steps)} steps")
        return "\n".join(lines)

    def get_routine_steps(self, trigger_phrase: str) -> Routine | None:
        phrase = trigger_phrase.lower().strip()
        for routine in self._routines.values():
            if routine.trigger_phrase == phrase:
                return routine
        return None

    def record_macro(self) -> str:
        self._recording = []
        return "Recording started. Say 'stop recording' to finish."

    def stop_recording(self) -> str:
        if self._recording is None:
            return "Not recording."
        count = len(self._recording)
        self._macros.extend(self._recording)
        self._recording = None
        self._save_macros()
        return f"Recorded {count} commands."

    def record_step(self, transcript: str, intent: str, response: str, success: bool) -> None:
        if self._recording is None:
            return
        self._recording.append(MacroEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            transcript=transcript,
            intent=intent,
            response=response,
            success=success,
        ))

    @property
    def is_recording(self) -> bool:
        return self._recording is not None

    def get_macros(self, limit: int = 50) -> list[MacroEntry]:
        return self._macros[-limit:]

    def clear_macros(self) -> str:
        self._macros.clear()
        self._save_macros()
        return "Macro history cleared."
