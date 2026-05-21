"""
Morale Component

Manages unit morale state, panic status, and morale-based effects.
Morale affects accuracy, movement willingness, and combat effectiveness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class MoraleState(Enum):
    NORMAL = auto()
    SUPPRESSED = auto()
    PANICED = auto()
    ROUTING = auto()


@dataclass(slots=True)
class MoraleComponent:
    value: int
    panic_threshold: int = 30
    rout_threshold: int = 10
    suppression: int = 0
    state: MoraleState = field(init=False)
    _recovery_fractional: float = field(init=False, default=0.0)

    def __post_init__(self) -> None:
        if not isinstance(self.value, int):
            raise TypeError(f"value must be int, got {type(self.value).__name__}")
        self._clamp_value()
        self._update_state()

    @property
    def is_combat_effective(self) -> bool:
        return self.state not in (MoraleState.PANICED, MoraleState.ROUTING)

    @property
    def accuracy_modifier(self) -> float:
        modifiers = {
            MoraleState.NORMAL: 1.0,
            MoraleState.SUPPRESSED: 0.7,
            MoraleState.PANICED: 0.4,
            MoraleState.ROUTING: 0.1,
        }
        return modifiers.get(self.state, 1.0)

    def apply_delta(self, delta: int) -> None:
        self.value += delta
        self._clamp_value()
        self._update_state()

    def add_suppression(self, amount: int) -> None:
        self.suppression += amount
        if self.suppression > 0 and self.state == MoraleState.NORMAL:
            self.state = MoraleState.SUPPRESSED

    def decay_suppression(self, amount: int) -> None:
        self.suppression = max(0, self.suppression - amount)
        if self.suppression == 0:
            self._update_state()

    def natural_recovery(self) -> None:
        if not self.is_combat_effective:
            return
        self._recovery_fractional += 0.5
        if self._recovery_fractional >= 1.0:
            self.apply_delta(1)
            self._recovery_fractional -= 1.0

    def _update_state(self) -> None:
        if self.value < self.rout_threshold:
            self.state = MoraleState.ROUTING
        elif self.value < self.panic_threshold:
            self.state = MoraleState.PANICED
        elif self.suppression > 0:
            self.state = MoraleState.SUPPRESSED
        else:
            self.state = MoraleState.NORMAL

    def _clamp_value(self) -> None:
        self.value = max(0, min(100, self.value))
