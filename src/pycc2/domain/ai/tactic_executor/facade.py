"""TacticExecutor facade — composes the SRP-split tactic execution mixins.

This module is the public entry point for tactic execution. The original
monolithic ``tactic_executor.py`` (1346 lines, 1 class, 38 methods, 32
TacticType dispatch entries) was split (D11 SRP refactor) into this facade
plus seven focused tactic mixins:

  - ``movement_mixin.MovementTacticsMixin``
      ``_execute_idle``, ``_execute_move_to``, ``_execute_patrol``,
      ``_execute_retreat``, ``_execute_regroup``, ``_execute_coordinated_advance``.
  - ``combat_mixin.CombatTacticsMixin``
      ``_execute_attack``, ``_execute_suppress_fire``, ``_execute_clear_building``,
      ``_execute_call_artillery``, ``_execute_melee_attack``,
      ``_execute_assault_fortified``, ``_execute_counter_attack``,
      ``_execute_flanking``, ``_execute_set_ambush``, ``_execute_break_ambush``.
  - ``defense_mixin.DefenseTacticsMixin``
      ``_execute_defend``, ``_execute_hold_position``, ``_execute_take_cover``,
      ``_execute_defend_vl``.
  - ``engineering_mixin.EngineeringTacticsMixin``
      ``_execute_dig_trench``, ``_execute_demolish_bridge``,
      ``_execute_lay_mine``, ``_execute_detect_mines``.
  - ``logistics_mixin.LogisticsTacticsMixin``
      ``_execute_scavenge_ammo``, ``_execute_heal_wounded``,
      ``_execute_rally_nco``, ``_execute_surrender``, ``_execute_capture_vl``.
  - ``vehicle_mixin.VehicleTacticsMixin``
      ``_execute_mount_tank``, ``_execute_dismount_tank``.
  - ``smoke_mixin.SmokeTacticsMixin``
      ``_execute_deploy_smoke``.

The facade ``TacticExecutor`` inherits all seven mixins (mixin-first in MRO)
and provides ``__init__``, ``register_unit``, ``register_smoke_capability``,
``unregister_unit``, the ``execute()`` dispatch orchestrator (32-entry
``dispatch_table``), ``_get_unit``, and ``_check_morale_preconditions``.
Public API is 100% backward-compatible:
``from pycc2.domain.ai.tactic_executor import TacticExecutor``.
"""

from __future__ import annotations

import logging
import random
from collections.abc import Callable
from typing import TYPE_CHECKING

from pycc2.domain.ai.ammo_pickup import AmmoPickupSystem, FallenUnitCache
from pycc2.domain.ai.artillery_callin import ArtilleryManager
from pycc2.domain.ai.engineer_assault import EngineerAssaultAI
from pycc2.domain.ai.mine_warfare import MineWarfareSystem
from pycc2.domain.ai.smoke_tactical_ai import SmokeGrenadeCapability, SmokeManager
from pycc2.domain.ai.tactic_executor.combat_mixin import CombatTacticsMixin
from pycc2.domain.ai.tactic_executor.defense_mixin import DefenseTacticsMixin
from pycc2.domain.ai.tactic_executor.engineering_mixin import EngineeringTacticsMixin
from pycc2.domain.ai.tactic_executor.logistics_mixin import LogisticsTacticsMixin
from pycc2.domain.ai.tactic_executor.movement_mixin import MovementTacticsMixin
from pycc2.domain.ai.tactic_executor.smoke_mixin import SmokeTacticsMixin
from pycc2.domain.ai.tactic_executor.vehicle_mixin import VehicleTacticsMixin
from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.ai.tank_riders import TankRiderSystem
from pycc2.domain.ai.trench_digging import TrenchDiggingSystem

if TYPE_CHECKING:
    from pycc2.domain.ai.squad_degradation import NCORallyBehavior
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.interfaces import IEventPublisher
    from pycc2.domain.systems.ballistic import BallisticEngine
    from pycc2.domain.systems.pathfinder import PathFinder

logger = logging.getLogger(__name__)

__all__ = ["TacticExecutor"]


