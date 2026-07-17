"""STATUS: ORPHAN — pending v0.8.0+ integration (TD-077). Day-Night Cycle System — game time management and temporal effects.

Provides time progression, time-of-day detection, vision/stealth modifiers,
lighting color grading, and searchlight entity logic.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, auto


class TimeOfDay(Enum):
    """Discrete time-of-day phases affecting vision and stealth."""

    DAWN = auto()
    DAY = auto()
    DUSK = auto()
    NIGHT = auto()


@dataclass
class GameTime:
    """Tracks elapsed game time with a configurable time scale."""

    total_seconds: float = 0.0
    time_scale: float = 600.0

    @property
    def hours(self) -> float:
        """Return the current in-game hour (0-24)."""
        game_total = self.total_seconds * self.time_scale
        return (game_total / 3600.0) % 24

    @property
    def minutes(self) -> int:
        """Return the current in-game minute (0-59)."""
        return int((self.hours % 1) * 60)

    @property
    def time_of_day(self) -> float:
        """Return the current time of day as a float hour (0.0-24.0).

        Implements IDayNightCycle.time_of_day protocol contract.
        """
        return self.hours

    @property
    def time_phase(self) -> TimeOfDay:
        """Return the discrete time-of-day phase for the current game time."""
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
        """Return the current game time as a formatted 12-hour clock string."""
        h = int(self.hours)
        m = self.minutes
        period = "AM" if h < 12 else "PM"
        display_h = h if h <= 12 else h - 12
        if display_h == 0:
            display_h = 12
        return f"{display_h:02d}:{m:02d} {period}"

    def advance(self, dt: float) -> None:
        """Advance game time by the given delta seconds."""
        self.total_seconds += dt

    def set_time(self, hour: float) -> None:
        """Set the in-game hour, preserving the current day."""
        scaled_hour = (hour % 24) / self.time_scale * 3600.0
        base_days = int(self.total_seconds * self.time_scale / 86400.0)
        self.total_seconds = base_days * 86400.0 / self.time_scale + scaled_hour


class DayNightEffects:
    """Applies vision, stealth, accuracy, and lighting modifiers by time of day."""

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

    def apply_vision_penalty(self, base_range: float, tod: TimeOfDay) -> float:
        """Return the vision range adjusted for the given time of day."""
        modifier = self.VISION_MODIFIERS.get(tod, 1.0)
        return base_range * modifier

    def apply_stealth_bonus(self, base_chance: float, tod: TimeOfDay) -> float:
        """Return the stealth chance increased by the time-of-day bonus."""
        bonus = self.STEALTH_BONUSES.get(tod, 0.0)
        return min(1.0, base_chance + bonus)

    def apply_accuracy_modifier(self, base_accuracy: float, tod: TimeOfDay) -> float:
        """Return the accuracy scaled by the time-of-day modifier."""
        modifier = self.ACCURACY_MODIFIERS.get(tod, 1.0)
        return base_accuracy * modifier

    def get_lighting_color(self, tod: TimeOfDay) -> tuple[int, int, int]:
        """Return the ambient lighting RGB tuple for the given time of day."""
        return self.LIGHTING_COLORS.get(tod, (255, 255, 255))

    def get_combined_vision_modifier(
        self,
        base_range: float,
        tod: TimeOfDay,
        weather_modifier: float = 1.0,
    ) -> float:
        """Return the vision range adjusted for both time of day and weather."""
        vision = self.apply_vision_penalty(base_range, tod)
        return vision * weather_modifier

    def get_combined_stealth_bonus(
        self,
        base_chance: float,
        tod: TimeOfDay,
        weather_concealment: float = 0.0,
    ) -> float:
        """Return the stealth chance adjusted for time of day and weather concealment."""
        stealth = self.apply_stealth_bonus(base_chance, tod)
        return min(1.0, stealth + weather_concealment)


@dataclass
class Searchlight:
    """Sweeping light source that reveals units within an arc during night."""

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
        """Return the list of tiles currently illuminated by the searchlight."""
        illuminated: list[tuple[int, int]] = []
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
        """Return True if the given tile lies within the searchlight's arc."""
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
        """Advance the searchlight sweep direction by the given delta seconds."""
        if not self.is_active:
            return

        self._current_direction += self._sweep_sign * self.sweep_speed * dt
        if self._current_direction > 180 or self._current_direction < -180:
            self._sweep_sign *= -1

    @property
    def current_direction(self) -> float:
        """Return the searchlight's current sweep direction in degrees."""
        return self._current_direction
