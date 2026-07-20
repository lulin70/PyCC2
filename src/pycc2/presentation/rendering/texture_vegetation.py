"""Vegetation textures: woods/forest, hedgerows/bushes, rough ground."""

from __future__ import annotations

import math
import random

import pygame

from ..visual_config import DEFAULT_VISUAL_CONFIG
from .terrain_tile_cache import CC2_TERRAIN_PALETTE

# V-01 (Wave C3b): TILE_SIZE migrated to DEFAULT_VISUAL_CONFIG for theme hot-reload.
TILE_SIZE = DEFAULT_VISUAL_CONFIG.dimensions.TILE_SIZE


def _texture_woods(surface: pygame.Surface, tid: int, var: int, pal, bitmask: int = 0) -> None:
    """WOODS (3): CC2 very dark green forest with individual tree canopies visible."""
    rng = random.Random(var * 41)
    base = (45, 68, 33)
    surface.fill(base)
    pixels = pygame.surfarray.pixels3d(surface)
    tile_sz = TILE_SIZE

    try:
        for y in range(tile_sz):
            for x in range(tile_sz):
                offset = rng.randint(-8, 8)
                r, g, b = int(pixels[x, y][0]), int(pixels[x, y][1]), int(pixels[x, y][2])
                new_r = max(0, min(255, r + offset))
                new_g = max(0, min(255, g + offset))
                new_b = max(0, min(255, b + offset))
                pixels[x, y] = (new_r, new_g, new_b)

        num_trees = rng.randint(6, 12)
        for _ in range(num_trees):
            cx = rng.randint(tile_sz // 8, tile_sz - tile_sz // 8)
            cy = rng.randint(tile_sz // 8, tile_sz - tile_sz // 8)
            radius = rng.randint(7, 13)
            for y in range(max(0, cy - radius), min(tile_sz, cy + radius + 1)):
                for x in range(max(0, cx - radius), min(tile_sz, cx + radius + 1)):
                    dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                    if dist < radius:
                        if dist > radius * 0.75:
                            pixels[x, y] = (30, 52, 22)
                        elif dist > radius * 0.5:
                            pixels[x, y] = (40, 62, 28)
                        elif dist > radius * 0.25:
                            pixels[x, y] = (50, 78, 35)
                        else:
                            pixels[x, y] = (58, 90, 42)

            trunk_y = min(tile_sz - 1, cy + radius - 3)
            if 0 <= cx < tile_sz and 0 <= trunk_y < tile_sz:
                pixels[cx, trunk_y] = (65, 48, 28)

        for _ in range(num_trees):
            sx = rng.randint(tile_sz // 10, tile_sz - tile_sz // 10)
            sy = rng.randint(int(0.7 * tile_sz), tile_sz - 1)
            pixels[sx, sy] = (28, 45, 20)
    except (ValueError, IndexError):
        pass
    finally:
        del pixels


def _texture_hedge(surface: pygame.Surface, tid: int, var: int, pal, bitmask: int = 0) -> None:
    """HEDGE (7): CC2 authentic Normandy bocage hedgerow."""
    from pycc2.presentation.rendering.autotile_system import (
        DIR_EAST,
        DIR_NORTH,
        DIR_SOUTH,
        DIR_WEST,
        get_edge_transition_width,
    )

    rng = random.Random(var * 151)
    tile_sz = TILE_SIZE
    ground_color = (90, 130, 55)
    surface.fill(ground_color)
    pixels = pygame.surfarray.pixels3d(surface)

    hedge_dark = CC2_TERRAIN_PALETTE["hedgerow_dark"]
    hedge_base = CC2_TERRAIN_PALETTE["hedgerow_base"]
    hedge_light = CC2_TERRAIN_PALETTE["hedgerow_light"]
    embankment_color = CC2_TERRAIN_PALETTE.get("embankment", (68, 58, 38))

    edge_widths = get_edge_transition_width(tid, bitmask, tile_sz)
    center_y = tile_sz // 2
    base_width = rng.randint(10, 16)

    top_edge = []
    x = 0
    y = center_y - base_width // 2
    if bitmask & DIR_NORTH:
        y = int(tile_sz * 0.7)
    while x < tile_sz:
        top_edge.append((x, y))
        x += 1
        coord_seed = var * 151 + bitmask * 17 + x * 3
        coord_rng = random.Random(coord_seed)
        y += coord_rng.randint(-3, 3)
        y = max(tile_sz // 6, min(5 * tile_sz // 6, y))

    bottom_edge = []
    x = 0
    y = center_y + base_width // 2
    if bitmask & DIR_SOUTH:
        y = int(tile_sz * 0.3)
    while x < tile_sz:
        bottom_edge.append((x, y))
        x += 1
        coord_seed = var * 151 + bitmask * 23 + x * 5
        coord_rng = random.Random(coord_seed)
        y += coord_rng.randint(-3, 3)
        y = max(tile_sz // 6, min(5 * tile_sz // 6, y))

    embankment_offset = 2
    for x in range(tile_sz):
        if x < len(top_edge) and x < len(bottom_edge):
            y_top = top_edge[x][1] - embankment_offset
            y_bottom = bottom_edge[x][1] + embankment_offset
            if y_top > y_bottom:
                y_top, y_bottom = y_bottom, y_top
            for y in range(y_top, y_bottom):
                if 0 <= y < tile_sz:
                    edge_dist = min(abs(y - y_top), abs(y - y_bottom))
                    if edge_dist <= embankment_offset + 1:
                        pixels[x, y] = embankment_color

    for x in range(tile_sz):
        if x < len(top_edge) and x < len(bottom_edge):
            y_top = top_edge[x][1]
            y_bottom = bottom_edge[x][1]
            if y_top > y_bottom:
                y_top, y_bottom = y_bottom, y_top
            for y in range(y_top, y_bottom):
                if 0 <= y < tile_sz:
                    r = rng.random()
                    if r > 0.80:
                        pixels[x, y] = hedge_dark
                    elif r > 0.35:
                        pixels[x, y] = hedge_base
                    elif r > 0.15:
                        pixels[x, y] = hedge_light
                    else:
                        pixels[x, y] = (65, 105, 42)

    num_leaf_clusters = rng.randint(15, 25)
    for _ in range(num_leaf_clusters):
        lx = rng.randint(tile_sz // 8, 7 * tile_sz // 8)
        ly = rng.randint(tile_sz // 6, 5 * tile_sz // 6)
        cluster_size = rng.randint(2, 4)
        if (
            lx < len(top_edge)
            and ly > top_edge[min(lx, len(top_edge) - 1)][1]
            and ly < bottom_edge[min(lx, len(bottom_edge) - 1)][1]
        ):
            leaf_color = rng.choice(
                [
                    (55, 95, 35),
                    (70, 115, 45),
                    (40, 75, 28),
                    (85, 130, 50),
                ]
            )
            for dy in range(cluster_size):
                for dx in range(cluster_size):
                    if 0 <= lx + dx < tile_sz and 0 <= ly + dy < tile_sz:
                        if rng.random() > 0.4:
                            pixels[lx + dx, ly + dy] = leaf_color

    if edge_widths["west"] > 0 and not (bitmask & DIR_WEST):
        taper_width = min(edge_widths["west"], 10)
        for x in range(taper_width):
            taper_factor = x / taper_width
            for y in range(tile_sz):
                if rng.random() > taper_factor * 0.8:
                    r, g, b = int(pixels[x, y][0]), int(pixels[x, y][1]), int(pixels[x, y][2])
                    pixels[x, y] = (
                        int(r + (ground_color[0] - r) * (1 - taper_factor)),
                        int(g + (ground_color[1] - g) * (1 - taper_factor)),
                        int(b + (ground_color[2] - b) * (1 - taper_factor)),
                    )

    if edge_widths["east"] > 0 and not (bitmask & DIR_EAST):
        taper_width = min(edge_widths["east"], 10)
        for x in range(tile_sz - taper_width, tile_sz):
            dist_from_east = tile_sz - 1 - x
            taper_factor = dist_from_east / taper_width
            for y in range(tile_sz):
                if rng.random() > taper_factor * 0.8:
                    r, g, b = int(pixels[x, y][0]), int(pixels[x, y][1]), int(pixels[x, y][2])
                    pixels[x, y] = (
                        int(r + (ground_color[0] - r) * (1 - taper_factor)),
                        int(g + (ground_color[1] - g) * (1 - taper_factor)),
                        int(b + (ground_color[2] - b) * (1 - taper_factor)),
                    )

    num_bushes = rng.randint(9, 15)
    for _ in range(num_bushes):
        cx = rng.randint(tile_sz // 6, 5 * tile_sz // 6)
        cy = rng.randint(tile_sz // 4, 3 * tile_sz // 4)
        radius_x = rng.randint(5, 10)
        radius_y = rng.randint(4, 9)
        for y in range(max(0, cy - radius_y), min(tile_sz, cy + radius_y + 1)):
            for x in range(max(0, cx - radius_x), min(tile_sz, cx + radius_x + 1)):
                if radius_x > 0 and radius_y > 0:
                    norm_dist = ((x - cx) / radius_x) ** 2 + ((y - cy) / radius_y) ** 2
                    if norm_dist <= 1.0:
                        if y >= tile_sz // 4 and y <= 3 * tile_sz // 4:
                            if norm_dist > 0.7:
                                pixels[x, y] = hedge_dark
                            elif norm_dist > 0.4:
                                pixels[x, y] = hedge_base
                            else:
                                pixels[x, y] = hedge_light

    leaf_color = (52, 98, 36)
    num_leaves = rng.randint(45, 75)
    for _ in range(num_leaves):
        lx = rng.randint(2, tile_sz - 3)
        ly = rng.randint(tile_sz // 5, 4 * tile_sz // 5)
        if lx < len(top_edge) and lx < len(bottom_edge):
            y_top = top_edge[lx][1]
            y_bottom = bottom_edge[lx][1]
            if y_top <= ly <= y_bottom:
                pixels[lx, ly] = leaf_color
                if rng.random() > 0.65:
                    dx, dy = rng.choice([(1, 0), (0, 1), (-1, 0), (0, -1)])
                    if 0 <= lx + dx < tile_sz and 0 <= ly + dy < tile_sz:
                        pixels[lx + dx, ly + dy] = (
                            min(255, leaf_color[0] + 15),
                            min(255, leaf_color[1] + 10),
                            min(255, leaf_color[2] + 12),
                        )

    del pixels


def _texture_rough(surface: pygame.Surface, tid: int, var: int, pal, bitmask: int = 0) -> None:
    """ROUGH (9): Brown dirt/rubble with scattered rocks."""
    from .texture_basic import _fill_with_variation

    rng = random.Random(var * 193)
    base = (155, 130, 85)
    _fill_with_variation(surface, base, rng, 18)

    pixels = pygame.surfarray.pixels3d(surface)
    tile_sz = TILE_SIZE

    rock_colors = [(120, 115, 105), (140, 135, 125), (100, 95, 85)]
    num_rocks = rng.randint(12, 20)
    for _ in range(num_rocks):
        rx = rng.randint(tile_sz // 16, tile_sz - tile_sz // 16)
        ry = rng.randint(tile_sz // 16, tile_sz - tile_sz // 16)
        size = rng.randint(2, 5)
        rock_color = rng.choice(rock_colors)
        for dy in range(size):
            for dx in range(size):
                if 0 <= rx + dx < tile_sz and 0 <= ry + dy < tile_sz:
                    pixels[rx + dx, ry + dy] = rock_color

    num_patches = rng.randint(7, 12)
    for _ in range(num_patches):
        dx = rng.randint(tile_sz // 8, tile_sz - tile_sz // 6)
        dy = rng.randint(tile_sz // 8, tile_sz - tile_sz // 6)
        dirt_color = (135, 110, 70)
        patch_size_y = rng.randint(2, 5)
        patch_size_x = rng.randint(2, 5)
        for ddy in range(patch_size_y):
            for ddx in range(patch_size_x):
                if 0 <= dx + ddx < tile_sz and 0 <= dy + ddy < tile_sz:
                    pixels[dx + ddx, dy + ddy] = dirt_color
    del pixels
