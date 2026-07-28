from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger("abix.shortcuts")

_SHORTCUTS_FILE = Path(__file__).parent.parent / "config" / "shortcuts.json"


class Shortcut:
    def __init__(self, keyword: str, browser: str, url: str, description: str = ""):
        self.keyword = keyword.upper()
        self.browser = browser
        self.url = url
        self.description = description

    def to_dict(self) -> dict:
        return {
            "keyword": self.keyword,
            "browser": self.browser,
            "url": self.url,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Shortcut:
        return cls(
            keyword=data.get("keyword", ""),
            browser=data.get("browser", "brave-browser"),
            url=data.get("url", ""),
            description=data.get("description", ""),
        )


class ShortcutManager:
    def __init__(self):
        self._shortcuts: dict[str, Shortcut] = {}
        self.load()

    def load(self) -> None:
        if _SHORTCUTS_FILE.exists():
            try:
                data = json.loads(_SHORTCUTS_FILE.read_text())
                for item in data:
                    sc = Shortcut.from_dict(item)
                    self._shortcuts[sc.keyword] = sc
                logger.info("Loaded %d shortcuts", len(self._shortcuts))
            except Exception as e:
                logger.warning("Failed to load shortcuts: %s", e)

    def save(self) -> None:
        _SHORTCUTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = [sc.to_dict() for sc in self._shortcuts.values()]
        _SHORTCUTS_FILE.write_text(json.dumps(data, indent=2))
        logger.info("Saved %d shortcuts", len(data))

    def get_all(self) -> list[dict]:
        return [sc.to_dict() for sc in self._shortcuts.values()]

    def get(self, keyword: str) -> Shortcut | None:
        return self._shortcuts.get(keyword.upper())

    def add(self, keyword: str, browser: str, url: str, description: str = "") -> str:
        keyword = keyword.upper().strip()
        if not keyword:
            return "Keyword cannot be empty"
        if not url:
            return "URL cannot be empty"
        self._shortcuts[keyword] = Shortcut(keyword, browser, url, description)
        self.save()
        return f"Shortcut '{keyword}' saved"

    def update(self, keyword: str, browser: str = None, url: str = None, description: str = None) -> str:
        keyword = keyword.upper().strip()
        sc = self._shortcuts.get(keyword)
        if not sc:
            return f"Shortcut '{keyword}' not found"
        if browser is not None:
            sc.browser = browser
        if url is not None:
            sc.url = url
        if description is not None:
            sc.description = description
        self.save()
        return f"Shortcut '{keyword}' updated"

    def delete(self, keyword: str) -> str:
        keyword = keyword.upper().strip()
        if keyword in self._shortcuts:
            del self._shortcuts[keyword]
            self.save()
            return f"Shortcut '{keyword}' deleted"
        return f"Shortcut '{keyword}' not found"

    def execute(self, keyword: str) -> str:
        keyword = keyword.upper().strip()
        sc = self._shortcuts.get(keyword)
        if not sc:
            return ""
        import subprocess
        import webbrowser
        env = dict(subprocess.os.environ)
        env.setdefault("DISPLAY", ":0")
        try:
            browser_path = subprocess.run(
                ["which", sc.browser], capture_output=True, text=True
            ).stdout.strip()
            if browser_path:
                subprocess.Popen(
                    [browser_path, sc.url],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    env=env,
                )
                return f"Opening {sc.description or sc.keyword} in browser"
        except Exception:
            pass
        webbrowser.open(sc.url)
        return f"Opening {sc.description or sc.keyword} in browser"
