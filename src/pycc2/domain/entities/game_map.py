from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from pycc2.domain.value_objects.terrain_type import TerrainType
from pycc2.domain.value_objects.tile_coord import TileCoord

_TERRAIN_NAME_MAP: dict[str, int] = {
    "open": 0,
    "road": 1,
    "grass": 2,
    "woods": 3,
    "building_enterable": 4,
    "building_solid": 5,
    "water": 6,
    "hedge": 7,
    "wall": 8,
    "rough": 9,
    "shallow": 10,
    "bridge": 11,
}


def _angle_diff(a: float, b: float) -> float:
    """Compute the shortest angular difference between two angles."""
    diff = a - b
    while diff > math.pi:
        diff -= 2 * math.pi
    while diff < -math.pi:
        diff += 2 * math.pi
    return diff


def _resolve_vp_points(obj: dict) -> int:
    """Resolve Victory Location point value from JSON objective data.

    CC2 authenticity (per GAP_ANALYSIS.md):
      - Bridge = 40 pts
      - Road = 30 pts
      - Landing Zone (LZ) = 20 pts
      - Regular = 10 pts

    Priority: explicit "points" field > id/name keyword inference > default 10.
    """
    explicit = obj.get("points")
    if isinstance(explicit, (int, float)) and explicit > 0:
        return int(explicit)

    text = f"{obj.get('id', '')} {obj.get('name', '')} {obj.get('type', '')}".lower()
    if "bridge" in text:
        return 40
    if "road" in text:
        return 30
    if "lz" in text or "landing" in text:
        return 20
    return 10


@dataclass(slots=True)
class MapObjective:
    id: str
    name: str
    position: TileCoord
    radius: int = 1
    required: bool = True
    owner: str | None = None
    # CC2-authentic VP point value (Bridge=40, Road=30, LZ=20, Regular=10-19).
    # 0 hides the numeral on the map (backwards-compatible default).
    points: int = 0


@dataclass(slots=True)
class SpawnPoint:
    id: str
    side: str
    position: TileCoord
    units_max: int = 6


