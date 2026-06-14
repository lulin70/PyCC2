from __future__ import annotations

from typing import Any, NotRequired, Required, TypedDict


class UnitMoved(TypedDict, total=False):
    unit_id: Required[str]
    from_tile: Required[tuple[int, int]]
    to_tile: Required[tuple[int, int]]
    timestamp: float


class UnitAttacked(TypedDict, total=False):
    attacker_id: Required[str]
    target_id: Required[str]
    is_hit: Required[bool]
    damage: Required[float]
    kill_shot: NotRequired[bool]
    timestamp: float


class UnitKilled(TypedDict, total=False):
    unit_id: Required[str]
    killer_id: NotRequired[str]
    attacker_id: NotRequired[str]
    attacker_role: NotRequired[str]
    unit_type: NotRequired[str]
    position: Required[tuple[int, int]]
    faction: Required[str]
    timestamp: float


class MoraleChanged(TypedDict, total=False):
    unit_id: Required[str]
    old_value: Required[int]
    new_value: Required[int]
    event_type: Required[str]
    state_changed: Required[bool]
    new_state: NotRequired[str]
    timestamp: float


class WeaponFired(TypedDict, total=False):
    unit_id: Required[str]
    weapon_id: Required[str]
    target_id: Required[str]
    hit: Required[bool]
    ammo_remaining: Required[int]
    timestamp: float


class WeaponReloaded(TypedDict, total=False):
    unit_id: Required[str]
    weapon_id: Required[str]
    timestamp: float


class WeaponJammed(TypedDict, total=False):
    unit_id: Required[str]
    weapon_id: Required[str]
    timestamp: float


class ProjectileSpawned(TypedDict, total=False):
    projectile_id: Required[str]
    firer_id: Required[str]
    start_pos: Required[tuple[int, int]]
    target_pos: Required[tuple[int, int]]
    speed: Required[float]
    timestamp: float


class ProjectileHit(TypedDict, total=False):
    projectile_id: Required[str]
    target_id: Required[str]
    hit_pos: Required[tuple[int, int]]
    damage: Required[float]
    timestamp: float


class FogOfWarUpdated(TypedDict, total=False):
    observer_id: Required[str]
    newly_revealed_count: Required[int]
    total_visible: Required[int]
    tick: Required[int]
    timestamp: float


class TurnStarted(TypedDict, total=False):
    turn_number: Required[int]
    side: Required[str]
    timestamp: float


class TurnEnded(TypedDict, total=False):
    turn_number: Required[int]
    side: Required[str]
    units_moved: Required[int]
    attacks_made: Required[int]
    timestamp: float


class GamePaused(TypedDict, total=False):
    reason: NotRequired[str]
    timestamp: float


class GameResumed(TypedDict, total=False):
    timestamp: float


class SaveRequested(TypedDict, total=False):
    slot: Required[int]
    auto_save: NotRequired[bool]
    timestamp: float


class SaveCompleted(TypedDict, total=False):
    slot: Required[int]
    filepath: Required[str]
    success: Required[bool]
    error_message: NotRequired[str]
    timestamp: float


class SaveLoaded(TypedDict, total=False):
    slot: Required[int]
    filepath: Required[str]
    success: Required[bool]
    error_message: NotRequired[str]
    timestamp: float


class ErrorOccurred(TypedDict, total=False):
    source: Required[str]
    error_type: Required[str]
    message: Required[str]
    severity: Required[str]
    context: NotRequired[dict[str, Any]]
    timestamp: float


class VictoryConditionMet(TypedDict, total=False):
    condition_type: Required[str]
    winner: Required[str]
    turn_number: Required[int]
    timestamp: float


class DebugCommand(TypedDict, total=False):
    command: Required[str]
    args: NotRequired[list[Any]]
    result: NotRequired[Any]
    timestamp: float


from pycc2.domain.interfaces.event_types import (
    PlayerCommand,  # noqa: F401 — re-export for backward compatibility
)

__all__ = [
    "UnitMoved",
    "UnitAttacked",
    "UnitKilled",
    "MoraleChanged",
    "WeaponFired",
    "WeaponReloaded",
    "WeaponJammed",
    "ProjectileSpawned",
    "ProjectileHit",
    "FogOfWarUpdated",
    "TurnStarted",
    "TurnEnded",
    "GamePaused",
    "GameResumed",
    "SaveRequested",
    "SaveCompleted",
    "SaveLoaded",
    "ErrorOccurred",
    "VictoryConditionMet",
    "DebugCommand",
    "PlayerCommand",
]
