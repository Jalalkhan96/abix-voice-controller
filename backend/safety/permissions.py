from __future__ import annotations

import enum
import yaml
from pathlib import Path
from dataclasses import dataclass


class PermissionTier(enum.IntEnum):
    SAFE = 1
    WRITE = 2
    DESTRUCTIVE = 3


@dataclass
class PermissionResult:
    tier: PermissionTier
    allowed: bool
    reason: str
    requires_confirmation: bool = False


class PermissionManager:
    def __init__(self, whitelist_path: str = "config/whitelist.yaml") -> None:
        self._whitelist_path = Path(whitelist_path)
        self._pre_approved: list[str] = []
        self._blocked: list[str] = []
        self._load_whitelist()

    def _load_whitelist(self) -> None:
        if not self._whitelist_path.exists():
            return
        with open(self._whitelist_path) as f:
            data = yaml.safe_load(f) or {}
        self._pre_approved = [c.strip().lower() for c in data.get("pre_approved", [])]
        self._blocked = [c.strip().lower() for c in data.get("blocked", [])]

    def reload(self) -> None:
        self._load_whitelist()

    def check(self, command: str, tier: PermissionTier) -> PermissionResult:
        cmd_lower = command.strip().lower()

        for pattern in self._blocked:
            if pattern in cmd_lower:
                return PermissionResult(
                    tier=tier,
                    allowed=False,
                    reason=f"Command matches blocked pattern: {pattern}",
                )

        if tier == PermissionTier.DESTRUCTIVE:
            return PermissionResult(
                tier=tier,
                allowed=True,
                reason="Requires confirmation",
                requires_confirmation=True,
            )

        if tier == PermissionTier.SAFE:
            return PermissionResult(
                tier=tier,
                allowed=True,
                reason="Safe command, auto-approved",
            )

        if tier == PermissionTier.WRITE:
            if any(approved in cmd_lower for approved in self._pre_approved):
                return PermissionResult(
                    tier=tier,
                    allowed=True,
                    reason="Pre-approved write command",
                )
            return PermissionResult(
                tier=tier,
                allowed=True,
                reason="Write command auto-approved, logged",
            )

        return PermissionResult(
            tier=tier,
            allowed=False,
            reason=f"Unknown tier: {tier}",
        )

    def is_whitelisted(self, command: str) -> bool:
        cmd_lower = command.strip().lower()
        return any(approved in cmd_lower for approved in self._pre_approved)

    def is_blocked(self, command: str) -> bool:
        cmd_lower = command.strip().lower()
        return any(pattern in cmd_lower for pattern in self._blocked)

    @property
    def pre_approved(self) -> list[str]:
        return list(self._pre_approved)

    @property
    def blocked(self) -> list[str]:
        return list(self._blocked)
