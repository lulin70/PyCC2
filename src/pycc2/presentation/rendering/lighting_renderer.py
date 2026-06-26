"""
Lighting Renderer — applies color grading and illumination overlays for day-night cycle.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pygame


from pycc2.domain.systems.day_night_cycle import (
    DayNightEffects,
    Searchlight,
    TimeOfDay,
)


class LightingRenderer:
    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self._overlay_surface: pygame.Surface | None = None
        self._searchlight_surface: pygame.Surface | None = None
        _effects = DayNightEffects()
        self._init_surfaces()

    def _init_surfaces(self) -> None:
        import pygame

        self._overlay_surface = pygame.Surface(
            (self.screen_width, self.screen_height), pygame.SRCALPHA
        )
        self._searchlight_surface = pygame.Surface(
            (self.screen_width, self.screen_height), pygame.SRCALPHA
        )

    def render(
        self,
        screen,
        time_of_day: TimeOfDay,
        searchlights: list[Searchlight] | None = None,
    ) -> None:

        effects = DayNightEffects()
        color = effects.get_lighting_color(time_of_day)

        if time_of_day != TimeOfDay.DAY:
            alpha = self._calculate_overlay_alpha(time_of_day)
            tint_color = (*color, alpha)
            if self._overlay_surface is None:
                return
            self._overlay_surface.fill(tint_color)
            screen.blit(self._overlay_surface, (0, 0))

        if searchlights and time_of_day == TimeOfDay.NIGHT:
            self._render_searchlights(screen, searchlights)

    def _calculate_overlay_alpha(self, time_of_day: TimeOfDay) -> int:
        alphas = {
            TimeOfDay.DAWN: 60,
            TimeOfDay.DAY: 0,
            TimeOfDay.DUSK: 80,
            TimeOfDay.NIGHT: 140,
        }
        return alphas.get(time_of_day, 0)

    def _render_searchlights(self, screen, searchlights: list[Searchlight]) -> None:
        import pygame

        if self._searchlight_surface is None:
            return
        self._searchlight_surface.fill((0, 0, 0, 0))
        for sl in searchlights:
            if not sl.is_active:
                continue
            center_x = sl.position_x
            center_y = sl.position_y
            radius = sl.reveal_range * 10
            pygame.draw.circle(
                self._searchlight_surface,
                (255, 255, 200, 30),
                (center_x, center_y),
                radius,
            )
        screen.blit(self._searchlight_surface, (0, 0), special_flags=pygame.BLEND_ADD)

    def resize(self, width: int, height: int) -> None:
        self.screen_width = width
        self.screen_height = height
        self._init_surfaces()
