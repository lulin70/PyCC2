"""AmbushAI — General Infantry Ambush Tactics

Implements CC2-authentic infantry ambush behavior:

  1. Identify friendly infantry units in concealed positions
     (woods / buildings / trenches with sufficient concealment)
  2. Hold fire while enemy units approach within effective range
  3. Trigger a coordinated ambush (concentrated fire) once the enemy
     is inside the kill zone

Evaluation heuristic:
  - Returns 0.0 if no friendly infantry units exist
  - Returns 0.0 if no enemy units are within the approach radius
  - Higher score when enemies are approaching (within 15 tiles)
  - Higher score when friendly units are well concealed
  - Night time adds a +0.2 bonus (darkness favors ambushes)
  - Returns the highest score across all candidate units
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycc2.domain.ai.night_stealth_ai import NIGHT_TIMES
from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.ai.tactical_ai import TacticalAIBase, TacticalContext
from pycc2.domain.entities.unit import UnitType
from pycc2.domain.systems.environment import TimeOfDay

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_AMBUSH_INFANTRY_TYPES: set[UnitType] = {
    UnitType.INFANTRY_SQUAD,
    UnitType.MACHINE_GUN_SQUAD,
    UnitType.SNIPER_TEAM,
}

# Minimum concealment required to qualify as an ambush position
# (woods=0.50, building_enterable=0.70, bunker=0.80, etc.)
_MIN_CONCEALMENT: float = 0.4

# Enemy approach radius (tiles) within which ambush becomes relevant
_APPROACH_RADIUS: int = 15

# Distance (tiles) inside which the ambush is triggered (concentrated fire)
_BREAK_AMBUSH_RADIUS: int = 8

# Night time bonus added to the evaluation score (per spec)
_NIGHT_SCORE_BONUS: float = 0.20

# Priority weighting for unit selection (higher = processed first)
_UNIT_PRIORITY: dict[UnitType, int] = {
    UnitType.SNIPER_TEAM: 3,
    UnitType.MACHINE_GUN_SQUAD: 2,
    UnitType.INFANTRY_SQUAD: 1,
}


# ---------------------------------------------------------------------------
# AmbushAI
# ---------------------------------------------------------------------------


class AmbushAI(TacticalAIBase):
    """General infantry ambush AI — sets up concealed positions and triggers coordinated fire."""

    # -- evaluate -----------------------------------------------------------

    def evaluate(self, context: TacticalContext) -> float:
        """Return ambush priority based on infantry concealment and enemy proximity."""
        candidates = self._find_ambush_candidates(context)
        if not candidates:
            return 0.0

        is_night = self._is_night(context)
        best_score = 0.0

        for unit in candidates:
            nearest_enemy, dist = self._nearest_enemy(unit, context)
            if nearest_enemy is None or dist > _APPROACH_RADIUS:
                continue

            proximity = 1.0 - (dist / float(_APPROACH_RADIUS))
            concealment = self._concealment_at(unit, context)
            if concealment < _MIN_CONCEALMENT:
                continue

            unit_score = 0.5 * proximity + 0.3 * concealment
            if is_night:
                unit_score += _NIGHT_SCORE_BONUS

            unit_score = max(0.0, min(unit_score, 1.0))
            if unit_score > best_score:
                best_score = unit_score

        return best_score

    # -- execute ------------------------------------------------------------

    def execute(self, context: TacticalContext) -> list[TacticIntent]:
        """Generate ambush intents for infantry units engaging approaching enemies."""
        candidates = self._find_ambush_candidates(context)
        if not candidates:
            return []

        # Priority order: sniper > MG > infantry
        candidates.sort(
            key=lambda u: _UNIT_PRIORITY.get(u.unit_type, 0),
            reverse=True,
        )

        intents: list[TacticIntent] = []
        for unit in candidates:
            if not unit.can_act:
                continue

            nearest_enemy, dist = self._nearest_enemy(unit, context)
            if nearest_enemy is None:
                # No enemy visible — hold position and stay concealed
                intents.append(
                    TacticIntent(
                        unit_id=unit.id,
                        tactic_type=TacticType.SET_AMBUSH,
                        priority=7,
                        target_position=unit.position.tile_coord,
                    )
                )
                continue

            if dist <= _BREAK_AMBUSH_RADIUS:
                # Enemy inside the kill zone — trigger the ambush
                intents.append(
                    TacticIntent(
                        unit_id=unit.id,
                        tactic_type=TacticType.BREAK_AMBUSH,
                        priority=9,
                        target_unit_id=nearest_enemy.id,
                        target_position=nearest_enemy.position.tile_coord,
                    )
                )
            else:
                # Enemy approaching but still outside fire range — hold and wait
                intents.append(
                    TacticIntent(
                        unit_id=unit.id,
                        tactic_type=TacticType.SET_AMBUSH,
                        priority=7,
                        target_position=unit.position.tile_coord,
                    )
                )

        return intents

    # -- helper methods -----------------------------------------------------

    @staticmethod
    def _find_ambush_candidates(context: TacticalContext) -> list[Unit]:
        """Find friendly infantry units eligible for ambush duty."""
        return [
            u
            for u in context.friendly_units
            if u.is_alive
            and u.can_act
            and u.unit_type in _AMBUSH_INFANTRY_TYPES
        ]

    @staticmethod
    def _nearest_enemy(
        unit: Unit, context: TacticalContext
    ) -> tuple[Unit | None, int]:
        """Return the nearest living enemy and its chebyshev distance."""
        best: Unit | None = None
        best_dist = int(1 << 30)
        for enemy in context.enemy_units:
            if not enemy.is_alive:
                continue
            dist = unit.position.tile_coord.chebyshev_distance(
                enemy.position.tile_coord
            )
            if dist < best_dist:
                best_dist = dist
                best = enemy
        return best, best_dist

    @staticmethod
    def _concealment_at(unit: Unit, context: TacticalContext) -> float:
        """Return the terrain concealment modifier at the unit's position."""
        pos = unit.position.tile_coord
        game_map = context.game_map
        if not game_map.is_within_bounds(pos):
            return 0.0
        terrain = game_map.get_terrain(pos)
        return float(terrain.concealment_modifier)

    @staticmethod
    def _is_night(context: TacticalContext) -> bool:
        """Return True when the current time of day is night/dawn/dusk.

        Reads ``time_of_day`` from any unit blackboard (matching the
        :class:`NightStealthAI` convention); defaults to day when absent.
        """
        for bb in context.blackboards.values():
            tod = bb.get("time_of_day")
            if tod is not None and isinstance(tod, TimeOfDay):
                return tod in NIGHT_TIMES
        return False
