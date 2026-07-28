from __future__ import annotations

import sys
import platform
import psutil

from backend.os_backends.base import OSBackend


def get_backend() -> OSBackend:
    system = platform.system()
    if system == "Linux":
        from backend.os_backends.linux_backend import LinuxBackend
        return LinuxBackend()
    elif system == "Windows":
        from backend.os_backends.windows_backend import WindowsBackend
        return WindowsBackend()
    elif system == "Darwin":
        from backend.os_backends.mac_backend import MacBackend
        return MacBackend()
    else:
        raise RuntimeError(f"Unsupported OS: {system}")


class SystemAutomation:
    def __init__(self) -> None:
        self._backend = get_backend()

    @property
    def backend(self) -> OSBackend:
        return self._backend

    def get_system_info(self) -> str:
        info_parts = []

        disk = psutil.disk_usage("/")
        info_parts.append(f"Disk: {disk.percent}% used ({disk.free // (1024**3)}GB free of {disk.total // (1024**3)}GB)")

        mem = psutil.virtual_memory()
        info_parts.append(f"RAM: {mem.percent}% used ({mem.available // (1024**3)}GB available of {mem.total // (1024**3)}GB)")

        cpu_pct = psutil.cpu_percent(interval=1)
        info_parts.append(f"CPU: {cpu_pct}% used")

        boot = psutil.boot_time()
        import time
        uptime_seconds = time.time() - boot
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        mins = int((uptime_seconds % 3600) // 60)
        info_parts.append(f"Uptime: {days}d {hours}h {mins}m")

        return "System info:\n" + "\n".join(info_parts)

    def launch_app(self, app_name: str) -> str:
        return self._backend.launch_app(app_name)

    def close_app(self, app_name: str) -> str:
        return self._backend.close_app(app_name)

    def close_window(self) -> str:
        return self._backend.close_window()

    def open_file(self, file_path: str) -> str:
        return self._backend.open_file_with_default(file_path)

    def set_volume(self, level: int) -> str:
        return self._backend.set_volume(level)

    def get_volume(self) -> int:
        return self._backend.get_volume()

    def volume_up(self) -> str:
        current = self.get_volume()
        new_level = min(100, current + 10)
        return self.set_volume(new_level)

    def volume_down(self) -> str:
        current = self.get_volume()
        new_level = max(0, current - 10)
        return self.set_volume(new_level)

    def volume_mute(self) -> str:
        return self.set_volume(0)

    def media_play_pause(self) -> str:
        return self._backend.media_play_pause()

    def media_next(self) -> str:
        return self._backend.media_next()

    def media_previous(self) -> str:
        return self._backend.media_previous()
