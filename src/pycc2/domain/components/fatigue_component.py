"""Fatigue Component — tracks unit exhaustion over extended operations.
Fatigued units have reduced accuracy, slower movement, and higher panic risk.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class FatigueLevel(Enum):
    """Progressive exhaustion tiers from fresh to spent."""

    FRESH = auto()
    TIRED = auto()
    WEARY = auto()
    EXHAUSTED = auto()
    SPENT = auto()


FATIGUE_THRESHOLDS = {
    FatigueLevel.FRESH: 0,
    FatigueLevel.TIRED: 25,
    FatigueLevel.WEARY: 50,
    FatigueLevel.EXHAUSTED: 75,
    FatigueLevel.SPENT: 100,
}

FATIGUE_EFFECTS = {
    FatigueLevel.FRESH: {"accuracy": 1.0, "movement": 1.0, "panic_mod": 1.0, "morale_drain": 0.0},
    FatigueLevel.TIRED: {
        "accuracy": 0.95,
        "movement": 0.95,
        "panic_mod": 1.05,
        "morale_drain": 0.02,
    },
    FatigueLevel.WEARY: {
        "accuracy": 0.85,
        "movement": 0.85,
        "panic_mod": 1.15,
        "morale_drain": 0.05,
    },
    FatigueLevel.EXHAUSTED: {
        "accuracy": 0.70,
        "movement": 0.70,
        "panic_mod": 1.35,
        "morale_drain": 0.10,
    },
    FatigueLevel.SPENT: {
        "accuracy": 0.50,
        "movement": 0.50,
        "panic_mod": 1.60,
        "morale_drain": 0.18,
    },
}

FATIGUE_RATES = {
    "moving": 0.002,
    "fast_move": 0.006,
    "firing": 0.008,
    "combat_stress": 0.015,
    "resting": -0.005,
    "night_malus": 0.003,
}


@dataclass(slots=True)
class FatigueComponent:
    """Tracks unit exhaustion and exposes accuracy, movement, and panic modifiers."""

    value: float = 0.0
    ticks_at_current_level: int = 0
    max_fatigue: float = 120.0

    @property
    def level(self) -> FatigueLevel:
        """Return the current fatigue level tier based on accumulated value."""
        v = min(self.value, self.max_fatigue)
        for level, threshold in sorted(
            FATIGUE_THRESHOLDS.items(), key=lambda x: x[1], reverse=True
        ):
            if v >= threshold:
                return level
        return FatigueLevel.FRESH

    @property
    def level_name(self) -> str:
        """Return the name of the current fatigue level tier."""
        return self.level.name

    @property
    def accuracy_modifier(self) -> float:
        """Return the accuracy multiplier imposed by current fatigue."""
        return FATIGUE_EFFECTS[self.level]["accuracy"]

    @property
    def movement_modifier(self) -> float:
        """Return the movement speed multiplier imposed by current fatigue."""
        return FATIGUE_EFFECTS[self.level]["movement"]

    @property
    def panic_probability_mod(self) -> float:
        """Return the panic probability multiplier imposed by current fatigue."""
        return FATIGUE_EFFECTS[self.level]["panic_mod"]

    @property
    def morale_drain_rate(self) -> float:
        """Return the morale drain per tick imposed by current fatigue."""
        return FATIGUE_EFFECTS[self.level]["morale_drain"]

    def accumulate(self, activity: str, ticks: int = 1, is_night: bool = False) -> None:
        """Accumulate fatigue from the given activity over the given ticks."""
        rate = FATIGUE_RATES.get(activity, 0.0)
        delta = rate * ticks
        if is_night and activity != "resting":
            delta += FATIGUE_RATES["night_malus"] * ticks
        self.value = max(0.0, min(self.max_fatigue, self.value + delta))
        self._check_level_change()

    def recover(self, ticks: int = 1, recovery_multiplier: float = 1.0) -> None:
        """Reduce fatigue through active recovery over the given ticks."""
        base_recovery = 0.008 * recovery_multiplier * ticks
        self.value = max(0.0, self.value - base_recovery)
        self._check_level_change()

    def rest_full(self) -> None:
        """Reset fatigue to zero (full rest)."""
        self.value = 0.0
        self.ticks_at_current_level = 0

    def partial_rest(self, pct: float = 0.4) -> None:
        """Reduce fatigue by a fraction (default 40%) of its current value."""
        self.value = max(0.0, self.value * (1.0 - pct))
        self._check_level_change()

    def _check_level_change(self) -> None:
        old_level = self.level
        new_val = min(self.value, self.max_fatigue)
        for lvl, thresh in sorted(FATIGUE_THRESHOLDS.items(), key=lambda x: x[1], reverse=True):
            if new_val >= thresh:
                if lvl != old_level:
                    self.ticks_at_current_level = 0
                break

    def to_dict(self) -> dict:
        """Serialize the component to a plain dict for saving."""
        return {
            "value": round(self.value, 2),
            "level": self.level.name,
            "ticks_at_level": self.ticks_at_current_level,
        }

    @classmethod
    def from_dict(cls, data: dict) -> FatigueComponent:
        """Reconstruct a FatigueComponent from a saved dict."""
        return cls(
            value=data.get("value", 0.0),
            ticks_at_current_level=data.get("ticks_at_level", 0),
        )
