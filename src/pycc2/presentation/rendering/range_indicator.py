"""Range Indicator System - Show weapon range circles for selected unit."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit
    from pycc2.presentation.rendering.camera import Camera


class RangeType(Enum):
    """Types of range indicators."""
    MIN_RANGE = auto()   # Inner circle (minimum effective range)
    MAX_RANGE = auto()   # Outer circle (maximum range)


@dataclass(slots=True)
class RangeIndicator:
    """
    Weapon range indicator display system.

    Features:
    - Show minimum and maximum weapon range circles
    - Semi-transparent rendering (doesn't obscure gameplay)
    - Auto-update when selected unit changes
    - Support for multiple weapons

    CC2 Behavior:
    - Inner yellow circle: minimum range (too close = penalty)
    - Outer red circle: maximum engagement range
    - Helps player visualize threat/engagement zones
    """

    active_unit: Unit | None = None
    _min_range: float = 0.0
    _max_range: float = 0.0
    _visible: bool = False
    _alpha: int = 128  # Semi-transparent
    _range_surf: object | None = None
    _range_surf_size: int = 0

    def set_unit(self, unit: Unit | None) -> None:
        """Set the currently selected unit for range display."""
        self.active_unit = unit
        if unit:
            ranges = self._calculate_ranges(unit)
            self._min_range = ranges[0]
            self._max_range = ranges[1]
            self._visible = True
        else:
            self._min_range = 0.0
            self._max_range = 0.0
            self._visible = False

    def _calculate_ranges(self, unit: Unit) -> tuple[float, float]:
        """Calculate min/max range from unit's weapon."""
        min_range = 0.0
        max_range = 0.0

        weapon_comp = getattr(unit, 'weapon_component', None)
        if weapon_comp:
            min_range = getattr(weapon_comp, 'min_range', 0.0)
            max_range = getattr(weapon_comp, 'max_range', 0.0)

        if max_range == 0.0:
            max_range = getattr(unit, 'vision_range', 10.0)

        return (min_range, max_range)

    def get_ranges(self) -> tuple[float, float]:
        """Get current (min_range, max_range)."""
        return (self._min_range, self._max_range)

    def clear(self) -> None:
        """Clear the range indicator."""
        self.active_unit = None
        self._visible = False
        self._min_range = 0.0
        self._max_range = 0.0

    @property
    def is_visible(self) -> bool:
        return self._visible and self.active_unit is not None

    def render(
        self,
        surface,
        camera: Camera,
        unit_pos: tuple[float, float] | None = None,
    ) -> None:
        """
        Render range circles on surface.

        Draws two concentric circles:
        - Inner circle (yellow, semi-transparent): minimum range
        - Outer circle (red, semi-transparent): maximum range

        Args:
            surface: Pygame surface to draw on
            camera: Camera for coordinate transformation
            unit_pos: Override position (default: use active_unit.position)
        """
        if not self.is_visible:
            return

        try:
            import pygame

            pos = unit_pos
            if pos is None and self.active_unit:
                pos = (
                    self.active_unit.position_component.x,
                    self.active_unit.position_component.y,
                )

            if pos is None:
                return

            screen_pos = camera.world_to_screen(__to_vec2(pos))

            scale = camera.zoom
            min_radius = int(self._min_range * 32 * scale)  # 32 pixels per tile
            max_radius = int(self._max_range * 32 * scale)

            if max_radius > 0:
                surf_size = max_radius * 2 + 4
                if self._range_surf is None or self._range_surf_size != surf_size:
                    self._range_surf = pygame.Surface((surf_size, surf_size), pygame.SRCALPHA)
                    self._range_surf_size = surf_size
                self._range_surf.fill((0, 0, 0, 0))
                center = (max_radius + 2, max_radius + 2)

                if min_radius > 0:
                    pygame.draw.circle(
                        self._range_surf, (255, 255, 0, self._alpha),
                        center, min_radius, 2
                    )

                pygame.draw.circle(
                    self._range_surf, (255, 0, 0, self._alpha),
                    center, max_radius, 2
                )

                surface.blit(
                    self._range_surf,
                    (int(screen_pos[0]) - max_radius - 2,
                     int(screen_pos[1]) - max_radius - 2),
                )

        except Exception as e:
            logging.debug(f"Range indicator rendering failed: {e}")

    def contains_point(
        self,
        point: tuple[float, float],
        unit_pos: tuple[float, float],
    ) -> str:
        """
        Check if a point is within range zones.

        Returns:
            'inside_min': Inside minimum range (too close)
            'between': Between min and max (optimal)
            'outside_max': Beyond maximum range
            'no_unit': No unit selected
        """
        if not self.active_unit:
            return 'no_unit'

        dx = point[0] - unit_pos[0]
        dy = point[1] - unit_pos[1]
        distance = (dx * dx + dy * dy) ** 0.5

        if distance < self._min_range:
            return 'inside_min'
        elif distance <= self._max_range:
            return 'between'
        else:
            return 'outside_max'


def __to_vec2(pos: tuple[float, float]):
    """Helper to convert tuple to Vec2."""
    from pycc2.domain.value_objects.vec2 import Vec2
    return Vec2(pos[0], pos[1])
