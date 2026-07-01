"""CC2 building renderer shared constants, enums, and helpers.

提取自原 cc2_building_renderer.py（D11 SRP 拆分）。
本模块为 cc2_residential_renderer / cc2_normandy_renderer / cc2_special_renderer
提供共享的:
- DamageLevel 枚举（4 级损坏）
- CC2_ROOF_COLORS / CC2_ROOF_VARIANTS / ROOF_TRIM_COLOR / WALL_FACE_MULTIPLIER / ROOF_NUMBER_COLOR 常量
- _deterministic_seed 抗 PYTHONHASHSEED 随机种子
- _draw_pixel_digit 像素风格数字绘制
- get_building_size / floors_to_building_type / should_show_interior 辅助函数
"""

import hashlib
from enum import Enum

import pygame

from pycc2.domain.value_objects.building_data import CC2BuildingType


class DamageLevel(Enum):
    """建筑损坏等级枚举，从完好到摧毁共四级。"""

    INTACT = 0
    LIGHT_DAMAGE = 1
    HEAVY_DAMAGE = 2
    DESTROYED = 3


def _deterministic_seed(key: str) -> int:
    """Deterministic RNG seed, immune to PYTHONHASHSEED randomization.

    Python's built-in _deterministic_seed() is randomized per-process since Python 3.3+.
    Using _deterministic_seed() for seeding caused flaky tests because crack positions
    changed across process invocations. hashlib.sha256 is always deterministic.
    """
    return int(hashlib.sha256(key.encode()).hexdigest(), 16) % (2**32)


CC2_ROOF_COLORS = {
    CC2BuildingType.SMALL_HOUSE: (90, 95, 100),  # #5A5F64 grey-blue
    CC2BuildingType.MEDIUM_HOUSE: (80, 85, 92),  # Slightly darker grey-blue
    CC2BuildingType.LARGE_BUILDING: (70, 76, 84),  # Darker grey
    CC2BuildingType.BARN: (139, 96, 64),  # Brown (special building)
    CC2BuildingType.CHURCH: (200, 200, 200),  # White/grey
    CC2BuildingType.WALL: (112, 112, 112),  # Grey
    CC2BuildingType.NORMANDY_FARMHOUSE: (160, 42, 28),  # Red tile (Normandy special)
    CC2BuildingType.NORMANDY_BARN: (120, 75, 45),  # Brown wood (Normandy special)
}

# A2 Fix: 建筑颜色变体池（从CC2截图提取的5种主要屋顶色）
CC2_ROOF_VARIANTS = [
    (90, 95, 100),  # 灰蓝色 (默认)
    (140, 82, 45),  # 橙棕色 (常见于CC2城市)
    (150, 55, 38),  # 红橙色 (工厂/仓库)
    (65, 75, 95),  # 深蓝灰色 (大型建筑)
    (120, 115, 105),  # 暖灰色 (住宅区)
]

ROOF_TRIM_COLOR = (176, 128, 80)  # #B08050 orange-brown
WALL_FACE_MULTIPLIER = 0.55  # Wall is much darker than roof (not 0.7!)
ROOF_NUMBER_COLOR = (220, 200, 50)  # Yellow for floor count digits


