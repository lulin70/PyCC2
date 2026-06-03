"""
Engineer Assault Team — CC2-Authentic Fortified Position Assault

Specialized engineer assault teams with demo charges and flamethrowers
for attacking fortified enemy positions (buildings, bunkers).

Components:
  1. EngineerAssaultAI  — Evaluates and executes assaults on fortified positions

Assault capabilities:
  - Demo charges: 50 damage in 2-tile radius, destroys building walls
    (BUILDING_SOLID -> OPEN)
  - Flamethrower: 3-tile range, 25 damage, sets area on fire for 30 ticks
    (5 damage/tick)
  - Bangalore torpedo: clears hedge/wire in 5-tile line

Assault phases:
  1. Approach under covering fire
  2. Place charge at target (5 ticks, must be adjacent)
  3. Retreat to safe distance (3 tiles minimum)
  4. Detonate (instant, large explosion)

Flamethrower special:
  - Can fire while moving (unlike other weapons)
  - Fuel limited: 5 bursts per battle
  - Hit on flamethrower: 50% chance fuel tank explodes
    (kills user + 2-tile radius)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
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
    from pycc2.domain.interfaces import IEventPublisher

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Demo charge
DEMO_CHARGE_DAMAGE: int = 50
DEMO_CHARGE_RADIUS: int = 2
DEMO_CHARGE_PLACE_TICKS: int = 5
DEMO_CHARGE_RETREAT_DISTANCE: int = 3

# Flamethrower
FLAMETHROWER_RANGE: int = 3
FLAMETHROWER_DAMAGE: int = 25
FLAMETHROWER_FIRE_DURATION: int = 30
FLAMETHROWER_FIRE_DAMAGE_PER_TICK: int = 5
FLAMETHROWER_MAX_BURSTS: int = 5
FLAMETHROWER_EXPLODE_CHANCE: float = 0.50
FLAMETHROWER_EXPLODE_RADIUS: int = 2

# Bangalore torpedo
BANGALORE_LENGTH: int = 5
BANGALORE_CLEARABLE: set[TerrainType] = {
    TerrainType.HEDGE,
}

# Fortified position terrain types
_FORTIFIED_TERRAIN: set[TerrainType] = {
    TerrainType.BUILDING_SOLID,
    TerrainType.BUILDING_ENTERABLE,
    TerrainType.WALL,
}

# Engineer proxy type
_ENGINEER_TYPES: set[UnitType] = {
    UnitType.AT_GUN_TEAM,  # Using AT_GUN_TEAM as proxy for engineers
}


# ---------------------------------------------------------------------------
# Assault phase
# ---------------------------------------------------------------------------

class AssaultPhase(Enum):
    APPROACH = auto()       # Moving toward target under covering fire
    PLACE_CHARGE = auto()   # Placing demo charge at target
    RETREAT = auto()        # Retreating to safe distance
    DETONATE = auto()       # Detonating the charge
    FLAMETHROWER = auto()   # Using flamethrower on target
    BANGALORE = auto()      # Using bangalore torpedo
    COMPLETE = auto()       # Assault complete


# ---------------------------------------------------------------------------
# Assault state
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class AssaultState:
    """Tracks the state of an ongoing engineer assault."""
    engineer_id: str
    target_position: TileCoord
    phase: AssaultPhase = AssaultPhase.APPROACH
    charge_progress: int = 0       # 0 to DEMO_CHARGE_PLACE_TICKS
    flamethrower_bursts_used: int = 0
    bangalore_direction: TileCoord | None = None

    @property
    def has_flamethrower_fuel(self) -> bool:
        return self.flamethrower_bursts_used < FLAMETHROWER_MAX_BURSTS


# ---------------------------------------------------------------------------
# Fire zone
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class FireZone:
    """Tracks a fire zone created by a flamethrower."""
    position: TileCoord
    remaining_ticks: int
    damage_per_tick: int = FLAMETHROWER_FIRE_DAMAGE_PER_TICK


# ---------------------------------------------------------------------------
# EngineerAssaultAI
# ---------------------------------------------------------------------------

class EngineerAssaultAI(TacticalAIBase):
    """Evaluate and execute assaults on fortified enemy positions.

    CC2 behaviour: Engineer teams with demo charges and flamethrowers
    are the primary means of clearing fortified positions. They approach
    under covering fire, place charges, retreat, and detonate.

    Evaluation heuristic:
      - Higher score when fortified enemy positions are detected
      - Higher score when engineers are available
      - Lower score when no fortified positions or no engineers
      - Zero when no enemies in fortified positions
    """

    def __init__(self) -> None:
        self._assaults: dict[str, AssaultState] = {}
        self._fire_zones: list[FireZone] = []
        self._logger = logging.getLogger("pycc2.ai.engineer_assault")

    @property
    def active_assaults(self) -> list[AssaultState]:
        return list(self._assaults.values())

    @property
    def fire_zones(self) -> list[FireZone]:
        return list(self._fire_zones)

    def evaluate(self, context: TacticalContext) -> float:
        engineers = self._find_engineers(context)
        if not engineers:
            return 0.0

        fortified = self._find_fortified_enemies(context)
        if not fortified:
            return 0.0

        # Fortification factor
        fort_ratio = min(len(fortified) / 3.0, 1.0)

        # Engineer availability
        available = [
            e for e in engineers
            if e.id not in self._assaults
        ]
        eng_ratio = min(len(available) / max(len(engineers), 1), 1.0)

        score = 0.5 * fort_ratio + 0.5 * eng_ratio
        return min(score, 1.0)

    def execute(self, context: TacticalContext) -> list[TacticIntent]:
        engineers = self._find_engineers(context)
        fortified = self._find_fortified_enemies(context)

        if not engineers or not fortified:
            return []

        intents: list[TacticIntent] = []
        assigned: set[str] = set()

        # Continue existing assaults
        for eng_id, state in list(self._assaults.items()):
            engineer = self._find_unit(eng_id, context.friendly_units)
            if engineer is None or not engineer.is_alive:
                self._assaults.pop(eng_id, None)
                continue

            assigned.add(eng_id)

            intent = self._advance_assault(state, engineer, context)
            if intent is not None:
                intents.append(intent)

        # Start new assaults
        available = [
            e for e in engineers
            if e.id not in assigned and e.id not in self._assaults
        ]

        for engineer in available:
            # Find nearest fortified position
            best_target = None
            best_dist = float("inf")
            for pos, _enemy_ids in fortified:
                dist = engineer.position.tile_coord.chebyshev_distance(pos)
                if dist < best_dist:
                    best_dist = dist
                    best_target = pos

            if best_target is None:
                continue

            assigned.add(engineer.id)

            # Create assault state
            state = AssaultState(
                engineer_id=engineer.id,
                target_position=best_target,
            )
            self._assaults[engineer.id] = state

            # Start approach phase
            intents.append(
                TacticIntent(
                    unit_id=engineer.id,
                    tactic_type=TacticType.ASSAULT_FORTIFIED,
                    priority=7,
                    target_position=best_target,
                )
            )

        return intents

    def tick_fire_zones(self, all_units: list[Unit]) -> list[FireZone]:
        """Advance all fire zones by one tick. Returns expired zones."""
        expired: list[FireZone] = []

        for fz in self._fire_zones:
            fz.remaining_ticks -= 1

            # Apply fire damage to units in the zone
            for unit in all_units:
                if unit.is_alive and unit.position.tile_coord == fz.position:
                    unit.take_damage(fz.damage_per_tick)

            if fz.remaining_ticks <= 0:
                expired.append(fz)

        for fz in expired:
            self._fire_zones.remove(fz)

        return expired

    def apply_demo_charge(
        self, position: TileCoord, game_map: GameMap,
        event_bus: IEventPublisher | None = None,
    ) -> list[TileCoord]:
        """Apply demo charge effects at a position.

        - Deals DEMO_CHARGE_DAMAGE in DEMO_CHARGE_RADIUS
        - Converts BUILDING_SOLID to OPEN terrain
        - Converts BRIDGE to BRIDGE_DESTROYED (blocks vehicles, infantry wades)
        Returns list of affected tile positions.
        """
        affected: list[TileCoord] = []

        for dy in range(-DEMO_CHARGE_RADIUS, DEMO_CHARGE_RADIUS + 1):
            for dx in range(-DEMO_CHARGE_RADIUS, DEMO_CHARGE_RADIUS + 1):
                tc = TileCoord(position.x + dx, position.y + dy)
                if not game_map.is_within_bounds(tc):
                    continue
                affected.append(tc)

                terrain = game_map.get_terrain(tc)

                # Destroy building walls
                if terrain == TerrainType.BUILDING_SOLID:
                    game_map.modify_terrain(tc.x, tc.y, TerrainType.OPEN)
                    self._logger.info(
                        f"Demo charge destroyed building wall at "
                        f"({tc.x}, {tc.y})"
                    )

                # Destroy bridge
                elif terrain == TerrainType.BRIDGE:
                    game_map.modify_terrain(tc.x, tc.y, TerrainType.BRIDGE_DESTROYED)
                    self._logger.info(
                        f"Demo charge destroyed bridge at "
                        f"({tc.x}, {tc.y})"
                    )
                    if event_bus is not None:
                        event_bus.publish_named("BridgeDestroyed", {
                            "event_type": "BridgeDestroyed",
                            "position": (tc.x, tc.y),
                            "message": "Bridge Destroyed",
                        })

        return affected

    def apply_flamethrower(
        self, origin: TileCoord, target: TileCoord
    ) -> FireZone:
        """Apply flamethrower effects at the target position.

        Creates a fire zone at the target position.
        """
        fz = FireZone(
            position=target,
            remaining_ticks=FLAMETHROWER_FIRE_DURATION,
        )
        self._fire_zones.append(fz)

        self._logger.debug(
            f"Flamethrower fired from ({origin.x}, {origin.y}) "
            f"to ({target.x}, {target.y}), fire for {FLAMETHROWER_FIRE_DURATION} ticks"
        )
        return fz

    def apply_bangalore(
        self, start: TileCoord, direction: TileCoord, game_map: GameMap
    ) -> list[TileCoord]:
        """Apply bangalore torpedo effects in a line.

        Clears hedges and wire in a 5-tile line from start in direction.
        Returns list of cleared tile positions.
        """
        cleared: list[TileCoord] = []

        dx = direction.x - start.x
        dy = direction.y - start.y
        length = max(abs(dx), abs(dy), 1)
        step_x = dx // length
        step_y = dy // length

        current = start
        for _ in range(BANGALORE_LENGTH):
            if not game_map.is_within_bounds(current):
                break

            terrain = game_map.get_terrain(current)
            if terrain in BANGALORE_CLEARABLE:
                cleared.append(current)
                self._logger.info(
                    f"Bangalore cleared hedge at ({current.x}, {current.y})"
                )

            current = TileCoord(current.x + step_x, current.y + step_y)

        return cleared

    def check_flamethrower_hit(self, engineer: Unit) -> bool:
        """Check if a hit on a flamethrower-carrying engineer causes explosion.

        50% chance the fuel tank explodes, killing the user and damaging
        everything in a 2-tile radius.
        """
        import random

        if random.random() < FLAMETHROWER_EXPLODE_CHANCE:
            self._logger.info(
                f"Flamethrower fuel tank exploded on unit {engineer.id}!"
            )
            return True
        return False

    # -- helpers --

    def _advance_assault(
        self,
        state: AssaultState,
        engineer: Unit,
        context: TacticalContext,
    ) -> TacticIntent | None:
        """Advance an assault to the next phase and return the appropriate intent."""
        eng_pos = engineer.position.tile_coord
        target_pos = state.target_position
        dist = eng_pos.chebyshev_distance(target_pos)

        if state.phase == AssaultPhase.APPROACH:
            if dist <= 1:
                # Reached target — decide assault method
                state.phase = AssaultPhase.PLACE_CHARGE
                return TacticIntent(
                    unit_id=engineer.id,
                    tactic_type=TacticType.ASSAULT_FORTIFIED,
                    priority=8,
                    target_position=target_pos,
                )
            else:
                # Continue approach
                return TacticIntent(
                    unit_id=engineer.id,
                    tactic_type=TacticType.MOVE_TO,
                    priority=7,
                    target_position=target_pos,
                )

        elif state.phase == AssaultPhase.PLACE_CHARGE:
            state.charge_progress += 1
            if state.charge_progress >= DEMO_CHARGE_PLACE_TICKS:
                state.phase = AssaultPhase.RETREAT
            return TacticIntent(
                unit_id=engineer.id,
                tactic_type=TacticType.HOLD_POSITION,
                priority=8,
                target_position=target_pos,
            )

        elif state.phase == AssaultPhase.RETREAT:
            # Calculate retreat position (3 tiles away from target)
            dx = eng_pos.x - target_pos.x
            dy = eng_pos.y - target_pos.y
            length = max(abs(dx), abs(dy), 1)
            retreat_pos = TileCoord(
                eng_pos.x + (dx // length) * DEMO_CHARGE_RETREAT_DISTANCE,
                eng_pos.y + (dy // length) * DEMO_CHARGE_RETREAT_DISTANCE,
            )

            if dist >= DEMO_CHARGE_RETREAT_DISTANCE:
                # Safe distance reached — detonate
                state.phase = AssaultPhase.DETONATE
                return TacticIntent(
                    unit_id=engineer.id,
                    tactic_type=TacticType.ASSAULT_FORTIFIED,
                    priority=9,
                    target_position=target_pos,
                )
            else:
                return TacticIntent(
                    unit_id=engineer.id,
                    tactic_type=TacticType.MOVE_TO,
                    priority=9,
                    target_position=retreat_pos,
                )

        elif state.phase == AssaultPhase.DETONATE:
            # Apply demo charge effects
            self.apply_demo_charge(target_pos, context.game_map)

            # Damage enemies at the target position
            for enemy in context.enemy_units:
                if enemy.is_alive and enemy.position.tile_coord.chebyshev_distance(target_pos) <= DEMO_CHARGE_RADIUS:
                    enemy.take_damage(DEMO_CHARGE_DAMAGE)

            state.phase = AssaultPhase.COMPLETE
            self._assaults.pop(engineer.id, None)

            self._logger.info(
                f"Engineer {engineer.id} detonated charge at "
                f"({target_pos.x}, {target_pos.y})"
            )
            return TacticIntent(
                unit_id=engineer.id,
                tactic_type=TacticType.HOLD_POSITION,
                priority=5,
                target_position=eng_pos,
            )

        return None

    @staticmethod
    def _find_engineers(context: TacticalContext) -> list[Unit]:
        """Find engineer-capable units."""
        return [
            u for u in context.friendly_units
            if u.is_alive and u.can_act and u.unit_type in _ENGINEER_TYPES
        ]

    @staticmethod
    def _find_fortified_enemies(
        context: TacticalContext,
    ) -> list[tuple[TileCoord, list[str]]]:
        """Find enemy units in fortified positions.

        Returns list of (position, [enemy_ids]) tuples.
        """
        game_map = context.game_map
        fortified: dict[tuple[int, int], list[str]] = {}

        for enemy in context.enemy_units:
            if not enemy.is_alive:
                continue
            pos = enemy.position.tile_coord
            terrain = game_map.get_terrain(pos)
            if terrain in _FORTIFIED_TERRAIN:
                key = (pos.x, pos.y)
                fortified.setdefault(key, []).append(enemy.id)

        return [
            (TileCoord(k[0], k[1]), v) for k, v in fortified.items()
        ]

    @staticmethod
    def _find_unit(unit_id: str, units: list[Unit]) -> Unit | None:
        for u in units:
            if u.id == unit_id:
                return u
        return None
