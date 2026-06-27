"""Surrender/Capture System — CC2-Authentic Unit Surrender Behavior

Implements the P0-priority AI behavior for unit surrender, a critical
element of CC2 fidelity.  At Arnhem, British paras surrendered en masse
after running out of ammunition — this system models that dynamic.

Surrender conditions (ALL must be met):
  - Ammo ratio < 0.05 (virtually out of ammo)
  - Morale < 15 (near breaking point)
  - No friendly units within 8 tiles (isolated)
  - Enemy units within 5 tiles (threat is immediate)
  - Not already surrendered

Surrender probability per tick:
  - Base: 5%
  - +10% if surrounded (enemies on 2+ sides)
  - +15% if officer is dead
  - -10% if veteran/elite experience
  - -5% per nearby friendly unit (even beyond 8 tiles)

When surrendered:
  - Unit state changes to SURRENDERED
  - Unit drops all weapons and ammo
  - Unit becomes non-combatant (cannot be targeted, cannot act)
  - Creates a FallenUnitCache entry (weapons/ammo available for pickup)

Enemy AI can "accept surrender" — unit moves toward nearest enemy unit.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.ai.tactical_ai import TacticalAIBase, TacticalContext
from pycc2.domain.entities.unit import UnitState
from pycc2.domain.value_objects.tile_coord import TileCoord

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AMMO_RATIO_THRESHOLD: float = 0.05
MORALE_THRESHOLD: int = 15
ISOLATION_RADIUS: int = 8
THREAT_RADIUS: int = 5
BASE_SURRENDER_PROBABILITY: float = 0.05
SURROUNDED_BONUS: float = 0.10
OFFICER_DEAD_BONUS: float = 0.15
VETERAN_ELITE_PENALTY: float = 0.10
NEARBY_FRIENDLY_PENALTY: float = 0.05
MORALE_EVENT_RADIUS: int = 10
MORALE_EVENT_DELTA: int = -5


# ---------------------------------------------------------------------------
# FallenUnitCache — weapons/ammo dropped by surrendered units
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class FallenUnitCache:
    """Weapons and ammo dropped by a surrendered or dead unit.

    Other units can pick up these resources during gameplay.
    """

    unit_id: str
    position_tile: tuple[int, int]
    weapon_id: str
    ammo_count: int
    is_captured_weapon: bool = False
    tick_created: int = 0


# ---------------------------------------------------------------------------
# SurrenderSystem
# ---------------------------------------------------------------------------


class SurrenderSystem:
    """Evaluate and process unit surrender each tick.

    Usage::

        system = SurrenderSystem()
        for unit in alive_units:
            system.evaluate_tick(unit, all_units, current_tick)
    """

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()
        self._fallen_caches: list[FallenUnitCache] = []

    @property
    def fallen_caches(self) -> list[FallenUnitCache]:
        return list(self._fallen_caches)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate_tick(
        self,
        unit: Unit,
        all_units: list[Unit],
        current_tick: int,
    ) -> bool:
        """Check if *unit* should surrender this tick.

        Returns True if the unit surrendered.
        """
        if not self._meets_conditions(unit, all_units):
            return False

        probability = self._calculate_probability(unit, all_units)
        if self._rng.random() < probability:
            self._execute_surrender(unit, all_units, current_tick)
            return True

        return False

    def accept_surrender(
        self,
        surrendered_unit: Unit,
        enemy_units: list[Unit],
    ) -> TileCoord | None:
        """Move a surrendered unit toward the nearest enemy unit.

        Returns the target position the unit should move toward, or
        None if no enemy is alive.
        """
        alive_enemies = [e for e in enemy_units if e.is_alive]
        if not alive_enemies:
            return None

        nearest = min(
            alive_enemies,
            key=lambda e: surrendered_unit.position.tile_coord.chebyshev_distance(
                e.position.tile_coord
            ),
        )
        return nearest.position.tile_coord

    # ------------------------------------------------------------------
    # Condition checks
    # ------------------------------------------------------------------

    @staticmethod
    def _meets_conditions(unit: Unit, all_units: list[Unit]) -> bool:
        """Return True if ALL surrender conditions are met."""
        # Already surrendered or dead
        if unit.state_machine.current in (UnitState.DEAD, UnitState.SURRENDERED):
            return False
        # Ammo ratio check
        if unit.weapon.ammo_ratio >= AMMO_RATIO_THRESHOLD:
            return False
        # Morale check
        if unit.morale.value >= MORALE_THRESHOLD:
            return False
        # Isolation check — no friendly within ISOLATION_RADIUS
        nearby_friendlies = SurrenderSystem._count_nearby_friendlies(
            unit, all_units, ISOLATION_RADIUS
        )
        if nearby_friendlies > 0:
            return False
        # Immediate threat — enemy within THREAT_RADIUS
        nearby_enemies = SurrenderSystem._count_nearby_enemies(unit, all_units, THREAT_RADIUS)
        return nearby_enemies != 0

    # ------------------------------------------------------------------
    # Probability calculation
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_probability(unit: Unit, all_units: list[Unit]) -> float:
        """Calculate surrender probability with modifiers."""
        prob = BASE_SURRENDER_PROBABILITY

        # Surrounded bonus — enemies on 2+ cardinal sides
        if SurrenderSystem._is_surrounded(unit, all_units):
            prob += SURROUNDED_BONUS

        # Officer dead bonus
        if SurrenderSystem._is_officer_dead(unit, all_units):
            prob += OFFICER_DEAD_BONUS

        # Veteran/elite penalty
        exp_level = getattr(unit, "experience_level", 0)
        if exp_level >= 2:
            prob -= VETERAN_ELITE_PENALTY

        # Nearby friendly penalty (even beyond isolation radius)
        all_friendlies = SurrenderSystem._count_all_nearby_friendlies(unit, all_units)
        prob -= NEARBY_FRIENDLY_PENALTY * all_friendlies

        return max(0.0, min(prob, 1.0))

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def _execute_surrender(
        self,
        unit: Unit,
        all_units: list[Unit],
        current_tick: int,
    ) -> None:
        """Process the surrender of *unit*."""
        # Change unit state to SURRENDERED
        unit.state_machine.force_transition(UnitState.SURRENDERED)

        # Create FallenUnitCache — drop weapons and ammo
        cache = FallenUnitCache(
            unit_id=unit.id,
            position_tile=(
                unit.position.tile_coord.x,
                unit.position.tile_coord.y,
            ),
            weapon_id=unit.weapon.primary_weapon_id,
            ammo_count=unit.weapon.ammo_remaining,
            tick_created=current_tick,
        )
        self._fallen_caches.append(cache)

        # Zero out the unit's ammo
        unit.weapon.ammo_remaining = 0
        from pycc2.domain.components.weapon_component import WeaponState

        unit.weapon.state = WeaponState.OUT_OF_AMMO

        # Morale event for nearby friendly units
        self._propagate_morale_event(unit, all_units)

        logger.info(f"Unit {unit.id} ({unit.name}) surrendered at tick {current_tick}")

    @staticmethod
    def _propagate_morale_event(unit: Unit, all_units: list[Unit]) -> None:
        """Nearby friendly units suffer a morale hit when a unit surrenders."""
        for other in all_units:
            if other.id == unit.id:
                continue
            if not other.is_alive:
                continue
            if other.faction != unit.faction:
                continue
            dist = unit.position.tile_coord.chebyshev_distance(other.position.tile_coord)
            if dist <= MORALE_EVENT_RADIUS:
                other.morale.apply_delta(MORALE_EVENT_DELTA)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _count_nearby_friendlies(unit: Unit, all_units: list[Unit], radius: int) -> int:
        return sum(
            1
            for u in all_units
            if u.id != unit.id
            and u.is_alive
            and u.faction == unit.faction
            and unit.position.tile_coord.chebyshev_distance(u.position.tile_coord) <= radius
        )

    @staticmethod
    def _count_nearby_enemies(unit: Unit, all_units: list[Unit], radius: int) -> int:
        return sum(
            1
            for u in all_units
            if u.is_alive
            and u.faction != unit.faction
            and unit.position.tile_coord.chebyshev_distance(u.position.tile_coord) <= radius
        )

    @staticmethod
    def _count_all_nearby_friendlies(unit: Unit, all_units: list[Unit]) -> int:
        """Count all friendly units within a generous radius for penalty calc."""
        return sum(
            1
            for u in all_units
            if u.id != unit.id
            and u.is_alive
            and u.faction == unit.faction
            and unit.position.tile_coord.chebyshev_distance(u.position.tile_coord) <= 15
        )

    @staticmethod
    def _is_surrounded(unit: Unit, all_units: list[Unit]) -> bool:
        """Check if enemies are on 2+ cardinal sides (N/S/E/W)."""
        ux = unit.position.tile_coord.x
        uy = unit.position.tile_coord.y
        sides_with_enemies: set[str] = set()

        for u in all_units:
            if not u.is_alive or u.faction == unit.faction:
                continue
            dx = u.position.tile_coord.x - ux
            dy = u.position.tile_coord.y - uy
            dist = abs(dx) + abs(dy)
            if dist > 8:
                continue
            if abs(dx) > abs(dy):
                sides_with_enemies.add("E" if dx > 0 else "W")
            else:
                sides_with_enemies.add("S" if dy > 0 else "N")

        return len(sides_with_enemies) >= 2

    @staticmethod
    def _is_officer_dead(unit: Unit, all_units: list[Unit]) -> bool:
        """Check if the squad's officer/commander is dead."""
        from pycc2.domain.entities.unit import UnitType

        for u in all_units:
            if u.faction != unit.faction:
                continue
            if u.unit_type == UnitType.COMMANDER and not u.is_alive:
                # Check if the dead officer was in the same squad
                if unit.squad_id and u.squad_id == unit.squad_id:
                    return True
        return False


