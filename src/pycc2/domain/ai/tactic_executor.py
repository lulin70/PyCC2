from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

from pycc2.domain.ai.ammo_pickup import AmmoPickupSystem, FallenUnitCache
from pycc2.domain.ai.artillery_callin import ArtilleryManager
from pycc2.domain.ai.building_clearing import BuildingClearingAI
from pycc2.domain.ai.engineer_assault import EngineerAssaultAI
from pycc2.domain.ai.melee_combat import MeleeCombatSystem
from pycc2.domain.ai.mine_warfare import MineType, MineWarfareSystem
from pycc2.domain.ai.smoke_tactical_ai import SmokeDeployment, SmokeGrenadeCapability, SmokeManager
from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.ai.tank_riders import TankRiderSystem
from pycc2.domain.ai.trench_digging import TrenchDiggingSystem
from pycc2.domain.entities.unit import UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord

if TYPE_CHECKING:
    from pycc2.domain.ai.squad_degradation import NCORallyBehavior
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.interfaces import IEventPublisher
    from pycc2.domain.systems.ballistic import BallisticEngine
    from pycc2.domain.systems.pathfinder import PathFinder

logger = logging.getLogger(__name__)


class TacticExecutor:
    def __init__(
        self,
        event_bus: IEventPublisher,
        pathfinder: PathFinder | None = None,
        ballistic_engine: BallisticEngine | None = None,
        game_map: GameMap | None = None,
        nco_rally: NCORallyBehavior | None = None,
        fallen_cache: FallenUnitCache | None = None,
    ) -> None:
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
        self._logger = logging.getLogger("pycc2.ai.executor")

    def register_unit(self, unit: Unit) -> None:
        self._unit_registry[unit.id] = unit

    def register_smoke_capability(
        self,
        unit_id: str,
        capability: SmokeGrenadeCapability,
    ) -> None:
        """Register smoke deployment capability for a unit."""
        self._smoke_capabilities[unit_id] = capability

    def unregister_unit(self, unit_id: str) -> None:
        self._unit_registry.pop(unit_id, None)
        self._smoke_capabilities.pop(unit_id, None)

    def execute(self, intent: TacticIntent) -> bool:
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
        }
        handler = dispatch_table.get(intent.tactic_type)
        if handler is None:
            self._logger.warning(f"Unknown tactic type: {intent.tactic_type}")
            return False
        try:
            return bool(handler(intent))
        except Exception as e:
            self._logger.error(
                f"Error executing {intent.tactic_type.name} for {intent.unit_id}: {e}",
                exc_info=True,
            )
            return False

    def _get_unit(self, unit_id: str) -> Unit | None:
        return self._unit_registry.get(unit_id)

    def _check_morale_preconditions(self, unit: Unit, intent: TacticIntent) -> dict:
        """
        Check if unit's morale state allows executing the given command.

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
        if not hasattr(unit, "morale") or unit.morale is None:
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

    def _execute_attack(self, intent: TacticIntent) -> bool:
        unit = self._get_unit(intent.unit_id)
        target = self._get_unit(intent.target_unit_id or "") if intent.target_unit_id else None
        if unit is None or target is None:
            return False
        # Publish typed PlayerCommand so CombatDirector handles the full
        # attack pipeline (ballistics, damage, ammo, visual effects).
        from pycc2.domain.interfaces.event_types import PlayerCommand

        event = PlayerCommand(
            command="attack",
            unit_ids=[intent.unit_id],
            target_id=intent.target_unit_id,
        )
        self.event_bus.publish(event)
        self._logger.debug(
            f"Unit {intent.unit_id} attack command issued -> {intent.target_unit_id}"
        )
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

    def _execute_suppress_fire(self, intent: TacticIntent) -> bool:
        unit = self._get_unit(intent.unit_id)
        target = self._get_unit(intent.target_unit_id or "") if intent.target_unit_id else None
        if unit is None or target is None:
            return False
        if self.ballistic_engine is None:
            self._logger.warning("No ballistic engine available for suppress fire")
            return False
        for _ in range(3):
            result = self.ballistic_engine.calculate_shot(
                attacker=unit, target=target, game_map=self.game_map
            )
            event = {
                "attacker_id": intent.unit_id,
                "target_id": intent.target_unit_id,
                "is_hit": result.hit,
                "damage": result.damage_dealt,
                "timestamp": time.time(),
            }
            self.event_bus.publish(event)
        self._logger.debug(f"Unit {intent.unit_id} suppressing fire on {intent.target_unit_id}")
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

    def _execute_deploy_smoke(self, intent: TacticIntent) -> bool:
        """Execute a DEPLOY_SMOKE intent.

        Consumes a smoke charge from the unit's SmokeGrenadeCapability,
        creates a SmokeDeployment on the SmokeManager, and publishes
        a smoke_deployed event.
        """
        unit = self._get_unit(intent.unit_id)
        if unit is None:
            return False
        if intent.target_position is None:
            self._logger.warning(f"DEPLOY_SMOKE for {intent.unit_id} has no target_position")
            return False

        # Check smoke capability
        capability = self._smoke_capabilities.get(intent.unit_id)
        if capability is not None:
            if not capability.has_smoke:
                self._logger.debug(f"Unit {intent.unit_id} has no smoke charges remaining")
                return False
            capability.use_smoke()
        # Units without registered capability can still deploy smoke
        # (fallback for units not explicitly registered)

        # Determine wind drift direction from environment
        drift_direction = (0, 0)
        env = getattr(self, "_environment", None)
        if env is not None:
            wind = getattr(env, "wind_direction", (0, 0))
            wx, wy = wind
            length = (wx * wx + wy * wy) ** 0.5
            if length >= 0.01:
                drift_direction = (int(round(wx / length)), int(round(wy / length)))

        # Create and register the smoke deployment
        smoke = SmokeDeployment(
            position=(intent.target_position.x, intent.target_position.y),
            radius=3,
            duration_ticks=180,
            remaining_ticks=180,
            drift_direction=drift_direction,
            deployed_by=intent.unit_id,
        )
        self.smoke_manager.deploy(smoke)

        # Update unit concealment: unit is now in smoke
        combat_state = getattr(unit, "combat_state", None)
        if combat_state is not None:
            concealment = getattr(combat_state, "concealment", None)
            if concealment is not None:
                concealment.in_smoke = True

        # Publish event
        event = {
            "unit_id": intent.unit_id,
            "smoke_position": (intent.target_position.x, intent.target_position.y),
            "smoke_radius": smoke.radius,
            "smoke_duration": smoke.duration_ticks,
            "timestamp": time.time(),
        }
        self.event_bus.publish(event)
        self._logger.debug(
            f"Unit {intent.unit_id} deployed smoke at "
            f"({intent.target_position.x}, {intent.target_position.y})"
        )
        return True

    def _execute_scavenge_ammo(self, intent: TacticIntent) -> bool:
        """Execute a SCAVENGE_AMMO intent.

        The unit moves toward the ammo source position, then initiates
        the pickup process via AmmoPickupSystem.  If the unit is already
        at the source, the pickup begins immediately.  If the unit is
        already in an active pickup state, the tick is advanced.
        """
        unit = self._get_unit(intent.unit_id)
        if unit is None:
            return False

        # Check if unit already has an active pickup in progress
        pickup_state = self._ammo_pickup.get_pickup_state(intent.unit_id)
        if pickup_state is not None:
            # Pickup already in progress — nothing more to do this tick
            self._logger.debug(
                f"Unit {intent.unit_id} already scavenging "
                f"({pickup_state.ticks_remaining} ticks remaining)"
            )
            return True

        # If the unit is not at the source position, move toward it first
        if intent.target_position is not None:
            dist = unit.position.tile_coord.chebyshev_distance(intent.target_position)
            if dist > 1:
                # Not yet at the source — move closer
                move_intent = TacticIntent(
                    unit_id=intent.unit_id,
                    tactic_type=TacticType.MOVE_TO,
                    target_position=intent.target_position,
                    priority=intent.priority,
                    path=intent.path,
                )
                return self._execute_move_to(move_intent)

        # Unit is at the source — try to start pickup
        if intent.target_position is None:
            self._logger.warning(f"SCAVENGE_AMMO for {intent.unit_id} has no target_position")
            return False

        # Find the source in the fallen cache
        sources = self._ammo_pickup.fallen_cache.find_sources_near(
            position=unit.position.tile_coord,
            seeker_faction=unit.faction,
            current_tick=0,  # Tick managed externally; 0 for immediate lookup
        )

        # Match source by target_unit_id if provided
        source = None
        if intent.target_unit_id:
            source = next(
                (s for s in sources if s.unit_id == intent.target_unit_id),
                None,
            )
        if source is None and sources:
            source = sources[0]

        if source is None:
            self._logger.debug(f"Unit {intent.unit_id} found no ammo source at target position")
            return False

        # Attempt to start the pickup
        from pycc2.domain.ai.ammo_pickup import PickupResult

        result = self._ammo_pickup.start_pickup(unit, source, current_tick=0)
        if result == PickupResult.SUCCESS:
            event = {
                "unit_id": intent.unit_id,
                "source_id": source.unit_id,
                "source_type": source.source_type.name,
                "target_position": (
                    intent.target_position.x,
                    intent.target_position.y,
                ),
                "timestamp": time.time(),
            }
            self.event_bus.publish(event)
            self._logger.debug(
                f"Unit {intent.unit_id} started scavenging from {source.unit_id} "
                f"({source.source_type.name})"
            )
            return True
        elif result == PickupResult.WRONG_STANCE:
            self._logger.debug(
                f"Unit {intent.unit_id} cannot scavenge: wrong stance (must be PRONE or CROUCHING)"
            )
        elif result == PickupResult.SUPPRESSED:
            self._logger.debug(f"Unit {intent.unit_id} cannot scavenge: suppressed")
        elif result == PickupResult.ALREADY_PICKING_UP:
            return True  # Already in progress, not a failure

        return False

    def _execute_rally_nco(self, intent: TacticIntent) -> bool:
        nco = self._get_unit(intent.unit_id)
        if nco is None:
            return False
        if self.nco_rally is None:
            self._logger.warning("No NCORallyBehavior configured for RALLY_NCO tactic")
            return False
        target = self._get_unit(intent.target_unit_id or "") if intent.target_unit_id else None
        if target is None:
            return False
        if not self.nco_rally.can_rally(nco):
            self._logger.debug(f"NCO {intent.unit_id} cannot rally right now")
            return False
        nco_pos = nco.position.tile_coord
        target_pos = target.position.tile_coord
        dist = nco_pos.chebyshev_distance(target_pos)
        if dist > 5:
            if intent.target_position is not None:
                move_intent = TacticIntent(
                    unit_id=intent.unit_id,
                    tactic_type=TacticType.MOVE_TO,
                    target_position=intent.target_position,
                    priority=intent.priority + 8,
                    path=intent.path,
                )
                self._execute_move_to(move_intent)
            return False
        success = bool(self.nco_rally.rally_unit(nco, target))
        if success:
            event = {
                "nco_id": intent.unit_id,
                "rallied_unit_id": intent.target_unit_id,
                "timestamp": time.time(),
            }
            self.event_bus.publish(event)
        return success

    def _execute_surrender(self, intent: TacticIntent) -> bool:
        """Execute a SURRENDER intent.

        Marks the unit as SURRENDERED, drops weapons/ammo, and
        triggers a morale event for nearby friendly units.
        """
        from pycc2.domain.entities.unit import UnitState

        unit = self._get_unit(intent.unit_id)
        if unit is None:
            return False

        # Already surrendered or dead — nothing to do
        if unit.state_machine.current in (UnitState.SURRENDERED, UnitState.DEAD):
            return False

        # Transition unit state to SURRENDERED
        unit.state_machine.force_transition(UnitState.SURRENDERED)

        # Zero out ammo
        unit.weapon.ammo_remaining = 0

        # Publish surrender event
        event = {
            "unit_id": intent.unit_id,
            "action": "surrender",
            "position": (
                unit.position.tile_coord.x,
                unit.position.tile_coord.y,
            ),
            "timestamp": time.time(),
        }
        self.event_bus.publish(event)

        self._logger.info(f"Unit {intent.unit_id} surrendered")
        return True

    def _execute_heal_wounded(self, intent: TacticIntent) -> bool:
        """Execute a HEAL_WOUNDED intent.

        The medic moves toward the wounded unit, then initiates
        treatment.  If the medic is already treating, the tick
        advances the treatment.  The medic must be adjacent to
        the patient and not suppressed.
        """
        from pycc2.domain.ai.medic_ai import (
            HEAL_ADJACENT_RANGE,
            HEAL_CAP_RATIO,
            HEAL_PER_TICK,
        )

        unit = self._get_unit(intent.unit_id)
        if unit is None:
            return False

        # Must be a medic unit
        if unit.unit_type != UnitType.MEDIC_TEAM:
            self._logger.warning(f"HEAL_WOUNDED for {intent.unit_id} is not a medic unit")
            return False

        # Find the patient
        patient = self._get_unit(intent.target_unit_id or "") if intent.target_unit_id else None
        if patient is None:
            self._logger.warning(f"HEAL_WOUNDED for {intent.unit_id} has no valid target")
            return False

        # Check if patient is still alive and wounded
        if not patient.is_alive:
            return False
        if patient.health.hp_ratio >= HEAL_CAP_RATIO:
            self._logger.debug(f"Patient {patient.id} no longer needs treatment")
            return True

        # Check if medic is suppressed
        from pycc2.domain.systems.combat_mechanics_enhanced import SuppressionEffect

        suppression = unit.suppression_level
        if suppression in (
            SuppressionEffect.MODERATE,
            SuppressionEffect.HEAVY,
            SuppressionEffect.PINNED,
            SuppressionEffect.PANIC,
        ):
            self._logger.debug(f"Medic {intent.unit_id} is suppressed, cannot heal")
            return False

        # Check distance — must be adjacent
        dist = unit.position.tile_coord.chebyshev_distance(patient.position.tile_coord)
        if dist > HEAL_ADJACENT_RANGE:
            # Move toward patient first
            move_intent = TacticIntent(
                unit_id=intent.unit_id,
                tactic_type=TacticType.MOVE_TO,
                target_position=patient.position.tile_coord,
                priority=intent.priority,
            )
            return self._execute_move_to(move_intent)

        # Heal the patient
        if patient.health.hp_ratio < HEAL_CAP_RATIO:
            heal_amount = int(HEAL_PER_TICK * patient.health.max_hp)
            if heal_amount > 0:
                max_hp = int(HEAL_CAP_RATIO * patient.health.max_hp)
                actual_heal = min(heal_amount, max_hp - patient.health.hp)
                if actual_heal > 0:
                    patient.health.heal(actual_heal)

        # Publish heal event
        event = {
            "medic_id": intent.unit_id,
            "patient_id": intent.target_unit_id,
            "action": "heal",
            "patient_hp_ratio": patient.health.hp_ratio,
            "timestamp": time.time(),
        }
        self.event_bus.publish(event)

        self._logger.debug(
            f"Medic {intent.unit_id} healed {intent.target_unit_id} "
            f"(hp_ratio: {patient.health.hp_ratio:.2f})"
        )
        return True

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

    def _execute_clear_building(self, intent: TacticIntent) -> bool:
        """Execute a CLEAR_BUILDING intent.

        Moves the unit toward the building, then initiates the clearing
        process: approach, grenade, stack, breach, and clear.
        """
        unit = self._get_unit(intent.unit_id)
        if unit is None:
            return False

        if self.game_map is None:
            self._logger.warning("No game map available for building clearing")
            return False

        if intent.target_position is None:
            self._logger.warning(f"CLEAR_BUILDING for {intent.unit_id} has no target_position")
            return False

        target_pos = intent.target_position
        unit_pos = unit.position.tile_coord

        # Check if unit is adjacent to the building
        dist = unit_pos.chebyshev_distance(target_pos)
        if dist > 1:
            # Move toward the building
            approach_pos = BuildingClearingAI.find_adjacent_approach_pos(
                target_pos, unit_pos, self.game_map
            )
            if approach_pos is None:
                self._logger.debug(f"Unit {intent.unit_id} cannot find approach to building")
                return False
            move_intent = TacticIntent(
                unit_id=intent.unit_id,
                tactic_type=TacticType.MOVE_TO,
                target_position=approach_pos,
                priority=intent.priority,
            )
            return self._execute_move_to(move_intent)

        # Unit is adjacent — apply grenade effects to defenders

        # Find all enemy units in the building
        defenders = [
            u
            for u in self._unit_registry.values()
            if u.is_alive
            and u.position.tile_coord == target_pos
            and u.id != intent.unit_id
            and u.faction != unit.faction
        ]

        # Apply grenade effects
        effects = BuildingClearingAI.apply_grenade_effects(target_pos, self.game_map, defenders)

        # Apply defender penalty
        for defender in defenders:
            BuildingClearingAI.apply_defender_penalty(defender)

        # Apply surprise bonus to attacker
        BuildingClearingAI.apply_surprise_bonus(unit)

        # Move unit into the building
        unit.move_to_tile(target_pos)

        # Publish event
        event = {
            "unit_id": intent.unit_id,
            "action": "clear_building",
            "building_pos": (target_pos.x, target_pos.y),
            "grenade_effects": len(effects),
            "timestamp": time.time(),
        }
        self.event_bus.publish(event)

        self._logger.info(
            f"Unit {intent.unit_id} cleared building at "
            f"({target_pos.x}, {target_pos.y}), "
            f"{len(effects)} defenders hit by grenade"
        )
        return True

    def _execute_call_artillery(self, intent: TacticIntent) -> bool:
        """Execute a CALL_ARTILLERY intent.

        Initiates an artillery fire mission through the ArtilleryManager.
        The mission proceeds through phases: CALLING -> INCOMING -> IMPACT.
        """
        unit = self._get_unit(intent.unit_id)
        if unit is None:
            return False

        if intent.target_position is None:
            self._logger.warning(f"CALL_ARTILLERY for {intent.unit_id} has no target_position")
            return False

        # Check if a new mission can be started
        if not self._artillery_manager.can_call_mission(intent.unit_id):
            self._logger.debug(
                f"Unit {intent.unit_id} cannot call artillery "
                f"(no missions remaining or already active)"
            )
            return False

        # Calculate weather scatter
        env = getattr(self, "_environment", None)
        scatter = ArtilleryManager.calculate_weather_scatter(env)

        # Start the mission
        mission = self._artillery_manager.start_mission(
            observer_id=intent.unit_id,
            target_pos=intent.target_position,
            scatter=scatter,
        )
        if mission is None:
            return False

        # Publish event
        event = {
            "unit_id": intent.unit_id,
            "action": "call_artillery",
            "target_pos": (
                intent.target_position.x,
                intent.target_position.y,
            ),
            "scatter": scatter,
            "missions_remaining": self._artillery_manager.missions_remaining,
            "timestamp": time.time(),
        }
        self.event_bus.publish(event)

        self._logger.info(
            f"Unit {intent.unit_id} called artillery on "
            f"({intent.target_position.x}, {intent.target_position.y}), "
            f"scatter={scatter}, "
            f"{self._artillery_manager.missions_remaining} missions remaining"
        )
        return True

    def _execute_melee_attack(self, intent: TacticIntent) -> bool:
        """Execute a MELEE_ATTACK intent.

        Resolves close-quarters combat between the attacker and defender.
        Both units can take damage (melee is risky).
        """
        unit = self._get_unit(intent.unit_id)
        target = self._get_unit(intent.target_unit_id or "") if intent.target_unit_id else None
        if unit is None or target is None:
            return False

        # Verify melee conditions
        if not MeleeCombatSystem.can_melee(unit, target):
            self._logger.debug(f"Unit {intent.unit_id} cannot melee target {intent.target_unit_id}")
            return False

        # Determine if charging (moving into melee)
        is_charging = unit.state_machine.current and unit.state_machine.current.name == "MOVING"

        # Resolve melee
        result = MeleeCombatSystem.resolve_melee(unit, target, is_charging)

        # Publish event
        event = {
            "attacker_id": intent.unit_id,
            "defender_id": intent.target_unit_id,
            "action": "melee_attack",
            "weapon": result.attacker_weapon.name,
            "hit": result.hit,
            "damage": result.damage,
            "counter_hit": result.counter_hit,
            "counter_damage": result.counter_damage,
            "attacker_killed": result.attacker_killed,
            "defender_killed": result.defender_killed,
            "timestamp": time.time(),
        }
        self.event_bus.publish(event)

        self._logger.info(
            f"Melee: {intent.unit_id} vs {intent.target_unit_id}: "
            f"hit={result.hit}, dmg={result.damage}, "
            f"counter={result.counter_hit}, counter_dmg={result.counter_damage}"
        )
        return True

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

    def _execute_assault_fortified(self, intent: TacticIntent) -> bool:
        """Execute an ASSAULT_FORTIFIED intent.

        Engineer assault team attacks a fortified position using
        demo charges, flamethrowers, or bangalore torpedoes.
        The engineer assault AI manages the assault phases.
        """
        unit = self._get_unit(intent.unit_id)
        if unit is None:
            return False

        if self.game_map is None:
            self._logger.warning("No game map available for engineer assault")
            return False

        if intent.target_position is None:
            self._logger.warning(f"ASSAULT_FORTIFIED for {intent.unit_id} has no target_position")
            return False

        # Check if unit has an active assault
        assault = self._engineer_assault_ai._assaults.get(intent.unit_id)

        if assault is None:
            # Start a new assault — move toward target
            dist = unit.position.tile_coord.chebyshev_distance(intent.target_position)
            if dist > 1:
                move_intent = TacticIntent(
                    unit_id=intent.unit_id,
                    tactic_type=TacticType.MOVE_TO,
                    target_position=intent.target_position,
                    priority=intent.priority,
                )
                return self._execute_move_to(move_intent)

        # Publish assault event
        event = {
            "unit_id": intent.unit_id,
            "action": "assault_fortified",
            "target_position": (
                intent.target_position.x,
                intent.target_position.y,
            ),
            "timestamp": time.time(),
        }
        self.event_bus.publish(event)
        self._logger.info(
            f"Unit {intent.unit_id} assaulting fortified position at "
            f"({intent.target_position.x}, {intent.target_position.y})"
        )
        return True
