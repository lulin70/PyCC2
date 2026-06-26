"""
Deployment Pre-Battle Orders System — GAP-8

Extracted from deployment_ui.py (SRP refactoring).
Manages pre-battle movement orders that players can assign to deployed
units before battle begins. These orders are executed when battle starts.
"""

from __future__ import annotations

# Import models
from pycc2.presentation.ui.deployment_models import DeploymentPhase, DeploymentUnit


class DeploymentOrders:
    """
    Manages pre-battle movement orders for deployed units.

    Players can select a placed unit and right-click on the map to set
    a pending move target. Orders are stored as unit_template_id -> (target_x, target_y)
    mappings and included in the battle finalization data.
    """

    def __init__(self) -> None:
        # === Pre-battle orders (GAP-8) ===
        self._pending_orders: dict[
            str, tuple[int, int]
        ] = {}  # unit_template_id -> (target_x, target_y)
        self._selected_placed_unit: DeploymentUnit | None = None  # For setting orders
        self._highlight_surface_cache: dict[int, object] = {}

    # ------------------------------------------------------------------
    # Public API – order management
    # ------------------------------------------------------------------

    def set_pending_order(self, unit_template_id: str, target_x: int, target_y: int) -> None:
        """Set a pending movement order for a deployed unit.

        The unit will move toward (target_x, target_y) when battle begins.
        """
        self._pending_orders[unit_template_id] = (target_x, target_y)

    def get_pending_order(self, unit_template_id: str) -> tuple[int, int] | None:
        """Return the pending order target for a unit, or None."""
        return self._pending_orders.get(unit_template_id)

    def clear_pending_order(self, unit_template_id: str) -> None:
        """Remove a pending order for a unit."""
        self._pending_orders.pop(unit_template_id, None)

    @property
    def pending_orders(self) -> dict[str, tuple[int, int]]:
        """Return a copy of all pending orders."""
        return dict(self._pending_orders)

    @property
    def selected_placed_unit(self) -> DeploymentUnit | None:
        """The currently selected placed unit for order assignment."""
        return self._selected_placed_unit

    @selected_placed_unit.setter
    def selected_placed_unit(self, value: DeploymentUnit | None) -> None:
        """Set the selected placed unit for order assignment."""
        self._selected_placed_unit = value

    def clear_selection(self) -> None:
        """Clear the selected placed unit."""
        self._selected_placed_unit = None

    # ------------------------------------------------------------------
    # Right-click handling with order logic
    # ------------------------------------------------------------------

    def handle_right_click(
        self,
        screen_x: int,
        screen_y: int,
        ui,
    ) -> str | None:
        """Handle a right-click during deployment with order support.

        Behaviour (GAP-8):
          - If a placed unit is selected, right-click on the map sets a
            pending move order for that unit.
          - If no placed unit is selected, right-click on a placed unit
            selects it for ordering.
          - Right-click on roster deselects.

        Parameters
        ----------
        screen_x, screen_y : int
            Screen coordinates of the right-click.
        ui : DeploymentUI
            The parent DeploymentUI instance.

        Returns an action string or None:
          - ``"set_order:<unit_id>,<tx>,<ty>"`` – pending move order set
          - ``"select_placed_unit:<x>,<y>"`` – placed unit selected for ordering
          - ``"remove_unit:<x>,<y>"`` – placed unit removed (no unit selected)
          - ``None`` – click did nothing
        """
        if ui._state.phase not in (DeploymentPhase.DEPLOYING, DeploymentPhase.READY):
            return None

        # Right-click on roster → deselect
        if screen_x < ui._roster_width:
            ui._selected_unit_index = None
            self._selected_placed_unit = None
            return None

        # Right-click on map
        map_pos = ui.screen_to_map(screen_x, screen_y)
        if map_pos is None:
            return None

        map_x, map_y = map_pos

        # If a placed unit is selected, set a pending move order
        if self._selected_placed_unit is not None and self._selected_placed_unit.is_placed:
            # Set the pending order
            self.set_pending_order(self._selected_placed_unit.unit_template_id, map_x, map_y)
            result = f"set_order:{self._selected_placed_unit.unit_template_id},{map_x},{map_y}"
            return result

        # Otherwise, try to select a placed unit at this position
        for pu in ui._state.placed_units:
            if pu.position == (map_x, map_y):
                self._selected_placed_unit = pu
                # Also find and set the roster index for the detail panel
                for i, au in enumerate(ui._state.available_units):
                    if au is pu:
                        ui._selected_unit_index = i
                        break
                return f"select_placed_unit:{map_x},{map_y}"

        # No placed unit selected and no unit at click position → remove (legacy behavior)
        if ui.remove_unit(map_x, map_y):
            return f"remove_unit:{map_x},{map_y}"

        return None

    # ------------------------------------------------------------------
    # Battle finalization
    # ------------------------------------------------------------------

    def get_orders_for_battle(self) -> dict[str, tuple[int, int]]:
        """Return pending orders for inclusion in battle finalization data.

        Called by begin_battle() to include pre-battle orders in the
        deployment result.
        """
        return dict(self._pending_orders)
