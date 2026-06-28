"""Command Bar

Bottom command bar showing available actions for selected units.
Provides quick access to common commands like move, attack, etc.
"""

from collections.abc import Callable

import pygame
from pygame import Rect, Surface, draw
from pygame.font import Font

from pycc2.domain.entities.unit import Unit
from pycc2.domain.interfaces.display_config import DisplayConfig
from pycc2.presentation.rendering.visual_spec import VisualSpec


class CommandBar:
    """Command bar with action buttons."""

    def __init__(self, display_config: DisplayConfig | None = None, height: int | None = None):
        """Initialize the CommandBar."""
        self._dc = display_config or DisplayConfig()
        self.height = height or int(60 * self._dc.ui_scale)
        self.spec = VisualSpec()
        self._font: Font | None = None
        self._commands: list[dict] = [
            {"id": "move", "label": "Move [M]", "key": "m"},
            {"id": "attack", "label": "Attack [A]", "key": "a"},
            {"id": "hold", "label": "Hold [H]", "key": "h"},
            {"id": "dig_in", "label": "Dig In [D]", "key": "d"},
            {"id": "cancel", "label": "Cancel [ESC]", "key": "escape"},
        ]
        self._command_callbacks: dict[str, Callable] = {}
        self._selected_unit: Unit | None = None
        self._hovered_command: str | None = None
        self._button_width: int = int(120 * self._dc.ui_scale)
        self._button_height: int = int(40 * self._dc.ui_scale)
        self._button_margin: int = int(10 * self._dc.ui_scale)

    def initialize(self) -> None:
        """Initialize fonts."""
        pygame.font.init()
        self._font = pygame.font.Font(None, self._dc.font_size_normal)

    def register_callback(self, command_id: str, callback: Callable) -> None:
        """Register a callback function for a command."""
        self._command_callbacks[command_id] = callback

    def set_selected_unit(self, unit: Unit | None) -> None:
        """Set currently selected unit to contextually enable commands."""
        self._selected_unit = unit

    def render(self, surface: Surface) -> None:
        """Render the command bar at bottom of screen."""
        if not self._font:
            return
        bar_y = surface.get_height() - self.height
        bar_rect = Rect(0, bar_y, surface.get_width(), self.height)
        draw.rect(surface, self.spec.command_bar_bg_color, bar_rect)
        draw.line(
            surface,
            self.spec.command_bar_border_color,
            (0, bar_y),
            (surface.get_width(), bar_y),
            2,
        )

        total_width = len(self._commands) * (self._button_width + self._button_margin)
        start_x = (surface.get_width() - total_width) // 2

        for i, cmd in enumerate(self._commands):
            btn_x = start_x + i * (self._button_width + self._button_margin)
            btn_y = bar_y + (self.height - self._button_height) // 2
            btn_rect = Rect(btn_x, btn_y, self._button_width, self._button_height)

            is_hovered = cmd["id"] == self._hovered_command
            is_enabled = self._is_command_enabled(cmd["id"])

            if is_hovered and is_enabled:
                bg_color = self.spec.button_hover_color
            elif not is_enabled:
                bg_color = self.spec.button_disabled_color
            else:
                bg_color = self.spec.button_normal_color

            draw.rect(surface, bg_color, btn_rect, border_radius=5)
            draw.rect(surface, self.spec.button_border_color, btn_rect, width=1, border_radius=5)

            text_color = (
                self.spec.button_text_color if is_enabled else self.spec.button_disabled_text_color
            )
            text_surface = self._font.render(cmd["label"], True, text_color)
            text_x = btn_x + (self._button_width - text_surface.get_width()) // 2
            text_y = btn_y + (self._button_height - text_surface.get_height()) // 2
            surface.blit(text_surface, (text_x, text_y))

    def handle_click(self, pos: tuple) -> str | None:
        """Handle mouse click on command bar. Returns command ID or None."""
        for cmd in self._commands:
            if self._is_command_in_bounds(pos, cmd["id"]) and self._is_command_enabled(cmd["id"]):
                callback = self._command_callbacks.get(cmd["id"])
                if callback:
                    callback()
                return cmd["id"]
        return None

    def handle_mouse_move(self, pos: tuple) -> None:
        """Handle mouse movement for hover effects."""
        self._hovered_command = None
        for cmd in self._commands:
            if self._is_command_in_bounds(pos, cmd["id"]):
                self._hovered_command = cmd["id"]
                break

    def _is_command_in_bounds(self, pos: tuple, command_id: str) -> bool:
        """Check if position is within button bounds."""
        sw = 1280
        sh = 720
        bar_y = sh - self.height
        total_width = len(self._commands) * (self._button_width + self._button_margin)
        start_x = (sw - total_width) // 2

        for i, cmd in enumerate(self._commands):
            if cmd["id"] == command_id:
                btn_x = start_x + i * (self._button_width + self._button_margin)
                btn_y = bar_y + (self.height - self._button_height) // 2
                btn_rect = Rect(btn_x, btn_y, self._button_width, self._button_height)
                return btn_rect.collidepoint(pos)
        return False

    def _is_command_enabled(self, command_id: str) -> bool:
        """Check if a command should be enabled based on context."""
        if not self._selected_unit:
            return False
        if not self._selected_unit.is_alive:  # Property, not method!
            return command_id in ["cancel"]
        return True

    def cleanup(self) -> None:
        """Clean up resources."""
        pass
