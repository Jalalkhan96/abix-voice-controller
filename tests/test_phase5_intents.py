from __future__ import annotations

import pytest

from backend.nlu.intent_parser import parse


class TestPhase5Intents:
    def test_undo(self):
        result = parse("undo that")
        assert result.intent == "undo"

    def test_undo_bare(self):
        result = parse("undo")
        assert result.intent == "undo"

    def test_undo_list(self):
        result = parse("show undo history")
        assert result.intent == "undo_list"

    def test_create_routine(self):
        result = parse("create routine morning with open firefox, open calendar")
        assert result.intent == "create_routine"
        assert result.args.get("target") == "morning"
        assert "firefox" in result.args.get("steps", "")

    def test_delete_routine(self):
        result = parse("delete routine morning")
        assert result.intent == "delete_routine"
        assert "morning" in result.args.get("target", "")

    def test_list_routines(self):
        result = parse("list routines")
        assert result.intent == "list_routines"

    def test_run_routine(self):
        result = parse("run routine morning")
        assert result.intent == "run_routine"
        assert "morning" in result.args.get("target", "")

    def test_start_recording(self):
        result = parse("start recording")
        assert result.intent == "start_recording"

    def test_stop_recording(self):
        result = parse("stop recording")
        assert result.intent == "stop_recording"

    def test_list_macros(self):
        result = parse("list macros")
        assert result.intent == "list_macros"

    def test_list_skills(self):
        result = parse("list skills")
        assert result.intent == "list_skills"

    def test_list_plugins(self):
        result = parse("show plugins")
        assert result.intent == "list_skills"

    def test_enroll_voice(self):
        result = parse("enroll my voice")
        assert result.intent == "enroll_voice"

    def test_verify_voice(self):
        result = parse("verify my voice")
        assert result.intent == "verify_voice"

    def test_list_voice_profiles(self):
        result = parse("list voice profiles")
        assert result.intent == "list_voice_profiles"

    def test_train_wakeword(self):
        result = parse("train wake word for hey computer")
        assert result.intent == "train_wakeword"
        assert "hey computer" in result.args.get("target", "")

    def test_list_wakewords(self):
        result = parse("list wake words")
        assert result.intent == "list_wakewords"
