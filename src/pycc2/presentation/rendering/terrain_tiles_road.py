"""Road tile generator with neighbor-aware orientation logic.

Extracted from terrain_tile_generator.py during Phase 2 P0-1 large file split (2026-07-04).
Largest single generator (~320L) due to horizontal/vertical orientation branches
and neighbor-aware curb/tire-track/fade rendering.
"""

from __future__ import annotations

import math
import random

from pycc2.presentation.rendering.pixel_canvas import (
    CCPalette,
    PixelCanvas,
    add_noise,
)


def generate_road(
    size: int, orientation: str = "horizontal", neighbors: dict | None = None
) -> PixelCanvas:
    """Generate road tile — enhanced: gravel particles + crack texture + cross-tile continuity.

    Args:
        size: tile size
        orientation: "horizontal" or "vertical"
        neighbors: neighbor info dict, keys are "north"/"east"/"south"/"west",
                   values are True (road neighbor) or False (non-road neighbor)

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
        blended = tuple(int(edge_color[j] * (1 - alpha) + road_color[j] * alpha) for j in range(3))
        if orientation == "horizontal":
            c.set_pixel(i, size // 2, blended)
            c.set_pixel(size - 1 - i, size // 2, blended)
        else:
            c.set_pixel(size // 2, i, blended)
            c.set_pixel(size // 2, size - 1 - i, blended)

    add_noise(c, intensity=8)
    return c
