from __future__ import annotations

import json
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


@dataclass(slots=True)
class MapObjective:
    id: str
    name: str
    position: TileCoord
    radius: int = 1
    required: bool = True
    owner: str | None = None


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

    def __post_init__(self) -> None:
        if not isinstance(self.tile_grid, np.ndarray):
            self.tile_grid = np.array(self.tile_grid, dtype=np.int8)
        assert self.tile_grid.shape == (self.height, self.width), (
            f"tile_grid shape {self.tile_grid.shape} != ({self.height}, {self.width})"
        )

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
                [[_TERRAIN_NAME_MAP.get(t.get("terrain_type", "open").lower(), 0) for t in row] for row in raw_tiles],
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

        return cls(
            id=data.get("id", Path(filepath).stem),
            name=data.get("name", "Untitled"),
            width=data["width"],
            height=data["height"],
            tile_grid=grid,
            objectives=objectives,
            spawn_points=spawn_points,
            tiles_enhanced=data.get("tiles_enhanced"),
        )

    def get_terrain(self, coord: TileCoord) -> TerrainType:
        return TerrainType(int(self.tile_grid[coord.y, coord.x]))

    def set_terrain(self, coord: TileCoord, terrain: TerrainType) -> None:
        self.tile_grid[coord.y, coord.x] = terrain.value

    def is_passable(self, coord: TileCoord) -> bool:
        if not self.is_within_bounds(coord):
            return False
        return self.get_terrain(coord).is_passable

    def is_within_bounds(self, coord: TileCoord) -> bool:
        return coord.is_within_bounds(self.width, self.height)

    def has_line_of_sight(self, from_coord: TileCoord, to_coord: TileCoord) -> bool:
        line = self._bresenham_line(from_coord, to_coord)
        for c in line[1:-1]:
            if not self.is_within_bounds(c):
                return False
            if self.get_terrain(c).blocks_los:
                return False
        return True

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
        key = f"{x},{y}"
        return self.tiles_enhanced.get(key)

    def has_enhanced_data(self) -> bool:
        """Return True if tiles_enhanced data is present."""
        return self.tiles_enhanced is not None
