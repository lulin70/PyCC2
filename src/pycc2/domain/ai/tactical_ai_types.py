"""
Shared types and base class for the P9 Tactical AI system.

This module contains:
  - FlankSide enum
  - TacticalContext dataclass (battlefield snapshot)
  - PrioritizedIntent dataclass (scored intent wrapper)
  - TacticalAIBase abstract base class
  - Shared helper functions and unit-type constants

All tactical AI sub-modules import from here.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

from pycc2.domain.entities.unit import Faction, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord

if TYPE_CHECKING:
    from pycc2.domain.ai.blackboard import Blackboard
    from pycc2.domain.ai.difficulty_system import DifficultyConfig
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit


# ---------------------------------------------------------------------------
# Shared enums / dataclasses
# ---------------------------------------------------------------------------


class FlankSide(Enum):
    LEFT = auto()
    RIGHT = auto()


@dataclass(slots=True)
class TacticalContext:
    """Read-only snapshot of the battlefield passed to every tactical AI."""

    friendly_units: list[Unit]
    enemy_units: list[Unit]
    game_map: GameMap
    current_tick: int
    blackboards: dict[str, Blackboard] = field(default_factory=dict)
    difficulty_config: DifficultyConfig | None = None
    vl_positions: list[tuple[TileCoord, str | None, int]] = field(default_factory=list)

    @property
    def friendly_faction(self) -> Faction | None:
        if self.friendly_units:
            return self.friendly_units[0].faction
        return None


@dataclass(slots=True)
class PrioritizedIntent:
    """An intent tagged with the originating AI and a float priority [0..1]."""

    intent: pycc2.domain.ai.tactic_intent.TacticIntent  # type: ignore[name-defined]  # noqa: F821
    ai_name: str
    score: float = 0.0


# ---------------------------------------------------------------------------
# Unit-type constants shared across AIs
# ---------------------------------------------------------------------------

_HIGH_THREAT_TYPES: set[UnitType] = {
    UnitType.MACHINE_GUN_SQUAD,
    UnitType.AT_GUN_TEAM,
    UnitType.COMMANDER,
    UnitType.MORTAR_TEAM,
    UnitType.SNIPER_TEAM,
}

_ARMOR_TYPES: set[UnitType] = {UnitType.TANK}

_AT_TYPES: set[UnitType] = {UnitType.AT_GUN_TEAM}

_INFANTRY_TYPES: set[UnitType] = {
    UnitType.INFANTRY_SQUAD,
    UnitType.COMMANDER,
    UnitType.SNIPER_TEAM,
    UnitType.MEDIC_TEAM,
}


# ---------------------------------------------------------------------------
# Helper functions used by multiple AI modules
# ---------------------------------------------------------------------------


def _threat_score(unit: Unit, reference_pos: TileCoord) -> float:
    """Score an enemy unit by type, health, and distance to a reference point."""
    type_weights: dict[UnitType, float] = {
        UnitType.MACHINE_GUN_SQUAD: 3.0,
        UnitType.AT_GUN_TEAM: 2.5,
        UnitType.COMMANDER: 2.0,
        UnitType.MORTAR_TEAM: 1.8,
        UnitType.TANK: 3.5,
        UnitType.SNIPER_TEAM: 1.5,
        UnitType.INFANTRY_SQUAD: 1.0,
        UnitType.MEDIC_TEAM: 0.5,
    }
    weight = float(type_weights.get(unit.unit_type, 1.0))
    dist = max(unit.position.tile_coord.chebyshev_distance(reference_pos), 1)
    hp_ratio = float(unit.health.hp_ratio)
    result = weight * (0.5 + 0.5 * hp_ratio) / dist
    return float(result)


def _infer_facing(unit: Unit, allies: list[Unit]) -> TileCoord:
    """Infer the direction a unit is facing based on the centroid of
    opposing forces.  Returns the tile the unit is 'looking at'."""
    if not allies:
        return unit.position.tile_coord
    cx = sum(u.position.tile_coord.x for u in allies) / len(allies)
    cy = sum(u.position.tile_coord.y for u in allies) / len(allies)
    return TileCoord(int(cx), int(cy))


def _flank_position(
    enemy_pos: TileCoord,
    facing_target: TileCoord,
    side: FlankSide,
    offset: int = 4,
) -> TileCoord:
    """Calculate a flanking position offset perpendicular to the enemy's
    facing direction.  *facing_target* is the tile the enemy faces toward."""
    dx = facing_target.x - enemy_pos.x
    dy = facing_target.y - enemy_pos.y
    length = math.sqrt(dx * dx + dy * dy) or 1.0
    # Perpendicular (rotate 90 degrees)
    if side == FlankSide.LEFT:
        perp_x = dy / length
        perp_y = -dx / length
    else:
        perp_x = -dy / length
        perp_y = dx / length
    # Flank position is offset perpendicular + slightly forward
    fx = int(enemy_pos.x + perp_x * offset + dx / length * 2)
    fy = int(enemy_pos.y + perp_y * offset + dy / length * 2)
    return TileCoord(fx, fy)


def _nearest_vl(
    pos: TileCoord,
    vl_list: list[tuple[TileCoord, str | None, int]],
) -> tuple[TileCoord, str | None, int] | None:
    """Return the nearest VL entry (position, owner, value)."""
    if not vl_list:
        return None
    return min(vl_list, key=lambda v: pos.chebyshev_distance(v[0]))


# ---------------------------------------------------------------------------
# Abstract base class for all tactical AI modules
# ---------------------------------------------------------------------------


class TacticalAIBase(ABC):
    """Base class for composable tactical AI modules.

    Each AI evaluates the battlefield and returns a priority score (0.0-1.0)
    indicating how relevant its behaviour is this tick.  If the score is
    above a threshold the orchestrator calls ``execute`` to collect orders.
    """

    @abstractmethod
    def evaluate(self, context: TacticalContext) -> float:
        """Return a priority score in [0.0, 1.0]."""

    @abstractmethod
    def execute(self, context: TacticalContext) -> list[pycc2.domain.ai.tactic_intent.TacticIntent]:  # noqa: F821,E501
        """Return a list of TacticIntents for units this AI wants to control."""
