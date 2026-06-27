"""Deployment Input Router — Click handling and input routing for deployment phase.

Extracted from deployment_ui.py God Class (SRP refactoring).
Handles mouse click routing: roster selection, button hits, map placement,
and detail-panel button interactions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.presentation.ui.deployment_ui import DeploymentUI

# Import models and constants
from pycc2.presentation.ui.deployment_models import DeploymentPhase


class DeploymentInputRouter:
    """Routes mouse clicks during the deployment phase.

    Extracted from DeploymentUI God Class to follow SRP.
    Accesses parent UI state via ``self._ui``.
    """

    def __init__(self, ui: DeploymentUI) -> None:
        """Store reference to parent UI for state access."""
        self._ui = ui

    def handle_click(self, x: int, y: int) -> str | None:
        """Handle a mouse click at screen coordinates (x, y).

        Returns an action string or None:
          - ``"select_unit:<index>"`` – roster unit selected
          - ``"place_unit:<index>"`` – unit placed on map
          - ``"remove_unit:<x>,<y>"`` – placed unit removed
          - ``"begin_battle"`` – player confirmed deployment
          - ``None`` – click did nothing
        """
        ui = self._ui
        if ui._state.phase not in (DeploymentPhase.DEPLOYING, DeploymentPhase.READY):
            return None

        # Check Begin Battle button first
        if ui._button_rect and self._is_in_button(x, y):
            if ui.is_deployment_complete():
                return "begin_battle"
            return None

        # Check roster panel click (LEFT side)
        if x < ui._roster_width:
            idx = self._roster_index_at(x, y)
            if idx is not None and 0 <= idx < len(ui._state.available_units):
                unit = ui._state.available_units[idx]
                if not unit.is_placed:
                    ui._selected_unit_index = idx
                    return f"select_unit:{idx}"
            return None

        # Map click – either place or remove
        return None

    def handle_click_full(
        self,
        screen_x: int,
        screen_y: int,
        map_offset_x: int = 0,
        map_offset_y: int = 0,
        tile_size: int = 16,
        right_click: bool = False,
    ) -> str | None:
        """Full click handler that converts screen coords to map coords automatically.

        This is the preferred entry point for integration with the game loop.
        Supports both left-click (place/select) and right-click (remove).
        """
        ui = self._ui
        if ui._state.phase not in (DeploymentPhase.DEPLOYING, DeploymentPhase.READY):
            return None

        # Handle right-click for removal
        if right_click:
            return ui.handle_right_click(screen_x, screen_y, map_offset_x, map_offset_y, tile_size)

        # Check Start Battle button
        if ui._button_rect and self._is_in_button(screen_x, screen_y):
            if ui.is_deployment_complete():
                return "begin_battle"
            return None

        # Check detail panel button (PLACE ON MAP / REMOVE FROM MAP)
        if hasattr(ui, "_detail_panel_btn_rect") and ui._detail_panel_btn_rect:
            btn_x, btn_y, btn_w, btn_h = ui._detail_panel_btn_rect
            if btn_x <= screen_x <= btn_x + btn_w and btn_y <= screen_y <= btn_y + btn_h:
                # Button was clicked!
                action = getattr(ui, "_detail_panel_btn_action", None)
                if action == "remove" and ui._selected_unit_index is not None:
                    # Execute remove
                    unit = ui._state.available_units[ui._selected_unit_index]
                    if unit.is_placed and unit.position is not None:
                        pos_x, pos_y = unit.position[0], unit.position[1]
                        ui.remove_unit(pos_x, pos_y)
                        return f"detail_panel_remove:{pos_x},{pos_y}"
                elif action == "place" and ui._selected_unit_index is not None:
                    # For place, just return - the user should drag to map
                    return "detail_panel_place_requested"

        # Check roster panel (LEFT side)
        if screen_x < ui._roster_width:
            idx = self._roster_index_at(screen_x, screen_y)
            if idx is not None and 0 <= idx < len(ui._state.available_units):
                unit = ui._state.available_units[idx]
                if not unit.is_placed:
                    # Select unplaced unit for deployment
                    ui._selected_unit_index = idx
                    return f"select_unit:{idx}"
                else:
                    # Click placed unit in roster → just select it (DO NOT auto-remove)
                    # This prevents accidental removal. User must right-click to remove.
                    ui._selected_unit_index = idx
                    return f"view_placed_unit:{idx}"
            return None

        # Map click
        map_pos = ui.screen_to_map(screen_x, screen_y, map_offset_x, map_offset_y, tile_size)
        if map_pos is None:
            return None

        map_x, map_y = map_pos

        # If a unit is selected, try to place
        if ui._selected_unit_index is not None:
            if ui.place_unit(ui._selected_unit_index, map_x, map_y):
                return f"place_unit:{ui._selected_unit_index}"
            return None

        # Otherwise, try to remove a placed unit at this position
        if ui.remove_unit(map_x, map_y):
            return f"remove_unit:{map_x},{map_y}"

        return None

    def _roster_index_at(self, click_x: int, click_y: int) -> int | None:
        """Return the roster unit index at screen coords, or None."""
        ui = self._ui
        if click_x < ui._roster_padding or click_x > ui._roster_width - ui._roster_padding:
            return None

        # Walk the layout to find which unit was clicked
        y_offset = 36
        for entry_type, entry_data in ui._roster_layout:
            if entry_type == "category":
                h = ui._roster_category_height + 2
                if y_offset <= click_y < y_offset + h:
                    return None  # Clicked on category header
                y_offset += h
            elif entry_type == "unit":
                h = ui._roster_item_height + 2
                if y_offset <= click_y < y_offset + h:
                    assert isinstance(entry_data, int)
                    return entry_data  # Return the unit index
                y_offset += h

        return None

    def _is_in_button(self, x: int, y: int) -> bool:
        ui = self._ui
        if ui._button_rect is None:
            return False
        bx, by, bw, bh = ui._button_rect
        return bx <= x <= bx + bw and by <= y <= by + bh
