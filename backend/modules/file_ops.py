from __future__ import annotations

from pathlib import Path


class FileOps:
    def open_file(self, file_path: str) -> str:
        path = Path(file_path).expanduser().resolve()
        if not path.exists():
            return f"File not found: {file_path}"
        if path.is_dir():
            return f"Cannot open a directory as a file: {file_path}"
        return str(path)

    def create_file(self, file_path: str) -> str:
        path = Path(file_path).expanduser().resolve()
        if path.exists():
            return f"File already exists: {file_path}"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        return f"Created file: {path}"

    def write_to_file(self, content: str, file_path: str) -> str:
        path = Path(file_path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        return f"Wrote content to {path}"

    def append_to_file(self, content: str, file_path: str) -> str:
        path = Path(file_path).expanduser().resolve()
        if not path.exists():
            return f"File not found: {file_path}"
        with open(path, "a") as f:
            f.write(content)
        return f"Appended content to {path}"

    def read_file(self, file_path: str, max_lines: int = 100) -> str:
        path = Path(file_path).expanduser().resolve()
        if not path.exists():
            return f"File not found: {file_path}"
        if path.is_dir():
            return f"Cannot read a directory: {file_path}"
        try:
            with open(path) as f:
                lines = f.readlines()[:max_lines]
            result = "".join(lines)
            if len(lines) == max_lines:
                result += f"\n... (showing first {max_lines} lines)"
            return result
        except UnicodeDecodeError:
            return f"Cannot read binary file: {file_path}"

    def delete_file(self, file_path: str) -> str:
        path = Path(file_path).expanduser().resolve()
        if not path.exists():
            return f"File not found: {file_path}"
        if path.is_dir():
            import shutil
            shutil.rmtree(path)
            return f"Deleted directory: {path}"
        path.unlink()
        return f"Deleted file: {path}"

    def search_files(self, query: str, search_dir: str = "~") -> str:
        search_path = Path(search_dir).expanduser().resolve()
        if not search_path.exists():
            return f"Directory not found: {search_dir}"
        matches = []
        query_lower = query.lower()
        for item in search_path.rglob("*"):
            if query_lower in item.name.lower():
                matches.append(str(item))
                if len(matches) >= 20:
                    break
        if not matches:
            return f"No files found matching '{query}'"
        return f"Found {len(matches)} matches:\n" + "\n".join(matches)

    def list_directory(self, dir_path: str = ".") -> str:
        path = Path(dir_path).expanduser().resolve()
        if not path.exists():
            return f"Directory not found: {dir_path}"
        if not path.is_dir():
            return f"Not a directory: {dir_path}"
        entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        lines = []
        for entry in entries[:50]:
            prefix = "  " if entry.is_file() else "d "
            lines.append(f"{prefix}{entry.name}")
        if len(entries) > 50:
            lines.append(f"... and {len(entries) - 50} more entries")
        return f"Contents of {path}:\n" + "\n".join(lines) if lines else f"Directory is empty: {path}"
