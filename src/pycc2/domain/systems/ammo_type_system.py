"""Ammo Type System - Differentiated ammunition with tactical effects.

Implements B7: Ammo type differentiation (AP, HE, SMOKE) with unique effects
for anti-vehicle, anti-infantry, and tactical smoke deployment.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit


class AmmoType(Enum):
    """Ammunition types with different tactical purposes."""
    AP = "ap"           # Armor-Piercing: High penetration, lower damage
    HE = "he"           # High-Explosive: AOE damage, lower penetration
    SMOKE = "smoke"     # Smoke grenade: Creates concealment
    STANDARD = "standard"  # Standard ammo: Balanced stats


@dataclass(slots=True)
class AmmoEffects:
    """Effects configuration for an ammo type."""
    ammo_type: AmmoType
    damage_multiplier: float = 1.0
    armor_penetration: float = 1.0
    aoe_radius: float = 0.0  # Grid cells
    smoke_duration: int = 0   # Turns
    smoke_radius: float = 0.0  # Grid cells
    effective_against: list[str] = field(default_factory=list)
    name: str = ""
    description: str = ""


# Predefined ammo effect configurations
AMMO_EFFECTS_CONFIG: dict[AmmoType, AmmoEffects] = {
    AmmoType.AP: AmmoEffects(
        ammo_type=AmmoType.AP,
        damage_multiplier=0.8,
        armor_penetration=1.5,
        effective_against=["vehicle", "tank", "halftrack"],
        name="Armor Piercing",
        description="Increased armor penetration, reduced damage. Effective against vehicles.",
    ),
    AmmoType.HE: AmmoEffects(
        ammo_type=AmmoType.HE,
        damage_multiplier=1.3,
        armor_penetration=0.5,
        aoe_radius=1.0,
        effective_against=["infantry", "squad"],
        name="High Explosive",
        description="Area-of-effect damage. Devastating against infantry groups.",
    ),
    AmmoType.SMOKE: AmmoEffects(
        ammo_type=AmmoType.SMOKE,
        damage_multiplier=0.0,
        armor_penetration=0.0,
        smoke_duration=3,
        smoke_radius=2.0,
        effective_against=["all"],
        name="Smoke",
        description="Creates smoke screen for concealment. No direct damage.",
    ),
    AmmoType.STANDARD: AmmoEffects(
        ammo_type=AmmoType.STANDARD,
        damage_multiplier=1.0,
        armor_penetration=1.0,
        effective_against=["infantry", "vehicle"],
        name="Standard",
        description="Balanced ammunition. Good all-round performance.",
    ),
}


@dataclass
class AmmoInventory:
    """
    Manages ammunition inventory and type selection for a unit.

    Features:
    - Multiple ammo types with limited quantities
    - Type cycling with cooldown
    - Effect application during combat
    - Smoke deployment tracking
    """

    def __init__(self, unit: "Unit"):
        self._unit = unit
        self._current_type: AmmoType = AmmoType.STANDARD
        self._inventory: dict[AmmoType, int] = {
            AmmoType.STANDARD: 999,  # Unlimited standard ammo
            AmmoType.AP: 10,
            AmmoType.HE: 8,
            AmmoType.SMOKE: 3,
        }
        self._max_inventory: dict[AmmoType, int] = dict(self._inventory)
        self._smoke_clouds: list[dict] = []  # Active smoke clouds
        self._type_change_cooldown: float = 0.0
        self._last_type_change: float = 0.0

    @property
    def current_type(self) -> AmmoType:
        return self._current_type

    @property
    def current_effects(self) -> AmmoEffects:
        return AMMO_EFFECTS_CONFIG.get(
            self._current_type,
            AMMO_EFFECTS_CONFIG[AmmoType.STANDARD],
        )

    @property
    def available_types(self) -> list[AmmoType]:
        return [t for t in AmmoType if self._inventory.get(t, 0) > 0]

    def get_ammo_count(self, ammo_type: AmmoType) -> int:
        return self._inventory.get(ammo_type, 0)

    def can_fire(self) -> bool:
        """Check if current ammo type has remaining rounds."""
        if self._current_type == AmmoType.STANDARD:
            return True
        return self._inventory.get(self._current_type, 0) > 0

    def cycle_ammo_type(self) -> AmmoType:
        """
        Cycle to next available ammo type.

        Returns:
            New active ammo type
        """
        import time
        current_time = time.perf_counter() * 1000

        if (current_time - self._last_type_change) < self._type_change_cooldown:
            return self._current_type

        types_order = [AmmoType.STANDARD, AmmoType.AP, AmmoType.HE, AmmoType.SMOKE]

        current_idx = types_order.index(self._current_type) if self._current_type in types_order else 0

        for i in range(1, len(types_order) + 1):
            next_idx = (current_idx + i) % len(types_order)
            next_type = types_order[next_idx]

            if next_type in self.available_types:
                self._current_type = next_type
                self._last_type_change = current_time

                logger.info("[Ammo] %s: Switched to %s", self._unit.name, next_type.value)
                return next_type

        return self._current_type

    def set_ammo_type(self, ammo_type: AmmoType) -> bool:
        """
        Manually set ammo type.

        Args:
            ammo_type: Target ammo type

        Returns:
            True if change successful
        """
        if ammo_type not in self.available_types:
            return False

        self._current_type = ammo_type
        import time
        self._last_type_change = time.perf_counter() * 1000
        return True

    def consume_round(self) -> bool:
        """
        Consume one round of current ammo.

        Returns:
            True if round was consumed (had ammo)
        """
        if self._current_type == AmmoType.STANDARD:
            return True

        current_count = self._inventory.get(self._current_type, 0)
        if current_count <= 0:
            return False

        self._inventory[self._current_type] = current_count - 1
        return True

    def apply_damage_modifiers(
        self,
        base_damage: float,
        target_unit: "Unit",
    ) -> float:
        """
        Apply ammo-type-specific damage modifiers.

        Args:
            base_damage: Base weapon damage
            target_unit: Target being hit

        Returns:
            Modified damage value
        """
        effects = self.current_effects

        modified_damage = base_damage * effects.damage_multiplier

        # Check effectiveness against target type
        target_type_str = getattr(target_unit, 'unit_type', None)
        if target_type_str:
            target_name = str(target_type_str).lower().replace('unittype.', '').replace('_', '')

            if any(eff in target_name for eff in effects.effective_against):
                modified_damage *= 1.2  # +20% bonus vs effective targets
            elif effects.effective_against and effects.effective_against[0] != "all":
                modified_damage *= 0.8  # -20% penalty vs ineffective targets

        return modified_damage

    def apply_armor_penetration(
        self,
        base_armor: float,
    ) -> float:
        """
        Modify armor value based on ammo penetration.

        Args:
            base_armor: Target's base armor value

        Returns:
            Modified armor (lower = more penetration)
        """
        effects = self.current_effects
        return base_armor / effects.armor_penetration

    def deploy_smoke(self, position: tuple[int, int]) -> dict | None:
        """
        Deploy smoke at position if using SMOKE ammo.

        Args:
            position: Grid coordinates (x, y)

        Returns:
            Smoke cloud info dict or None if not possible
        """
        if self._current_type != AmmoType.SMOKE:
            return None

        if not self.consume_round():
            return None

        effects = self.current_effects

        smoke_cloud = {
            "position": position,
            "radius": effects.smoke_radius,
            "duration_remaining": effects.smoke_duration,
            "max_duration": effects.smoke_duration,
            "created_turn": 0,  # Would be set by game state
        }

        self._smoke_clouds.append(smoke_cloud)

        logger.info("[Smoke] Deployed at %s, radius=%.1f, duration=%d turns",
                   position, effects.smoke_radius, effects.smoke_duration)

        return smoke_cloud

    def update_smoke_clouds(self, turn_increment: int = 1) -> None:
        """Decrement smoke durations and remove expired clouds."""
        active_clouds = []

        for cloud in self._smoke_clouds:
            cloud["duration_remaining"] -= turn_increment

            if cloud["duration_remaining"] > 0:
                active_clouds.append(cloud)

        self._smoke_clouds = active_clouds

    def is_position_in_smoke(
        self,
        position: tuple[int, int],
    ) -> bool:
        """Check if a position is covered by any smoke cloud."""
        for cloud in self._smoke_clouds:
            cx, cy = cloud["position"]
            px, py = position
            distance = ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5

            if distance <= cloud["radius"]:
                return True

        return False

    def refill_ammo(self, ammo_type: AmmoType | None = None, amount: int | None = None) -> None:
        """Refill ammunition (for resupply mechanics)."""
        if ammo_type:
            if amount is None:
                amount = self._max_inventory.get(ammo_type, 10)
            self._inventory[ammo_type] = min(
                amount,
                self._max_inventory.get(ammo_type, amount),
            )
        else:
            # Refill all
            for atype in self._inventory:
                max_amt = self._max_inventory.get(atype, 10)
                self._inventory[atype] = max_amt

    def get_status_dict(self) -> dict:
        """Get serializable status for UI display."""
        return {
            "current_type": self._current_type.value,
            "current_name": self.current_effects.name,
            "inventory": {k.value: v for k, v in self._inventory.items()},
            "available_types": [t.value for t in self.available_types],
            "active_smoke_clouds": len(self._smoke_clouds),
        }