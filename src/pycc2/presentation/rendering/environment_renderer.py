"""
Environment Renderer for PyCC2 - Extracted from EnhancedRenderer

Handles all environment and lighting-related rendering:
- Screen overlays (warm tint, vignette)
- Environment lighting (warm overlay + vignette effect)
- Health-based color tinting
- Height-based lighting
- Time-of-day color grading (dawn/noon/dusk/night)
- CC2 authentic color grading
- Dynamic light management (spawn/update/render)
- Lighting configuration API

This module was extracted from EnhancedRenderer following SRP (Single Responsibility Principle).
All method signatures remain unchanged for backward compatibility.
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from pycc2.presentation.rendering.lighting_effects import LightingEffectsSystem
    from pycc2.presentation.rendering.lighting_system import TopDownLightingConfig

logger = logging.getLogger(__name__)


class EnvironmentRenderer:
    """
    Manages environmental visual effects and lighting systems.
    
    Delegated by EnhancedRenderer to maintain clean separation of concerns.
    Handles:
    - Post-processing effects (vignette, warm overlay)
    - Time-of-day lighting simulation
    - Dynamic light sources
    - CC2 color grading pipeline
    """

    # Rendering constants (inherited from coordinator)
    WARM_OVERLAY_COLOR = (255, 220, 160, 12)  # Subtle orange-gold tint
    VIGNETTE_MIN_EDGE = 30  # Minimum vignette edge dimension (pixels)
    VIGNETTE_MAX_ALPHA = 40  # Maximum vignette darkness

    def __init__(self):
        self._lighting_effects_sys = None  # Set via set_lighting_effects()
        self._lighting_config = None  # Set via set_lighting_config()
        self._offscreen = None  # Set via set_offscreen()
        self._cached_screen_size = None
        self._cached_warm_overlay = None
        self._cached_vignette = None

    def set_dependencies(
        self,
        lighting_effects_sys: LightingEffectsSystem | None = None,
        lighting_config: TopDownLightingConfig | None = None,
        offscreen=None,
    ) -> None:
        """Inject dependencies from coordinator."""
        self._lighting_effects_sys = lighting_effects_sys
        self._lighting_config = lighting_config
        self._offscreen = offscreen

    def _get_screen_overlays(self, screen_size: tuple[int, int]) -> tuple[pygame.Surface, pygame.Surface]:
        """Get cached full-screen overlay surfaces (PERF-001).
        
        Returns:
            Tuple of (warm_overlay, vignette) surfaces, cached across frames.
        """
        if self._cached_screen_size != screen_size:
            self._invalidate_surface_cache()
            self._cached_screen_size = screen_size
            
            # Pre-create warm overlay (subtle orange-gold tint)
            self._cached_warm_overlay = pygame.Surface(screen_size, pygame.SRCALPHA)
            self._cached_warm_overlay.fill(self.WARM_OVERLAY_COLOR)
            
            # Pre-create vignette (darker edges)
            self._cached_vignette = pygame.Surface(screen_size, pygame.SRCALPHA)
            screen_w, screen_h = screen_size
            edge_width = max(self.VIGNETTE_MIN_EDGE, screen_w // 8)
            edge_height = max(self.VIGNETTE_MIN_EDGE, screen_h // 8)
            for i in range(edge_height):
                alpha = int(self.VIGNETTE_MAX_ALPHA * (1.0 - i / edge_height))
                pygame.draw.line(self._cached_vignette, (0, 0, 0, alpha), (0, i), (screen_w, i))
            for i in range(edge_height):
                alpha = int(self.VIGNETTE_MAX_ALPHA * (1.0 - i / edge_height))
                y = screen_h - 1 - i
                pygame.draw.line(self._cached_vignette, (0, 0, 0, alpha), (0, y), (screen_w, y))
        
        return self._cached_warm_overlay, self._cached_vignette

    def _invalidate_surface_cache(self) -> None:
        """Clear surface cache when screen size changes (PERF-001)."""
        self._cached_warm_overlay = None
        self._cached_vignette = None
        self._cached_screen_size = None

    def _apply_environment_lighting(self, game_map, camera, units=None) -> None:
        """Apply environment lighting effects to the offscreen buffer.

        Adds:
        - Slight warm tint to the overall scene
        - Slightly darker edges (vignette effect)

        Note: Shadow rendering has been moved to dedicated _render_* methods
              (_render_building_shadows, _render_tree_shadows, _render_unit_shadows)
              which are called separately in the main render pipeline for correct Z-order.
        """
        if self._offscreen is None:
            return

        screen_w, screen_h = self._offscreen.get_size()

        # 1. Warm tint overlay (cached - PERF-001)
        try:
            warm_overlay, vignette = self._get_screen_overlays((screen_w, screen_h))
            self._offscreen.blit(warm_overlay, (0, 0))
        except (ValueError, pygame.error) as e:
            logging.debug(f"Warm tint overlay failed: {e}")

        # 2. Vignette effect (cached - PERF-001)
        try:
            # Reuse cached vignette from _get_screen_overlays()
            self._offscreen.blit(vignette, (0, 0))
        except (ValueError, pygame.error) as e:
            logging.debug(f"Vignette effect failed: {e}")

    def _get_health_tinted_color(self, base_color: tuple, unit) -> tuple:
        """Delegate to LightingEffectsSystem for health-based color tinting."""
        if self._lighting_effects_sys:
            return self._lighting_effects_sys.get_health_tinted_color(base_color, unit)
        return base_color

    def _apply_height_lighting(self, surface: pygame.Surface, height: int) -> pygame.Surface:
        """Delegate to LightingEffectsSystem for height-based lighting."""
        if self._lighting_effects_sys:
            return self._lighting_effects_sys.apply_height_lighting(surface, height)
        return surface

    def _apply_time_of_day_tint(self, surface: pygame.Surface) -> pygame.Surface:
        """Delegate to LightingEffectsSystem for time-of-day color grading."""
        if self._lighting_effects_sys:
            return self._lighting_effects_sys.apply_time_of_day_tint(surface)
        return surface

    def _apply_cc2_color_grading(self, surface: pygame.Surface) -> None:
        """Delegate to LightingEffectsSystem for CC2-style color grading."""
        if self._lighting_effects_sys:
            self._lighting_effects_sys.apply_cc2_color_grading(surface)

    def spawn_dynamic_light(
        self,
        position: tuple[int, int],
        radius: float,
        intensity: float,
        color: tuple[int, int, int] = (255, 255, 200),
        duration_ms: int = 200
    ) -> None:
        """Delegate to LightingEffectsSystem for dynamic light registration."""
        if self._lighting_effects_sys:
            self._lighting_effects_sys.spawn_dynamic_light(
                position, radius, intensity, color, duration_ms
            )

    def update_dynamic_lights(self, dt_ms: int) -> None:
        """Delegate to LightingEffectsSystem for dynamic light lifecycle update."""
        if self._lighting_effects_sys:
            self._lighting_effects_sys.update_dynamic_lights(dt_ms)

    def _render_dynamic_lights(self) -> None:
        """Delegate to LightingEffectsSystem for dynamic light rendering (legacy API)."""
        if self._lighting_effects_sys and self._offscreen:
            self._lighting_effects_sys.render_dynamic_lights(self._offscreen)

    def set_time_of_day(self, tod: str) -> None:
        """
        Set time of day for color grading.
        
        Args:
            tod: Time of day string - 'dawn'/'noon'/'dusk'/'night'
        
        Raises:
            ValueError: If tod is not a valid time of day
        """
        if self._lighting_config is None:
            raise RuntimeError("Lighting config not initialized")
            
        valid_times = ['dawn', 'noon', 'dusk', 'night']
        if tod not in valid_times:
            raise ValueError(f"Invalid time of day: '{tod}'. Must be one of {valid_times}")
        
        self._lighting_config.time_of_day = tod
        logger.debug(f"Lighting: Time of day set to '{tod}'")

    def set_light_intensity(self, intensity: float) -> None:
        """
        Set global light intensity.
        
        Args:
            intensity: Brightness level (0.0 = dark, 1.0 = normal, 2.0 = very bright)
        """
        if self._lighting_config is None:
            raise RuntimeError("Lighting config not initialized")
            
        self._lighting_config.light_intensity = max(0.0, min(2.0, intensity))
        logger.debug(f"Lighting: Intensity set to {self._lighting_config.light_intensity:.2f}")

    def get_lighting_config(self):
        """
        Get current lighting configuration (read-only access).
        
        Returns:
            TopDownLightingConfig: Current lighting configuration
        """
        return self._lighting_config