# ---------------------------------------------------------------------------
# SurrenderAI — Tactical AI pattern for surrender
# ---------------------------------------------------------------------------


class SurrenderAI(TacticalAIBase):
    """Tactical AI that evaluates whether friendly units should surrender.

    Follows the same evaluate/score/execute pattern as other tactical AIs
    (FlankingAI, SuppressionAI, etc.).
    """

    def __init__(self, surrender_system: SurrenderSystem | None = None) -> None:
        self._system = surrender_system or SurrenderSystem()

    def evaluate(self, context: TacticalContext) -> float:
        """Return priority score based on how many units are close to
        surrender threshold.
        """
        candidates = self._surrender_candidates(context)
        if not candidates:
            return 0.0

        # Score based on how close candidates are to surrender
        total_closeness = 0.0
        for unit in candidates:
            ammo_closeness = max(0.0, 1.0 - unit.weapon.ammo_ratio / AMMO_RATIO_THRESHOLD)
            morale_closeness = max(0.0, 1.0 - unit.morale.value / MORALE_THRESHOLD)
            total_closeness += (ammo_closeness + morale_closeness) / 2.0

        avg_closeness = total_closeness / len(candidates)
        count_factor = min(len(candidates) / 3.0, 1.0)

        return min(0.3 * avg_closeness + 0.7 * count_factor, 1.0)

    def execute(self, context: TacticalContext) -> list[TacticIntent]:
        """Issue SURRENDER intents for units that meet the conditions."""
        intents: list[TacticIntent] = []
        candidates = self._surrender_candidates(context)

        for unit in candidates:
            if self._system._meets_conditions(unit, context.friendly_units + context.enemy_units):
                intents.append(
                    TacticIntent(
                        unit_id=unit.id,
                        tactic_type=TacticType.SURRENDER,
                        priority=10,
                    )
                )

        return intents

    # -- helpers --

    @staticmethod
    def _surrender_candidates(context: TacticalContext) -> list[Unit]:
        """Return friendly units that are approaching surrender conditions
        (not yet meeting all conditions, but close).
        """
        return [
            u
            for u in context.friendly_units
            if u.is_alive
            and u.weapon.ammo_ratio < 0.15
            and u.morale.value < 30
            and u.state_machine.current != UnitState.DEAD
        ]
