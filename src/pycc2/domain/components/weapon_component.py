"""Weapon Component

Manages unit weapon state, ammunition, and weapon properties.
Supports primary weapon with ammo tracking and reload mechanics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class WeaponState(Enum):
    """Operational states for a weapon component."""

    READY = auto()
    RELOADING = auto()
    JAMMED = auto()
    OUT_OF_AMMO = auto()


class WeaponType(Enum):
    """Classification of weapon damage and delivery types."""

    KINETIC = auto()
    EXPLOSIVE = auto()
    AP = auto()
    HE = auto()


@dataclass(slots=True)
class WeaponComponent:
    """Tracks ammo, reload progress, and captured-weapon penalties for a unit."""

    primary_weapon_id: str
    ammo_remaining: int
    max_ammo: int
    reload_ticks_left: int = 0
    is_captured: bool = False
    captured_accuracy_penalty: float = 0.0
    captured_reload_penalty: float = 0.0
    state: WeaponState = field(init=False)

    def __post_init__(self) -> None:
        self._update_state()

    @property
    def can_fire(self) -> bool:
        """Return whether the weapon is ready and has ammo."""
        return self.state == WeaponState.READY and self.ammo_remaining > 0

    @property
    def ammo_ratio(self) -> float:
        """Return remaining ammo as a 0-1 ratio of max ammo."""
        if self.max_ammo <= 0:
            return 0.0
        return self.ammo_remaining / self.max_ammo

    @property
    def is_reloading(self) -> bool:
        """Return whether the weapon is currently reloading."""
        return self.state == WeaponState.RELOADING

    @property
    def accuracy_modifier(self) -> float:
        """Accuracy multiplier: 0.8 for captured weapons (-20%), 1.0 otherwise."""
        return 0.8 if self.is_captured else 1.0

    def fire(self) -> bool:
        """Consume one ammo and return whether the shot was fired."""
        if not self.can_fire:
            if self.ammo_remaining == 0 and self.state != WeaponState.OUT_OF_AMMO:
                self.state = WeaponState.OUT_OF_AMMO
            return False

        self.ammo_remaining -= 1
        if self.ammo_remaining == 0:
            self.state = WeaponState.OUT_OF_AMMO
        return True

    def start_reload(self, reload_ticks: int) -> None:
        """Begin a reload, applying captured-weapon penalty if applicable."""
        if self.is_captured:
            reload_ticks = int(reload_ticks * 1.5)  # +50% reload time for captured weapons
        self.reload_ticks_left = reload_ticks
        self.state = WeaponState.RELOADING

    def tick(self) -> None:
        """Advance reload progress by one tick."""
        if self.state == WeaponState.RELOADING and self.reload_ticks_left > 0:
            self.reload_ticks_left -= 1
            if self.reload_ticks_left == 0:
                self.ammo_remaining = self.max_ammo
                self.state = WeaponState.READY

    def clear_jam(self) -> None:
        """Clear a jammed state, returning to ready or out-of-ammo as appropriate."""
        if self.state == WeaponState.JAMMED:
            if self.ammo_remaining > 0:
                self.state = WeaponState.READY
            else:
                self.state = WeaponState.OUT_OF_AMMO

    def _update_state(self) -> None:
        if self.reload_ticks_left > 0:
            self.state = WeaponState.RELOADING
        elif self.ammo_remaining <= 0:
            self.state = WeaponState.OUT_OF_AMMO
        else:
            self.state = WeaponState.READY
