"""Deployment Placement Service — Unit placement and removal logic.

Extracted from deployment_ui.py God Class (SRP refactoring).
Handles unit placement validation, placement execution, and removal.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.presentation.ui.deployment_ui import DeploymentUI

# Import models and constants
from pycc2.presentation.ui.deployment_models import (
    TERRAIN_BUILDING_SOLID,
    TERRAIN_WATER,
    DeploymentPhase,
    DeploymentUnit,
    ZoneType,
)


class DeploymentPlacementService:
    """Handles unit placement and removal during deployment.

    Extracted from DeploymentUI God Class to follow SRP.
    Accesses parent UI state via ``self._ui``.
    """

    def __init__(self, ui: DeploymentUI) -> None:
        """Store reference to parent UI for state access."""
        self._ui = ui

    def place_unit(self, unit_index: int, map_x: int, map_y: int) -> bool:
        """Place a unit at the given map tile position.

        Returns True if placement succeeded.
        """
        ui = self._ui
        if ui._state.phase not in (DeploymentPhase.DEPLOYING, DeploymentPhase.READY):
            return False

        if unit_index < 0 or unit_index >= len(ui._state.available_units):
            return False

        unit = ui._state.available_units[unit_index]

        # Already placed somewhere else?
        if unit.is_placed:
            return False

        # Check requisition points
        if unit.deployment_cost > ui.requisition_remaining:
            return False

        # Check zone
        if not self._is_in_friendly_zone(map_x, map_y):
            return False

        # Check terrain
        terrain = ui._get_terrain_at(map_x, map_y)
        if not self.can_place_at(unit, map_x, map_y, terrain):
            return False

        # Check unit count limits
        if not self._check_unit_limits(unit):
            return False

        # Check tile not already occupied
        for pu in ui._state.placed_units:
            if pu.position == (map_x, map_y):
                return False

        # Place the unit (with defensive checks)
        try:
            unit.position = (map_x, map_y)
            unit.is_placed = True
            ui._state.placed_units.append(unit)
            ui._state.requisition_points_spent += unit.deployment_cost
        except (AttributeError, ValueError, TypeError):
            # If placement fails, rollback
            unit.position = None
            unit.is_placed = False
            return False

        # Clear selection after placing
        ui._selected_unit_index = None

        # Auto-transition to READY when at least one unit placed
        if ui._state.phase == DeploymentPhase.DEPLOYING and ui._state.placed_units:
            ui._state.phase = DeploymentPhase.READY

        return True

    def remove_unit(self, map_x: int, map_y: int) -> bool:
        """Remove a placed unit at the given map position, returning it to roster.

        Returns True if a unit was removed.
        """
        ui = self._ui
        for i, pu in enumerate(ui._state.placed_units):
            if pu.position == (map_x, map_y):
                # Refund requisition points
                ui._state.requisition_points_spent -= pu.deployment_cost
                pu.position = None
                pu.is_placed = False
                ui._state.placed_units.pop(i)

                # Revert phase if no units left
                if not ui._state.placed_units:
                    ui._state.phase = DeploymentPhase.DEPLOYING

                return True
        return False

    def can_place_at(self, unit: DeploymentUnit, map_x: int, map_y: int, terrain: int) -> bool:
        """Check if *unit* can be placed at (map_x, map_y) with the given terrain value.

        ULTRA-RELAXED RULES for maximum gameplay flexibility:
        - ONLY block deep water and solid buildings (truly impassable)
        - ALL other terrains are allowed (roads, bridges, rough, hedges, etc.)
        """
        # Check 1: Must be in friendly zone
        if not self._is_in_friendly_zone(map_x, map_y):
            return False

        # Check 2: Only truly impassable terrains are blocked
        # Check 3: Everything else is ALLOWED!
        # No more restrictions on roads, rough terrain, buildings, hedges, etc.
        return terrain not in (TERRAIN_WATER, TERRAIN_BUILDING_SOLID)

    def _is_in_friendly_zone(self, x: int, y: int) -> bool:
        ui = self._ui
        if ui._zone_map is None:
            return False
        if not (0 <= x < ui._map_width and 0 <= y < ui._map_height):
            return False
        return ui._zone_map[y][x] == ZoneType.FRIENDLY

    def _check_unit_limits(self, unit: DeploymentUnit) -> bool:
        ui = self._ui
        infantry_count = sum(
            1 for u in ui._state.placed_units if u.unit_type in ("infantry", "recon")
        )
        support_count = sum(
            1 for u in ui._state.placed_units if u.unit_type in ("support", "vehicle")
        )

        if unit.unit_type == "infantry":
            return infantry_count < ui._state.max_infantry
        elif unit.unit_type in ("support", "vehicle"):
            return support_count < ui._state.max_support
        elif unit.unit_type == "recon":
            return infantry_count < ui._state.max_infantry
        return False
