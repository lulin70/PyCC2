"""CC2 HUD input handling extracted from CC2HUD.

CC2HUDInputHandler processes mouse clicks, movement, and scroll events
for the three-panel HUD. It reads/writes state on a CC2HUD instance.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    pass


class CC2HUDInputHandler:
    """Handles all mouse input for the CC2 HUD."""

    def handle_click(self, hud, pos: tuple[int, int]) -> str | None:
        """Process mouse click and return action string or None.

        Args:
            hud: CC2HUD instance providing visibility, rects, callbacks, etc.
            pos: Screen coordinates (x, y)

        Returns:
            Action string like 'select_unit:xxx', 'command:xxx', or None
        """
        if not hud._visible:
            return None

        x, y = pos
        panel_y = hud._screen_height - hud.PANEL_HEIGHT

        # Convert to HUD-local coordinates
        local_y = y - panel_y
        if local_y < 0 or local_y > hud.PANEL_HEIGHT:
            return None

        # Check unit roster items
        for rect, unit_id in hud._unit_rects:
            if rect.collidepoint(x, local_y):
                if hud._on_unit_select:
                    hud._on_unit_select(unit_id)
                return f"select_unit:{unit_id}"

        # Check hide buttons
        for unit_id, rect in hud._hide_button_rects.items():
            if rect.collidepoint(x, local_y):
                if hud._on_hide_toggle:
                    hud._on_hide_toggle(unit_id)
                return f"hide_toggle:{unit_id}"

        # Check command buttons
        for cmd_id, rect in hud._command_button_rects.items():
            if rect.collidepoint(x, local_y):
                if hud._on_command:
                    hud._on_command(cmd_id)
                return f"command:{cmd_id}"

        # Check info mode buttons
        for mode, rect in hud._info_mode_rects.items():
            if rect.collidepoint(x, local_y):
                hud._info_mode = mode
                return f"info_mode:{mode}"

        return None

    def handle_mouse_move(self, hud, pos: tuple[int, int]) -> None:
        """Update hover states for visual feedback.

        Args:
            hud: CC2HUD instance
            pos: Current mouse position
        """
        x, y = pos
        panel_y = hud._screen_height - hud.PANEL_HEIGHT
        local_y = y - panel_y

        hud._hovered_command = None
        hud._hovered_unit = None

        if local_y < 0 or local_y > hud.PANEL_HEIGHT:
            return

        for cmd_id, rect in hud._command_button_rects.items():
            if rect.collidepoint(x, local_y):
                hud._hovered_command = cmd_id
                break

        for rect, unit_id in hud._unit_rects:
            if rect.collidepoint(x, local_y):
                hud._hovered_unit = unit_id
                break

    def handle_scroll(self, hud, direction: int) -> None:
        """Handle mouse wheel scrolling for the unit roster.

        Args:
            hud: CC2HUD instance
            direction: Scroll direction (+1 or -1)
        """
        max_offset = max(0, len(hud._units) - hud._max_visible_units)
        new_offset = hud._scroll_offset - direction
        hud._scroll_offset = max(0, min(new_offset, max_offset))
