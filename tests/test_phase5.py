from __future__ import annotations

import pytest
from pathlib import Path

from backend.modules.routines import RoutineManager, Routine, MacroEntry
from backend.modules.undo import UndoManager, UndoEntry, build_undo_entry
from backend.plugins.registry import SkillRegistry, Skill, SkillManifest


class TestRoutineManager:
    def test_create_and_list_routines(self, tmp_path: Path):
        mgr = RoutineManager(data_dir=str(tmp_path))
        result = mgr.create_routine("morning", "good morning", ["open firefox", "open calendar"])
        assert "Created" in result
        assert "morning" in result

        listing = mgr.list_routines()
        assert "morning" in listing

    def test_get_routine_steps(self, tmp_path: Path):
        mgr = RoutineManager(data_dir=str(tmp_path))
        mgr.create_routine("test", "run test", ["cmd1", "cmd2"])
        routine = mgr.get_routine_steps("run test")
        assert routine is not None
        assert len(routine.steps) == 2
        assert routine.steps[0].command == "cmd1"

    def test_delete_routine(self, tmp_path: Path):
        mgr = RoutineManager(data_dir=str(tmp_path))
        mgr.create_routine("temp", "temp trigger", ["cmd1"])
        result = mgr.delete_routine("temp")
        assert "Deleted" in result
        assert mgr.get_routine_steps("temp") is None

    def test_persistence(self, tmp_path: Path):
        mgr1 = RoutineManager(data_dir=str(tmp_path))
        mgr1.create_routine("saved", "saved trigger", ["cmd1"])

        mgr2 = RoutineManager(data_dir=str(tmp_path))
        routine = mgr2.get_routine_steps("saved trigger")
        assert routine is not None

    def test_recording_macro(self, tmp_path: Path):
        mgr = RoutineManager(data_dir=str(tmp_path))
        assert mgr.is_recording is False

        result = mgr.record_macro()
        assert "started" in result.lower()
        assert mgr.is_recording is True

        mgr.record_step("open firefox", "open_app", "Launched firefox", True)
        mgr.record_step("pause music", "media_pause", "Toggled", True)

        result = mgr.stop_recording()
        assert "2" in result
        assert mgr.is_recording is False

    def test_list_macros(self, tmp_path: Path):
        mgr = RoutineManager(data_dir=str(tmp_path))
        macros = mgr.get_macros()
        assert len(macros) == 0

        mgr.record_macro()
        mgr.record_step("test command", "unknown", "response", True)
        mgr.stop_recording()

        macros = mgr.get_macros()
        assert len(macros) == 1
        assert macros[0].transcript == "test command"


class TestUndoManager:
    def test_record_and_pop(self):
        mgr = UndoManager()
        assert mgr.can_undo() is False

        mgr.record(UndoEntry(action="create_file", target="test.txt", details="ok", inverse_action="delete_file"))
        assert mgr.can_undo() is True

        entry = mgr.pop()
        assert entry is not None
        assert entry.action == "create_file"
        assert entry.target == "test.txt"

    def test_max_history(self):
        mgr = UndoManager(max_history=3)
        for i in range(5):
            mgr.record(UndoEntry(action=f"action_{i}", target="x", details="", inverse_action="undo"))

        history = mgr.get_history()
        assert len(history) == 3
        assert history[0].action == "action_2"

    def test_peek(self):
        mgr = UndoManager()
        mgr.record(UndoEntry(action="a", target="", details="", inverse_action="b"))
        entry = mgr.peek()
        assert entry is not None
        assert mgr.can_undo() is True

    def test_clear(self):
        mgr = UndoManager()
        mgr.record(UndoEntry(action="a", target="", details="", inverse_action="b"))
        mgr.clear()
        assert mgr.can_undo() is False


class TestBuildUndoEntry:
    def test_create_file_undo(self):
        entry = build_undo_entry("create_file", "test.txt", "Created test.txt")
        assert entry is not None
        assert entry.inverse_action == "delete_file"
        assert entry.inverse_args["target"] == "test.txt"

    def test_open_app_undo(self):
        entry = build_undo_entry("open_app", "firefox", "Launched firefox")
        assert entry is not None
        assert entry.inverse_action == "close_app"

    def test_unknown_action_no_undo(self):
        entry = build_undo_entry("system_info", "", "")
        assert entry is None


class TestSkillRegistry:
    def test_discover_skills(self, tmp_path: Path):
        skill_dir = tmp_path / "skills" / "test_skill"
        skill_dir.mkdir(parents=True)

        manifest = skill_dir / "manifest.yaml"
        manifest.write_text("""
name: test_skill
version: "0.1.0"
description: "A test skill"
author: "Test"
commands:
  - trigger: "test command"
    description: "Runs a test"
module: test_skill_mod
""")

        module = skill_dir / "test_skill_mod.py"
        module.write_text("""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from backend.plugins.registry import Skill, SkillManifest

class TestSkillImpl(Skill):
    @property
    def name(self):
        return "test_skill"

    @property
    def manifest(self):
        return SkillManifest(
            name="test_skill", version="0.1.0", description="test",
            author="Test", commands=[{"trigger": "test command", "description": "test"}]
        )

    def handle(self, intent, args):
        return "Test skill executed!"
""")

        registry = SkillRegistry(skills_dirs=[str(tmp_path / "skills")])
        count = registry.discover()
        assert count == 1

        result = registry.handle_command("test command")
        assert result == "Test skill executed!"

    def test_list_skills(self, tmp_path: Path):
        registry = SkillRegistry(skills_dirs=[str(tmp_path / "nonexistent")])
        registry.discover()
        assert len(registry.list_skills()) == 0

    def test_trigger_lookup(self, tmp_path: Path):
        registry = SkillRegistry(skills_dirs=[str(tmp_path / "nonexistent")])
        assert registry.registered_triggers == {}
