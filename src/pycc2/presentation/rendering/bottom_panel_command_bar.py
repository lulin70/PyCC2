"""Command bar and battle timer rendering for the CC2 bottom panel."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame
from pygame import Rect, Surface, draw

if TYPE_CHECKING:
    from pycc2.presentation.rendering.cc2_bottom_panel import CC2BottomPanel


class CommandBarRenderer:
    """Renders the vertical command button bar and optional battle timer."""

    def __init__(self, panel: CC2BottomPanel) -> None:
        self._panel = panel

    def render(
        self, surface: Surface, x: int, y: int, w: int, h: int, time_remaining: float | None = None
    ) -> None:
        """Render command buttons in vertical layout (right of unit details).

        Args:
            surface: Target surface
            x, y: Top-left position
            w, h: Width and height
            time_remaining: Optional battle timer in seconds for countdown display

        """
        # === TIMER DISPLAY (Top of command bar) ===
        timer_height = 0
        if time_remaining is not None and time_remaining > 0:
            timer_height = 28  # Space for timer display
            self._render_timer(surface, x, y, w, timer_height, time_remaining)

        # Adjust command button area to account for timer
        cmd_y = y + timer_height + (4 if timer_height > 0 else 0)
        cmd_h = h - timer_height - (4 if timer_height > 0 else 0)

        num_cmds = len(self._panel._commands)
        btn_height = (cmd_h - (num_cmds - 1) * 4) // num_cmds if num_cmds > 0 else 0
        btn_width = w - 10

        self._panel._button_rects = {}

        # Reset tooltip at start of each frame; buttons will re-trigger if hovered
        self._panel._tooltip.end_hover()

        # Check if we have a selected unit for enabling/disabling commands
        has_selection = self._panel._selected_unit_id is not None

        # Get selected unit to check smoke ammo
        selected_unit = None
        if has_selection:
            selected_unit = next(
                (u for u in self._panel._friendly_units if u.id == self._panel._selected_unit_id),
                None,
            )

        for i, cmd in enumerate(self._panel._commands):
            btn_y = cmd_y + i * (btn_height + 4)
            btn_rect = Rect(x + 5, btn_y, btn_width, btn_height)

            # Determine if this command should be enabled
            cmd_enabled = True

            # Cancel and End Battle are always enabled
            if cmd["id"] in ("cancel", "end_battle"):
                cmd_enabled = True
            # Other commands require selection
            elif not has_selection:
                cmd_enabled = False
            # Smoke requires smoke ammunition
            elif cmd.get("needs_smoke_ammo") and selected_unit:
                has_smoke = getattr(selected_unit, "has_smoke_grenades", False)
                if not has_smoke:
                    cmd_enabled = False

            self._panel._button_rects[cmd["id"]] = btn_rect

            is_hovered = cmd["id"] == self._panel._hovered_command
            is_pressed = is_hovered and self._panel._mouse_pressed

            # Button background color based on state
            if not cmd_enabled:
                bg_color = (35, 38, 43)  # Disabled: dark gray
                text_color = (100, 100, 100)  # Dimmed text
            elif cmd["id"] == "end_battle":
                # End Battle: olive green color scheme (CC2 style)
                if is_pressed:
                    bg_color = (50, 58, 38)  # Pressed: darker olive
                    text_color = (200, 200, 130)
                elif is_hovered:
                    bg_color = (90, 100, 70)  # Hovered: lighter olive
                    text_color = (255, 255, 150)
                else:
                    bg_color = (60, 68, 50)  # Normal: olive green
                    text_color = (220, 220, 180)
            elif is_pressed:
                bg_color = (40, 48, 62)  # Pressed: darkened ~20%
                text_color = (200, 210, 230)
            elif is_hovered:
                bg_color = (80, 90, 110)  # Hovered: lighter
                text_color = self._panel.HIGHLIGHT_COLOR
            else:
                bg_color = (50, 58, 70)  # Normal: military blue-gray
                text_color = self._panel.TEXT_COLOR

            draw.rect(surface, bg_color, btn_rect)

            # 3D raised border effect: top/left bright, bottom/right dark
            if cmd_enabled:
                if is_pressed:
                    # Pressed: inverted borders (sunken look)
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
                    # Top edge
                    draw.line(
                        surface,
                        self._panel.BORDER_LIGHT,
                        (btn_rect.left, btn_rect.top),
                        (btn_rect.right, btn_rect.top),
                        1,
                    )
                    # Left edge
                    draw.line(
                        surface,
                        self._panel.BORDER_LIGHT,
                        (btn_rect.left, btn_rect.top),
                        (btn_rect.left, btn_rect.bottom),
                        1,
                    )
                    # Bottom edge
                    draw.line(
                        surface,
                        self._panel.BORDER_DARK,
                        (btn_rect.left, btn_rect.bottom),
                        (btn_rect.right, btn_rect.bottom),
                        1,
                    )
                    # Right edge
                    draw.line(
                        surface,
                        self._panel.BORDER_DARK,
                        (btn_rect.right, btn_rect.top),
                        (btn_rect.right, btn_rect.bottom),
                        1,
                    )

                # Hover highlight: bright inner border glow when hovered (not pressed)
                if is_hovered and not is_pressed:
                    highlight_color = (140, 160, 200, 180)
                    highlight_rect = Rect(
                        btn_rect.x + 1, btn_rect.y + 1, btn_rect.width - 2, btn_rect.height - 2
                    )
                    hl_surf = Surface(
                        (highlight_rect.width, highlight_rect.height), pygame.SRCALPHA
                    )
                    draw.rect(hl_surf, highlight_color, hl_surf.get_rect(), 1)
                    surface.blit(hl_surf, highlight_rect.topleft)
            else:
                draw.rect(surface, (45, 48, 53), btn_rect, 1)

            # Command icon (24x24, drawn left of text)
            icon = self._panel._command_icons.get(cmd["id"])
            icon_x = btn_rect.left + 4
            icon_y = btn_y + (btn_height - 24) // 2
            if icon:
                if not cmd_enabled:
                    # Dim the icon for disabled state
                    dimmed = icon.copy()
                    dimmed.set_alpha(80)
                    surface.blit(dimmed, (icon_x, icon_y))
                else:
                    surface.blit(icon, (icon_x, icon_y))

            # Label with key binding (shifted right to make room for icon)
            label = f"{cmd['label']} [{cmd['key']}]"
            text_surf = self._panel._font_small.render(label, True, text_color)
            text_x = icon_x + 26
            text_y = btn_y + (btn_height - text_surf.get_height()) // 2
            surface.blit(text_surf, (text_x, text_y))

            # Trigger tooltip on hovered enabled button
            if is_hovered and cmd_enabled and self._panel._mouse_pos is not None:
                tip_text = self._panel._command_tooltips.get(cmd["id"], "")
                if tip_text:
                    self._panel._tooltip.begin_hover(tip_text, (btn_rect.centerx, btn_rect.top))

    def _render_timer(
        self, surface: Surface, x: int, y: int, w: int, h: int, time_remaining: float
    ) -> None:
        """Render battle countdown timer display.

        Args:
            surface: Target surface
            x, y: Top-left position of timer area
            w, h: Width and height of timer area
            time_remaining: Remaining time in seconds

        """
        # Timer background (slightly darker than panel)
        timer_rect = Rect(x + 2, y + 2, w - 4, h - 4)
        draw.rect(surface, (45, 50, 38), timer_rect)
        draw.rect(surface, self._panel.BORDER_COLOR, timer_rect, 1)

        # Format time as MM:SS
        total_seconds = int(time_remaining)
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        time_str = f"{minutes:02d}:{seconds:02d}"

        # Determine color based on remaining time
        if time_remaining < 30:
            timer_color = (255, 68, 68)  # Red (#FF4444) - critical
        elif time_remaining < 60:
            timer_color = (255, 255, 0)  # Yellow (#FFFF00) - warning
        else:
            timer_color = (255, 255, 255)  # White - normal

        # Render timer text (monospace bold, centered)
        try:
            timer_font = pygame.font.SysFont("consolas", 18, bold=True)
        except (pygame.error, OSError, ValueError) as e:
            import logging

            logging.debug("Timer font fallback: %s", e)
            timer_font = pygame.font.Font(None, 24)

        timer_text = timer_font.render(time_str, True, timer_color)
        text_x = x + (w - timer_text.get_width()) // 2
        text_y = y + (h - timer_text.get_height()) // 2
        surface.blit(timer_text, (text_x, text_y))
