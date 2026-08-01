from __future__ import annotations

from pathlib import Path

from ruamel.yaml import YAML

_SETTINGS_PATH = Path(__file__).parent.parent.parent / "config" / "settings.yaml"

# Round-trip loader/dumper: preserves comments and key ordering in
# settings.yaml for everything the Settings UI doesn't touch, instead of
# collapsing the whole file to bare key/value pairs on every save.
_yaml = YAML()
_yaml.preserve_quotes = True


def _load():
    if _SETTINGS_PATH.exists():
        with open(_SETTINGS_PATH) as f:
            data = _yaml.load(f)
            return data if data is not None else {}
    return {}


def get_editable() -> dict:
    data = _load()
    agent = data.get("agent", {}) or {}
    services = data.get("services", {}) or {}
    return {
        "wake_word_phrase": agent.get("wake_word_phrase", "hi abix"),
        "listen_duration_seconds": agent.get("listen_duration_seconds", 10),
        "stt_url": (services.get("stt", {}) or {}).get("url", "http://localhost:8001"),
        "tts_url": (services.get("tts", {}) or {}).get("url", "http://localhost:8002"),
        "nlu_url": (services.get("nlu", {}) or {}).get("url", "http://localhost:8003"),
    }


def update(fields: dict) -> dict:
    data = _load()
    if "agent" not in data or data["agent"] is None:
        data["agent"] = {}
    if "services" not in data or data["services"] is None:
        data["services"] = {}
    for svc in ("stt", "tts", "nlu"):
        if svc not in data["services"] or data["services"][svc] is None:
            data["services"][svc] = {}

    if "wake_word_phrase" in fields:
        data["agent"]["wake_word_phrase"] = str(fields["wake_word_phrase"]).strip() or "hi abix"
    if "listen_duration_seconds" in fields:
        try:
            data["agent"]["listen_duration_seconds"] = max(3, int(fields["listen_duration_seconds"]))
        except (TypeError, ValueError):
            pass
    if fields.get("stt_url"):
        data["services"]["stt"]["url"] = str(fields["stt_url"]).strip()
    if fields.get("tts_url"):
        data["services"]["tts"]["url"] = str(fields["tts_url"]).strip()
    if fields.get("nlu_url"):
        data["services"]["nlu"]["url"] = str(fields["nlu_url"]).strip()

    _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_SETTINGS_PATH, "w") as f:
        _yaml.dump(data, f)

    return get_editable()
