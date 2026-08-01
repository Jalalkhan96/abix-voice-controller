from __future__ import annotations

import asyncio
import logging
import time
import webbrowser
from dataclasses import dataclass, field

from backend.nlu.intent_parser import ParsedIntent, parse
from backend.nlu.llm_fallback import LLMIntentParser
from backend.safety.permissions import PermissionManager, PermissionTier
from backend.safety.audit_log import AuditLog
from backend.modules.file_ops import FileOps
from backend.modules.system_automation import SystemAutomation
from backend.modules.cli_executor import CLIExecutor
from backend.modules.app_launcher import AppLauncher
from backend.modules.semantic_search import SemanticSearchEngine
from backend.modules.routines import RoutineManager
from backend.modules.undo import UndoManager, build_undo_entry
from backend.modules.shortcuts import ShortcutManager
from backend.modules.custom_commands import CustomCommandManager
from backend.modules.voiceprint import VoiceprintVerifier
from backend.plugins.registry import SkillRegistry
from backend.router.handlers import command, get_registry

logger = logging.getLogger("abix.router")

# Intents safe to cache by exact transcript: idempotent for a given input and
# expensive enough (disk I/O, embeddings, subprocess) that a short-lived repeat
# is worth skipping. Deliberately excludes SAFE-tier intents whose output
# reflects mutable state that *other* commands change (undo_list, list_macros,
# list_routines) — those are cheap in-memory reads anyway, so caching them
# would only add staleness risk with no perf benefit.
_CACHEABLE_INTENTS = frozenset({
    "system_info",
    "list_directory",
    "search_files",
    "semantic_search",
    "list_skills",
    "list_wakewords",
    "list_voice_profiles",
    "open_file",
})
_CACHE_TTL_SECONDS = 5.0


@dataclass
class RouteResult:
    intent: ParsedIntent
    tier: PermissionTier
    response: str
    success: bool
    needs_confirmation: bool = False
    confirmation_message: str = ""
    pending_action: str = ""
    pending_args: dict[str, str] = field(default_factory=dict)


