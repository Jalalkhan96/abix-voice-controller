from __future__ import annotations

import enum
import re
import shlex
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

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"\s+", " ", text.strip().lower())

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        try:
            return shlex.split(text.lower())
        except ValueError:
            return text.lower().split()

    def _matches_blocked(self, command: str, pattern: str) -> bool:
        # Plain substring match on whitespace-normalized text — catches the
        # common case and is robust to extra/irregular spacing that would
        # otherwise slip past a raw substring check.
        if self._normalize(pattern) in self._normalize(command):
            return True

        # Token-subsequence match — catches the same pattern expressed with
        # different quoting (e.g. 'rm' '-rf' '/' vs rm -rf /), which raw
        # substring matching misses because the quote characters break it.
        pattern_tokens = self._tokenize(pattern)
        if not pattern_tokens:
            return False
        cmd_tokens = self._tokenize(command)
        n, m = len(cmd_tokens), len(pattern_tokens)
        for i in range(n - m + 1):
            if cmd_tokens[i:i + m] == pattern_tokens:
                return True
        return False

    def check(self, command: str, tier: PermissionTier) -> PermissionResult:
        cmd_lower = command.strip().lower()

        for pattern in self._blocked:
            if self._matches_blocked(command, pattern):
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
