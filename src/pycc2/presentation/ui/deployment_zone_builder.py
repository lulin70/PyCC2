"""Deployment Zone Builder — Map zone construction and deployment initialization.

Extracted from deployment_ui.py God Class (SRP refactoring).
Handles zone map construction from map data, spawn-point zone inference,
and default roster/force-pool initialization.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.presentation.ui.deployment_ui import DeploymentUI

# Import models and constants
from pycc2.presentation.ui.deployment_factory import build_default_roster
from pycc2.presentation.ui.deployment_models import (
    DeploymentPhase,
    DeploymentUnit,
    ZoneType,
)


class DeploymentZoneBuilder:
    """Builds deployment zones and initializes the deployment phase.

    Extracted from DeploymentUI God Class to follow SRP.
    Accesses parent UI state via ``self._ui``.
    """

    def __init__(self, ui: DeploymentUI) -> None:
        """Store reference to parent UI for state access."""
        self._ui = ui

    def start_deployment(self, map_data: dict, faction: str = "ally") -> None:
        """Initialize deployment phase with map zones and unit roster.

        Parameters
        ----------
        map_data : dict
            Must contain keys:
              - ``width`` (int): map tile width
              - ``height`` (int): map tile height
              - ``tiles`` (list[list[int]]): 2-D terrain grid
            May contain:
              - ``friendly_zone`` / ``enemy_zone`` / ``no_mans_land``:
                lists of (x, y) tuples
              - ``spawn_points``: list of spawn point dicts with
                ``side`` and ``position`` keys
        faction : str
            ``"ally"`` or ``"axis"`` – determines which side's zones are
            used as FRIENDLY.

        """
        ui = self._ui
        ui._map_width = map_data.get("width", 50)
        ui._map_height = map_data.get("height", 42)
        ui._tile_grid = map_data.get("tiles")
        ui._faction = faction

        # Build zone map from explicit zones or spawn_points -----------
        friendly = set(map_data.get("friendly_zone", []))
        enemy = set(map_data.get("enemy_zone", []))
        nml = set(map_data.get("no_mans_land", []))

        # If no explicit zones, try building from spawn_points
        if not friendly and not enemy and not nml:
            spawn_points = map_data.get("spawn_points", [])
            if spawn_points:
                friendly, enemy, nml = self._zones_from_spawn_points(spawn_points)

        # Default: left third = friendly, right third = enemy, middle = NML
        if not friendly and not enemy and not nml:
            third = ui._map_width // 3
            for y in range(ui._map_height):
                for x in range(ui._map_width):
                    if x < third:
                        friendly.add((x, y))
                    elif x >= ui._map_width - third:
                        enemy.add((x, y))
                    else:
                        nml.add((x, y))

        # Swap for axis faction
        if faction == "axis":
            friendly, enemy = enemy, friendly

        ui._state.friendly_zone = sorted(friendly)
        ui._state.enemy_zone = sorted(enemy)
        ui._state.no_mans_land = sorted(nml)

        ui._zone_map = []
        for y in range(ui._map_height):
            row: list[ZoneType] = []
            for x in range(ui._map_width):
                if (x, y) in friendly:
                    row.append(ZoneType.FRIENDLY)
                elif (x, y) in enemy:
                    row.append(ZoneType.ENEMY_CONTROLLED)
                else:
                    row.append(ZoneType.NO_MANS_LAND)
            ui._zone_map.append(row)

        # Build default unit roster --------------------------------------
        ui._state.available_units = build_default_roster()
        ui._state.placed_units = []
        ui._state.phase = DeploymentPhase.DEPLOYING
        ui._selected_unit_index = None

        # Default requisition points
        if ui._state.requisition_points <= 0:
            ui._state.requisition_points = 2000
        ui._state.requisition_points_spent = 0

        # Store victory locations for LOS preview (G5)
        ui._victory_locations = map_data.get("victory_locations", [])

        # Rebuild roster layout
        ui._renderer._rebuild_roster_layout()

        # Invalidate overlay cache
        ui._overlay_cache = None

    def start_deployment_with_settings(
        self,
        map_data: dict,
        faction: str = "ally",
        requisition_points: int = 2000,
        max_infantry: int = 9,
        max_support: int = 6,
        force_pool: list[DeploymentUnit] | None = None,
    ) -> None:
        """Initialize deployment with game settings controlling the force pool.

        Parameters
        ----------
        map_data : dict
            Map data (same as ``start_deployment``).
        faction : str
            Player faction.
        requisition_points : int
            Total requisition points available.
        max_infantry, max_support : int
            Maximum units per category.
        force_pool : list[DeploymentUnit] | None
            Custom force pool; if None, default roster is built.

        """
        ui = self._ui
        ui._state.requisition_points = requisition_points
        ui._state.max_infantry = max_infantry
        ui._state.max_support = max_support
        ui._state.requisition_points_spent = 0

        # Initialize zones via the base method
        self.start_deployment(map_data, faction)

        # Override roster if custom force pool provided
        if force_pool is not None:
            ui._state.available_units = force_pool
            ui._renderer._rebuild_roster_layout()

    def _zones_from_spawn_points(
        self, spawn_points: list[dict]
    ) -> tuple[set[tuple[int, int]], set[tuple[int, int]], set[tuple[int, int]]]:
        """Build deployment zones from map spawn_points data.

        Uses spawn point positions as centers and expands outward to
        create deployment zones covering roughly 1/3 of the map each.
        """
        ui = self._ui
        friendly: set[tuple[int, int]] = set()
        enemy: set[tuple[int, int]] = set()
        nml: set[tuple[int, int]] = set()

        ally_spawns = [sp for sp in spawn_points if sp.get("side") == "allies"]
        axis_spawns = [sp for sp in spawn_points if sp.get("side") == "axis"]

        # Determine zone boundaries based on spawn positions
        if ally_spawns and axis_spawns:
            ally_center_x = sum(sp["position"][0] for sp in ally_spawns) // len(ally_spawns)
            axis_center_x = sum(sp["position"][0] for sp in axis_spawns) // len(axis_spawns)

            # Ensure ally is left, axis is right
            if ally_center_x > axis_center_x:
                ally_center_x, axis_center_x = axis_center_x, ally_center_x

            # Create zones: ally left portion, axis right portion, NML middle
            ally_boundary = (ally_center_x + axis_center_x) // 3
            axis_boundary = 2 * (ally_center_x + axis_center_x) // 3

            for y in range(ui._map_height):
                for x in range(ui._map_width):
                    if x <= ally_boundary:
                        friendly.add((x, y))
                    elif x >= axis_boundary:
                        enemy.add((x, y))
                    else:
                        nml.add((x, y))
        else:
            # Fallback to default thirds
            third = ui._map_width // 3
            for y in range(ui._map_height):
                for x in range(ui._map_width):
                    if x < third:
                        friendly.add((x, y))
                    elif x >= ui._map_width - third:
                        enemy.add((x, y))
                    else:
                        nml.add((x, y))

        return friendly, enemy, nml
