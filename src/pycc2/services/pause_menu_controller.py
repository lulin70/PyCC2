"""Pause menu controller managing the in-game pause overlay state and input."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import pygame

logger = logging.getLogger(__name__)


@dataclass
class PauseMenuController:
    """Manages the in-game pause menu overlay: rendering, input, and state."""

    _active: bool = field(init=False, default=False)
    _buttons: dict[str, pygame.Rect] = field(init=False, default_factory=dict)
    _mouse: tuple[int, int] = field(init=False, default=(0, 0))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_active(self) -> bool:
        """Return whether the pause menu is currently shown."""
        return self._active

    def toggle(self) -> None:
        """Toggle the pause menu on/off."""
        self._active = not self._active

    def deactivate(self) -> None:
        """Close the pause menu."""
        self._active = False

    def handle_click(self, pos: tuple[int, int]) -> str | None:
        """Handle a click on the pause menu. Returns action string or None."""
        for key, rect in self._buttons.items():
            if rect.collidepoint(pos):
                return key
        return None

    def update_mouse(self, pos: tuple[int, int]) -> None:
        """Track mouse position for hover highlighting."""
        self._mouse = pos

    def render(self, screen: pygame.Surface) -> None:
        """Render the pause menu overlay."""
        sw, sh = screen.get_size()

        # Semi-transparent overlay
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        # Menu panel
        panel_w, panel_h = 360, 320
        panel_x = (sw - panel_w) // 2
        panel_y = (sh - panel_h) // 2
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

        pygame.draw.rect(screen, (38, 42, 34), panel_rect, border_radius=10)
        pygame.draw.rect(screen, (80, 85, 60), panel_rect, width=2, border_radius=10)

        # Title
        font = pygame.font.Font(None, 42)
        title_surf = font.render("PAUSED", True, (218, 195, 130))
        screen.blit(title_surf, ((sw - title_surf.get_width()) // 2, panel_y + 20))

        # Buttons
        self._buttons = {}
        btn_w, btn_h = 260, 48
        btn_x = (sw - btn_w) // 2
        btn_start_y = panel_y + 80
        gap = 58

        menu_items = [
            ("resume", "Resume"),
            ("save", "Save Game"),
            ("load", "Load Game"),
            ("quit_to_menu", "Quit to Menu"),
        ]

        font_btn = pygame.font.Font(None, 30)
        for i, (key, label) in enumerate(menu_items):
            rect = pygame.Rect(btn_x, btn_start_y + i * gap, btn_w, btn_h)
            self._buttons[key] = rect

            hovered = rect.collidepoint(self._mouse)
            bg = (70, 78, 55) if hovered else (50, 55, 42)
            pygame.draw.rect(screen, bg, rect, border_radius=6)
            pygame.draw.rect(screen, (90, 95, 65), rect, width=2, border_radius=6)

            txt_surf = font_btn.render(label, True, (220, 220, 210))
            screen.blit(txt_surf, txt_surf.get_rect(center=rect.center))
