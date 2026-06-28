"""CC2 Authentic Weapon Database — facade (P5-1 batch 1).

This module is a thin facade re-exporting types and composing the weapon
database from per-category builders:
  - weapon_type_defs.py: WeaponType/InfantryRole/VehicleType enums + WeaponProfile
  - allied_weapon_profiles.py: American + British infantry weapons
  - axis_weapon_profiles.py: German infantry weapons
  - vehicle_weapon_profiles.py: Tank guns + vehicle MGs + specials

Public API (backward-compatible):
  - build_cc2_weapon_database() -> dict[str, WeaponProfile]
  - get_cc2_weapons() -> dict[str, WeaponProfile]
  - get_weapons_for_faction(faction) -> list[WeaponProfile]
  - WeaponType, InfantryRole, VehicleType, WeaponProfile, Faction (re-exports)
"""

from __future__ import annotations

import logging

from pycc2.domain.entities.unit import Faction
from pycc2.domain.systems.allied_weapon_profiles import build_allied_weapons
from pycc2.domain.systems.axis_weapon_profiles import build_axis_weapons
from pycc2.domain.systems.vehicle_weapon_profiles import build_vehicle_weapons
from pycc2.domain.systems.weapon_type_defs import (
    InfantryRole,
    VehicleType,
    WeaponProfile,
    WeaponType,
)

logger = logging.getLogger(__name__)

__all__ = [
    "Faction",
    "InfantryRole",
    "VehicleType",
    "WeaponProfile",
    "WeaponType",
    "build_cc2_weapon_database",
    "get_cc2_weapons",
    "get_weapons_for_faction",
]


def build_cc2_weapon_database() -> dict[str, WeaponProfile]:
    """Build complete CC2 weapon database by merging all category builders.

    Delegates to:
      - build_allied_weapons() (American + British infantry)
      - build_axis_weapons() (German infantry)
      - build_vehicle_weapons() (tank guns, MGs, specials)
    """
    weapons: dict[str, WeaponProfile] = {}
    weapons.update(build_allied_weapons())
    weapons.update(build_axis_weapons())
    weapons.update(build_vehicle_weapons())
    return weapons


# Global instance
CC2_WEAPONS: dict[str, WeaponProfile] = {}


def get_cc2_weapons() -> dict[str, WeaponProfile]:
    """Lazy-initialize and return weapon database."""
    global CC2_WEAPONS
    if not CC2_WEAPONS:
        CC2_WEAPONS = build_cc2_weapon_database()
    return CC2_WEAPONS


def get_weapons_for_faction(faction: Faction) -> list[WeaponProfile]:
    """Get all weapons available to a faction."""
    db = get_cc2_weapons()
    return [w for w in db.values() if faction in w.users]