@dataclass
class GameMap:
    id: str
    name: str
    width: int
    height: int
    tile_grid: np.ndarray
    objectives: list[MapObjective] = field(default_factory=list)
    spawn_points: list[SpawnPoint] = field(default_factory=list)
    tiles_enhanced: dict | None = None
    height_grid: np.ndarray | None = None  # Building height (0-3 floors)
    elevation_grid: np.ndarray | None = None  # Terrain elevation (0-5 levels)

    def __post_init__(self) -> None:
        if not isinstance(self.tile_grid, np.ndarray):
            self.tile_grid = np.array(self.tile_grid, dtype=np.int8)
        assert self.tile_grid.shape == (self.height, self.width), (
            f"tile_grid shape {self.tile_grid.shape} != ({self.height}, {self.width})"
        )

        if self.height_grid is None:
            self.height_grid = np.zeros((self.height, self.width), dtype=np.int8)

        if self.elevation_grid is None:
            self.elevation_grid = np.zeros((self.height, self.width), dtype=np.int8)

    @classmethod
    def from_json(cls, filepath: str | Path) -> GameMap:
        with open(filepath, encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)

        raw_tiles = data["tiles"]
        first_tile = raw_tiles[0][0]
        if isinstance(first_tile, str):
            grid = np.array(
                [[_TERRAIN_NAME_MAP.get(t.lower(), 0) for t in row] for row in raw_tiles],
                dtype=np.int8,
            )
        elif isinstance(first_tile, dict):
            # Rich tile format: {"terrain_type": "open", "elevation": 0, ...}
            grid = np.array(
                [
                    [_TERRAIN_NAME_MAP.get(t.get("terrain_type", "open").lower(), 0) for t in row]
                    for row in raw_tiles
                ],
                dtype=np.int8,
            )
        else:
            grid = np.array(raw_tiles, dtype=np.int8)

        objectives = [
            MapObjective(
                id=obj["id"],
                name=obj["name"],
                position=TileCoord(obj["position"][0], obj["position"][1]),
                radius=obj.get("radius", 1),
                required=obj.get("required", True),
                owner=obj.get("owner"),
                points=_resolve_vp_points(obj),
            )
            for obj in data.get("objectives", [])
        ]

        spawn_points = [
            SpawnPoint(
                id=sp["id"],
                side=sp["side"],
                position=TileCoord(sp["position"][0], sp["position"][1]),
                units_max=sp.get("units_max", 6),
            )
            for sp in data.get("spawn_points", [])
        ]

        # Extract height and elevation grids from rich tile format if available
        height_grid = None
        elevation_grid = None
        if isinstance(first_tile, dict):
            height_grid = np.array(
                [[t.get("height", 0) for t in row] for row in raw_tiles],
                dtype=np.int8,
            )
            elevation_grid = np.array(
                [[t.get("elevation", 0) for t in row] for row in raw_tiles],
                dtype=np.int8,
            )

        return cls(
            id=data.get("id", Path(filepath).stem),
            name=data.get("name", "Untitled"),
            width=data["width"],
            height=data["height"],
            tile_grid=grid,
            objectives=objectives,
            spawn_points=spawn_points,
            tiles_enhanced=data.get("tiles_enhanced"),
            height_grid=height_grid,
            elevation_grid=elevation_grid,
        )

    def get_terrain(self, coord: TileCoord) -> TerrainType:
        return TerrainType(int(self.tile_grid[coord.y, coord.x]))

    def set_terrain(self, coord: TileCoord, terrain: TerrainType) -> None:
        self.tile_grid[coord.y, coord.x] = terrain.value

    def modify_terrain(self, x: int, y: int, new_terrain: TerrainType) -> None:
        """Safely change a tile's terrain type at runtime.

        Validates coordinates before modification. Used for dynamic
        terrain changes such as bridge destruction or building collapse.
        """
        coord = TileCoord(x, y)
        if not self.is_within_bounds(coord):
            return
        self.tile_grid[y, x] = new_terrain.value

    def is_passable(self, coord: TileCoord) -> bool:
        if not self.is_within_bounds(coord):
            return False
        return self.get_terrain(coord).is_passable

    def is_within_bounds(self, coord: TileCoord) -> bool:
        return coord.is_within_bounds(self.width, self.height)

    def has_line_of_sight(self, from_coord: TileCoord, to_coord: TileCoord) -> bool:
        # Window firing arc check: if shooter is inside a building, verify
        # the firing angle passes through a window
        from_terrain = self.get_terrain(from_coord)
        if from_terrain.name == "building_enterable":
            if not self._check_window_firing_arc(from_coord, to_coord):
                return False

        line = self._bresenham_line(from_coord, to_coord)
        for c in line[1:-1]:
            if not self.is_within_bounds(c):
                return False
            if self.get_terrain(c).blocks_los:
                return False
        return True

    def _check_window_firing_arc(
        self,
        from_coord: TileCoord,
        to_coord: TileCoord,
    ) -> bool:
        """Check if a unit inside a building can fire through a window toward the target.

        In CC2, units inside buildings can only fire through windows. Each window
        faces a cardinal direction (N/S/E/W) with a ~90 degree firing arc centered
        on that direction. If no window faces the target direction, the shot is blocked.
        """
        from pycc2.domain.value_objects.building_data import (
            BUILDING_WINDOWS,
            CC2BuildingType,
        )

        # Calculate firing angle from building center to target
        angle = math.atan2(
            to_coord.y - from_coord.y,
            to_coord.x - from_coord.x,
        )

        # Look up building type from enhanced tile data
        enhanced = self.get_enhanced_tile(from_coord.x, from_coord.y)
        building_type_str = ""
        if enhanced and "building_type" in enhanced:
            building_type_str = enhanced["building_type"]

        bt = None
        for btype in CC2BuildingType:
            if btype.value == building_type_str:
                bt = btype
                break

        if bt is None:
            # Unknown building type: allow firing (no window restriction)
            return True

        windows = BUILDING_WINDOWS.get(bt, [])
        if not windows:
            # No windows defined: allow firing
            return True

        # Check if any window faces the target direction
        # Screen coordinates: y increases downward
        #   east  = 0 rad, south = pi/2, west = pi/-pi, north = -pi/2
        half_arc = math.pi / 4  # 45-degree half-arc → 90 degree total arc
        for window in windows:
            wall = window["wall"]
            if (
                wall == "east"
                and abs(_angle_diff(angle, 0.0)) < half_arc
                or wall == "south"
                and abs(_angle_diff(angle, math.pi / 2)) < half_arc
                or wall == "west"
                and abs(_angle_diff(angle, math.pi)) < half_arc
                or wall == "north"
                and abs(_angle_diff(angle, -math.pi / 2)) < half_arc
            ):
                return True

        return False  # No window faces the target direction

    @staticmethod
    def _bresenham_line(from_coord: TileCoord, to_coord: TileCoord) -> list[TileCoord]:
        x0, y0 = from_coord.x, from_coord.y
        x1, y1 = to_coord.x, to_coord.y
        points: list[TileCoord] = []
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        x, y = x0, y0
        while True:
            points.append(TileCoord(x, y))
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
        return points

    def get_spawn_point(self, side: str) -> SpawnPoint | None:
        for sp in self.spawn_points:
            if sp.side == side:
                return sp
        return None

    def get_objectives(self) -> list[MapObjective]:
        return list(self.objectives)

    def get_enhanced_tile(self, x: int, y: int) -> dict | None:
        """Return enhanced tile data for the given coordinates, if available."""
        if self.tiles_enhanced is None:
            return None
        if isinstance(self.tiles_enhanced, dict):
            key = f"{x},{y}"
            return self.tiles_enhanced.get(key)
        if isinstance(self.tiles_enhanced, list):
            # tiles_enhanced is a 2D array: list of rows, each row is a list of tile dicts
            if 0 <= y < len(self.tiles_enhanced):
                row = self.tiles_enhanced[y]
                if isinstance(row, list) and 0 <= x < len(row):
                    tile = row[x]
                    if isinstance(tile, dict):
                        return tile
            return None
        return None

    def has_enhanced_data(self) -> bool:
        """Return True if tiles_enhanced data is present."""
        return self.tiles_enhanced is not None

    # ========================================================================
    # M-1: Multi-level Building System (Height)
    # ========================================================================

    def get_building_height(self, coord: TileCoord) -> int:
        """
        Get building height at coordinate (0-3 floors).

        0 = Ground level (no building)
        1 = 1st floor
        2 = 2nd floor
        3 = Roof/3rd floor
        """
        if self.height_grid is None:
            return 0
        if not self.is_within_bounds(coord):
            return 0
        return int(self.height_grid[coord.y, coord.x])

    def set_building_height(self, coord: TileCoord, height: int) -> None:
        """
        Set building height at coordinate.

        Args:
            coord: Tile coordinate
            height: Building height (0-3)
        """
        if self.height_grid is None or not self.is_within_bounds(coord):
            return
        self.height_grid[coord.y, coord.x] = max(0, min(3, height))

    def get_total_height(self, coord: TileCoord) -> float:
        """
        Get total effective height = elevation + building_height.

        Used for LOS calculations.
        """
        return self.get_elevation(coord) + self.get_building_height(coord)

    # ========================================================================
    # M-2: Hill/Terrain Elevation System
    # ========================================================================

    def get_elevation(self, coord: TileCoord) -> float:
        """
        Get terrain elevation at coordinate (0-5 levels).

        0 = Flat ground
        1 = Gentle slope
        2 = Moderate hill
        3 = Steep hill
        4 = High ground
        5 = Mountain/cliff
        """
        if self.elevation_grid is None:
            return 0.0
        if not self.is_within_bounds(coord):
            return 0.0
        return float(self.elevation_grid[coord.y, coord.x])

    def set_elevation(self, coord: TileCoord, elevation: float) -> None:
        """
        Set terrain elevation at coordinate.

        Args:
            coord: Tile coordinate
            elevation: Elevation value (0.0-5.0)
        """
        if self.elevation_grid is None or not self.is_within_bounds(coord):
            return
        self.elevation_grid[coord.y, coord.x] = max(0.0, min(5.0, elevation))

    def get_slope_cost(self, from_coord: TileCoord, to_coord: TileCoord) -> float:
        """
        Calculate movement cost modifier based on slope.

        Returns:
            Multiplier for movement cost:
            - 1.0: Flat or downhill
            - 1.0-2.0: Uphill (steeper = slower)
        """
        from_elev = self.get_elevation(from_coord)
        to_elev = self.get_elevation(to_coord)
        elev_diff = to_elev - from_elev

        if elev_diff <= 0:
            return 1.0  # Flat or downhill: normal speed

        slope_multiplier = 1.0 + (elev_diff * 0.25)
        return min(slope_multiplier, 2.5)  # Cap at 2.5x slowdown

    def get_los_height_advantage(
        self,
        from_coord: TileCoord,
        to_coord: TileCoord,
    ) -> float:
        """
        Calculate LOS range advantage from elevation difference.

        Higher ground can see further over obstacles.

        Returns:
            Bonus to LOS range in tiles (can be negative if lower)
        """
        from_height = self.get_total_height(from_coord)
        to_height = self.get_total_height(to_coord)
        height_diff = from_height - to_height

        return height_diff * 2.0  # Each level of advantage = +2 tiles range
