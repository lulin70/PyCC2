"""Unit command-queue mixin — extracted from unit.py (D12 Phase 4 P0-2 God Class split).

Contains queued-command methods used by the Unit facade:
  - queue_command, get_next_queued_command, has_queued_commands,
    clear_command_queue (queue manipulation).
  - _execute_queued_command (dispatch queued move/attack orders).

This is a mixin — do not instantiate directly. The Unit facade inherits this
mixin and provides all required fields via its dataclass definition.
"""

from __future__ import annotations

import logging
from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.state_machine import StateMachine
    from pycc2.domain.value_objects.tile_coord import TileCoord

__all__ = ["UnitCommandQueueMixin"]


class UnitCommandQueueMixin:
    """Queued-command methods for Unit.

    Inherited by the Unit facade, not instantiated. Provides 5 methods
    covering Shift+right-click command queue manipulation (append/pop/
    clear/execute) for chained move and attack orders.
    """

    # -- Facade fields used by command-queue methods (set by Unit dataclass) --
    _command_queue: deque[dict]
    state_machine: StateMachine

    if TYPE_CHECKING:
        # -- Cross-mixin method provided by UnitMovementMixin via MRO --
        def set_move_target(self, tile: TileCoord) -> None: ...

    # ------------------------------------------------------------------
    # Queue manipulation
    # ------------------------------------------------------------------

    def queue_command(
        self, command_type: str, target_x: float = 0, target_y: float = 0, **kwargs
    ) -> None:
        """Add a command to the execution queue (Shift+right-click)."""
        self._command_queue.append(
            {"type": command_type, "target_x": target_x, "target_y": target_y, **kwargs}
        )

    def get_next_queued_command(self) -> dict | None:
        """Get and remove the next command from the queue."""
        if self._command_queue:
            return self._command_queue.popleft()
        return None

    @property
    def has_queued_commands(self) -> bool:
        """Return True if there are pending commands in the queue."""
        return len(self._command_queue) > 0

    def clear_command_queue(self) -> None:
        """Remove all pending commands from the queue."""
        self._command_queue.clear()

    # ------------------------------------------------------------------
    # Queue execution
    # ------------------------------------------------------------------

    def _execute_queued_command(self, cmd: dict) -> None:
        """Execute the next queued command after current one completes."""
        from pycc2.domain.entities.unit import UnitState

        cmd_type = cmd.get("type", "move")
        if cmd_type == "move":
            tx = cmd.get("target_x", 0)
            ty = cmd.get("target_y", 0)
            from pycc2.domain.value_objects.tile_coord import TileCoord

            self.set_move_target(TileCoord(int(tx), int(ty)))
        elif cmd_type == "attack":
            try:
                self.state_machine.try_transition(UnitState.ATTACKING)
            except (ValueError, RuntimeError) as e:
                logging.warning("Unit state transition to ATTACKING failed: %s", e)
