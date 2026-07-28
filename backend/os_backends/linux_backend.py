from __future__ import annotations

import shutil
import subprocess

from backend.os_backends.base import OSBackend


class LinuxBackend(OSBackend):
    def launch_app(self, app_name: str) -> str:
        candidates = [app_name, app_name.lower(), app_name.capitalize(), app_name.title()]
        env = dict(subprocess.os.environ)
        env.setdefault("DISPLAY", ":0")
        seen = set()
        for name in candidates:
            if name in seen:
                continue
            seen.add(name)
            try:
                subprocess.Popen(
                    [name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    env=env,
                )
                return f"Launched {app_name}"
            except FileNotFoundError:
                path = shutil.which(name)
                if path:
                    subprocess.Popen(
                        [path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        env=env,
                    )
                    return f"Launched {app_name}"
        return f"Could not find application: {app_name}"

    def close_app(self, app_name: str) -> str:
        try:
            subprocess.run(["pkill", "-f", app_name], check=True, capture_output=True)
            return f"Closed {app_name}"
        except subprocess.CalledProcessError:
            return f"Could not close {app_name} — not running?"

    def close_window(self) -> str:
        try:
            subprocess.run(
                ["xdotool", "key", "alt+F4"],
                check=True,
                capture_output=True,
            )
            return "Closed active window"
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "Could not close window (xdotool not available)"

    def minimize_window(self) -> str:
        try:
            subprocess.run(
                ["xdotool", "key", "super+Down"],
                check=True,
                capture_output=True,
            )
            return "Minimized window"
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "Could not minimize window"

    def maximize_window(self) -> str:
        try:
            subprocess.run(
                ["xdotool", "key", "super+Up"],
                check=True,
                capture_output=True,
            )
            return "Maximized window"
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "Could not maximize window"

    def focus_window(self, title: str) -> str:
        try:
            result = subprocess.run(
                ["wmctrl", "-a", title],
                check=True,
                capture_output=True,
                text=True,
            )
            return f"Focused window: {title}"
        except (subprocess.CalledProcessError, FileNotFoundError):
            return f"Could not focus window: {title}"

    def get_active_window_title(self) -> str:
        try:
            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                check=True,
                capture_output=True,
                text=True,
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "unknown"

    def open_file_with_default(self, file_path: str) -> str:
        try:
            subprocess.Popen(
                ["xdg-open", file_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return f"Opened {file_path}"
        except FileNotFoundError:
            return f"Could not open {file_path}"

    def set_volume(self, level: int) -> str:
        level = max(0, min(100, level))
        try:
            subprocess.run(
                ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{level}%"],
                check=True,
                capture_output=True,
            )
            return f"Volume set to {level}%"
        except (subprocess.CalledProcessError, FileNotFoundError):
            return f"Could not set volume (pactl not available)"

    def get_volume(self) -> int:
        try:
            result = subprocess.run(
                ["pactl", "get-sink-volume", "@DEFAULT_SINK@"],
                check=True,
                capture_output=True,
                text=True,
            )
            import re
            match = re.search(r"(\d+)%", result.stdout)
            return int(match.group(1)) if match else 0
        except (subprocess.CalledProcessError, FileNotFoundError):
            return 0

    def media_play_pause(self) -> str:
        try:
            subprocess.run(
                ["xdotool", "key", "XF86AudioPlay"],
                check=True,
                capture_output=True,
            )
            return "Toggled media play/pause"
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "Could not toggle media"

    def media_next(self) -> str:
        try:
            subprocess.run(
                ["xdotool", "key", "XF86AudioNext"],
                check=True,
                capture_output=True,
            )
            return "Skipped to next track"
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "Could not skip track"

    def media_previous(self) -> str:
        try:
            subprocess.run(
                ["xdotool", "key", "XF86AudioPrev"],
                check=True,
                capture_output=True,
            )
            return "Went to previous track"
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "Could not go to previous track"
