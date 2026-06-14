"""
Top-Down Lighting System for CC2-Style Rendering

Provides lighting configuration and color grading for top-down/isometric views.
Includes time-of-day effects, dynamic lights, and CC2-authentic color grading.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pygame

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    pass


@dataclass
class TopDownLightingConfig:
    """顶部视角光照配置 - 俯视/等距游戏专用"""
    light_angle: float = -math.pi / 4  # 光源方向：左上45度（弧度）→ 阴影投射向右下
    light_intensity: float = 1.0        # 全局亮度 (0.0-2.0)
    ambient_light: float = 0.4          # 环境光比例 (0.0-1.0)
    shadow_darkness: float = 0.6        # 阴影深度 (0.0-1.0)
    time_of_day: str = "noon"           # dawn/noon/dusk/night
    enable_dynamic_lights: bool = True   # 是否启用动态光源


class LightingSystem:
    """Manages lighting effects for the renderer.

    Handles:
    - Time-of-day color grading
    - Dynamic light sources (explosions, muzzle flashes)
    - Height-based lighting
    - CC2-style color grading
    """

    def __init__(self, config: TopDownLightingConfig | None = None):
        self._config = config or TopDownLightingConfig()
        self._dynamic_lights: list[dict] = []
        self._max_dynamic_lights = 8
        self._tod_tint_cache: pygame.Surface | None = None
        self._last_time_of_day: str = self._config.time_of_day
        self._light_surf_cache: dict[int, pygame.Surface] = {}

    @property
    def config(self) -> TopDownLightingConfig:
        """Get current lighting configuration."""
        return self._config

    def set_time_of_day(self, tod: str) -> None:
        """
        Set time of day for color grading.

        Args:
            tod: Time of day string - 'dawn'/'noon'/'dusk'/'night'

        Raises:
            ValueError: If tod is not a valid time of day
        """
        valid_times = ['dawn', 'noon', 'dusk', 'night']
        if tod not in valid_times:
            raise ValueError(f"Invalid time of day: '{tod}'. Must be one of {valid_times}")

        self._config.time_of_day = tod

    def set_light_intensity(self, intensity: float) -> None:
        """
        Set global light intensity.

        Args:
            intensity: Brightness level (0.0 = dark, 1.0 = normal, 2.0 = very bright)
        """
        self._config.light_intensity = max(0.0, min(2.0, intensity))

    def add_dynamic_light(self, x: int, y: int, radius: int,
                          color: tuple[int, int, int],
                          intensity: float = 1.0,
                          duration_ms: int = 500) -> None:
        """Add a temporary dynamic light source.

        Used for explosions, muzzle flashes, etc.
        Automatically removed after duration expires.
        """
        if len(self._dynamic_lights) >= self._max_dynamic_lights:
            self._dynamic_lights.pop(0)

        self._dynamic_lights.append({
            'x': x, 'y': y,
            'radius': radius,
            'color': color,
            'intensity': intensity,
            'duration': duration_ms,
            'elapsed': 0,
        })

    def update(self, dt_ms: int) -> None:
        """Update dynamic lights (remove expired ones)."""
        alive = []
        for light in self._dynamic_lights:
            light['elapsed'] += dt_ms
            if light['elapsed'] < light['duration']:
                alive.append(light)
        self._dynamic_lights = alive

    def apply_height_lighting(self, surface: pygame.Surface, height: int) -> pygame.Surface:
        """Apply height-based lighting to a surface.

        Higher elevations appear brighter (more direct light).
        """
        if height == 0:
            return surface

        result = surface.copy()
        result.unlock()

        factor = 1.0 + (height * 0.05)
        factor = min(2.0, max(0.5, factor))

        for y in range(surface.get_height()):
            for x in range(surface.get_width()):
                color = surface.get_at((x, y))
                if color.a > 0:
                    new_color = pygame.Color(
                        min(255, int(color.r * factor)),
                        min(255, int(color.g * factor)),
                        min(255, int(color.b * factor)),
                        color.a
                    )
                    result.set_at((x, y), new_color)

        result.lock()
        return result

    def apply_time_of_day_tint(self, surface: pygame.Surface) -> pygame.Surface:
        """Apply time-of-day color tinting to a surface.

        Different times have different color casts:
        - dawn: warm orange/pink tones
        - noon: neutral (no tint)
        - dusk: warm red/orange tones
        - night: cool blue tones
        """
        if self._config.time_of_day == 'noon':
            return surface

        tod = self._config.time_of_day

        tint_maps = {
            'dawn': {
                'r_mult': 1.15, 'g_mult': 1.05, 'b_mult': 0.9,
                'r_add': 15, 'g_add': 5, 'b_add': -10
            },
            'dusk': {
                'r_mult': 1.2, 'g_mult': 0.95, 'b_mult': 0.8,
                'r_add': 20, 'g_add': 0, 'b_add': -20
            },
            'night': {
                'r_mult': 0.8, 'g_mult': 0.85, 'b_mult': 1.1,
                'r_add': -20, 'g_add': -10, 'b_add': 10
            }
        }

        if tod not in tint_maps:
            return surface

        tint = tint_maps[tod]
        result = surface.copy()

        intensity = self._config.light_intensity

        for y in range(surface.get_height()):
            for x in range(surface.get_width()):
                color = surface.get_at((x, y))
                if color.a > 0:
                    new_r = min(255, max(0, int(color.r * tint['r_mult'] * intensity + tint['r_add'])))
                    new_g = min(255, max(0, int(color.g * tint['g_mult'] * intensity + tint['g_add'])))
                    new_b = min(255, max(0, int(color.b * tint['b_mult'] * intensity + tint['b_add'])))

                    result.set_at((x, y), pygame.Color(new_r, new_g, new_b, color.a))

        return result

    def apply_cc2_color_grading(self, surface: pygame.Surface) -> None:
        """
        Apply CC2 authentic color grading in-place.

        CC2 visual characteristics:
        - Slightly desaturated (military documentary look)
        - Lifted blacks (slightly gray instead of pure black)
        - Warm overall tone (1997 CRT monitor feel)
        - Reduced contrast (flat appearance)
        """
        surface.lock()

        try:
            pixel_array = pygame.surfarray.pixels3d(surface)

            # CC2 color grading parameters
            saturation = 0.85   # Slight desaturation
            black_lift = 12     # Lifted blacks (gray instead of black)
            contrast = 0.92     # Slightly reduced contrast
            warmth = 1.03       # Slight warm tint (red channel boost)

            # Apply grading to all pixels
            r_channel = pixel_array[:, :, 0].astype(int)
            g_channel = pixel_array[:, :, 1].astype(int)
            b_channel = pixel_array[:, :, 2].astype(int)

            # Convert to luminance for desaturation
            luminance = (0.299 * r_channel + 0.587 * g_channel + 0.114 * b_channel)

            # Desaturate by mixing with luminance
            r_channel = (r_channel * saturation + luminance * (1 - saturation)).astype(int)
            g_channel = (g_channel * saturation + luminance * (1 - saturation)).astype(int)
            b_channel = (b_channel * saturation + luminance * (1 - saturation)).astype(int)

            # Apply contrast adjustment around midpoint (128)
            r_channel = 128 + ((r_channel.astype(float) - 128) * contrast).astype(int)
            g_channel = 128 + ((g_channel.astype(float) - 128) * contrast).astype(int)
            b_channel = 128 + ((b_channel.astype(float) - 128) * contrast).astype(int)

            # Apply warmth (boost red slightly)
            r_channel = (r_channel.astype(float) * warmth).astype(int)

            # Lift blacks
            r_channel = np.clip(r_channel + black_lift, 0, 255)
            g_channel = np.clip(g_channel + black_lift, 0, 255)
            b_channel = np.clip(b_channel + black_lift, 0, 255)

            # Write back
            pixel_array[:, :, 0] = r_channel.astype(np.uint8)
            pixel_array[:, :, 1] = g_channel.astype(np.uint8)
            pixel_array[:, :, 2] = b_channel.astype(np.uint8)

            del pixel_array
        except Exception:
            pass
        finally:
            surface.unlock()

    def render_dynamic_lights(self, surface: pygame.Surface) -> None:
        """Render dynamic light sources onto the surface.

        Creates additive glow effects around each active light source.
        Uses radial gradients for soft falloff.
        """
        if not self._dynamic_lights or surface is None:
            return

        for light in self._dynamic_lights:
            progress = light['elapsed'] / max(light['duration'], 1)
            fade = 1.0 - progress

            radius = int(light['radius'] * fade)
            if radius < 1:
                continue

            cx, cy = int(light['x']), int(light['y'])
            color = light['color']
            intensity = light['intensity'] * fade

            # Create radial gradient surface
            size = radius * 2 + 4
            try:
                light_surf = self._light_surf_cache.get(size)
                if light_surf is None:
                    light_surf = pygame.Surface((size, size), pygame.SRCALPHA)
                    self._light_surf_cache[size] = light_surf
                light_surf.fill((0, 0, 0, 0))
                center = size // 2

                for r in range(radius, 0, -2):
                    alpha = int(60 * intensity * (r / radius))
                    grad_color = (*color[:3], alpha)
                    pygame.draw.circle(light_surf, grad_color, (center, center), r)

                # Blit onto main surface
                surface.blit(light_surf, (cx - center, cy - center),
                           special_flags=pygame.BLEND_RGBA_ADD)
            except Exception as e:
                logger.warning("Dynamic light rendering failed: %s", e)
