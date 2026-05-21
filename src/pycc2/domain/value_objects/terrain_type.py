"""
TerrainType IntEnum - 14 Terrain Types with Properties
"""

from __future__ import annotations

from enum import IntEnum


class TerrainType(IntEnum):
    OPEN = 0
    ROAD = 1
    GRASS = 2
    WOODS = 3
    BUILDING_ENTERABLE = 4
    BUILDING_SOLID = 5
    WATER = 6
    HEDGE = 7
    WALL = 8
    ROUGH = 9
    SHALLOW = 10
    BRIDGE = 11
    CRATER = 12
    SWAMP = 13

    @property
    def movement_cost(self) -> float:
        _costs: dict[TerrainType, float] = {
            TerrainType.OPEN: 1.0,
            TerrainType.ROAD: 0.8,
            TerrainType.GRASS: 1.2,
            TerrainType.WOODS: 2.0,
            TerrainType.BUILDING_ENTERABLE: 1.5,
            TerrainType.BUILDING_SOLID: float("inf"),
            TerrainType.WATER: float("inf"),
            TerrainType.HEDGE: 2.5,
            TerrainType.WALL: float("inf"),
            TerrainType.ROUGH: 1.8,
            TerrainType.SHALLOW: 3.0,
            TerrainType.BRIDGE: 0.9,
            TerrainType.CRATER: 2.5,
            TerrainType.SWAMP: 4.0,
        }
        return _costs[self]

    @property
    def cover_bonus(self) -> float:
        _covers: dict[TerrainType, float] = {
            TerrainType.OPEN: 0.0,
            TerrainType.ROAD: 0.0,
            TerrainType.GRASS: 0.05,
            TerrainType.WOODS: 0.20,
            TerrainType.BUILDING_ENTERABLE: 0.50,
            TerrainType.BUILDING_SOLID: 0.80,
            TerrainType.WATER: 0.0,
            TerrainType.HEDGE: 0.15,
            TerrainType.WALL: 0.70,
            TerrainType.ROUGH: 0.08,
            TerrainType.SHALLOW: 0.05,
            TerrainType.BRIDGE: 0.0,
            TerrainType.CRATER: 0.25,
            TerrainType.SWAMP: 0.0,
        }
        return _covers[self]

    @property
    def concealment_modifier(self) -> float:
        _concealments: dict[TerrainType, float] = {
            TerrainType.OPEN: 0.0,
            TerrainType.ROAD: 0.0,
            TerrainType.GRASS: 0.15,
            TerrainType.WOODS: 0.50,
            TerrainType.BUILDING_ENTERABLE: 0.70,
            TerrainType.BUILDING_SOLID: 0.90,
            TerrainType.WATER: 0.05,
            TerrainType.HEDGE: 0.35,
            TerrainType.WALL: 0.80,
            TerrainType.ROUGH: 0.25,
            TerrainType.SHALLOW: 0.10,
            TerrainType.BRIDGE: 0.0,
            TerrainType.CRATER: 0.20,
            TerrainType.SWAMP: 0.30,
        }
        return _concealments[self]

    @property
    def blocks_los(self) -> bool:
        _blocks: dict[TerrainType, bool] = {
            TerrainType.OPEN: False,
            TerrainType.ROAD: False,
            TerrainType.GRASS: False,
            TerrainType.WOODS: True,
            TerrainType.BUILDING_ENTERABLE: False,
            TerrainType.BUILDING_SOLID: True,
            TerrainType.WATER: True,
            TerrainType.HEDGE: False,
            TerrainType.WALL: True,
            TerrainType.ROUGH: False,
            TerrainType.SHALLOW: False,
            TerrainType.BRIDGE: False,
            TerrainType.CRATER: False,
            TerrainType.SWAMP: False,
        }
        return _blocks[self]

    @property
    def is_passable(self) -> bool:
        _passable: dict[TerrainType, bool] = {
            TerrainType.OPEN: True,
            TerrainType.ROAD: True,
            TerrainType.GRASS: True,
            TerrainType.WOODS: True,
            TerrainType.BUILDING_ENTERABLE: True,
            TerrainType.BUILDING_SOLID: False,
            TerrainType.WATER: False,
            TerrainType.HEDGE: True,
            TerrainType.WALL: False,
            TerrainType.ROUGH: True,
            TerrainType.SHALLOW: True,
            TerrainType.BRIDGE: True,
            TerrainType.CRATER: True,
            TerrainType.SWAMP: True,
        }
        return _passable[self]

    @property
    def height(self) -> int:
        _heights: dict[TerrainType, int] = {
            TerrainType.OPEN: 0,
            TerrainType.ROAD: 0,
            TerrainType.GRASS: 0,
            TerrainType.WOODS: 2,
            TerrainType.BUILDING_ENTERABLE: 2,
            TerrainType.BUILDING_SOLID: 3,
            TerrainType.WATER: 0,
            TerrainType.HEDGE: 1,
            TerrainType.WALL: 2,
            TerrainType.ROUGH: 0,
            TerrainType.SHALLOW: 0,
            TerrainType.BRIDGE: 1,
            TerrainType.CRATER: -1,
            TerrainType.SWAMP: 0,
        }
        return _heights[self]

    @property
    def color(self) -> tuple[int, int, int]:
        _colors: dict[TerrainType, tuple[int, int, int]] = {
            TerrainType.OPEN: (200, 200, 180),
            TerrainType.ROAD: (128, 128, 128),
            TerrainType.GRASS: (76, 153, 0),
            TerrainType.WOODS: (34, 100, 34),
            TerrainType.BUILDING_ENTERABLE: (160, 140, 120),
            TerrainType.BUILDING_SOLID: (100, 80, 60),
            TerrainType.WATER: (65, 105, 225),
            TerrainType.HEDGE: (80, 120, 40),
            TerrainType.WALL: (105, 105, 105),
            TerrainType.ROUGH: (154, 140, 125),
            TerrainType.SHALLOW: (100, 149, 237),
            TerrainType.BRIDGE: (139, 119, 101),
            TerrainType.CRATER: (90, 75, 60),
            TerrainType.SWAMP: (60, 80, 50),
        }
        return _colors[self]

    @property
    def display_name(self) -> str:
        _names: dict[TerrainType, str] = {
            TerrainType.OPEN: "Open",
            TerrainType.ROAD: "Road",
            TerrainType.GRASS: "Grass",
            TerrainType.WOODS: "Woods",
            TerrainType.BUILDING_ENTERABLE: "Building (Enterable)",
            TerrainType.BUILDING_SOLID: "Building (Solid)",
            TerrainType.WATER: "Water",
            TerrainType.HEDGE: "Hedge",
            TerrainType.WALL: "Wall",
            TerrainType.ROUGH: "Rough",
            TerrainType.SHALLOW: "Shallow Water",
            TerrainType.BRIDGE: "Bridge",
            TerrainType.CRATER: "Crater",
            TerrainType.SWAMP: "Swamp",
        }
        return _names[self]


def get_movement_cost(terrain: TerrainType) -> float:
    return terrain.movement_cost
