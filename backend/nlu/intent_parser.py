from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger("abix.nlu")


@dataclass
class ParsedIntent:
    intent: str
    target: str
    args: dict[str, str] = field(default_factory=dict)
    confidence: float = 1.0
    raw_text: str = ""


_RULES: list[tuple[str, re.Pattern[str], str, list[str]]] = [
    (
        "close_window",
        re.compile(r"^close\s+this\s+window$", re.IGNORECASE),
        "close_window",
        [],
    ),
    (
        "open_file",
        re.compile(r"^open\s+(?:the\s+)?(?:file\s+)?(.+\.\w+)$", re.IGNORECASE),
        "open_file",
        ["target"],
    ),
    (
        "open_file_with_keyword",
        re.compile(r"^open\s+(?:the\s+)?file\s+(.+)$", re.IGNORECASE),
        "open_file",
        ["target"],
    ),
    (
        "open_app",
        re.compile(r"^open\s+(?:the\s+)?(.+)$", re.IGNORECASE),
        "open_app",
        ["target"],
    ),
    (
        "close_app",
        re.compile(r"^close\s+(?:the\s+)?(.+)$", re.IGNORECASE),
        "close_app",
        ["target"],
    ),
    (
        "create_routine",
        re.compile(
            r"^create\s+(?:a\s+)?routine\s+(?:called\s+|named\s+)?(.+?)(?:\s+with\s+(.+))?$",
            re.IGNORECASE,
        ),
        "create_routine",
        ["target", "steps"],
    ),
    (
        "create_file",
        re.compile(r"^create\s+(?:a\s+)?(?:new\s+)?(?:file\s+)?(?:called\s+|named\s+)?(.+)$", re.IGNORECASE),
        "create_file",
        ["target"],
    ),
    (
        "write_to_file",
        re.compile(
            r"^(?:write|save|put)\s+['\"](.+?)['\"]\s+(?:to|in|into)\s+(?:the\s+)?(?:file\s+)?(.+)$",
            re.IGNORECASE,
        ),
        "write_to_file",
        ["content", "target"],
    ),
    (
        "edit_file",
        re.compile(
            r"^(?:edit|modify|change)\s+(?:the\s+)?(?:file\s+)?(.+)$",
            re.IGNORECASE,
        ),
        "edit_file",
        ["target"],
    ),
    (
        "delete_routine",
        re.compile(r"^delete\s+(?:the\s+)?routine\s+(.+)$", re.IGNORECASE),
        "delete_routine",
        ["target"],
    ),
    (
        "delete_file",
        re.compile(
            r"^(?:delete|remove|trash)\s+(?:the\s+)?(?:file\s+)?(.+)$",
            re.IGNORECASE,
        ),
        "delete_file",
        ["target"],
    ),
    (
        "semantic_search",
        re.compile(
            r"^(?:find|where\s+is|locate)\s+(?:my\s+|the\s+)?(.+)$",
            re.IGNORECASE,
        ),
        "semantic_search",
        ["query"],
    ),
    (
        "web_search",
        re.compile(r"^(?:search|find|look\s+up)\s+(?:for\s+)?(.+?)(?:\s+(?:on|using|with)\s+(.+))?$", re.IGNORECASE),
        "web_search",
        ["query", "engine"],
    ),
    (
        "search_files",
        re.compile(
            r"^(?:grep)\s+(?:for\s+)?(?:the\s+)?(.+)$",
            re.IGNORECASE,
        ),
        "search_files",
        ["query"],
    ),
    (
        "run_routine",
        re.compile(r"^(?:run|execute|start)\s+(?:the\s+)?routine\s+(.+)$", re.IGNORECASE),
        "run_routine",
        ["target"],
    ),
    (
        "run_command",
        re.compile(
            r"^(?:run|execute|do)\s+(.+)$",
            re.IGNORECASE,
        ),
        "run_command",
        ["command"],
    ),
    (
        "system_info",
        re.compile(
            r"^(?:what(?:'s| is)\s+)?(?:the\s+)?(?:how\s+much\s+)?(?:disk\s+space|free\s+space|memory|ram|cpu|system\s+info)|^how\s+much\s+(?:memory|ram|disk|space|cpu)",
            re.IGNORECASE,
        ),
        "system_info",
        [],
    ),
    (
        "list_directory",
        re.compile(
            r"^(?:list|show|what(?:'s| is))\s+(?:in\s+)?(?:the\s+)?(?:this\s+)?(?:directory|folder|here)\s*(.+)?$",
            re.IGNORECASE,
        ),
        "list_directory",
        ["target"],
    ),
    (
        "index_files",
        re.compile(
            r"^(?:index|scan|reindex)\s+(?:the\s+)?(?:files?|directory|folder)\s*(.+)?$",
            re.IGNORECASE,
        ),
        "index_files",
        ["target"],
    ),
    (
        "media_play",
        re.compile(r"^(?:play|start)\s+(?:the\s+)?(?:music|media|song|audio)$", re.IGNORECASE),
        "media_play",
        [],
    ),
    (
        "media_pause",
        re.compile(r"^(?:pause|stop|halt)(?:\s+(?:the\s+)?(?:music|media|song|audio))?$", re.IGNORECASE),
        "media_pause",
        [],
    ),
    (
        "media_next",
        re.compile(r"^(?:next|skip)\s+(?:track|song)?$", re.IGNORECASE),
        "media_next",
        [],
    ),
    (
        "volume_up",
        re.compile(r"^(?:turn\s+up|increase|raise)\s+(?:the\s+)?volume$", re.IGNORECASE),
        "volume_up",
        [],
    ),
    (
        "volume_down",
        re.compile(r"^(?:turn\s+down|decrease|lower)\s+(?:the\s+)?volume$", re.IGNORECASE),
        "volume_down",
        [],
    ),
    (
        "volume_mute",
        re.compile(r"^(?:mute|unmute)\s+(?:the\s+)?(?:volume|sound|audio)?$", re.IGNORECASE),
        "volume_mute",
        [],
    ),
    (
        "hand_tracking_toggle",
        re.compile(r"^(?:turn\s+on|enable|start|activate)\s+(?:the\s+)?hand\s+tracking$", re.IGNORECASE),
        "hand_tracking_toggle",
        ["action"],
    ),
    (
        "hand_tracking_off",
        re.compile(r"^(?:turn\s+off|disable|stop|deactivate)\s+(?:the\s+)?hand\s+tracking$", re.IGNORECASE),
        "hand_tracking_off",
        [],
    ),
    (
        "undo",
        re.compile(r"^undo(?:\s+that)?$", re.IGNORECASE),
        "undo",
        [],
    ),
    (
        "undo_list",
        re.compile(r"^(?:show|list)\s+(?:the\s+)?(?:undo(?:\s+history)?|history|last\s+actions)$", re.IGNORECASE),
        "undo_list",
        [],
    ),
    (
        "list_routines",
        re.compile(r"^(?:show|list)\s+(?:the\s+)?(?:my\s+)?routines?$", re.IGNORECASE),
        "list_routines",
        [],
    ),
    (
        "start_recording",
        re.compile(r"^start\s+(?:a\s+)?(?:macro\s+)?recording$", re.IGNORECASE),
        "start_recording",
        [],
    ),
    (
        "stop_recording",
        re.compile(r"^stop\s+(?:the\s+)?(?:macro\s+)?recording$", re.IGNORECASE),
        "stop_recording",
        [],
    ),
    (
        "list_macros",
        re.compile(r"^(?:show|list)\s+(?:the\s+)?(?:my\s+)?macros?$", re.IGNORECASE),
        "list_macros",
        [],
    ),
    (
        "list_skills",
        re.compile(r"^(?:show|list)\s+(?:the\s+)?(?:my\s+)?(?:skills?|plugins?)$", re.IGNORECASE),
        "list_skills",
        [],
    ),
    (
        "enroll_voice",
        re.compile(r"^(?:enroll|register|add)\s+(?:my\s+)?voice(?:\s+(?:for\s+)?(.+))?$", re.IGNORECASE),
        "enroll_voice",
        ["target"],
    ),
    (
        "verify_voice",
        re.compile(r"^(?:verify|check)\s+(?:my\s+)?voice$", re.IGNORECASE),
        "verify_voice",
        [],
    ),
    (
        "list_voice_profiles",
        re.compile(r"^(?:show|list)\s+(?:the\s+)?(?:my\s+)?voice\s+profiles?$", re.IGNORECASE),
        "list_voice_profiles",
        [],
    ),
    (
        "train_wakeword",
        re.compile(r"^(?:train|create)\s+(?:a\s+)?(?:custom\s+)?wake\s+word\s+(?:for\s+)?(.+)$", re.IGNORECASE),
        "train_wakeword",
        ["target"],
    ),
    (
        "list_wakewords",
        re.compile(r"^(?:show|list)\s+(?:the\s+)?(?:my\s+)?(?:custom\s+)?wake\s+words?$", re.IGNORECASE),
        "list_wakewords",
        [],
    ),
    (
        "open_url",
        re.compile(r"^(?:go\s+to|navigate\s+to)\s+(.+)$", re.IGNORECASE),
        "open_url",
        ["target"],
    ),
    (
        "play_youtube",
        re.compile(r"^(?:play|play\s+me|search\s+for)\s+(.+?)(?:\s+on\s+youtube)?$", re.IGNORECASE),
        "play_youtube",
        ["query"],
    ),
]


