"""Structure tile generators (building / bridge / hedge / wall / bunker).

Extracted from terrain_tile_generator.py during Phase 2 P0-1 large file split (2026-07-04).
Each function returns a PixelCanvas. Functions are stateless and can be called directly.
"""

from __future__ import annotations

import random

from pycc2.presentation.rendering.pixel_canvas import (
    CCPalette,
    PixelCanvas,
    add_noise,
)


def generate_building(size: int, building_type: str = "solid") -> PixelCanvas:
    """Generate building tile.

    Args:
        size: Tile size in pixels.
        building_type: "solid" (fortified block) or "detailed" (with door/windows/roof).

    Returns:
        PixelCanvas of the building tile.
    """
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
        c.fill_rect(roof_margin, roof_margin, size - roof_margin * 2, size - roof_margin * 2, roof)

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


def generate_bridge(size: int) -> PixelCanvas:
    """Generate bridge tile — top-down view: rectangular deck on water with planks and rails.

    Args:
        size: Tile size in pixels.

    Returns:
        PixelCanvas of the bridge tile.
    """
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


def generate_hedge(size: int) -> PixelCanvas:
    """Generate hedge tile — top-down view: dense shrub row with irregular green clumps.

    Args:
        size: Tile size in pixels.

    Returns:
        PixelCanvas of the hedge tile.
    """
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


def generate_wall(size: int) -> PixelCanvas:
    """Generate stone wall tile — top-down view: thin line of stone blocks with alternating shades.

    Args:
        size: Tile size in pixels.

    Returns:
        PixelCanvas of the wall tile.
    """
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


def generate_bunker(size: int, variant: int = 0) -> PixelCanvas:
    """Generate bunker tile — top-down view: concrete block with central slit.

    Args:
        size: Tile size in pixels.
        variant: Variant seed for deterministic randomness.

    Returns:
        PixelCanvas of the bunker tile.
    """
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
