"""Vehicle Crew System - Crew member management for vehicle units.

Implements B10: Vehicle crew with individual members, damage distribution,
and efficiency penalties based on crew casualties.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit


class CrewRole(Enum):
    """Roles within a vehicle crew."""

    COMMANDER = "commander"
    GUNNER = "gunner"
    DRIVER = "driver"
    LOADER = "loader"


class CrewStatus(Enum):
    """Health status of a crew member."""

    ACTIVE = "active"
    WOUNDED = "wounded"
    DEAD = "dead"


@dataclass(slots=True)
class CrewMember:
    """Individual crew member with role-based attributes."""

    name: str
    role: CrewRole
    hp: int = 100
    max_hp: int = 100
    status: CrewStatus = CrewStatus.ACTIVE
    efficiency: float = 1.0
    skills: dict[str, float] = field(
        default_factory=lambda: {
            "aiming": 1.0,
            "driving": 1.0,
            "loading": 1.0,
            "command": 1.0,
        }
    )


@dataclass
class VehicleCrew:
    """
    Manages crew for a vehicle unit.

    Features:
    - Individual crew members with roles and HP
    - Random damage distribution among active crew
    - Role-specific penalties when crew members are lost
    - Efficiency calculation affecting vehicle performance
    - Crew evacuation/replacement mechanics
    """

    def __init__(self, vehicle_id: str = "", crew_config: list[CrewRole] | None = None):
        self._vehicle_id = vehicle_id
        self._vehicle: Unit | None = None
        self._members: list[CrewMember] = []
        self._alive_count: int = 0
        self._vehicle_efficiency: float = 1.0
        self._penalties_applied: dict[str, float] = {}

        # Default crew composition based on vehicle type
        if crew_config is None:
            crew_config = self._get_default_crew_composition()

        for role in crew_config:
            member = CrewMember(
                name=role.value.capitalize(),
                role=role,
            )
            self._members.append(member)

        self._alive_count = len(self._members)

    def set_vehicle(self, vehicle: Unit) -> None:
        """Set vehicle reference after creation."""
        self._vehicle = vehicle
        self._vehicle_id = vehicle.id

    def _get_default_crew_composition(self) -> list[CrewRole]:
        """Determine default crew based on vehicle type."""
        unit_type = getattr(self._vehicle, "unit_type", None) if self._vehicle else None
        type_name = str(unit_type).lower() if unit_type else ""

        if "tank" in type_name or "heavy" in type_name:
            return [
                CrewRole.COMMANDER,
                CrewRole.GUNNER,
                CrewRole.DRIVER,
                CrewRole.LOADER,
            ]
        elif "halftrack" in type_name or "jeep" in type_name:
            return [
                CrewRole.COMMANDER,
                CrewRole.DRIVER,
            ]
        else:
            return [
                CrewRole.COMMANDER,
                CrewRole.GUNNER,
                CrewRole.DRIVER,
            ]

    @property
    def members(self) -> list[CrewMember]:
        return list(self._members)

    @property
    def alive_count(self) -> int:
        return self._alive_count

    @property
    def total_count(self) -> int:
        return len(self._members)

    @property
    def is_crew_alive(self) -> bool:
        return self._alive_count > 0

    @property
    def efficiency(self) -> float:
        return self._vehicle_efficiency

    @property
    def vehicle_efficiency(self) -> float:
        """Alias for efficiency, used by Unit.get_accuracy_modifier() etc."""
        return self._vehicle_efficiency

    @property
    def crew_ratio(self) -> float:
        if self.total_count == 0:
            return 0.0
        return self._alive_count / self.total_count

    def get_member_by_role(self, role: CrewRole) -> CrewMember | None:
        """Find crew member by role."""
        for member in self._members:
            if member.role == role:
                return member
        return None

    def get_active_members(self) -> list[CrewMember]:
        return [m for m in self._members if m.status == CrewStatus.ACTIVE]

    def apply_damage(
        self,
        damage: int,
        hit_location: str = "random",
        role_target: CrewRole | None = None,
    ) -> dict:
        """
        Apply damage to crew member(s).

        Args:
            damage: Damage points to apply
            hit_location: 'random', 'commander', 'gunner', etc.
            role_target: Specific role to target (overrides hit_location)

        Returns:
            Dict with damage result details
        """
        result = {
            "damage_dealt": 0,
            "member_hit": None,
            "was_kill": False,
            "crew_destroyed": False,
            "new_penalties": {},
        }

        if not self.is_crew_alive:
            result["crew_destroyed"] = True
            return result

        # Determine target
        target = self._select_damage_target(hit_location, role_target)

        if target is None:
            return result

        # Apply damage
        actual_damage = min(damage, target.hp)
        target.hp -= actual_damage
        result["damage_dealt"] = actual_damage
        result["member_hit"] = target.role.value

        # Check for death
        if target.hp <= 0:
            target.status = CrewStatus.DEAD
            target.hp = 0
            target.efficiency = 0.0
            self._alive_count -= 1
            result["was_kill"] = True

            logger.warning("[Crew] %s (%s) killed!", target.name, target.role.value)

            # Apply penalties
            new_penalties = self._apply_crew_death_penalty(target)
            result["new_penalties"] = new_penalties

            # Check for crew wipeout
            if self._alive_count <= 0:
                self._vehicle_efficiency = 0.0
                result["crew_destroyed"] = True

                # Mark vehicle as destroyed/disabled
                if self._vehicle is not None and hasattr(self._vehicle, "health"):
                    self._vehicle.health.current_hp = 0

                logger.warning("[Crew] All crew members dead! Vehicle disabled.")
        else:
            # Wound the member
            if target.hp < target.max_hp * 0.3:
                target.status = CrewStatus.WOUNDED
                target.efficiency = 0.5
                self._apply_wound_penalty(target)

        return result

    def _select_damage_target(
        self,
        hit_location: str,
        role_target: CrewRole | None,
    ) -> CrewMember | None:
        """Select which crew member takes the damage."""
        if role_target:
            member = self.get_member_by_role(role_target)
            if member and member.status != CrewStatus.DEAD:
                return member

        if hit_location == "random":
            active = self.get_active_members()
            if active:
                return random.choice(active)
            wounded = [m for m in self._members if m.status == CrewStatus.WOUNDED]
            if wounded:
                return random.choice(wounded)
            return None

        # Try to match location string to role
        role_map = {
            "commander": CrewRole.COMMANDER,
            "gunner": CrewRole.GUNNER,
            "driver": CrewRole.DRIVER,
            "loader": CrewRole.LOADER,
        }

        target_role = role_map.get(hit_location.lower())
        if target_role:
            member = self.get_member_by_role(target_role)
            if member and member.status != CrewStatus.DEAD:
                return member

        # Fallback to random
        active = self.get_active_members()
        return random.choice(active) if active else None

    def _apply_crew_death_penalty(self, deceased: CrewMember) -> dict[str, float]:
        """Apply performance penalties based on deceased crew member's role."""
        penalties = {}

        ratio = max(0.2, self.crew_ratio)
        self._vehicle_efficiency = ratio

        # Role-specific penalties
        if deceased.role == CrewRole.DRIVER:
            penalties["speed_multiplier"] = 0.5
            if self._vehicle is not None and hasattr(self._vehicle, "position"):
                pass  # Would modify movement speed component

        elif deceased.role == CrewRole.GUNNER:
            penalties["accuracy_multiplier"] = 0.5
            penalties["reload_time_multiplier"] = 2.0

        elif deceased.role == CrewRole.COMMANDER:
            penalties["vision_range_multiplier"] = 0.7
            penalties["morale_penalty"] = -15

        elif deceased.role == CrewRole.LOADER:
            penalties["reload_time_multiplier"] = 1.8

        self._penalties_applied.update(penalties)

        logger.info("[Crew] Penalties applied: %s", penalties)
        logger.info("[Crew] Overall efficiency: %.1f%%", self._vehicle_efficiency * 100)

        return penalties

    def _apply_wound_penalty(self, wounded: CrewMember) -> None:
        """Apply minor penalty for wounded crew member."""
        if wounded.role == CrewRole.GUNNER:
            self._penalties_applied["accuracy_multiplier"] = (
                self._penalties_applied.get("accuracy_multiplier", 1.0) * 0.8
            )
        elif wounded.role == CrewRole.DRIVER:
            self._penalties_applied["speed_multiplier"] = (
                self._penalties_applied.get("speed_multiplier", 1.0) * 0.8
            )

    def heal_member(
        self,
        role: CrewRole,
        heal_amount: int,
    ) -> bool:
        """
        Heal a crew member.

        Args:
            role: Role of member to heal
            heal_amount: HP to restore

        Returns:
            True if healing applied
        """
        member = self.get_member_by_role(role)
        if not member or member.status == CrewStatus.DEAD:
            return False

        old_hp = member.hp
        member.hp = min(member.max_hp, member.hp + heal_amount)

        if member.hp > member.max_hp * 0.3:
            member.status = CrewStatus.ACTIVE
            member.efficiency = 1.0

        return member.hp > old_hp

    def replace_member(
        self,
        role: CrewRole,
        replacement: CrewMember | None = None,
    ) -> bool:
        """
        Replace a dead crew member.

        Args:
            role: Role to replace
            replacement: New crew member (or create default)

        Returns:
            True if replacement successful
        """
        existing = self.get_member_by_role(role)
        if not existing or existing.status != CrewStatus.DEAD:
            return False

        if replacement is None:
            replacement = CrewMember(
                name=f"Replacement {role.value}",
                role=role,
                hp=50,  # Start at half health
                max_hp=100,
                status=CrewStatus.ACTIVE,
                efficiency=0.7,  # Lower skill than original
            )

        idx = self._members.index(existing)
        self._members[idx] = replacement
        self._alive_count += 1

        # Recalculate efficiency
        self._vehicle_efficiency = max(0.2, self.crew_ratio)

        logger.info("[Crew] %s replaced with %s", role.value, replacement.name)
        return True

    def evacuate_crew(self) -> list[CrewMember]:
        """
        Evacuate all surviving crew members.

        Returns:
            List of evacuated members
        """
        surviving = [m for m in self._members if m.status != CrewStatus.DEAD]

        for member in surviving:
            member.status = CrewStatus.ACTIVE  # Reset to active (evacuated safely)

        self._alive_count = 0
        self._vehicle_efficiency = 0.0

        logger.info("[Crew] Evacuated %d crew members", len(surviving))
        return surviving

    def get_status_display(self) -> dict:
        """Get crew status formatted for UI display."""
        return {
            "total_crew": self.total_count,
            "alive": self._alive_count,
            "efficiency": f"{self._vehicle_efficiency:.1%}",
            "members": [
                {
                    "name": m.name,
                    "role": m.role.value,
                    "hp": m.hp,
                    "max_hp": m.max_hp,
                    "status": m.status.value,
                    "efficiency": f"{m.efficiency:.0%}",
                }
                for m in self._members
            ],
            "penalties": self._penalties_applied,
        }