def _draw_pixel_digit(
    surface: pygame.Surface,
    digit: int,
    cx: int,
    cy: int,
    size: int,
    color: tuple[int, int, int],
) -> None:
    """Draw a single pixel-style digit using pygame.draw.lines.

    Args:
        surface: Target surface to draw on.
        digit: Digit to draw (0-9).
        cx, cy: Center position of the digit.
        size: Base size of the digit (height=1 → small, height=3 → larger).
        color: RGB color tuple for the digit.

    """
    scale = max(1, size)
    thickness = max(1, scale // 3)

    pixel_patterns: dict[int, list[tuple[float, float, float, float]]] = {
        0: [
            (0, 0, 1, 0),
            (1, 0, 1, 2),
            (0, 2, 1, 2),
            (0, 0, 0, 2),
        ],
        1: [
            (0.5, 0, 0.5, 2),
        ],
        2: [
            (0, 0, 1, 0),
            (1, 0, 1, 1),
            (0, 1, 1, 1),
            (0, 1, 0, 2),
            (0, 2, 1, 2),
        ],
        3: [
            (0, 0, 1, 0),
            (1, 0, 1, 2),
            (0, 2, 1, 2),
            (0, 1, 1, 1),
        ],
        4: [
            (0, 0, 0, 1),
            (0, 1, 1, 1),
            (1, 0, 1, 2),
        ],
        5: [
            (1, 0, 0, 0),
            (0, 0, 0, 1),
            (0, 1, 1, 1),
            (1, 1, 1, 2),
            (0, 2, 1, 2),
        ],
        6: [
            (1, 0, 0, 0),
            (0, 0, 0, 2),
            (0, 2, 1, 2),
            (0, 1, 1, 1),
            (1, 1, 1, 2),
        ],
        7: [
            (0, 0, 1, 0),
            (1, 0, 1, 2),
        ],
        8: [
            (0, 0, 1, 0),
            (1, 0, 1, 2),
            (0, 2, 1, 2),
            (0, 0, 0, 2),
            (0, 1, 1, 1),
        ],
        9: [
            (0, 2, 1, 2),
            (1, 2, 1, 0),
            (1, 0, 0, 0),
            (0, 1, 1, 1),
        ],
    }

    if digit not in pixel_patterns:
        return

    pattern = pixel_patterns[digit]
    for x1, y1, x2, y2 in pattern:
        px1 = int(cx + (x1 - 0.5) * scale)
        py1 = int(cy + (y1 - 1) * scale)
        px2 = int(cx + (x2 - 0.5) * scale)
        py2 = int(cy + (y2 - 1) * scale)
        pygame.draw.line(surface, color, (px1, py1), (px2, py2), thickness)


def get_building_size(building_type: CC2BuildingType) -> tuple[int, int]:
    """Return (width_tiles, height_tiles) for a building type."""
    sizes = {
        CC2BuildingType.SMALL_HOUSE: (1, 1),
        CC2BuildingType.MEDIUM_HOUSE: (2, 2),
        CC2BuildingType.LARGE_BUILDING: (3, 3),
        CC2BuildingType.BARN: (2, 2),
        CC2BuildingType.CHURCH: (2, 2),
        CC2BuildingType.WALL: (1, 1),
        # 诺曼底建筑尺寸 - 基于历史建筑平面图
        CC2BuildingType.NORMANDY_FARMHOUSE: (2, 2),  # 标准农舍大小
        CC2BuildingType.NORMANDY_BARN: (2, 3),  # 长形谷仓 (更长!)
    }
    return sizes.get(building_type, (1, 1))


def floors_to_building_type(floors: int) -> CC2BuildingType:
    """Map floor count to building type automatically.

    Args:
        floors: Number of floors in the building

    Returns:
        Appropriate CC2BuildingType based on floor count

    """
    if floors <= 1:
        return CC2BuildingType.SMALL_HOUSE
    elif floors == 2:
        return CC2BuildingType.MEDIUM_HOUSE
    elif floors <= 4:
        return CC2BuildingType.LARGE_BUILDING
    else:
        return CC2BuildingType.LARGE_BUILDING


def should_show_interior(building_pos: tuple[int, int], units: list, tile_size: int = 48) -> bool:
    """Check if any unit is inside the building at the given tile position.

    When a unit occupies the same tile as a building, the building renderer
    should automatically switch to interior mode (showing floor + windows
    instead of roof). When all units leave, it switches back to roof mode.

    Args:
        building_pos: (x, y) tile coordinate of the building.
        units: List of unit objects (must have .position.tile_coord.x/y).
        tile_size: Tile size in pixels (unused, kept for API compatibility).

    Returns:
        True if any unit is inside the building tile.

    """
    for unit in units:
        if hasattr(unit, "position") and hasattr(unit.position, "tile_coord"):
            ux, uy = unit.position.tile_coord.x, unit.position.tile_coord.y
            bx, by = building_pos
            if ux == bx and uy == by:
                return True
    return False
