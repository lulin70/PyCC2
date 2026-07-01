"""Defense tactics mixin — extracted from tactic_executor.py (D11 SRP split).

Contains defense-related tactic execution methods used by the TacticExecutor
facade:
  - ``_execute_defend``: log + return True
  - ``_execute_hold_position``: log + return True
  - ``_execute_take_cover``: delegates to _execute_move_to with priority+5
  - ``_execute_defend_vl``: move to VL if not there, then set_movement_mode("defend")

This is a mixin — do not instantiate directly. The TacticExecutor facade
inherits this mixin and provides all required attributes via its __init__.
Class-level attribute declarations below tell mypy which facade fields the
mixin methods rely on.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.interfaces import IEventPublisher

__all__ = ["DefenseTacticsMixin"]


class DefenseTacticsMixin:
    """Defense tactic execution methods. Inherited by the TacticExecutor facade,
    not instantiated directly."""

    # -- Facade attributes used by defense methods (no defaults; set by TacticExecutor.__init__) --
    event_bus: IEventPublisher
    game_map: GameMap | None
    _unit_registry: dict[str, Unit]
    _logger: logging.Logger

    if TYPE_CHECKING:
        # -- Cross-mixin methods provided by other mixins / the facade --
        # Declared as TYPE_CHECKING-only stubs so mypy can verify defense
        # methods without runtime shadowing (facade is first in MRO; real
        # methods come from MovementTacticsMixin / TacticExecutor).
        def _get_unit(self, unit_id: str) -> Unit | None: ...
        def _execute_move_to(self, intent: TacticIntent) -> bool: ...

    def _execute_defend(self, intent: TacticIntent) -> bool:
        unit = self._get_unit(intent.unit_id)
        if unit is None:
            return False
        self._logger.debug(f"Unit {intent.unit_id} defending position")
        return True

    def _execute_hold_position(self, intent: TacticIntent) -> bool:
        unit = self._get_unit(intent.unit_id)
        if unit is None:
            return False
        self._logger.debug(f"Unit {intent.unit_id} holding position")
        return True

    def _execute_take_cover(self, intent: TacticIntent) -> bool:
        unit = self._get_unit(intent.unit_id)
        if unit is None:
            return False
        if intent.target_position is not None:
            move_intent = TacticIntent(
                unit_id=intent.unit_id,
                tactic_type=TacticType.MOVE_TO,
                target_position=intent.target_position,
                priority=intent.priority + 5,
                path=intent.path,
            )
            return self._execute_move_to(move_intent)
        self._logger.debug(f"Unit {intent.unit_id} taking cover at current position")
        return True

    def _execute_defend_vl(self, intent: TacticIntent) -> bool:
        """Execute VL defense — hold position at victory point."""
        unit = self._get_unit(intent.unit_id)
        if unit is None:
            return False
        if intent.target_position is not None:
            current = unit.position.tile_coord
            target = intent.target_position
            if current.x != target.x or current.y != target.y:
                move_intent = TacticIntent(
                    unit_id=intent.unit_id,
                    tactic_type=TacticType.MOVE_TO,
                    target_position=intent.target_position,
                    priority=intent.priority,
                )
                return self._execute_move_to(move_intent)
        unit.set_movement_mode("defend")
        self._logger.debug(f"Unit {intent.unit_id} defending VL at {intent.target_position}")
        return True