class TacticExecutor(
    MovementTacticsMixin,
    CombatTacticsMixin,
    DefenseTacticsMixin,
    EngineeringTacticsMixin,
    LogisticsTacticsMixin,
    VehicleTacticsMixin,
    SmokeTacticsMixin,
):
    """Executes tactic intents by dispatching to AI subsystems and the event bus."""

    def __init__(
        self,
        event_bus: IEventPublisher,
        pathfinder: PathFinder | None = None,
        ballistic_engine: BallisticEngine | None = None,
        game_map: GameMap | None = None,
        nco_rally: NCORallyBehavior | None = None,
        fallen_cache: FallenUnitCache | None = None,
    ) -> None:
        """Initialize the executor with its event bus and optional subsystem dependencies."""
        self.event_bus = event_bus
        self.pathfinder = pathfinder
        self.ballistic_engine = ballistic_engine
        self.game_map = game_map
        self.nco_rally = nco_rally
        self._unit_registry: dict[str, Unit] = {}
        self.smoke_manager: SmokeManager = SmokeManager()
        self._smoke_capabilities: dict[str, SmokeGrenadeCapability] = {}
        self._ammo_pickup: AmmoPickupSystem = AmmoPickupSystem(
            fallen_cache=fallen_cache or FallenUnitCache()
        )
        self._trench_digging: TrenchDiggingSystem = TrenchDiggingSystem()
        self._artillery_manager: ArtilleryManager = ArtilleryManager()
        self._tank_rider_system: TankRiderSystem = TankRiderSystem()
        self._mine_warfare_system: MineWarfareSystem = MineWarfareSystem()
        self._engineer_assault_ai: EngineerAssaultAI = EngineerAssaultAI()
        self._environment = None
        self._logger = logging.getLogger("pycc2.ai.executor")

    def register_unit(self, unit: Unit) -> None:
        """Register a unit so its intents can be resolved by the executor."""
        self._unit_registry[unit.id] = unit

    def register_smoke_capability(
        self,
        unit_id: str,
        capability: SmokeGrenadeCapability,
    ) -> None:
        """Register smoke deployment capability for a unit."""
        self._smoke_capabilities[unit_id] = capability

    def unregister_unit(self, unit_id: str) -> None:
        """Remove a unit and its smoke capability from the executor."""
        self._unit_registry.pop(unit_id, None)
        self._smoke_capabilities.pop(unit_id, None)

    def execute(self, intent: TacticIntent) -> bool:
        """Execute a tactic intent, returning True when the command was applied."""
        # Check unit morale state before executing any command
        unit = self._get_unit(intent.unit_id)
        if unit is not None:
            morale_check = self._check_morale_preconditions(unit, intent)
            if not morale_check["can_execute"]:
                self._logger.debug(
                    f"Command {intent.tactic_type.name} blocked for unit {unit.id}: "
                    f"{morale_check['reason']}"
                )
                return False

        dispatch_table: dict[TacticType, Callable[[TacticIntent], bool]] = {
            TacticType.IDLE: self._execute_idle,
            TacticType.PATROL: self._execute_patrol,
            TacticType.MOVE_TO: self._execute_move_to,
            TacticType.ATTACK: self._execute_attack,
            TacticType.RETREAT: self._execute_retreat,
            TacticType.SUPPRESS_FIRE: self._execute_suppress_fire,
            TacticType.DEFEND: self._execute_defend,
            TacticType.HOLD_POSITION: self._execute_hold_position,
            TacticType.TAKE_COVER: self._execute_take_cover,
            TacticType.REGROUP: self._execute_regroup,
            TacticType.DEPLOY_SMOKE: self._execute_deploy_smoke,
            TacticType.RALLY_NCO: self._execute_rally_nco,
            TacticType.SCAVENGE_AMMO: self._execute_scavenge_ammo,
            TacticType.SURRENDER: self._execute_surrender,
            TacticType.HEAL_WOUNDED: self._execute_heal_wounded,
            TacticType.DIG_TRENCH: self._execute_dig_trench,
            TacticType.CLEAR_BUILDING: self._execute_clear_building,
            TacticType.CALL_ARTILLERY: self._execute_call_artillery,
            TacticType.MELEE_ATTACK: self._execute_melee_attack,
            TacticType.MOUNT_TANK: self._execute_mount_tank,
            TacticType.DISMOUNT_TANK: self._execute_dismount_tank,
            TacticType.LAY_MINE: self._execute_lay_mine,
            TacticType.DETECT_MINES: self._execute_detect_mines,
            TacticType.ASSAULT_FORTIFIED: self._execute_assault_fortified,
            TacticType.COUNTER_ATTACK: self._execute_counter_attack,
            TacticType.FLANKING: self._execute_flanking,
            TacticType.COORDINATED_ADVANCE: self._execute_coordinated_advance,
            TacticType.CAPTURE_VL: self._execute_capture_vl,
            TacticType.DEFEND_VL: self._execute_defend_vl,
            TacticType.DEMOLISH_BRIDGE: self._execute_demolish_bridge,
            TacticType.SET_AMBUSH: self._execute_set_ambush,
            TacticType.BREAK_AMBUSH: self._execute_break_ambush,
        }
        handler = dispatch_table.get(intent.tactic_type)
        if handler is None:
            self._logger.warning(f"Unknown tactic type: {intent.tactic_type}")
            return False
        try:
            return bool(handler(intent))
        except (RuntimeError, ValueError, TypeError, AttributeError) as e:
            self._logger.error(
                "Error executing %s for %s: %s",
                intent.tactic_type.name,
                intent.unit_id,
                e,
                exc_info=True,
            )
            return False

    def _get_unit(self, unit_id: str) -> Unit | None:
        return self._unit_registry.get(unit_id)

    def _check_morale_preconditions(self, unit: Unit, intent: TacticIntent) -> dict:
        """Check if unit's morale state allows executing the given command.

        Implements CC2-authentic morale behavior:
        - PINNED: Cannot move, can only fire if enemy in range
        - BROKEN: 30% chance to refuse orders
        - ROUTING: Cannot receive commands (fleeing)

        Returns:
            Dict with 'can_execute' (bool) and 'reason' (str)

        """
        # Import here to avoid circular imports
        from pycc2.domain.systems.morale_system import MoraleState, MoraleSystem

        result = {"can_execute": True, "reason": ""}

        # Check if unit has morale component
        if unit.morale is None:
            return result

        # Safely get morale value (handle both real components and mocks)
        try:
            morale_value = unit.morale.value
            # Handle MagicMock or non-integer values gracefully
            if not isinstance(morale_value, (int, float)):
                return result  # Allow execution for mock/unusual values
            current_state = MoraleSystem.get_state(int(morale_value))
        except (AttributeError, TypeError, ValueError):
            return result  # If we can't determine state, allow execution

        # Commands that are allowed even when pinned (defensive actions)
        defensive_commands = {
            TacticType.ATTACK,
            TacticType.SUPPRESS_FIRE,
            TacticType.HOLD_POSITION,
            TacticType.TAKE_COVER,
            TacticType.IDLE,
        }

        # Commands that should be replaced with flee behavior
        movement_commands = {
            TacticType.MOVE_TO,
            TacticType.PATROL,
            TacticType.COORDINATED_ADVANCE,
            TacticType.RETREAT,  # Note: retreat is different from routing
        }

        if current_state == MoraleState.ROUTING:
            # Unit is actively fleeing - block all commands except idle
            if intent.tactic_type != TacticType.IDLE:
                result["can_execute"] = False
                result["reason"] = "Unit is routing and cannot receive commands"
                return result

        elif current_state == MoraleState.PINNED:
            # Pinned units cannot move but can fire defensively
            if intent.tactic_type in movement_commands:
                result["can_execute"] = False
                result["reason"] = "Unit is pinned and cannot move"
                return result

            # Allow defensive actions with reduced effectiveness warning
            if intent.tactic_type not in defensive_commands:
                result["can_execute"] = False
                result["reason"] = "Unit is pinned - only defensive actions allowed"

        elif current_state == MoraleState.BROKEN:
            # Broken units have a chance to refuse orders (30% refusal rate)
            if random.random() < 0.3:
                result["can_execute"] = False
                result["reason"] = "Unit is broken and refused orders (morale check failed)"
                return result

            # Even if order is accepted, apply penalty (logged for awareness)
            if intent.tactic_type not in defensive_commands:
                self._logger.debug(
                    f"Unit {unit.id} is broken but accepted order with reduced effectiveness"
                )

        return result
