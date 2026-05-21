"""
Panel UI Component

Container panel for grouping related UI elements.
"""

import pygame
from pygame import Rect, Surface, draw
from pygame.font import Font


class Panel:
    """Container panel for UI elements."""

    def __init__(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        title: str = "",
    ):
        self.rect = Rect(x, y, width, height)
        self.title = title
        self._children: list = []
        self._visible: bool = True
        self._font_title: Font | None = None
        self._font_normal: Font | None = None

        self.background_color = (40, 44, 52, 230)
        self.border_color = (80, 84, 92)
        self.title_color = (240, 240, 240)
        self.border_width = 2
        self.border_radius = 8
        self.padding = 10

    def initialize(self) -> None:
        """Initialize panel resources."""
        pygame.font.init()
        self._font_title = pygame.font.Font(None, 28)
        self._font_normal = pygame.font.Font(None, 20)

    def add_child(self, child) -> None:
        """Add a child UI element to the panel."""
        self._children.append(child)

    def remove_child(self, child) -> None:
        """Remove a child UI element from the panel."""
        if child in self._children:
            self._children.remove(child)

    def clear_children(self) -> None:
        """Remove all children from panel."""
        self._children.clear()

    @property
    def is_visible(self) -> bool:
        """Check if panel is visible."""
        return self._visible

    def show(self) -> None:
        """Show the panel."""
        self._visible = True

    def hide(self) -> None:
        """Hide the panel."""
        self._visible = False

    def toggle(self) -> None:
        """Toggle panel visibility."""
        self._visible = not self._visible

    def set_position(self, x: int, y: int) -> None:
        """Move panel to new position."""
        self.rect.x = x
        self.rect.y = y

    def resize(self, width: int, height: int) -> None:
        """Resize panel."""
        self.rect.width = width
        self.rect.height = height

    def render(self, surface: Surface) -> None:
        """Render panel and all children."""
        if not self._visible:
            return

        panel_surface = Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        draw.rect(
            panel_surface,
            self.background_color,
            (0, 0, self.rect.width, self.rect.height),
            border_radius=self.border_radius,
        )
        draw.rect(
            panel_surface,
            self.border_color,
            (0, 0, self.rect.width, self.rect.height),
            width=self.border_width,
            border_radius=self.border_radius,
        )

        if self.title and self._font_title:
            title_surface = self._font_title.render(self.title, True, self.title_color)
            title_x = (self.rect.width - title_surface.get_width()) // 2
            panel_surface.blit(title_surface, (title_x, 8))

        for child in self._children:
            if hasattr(child, "render"):
                child.render(panel_surface)

        surface.blit(panel_surface, self.rect.topleft)

    def handle_event(self, event) -> bool:
        """Pass events to children. Returns True if event was handled."""
        if not self._visible:
            return False
        for child in self._children:
            if hasattr(child, "handle_event") and child.handle_event(event):
                return True
        return False

    def cleanup(self) -> None:
        """Clean up panel and all children resources."""
        for child in self._children:
            if hasattr(child, "cleanup"):
                child.cleanup()
        self._children.clear()
