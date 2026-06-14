"""
Day-Night Cycle System — game time management and temporal effects.

Provides time progression, time-of-day detection, vision/stealth modifiers,
lighting color grading, and searchlight entity logic.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, auto


class TimeOfDay(Enum):
    DAWN = auto()
    DAY = auto()
    DUSK = auto()
    NIGHT = auto()


@dataclass
class GameTime:
    total_seconds: float = 0.0
    time_scale: float = 600.0

    @property
    def hours(self) -> float:
        game_total = self.total_seconds * self.time_scale
        return (game_total / 3600.0) % 24

    @property
    def minutes(self) -> int:
        return int((self.hours % 1) * 60)

    @property
    def time_of_day(self) -> TimeOfDay:
        h = self.hours
        if 5 <= h < 7:
            return TimeOfDay.DAWN
        if 7 <= h < 18:
            return TimeOfDay.DAY
        if 18 <= h < 20:
            return TimeOfDay.DUSK
        return TimeOfDay.NIGHT

    @property
    def formatted_time(self) -> str:
        h = int(self.hours)
        m = self.minutes
        period = "AM" if h < 12 else "PM"
        display_h = h if h <= 12 else h - 12
        if display_h == 0:
            display_h = 12
        return f"{display_h:02d}:{m:02d} {period}"

    def advance(self, dt: float) -> None:
        self.total_seconds += dt

    def set_time(self, hour: float) -> None:
        scaled_hour = (hour % 24) / self.time_scale * 3600.0
        base_days = int(self.total_seconds * self.time_scale / 86400.0)
        self.total_seconds = base_days * 86400.0 / self.time_scale + scaled_hour


class DayNightEffects:
    VISION_MODIFIERS: dict[TimeOfDay, float] = {
        TimeOfDay.DAWN: 0.9,
        TimeOfDay.DAY: 1.0,
        TimeOfDay.DUSK: 0.8,
        TimeOfDay.NIGHT: 0.3,
    }

    STEALTH_BONUSES: dict[TimeOfDay, float] = {
        TimeOfDay.DAWN: 0.1,
        TimeOfDay.DAY: 0.0,
        TimeOfDay.DUSK: 0.2,
        TimeOfDay.NIGHT: 0.5,
    }

    ACCURACY_MODIFIERS: dict[TimeOfDay, float] = {
        TimeOfDay.DAWN: 0.95,
        TimeOfDay.DAY: 1.0,
        TimeOfDay.DUSK: 0.9,
        TimeOfDay.NIGHT: 0.85,
    }

    LIGHTING_COLORS: dict[TimeOfDay, tuple[int, int, int]] = {
        TimeOfDay.DAWN: (255, 200, 150),
        TimeOfDay.DAY: (255, 255, 255),
        TimeOfDay.DUSK: (255, 180, 120),
        TimeOfDay.NIGHT: (80, 100, 140),
    }

    def apply_vision_penalty(
        self, base_range: float, tod: TimeOfDay
    ) -> float:
        modifier = self.VISION_MODIFIERS.get(tod, 1.0)
        return base_range * modifier

    def apply_stealth_bonus(
        self, base_chance: float, tod: TimeOfDay
    ) -> float:
        bonus = self.STEALTH_BONUSES.get(tod, 0.0)
        return min(1.0, base_chance + bonus)

    def apply_accuracy_modifier(
        self, base_accuracy: float, tod: TimeOfDay
    ) -> float:
        modifier = self.ACCURACY_MODIFIERS.get(tod, 1.0)
        return base_accuracy * modifier

    def get_lighting_color(self, tod: TimeOfDay) -> tuple[int, int, int]:
        return self.LIGHTING_COLORS.get(tod, (255, 255, 255))

    def get_combined_vision_modifier(
        self,
        base_range: float,
        tod: TimeOfDay,
        weather_modifier: float = 1.0,
    ) -> float:
        vision = self.apply_vision_penalty(base_range, tod)
        return vision * weather_modifier

    def get_combined_stealth_bonus(
        self,
        base_chance: float,
        tod: TimeOfDay,
        weather_concealment: float = 0.0,
    ) -> float:
        stealth = self.apply_stealth_bonus(base_chance, tod)
        return min(1.0, stealth + weather_concealment)


@dataclass
class Searchlight:
    position_x: int
    position_y: int
    direction_deg: float = 0.0
    arc_angle: float = 60.0
    reveal_range: int = 15
    sweep_speed: float = 30.0
    is_active: bool = True
    _current_direction: float = field(default=0.0, init=False)
    _sweep_sign: float = field(default=1.0, init=False)

    def __post_init__(self):
        self._current_direction = self.direction_deg

    def get_illuminated_tiles(self) -> list[tuple[int, int]]:
        illuminated = []
        if not self.is_active:
            return illuminated

        math.radians(self.arc_angle / 2.0)
        direction_rad = math.radians(self._current_direction)

        for r in range(1, self.reveal_range + 1):
            for angle_offset in range(-int(self.arc_angle), int(self.arc_angle) + 1, 2):
                angle = direction_rad + math.radians(angle_offset)
                dx = int(r * math.cos(angle))
                dy = int(r * math.sin(angle))
                tile_x = self.position_x + dx
                tile_y = self.position_y + dy
                illuminated.append((tile_x, tile_y))

        return illuminated

    def is_tile_illuminated(self, x: int, y: int) -> bool:
        if not self.is_active:
            return False

        dx = x - self.position_x
        dy = y - self.position_y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance > self.reveal_range:
            return False

        angle_to_tile = math.degrees(math.atan2(dy, dx))
        angle_diff = abs(angle_to_tile - self._current_direction)
        if angle_diff > 180:
            angle_diff = 360 - angle_diff

        return angle_diff <= (self.arc_angle / 2.0)

    def update(self, dt: float) -> None:
        if not self.is_active:
            return

        self._current_direction += self._sweep_sign * self.sweep_speed * dt
        if self._current_direction > 180 or self._current_direction < -180:
            self._sweep_sign *= -1

    @property
    def current_direction(self) -> float:
        return self._current_direction
