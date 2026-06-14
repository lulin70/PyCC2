"""
Button UI Component

Reusable button with multiple states and callback support.
"""

from collections.abc import Callable

import pygame
from pygame import Rect, Surface, draw
from pygame.font import Font


class ButtonState:
    """Button visual states."""

    NORMAL = "normal"
    HOVER = "hover"
    PRESSED = "pressed"
    DISABLED = "disabled"


class Button:
    """Interactive button component."""

    def __init__(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        text: str = "",
        callback: Callable | None = None,
    ):
        self.rect = Rect(x, y, width, height)
        self.text = text
        self.callback = callback
        self._state = ButtonState.NORMAL
        self._enabled: bool = True
        self._visible: bool = True
        self._font: Font | None = None
        self._hover_time: float = 0.0

        self.colors = {
            ButtonState.NORMAL: (70, 74, 82),
            ButtonState.HOVER: (90, 94, 102),
            ButtonState.PRESSED: (50, 54, 62),
            ButtonState.DISABLED: (45, 48, 55),
        }
        self.text_colors = {
            ButtonState.NORMAL: (220, 220, 220),
            ButtonState.HOVER: (255, 255, 255),
            ButtonState.PRESSED: (200, 200, 200),
            ButtonState.DISABLED: (120, 120, 120),
        }
        self.border_color = (100, 104, 112)

    def initialize(self) -> None:
        """Initialize button resources."""
        if self._font is None:
            pygame.font.init()
            self._font = pygame.font.Font(None, 24)

    @property
    def state(self) -> str:
        """Get current button state."""
        return self._state

    @property
    def is_enabled(self) -> bool:
        """Check if button is enabled."""
        return self._enabled

    @property
    def is_visible(self) -> bool:
        """Check if button is visible."""
        return self._visible

    def enable(self) -> None:
        """Enable the button."""
        self._enabled = True
        if self._state == ButtonState.DISABLED:
            self._state = ButtonState.NORMAL

    def disable(self) -> None:
        """Disable the button."""
        self._enabled = False
        self._state = ButtonState.DISABLED

    def show(self) -> None:
        """Show the button."""
        self._visible = True

    def hide(self) -> None:
        """Hide the button."""
        self._visible = False

    def set_text(self, text: str) -> None:
        """Update button text."""
        self.text = text

    def set_callback(self, callback: Callable) -> None:
        """Set button click callback."""
        self.callback = callback

    def update(self, mouse_pos: tuple, mouse_pressed: bool) -> bool:
        """
        Update button state based on mouse input.

        Returns:
            True if button was clicked this frame
        """
        if not self._enabled or not self._visible:
            return False

        was_hovered = self.rect.collidepoint(mouse_pos)
        is_clicked = False

        if was_hovered:
            if mouse_pressed:
                self._state = ButtonState.PRESSED
            else:
                if self._state == ButtonState.PRESSED:
                    is_clicked = True
                    if self.callback:
                        self.callback()
                self._state = ButtonState.HOVER
        else:
            self._state = ButtonState.NORMAL

        return is_clicked

    def render(self, surface: Surface) -> None:
        """Render the button to surface."""
        if not self._visible:
            return

        bg_color = self.colors.get(self._state, self.colors[ButtonState.NORMAL])
        text_color = self.text_colors.get(self._state, self.text_colors[ButtonState.NORMAL])

        draw.rect(surface, bg_color, self.rect, border_radius=6)
        draw.rect(surface, self.border_color, self.rect, width=1, border_radius=6)

        if self.text and self._font:
            text_surface = self._font.render(self.text, True, text_color)
            text_rect = text_surface.get_rect(center=self.rect.center)
            surface.blit(text_surface, text_rect)

    def contains_point(self, pos: tuple) -> bool:
        """Check if point is within button bounds."""
        return self.rect.collidepoint(pos)

    def cleanup(self) -> None:
        """Clean up resources."""
        pass
