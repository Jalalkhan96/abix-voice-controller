from __future__ import annotations

import pytest

from backend.nlu.intent_parser import parse, ParsedIntent


class TestIntentParser:
    def test_open_app(self):
        result = parse("open firefox")
        assert result.intent == "open_app"
        assert "firefox" in result.target.lower()

    def test_open_app_with_the(self):
        result = parse("open the browser")
        assert result.intent == "open_app"
        assert "browser" in result.target.lower()

    def test_close_app(self):
        result = parse("close firefox")
        assert result.intent == "close_app"
        assert "firefox" in result.target.lower()

    def test_close_window(self):
        result = parse("close this window")
        assert result.intent == "close_window"

    def test_open_file(self):
        result = parse("open my resume.pdf")
        assert result.intent == "open_file"
        assert "resume.pdf" in result.target

    def test_open_file_with_keyword(self):
        result = parse("open file notes.txt")
        assert result.intent == "open_file"

    def test_create_file(self):
        result = parse("create a new file called notes.txt")
        assert result.intent == "create_file"

    def test_write_to_file(self):
        result = parse("write 'hello world' to notes.txt")
        assert result.intent == "write_to_file"
        assert result.args.get("content") == "hello world"
        assert "notes.txt" in result.args.get("target", "")

    def test_delete_file(self):
        result = parse("delete test.txt")
        assert result.intent == "delete_file"
        assert "test.txt" in result.target

    def test_search_files(self):
        result = parse("search for the budget spreadsheet")
        assert result.intent == "search_files"
        assert "budget spreadsheet" in result.args.get("query", "")

    def test_run_command(self):
        result = parse("run git status")
        assert result.intent == "run_command"
        assert "git status" in result.args.get("command", "")

    def test_system_info_disk(self):
        result = parse("what's the disk space")
        assert result.intent == "system_info"

    def test_system_info_memory(self):
        result = parse("how much memory")
        assert result.intent == "system_info"

    def test_list_directory(self):
        result = parse("list directory /home")
        assert result.intent == "list_directory"

    def test_list_directory_default(self):
        result = parse("what's in this folder")
        assert result.intent == "list_directory"

    def test_media_play(self):
        result = parse("play music")
        assert result.intent == "media_play"

    def test_media_pause(self):
        result = parse("pause")
        assert result.intent == "media_pause"

    def test_media_next(self):
        result = parse("next track")
        assert result.intent == "media_next"

    def test_volume_up(self):
        result = parse("turn up the volume")
        assert result.intent == "volume_up"

    def test_volume_down(self):
        result = parse("lower the volume")
        assert result.intent == "volume_down"

    def test_unknown_command(self):
        result = parse("blorp snazzle foo")
        assert result.intent == "unknown"
        assert result.confidence == 0.0

    def test_case_insensitive(self):
        result = parse("OPEN FIREFOX")
        assert result.intent == "open_app"

    def test_hand_tracking_on(self):
        result = parse("turn on hand tracking")
        assert result.intent == "hand_tracking_toggle"

    def test_hand_tracking_off(self):
        result = parse("disable hand tracking")
        assert result.intent == "hand_tracking_off"


class TestCommandRouter:
    def test_router_routes_to_file_ops(self):
        from backend.safety.permissions import PermissionManager
        from backend.safety.audit_log import AuditLog
        from backend.router.command_router import CommandRouter
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "test.db"
            wl_path = Path(tmp_dir) / "whitelist.yaml"
            wl_path.write_text("pre_approved:\n  - ls\nblocked:\n  - rm -rf /\n")

            perms = PermissionManager(str(wl_path))
            audit = AuditLog(str(db_path))
            router = CommandRouter(perms, audit)

            result = router.route("list directory .")
            assert result.success is True
            assert "Contents of" in result.response or "empty" in result.response

    def test_router_blocks_dangerous(self):
        from backend.safety.permissions import PermissionManager
        from backend.safety.audit_log import AuditLog
        from backend.router.command_router import CommandRouter
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "test.db"
            wl_path = Path(tmp_dir) / "whitelist.yaml"
            wl_path.write_text("pre_approved:\n  - ls\nblocked:\n  - rm -rf /\n")

            perms = PermissionManager(str(wl_path))
            audit = AuditLog(str(db_path))
            router = CommandRouter(perms, audit)

            result = router.route("run rm -rf /")
            assert result.success is False
            assert "blocked" in result.response.lower()

    def test_router_confirms_destructive(self):
        from backend.safety.permissions import PermissionManager
        from backend.safety.audit_log import AuditLog
        from backend.router.command_router import CommandRouter
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "test.db"
            wl_path = Path(tmp_dir) / "whitelist.yaml"
            wl_path.write_text("pre_approved:\n  - ls\nblocked:\n  - rm -rf /\n")

            perms = PermissionManager(str(wl_path))
            audit = AuditLog(str(db_path))
            router = CommandRouter(perms, audit)

            result = router.route("delete file.txt")
            assert result.needs_confirmation is True
            assert "Confirm" in result.confirmation_message or "confirm" in result.confirmation_message
