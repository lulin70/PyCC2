"""Mouse input handling for the CC2 bottom panel."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pygame import Rect

if TYPE_CHECKING:
    from pycc2.presentation.rendering.cc2_bottom_panel import CC2BottomPanel


class BottomPanelInputHandler:
    """Translates mouse events into actions on the bottom panel."""

    def __init__(self, panel: CC2BottomPanel) -> None:
        """Initialize the BottomPanelInputHandler."""
        self._panel = panel

    def handle_click(self, screen_pos: tuple[int, int]) -> str | None:
        """Handle click on panel. Returns action or None."""
        if not self._panel._visible:
            return None

        x, y = screen_pos

        # Check roster items
        for rect, unit_id in self._panel._roster_item_rects:
            if rect.collidepoint(x, y):
                if self._panel._on_unit_select:
                    self._panel._on_unit_select(unit_id)
                return f"select_unit:{unit_id}"

        # Check command buttons
        for cmd_id, rect in self._panel._button_rects.items():
            if rect.collidepoint(x, y):
                # End Battle button: publish event to EventBus
                if cmd_id == "end_battle" and self._panel._event_bus is not None:
                    self._panel._event_bus.publish_named("EndBattle", {"event_type": "end_battle"})
                callback = self._panel._command_callbacks.get(cmd_id)
                if callback:
                    callback()
                return f"command:{cmd_id}"

        # Check zoom buttons
        if self._panel._zoom_in_rect and self._panel._zoom_in_rect.collidepoint(x, y):
            return f"zoom:{self._panel.zoom_in()}"
        if self._panel._zoom_out_rect and self._panel._zoom_out_rect.collidepoint(x, y):
            return f"zoom:{self._panel.zoom_out()}"

        # Check info toggle buttons
        for mode, rect in self._panel._info_button_rects.items():
            if rect.collidepoint(x, y):
                self._panel._info_mode = mode
                return f"info_mode:{mode}"

        # If click is outside any soldier member rect, dismiss popup
        if self._panel._active_popup_member is not None:
            self._panel._active_popup_member = None
            self._panel._active_popup_rect = None

        return None

    def handle_right_click(self, screen_pos: tuple[int, int]) -> str | None:
        """Handle right-click on panel. Shows soldier detail popup if clicked on a squad member.

        Returns action string or None.
        """
        if not self._panel._visible:
            return None

        x, y = screen_pos

        # Check soldier monitor member rects
        for rect, member in self._panel._soldier_member_rects:
            if rect.collidepoint(x, y):
                self._panel._active_popup_member = member
                self._panel._active_popup_rect = Rect(x, y, 1, 1)  # Position for popup
                return f"soldier_detail:{getattr(member, 'member_id', '?')}"

        # Click elsewhere dismisses popup
        if self._panel._active_popup_member is not None:
            self._panel._active_popup_member = None
            self._panel._active_popup_rect = None

        return None

    def handle_mouse_move(self, screen_pos: tuple[int, int]) -> None:
        """Handle mouse move for hover effects."""
        x, y = screen_pos
        self._panel._hovered_command = None

        for cmd_id, rect in self._panel._button_rects.items():
            if rect.collidepoint(x, y):
                self._panel._hovered_command = cmd_id
                break
