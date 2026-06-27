"""Night Stealth AI — CC2-Authentic Night Operations Behavior

AI actively uses darkness for stealth operations.  In CC2,
night missions dramatically change unit behavior — troops move
more cautiously, prefer concealment, and avoid firing unless
necessary to avoid revealing their position.

Rules:
  - Only active during NIGHT/DAWN/DUSK time_of_day
  - Evaluate: score based on time of day + mission type
  - Night behaviors:
    - Prefer SNEAK movement over MOVE_FAST (reduced noise)
    - Avoid firing unless necessary (firing reveals position)
    - Use darkness to reposition closer to VLs
    - Ambush setup: units in HIDE state get +30% detection range bonus at night
    - Night movement speed reduced by 20% (careful movement)
    - Units avoid roads at night (prefer cover routes)
  - Integration: modify existing behavior trees to check time_of_day
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.ai.tactical_ai import TacticalAIBase, TacticalContext
from pycc2.domain.entities.unit import UnitType
from pycc2.domain.systems.environment import TimeOfDay
from pycc2.domain.value_objects.tile_coord import TileCoord

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NIGHT_TIMES: set[TimeOfDay] = {TimeOfDay.NIGHT, TimeOfDay.DAWN, TimeOfDay.DUSK}

# Night concealment bonus for HIDE/ambush state
NIGHT_AMBUSH_DETECTION_BONUS: float = 0.30

# Night movement speed reduction
NIGHT_SPEED_PENALTY: float = 0.20

# Terrain types to avoid at night (roads expose movement)
_ROAD_TERRAIN_TYPES: set[str] = {"road", "bridge", "path"}

# Terrain types preferred at night (cover/concealment)
_COVER_TERRAIN_TYPES: set[str] = {"woods", "hedge", "building_enterable", "crater", "rough"}


# ---------------------------------------------------------------------------
# NightStealthAI
# ---------------------------------------------------------------------------


class NightStealthAI(TacticalAIBase):
    """Tactical AI for night stealth operations.

    Only active during NIGHT/DAWN/DUSK.  Modifies unit behavior to
    prioritize stealth, concealment, and ambush tactics.

    Evaluation heuristic:
      - 0.0 during DAY
      - Higher score during NIGHT (0.7), DAWN/DUSK (0.5)
      - Boosted when VLs are nearby (opportunity to infiltrate)
      - Reduced when enemies are very close (combat takes priority)

    Execution:
      - Units prefer SNEAK movement (use MOVE_TO with stealth)
      - Units avoid firing unless engaged
      - Units reposition toward VLs using cover routes
      - Units in HIDE state get night ambush bonus
      - Units avoid roads at night
    """

    def __init__(self) -> None:
        self._logger = logging.getLogger("pycc2.ai.night_stealth")

    # ------------------------------------------------------------------
    # TacticalAIBase interface
    # ------------------------------------------------------------------

    def evaluate(self, context: TacticalContext) -> float:
        """Return a priority score in [0.0, 1.0].

        Score is driven by:
          - Time of day (0.0 during day, higher at night)
          - VL proximity (opportunity to infiltrate)
          - Enemy distance (closer enemies reduce stealth priority)
        """
        time_of_day = self._get_time_of_day(context)
        if time_of_day not in NIGHT_TIMES:
            return 0.0

        # Base score by time of day
        base = 0.7 if time_of_day == TimeOfDay.NIGHT else 0.5

        # Boost for nearby VLs (infiltration opportunity)
        vl_boost = 0.0
        if context.vl_positions:
            friendly_faction = (
                context.friendly_units[0].faction.name if context.friendly_units else None
            )
            uncontrolled_vls = [
                v for v in context.vl_positions if v[1] is None or v[1] != friendly_faction
            ]
            if uncontrolled_vls:
                vl_boost = 0.15

        # Reduce if enemies are very close (combat takes priority)
        enemy_penalty = 0.0
        for unit in context.friendly_units:
            if not unit.is_alive:
                continue
            for enemy in context.enemy_units:
                if not enemy.is_alive:
                    continue
                dist = unit.position.tile_coord.chebyshev_distance(enemy.position.tile_coord)
                if dist <= 3:
                    enemy_penalty = 0.3
                    break
            if enemy_penalty > 0:
                break

        score = base + vl_boost - enemy_penalty
        return max(0.0, min(score, 1.0))

    def execute(self, context: TacticalContext) -> list[TacticIntent]:
        """Return stealth-oriented intents for units at night.

        For each available unit:
          1. If near an uncontrolled VL, move toward it using cover routes
          2. If in open terrain, move to nearest cover
          3. If on a road, move off it to cover
          4. If enemy is close, set up ambush (HOLD_POSITION with stealth)
          5. Avoid issuing ATTACK intents unless absolutely necessary
        """
        time_of_day = self._get_time_of_day(context)
        if time_of_day not in NIGHT_TIMES:
            return []

        available = self._available_units(context)
        if not available:
            return []

        intents: list[TacticIntent] = []
        assigned: set[str] = set()

        friendly_faction = (
            context.friendly_units[0].faction.name if context.friendly_units else None
        )

        # Find uncontrolled VLs as infiltration targets
        uncontrolled_vls = [
            v for v in context.vl_positions if v[1] is None or v[1] != friendly_faction
        ]

        for unit in available:
            if unit.id in assigned:
                continue

            unit_pos = unit.position.tile_coord

            # Priority 1: Move off roads at night
            if self._is_on_road(unit, context):
                cover_pos = self._find_nearby_cover(unit, context)
                if cover_pos is not None:
                    assigned.add(unit.id)
                    intents.append(
                        TacticIntent(
                            unit_id=unit.id,
                            tactic_type=TacticType.MOVE_TO,
                            priority=7,
                            target_position=cover_pos,
                        )
                    )
                    continue

            # Priority 2: If in open terrain, seek cover
            if self._is_in_open(unit, context):
                cover_pos = self._find_nearby_cover(unit, context)
                if cover_pos is not None:
                    assigned.add(unit.id)
                    intents.append(
                        TacticIntent(
                            unit_id=unit.id,
                            tactic_type=TacticType.TAKE_COVER,
                            priority=6,
                            target_position=cover_pos,
                        )
                    )
                    continue

            # Priority 3: Infiltrate toward uncontrolled VLs
            if uncontrolled_vls:
                nearest_vl = min(
                    uncontrolled_vls,
                    key=lambda v: unit_pos.chebyshev_distance(v[0]),
                )
                vl_pos = nearest_vl[0]
                dist = unit_pos.chebyshev_distance(vl_pos)
                if dist > 3:
                    # Use cover route toward VL
                    cover_route_dest = self._find_cover_route_toward(unit, vl_pos, context)
                    if cover_route_dest is not None:
                        assigned.add(unit.id)
                        intents.append(
                            TacticIntent(
                                unit_id=unit.id,
                                tactic_type=TacticType.MOVE_TO,
                                priority=5,
                                target_position=cover_route_dest,
                            )
                        )
                        continue

            # Priority 4: Set up ambush if enemy is nearby
            nearby_enemies = [
                e
                for e in context.enemy_units
                if e.is_alive and unit_pos.chebyshev_distance(e.position.tile_coord) <= 8
            ]
            if nearby_enemies and self._has_cover(unit, context):
                assigned.add(unit.id)
                intents.append(
                    TacticIntent(
                        unit_id=unit.id,
                        tactic_type=TacticType.HOLD_POSITION,
                        priority=4,
                        target_position=unit_pos,
                    )
                )
                continue

        return intents

    # ------------------------------------------------------------------
    # Night-specific modifiers
    # ------------------------------------------------------------------

    @staticmethod
    def get_night_speed_modifier(time_of_day: TimeOfDay) -> float:
        """Return movement speed modifier for night conditions.

        Returns 0.8 (20% reduction) during night, 1.0 otherwise.
        """
        if time_of_day in NIGHT_TIMES:
            return 1.0 - NIGHT_SPEED_PENALTY
        return 1.0

    @staticmethod
    def get_night_ambush_bonus(time_of_day: TimeOfDay) -> float:
        """Return detection range bonus for units in ambush at night.

        Returns 0.30 at night/dawn/dusk, 0.0 during day.
        """
        if time_of_day in NIGHT_TIMES:
            return NIGHT_AMBUSH_DETECTION_BONUS
        return 0.0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _available_units(context: TacticalContext) -> list[Unit]:
        """Return friendly units available for night stealth operations."""
        return [
            u
            for u in context.friendly_units
            if u.is_alive
            and u.can_act
            and u.morale.is_combat_effective
            and u.unit_type not in (UnitType.TANK,)  # Tanks don't stealth
        ]

    @staticmethod
    def _get_time_of_day(context: TacticalContext) -> TimeOfDay:
        """Extract time_of_day from the tactical context.

        Checks the blackboard for environment state, defaults to DAY.
        """
        # Try to get from any unit's blackboard
        for bb in context.blackboards.values():
            tod = bb.get("time_of_day")
            if tod is not None and isinstance(tod, TimeOfDay):
                return tod
        # Default to DAY if no time info available
        return TimeOfDay.DAY

    @staticmethod
    def _is_on_road(unit: Unit, context: TacticalContext) -> bool:
        """Check if a unit is currently on road terrain."""
        pos = unit.position.tile_coord
        game_map = context.game_map
        if not game_map.is_within_bounds(pos):
            return False
        terrain = game_map.get_terrain(pos)
        if terrain is None:
            return False
        terrain_type = getattr(terrain, "terrain_type", "")
        return terrain_type in _ROAD_TERRAIN_TYPES

    @staticmethod
    def _is_in_open(unit: Unit, context: TacticalContext) -> bool:
        """Check if a unit is in open terrain with no cover."""
        return float(unit.concealment_level) < 0.1

    @staticmethod
    def _has_cover(unit: Unit, context: TacticalContext) -> bool:
        """Check if a unit has cover at its current position."""
        return float(unit.concealment_level) >= 0.2

    @staticmethod
    def _find_nearby_cover(unit: Unit, context: TacticalContext) -> TileCoord | None:
        """Find a nearby position with cover/concealment.

        Prefers positions with higher concealment that are close to
        the unit.  Avoids roads at night.
        """
        pos = unit.position.tile_coord
        game_map = context.game_map

        best: TileCoord | None = None
        best_score = -1.0

        for dy in range(-5, 6):
            for dx in range(-5, 6):
                if dx == 0 and dy == 0:
                    continue
                candidate = TileCoord(pos.x + dx, pos.y + dy)
                if not game_map.is_within_bounds(candidate):
                    continue
                if not game_map.is_passable(candidate):
                    continue

                terrain = game_map.get_terrain(candidate)
                if terrain is None:
                    continue

                # Avoid roads at night
                terrain_type = getattr(terrain, "terrain_type", "")
                if terrain_type in _ROAD_TERRAIN_TYPES:
                    continue

                concealment = getattr(terrain, "concealment_modifier", 0.0)
                cover = getattr(terrain, "cover_modifier", 0.0)

                if concealment < 0.1:
                    continue

                dist = abs(dx) + abs(dy)
                score = concealment * 0.5 + cover * 0.3 - dist * 0.05

                if score > best_score:
                    best_score = score
                    best = candidate

        return best

    @staticmethod
    def _find_cover_route_toward(
        unit: Unit,
        target: TileCoord,
        context: TacticalContext,
    ) -> TileCoord | None:
        """Find a waypoint toward *target* that uses cover routes.

        Instead of moving directly toward the target (which may cross
        open terrain), find an intermediate position that offers
        concealment while progressing toward the target.
        """
        pos = unit.position.tile_coord
        game_map = context.game_map

        # Direction toward target
        dx = target.x - pos.x
        dy = target.y - pos.y
        dist = max(abs(dx), abs(dy))
        if dist == 0:
            return None

        # Step size: advance 3-5 tiles
        step = min(5, max(3, dist // 3))
        ndx = dx / dist
        ndy = dy / dist

        # Generate candidates: direct + perpendicular offsets
        candidates = []

        # Direct path
        direct = TileCoord(
            int(pos.x + ndx * step),
            int(pos.y + ndy * step),
        )
        candidates.append(direct)

        # Perpendicular offsets (avoid open terrain)
        perp_x = -ndy
        perp_y = ndx
        for offset in (2, -2):
            offset_pos = TileCoord(
                int(pos.x + ndx * step + perp_x * offset),
                int(pos.y + ndy * step + perp_y * offset),
            )
            candidates.append(offset_pos)

        # Score each candidate: prefer cover, avoid roads
        best: TileCoord | None = None
        best_score = -1.0

        for candidate in candidates:
            if not game_map.is_within_bounds(candidate):
                continue
            if not game_map.is_passable(candidate):
                continue

            terrain = game_map.get_terrain(candidate)
            if terrain is None:
                continue

            # Avoid roads at night
            terrain_type = getattr(terrain, "terrain_type", "")
            if terrain_type in _ROAD_TERRAIN_TYPES:
                continue

            concealment = getattr(terrain, "concealment_modifier", 0.0)
            cover = getattr(terrain, "cover_modifier", 0.0)

            # Progress toward target
            current_dist = pos.chebyshev_distance(target)
            new_dist = candidate.chebyshev_distance(target)
            progress = current_dist - new_dist

            score = concealment * 0.4 + cover * 0.3 + progress * 0.1

            if score > best_score:
                best_score = score
                best = candidate

        return best
