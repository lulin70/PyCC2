"""Weather Effects System — business logic engine for environmental weather impacts.

Provides vision modifiers, movement penalties, concealment bonuses,
and state management for dynamic weather transitions.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto


class WeatherType(Enum):
    """Discrete weather states affecting vision, movement, and accuracy."""

    CLEAR = auto()
    RAIN = auto()
    FOG = auto()
    SNOW = auto()
    OVERCAST = auto()


@dataclass
class WeatherState:
    """Runtime state of the current weather including intensity and duration."""

    weather_type: WeatherType = WeatherType.CLEAR
    intensity: float = 1.0
    duration_turns: int = 0
    remaining_turns: int = 0

    def is_active(self) -> bool:
        """Return True if a non-CLEAR weather effect is currently active."""
        return self.weather_type != WeatherType.CLEAR

    def is_expired(self) -> bool:
        """Return True if the weather effect has run out of remaining turns."""
        if self.duration_turns == 0:
            return False
        return self.remaining_turns <= 0

    def advance_turn(self) -> None:
        """Decrement remaining turns and clear weather when the duration elapses."""
        if self.remaining_turns > 0:
            self.remaining_turns -= 1
            if self.remaining_turns <= 0:
                self.weather_type = WeatherType.CLEAR
                self.intensity = 1.0
                self.remaining_turns = 0

    def set_weather(
        self,
        weather_type: WeatherType,
        intensity: float = 1.0,
        duration_turns: int = 0,
    ) -> None:
        """Configure a new weather effect with clamped intensity and duration."""
        self.weather_type = weather_type
        self.intensity = max(0.0, min(1.0, intensity))
        self.duration_turns = max(0, duration_turns)
        self.remaining_turns = self.duration_turns


class WeatherEffects:
    """Lookup-based modifiers for weather impacts on combat parameters."""

    VISION_MODIFIERS: dict[WeatherType, float] = {
        WeatherType.CLEAR: 1.0,
        WeatherType.RAIN: 0.7,
        WeatherType.FOG: 0.5,
        WeatherType.SNOW: 0.85,
        WeatherType.OVERCAST: 0.9,
    }

    MOVEMENT_MODIFIERS: dict[WeatherType, float] = {
        WeatherType.CLEAR: 1.0,
        WeatherType.RAIN: 0.9,
        WeatherType.FOG: 1.0,
        WeatherType.SNOW: 0.8,
        WeatherType.OVERCAST: 1.0,
    }

    MUD_PENALTY_RAIN: float = 0.7
    ACCURACY_MODIFIERS: dict[WeatherType, float] = {
        WeatherType.CLEAR: 1.0,
        WeatherType.RAIN: 0.9,
        WeatherType.FOG: 0.85,
        WeatherType.SNOW: 0.95,
        WeatherType.OVERCAST: 0.95,
    }

    def apply_to_vision(self, base_range: float, weather: WeatherType) -> float:
        """Return the effective vision range after applying the weather modifier."""
        modifier = self.VISION_MODIFIERS.get(weather, 1.0)
        return base_range * modifier

    def apply_to_movement(
        self,
        base_speed: float,
        weather: WeatherType,
        is_muddy_terrain: bool = False,
    ) -> float:
        """Return the effective movement speed after weather and mud penalties."""
        modifier = self.MOVEMENT_MODIFIERS.get(weather, 1.0)
        if is_muddy_terrain and weather == WeatherType.RAIN:
            modifier *= self.MUD_PENALTY_RAIN
        return base_speed * modifier

    def get_concealment_bonus(self, weather: WeatherType) -> float:
        """Return the additive concealment bonus granted by the current weather."""
        if weather == WeatherType.FOG:
            return 0.2
        if weather == WeatherType.SNOW:
            return 0.05
        if weather == WeatherType.RAIN:
            return 0.1
        return 0.0

    def apply_to_accuracy(self, base_accuracy: float, weather: WeatherType) -> float:
        """Return the effective accuracy after applying the weather modifier."""
        modifier = self.ACCURACY_MODIFIERS.get(weather, 1.0)
        return base_accuracy * modifier


class WeatherTransitionTable:
    """Probabilistic transition matrix between weather states per turn."""

    TRANSITIONS: dict[WeatherType, list[tuple[WeatherType, float]]] = {
        WeatherType.CLEAR: [
            (WeatherType.CLEAR, 0.70),
            (WeatherType.RAIN, 0.15),
            (WeatherType.FOG, 0.08),
            (WeatherType.OVERCAST, 0.07),
        ],
        WeatherType.RAIN: [
            (WeatherType.CLEAR, 0.30),
            (WeatherType.RAIN, 0.40),
            (WeatherType.FOG, 0.10),
            (WeatherType.OVERCAST, 0.20),
        ],
        WeatherType.FOG: [
            (WeatherType.CLEAR, 0.35),
            (WeatherType.RAIN, 0.20),
            (WeatherType.FOG, 0.30),
            (WeatherType.OVERCAST, 0.15),
        ],
        WeatherType.SNOW: [
            (WeatherType.CLEAR, 0.25),
            (WeatherType.SNOW, 0.50),
            (WeatherType.OVERCAST, 0.25),
        ],
        WeatherType.OVERCAST: [
            (WeatherType.CLEAR, 0.40),
            (WeatherType.RAIN, 0.25),
            (WeatherType.FOG, 0.15),
            (WeatherType.OVERCAST, 0.20),
        ],
    }

    @classmethod
    def get_next_weather(
        cls, current: WeatherType, rng: random.Random | None = None
    ) -> WeatherType:
        """Sample the next weather state from the transition table using the given RNG."""
        if rng is None:
            rng = random.Random()
        transitions = cls.TRANSITIONS.get(current, [(WeatherType.CLEAR, 1.0)])
        roll = rng.random()
        cumulative = 0.0
        for weather_type, probability in transitions:
            cumulative += probability
            if roll <= cumulative:
                return weather_type
        return current

    @classmethod
    def generate_weather_duration(
        cls, weather: WeatherType, rng: random.Random | None = None
    ) -> int:
        """Sample a random duration in turns for the given weather type."""
        if rng is None:
            rng = random.Random()
        base_durations = {
            WeatherType.CLEAR: (3, 8),
            WeatherType.RAIN: (2, 6),
            WeatherType.FOG: (2, 5),
            WeatherType.SNOW: (3, 7),
            WeatherType.OVERCAST: (2, 4),
        }
        low, high = base_durations.get(weather, (3, 5))
        return rng.randint(low, high)
