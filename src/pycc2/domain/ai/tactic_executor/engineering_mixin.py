"""Engineering tactics mixin — extracted from tactic_executor.py (D11 SRP split).

Contains engineering-related tactic execution methods used by the TacticExecutor
facade:
  - ``_execute_dig_trench``: TrenchDiggingSystem start/tick + events
  - ``_execute_demolish_bridge``: scan 3x3 for BRIDGE terrain, set to BRIDGE_DESTROYED
  - ``_execute_lay_mine``: MineWarfareSystem start_laying/tick_laying + events
  - ``_execute_detect_mines``: MineWarfareSystem.detect_mines + event

This is a mixin — do not instantiate directly. The TacticExecutor facade
inherits this mixin and provides all required attributes via its __init__.
Class-level attribute declarations below tell mypy which facade fields the
mixin methods rely on.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from pycc2.domain.ai.mine_warfare import MineType, MineWarfareSystem
from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.ai.trench_digging import TrenchDiggingSystem
from pycc2.domain.value_objects.tile_coord import TileCoord

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.interfaces import IEventPublisher

__all__ = ["EngineeringTacticsMixin"]


class EngineeringTacticsMixin:
    """Engineering tactic execution methods. Inherited by the TacticExecutor facade,
    not instantiated directly."""

    # -- Facade attributes used by engineering methods (no defaults; set by TacticExecutor.__init__) --
    event_bus: IEventPublisher
    game_map: GameMap | None
    _unit_registry: dict[str, Unit]
    _trench_digging: TrenchDiggingSystem
    _mine_warfare_system: MineWarfareSystem
    _logger: logging.Logger

    if TYPE_CHECKING:
        # -- Cross-mixin methods provided by other mixins / the facade --
        # Declared as TYPE_CHECKING-only stubs so mypy can verify engineering
        # methods without runtime shadowing (facade is first in MRO; real
        # methods come from MovementTacticsMixin / TacticExecutor).
        def _get_unit(self, unit_id: str) -> Unit | None: ...
        def _execute_move_to(self, intent: TacticIntent) -> bool: ...

    def _execute_dig_trench(self, intent: TacticIntent) -> bool:
        """Execute a DIG_TRENCH intent.

        Starts or advances the trench digging process for a unit.
        When complete, a TRENCH_SECTION decoration is placed at the
        unit's position.
        """
        unit = self._get_unit(intent.unit_id)
        if unit is None:
            return False

        if self.game_map is None:
            self._logger.warning("No game map available for trench digging")
            return False

        # Check if unit can dig
        if not self._trench_digging.can_dig(unit, self.game_map):
            self._logger.debug(f"Unit {intent.unit_id} cannot dig trench at current position")
            return False

        # Start digging if not already in progress
        progress = self._trench_digging.get_progress(intent.unit_id)
        if progress is None:
            if not self._trench_digging.start_digging(unit):
                return False
            event = {
                "unit_id": intent.unit_id,
                "action": "dig_trench_start",
                "position": (
                    unit.position.tile_coord.x,
                    unit.position.tile_coord.y,
                ),
                "timestamp": time.time(),
            }
            self.event_bus.publish(event)
            return True

        # Advance digging
        completed = self._trench_digging.tick(unit, self.game_map)
        if completed:
            event = {
                "unit_id": intent.unit_id,
                "action": "dig_trench_complete",
                "position": (
                    unit.position.tile_coord.x,
                    unit.position.tile_coord.y,
                ),
                "timestamp": time.time(),
            }
            self.event_bus.publish(event)
            self._logger.info(
                f"Unit {intent.unit_id} completed trench at "
                f"({unit.position.tile_coord.x}, {unit.position.tile_coord.y})"
            )

        return True

    def _execute_demolish_bridge(self, intent: TacticIntent) -> bool:
        """Demolish bridge near the unit — set terrain to BRIDGE_DESTROYED."""
        unit = self._get_unit(intent.unit_id)
        if unit is None or self.game_map is None:
            return False
        from pycc2.domain.value_objects.terrain_type import TerrainType

        current = unit.position.tile_coord
        bridge_tiles = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                check_coord = TileCoord(current.x + dx, current.y + dy)
                terrain = self.game_map.get_terrain(check_coord)
                if terrain == TerrainType.BRIDGE:
                    bridge_tiles.append(check_coord)
        if not bridge_tiles:
            self._logger.debug(f"Unit {intent.unit_id} no bridge found to demolish")
            return False
        for bridge_coord in bridge_tiles:
            self.game_map.set_terrain(bridge_coord, TerrainType.BRIDGE_DESTROYED)
        event = {
            "unit_id": intent.unit_id,
            "action": "demolish_bridge",
            "bridge_tiles": [(c.x, c.y) for c in bridge_tiles],
            "timestamp": time.time(),
        }
        self.event_bus.publish(event)
        self._logger.info(f"Unit {intent.unit_id} demolished {len(bridge_tiles)} bridge tile(s)")
        return True

    def _execute_lay_mine(self, intent: TacticIntent) -> bool:
        """Execute a LAY_MINE intent.

        Engineer squad lays a mine at the target position.
        The mine warfare system handles laying progress.
        """
        unit = self._get_unit(intent.unit_id)
        if unit is None:
            return False

        if self.game_map is None:
            self._logger.warning("No game map available for mine laying")
            return False

        if intent.target_position is None:
            self._logger.warning(f"LAY_MINE for {intent.unit_id} has no target_position")
            return False

        # Check if unit is at the target position
        dist = unit.position.tile_coord.chebyshev_distance(intent.target_position)
        if dist > 1:
            move_intent = TacticIntent(
                unit_id=intent.unit_id,
                tactic_type=TacticType.MOVE_TO,
                target_position=intent.target_position,
                priority=intent.priority,
            )
            return self._execute_move_to(move_intent)

        # Check if already laying
        progress = self._mine_warfare_system.get_lay_progress(intent.unit_id)
        if progress is not None:
            # Advance laying progress
            completed = self._mine_warfare_system.tick_laying(unit, self.game_map)
            if completed:
                event = {
                    "unit_id": intent.unit_id,
                    "action": "mine_laid",
                    "position": (
                        unit.position.tile_coord.x,
                        unit.position.tile_coord.y,
                    ),
                    "timestamp": time.time(),
                }
                self.event_bus.publish(event)
            return True

        # Start laying — choose mine type based on context
        mine_type = MineType.AT_MINE  # Default
        self._mine_warfare_system.start_laying(unit, mine_type, self.game_map)

        event = {
            "unit_id": intent.unit_id,
            "action": "lay_mine_start",
            "mine_type": mine_type.name,
            "position": (
                unit.position.tile_coord.x,
                unit.position.tile_coord.y,
            ),
            "timestamp": time.time(),
        }
        self.event_bus.publish(event)
        self._logger.info(f"Unit {intent.unit_id} started laying {mine_type.name}")
        return True

    def _execute_detect_mines(self, intent: TacticIntent) -> bool:
        """Execute a DETECT_MINES intent.

        Engineer squad attempts to detect mines in the area.
        Detected mines are marked on the map for friendly units.
        """
        unit = self._get_unit(intent.unit_id)
        if unit is None:
            return False

        if self.game_map is None:
            self._logger.warning("No game map available for mine detection")
            return False

        # Attempt detection
        detected = self._mine_warfare_system.detect_mines(unit, self.game_map)

        if detected:
            event = {
                "unit_id": intent.unit_id,
                "action": "mines_detected",
                "count": len(detected),
                "positions": [(m.position.x, m.position.y) for m in detected],
                "timestamp": time.time(),
            }
            self.event_bus.publish(event)
            self._logger.info(f"Unit {intent.unit_id} detected {len(detected)} mines")

        return True
