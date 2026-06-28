"""Screen-wide effects rendering.

Extracted from EnhancedRenderer to isolate:
- Screen flash overlay (P2-03)
- Weather overlay rendering (P3-01)

Suppression overlay rendering has been moved to
`suppression_overlay_renderer.py` (SRP).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from pycc2.presentation.rendering.flash_effect_system import FlashEffectSystem
    from pycc2.presentation.rendering.weather_system import WeatherSystem

logger = logging.getLogger(__name__)


class ScreenEffectsRenderer:
    """Renders full-screen visual effects on top of the world."""

    def __init__(self) -> None:
        """Initialize the ScreenEffectsRenderer."""
        self._flash_surf_cache: pygame.Surface | None = None

    def render_effects(
        self,
        offscreen: pygame.Surface | None,
        flash_sys: FlashEffectSystem | None,
        weather_sys: WeatherSystem | None,
        dirty_tracker,
    ) -> None:
        """Render visual effects (flash, weather overlays)."""
        if offscreen is None:
            return

        # P2-03: Screen flash overlay (after all rendering, before atomic flip)
        if flash_sys is not None and flash_sys.is_active:
            # PERF: Flash is full-screen overlay -> must dirty entire screen
            if dirty_tracker is not None:
                dirty_tracker.mark_full_dirty()
            # Reuse cached flash surface (avoid per-frame allocation)
            flash_size = offscreen.get_size()
            if self._flash_surf_cache is None or self._flash_surf_cache.get_size() != flash_size:
                self._flash_surf_cache = pygame.Surface(flash_size, pygame.SRCALPHA)
            flash_surf = self._flash_surf_cache
            flash_surf.fill((0, 0, 0, 0))  # Clear for reuse
            color = flash_sys.color
            if color is not None:
                flash_surf.fill((*color, int(max(0, flash_sys.alpha))))
                offscreen.blit(flash_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        # P3-01: Weather atmosphere overlay (light_fog / dust / smoke)
        if weather_sys is not None and weather_sys.mode != "clear":
            # PERF: weather overlays can be full-screen -> mark full dirty
            if dirty_tracker is not None:
                dirty_tracker.mark_full_dirty()
            weather_sys.render(offscreen)

    def invalidate_cache(self) -> None:
        """Clear cached overlay surfaces when screen size changes."""
        self._flash_surf_cache = None
