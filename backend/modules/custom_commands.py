from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger("abix.custom_commands")

_STORE_FILE = Path(__file__).parent.parent / "config" / "custom_commands.json"

# Curated subset of router intents that are safe and useful to bind to a
# fixed trigger phrase from the UI, mapped to the single argument key each
# one reads. None means the intent takes no argument. Intents needing more
# structure than one value (delete_file, create_routine, write_to_file, ...)
# are deliberately left out — those still go through full voice/NLU parsing.
AVAILABLE_INTENTS: dict[str, str | None] = {
    "open_app": "target",
    "close_app": "target",
    "open_file": "target",
    "open_url": "target",
    "web_search": "query",
    "play_youtube": "query",
    "run_command": "command",
    "media_play": None,
    "media_pause": None,
    "media_next": None,
    "volume_up": None,
    "volume_down": None,
    "volume_mute": None,
    "system_info": None,
}


class CustomCommand:
    def __init__(self, trigger: str, intent: str, argument: str = "", description: str = ""):
        self.trigger = trigger.upper()
        self.intent = intent
        self.argument = argument
        self.description = description

    def to_dict(self) -> dict:
        return {
            "trigger": self.trigger,
            "intent": self.intent,
            "argument": self.argument,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> CustomCommand:
        return cls(
            trigger=data.get("trigger", ""),
            intent=data.get("intent", ""),
            argument=data.get("argument", ""),
            description=data.get("description", ""),
        )

    def to_args(self) -> dict[str, str]:
        arg_key = AVAILABLE_INTENTS.get(self.intent)
        return {arg_key: self.argument} if arg_key else {}


class CustomCommandManager:
    def __init__(self) -> None:
        self._commands: dict[str, CustomCommand] = {}
        self.load()

    def load(self) -> None:
        if _STORE_FILE.exists():
            try:
                data = json.loads(_STORE_FILE.read_text())
                for item in data:
                    cmd = CustomCommand.from_dict(item)
                    self._commands[cmd.trigger] = cmd
                logger.info("Loaded %d custom commands", len(self._commands))
            except Exception as e:
                logger.warning("Failed to load custom commands: %s", e)

    def save(self) -> None:
        _STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = [c.to_dict() for c in self._commands.values()]
        _STORE_FILE.write_text(json.dumps(data, indent=2))

    def get_all(self) -> list[dict]:
        return [c.to_dict() for c in self._commands.values()]

    def get(self, trigger: str) -> CustomCommand | None:
        return self._commands.get(trigger.strip().upper())

    def add(self, trigger: str, intent: str, argument: str = "", description: str = "") -> str:
        trigger = trigger.strip().upper()
        if not trigger:
            return "Trigger phrase cannot be empty"
        if intent not in AVAILABLE_INTENTS:
            return f"Unknown intent: {intent}"
        self._commands[trigger] = CustomCommand(trigger, intent, argument, description)
        self.save()
        return f"Custom command '{trigger}' saved"

    def update(self, trigger: str, intent: str | None = None, argument: str | None = None, description: str | None = None) -> str:
        trigger = trigger.strip().upper()
        cmd = self._commands.get(trigger)
        if not cmd:
            return f"Custom command '{trigger}' not found"
        if intent is not None:
            if intent not in AVAILABLE_INTENTS:
                return f"Unknown intent: {intent}"
            cmd.intent = intent
        if argument is not None:
            cmd.argument = argument
        if description is not None:
            cmd.description = description
        self.save()
        return f"Custom command '{trigger}' updated"

    def delete(self, trigger: str) -> str:
        trigger = trigger.strip().upper()
        if trigger in self._commands:
            del self._commands[trigger]
            self.save()
            return f"Custom command '{trigger}' deleted"
        return f"Custom command '{trigger}' not found"
