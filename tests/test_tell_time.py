from __future__ import annotations

import asyncio
import re
import tempfile
from pathlib import Path

from backend.nlu.intent_parser import parse


class TestTellTimeIntent:
    def test_what_time_is_it(self):
        result = parse("what time is it")
        assert result.intent == "tell_time"

    def test_whats_the_time(self):
        result = parse("what's the time")
        assert result.intent == "tell_time"

    def test_tell_me_the_time(self):
        result = parse("tell me the time")
        assert result.intent == "tell_time"

    def test_current_time(self):
        result = parse("current time")
        assert result.intent == "tell_time"

    def test_case_insensitive(self):
        result = parse("WHAT TIME IS IT")
        assert result.intent == "tell_time"

    def test_tell_me_a_story_is_not_time(self):
        result = parse("tell me a story")
        assert result.intent != "tell_time"

    def test_open_downloads_unaffected(self):
        result = parse("open downloads")
        assert result.intent == "open_downloads"


class TestTellTimeRouter:
    def test_router_reports_current_time(self):
        from backend.router.command_router import CommandRouter
        from backend.safety.audit_log import AuditLog
        from backend.safety.permissions import PermissionManager

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "test.db"
            wl_path = Path(tmp_dir) / "whitelist.yaml"
            wl_path.write_text("pre_approved:\n  - ls\nblocked:\n  - rm -rf /\n")

            perms = PermissionManager(str(wl_path))
            audit = AuditLog(str(db_path))
            router = CommandRouter(perms, audit)

            result = asyncio.run(router.route("what time is it"))
            audit.close()
            assert result.intent.intent == "tell_time"
            assert result.success is True
            assert re.match(r"It's \d{2}:\d{2} [AP]M\.", result.response)