def parse_rules(text: str) -> ParsedIntent | None:
    text = text.strip()
    for _name, pattern, intent, fields in _RULES:
        match = pattern.match(text)
        if match:
            args: dict[str, str] = {}
            groups = match.groups()
            for i, field_name in enumerate(fields):
                if i < len(groups) and groups[i]:
                    args[field_name] = groups[i].strip()
            return ParsedIntent(
                intent=intent,
                target=args.get("target", args.get("query", args.get("command", ""))),
                args=args,
                confidence=0.95,
                raw_text=text,
            )
    return None


def parse(text: str) -> ParsedIntent:
    result = parse_rules(text)
    if result:
        return result
    return ParsedIntent(
        intent="unknown",
        target=text,
        args={"raw": text},
        confidence=0.0,
        raw_text=text,
    )


async def parse_with_llm(text: str, llm_parser) -> ParsedIntent:
    result = parse_rules(text)
    if result and result.intent != "unknown":
        return result

    if llm_parser is not None:
        llm_result = await llm_parser.parse(text)
        if llm_result is not None and llm_result.intent != "unknown":
            logger.info("LLM resolved intent: %s (confidence: %.2f)", llm_result.intent, llm_result.confidence)
            return llm_result

    return ParsedIntent(
        intent="unknown",
        target=text,
        args={"raw": text},
        confidence=0.0,
        raw_text=text,
    )
