"""
Trench/Foxhole Digging — CC2-Authentic Defensive Behavior

Infantry can dig temporary defensive positions when holding ground.
This mirrors the real WWII practice where soldiers would entrench
at every halt, creating the characteristic battlefield landscape.

Components:
  1. TrenchDiggingSystem  — Manages digging progress and trench creation
  2. TrenchDiggingAI      — Evaluates when units should dig and issues orders

Digging conditions (CC2-authentic):
  - Unit is in DEFEND or HOLD_POSITION state
  - Unit has been stationary for 30+ ticks
  - Terrain is diggable (OPEN, GRASS, ROUGH — not WATER, ROAD, BUILDING)
  - Unit is not suppressed
  - Unit is not already in trench

Digging process:
  - Takes 90 ticks (~15 seconds at 6 ticks/sec)
  - Progress tracked per unit (0-90)
  - Moving or taking fire resets progress
  - On completion: TRENCH_SECTION decoration added at unit's position

Trench effects (from enhanced_tile.py DecorationType.TRENCH_SECTION):
  - Cover bonus: +3
  - Concealment bonus: +0.4
  - Counts as hard cover for suppression recovery
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.ai.tactical_ai import TacticalAIBase, TacticalContext
from pycc2.domain.entities.unit import UnitType
from pycc2.domain.systems.enhanced_tile import DecorationType
from pycc2.domain.value_objects.terrain_type import TerrainType
from pycc2.domain.value_objects.tile_coord import TileCoord

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DIGGABLE_TERRAIN: set[TerrainType] = {
    TerrainType.OPEN,
    TerrainType.GRASS,
    TerrainType.ROUGH,
}

_INFANTRY_TYPES: set[UnitType] = {
    UnitType.INFANTRY_SQUAD,
    UnitType.COMMANDER,
    UnitType.SNIPER_TEAM,
    UnitType.MEDIC_TEAM,
    UnitType.MACHINE_GUN_SQUAD,
}

DIG_DURATION: int = 90  # Ticks to complete trench
STATIONARY_THRESHOLD: int = 30  # Ticks before digging can start


# ---------------------------------------------------------------------------
# TrenchDiggingSystem
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class DigProgress:
    """Tracks digging progress for a single unit."""

    unit_id: str
    progress: int = 0  # 0 to DIG_DURATION
    position: TileCoord | None = None  # Position where digging started
    interrupted: bool = False

    @property
    def is_complete(self) -> bool:
        return self.progress >= DIG_DURATION

    @property
    def progress_ratio(self) -> float:
        return min(1.0, self.progress / DIG_DURATION)


class TrenchDiggingSystem:
    """Manages the trench digging process for all units.

    Responsibilities:
      - Track digging progress per unit
      - Validate digging conditions each tick
      - Create trench decorations on completion
      - Handle interruption (movement, taking fire)
    """

    def __init__(self) -> None:
        self._progress: dict[str, DigProgress] = {}

    @property
    def active_digs(self) -> list[DigProgress]:
        return list(self._progress.values())

    def can_dig(self, unit: Unit, game_map: GameMap) -> bool:
        """Check if a unit meets all conditions for digging."""
        # Must be alive and able to act
        if not unit.is_alive or not unit.can_act:
            return False

        # Must be infantry type
        if unit.unit_type not in _INFANTRY_TYPES:
            return False

        # Must not be suppressed
        combat_state = getattr(unit, "combat_state", None)
        if combat_state is not None:
            suppression = getattr(combat_state, "suppression", None)
            if suppression is not None:
                effect = suppression.get_current_effect()
                from pycc2.domain.systems.combat_mechanics_enhanced import SuppressionEffect

                if effect in (
                    SuppressionEffect.HEAVY,
                    SuppressionEffect.PINNED,
                    SuppressionEffect.PANIC,
                ):
                    return False

        # Must not already be in a trench
        pos = unit.position.tile_coord
        if self._is_in_trench(pos, game_map):
            return False

        # Terrain must be diggable
        terrain = game_map.get_terrain(pos)
        return terrain in _DIGGABLE_TERRAIN

    def start_digging(self, unit: Unit) -> bool:
        """Start the digging process for a unit."""
        if unit.id in self._progress:
            return False  # Already digging
        self._progress[unit.id] = DigProgress(
            unit_id=unit.id,
            position=unit.position.tile_coord,
        )
        logger.debug(f"Unit {unit.id} started digging trench")
        return True

    def tick(self, unit: Unit, game_map: GameMap) -> bool:
        """Advance digging progress for a unit by one tick.

        Returns True if the trench was completed this tick.
        """
        progress = self._progress.get(unit.id)
        if progress is None:
            return False

        # Check for interruption: unit moved away from dig position
        current_pos = unit.position.tile_coord
        if progress.position is not None and current_pos != progress.position:
            self.interrupt(unit.id)
            return False

        # Check for interruption: unit is taking fire (suppression increased)
        combat_state = getattr(unit, "combat_state", None)
        if combat_state is not None:
            suppression = getattr(combat_state, "suppression", None)
            if suppression is not None:
                from pycc2.domain.systems.combat_mechanics_enhanced import SuppressionEffect

                effect = suppression.get_current_effect()
                if effect in (
                    SuppressionEffect.HEAVY,
                    SuppressionEffect.PINNED,
                    SuppressionEffect.PANIC,
                ):
                    self.interrupt(unit.id)
                    return False

        # Advance progress
        progress.progress += 1

        if progress.is_complete:
            self._complete_trench(unit, game_map)
            self._progress.pop(unit.id, None)
            return True

        return False

    def interrupt(self, unit_id: str) -> None:
        """Interrupt digging progress for a unit (resets to 0)."""
        if unit_id in self._progress:
            self._progress.pop(unit_id)
            logger.debug(f"Unit {unit_id} digging interrupted")

    def get_progress(self, unit_id: str) -> DigProgress | None:
        """Get the current digging progress for a unit."""
        return self._progress.get(unit_id)

    def _complete_trench(self, unit: Unit, game_map: GameMap) -> None:
        """Create a TRENCH_SECTION decoration at the unit's position."""
        pos = unit.position.tile_coord

        # Add TRENCH_SECTION decoration via enhanced tile data
        enhanced = game_map.get_enhanced_tile(pos.x, pos.y)
        if enhanced is not None:
            decorations = enhanced.get("decorations", [])
            decorations.append(
                {
                    "type": DecorationType.TRENCH_SECTION.name,
                    "offset_x": 0.0,
                    "offset_y": 0.0,
                    "scale": 1.0,
                    "rotation": 0,
                    "variant": 0,
                }
            )
            enhanced["decorations"] = decorations

        # Also update unit's concealment to reflect trench cover
        combat_state = getattr(unit, "combat_state", None)
        if combat_state is not None:
            concealment = getattr(combat_state, "concealment", None)
            if concealment is not None:
                concealment.terrain_concealment = min(0.95, concealment.terrain_concealment + 0.4)

        logger.info(f"Unit {unit.id} completed trench at ({pos.x}, {pos.y})")

    @staticmethod
    def _is_in_trench(pos: TileCoord, game_map: GameMap) -> bool:
        """Check if a position already has a TRENCH_SECTION decoration."""
        enhanced = game_map.get_enhanced_tile(pos.x, pos.y)
        if enhanced is None:
            return False
        decorations = enhanced.get("decorations", [])
        return any(d.get("type") == DecorationType.TRENCH_SECTION.name for d in decorations)


