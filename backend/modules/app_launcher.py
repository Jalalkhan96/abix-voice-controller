from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class AppLauncher:
    _LINUX_APP_DIRS = [
        Path("/usr/share/applications"),
        Path.home() / ".local/share/applications",
        Path("/var/lib/flatpak/exports/share/applications"),
        Path("/var/lib/snapd/desktop/applications"),
    ]

    def find_executable(self, name: str) -> str | None:
        candidates = [name, name.lower(), name.capitalize(), name.title()]

        import re
        for suffix in [" browser", " app", " application", " editor"]:
            if name.lower().endswith(suffix):
                stem = name[:-len(suffix)]
                candidates.extend([stem, stem.lower(), stem.capitalize(), stem.title()])

        first_word = name.split()[0] if name.split() else name
        candidates.extend([first_word, first_word.lower()])

        clean = re.sub(r"\s+(and|or|to|then)\s+.*", "", name, flags=re.IGNORECASE).strip()
        if clean != name:
            candidates.extend([clean, clean.lower(), clean.capitalize(), clean.title()])
            first_clean = clean.split()[0]
            candidates.extend([first_clean, first_clean.lower()])

        known_map = {
            "chrome": ["google-chrome", "google-chrome-stable", "chrome", "chromium", "chromium-browser"],
            "firefox": ["firefox", "firefox-esr"],
            "brave": ["brave-browser", "brave"],
            "code": ["code", "vscode"],
            "discord": ["discord"],
            "spotify": ["spotify"],
            "terminal": ["gnome-terminal", "konsole", "xterm"],
            "files": ["nautilus", "dolphin", "thunar"],
            "settings": ["gnome-control-center", "systemsettings"],
        }
        for key, alts in known_map.items():
            if key in name.lower() or key in first_word.lower():
                candidates.extend(alts)

        seen = set()
        for c in candidates:
            if not c or c in seen:
                continue
            seen.add(c)
            path = shutil.which(c)
            if path:
                return path

        for d in self._LINUX_APP_DIRS:
            if not d.is_dir():
                continue
            for desktop in d.iterdir():
                if not desktop.suffix == ".desktop":
                    continue
                content = desktop.read_text()
                app_name_match = re.search(r"^Name=(.+)$", content, re.MULTILINE)
                if not app_name_match:
                    continue
                desktop_name = app_name_match.group(1).strip()
                if name.lower() in desktop_name.lower() or first_word.lower() in desktop_name.lower():
                    exec_match = re.search(r"^Exec=(.+)$", content, re.MULTILINE)
                    if exec_match:
                        exe = exec_match.group(1).split("%")[0].strip().strip('"')
                        path = shutil.which(exe.split()[0]) if exe.split() else None
                        if path:
                            return path

        return None

    def launch(self, app_name: str) -> str:
        exe = self.find_executable(app_name)
        if exe:
            try:
                env = dict(subprocess.os.environ)
                env.setdefault("DISPLAY", ":0")
                subprocess.Popen(
                    [exe],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    env=env,
                )
                return f"Launched {app_name}"
            except Exception as e:
                return f"Failed to launch {app_name}: {e}"

        from backend.modules.system_automation import get_backend
        backend = get_backend()
        return backend.launch_app(app_name)

    def close(self, app_name: str) -> str:
        from backend.modules.system_automation import get_backend
        backend = get_backend()
        return backend.close_app(app_name)

    def switch_to(self, app_name: str) -> str:
        from backend.modules.system_automation import get_backend
        backend = get_backend()
        return backend.focus_window(app_name)
