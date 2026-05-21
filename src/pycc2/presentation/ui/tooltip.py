"""
Tooltip Component

Context-sensitive help/information popup that appears on hover.
"""

import time

import pygame
from pygame import Rect, Surface, draw, mouse
from pygame.font import Font


class Tooltip:
    """Hover tooltip component."""

    def __init__(self, delay: float = 0.5, max_width: int = 250):
        self.delay = delay
        self.max_width = max_width
        self._text: str = ""
        self._target_rect: Rect | None = None
        self._hover_start: float = 0.0
        self._visible: bool = False
        self._font: Font | None = None

        self.background_color = (30, 33, 40, 245)
        self.border_color = (100, 104, 112)
        self.text_color = (220, 220, 220)
        self.padding = 8
        self.border_radius = 4

    def initialize(self) -> None:
        """Initialize tooltip resources."""
        pygame.font.init()
        self._font = pygame.font.Font(None, 18)

    def show(self, text: str, target_rect: Rect) -> None:
        """Show tooltip with text at target position."""
        self._text = text
        self._target_rect = target_rect
        self._hover_start = time.time()
        self._visible = False

    def hide(self) -> None:
        """Hide tooltip immediately."""
        self._text = ""
        self._target_rect = None
        self._visible = False

    def update(self, mouse_pos: tuple) -> None:
        """Update tooltip visibility based on hover duration."""
        if self._target_rect and self._target_rect.collidepoint(mouse_pos):
            elapsed = time.time() - self._hover_start
            if elapsed >= self.delay:
                self._visible = True
        else:
            self.hide()

    def render(self, surface: Surface) -> None:
        """Render tooltip if visible."""
        if not self._visible or not self._text or not self._font:
            return

        lines = self._wrap_text(self._text)
        line_surfaces = [self._font.render(line, True, self.text_color) for line in lines]

        max_line_width = max(s.get_width() for s in line_surfaces) if line_surfaces else 0
        total_height = sum(s.get_height() for s in line_surfaces) + self.padding * 2

        tooltip_width = min(max_line_width + self.padding * 2, self.max_width)
        tooltip_height = total_height

        mouse_pos = mouse.get_pos()
        x = mouse_pos[0] + 15
        y = mouse_pos[1] + 15

        if x + tooltip_width > surface.get_width():
            x = mouse_pos[0] - tooltip_width - 15
        if y + tooltip_height > surface.get_height():
            y = mouse_pos[1] - tooltip_height - 15

        tooltip_surface = Surface((tooltip_width, tooltip_height), pygame.SRCALPHA)
        draw.rect(
            tooltip_surface,
            self.background_color,
            (0, 0, tooltip_width, tooltip_height),
            border_radius=self.border_radius,
        )
        draw.rect(
            tooltip_surface,
            self.border_color,
            (0, 0, tooltip_width, tooltip_height),
            width=1,
            border_radius=self.border_radius,
        )

        current_y = self.padding
        for line_surf in line_surfaces:
            tooltip_surface.blit(line_surf, (self.padding, current_y))
            current_y += line_surf.get_height()

        surface.blit(tooltip_surface, (x, y))

    def _wrap_text(self, text: str) -> list:
        """Wrap text to fit within max_width."""
        if not self._font:
            return [text]
        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            test_line = f"{current_line} {word}".strip()
            test_surface = self._font.render(test_line, True, self.text_color)

            if test_surface.get_width() <= self.max_width - self.padding * 2:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        return lines if lines else [text]

    @property
    def is_visible(self) -> bool:
        """Check if tooltip is currently visible."""
        return self._visible

    def cleanup(self) -> None:
        """Clean up resources."""
        self.hide()
