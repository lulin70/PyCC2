"""Atmosphere controller - weather, screen flash, and shell casing state.

Extracted from EnhancedRenderer to group related atmospheric effect state and
keep the coordinator focused on high-level render pipeline orchestration.
"""

from __future__ import annotations

import pygame

from pycc2.presentation.rendering.flash_effect_system import FlashEffectSystem
from pycc2.presentation.rendering.shell_casing_system import ShellCasingSystem
from pycc2.presentation.rendering.weather_system import WeatherSystem


class AtmosphereController:
    """Owns weather, screen flash, and shell casing systems."""

    def __init__(self) -> None:
        """Initialize the AtmosphereController."""
        self._flash_sys = FlashEffectSystem()
        self._weather_sys = WeatherSystem()
        self._shell_sys = ShellCasingSystem()

    @property
    def flash_sys(self) -> FlashEffectSystem:
        """Get the flash system."""
        return self._flash_sys

    @property
    def weather_sys(self) -> WeatherSystem:
        """Get the weather system."""
        return self._weather_sys

    @property
    def shell_sys(self) -> ShellCasingSystem:
        """Get the shell system."""
        return self._shell_sys

    def trigger_flash(
        self,
        color: tuple[int, int, int] = (255, 255, 255),
        intensity: float = 0.4,
        duration: float = 0.12,
    ) -> None:
        """Trigger a screen flash overlay effect."""
        self._flash_sys.trigger(color, intensity, duration)

    def update_flash(self, dt: float) -> None:
        """Update screen flash alpha."""
        self._flash_sys.update(dt)

    def set_weather(self, mode: str) -> None:
        """Set weather overlay mode."""
        self._weather_sys.set_mode(mode)

    def update_weather(self, dt: float) -> None:
        """Update weather animation state."""
        self._weather_sys.update(dt)

    def spawn_shell_casing(self, x: float, y: float, direction_rad: float = 0) -> None:
        """Spawn a shell casing ejected from weapon position."""
        self._shell_sys.spawn(x, y, direction_rad)

    def update_shell_casings(self, dt: float) -> None:
        """Update shell casing physics simulation."""
        self._shell_sys.update(dt)

    def render_shell_casings(self, offscreen: pygame.Surface | None, camera) -> None:
        """Render shell casings as small ellipses with fade-out."""
        if offscreen is not None:
            self._shell_sys.render(offscreen, camera)

    def update_screen_size(self, width: int, height: int) -> None:
        """Notify weather system of screen resize."""
        self._weather_sys.update_screen_size(width, height)
