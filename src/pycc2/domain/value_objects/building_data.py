"""Building domain data — types and window positions.

This module belongs to the Domain layer so that both domain systems
(LOS, GameMap) and presentation renderers can depend on it without
creating a Domain→Presentation coupling.
"""

from __future__ import annotations

from enum import Enum


class CC2BuildingType(Enum):
    """Building types matching CC2 - 包含诺曼底战役特有建筑风格."""

    SMALL_HOUSE = "small_house"
    MEDIUM_HOUSE = "medium_house"
    LARGE_BUILDING = "large_building"
    BARN = "barn"
    CHURCH = "church"
    WALL = "wall"
    # 诺曼底战役特有建筑类型 - 基于历史建筑学研究
    NORMANDY_FARMHOUSE = "normandy_farmhouse"  # 诺曼底农舍: 2x2, 陡峭红瓦屋顶, 石墙
    NORMANDY_BARN = "normandy_barn"  # 诺曼底谷仓: 2x3, 大型, 棕色双开门


# Window positions for each building type (relative to tile, used for firing arc restrictions)
# Each window has a 'wall' (cardinal direction it faces) and 'offset' (0.0-1.0 along that wall)
BUILDING_WINDOWS: dict[CC2BuildingType, list[dict]] = {
    CC2BuildingType.SMALL_HOUSE: [
        {"wall": "north", "offset": 0.5},
        {"wall": "south", "offset": 0.5},
        {"wall": "east", "offset": 0.5},
        {"wall": "west", "offset": 0.5},
    ],
    CC2BuildingType.MEDIUM_HOUSE: [
        {"wall": "north", "offset": 0.3},
        {"wall": "north", "offset": 0.7},
        {"wall": "south", "offset": 0.3},
        {"wall": "south", "offset": 0.7},
        {"wall": "east", "offset": 0.5},
        {"wall": "west", "offset": 0.5},
    ],
    CC2BuildingType.LARGE_BUILDING: [
        {"wall": "north", "offset": 0.2},
        {"wall": "north", "offset": 0.5},
        {"wall": "north", "offset": 0.8},
        {"wall": "south", "offset": 0.2},
        {"wall": "south", "offset": 0.5},
        {"wall": "south", "offset": 0.8},
        {"wall": "east", "offset": 0.3},
        {"wall": "east", "offset": 0.7},
        {"wall": "west", "offset": 0.3},
        {"wall": "west", "offset": 0.7},
    ],
    CC2BuildingType.BARN: [
        {"wall": "north", "offset": 0.5},
        {"wall": "south", "offset": 0.5},
        {"wall": "east", "offset": 0.3},
        {"wall": "east", "offset": 0.7},
        {"wall": "west", "offset": 0.3},
        {"wall": "west", "offset": 0.7},
    ],
    CC2BuildingType.CHURCH: [
        {"wall": "north", "offset": 0.5},
        {"wall": "south", "offset": 0.5},
        {"wall": "east", "offset": 0.3},
        {"wall": "east", "offset": 0.7},
        {"wall": "west", "offset": 0.3},
        {"wall": "west", "offset": 0.7},
    ],
    CC2BuildingType.WALL: [],
    CC2BuildingType.NORMANDY_FARMHOUSE: [
        {"wall": "north", "offset": 0.3},
        {"wall": "north", "offset": 0.7},
        {"wall": "south", "offset": 0.3},
        {"wall": "south", "offset": 0.7},
        {"wall": "east", "offset": 0.5},
        {"wall": "west", "offset": 0.5},
    ],
    CC2BuildingType.NORMANDY_BARN: [
        {"wall": "north", "offset": 0.5},
        {"wall": "south", "offset": 0.5},
        {"wall": "east", "offset": 0.3},
        {"wall": "east", "offset": 0.7},
        {"wall": "west", "offset": 0.3},
        {"wall": "west", "offset": 0.7},
    ],
}
