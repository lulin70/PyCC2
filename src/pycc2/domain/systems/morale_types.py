"""Morale type definitions — extracted from morale_system.py (P5-1 batch 2).

Contains the pure data types used across the morale subsystem:
  - MoraleEvent: discrete events that affect morale
  - MoraleState: 5-state CC2-authentic morale state machine
  - RoutingTarget: target position dataclass for fleeing units
  - MoraleCalculationResult: result of event-driven morale calculation

This module has NO pycc2 runtime dependencies (only stdlib) so it can be
imported by all other morale sub-modules without circular import risk.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.value_objects.vec2 import Vec2


class MoraleEvent(Enum):
    """Events that can affect unit morale."""

    ALLY_KILLED = auto()
    LEADER_KILLED = auto()
    UNDER_HEAVY_FIRE = auto()
    NEAR_EXPLOSION = auto()
    KILL_CONFIRMED = auto()
    RALLY = auto()
    IN_COVER = auto()
    COMMANDER_NEARBY = auto()
    PANIC_CONTAGION = auto()


class MoraleState(Enum):
    """CC2 morale states with behavioral effects."""

    RALLYED = "rallyed"  # >70: Full combat effectiveness
    WAVERING = "wavering"  # 40-70: Slightly degraded
    PINNED = "pinned"  # 20-40: Cannot move, reduced fire
    BROKEN = "broken"  # <20: May flee, refuses orders
    ROUTING = "routing"  # Actively fleeing


# ===========================================================================
# Threshold / configuration constants (CC2 authentic)
# ===========================================================================

RALLYED_THRESHOLD: int = 70
WAVERING_THRESHOLD: int = 40
PINNED_THRESHOLD: int = 20
BROKEN_THRESHOLD: int = 20  # Same as pinned upper bound

# Recovery rates
BASE_RECOVERY_RATE: float = 0.5  # Morale points per second
COMMANDER_BONUS_MULTIPLIER: float = 2.0  # Near commander recovery bonus
COVER_BONUS: float = 0.3  # In cover recovery bonus

# Suppression impact on morale
SUPPRESSION_TO_MORALE_RATIO: float = 0.3  # 30% of suppression affects morale

# Routing behavior
ROUTING_CHECK_INTERVAL: int = 30  # Check every 30 ticks
ROUTING_FLEE_DURATION: int = 180  # 3 seconds at 60 FPS
FLEE_CHANCE_BROKEN: float = 0.15  # 15% chance per check when broken
FLEE_CHANCE_ROUTING: float = 0.4  # 40% chance when already routing


def resolve_morale_state(morale_value: int) -> MoraleState:
    """Map numeric morale value to state enum (pure threshold check)."""
    if morale_value > RALLYED_THRESHOLD:
        return MoraleState.RALLYED
    elif morale_value > WAVERING_THRESHOLD:
        return MoraleState.WAVERING
    elif morale_value > PINNED_THRESHOLD:
        return MoraleState.PINNED
    else:
        return MoraleState.BROKEN


@dataclass
class RoutingTarget:
    """Target position for routing/fleeing unit."""

    position: Vec2 | None = None
    is_fleeing: bool = False
    flee_ticks_remaining: int = 0


@dataclass(slots=True)
class MoraleCalculationResult:
    """Result of a morale event calculation."""

    morale_delta: int
    suppression_delta: int
    state_changed: bool
    old_state: str | None
    new_state: str | None
    contagion_targets: list[str] = field(default_factory=list)


__all__ = [
    "BASE_RECOVERY_RATE",
    "BROKEN_THRESHOLD",
    "COMMANDER_BONUS_MULTIPLIER",
    "COVER_BONUS",
    "FLEE_CHANCE_BROKEN",
    "FLEE_CHANCE_ROUTING",
    "MoraleCalculationResult",
    "MoraleEvent",
    "MoraleState",
    "PINNED_THRESHOLD",
    "RALLYED_THRESHOLD",
    "ROUTING_CHECK_INTERVAL",
    "ROUTING_FLEE_DURATION",
    "RoutingTarget",
    "SUPPRESSION_TO_MORALE_RATIO",
    "WAVERING_THRESHOLD",
    "resolve_morale_state",
]
