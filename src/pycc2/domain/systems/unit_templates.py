"""CC2 unit template dataclass."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pycc2.domain.systems.cc2_authentic_weapons import (
    Faction,
    InfantryRole,
    VehicleType,
    WeaponProfile,
    get_cc2_weapons,
)


@dataclass
class CC2UnitTemplate:
    """Complete unit specification matching CC2's internal data structure.

    Each template represents a deployable team/squad/vehicle.
    """

    # === IDENTITY ===
    template_id: str  # Unique identifier: 'us_rifle_squad_82nd'
    display_name: str  # "82nd Airborne Rifle Squad"
    faction: Faction
    role: InfantryRole | VehicleType  # Unit role classification

    # === COMPOSITION (Infantry only) ===
    squad_size: int = 10  # Number of men (1-15)
    weapon_primary_id: str = ""  # Primary weapon key from weapon DB
    weapon_secondary_id: str | None = None  # Optional secondary weapon

    # === VEHICLE DATA (Vehicles only) ===
    vehicle_armor: int = 0  # Armor thickness (mm equivalent)
    vehicle_speed: int = 0  # Max speed (km/h)
    vehicle_crew: int = 0  # Crew size
    is_amphibious: bool = False  # Can cross water

    # === COMBAT STATS (derived from weapons + experience) ===
    experience_level: int = 0  # 0=Green, 1=Regular, 2=Veteran, 3=Elite
    morale_initial: float = 80.0  # Starting morale (0-100)
    stealth_rating: float = 0.3  # Base concealment (0.0-1.0)
    vision_range: int = 6  # Tiles of visibility

    # === SPECIAL PROPERTIES ===
    can_capture: bool = True  # Can capture victory locations
    can_deploy_in_building: bool = True
    can_deploy_in_open: bool = True
    is_command_unit: bool = False  # Morale boost to nearby units
    is_fanatic: bool = False  # Never panics (SS/Fanatics)
    has_demolitions: bool = False  # Can destroy structures

    # === DEPLOYMENT RULES ===
    deployment_cost: int = 100  # "Requisition points" cost (Operations mode)
    max_per_battle: int = 99  # Limit on how many can be brought
    min_turns_reinforce: int = 0  # 0=available start, >0=reinforcement turn

    # === FLAVOR TEXT ===
    historical_notes: str = ""

    def get_weapon(self) -> WeaponProfile | None:
        """Resolve and return primary weapon profile."""
        db = get_cc2_weapons()
        return db.get(self.weapon_primary_id)

    def get_secondary_weapon(self) -> WeaponProfile | None:
        """Resolve optional secondary weapon."""
        if not self.weapon_secondary_id:
            return None
        db = get_cc2_weapons()
        return db.get(self.weapon_secondary_id)

    def calculate_effective_stats(self) -> dict[str, Any]:
        """Calculate effective combat stats based on equipment + experience.

        Returns dict with all relevant combat parameters.
        """
        weapon = self.get_weapon()
        if not weapon:
            return {"error": f"Unknown weapon: {self.weapon_primary_id}"}

        # Experience multipliers (CC2-style)
        exp_mult = {
            0: {"accuracy": 1.0, "morale": 1.0, "suppression_resist": 1.0},
            1: {"accuracy": 1.10, "morale": 1.05, "suppression_resist": 1.05},
            2: {"accuracy": 1.20, "morale": 1.12, "suppression_resist": 1.12},
            3: {"accuracy": 1.35, "morale": 1.25, "suppression_resist": 1.25},
        }

        m = exp_mult.get(self.experience_level, exp_mult[0])

        base_stats = {
            "name": self.display_name,
            "role": self.role.name,
            "faction": self.faction.name,
            "squad_size": self.squad_size,
            # Weapon stats (experience-modified)
            "weapon_name": weapon.name,
            "weapon_type": weapon.weapon_type.name,
            "range_short": weapon.range_short,
            "range_max": weapon.range_max,
            "accuracy_short": min(0.95, weapon.accuracy_short * m["accuracy"]),
            "accuracy_long": min(0.95, weapon.accuracy_long * m["accuracy"]),
            "damage_vs_infantry": weapon.damage_vs_infantry,
            "damage_vs_light_armor": weapon.damage_vs_light_armor,
            "suppress_power": min(1.0, weapon.suppress_power),
            "rpm": weapon.rpm,
            # Unit stats
            "morale": min(100, self.morale_initial * m["morale"]),
            "stealth": self.stealth_rating,
            "vision": self.vision_range,
            "exp_level": self.experience_level,
            "is_fanatic": self.is_fanatic,
            "can_capture": self.can_capture,
            "deployment_cost": self.deployment_cost,
        }

        return base_stats


__all__ = ["CC2UnitTemplate"]
