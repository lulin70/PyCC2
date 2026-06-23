"""Lightweight tooltip display manager for CC2 UI elements.

Provides timed hover-tooltips with a short delay to avoid flickering.
Designed for CC2 dark-toned UI (deep gray background, off-white text).

Extracted from cc2_bottom_panel.py for maintainability.
"""

from __future__ import annotations

import time

import pygame
from pygame import Surface, font


class TooltipManager:
    """Simple tooltip display manager for UI elements.

    Provides timed hover-tooltips with a short delay to avoid flickering.
    Designed for CC2 dark-toned UI (deep gray background, off-white text).
    """

    def __init__(self, font_size: int = 11, delay: float = 0.4) -> None:
        self._text: str = ""
        self._pos: tuple[int, int] = (0, 0)
        self._visible: bool = False
        self._delay: float = delay
        self._hover_start: float = 0.0
        self._font_size: int = font_size

    def begin_hover(self, text: str, pos: tuple[int, int]) -> None:
        """Called when mouse enters a tooltippable area."""
        if text != self._text:
            self._text = text
            self._pos = pos
            self._hover_start = time.monotonic()
            self._visible = False

    def end_hover(self) -> None:
        """Called when mouse leaves the area."""
        self._text = ""
        self._visible = False

    def update(self, dt: float) -> None:
        """Advance tooltip timer; show after delay elapsed."""
        if self._text and not self._visible:
            elapsed = time.monotonic() - self._hover_start
            if elapsed >= self._delay:
                self._visible = True

    def render(self, surface: Surface) -> None:
        """Render the tooltip above the stored position if visible."""
        if not self._visible or not self._text:
            return
        try:
            font_obj = font.SysFont("arial", self._font_size)
            text_surf = font_obj.render(self._text, True, (240, 235, 220))
            padding = 4
            bg_rect = text_surf.get_rect.inflate(padding * 2, padding * 2)
            bg_rect.topleft = (self._pos[0], self._pos[1] - bg_rect.height - 8)
            # Keep on screen
            bg_rect.clamp_ip(surface.get_rect())
            bg_surf = Surface(bg_rect.size, pygame.SRCALPHA)
            bg_surf.fill((30, 28, 25, 230))  # dark semi-transparent
            surface.blit(bg_surf, bg_rect.topleft)
            surface.blit(text_surf, (bg_rect.x + padding, bg_rect.y + padding))
        except (pygame.error, ValueError, OSError):
            pass  # Silently skip if font/render fails
