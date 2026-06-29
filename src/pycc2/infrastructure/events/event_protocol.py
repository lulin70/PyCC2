"""Typed event protocol definitions shared across the event bus.

Defines TypedDict schemas for every game event payload so publishers and
subscribers share a common, type-checked contract.
"""

from __future__ import annotations

from typing import Any, NotRequired, Required, TypedDict


class UnitMoved(TypedDict, total=False):
    """Event emitted when a unit moves from one tile to another."""

    unit_id: Required[str]
    from_tile: Required[tuple[int, int]]
    to_tile: Required[tuple[int, int]]
    timestamp: float


class UnitAttacked(TypedDict, total=False):
    """Event emitted when a unit attacks another unit."""

    attacker_id: Required[str]
    target_id: Required[str]
    is_hit: Required[bool]
    damage: Required[float]
    kill_shot: NotRequired[bool]
    timestamp: float


class UnitKilled(TypedDict, total=False):
    """Event emitted when a unit is killed in combat."""

    unit_id: Required[str]
    killer_id: NotRequired[str]
    attacker_id: NotRequired[str]
    attacker_role: NotRequired[str]
    unit_type: NotRequired[str]
    position: Required[tuple[int, int]]
    faction: Required[str]
    timestamp: float


class MoraleChanged(TypedDict, total=False):
    """Event emitted when a unit's morale value changes."""

    unit_id: Required[str]
    old_value: Required[int]
    new_value: Required[int]
    event_type: Required[str]
    state_changed: Required[bool]
    new_state: NotRequired[str]
    timestamp: float


class WeaponFired(TypedDict, total=False):
    """Event emitted when a unit fires a weapon at a target."""

    unit_id: Required[str]
    weapon_id: Required[str]
    target_id: Required[str]
    hit: Required[bool]
    ammo_remaining: Required[int]
    timestamp: float


class WeaponReloaded(TypedDict, total=False):
    """Event emitted when a unit finishes reloading a weapon."""

    unit_id: Required[str]
    weapon_id: Required[str]
    timestamp: float


class WeaponJammed(TypedDict, total=False):
    """Event emitted when a weapon jams during firing."""

    unit_id: Required[str]
    weapon_id: Required[str]
    timestamp: float


class ProjectileSpawned(TypedDict, total=False):
    """Event emitted when a projectile is created in the world."""

    projectile_id: Required[str]
    firer_id: Required[str]
    start_pos: Required[tuple[int, int]]
    target_pos: Required[tuple[int, int]]
    speed: Required[float]
    timestamp: float


class ProjectileHit(TypedDict, total=False):
    """Event emitted when a projectile impacts a target."""

    projectile_id: Required[str]
    target_id: Required[str]
    hit_pos: Required[tuple[int, int]]
    damage: Required[float]
    timestamp: float


class FogOfWarUpdated(TypedDict, total=False):
    """Event emitted when fog-of-war visibility changes for an observer."""

    observer_id: Required[str]
    newly_revealed_count: Required[int]
    total_visible: Required[int]
    tick: Required[int]
    timestamp: float


class TurnStarted(TypedDict, total=False):
    """Event emitted when a turn begins for a side."""

    turn_number: Required[int]
    side: Required[str]
    timestamp: float


class TurnEnded(TypedDict, total=False):
    """Event emitted when a turn ends for a side."""

    turn_number: Required[int]
    side: Required[str]
    units_moved: Required[int]
    attacks_made: Required[int]
    timestamp: float


class TurnStartedEvent(TypedDict, total=False):
    """Event emitted when a new turn starts for a faction."""

    turn_number: Required[int]
    faction: Required[str]
    timestamp: float


class TurnEndedEvent(TypedDict, total=False):
    """Event emitted when the current turn ends."""

    turn_number: Required[int]
    timestamp: float


class GamePhaseChangedEvent(TypedDict, total=False):
    """Event emitted when the game transitions between phases."""

    old_phase: Required[str]
    new_phase: Required[str]
    turn_number: Required[int]
    timestamp: float


class GamePaused(TypedDict, total=False):
    """Event emitted when the game is paused."""

    reason: NotRequired[str]
    timestamp: float


class GameResumed(TypedDict, total=False):
    """Event emitted when the game is resumed from pause."""

    timestamp: float


class SaveRequested(TypedDict, total=False):
    """Event emitted when a save operation is requested."""

    slot: Required[int]
    auto_save: NotRequired[bool]
    timestamp: float


class SaveCompleted(TypedDict, total=False):
    """Event emitted when a save operation finishes."""

    slot: Required[int]
    filepath: Required[str]
    success: Required[bool]
    error_message: NotRequired[str]
    timestamp: float


class SaveLoaded(TypedDict, total=False):
    """Event emitted when a save file is loaded."""

    slot: Required[int]
    filepath: Required[str]
    success: Required[bool]
    error_message: NotRequired[str]
    timestamp: float


class ErrorOccurred(TypedDict, total=False):
    """Event emitted when a runtime error is captured for reporting."""

    source: Required[str]
    error_type: Required[str]
    message: Required[str]
    severity: Required[str]
    context: NotRequired[dict[str, Any]]
    timestamp: float


class VictoryConditionMet(TypedDict, total=False):
    """Event emitted when a victory condition is satisfied."""

    condition_type: Required[str]
    winner: Required[str]
    turn_number: Required[int]
    timestamp: float


class DebugCommand(TypedDict, total=False):
    """Event emitted when a debug command is issued."""

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
    "TurnStartedEvent",
    "TurnEndedEvent",
    "GamePhaseChangedEvent",
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
