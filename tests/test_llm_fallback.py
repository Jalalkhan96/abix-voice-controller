from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from backend.nlu.llm_fallback import LLMIntentParser
from backend.nlu.intent_parser import ParsedIntent


class TestLLMIntentParser:
    def test_parse_valid_json(self):
        parser = LLMIntentParser()
        response = json.dumps({
            "intent": "open_app",
            "target": "firefox",
            "args": {"target": "firefox"},
            "confidence": 0.85,
        })
        result = parser._parse_response(response, "open firefox")
        assert result is not None
        assert result.intent == "open_app"
        assert result.target == "firefox"
        assert result.confidence == 0.85

    def test_parse_json_in_codeblock(self):
        parser = LLMIntentParser()
        response = '```json\n{"intent": "delete_file", "target": "test.txt", "args": {"target": "test.txt"}, "confidence": 0.9}\n```'
        result = parser._parse_response(response, "delete test.txt")
        assert result is not None
        assert result.intent == "delete_file"
        assert result.target == "test.txt"

    def test_parse_json_with_surrounding_text(self):
        parser = LLMIntentParser()
        response = 'Here is the parsed intent:\n{"intent": "run_command", "target": "ls -la", "args": {"command": "ls -la"}, "confidence": 0.8}\nDone.'
        result = parser._parse_response(response, "run ls -la")
        assert result is not None
        assert result.intent == "run_command"
        assert result.args.get("command") == "ls -la"

    def test_parse_invalid_json(self):
        parser = LLMIntentParser()
        result = parser._parse_response("not json at all", "open firefox")
        assert result is None

    def test_parse_semantic_search_populates_query(self):
        parser = LLMIntentParser()
        response = json.dumps({
            "intent": "semantic_search",
            "target": "budget spreadsheet",
            "args": {},
            "confidence": 0.8,
        })
        result = parser._parse_response(response, "find my budget spreadsheet")
        assert result is not None
        assert result.intent == "semantic_search"
        assert result.args.get("query") == "budget spreadsheet"

    def test_parse_search_files_populates_query(self):
        parser = LLMIntentParser()
        response = json.dumps({
            "intent": "search_files",
            "target": "notes",
            "args": {},
            "confidence": 0.8,
        })
        result = parser._parse_response(response, "search for notes")
        assert result is not None
        assert result.args.get("query") == "notes"

    def test_parse_run_command_populates_command(self):
        parser = LLMIntentParser()
        response = json.dumps({
            "intent": "run_command",
            "target": "git status",
            "args": {},
            "confidence": 0.8,
        })
        result = parser._parse_response(response, "run git status")
        assert result is not None
        assert result.args.get("command") == "git status"

    @pytest.mark.asyncio
    async def test_parse_calls_ollama(self):
        parser = LLMIntentParser(ollama_url="http://localhost:99999")
        with patch.object(parser, "_call_ollama", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = json.dumps({
                "intent": "open_app",
                "target": "vim",
                "args": {"target": "vim"},
                "confidence": 0.7,
            })
            result = await parser.parse("launch vim")
            assert result is not None
            assert result.intent == "open_app"
            mock_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_parse_returns_none_on_ollama_failure(self):
        parser = LLMIntentParser(ollama_url="http://localhost:99999")
        with patch.object(parser, "_call_ollama", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = None
            result = await parser.parse("open vim")
            assert result is None


class TestIntentParserPhase4:
    def test_find_with_file_extension_is_semantic_search(self):
        from backend.nlu.intent_parser import parse
        result = parse("find my report.pdf")
        assert result.intent == "semantic_search"

    def test_find_without_extension_is_semantic_search(self):
        from backend.nlu.intent_parser import parse
        result = parse("find the budget spreadsheet")
        assert result.intent == "semantic_search"

    def test_locate_is_semantic_search(self):
        from backend.nlu.intent_parser import parse
        result = parse("locate my resume")
        assert result.intent == "semantic_search"

    def test_where_is_is_semantic_search(self):
        from backend.nlu.intent_parser import parse
        result = parse("where is the meeting notes")
        assert result.intent == "semantic_search"

    def test_index_files(self):
        from backend.nlu.intent_parser import parse
        result = parse("index files ~")
        assert result.intent == "index_files"
        assert result.args.get("target") == "~"

    def test_grep_is_search_files(self):
        from backend.nlu.intent_parser import parse
        result = parse("search for main function")
        assert result.intent == "search_files"
