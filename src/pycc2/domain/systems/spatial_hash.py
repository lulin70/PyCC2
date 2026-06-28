"""SpatialHash - Optimized spatial indexing for combat target selection.

Replaces O(n^2) target selection in combat_resolver.py by partitioning
the game world into a uniform grid. Query operations only check cells
within the search area, reducing average complexity to O(k) where k is
the number of units in the relevant cells.
"""

from __future__ import annotations

from dataclasses import dataclass

from pycc2.domain.entities.unit import Faction
from pycc2.domain.value_objects.tile_coord import TileCoord


@dataclass(slots=True)
class _UnitEntry:
    unit_id: str
    position: TileCoord
    faction: Faction
    cell: tuple[int, int]


class SpatialHash:
    """Spatial hash grid for efficient proximity queries on game units.

    The world is divided into a uniform grid of cell_size x cell_size tiles.
    Each unit is placed in the cell corresponding to its position. Queries
    scan only the cells that overlap the search area.
    """

    def __init__(self, cell_size: int = 10) -> None:
        """Initialize the spatial hash with the given cell size in tiles."""
        if cell_size <= 0:
            raise ValueError(f"cell_size must be positive, got {cell_size}")
        self._cell_size = cell_size
        self._cells: dict[tuple[int, int], list[str]] = {}
        self._unit_data: dict[str, _UnitEntry] = {}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _cell_key(self, position: TileCoord) -> tuple[int, int]:
        return (position.x // self._cell_size, position.y // self._cell_size)

    def _add_to_cell(self, cell: tuple[int, int], unit_id: str) -> None:
        if cell not in self._cells:
            self._cells[cell] = []
        self._cells[cell].append(unit_id)

    def _remove_from_cell(self, cell: tuple[int, int], unit_id: str) -> None:
        bucket = self._cells.get(cell)
        if bucket is None:
            return
        try:
            bucket.remove(unit_id)
        except ValueError:
            return
        if not bucket:
            del self._cells[cell]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Remove all units and cells from the spatial hash."""
        self._cells.clear()
        self._unit_data.clear()

    def insert(self, unit_id: str, position: TileCoord, faction: Faction) -> None:
        """Insert a unit into the grid, replacing any existing entry with the same id."""
        if unit_id in self._unit_data:
            self.remove(unit_id)
        cell = self._cell_key(position)
        self._unit_data[unit_id] = _UnitEntry(
            unit_id=unit_id,
            position=position,
            faction=faction,
            cell=cell,
        )
        self._add_to_cell(cell, unit_id)

    def remove(self, unit_id: str) -> None:
        """Remove a unit from the spatial hash by id."""
        entry = self._unit_data.pop(unit_id, None)
        if entry is not None:
            self._remove_from_cell(entry.cell, unit_id)

    def query_radius(
        self,
        center: TileCoord,
        radius: int,
        exclude_faction: Faction | None = None,
    ) -> list[str]:
        """Return unit ids within the given tile radius of center, optionally excluding a faction."""
        if radius < 0:
            return []
        # Determine the bounding box of cells that could contain results.
        min_cx = (center.x - radius) // self._cell_size
        max_cx = (center.x + radius) // self._cell_size
        min_cy = (center.y - radius) // self._cell_size
        max_cy = (center.y + radius) // self._cell_size

        radius_sq = radius * radius
        result: list[str] = []

        for cx in range(min_cx, max_cx + 1):
            for cy in range(min_cy, max_cy + 1):
                bucket = self._cells.get((cx, cy))
                if bucket is None:
                    continue
                for uid in bucket:
                    entry = self._unit_data[uid]
                    if exclude_faction is not None and entry.faction == exclude_faction:
                        continue
                    dx = entry.position.x - center.x
                    dy = entry.position.y - center.y
                    if dx * dx + dy * dy <= radius_sq:
                        result.append(uid)
        return result

    def query_rect(
        self,
        x_min: int,
        y_min: int,
        x_max: int,
        y_max: int,
        exclude_faction: Faction | None = None,
    ) -> list[str]:
        """Return unit ids inside the given axis-aligned rectangle, optionally excluding a faction."""
        min_cx = x_min // self._cell_size
        max_cx = x_max // self._cell_size
        min_cy = y_min // self._cell_size
        max_cy = y_max // self._cell_size

        result: list[str] = []

        for cx in range(min_cx, max_cx + 1):
            for cy in range(min_cy, max_cy + 1):
                bucket = self._cells.get((cx, cy))
                if bucket is None:
                    continue
                for uid in bucket:
                    entry = self._unit_data[uid]
                    if exclude_faction is not None and entry.faction == exclude_faction:
                        continue
                    px, py = entry.position.x, entry.position.y
                    if x_min <= px <= x_max and y_min <= py <= y_max:
                        result.append(uid)
        return result

    def get_position(self, unit_id: str) -> TileCoord | None:
        """Return the current tile position of the unit, or None if not tracked."""
        entry = self._unit_data.get(unit_id)
        return entry.position if entry is not None else None

    def get_faction(self, unit_id: str) -> Faction | None:
        """Return the faction of the unit, or None if not tracked."""
        entry = self._unit_data.get(unit_id)
        return entry.faction if entry is not None else None

    def update(self, unit_id: str, new_position: TileCoord) -> None:
        """Move a tracked unit to a new tile position, migrating cells when needed."""
        entry = self._unit_data.get(unit_id)
        if entry is None:
            return
        new_cell = self._cell_key(new_position)
        if new_cell != entry.cell:
            self._remove_from_cell(entry.cell, unit_id)
            self._add_to_cell(new_cell, unit_id)
        entry.position = new_position
        entry.cell = new_cell

    def unit_count(self) -> int:
        """Return the number of units currently tracked in the spatial hash."""
        return len(self._unit_data)

    def build_from_units(self, units: list) -> None:
        """Reset the hash and populate it from an iterable of unit objects."""
        self.clear()
        for unit in units:
            self.insert(unit.id, unit.position.tile_coord, unit.faction)
