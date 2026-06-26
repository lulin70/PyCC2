"""Basic terrain textures: open ground, roads, grass, and fallback."""

from __future__ import annotations

import math
import random

import pygame

from .terrain_tile_cache import CC2_TERRAIN_PALETTE

TILE_SIZE = 48


def _fill_with_variation(
    surface: pygame.Surface, base_color: tuple, rng: random.Random, intensity: int = 12
) -> None:
    """Fill surface with base color and subtle pixel-level variation (±10% brightness)."""
    surface.fill(base_color)
    try:
        pixels = pygame.surfarray.pixels3d(surface)
        w, h = surface.get_size()
        for y in range(h):
            for x in range(w):
                offset = rng.randint(-intensity, intensity)
                r, g, b = int(pixels[x, y][0]), int(pixels[x, y][1]), int(pixels[x, y][2])
                new_r = max(0, min(255, r + offset))
                new_g = max(0, min(255, g + offset))
                new_b = max(0, min(255, b + offset))
                pixels[x, y] = (new_r, new_g, new_b)
        del pixels
    except (ValueError, IndexError):
        pass  # Fallback: just use base color


def _texture_open(surface: pygame.Surface, tid: int, var: int, pal, bitmask: int = 0) -> None:
    """OPEN (0): CC2 authentic grass with visible grass blades and dirt spots."""
    from .texture_basic import _fill_with_variation

    rng = random.Random(var * 17)
    base = CC2_TERRAIN_PALETTE["grass_base"]
    _fill_with_variation(surface, base, rng, 12)

    pixels = pygame.surfarray.pixels3d(surface)
    tile_sz = TILE_SIZE

    grass_dark = CC2_TERRAIN_PALETTE["grass_dark"]
    num_blades = rng.randint(30, 50)
    for _ in range(num_blades):
        x = rng.randint(0, tile_sz - 1)
        y_start = rng.randint(0, tile_sz - 4)
        blade_len = rng.randint(2, 3)
        shade_var = rng.randint(-8, 8)
        blade_color = (
            max(0, min(255, grass_dark[0] + shade_var)),
            max(0, min(255, grass_dark[1] + shade_var)),
            max(0, min(255, grass_dark[2] + shade_var)),
        )
        for dy in range(blade_len):
            py = y_start + dy
            if 0 <= py < tile_sz:
                pixels[x, py] = blade_color

    grass_light = CC2_TERRAIN_PALETTE["grass_light"]
    num_patches = rng.randint(6, 10)
    for _ in range(num_patches):
        cx = rng.randint(5, tile_sz - 5)
        cy = rng.randint(5, tile_sz - 5)
        radius = rng.randint(3, 5)
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx * dx + dy * dy <= radius * radius:
                    px, py = cx + dx, cy + dy
                    if 0 <= px < tile_sz and 0 <= py < tile_sz:
                        dist_from_center = math.sqrt(dx * dx + dy * dy) / radius
                        if dist_from_center > 0.7:
                            blend_factor = (dist_from_center - 0.7) / 0.3
                            base_px = pixels[px, py]
                            try:
                                r_base = (
                                    int(base_px[0][0])
                                    if hasattr(base_px[0], "__len__")
                                    else int(base_px[0])
                                )
                                g_base = (
                                    int(base_px[1][0])
                                    if hasattr(base_px[1], "__len__")
                                    else int(base_px[1])
                                )
                                b_base = (
                                    int(base_px[2][0])
                                    if hasattr(base_px[2], "__len__")
                                    else int(base_px[2])
                                )
                            except (IndexError, TypeError):
                                r_base, g_base, b_base = (
                                    int(base_px[0]),
                                    int(base_px[1]),
                                    int(base_px[2]),
                                )

                            pixels[px, py] = (
                                int(grass_light[0] * (1 - blend_factor) + r_base * blend_factor),
                                int(grass_light[1] * (1 - blend_factor) + g_base * blend_factor),
                                int(grass_light[2] * (1 - blend_factor) + b_base * blend_factor),
                            )
                        else:
                            pixels[px, py] = grass_light

    dirt_color = CC2_TERRAIN_PALETTE.get("dirt_base", (139, 109, 59))
    num_dirt = rng.randint(3, 6)
    for _ in range(num_dirt):
        cx = rng.randint(3, tile_sz - 4)
        cy = rng.randint(3, tile_sz - 4)
        for dy in range(3):
            for dx in range(3):
                px, py = cx + dx, cy + dy
                if 0 <= px < tile_sz and 0 <= py < tile_sz and rng.random() > 0.2:
                    dirt_var = rng.randint(-10, 10)
                    pixels[px, py] = (
                        max(0, min(255, dirt_color[0] + dirt_var)),
                        max(0, min(255, dirt_color[1] + dirt_var)),
                        max(0, min(255, dirt_color[2] + dirt_var)),
                    )

    del pixels


