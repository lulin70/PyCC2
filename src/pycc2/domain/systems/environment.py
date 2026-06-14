from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class TimeOfDay(Enum):
    DAY = auto()
    NIGHT = auto()
    DAWN = auto()
    DUSK = auto()


class WeatherCondition(Enum):
    CLEAR = auto()
    RAIN = auto()
    FOG = auto()
    OVERCAST = auto()


@dataclass
class EnvironmentState:
    time_of_day: TimeOfDay = TimeOfDay.DAY
    weather: WeatherCondition = WeatherCondition.CLEAR

    night_vision_penalty: float = 0.45
    rain_vision_penalty: float = 0.80
    fog_vision_penalty: float = 0.50

    night_stealth_bonus: float = 0.30
    forest_stealth_bonus: float = 0.20

    night_accuracy_penalty: float = 0.85

    active_flares: list[dict] = field(default_factory=list)
    FLARE_DURATION_TICKS: int = 600
    FLARE_VISION_RADIUS: int = 8

    def is_night(self) -> bool:
        return self.time_of_day in (TimeOfDay.NIGHT, TimeOfDay.DAWN, TimeOfDay.DUSK)

    def get_vision_multiplier(self) -> float:
        mult = 1.0
        if self.is_night():
            mult *= self.night_vision_penalty
        if self.weather == WeatherCondition.RAIN:
            mult *= self.rain_vision_penalty
        elif self.weather == WeatherCondition.FOG:
            mult *= self.fog_vision_penalty
        return mult

    def get_stealth_bonus(self, terrain_id: int | None = None) -> float:
        bonus = 0.0
        if self.is_night():
            bonus += self.night_stealth_bonus
        if terrain_id is not None and terrain_id in (3, 7, 9):
            bonus += self.forest_stealth_bonus
        return min(bonus, 0.60)

    def get_accuracy_modifier(self) -> float:
        mod = 1.0
        if self.is_night():
            mod *= self.night_accuracy_penalty
        return mod

    def add_flare(self, x: int, y: int) -> None:
        self.active_flares.append(
            {
                "position": (x, y),
                "radius": self.FLARE_VISION_RADIUS,
                "remaining_ticks": self.FLARE_DURATION_TICKS,
            }
        )

    def update_flares(self) -> None:
        self.active_flares = [f for f in self.active_flares if f["remaining_ticks"] > 0]
        for f in self.active_flares:
            f["remaining_ticks"] -= 1

    def is_tile_illuminated(self, x: int, y: int) -> bool:
        for f in self.active_flares:
            fx, fy = f["position"]
            if abs(x - fx) <= f["radius"] and abs(y - fy) <= f["radius"]:
                return True
        return False

    @classmethod
    def create_night_mission(cls) -> EnvironmentState:
        return cls(
            time_of_day=TimeOfDay.NIGHT,
            weather=WeatherCondition.CLEAR,
        )

    @classmethod
    def create_day_mission(cls) -> EnvironmentState:
        return cls(
            time_of_day=TimeOfDay.DAY,
            weather=WeatherCondition.CLEAR,
        )
