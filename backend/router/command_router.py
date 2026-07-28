from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

from backend.nlu.intent_parser import ParsedIntent, parse, parse_with_llm
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
from backend.plugins.registry import SkillRegistry

logger = logging.getLogger("abix.router")


TIER_MAP: dict[str, PermissionTier] = {
    "open_app": PermissionTier.WRITE,
    "close_app": PermissionTier.WRITE,
    "close_window": PermissionTier.WRITE,
    "open_file": PermissionTier.SAFE,
    "create_file": PermissionTier.WRITE,
    "write_to_file": PermissionTier.WRITE,
    "edit_file": PermissionTier.WRITE,
    "delete_file": PermissionTier.DESTRUCTIVE,
    "search_files": PermissionTier.SAFE,
    "semantic_search": PermissionTier.SAFE,
    "index_files": PermissionTier.WRITE,
    "run_command": PermissionTier.DESTRUCTIVE,
    "system_info": PermissionTier.SAFE,
    "list_directory": PermissionTier.SAFE,
    "media_play": PermissionTier.WRITE,
    "media_pause": PermissionTier.WRITE,
    "media_next": PermissionTier.WRITE,
    "volume_up": PermissionTier.WRITE,
    "volume_down": PermissionTier.WRITE,
    "volume_mute": PermissionTier.WRITE,
    "hand_tracking_toggle": PermissionTier.WRITE,
    "hand_tracking_off": PermissionTier.WRITE,
    "create_routine": PermissionTier.WRITE,
    "delete_routine": PermissionTier.WRITE,
    "list_routines": PermissionTier.SAFE,
    "run_routine": PermissionTier.WRITE,
    "start_recording": PermissionTier.WRITE,
    "stop_recording": PermissionTier.WRITE,
    "list_macros": PermissionTier.SAFE,
    "undo": PermissionTier.WRITE,
    "undo_list": PermissionTier.SAFE,
    "list_skills": PermissionTier.SAFE,
    "enroll_voice": PermissionTier.WRITE,
    "verify_voice": PermissionTier.WRITE,
    "list_voice_profiles": PermissionTier.SAFE,
    "train_wakeword": PermissionTier.WRITE,
    "list_wakewords": PermissionTier.SAFE,
}


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

    def route(self, text: str) -> RouteResult:
        plugin_result = self._try_plugins(text)
        if plugin_result is not None:
            return plugin_result

        from backend.modules.shortcuts import ShortcutManager
        sm = ShortcutManager()
        keyword = text.strip().upper()
        sc = sm.get(keyword)
        if sc:
            response = sm.execute(keyword)
            return RouteResult(
                intent=ParsedIntent(intent="shortcut", args={"keyword": keyword}, confidence=1.0),
                response=response,
                success=True,
                tier=PermissionTier.WRITE,
            )

        intent = parse(text)
        tier = TIER_MAP.get(intent.intent, PermissionTier.WRITE)

        if intent.intent == "unknown":
            intent = self._try_llm_fallback(text, intent)
            tier = TIER_MAP.get(intent.intent, PermissionTier.WRITE)

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

        return self._execute(intent, tier, text)

    async def route_async(self, text: str) -> RouteResult:
        plugin_result = self._try_plugins(text)
        if plugin_result is not None:
            return plugin_result

        intent = parse(text)
        tier = TIER_MAP.get(intent.intent, PermissionTier.WRITE)

        if intent.intent == "unknown":
            try:
                intent = await parse_with_llm(text, self._llm_parser)
                tier = TIER_MAP.get(intent.intent, PermissionTier.WRITE)
            except Exception as e:
                logger.debug("Async LLM fallback failed: %s", e)

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

        return self._execute(intent, tier, text)

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

    def _try_llm_fallback(self, text: str, original_intent: ParsedIntent) -> ParsedIntent:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self._llm_parser.parse(text))
                    result = future.result(timeout=10)
            else:
                result = loop.run_until_complete(self._llm_parser.parse(text))

            if result is not None and result.intent != "unknown":
                logger.info("LLM resolved: %s -> %s", text, result.intent)
                return result
        except Exception as e:
            logger.debug("LLM fallback failed: %s", e)
        return original_intent

    def execute_confirmed(self, action: str, args: dict[str, str], original_text: str) -> RouteResult:
        intent = ParsedIntent(
            intent=action,
            target=args.get("target", args.get("query", args.get("command", ""))),
            args=args,
            raw_text=original_text,
        )
        tier = TIER_MAP.get(action, PermissionTier.WRITE)
        return self._execute(intent, tier, original_text)

    def _execute(self, intent: ParsedIntent, tier: PermissionTier, transcript: str) -> RouteResult:
        try:
            response = self._dispatch(intent)

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

    def _dispatch(self, intent: ParsedIntent) -> str:
        action = intent.intent
        args = intent.args

        if action == "open_app":
            target = args.get("target", "")
            result = self._app_launcher.launch(target)
            if result.startswith("Could not find application"):
                import webbrowser
                search_url = f"https://www.google.com/search?q={target.replace(' ', '+')}"
                webbrowser.open(search_url)
                return f"Searching the web for {target}"
            return result
        elif action == "close_app":
            return self._app_launcher.close(args.get("target", ""))
        elif action == "close_window":
            return self._sys_auto.close_window()
        elif action == "open_file":
            target = args.get("target", "")
            result = self._file_ops.open_file(target)
            if result and not result.startswith(("File not found", "Cannot")):
                return self._sys_auto.open_file(target)
            return result
        elif action == "create_file":
            return self._file_ops.create_file(args.get("target", ""))
        elif action == "write_to_file":
            return self._file_ops.write_to_file(
                args.get("content", ""), args.get("target", "")
            )
        elif action == "edit_file":
            return self._file_ops.read_file(args.get("target", ""))
        elif action == "delete_file":
            return self._file_ops.delete_file(args.get("target", ""))
        elif action == "search_files":
            return self._file_ops.search_files(args.get("query", ""))
        elif action == "semantic_search":
            return self._semantic_search(args.get("query", ""))
        elif action == "index_files":
            return self._index_files(args.get("target", "~"))
        elif action == "run_command":
            return self._cli.execute(args.get("command", "")).summary()
        elif action == "system_info":
            return self._sys_auto.get_system_info()
        elif action == "list_directory":
            target = args.get("target", ".")
            return self._file_ops.list_directory(target)
        elif action == "media_play":
            return self._sys_auto.media_play_pause()
        elif action == "media_pause":
            return self._sys_auto.media_play_pause()
        elif action == "media_next":
            return self._sys_auto.media_next()
        elif action == "volume_up":
            return self._sys_auto.volume_up()
        elif action == "volume_down":
            return self._sys_auto.volume_down()
        elif action == "volume_mute":
            return self._sys_auto.volume_mute()
        elif action == "undo":
            return self._undo_last()
        elif action == "undo_list":
            return self._undo_list()
        elif action == "create_routine":
            return self._create_routine(args)
        elif action == "delete_routine":
            return self._routines.delete_routine(args.get("target", ""))
        elif action == "list_routines":
            return self._routines.list_routines()
        elif action == "run_routine":
            return f"Routine playback not yet wired to agent loop."
        elif action == "start_recording":
            return self._routines.record_macro()
        elif action == "stop_recording":
            return self._routines.stop_recording()
        elif action == "list_macros":
            return self._list_macros()
        elif action == "list_skills":
            return self._list_skills()
        elif action == "enroll_voice":
            return "Voice enrollment requires the agent to capture audio samples. Say 'enroll voice' again to start."
        elif action == "verify_voice":
            return "Voice verification requires audio input from the microphone."
        elif action == "list_voice_profiles":
            return self._list_voice_profiles()
        elif action == "train_wakeword":
            from backend.modules.wakeword_train import WakeWordTrainer
            trainer = WakeWordTrainer()
            return trainer.start_training(args.get("target", "custom wake word"))
        elif action == "list_wakewords":
            from backend.modules.wakeword_train import WakeWordTrainer
            trainer = WakeWordTrainer()
            return trainer.list_models()
        elif action == "web_search":
            query = args.get("query", "")
            import webbrowser
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            webbrowser.open(search_url)
            return f"Searching the web for {query}"
        elif action == "open_url":
            target = args.get("target", "")
            import webbrowser
            url = target if "." in target or target.startswith("http") else f"https://www.google.com/search?q={target.replace(' ', '+')}"
            if not url.startswith("http"):
                url = "https://" + url
            webbrowser.open(url)
            return f"Opening {target}"
        elif action == "play_youtube":
            import webbrowser
            query = args.get("query", "")
            url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
            webbrowser.open(url)
            return f"Playing {query} on YouTube"
        else:
            return f"Unknown action: {action}"

    def _undo_last(self) -> str:
        entry = self._undo.pop()
        if entry is None:
            return "Nothing to undo."

        result = self._dispatch(ParsedIntent(
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

    def _semantic_search(self, query: str) -> str:
        results = self._semantic.search(query, top_k=5)
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

    def _index_files(self, directory: str) -> str:
        count = self._semantic.index_directory(directory)
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
