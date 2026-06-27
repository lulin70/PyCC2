"""Combat Service

Orchestrates combat operations by coordinating domain combat systems.
This service does NOT contain business rules - it delegates to domain layer.
"""

import logging
import math
from dataclasses import dataclass, replace
from enum import Enum, auto
from typing import Any, cast

from pycc2.domain.combat.combat_result import CombatResult
from pycc2.domain.entities.unit import Unit
from pycc2.domain.systems.ballistic import BallisticEngine, ShotResult
from pycc2.domain.systems.combat_resolver import CombatResolver
from pycc2.domain.systems.morale_system import MoraleCalculator
from pycc2.services.event_bus import EventBus
from pycc2.services.event_protocol import (
    UnitAttacked,
    UnitKilled,
    WeaponFired,
)


class AttackAngle(Enum):
    """Attack angle relative to target's facing direction."""

    FRONT = auto()  # 0° ±45°: Full armor
    FLANK_LEFT = auto()  # 45-135°: Side armor
    FLANK_RIGHT = auto()
    REAR = auto()  # 135-225°: Rear armor (weakest)
    FRONT_FLANK = auto()  # Transition zones


@dataclass
class AttackOrder:
    """Command to attack a target unit."""

    attacker_id: str
    target_id: str
    weapon_slot: str = "primary"


