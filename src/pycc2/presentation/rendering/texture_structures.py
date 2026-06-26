"""Structure textures: buildings, walls, craters, trenches."""

from __future__ import annotations

import logging
import math
import random

import pygame

from .terrain_tile_cache import CC2_TERRAIN_PALETTE
from .texture_basic import _fill_with_variation

TILE_SIZE = 48


def _texture_building_enterable(
    surface: pygame.Surface, tid: int, var: int, pal, bitmask: int = 0
) -> None:
    """BUILDING_ENTERABLE (4): CC2 earthy brown building with visible roof, door, windows."""
    rng = random.Random(var * 103)
    wall_color = (139, 115, 85)
    surface.fill(wall_color)
    pixels = pygame.surfarray.pixels3d(surface)
    tile_sz = TILE_SIZE

    roof_color = (110, 75, 45)
    roof_height = tile_sz // 6
    roof_line_color = (92, 60, 35)
    for x in range(tile_sz):
        for y in range(0, roof_height):
            pixels[x, y] = roof_color
        if roof_height < tile_sz:
            pixels[x, roof_height] = (95, 62, 35)
    for y in range(2, roof_height, 2):
        for x in range(tile_sz):
            pixels[x, y] = roof_line_color

    brick_color = (130, 108, 78)
    brick_spacing_y = max(3, tile_sz // 12)
    brick_width = max(5, tile_sz // 7)
    brick_offset = max(3, brick_width // 2)

    for y in range(roof_height + 1, tile_sz, brick_spacing_y):
        offset = brick_offset if ((y - roof_height - 1) // brick_spacing_y) % 2 == 0 else 0
        for x in range(offset, tile_sz - brick_width + 1, brick_width * 2):
            if rng.random() > 0.5:
                for dx in range(brick_width - 1):
                    if x + dx < tile_sz and y < tile_sz:
                        pixels[x + dx, y] = brick_color

    door_color = (90, 58, 33)
    door_top = int(0.42 * tile_sz)
    door_bottom = min(tile_sz - 1, int(0.65 * tile_sz))
    door_left = tile_sz // 3
    door_right = 2 * tile_sz // 3

    for y in range(door_top, door_bottom):
        for x in range(door_left, door_right):
            pixels[x, y] = door_color
    frame_color = (70, 45, 25)
    for y in range(door_top, door_bottom):
        if door_left < tile_sz:
            pixels[door_left, y] = frame_color
        if door_right < tile_sz:
            pixels[door_right - 1, y] = frame_color
    for x in range(door_left, door_right):
        if door_top < tile_sz:
            pixels[x, door_top] = frame_color

    window_color = (150, 185, 215)
    window_top = int(0.21 * tile_sz)
    window_bottom = int(0.33 * tile_sz)
    window_left = tile_sz // 8
    window_right = tile_sz // 4

    for y in range(window_top, window_bottom):
        for x in range(window_left, window_right):
            pixels[x, y] = window_color
    for y in range(window_top, window_bottom):
        if window_left < tile_sz:
            pixels[window_left, y] = frame_color
        if window_right < tile_sz:
            pixels[window_right - 1, y] = frame_color
    for x in range(window_left, window_right):
        if window_top < tile_sz:
            pixels[x, window_top] = frame_color
        if window_bottom < tile_sz:
            pixels[x, window_bottom - 1] = frame_color

    second_window_left = 3 * tile_sz // 5
    second_window_right = 7 * tile_sz // 10
    for y in range(window_top, window_bottom):
        for x in range(second_window_left, second_window_right):
            pixels[x, y] = window_color
    for y in range(window_top, window_bottom):
        if second_window_left < tile_sz:
            pixels[second_window_left, y] = frame_color
        if second_window_right < tile_sz:
            pixels[second_window_right - 1, y] = frame_color
    for x in range(second_window_left, second_window_right):
        if window_top < tile_sz:
            pixels[x, window_top] = frame_color
        if window_bottom < tile_sz:
            pixels[x, window_bottom - 1] = frame_color

    del pixels


def _texture_building_solid(
    surface: pygame.Surface, tid: int, var: int, pal, bitmask: int = 0
) -> None:
    """BUILDING_SOLID (5): Gray stone/brick building, no door, solid walls, roof line."""
    rng = random.Random(var * 109)
    wall_color = (140, 138, 135)
    surface.fill(wall_color)
    pixels = pygame.surfarray.pixels3d(surface)
    tile_sz = TILE_SIZE

    roof_color = (90, 85, 80)
    roof_height = max(2, tile_sz // 10)
    roof_line_color = (72, 67, 62)
    for x in range(tile_sz):
        for y in range(0, roof_height):
            pixels[x, y] = roof_color
        if roof_height < tile_sz:
            pixels[x, roof_height] = (75, 70, 65)
    for y in range(2, roof_height, 2):
        for x in range(tile_sz):
            pixels[x, y] = roof_line_color

    stone_dark = (120, 118, 115)
    stone_light = (155, 152, 148)
    block_height = max(4, tile_sz // 10)
    block_width = max(6, tile_sz // 6)
    mortar_offset = max(2, block_width // 3)

    for y in range(roof_height + 1, tile_sz, block_height):
        offset = mortar_offset if ((y - roof_height - 1) // block_height) % 2 == 0 else 0
        for x in range(offset, tile_sz - block_width + 1, block_width * 2):
            for dy in range(block_height - 1):
                for dx in range(block_width - 1):
                    if x + dx < tile_sz and y + dy < tile_sz:
                        color = stone_dark if rng.random() > 0.5 else stone_light
                        pixels[x + dx, y + dy] = color
        for x in range(tile_sz):
            if y < tile_sz:
                pixels[x, y] = (100, 98, 95)

    vent_color = (60, 60, 65)
    vent_top = int(0.21 * tile_sz)
    vent_bottom = int(0.29 * tile_sz)
    vent_left = tile_sz // 3
    vent_right = 2 * tile_sz // 3

    for y in range(vent_top, vent_bottom):
        for x in range(vent_left, vent_right):
            if x < tile_sz and y < tile_sz:
                pixels[x, y] = vent_color
    del pixels


def _texture_wall(surface: pygame.Surface, tid: int, var: int, pal, bitmask: int = 0) -> None:
    """WALL (8): Gray brick wall with mortar lines."""
    rng = random.Random(var * 173)
    wall_color = (130, 128, 125)
    surface.fill(wall_color)
    pixels = pygame.surfarray.pixels3d(surface)
    tile_sz = TILE_SIZE

    mortar_color = (95, 92, 88)
    brick_dark = (115, 112, 108)
    brick_light = (145, 142, 138)

    brick_height = max(4, tile_sz // 10)
    brick_width = max(8, tile_sz // 4)
    brick_offset = max(5, brick_width - 3)

    for y in range(0, tile_sz, brick_height):
        offset = brick_offset if (y // brick_height) % 2 == 0 else 0
        for x in range(tile_sz):
            if y < tile_sz:
                pixels[x, y] = mortar_color
        for bx in range(offset, tile_sz - brick_width + 1, brick_width * 2):
            for dy in range(1, brick_height):
                for dx in range(1, brick_width - 1):
                    if bx + dx < tile_sz and y + dy < tile_sz:
                        color = brick_dark if rng.random() > 0.5 else brick_light
                        pixels[bx + dx, y + dy] = color
            if bx + brick_width - 1 < tile_sz:
                for dy in range(1, brick_height):
                    if y + dy < tile_sz:
                        pixels[bx + brick_width - 1, y + dy] = mortar_color

    for x in range(tile_sz):
        pixels[x, 0] = (80, 78, 75)
        if tile_sz > 1:
            pixels[x, 1] = (100, 98, 95)
    del pixels


def _texture_crater(surface: pygame.Surface, tid: int, var: int, pal, bitmask: int = 0) -> None:
    """CRATER (12): CC2 authentic shell crater with elliptical depression and bright rim."""
    rng = random.Random(var * 331)
    tile_sz = TILE_SIZE
    base = (90, 75, 60)
    _fill_with_variation(surface, base, rng, 10)

    try:
        pixels = pygame.surfarray.pixels3d(surface)
        cx, cy = tile_sz // 2, tile_sz // 2
        radius_x = tile_sz // 2 - 3
        radius_y = int(radius_x / 1.4)
        radius_y = max(6, radius_y)

        for y in range(tile_sz):
            for x in range(tile_sz):
                if radius_x > 0 and radius_y > 0:
                    norm_dist = ((x - cx) / radius_x) ** 2 + ((y - cy) / radius_y) ** 2
                    if norm_dist < 0.15:
                        shade = max(
                            0, int(CC2_TERRAIN_PALETTE["crater_center"][0] + rng.randint(-8, 8))
                        )
                        pixels[x, y] = (shade, max(0, shade - 14), max(0, shade - 24))
                    elif norm_dist < 0.45:
                        t = (norm_dist - 0.15) / 0.30
                        base_r = CC2_TERRAIN_PALETTE["crater_center"][0]
                        rim_r = CC2_TERRAIN_PALETTE["crater_rim"][0]
                        shade = int(base_r + t * (rim_r - base_r) + rng.randint(-6, 6))
                        pixels[x, y] = (
                            min(255, shade),
                            min(255, max(0, shade - 6)),
                            min(255, max(0, shade - 16)),
                        )
                    elif norm_dist < 0.85:
                        t = (norm_dist - 0.45) / 0.40
                        base_r = CC2_TERRAIN_PALETTE["crater_rim"][0]
                        bright_rim_color = (158, 130, 72)
                        shade = int(
                            CC2_TERRAIN_PALETTE["crater_rim"][0]
                            + t * (bright_rim_color[0] - CC2_TERRAIN_PALETTE["crater_rim"][0])
                        )
                        pixels[x, y] = (
                            min(255, shade + rng.randint(-6, 6)),
                            min(255, max(0, shade - 4 + rng.randint(-5, 5))),
                            min(255, max(0, shade - 12 + rng.randint(-5, 5))),
                        )
                    elif norm_dist < 1.0:
                        rim_color = (158, 130, 72)
                        brightness_factor = 1.0 - (norm_dist - 0.85) / 0.15
                        pixels[x, y] = (
                            max(
                                0,
                                min(
                                    255,
                                    int(rim_color[0] * brightness_factor + rng.randint(-10, 10)),
                                ),
                            ),
                            max(
                                0,
                                min(
                                    255,
                                    int(rim_color[1] * brightness_factor + rng.randint(-8, 8)),
                                ),
                            ),
                            max(
                                0,
                                min(
                                    255,
                                    int(rim_color[2] * brightness_factor + rng.randint(-12, 12)),
                                ),
                            ),
                        )

        num_debris = tile_sz // 2
        for _ in range(num_debris):
            angle = rng.uniform(0, 2 * math.pi)
            dist = radius_x * rng.uniform(0.80, 1.20)
            rx = int(cx + math.cos(angle) * dist)
            ry = int(cy + math.sin(angle) * dist * (radius_y / max(radius_x, 1)))
            if 0 <= rx < tile_sz and 0 <= ry < tile_sz:
                rock_color = (rng.randint(100, 150), rng.randint(85, 130), rng.randint(65, 110))
                pixels[rx, ry] = rock_color
                if rng.random() > 0.55:
                    cluster_size = rng.randint(2, 3)
                    for _ in range(cluster_size):
                        dx, dy = rng.choice([(1, 0), (0, 1), (-1, 0), (0, -1), (1, 1)])
                        if 0 <= rx + dx < tile_sz and 0 <= ry + dy < tile_sz:
                            pixels[rx + dx, ry + dy] = tuple(
                                max(0, c - rng.randint(10, 20)) for c in rock_color
                            )

        del pixels
    except (ValueError, IndexError) as e:
        logging.debug(f"Texture generation failed: {e}")


def _texture_trench(surface: pygame.Surface, tid: int, var: int, pal, bitmask: int = 0) -> None:
    """TRENCH (13): Defensive earthwork line."""
    from pycc2.presentation.rendering.autotile_system import (
        DIR_EAST,
        DIR_WEST,
        get_edge_transition_width,
    )

    rng = random.Random(var * 397)
    tile_sz = TILE_SIZE
    ground_color = (100, 85, 65)
    surface.fill(ground_color)
    pixels = pygame.surfarray.pixels3d(surface)

    trench_main = CC2_TERRAIN_PALETTE["trench_main"]
    trench_embankment = CC2_TERRAIN_PALETTE["trench_embankment"]

    edge_widths = get_edge_transition_width(tid, bitmask, tile_sz)
    tile_sz // 2
    base_y = tile_sz // 2
    trench_width = rng.randint(3, 5)

    trench_center_points = []
    x = 0
    y = base_y
    if bitmask & DIR_WEST:
        y = int(tile_sz * 0.4) + rng.randint(-2, 2)
    elif bitmask & DIR_EAST:
        pass
    while x < tile_sz:
        trench_center_points.append((x, y))
        x += 1
        coord_seed = var * 397 + bitmask * 23 + x * 7
        coord_rng = random.Random(coord_seed)
        y += coord_rng.randint(-1, 1)
        y = max(tile_sz // 6, min(5 * tile_sz // 6, y))

    for point in trench_center_points:
        px, py = point[0], int(point[1])
        for offset in range(-trench_width // 2, trench_width // 2 + 1):
            draw_x = px + offset
            if 0 <= draw_x < tile_sz and 0 <= py < tile_sz:
                dist_from_center = abs(offset)
                if dist_from_center == 0:
                    pixels[draw_x, py] = trench_main
                else:
                    shade_var = rng.randint(-5, 5)
                    pixels[draw_x, py] = (
                        min(255, trench_main[0] + dist_from_center * 8 + shade_var),
                        min(255, trench_main[1] + dist_from_center * 6 + shade_var),
                        min(255, trench_main[2] + dist_from_center * 4 + shade_var),
                    )
        for emb_offset in [-(trench_width // 2 + 1), (trench_width // 2 + 1)]:
            emb_x = px + emb_offset
            if 0 <= emb_x < tile_sz and 0 <= py < tile_sz:
                pixels[emb_x, py] = trench_embankment
                if rng.random() > 0.6:
                    emb_x2 = px + emb_offset + (1 if emb_offset > 0 else -1)
                    if 0 <= emb_x2 < tile_sz and 0 < py < tile_sz:
                        pixels[emb_x2, py] = (
                            trench_embankment[0] - 10,
                            trench_embankment[1] - 8,
                            trench_embankment[2] - 6,
                        )

    if edge_widths["west"] > 0 and not (bitmask & DIR_WEST):
        taper_width = min(edge_widths["west"], 10)
        for x in range(taper_width):
            taper_factor = x / taper_width
            for y in range(tile_sz):
                if rng.random() > taper_factor * 0.7:
                    r, g, b = int(pixels[x, y][0]), int(pixels[x, y][1]), int(pixels[x, y][2])
                    pixels[x, y] = (
                        int(r + (ground_color[0] - r) * (1 - taper_factor)),
                        int(g + (ground_color[1] - g) * (1 - taper_factor)),
                        int(b + (ground_color[2] - b) * (1 - taper_factor)),
                    )
        dirt_pile_cx = 3
        dirt_pile_cy = base_y
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                dp_x = dirt_pile_cx + dx
                dp_y = dirt_pile_cy + dy
                if 0 <= dp_x < tile_sz and 0 <= dp_y < tile_sz:
                    if dx * dx + dy * dy <= 4:
                        pixels[dp_x, dp_y] = (110, 90, 60)

    if edge_widths["east"] > 0 and not (bitmask & DIR_EAST):
        taper_width = min(edge_widths["east"], 10)
        for x in range(tile_sz - taper_width, tile_sz):
            dist_from_east = tile_sz - 1 - x
            taper_factor = dist_from_east / taper_width
            for y in range(tile_sz):
                if rng.random() > taper_factor * 0.7:
                    r, g, b = int(pixels[x, y][0]), int(pixels[x, y][1]), int(pixels[x, y][2])
                    pixels[x, y] = (
                        int(r + (ground_color[0] - r) * (1 - taper_factor)),
                        int(g + (ground_color[1] - g) * (1 - taper_factor)),
                        int(b + (ground_color[2] - b) * (1 - taper_factor)),
                    )
        dirt_pile_cx = tile_sz - 4
        dirt_pile_cy = base_y
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                dp_x = dirt_pile_cx + dx
                dp_y = dirt_pile_cy + dy
                if 0 <= dp_x < tile_sz and 0 <= dp_y < tile_sz:
                    if dx * dx + dy * dy <= 4:
                        pixels[dp_x, dp_y] = (110, 90, 60)

    num_debris = rng.randint(3, 7)
    for _ in range(num_debris):
        debris_x = rng.randint(tile_sz // 4, 3 * tile_sz // 4)
        if debris_x < len(trench_center_points):
            approx_ty = int(trench_center_points[debris_x][1])
            debris_y = approx_ty + rng.randint(-trench_width // 2, trench_width // 2)
            if 0 <= debris_x < tile_sz and 0 <= debris_y < tile_sz:
                pixels[debris_x, debris_y] = (45, 35, 25)

    del pixels
