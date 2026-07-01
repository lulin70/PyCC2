"""CC2 Normandy special building renderers (farmhouse + barn).

提取自原 cc2_building_renderer.py（D11 SRP 拆分）。
诺曼底战役专属建筑:
- _render_normandy_farmhouse: 红瓦农舍（OBLIQUE PROJECTION）
- _render_normandy_barn: 棕木谷仓（TOP-DOWN VIEW）
"""

import math
import random

import pygame

from pycc2.presentation.rendering.cc2_building_common import (
    ROOF_TRIM_COLOR,
    WALL_FACE_MULTIPLIER,
    DamageLevel,
    _deterministic_seed,
)


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
