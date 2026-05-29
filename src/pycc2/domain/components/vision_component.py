"""
Vision Component

Manages unit vision, line of sight, and detection capabilities.
Integrates with fog of war system for visibility calculations.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass(slots=True)
class VisionComponent:
    range_tiles: int = 6
    angle_rad: float = math.pi
    last_update_tick: int = 0
    visible_tiles: set[tuple[int, int]] = field(default_factory=set)

    def needs_update(self, current_tick: int, interval: int = 5) -> bool:
        if self.last_update_tick == 0 and current_tick == 0:
            return True
        return current_tick - self.last_update_tick >= interval

    def mark_updated(self, tick: int) -> None:
        self.last_update_tick = tick

    def can_see_tile(self, x: int, y: int) -> bool:
        return (x, y) in self.visible_tiles

    def reveal_tiles(self, tiles: set[tuple[int, int]]) -> set[tuple[int, int]]:
        new_tiles = tiles - self.visible_tiles
        self.visible_tiles.update(tiles)
        return new_tiles

    def clear_vision(self) -> None:
        self.visible_tiles.clear()

    def effective_range(self, time_of_day: str | None = None, weather_modifier: float = 1.0) -> int:
        """Get effective vision range after applying day/night and weather modifiers.

        Args:
            time_of_day: One of 'dawn', 'day', 'dusk', 'night'. None = no modifier.
            weather_modifier: Multiplier from weather (1.0 = clear).
        """
        base = self.range_tiles
        # R5: Night battle visibility reduction
        tod_modifiers = {
            'dawn': 0.9,
            'day': 1.0,
            'dusk': 0.8,
            'night': 0.3,
        }
        tod_mod = tod_modifiers.get(time_of_day, 1.0) if time_of_day else 1.0
        return max(1, int(base * tod_mod * weather_modifier))
