"""Floating combat text popups for CC2-style battlefield feedback."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field

import pygame


@dataclass
class CombatPopup:
    """A single floating text popup."""

    text: str
    x: float
    y: float
    color: tuple[int, int, int]
    created_at: float = field(default_factory=time.time)
    duration: float = 2.0

    @property
    def age(self) -> float:
        return time.time() - self.created_at

    @property
    def is_expired(self) -> bool:
        return self.age > self.duration

    @property
    def alpha(self) -> int:
        """Fade out in last 0.5 seconds."""
        remaining = self.duration - self.age
        if remaining < 0.5:
            return int(255 * remaining / 0.5)
        return 255

    @property
    def offset_y(self) -> float:
        """Float upward over time."""
        return -self.age * 15  # 15 pixels per second upward


class CombatPopupManager:
    """Manages floating combat text popups."""

    def __init__(self, max_popups: int = 20):
        self._popups: deque[CombatPopup] = deque()
        self._max_popups = max_popups
        self._font: pygame.font.Font | None = None
        # Surface pool for popup alpha surfaces
        self._surface_pool: dict[tuple[int, int], pygame.Surface] = {}

    def add_popup(
        self,
        text: str,
        world_x: float,
        world_y: float,
        color: tuple[int, int, int] = (255, 255, 100),
    ) -> None:
        """Add a new combat popup."""
        if self._font is None:
            from pycc2.presentation.ui.font_helper import safe_init_font

            self._font = safe_init_font(13, bold=True)

        self._popups.append(CombatPopup(text=text, x=world_x, y=world_y, color=color))

        # Remove oldest if too many
        if len(self._popups) > self._max_popups:
            self._popups.popleft()

    def add_taking_fire(self, x: float, y: float) -> None:
        self.add_popup("Taking fire!", x, y, (255, 100, 100))

    def add_breaking(self, x: float, y: float) -> None:
        self.add_popup("They're breaking!", x, y, (255, 200, 100))

    def add_pinned(self, x: float, y: float) -> None:
        self.add_popup("Pinned!", x, y, (255, 150, 50))

    def add_out_of_ammo(self, x: float, y: float) -> None:
        self.add_popup("Out of ammo!", x, y, (200, 200, 200))

    def add_kia(self, x: float, y: float) -> None:
        self.add_popup("KIA", x, y, (255, 50, 50))

    def add_surrender(self, x: float, y: float) -> None:
        self.add_popup("Surrender!", x, y, (200, 200, 100))

    def render(self, surface: pygame.Surface, camera) -> None:
        """Render all active popups."""
        # Remove expired
        self._popups = deque(p for p in self._popups if not p.is_expired)

        if not self._popups or self._font is None:
            return

        cam_x = getattr(camera, "offset_x", 0)
        cam_y = getattr(camera, "offset_y", 0)

        for popup in self._popups:
            screen_x = popup.x - cam_x
            screen_y = popup.y - cam_y + popup.offset_y

            # Render text with alpha – reuse cached surface
            text_surf = self._font.render(popup.text, True, popup.color)
            text_size = text_surf.get_size()
            if text_size not in self._surface_pool:
                self._surface_pool[text_size] = pygame.Surface(text_size, pygame.SRCALPHA)
            alpha_surf = self._surface_pool[text_size]
            alpha_surf.fill((0, 0, 0, 0))
            alpha_surf.blit(text_surf, (0, 0))
            alpha_surf.set_alpha(popup.alpha)

            # Draw with shadow for readability – reuse same pool
            shadow_surf = self._font.render(popup.text, True, (0, 0, 0))
            shadow_size = shadow_surf.get_size()
            if shadow_size not in self._surface_pool:
                self._surface_pool[shadow_size] = pygame.Surface(shadow_size, pygame.SRCALPHA)
            shadow_alpha = self._surface_pool[shadow_size]
            shadow_alpha.fill((0, 0, 0, 0))
            shadow_alpha.blit(shadow_surf, (0, 0))
            shadow_alpha.set_alpha(popup.alpha)

            surface.blit(shadow_alpha, (screen_x + 1, screen_y + 1))
            surface.blit(alpha_surf, (screen_x, screen_y))
