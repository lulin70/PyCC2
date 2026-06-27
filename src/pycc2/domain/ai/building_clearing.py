"""Building Clearing — CC2-Authentic Urban Combat Behavior

Infantry can clear buildings room by room using WWII close-quarters tactics.
This mirrors the dangerous reality of urban combat where defenders have
significant advantages but attackers can use surprise and grenades.

Components:
  1. BuildingClearingAI   — Evaluates when to clear buildings and issues orders
  2. ClearingState        — Tracks the multi-step clearing process

Clearing process (CC2-authentic):
  1. APPROACH   — Move to adjacent tile of building
  2. GRENADE    — Throw grenade through window/door (3 tick delay)
  3. STACK      — Two units stack at entrance
  4. BREACH     — First unit enters, second follows
  5. CLEAR      — Room-by-room clearing

Combat modifiers:
  - Grenade in building: 2x damage, all occupants hit
  - Attackers: +20% accuracy for first 5 ticks after entry (surprise)
  - Defenders: -10% accuracy when building is being assaulted
  - Minimum 2 units needed for safe clearing
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.ai.tactical_ai import TacticalAIBase, TacticalContext
from pycc2.domain.entities.unit import UnitType
from pycc2.domain.value_objects.terrain_type import TerrainType
from pycc2.domain.value_objects.tile_coord import TileCoord

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BUILDING_TERRAIN: set[TerrainType] = {
    TerrainType.BUILDING_ENTERABLE,
}

_INFANTRY_TYPES: set[UnitType] = {
    UnitType.INFANTRY_SQUAD,
    UnitType.COMMANDER,
    UnitType.SNIPER_TEAM,
    UnitType.MEDIC_TEAM,
}

GRENADE_DELAY_TICKS: int = 3  # Time for grenade to detonate
SURPRISE_DURATION_TICKS: int = 5  # Duration of surprise accuracy bonus
SURPRISE_ACCURACY_BONUS: float = 0.20  # +20% accuracy for attackers
DEFENDER_PENALTY: float = 0.10  # -10% accuracy for defenders
GRENADE_BUILDING_DAMAGE: int = 30  # 2x normal grenade damage in building
MIN_CLEARING_UNITS: int = 2  # Minimum units for safe clearing


# ---------------------------------------------------------------------------
# ClearingState
# ---------------------------------------------------------------------------


class ClearingPhase(Enum):
    """Phases of building clearing operation."""

    APPROACH = auto()
    GRENADE = auto()
    STACK = auto()
    BREACH = auto()
    CLEAR = auto()
    COMPLETE = auto()


@dataclass(slots=True)
class ClearingState:
    """Tracks the state of a building clearing operation."""

    building_pos: TileCoord
    phase: ClearingPhase = ClearingPhase.APPROACH
    attackers: list[str] = field(default_factory=list)  # unit_ids
    grenade_timer: int = 0
    surprise_timer: int = 0
    phase_timer: int = 0

    @property
    def is_complete(self) -> bool:
        return self.phase == ClearingPhase.COMPLETE

    @property
    def has_surprise_bonus(self) -> bool:
        return self.surprise_timer > 0


# ---------------------------------------------------------------------------
# BuildingClearingAI
# ---------------------------------------------------------------------------


class BuildingClearingAI(TacticalAIBase):
    """Evaluate when to clear buildings and issue CLEAR_BUILDING orders.

    CC2 behaviour: When enemy units are in or near buildings, infantry
    squads coordinate to clear them. The process involves approaching,
    grenading, stacking at the entrance, and breaching.

    Evaluation heuristic:
      - Higher score when enemy units occupy buildings
      - Higher score when multiple friendly infantry are available
      - Lower score when insufficient units for clearing (need 2+)
      - Zero when no enemies in buildings
    """

    def evaluate(self, context: TacticalContext) -> float:
        enemies_in_buildings = self._enemies_in_buildings(context)
        if not enemies_in_buildings:
            return 0.0

        available = self._available_infantry(context)
        if len(available) < MIN_CLEARING_UNITS:
            return 0.0

        # Score based on enemy concentration in buildings
        enemy_ratio = min(len(enemies_in_buildings) / 3.0, 1.0)
        infantry_ratio = min(len(available) / 4.0, 1.0)

        score = 0.5 * enemy_ratio + 0.3 * infantry_ratio + 0.2 * 0.5
        return min(score, 1.0)

    def execute(self, context: TacticalContext) -> list[TacticIntent]:
        enemies_in_buildings = self._enemies_in_buildings(context)
        available = self._available_infantry(context)
        if not enemies_in_buildings or len(available) < MIN_CLEARING_UNITS:
            return []

        intents: list[TacticIntent] = []
        assigned: set[str] = set()

        # Group enemies by building position
        building_targets: dict[TileCoord, list[Unit]] = {}
        for enemy in enemies_in_buildings:
            pos = enemy.position.tile_coord
            building_targets.setdefault(pos, []).append(enemy)

        # Assign clearing teams to buildings
        for building_pos, defenders in building_targets.items():
            # Find nearest available infantry pair
            team = self._find_clearing_team(available, building_pos, assigned, context)
            if team is None:
                continue

            for unit in team:
                assigned.add(unit.id)
                intents.append(
                    TacticIntent(
                        unit_id=unit.id,
                        tactic_type=TacticType.CLEAR_BUILDING,
                        priority=8,
                        target_position=building_pos,
                        target_unit_id=defenders[0].id if defenders else None,
                    )
                )

        return intents

    # -- helpers --

    @staticmethod
    def _enemies_in_buildings(context: TacticalContext) -> list[Unit]:
        """Find enemy units inside or adjacent to enterable buildings."""
        result: list[Unit] = []
        for e in context.enemy_units:
            if not e.is_alive:
                continue
            pos = e.position.tile_coord
            game_map = context.game_map
            if not game_map.is_within_bounds(pos):
                continue
            terrain = game_map.get_terrain(pos)
            if terrain in _BUILDING_TERRAIN:
                result.append(e)
                continue
            # Also check adjacent tiles for enemies near buildings
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    adj = TileCoord(pos.x + dx, pos.y + dy)
                    if game_map.is_within_bounds(adj):
                        adj_terrain = game_map.get_terrain(adj)
                        if adj_terrain in _BUILDING_TERRAIN:
                            result.append(e)
                            break
                else:
                    continue
                break
        return result

    @staticmethod
    def _available_infantry(context: TacticalContext) -> list[Unit]:
        """Find friendly infantry available for clearing operations."""
        return [
            u
            for u in context.friendly_units
            if u.is_alive
            and u.can_act
            and u.unit_type in _INFANTRY_TYPES
            and u.morale.is_combat_effective
        ]

    @staticmethod
    def _find_clearing_team(
        available: list[Unit],
        building_pos: TileCoord,
        assigned: set[str],
        context: TacticalContext,
    ) -> list[Unit] | None:
        """Find the nearest pair of unassigned infantry for clearing."""
        candidates = [u for u in available if u.id not in assigned]
        if len(candidates) < MIN_CLEARING_UNITS:
            return None

        # Sort by distance to building
        candidates.sort(key=lambda u: u.position.tile_coord.chebyshev_distance(building_pos))
        return candidates[:MIN_CLEARING_UNITS]

    @staticmethod
    def find_adjacent_approach_pos(
        building_pos: TileCoord,
        unit_pos: TileCoord,
        game_map: GameMap,
    ) -> TileCoord | None:
        """Find the best adjacent tile to approach a building from.

        Returns the passable tile adjacent to the building that is
        closest to the unit's current position.
        """
        best: TileCoord | None = None
        best_dist = float("inf")

        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                adj = TileCoord(building_pos.x + dx, building_pos.y + dy)
                if not game_map.is_within_bounds(adj):
                    continue
                if not game_map.is_passable(adj):
                    continue
                dist = unit_pos.chebyshev_distance(adj)
                if dist < best_dist:
                    best_dist = dist
                    best = adj

        return best

    @staticmethod
    def apply_grenade_effects(
        building_pos: TileCoord,
        game_map: GameMap,
        units_in_building: list[Unit],
    ) -> list[dict]:
        """Apply grenade effects to all units in a building.

        Grenade in building: 2x damage, all occupants hit.
        Returns list of effect dicts for event publishing.
        """
        effects: list[dict] = []
        for unit in units_in_building:
            if not unit.is_alive:
                continue
            damage = unit.take_damage(GRENADE_BUILDING_DAMAGE)
            # Apply heavy suppression from grenade
            combat_state = getattr(unit, "combat_state", None)
            if combat_state is not None:
                suppression = getattr(combat_state, "suppression", None)
                if suppression is not None:
                    suppression.apply_suppression(40.0)

            effects.append(
                {
                    "unit_id": unit.id,
                    "damage": damage,
                    "source": "grenade_building",
                    "building_pos": (building_pos.x, building_pos.y),
                }
            )
        return effects

    @staticmethod
    def apply_surprise_bonus(attacker: Unit) -> None:
        """Apply surprise accuracy bonus to an attacking unit after breach."""
        combat_state = getattr(attacker, "combat_state", None)
        if combat_state is not None:
            concealment = getattr(combat_state, "concealment", None)
            if concealment is not None:
                concealment.special_bonus += SURPRISE_ACCURACY_BONUS

    @staticmethod
    def apply_defender_penalty(defender: Unit) -> None:
        """Apply accuracy penalty to a defender when building is assaulted."""
        combat_state = getattr(defender, "combat_state", None)
        if combat_state is not None:
            suppression = getattr(combat_state, "suppression", None)
            if suppression is not None:
                suppression.apply_suppression(10.0)
