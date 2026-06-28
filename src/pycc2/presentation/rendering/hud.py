"""HUD Manager

Heads-Up Display overlay system for game information display.
Shows unit info, commands, game state, etc.
"""

import pygame
from pygame import Rect, Surface
from pygame.font import Font

from pycc2.domain.entities.unit import Unit
from pycc2.domain.interfaces.display_config import DisplayConfig
from pycc2.presentation.rendering.fade_transition import FadeTransition
from pycc2.presentation.rendering.minimap import Minimap
from pycc2.presentation.rendering.visual_spec import VisualSpec
from pycc2.presentation.ui.theme import ThemeManager


class HUDManager:
    """Manages all HUD overlay elements."""

    def __init__(self, display_config: DisplayConfig | None = None):
        """Initialize the HUDManager."""
        self._dc = display_config or DisplayConfig()
        self.spec = VisualSpec()
        self._font_large: Font | None = None
        self._font_small: Font | None = None
        self._selected_units: list[Unit] = []
        self._show_fps: bool = True
        self._fps: float = 0.0
        self._game_time: str = "00:00"
        self._turn_number: int = 1
        self._minimap = Minimap(display_config)

        # Fade transition for unit info panel (appears/disappears on selection)
        self._unit_panel_fade = FadeTransition(fade_duration=0.18)

        # Surface cache – lazy init
        self._panel_surface_cache: Surface | None = None
        self._panel_surface_cache_size: tuple[int, int] | None = None

    def initialize(self) -> None:
        """Initialize fonts and resources."""
        pygame.font.init()
        self._font_large = pygame.font.Font(None, self._dc.font_size_large)
        self._font_small = pygame.font.Font(None, self._dc.font_size_normal)

        # Apply ThemeManager colors to VisualSpec for runtime theme switching
        theme = ThemeManager.get_current()
        self.spec.hud_background_color = (*theme.colors.background, 200)
        self.spec.hud_border_color = theme.colors.border
        self.spec.hud_text_color = theme.colors.text_primary
        self.spec.panel_background_color = (*theme.colors.surface, 220)
        self.spec.panel_border_color = theme.colors.border

    def set_selected_units(self, units: list[Unit]) -> None:
        """Set currently selected units for info display."""
        self._selected_units = units
        # Trigger fade-in when units are selected, fade-out when cleared
        if units:
            self._unit_panel_fade.show()
        else:
            self._unit_panel_fade.hide()

    def update(self, dt: float) -> None:
        """Update all HUD fade transitions.

        Args:
            dt: Delta time in seconds since last frame.

        """
        self._unit_panel_fade.update(dt)
        # Also propagate update to minimap's own fade
        self._minimap.update(dt)

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
        # Skip rendering if fully faded out
        if not self._unit_panel_fade.is_visible and self._unit_panel_fade.alpha <= 0.01:
            return

        panel_width = int(200 * self._dc.ui_scale)
        panel_height = int(120 * self._dc.ui_scale)
        panel_x = int(10 * self._dc.ui_scale)
        panel_y = surface.get_height() - panel_height - int(10 * self._dc.ui_scale)
        panel_rect = Rect(panel_x, panel_y, panel_width, panel_height)

        # Apply fade transition: render to temp surface with alpha
        alpha = self._unit_panel_fade.alpha
        if alpha < 1.0:
            import pygame

            panel_size = (panel_width, panel_height)
            if self._panel_surface_cache is None or self._panel_surface_cache_size != panel_size:
                self._panel_surface_cache = pygame.Surface(panel_size, pygame.SRCALPHA)
                self._panel_surface_cache_size = panel_size
            panel_surface = self._panel_surface_cache
            panel_surface.fill((0, 0, 0, 0))
            target = panel_surface
            target_offset = (0, 0)
        else:
            target = surface
            target_offset = (panel_x, panel_y)

        draw_rect = Rect(0, 0, panel_width, panel_height) if alpha < 1.0 else panel_rect
        pygame.draw.rect(target, self.spec.panel_background_color, draw_rect)
        pygame.draw.rect(target, self.spec.panel_border_color, draw_rect, 1)

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
            target.blit(text_surface, (target_offset[0] + pad, target_offset[1] + pad + i * line_h))

        # Blit faded panel surface onto main surface with alpha
        if alpha < 1.0:
            panel_surface.set_alpha(int(alpha * 255))
            surface.blit(panel_surface, (panel_x, panel_y))

    def _render_minimap_placeholder(self, surface: Surface) -> None:
        """Render minimap using real Minimap component."""
        minimap_size = int(150 * self._dc.ui_scale)
        minimap_x = surface.get_width() - minimap_size - int(10 * self._dc.ui_scale)
        minimap_y = surface.get_height() - minimap_size - int(40 * self._dc.ui_scale)
        self._minimap.render(surface, minimap_x, minimap_y)

    @property
    def minimap(self) -> Minimap:
        """Expose minimap for external configuration (set_map, update_units, etc.)."""
        return self._minimap

    def shutdown(self) -> None:
        """Clean up resources."""
        pass
