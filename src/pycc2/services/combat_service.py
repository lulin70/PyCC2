"""
Combat Service

Orchestrates combat operations by coordinating domain combat systems.
This service does NOT contain business rules - it delegates to domain layer.
"""

import logging
from dataclasses import dataclass

from pycc2.domain.combat.combat_result import CombatResult, ShotResult
from pycc2.domain.entities.unit import Unit
from pycc2.domain.systems.ballistic import BallisticEngine
from pycc2.domain.systems.combat_resolver import CombatResolver
from pycc2.domain.systems.morale_sys import MoraleCalculator
from pycc2.services.event_bus import EventBus
from pycc2.services.event_protocol import (
    ShotFiredEvent,
    UnitDamagedEvent,
    UnitEliminatedEvent,
)


@dataclass
class AttackOrder:
    """Command to attack a target unit."""

    attacker_id: str
    target_id: str
    weapon_slot: str = "primary"


class CombatService:
    """
    Combat orchestration service.

    Coordinates between ballistic calculations, damage resolution,
    morale effects, and event publishing.
    """

    def __init__(
        self,
        ballistic_engine: BallisticEngine,
        combat_resolver: CombatResolver,
        morale_calculator: MoraleCalculator,
        event_bus: EventBus,
    ):
        self.ballistic_engine = ballistic_engine
        self.combat_resolver = combat_resolver
        self.morale_calculator = morale_calculator
        self.event_bus = event_bus
        self._logger = logging.getLogger("pycc2.combat.service")

    def execute_attack(
        self, attacker: Unit, target: Unit, weapon_slot: str = "primary"
    ) -> CombatResult:
        """
        Execute a full attack sequence from attacker to target.

        Args:
            attacker: The attacking unit
            target: The target unit
            weapon_slot: Which weapon to use ("primary" or "secondary")

        Returns:
            CombatResult with full details of the engagement
        """
        self._logger.info(f"Attack: {attacker.name} -> {target.name} [{weapon_slot}]")

        shot_result = self.ballistic_engine.calculate_shot(attacker, target, weapon_slot)
        self.event_bus.publish(
            ShotFiredEvent(
                shooter_id=attacker.unit_id,
                target_id=target.unit_id,
                hit=shot_result.hit,
                damage=shot_result.damage_dealt if shot_result.hit else 0,
                position=(target.position_component.x, target.position_component.y),
            )
        )

        if not shot_result.hit:
            self._logger.debug(f"Miss: {attacker.name} missed {target.name}")
            return CombatResult(
                shots_fired=1,
                shots_hit=0,
                total_damage=0,
                target_eliminated=False,
                shot_results=[shot_result],
            )

        damage_result = self.combat_resolver.apply_damage(target, shot_result.damage_dealt)
        self.event_bus.publish(
            UnitDamagedEvent(
                unit_id=target.unit_id,
                damage=damage_result.damage_applied,
                remaining_hp=target.health_component.current_hp,
                source_unit_id=attacker.unit_id,
            )
        )

        morale_impact = self.morale_calculator.calculate_combat_morale_change(
            target,
            damage_taken=damage_result.damage_applied,
            ally_nearby=False,
        )
        target.morale_component.apply_change(morale_impact)

        if not target.is_alive:
            self.event_bus.publish(
                UnitEliminatedEvent(
                    unit_id=target.unit_id,
                    faction=target.faction,
                    position=(target.position_component.x, target.position_component.y),
                )
            )
            self._logger.warning(f"Unit eliminated: {target.name}")

        return CombatResult(
            shots_fired=1,
            shots_hit=1,
            total_damage=damage_result.damage_applied,
            target_eliminated=not target.is_alive,
            shot_results=[shot_result],
            morale_change=morale_impact,
        )

    def execute_suppression_fire(
        self,
        attacker: Unit,
        target_position: tuple,
        burst_size: int = 3,
    ) -> list[ShotResult]:
        """
        Execute suppression fire at a position (area denial).

        Args:
            attacker: Firing unit
            target_position: Grid position to suppress
            burst_size: Number of rounds to fire

        Returns:
            List of shot results for each round
        """
        results = []
        for _ in range(burst_size):
            result = self.ballistic_engine.calculate_suppression_shot(attacker, target_position)
            results.append(result)

        self._logger.info(
            f"Suppression: {attacker.name} fired {burst_size} rounds at {target_position}"
        )
        return results

    def resolve_melee_combat(self, attacker: Unit, defender: Unit) -> CombatResult:
        """
        Resolve close-quarters melee/tactical combat.

        Args:
            attacker: Attacking unit
            defender: Defending unit

        Returns:
            CombatResult of the melee engagement
        """
        self._logger.warning(f"Melee: {attacker.name} vs {defender.name}")
        base_damage = 15.0
        result = self.combat_resolver.apply_damage(defender, base_damage)
        return CombatResult(
            shots_fired=0,
            shots_hit=1,
            total_damage=result.damage_applied,
            target_eliminated=not defender.is_alive,
        )

    def can_engage(self, attacker: Unit, target: Unit) -> tuple[bool, str]:
        """
        Check if attacker can engage target.

        Returns:
            Tuple of (can_engage, reason_if_not)
        """
        if not attacker.is_alive:
            return False, "Attacker is eliminated"
        if not target.is_alive:
            return False, "Target is already eliminated"
        if attacker.ammo <= 0:
            return False, "No ammunition"
        if attacker.faction == target.faction:
            return False, "Cannot engage friendly units"

        distance = self._calculate_distance(attacker, target)
        weapon_range = attacker.weapon_component.range_meters / 10.0

        if distance > weapon_range:
            return False, f"Target out of range ({distance:.1f} > {weapon_range:.1f})"

        return True, "Can engage"

    def _calculate_distance(self, unit_a: Unit, unit_b: Unit) -> float:
        """Calculate grid distance between two units."""
        dx = unit_a.position_component.x - unit_b.position_component.x
        dy = unit_a.position_component.y - unit_b.position_component.y
        return (dx**2 + dy**2) ** 0.5