class CombatService:
    """Combat orchestration service.

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
        """Initialize the combat service with ballistic, morale, and event dependencies."""
        self.ballistic_engine = ballistic_engine
        self.combat_resolver = combat_resolver
        self.morale_calculator = morale_calculator
        self.event_bus = event_bus
        self._logger = logging.getLogger("pycc2.combat.service")

    def execute_attack(
        self, attacker: Unit, target: Unit, weapon_slot: str = "primary"
    ) -> CombatResult:
        """Execute a full attack sequence from attacker to target.

        Args:
            attacker: The attacking unit
            target: The target unit
            weapon_slot: Which weapon to use ("primary" or "secondary")

        Returns:
            CombatResult with full details of the engagement

        """
        self._logger.info(f"Attack: {attacker.name} -> {target.name} [{weapon_slot}]")

        angle = self.calculate_attack_angle(attacker, target)
        damage_multiplier = self.get_angle_damage_multiplier(angle)

        shot_result = self.ballistic_engine.calculate_shot(attacker, target, weapon_slot)

        if shot_result.hit and damage_multiplier != 1.0:
            adjusted_damage = shot_result.damage_dealt * damage_multiplier
            shot_result = replace(shot_result, damage_dealt=adjusted_damage)
            self._logger.info(
                f"Angle bonus applied: {angle.name} -> {damage_multiplier:.1f}x damage"
            )

        self.event_bus.publish_named(
            "weapon_fired",
            dict(
                WeaponFired(
                    unit_id=attacker.unit_id,
                    weapon_id=weapon_slot,
                    target_id=target.unit_id,
                    hit=shot_result.hit,
                    ammo_remaining=getattr(attacker.weapon, "ammo_remaining", 0),
                )
            ),
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

        damage_applied = target.take_damage(int(shot_result.damage_dealt))
        self.event_bus.publish_named(
            "unit_attacked",
            dict(
                UnitAttacked(
                    attacker_id=attacker.unit_id,
                    target_id=target.unit_id,
                    is_hit=True,
                    damage=float(damage_applied),
                )
            ),
        )

        morale_impact = -max(1, damage_applied // 5)
        if angle == AttackAngle.REAR:
            morale_impact = int(morale_impact * 1.5)
            self._logger.info("Rear attack morale penalty increased")
        target.morale.apply_delta(morale_impact)

        if not target.is_alive:
            self.event_bus.publish(
                UnitKilled(
                    unit_id=target.unit_id,
                    killer_id=attacker.unit_id,
                    position=(target.position_component.x, target.position_component.y),
                    faction=target.faction.name
                    if hasattr(target.faction, "name")
                    else str(target.faction),
                ),
            )
            self._logger.warning(f"Unit eliminated: {target.name}")

        return CombatResult(
            shots_fired=1,
            shots_hit=1,
            total_damage=float(damage_applied),
            target_eliminated=not target.is_alive,
            shot_results=[shot_result],
        )

    def execute_suppression_fire(
        self,
        attacker: Unit,
        target_position: tuple,
        burst_size: int = 3,
    ) -> list[ShotResult]:
        """Execute suppression fire at a position (area denial).

        Args:
            attacker: Firing unit
            target_position: Grid position to suppress
            burst_size: Number of rounds to fire

        Returns:
            List of shot results for each round

        """
        results = []
        ballistic_any = cast(Any, self.ballistic_engine)
        for _ in range(burst_size):
            result = ballistic_any.calculate_suppression_shot(attacker, target_position)
            results.append(result)

        self._logger.info(
            f"Suppression: {attacker.name} fired {burst_size} rounds at {target_position}"
        )
        return results

    def resolve_melee_combat(self, attacker: Unit, defender: Unit) -> CombatResult:
        """Resolve close-quarters melee/tactical combat.

        Args:
            attacker: Attacking unit
            defender: Defending unit

        Returns:
            CombatResult of the melee engagement

        """
        self._logger.warning(f"Melee: {attacker.name} vs {defender.name}")
        base_damage = 15.0
        damage_applied = defender.take_damage(int(base_damage))
        return CombatResult(
            shots_fired=0,
            shots_hit=1,
            total_damage=float(damage_applied),
            target_eliminated=not defender.is_alive,
        )

    def can_engage(self, attacker: Unit, target: Unit) -> tuple[bool, str]:
        """Check if attacker can engage target.

        Returns:
            Tuple of (can_engage, reason_if_not)

        """
        if not attacker.is_alive:
            return False, "Attacker is eliminated"
        if not target.is_alive:
            return False, "Target is already eliminated"
        if attacker.weapon.ammo_remaining <= 0:
            return False, "No ammunition"
        if attacker.faction == target.faction:
            return False, "Cannot engage friendly units"

        distance = self._calculate_distance(attacker, target)
        weapon_range = getattr(attacker.weapon, "max_range", 120) / 10.0

        if distance > weapon_range:
            return False, f"Target out of range ({distance:.1f} > {weapon_range:.1f})"

        return True, "Can engage"

    def _calculate_distance(self, unit_a: Unit, unit_b: Unit) -> float:
        """Calculate grid distance between two units."""
        dx = unit_a.position_component.x - unit_b.position_component.x
        dy = unit_a.position_component.y - unit_b.position_component.y
        return (dx**2 + dy**2) ** 0.5

    def calculate_attack_angle(self, attacker: Unit, target: Unit) -> AttackAngle:
        """Calculate attack angle relative to target's facing direction.

        Uses positional difference to determine if attack is from
        front, flank (left/right), or rear.

        Args:
            attacker: The attacking unit
            target: The target unit

        Returns:
            AttackAngle enum value

        """
        dx = attacker.position_component.x - target.position_component.x
        dy = attacker.position_component.y - target.position_component.y

        attack_bearing = math.degrees(math.atan2(dy, dx))
        relative_angle = (attack_bearing - target.facing + 360) % 360

        if relative_angle <= 45 or relative_angle >= 315:
            return AttackAngle.FRONT
        elif 45 < relative_angle <= 135:
            return AttackAngle.FLANK_LEFT
        elif 135 < relative_angle <= 225:
            return AttackAngle.REAR
        else:
            return AttackAngle.FLANK_RIGHT

    def get_angle_damage_multiplier(self, angle: AttackAngle) -> float:
        """Get damage multiplier based on attack angle.

        CC2-style armor penetration model:
        - Front: 1.0x (full frontal armor)
        - Flank: 1.5x (side armor is thinner)
        - Rear: 2.0x (rear armor is weakest)

        Args:
            angle: AttackAngle from calculate_attack_angle()

        Returns:
            Damage multiplier (1.0 to 2.0)

        """
        multipliers = {
            AttackAngle.FRONT: 1.0,
            AttackAngle.FLANK_LEFT: 1.5,
            AttackAngle.FLANK_RIGHT: 1.5,
            AttackAngle.REAR: 2.0,
            AttackAngle.FRONT_FLANK: 1.25,
        }
        return multipliers.get(angle, 1.0)

    def get_angle_description(self, angle: AttackAngle) -> str:
        """Get human-readable description of attack angle."""
        descriptions = {
            AttackAngle.FRONT: "Frontal",
            AttackAngle.FLANK_LEFT: "Left Flank",
            AttackAngle.FLANK_RIGHT: "Right Flank",
            AttackAngle.REAR: "Rear",
            AttackAngle.FRONT_FLANK: "Front-Frontal",
        }
        return descriptions.get(angle, "Unknown")
