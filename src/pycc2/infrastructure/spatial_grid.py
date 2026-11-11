"""Spatial Grid System - Sprint 2 Day 9 PERF-02.

Accelerates collision detection and spatial queries by partitioning units into grid cells.
Reduces O(n²) naive collision checks to O(n + k) where k = units in nearby cells.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.value_objects.tile_coord import TileCoord

logger = logging.getLogger(__name__)


class SpatialGrid:
    """Grid-based spatial indexing for fast unit queries.

    Divides game world into NxM grid cells. Units are indexed by their cell position.
    Supports fast range queries (get units in rectangle) and neighbor queries.

    Attributes:
        cell_size: Size of each grid cell (tiles)
        width: Total grid width (tiles)
        height: Total grid height (tiles)
        grid: Dict mapping (cell_x, cell_y) -> Set[Unit]
    """

    def __init__(self, cell_size: int = 16, width: int = 256, height: int = 256):
        """Initialize spatial grid.

        Args:
            cell_size: Size of each cell in tiles (default 16x16)
            width: Total world width in tiles
            height: Total world height in tiles
        """
        self.cell_size = cell_size
        self.width = width
        self.height = height
        self.cols = (width + cell_size - 1) // cell_size
        self.rows = (height + cell_size - 1) // cell_size

        # Grid storage: (cell_x, cell_y) -> Set[Unit]
        self.grid: dict[tuple[int, int], set[Unit]] = defaultdict(set)

        # Unit -> cell mapping for fast updates
        self.unit_cells: dict[str, tuple[int, int]] = {}

        logger.info(
            f"SpatialGrid initialized: {self.cols}x{self.rows} cells "
            f"({self.cell_size}x{self.cell_size} tiles each)"
        )

    def _get_cell_coords(self, tile_x: int, tile_y: int) -> tuple[int, int]:
        """Convert tile coordinates to cell coordinates.

        Args:
            tile_x: Tile X position
            tile_y: Tile Y position

        Returns:
            (cell_x, cell_y) tuple
        """
        cell_x = tile_x // self.cell_size
        cell_y = tile_y // self.cell_size

        # Clamp to grid bounds
        cell_x = max(0, min(cell_x, self.cols - 1))
        cell_y = max(0, min(cell_y, self.rows - 1))

        return (cell_x, cell_y)

    def insert(self, unit: Unit) -> None:
        """Insert unit into spatial grid.

        Args:
            unit: Unit to insert
        """
        tile_pos = unit.position.tile_position
        cell_coords = self._get_cell_coords(tile_pos.x, tile_pos.y)

        # Remove from old cell if exists
        if unit.id in self.unit_cells:
            old_cell = self.unit_cells[unit.id]
            if old_cell != cell_coords:
                self.grid[old_cell].discard(unit)

        # Add to new cell
        self.grid[cell_coords].add(unit)
        self.unit_cells[unit.id] = cell_coords

    def remove(self, unit: Unit) -> None:
        """Remove unit from spatial grid.

        Args:
            unit: Unit to remove
        """
        if unit.id in self.unit_cells:
            cell_coords = self.unit_cells[unit.id]
            self.grid[cell_coords].discard(unit)
            del self.unit_cells[unit.id]

    def update(self, unit: Unit) -> None:
        """Update unit position in grid (alias for insert).

        Args:
            unit: Unit to update
        """
        self.insert(unit)

    def query_rect(self, min_x: int, min_y: int, max_x: int, max_y: int) -> list[Unit]:
        """Query units in rectangle (tile coordinates).

        Args:
            min_x: Minimum tile X
            min_y: Minimum tile Y
            max_x: Maximum tile X
            max_y: Maximum tile Y

        Returns:
            List of units in rectangle (with possible duplicates removed)
        """
        min_cell = self._get_cell_coords(min_x, min_y)
        max_cell = self._get_cell_coords(max_x, max_y)

        units_set = set()
        for cy in range(min_cell[1], max_cell[1] + 1):
            for cx in range(min_cell[0], max_cell[0] + 1):
                units_set.update(self.grid.get((cx, cy), set()))

        # Filter to exact rectangle bounds
        result = [
            unit
            for unit in units_set
            if (
                min_x <= unit.position.tile_position.x <= max_x
                and min_y <= unit.position.tile_position.y <= max_y
            )
        ]

        return result

    def query_radius(self, center: TileCoord, radius: float) -> list[Unit]:
        """Query units in circular radius (tile coordinates).

        Args:
            center: Center tile coordinate
            radius: Search radius in tiles

        Returns:
            List of units within radius
        """
        # Convert radius to rectangle
        min_x = int(center.x - radius)
        min_y = int(center.y - radius)
        max_x = int(center.x + radius)
        max_y = int(center.y + radius)

        units_in_rect = self.query_rect(min_x, min_y, max_x, max_y)

        # Filter to exact circular distance
        result = [
            unit
            for unit in units_in_rect
            if unit.position.tile_position.octile_distance(center) <= radius
        ]

        return result

    def get_neighbors(self, unit: Unit, range_cells: int = 1) -> list[Unit]:
        """Get units in neighboring cells.

        Args:
            unit: Center unit
            range_cells: Cell range (1 = 3x3 neighborhood, 2 = 5x5, etc.)

        Returns:
            List of neighboring units (excluding self)
        """
        if unit.id not in self.unit_cells:
            return []

        center_cell = self.unit_cells[unit.id]
        neighbors = []

        for dy in range(-range_cells, range_cells + 1):
            for dx in range(-range_cells, range_cells + 1):
                cell = (center_cell[0] + dx, center_cell[1] + dy)
                neighbors.extend(self.grid.get(cell, set()))

        # Remove self
        return [u for u in neighbors if u.id != unit.id]

    def clear(self) -> None:
        """Clear all units from grid."""
        self.grid.clear()
        self.unit_cells.clear()

    def rebuild(self, units: list[Unit]) -> None:
        """Rebuild grid from scratch with given units.

        Args:
            units: List of all units to index
        """
        self.clear()
        for unit in units:
            self.insert(unit)

    def get_statistics(self) -> dict[str, float]:
        """Get grid statistics for profiling.

        Returns:
            Dict with keys: 'total_units', 'occupied_cells', 'avg_units_per_cell', 'max_units_in_cell'
        """
        total_units = len(self.unit_cells)
        occupied_cells = len([cell for cell, units in self.grid.items() if units])

        if occupied_cells == 0:
            return {
                "total_units": 0,
                "occupied_cells": 0,
                "avg_units_per_cell": 0.0,
                "max_units_in_cell": 0,
            }

        units_per_cell = [len(units) for units in self.grid.values() if units]
        avg_units = sum(units_per_cell) / len(units_per_cell)
        max_units = max(units_per_cell)

        return {
            "total_units": total_units,
            "occupied_cells": occupied_cells,
            "avg_units_per_cell": avg_units,
            "max_units_in_cell": max_units,
        }
