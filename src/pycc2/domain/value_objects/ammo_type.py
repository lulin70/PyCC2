"""Ammunition types for weapons that can switch between AP and HE (P1-6)."""

from __future__ import annotations

from enum import Enum, auto


class AmmoType(Enum):
    """Ammunition loaded into a weapon.

    AP (armor piercing) is best against vehicles.
    HE (high explosive) is best against infantry.
    """

    AP = auto()
    HE = auto()

    @property
    def display_name(self) -> str:
        """Return the short UI label."""
        return "AP" if self is AmmoType.AP else "HE"

    def damage_multiplier(self, target_is_vehicle: bool) -> float:
        """Return the damage multiplier against the target kind."""
        if self is AmmoType.AP:
            return 1.0 if target_is_vehicle else 0.9
        return 0.55 if target_is_vehicle else 1.25

    def penetration_multiplier(self, target_is_vehicle: bool) -> float:
        """Return the armor-penetration multiplier against the target kind."""
        if self is AmmoType.AP:
            return 1.0
        return 0.5 if target_is_vehicle else 1.0
