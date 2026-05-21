"""
Mine Warfare — CC2-Authentic Mine Laying and Detection

Engineers can lay and detect mines, creating defensive zones that
channel enemy movement and inflict casualties on advancing forces.

Components:
  1. MineWarfareSystem  — Manages mine placement, detection, and triggering
  2. MineWarfareAI      — Evaluates when/where engineers should lay mines

Mine laying:
  - Only engineer squads can lay mines
  - Takes 20 ticks per mine
  - Max 5 mines per engineer squad per battle
  - Mine types: AT_MINE (vs vehicles, 80 damage, 60% trigger chance),
                AP_MINE (vs infantry, 30 damage, 40% trigger chance)
  - Mines placed at engineer's current position
  - Mines are invisible to enemy until detected

Mine detection:
  - Engineer squads detect mines within 3 tiles when moving slowly (SNEAK speed)
  - Detection chance: 60% per tick when adjacent
  - Detected mines marked on map (visible to friendly side)
  - Defusing: engineer must be adjacent, takes 10 ticks, 10% chance of detonation

Mine triggering:
  - When unit moves into mine tile, roll trigger chance
  - AT mines only trigger for vehicles, AP mines only for infantry
  - Triggered mine: apply damage + heavy suppression (+30)
  - Mine is consumed after trigger
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

MINE_LAY_TICKS: int = 20          # Ticks to lay one mine
MAX_MINES_PER_SQUAD: int = 5      # Max mines per engineer squad per battle
MINE_DETECT_RANGE: int = 3        # Detection range when moving slowly
MINE_DETECT_CHANCE: float = 0.60  # 60% per tick when adjacent
MINE_DEFUSE_TICKS: int = 10       # Ticks to defuse a mine
MINE_DEFUSE_DETONATE_CHANCE: float = 0.10  # 10% chance of detonation
MINE_TRIGGER_SUPPRESSION: int = 30  # Suppression added on mine trigger

# Chokepoint terrain types for mine placement
_CHOKEPOINT_TERRAIN: set[TerrainType] = {
    TerrainType.BRIDGE,
    TerrainType.ROAD,
}

# Terrain where mines can be placed
_PLACEABLE_TERRAIN: set[TerrainType] = {
    TerrainType.OPEN,
    TerrainType.GRASS,
    TerrainType.ROUGH,
    TerrainType.ROAD,
    TerrainType.BRIDGE,
    TerrainType.CRATER,
}


# ---------------------------------------------------------------------------
# Mine types
# ---------------------------------------------------------------------------

class MineType(Enum):
    AT_MINE = auto()   # Anti-tank mine
    AP_MINE = auto()   # Anti-personnel mine


@dataclass(slots=True)
class MineProperties:
    """Properties for each mine type."""
    mine_type: MineType
    damage: int
    trigger_chance: float
    target_types: set[UnitType]


_MINE_PROPERTIES: dict[MineType, MineProperties] = {
    MineType.AT_MINE: MineProperties(
        mine_type=MineType.AT_MINE,
        damage=80,
        trigger_chance=0.60,
        target_types={UnitType.TANK},
    ),
    MineType.AP_MINE: MineProperties(
        mine_type=MineType.AP_MINE,
        damage=30,
        trigger_chance=0.40,
        target_types={
            UnitType.INFANTRY_SQUAD,
            UnitType.COMMANDER,
            UnitType.SNIPER_TEAM,
            UnitType.MEDIC_TEAM,
            UnitType.MACHINE_GUN_SQUAD,
            UnitType.AT_GUN_TEAM,
            UnitType.MORTAR_TEAM,
        },
    ),
}


# ---------------------------------------------------------------------------
# Mine instance
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Mine:
    """A single mine placed on the map."""
    mine_type: MineType
    position: TileCoord
    owner_faction: str   # Faction name that placed the mine
    detected_by: set[str] = field(default_factory=set)  # Faction names that detected it
    active: bool = True

    @property
    def is_detected_by_enemy(self) -> bool:
        """Check if mine has been detected by any faction other than the owner."""
        return any(f != self.owner_faction for f in self.detected_by)

    @property
    def properties(self) -> MineProperties:
        return _MINE_PROPERTIES[self.mine_type]


# ---------------------------------------------------------------------------
# Laying/Detection progress
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class LayProgress:
    """Tracks mine laying progress for an engineer squad."""
    unit_id: str
    progress: int = 0       # 0 to MINE_LAY_TICKS
    mine_type: MineType = MineType.AP_MINE
    mines_laid: int = 0     # Count of mines laid this battle

    @property
    def is_complete(self) -> bool:
        return self.progress >= MINE_LAY_TICKS

    @property
    def can_lay_more(self) -> bool:
        return self.mines_laid < MAX_MINES_PER_SQUAD


@dataclass(slots=True)
class DefuseProgress:
    """Tracks mine defusal progress for an engineer squad."""
    unit_id: str
    mine_index: int         # Index into the mine list
    progress: int = 0       # 0 to MINE_DEFUSE_TICKS

    @property
    def is_complete(self) -> bool:
        return self.progress >= MINE_DEFUSE_TICKS


# ---------------------------------------------------------------------------
# MineWarfareSystem
# ---------------------------------------------------------------------------

class MineWarfareSystem:
    """Manages mine placement, detection, and triggering.

    Responsibilities:
      - Track all mines on the map
      - Handle mine laying progress
      - Handle mine detection and defusal
      - Process mine triggering when units move into mine tiles
    """

    def __init__(self) -> None:
        self._mines: list[Mine] = []
        self._lay_progress: dict[str, LayProgress] = {}
        self._defuse_progress: dict[str, DefuseProgress] = {}
        self._logger = logging.getLogger("pycc2.ai.mine_warfare")

    @property
    def mines(self) -> list[Mine]:
        return list(self._mines)

    @property
    def active_mines(self) -> list[Mine]:
        return [m for m in self._mines if m.active]

    def can_lay_mine(self, unit: Unit, game_map: GameMap) -> bool:
        """Check if an engineer squad can lay a mine at its current position."""
        if not unit.is_alive or not unit.can_act:
            return False
        if unit.unit_type != UnitType.AT_GUN_TEAM:
            # Using AT_GUN_TEAM as proxy for engineers; in a full model
            # there would be an ENGINEER_SQUAD type
            return False

        progress = self._lay_progress.get(unit.id)
        if progress is not None and not progress.can_lay_more:
            return False

        # Check existing progress count
        existing = self._lay_progress.get(unit.id)
        if existing is not None and existing.mines_laid >= MAX_MINES_PER_SQUAD:
            return False

        # Terrain must be placeable
        pos = unit.position.tile_coord
        terrain = game_map.get_terrain(pos)
        return terrain in _PLACEABLE_TERRAIN

    def start_laying(
        self, unit: Unit, mine_type: MineType, game_map: GameMap
    ) -> bool:
        """Start laying a mine at the unit's current position."""
        if not self.can_lay_mine(unit, game_map):
            return False

        # Check no mine already at this position from same faction
        faction_name = unit.faction.name
        for m in self._mines:
            if m.position == unit.position.tile_coord and m.owner_faction == faction_name:
                return False

        progress = self._lay_progress.get(unit.id)
        if progress is None:
            progress = LayProgress(
                unit_id=unit.id,
                mine_type=mine_type,
            )
            self._lay_progress[unit.id] = progress
        else:
            progress.mine_type = mine_type
            progress.progress = 0

        self._logger.debug(
            f"Unit {unit.id} started laying {mine_type.name} at "
            f"({unit.position.tile_coord.x}, {unit.position.tile_coord.y})"
        )
        return True

    def tick_laying(self, unit: Unit, game_map: GameMap) -> bool:
        """Advance mine laying progress. Returns True if mine completed."""
        progress = self._lay_progress.get(unit.id)
        if progress is None:
            return False

        progress.progress += 1

        if progress.is_complete:
            mine = Mine(
                mine_type=progress.mine_type,
                position=unit.position.tile_coord,
                owner_faction=unit.faction.name,
            )
            self._mines.append(mine)
            progress.mines_laid += 1
            progress.progress = 0

            self._logger.info(
                f"Unit {unit.id} laid {progress.mine_type.name} at "
                f"({unit.position.tile_coord.x}, {unit.position.tile_coord.y})"
            )
            return True

        return False

    def detect_mines(
        self, unit: Unit, game_map: GameMap
    ) -> list[Mine]:
        """Attempt to detect mines near an engineer unit.

        Engineers moving slowly (SNEAK speed) detect mines within range.
        Returns list of newly detected mines.
        """
        if not unit.is_alive or not unit.can_act:
            return []

        if unit.unit_type != UnitType.AT_GUN_TEAM:
            return []

        faction_name = unit.faction.name
        pos = unit.position.tile_coord
        newly_detected: list[Mine] = []

        import random

        for mine in self._mines:
            if not mine.active:
                continue
            if faction_name in mine.detected_by:
                continue
            if mine.owner_faction == faction_name:
                # Always visible to owner
                mine.detected_by.add(faction_name)
                continue

            dist = pos.chebyshev_distance(mine.position)
            if dist <= MINE_DETECT_RANGE and random.random() < MINE_DETECT_CHANCE:
                mine.detected_by.add(faction_name)
                newly_detected.append(mine)
                self._logger.debug(
                    f"Unit {unit.id} detected {mine.mine_type.name} at "
                    f"({mine.position.x}, {mine.position.y})"
                )

        return newly_detected

    def start_defusing(self, unit: Unit, mine_index: int) -> bool:
        """Start defusing a mine. Engineer must be adjacent to the mine."""
        if not unit.is_alive or not unit.can_act:
            return False
        if unit.unit_type != UnitType.AT_GUN_TEAM:
            return False

        if mine_index < 0 or mine_index >= len(self._mines):
            return False

        mine = self._mines[mine_index]
        if not mine.active:
            return False

        dist = unit.position.tile_coord.chebyshev_distance(mine.position)
        if dist > 1:
            return False

        self._defuse_progress[unit.id] = DefuseProgress(
            unit_id=unit.id,
            mine_index=mine_index,
        )
        self._logger.debug(
            f"Unit {unit.id} started defusing mine at "
            f"({mine.position.x}, {mine.position.y})"
        )
        return True

    def tick_defusing(self, unit: Unit) -> bool:
        """Advance defusal progress. Returns True if defusal completed.

        On completion, there is a 10% chance the mine detonates instead.
        """
        progress = self._defuse_progress.get(unit.id)
        if progress is None:
            return False

        progress.progress += 1

        if progress.is_complete:
            mine = self._mines[progress.mine_index] if progress.mine_index < len(self._mines) else None
            self._defuse_progress.pop(unit.id, None)

            if mine is None or not mine.active:
                return False

            import random

            if random.random() < MINE_DEFUSE_DETONATE_CHANCE:
                # Mine detonates!
                self._trigger_mine(mine, unit)
                self._logger.info(
                    f"Mine detonated while unit {unit.id} was defusing!"
                )
                return True

            # Successfully defused
            mine.active = False
            self._logger.info(
                f"Unit {unit.id} defused {mine.mine_type.name} at "
                f"({mine.position.x}, {mine.position.y})"
            )
            return True

        return False

    def check_trigger(
        self, unit: Unit, position: TileCoord
    ) -> Mine | None:
        """Check if a unit moving into a position triggers a mine.

        Returns the triggered mine, or None if no mine was triggered.
        The mine is consumed (deactivated) after triggering.
        """
        import random

        for mine in self._mines:
            if not mine.active:
                continue
            if mine.position != position:
                continue
            # Don't trigger own faction's mines
            if mine.owner_faction == unit.faction.name:
                continue

            props = mine.properties
            # Check if this unit type triggers this mine type
            if unit.unit_type not in props.target_types:
                continue

            # Roll trigger chance
            if random.random() < props.trigger_chance:
                self._trigger_mine(mine, unit)
                return mine

        return None

    def get_lay_progress(self, unit_id: str) -> LayProgress | None:
        return self._lay_progress.get(unit_id)

    def get_defuse_progress(self, unit_id: str) -> DefuseProgress | None:
        return self._defuse_progress.get(unit_id)

    def get_mines_at(self, position: TileCoord) -> list[Mine]:
        """Get all mines at a given position."""
        return [m for m in self._mines if m.position == position and m.active]

    def _trigger_mine(self, mine: Mine, unit: Unit) -> None:
        """Apply mine effects to a unit and deactivate the mine."""
        props = mine.properties
        unit.take_damage(props.damage)

        # Apply heavy suppression
        combat_state = getattr(unit, 'combat_state', None)
        if combat_state is not None:
            suppression = getattr(combat_state, 'suppression', None)
            if suppression is not None:
                suppression.add_suppression(MINE_TRIGGER_SUPPRESSION)

        mine.active = False

        self._logger.info(
            f"Unit {unit.id} triggered {mine.mine_type.name} at "
            f"({mine.position.x}, {mine.position.y}), "
            f"damage={props.damage}"
        )


