"""
Unit Information Panel

Displays detailed information about selected units including stats,
equipment, status effects, etc.
"""

import pygame
from pygame import Rect, Surface
from pygame.font import Font

from pycc2.domain.entities.unit import Unit
from pycc2.domain.interfaces.display_config import DisplayConfig
from pycc2.presentation.rendering.visual_spec import VisualSpec

DEFAULT_PANEL_WIDTH = 250
DEFAULT_PANEL_HEIGHT = 220
DEFAULT_POS_X = 10  # Left side (will be adjusted dynamically)
DEFAULT_POS_Y = 80  # Below header
PADDING = 15
TITLE_LINE_HEIGHT = 35
LINE_HEIGHT = 18
BORDER_WIDTH = 2


class UnitPanel:
    """Detailed unit information panel."""

    def __init__(
        self,
        display_config: DisplayConfig | None = None,
        width: int | None = None,
        height: int | None = None,
    ):
        self._dc = display_config or DisplayConfig()
        self.width = width or int(DEFAULT_PANEL_WIDTH * self._dc.ui_scale)
        self.height = height or int(DEFAULT_PANEL_HEIGHT * self._dc.ui_scale)
        self.spec = VisualSpec()
        self._font_title: Font | None = None
        self._font_normal: Font | None = None
        self._selected_unit: Unit | None = None
        self._visible: bool = False
        self._position: tuple = (
            int(DEFAULT_POS_X * self._dc.ui_scale),
            int(DEFAULT_POS_Y * self._dc.ui_scale),
        )

    def initialize(self) -> None:
        """Initialize fonts."""
        pygame.font.init()
        self._font_title = pygame.font.Font(None, self._dc.font_size_large)
        self._font_normal = pygame.font.Font(None, self._dc.font_size_normal)

    def show(self) -> None:
        """Show the panel."""
        self._visible = True

    def hide(self) -> None:
        """Hide the panel."""
        self._visible = False

    def set_unit(self, unit: Unit | None) -> None:
        """Set the unit to display information for."""
        self._selected_unit = unit
        if unit:
            self.show()
        else:
            self.hide()

    def set_position(self, x: int, y: int) -> None:
        """Set panel position on screen."""
        self._position = (x, y)

    def render(self, surface: Surface) -> None:
        """Render the unit panel if visible - CC2-style: bottom of screen."""
        if not self._visible or not self._selected_unit:
            return
        if not self._font_title or not self._font_normal:
            return

        # CC2-style layout: panel at BOTTOM of screen (above command bar)
        screen_w, screen_h = surface.get_size()
        command_bar_height = 50  # Space for Move/Attack buttons
        panel_x = 10  # Left side
        panel_y = screen_h - self.height - command_bar_height - 10  # Above command bar
        self._position = (panel_x, panel_y)

        # Make panel smaller for CC2 compact look
        compact_width = min(self.width, 220)
        compact_height = min(self.height, 150)

        panel_rect = Rect(panel_x, panel_y, compact_width, compact_height)
        pygame.draw.rect(surface, self.spec.panel_background_color, panel_rect)
        pygame.draw.rect(surface, self.spec.panel_border_color, panel_rect, BORDER_WIDTH)

        unit = self._selected_unit
        pad = int(PADDING * self._dc.ui_scale)
        x_offset = self._position[0] + pad
        y_offset = self._position[1] + pad

        title_surface = self._font_title.render(
            f"Unit: {unit.name}", True, self.spec.hud_text_color
        )
        surface.blit(title_surface, (x_offset, y_offset))
        y_offset += max(28, int(TITLE_LINE_HEIGHT * self._dc.ui_scale))

        info_lines = [
            f"Type: {unit.unit_type.name}",
            f"Faction: {unit.faction.name}",
            "",
            f"Health: {unit.health.hp}/{unit.health.max_hp}",
            f"Morale: {unit.morale.value}%",
            "",
            f"Weapon: {unit.weapon.primary_weapon_id}",
            f"Ammo: {unit.weapon.ammo_remaining}/{unit.weapon.max_ammo}",
            "",
            f"Position: ({unit.position.tile_coord.x}, {unit.position.tile_coord.y})",
            f"Status: {'Combat Ready' if unit.is_alive else 'Eliminated'}",
        ]

        line_h = max(14, int(LINE_HEIGHT * self._dc.ui_scale))
        for line in info_lines:
            text_surface = self._font_normal.render(line, True, self.spec.hud_text_color)
            surface.blit(text_surface, (x_offset, y_offset))
            y_offset += line_h

    @property
    def is_visible(self) -> bool:
        """Check if panel is currently visible."""
        return self._visible

    def cleanup(self) -> None:
        """Clean up resources."""
        pass
