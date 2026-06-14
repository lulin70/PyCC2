"""
Fatigue Component — tracks unit exhaustion over extended operations.
Fatigued units have reduced accuracy, slower movement, and higher panic risk.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto


class FatigueLevel(Enum):
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
    FatigueLevel.TIRED: {"accuracy": 0.95, "movement": 0.95, "panic_mod": 1.05, "morale_drain": 0.02},
    FatigueLevel.WEARY: {"accuracy": 0.85, "movement": 0.85, "panic_mod": 1.15, "morale_drain": 0.05},
    FatigueLevel.EXHAUSTED: {"accuracy": 0.70, "movement": 0.70, "panic_mod": 1.35, "morale_drain": 0.10},
    FatigueLevel.SPENT: {"accuracy": 0.50, "movement": 0.50, "panic_mod": 1.60, "morale_drain": 0.18},
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
    value: float = 0.0
    ticks_at_current_level: int = 0
    max_fatigue: float = 120.0

    @property
    def level(self) -> FatigueLevel:
        v = min(self.value, self.max_fatigue)
        for level, threshold in sorted(FATIGUE_THRESHOLDS.items(), key=lambda x: x[1], reverse=True):
            if v >= threshold:
                return level
        return FatigueLevel.FRESH

    @property
    def level_name(self) -> str:
        return self.level.name

    @property
    def accuracy_modifier(self) -> float:
        return FATIGUE_EFFECTS[self.level]["accuracy"]

    @property
    def movement_modifier(self) -> float:
        return FATIGUE_EFFECTS[self.level]["movement"]

    @property
    def panic_probability_mod(self) -> float:
        return FATIGUE_EFFECTS[self.level]["panic_mod"]

    @property
    def morale_drain_rate(self) -> float:
        return FATIGUE_EFFECTS[self.level]["morale_drain"]

    def accumulate(self, activity: str, ticks: int = 1, is_night: bool = False) -> None:
        rate = FATIGUE_RATES.get(activity, 0.0)
        delta = rate * ticks
        if is_night and activity != "resting":
            delta += FATIGUE_RATES["night_malus"] * ticks
        self.value = max(0.0, min(self.max_fatigue, self.value + delta))
        self._check_level_change()

    def recover(self, ticks: int = 1, recovery_multiplier: float = 1.0) -> None:
        base_recovery = 0.008 * recovery_multiplier * ticks
        self.value = max(0.0, self.value - base_recovery)
        self._check_level_change()

    def rest_full(self) -> None:
        self.value = 0.0
        self.ticks_at_current_level = 0

    def partial_rest(self, pct: float = 0.4) -> None:
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
        return {
            "value": round(self.value, 2),
            "level": self.level.name,
            "ticks_at_level": self.ticks_at_current_level,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FatigueComponent":
        return cls(
            value=data.get("value", 0.0),
            ticks_at_current_level=data.get("ticks_at_level", 0),
        )