# ---------------------------------------------------------------------------
# MineWarfareAI
# ---------------------------------------------------------------------------

class MineWarfareAI(TacticalAIBase):
    """Evaluate when/where engineers should lay mines and issue LAY_MINE orders.

    CC2 behaviour: Engineers lay mines at chokepoints (bridges, road
    junctions) to slow enemy advances and protect defensive positions.

    Evaluation heuristic:
      - Higher score when chokepoints are identified on the map
      - Higher score when engineers are available and not engaged
      - Lower score when enemies are very close (combat priority)
      - Zero when no engineers or no suitable positions
    """

    def __init__(self, mine_system: MineWarfareSystem | None = None) -> None:
        self._system = mine_system or MineWarfareSystem()
        self._logger = logging.getLogger("pycc2.ai.mine_warfare_ai")

    @property
    def system(self) -> MineWarfareSystem:
        return self._system

    def evaluate(self, context: TacticalContext) -> float:
        engineers = self._find_engineers(context)
        if not engineers:
            return 0.0

        chokepoints = self._find_chokepoints(context)
        if not chokepoints:
            return 0.0

        # Chokepoint availability
        choke_ratio = min(len(chokepoints) / 3.0, 1.0)

        # Engineer availability (not all used up)
        available = sum(
            1 for e in engineers  # type: ignore[misc]
            if self._system.get_lay_progress(e.id) is None
            or self._system.get_lay_progress(e.id).can_lay_more  # type: ignore[union-attr]
        )
        eng_ratio = min(available / max(len(engineers), 1), 1.0)

        # Enemy pressure — lower score if enemies are very close
        enemy_pressure = self._enemy_pressure(context)

        score = 0.4 * choke_ratio + 0.4 * eng_ratio - 0.2 * enemy_pressure
        return max(0.0, min(score, 1.0))

    def execute(self, context: TacticalContext) -> list[TacticIntent]:
        engineers = self._find_engineers(context)
        if not engineers:
            return []

        chokepoints = self._find_chokepoints(context)
        if not chokepoints:
            return []

        intents: list[TacticIntent] = []
        assigned: set[str] = set()

        for engineer in engineers:
            if engineer.id in assigned:
                continue

            # Check if engineer can lay more mines
            progress = self._system.get_lay_progress(engineer.id)
            if progress is not None and not progress.can_lay_more:
                continue

            # Find nearest unmined chokepoint
            best_cp = None
            best_dist = float("inf")
            for cp in chokepoints:
                # Check if already mined by our faction
                existing = self._system.get_mines_at(cp)
                faction_name = engineer.faction.name
                if any(m.owner_faction == faction_name for m in existing):
                    continue

                dist = engineer.position.tile_coord.chebyshev_distance(cp)
                if dist < best_dist:
                    best_dist = dist
                    best_cp = cp

            if best_cp is None:
                continue

            assigned.add(engineer.id)

            dist = engineer.position.tile_coord.chebyshev_distance(best_cp)
            if dist <= 1:
                # At the chokepoint — lay mine
                intents.append(
                    TacticIntent(
                        unit_id=engineer.id,
                        tactic_type=TacticType.LAY_MINE,
                        priority=5,
                        target_position=best_cp,
                    )
                )
            else:
                # Move to chokepoint first
                intents.append(
                    TacticIntent(
                        unit_id=engineer.id,
                        tactic_type=TacticType.MOVE_TO,
                        priority=4,
                        target_position=best_cp,
                    )
                )

        return intents

    # -- helpers --

    @staticmethod
    def _find_engineers(context: TacticalContext) -> list[Unit]:
        """Find engineer-capable units (AT_GUN_TEAM used as proxy)."""
        return [
            u for u in context.friendly_units
            if u.is_alive and u.can_act and u.unit_type == UnitType.AT_GUN_TEAM
        ]

    @staticmethod
    def _find_chokepoints(context: TacticalContext) -> list[TileCoord]:
        """Find chokepoint positions on the map (bridges, road junctions)."""
        game_map = context.game_map
        chokepoints: list[TileCoord] = []

        for y in range(game_map.height):
            for x in range(game_map.width):
                tc = TileCoord(x, y)
                terrain = game_map.get_terrain(tc)
                if terrain in _CHOKEPOINT_TERRAIN:
                    chokepoints.append(tc)

        return chokepoints[:20]

    @staticmethod
    def _choose_mine_type(context: TacticalContext) -> MineType:
        """Choose mine type based on enemy composition."""
        enemy_armor = sum(
            1 for e in context.enemy_units
            if e.is_alive and e.unit_type == UnitType.TANK
        )
        enemy_infantry = sum(
            1 for e in context.enemy_units
            if e.is_alive and e.unit_type != UnitType.TANK
        )

        if enemy_armor >= 2:
            return MineType.AT_MINE
        if enemy_infantry >= 3:
            return MineType.AP_MINE
        # Default: AT mine at bridges, AP elsewhere
        return MineType.AT_MINE

    @staticmethod
    def _enemy_pressure(context: TacticalContext) -> float:
        """Measure how close enemy forces are."""
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

        if min_dist <= 5:
            return 1.0
        elif min_dist <= 10:
            return 0.5
        elif min_dist <= 20:
            return 0.2
        return 0.0
