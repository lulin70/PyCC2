"""
Artillery Call-in — CC2-Authentic Indirect Fire Support

Forward observers can call indirect fire support, mirroring the critical
role of artillery observers in WWII. Artillery was the dominant killer
on the battlefield and proper use of fire support is essential.

Components:
  1. ArtilleryCallinAI    — Evaluates when to call artillery and issues orders
  2. ArtilleryState       — Tracks the multi-step call-in process
  3. ArtilleryManager     — Manages all active artillery missions

Call-in process (CC2-authentic):
  1. SPOT     — Observer spots target (LOS check)
  2. CALL     — Radio call: 10 tick delay (communication time)
  3. FIRE     — Fire mission: 30 tick delay (artillery travel time)
  4. IMPACT   — 3x3 area, 15 damage/tile, 20 suppression/tile
  5. CORRECT  — Observer can adjust for second salvo (5 tick delay)

Observer requirements:
  - Must be officer (COMMANDER) or recon (SNIPER_TEAM)
  - Must have radio (not suppressed, not moving)
  - Must have direct LOS to target area

Limitations:
  - Max 2 fire missions per battle
  - Cannot call in own sector (minimum range 10 tiles)
  - Weather affects accuracy (FOG: scatter +3, RAIN: +2)
  - Friendly fire risk if allies in impact zone
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.ai.tactical_ai import TacticalAIBase, TacticalContext
from pycc2.domain.entities.unit import UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.systems.environment import EnvironmentState


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_OBSERVER_TYPES: set[UnitType] = {
    UnitType.COMMANDER,
    UnitType.SNIPER_TEAM,
}

CALL_DELAY_TICKS: int = 10         # Radio communication time
FIRE_DELAY_TICKS: int = 30         # Artillery travel time
CORRECTION_DELAY_TICKS: int = 5    # Correction for second salvo
IMPACT_RADIUS: int = 1             # 3x3 area (Chebyshev radius 1)
DAMAGE_PER_TILE: int = 15          # Damage per tile in impact zone
SUPPRESSION_PER_TILE: float = 20.0 # Suppression per tile in impact zone
MAX_FIRE_MISSIONS: int = 2         # Limited ammo per battle
MINIMUM_RANGE: int = 10            # Cannot call in own sector
FOG_SCATTER: int = 3               # Extra scatter in fog
RAIN_SCATTER: int = 2              # Extra scatter in rain


# ---------------------------------------------------------------------------
# ArtilleryState
# ---------------------------------------------------------------------------

class ArtilleryPhase(Enum):
    """Phases of an artillery call-in."""
    AVAILABLE = auto()     # Observer available, no mission active
    CALLING = auto()       # Radio call in progress
    INCOMING = auto()      # Shells in the air
    CORRECTION = auto()    # Observer adjusting for second salvo
    COMPLETE = auto()      # Mission finished


@dataclass(slots=True)
class ArtilleryMission:
    """Tracks a single artillery fire mission."""
    observer_id: str
    target_pos: TileCoord
    phase: ArtilleryPhase = ArtilleryPhase.CALLING
    timer: int = 0
    salvos_fired: int = 0
    scatter: int = 0       # Current scatter from weather/correction

    def advance(self) -> None:
        """Advance the mission by one tick."""
        self.timer += 1

        if self.phase == ArtilleryPhase.CALLING:
            if self.timer >= CALL_DELAY_TICKS:
                self.phase = ArtilleryPhase.INCOMING
                self.timer = 0

        elif self.phase == ArtilleryPhase.INCOMING:
            if self.timer >= FIRE_DELAY_TICKS:
                self.salvos_fired += 1
                self.phase = ArtilleryPhase.COMPLETE

        elif self.phase == ArtilleryPhase.CORRECTION and self.timer >= CORRECTION_DELAY_TICKS:
            self.phase = ArtilleryPhase.INCOMING
            self.timer = 0


# ---------------------------------------------------------------------------
# ArtilleryManager
# ---------------------------------------------------------------------------

class ArtilleryManager:
    """Manages all artillery missions for a faction.

    Responsibilities:
      - Track available fire missions (limited ammo)
      - Manage active missions through their phases
      - Apply impact effects when shells land
      - Handle weather-based scatter
    """

    def __init__(self, max_missions: int = MAX_FIRE_MISSIONS) -> None:
        self._missions_remaining: int = max_missions
        self._active_missions: dict[str, ArtilleryMission] = {}  # observer_id -> mission

    @property
    def missions_remaining(self) -> int:
        return self._missions_remaining

    @property
    def active_missions(self) -> list[ArtilleryMission]:
        return list(self._active_missions.values())

    def can_call_mission(self, observer_id: str) -> bool:
        """Check if a new mission can be called by this observer."""
        if self._missions_remaining <= 0:
            return False
        return observer_id not in self._active_missions

    def start_mission(
        self,
        observer_id: str,
        target_pos: TileCoord,
        scatter: int = 0,
    ) -> ArtilleryMission | None:
        """Start a new artillery mission."""
        if not self.can_call_mission(observer_id):
            return None

        self._missions_remaining -= 1
        mission = ArtilleryMission(
            observer_id=observer_id,
            target_pos=target_pos,
            scatter=scatter,
        )
        self._active_missions[observer_id] = mission
        logger.info(
            f"Artillery mission started by {observer_id} "
            f"targeting ({target_pos.x}, {target_pos.y}), "
            f"{self._missions_remaining} missions remaining"
        )
        return mission

    def tick(self) -> list[ArtilleryMission]:
        """Advance all active missions by one tick.

        Returns list of missions that reached impact this tick.
        """
        impacted: list[ArtilleryMission] = []
        to_remove: list[str] = []

        for obs_id, mission in self._active_missions.items():
            mission.advance()
            if mission.phase == ArtilleryPhase.COMPLETE:
                impacted.append(mission)
                to_remove.append(obs_id)

        for obs_id in to_remove:
            self._active_missions.pop(obs_id)

        return impacted

    def calculate_impact_area(
        self, mission: ArtilleryMission, game_map: GameMap,
    ) -> list[TileCoord]:
        """Calculate the actual impact tiles for a mission.

        Applies scatter from weather and random offset.
        """
        target = mission.target_pos
        scatter = mission.scatter

        # Apply scatter offset
        if scatter > 0:
            import random
            dx = random.randint(-scatter, scatter)
            dy = random.randint(-scatter, scatter)
            actual_center = TileCoord(target.x + dx, target.y + dy)
        else:
            actual_center = target

        # Generate 3x3 impact area
        tiles: list[TileCoord] = []
        for dx in range(-IMPACT_RADIUS, IMPACT_RADIUS + 1):
            for dy in range(-IMPACT_RADIUS, IMPACT_RADIUS + 1):
                tile = TileCoord(actual_center.x + dx, actual_center.y + dy)
                if game_map.is_within_bounds(tile):
                    tiles.append(tile)

        return tiles

    def apply_impact(
        self,
        impact_tiles: list[TileCoord],
        units: list[Unit],
        game_map: GameMap,
    ) -> list[dict]:
        """Apply artillery impact effects to units in the impact zone.

        Returns list of effect dicts for event publishing.
        """
        effects: list[dict] = []
        impact_set: set[tuple[int, int]] = {
            (t.x, t.y) for t in impact_tiles
        }

        for unit in units:
            if not unit.is_alive:
                continue
            pos = unit.position.tile_coord
            if (pos.x, pos.y) in impact_set:
                # Apply damage
                damage = unit.take_damage(DAMAGE_PER_TILE)
                # Apply heavy suppression
                combat_state = getattr(unit, 'combat_state', None)
                if combat_state is not None:
                    suppression = getattr(combat_state, 'suppression', None)
                    if suppression is not None:
                        suppression.apply_suppression(SUPPRESSION_PER_TILE)

                effects.append({
                    'unit_id': unit.id,
                    'damage': damage,
                    'suppression': SUPPRESSION_PER_TILE,
                    'source': 'artillery',
                })

        return effects

    @staticmethod
    def calculate_weather_scatter(environment: EnvironmentState | None) -> int:
        """Calculate scatter bonus from weather conditions."""
        if environment is None:
            return 0

        from pycc2.domain.systems.environment import WeatherCondition
        if environment.weather == WeatherCondition.FOG:
            return FOG_SCATTER
        elif environment.weather == WeatherCondition.RAIN:
            return RAIN_SCATTER
        return 0


# ---------------------------------------------------------------------------
# ArtilleryCallinAI
# ---------------------------------------------------------------------------

class ArtilleryCallinAI(TacticalAIBase):
    """Evaluate when to call artillery and issue CALL_ARTILLERY orders.

    CC2 behaviour: Forward observers call artillery on concentrations
    of enemy forces. The process takes time (radio + flight) and ammo
    is limited, so targets must be chosen carefully.

    Evaluation heuristic:
      - Higher score when enemy units are concentrated in an area
      - Higher score when observer has LOS to target
      - Lower score when no fire missions remaining
      - Zero when no observers available
    """

    def __init__(self, artillery_manager: ArtilleryManager | None = None) -> None:
        self._manager = artillery_manager or ArtilleryManager()

    @property
    def manager(self) -> ArtilleryManager:
        return self._manager

    def evaluate(self, context: TacticalContext) -> float:
        observers = self._available_observers(context)
        if not observers:
            return 0.0

        if self._manager.missions_remaining <= 0:
            return 0.0

        # Check for enemy concentration
        concentration = self._enemy_concentration(context)
        if concentration < 0.2:
            return 0.0

        # Check if any observer has LOS to a target area
        has_los = self._any_observer_has_los(observers, context)

        score = 0.5 * concentration + 0.3 * has_los + 0.2 * 0.6
        return min(score, 1.0)

    def execute(self, context: TacticalContext) -> list[TacticIntent]:
        observers = self._available_observers(context)
        if not observers or self._manager.missions_remaining <= 0:
            return []

        # Find best target: area with highest enemy concentration
        target = self._find_best_target(context)
        if target is None:
            return []

        # Find best observer for this target
        best_observer = self._best_observer_for(observers, target, context)
        if best_observer is None:
            return []

        # Check minimum range
        dist = best_observer.position.tile_coord.chebyshev_distance(target)
        if dist < MINIMUM_RANGE:
            return []

        # Check LOS
        if not context.game_map.has_line_of_sight(
            best_observer.position.tile_coord, target
        ):
            return []

        # Check for friendly units in impact zone
        if self._friendly_in_impact_zone(target, context):
            return []

        return [
            TacticIntent(
                unit_id=best_observer.id,
                tactic_type=TacticType.CALL_ARTILLERY,
                priority=9,
                target_position=target,
            )
        ]

    # -- helpers --

    @staticmethod
    def _available_observers(context: TacticalContext) -> list[Unit]:
        """Find available forward observers."""
        return [
            u for u in context.friendly_units
            if u.is_alive
            and u.can_act
            and u.unit_type in _OBSERVER_TYPES
            and u.morale.is_combat_effective
            and not u.is_pinned
        ]

    @staticmethod
    def _enemy_concentration(context: TacticalContext) -> float:
        """Measure how concentrated enemy forces are (0.0-1.0).

        Higher concentration = better artillery target.
        """
        enemies = [e for e in context.enemy_units if e.is_alive]
        if len(enemies) < 2:
            return 0.0

        # Find the densest cluster of enemies
        best_density = 0
        for e in enemies:
            nearby = sum(
                1 for other in enemies
                if other.position.tile_coord.chebyshev_distance(
                    e.position.tile_coord
                ) <= IMPACT_RADIUS + 1
            )
            best_density = max(best_density, nearby)

        return min(best_density / 5.0, 1.0)

    @staticmethod
    def _any_observer_has_los(
        observers: list[Unit], context: TacticalContext,
    ) -> float:
        """Check if any observer has LOS to an enemy concentration.

        Returns 1.0 if yes, 0.0 if no.
        """
        enemies = [e for e in context.enemy_units if e.is_alive]
        if not enemies:
            return 0.0

        for obs in observers:
            for e in enemies:
                if context.game_map.has_line_of_sight(
                    obs.position.tile_coord, e.position.tile_coord
                ):
                    return 1.0
        return 0.0

    @staticmethod
    def _find_best_target(context: TacticalContext) -> TileCoord | None:
        """Find the tile with the highest enemy concentration."""
        enemies = [e for e in context.enemy_units if e.is_alive]
        if not enemies:
            return None

        # Score each enemy position by number of nearby enemies
        best_pos: TileCoord | None = None
        best_count = 0

        for e in enemies:
            pos = e.position.tile_coord
            nearby = sum(
                1 for other in enemies
                if other.position.tile_coord.chebyshev_distance(pos) <= IMPACT_RADIUS + 1
            )
            if nearby > best_count:
                best_count = nearby
                best_pos = pos

        return best_pos

    @staticmethod
    def _best_observer_for(
        observers: list[Unit],
        target: TileCoord,
        context: TacticalContext,
    ) -> Unit | None:
        """Find the best observer to call fire on a target.

        Prefers observers with LOS who are closest to the target.
        """
        candidates: list[tuple[Unit, int]] = []
        for obs in observers:
            if not context.game_map.has_line_of_sight(
                obs.position.tile_coord, target
            ):
                continue
            dist = obs.position.tile_coord.chebyshev_distance(target)
            if dist < MINIMUM_RANGE:
                continue
            candidates.append((obs, dist))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[1])
        return candidates[0][0]

    @staticmethod
    def _friendly_in_impact_zone(
        target: TileCoord, context: TacticalContext,
    ) -> bool:
        """Check if any friendly units are in the potential impact zone."""
        for u in context.friendly_units:
            if not u.is_alive:
                continue
            dist = u.position.tile_coord.chebyshev_distance(target)
            if dist <= IMPACT_RADIUS + 1:
                return True
        return False
