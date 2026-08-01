from __future__ import annotations

import importlib
import importlib.util
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("abix.plugins")


@dataclass
class SkillManifest:
    name: str
    version: str
    description: str
    author: str
    commands: list[dict[str, str]]
    enabled: bool = True


class Skill(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def manifest(self) -> SkillManifest:
        ...

    @abstractmethod
    def handle(self, intent: str, args: dict[str, Any]) -> str:
        ...

    def on_load(self) -> None:
        pass

    def on_unload(self) -> None:
        pass


@dataclass
class RegisteredSkill:
    skill: Skill
    manifest: SkillManifest
    path: Path


class SkillRegistry:
    def __init__(self, skills_dirs: list[str] | None = None) -> None:
        self._skills: dict[str, RegisteredSkill] = {}
        self._commands: dict[str, str] = {}
        self._dirs = [Path(d) for d in (skills_dirs or ["skills"])]
        self._dirs.extend([Path.home() / ".config" / "abix" / "skills"])
        self._last_signature: frozenset[tuple[str, float]] = frozenset()

    def _current_signature(self) -> frozenset[tuple[str, float]]:
        sig: set[tuple[str, float]] = set()
        for skills_dir in self._dirs:
            if not skills_dir.exists():
                continue
            for skill_path in skills_dir.iterdir():
                manifest_path = skill_path / "manifest.yaml"
                if skill_path.is_dir() and manifest_path.exists():
                    try:
                        sig.add((str(manifest_path), manifest_path.stat().st_mtime))
                    except OSError:
                        pass
        return frozenset(sig)

    def discover(self) -> int:
        count = 0
        for skills_dir in self._dirs:
            if not skills_dir.exists():
                continue
            for skill_path in skills_dir.iterdir():
                if skill_path.is_dir() and (skill_path / "manifest.yaml").exists():
                    try:
                        self._load_skill(skill_path)
                        count += 1
                    except Exception as e:
                        logger.warning("Failed to load skill from %s: %s", skill_path, e)
        self._last_signature = self._current_signature()
        logger.info("Discovered %d skills", count)
        return count

    def reload_if_changed(self) -> bool:
        """Re-run discovery if a skill manifest was added, removed, or edited.

        Cheap enough to poll: this only stats manifest.yaml files, it doesn't
        touch the skill modules themselves unless something actually changed.
        Returns True if a reload happened.
        """
        current = self._current_signature()
        if current == self._last_signature:
            return False

        for name, registered in list(self._skills.items()):
            try:
                registered.skill.on_unload()
            except Exception as e:
                logger.warning("Error unloading skill %s: %s", name, e)

        self._skills.clear()
        self._commands.clear()
        self.discover()
        return True

    def _load_skill(self, skill_dir: Path) -> None:
        import yaml

        manifest_path = skill_dir / "manifest.yaml"
        with open(manifest_path) as f:
            data = yaml.safe_load(f)

        manifest = SkillManifest(
            name=data["name"],
            version=data.get("version", "0.1.0"),
            description=data.get("description", ""),
            author=data.get("author", "unknown"),
            commands=data.get("commands", []),
            enabled=data.get("enabled", True),
        )

        if not manifest.enabled:
            return

        module_name = data.get("module", f"{manifest.name}_skill")
        module_path = skill_dir / f"{module_name}.py"

        if not module_path.exists():
            for py_file in skill_dir.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue
                module_path = py_file
                break
        else:
            module_path = skill_dir / f"{module_name}.py"

        if not module_path.exists():
            logger.warning("No Python module found for skill: %s", manifest.name)
            return

        spec = importlib.util.spec_from_file_location(
            f"abix_skill_{manifest.name}", str(module_path)
        )
        if spec is None or spec.loader is None:
            return

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        skill_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, Skill)
                and attr is not Skill
            ):
                skill_class = attr
                break

        if skill_class is None:
            logger.warning("No Skill subclass found in %s", module_path)
            return

        skill_instance = skill_class()
        skill_instance.on_load()

        self._skills[manifest.name] = RegisteredSkill(
            skill=skill_instance,
            manifest=manifest,
            path=skill_dir,
        )

        for cmd in manifest.commands:
            trigger = cmd.get("trigger", "").lower()
            if trigger:
                self._commands[trigger] = manifest.name

        logger.info("Loaded skill: %s v%s", manifest.name, manifest.version)

    def get_skill(self, name: str) -> RegisteredSkill | None:
        return self._skills.get(name)

    def handle_command(self, trigger: str, args: dict[str, Any] | None = None) -> str | None:
        trigger_lower = trigger.lower()
        skill_name = self._commands.get(trigger_lower)
        if skill_name is None:
            return None

        registered = self._skills.get(skill_name)
        if registered is None:
            return None

        try:
            return registered.skill.handle(trigger, args or {})
        except Exception as e:
            logger.exception("Skill %s failed: %s", skill_name, e)
            return f"Skill {skill_name} error: {e}"

    def list_skills(self) -> list[dict[str, str]]:
        return [
            {
                "name": r.manifest.name,
                "version": r.manifest.version,
                "description": r.manifest.description,
                "commands": [c.get("trigger", "") for c in r.manifest.commands],
            }
            for r in self._skills.values()
        ]

    def enable(self, name: str) -> bool:
        registered = self._skills.get(name)
        if registered:
            registered.manifest.enabled = True
            return True
        return False

    def disable(self, name: str) -> bool:
        registered = self._skills.get(name)
        if registered:
            registered.manifest.enabled = False
            return True
        return False

    @property
    def registered_triggers(self) -> dict[str, str]:
        return dict(self._commands)