# ---------------------------------------------------------------------------
# TrenchDiggingAI
# ---------------------------------------------------------------------------


class TrenchDiggingAI(TacticalAIBase):
    """Evaluate when infantry should dig trenches and issue DIG_TRENCH orders.

    CC2 behaviour: Infantry in defensive positions without existing cover
    will entrench given time. This is a low-priority background action
    that happens when units are not engaged in combat.

    Evaluation heuristic:
      - Higher score when units are in DEFEND/HOLD_POSITION with no cover
      - Higher score when units have been stationary longer
      - Lower score when enemies are nearby (combat takes priority)
      - Zero when no infantry in defensive positions
    """

    def evaluate(self, context: TacticalContext) -> float:
        candidates = self._dig_candidates(context)
        if not candidates:
            return 0.0

        # Base score from number of candidates
        candidate_ratio = min(len(candidates) / 4.0, 1.0)

        # Reduce score if enemies are close (combat priority)
        enemy_pressure = self._enemy_pressure(context)

        # Reduce score if most candidates already have cover
        no_cover_ratio = self._no_cover_ratio(context)

        score = 0.3 * candidate_ratio + 0.4 * no_cover_ratio - 0.3 * enemy_pressure
        return max(0.0, min(score, 1.0))

    def execute(self, context: TacticalContext) -> list[TacticIntent]:
        candidates = self._dig_candidates(context)
        if not candidates:
            return []

        intents: list[TacticIntent] = []
        for unit in candidates:
            # Only issue dig order if unit has been stationary long enough
            bb = context.blackboards.get(unit.id)
            stationary_ticks = 0
            if bb is not None:
                stationary_ticks = bb.get("stationary_ticks", 0)

            if stationary_ticks < STATIONARY_THRESHOLD:
                continue

            intents.append(
                TacticIntent(
                    unit_id=unit.id,
                    tactic_type=TacticType.DIG_TRENCH,
                    priority=3,  # Low priority — background action
                    target_position=unit.position.tile_coord,
                )
            )

        return intents

    # -- helpers --

    @staticmethod
    def _dig_candidates(context: TacticalContext) -> list[Unit]:
        """Find infantry units that could potentially dig."""
        return [
            u
            for u in context.friendly_units
            if u.is_alive
            and u.can_act
            and u.unit_type in _INFANTRY_TYPES
            and u.morale.is_combat_effective
        ]

    @staticmethod
    def _enemy_pressure(context: TacticalContext) -> float:
        """Measure how close enemy forces are (0.0 = far, 1.0 = very close)."""
        enemies = [e for e in context.enemy_units if e.is_alive]
        if not enemies:
            return 0.0
        friendlies = [u for u in context.friendly_units if u.is_alive]
        if not friendlies:
            return 1.0

        min_dist = float("inf")
        for f in friendlies[:5]:
            for e in enemies[:5]:
                d = f.position.tile_coord.chebyshev_distance(e.position.tile_coord)
                min_dist = min(min_dist, d)

        # Closer enemies = higher pressure
        if min_dist <= 5:
            return 1.0
        elif min_dist <= 10:
            return 0.5
        elif min_dist <= 20:
            return 0.2
        return 0.0

    @staticmethod
    def _no_cover_ratio(context: TacticalContext) -> float:
        """Ratio of friendly infantry in positions with no cover."""
        infantry = [
            u for u in context.friendly_units if u.is_alive and u.unit_type in _INFANTRY_TYPES
        ]
        if not infantry:
            return 0.0

        no_cover = 0
        for u in infantry:
            pos = u.position.tile_coord
            game_map = context.game_map
            if not game_map.is_within_bounds(pos):
                continue
            terrain = game_map.get_terrain(pos)
            if terrain.cover_bonus < 0.1:
                no_cover += 1

        return no_cover / len(infantry)