def _texture_road(surface: pygame.Surface, tid: int, var: int, pal, bitmask: int = 0) -> None:
    """ROAD (1): CC2 authentic gravel road with texture and autotile continuity."""
    from pycc2.presentation.rendering.autotile_system import (
        get_edge_transition_width,
    )

    rng = random.Random(var * 67)
    road_color = CC2_TERRAIN_PALETTE["road_base"]
    surface.fill(road_color)
    pixels = pygame.surfarray.pixels3d(surface)
    tile_sz = TILE_SIZE

    edge_widths = get_edge_transition_width(tid, bitmask, tile_sz)
    CC2_TERRAIN_PALETTE["road_dark"]

    if edge_widths["north"] > 0:
        for x in range(tile_sz):
            for y in range(edge_widths["north"]):
                gradient_factor = y / edge_widths["north"] if edge_widths["north"] > 0 else 0
                darkness = int((1.0 - gradient_factor) * 40)
                if rng.random() > 0.3:
                    r, g, b = int(pixels[x, y][0]), int(pixels[x, y][1]), int(pixels[x, y][2])
                    pixels[x, y] = (
                        max(0, r - darkness),
                        max(0, g - darkness),
                        max(0, b - darkness),
                    )

    if edge_widths["south"] > 0:
        for x in range(tile_sz):
            for y in range(tile_sz - edge_widths["south"], tile_sz):
                dist_from_south = tile_sz - 1 - y
                gradient_factor = (
                    dist_from_south / edge_widths["south"] if edge_widths["south"] > 0 else 0
                )
                darkness = int((1.0 - gradient_factor) * 40)
                if rng.random() > 0.3:
                    r, g, b = int(pixels[x, y][0]), int(pixels[x, y][1]), int(pixels[x, y][2])
                    pixels[x, y] = (
                        max(0, r - darkness),
                        max(0, g - darkness),
                        max(0, b - darkness),
                    )

    if edge_widths["west"] > 0:
        for x in range(edge_widths["west"]):
            dist_from_west = x
            gradient_factor = dist_from_west / edge_widths["west"] if edge_widths["west"] > 0 else 0
            darkness = int((1.0 - gradient_factor) * 40)
            if rng.random() > 0.3:
                for y in range(tile_sz):
                    r, g, b = int(pixels[x, y][0]), int(pixels[x, y][1]), int(pixels[x, y][2])
                    pixels[x, y] = (
                        max(0, r - darkness),
                        max(0, g - darkness),
                        max(0, b - darkness),
                    )

    if edge_widths["east"] > 0:
        for x in range(tile_sz - edge_widths["east"], tile_sz):
            dist_from_east = tile_sz - 1 - x
            gradient_factor = dist_from_east / edge_widths["east"] if edge_widths["east"] > 0 else 0
            darkness = int((1.0 - gradient_factor) * 40)
            if rng.random() > 0.3:
                for y in range(tile_sz):
                    r, g, b = int(pixels[x, y][0]), int(pixels[x, y][1]), int(pixels[x, y][2])
                    pixels[x, y] = (
                        max(0, r - darkness),
                        max(0, g - darkness),
                        max(0, b - darkness),
                    )

    road_stone = CC2_TERRAIN_PALETTE["road_stone"]
    num_pebbles = rng.randint(60, 85)
    for _ in range(num_pebbles):
        px = rng.randint(
            max(2, min(edge_widths.values())), tile_sz - max(2, min(edge_widths.values())) - 2
        )
        py = rng.randint(
            max(2, min(edge_widths.values())), tile_sz - max(2, min(edge_widths.values())) - 2
        )
        pebble_var = rng.randint(-18, 18)
        pixels[px, py] = tuple(max(0, min(255, c + pebble_var)) for c in road_stone)
        if rng.random() > 0.55:
            dx, dy = rng.choice([(1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, -1)])
            if max(2, min(edge_widths.values())) <= px + dx < tile_sz - max(
                2, min(edge_widths.values())
            ) and max(2, min(edge_widths.values())) <= py + dy < tile_sz - max(
                2, min(edge_widths.values())
            ):
                pixels[px + dx, py + dy] = tuple(
                    max(0, min(255, c + pebble_var - 10)) for c in road_stone
                )

    track_color = CC2_TERRAIN_PALETTE["road_dark"]
    num_tracks = rng.randint(2, 4)
    track_positions = sorted([tile_sz // 5 + i * (tile_sz // 5) for i in range(num_tracks)])

    for track_y in track_positions:
        for x in range(tile_sz):
            if rng.random() > 0.3:
                min_edge = max(3, min(edge_widths.values()))
                if min_edge <= track_y < tile_sz - min_edge:
                    pixels[x, track_y] = track_color
                    if 0 <= track_y + 1 < tile_sz and rng.random() > 0.4:
                        pixels[x, track_y + 1] = tuple(max(0, c + 12) for c in track_color)
                    if rng.random() > 0.85 and 0 <= track_y - 1 < tile_sz:
                        pixels[x, track_y - 1] = tuple(max(0, c + 8) for c in track_color)

    crack_color = tuple(max(0, c - 30) for c in road_color)
    num_cracks = rng.randint(3, 6)
    for _ in range(num_cracks):
        cx = rng.randint(4, tile_sz - 8)
        cy = rng.randint(4, tile_sz - 4)
        crack_len = rng.randint(5, 12)
        crack_angle = rng.uniform(-0.4, 0.4)
        for i in range(crack_len):
            px = cx + i
            py = cy + int(i * math.sin(crack_angle))
            if 0 <= px < tile_sz and 0 <= py < tile_sz:
                pixels[px, py] = crack_color

    del pixels


def _texture_grass(surface: pygame.Surface, tid: int, var: int, pal, bitmask: int = 0) -> None:
    """GRASS (2): Medium green with visible grass blades and dirt spots."""
    from .texture_basic import _fill_with_variation

    rng = random.Random(var * 31)
    base = (105, 165, 55)
    _fill_with_variation(surface, base, rng, 14)

    pixels = pygame.surfarray.pixels3d(surface)
    tile_sz = TILE_SIZE

    num_blades = rng.randint(40, 60)
    for _ in range(num_blades):
        x = rng.randint(0, tile_sz - 1)
        y_start = rng.randint(0, tile_sz - 4)
        blade_len = rng.randint(2, 3)
        shade = rng.choice(
            [
                (90, 150, 45),
                (120, 180, 65),
                (85, 140, 40),
                (110, 170, 55),
                (100, 160, 50),
            ]
        )
        for dy in range(blade_len):
            if 0 <= y_start + dy < tile_sz:
                pixels[x, y_start + dy] = shade

    dirt_color = CC2_TERRAIN_PALETTE.get("dirt_base", (139, 109, 59))
    num_dirt = rng.randint(3, 6)
    for _ in range(num_dirt):
        cx = rng.randint(3, tile_sz - 4)
        cy = rng.randint(3, tile_sz - 4)
        for ddy in range(3):
            for ddx in range(3):
                px, py = cx + ddx, cy + ddy
                if 0 <= px < tile_sz and 0 <= py < tile_sz and rng.random() > 0.2:
                    dirt_var = rng.randint(-10, 10)
                    pixels[px, py] = (
                        max(0, min(255, dirt_color[0] + dirt_var)),
                        max(0, min(255, dirt_color[1] + dirt_var)),
                        max(0, min(255, dirt_color[2] + dirt_var)),
                    )

    num_patches = rng.randint(4, 8)
    for _ in range(num_patches):
        cx = rng.randint(tile_sz // 10, tile_sz - tile_sz // 10)
        cy = rng.randint(tile_sz // 10, tile_sz - tile_sz // 10)
        patch_size = rng.randint(2, 4)
        for ddy in range(patch_size):
            for ddx in range(patch_size):
                if 0 <= cx + ddx < tile_sz and 0 <= cy + ddy < tile_sz:
                    pixels[cx + ddx, cy + ddy] = (80, 130, 35)
    del pixels


def _texture_default(surface: pygame.Surface, tid: int, var: int, pal, bitmask: int = 0) -> None:
    """Fallback simple noise texture."""
    from .texture_basic import _fill_with_variation

    rng = random.Random(var * 277)
    base = pal.get_color(tid, 4)
    _fill_with_variation(surface, base, rng, 15)
