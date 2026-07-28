from __future__ import annotations

from typing import Any

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.plugins.registry import Skill, SkillManifest


class WeatherSkill(Skill):
    def __init__(self) -> None:
        self._manifest = SkillManifest(
            name="weather",
            version="0.1.0",
            description="Get current weather information",
            author="ABIX Team",
            commands=[
                {"trigger": "what's the weather", "description": "Get current weather"},
                {"trigger": "weather forecast", "description": "Get weather forecast"},
            ],
        )

    @property
    def name(self) -> str:
        return "weather"

    @property
    def manifest(self) -> SkillManifest:
        return self._manifest

    def handle(self, intent: str, args: dict[str, Any]) -> str:
        return (
            "Weather plugin is a demo. "
            "To enable real weather data, install the 'requests' library "
            "and configure an API key in config/settings.yaml."
        )
