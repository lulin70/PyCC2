"""Vehicle tactics mixin — extracted from tactic_executor.py (D11 SRP split).

Contains vehicle-mounted infantry tactic execution methods used by the
TacticExecutor facade:
  - ``_execute_mount_tank``: TankRiderSystem mount progress + event
  - ``_execute_dismount_tank``: TankRiderSystem dismount (instant if under fire)

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
from pycc2.domain.ai.tank_riders import TankRiderSystem

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.interfaces import IEventPublisher

__all__ = ["VehicleTacticsMixin"]


class VehicleTacticsMixin:
    """Vehicle tactic execution methods. Inherited by the TacticExecutor facade,
    not instantiated directly."""

    # -- Facade attributes used by vehicle methods (no defaults; set by TacticExecutor.__init__) --
    event_bus: IEventPublisher
    game_map: GameMap | None
    _unit_registry: dict[str, Unit]
    _tank_rider_system: TankRiderSystem
    _logger: logging.Logger

    if TYPE_CHECKING:
        # -- Cross-mixin methods provided by other mixins / the facade --
        # Declared as TYPE_CHECKING-only stubs so mypy can verify vehicle
        # methods without runtime shadowing (facade is first in MRO; real
        # methods come from MovementTacticsMixin / TacticExecutor).
        def _get_unit(self, unit_id: str) -> Unit | None: ...
        def _execute_move_to(self, intent: TacticIntent) -> bool: ...

    def _execute_mount_tank(self, intent: TacticIntent) -> bool:
        """Execute a MOUNT_TANK intent.

        Infantry attempts to mount a friendly tank for rapid transport.
        The rider system handles mount progress and state tracking.
        """
        unit = self._get_unit(intent.unit_id)
        if unit is None:
            return False

        tank = self._get_unit(intent.target_unit_id or "") if intent.target_unit_id else None
        if tank is None:
            self._logger.warning(f"MOUNT_TANK for {intent.unit_id} has no target tank")
            return False

        all_units = list(self._unit_registry.values())

        # Check if already riding
        if self._tank_rider_system.is_riding(intent.unit_id):
            self._logger.debug(f"Unit {intent.unit_id} is already riding")
            return True

        # Check mount conditions
        if not self._tank_rider_system.can_mount(unit, tank, all_units):
            # If not in range, move toward the tank
            dist = unit.position.tile_coord.chebyshev_distance(tank.position.tile_coord)
            if dist > 2:
                move_intent = TacticIntent(
                    unit_id=intent.unit_id,
                    tactic_type=TacticType.MOVE_TO,
                    target_position=tank.position.tile_coord,
                    priority=intent.priority,
                )
                return self._execute_move_to(move_intent)
            self._logger.debug(f"Unit {intent.unit_id} cannot mount tank {tank.id}")
            return False

        # Start mounting
        if self._tank_rider_system.start_mount(unit, tank):
            event = {
                "unit_id": intent.unit_id,
                "action": "mount_tank",
                "tank_id": tank.id,
                "position": (
                    tank.position.tile_coord.x,
                    tank.position.tile_coord.y,
                ),
                "timestamp": time.time(),
            }
            self.event_bus.publish(event)
            self._logger.info(f"Unit {intent.unit_id} mounting tank {tank.id}")
            return True

        return False

    def _execute_dismount_tank(self, intent: TacticIntent) -> bool:
        """Execute a DISMOUNT_TANK intent.

        Infantry dismounts from a tank. Can be instant when under fire.
        """
        unit = self._get_unit(intent.unit_id)
        if unit is None:
            return False

        if not self._tank_rider_system.is_riding(intent.unit_id):
            self._logger.debug(f"Unit {intent.unit_id} is not riding a tank")
            return True

        # Check if under fire (instant dismount)
        instant = False
        if intent.target_position is not None:
            # If target_position is set, it means dismount toward that position
            # (likely under fire)
            instant = True

        if self._tank_rider_system.start_dismount(intent.unit_id, instant=instant):
            tank_id = self._tank_rider_system.get_rider_tank(intent.unit_id)
            event = {
                "unit_id": intent.unit_id,
                "action": "dismount_tank",
                "tank_id": tank_id,
                "instant": instant,
                "timestamp": time.time(),
            }
            self.event_bus.publish(event)
            self._logger.info(
                f"Unit {intent.unit_id} dismounting from tank {'(instant)' if instant else ''}"
            )
            return True

        return False
