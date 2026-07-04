"""Battlefield tile generators (crater / wire / trench).

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
from pycc2.presentation.rendering.terrain_tiles_natural import generate_grass


def generate_crater(size: int, variant: int = 0) -> PixelCanvas:
    """Generate crater tile — top-down view: elliptical impact crater with scattered debris.

    Args:
        size: Tile size in pixels.
        variant: Variant seed for deterministic randomness.

    Returns:
        PixelCanvas of the crater tile.
    """
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


def generate_wire(size: int, variant: int = 0) -> PixelCanvas:
    """Generate wire tile — top-down view: grass base with zigzag wire strands and posts.

    Args:
        size: Tile size in pixels.
        variant: Variant seed for deterministic randomness.

    Returns:
        PixelCanvas of the wire tile.
    """
    c = generate_grass(size, variant=variant + 10)

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


def generate_trench(size: int, variant: int = 0) -> PixelCanvas:
    """Generate trench tile — top-down view: central depression with earth walls on both sides.

    Args:
        size: Tile size in pixels.
        variant: Variant seed for deterministic randomness.

    Returns:
        PixelCanvas of the trench tile.
    """
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
