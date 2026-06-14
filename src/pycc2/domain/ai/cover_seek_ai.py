"""
Cover Seeking AI — CC2-Authentic Suppressed Unit Behavior

When units are under heavy fire (suppression > threshold), they
automatically scan surrounding tiles to find the best available cover.
This mirrors real WWII behavior where soldiers would dive for cover when
pinned down.

Components:
  1. CoverSeekAI          — Evaluates when to seek cover and issues orders
  2. CoverScoringSystem   — Scores tiles based on distance/protection/concealment

CC2 Rules:
- Triggered when suppression > HEAVY (65+) or taking continuous fire
- Scans tiles within SEARCH_RADIUS (typically 5-8 tiles)
- Scores each tile using weighted formula:
    score = (cover_bonus * COVER_WEIGHT) +
            (concealment * CONCEAL_WEIGHT) -
            (distance * DISTANCE_PENALTY) +
            (not_in_los_bonus * LOS_BONUS)
- Picks highest-scoring tile that is passable and not occupied
- Issues MOVE order to best cover position
- Higher priority for units with low HP or already suppressed

Integration:
- Works with existing SuppressionState from combat_mechanics_enhanced.py
- Uses EnhancedTile.cover_bonus and .concealment properties
- Integrates with Lossystem to check if cover position is in enemy LOS
- Outputs TacticIntent.MOVE_TO_COVER for execution by TacticExecutor
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.ai.tactical_ai import TacticalAIBase, TacticalContext
from pycc2.domain.systems.combat_mechanics_enhanced import (
    SuppressionState,
)
from pycc2.domain.value_objects.tile_coord import TileCoord

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.systems.los_system import Lossystem


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# When to trigger cover seeking
SUPPRESSION_THRESHOLD: float = 65.0  # HEAVY suppression level
CONTINUOUS_FIRE_TICKS: int = 15  # Ticks of continuous fire before seeking

# Search parameters
SEARCH_RADIUS: int = 7  # Tiles to search around unit
MIN_SEARCH_RADIUS: int = 2  # Minimum radius (check close cover first)
MAX_CANDIDATES: int = 20  # Max tiles to evaluate (performance)

# Scoring weights (tuned for CC2-authentic behavior)
COVER_WEIGHT: float = 25.0  # Importance of cover bonus (-1 to +3)
CONCEAL_WEIGHT: float = 15.0  # Importance of concealment (0.0 to 0.95)
DISTANCE_PENALTY: float = 2.0  # Cost per tile distance
LOS_BONUS: float = 30.0  # Bonus for being out of enemy LOS
OCCUPIED_PENALTY: float = -100.0  # Penalty for occupied tiles
ENEMY_ADJACENT_PENALTY: float = -50.0  # Penalty for tiles next to enemies
MOVEMENT_COST_PENALTY: float = -10.0  # Penalty per 1.0 movement cost multiplier


# ---------------------------------------------------------------------------
# CoverCandidate
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class CoverCandidate:
    """A potential cover position with its evaluation score."""

    coord: TileCoord
    score: float
    cover_bonus: int
    concealment: float
    distance: float
    is_in_enemy_los: bool
    is_occupied: bool
    has_enemy_adjacent: bool
    movement_cost: float

    def __lt__(self, other: CoverCandidate) -> bool:
        return self.score < other.score


# ---------------------------------------------------------------------------
# CoverScoringSystem
# ---------------------------------------------------------------------------


class CoverScoringSystem:
    """
    Evaluates and scores potential cover positions.

    The scoring formula balances multiple tactical factors:
    1. Cover bonus (hard cover from terrain/decorations)
    2. Concealment (soft cover, hiding from view)
    3. Distance (closer is better - less exposure time)
    4. LOS status (out of enemy sight lines is ideal)
    5. Occupancy (cannot move to occupied tiles)
    6. Enemy proximity (avoid moving next to enemies)
    7. Movement cost (difficult terrain takes longer to reach)

    CC2 Authentic Behavior:
    - Soldiers prefer hard cover (walls, buildings, trenches) over soft
    - Will accept slightly worse cover if much closer
    - Strongly prefer positions where they can't be seen
    - Never move through/onto enemy-adjacent positions unless desperate
    """

    def __init__(
        self,
        los_system: Lossystem | None = None,
        game_map: GameMap | None = None,
    ) -> None:
        self._los = los_system
        self._map = game_map

    def find_best_cover(
        self,
        unit: Unit,
        enemy_units: list[Unit],
        friendly_units: list[Unit] | None = None,
        search_radius: int = SEARCH_RADIUS,
    ) -> CoverCandidate | None:
        """
        Find the best cover position for a suppressed unit.

        Args:
            unit: The suppressed unit seeking cover
            enemy_units: List of visible enemy units (for LOS checks)
            friendly_units: List of friendly units (to avoid blocking)
            search_radius: How far to search (tiles)

        Returns:
            Best CoverCandidate, or None if no valid cover found
        """
        if not self._map:
            logger.warning("CoverScoringSystem: No game_map configured")
            return None

        # Get candidates
        candidates = self._get_candidates(unit, enemy_units, friendly_units, search_radius)

        if not candidates:
            logger.debug(
                f"CoverSeek: No valid cover found for unit at ({unit.position_component.x}, {unit.position_component.y})"
            )
            return None

        # Sort by score descending and return best
        candidates.sort(reverse=True)
        best = candidates[0]

        logger.debug(
            f"CoverSeek: Best cover for unit at "
            f"({unit.position_component.x}, {unit.position_component.y}) -> "
            f"({best.coord.x}, {best.coord.y}) score={best.score:.1f}"
        )

        return best

    def _get_candidates(
        self,
        unit: Unit,
        enemy_units: list[Unit],
        friendly_units: list[Unit] | None,
        search_radius: int,
    ) -> list[CoverCandidate]:
        """Generate and score all candidate cover positions."""
        candidates: list[CoverCandidate] = []
        unit_x = int(unit.position_component.x)
        unit_y = int(unit.position_component.y)
        TileCoord(unit_x, unit_y)

        # Get occupied positions
        occupied: set[tuple[int, int]] = set()
        if friendly_units:
            for u in friendly_units:
                if u.is_alive and u != unit:
                    occupied.add((int(u.position_component.x), int(u.position_component.y)))

        # Get enemy positions for adjacency check
        enemy_positions: set[tuple[int, int]] = {
            (int(e.position_component.x), int(e.position_component.y))
            for e in enemy_units
            if e.is_alive
        }

        # Search in expanding rings (prefer closer cover)
        checked = 0
        for radius in range(MIN_SEARCH_RADIUS, search_radius + 1):
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    # Skip center (current position)
                    if dx == 0 and dy == 0:
                        continue

                    # Only check perimeter of current ring
                    if abs(dx) != radius and abs(dy) != radius:
                        continue

                    cx = unit_x + dx
                    cy = unit_y + dy

                    # Bounds check
                    if not self._map.is_valid_coord(cx, cy):
                        continue

                    coord = TileCoord(cx, cy)

                    # Check if occupied
                    is_occupied = (cx, cy) in occupied

                    # Get tile properties
                    tile = self._map.get_tile(coord)
                    if tile is None:
                        continue

                    # Calculate distance (Manhattan for performance, could use Euclidean)
                    distance = math.sqrt(dx * dx + dy * dy)

                    # Get cover and concealment values
                    cover_bonus = getattr(tile, "total_cover_bonus", 0)
                    concealment = getattr(tile, "total_concealment", 0.0)
                    movement_cost = getattr(tile, "effective_movement_cost", 1.0)

                    # Check if passable
                    if movement_cost >= 5.0:  # Impassable
                        continue

                    # Check enemy adjacency
                    has_enemy_adjacent = False
                    for ex, ey in enemy_positions:
                        if abs(ex - cx) <= 1 and abs(ey - cy) <= 1:
                            has_enemy_adjacent = True
                            break

                    # Check LOS status (expensive, so limit checks)
                    is_in_los = False
                    if self._los and enemy_units:
                        for enemy in enemy_units[:3]:  # Check up to 3 nearest enemies
                            can_see, _ = self._los.can_see(unit_pos=coord, target_unit=enemy)
                            if can_see:
                                is_in_los = True
                                break

                    # Score this candidate
                    score = self._score_tile(
                        cover_bonus=cover_bonus,
                        concealment=concealment,
                        distance=distance,
                        is_in_los=is_in_los,
                        is_occupied=is_occupied,
                        has_enemy_adjacent=has_enemy_adjacent,
                        movement_cost=movement_cost,
                    )

                    candidate = CoverCandidate(
                        coord=coord,
                        score=score,
                        cover_bonus=cover_bonus,
                        concealment=concealment,
                        distance=distance,
                        is_in_enemy_los=is_in_los,
                        is_occupied=is_occupied,
                        has_enemy_adjacent=has_enemy_adjacent,
                        movement_cost=movement_cost,
                    )
                    candidates.append(candidate)

                    checked += 1
                    if checked >= MAX_CANDIDATES:
                        return candidates

        return candidates

    def _score_tile(
        self,
        cover_bonus: int,
        concealment: float,
        distance: float,
        is_in_los: bool,
        is_occupied: bool,
        has_enemy_adjacent: bool,
        movement_cost: float,
    ) -> float:
        """
        Calculate score for a candidate tile.

        Formula:
            score = (cover * COVER_W) + (conc * CONC_W)
                   - (dist * DIST_PEN)
                   + (not_in_los * LOS_BONUS)
                   + (occ * OCC_PEN)
                   + (enemy_adj * ENEMY_ADJ_PEN)
                   + ((mov_cost - 1.0) * MOV_COST_PEN)
        """
        score = 0.0

        # Cover bonus (most important factor)
        score += cover_bonus * COVER_WEIGHT

        # Concealment (secondary factor)
        score += concealment * CONCEAL_WEIGHT * 100  # Scale to match cover weight

        # Distance penalty (closer is better)
        score -= distance * DISTANCE_PENALTY

        # LOS bonus (being hidden is very valuable)
        if not is_in_los:
            score += LOS_BONUS

        # Occupied penalty (cannot move there)
        if is_occupied:
            score += OCCUPIED_PENALTY

        # Enemy adjacent penalty (dangerous)
        if has_enemy_adjacent:
            score += ENEMY_ADJACENT_PENALTY

        # Movement cost penalty (slow terrain = more exposure)
        if movement_cost > 1.0:
            score += (movement_cost - 1.0) * MOVEMENT_COST_PENALTY

        return score


# ---------------------------------------------------------------------------
# CoverSeekAI
# ---------------------------------------------------------------------------


class CoverSeekAI(TacticalAIBase):
    """
    Evaluates when units should seek cover and generates move orders.

    Works in batch mode: evaluates all friendly units and generates
    MOVE_TO_COVER intents for suppressed units that would benefit
    from repositioning.

    Priority calculation (per unit):
    - Base priority depends on suppression level
    - Boosted by low HP ratio
    - Boosted by continuous fire (ticks under suppression)
    - Reduced if already in good cover
    - Reduced if currently moving (don't interrupt)

    CC2 Behavior:
    - Units under heavy fire will try to reach cover
    - Won't abandon defensive positions lightly
    - Prefers to keep facing toward enemy while moving
    - May abort if cover is too far or route is dangerous
    """

    SUPPRESSION_THRESHOLD: float = SUPPRESSION_THRESHOLD
    CONTINUOUS_FIRE_THRESHOLD: int = CONTINUOUS_FIRE_TICKS
    GOOD_COVER_THRESHOLD: int = 2  # Already have this much cover = lower priority
    MAX_MOVE_DISTANCE: float = SEARCH_RADIUS * 0.7  # Don't seek too far

    def __init__(self, scoring_system: CoverScoringSystem | None = None) -> None:
        super().__init__()
        self._scorer = scoring_system or CoverScoringSystem()

    @property
    def scorer(self) -> CoverScoringSystem:
        return self._scorer

    def evaluate(self, context: TacticalContext) -> float:
        """
        Evaluate if ANY unit in the force should seek cover.

        Returns priority 0.0-1.0 based on most urgent unit's need.
        """
        max_priority = 0.0

        for unit in context.friendly_units:
            if not unit.is_alive:
                continue

            unit_priority = self._evaluate_unit(unit, context)
            max_priority = max(max_priority, unit_priority)

        return max_priority

    def _evaluate_unit(self, unit: Unit, context: TacticalContext) -> float:
        """Evaluate single unit's need for cover."""
        # Must be combat-effective
        if not getattr(unit, "is_combat_effective", True):
            return 0.0

        # Check suppression state
        suppression_state = self._get_suppression_state(unit)
        if suppression_state is None:
            return 0.0

        current_suppression = suppression_state.current_suppression

        # Base priority from suppression level
        if current_suppression < self.SUPPRESSION_THRESHOLD:
            return 0.0

        # Calculate base priority (0.3 to 0.9 based on suppression)
        sup_ratio = (current_suppression - self.SUPPRESSION_THRESHOLD) / (
            100.0 - self.SUPPRESSION_THRESHOLD
        )
        base_priority = 0.3 + 0.6 * sup_ratio

        # Boost for low HP
        hp_ratio = self._get_hp_ratio(unit)
        if hp_ratio < 0.5:
            base_priority += 0.15 * (0.5 - hp_ratio) / 0.5

        # Boost for continuous fire
        turns_since_hit = getattr(suppression_state, "turns_since_last_hit", 0)
        if turns_since_hit < self.CONTINUOUS_FIRE_THRESHOLD:
            fire_intensity = 1.0 - (turns_since_hit / self.CONTINUOUS_FIRE_THRESHOLD)
            base_priority += 0.1 * fire_intensity

        # Reduce if already in good cover
        current_cover = self._get_current_cover(unit, context)
        if current_cover >= self.GOOD_COVER_THRESHOLD:
            base_priority -= 0.2

        # Reduce if currently moving (don't interrupt mid-move)
        if self._is_moving(unit):
            base_priority -= 0.3

        return max(0.0, min(1.0, base_priority))

    def execute(self, context: TacticalContext) -> list[TacticIntent]:
        """Generate MOVE_TO_COVER intents for all suppressed units needing cover."""
        intents: list[TacticIntent] = []

        for unit in context.friendly_units:
            if not unit.is_alive:
                continue

            unit_priority = self._evaluate_unit(unit, context)
            if unit_priority <= 0:
                continue

            best_cover = self._scorer.find_best_cover(
                unit=unit,
                enemy_units=context.enemy_units,
                friendly_units=context.friendly_units,
            )

            if best_cover is None:
                continue

            # Don't move too far
            if best_cover.distance > self.MAX_MOVE_DISTANCE:
                continue

            # Create move intent
            intent = TacticIntent(
                tactic_type=TacticType.MOVE_TO,
                unit_id=unit.id,
                target_position=best_cover.coord,
                priority=int(unit_priority * 10),
            )
            intents.append(intent)

            logger.info(
                f"CoverSeek: Unit {unit.id} at "
                f"({unit.position_component.x}, {unit.position_component.y}) "
                f"seeking cover at ({best_cover.coord.x}, {best_cover.coord.y}) "
                f"(score={best_cover.score:.1f}, cover={best_cover.cover_bonus})"
            )

        return intents

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def _get_suppression_state(self, unit: Unit) -> SuppressionState | None:
        """Extract suppression state from unit if available."""
        # Try to get from component or attribute
        if hasattr(unit, "suppression_state"):
            return unit.suppression_state
        if hasattr(unit, "_suppression_state"):
            return unit._suppression_state
        return None

    def _get_hp_ratio(self, unit: Unit) -> float:
        """Get current HP as ratio of max HP."""
        if hasattr(unit, "health_component"):
            hc = unit.health_component
            max_hp = getattr(hc, "max_hp", None)
            current_hp = getattr(hc, "current_hp", None)
            if max_hp is not None and current_hp is not None:
                try:
                    if max_hp > 0:
                        return current_hp / max_hp
                except TypeError:
                    pass  # Mock objects or incompatible types
        return 1.0

    def _get_current_cover(self, unit: Unit, context: TacticalContext) -> int:
        """Get cover value at unit's current position."""
        if not self._scorer._map:
            return 0

        pos = TileCoord(
            int(unit.position_component.x),
            int(unit.position_component.y),
        )
        tile = self._scorer._map.get_tile(pos)
        if tile:
            return getattr(tile, "total_cover_bonus", 0)
        return 0

    def _is_moving(self, unit: Unit) -> bool:
        """Check if unit is currently moving."""
        state = getattr(unit, "state", None)
        if state is not None:
            return str(state).upper() in ("MOVING", "SPRINTING")
        return False
