"""CC2 special building renderers (church + wall + barn + interior view).

提取自原 cc2_building_renderer.py（D11 SRP 拆分）。
非住宅特殊建筑:
- _render_church: 教堂（TOP-DOWN VIEW，十字架 + 彩色玻璃）
- _render_wall: 石墙（TOP-DOWN VIEW，薄矩形 + 石块图案）
- _render_barn: 标准谷仓（TOP-DOWN VIEW，干草门 + 阴影条）
- _render_building_interior: 室内视图（单位进入建筑时切换，地板 + 窗户 + 占据者标记）
"""

import math
import random

import pygame

from pycc2.presentation.rendering.cc2_building_common import (
    CC2_ROOF_COLORS,
    CC2BuildingType,
    DamageLevel,
    _deterministic_seed,
)


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
