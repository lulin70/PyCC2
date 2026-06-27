"""Terrain tile generator producing CC2-style map tiles."""

from __future__ import annotations

import math
import random

from pycc2.presentation.rendering.pixel_canvas import (
    CCPalette,
    PixelCanvas,
    add_noise,
)

# ============================================================
# 5. 地形瓦片生成器
# ============================================================


class TerrainTileGenerator:
    """地形瓦片生成器 — 生成CC2风格的地形tile。

    特点：
    - 多层细节（基础色+纹理+高光+阴影）
    - 自然不规则感（不是完美的几何形状）
    - 可配置大小（32/48/64px自适应）
    """

    @staticmethod
    def generate_grass(size: int, variant: int = 0) -> PixelCanvas:
        """生成草地瓦片 — CC2风格: 暗军绿色+微妙纹理+稀有泥土颗粒"""
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

    @staticmethod
    def generate_road(
        size: int, orientation: str = "horizontal", neighbors: dict | None = None
    ) -> PixelCanvas:
        """生成道路瓦片 — 增强版: 碎石颗粒+裂缝纹理+跨瓦片连续性

        Args:
            size: 瓦片尺寸
            orientation: "horizontal" 或 "vertical"
            neighbors: 邻居信息字典, 键为 "north"/"east"/"south"/"west",
                       值为 True(道路邻居) 或 False(非道路邻居)

        """
        if neighbors is None:
            neighbors = {}
        c = PixelCanvas(size, size)

        c.fill_rect(0, 0, size, size, CCPalette.DIRT.value)

        road_color = CCPalette.ROAD.value
        road_margin = max(3, size // 10)

        has_n = neighbors.get("north", False)
        has_e = neighbors.get("east", False)
        has_s = neighbors.get("south", False)
        has_w = neighbors.get("west", False)

        if orientation == "horizontal":
            road_top = size // 2 - road_margin // 2
            road_bot = size // 2 + road_margin // 2
            if has_n:
                road_top = 0
            if has_s:
                road_bot = size
            road_h = road_bot - road_top
            c.fill_rect(0, road_top, size, road_h, road_color)
            if not has_n and road_h > 4:
                curb_y = road_top
                c.fill_rect(0, curb_y, size, 2, tuple(max(0, v - 25) for v in road_color))
            if not has_s and road_h > 4:
                curb_y = road_bot - 2
                c.fill_rect(0, curb_y, size, 2, tuple(max(0, v - 25) for v in road_color))
            if not has_w:
                for i in range(min(4, road_margin)):
                    alpha = i / 4
                    blended = tuple(
                        int(CCPalette.DIRT.value[j] * (1 - alpha) + road_color[j] * alpha)
                        for j in range(3)
                    )
                    for ry in range(road_top, road_bot):
                        c.set_pixel(i, ry, blended)
            if not has_e:
                for i in range(min(4, road_margin)):
                    alpha = i / 4
                    blended = tuple(
                        int(CCPalette.DIRT.value[j] * (1 - alpha) + road_color[j] * alpha)
                        for j in range(3)
                    )
                    for ry in range(road_top, road_bot):
                        c.set_pixel(size - 1 - i, ry, blended)
            rut_y1 = size // 2 - road_margin // 4
            rut_y2 = size // 2 + road_margin // 4
            rut_color = tuple(max(0, v - 20) for v in road_color)
            c.fill_rect(0, rut_y1, size, max(1, size // 32), rut_color)
            c.fill_rect(0, rut_y2, size, max(1, size // 32), rut_color)

            # *** 轮胎痕迹（两条平行暗线，略不规则）***
            tire_rng = random.Random(7777)
            tire_color = tuple(max(0, v - 30) for v in road_color)  # 比路面暗30
            tire_spacing = tire_rng.randint(4, 6)  # 轮胎间距(中心到中心) 4-6px
            tire_width = tire_rng.choice([1, 2])  # 轮胎宽度

            # 计算轮胎位置（相对于道路中心）
            center_y = (road_top + road_bot) // 2
            tire1_y = center_y - tire_spacing // 2
            tire2_y = center_y + tire_spacing // 2

            # 绘制左轮胎痕迹（带周期性随机偏移，每8-12px偏移一次）
            wobble_interval = tire_rng.randint(8, 12)
            current_offset = tire_rng.randint(-1, 1)
            for px in range(0, size):
                # 在道路边缘处,如果有邻居则延伸,否则逐渐消失
                if px < 4 and not has_w:
                    fade = px / 4
                    if tire_rng.random() > fade:
                        continue
                elif px >= size - 4 and not has_e:
                    fade = (size - 1 - px) / 4
                    if tire_rng.random() > fade:
                        continue

                # 每隔8-12px更新偏移量（模拟真实轮胎摆动）
                if px > 0 and px % wobble_interval == 0:
                    current_offset = tire_rng.randint(-1, 1)
                py = tire1_y + current_offset
                if road_top <= py < road_bot:
                    # 偶尔断开（模拟真实轮胎痕迹）
                    if tire_rng.random() > 0.05:  # 95%的概率绘制
                        for w in range(tire_width):
                            if 0 <= py + w < size:
                                c.set_pixel(px, py + w, tire_color)

            # 绘制右轮胎痕迹（带周期性随机偏移）
            wobble_interval = tire_rng.randint(8, 12)
            current_offset = tire_rng.randint(-1, 1)
            for px in range(0, size):
                if px < 4 and not has_w:
                    fade = px / 4
                    if tire_rng.random() > fade:
                        continue
                elif px >= size - 4 and not has_e:
                    fade = (size - 1 - px) / 4
                    if tire_rng.random() > fade:
                        continue

                if px > 0 and px % wobble_interval == 0:
                    current_offset = tire_rng.randint(-1, 1)
                py = tire2_y + current_offset
                if road_top <= py < road_bot and tire_rng.random() > 0.05:
                    for w in range(tire_width):
                        if 0 <= py + w < size:
                            c.set_pixel(px, py + w, tire_color)

            rng = random.Random(77)

            gravel_count = max(20, size * size // 10)
            if road_top <= road_bot - 1:
                for _ in range(gravel_count):
                    gx = rng.randint(1, size - 2)
                    gy = rng.randint(road_top, road_bot - 1)
                    bright_var = rng.randint(15, 35)
                    gravel_color = (
                        min(255, road_color[0] + bright_var),
                        min(255, road_color[1] + bright_var),
                        min(255, road_color[2] + bright_var),
                    )
                    c.set_pixel(gx, gy, gravel_color)

            dark_gravel_count = max(10, size * size // 20)
            if road_top <= road_bot - 1:
                for _ in range(dark_gravel_count):
                    gx = rng.randint(1, size - 2)
                    gy = rng.randint(road_top, road_bot - 1)
                    dark_var = rng.randint(10, 25)
                    if rng.random() > 0.5:
                        gravel_color = (
                            max(0, road_color[0] - dark_var),
                            max(0, road_color[1] - dark_var),
                            max(0, road_color[2] - dark_var),
                        )
                    else:
                        gray_tone = rng.randint(100, 140)
                        gravel_color = (gray_tone, gray_tone - 5, gray_tone - 10)
                    c.set_pixel(gx, gy, gravel_color)

            crack_count = max(3, size // 10)
            crack_lo = road_top + 1
            crack_hi = road_bot - 2
            if crack_lo <= crack_hi:
                for _ in range(crack_count):
                    cx = rng.randint(2, size - 8)
                    cy = rng.randint(crack_lo, crack_hi)
                    crack_len = rng.randint(4, 10)
                    crack_angle = rng.uniform(-0.4, 0.4)
                    crack_color = tuple(max(0, v - 30) for v in road_color)
                    for i in range(crack_len):
                        px = cx + i
                        py = cy + int(i * math.sin(crack_angle))
                        if 0 <= px < size and road_top <= py < road_bot:
                            c.set_pixel(px, py, crack_color)
        else:
            road_left = size // 2 - road_margin // 2
            road_right = size // 2 + road_margin // 2
            if has_w:
                road_left = 0
            if has_e:
                road_right = size
            road_w = road_right - road_left
            c.fill_rect(road_left, 0, road_w, size, road_color)
            if not has_w and road_w > 4:
                curb_x = road_left
                c.fill_rect(curb_x, 0, 2, size, tuple(max(0, v - 25) for v in road_color))
            if not has_e and road_w > 4:
                curb_x = road_right - 2
                c.fill_rect(curb_x, 0, 2, size, tuple(max(0, v - 25) for v in road_color))
            if not has_n:
                for i in range(min(4, road_margin)):
                    alpha = i / 4
                    blended = tuple(
                        int(CCPalette.DIRT.value[j] * (1 - alpha) + road_color[j] * alpha)
                        for j in range(3)
                    )
                    for rx in range(road_left, road_right):
                        c.set_pixel(rx, i, blended)
            if not has_s:
                for i in range(min(4, road_margin)):
                    alpha = i / 4
                    blended = tuple(
                        int(CCPalette.DIRT.value[j] * (1 - alpha) + road_color[j] * alpha)
                        for j in range(3)
                    )
                    for rx in range(road_left, road_right):
                        c.set_pixel(rx, size - 1 - i, blended)

            # *** 轮胎痕迹（两条平行暗线，略不规则）***
            tire_rng = random.Random(7778)
            tire_color = tuple(max(0, v - 30) for v in road_color)  # 比路面暗30
            tire_spacing = tire_rng.randint(4, 6)  # 轮胎间距(中心到中心) 4-6px
            tire_width = tire_rng.choice([1, 2])  # 轮胎宽度

            # 计算轮胎位置（相对于道路中心）
            center_x = (road_left + road_right) // 2
            tire1_x = center_x - tire_spacing // 2
            tire2_x = center_x + tire_spacing // 2

            # 绘制上轮胎痕迹（带周期性随机偏移，每8-12px偏移一次）
            wobble_interval = tire_rng.randint(8, 12)
            current_offset = tire_rng.randint(-1, 1)
            for py in range(0, size):
                if py < 4 and not has_n:
                    fade = py / 4
                    if tire_rng.random() > fade:
                        continue
                elif py >= size - 4 and not has_s:
                    fade = (size - 1 - py) / 4
                    if tire_rng.random() > fade:
                        continue

                # 每隔8-12px更新偏移量（模拟真实轮胎摆动）
                if py > 0 and py % wobble_interval == 0:
                    current_offset = tire_rng.randint(-1, 1)
                px = tire1_x + current_offset
                if road_left <= px < road_right and tire_rng.random() > 0.05:
                    for w in range(tire_width):
                        if 0 <= px + w < size:
                            c.set_pixel(px + w, py, tire_color)

            # 绘制下轮胎痕迹（带周期性随机偏移）
            wobble_interval = tire_rng.randint(8, 12)
            current_offset = tire_rng.randint(-1, 1)
            for py in range(0, size):
                if py < 4 and not has_n:
                    fade = py / 4
                    if tire_rng.random() > fade:
                        continue
                elif py >= size - 4 and not has_s:
                    fade = (size - 1 - py) / 4
                    if tire_rng.random() > fade:
                        continue

                if py > 0 and py % wobble_interval == 0:
                    current_offset = tire_rng.randint(-1, 1)
                px = tire2_x + current_offset
                if road_left <= px < road_right and tire_rng.random() > 0.05:
                    for w in range(tire_width):
                        if 0 <= px + w < size:
                            c.set_pixel(px + w, py, tire_color)

            rng = random.Random(77)
            gravel_count = max(20, size * size // 10)
            if road_left <= road_right - 1:
                for _ in range(gravel_count):
                    gx = rng.randint(road_left, road_right - 1)
                    gy = rng.randint(1, size - 2)
                    bright_var = rng.randint(15, 35)
                    gravel_color = (
                        min(255, road_color[0] + bright_var),
                        min(255, road_color[1] + bright_var),
                        min(255, road_color[2] + bright_var),
                    )
                    c.set_pixel(gx, gy, gravel_color)

            dark_gravel_count = max(10, size * size // 20)
            if road_left <= road_right - 1:
                for _ in range(dark_gravel_count):
                    gx = rng.randint(road_left, road_right - 1)
                    gy = rng.randint(1, size - 2)
                    dark_var = rng.randint(10, 25)
                    if rng.random() > 0.5:
                        gravel_color = (
                            max(0, road_color[0] - dark_var),
                            max(0, road_color[1] - dark_var),
                            max(0, road_color[2] - dark_var),
                        )
                    else:
                        gray_tone = rng.randint(100, 140)
                        gravel_color = (gray_tone, gray_tone - 5, gray_tone - 10)
                    c.set_pixel(gx, gy, gravel_color)

            crack_count = max(3, size // 10)
            crack_lo = road_left + 1
            crack_hi = road_right - 2
            if crack_lo <= crack_hi:
                for _ in range(crack_count):
                    cx = rng.randint(crack_lo, crack_hi)
                    cy = rng.randint(2, size - 8)
                    crack_len = rng.randint(4, 10)
                    crack_angle = rng.uniform(-0.4, 0.4)
                    crack_color = tuple(max(0, v - 30) for v in road_color)
                    for i in range(crack_len):
                        px = cx + int(i * math.sin(crack_angle))
                        py = cy + i
                        if 0 <= py < size and road_left <= px < road_right:
                            c.set_pixel(px, py, crack_color)

        edge_color = CCPalette.DIRT.value
        for i in range(road_margin):
            alpha = i / road_margin
            blended = tuple(
                int(edge_color[j] * (1 - alpha) + road_color[j] * alpha) for j in range(3)
            )
            if orientation == "horizontal":
                c.set_pixel(i, size // 2, blended)
                c.set_pixel(size - 1 - i, size // 2, blended)
            else:
                c.set_pixel(size // 2, i, blended)
                c.set_pixel(size // 2, size - 1 - i, blended)

        add_noise(c, intensity=8)
        return c

    @staticmethod
    def generate_woods(size: int, density: str = "medium") -> PixelCanvas:
        """生成树林瓦片"""
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

    @staticmethod
    def generate_building(size: int, building_type: str = "solid") -> PixelCanvas:
        """生成建筑瓦片"""
        c = PixelCanvas(size, size)

        wall = CCPalette.BUILDING_WALL.value
        roof = CCPalette.BUILDING_ROOF.value
        window = CCPalette.BUILDING_WINDOW.value
        door = CCPalette.BUILDING_DOOR.value
        shadow = CCPalette.BUILDING_SHADOW.value

        margin = max(2, size // 16)

        if building_type == "solid":
            c.fill_rect(margin, margin, size - margin * 2, size - margin * 2, wall)

            roof_margin = margin - max(1, size // 32)
            c.fill_rect(
                roof_margin, roof_margin, size - roof_margin * 2, size - roof_margin * 2, roof
            )

            shadow_w = max(2, size // 16)
            for i in range(shadow_w):
                shade = tuple(int(wall[j] * (1 - i / shadow_w * 0.4)) for j in range(3))
                c.fill_rect(
                    size - margin - shadow_w + i,
                    margin + i,
                    1,
                    size - margin * 2 - i * 2,
                    shade,
                )

            win_sz = max(6, size // 8)
            win_margin = max(4, size // 8)
            c.fill_rect(margin + win_margin, margin + win_margin, win_sz, win_sz, (60, 60, 65))
            c.draw_outline_rect(
                margin + win_margin,
                margin + win_margin,
                win_sz,
                win_sz,
                (80, 80, 85),
                1,
            )
            c.fill_rect(
                size - margin - win_margin - win_sz,
                margin + win_margin * 2,
                win_sz,
                win_sz,
                (60, 60, 65),
            )
            c.draw_outline_rect(
                size - margin - win_margin - win_sz,
                margin + win_margin * 2,
                win_sz,
                win_sz,
                (80, 80, 85),
                1,
            )

        else:
            inner_margin = margin + max(2, size // 20)
            c.fill_rect(margin, margin, size - margin * 2, size - margin * 2, wall)
            c.fill_rect(
                inner_margin,
                inner_margin,
                size - inner_margin * 2,
                size - inner_margin * 2,
                tuple(min(255, v + 25) for v in wall),
            )

            door_w = max(6, size // 8)
            door_h = max(10, size // 6)
            door_x = size // 2 - door_w // 2
            door_y = size - margin - door_h
            c.fill_rect(door_x, door_y, door_w, door_h, (35, 28, 22))
            c.draw_outline_rect(door_x, door_y, door_w, door_h, door, 1)

            win_sz = max(6, size // 8)
            c.fill_rect(inner_margin + 2, inner_margin + 2, win_sz, win_sz, window)
            c.fill_rect(
                size - inner_margin - win_sz - 2,
                inner_margin + 4,
                win_sz,
                win_sz,
                window,
            )
            c.draw_outline_rect(
                inner_margin + 2,
                inner_margin + 2,
                win_sz,
                win_sz,
                (100, 100, 110),
                1,
            )
            c.draw_outline_rect(
                size - inner_margin - win_sz - 2,
                inner_margin + 4,
                win_sz,
                win_sz,
                (100, 100, 110),
                1,
            )

            roof_margin = margin - 1
            c.fill_rect(
                roof_margin,
                roof_margin,
                size - roof_margin * 2,
                size // 2 - roof_margin,
                roof,
            )
            eave_color = tuple(max(0, v - 15) for v in roof)
            c.fill_rect(
                roof_margin,
                size // 2 - roof_margin - 1,
                size - roof_margin * 2,
                2,
                eave_color,
            )

        shadow_h = max(2, size // 16)
        c.fill_rect(margin, size - margin, size - margin * 2, shadow_h, shadow)

        add_noise(c, intensity=4)
        return c

    @staticmethod
    def generate_bridge(size: int) -> PixelCanvas:
        """生成桥梁瓦片 — 纯俯视: 水上矩形平台, 木板线+细栏杆"""
        c = PixelCanvas(size, size)

        water = CCPalette.WATER.value
        deck_color = (160, 140, 90)
        deck_dark = (130, 112, 70)
        plank_line = (110, 92, 55)
        rail_color = (90, 72, 50)
        rail_post = (110, 90, 60)

        c.fill_rect(0, 0, size, size, water)
        rng = random.Random(99)
        for _ in range(max(5, size // 10)):
            wx = rng.randint(2, size - 3)
            wy = rng.randint(2, size - 3)
            ww = rng.randint(3, size // 6)
            c.fill_rect(wx, wy, ww, 1, tuple(min(255, v + 25) for v in water))

        max(3, size // 10)
        deck_h = max(size // 5, 8)
        deck_y = size // 2 - deck_h // 2

        c.fill_rect(0, deck_y, size, deck_h, deck_color)

        c.fill_rect(0, deck_y, size, 1, deck_dark)
        c.fill_rect(0, deck_y + deck_h - 1, size, 1, deck_dark)

        plank_gap = max(6, size // 8)
        for px in range(plank_gap, size, plank_gap):
            c.fill_rect(px - 1, deck_y, 1, deck_h, plank_line)

        nail_spacing = max(10, size // 4)
        for nx in range(nail_spacing // 2, size, nail_spacing):
            c.set_pixel(nx, deck_y + 1, (80, 70, 55))
            c.set_pixel(nx, deck_y + deck_h - 2, (80, 70, 55))

        rail_y_top = deck_y
        rail_y_bot = deck_y + deck_h - 1
        c.fill_rect(0, rail_y_top, size, 1, rail_color)
        c.fill_rect(0, rail_y_bot, size, 1, rail_color)

        post_spacing = max(8, size // 6)
        for px in range(post_spacing // 2, size, post_spacing):
            c.fill_rect(px, rail_y_top, 2, 1, rail_post)
            c.fill_rect(px, rail_y_bot, 2, 1, rail_post)

        add_noise(c, intensity=5)
        return c

    @staticmethod
    def generate_water(
        size: int, tile_x: int = 0, tile_y: int = 0, neighbors: dict | None = None
    ) -> PixelCanvas:
        """生成水面瓦片 — 增强版: 暗蓝绿色基底+有机波纹+稀有白色闪光

        CC2风格水面特征:
        - 基础颜色: 暗蓝绿色 (35, 70, 120) 而非亮蓝色
        - 整体亮度降低25%，营造深邃水体感
        - 半透明效果 (alpha=170)
        - 有机波纹: 正弦波+变化频率，非规则条纹
        - 稀有白色闪光: 仅2-3个/tile，1-2px大小

        Args:
            size: 瓦片尺寸
            tile_x: 瓦片在世界中的X坐标(用于波纹相位对齐)
            tile_y: 瓦片在世界中的Y坐标(用于波纹相位对齐)
            neighbors: 邻居信息字典, 键为 "north"/"east"/"south"/"west",
                       值为 True(水域邻居) 或 False(非水域邻居)

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
                wy = wy_base + int(
                    wave_amp * math.sin(wave_freq * (x + tile_x * size) + wave_phase)
                )
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

    @staticmethod
    def generate_hedge(size: int) -> PixelCanvas:
        """生成树篱瓦片 — 纯俯视: 密集灌木丛行, 不规则绿色团块"""
        c = PixelCanvas(size, size)

        grass_base = CCPalette.GRASS_LIGHT.value
        c.fill_rect(0, 0, size, size, grass_base)

        rng = random.Random(55)

        hedge_band_y = size // 3
        hedge_band_h = size // 3

        leaf_shades = [
            (35, 70, 25),
            (45, 85, 32),
            (55, 100, 38),
            (65, 115, 45),
        ]

        for y in range(hedge_band_y, hedge_band_y + hedge_band_h):
            for x in range(0, size):
                dist_from_center = abs(y - (hedge_band_y + hedge_band_h // 2))
                edge_fade = max(0, 1.0 - dist_from_center / (hedge_band_h // 2 + 1))
                if rng.random() < edge_fade * 0.95:
                    shade = leaf_shades[rng.randint(0, len(leaf_shades) - 1)]
                    var = rng.randint(-8, 8)
                    dot_color = (
                        max(0, min(255, shade[0] + var)),
                        max(0, min(255, shade[1] + var)),
                        max(0, min(255, shade[2] + var)),
                    )
                    c.set_pixel(x, y, dot_color)

        bush_count = max(6, size // 4)
        for _ in range(bush_count):
            bx = rng.randint(2, size - 5)
            by = rng.randint(hedge_band_y + 1, hedge_band_y + hedge_band_h - 3)
            br = rng.randint(2, 4)
            shade = leaf_shades[rng.randint(0, len(leaf_shades) - 1)]
            c.fill_circle(bx, by, br, shade)
            hl_color = (min(255, shade[0] + 20), min(255, shade[1] + 25), min(255, shade[2] + 12))
            c.fill_circle(bx - 1, by - 1, max(1, br // 2), hl_color)

        for _ in range(max(8, size // 3)):
            gx = rng.randint(1, size - 3)
            gy = rng.randint(hedge_band_y, hedge_band_y + hedge_band_h - 1)
            shade = leaf_shades[rng.randint(0, len(leaf_shades) - 1)]
            var = rng.randint(-10, 10)
            dot_color = (
                max(0, min(255, shade[0] + var)),
                max(0, min(255, shade[1] + var)),
                max(0, min(255, shade[2] + var)),
            )
            c.set_pixel(gx, gy, dot_color)
            if rng.random() > 0.5 and gx + 1 < size:
                c.set_pixel(gx + 1, gy, dot_color)

        shadow_offset = 2
        for y in range(
            hedge_band_y + hedge_band_h, min(size, hedge_band_y + hedge_band_h + shadow_offset + 2)
        ):
            alpha = max(0, 1.0 - (y - hedge_band_y - hedge_band_h) / (shadow_offset + 2))
            for x in range(0, size):
                if rng.random() < alpha * 0.6:
                    existing = c.get_pixel(x, y)
                    shadow_blend = (
                        max(0, int(existing[0] * (1 - alpha * 0.4))),
                        max(0, int(existing[1] * (1 - alpha * 0.3))),
                        max(0, int(existing[2] * (1 - alpha * 0.4))),
                    )
                    c.set_pixel(x, y, shadow_blend)

        add_noise(c, intensity=5)
        return c

    @staticmethod
    def generate_wall(size: int) -> PixelCanvas:
        """生成石墙瓦片 — 纯俯视: 细线石块纹理, 交替明暗段"""
        c = PixelCanvas(size, size)

        grass_base = CCPalette.GRASS_LIGHT.value
        c.fill_rect(0, 0, size, size, grass_base)

        rng = random.Random(88)

        wall_y = size // 2 - 1
        wall_h = 3

        stone_light = (140, 135, 125)
        stone_dark = (100, 95, 88)
        stone_mid = (120, 115, 108)
        mortar_color = (85, 80, 72)

        c.fill_rect(0, wall_y, size, wall_h, stone_mid)

        block_w = max(4, size // 8)
        for row in range(wall_h):
            offset = (row % 2) * (block_w // 2)
            for bx in range(-offset, size, block_w):
                block_type = rng.random()
                if block_type < 0.4:
                    block_color = stone_light
                elif block_type < 0.7:
                    block_color = stone_dark
                else:
                    block_color = stone_mid
                var = rng.randint(-8, 8)
                block_color = (
                    max(0, min(255, block_color[0] + var)),
                    max(0, min(255, block_color[1] + var)),
                    max(0, min(255, block_color[2] + var)),
                )
                bw = min(block_w - 1, size - bx)
                if bw > 0 and 0 <= bx < size:
                    c.fill_rect(bx, wall_y + row, bw, 1, block_color)

        for row in range(wall_h + 1):
            cy = wall_y + row
            for bx in range(0, size, block_w):
                offset = (row % 2) * (block_w // 2)
                mx = bx + offset
                if 0 <= mx < size:
                    c.set_pixel(mx, cy, mortar_color)

        shadow_y = wall_y + wall_h
        for sy in range(shadow_y, min(size, shadow_y + 2)):
            alpha = max(0, 1.0 - (sy - shadow_y) / 2)
            for sx in range(0, size):
                if rng.random() < alpha * 0.5:
                    existing = c.get_pixel(sx, sy)
                    shadow_blend = (
                        max(0, int(existing[0] * (1 - alpha * 0.3))),
                        max(0, int(existing[1] * (1 - alpha * 0.3))),
                        max(0, int(existing[2] * (1 - alpha * 0.3))),
                    )
                    c.set_pixel(sx, sy, shadow_blend)

        add_noise(c, intensity=5)
        return c

    @staticmethod
    def generate_open(size: int) -> PixelCanvas:
        """生成开阔地瓦片"""
        return TerrainTileGenerator.generate_grass(size, variant=1)

    @staticmethod
    def generate_shallow(size: int) -> PixelCanvas:
        """生成浅水瓦片"""
        c = TerrainTileGenerator.generate_grass(size, variant=2)
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

    @staticmethod
    def generate_rough(size: int) -> PixelCanvas:
        """生成崎岖地形瓦片"""
        c = TerrainTileGenerator.generate_grass(size, variant=3)
        rough_color = (160, 140, 90)
        rng = random.Random(66)
        for _ in range(max(8, size // 6)):
            rx = rng.randint(2, size - 3)
            ry = rng.randint(2, size - 3)
            rr = rng.randint(2, max(4, size // 12))
            c.fill_circle(rx, ry, rr, rough_color)
        add_noise(c, intensity=12)
        return c

    @staticmethod
    def generate_crater(size: int, variant: int = 0) -> PixelCanvas:
        c = PixelCanvas(size, size, bg=(90, 75, 60))
        cx, cy = size // 2, size // 2
        rng = random.Random(variant * 137 + 42)

        r = size // 3
        c.fill_ellipse(cx - r, cy - r, r * 2, r * 2, (65, 52, 40))
        inner_r = r // 2
        c.fill_ellipse(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2, (50, 40, 32))

        for _ in range(size // 2):
            angle = rng.uniform(0, 2 * math.pi)
            dist = r + rng.randint(-2, 3)
            px = int(cx + math.cos(angle) * dist)
            py = int(cy + math.sin(angle) * dist)
            if 0 <= px < size and 0 <= py < size:
                shade = rng.randint(35, 55)
                c.set_pixel(px, py, (shade, shade - 10, shade - 20))

        for _ in range(size // 4):
            rx = rng.randint(2, size - 3)
            ry = rng.randint(2, size - 3)
            rock_color = (rng.randint(70, 110), rng.randint(65, 100), rng.randint(55, 85))
            c.set_pixel(rx, ry, rock_color)
            if rng.random() > 0.5:
                c.set_pixel(rx + 1, ry, rock_color)

        return c

    @staticmethod
    def generate_swamp(size: int, variant: int = 0) -> PixelCanvas:
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

    @staticmethod
    def generate_mud(size: int, variant: int = 0) -> PixelCanvas:
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

    @staticmethod
    def generate_sand(size: int, variant: int = 0) -> PixelCanvas:
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

    @staticmethod
    def generate_snow(size: int, variant: int = 0) -> PixelCanvas:
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

    @staticmethod
    def generate_wire(size: int, variant: int = 0) -> PixelCanvas:
        c = TerrainTileGenerator.generate_grass(size, variant=variant + 10)

        rng = random.Random(variant * 523 + 51)
        wire_color = (100, 100, 100)
        post_color = (80, 75, 65)

        for strand in range(3):
            y_base = size // 4 + strand * (size // 5)
            x = 0
            y = y_base
            while x < size - 1:
                zig = rng.randint(2, max(3, size // 8))
                rng.randint(2, max(3, size // 8))
                next_x = min(size - 1, x + zig)
                next_y = max(1, min(size - 2, y + rng.choice([-2, -1, 0, 1, 2])))
                c.draw_line(x, y, next_x, next_y, wire_color, 1)
                x = next_x
                y = next_y

        post_spacing = max(8, size // 4)
        for px in range(post_spacing // 2, size, post_spacing):
            for strand in range(3):
                py = size // 4 + strand * (size // 5)
                c.fill_rect(px - 1, py - 1, 3, 3, post_color)

        add_noise(c, intensity=4)
        return c

    @staticmethod
    def generate_trench(size: int, variant: int = 0) -> PixelCanvas:
        c = PixelCanvas(size, size, bg=(76, 153, 0))
        rng = random.Random(variant * 641 + 61)

        grass_base = CCPalette.GRASS_LIGHT.value
        c.fill_rect(0, 0, size, size, grass_base)

        trench_w = max(8, size // 3)
        trench_left = (size - trench_w) // 2
        trench_right = trench_left + trench_w

        earth_wall = (120, 90, 55)
        wall_w = max(2, size // 10)
        c.fill_rect(trench_left - wall_w, 0, wall_w, size, earth_wall)
        c.fill_rect(trench_right, 0, wall_w, size, earth_wall)

        depression = (60, 45, 30)
        c.fill_rect(trench_left, 0, trench_w, size, depression)

        for _ in range(size // 2):
            dx = rng.randint(trench_left + 1, trench_right - 2)
            dy = rng.randint(0, size - 1)
            var = rng.randint(-10, 10)
            dirt_color = (
                max(0, min(255, depression[0] + var)),
                max(0, min(255, depression[1] + var)),
                max(0, min(255, depression[2] + var)),
            )
            c.set_pixel(dx, dy, dirt_color)

        for _ in range(size // 3):
            wx = rng.randint(trench_left - wall_w, trench_left - 1)
            wy = rng.randint(0, size - 1)
            var = rng.randint(-8, 8)
            wall_var = (
                max(0, min(255, earth_wall[0] + var)),
                max(0, min(255, earth_wall[1] + var)),
                max(0, min(255, earth_wall[2] + var)),
            )
            c.set_pixel(wx, wy, wall_var)

        add_noise(c, intensity=6)
        return c

    @staticmethod
    def generate_bunker(size: int, variant: int = 0) -> PixelCanvas:
        c = PixelCanvas(size, size, bg=(76, 153, 0))
        grass_base = CCPalette.GRASS_LIGHT.value
        c.fill_rect(0, 0, size, size, grass_base)

        concrete = (120, 115, 105)
        concrete_dark = (90, 85, 78)
        slit_dark = (30, 28, 25)

        bw = max(16, size * 2 // 3)
        bh = max(12, size // 2)
        bx = (size - bw) // 2
        by = (size - bh) // 2

        c.fill_rect(bx, by, bw, bh, concrete)

        c.fill_rect(bx, by, bw, max(2, size // 16), concrete_dark)
        c.fill_rect(bx, by + bh - max(2, size // 16), bw, max(2, size // 16), concrete_dark)
        c.fill_rect(bx, by, max(2, size // 16), bh, concrete_dark)
        c.fill_rect(bx + bw - max(2, size // 16), by, max(2, size // 16), bh, concrete_dark)

        slit_w = max(6, bw // 3)
        slit_h = max(2, size // 16)
        slit_x = bx + (bw - slit_w) // 2
        slit_y = by + bh // 2 - slit_h // 2
        c.fill_rect(slit_x, slit_y, slit_w, slit_h, slit_dark)

        rng = random.Random(variant * 757 + 71)
        for _ in range(bw * bh // 8):
            px = rng.randint(bx + 1, bx + bw - 2)
            py = rng.randint(by + 1, by + bh - 2)
            var = rng.randint(-8, 8)
            tex_color = (
                max(0, min(255, concrete[0] + var)),
                max(0, min(255, concrete[1] + var)),
                max(0, min(255, concrete[2] + var)),
            )
            c.set_pixel(px, py, tex_color)

        add_noise(c, intensity=5)
        return c
