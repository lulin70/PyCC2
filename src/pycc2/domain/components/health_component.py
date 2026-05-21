"""
Health Component

Manages unit health points, damage application, and death state.
Part of the Entity-Component pattern for unit composition.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class HealthState(Enum):
    HEALTHY = auto()
    WOUNDED = auto()
    CRITICAL = auto()
    DEAD = auto()


@dataclass(slots=True)
class HealthComponent:
    hp: int
    max_hp: int
    state: HealthState = field(init=False)

    def __post_init__(self) -> None:
        self._update_state()

    @property
    def hp_ratio(self) -> float:
        if self.max_hp <= 0:
            return 0.0
        return self.hp / self.max_hp

    @property
    def is_alive(self) -> bool:
        return self.state != HealthState.DEAD

    @property
    def is_healthy(self) -> bool:
        return self.state == HealthState.HEALTHY

    def take_damage(self, amount: int) -> int:
        if amount <= 0 or not self.is_alive:
            return 0

        actual_damage = min(amount, self.hp)
        self.hp -= actual_damage

        if self.hp < 0:
            self.hp = 0

        self._update_state()
        return actual_damage

    def heal(self, amount: int) -> int:
        if amount <= 0:
            return 0

        missing_hp = self.max_hp - self.hp
        actual_heal = min(amount, missing_hp)
        self.hp += actual_heal
        self._update_state()
        return actual_heal

    def _update_state(self) -> None:
        ratio = self.hp_ratio
        if self.hp <= 0:
            self.state = HealthState.DEAD
        elif ratio < 0.3:
            self.state = HealthState.CRITICAL
        elif ratio <= 0.7:
            self.state = HealthState.WOUNDED
        else:
            self.state = HealthState.HEALTHY
