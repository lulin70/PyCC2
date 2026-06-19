"""
TerrainType IntEnum - 22 Terrain Types with Properties
"""

from __future__ import annotations

from enum import IntEnum


class CoverType(IntEnum):
    """Cover classification for combat resolution.

    - NONE: Open ground - no protection
    - SOFT: Hedges, bushes, grass - reduces accuracy but doesn't block
    - HARD: Buildings, walls, bunkers - can completely block shots
    - HYBRID: Building interior - hard walls + soft windows
    """

    NONE = 0
    SOFT = 1
    HARD = 2
    HYBRID = 3


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
    BRIDGE_DESTROYED = 14
    FOXHOLE = 15
    TRENCH = 16
    MUD = 17
    SAND = 18
    SNOW = 19
    WIRE = 20
    BUNKER = 21

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
            TerrainType.BRIDGE_DESTROYED: 5.0,
            TerrainType.FOXHOLE: 1.3,
            TerrainType.TRENCH: 1.5,
            TerrainType.MUD: 2.5,
            TerrainType.SAND: 1.8,
            TerrainType.SNOW: 2.0,
            TerrainType.WIRE: 3.0,
            TerrainType.BUNKER: 1.5,
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
            TerrainType.BRIDGE_DESTROYED: 0.0,
            TerrainType.FOXHOLE: 0.30,
            TerrainType.TRENCH: 0.40,
            TerrainType.MUD: 0.0,
            TerrainType.SAND: 0.0,
            TerrainType.SNOW: 0.05,
            TerrainType.WIRE: 0.10,
            TerrainType.BUNKER: 0.60,
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
            TerrainType.BRIDGE_DESTROYED: 0.10,
            TerrainType.FOXHOLE: 0.25,
            TerrainType.TRENCH: 0.35,
            TerrainType.MUD: 0.10,
            TerrainType.SAND: 0.0,
            TerrainType.SNOW: 0.15,
            TerrainType.WIRE: 0.05,
            TerrainType.BUNKER: 0.80,
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
            TerrainType.WATER: False,
            TerrainType.HEDGE: False,
            TerrainType.WALL: True,
            TerrainType.ROUGH: False,
            TerrainType.SHALLOW: False,
            TerrainType.BRIDGE: False,
            TerrainType.CRATER: False,
            TerrainType.SWAMP: False,
            TerrainType.BRIDGE_DESTROYED: True,
            TerrainType.FOXHOLE: False,
            TerrainType.TRENCH: False,
            TerrainType.MUD: False,
            TerrainType.SAND: False,
            TerrainType.SNOW: False,
            TerrainType.WIRE: False,
            TerrainType.BUNKER: True,
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
            TerrainType.BRIDGE_DESTROYED: True,
            TerrainType.FOXHOLE: True,
            TerrainType.TRENCH: True,
            TerrainType.MUD: True,
            TerrainType.SAND: True,
            TerrainType.SNOW: True,
            TerrainType.WIRE: True,
            TerrainType.BUNKER: True,
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
            TerrainType.CRATER: 0,
            TerrainType.SWAMP: 0,
            TerrainType.BRIDGE_DESTROYED: 0,
            TerrainType.FOXHOLE: 0,
            TerrainType.TRENCH: 0,
            TerrainType.MUD: 0,
            TerrainType.SAND: 0,
            TerrainType.SNOW: 0,
            TerrainType.WIRE: 0,
            TerrainType.BUNKER: 1,
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
            TerrainType.BRIDGE_DESTROYED: (80, 65, 50),
            TerrainType.FOXHOLE: (120, 110, 80),
            TerrainType.TRENCH: (100, 90, 65),
            TerrainType.MUD: (90, 70, 45),
            TerrainType.SAND: (180, 165, 120),
            TerrainType.SNOW: (230, 235, 240),
            TerrainType.WIRE: (76, 153, 0),
            TerrainType.BUNKER: (120, 115, 105),
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
            TerrainType.BRIDGE_DESTROYED: "Bridge (Destroyed)",
            TerrainType.FOXHOLE: "Foxhole",
            TerrainType.TRENCH: "Trench",
            TerrainType.MUD: "Mud",
            TerrainType.SAND: "Sand",
            TerrainType.SNOW: "Snow",
            TerrainType.WIRE: "Wire",
            TerrainType.BUNKER: "Bunker",
        }
        return _names[self]

    @property
    def is_passable_by_vehicle(self) -> bool:
        """Whether vehicles can traverse this terrain.

        BRIDGE_DESTROYED is passable by infantry (wading through rubble)
        but impassable by vehicles.
        """
        _vehicle_passable: dict[TerrainType, bool] = {
            TerrainType.OPEN: True,
            TerrainType.ROAD: True,
            TerrainType.GRASS: True,
            TerrainType.WOODS: False,
            TerrainType.BUILDING_ENTERABLE: False,
            TerrainType.BUILDING_SOLID: False,
            TerrainType.WATER: False,
            TerrainType.HEDGE: False,
            TerrainType.WALL: False,
            TerrainType.ROUGH: True,
            TerrainType.SHALLOW: False,
            TerrainType.BRIDGE: True,
            TerrainType.CRATER: False,
            TerrainType.SWAMP: False,
            TerrainType.BRIDGE_DESTROYED: False,
            TerrainType.FOXHOLE: True,
            TerrainType.TRENCH: True,
            TerrainType.MUD: False,
            TerrainType.SAND: True,
            TerrainType.SNOW: True,
            TerrainType.WIRE: False,
            TerrainType.BUNKER: False,
        }
        return _vehicle_passable[self]

    @property
    def cover_type(self) -> CoverType:
        """Classify terrain cover as NONE, SOFT, HARD, or HYBRID."""
        _cover_types: dict[TerrainType, CoverType] = {
            TerrainType.OPEN: CoverType.NONE,
            TerrainType.ROAD: CoverType.NONE,
            TerrainType.GRASS: CoverType.SOFT,
            TerrainType.WOODS: CoverType.SOFT,
            TerrainType.BUILDING_ENTERABLE: CoverType.HYBRID,
            TerrainType.BUILDING_SOLID: CoverType.HARD,
            TerrainType.WATER: CoverType.NONE,
            TerrainType.HEDGE: CoverType.SOFT,
            TerrainType.WALL: CoverType.HARD,
            TerrainType.ROUGH: CoverType.SOFT,
            TerrainType.SHALLOW: CoverType.NONE,
            TerrainType.BRIDGE: CoverType.NONE,
            TerrainType.CRATER: CoverType.SOFT,
            TerrainType.SWAMP: CoverType.SOFT,
            TerrainType.BRIDGE_DESTROYED: CoverType.NONE,
            TerrainType.FOXHOLE: CoverType.SOFT,
            TerrainType.TRENCH: CoverType.SOFT,
            TerrainType.MUD: CoverType.NONE,
            TerrainType.SAND: CoverType.NONE,
            TerrainType.SNOW: CoverType.SOFT,
            TerrainType.WIRE: CoverType.SOFT,
            TerrainType.BUNKER: CoverType.HARD,
        }
        return _cover_types[self]


def get_movement_cost(terrain: TerrainType) -> float:
    return terrain.movement_cost
