"""CC2-style oblique projection building renderer.

Renders buildings in CC2's authentic OBLIQUE projection view with:
- Roof plane (top surface with texture)
- South wall face (bottom edge, darker, 1-2px tall)
- East wall face (right edge, darker, 1-2px wide)
- Roof edge trim (orange-brown border)
This matches CC2 screenshot analysis exactly.
"""

import hashlib
import random
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


def render_cc2_building(
    building_type: CC2BuildingType,
    damage: DamageLevel = DamageLevel.INTACT,
    tile_size: int = 48,
    show_number: bool = False,
    number: str | None = None,
    interior_mode: bool = False,  # *** NEW: Interior mode (floor + windows) ***
    occupant_positions: list[tuple[int, int]] | None = None,  # *** NEW: Unit positions inside ***
    tile_x: int = 0,
    tile_y: int = 0,
) -> pygame.Surface:
    """Render a CC2-style building in orthographic top-down view.

    支持两种模式:
    1. **屋顶模式** (默认): 显示屋顶平面（单位在外部时）
    2. **室内模式** (interior_mode=True): 显示地板+窗户轮廓（单位进入时）

    CC2原版机制:
    - 单位进入建筑 → 切换到室内视图
    - 地板纹理 (棋盘格/木地板)
    - 窗户白线轮廓 (影响LOS和射击角度)
    - 反坦克炮等重型武器受窗户位置限制

    Args:
        building_type: Type of building (determines size/color).
        damage: Damage level (affects color/cracks).
        tile_size: Size of one tile in pixels (default 48).
        show_number: Whether to show floor count on roof.
        number: The floor count string to display (e.g., "1", "2", "3", "5").
        interior_mode: If True, render floor instead of roof (CC2 interior view).
        occupant_positions: List of (x,y) positions for units inside (for LOS visualization).

    Returns:
        A pygame.Surface with the building rendered in CC2 style.

    """
    tw, th = get_building_size(building_type)
    w = tw * tile_size
    h = th * tile_size
    surface = pygame.Surface((w, h), pygame.SRCALPHA)

    # *** 室内模式路径 (CC2 Interior View!) ***
    if interior_mode:
        return _render_building_interior(
            surface, w, h, tile_size, building_type, damage, occupant_positions or []
        )

    # *** 屋顶模式 (标准外观) - OBLIQUE PROJECTION ***
    # 诺曼底建筑特殊渲染路径
    if building_type == CC2BuildingType.NORMANDY_FARMHOUSE:
        return _render_normandy_farmhouse(surface, w, h, tile_size, damage, show_number, number)
    elif building_type == CC2BuildingType.NORMANDY_BARN:
        return _render_normandy_barn(surface, w, h, tile_size, damage, show_number, number)
    elif building_type == CC2BuildingType.CHURCH:
        return _render_church(surface, w, h, tile_size, damage, show_number, number)
    elif building_type == CC2BuildingType.WALL:
        return _render_wall(surface, w, h, tile_size, damage)
    elif building_type == CC2BuildingType.BARN:
        return _render_barn(surface, w, h, tile_size, damage, show_number, number)

    # 标准CC2建筑渲染（OBLIQUE PROJECTION!）
    roof_color: tuple[int, ...] = CC2_ROOF_COLORS[building_type]

    # A2 Fix: 为标准建筑应用颜色变体（基于位置hash实现多样性）
    if building_type in [
        CC2BuildingType.SMALL_HOUSE,
        CC2BuildingType.MEDIUM_HOUSE,
        CC2BuildingType.LARGE_BUILDING,
    ]:
        import random as _rnd

        variant_seed = _deterministic_seed(str((building_type.name, tile_x, tile_y)))
        variant_idx = _rnd.Random(variant_seed).randint(0, len(CC2_ROOF_VARIANTS) - 1)
        roof_color = CC2_ROOF_VARIANTS[variant_idx]

    if damage == DamageLevel.LIGHT_DAMAGE:
        roof_color = tuple(max(0, c - 20) for c in roof_color)
    elif damage == DamageLevel.HEAVY_DAMAGE:
        roof_color = tuple(max(0, c - 45) for c in roof_color)
    elif damage == DamageLevel.DESTROYED:
        roof_color = tuple(max(0, c - 70) for c in roof_color)

    # === OBLIQUE PROJECTION: Roof + South Wall + East Wall ===
    # CC2修正: 墙面几乎不可见，仅1-2px暗色边缘提示（非5px墙面！）
    wall_height = 2  # 从5减至2 - 微妙阴影提示
    wall_width = 2  # 从5减至2 - 微妙阴影提示
    wall_color = tuple(int(c * WALL_FACE_MULTIPLIER) for c in roof_color)

    # 1. Roof plane (main rectangle)
    roof_rect = (0, 0, w - wall_width, h - wall_height)
    pygame.draw.rect(surface, roof_color, roof_rect)

    # 2. Roof edge trim (orange-brown border, 1-2px)
    pygame.draw.rect(surface, ROOF_TRIM_COLOR, roof_rect, 2)

    # 3. Stipple texture on roof (~15% density)
    stipple_rng = random.Random(_deterministic_seed(str(building_type) + "stipple"))
    for _ in range((w * h) // 15):
        sx = stipple_rng.randint(2, w - wall_width - 3)
        sy = stipple_rng.randint(2, h - wall_height - 3)
        brightness_var = stipple_rng.choice([-15, +10, -8])
        stipple_color = tuple(max(0, min(255, c + brightness_var)) for c in roof_color)
        surface.set_at((sx, sy), stipple_color)

    # 4. Window dots (dark rectangles, 2-6 depending on size)
    window_color = tuple(int(c * 0.5) for c in roof_color)  # roof_color * 0.5
    win_rng = random.Random(_deterministic_seed(str(building_type) + "roof_windows"))
    if building_type in [CC2BuildingType.SMALL_HOUSE, CC2BuildingType.WALL]:
        num_windows = 2
    elif building_type in [CC2BuildingType.MEDIUM_HOUSE]:
        num_windows = 4
    elif building_type in [CC2BuildingType.LARGE_BUILDING]:
        num_windows = 6
    else:
        num_windows = win_rng.randint(3, 5)

    placed_windows = []
    if building_type == CC2BuildingType.MEDIUM_HOUSE and num_windows >= 4:
        margin = tile_size // 4
        corners = [
            (margin + 2, margin + 2),
            (w - wall_width - margin - 4, margin + 2),
            (margin + 2, h - wall_height - margin - 4),
            (w - wall_width - margin - 4, h - wall_height - margin - 4),
        ]
        for wx, wy in corners[:num_windows]:
            win_size = 2 if tw >= 2 else 3
            pygame.draw.rect(surface, window_color, (wx, wy, win_size, win_size))
            placed_windows.append((wx, wy))
    else:
        for _ in range(num_windows * 3):
            wx = win_rng.randint(4, w - wall_width - 5)
            wy = win_rng.randint(4, h - wall_height - 5)
            too_close = False
            for px, py in placed_windows:
                if abs(wx - px) < 5 and abs(wy - py) < 5:
                    too_close = True
                    break
            if not too_close:
                win_size = 2 if tw >= 2 else 3
                pygame.draw.rect(surface, window_color, (wx, wy, win_size, win_size))
                placed_windows.append((wx, wy))
                if len(placed_windows) >= num_windows:
                    break

    # 5. Building number (pixel digits at center, size proportional to floor count)
    if show_number and number:
        cx = (w - wall_width) // 2
        cy = (h - wall_height) // 2

        try:
            floor_value = int(number)
            digit_size = 6 + floor_value * 2  # height=1 → 8px, height=3 → 12px
        except (ValueError, TypeError):
            digit_size = 8

        for i, char in enumerate(str(number)):
            try:
                digit = int(char)
                offset_x = int((i - len(str(number)) / 2 + 0.5) * (digit_size + 2))
                _draw_pixel_digit(surface, digit, cx + offset_x, cy, digit_size, ROOF_NUMBER_COLOR)
            except ValueError:
                pass

    # 6. Chimney (some building types)
    chimney_rng = random.Random(_deterministic_seed(str(building_type) + "chimney"))
    should_have_chimney = building_type in [
        CC2BuildingType.SMALL_HOUSE,
        CC2BuildingType.MEDIUM_HOUSE,
        CC2BuildingType.NORMANDY_FARMHOUSE,
    ]
    if should_have_chimney and chimney_rng.random() > 0.3:
        chimney_w = max(6, tile_size // 7)
        chimney_h = max(8, tile_size // 5)
        chimney_x = w - wall_width - chimney_w - 5
        chimney_y = h // 4
        chimney_stone = (100, 95, 88)
        chimney_dark = (80, 75, 68)
        pygame.draw.rect(surface, chimney_stone, (chimney_x, chimney_y, chimney_w, chimney_h))
        pygame.draw.rect(
            surface, chimney_dark, (chimney_x + chimney_w - 1, chimney_y, 1, chimney_h)
        )
        pygame.draw.rect(
            surface, chimney_dark, (chimney_x, chimney_y + chimney_h - 1, chimney_w, 1)
        )

    # 7. South wall face (bottom strip, darker)
    south_wall_rect = (0, h - wall_height, w, wall_height)
    pygame.draw.rect(surface, wall_color, south_wall_rect)

    # 8. East wall face (right strip, darker)
    east_wall_rect = (w - wall_width, 0, wall_width, h)
    pygame.draw.rect(surface, wall_color, east_wall_rect)

    # 9. Corner pixel (darkest where walls meet)
    corner_color = tuple(int(c * WALL_FACE_MULTIPLIER * 0.85) for c in roof_color)
    surface.set_at((w - wall_width, h - wall_height), corner_color)

    if damage.value >= DamageLevel.LIGHT_DAMAGE.value:
        crack_color = (40, 36, 32)
        rng = random.Random(_deterministic_seed(str(building_type) + str(damage)))
        num_cracks = damage.value * 2
        for _ in range(num_cracks):
            x1 = rng.randint(5, w - 5)
            y1 = rng.randint(5, h - 5)
            x2 = x1 + rng.randint(-15, 15)
            y2 = y1 + rng.randint(-15, 15)
            pygame.draw.line(surface, crack_color, (x1, y1), (x2, y2), 1)
        if damage.value >= DamageLevel.HEAVY_DAMAGE.value:
            for _ in range(damage.value):
                hole_x = rng.randint(5, w - 10)
                hole_y = rng.randint(5, h - 10)
                hole_w = rng.randint(4, 8)
                hole_h = rng.randint(4, 8)
                pygame.draw.rect(surface, (0, 0, 0), (hole_x, hole_y, hole_w, hole_h))
        if damage == DamageLevel.DESTROYED:
            for _ in range(8):
                edge = rng.randint(0, 3)
                if edge == 0:
                    rx, ry = rng.randint(0, w), rng.randint(0, 3)
                elif edge == 1:
                    rx, ry = rng.randint(0, w), rng.randint(h - 4, h)
                elif edge == 2:
                    rx, ry = rng.randint(0, 3), rng.randint(0, h)
                else:
                    rx, ry = rng.randint(w - 4, w), rng.randint(0, h)
                pygame.draw.rect(surface, (50, 45, 40), (rx, ry, 2, 2))

    return surface


def _render_normandy_farmhouse(
    surface: pygame.Surface,
    w: int,
    h: int,
    tile_size: int,
    damage: DamageLevel,
    show_number: bool,
    number: str | None,
) -> pygame.Surface:
    """渲染诺曼底农舍 - CC2 OBLIQUE PROJECTION

    斜投影视角特征:
    - 屋顶平面（矩形，深红瓦片）
    - 南墙立面（底部5px暗色条）
    - 东墙立面（右侧5px暗色条）
    - 屋顶边缘装饰线（橙棕色）
    - 烟囱、天窗等细节
    """
    import math

    red_tile_roof: tuple[int, ...] = (160, 42, 28)
    red_tile_light = (185, 60, 45)
    red_tile_dark: tuple[int, ...] = (130, 32, 20)
    chimney_stone = (100, 95, 88)
    chimney_dark = (80, 75, 68)
    skylight_color = (50, 55, 65)

    if damage == DamageLevel.LIGHT_DAMAGE:
        red_tile_roof = tuple(max(0, c - 18) for c in red_tile_roof)
        red_tile_dark = tuple(max(0, c - 25) for c in red_tile_dark)
    elif damage == DamageLevel.HEAVY_DAMAGE:
        red_tile_roof = tuple(max(0, c - 40) for c in red_tile_roof)
        red_tile_dark = tuple(max(0, c - 50) for c in red_tile_dark)
    elif damage == DamageLevel.DESTROYED:
        red_tile_roof = tuple(max(0, c - 65) for c in red_tile_roof)
        red_tile_dark = tuple(max(0, c - 75) for c in red_tile_dark)

    # CC2修正: 墙面几乎不可见，仅1-2px暗色边缘提示
    wall_height = 2  # 从5减至2 - 微妙阴影提示
    wall_width = 2  # 从5减至2 - 微妙阴影提示
    wall_color = tuple(int(c * WALL_FACE_MULTIPLIER) for c in red_tile_roof)
    cx, cy = (w - wall_width) // 2, (h - wall_height) // 2

    # 1. Roof plane
    (0, 0, w - wall_width, h - wall_height)
    roof_margin = tile_size // 8
    inner_roof = (
        roof_margin,
        roof_margin,
        w - wall_width - 2 * roof_margin,
        h - wall_height - 2 * roof_margin,
    )
    pygame.draw.rect(surface, red_tile_roof, inner_roof)

    # 2. Roof edge trim
    pygame.draw.rect(surface, ROOF_TRIM_COLOR, inner_roof, 2)

    # 3. Roof texture (tile lines)
    tile_rng = random.Random(_deterministic_seed("normandy_rooftop_tiles"))
    for ty in range(inner_roof[1] + 4, inner_roof[1] + inner_roof[3] - 2, tile_rng.randint(4, 6)):
        pygame.draw.line(
            surface,
            red_tile_dark,
            (inner_roof[0] + 2, ty),
            (inner_roof[0] + inner_roof[2] - 2, ty),
            1,
        )
    for _ in range(tile_rng.randint(2, 4)):
        vx = tile_rng.randint(inner_roof[0] + 6, inner_roof[0] + inner_roof[2] - 6)
        pygame.draw.line(
            surface,
            red_tile_light,
            (vx, inner_roof[1] + 2),
            (vx, inner_roof[1] + inner_roof[3] - 2),
            1,
        )

    # 4. Ridge line
    ridge_y = cy
    ridge_color = tuple(max(0, c - 25) for c in red_tile_roof)
    pygame.draw.line(
        surface,
        ridge_color,
        (inner_roof[0] + 4, ridge_y),
        (inner_roof[0] + inner_roof[2] - 4, ridge_y),
        2,
    )

    # 5. Chimney
    chimney_w = max(8, tile_size // 5)
    chimney_h = max(12, tile_size // 4)
    chimney_x = cx + (w - wall_width) // 7
    chimney_y = cy - h // 6
    pygame.draw.rect(surface, chimney_stone, (chimney_x, chimney_y, chimney_w, chimney_h))
    pygame.draw.rect(surface, chimney_dark, (chimney_x + chimney_w - 1, chimney_y, 1, chimney_h))
    pygame.draw.rect(surface, chimney_dark, (chimney_x, chimney_y + chimney_h - 1, chimney_w, 1))
    pygame.draw.rect(surface, (115, 108, 100), (chimney_x - 1, chimney_y - 1, chimney_w + 2, 3), 1)

    # 6. Skylight (optional)
    if random.Random(_deterministic_seed("skylight")).random() > 0.4:
        sky_w = max(10, tile_size // 4)
        sky_h = max(8, tile_size // 5)
        sky_x = cx - (w - wall_width) // 5
        sky_y = cy + (h - wall_height) // 8
        pygame.draw.rect(surface, skylight_color, (sky_x, sky_y, sky_w, sky_h))
        pygame.draw.rect(surface, chimney_dark, (sky_x, sky_y, sky_w, sky_h), 1)

    # 7. Building number
    if show_number and number:
        font_size = min(w - wall_width, h - wall_height) // 2
        font = pygame.font.SysFont("arial", font_size, bold=True)
        text = font.render(number, True, (255, 215, 0))
        text_rect = text.get_rect(center=(cx, cy))
        surface.blit(text, text_rect)

    # 8. South wall face
    south_wall_rect = (0, h - wall_height, w, wall_height)
    pygame.draw.rect(surface, wall_color, south_wall_rect)

    # 9. East wall face
    east_wall_rect = (w - wall_width, 0, wall_width, h)
    pygame.draw.rect(surface, wall_color, east_wall_rect)

    # 10. Corner pixel
    corner_color = tuple(int(c * WALL_FACE_MULTIPLIER * 0.85) for c in red_tile_roof)
    surface.set_at((w - wall_width, h - wall_height), corner_color)

    if damage.value >= DamageLevel.LIGHT_DAMAGE.value:
        crack_color = (40, 36, 32)
        rng = random.Random(_deterministic_seed(str(damage) + "farmhouse"))
        num_cracks = damage.value * 3
        for _ in range(num_cracks):
            x1 = rng.randint(inner_roof[0] + 5, inner_roof[0] + inner_roof[2] - 5)
            y1 = rng.randint(inner_roof[1] + 5, inner_roof[1] + inner_roof[3] - 5)
            length = rng.randint(5, 15)
            angle = rng.uniform(0, 2 * math.pi)
            x2 = x1 + int(length * math.cos(angle))
            y2 = y1 + int(length * math.sin(angle))
            pygame.draw.line(surface, crack_color, (x1, y1), (x2, y2), 1)
        if damage.value >= DamageLevel.HEAVY_DAMAGE.value:
            for _ in range(damage.value):
                hole_x = rng.randint(inner_roof[0] + 8, inner_roof[0] + inner_roof[2] - 16)
                hole_y = rng.randint(inner_roof[1] + 8, inner_roof[1] + inner_roof[3] - 16)
                hole_w = rng.randint(8, 16)
                hole_h = rng.randint(8, 16)
                pygame.draw.rect(surface, (30, 28, 24), (hole_x, hole_y, hole_w, hole_h))

    return surface


def _render_normandy_barn(
    surface: pygame.Surface,
    w: int,
    h: int,
    tile_size: int,
    damage: DamageLevel,
    show_number: bool,
    number: str | None,
) -> pygame.Surface:
    """渲染诺曼底谷仓 - CC2正交顶部俯视 (TOP-DOWN VIEW!)

    *** 关键修正: 从伪3D侧视改为纯顶部俯视 ***
    CC2使用Orthographic Top-Down投影，谷仓显示为:
    - 屋顶平面（长矩形，不是三角形坡顶!）
    - 双开门（从上方看是两个并排矩形）
    - 通风口（屋顶小矩形）
    - 不显示侧面墙体!

    诺曼底谷仓历史特征（俯视角度）:
    - 长形屋顶 (2×3 tiles)
    - 棕色木质/金属屋顶 (#784B2D)
    - 大型双开门（一端）
    - 屋顶通风口
    """
    import math

    # 诺曼底谷仓调色板 - 屋顶为主色调
    barn_wood_roof: tuple[int, ...] = (120, 75, 45)  # 棕色木质屋顶 (主色!)
    barn_wood_light = (145, 95, 60)  # 屋顶高光
    barn_wood_dark: tuple[int, ...] = (95, 58, 33)  # 屋顶暗部（木板间隙）
    door_color = (90, 62, 38)  # 双开门棕色
    door_dark = (68, 46, 28)  # 门暗部/缝隙
    vent_color = (50, 52, 48)  # 通风口暗色

    # 应用损毁效果
    if damage == DamageLevel.LIGHT_DAMAGE:
        barn_wood_roof = tuple(max(0, c - 15) for c in barn_wood_roof)
        barn_wood_dark = tuple(max(0, c - 22) for c in barn_wood_dark)
    elif damage == DamageLevel.HEAVY_DAMAGE:
        barn_wood_roof = tuple(max(0, c - 35) for c in barn_wood_roof)
        barn_wood_dark = tuple(max(0, c - 42) for c in barn_wood_dark)
    elif damage == DamageLevel.DESTROYED:
        barn_wood_roof = tuple(max(0, c - 60) for c in barn_wood_roof)
        barn_wood_dark = tuple(max(0, c - 67) for c in barn_wood_dark)

    cx, cy = w // 2, h // 2

    # *** 1. 主屋顶平面 (长矩形 - TOP-DOWN VIEW!) ***
    roof_margin = tile_size // 8
    roof_rect = (roof_margin, roof_margin, w - 2 * roof_margin, h - 2 * roof_margin)
    pygame.draw.rect(surface, barn_wood_roof, roof_rect)

    # *** 2. 屋顶纹理 (木板线条 - 谷仓通常是纵向木板!) ***
    wood_rng = random.Random(_deterministic_seed("barn_wood_grain"))
    # 纵向木纹线（每隔5-8px一条）
    for wx in range(roof_margin + 5, w - roof_margin - 2, wood_rng.randint(5, 8)):
        pygame.draw.line(
            surface, barn_wood_dark, (wx, roof_margin + 2), (wx, h - roof_margin - 2), 1
        )
    # 偶尔的横向支撑梁
    for _ in range(wood_rng.randint(3, 5)):
        by = wood_rng.randint(roof_margin + 8, h - roof_margin - 8)
        pygame.draw.line(
            surface, barn_wood_light, (roof_margin + 2, by), (w - roof_margin - 2, by), 1
        )

    # *** 3. 屋脊线 (长形谷仓的中央隆起!) ***
    ridge_y = cy
    ridge_color = tuple(max(0, c - 20) for c in barn_wood_roof)
    pygame.draw.line(
        surface, ridge_color, (roof_margin + 4, ridge_y), (w - roof_margin - 4, ridge_y), 2
    )

    # *** 4. 双开门 (从上方看的两个并排矩形!) ***
    door_w = max(16, tile_size // 2.5)
    door_h = max(20, tile_size // 2.2)
    door_x = cx - door_w // 2
    door_y = h - roof_margin - door_h - 2  # 靠近底部（门在一端）

    # 左门扇
    pygame.draw.rect(surface, door_color, (door_x, door_y, door_w // 2 - 2, door_h))
    # 右门扇
    pygame.draw.rect(
        surface, door_color, (door_x + door_w // 2 + 2, door_y, door_w // 2 - 2, door_h)
    )
    # 门边框和中间缝
    pygame.draw.rect(surface, door_dark, (door_x, door_y, door_w, door_h), 1)
    pygame.draw.line(
        surface,
        door_dark,
        (door_x + door_w // 2, door_y),
        (door_x + door_w // 2, door_y + door_h),
        1,
    )

    # *** 5. 通风口 (屋顶小矩形 - 俯视可见!) ***
    vent_w = max(10, tile_size // 4)
    vent_h = max(6, tile_size // 7)
    vent_x = cx - vent_w // 2
    vent_y = roof_margin + tile_size // 6
    pygame.draw.rect(surface, vent_color, (vent_x, vent_y, vent_w, vent_h))
    pygame.draw.rect(surface, (40, 42, 38), (vent_x, vent_y, vent_w, vent_h), 1)

    # *** 6. 楼层数字 (如果启用) ***
    if show_number and number:
        font_size = min(w, h) // 2
        font = pygame.font.SysFont("arial", font_size, bold=True)
        text = font.render(number, True, (255, 215, 0))  # 金黄色数字
        text_rect = text.get_rect(center=(cx, cy))
        surface.blit(text, text_rect)

    # *** 7. 损坏效果 (屋顶破洞/木板缺失!) ***
    if damage.value >= DamageLevel.LIGHT_DAMAGE.value:
        crack_color = (42, 36, 30)
        rng = random.Random(_deterministic_seed(str(damage) + "barn"))
        num_cracks = damage.value * 3
        for _ in range(num_cracks):
            x1 = rng.randint(roof_margin + 5, w - roof_margin - 5)
            y1 = rng.randint(roof_margin + 5, h - roof_margin - 5)
            length = rng.randint(6, 18)
            angle = rng.uniform(0, 2 * math.pi)
            x2 = x1 + int(length * math.cos(angle))
            y2 = y1 + int(length * math.sin(angle))
            pygame.draw.line(surface, crack_color, (x1, y1), (x2, y2), 1)
        # 重度损坏: 木板缺失区域
        if damage.value >= DamageLevel.HEAVY_DAMAGE.value:
            for _ in range(damage.value):
                hole_x = rng.randint(roof_margin + 10, w - roof_margin - 20)
                hole_y = rng.randint(roof_margin + 10, h - roof_margin - 20)
                hole_w = rng.randint(12, 20)
                hole_h = rng.randint(10, 18)
                pygame.draw.rect(surface, (25, 22, 18), (hole_x, hole_y, hole_w, hole_h))

    # Shadow strips (consistent with standard building rendering, with gradient)
    shadow_base_color = tuple(int(c * 0.7) for c in barn_wood_roof)
    shadow_width = 4

    # South shadow (bottom, gradient: darker at outer edge)
    for i in range(shadow_width):
        gradient_factor = 1.0 - (i / shadow_width) * 0.4
        shadow_color = tuple(int(c * gradient_factor) for c in shadow_base_color)
        pygame.draw.line(
            surface, shadow_color, (0, h - shadow_width + i), (w, h - shadow_width + i), 1
        )

    # East shadow (right side, gradient: darker at outer edge)
    for i in range(shadow_width):
        gradient_factor = 1.0 - (i / shadow_width) * 0.4
        shadow_color = tuple(int(c * gradient_factor) for c in shadow_base_color)
        pygame.draw.line(
            surface, shadow_color, (w - shadow_width + i, 0), (w - shadow_width + i, h), 1
        )

    return surface


def _render_building_interior(
    surface: pygame.Surface,
    w: int,
    h: int,
    tile_size: int,
    building_type: CC2BuildingType,
    damage: DamageLevel,
    occupant_positions: list[tuple[int, int]],
) -> pygame.Surface:
    """Render building INTERIOR view (CC2-style floor + windows).

    *** 核心功能: CC2建筑内部系统 ***
    当单位进入建筑时，CC2切换到此视图:
    - 地板纹理（棋盘格或木地板）
    - 窗户白线轮廓（影响LOS和射击角度）
    - 墙壁暗色边框
    - 占据者位置标记

    CC2原版机制（基于截图分析）:
    - 反坦克炮等重型武器受窗户位置限制
    - 从窗户射出的攻击线有特定角度
    - 室内单位获得掩护加成
    """
    import math

    # === 调色板: 室内模式颜色 ===
    # 地板颜色（基于CC2截图中的棋盘格地板）
    floor_light = (180, 170, 155)  # 浅色木地板/石板
    floor_dark = (145, 135, 122)  # 深色木地板/石板（棋盘格交替!）
    floor_wood = (160, 120, 80)  # 纯木质地板（谷仓等）

    # 窗户和墙壁
    window_outline = (255, 255, 255)  # 白色窗户轮廓（CC2特征!）
    wall_color = (90, 85, 78)  # 内部墙壁暗色
    wall_thickness = max(3, tile_size // 10)

    # 门
    door_color = (100, 70, 45)  # 木门颜色

    # 占据者标记
    occupant_marker = (0, 200, 0)  # 绿色圆圈（表示单位位置）

    cx, _cy = w // 2, h // 2

    # === 1. 地板纹理（棋盘格/木地板）===
    check_size = max(8, tile_size // 5)  # 棋盘格大小

    # 根据建筑类型选择地板风格
    if building_type in [CC2BuildingType.NORMANDY_BARN, CC2BuildingType.BARN]:
        # 谷仓: 纯木质地板（纵向木板）
        surface.fill(floor_wood)
        wood_rng = random.Random(_deterministic_seed("interior_wood_floor"))
        for wx in range(check_size // 2, w, wood_rng.randint(6, 10)):
            pygame.draw.line(
                surface, tuple(max(0, c - 20) for c in floor_wood), (wx, 0), (wx, h), 1
            )
    else:
        # 其他建筑: 棋盘格地板（诺曼底房屋常见石板地）
        for gx in range(0, w, check_size):
            for gy in range(0, h, check_size):
                is_light = ((gx // check_size) + (gy // check_size)) % 2 == 0
                color = floor_light if is_light else floor_dark
                rect = pygame.Rect(gx, gy, min(check_size, w - gx), min(check_size, h - gy))
                pygame.draw.rect(surface, color, rect)

        # 地板缝隙线（增加真实感）
        seam_color = tuple(max(0, c - 25) for c in floor_dark)
        for sx in range(0, w, check_size):
            pygame.draw.line(surface, seam_color, (sx, 0), (sx, h), 1)
        for sy in range(0, h, check_size):
            pygame.draw.line(surface, seam_color, (0, sy), (w, sy), 1)

    # === 2. 墙壁边框（内部视角的墙壁）===
    pygame.draw.rect(surface, wall_color, (0, 0, w, wall_thickness))  # 上墙
    pygame.draw.rect(surface, wall_color, (0, h - wall_thickness, w, wall_thickness))  # 下墙
    pygame.draw.rect(surface, wall_color, (0, 0, wall_thickness, h))  # 左墙
    pygame.draw.rect(surface, wall_color, (w - wall_thickness, 0, wall_thickness, h))  # 右墙

    # === 3. 窗户白线轮廓（CC2核心特征！）===
    # 窗户数量根据建筑大小决定
    num_windows = max(1, (w * h) // (tile_size * tile_size * 2))
    window_w = max(12, tile_size // 3)
    window_h = max(8, tile_size // 5)

    win_rng = random.Random(_deterministic_seed(f"interior_windows_{building_type.name}"))
    for i in range(num_windows):
        # 窗户位置（分布在四周墙壁上）
        if i % 4 == 0:  # 上墙窗户
            wx = win_rng.randint(wall_thickness + 8, w - wall_thickness - window_w - 8)
            wy = wall_thickness + 2
        elif i % 4 == 1:  # 下墙窗户
            wx = win_rng.randint(wall_thickness + 8, w - wall_thickness - window_w - 8)
            wy = h - wall_thickness - window_h - 2
        elif i % 4 == 2:  # 左墙窗户
            wx = wall_thickness + 2
            wy = win_rng.randint(wall_thickness + 8, h - wall_thickness - window_h - 8)
        else:  # 右墙窗户
            wx = w - wall_thickness - window_w - 2
            wy = win_rng.randint(wall_thickness + 8, h - wall_thickness - window_h - 8)

        # 绘制白色窗户轮廓（CC2特征！）
        pygame.draw.rect(surface, window_outline, (wx, wy, window_w, window_h), 2)
        # 窗户玻璃（半透明深色）
        glass_color = (60, 70, 90, 180)
        pygame.draw.rect(surface, glass_color, (wx + 2, wy + 2, window_w - 4, window_h - 4))
        # 窗户十字框（有些窗户有的装饰）
        if win_rng.random() > 0.5:
            pygame.draw.line(
                surface,
                window_outline,
                (wx + window_w // 2, wy),
                (wx + window_w // 2, wy + window_h),
                1,
            )
            pygame.draw.line(
                surface,
                window_outline,
                (wx, wy + window_h // 2),
                (wx + window_w, wy + window_h // 2),
                1,
            )

    # === 4. 门的位置标记 ===
    door_w = max(14, tile_size // 3)
    door_h = max(20, tile_size // 2.2)
    door_x = cx - door_w // 2
    door_y = h - wall_thickness - door_h - 2

    pygame.draw.rect(surface, door_color, (door_x, door_y, door_w, door_h))
    pygame.draw.rect(
        surface, tuple(max(0, c - 30) for c in door_color), (door_x, door_y, door_w, door_h), 2
    )

    # === 5. 占据者位置标记（如果提供）===
    for ox, oy in occupant_positions:
        if 0 <= ox < w and 0 <= oy < h:
            # 绿色圆圈表示单位位置
            pygame.draw.circle(surface, occupant_marker, (ox, oy), 6, 2)
            # 小方向指示器
            pygame.draw.circle(surface, (0, 180, 0), (ox, oy), 3)

    # === 6. 损坏效果（室内损坏：地板裂缝/破洞）===
    if damage.value >= DamageLevel.LIGHT_DAMAGE.value:
        crack_color = (50, 45, 40)
        dmg_rng = random.Random(_deterministic_seed(f"interior_damage_{damage.value}"))
        num_cracks = damage.value * 4
        for _ in range(num_cracks):
            x1 = dmg_rng.randint(wall_thickness + 10, w - wall_thickness - 10)
            y1 = dmg_rng.randint(wall_thickness + 10, h - wall_thickness - 10)
            length = dmg_rng.randint(8, 20)
            angle = dmg_rng.uniform(0, 2 * math.pi)
            x2 = x1 + int(length * math.cos(angle))
            y2 = y1 + int(length * math.sin(angle))
            pygame.draw.line(surface, crack_color, (x1, y1), (x2, y2), 1)
        # 重度损坏: 地板破洞
        if damage.value >= DamageLevel.HEAVY_DAMAGE.value:
            for _ in range(damage.value):
                hx = dmg_rng.randint(wall_thickness + 15, w - wall_thickness - 25)
                hy = dmg_rng.randint(wall_thickness + 15, h - wall_thickness - 25)
                hw = dmg_rng.randint(15, 25)
                hh = dmg_rng.randint(15, 25)
                pygame.draw.rect(surface, (30, 28, 24), (hx, hy, hw, hh))
                # 破洞边缘
                pygame.draw.rect(surface, (60, 55, 48), (hx, hy, hw, hh), 2)

    return surface


def _render_church(
    surface: pygame.Surface,
    w: int,
    h: int,
    tile_size: int,
    damage: DamageLevel,
    show_number: bool,
    number: str | None,
) -> pygame.Surface:
    """渲染教堂 - CC2正交顶部俯视 (TOP-DOWN VIEW!)

    教堂特征（纯俯视角度）:
    - 矩形主体屋顶（无尖塔/三角形！俯视看不到尖塔侧面）
    - 屋顶中心小十字架符号 (2px)
    - 彩色玻璃: 4个彩色圆点 (蓝/红) 靠近十字架
    - 同标准建筑的阴影条
    - 损坏: 裂缝/破洞
    """
    import math

    church_roof: tuple[int, ...] = (200, 200, 200)
    church_roof_dark: tuple[int, ...] = (160, 160, 160)
    cross_color = (220, 200, 180)

    if damage == DamageLevel.LIGHT_DAMAGE:
        church_roof = tuple(max(0, c - 20) for c in church_roof)
        church_roof_dark = tuple(max(0, c - 25) for c in church_roof_dark)
    elif damage == DamageLevel.HEAVY_DAMAGE:
        church_roof = tuple(max(0, c - 45) for c in church_roof)
        church_roof_dark = tuple(max(0, c - 50) for c in church_roof_dark)
    elif damage == DamageLevel.DESTROYED:
        church_roof = tuple(max(0, c - 70) for c in church_roof)
        church_roof_dark = tuple(max(0, c - 75) for c in church_roof_dark)

    cx, cy = w // 2, h // 2

    roof_margin = tile_size // 8
    body_rect = (roof_margin, roof_margin, w - 2 * roof_margin, h - 2 * roof_margin)
    pygame.draw.rect(surface, church_roof, body_rect)

    tile_rng = random.Random(_deterministic_seed("church_roof_tiles"))
    for ty in range(body_rect[1] + 4, body_rect[1] + body_rect[3] - 2, tile_rng.randint(4, 6)):
        pygame.draw.line(
            surface,
            church_roof_dark,
            (body_rect[0] + 2, ty),
            (body_rect[0] + body_rect[2] - 2, ty),
            1,
        )

    ridge_y = cy
    ridge_color = tuple(max(0, c - 25) for c in church_roof)
    pygame.draw.line(
        surface,
        ridge_color,
        (body_rect[0] + 4, ridge_y),
        (body_rect[0] + body_rect[2] - 4, ridge_y),
        1,
    )

    pygame.draw.line(surface, cross_color, (cx, cy - 3), (cx, cy + 3), 2)
    pygame.draw.line(surface, cross_color, (cx - 2, cy - 1), (cx + 2, cy - 1), 2)

    dot_offset = max(6, tile_size // 5)
    stained_glass = [
        (cx - dot_offset, cy - dot_offset // 2, (60, 80, 160)),
        (cx + dot_offset, cy - dot_offset // 2, (160, 60, 60)),
        (cx - dot_offset, cy + dot_offset // 2, (160, 60, 60)),
        (cx + dot_offset, cy + dot_offset // 2, (60, 80, 160)),
    ]
    for dx, dy, color in stained_glass:
        pygame.draw.circle(surface, color, (dx, dy), 2)

    if show_number and number:
        font_size = min(w, h) // 2
        font = pygame.font.SysFont("arial", font_size, bold=True)
        text = font.render(number, True, (255, 215, 0))
        text_rect = text.get_rect(center=(cx, cy + tile_size // 4))
        surface.blit(text, text_rect)

    if damage.value >= DamageLevel.LIGHT_DAMAGE.value:
        crack_color = (40, 36, 32)
        rng = random.Random(_deterministic_seed(str(damage) + "church"))
        num_cracks = damage.value * 3
        for _ in range(num_cracks):
            x1 = rng.randint(roof_margin + 5, w - roof_margin - 5)
            y1 = rng.randint(roof_margin + 5, h - roof_margin - 5)
            length = rng.randint(5, 15)
            angle = rng.uniform(0, 2 * math.pi)
            x2 = x1 + int(length * math.cos(angle))
            y2 = y1 + int(length * math.sin(angle))
            pygame.draw.line(surface, crack_color, (x1, y1), (x2, y2), 1)
        if damage.value >= DamageLevel.HEAVY_DAMAGE.value:
            for _ in range(damage.value):
                hole_x = rng.randint(roof_margin + 8, w - roof_margin - 16)
                hole_y = rng.randint(roof_margin + 8, h - roof_margin - 16)
                hole_w = rng.randint(8, 16)
                hole_h = rng.randint(8, 16)
                pygame.draw.rect(surface, (0, 0, 0), (hole_x, hole_y, hole_w, hole_h))

    shadow_base_color = tuple(int(c * 0.7) for c in church_roof)
    shadow_width = 4

    # South shadow (bottom, gradient: darker at outer edge)
    for i in range(shadow_width):
        gradient_factor = 1.0 - (i / shadow_width) * 0.4
        shadow_color = tuple(int(c * gradient_factor) for c in shadow_base_color)
        pygame.draw.line(
            surface, shadow_color, (0, h - shadow_width + i), (w, h - shadow_width + i), 1
        )

    # East shadow (right side, gradient: darker at outer edge)
    for i in range(shadow_width):
        gradient_factor = 1.0 - (i / shadow_width) * 0.4
        shadow_color = tuple(int(c * gradient_factor) for c in shadow_base_color)
        pygame.draw.line(
            surface, shadow_color, (w - shadow_width + i, 0), (w - shadow_width + i, h), 1
        )

    return surface


def _render_wall(
    surface: pygame.Surface, w: int, h: int, tile_size: int, damage: DamageLevel
) -> pygame.Surface:
    """渲染石墙 - CC2正交顶部俯视 (TOP-DOWN VIEW!)

    石墙特征（纯俯视角度）:
    - 薄矩形 (width = 3px, length = tile width)
    - 石块图案: 交替亮暗段 (1-2px each)
    - 无侧面可见 — 只有墙顶面
    - 损坏: 墙线中的缺口
    """
    wall_stone: tuple[int, ...] = (112, 112, 112)
    wall_stone_light = (128, 128, 128)
    wall_stone_dark = (85, 85, 85)

    if damage == DamageLevel.LIGHT_DAMAGE:
        wall_stone = tuple(max(0, c - 15) for c in wall_stone)
    elif damage == DamageLevel.HEAVY_DAMAGE:
        wall_stone = tuple(max(0, c - 35) for c in wall_stone)
    elif damage == DamageLevel.DESTROYED:
        wall_stone = tuple(max(0, c - 55) for c in wall_stone)

    wall_thickness = 3
    wall_y = h // 2 - wall_thickness // 2

    rng_gaps = random.Random(_deterministic_seed(str(damage) + "wall_topdown"))
    gaps = []
    if damage.value >= DamageLevel.LIGHT_DAMAGE.value:
        for _ in range(damage.value):
            gap_x = rng_gaps.randint(4, w - 8)
            gap_w = rng_gaps.randint(4, 8)
            gaps.append((gap_x, gap_w))

    segments = []
    current_x = 0
    for gap_x, gap_w in sorted(gaps):
        if current_x < gap_x:
            segments.append((current_x, gap_x - current_x))
        current_x = gap_x + gap_w
    if current_x < w:
        segments.append((current_x, w - current_x))
    if not gaps:
        segments = [(0, w)]

    for seg_x, seg_w in segments:
        pygame.draw.rect(surface, wall_stone, (seg_x, wall_y, seg_w, wall_thickness))

    stone_rng = random.Random(_deterministic_seed("wall_stone_topdown"))
    for seg_x, seg_w in segments:
        sx = seg_x
        while sx < seg_x + seg_w:
            seg_len = stone_rng.randint(2, 4)
            is_light = stone_rng.random() > 0.5
            seg_color = wall_stone_light if is_light else wall_stone_dark
            seg_end = min(sx + seg_len, seg_x + seg_w)
            pygame.draw.line(surface, seg_color, (sx, wall_y), (seg_end, wall_y), 1)
            pygame.draw.line(
                surface,
                seg_color,
                (sx, wall_y + wall_thickness - 1),
                (seg_end, wall_y + wall_thickness - 1),
                1,
            )
            if sx > seg_x:
                pygame.draw.line(
                    surface, (90, 88, 82), (sx, wall_y), (sx, wall_y + wall_thickness), 1
                )
            sx = seg_end

    pygame.draw.line(surface, wall_stone_light, (0, wall_y), (w, wall_y), 1)

    if damage.value >= DamageLevel.LIGHT_DAMAGE.value:
        for gap_x, gap_w in sorted(gaps):
            for _ in range(rng_gaps.randint(2, 4)):
                rx = gap_x + rng_gaps.randint(-2, gap_w + 2)
                ry = wall_y + rng_gaps.randint(-3, wall_thickness + 3)
                if 0 <= rx < w and 0 <= ry < h:
                    pygame.draw.rect(surface, wall_stone_dark, (rx, ry, 1, 1))

    return surface


def _render_barn(
    surface: pygame.Surface,
    w: int,
    h: int,
    tile_size: int,
    damage: DamageLevel,
    show_number: bool,
    number: str | None,
) -> pygame.Surface:
    """渲染谷仓 - CC2正交顶部俯视 (TOP-DOWN VIEW!)

    谷仓特征（纯俯视角度）:
    - 较大矩形 + 棕色屋顶
    - 干草门 (一端较大的矩形)
    - 同标准建筑的阴影条
    """
    barn_roof: tuple[int, ...] = CC2_ROOF_COLORS[CC2BuildingType.BARN]

    if damage == DamageLevel.LIGHT_DAMAGE:
        barn_roof = tuple(max(0, c - 20) for c in barn_roof)
    elif damage == DamageLevel.HEAVY_DAMAGE:
        barn_roof = tuple(max(0, c - 45) for c in barn_roof)
    elif damage == DamageLevel.DESTROYED:
        barn_roof = tuple(max(0, c - 70) for c in barn_roof)

    surface.fill(barn_roof)

    ridge_color = tuple(max(0, c - 25) for c in barn_roof)
    pygame.draw.line(surface, ridge_color, (2, h // 2), (w - 2, h // 2), 1)

    hayloft_color = tuple(max(0, c - 30) for c in barn_roof)
    hayloft_w = max(8, w // 3)
    hayloft_h = max(6, h // 5)
    hayloft_x = w // 2 - hayloft_w // 2
    hayloft_y = h - hayloft_h - 2
    pygame.draw.rect(surface, hayloft_color, (hayloft_x, hayloft_y, hayloft_w, hayloft_h))
    pygame.draw.rect(
        surface,
        tuple(max(0, c - 40) for c in barn_roof),
        (hayloft_x, hayloft_y, hayloft_w, hayloft_h),
        1,
    )

    shadow_base_color = tuple(int(c * 0.7) for c in barn_roof)
    shadow_width = 4

    # South shadow (bottom, gradient: darker at outer edge)
    for i in range(shadow_width):
        gradient_factor = 1.0 - (i / shadow_width) * 0.4
        shadow_color = tuple(int(c * gradient_factor) for c in shadow_base_color)
        pygame.draw.line(
            surface, shadow_color, (0, h - shadow_width + i), (w, h - shadow_width + i), 1
        )

    # East shadow (right side, gradient: darker at outer edge)
    for i in range(shadow_width):
        gradient_factor = 1.0 - (i / shadow_width) * 0.4
        shadow_color = tuple(int(c * gradient_factor) for c in shadow_base_color)
        pygame.draw.line(
            surface, shadow_color, (w - shadow_width + i, 0), (w - shadow_width + i, h), 1
        )

    if show_number and number:
        font_size = min(w, h) // 2
        font = pygame.font.SysFont("arial", font_size, bold=True)
        text = font.render(number, True, (255, 215, 0))
        text_rect = text.get_rect(center=(w // 2, h // 2))
        surface.blit(text, text_rect)

    if damage.value >= DamageLevel.LIGHT_DAMAGE.value:
        crack_color = (40, 36, 32)
        rng = random.Random(_deterministic_seed(str(damage) + "barn"))
        num_cracks = damage.value * 2
        for _ in range(num_cracks):
            x1 = rng.randint(5, w - 5)
            y1 = rng.randint(5, h - 5)
            x2 = x1 + rng.randint(-15, 15)
            y2 = y1 + rng.randint(-15, 15)
            pygame.draw.line(surface, crack_color, (x1, y1), (x2, y2), 1)
        if damage.value >= DamageLevel.HEAVY_DAMAGE.value:
            for _ in range(damage.value):
                hole_x = rng.randint(5, w - 10)
                hole_y = rng.randint(5, h - 10)
                hole_w = rng.randint(4, 8)
                hole_h = rng.randint(4, 8)
                pygame.draw.rect(surface, (0, 0, 0), (hole_x, hole_y, hole_w, hole_h))

    return surface
