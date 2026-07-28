from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger("abix.undo")


@dataclass
class UndoEntry:
    action: str
    target: str
    details: str
    inverse_action: str
    inverse_args: dict[str, str] = field(default_factory=dict)


class UndoManager:
    def __init__(self, max_history: int = 20) -> None:
        self._history: list[UndoEntry] = []
        self._max_history = max_history

    def record(self, entry: UndoEntry) -> None:
        self._history.append(entry)
        if len(self._history) > self._max_history:
            self._history.pop(0)

    def can_undo(self) -> bool:
        return len(self._history) > 0

    def peek(self) -> UndoEntry | None:
        return self._history[-1] if self._history else None

    def pop(self) -> UndoEntry | None:
        if self._history:
            return self._history.pop()
        return None

    def get_history(self) -> list[UndoEntry]:
        return list(self._history)

    def clear(self) -> None:
        self._history.clear()


def build_undo_entry(action: str, target: str, response: str) -> UndoEntry | None:
    if action == "create_file":
        return UndoEntry(
            action="create_file",
            target=target,
            details=response,
            inverse_action="delete_file",
            inverse_args={"target": target},
        )
    elif action == "write_to_file":
        return UndoEntry(
            action="write_to_file",
            target=target,
            details=response,
            inverse_action="create_file",
            inverse_args={"target": target},
        )
    elif action == "delete_file":
        return UndoEntry(
            action="delete_file",
            target=target,
            details=response,
            inverse_action="create_file",
            inverse_args={"target": target},
        )
    elif action == "open_app":
        return UndoEntry(
            action="open_app",
            target=target,
            details=response,
            inverse_action="close_app",
            inverse_args={"target": target},
        )
    return None
