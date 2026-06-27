"""Weather Atmosphere Overlay System for PyCC2 renderer.

Extracted from EnhancedRenderer (God Class refactoring).
Manages atmospheric weather overlays (clear, light fog, dust, smoke).

Responsibilities:
- Set weather mode and initialize particle state accordingly
- Animate drifting particles each frame (dust/smoke modes)
- Render weather overlay onto the offscreen buffer

Needs screen dimensions for particle initialization and bounds checking;
otherwise fully self-contained.
"""

from __future__ import annotations

import contextlib
import logging
import math
import random

import pygame

logger = logging.getLogger(__name__)

# Default fallback screen size when offscreen surface is not yet available
_FALLBACK_SCREEN_SIZE = (800, 600)


class WeatherSystem:
    """Atmospheric weather overlay manager.

    Supported modes:
        clear     - No overlay (default)
        light_fog - Subtle uniform gray fog layer
        dust      - Drifting dust particles (horizontal drift + gentle wave)
        smoke     - Drifting smoke particles (slower turbulent drift)
    """

    VALID_MODES = {"clear", "light_fog", "dust", "smoke"}

    def __init__(self) -> None:
        self._mode: str = "clear"
        self._alpha: float = 0.0
        self._particles: list[tuple[float, float, float, float]] = []  # (x, y, speed, size)
        self._screen_size: tuple[int, int] = _FALLBACK_SCREEN_SIZE
        # Fog surface cache – lazy init
        self._fog_surf_cache: pygame.Surface | None = None
        self._fog_surf_cache_size: tuple[int, int] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_mode(self, mode: str) -> None:
        """Set weather overlay mode.

        Args:
            mode: One of 'clear', 'light_fog', 'dust', or 'smoke'.

        """
        if mode not in self.VALID_MODES:
            logger.warning("Invalid weather mode '%s'. Valid modes: %s", mode, self.VALID_MODES)
            return
        self._mode = mode
        if mode == "clear":
            self._alpha = 0.0
            self._particles = []
        elif mode == "light_fog":
            self._alpha = 0.15  # subtle gray fog
        elif mode == "dust":
            self._alpha = 0.12
            self._init_dust_particles()
        elif mode == "smoke":
            self._alpha = 0.18
            self._init_smoke_particles()
        logger.debug("Weather mode set to '%s' (alpha=%.2f)", mode, self._alpha)

    def update_screen_size(self, width: int, height: int) -> None:
        """Update cached screen dimensions (call on resize / initialize).

        Args:
            width: Screen width in pixels.
            height: Screen height in pixels.

        """
        self._screen_size = (width, height)

    def update(self, dt: float) -> None:
        """Update weather animation state each frame.

        Args:
            dt: Delta time in seconds since last frame.

        """
        if self._mode == "dust" and self._particles:
            w = self._screen_size[0]
            for i, (x, y, speed, size) in enumerate(self._particles):
                nx = x + speed * dt * 20
                ny = y + math.sin(x * 0.01) * 0.5  # gentle wave
                if nx > w:
                    nx = -size
                self._particles[i] = (nx, ny, speed, size)
        elif self._mode == "smoke" and self._particles:
            w, h = self._screen_size
            for i, (x, y, speed, size) in enumerate(self._particles):
                nx = x + speed * dt * 10
                ny = y + math.sin(x * 0.005 + y * 0.008) * 1.0  # slow turbulent drift
                if nx > w + size:
                    nx = -size
                    ny = random.randint(0, h)
                elif nx < -size:
                    nx = w + size
                    ny = random.randint(0, h)
                self._particles[i] = (nx, ny, speed, size)

    def render(self, offscreen: pygame.Surface) -> None:
        """Render weather overlay onto the offscreen buffer.

        Args:
            offscreen: The off-screen rendering surface to draw onto.

        """
        if self._mode == "clear" or self._alpha <= 0:
            return

        if self._mode == "light_fog":
            fog_size = offscreen.get_size()
            if self._fog_surf_cache is None or self._fog_surf_cache_size != fog_size:
                self._fog_surf_cache = pygame.Surface(fog_size, pygame.SRCALPHA)
                self._fog_surf_cache_size = fog_size
            fog_surf = self._fog_surf_cache
            fog_surf.fill((0, 0, 0, 0))
            fog_surf.fill((180, 175, 170, int(self._alpha * 255)))
            offscreen.blit(fog_surf, (0, 0))
        elif self._mode in ("dust", "smoke"):
            color = (160, 140, 110) if self._mode == "dust" else (80, 75, 70)
            alpha = int(self._alpha * 200)
            for px, py, _, sz in self._particles:
                with contextlib.suppress(Exception):
                    pygame.draw.circle(offscreen, (*color, alpha), (int(px), int(py)), int(sz))

    # ------------------------------------------------------------------
    # Read-only properties
    # ------------------------------------------------------------------

    @property
    def mode(self) -> str:
        """Current weather mode string."""
        return self._mode

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _init_dust_particles(self) -> None:
        """Initialize drifting dust particle positions."""
        w, h = self._screen_size
        self._particles = [
            (
                random.randint(0, w),
                random.randint(0, h),
                random.uniform(10, 40),
                random.uniform(1, 3),
            )
            for _ in range(30)
        ]

    def _init_smoke_particles(self) -> None:
        """Initialize drifting smoke particle positions."""
        w, h = self._screen_size
        self._particles = [
            (
                random.randint(0, w),
                random.randint(0, h),
                random.uniform(5, 20),
                random.uniform(3, 8),
            )
            for _ in range(20)
        ]


# Re-export WeatherRenderer so existing imports from this module keep working
# after the class was extracted into weather_renderer.py during v0.3.37 refactoring.
from pycc2.presentation.rendering.weather_renderer import WeatherRenderer as WeatherRenderer
