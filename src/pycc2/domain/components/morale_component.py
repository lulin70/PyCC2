"""
Morale Component

Manages unit morale state, panic status, and morale-based effects.
Morale affects accuracy, movement willingness, and combat effectiveness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class MoraleState(Enum):
    RALLIED = auto()  # >70 morale
    WAVERING = auto()  # 40-70 morale
    PINNED = auto()  # 20-40 morale
    BROKEN = auto()  # <20 morale
    ROUTING = auto()  # Fleeing behavior


@dataclass(slots=True)
class MoraleComponent:
    value: int
    panic_threshold: int = 30
    rout_threshold: int = 10
    suppression: int = 0
    state: MoraleState = field(init=False)
    _is_routing: bool = field(init=False, default=False)
    _recovery_fractional: float = field(init=False, default=0.0)

    def __post_init__(self) -> None:
        if not isinstance(self.value, int):
            raise TypeError(f"value must be int, got {type(self.value).__name__}")
        self._clamp_value()
        self._update_state()

    @property
    def is_combat_effective(self) -> bool:
        return self.state in (MoraleState.RALLIED, MoraleState.WAVERING)

    @property
    def accuracy_modifier(self) -> float:
        modifiers = {
            MoraleState.RALLIED: 1.05,
            MoraleState.WAVERING: 0.95,
            MoraleState.PINNED: 0.60,
            MoraleState.BROKEN: 0.30,
            MoraleState.ROUTING: 0.10,
        }
        return modifiers.get(self.state, 1.0)

    def apply_delta(self, delta: int) -> None:
        self.value += delta
        self._clamp_value()
        self._update_state()

    def add_suppression(self, amount: int) -> None:
        self.suppression += amount
        if self.suppression > 0 and self.state == MoraleState.RALLIED:
            self.state = MoraleState.WAVERING

    def decay_suppression(self, amount: int) -> None:
        self.suppression = max(0, self.suppression - amount)
        if self.suppression == 0:
            self._update_state()

    def natural_recovery(self, veterancy_morale_resist: float = 1.0) -> None:
        """Recover morale over time. Veteran units recover faster."""
        if not self.is_combat_effective:
            return
        recovery_rate = 0.5 * veterancy_morale_resist
        self._recovery_fractional += recovery_rate
        if self._recovery_fractional >= 1.0:
            self.apply_delta(1)
            self._recovery_fractional -= 1.0

    def _update_state(self) -> None:
        if self._is_routing:
            self.state = MoraleState.ROUTING
        elif self.value > 70:
            self.state = MoraleState.RALLIED
        elif self.value > 40:
            self.state = MoraleState.WAVERING
        elif self.value > 20:
            self.state = MoraleState.PINNED
        else:
            self.state = MoraleState.BROKEN

    def _clamp_value(self) -> None:
        self.value = max(0, min(100, self.value))

    def start_routing(self) -> None:
        self._is_routing = True
        self.state = MoraleState.ROUTING

    def stop_routing(self) -> None:
        self._is_routing = False
        self._update_state()
