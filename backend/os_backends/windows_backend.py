from __future__ import annotations

import subprocess
import sys

from backend.os_backends.base import OSBackend


class WindowsBackend(OSBackend):
    def launch_app(self, app_name: str) -> str:
        try:
            subprocess.Popen(
                ["cmd", "/c", "start", "", app_name],
                shell=False,
            )
            return f"Launched {app_name}"
        except Exception as e:
            return f"Could not launch {app_name}: {e}"

    def close_app(self, app_name: str) -> str:
        try:
            subprocess.run(
                ["taskkill", "/IM", f"{app_name}.exe", "/F"],
                check=True,
                capture_output=True,
            )
            return f"Closed {app_name}"
        except subprocess.CalledProcessError:
            return f"Could not close {app_name}"

    def close_window(self) -> str:
        try:
            import pyautogui
            pyautogui.hotkey("alt", "f4")
            return "Closed active window"
        except Exception:
            return "Could not close window"

    def minimize_window(self) -> str:
        try:
            import pyautogui
            pyautogui.hotkey("win", "Down")
            return "Minimized window"
        except Exception:
            return "Could not minimize window"

    def maximize_window(self) -> str:
        try:
            import pyautogui
            pyautogui.hotkey("win", "Up")
            return "Maximized window"
        except Exception:
            return "Could not maximize window"

    def focus_window(self, title: str) -> str:
        try:
            import pygetwindow as gw
            windows = gw.getWindowsWithTitle(title)
            if windows:
                windows[0].activate()
                return f"Focused window: {title}"
            return f"No window found with title: {title}"
        except Exception as e:
            return f"Could not focus window: {e}"

    def get_active_window_title(self) -> str:
        try:
            import pygetwindow as gw
            win = gw.getActiveWindow()
            return win.title if win else "unknown"
        except Exception:
            return "unknown"

    def open_file_with_default(self, file_path: str) -> str:
        try:
            subprocess.Popen(["cmd", "/c", "start", "", file_path])
            return f"Opened {file_path}"
        except Exception as e:
            return f"Could not open {file_path}: {e}"

    def set_volume(self, level: int) -> str:
        return "Volume control not implemented on Windows yet"

    def get_volume(self) -> int:
        return 0

    def media_play_pause(self) -> str:
        try:
            import pyautogui
            pyautogui.press("playpause")
            return "Toggled media play/pause"
        except Exception:
            return "Could not toggle media"

    def media_next(self) -> str:
        try:
            import pyautogui
            pyautogui.press("nexttrack")
            return "Skipped to next track"
        except Exception:
            return "Could not skip track"

    def media_previous(self) -> str:
        try:
            import pyautogui
            pyautogui.press("prevtrack")
            return "Went to previous track"
        except Exception:
            return "Could not go to previous track"
