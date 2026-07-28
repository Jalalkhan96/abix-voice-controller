from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from backend.safety.permissions import PermissionManager, PermissionTier, PermissionResult


@pytest.fixture
def perm_manager(tmp_path: Path) -> PermissionManager:
    whitelist_file = tmp_path / "whitelist.yaml"
    whitelist_file.write_text("""
pre_approved:
  - "ls"
  - "pwd"
  - "git status"
blocked:
  - "rm -rf /"
  - "dd if="
""")
    return PermissionManager(str(whitelist_file))


class TestPermissionManager:
    def test_safe_command_allowed(self, perm_manager: PermissionManager):
        result = perm_manager.check("open file.txt", PermissionTier.SAFE)
        assert result.allowed is True
        assert result.tier == PermissionTier.SAFE

    def test_write_command_allowed(self, perm_manager: PermissionManager):
        result = perm_manager.check("create file.txt", PermissionTier.WRITE)
        assert result.allowed is True
        assert result.requires_confirmation is False

    def test_destructive_requires_confirmation(self, perm_manager: PermissionManager):
        result = perm_manager.check("delete file.txt", PermissionTier.DESTRUCTIVE)
        assert result.allowed is True
        assert result.requires_confirmation is True

    def test_blocked_command_rejected(self, perm_manager: PermissionManager):
        result = perm_manager.check("rm -rf /", PermissionTier.WRITE)
        assert result.allowed is False
        assert "blocked" in result.reason.lower()

    def test_blocked_dd_rejected(self, perm_manager: PermissionManager):
        result = perm_manager.check("dd if=/dev/zero of=/dev/sda", PermissionTier.WRITE)
        assert result.allowed is False

    def test_whitelisted_command(self, perm_manager: PermissionManager):
        assert perm_manager.is_whitelisted("ls -la") is True
        assert perm_manager.is_whitelisted("git status") is True
        assert perm_manager.is_whitelisted("rm file.txt") is False

    def test_blocked_pattern(self, perm_manager: PermissionManager):
        assert perm_manager.is_blocked("rm -rf /") is True
        assert perm_manager.is_blocked("dd if=/dev/zero") is True
        assert perm_manager.is_blocked("ls") is False

    def test_reload(self, perm_manager: PermissionManager):
        perm_manager.reload()
        assert perm_manager.pre_approved == ["ls", "pwd", "git status"]
