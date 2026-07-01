"""CC2 standard residential building renderer (render_cc2_building entry point).

提取自原 cc2_building_renderer.py（D11 SRP 拆分）。
本模块为对外公开入口 render_cc2_building 的实现：
- 标准住宅建筑（SMALL_HOUSE / MEDIUM_HOUSE / LARGE_BUILDING）的 OBLIQUE PROJECTION 渲染
- dispatch 至诺曼底/特殊建筑子模块
- 室内模式 dispatch 至 cc2_special_renderer._render_building_interior
"""

import random

import pygame

from pycc2.domain.value_objects.building_data import CC2BuildingType
from pycc2.presentation.rendering.cc2_building_common import (
    CC2_ROOF_COLORS,
    CC2_ROOF_VARIANTS,
    ROOF_NUMBER_COLOR,
    ROOF_TRIM_COLOR,
    WALL_FACE_MULTIPLIER,
    DamageLevel,
    _deterministic_seed,
    _draw_pixel_digit,
    get_building_size,
)
from pycc2.presentation.rendering.cc2_normandy_renderer import (
    _render_normandy_barn,
    _render_normandy_farmhouse,
)
from pycc2.presentation.rendering.cc2_special_renderer import (
    _render_barn,
    _render_building_interior,
    _render_church,
    _render_wall,
)


def render_cc2_building(
    building_type: CC2BuildingType,
    damage: DamageLevel = DamageLevel.INTACT,
    tile_size: int = 48,
    show_number: bool = False,
    number: str | None = None,
    interior_mode: bool = False,
    occupant_positions: list[tuple[int, int]] | None = None,
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
        tile_x: Tile x coordinate (for deterministic color variant selection).
        tile_y: Tile y coordinate (for deterministic color variant selection).

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
