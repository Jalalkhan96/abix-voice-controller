from __future__ import annotations

import subprocess

from backend.os_backends.base import OSBackend


class MacBackend(OSBackend):
    def launch_app(self, app_name: str) -> str:
        try:
            subprocess.Popen(
                ["open", "-a", app_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return f"Launched {app_name}"
        except Exception as e:
            return f"Could not launch {app_name}: {e}"

    def close_app(self, app_name: str) -> str:
        try:
            subprocess.run(
                ["osascript", "-e", f'tell application "{app_name}" to quit'],
                check=True,
                capture_output=True,
            )
            return f"Closed {app_name}"
        except subprocess.CalledProcessError:
            return f"Could not close {app_name}"

    def close_window(self) -> str:
        try:
            subprocess.run(
                ["osascript", "-e", 'tell application "System Events" to keystroke "w" using command down'],
                check=True,
                capture_output=True,
            )
            return "Closed active window"
        except subprocess.CalledProcessError:
            return "Could not close window"

    def minimize_window(self) -> str:
        try:
            subprocess.run(
                ["osascript", "-e", 'tell application "System Events" to keystroke "m" using command down'],
                check=True,
                capture_output=True,
            )
            return "Minimized window"
        except subprocess.CalledProcessError:
            return "Could not minimize window"

    def maximize_window(self) -> str:
        try:
            subprocess.run(
                ["osascript", "-e", 'tell application "System Events" to keystroke "m" using {command down, option down}'],
                check=True,
                capture_output=True,
            )
            return "Maximized window"
        except subprocess.CalledProcessError:
            return "Could not maximize window"

    def focus_window(self, title: str) -> str:
        try:
            subprocess.run(
                ["osascript", "-e", f'tell application "{title}" to activate'],
                check=True,
                capture_output=True,
            )
            return f"Focused window: {title}"
        except subprocess.CalledProcessError:
            return f"Could not focus window: {title}"

    def get_active_window_title(self) -> str:
        try:
            result = subprocess.run(
                [
                    "osascript", "-e",
                    'tell application "System Events" to get name of first application process whose frontmost is true',
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, Exception):
            return "unknown"

    def open_file_with_default(self, file_path: str) -> str:
        try:
            subprocess.Popen(
                ["open", file_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return f"Opened {file_path}"
        except Exception as e:
            return f"Could not open {file_path}: {e}"

    def set_volume(self, level: int) -> str:
        level = max(0, min(100, level))
        try:
            subprocess.run(
                ["osascript", "-e", f"set volume output volume {level}"],
                check=True,
                capture_output=True,
            )
            return f"Volume set to {level}%"
        except subprocess.CalledProcessError:
            return "Could not set volume"

    def get_volume(self) -> int:
        try:
            result = subprocess.run(
                ["osascript", "-e", "output volume of (get volume settings)"],
                check=True,
                capture_output=True,
                text=True,
            )
            return int(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError):
            return 0

    def media_play_pause(self) -> str:
        try:
            subprocess.run(
                ["osascript", "-e", 'tell application "System Events" to key code 16'],
                check=True,
                capture_output=True,
            )
            return "Toggled media play/pause"
        except subprocess.CalledProcessError:
            return "Could not toggle media"

    def media_next(self) -> str:
        try:
            subprocess.run(
                ["osascript", "-e", 'tell application "System Events" to key code 17'],
                check=True,
                capture_output=True,
            )
            return "Skipped to next track"
        except subprocess.CalledProcessError:
            return "Could not skip track"

    def media_previous(self) -> str:
        try:
            subprocess.run(
                ["osascript", "-e", 'tell application "System Events" to key code 20'],
                check=True,
                capture_output=True,
            )
            return "Went to previous track"
        except subprocess.CalledProcessError:
            return "Could not go to previous track"
