"""Movement tactics mixin — extracted from tactic_executor.py (D11 SRP split).

Contains movement-related tactic execution methods used by the TacticExecutor
facade:
  - ``_execute_idle``: idle log + return True
  - ``_execute_move_to``: pathfinding + unit.move_to_tile + event publish
  - ``_execute_patrol``: delegates to _execute_move_to with target_position
  - ``_execute_retreat``: computes safe_pos and delegates to _execute_move_to
  - ``_execute_regroup``: delegates to _execute_move_to with priority+7
  - ``_execute_coordinated_advance``: delegates to _execute_move_to

This is a mixin — do not instantiate directly. The TacticExecutor facade
inherits this mixin and provides all required attributes via its __init__.
Class-level attribute declarations below tell mypy which facade fields the
mixin methods rely on.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.value_objects.tile_coord import TileCoord

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.interfaces import IEventPublisher
    from pycc2.domain.systems.pathfinder import PathFinder

__all__ = ["MovementTacticsMixin"]


class MovementTacticsMixin:
    """Movement tactic execution methods. Inherited by the TacticExecutor facade,
    not instantiated directly."""

    # -- Facade attributes used by movement methods (no defaults; set by TacticExecutor.__init__) --
    event_bus: IEventPublisher
    pathfinder: PathFinder | None
    game_map: GameMap | None
    _unit_registry: dict[str, Unit]
    _logger: logging.Logger

    if TYPE_CHECKING:
        # -- Cross-mixin method provided by the TacticExecutor facade --
        # Declared as TYPE_CHECKING-only stub so mypy can verify movement
        # methods without runtime shadowing (facade is first in MRO; real
        # method comes from TacticExecutor).
        def _get_unit(self, unit_id: str) -> Unit | None: ...

    def _execute_idle(self, intent: TacticIntent) -> bool:
        unit = self._get_unit(intent.unit_id)
        if unit is None:
            return False
        self._logger.debug(f"Unit {intent.unit_id} is idling")
        return True

    def _execute_move_to(self, intent: TacticIntent) -> bool:
        unit = self._get_unit(intent.unit_id)
        if unit is None or intent.target_position is None:
            return False
        from_tile = (unit.position.tile_coord.x, unit.position.tile_coord.y)
        to_tile = (intent.target_position.x, intent.target_position.y)
        if intent.path is None and self.pathfinder is not None and self.game_map is not None:
            intent.path = self.pathfinder.find_path(
                unit.position.tile_coord, intent.target_position, self.game_map
            )
        if intent.path and len(intent.path) > 1:
            next_tile = intent.path[1]
            unit.move_to_tile(next_tile)
            intent.path = intent.path[1:]
        else:
            unit.move_to_tile(intent.target_position)
        event = {
            "unit_id": intent.unit_id,
            "from_tile": from_tile,
            "to_tile": to_tile,
            "timestamp": time.time(),
        }
        self.event_bus.publish(event)
        self._logger.debug(f"Unit {intent.unit_id} moved to {to_tile}")
        return True

    def _execute_patrol(self, intent: TacticIntent) -> bool:
        unit = self._get_unit(intent.unit_id)
        if unit is None:
            return False
        if intent.target_position is not None:
            move_intent = TacticIntent(
                unit_id=intent.unit_id,
                tactic_type=TacticType.MOVE_TO,
                target_position=intent.target_position,
                priority=intent.priority,
                path=intent.path,
            )
            return self._execute_move_to(move_intent)
        self._logger.debug(f"Unit {intent.unit_id} patrolling without destination")
        return True

    def _execute_retreat(self, intent: TacticIntent) -> bool:
        unit = self._get_unit(intent.unit_id)
        if unit is None:
            return False
        if intent.target_position is not None:
            move_intent = TacticIntent(
                unit_id=intent.unit_id,
                tactic_type=TacticType.MOVE_TO,
                target_position=intent.target_position,
                priority=intent.priority + 10,
                path=intent.path,
            )
            return self._execute_move_to(move_intent)
        current = unit.position.tile_coord
        safe_pos = TileCoord(current.x - 3, current.y - 3)
        move_intent = TacticIntent(
            unit_id=intent.unit_id,
            tactic_type=TacticType.MOVE_TO,
            target_position=safe_pos,
            priority=intent.priority + 10,
        )
        return self._execute_move_to(move_intent)

    def _execute_regroup(self, intent: TacticIntent) -> bool:
        unit = self._get_unit(intent.unit_id)
        if unit is None:
            return False
        if intent.target_position is not None:
            move_intent = TacticIntent(
                unit_id=intent.unit_id,
                tactic_type=TacticType.MOVE_TO,
                target_position=intent.target_position,
                priority=intent.priority + 7,
                path=intent.path,
            )
            return self._execute_move_to(move_intent)
        self._logger.debug(f"Unit {intent.unit_id} regrouping")
        return True

    def _execute_coordinated_advance(self, intent: TacticIntent) -> bool:
        """Execute coordinated advance — move to target while maintaining formation."""
        unit = self._get_unit(intent.unit_id)
        if unit is None:
            return False
        if intent.target_position is None:
            self._logger.debug(f"Unit {intent.unit_id} advancing without destination")
            return True
        move_intent = TacticIntent(
            unit_id=intent.unit_id,
            tactic_type=TacticType.MOVE_TO,
            target_position=intent.target_position,
            priority=intent.priority,
            path=intent.path,
        )
        return self._execute_move_to(move_intent)
