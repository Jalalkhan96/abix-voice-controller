from __future__ import annotations

import abc


class OSBackend(abc.ABC):
    @abc.abstractmethod
    def launch_app(self, app_name: str) -> str:
        ...

    @abc.abstractmethod
    def close_app(self, app_name: str) -> str:
        ...

    @abc.abstractmethod
    def close_window(self) -> str:
        ...

    @abc.abstractmethod
    def minimize_window(self) -> str:
        ...

    @abc.abstractmethod
    def maximize_window(self) -> str:
        ...

    @abc.abstractmethod
    def focus_window(self, title: str) -> str:
        ...

    @abc.abstractmethod
    def get_active_window_title(self) -> str:
        ...

    @abc.abstractmethod
    def open_file_with_default(self, file_path: str) -> str:
        ...

    @abc.abstractmethod
    def set_volume(self, level: int) -> str:
        ...

    @abc.abstractmethod
    def get_volume(self) -> int:
        ...

    @abc.abstractmethod
    def media_play_pause(self) -> str:
        ...

    @abc.abstractmethod
    def media_next(self) -> str:
        ...

    @abc.abstractmethod
    def media_previous(self) -> str:
        ...
