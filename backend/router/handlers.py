from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from backend.safety.permissions import PermissionTier

HandlerFn = Callable[..., Awaitable[str]]


@dataclass(frozen=True)
class HandlerSpec:
    tier: PermissionTier
    fn: HandlerFn


_REGISTRY: dict[str, HandlerSpec] = {}


def command(intent: str, tier: PermissionTier) -> Callable[[HandlerFn], HandlerFn]:
    """Register an async handler for a voice command intent.

    Handlers are plain async functions of the form `(router, args) -> str`.
    Used both for CommandRouter's own intents and for plugin-registered
    commands, so new commands never require editing the router's dispatch.
    """

    def decorator(fn: HandlerFn) -> HandlerFn:
        if intent in _REGISTRY:
            raise ValueError(f"Duplicate handler registered for intent '{intent}'")
        _REGISTRY[intent] = HandlerSpec(tier=tier, fn=fn)
        return fn

    return decorator


def get_registry() -> dict[str, HandlerSpec]:
    return _REGISTRY


def tier_for(intent: str, default: PermissionTier = PermissionTier.WRITE) -> PermissionTier:
    spec = _REGISTRY.get(intent)
    return spec.tier if spec is not None else default
