"""Weapon Switch System - Multi-slot weapon management for CC2 units.

Implements B6: Weapon switching between primary, secondary, and melee weapons.
Supports hotkey binding (1=primary, 2=secondary, 3=melee) and cooldown management.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit


class WeaponSlot(Enum):
    """Weapon equipment slots for units."""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    MELEE = "melee"


@dataclass(slots=True)
class WeaponSlotConfig:
    """Configuration for a weapon slot."""
    slot: WeaponSlot
    switch_cooldown_ms: int = 500  # Time between switches
    draw_time_ms: int = 300  # Animation time to draw weapon
    holster_time_ms: int = 200  # Time to put away


@dataclass
class WeaponSwitchSystem:
    """
    Manages weapon switching for a unit.
    
    Features:
    - 3 weapon slots: primary, secondary, melee
    - Cooldown-based switching to prevent spam
    - Draw/holster animation timing integration
    - Hotkey support (1/2/3)
    - State tracking for UI display
    """

    def __init__(self, unit: "Unit"):
        self._unit = unit
        self._active_slot = WeaponSlot.PRIMARY
        self._weapons: dict[WeaponSlot, object] = {}
        self._slot_configs: dict[WeaponSlot, WeaponSlotConfig] = {
            WeaponSlot.PRIMARY: WeaponSlotConfig(slot=WeaponSlot.PRIMARY),
            WeaponSlot.SECONDARY: WeaponSlotConfig(slot=WeaponSlot.SECONDARY),
            WeaponSlot.MELEE: WeaponSlotConfig(slot=WeaponSlot.MELEE),
        }
        self._last_switch_time: float = 0.0
        self._is_switching: bool = False
        self._switch_start_time: float = 0.0
        
        self._initialize_default_weapons()

    def _initialize_default_weapons(self) -> None:
        """Set up default weapons based on unit type."""
        from pycc2.domain.components.weapon_component import WeaponComponent
        
        # Primary is the unit's current weapon
        if hasattr(self._unit, 'weapon'):
            self._weapons[WeaponSlot.PRIMARY] = self._unit.weapon
            
        # Create default secondary (pistol) and melee weapons
        try:
            secondary_weapon = WeaponComponent(
                name="Pistol",
                damage=15,
                range_meters=30,
                fire_rate=3.0,
                accuracy=0.6,
            )
            self._weapons[WeaponSlot.SECONDARY] = secondary_weapon
        except Exception as e:
            logging.warning(f"Secondary weapon init failed: {e}")
            
        try:
            melee_weapon = WeaponComponent(
                name="Bayonet/Knife",
                damage=25,
                range_meters=1,
                fire_rate=1.5,
                accuracy=0.9,
                is_melee=True,
            )
            self._weapons[WeaponSlot.MELEE] = melee_weapon
        except Exception as e:
            logging.warning(f"Melee weapon init failed: {e}")

    @property
    def active_slot(self) -> WeaponSlot:
        return self._active_slot

    @property
    def active_weapon(self) -> object:
        """Get the currently equipped weapon."""
        return self._weapons.get(self._active_slot)

    @property
    def available_slots(self) -> list[WeaponSlot]:
        return [s for s in WeaponSlot if s in self._weapons]

    @property
    def is_switching(self) -> bool:
        return self._is_switching

    def can_switch(self, target_slot: WeaponSlot) -> bool:
        """Check if switching to target slot is allowed."""
        if target_slot not in self._weapons:
            return False
            
        if target_slot == self._active_slot:
            return False
            
        if self._is_switching:
            return False
            
        import time
        current_time = time.perf_counter() * 1000
        config = self._slot_configs.get(self._active_slot)
        
        if config and (current_time - self._last_switch_time) < config.switch_cooldown_ms:
            return False
            
        return True

    def switch_to(self, target_slot: WeaponSlot) -> bool:
        """
        Attempt to switch to target weapon slot.
        
        Args:
            target_slot: Target weapon slot
            
        Returns:
            True if switch initiated successfully
        """
        if not self.can_switch(target_slot):
            return False
            
        old_slot = self._active_slot
        self._active_slot = target_slot
        
        import time
        self._last_switch_time = time.perf_counter() * 1000
        self._switch_start_time = self._last_switch_time
        self._is_switching = True
        
        print(f"[WeaponSwitch] {self._unit.name}: {old_slot.value} → {target_slot.value}")
        
        return True

    def switch_by_hotkey(self, key_number: int) -> bool:
        """
        Switch weapon using numeric hotkey.
        
        Args:
            key_number: 1=primary, 2=secondary, 3=melee
            
        Returns:
            True if switch initiated
        """
        mapping = {
            1: WeaponSlot.PRIMARY,
            2: WeaponSlot.SECONDARY,
            3: WeaponSlot.MELEE,
        }
        
        target = mapping.get(key_number)
        if target:
            return self.switch_to(target)
        return False

    def update(self, delta_ms: float) -> None:
        """Update switch animation state."""
        if not self._is_switching:
            return
            
        import time
        current_time = time.perf_counter() * 1000
        config = self._slot_configs.get(self._active_slot)
        
        if config:
            elapsed = current_time - self._switch_start_time
            total_switch_time = config.draw_time_ms + config.holster_time_ms
            
            if elapsed >= total_switch_time:
                self._is_switching = False

    def get_switch_progress(self) -> float:
        """
        Get current switch animation progress (0.0 to 1.0).
        
        Returns:
            Progress fraction or 0.0 if not switching
        """
        if not self._is_switching:
            return 0.0
            
        import time
        current_time = time.perf_counter() * 1000
        config = self._slot_configs.get(self._active_slot)
        
        if config:
            elapsed = current_time - self._switch_start_time
            total = config.draw_time_ms + config.holster_time_ms
            return min(1.0, elapsed / max(1, total))
            
        return 0.0

    def set_weapon(self, slot: WeaponSlot, weapon: object) -> None:
        """Assign a weapon to a specific slot."""
        self._weapons[slot] = weapon

    def remove_weapon(self, slot: WeaponSlot) -> object | None:
        """Remove weapon from slot and return it."""
        return self._weapons.pop(slot, None)

    def get_all_weapons(self) -> dict[WeaponSlot, object]:
        return dict(self._weapons)

    def get_status_dict(self) -> dict:
        """Get serializable status for UI display."""
        return {
            "active_slot": self._active_slot.value,
            "available_slots": [s.value for s in self.available_slots],
            "is_switching": self._is_switching,
            "switch_progress": self.get_switch_progress(),
        }