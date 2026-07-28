from __future__ import annotations

from pathlib import Path

import pytest

from backend.modules.file_ops import FileOps


@pytest.fixture
def file_ops() -> FileOps:
    return FileOps()


class TestFileOps:
    def test_create_file(self, file_ops: FileOps, tmp_path: Path):
        file_path = str(tmp_path / "test.txt")
        result = file_ops.create_file(file_path)
        assert "Created" in result
        assert Path(file_path).exists()

    def test_create_file_already_exists(self, file_ops: FileOps, tmp_path: Path):
        file_path = tmp_path / "test.txt"
        file_path.write_text("existing")
        result = file_ops.create_file(str(file_path))
        assert "already exists" in result

    def test_write_to_file(self, file_ops: FileOps, tmp_path: Path):
        file_path = str(tmp_path / "test.txt")
        result = file_ops.write_to_file("hello world", file_path)
        assert "Wrote" in result
        assert Path(file_path).read_text() == "hello world"

    def test_read_file(self, file_ops: FileOps, tmp_path: Path):
        file_path = tmp_path / "test.txt"
        file_path.write_text("line 1\nline 2\n")
        result = file_ops.read_file(str(file_path))
        assert "line 1" in result
        assert "line 2" in result

    def test_read_file_not_found(self, file_ops: FileOps):
        result = file_ops.read_file("/nonexistent/file.txt")
        assert "not found" in result.lower()

    def test_delete_file(self, file_ops: FileOps, tmp_path: Path):
        file_path = tmp_path / "test.txt"
        file_path.write_text("to delete")
        result = file_ops.delete_file(str(file_path))
        assert "Deleted" in result
        assert not file_path.exists()

    def test_search_files(self, file_ops: FileOps, tmp_path: Path):
        (tmp_path / "budget.txt").write_text("money")
        (tmp_path / "notes.txt").write_text("notes")
        result = file_ops.search_files("budget", str(tmp_path))
        assert "budget.txt" in result

    def test_list_directory(self, file_ops: FileOps, tmp_path: Path):
        (tmp_path / "file1.txt").write_text("a")
        (tmp_path / "file2.txt").write_text("b")
        result = file_ops.list_directory(str(tmp_path))
        assert "file1.txt" in result
        assert "file2.txt" in result
