from __future__ import annotations

import pytest
from pathlib import Path

from backend.modules.semantic_search import SemanticSearchEngine, SearchResult


class TestChunkText:
    def _chunk(self, text: str) -> list[str]:
        engine = SemanticSearchEngine(persist_dir="/tmp/_test_chunk")
        return engine._chunk_text(text)

    def test_short_text_single_chunk(self):
        chunks = self._chunk("hello world")
        assert len(chunks) == 1
        assert chunks[0] == "hello world"

    def test_long_text_multiple_chunks(self):
        text = "word " * 200
        chunks = self._chunk(text)
        assert len(chunks) > 1

    def test_empty_text(self):
        chunks = self._chunk("")
        assert len(chunks) >= 1

    def test_whitespace_only(self):
        chunks = self._chunk("   \n  \n  ")
        assert len(chunks) >= 1


class TestSemanticSearchEngine:
    def test_init_creates_persist_dir(self, tmp_path: Path):
        persist = tmp_path / "chroma_test"
        engine = SemanticSearchEngine(persist_dir=str(persist))
        engine._ensure_init()
        assert persist.exists()

    def test_should_index_text_files(self, tmp_path: Path):
        engine = SemanticSearchEngine(persist_dir=str(tmp_path / "c"))
        assert engine._should_index(Path("test.py"))
        assert engine._should_index(Path("notes.md"))
        assert engine._should_index(Path("data.json"))
        assert engine._should_index(Path("Makefile"))

    def test_should_not_index_binary(self, tmp_path: Path):
        engine = SemanticSearchEngine(persist_dir=str(tmp_path / "c"))
        assert not engine._should_index(Path("image.png"))
        assert not engine._should_index(Path("video.mp4"))
        assert not engine._should_index(Path("binary"))

    def test_index_and_search(self, tmp_path: Path):
        try:
            import chromadb
        except ImportError:
            pytest.skip("chromadb not installed")

        test_dir = tmp_path / "docs"
        test_dir.mkdir()
        (test_dir / "budget.txt").write_text("Monthly budget report for Q3 2024. Revenue was $50,000.")
        (test_dir / "notes.txt").write_text("Meeting notes from Tuesday standup. Action items: finish UI.")
        (test_dir / "image.png").write_text("not a real png but tests filtering")

        engine = SemanticSearchEngine(persist_dir=str(tmp_path / "chroma"))
        count = engine.index_directory(str(test_dir))
        assert count >= 2

        results = engine.search("budget report", top_k=3)
        assert len(results) > 0
        assert any("budget" in r.path.lower() for r in results)

    def test_search_empty_index(self, tmp_path: Path):
        engine = SemanticSearchEngine(persist_dir=str(tmp_path / "empty"))
        results = engine.search("anything")
        assert results == []

    def test_clear_index(self, tmp_path: Path):
        try:
            import chromadb
        except ImportError:
            pytest.skip("chromadb not installed")

        test_dir = tmp_path / "docs"
        test_dir.mkdir()
        (test_dir / "test.txt").write_text("hello world")

        engine = SemanticSearchEngine(persist_dir=str(tmp_path / "chroma"))
        engine.index_directory(str(test_dir))
        engine.clear_index()

        results = engine.search("hello")
        assert results == []

    def test_deduplicates_files(self, tmp_path: Path):
        try:
            import chromadb
        except ImportError:
            pytest.skip("chromadb not installed")

        test_dir = tmp_path / "docs"
        test_dir.mkdir()
        (test_dir / "a.txt").write_text("content A with unique keyword zephyr")
        (test_dir / "b.txt").write_text("content B also about zephyr topic")

        engine = SemanticSearchEngine(persist_dir=str(tmp_path / "chroma"))
        engine.index_directory(str(test_dir))

        results = engine.search("zephyr", top_k=10)
        paths = [r.path for r in results]
        assert len(paths) == len(set(paths))
