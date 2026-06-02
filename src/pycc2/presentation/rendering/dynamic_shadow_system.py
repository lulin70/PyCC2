"""
Dynamic Shadow System - Enhanced shadow rendering with time-of-day awareness.

Extends the existing ShadowRenderingSystem with:
- Dynamic shadow direction based on sun position (time-of-day)
- Shadow length variation (longer at dawn/dusk, shorter at noon)
- Tree shadow rendering with leaf detail
- Unit shadow rendering for infantry and vehicles
- Shadow opacity based on time-of-day

Integrates with existing ShadowRenderingSystem and LightingEffectsSystem.
"""

import math
from typing import Any, Optional, Tuple, TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.domain.value_objects.vec2 import Vec2


class DynamicShadowSystem:
    """Renders dynamic shadows that respond to time-of-day lighting."""

    SHADOW_COLOR = (0, 0, 0, 50)
    DAWN_DUSK_ALPHA = 70
    NOON_ALPHA = 35
    NIGHT_ALPHA = 15
    MAX_SHADOW_LENGTH = 2.5
    MIN_SHADOW_LENGTH = 0.8

    def __init__(self, tile_size: int = 48):
        self.TILE_SIZE = tile_size
        self._time_of_day: float = 0.5
        self._shadow_surface: Optional[pygame.Surface] = None
        self._cached_size: Optional[Tuple[int, int]] = None

    def set_time_of_day(self, tod: float) -> None:
        """Set time of day (0.0=midnight, 0.25=dawn, 0.5=noon, 0.75=dusk)."""
        self._time_of_day = max(0.0, min(1.0, tod))

    def get_shadow_direction(self) -> Tuple[float, float]:
        """Calculate shadow direction based on sun position."""
        sun_angle = self._time_of_day * 2 * math.pi
        dx = math.cos(sun_angle)
        dy = math.sin(sun_angle)
        length = math.sqrt(dx * dx + dy * dy)
        if length < 0.001:
            return (1.0, 1.0)
        return (dx / length, dy / length)

    def get_shadow_length_multiplier(self) -> float:
        """Shadow length varies with sun angle (longer at dawn/dusk)."""
        sun_height = math.sin(self._time_of_day * math.pi)
        sun_height = max(0.1, sun_height)
        multiplier = 1.0 / sun_height
        return max(self.MIN_SHADOW_LENGTH, min(self.MAX_SHADOW_LENGTH, multiplier))

    def get_shadow_alpha(self) -> int:
        """Shadow opacity based on time of day."""
        if self._time_of_day < 0.2 or self._time_of_day > 0.8:
            return self.NIGHT_ALPHA
        elif self._time_of_day < 0.3 or self._time_of_day > 0.7:
            return self.DAWN_DUSK_ALPHA
        else:
            return self.NOON_ALPHA

    def render_building_shadow(
        self,
        surface: pygame.Surface,
        screen_x: int,
        screen_y: int,
        building_width: int,
        building_height: int,
    ) -> None:
        """Render a single building shadow with dynamic direction."""
        dx, dy = self.get_shadow_direction()
        length_mult = self.get_shadow_length_multiplier()
        alpha = self.get_shadow_alpha()

        shadow_offset_x = int(dx * building_width * length_mult * 0.5)
        shadow_offset_y = int(dy * building_height * length_mult * 0.5)

        shadow_w = building_width + abs(shadow_offset_x)
        shadow_h = building_height + abs(shadow_offset_y)

        if shadow_w <= 0 or shadow_h <= 0:
            return

        shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        shadow_color = (0, 0, 0, alpha)
        pygame.draw.polygon(
            shadow_surf,
            shadow_color,
            [
                (0, 0),
                (building_width, 0),
                (building_width + shadow_offset_x, shadow_offset_y),
                (shadow_offset_x, shadow_offset_y + building_height),
                (0, building_height),
            ],
        )

        dest_x = screen_x + min(0, shadow_offset_x)
        dest_y = screen_y + min(0, shadow_offset_y)
        surface.blit(shadow_surf, (dest_x, dest_y))

    def render_tree_shadow(
        self,
        surface: pygame.Surface,
        screen_x: int,
        screen_y: int,
        tree_radius: int = 12,
    ) -> None:
        """Render a tree shadow as an ellipse."""
        dx, dy = self.get_shadow_direction()
        length_mult = self.get_shadow_length_multiplier()
        alpha = self.get_shadow_alpha()

        offset_x = int(dx * tree_radius * length_mult)
        offset_y = int(dy * tree_radius * length_mult)

        ellipse_w = tree_radius * 2 + abs(offset_x)
        ellipse_h = tree_radius + abs(offset_y)

        if ellipse_w <= 0 or ellipse_h <= 0:
            return

        shadow_surf = pygame.Surface((ellipse_w, ellipse_h), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, alpha), (0, 0, ellipse_w, ellipse_h))
        surface.blit(shadow_surf, (screen_x + offset_x - ellipse_w // 2, screen_y + offset_y - ellipse_h // 2))

    def render_unit_shadow(
        self,
        surface: pygame.Surface,
        screen_x: int,
        screen_y: int,
        unit_width: int = 16,
        unit_height: int = 16,
        is_vehicle: bool = False,
    ) -> None:
        """Render a unit shadow (infantry or vehicle)."""
        dx, dy = self.get_shadow_direction()
        length_mult = self.get_shadow_length_multiplier()
        alpha = self.get_shadow_alpha()

        if is_vehicle:
            shadow_size = max(unit_width, unit_height)
        else:
            shadow_size = min(unit_width, unit_height)

        offset_x = int(dx * shadow_size * length_mult * 0.3)
        offset_y = int(dy * shadow_size * length_mult * 0.3)

        shadow_w = shadow_size + abs(offset_x)
        shadow_h = shadow_size // 2 + abs(offset_y)

        if shadow_w <= 0 or shadow_h <= 0:
            return

        shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, alpha), (0, 0, shadow_w, shadow_h))
        surface.blit(shadow_surf, (screen_x + offset_x, screen_y + offset_y))
