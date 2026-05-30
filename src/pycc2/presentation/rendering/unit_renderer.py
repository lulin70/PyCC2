"""
Unit Renderer Module for CC2-Style Games

Handles all unit-related rendering including:
- Unit drawing with health-based coloring
- Direction indicators
- Movement mode overlays
- Damage visual effects (VFX)
- Unit shadows
- Selection highlighting
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

import pygame

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit
    from pycc2.presentation.rendering.camera import Camera


class UnitRenderer:
    """Handles all unit rendering operations.

    This class manages:
    - Drawing units with appropriate sprites/textures
    - Health-based color tinting (green→yellow→red)
    - Direction and facing indicators
    - Movement mode visual overlays
    - Damage VFX (sparks, smoke, etc.)
    - Shadow rendering for units
    """

    def __init__(self, parent_renderer):
        """Initialize with reference to parent EnhancedRenderer."""
        self._parent = parent_renderer

    def draw_units(self, units: list[Unit], camera: Camera,
                   selected_unit_ids: set[str] | None = None) -> None:
        """Main unit drawing entry point.

        Args:
            units: List of units to render
            camera: Camera for coordinate transformation
            selected_unit_ids: Set of currently selected unit IDs (for highlighting)
        """
        if hasattr(self._parent, '_draw_units'):
            self._parent._draw_units(units, camera, selected_unit_ids)

    def get_health_tinted_color(self, base_color: tuple, unit) -> tuple:
        """Apply health-based tinting to a unit color.

        Returns green-ish for healthy, yellow for damaged, red for critical.
        """
        if hasattr(self._parent, '_get_health_tinted_color'):
            return self._parent._get_health_tinted_color(base_color, unit)
        return base_color

    def draw_direction_indicator(self, surface: pygame.Surface,
                                  cx: int, cy: int,
                                  unit) -> None:
        """Draw direction/facing indicator for a unit."""
        if hasattr(self._parent, '_draw_direction_indicator'):
            self._parent._draw_direction_indicator(surface, cx, cy, unit)

    def draw_damage_vfx(self, unit, cx: int, cy: int) -> None:
        """Draw damage visual effects for a damaged unit."""
        if hasattr(self._parent, '_draw_damage_vfx'):
            self._parent._draw_damage_vfx(unit, cx, cy)

    def draw_movement_mode_overlay(self, surface: pygame.Surface,
                                    x: int, y: int,
                                    unit, size: int = 24) -> None:
        """Draw movement mode indicator overlay."""
        if hasattr(self._parent, '_draw_movement_mode_overlay'):
            self._parent._draw_movement_mode_overlay(surface, x, y, unit, size)

    def draw_unit_shadows(self, units: list, camera: Camera) -> None:
        """Render shadows beneath all visible units."""
        if hasattr(self._parent, '_render_unit_shadows'):
            # Use the newer version if available
            self._parent._render_unit_shadows(units, camera)
        elif hasattr(self._parent, '_draw_unit_shadows'):
            # Fallback to older version
            self._parent._draw_unit_shadows(units, camera)
