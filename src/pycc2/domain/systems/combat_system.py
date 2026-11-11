"""Combat System - Sprint 3 Day 13 FUNC-06.

Manages unit combat: auto-attack, damage calculation, death handling.
Supports attack range detection, target acquisition, and kill notifications.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from enum import Enum, auto

logger = logging.getLogger(__name__)


class CombatState(Enum):
    """Unit combat states."""

    IDLE = auto()
    ATTACKING = auto()
    DEAD = auto()


@dataclass
class SimpleCombatUnit:
    """Simplified unit for combat system.

    Attributes:
        id: Unit identifier
        faction: Faction ID (for ally/enemy detection)
        position_x: X position (pixels)
        position_y: Y position (pixels)
        hp: Current hit points
        max_hp: Maximum hit points
        attack_damage: Damage per attack
        attack_range: Attack range (pixels)
        attack_cooldown: Cooldown between attacks (seconds)
        combat_state: Current combat state
        current_target_id: ID of current attack target
        cooldown_timer: Time until next attack allowed (seconds)
    """

    id: str
    faction: str
    position_x: float
    position_y: float
    hp: int
    max_hp: int
    attack_damage: int = 10
    attack_range: float = 100.0
    attack_cooldown: float = 1.0
    combat_state: CombatState = CombatState.IDLE
    current_target_id: str | None = None
    cooldown_timer: float = 0.0

    def is_alive(self) -> bool:
        """Check if unit is alive."""
        return self.hp > 0 and self.combat_state != CombatState.DEAD

    def is_enemy(self, other: SimpleCombatUnit) -> bool:
        """Check if another unit is an enemy."""
        return self.faction != other.faction

    def distance_to(self, other: SimpleCombatUnit) -> float:
        """Calculate distance to another unit."""
        dx = other.position_x - self.position_x
        dy = other.position_y - self.position_y
        return math.sqrt(dx**2 + dy**2)

    def can_attack(self, target: SimpleCombatUnit) -> bool:
        """Check if this unit can attack target.

        Args:
            target: Potential target

        Returns:
            True if can attack (alive, enemy, in range, cooldown ready)
        """
        if not self.is_alive() or not target.is_alive():
            return False

        if not self.is_enemy(target):
            return False

        if self.distance_to(target) > self.attack_range:
            return False

        return self.cooldown_timer <= 0.0

    def take_damage(self, damage: int) -> bool:
        """Take damage and return if unit died.

        Args:
            damage: Damage amount

        Returns:
            True if unit died from this damage
        """
        self.hp = max(0, self.hp - damage)

        if self.hp == 0:
            self.combat_state = CombatState.DEAD
            self.current_target_id = None
            return True

        return False


class CombatSystem:
    """Manages combat between units.

    Responsibilities:
    - Find enemies in attack range
    - Execute attacks (damage calculation)
    - Handle unit death
    - Track attack cooldowns

    Attributes:
        units: List of all combat units
        attack_notifications: List of (attacker_id, target_id, damage) events
        death_notifications: List of unit_id that died this frame
    """

    def __init__(self):
        """Initialize combat system."""
        self.units: list[SimpleCombatUnit] = []
        self.attack_notifications: list[tuple[str, str, int]] = []
        self.death_notifications: list[str] = []

    def add_unit(self, unit: SimpleCombatUnit) -> None:
        """Add unit to combat system.

        Args:
            unit: Unit to add
        """
        self.units.append(unit)
        logger.info(f"Added unit {unit.id} to combat system")

    def remove_unit(self, unit_id: str) -> bool:
        """Remove unit from combat system.

        Args:
            unit_id: Unit ID to remove

        Returns:
            True if unit was removed
        """
        for i, unit in enumerate(self.units):
            if unit.id == unit_id:
                self.units.pop(i)
                logger.info(f"Removed unit {unit_id} from combat system")
                return True
        return False

    def find_nearest_enemy(self, unit: SimpleCombatUnit) -> SimpleCombatUnit | None:
        """Find nearest enemy in attack range.

        Args:
            unit: Unit to find enemy for

        Returns:
            Nearest enemy unit or None
        """
        nearest = None
        nearest_distance = float("inf")

        for other in self.units:
            if not other.is_alive() or not unit.is_enemy(other):
                continue

            distance = unit.distance_to(other)
            if distance <= unit.attack_range and distance < nearest_distance:
                nearest = other
                nearest_distance = distance

        return nearest

    def update_unit_combat(self, unit: SimpleCombatUnit, delta_time: float) -> None:
        """Update single unit's combat state.

        Args:
            unit: Unit to update
            delta_time: Time elapsed (seconds)
        """
        if not unit.is_alive():
            return

        # Update cooldown
        if unit.cooldown_timer > 0.0:
            unit.cooldown_timer = max(0.0, unit.cooldown_timer - delta_time)

        # Validate current target (check if still valid, not on cooldown)
        if unit.current_target_id:
            target = self.get_unit_by_id(unit.current_target_id)
            # Only clear target if dead or out of range (not due to cooldown)
            if not target or not target.is_alive() or unit.distance_to(target) > unit.attack_range:
                unit.current_target_id = None
                unit.combat_state = CombatState.IDLE

        # Find new target if none
        if not unit.current_target_id:
            nearest_enemy = self.find_nearest_enemy(unit)
            if nearest_enemy:
                unit.current_target_id = nearest_enemy.id
                unit.combat_state = CombatState.ATTACKING
            else:
                unit.combat_state = CombatState.IDLE
                return

        # Execute attack if cooldown ready
        if unit.current_target_id and unit.cooldown_timer == 0.0:
            target = self.get_unit_by_id(unit.current_target_id)
            if target and unit.can_attack(target):
                self.execute_attack(unit, target)

    def execute_attack(self, attacker: SimpleCombatUnit, target: SimpleCombatUnit) -> None:
        """Execute attack from attacker to target.

        Args:
            attacker: Attacking unit
            target: Target unit
        """
        damage = attacker.attack_damage
        died = target.take_damage(damage)

        # Reset attacker cooldown
        attacker.cooldown_timer = attacker.attack_cooldown

        # Record notification
        self.attack_notifications.append((attacker.id, target.id, damage))
        logger.debug(
            f"{attacker.id} attacked {target.id} for {damage} damage (hp: {target.hp}/{target.max_hp})"
        )

        if died:
            self.death_notifications.append(target.id)
            logger.info(f"{target.id} died")

    def update(self, delta_time: float) -> None:
        """Update all units' combat state.

        Args:
            delta_time: Time elapsed (seconds)
        """
        # Clear notifications from last frame
        self.attack_notifications.clear()
        self.death_notifications.clear()

        # Update each unit
        for unit in self.units:
            self.update_unit_combat(unit, delta_time)

    def get_unit_by_id(self, unit_id: str) -> SimpleCombatUnit | None:
        """Get unit by ID.

        Args:
            unit_id: Unit ID

        Returns:
            Unit or None
        """
        for unit in self.units:
            if unit.id == unit_id:
                return unit
        return None

    def get_alive_units(self) -> list[SimpleCombatUnit]:
        """Get all alive units.

        Returns:
            List of alive units
        """
        return [u for u in self.units if u.is_alive()]

    def get_dead_units(self) -> list[SimpleCombatUnit]:
        """Get all dead units.

        Returns:
            List of dead units
        """
        return [u for u in self.units if not u.is_alive()]
