"""Natural terrain tile generators (grass / woods / water / shallow / swamp / mud / sand / snow / rough / open).

Extracted from terrain_tile_generator.py during Phase 2 P0-1 large file split (2026-07-04).
Each function returns a PixelCanvas. Functions are stateless and can be called directly.
"""

from __future__ import annotations

import math
import random

from pycc2.presentation.rendering.pixel_canvas import (
    CCPalette,
    PixelCanvas,
    add_noise,
)


def generate_grass(size: int, variant: int = 0) -> PixelCanvas:
    """Generate grass tile — CC2 style: dark military green + subtle texture + rare dirt specks."""
    c = PixelCanvas(size, size)

    base = CCPalette.GRASS_LIGHT.value if variant % 2 == 0 else CCPalette.GRASS_DARK.value
    dark = CCPalette.GRASS_DARK.value
    dirt = CCPalette.DIRT.value

    # Base fill with subtle per-pixel random variation (reduced range for less contrast)
    import numpy as np

    c.fill_rect(0, 0, size, size, base)
    rng = random.Random(123 + variant)
    region = c._pixels.astype(np.int16)
    np_rng = np.random.RandomState(123 + variant)
    noise = np_rng.randint(
        -8, 10, size=(size, size), dtype=np.int16
    )  # Reduced from -12~14 to -8~10
    for ch in range(3):
        region[:, :, ch] = np.clip(region[:, :, ch] + noise, 0, 255)
    c._pixels = region.astype(np.uint8)

    # Scattered grass blade pixels (smaller, more scattered, 1px wide, 1-2px tall)
    grass_blade_count = max(18, size * size // 20)  # Reduced count for subtlety
    blade_shades = [
        dark,
        (max(0, dark[0] - 8), max(0, dark[1] + 12), max(0, dark[2] - 4)),
        (min(255, base[0] + 6), min(255, base[1] + 5), min(255, base[2] + 3)),
    ]
    for _ in range(grass_blade_count):
        gx = rng.randint(1, size - 2)
        gy = rng.randint(1, size - 3)
        blade_len = rng.randint(1, 2)  # Shorter blades (1-2px instead of 2-3px)
        blade_color = blade_shades[rng.randint(0, len(blade_shades) - 1)]
        shade_var = rng.randint(-4, 4)  # Reduced variation
        blade_color = (
            max(0, min(255, blade_color[0] + shade_var)),
            max(0, min(255, blade_color[1] + shade_var)),
            max(0, min(255, blade_color[2] + shade_var)),
        )
        for dy in range(blade_len):
            if 0 <= gy + dy < size:
                c.set_pixel(gx, gy + dy, blade_color)

    # Rare 1px brown/dirt specks for realism (very sparse)
    dirt_speck_count = max(2, size // 16)  # Very rare: only a few specks per tile
    for _ in range(dirt_speck_count):
        dx = rng.randint(1, size - 2)
        dy = rng.randint(1, size - 2)
        dirt_var = rng.randint(-8, 8)
        speck_color = (
            max(0, min(255, dirt[0] + dirt_var - 15)),  # Slightly darker dirt
            max(0, min(255, dirt[1] + dirt_var - 10)),
            max(0, min(255, dirt[2] + dirt_var - 5)),
        )
        c.set_pixel(dx, dy, speck_color)

    # Smaller, more subtle brown dirt patches (2x2 instead of 3x3, less frequent)
    dirt_count = max(2, size // 16)  # Reduced from size//12
    for _ in range(dirt_count):
        dx = rng.randint(2, size - 4)
        dy = rng.randint(2, size - 4)
        dirt_var = rng.randint(-8, 8)  # Reduced variation
        patch_color = (
            max(0, min(255, dirt[0] + dirt_var)),
            max(0, min(255, dirt[1] + dirt_var)),
            max(0, min(255, dirt[2] + dirt_var)),
        )
        for py in range(2):  # 2x2 instead of 3x3
            for px in range(2):
                if 0 <= dx + px < size and 0 <= dy + py < size and rng.random() > 0.35:
                    c.set_pixel(dx + px, dy + py, patch_color)

    # Subtle edge darkening
    edge_color = tuple(max(0, v - 15) for v in base)  # Softer edge
    for i in range(max(1, size // 20)):  # Thinner edge
        c.draw_outline_rect(i, i, size - i * 2, size - i * 2, edge_color, 1)

    add_noise(c, intensity=4)  # Reduced noise for cleaner look
    return c


def generate_woods(size: int, density: str = "medium") -> PixelCanvas:
    """Generate woods tile."""
    c = PixelCanvas(size, size)

    c.fill_rect(0, 0, size, size, CCPalette.GRASS_DARK.value)

    trunk_color = CCPalette.WOOD_TRUNK.value
    leaf_dark = CCPalette.WOOD_LEAF_DARK.value
    leaf_light = CCPalette.WOOD_LEAF_LIGHT.value
    leaf_mid = CCPalette.TREE_CROWN_MID.value  # A4: 新增中间色调

    if density == "light":
        trees = [(size // 4, size // 3, size // 5), (size * 3 // 4, size * 2 // 3, size // 6)]
    elif density == "dense":
        trees = [
            (size // 5, size // 4, size // 4),
            (size * 2 // 5, size // 5, size // 5),
            (size * 3 // 5, size * 3 // 5, size // 4),
            (size * 4 // 5, size * 2 // 3, size // 5),
            (size // 2, size * 3 // 4, size // 6),
        ]
    else:
        trees = [(size // 4, size // 3, size // 4), (size * 3 // 4, size * 2 // 3, size // 5)]

    for tx, ty, tr in trees:
        tw = max(3, tr // 5)
        th = max(6, tr // 3)
        c.fill_rect(tx - tw // 2, ty + tr // 2, tw, th, trunk_color)
        c.draw_line(
            tx - tw // 2,
            ty + tr // 2,
            tx - tw // 2,
            ty + tr // 2 + th,
            tuple(max(0, v - 20) for v in trunk_color),
            1,
        )

        layers = 4  # A4: 从3层增加到4层增强层次感
        for layer in range(layers):
            lr = tr - layer * (tr // 7)
            ly_offset = -layer * (tr // 9)
            # A4: 使用3种色调循环 (dark → mid → light → mid)
            if layer % 3 == 0:
                lc = leaf_dark
            elif layer % 3 == 1:
                lc = leaf_mid
            else:
                lc = leaf_light
            c.fill_circle(tx, ty + ly_offset, lr, lc)
            hl_r = lr // 2
            c.fill_circle(
                tx - lr // 4,
                ty + ly_offset - lr // 4,
                hl_r,
                tuple(min(255, v + 35) for v in lc),
            )
            sh_r = lr // 3
            c.fill_circle(
                tx + lr // 4,
                ty + ly_offset + lr // 4,
                sh_r,
                tuple(max(0, v - 25) for v in lc),
            )

    for tx, ty, tr in trees:
        shadow_r = tr // 2
        shadow_y = ty + tr // 2 + max(6, tr // 3)
        c.fill_circle(tx, shadow_y, shadow_r, (40, 55, 30))

    # Small circular clusters of dark green dots (canopy/underbrush texture)
    canopy_rng = random.Random(88)
    cluster_count = max(8, size // 4)
    for _ in range(cluster_count):
        cx = canopy_rng.randint(3, size - 4)
        cy = canopy_rng.randint(3, size - 4)
        cluster_r = canopy_rng.randint(2, 4)
        dot_count = canopy_rng.randint(3, 6)
        for _ in range(dot_count):
            dx = cx + canopy_rng.randint(-cluster_r, cluster_r)
            dy = cy + canopy_rng.randint(-cluster_r, cluster_r)
            if 0 <= dx < size and 0 <= dy < size:
                shade = canopy_rng.randint(-15, 15)
                dot_color = (
                    max(0, min(255, leaf_dark[0] + shade)),
                    max(0, min(255, leaf_dark[1] + shade)),
                    max(0, min(255, leaf_dark[2] + shade)),
                )
                c.set_pixel(dx, dy, dot_color)

    add_noise(c, intensity=5)
    return c


def generate_water(
    size: int, tile_x: int = 0, tile_y: int = 0, neighbors: dict | None = None
) -> PixelCanvas:
    """Generate water tile — enhanced: dark blue-green base + organic ripples + rare white glints.

    CC2-style water features:
    - Base color: dark blue-green (35, 70, 120) instead of bright blue
    - Overall brightness reduced 25% for deep water feel
    - Semi-transparent effect (alpha=170)
    - Organic ripples: sine waves with varying frequency, not regular stripes
    - Rare white glints: only 2-3 per tile, 1-2px size

    Args:
        size: tile size
        tile_x: tile world X coordinate (for ripple phase alignment)
        tile_y: tile world Y coordinate (for ripple phase alignment)
        neighbors: neighbor info dict, keys are "north"/"east"/"south"/"west",
                   values are True (water neighbor) or False (non-water neighbor)

    """
    if neighbors is None:
        neighbors = {}
    c = PixelCanvas(size, size)

    # *** 暗蓝绿色基底 (替代原来的亮蓝色) ***
    base = (35, 70, 120)  # DARK blue-green, not bright swimming pool blue
    c.fill_rect(0, 0, size, size, base)

    rng = random.Random(44)

    has_n = neighbors.get("north", False)
    has_e = neighbors.get("east", False)
    has_s = neighbors.get("south", False)
    has_w = neighbors.get("west", False)

    # *** 降低亮度25%的水面纹理 ***
    water_light = tuple(min(255, int(v * 0.88)) for v in base)  # 比基底稍亮12% (总降25%)
    water_dark = tuple(max(0, int(v * 0.85)) for v in base)  # 比基底暗15%

    # *** 有机波纹模式 (正弦波 + 变化频率，非规则条纹) ***
    for y in range(size):
        for x in range(size):
            # 使用复合正弦波创建有机波纹
            wave1 = math.sin((x + tile_x * size) * 0.15 + tile_y * 0.3)
            wave2 = math.sin((y + tile_y * size) * 0.12 + tile_x * 0.25)
            wave3 = math.sin(((x + y) + (tile_x + tile_y) * size) * 0.08)

            # 组合波形 (加权平均)
            combined_wave = wave1 * 0.4 + wave2 * 0.35 + wave3 * 0.25

            # 根据波相位选择颜色
            if combined_wave > 0.15:
                row_color = water_light
            elif combined_wave < -0.15:
                row_color = water_dark
            else:
                row_color = base

            # 添加微小随机变化
            var = rng.randint(-4, 4)
            px_color = (
                max(0, min(255, row_color[0] + var)),
                max(0, min(255, row_color[1] + var)),
                max(0, min(255, row_color[2] + var)),
            )
            c.set_pixel(x, y, px_color)

    # *** 增强有机波纹线条 (多条不同频率的正弦波) ***
    wave_phase_base = (tile_x * size) * 0.3
    for _wave_idx in range(max(6, size // 8)):  # 减少波纹线条数量
        wy_base = rng.randint(2, size - 3)
        wx_start = rng.randint(0, size // 4)
        ww = rng.randint(size // 4, size // 2)
        wave_color = tuple(min(255, base[i] + rng.randint(10, 22)) for i in range(3))
        wave_amp = rng.randint(1, 2)
        # 变化频率 (每次都不同)
        wave_freq = rng.uniform(0.2, 0.7)  # 更宽的频率范围
        wave_phase = wave_phase_base + rng.uniform(0, 2 * math.pi)
        for x in range(wx_start, min(size, wx_start + ww)):
            wy = wy_base + int(wave_amp * math.sin(wave_freq * (x + tile_x * size) + wave_phase))
            if 0 <= wy < size:
                c.set_pixel(x, wy, wave_color)

    # *** 稀有白色闪光点 (仅2-3个/tile，非常稀少) ***
    glint_count = 3  # 固定2-3个闪光点（原来太多）
    for _ in range(glint_count):
        gx = rng.randint(3, size - 4)
        gy = rng.randint(3, size - 4)
        # 1-2px 大小的白色闪光
        c.set_pixel(gx, gy, (240, 248, 255))  # 微蓝白色
        if rng.random() > 0.5:
            # 50%概率扩展到2px
            c.set_pixel(gx + 1, gy, (240, 248, 255))

    # *** 岸边渐变处理 ***
    bank_color = CCPalette.WATER_FOAM.value
    bank_dark = tuple(max(0, v - 30) for v in base)
    bank_width = max(3, size // 10)
    if not has_n:
        for y in range(bank_width):
            gradient = y / bank_width
            for x in range(size):
                existing = c.get_pixel(x, y)
                blended = (
                    max(0, int(bank_dark[0] * (1 - gradient) + existing[0] * gradient)),
                    max(0, int(bank_dark[1] * (1 - gradient) + existing[1] * gradient)),
                    max(0, int(bank_dark[2] * (1 - gradient) + existing[2] * gradient)),
                )
                c.set_pixel(x, y, blended)
        for x in range(0, size, 2):
            c.set_pixel(x, 0, bank_color)
    if not has_s:
        for y in range(bank_width):
            gradient = y / bank_width
            for x in range(size):
                existing = c.get_pixel(x, size - 1 - y)
                blended = (
                    max(0, int(bank_dark[0] * (1 - gradient) + existing[0] * gradient)),
                    max(0, int(bank_dark[1] * (1 - gradient) + existing[1] * gradient)),
                    max(0, int(bank_dark[2] * (1 - gradient) + existing[2] * gradient)),
                )
                c.set_pixel(x, size - 1 - y, blended)
        for x in range(0, size, 2):
            c.set_pixel(x, size - 1, bank_color)
    if not has_w:
        for x in range(bank_width):
            gradient = x / bank_width
            for y in range(size):
                existing = c.get_pixel(x, y)
                blended = (
                    max(0, int(bank_dark[0] * (1 - gradient) + existing[0] * gradient)),
                    max(0, int(bank_dark[1] * (1 - gradient) + existing[1] * gradient)),
                    max(0, int(bank_dark[2] * (1 - gradient) + existing[2] * gradient)),
                )
                c.set_pixel(x, y, blended)
        for y in range(0, size, 2):
            c.set_pixel(0, y, bank_color)
    if not has_e:
        for x in range(bank_width):
            gradient = x / bank_width
            for y in range(size):
                existing = c.get_pixel(size - 1 - x, y)
                blended = (
                    max(0, int(bank_dark[0] * (1 - gradient) + existing[0] * gradient)),
                    max(0, int(bank_dark[1] * (1 - gradient) + existing[1] * gradient)),
                    max(0, int(bank_dark[2] * (1 - gradient) + existing[2] * gradient)),
                )
                c.set_pixel(size - 1 - x, y, blended)
        for y in range(0, size, 2):
            c.set_pixel(size - 1, y, bank_color)

    add_noise(c, intensity=3)

    # *** 移除旧的spark代码，已整合到上面的glint中 ***

    # *** 半透明设置 (alpha = 170) ***
    c._pixels[:, :, 3] = 170
    return c


def generate_open(size: int) -> PixelCanvas:
    """Generate open ground tile."""
    return generate_grass(size, variant=1)


def generate_shallow(size: int) -> PixelCanvas:
    """Generate shallow water tile."""
    c = generate_grass(size, variant=2)
    water = CCPalette.WATER.value
    rng = random.Random(33)
    for _ in range(max(5, size // 8)):
        wx = rng.randint(2, size - 3)
        wy = rng.randint(2, size - 3)
        wr = rng.randint(3, max(5, size // 10))
        shallow_color = tuple(
            int(water[i] * 0.5 + CCPalette.GRASS_LIGHT.value[i] * 0.5) for i in range(3)
        )
        c.fill_circle(wx, wy, wr, shallow_color)
    return c


def generate_rough(size: int) -> PixelCanvas:
    """Generate rough terrain tile."""
    c = generate_grass(size, variant=3)
    rough_color = (160, 140, 90)
    rng = random.Random(66)
    for _ in range(max(8, size // 6)):
        rx = rng.randint(2, size - 3)
        ry = rng.randint(2, size - 3)
        rr = rng.randint(2, max(4, size // 12))
        c.fill_circle(rx, ry, rr, rough_color)
    add_noise(c, intensity=12)
    return c


def generate_swamp(size: int, variant: int = 0) -> PixelCanvas:
    """Generate swamp."""
    c = PixelCanvas(size, size, bg=(60, 80, 50))
    rng = random.Random(variant * 199 + 7)

    for _ in range(size // 2):
        wx = rng.randint(1, size - 2)
        wy = rng.randint(1, size - 2)
        wr = rng.randint(1, 3)
        shade = rng.randint(40, 65)
        g = rng.randint(55, 80)
        c.fill_circle(wx, wy, wr, (shade, g, shade - 15))

    for _ in range(size // 3):
        tx = rng.randint(0, size - 1)
        ty = rng.randint(0, size - 1)
        th = rng.randint(2, 4)
        for i in range(th):
            offset = rng.randint(-1, 1)
            gc = rng.randint(25, 55)
            if 0 <= ty + i < size and 0 <= tx + offset < size:
                c.set_pixel(tx + offset, ty + i, (gc, gc + 30, gc))

    for _ in range(3):
        bx = rng.randint(3, size - 4)
        by = rng.randint(3, size - 4)
        c.set_pixel(bx, by, (80, 100, 70))
        c.set_pixel(bx + 1, by, (75, 95, 65))

    return c


def generate_mud(size: int, variant: int = 0) -> PixelCanvas:
    """Generate mud."""
    c = PixelCanvas(size, size, bg=(90, 70, 45))
    rng = random.Random(variant * 211 + 13)

    wet_dark = (65, 50, 32)
    dry_light = (110, 88, 58)
    highlight = (130, 105, 70)

    for _ in range(size * size // 8):
        mx = rng.randint(0, size - 1)
        my = rng.randint(0, size - 1)
        mr = rng.randint(1, max(2, size // 16))
        shade = rng.choice([wet_dark, dry_light])
        c.fill_circle(mx, my, mr, shade)

    for _ in range(size // 2):
        rx = rng.randint(1, size - 2)
        ry = rng.randint(1, size - 2)
        rw = rng.randint(2, max(3, size // 8))
        c.fill_rect(rx, ry, rw, 1, highlight)

    for _ in range(max(3, size // 8)):
        px = rng.randint(2, size - 3)
        py = rng.randint(2, size - 3)
        c.set_pixel(px, py, (50, 38, 25))
        if rng.random() > 0.5:
            c.set_pixel(px + 1, py, (50, 38, 25))

    add_noise(c, intensity=8)
    return c


def generate_sand(size: int, variant: int = 0) -> PixelCanvas:
    """Generate sand."""
    c = PixelCanvas(size, size, bg=(180, 165, 120))
    rng = random.Random(variant * 317 + 23)

    ripple_light = (195, 180, 135)
    ripple_dark = (160, 145, 100)
    grain_dark = (140, 125, 85)

    for i in range(max(4, size // 6)):
        ry = rng.randint(2, size - 3)
        rx_start = rng.randint(0, size // 4)
        rw = rng.randint(size // 4, size // 2)
        ripple_color = ripple_light if i % 2 == 0 else ripple_dark
        for x in range(rx_start, min(size, rx_start + rw)):
            wy = ry + int(0.5 * math.sin(0.3 * x + i))
            if 0 <= wy < size:
                c.set_pixel(x, wy, ripple_color)

    for _ in range(size * size // 6):
        gx = rng.randint(0, size - 1)
        gy = rng.randint(0, size - 1)
        var = rng.randint(-8, 8)
        grain_color = (
            max(0, min(255, grain_dark[0] + var)),
            max(0, min(255, grain_dark[1] + var)),
            max(0, min(255, grain_dark[2] + var)),
        )
        c.set_pixel(gx, gy, grain_color)

    add_noise(c, intensity=6)
    return c


def generate_snow(size: int, variant: int = 0) -> PixelCanvas:
    """Generate snow."""
    c = PixelCanvas(size, size, bg=(230, 235, 240))
    rng = random.Random(variant * 431 + 37)

    blue_shadow = (200, 210, 225)
    footprint_dark = (210, 218, 228)

    for _ in range(size // 3):
        sx = rng.randint(1, size - 3)
        sy = rng.randint(1, size - 3)
        sw = rng.randint(2, max(3, size // 10))
        sh = rng.randint(2, max(3, size // 10))
        c.fill_rect(sx, sy, sw, sh, blue_shadow)

    for _ in range(max(2, size // 10)):
        fx = rng.randint(3, size - 6)
        fy = rng.randint(3, size - 6)
        c.fill_ellipse(fx, fy, 2, 3, footprint_dark)
        c.fill_ellipse(fx + 4, fy + 1, 2, 3, footprint_dark)

    for _ in range(size * size // 20):
        sx = rng.randint(0, size - 1)
        sy = rng.randint(0, size - 1)
        var = rng.randint(-5, 5)
        sparkle = (
            max(0, min(255, 235 + var)),
            max(0, min(255, 240 + var)),
            max(0, min(255, 245 + var)),
        )
        c.set_pixel(sx, sy, sparkle)

    add_noise(c, intensity=3)
    return c
