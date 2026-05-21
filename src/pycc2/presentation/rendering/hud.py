"""
HUD Manager

Heads-Up Display overlay system for game information display.
Shows unit info, commands, game state, etc.
"""

import pygame
from pygame import Rect, Surface
from pygame.font import Font

from pycc2.domain.entities.unit import Unit
from pycc2.presentation.rendering.display_config import DisplayConfig
from pycc2.presentation.rendering.visual_spec import VisualSpec


class HUDManager:
    """Manages all HUD overlay elements."""

    def __init__(self, display_config: DisplayConfig | None = None):
        self._dc = display_config or DisplayConfig()
        self.spec = VisualSpec()
        self._font_large: Font | None = None
        self._font_small: Font | None = None
        self._selected_units: list[Unit] = []
        self._show_fps: bool = True
        self._fps: float = 0.0
        self._game_time: str = "00:00"
        self._turn_number: int = 1

    def initialize(self) -> None:
        """Initialize fonts and resources."""
        pygame.font.init()
        self._font_large = pygame.font.Font(None, self._dc.font_size_large)
        self._font_small = pygame.font.Font(None, self._dc.font_size_normal)

    def set_selected_units(self, units: list[Unit]) -> None:
        """Set currently selected units for info display."""
        self._selected_units = units

    def update_fps(self, fps: float) -> None:
        """Update FPS counter value."""
        self._fps = fps

    def update_game_time(self, time_str: str) -> None:
        """Update displayed game time."""
        self._game_time = time_str

    def update_turn(self, turn_num: int) -> None:
        """Update turn number display."""
        self._turn_number = turn_num

    def render(self, surface: Surface) -> None:
        """Render all HUD elements to surface."""
        self._render_top_bar(surface)
        self._render_unit_panel(surface)
        self._render_minimap_placeholder(surface)

    def _render_top_bar(self, surface: Surface) -> None:
        """Render top information bar."""
        if not self._font_small:
            return
        bar_height = int(30 * self._dc.ui_scale)
        bar_rect = Rect(0, 0, surface.get_width(), bar_height)
        pygame.draw.rect(surface, self.spec.hud_background_color, bar_rect)
        pygame.draw.rect(surface, self.spec.hud_border_color, bar_rect, 1)

        pad = int(12 * self._dc.ui_scale)
        y_pad = int(6 * self._dc.ui_scale)
        fps_text = f"FPS: {self._fps:.1f}" if self._show_fps else ""
        turn_text = f"Turn: {self._turn_number}"
        time_text = f"Time: {self._game_time}"

        fps_surface = self._font_small.render(fps_text, True, self.spec.hud_text_color)
        turn_surface = self._font_small.render(turn_text, True, self.spec.hud_text_color)
        time_surface = self._font_small.render(time_text, True, self.spec.hud_text_color)

        surface.blit(fps_surface, (pad, y_pad))
        surface.blit(turn_surface, (surface.get_width() // 2 - 30, y_pad))
        surface.blit(time_surface, (surface.get_width() - int(90 * self._dc.ui_scale), y_pad))

    def _render_unit_panel(self, surface: Surface) -> None:
        """Render selected unit information panel."""
        if not self._selected_units or not self._font_small:
            return
        panel_width = int(200 * self._dc.ui_scale)
        panel_height = int(120 * self._dc.ui_scale)
        panel_x = int(10 * self._dc.ui_scale)
        panel_y = surface.get_height() - panel_height - int(10 * self._dc.ui_scale)
        panel_rect = Rect(panel_x, panel_y, panel_width, panel_height)
        pygame.draw.rect(surface, self.spec.panel_background_color, panel_rect)
        pygame.draw.rect(surface, self.spec.panel_border_color, panel_rect, 1)

        unit = self._selected_units[0]
        lines = [
            f"Unit: {unit.name}",
            f"HP: {unit.health.hp}/{unit.health.max_hp}",
            f"Morale: {unit.morale.value}%",
            f"Pos: ({unit.position.tile_coord.x}, {unit.position.tile_coord.y})",
        ]

        line_h = max(16, int(22 * self._dc.ui_scale))
        pad = int(10 * self._dc.ui_scale)
        for i, line in enumerate(lines):
            text_surface = self._font_small.render(line, True, self.spec.hud_text_color)
            surface.blit(text_surface, (panel_x + pad, panel_y + pad + i * line_h))

    def _render_minimap_placeholder(self, surface: Surface) -> None:
        """Render minimap placeholder area."""
        minimap_size = int(150 * self._dc.ui_scale)
        minimap_x = surface.get_width() - minimap_size - int(10 * self._dc.ui_scale)
        minimap_y = surface.get_height() - minimap_size - int(40 * self._dc.ui_scale)
        minimap_rect = Rect(minimap_x, minimap_y, minimap_size, minimap_size)
        pygame.draw.rect(surface, self.spec.minimap_background_color, minimap_rect)
        pygame.draw.rect(surface, self.spec.minimap_border_color, minimap_rect, 1)

        if self._font_small:
            label = self._font_small.render("MINIMAP", True, self.spec.hud_text_color)
            surface.blit(
                label, (minimap_x + minimap_size // 2 - 30, minimap_y + minimap_size // 2 - 7)
            )

    def shutdown(self) -> None:
        """Clean up resources."""
        pass