class CommandRouter:
    def __init__(
        self,
        permission_manager: PermissionManager,
        audit_log: AuditLog,
        ollama_url: str = "http://localhost:11434",
        ollama_model: str = "mistral",
    ) -> None:
        self._perms = permission_manager
        self._audit = audit_log
        self._file_ops = FileOps()
        self._sys_auto = SystemAutomation()
        self._cli = CLIExecutor()
        self._app_launcher = AppLauncher()
        self._shortcuts = ShortcutManager()
        self._custom_commands = CustomCommandManager()
        self._voiceprint = VoiceprintVerifier()
        self._last_file: str | None = None
        self._last_response: str = ""

        self._llm_parser = LLMIntentParser(
            ollama_url=ollama_url,
            model=ollama_model,
        )
        self._semantic = SemanticSearchEngine()
        self._routines = RoutineManager()
        self._undo = UndoManager()
        self._plugins = SkillRegistry()
        self._plugins.discover()
        self._handlers = get_registry()
        self._result_cache: dict[str, tuple[float, RouteResult]] = {}

    def _get_cached(self, key: str) -> RouteResult | None:
        entry = self._result_cache.get(key)
        if entry is None:
            return None
        cached_at, result = entry
        if time.monotonic() - cached_at > _CACHE_TTL_SECONDS:
            del self._result_cache[key]
            return None
        return result

    def _store_cache(self, key: str, intent_name: str, result: RouteResult) -> None:
        if intent_name in _CACHEABLE_INTENTS and result.success:
            self._result_cache[key] = (time.monotonic(), result)

    async def warm_up(self) -> None:
        """Fire a lightweight Ollama request so the model is loaded before first real use."""
        try:
            ok = await self._llm_parser.warm_up()
            logger.info("LLM warm-up %s", "succeeded" if ok else "skipped (Ollama unavailable)")
        except Exception as e:
            logger.debug("LLM warm-up failed: %s", e)

    async def route(self, text: str) -> RouteResult:
        t_start = time.perf_counter()

        plugin_result = self._try_plugins(text)
        if plugin_result is not None:
            return plugin_result

        shortcut_result = self._try_shortcut(text)
        if shortcut_result is not None:
            return shortcut_result

        cache_key = text.strip().lower()
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        intent = self._try_custom_command(text) or parse(text)
        t_parsed = time.perf_counter()

        if intent.intent == "unknown":
            intent = await self._try_llm_fallback(text)
        t_nlu = time.perf_counter()

        tier = self._tier_for(intent.intent)

        if intent.intent == "unknown":
            response = "I didn't understand that command."
            self._audit.log(
                transcript=text,
                intent="unknown",
                tier=tier,
                outcome="failed",
                details="No matching intent",
            )
            return RouteResult(
                intent=intent,
                tier=tier,
                response=response,
                success=False,
            )

        permission = self._perms.check(text, tier)
        t_perm = time.perf_counter()

        if not permission.allowed:
            self._audit.log(
                transcript=text,
                intent=intent.intent,
                tier=tier,
                outcome="blocked",
                details=permission.reason,
            )
            return RouteResult(
                intent=intent,
                tier=tier,
                response=f"Command blocked: {permission.reason}",
                success=False,
            )

        if permission.requires_confirmation:
            confirm_msg = self._build_confirmation(intent)
            return RouteResult(
                intent=intent,
                tier=tier,
                response=confirm_msg,
                success=False,
                needs_confirmation=True,
                confirmation_message=confirm_msg,
                pending_action=intent.intent,
                pending_args=intent.args,
            )

        result = await self._execute(intent, tier, text)
        self._store_cache(cache_key, intent.intent, result)
        t_done = time.perf_counter()
        logger.debug(
            "route timings (ms) parse=%.1f nlu_fallback=%.1f perm=%.1f exec=%.1f total=%.1f intent=%s",
            (t_parsed - t_start) * 1000,
            (t_nlu - t_parsed) * 1000,
            (t_perm - t_nlu) * 1000,
            (t_done - t_perm) * 1000,
            (t_done - t_start) * 1000,
            intent.intent,
        )
        return result

    def _tier_for(self, intent: str) -> PermissionTier:
        spec = self._handlers.get(intent)
        return spec.tier if spec is not None else PermissionTier.WRITE

    def _try_plugins(self, text: str) -> RouteResult | None:
        for trigger, skill_name in self._plugins.registered_triggers.items():
            if trigger in text.lower():
                response = self._plugins.handle_command(trigger)
                if response is not None:
                    return RouteResult(
                        intent=ParsedIntent(
                            intent="plugin",
                            target=skill_name,
                            args={"trigger": trigger},
                            raw_text=text,
                        ),
                        tier=PermissionTier.WRITE,
                        response=response,
                        success=True,
                    )
        return None

    def _try_shortcut(self, text: str) -> RouteResult | None:
        keyword = text.strip().upper()
        sc = self._shortcuts.get(keyword)
        if not sc:
            return None
        response = self._shortcuts.execute(keyword)
        return RouteResult(
            intent=ParsedIntent(intent="shortcut", target=keyword, args={"keyword": keyword}, confidence=1.0),
            response=response,
            success=True,
            tier=PermissionTier.WRITE,
        )

    def _try_custom_command(self, text: str) -> ParsedIntent | None:
        cmd = self._custom_commands.get(text)
        if cmd is None:
            return None
        return ParsedIntent(
            intent=cmd.intent,
            target=cmd.argument,
            args=cmd.to_args(),
            confidence=1.0,
            raw_text=text,
        )

    async def _try_llm_fallback(self, text: str) -> ParsedIntent:
        try:
            result = await self._llm_parser.parse(text)
            if result is not None and result.intent != "unknown":
                logger.info("LLM resolved: %s -> %s", text, result.intent)
                return result
        except Exception as e:
            logger.debug("LLM fallback failed: %s", e)
        return ParsedIntent(
            intent="unknown",
            target=text,
            args={"raw": text},
            confidence=0.0,
            raw_text=text,
        )

    async def execute_confirmed(self, action: str, args: dict[str, str], original_text: str) -> RouteResult:
        intent = ParsedIntent(
            intent=action,
            target=args.get("target", args.get("query", args.get("command", ""))),
            args=args,
            raw_text=original_text,
        )
        tier = self._tier_for(action)
        return await self._execute(intent, tier, original_text)

    async def _execute(self, intent: ParsedIntent, tier: PermissionTier, transcript: str) -> RouteResult:
        try:
            response = await self._dispatch(intent)

            if intent.intent not in ("undo", "undo_list", "list_routines", "list_macros", "list_skills", "system_info", "list_directory"):
                entry = build_undo_entry(intent.intent, intent.args.get("target", ""), response)
                if entry:
                    self._undo.record(entry)

            if self._routines.is_recording and intent.intent not in ("start_recording", "stop_recording", "list_macros"):
                self._routines.record_step(transcript, intent.intent, response, True)

            self._last_file = intent.args.get("target") or self._last_file
            self._last_response = response
            self._audit.log(
                transcript=transcript,
                intent=intent.intent,
                tier=tier,
                outcome="success",
                details=response,
            )
            return RouteResult(
                intent=intent,
                tier=tier,
                response=response,
                success=True,
            )
        except Exception as e:
            logger.exception("Error executing intent %s", intent.intent)
            self._audit.log(
                transcript=transcript,
                intent=intent.intent,
                tier=tier,
                outcome="error",
                details=str(e),
            )
            return RouteResult(
                intent=intent,
                tier=tier,
                response=f"Error: {e}",
                success=False,
            )

    async def _dispatch(self, intent: ParsedIntent) -> str:
        spec = self._handlers.get(intent.intent)
        if spec is None:
            return f"Unknown action: {intent.intent}"
        return await spec.fn(self, intent.args)

    # ---- intent handlers -------------------------------------------------
    # Each handler is registered against the intent name it serves, together
    # with the permission tier it requires. This is the single source of
    # truth per command — adding a new one (core or plugin) never requires
    # touching route()/_dispatch() above.

    @command("open_app", PermissionTier.WRITE)
    async def _h_open_app(self, args: dict[str, str]) -> str:
        target = args.get("target", "")
        result = await asyncio.to_thread(self._app_launcher.launch, target)
        if result.startswith("Could not find application"):
            search_url = f"https://www.google.com/search?q={target.replace(' ', '+')}"
            webbrowser.open(search_url)
            return f"Searching the web for {target}"
        return result

    @command("close_app", PermissionTier.WRITE)
    async def _h_close_app(self, args: dict[str, str]) -> str:
        return await asyncio.to_thread(self._app_launcher.close, args.get("target", ""))

    @command("close_window", PermissionTier.WRITE)
    async def _h_close_window(self, args: dict[str, str]) -> str:
        return self._sys_auto.close_window()

    @command("open_file", PermissionTier.SAFE)
    async def _h_open_file(self, args: dict[str, str]) -> str:
        target = args.get("target", "")
        result = self._file_ops.open_file(target)
        if result and not result.startswith(("File not found", "Cannot")):
            return self._sys_auto.open_file(target)
        return result

    @command("create_file", PermissionTier.WRITE)
    async def _h_create_file(self, args: dict[str, str]) -> str:
        return self._file_ops.create_file(args.get("target", ""))

    @command("write_to_file", PermissionTier.WRITE)
    async def _h_write_to_file(self, args: dict[str, str]) -> str:
        return self._file_ops.write_to_file(args.get("content", ""), args.get("target", ""))

    @command("edit_file", PermissionTier.WRITE)
    async def _h_edit_file(self, args: dict[str, str]) -> str:
        return self._file_ops.read_file(args.get("target", ""))

    @command("delete_file", PermissionTier.DESTRUCTIVE)
    async def _h_delete_file(self, args: dict[str, str]) -> str:
        return self._file_ops.delete_file(args.get("target", ""))

    @command("search_files", PermissionTier.SAFE)
    async def _h_search_files(self, args: dict[str, str]) -> str:
        return self._file_ops.search_files(args.get("query", ""))

    @command("semantic_search", PermissionTier.SAFE)
    async def _h_semantic_search(self, args: dict[str, str]) -> str:
        return await self._semantic_search(args.get("query", ""))

    @command("index_files", PermissionTier.WRITE)
    async def _h_index_files(self, args: dict[str, str]) -> str:
        return await self._index_files(args.get("target", "~"))

    @command("run_command", PermissionTier.DESTRUCTIVE)
    async def _h_run_command(self, args: dict[str, str]) -> str:
        result = await asyncio.to_thread(self._cli.execute, args.get("command", ""))
        return result.summary()

    @command("system_info", PermissionTier.SAFE)
    async def _h_system_info(self, args: dict[str, str]) -> str:
        return self._sys_auto.get_system_info()

    @command("list_directory", PermissionTier.SAFE)
    async def _h_list_directory(self, args: dict[str, str]) -> str:
        return self._file_ops.list_directory(args.get("target", "."))

    @command("media_play", PermissionTier.WRITE)
    async def _h_media_play(self, args: dict[str, str]) -> str:
        return self._sys_auto.media_play_pause()

    @command("media_pause", PermissionTier.WRITE)
    async def _h_media_pause(self, args: dict[str, str]) -> str:
        return self._sys_auto.media_play_pause()

    @command("media_next", PermissionTier.WRITE)
    async def _h_media_next(self, args: dict[str, str]) -> str:
        return self._sys_auto.media_next()

    @command("volume_up", PermissionTier.WRITE)
    async def _h_volume_up(self, args: dict[str, str]) -> str:
        return self._sys_auto.volume_up()

    @command("volume_down", PermissionTier.WRITE)
    async def _h_volume_down(self, args: dict[str, str]) -> str:
        return self._sys_auto.volume_down()

    @command("volume_mute", PermissionTier.WRITE)
    async def _h_volume_mute(self, args: dict[str, str]) -> str:
        return self._sys_auto.volume_mute()

    @command("undo", PermissionTier.WRITE)
    async def _h_undo(self, args: dict[str, str]) -> str:
        return await self._undo_last()

    @command("undo_list", PermissionTier.SAFE)
    async def _h_undo_list(self, args: dict[str, str]) -> str:
        return self._undo_list()

    @command("create_routine", PermissionTier.WRITE)
    async def _h_create_routine(self, args: dict[str, str]) -> str:
        return self._create_routine(args)

    @command("delete_routine", PermissionTier.WRITE)
    async def _h_delete_routine(self, args: dict[str, str]) -> str:
        return self._routines.delete_routine(args.get("target", ""))

    @command("list_routines", PermissionTier.SAFE)
    async def _h_list_routines(self, args: dict[str, str]) -> str:
        return self._routines.list_routines()

    @command("run_routine", PermissionTier.WRITE)
    async def _h_run_routine(self, args: dict[str, str]) -> str:
        return "Routine playback not yet wired to agent loop."

    @command("start_recording", PermissionTier.WRITE)
    async def _h_start_recording(self, args: dict[str, str]) -> str:
        return self._routines.record_macro()

    @command("stop_recording", PermissionTier.WRITE)
    async def _h_stop_recording(self, args: dict[str, str]) -> str:
        return self._routines.stop_recording()

    @command("list_macros", PermissionTier.SAFE)
    async def _h_list_macros(self, args: dict[str, str]) -> str:
        return self._list_macros()

    @command("list_skills", PermissionTier.SAFE)
    async def _h_list_skills(self, args: dict[str, str]) -> str:
        return self._list_skills()

    @command("enroll_voice", PermissionTier.WRITE)
    async def _h_enroll_voice(self, args: dict[str, str]) -> str:
        return "Voice enrollment requires the agent to capture audio samples. Say 'enroll voice' again to start."

    @command("verify_voice", PermissionTier.WRITE)
    async def _h_verify_voice(self, args: dict[str, str]) -> str:
        return "Voice verification requires audio input from the microphone."

    @command("list_voice_profiles", PermissionTier.SAFE)
    async def _h_list_voice_profiles(self, args: dict[str, str]) -> str:
        profiles = self._voiceprint.list_profiles()
        if not profiles:
            return "No voice profiles enrolled."
        return "Enrolled voice profiles:\n" + "\n".join(f"  - {p}" for p in profiles)

    @command("train_wakeword", PermissionTier.WRITE)
    async def _h_train_wakeword(self, args: dict[str, str]) -> str:
        from backend.modules.wakeword_train import WakeWordTrainer
        trainer = WakeWordTrainer()
        return await asyncio.to_thread(trainer.start_training, args.get("target", "custom wake word"))

    @command("list_wakewords", PermissionTier.SAFE)
    async def _h_list_wakewords(self, args: dict[str, str]) -> str:
        from backend.modules.wakeword_train import WakeWordTrainer
        trainer = WakeWordTrainer()
        return trainer.list_models()

    @command("web_search", PermissionTier.WRITE)
    async def _h_web_search(self, args: dict[str, str]) -> str:
        query = args.get("query", "")
        webbrowser.open(f"https://www.google.com/search?q={query.replace(' ', '+')}")
        return f"Searching the web for {query}"

    @command("open_url", PermissionTier.WRITE)
    async def _h_open_url(self, args: dict[str, str]) -> str:
        target = args.get("target", "")
        url = target if "." in target or target.startswith("http") else f"https://www.google.com/search?q={target.replace(' ', '+')}"
        if not url.startswith("http"):
            url = "https://" + url
        webbrowser.open(url)
        return f"Opening {target}"

    @command("play_youtube", PermissionTier.WRITE)
    async def _h_play_youtube(self, args: dict[str, str]) -> str:
        query = args.get("query", "")
        webbrowser.open(f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}")
        return f"Playing {query} on YouTube"

    # ---- supporting helpers ----------------------------------------------

    async def _undo_last(self) -> str:
        entry = self._undo.pop()
        if entry is None:
            return "Nothing to undo."

        result = await self._dispatch(ParsedIntent(
            intent=entry.inverse_action,
            target=entry.inverse_args.get("target", ""),
            args=entry.inverse_args,
        ))
        return f"Undid '{entry.action}' on '{entry.target}'. {result}"

    def _undo_list(self) -> str:
        history = self._undo.get_history()
        if not history:
            return "No actions to undo."
        lines = ["Recent actions:"]
        for i, entry in enumerate(reversed(history), 1):
            lines.append(f"  {i}. {entry.action} on '{entry.target}'")
        return "\n".join(lines)

    def _create_routine(self, args: dict[str, str]) -> str:
        name = args.get("target", "unnamed")
        steps_str = args.get("steps", "")
        steps = [s.strip() for s in steps_str.split(",") if s.strip()] if steps_str else []
        if not steps:
            return "Provide steps as a comma-separated list. Example: create routine morning with open firefox, open calendar"
        return self._routines.create_routine(name, name, steps)

    def _list_macros(self) -> str:
        macros = self._routines.get_macros(limit=10)
        if not macros:
            return "No macros recorded."
        lines = ["Recent macros:"]
        for m in macros:
            status = "ok" if m.success else "fail"
            lines.append(f"  [{status}] {m.transcript}")
        return "\n".join(lines)

    def _list_skills(self) -> str:
        skills = self._plugins.list_skills()
        if not skills:
            return "No skills loaded."
        lines = ["Loaded skills:"]
        for s in skills:
            cmds = ", ".join(s["commands"]) if s["commands"] else "none"
            lines.append(f"  - {s['name']} v{s['version']}: {s['description']} (commands: {cmds})")
        return "\n".join(lines)

    async def _semantic_search(self, query: str) -> str:
        results = await asyncio.to_thread(self._semantic.search, query, 5)
        if not results:
            fallback = self._file_ops.search_files(query)
            if "No files found" in fallback:
                return f"No files found matching '{query}'. Try indexing files first: 'index files ~'"
            return fallback

        lines = [f"Found {len(results)} results for '{query}':"]
        for i, r in enumerate(results, 1):
            score_pct = int(r.score * 100)
            lines.append(f"  {i}. {r.path} ({score_pct}% match)")
            if r.snippet:
                snippet = r.snippet[:120].replace("\n", " ")
                lines.append(f"     \"{snippet}...\"")
        return "\n".join(lines)

    async def _index_files(self, directory: str) -> str:
        count = await asyncio.to_thread(self._semantic.index_directory, directory)
        if count == 0:
            return f"No indexable files found in {directory}"
        return f"Indexed {count} files from {directory}. Semantic search is now available."

    def _build_confirmation(self, intent: ParsedIntent) -> str:
        action = intent.intent
        target = intent.args.get("target", intent.args.get("command", ""))

        descriptions = {
            "delete_file": f"Delete the file '{target}'? This cannot be undone.",
            "run_command": f"Run the command '{target}'? This may modify your system.",
        }

        description = descriptions.get(action, f"Execute '{action}' on '{target}'?")
        return f"Confirm: {description} Say 'yes' to proceed or 'no' to cancel."

    @property
    def last_file(self) -> str | None:
        return self._last_file

    def init_plugins(self) -> None:
        self._plugins.discover()

    def reload_plugins_if_changed(self) -> bool:
        return self._plugins.reload_if_changed()
