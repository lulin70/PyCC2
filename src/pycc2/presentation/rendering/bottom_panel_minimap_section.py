"""Minimap section rendering for the CC2 bottom panel."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame
from pygame import Rect, Surface, draw

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.presentation.rendering.cc2_bottom_panel import CC2BottomPanel
    from pycc2.presentation.rendering.minimap import Minimap


class MinimapSectionRenderer:
    """Renders the minimap, info-toggle buttons, and zoom controls."""

    def __init__(self, panel: CC2BottomPanel) -> None:
        self._panel = panel

    def render(
        self,
        surface: Surface,
        x: int,
        y: int,
        size: int,
        minimap: Minimap | None,
        camera: Camera,
        game_map: GameMap,
    ) -> None:
        """Render minimap with zoom controls and info toggle buttons."""
        # Info toggle buttons (above minimap)
        self._render_info_toggle_buttons(surface, x, y, size)

        # Adjust minimap position to account for info buttons (22px height for buttons)
        minimap_y = y + 24
        minimap_size = size - 24

        # Background for minimap area
        draw.rect(surface, (30, 33, 38), Rect(x, minimap_y, size, minimap_size))
        draw.rect(surface, self._panel.BORDER_COLOR, Rect(x, minimap_y, size, minimap_size), 1)

        # Minimap title label
        title = self._panel._font_small.render("MAP", True, (150, 150, 150))
        surface.blit(title, (x + 4, minimap_y + 2))

        # Render minimap if available
        if minimap:
            minimap.render(surface, x + 2, minimap_y + 2)

        # Zoom controls (+/- buttons)
        btn_size = 20
        btn_y = minimap_y + minimap_size - btn_size - 2

        # Helper to check if a rect is hovered/pressed
        mp = self._panel._mouse_pos

        # Zoom out (-)
        self._panel._zoom_out_rect = Rect(x + 2, btn_y, btn_size, btn_size)
        zo_hovered = mp is not None and self._panel._zoom_out_rect.collidepoint(mp)
        zo_pressed = zo_hovered and self._panel._mouse_pressed
        zo_bg = (45, 45, 55) if zo_pressed else ((80, 85, 100) if zo_hovered else (60, 60, 70))
        draw.rect(surface, zo_bg, self._panel._zoom_out_rect)
        draw.rect(
            surface,
            (140, 150, 170) if zo_hovered else self._panel.BORDER_COLOR,
            self._panel._zoom_out_rect,
            1,
        )
        minus = self._panel._font_normal.render("-", True, self._panel.TEXT_COLOR)
        surface.blit(minus, (x + 7, btn_y + 2))
        if zo_hovered:
            self._panel._tooltip.begin_hover(
                "Zoom out [-]", (self._panel._zoom_out_rect.centerx, self._panel._zoom_out_rect.top)
            )

        # Zoom in (+)
        self._panel._zoom_in_rect = Rect(x + size - btn_size - 2, btn_y, btn_size, btn_size)
        zi_hovered = mp is not None and self._panel._zoom_in_rect.collidepoint(mp)
        zi_pressed = zi_hovered and self._panel._mouse_pressed
        zi_bg = (45, 45, 55) if zi_pressed else ((80, 85, 100) if zi_hovered else (60, 60, 70))
        draw.rect(surface, zi_bg, self._panel._zoom_in_rect)
        draw.rect(
            surface,
            (140, 150, 170) if zi_hovered else self._panel.BORDER_COLOR,
            self._panel._zoom_in_rect,
            1,
        )
        plus = self._panel._font_normal.render("+", True, self._panel.TEXT_COLOR)
        surface.blit(plus, (x + size - btn_size + 5, btn_y + 2))
        if zi_hovered:
            self._panel._tooltip.begin_hover(
                "Zoom in [+]", (self._panel._zoom_in_rect.centerx, self._panel._zoom_in_rect.top)
            )

        # Zoom level indicator
        zoom_lvl = self._panel._current_zoom_index + 1
        zoom_text = self._panel._font_small.render(f"{zoom_lvl}/5", True, (150, 150, 150))
        surface.blit(zoom_text, (x + size // 2 - 10, btn_y + 4))

    def _render_info_toggle_buttons(self, surface: Surface, x: int, y: int, width: int) -> None:
        """Render info mode toggle buttons (ALL/Style/Outline) above minimap.

        Args:
            surface: Target surface
            x, y: Top-left position for button row
            width: Total width available for buttons

        """
        # Button configuration
        modes = ["ALL", "STYLE", "OUTLINE"]
        btn_width = 35
        btn_height = 20
        spacing = 3

        # Calculate total width and center the buttons
        total_width = len(modes) * btn_width + (len(modes) - 1) * spacing
        start_x = x + (width - total_width) // 2

        self._panel._info_button_rects = {}

        for i, mode in enumerate(modes):
            btn_x = start_x + i * (btn_width + spacing)
            btn_rect = Rect(btn_x, y + 2, btn_width, btn_height)

            # Store rect for click detection
            self._panel._info_button_rects[mode] = btn_rect

            is_active = mode == self._panel._info_mode

            # Check hover/press state
            mp = self._panel._mouse_pos
            btn_hovered = mp is not None and btn_rect.collidepoint(mp)
            btn_pressed = btn_hovered and self._panel._mouse_pressed

            # Button background color based on state
            if is_active:
                bg_color = (55, 65, 48) if btn_pressed else (70, 80, 60)  # Active
                text_color = self._panel.HIGHLIGHT_COLOR
            elif btn_pressed:
                bg_color = (35, 40, 32)  # Inactive + pressed
                text_color = (140, 140, 130)
            elif btn_hovered:
                bg_color = (58, 65, 50)  # Inactive + hovered
                text_color = (190, 190, 170)
            else:
                bg_color = (45, 50, 40)  # Inactive normal
                text_color = (160, 160, 150)  # Dimmed text

            draw.rect(surface, bg_color, btn_rect)

            # 3D border effect based on state
            if is_active or btn_pressed:
                # Active/pressed button: sunken look (inverted borders)
                draw.line(
                    surface,
                    self._panel.BORDER_DARK,
                    (btn_rect.left, btn_rect.top),
                    (btn_rect.right, btn_rect.top),
                    1,
                )
                draw.line(
                    surface,
                    self._panel.BORDER_DARK,
                    (btn_rect.left, btn_rect.top),
                    (btn_rect.left, btn_rect.bottom),
                    1,
                )
                draw.line(
                    surface,
                    self._panel.BORDER_LIGHT,
                    (btn_rect.left, btn_rect.bottom),
                    (btn_rect.right, btn_rect.bottom),
                    1,
                )
                draw.line(
                    surface,
                    self._panel.BORDER_LIGHT,
                    (btn_rect.right, btn_rect.top),
                    (btn_rect.right, btn_rect.bottom),
                    1,
                )
            else:
                # Inactive button: raised look
                border_c = (130, 140, 120) if btn_hovered else self._panel.BORDER_LIGHT
                draw.line(
                    surface,
                    border_c,
                    (btn_rect.left, btn_rect.top),
                    (btn_rect.right, btn_rect.top),
                    1,
                )
                draw.line(
                    surface,
                    border_c,
                    (btn_rect.left, btn_rect.top),
                    (btn_rect.left, btn_rect.bottom),
                    1,
                )
                draw.line(
                    surface,
                    self._panel.BORDER_DARK,
                    (btn_rect.left, btn_rect.bottom),
                    (btn_rect.right, btn_rect.bottom),
                    1,
                )
                draw.line(
                    surface,
                    self._panel.BORDER_DARK,
                    (btn_rect.right, btn_rect.top),
                    (btn_rect.right, btn_rect.bottom),
                    1,
                )

            # Hover highlight border for inactive hovered buttons
            if btn_hovered and not is_active and not btn_pressed:
                hl_rect = Rect(
                    btn_rect.x + 1, btn_rect.y + 1, btn_rect.width - 2, btn_rect.height - 2
                )
                hl_surf = Surface((hl_rect.width, hl_rect.height), pygame.SRCALPHA)
                draw.rect(hl_surf, (120, 150, 100, 150), hl_surf.get_rect(), 1)
                surface.blit(hl_surf, hl_rect.topleft)

            # Button label (small font)
            label = self._panel._font_small.render(mode, True, text_color)
            label_x = btn_x + (btn_width - label.get_width()) // 2
            label_y = y + 2 + (btn_height - label.get_height()) // 2
            surface.blit(label, (label_x, label_y))

            # Tooltip for info toggle buttons
            if btn_hovered:
                tip_map = {
                    "ALL": "Show all unit information",
                    "STYLE": "Show visual style info only",
                    "OUTLINE": "Show outline info only",
                }
                self._panel._tooltip.begin_hover(
                    tip_map.get(mode, f"Switch to {mode} mode"), (btn_rect.centerx, btn_rect.top)
                )
