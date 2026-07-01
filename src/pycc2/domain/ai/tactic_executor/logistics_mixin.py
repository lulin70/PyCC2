"""Logistics tactics mixin — extracted from tactic_executor.py (D11 SRP split).

Contains logistics/medical/medical tactics execution methods used by the
TacticExecutor facade:
  - ``_execute_scavenge_ammo``: move to source + AmmoPickupSystem.start_pickup
  - ``_execute_heal_wounded``: medic moves to patient + heals per tick
  - ``_execute_rally_nco``: NCORallyBehavior.can_rally/rally_unit
  - ``_execute_surrender``: force SURRENDERED state + zero ammo + event
  - ``_execute_capture_vl``: delegates to _execute_move_to

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
from pycc2.domain.entities.unit import UnitType

if TYPE_CHECKING:
    from pycc2.domain.ai.ammo_pickup import AmmoPickupSystem
    from pycc2.domain.ai.squad_degradation import NCORallyBehavior
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.interfaces import IEventPublisher

__all__ = ["LogisticsTacticsMixin"]


class LogisticsTacticsMixin:
    """Logistics tactic execution methods. Inherited by the TacticExecutor facade,
    not instantiated directly."""

    # -- Facade attributes used by logistics methods (no defaults; set by TacticExecutor.__init__) --
    event_bus: IEventPublisher
    game_map: GameMap | None
    nco_rally: NCORallyBehavior | None
    _unit_registry: dict[str, Unit]
    _ammo_pickup: AmmoPickupSystem
    _logger: logging.Logger

    if TYPE_CHECKING:
        # -- Cross-mixin methods provided by other mixins / the facade --
        # Declared as TYPE_CHECKING-only stubs so mypy can verify logistics
        # methods without runtime shadowing (facade is first in MRO; real
        # methods come from MovementTacticsMixin / TacticExecutor).
        def _get_unit(self, unit_id: str) -> Unit | None: ...
        def _execute_move_to(self, intent: TacticIntent) -> bool: ...

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

    def _execute_capture_vl(self, intent: TacticIntent) -> bool:
        """Execute VL capture — move unit to victory point location."""
        unit = self._get_unit(intent.unit_id)
        if unit is None:
            return False
        if intent.target_position is None:
            self._logger.warning(f"Unit {intent.unit_id} capture_vl without target_position")
            return False
        move_intent = TacticIntent(
            unit_id=intent.unit_id,
            tactic_type=TacticType.MOVE_TO,
            target_position=intent.target_position,
            priority=intent.priority,
            path=intent.path,
        )
        return self._execute_move_to(move_intent)
