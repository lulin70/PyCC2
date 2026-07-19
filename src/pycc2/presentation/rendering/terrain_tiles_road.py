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

    if orientation == "horizontal":
        _generate_horizontal_road(size, neighbors, c, road_color, road_margin)
    else:
        _generate_vertical_road(size, neighbors, c, road_color, road_margin)

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


def _generate_horizontal_road(
    size: int,
    neighbors: dict,
    c: PixelCanvas,
    road_color: tuple[int, int, int],
    road_margin: int,
) -> None:
    """Draw horizontal road: fill, curbs, edge fades, rut lines, tire tracks, gravel, cracks."""
    has_n = neighbors.get("north", False)
    has_e = neighbors.get("east", False)
    has_s = neighbors.get("south", False)
    has_w = neighbors.get("west", False)

    road_top = size // 2 - road_margin // 2
    road_bot = size // 2 + road_margin // 2
    if has_n:
        road_top = 0
    if has_s:
        road_bot = size
    road_h = road_bot - road_top
    c.fill_rect(0, road_top, size, road_h, road_color)

    _draw_curbs(c, size, road_top, road_bot, has_n, has_s, road_color, "horizontal")
    _draw_edge_fade(c, size, road_top, road_bot, has_w, has_e, road_color, "horizontal")

    rut_y1 = size // 2 - road_margin // 4
    rut_y2 = size // 2 + road_margin // 4
    rut_color = tuple(max(0, v - 20) for v in road_color)
    c.fill_rect(0, rut_y1, size, max(1, size // 32), rut_color)
    c.fill_rect(0, rut_y2, size, max(1, size // 32), rut_color)

    _draw_tire_tracks(c, size, road_top, road_bot, has_w, has_e, road_color, "horizontal")

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


def _generate_vertical_road(
    size: int,
    neighbors: dict,
    c: PixelCanvas,
    road_color: tuple[int, int, int],
    road_margin: int,
) -> None:
    """Draw vertical road: fill, curbs, edge fades, tire tracks, gravel, cracks."""
    has_n = neighbors.get("north", False)
    has_e = neighbors.get("east", False)
    has_s = neighbors.get("south", False)
    has_w = neighbors.get("west", False)

    road_left = size // 2 - road_margin // 2
    road_right = size // 2 + road_margin // 2
    if has_w:
        road_left = 0
    if has_e:
        road_right = size
    road_w = road_right - road_left
    c.fill_rect(road_left, 0, road_w, size, road_color)

    _draw_curbs(c, size, road_left, road_right, has_w, has_e, road_color, "vertical")
    _draw_edge_fade(c, size, road_left, road_right, has_n, has_s, road_color, "vertical")

    _draw_tire_tracks(c, size, road_left, road_right, has_n, has_s, road_color, "vertical")

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


def _draw_curbs(
    c: PixelCanvas,
    size: int,
    road_top: int,
    road_bot: int,
    has_n: bool,
    has_s: bool,
    road_color: tuple[int, int, int],
    orientation: str,
) -> None:
    """Draw curbs at the two road edges perpendicular to the road direction.

    For horizontal orientation, road_top/road_bot are y-bounds and has_n/has_s
    are north/south neighbor flags. For vertical orientation, road_top/road_bot
    are x-bounds (left/right) and has_n/has_s are west/east neighbor flags.
    """
    road_span = road_bot - road_top
    if road_span <= 4:
        return
    curb_color = tuple(max(0, v - 25) for v in road_color)
    if orientation == "horizontal":
        if not has_n:
            c.fill_rect(0, road_top, size, 2, curb_color)
        if not has_s:
            c.fill_rect(0, road_bot - 2, size, 2, curb_color)
    else:
        if not has_n:
            c.fill_rect(road_top, 0, 2, size, curb_color)
        if not has_s:
            c.fill_rect(road_bot - 2, 0, 2, size, curb_color)


def _draw_edge_fade(
    c: PixelCanvas,
    size: int,
    road_top: int,
    road_bot: int,
    has_w: bool,
    has_e: bool,
    road_color: tuple[int, int, int],
    orientation: str,
) -> None:
    """Draw fade-in gradient at road ends where there is no road neighbor.

    For horizontal orientation, road_top/road_bot are y-bounds and has_w/has_e
    are west/east neighbor flags. For vertical orientation, road_top/road_bot
    are x-bounds (left/right) and has_w/has_e are north/south neighbor flags.
    """
    road_margin = max(3, size // 10)
    fade_range = min(4, road_margin)
    if orientation == "horizontal":
        if not has_w:
            for i in range(fade_range):
                alpha = i / 4
                blended = tuple(
                    int(CCPalette.DIRT.value[j] * (1 - alpha) + road_color[j] * alpha)
                    for j in range(3)
                )
                for ry in range(road_top, road_bot):
                    c.set_pixel(i, ry, blended)
        if not has_e:
            for i in range(fade_range):
                alpha = i / 4
                blended = tuple(
                    int(CCPalette.DIRT.value[j] * (1 - alpha) + road_color[j] * alpha)
                    for j in range(3)
                )
                for ry in range(road_top, road_bot):
                    c.set_pixel(size - 1 - i, ry, blended)
    else:
        if not has_w:
            for i in range(fade_range):
                alpha = i / 4
                blended = tuple(
                    int(CCPalette.DIRT.value[j] * (1 - alpha) + road_color[j] * alpha)
                    for j in range(3)
                )
                for rx in range(road_top, road_bot):
                    c.set_pixel(rx, i, blended)
        if not has_e:
            for i in range(fade_range):
                alpha = i / 4
                blended = tuple(
                    int(CCPalette.DIRT.value[j] * (1 - alpha) + road_color[j] * alpha)
                    for j in range(3)
                )
                for rx in range(road_top, road_bot):
                    c.set_pixel(rx, size - 1 - i, blended)


def _draw_tire_tracks(
    c: PixelCanvas,
    size: int,
    road_top: int,
    road_bot: int,
    has_w: bool,
    has_e: bool,
    road_color: tuple[int, int, int],
    orientation: str,
) -> None:
    """Draw two parallel tire tracks with wobble and edge fade.

    For horizontal orientation, road_top/road_bot are y-bounds and has_w/has_e
    are west/east neighbor flags (seed 7777). For vertical orientation,
    road_top/road_bot are x-bounds (left/right) and has_w/has_e are
    north/south neighbor flags (seed 7778).
    """
    seed = 7777 if orientation == "horizontal" else 7778
    tire_rng = random.Random(seed)
    tire_color = tuple(max(0, v - 30) for v in road_color)
    tire_spacing = tire_rng.randint(4, 6)
    tire_width = tire_rng.choice([1, 2])

    center = (road_top + road_bot) // 2
    tire1 = center - tire_spacing // 2
    tire2 = center + tire_spacing // 2

    _draw_single_tire_track(
        c,
        size,
        road_top,
        road_bot,
        has_w,
        has_e,
        tire1,
        tire_width,
        tire_color,
        tire_rng,
        orientation,
    )
    _draw_single_tire_track(
        c,
        size,
        road_top,
        road_bot,
        has_w,
        has_e,
        tire2,
        tire_width,
        tire_color,
        tire_rng,
        orientation,
    )


def _draw_single_tire_track(
    c: PixelCanvas,
    size: int,
    road_lo: int,
    road_hi: int,
    has_start: bool,
    has_end: bool,
    tire_pos: int,
    tire_width: int,
    tire_color: tuple[int, ...],
    tire_rng: random.Random,
    orientation: str,
) -> None:
    """Draw a single tire track with periodic wobble and edge fade.

    Iterates along the road direction (p), computing the cross-axis position
    (cross) via tire_pos + current_offset. The has_start/has_end flags control
    fade at the two road-direction ends.
    """
    wobble_interval = tire_rng.randint(8, 12)
    current_offset = tire_rng.randint(-1, 1)
    for p in range(size):
        if p < 4 and not has_start:
            fade = p / 4
            if tire_rng.random() > fade:
                continue
        elif p >= size - 4 and not has_end:
            fade = (size - 1 - p) / 4
            if tire_rng.random() > fade:
                continue
        if p > 0 and p % wobble_interval == 0:
            current_offset = tire_rng.randint(-1, 1)
        cross = tire_pos + current_offset
        if road_lo <= cross < road_hi and tire_rng.random() > 0.05:
            for w in range(tire_width):
                if 0 <= cross + w < size:
                    if orientation == "horizontal":
                        c.set_pixel(p, cross + w, tire_color)
                    else:
                        c.set_pixel(cross + w, p, tire_color)
