from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from backend.nlu.intent_parser import parse


class TestOpenDownloadsIntent:
    def test_open_downloads(self):
        result = parse("open downloads")
        assert result.intent == "open_downloads"

    def test_open_the_downloads_folder(self):
        result = parse("open the downloads folder")
        assert result.intent == "open_downloads"

    def test_case_insensitive(self):
        result = parse("OPEN DOWNLOADS")
        assert result.intent == "open_downloads"

    def test_open_app_still_wins_for_other_targets(self):
        result = parse("open downloads manager")
        assert result.intent == "open_app"
        assert "downloads manager" in result.target.lower()

    def test_open_firefox_unaffected(self):
        result = parse("open firefox")
        assert result.intent == "open_app"


class TestOpenDownloadsRouter:
    def test_router_opens_downloads_folder(self):
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

            result = asyncio.run(router.route("open downloads"))
            audit.close()
            assert result.intent.intent == "open_downloads"
            assert result.success is True
            assert "Downloads" in result.response
