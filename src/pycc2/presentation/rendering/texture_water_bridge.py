"""Water feature textures: deep water, shallow water/fords, bridges."""

from __future__ import annotations

import math
import random

import pygame

from ..visual_config import DEFAULT_VISUAL_CONFIG
from .terrain_tile_cache import CC2_TERRAIN_PALETTE

# V-01 (Wave C3b): TILE_SIZE migrated to DEFAULT_VISUAL_CONFIG for theme hot-reload.
TILE_SIZE = DEFAULT_VISUAL_CONFIG.dimensions.TILE_SIZE


def _texture_water(surface: pygame.Surface, tid: int, var: int, pal, bitmask: int = 0) -> None:
    """WATER (6): CC2 authentic water with wave animation hints and autotile continuity."""
    from pycc2.presentation.rendering.autotile_system import (
        DIR_EAST,
        DIR_NORTH,
        DIR_SOUTH,
        DIR_WEST,
        get_edge_transition_width,
    )

    rng = random.Random(var * 127)
    base = CC2_TERRAIN_PALETTE["water_base"]
    surface.fill(base)
    pixels = pygame.surfarray.pixels3d(surface)
    tile_sz = TILE_SIZE

    water_light_row = tuple(min(255, c + 15) for c in base)
    water_dark_row = tuple(max(0, c - 10) for c in base)
    for y in range(tile_sz):
        wave_cycle = y % 4
        row_color = water_light_row if wave_cycle < 2 else water_dark_row
        for x in range(tile_sz):
            offset = rng.randint(-5, 5)
            r, g, b = row_color
            pixels[x, y] = (
                max(0, min(255, r + offset)),
                max(0, min(255, g + offset)),
                max(0, min(255, b + offset)),
            )

    water_light = CC2_TERRAIN_PALETTE["water_light"]
    num_waves = rng.randint(12, 20)
    for _i in range(num_waves):
        wy = rng.randint(3, tile_sz - 3)
        wx_start = rng.randint(2, tile_sz - 6)
        wave_len = rng.randint(4, 8)
        wave_amp = rng.randint(1, 2)
        wave_freq = rng.uniform(0.3, 0.8)
        wave_phase = rng.uniform(0, 2 * math.pi)
        for j in range(wave_len):
            wx = wx_start + j
            if 0 <= wx < tile_sz:
                wy_offset = int(wave_amp * math.sin(wave_freq * wx + wave_phase))
                if 0 <= wy + wy_offset < tile_sz:
                    pixels[wx, wy + wy_offset] = water_light

    glint_color = (220, 235, 250)
    num_glints = rng.randint(8, 14)
    for _ in range(num_glints):
        gx = rng.randint(3, tile_sz - 3)
        gy = rng.randint(3, tile_sz - 3)
        pixels[gx, gy] = glint_color

    CC2_TERRAIN_PALETTE["water_dark"]
    water_foam = CC2_TERRAIN_PALETTE["water_foam"]
    edge_widths = get_edge_transition_width(tid, bitmask, tile_sz)

    if not (bitmask & DIR_NORTH) and edge_widths["north"] > 0:
        ew = edge_widths["north"]
        for y in range(ew):
            gradient = y / ew
            darkness = int((1.0 - gradient) * 30)
            for x in range(tile_sz):
                r, g, b = int(pixels[x, y][0]), int(pixels[x, y][1]), int(pixels[x, y][2])
                pixels[x, y] = (
                    max(32, r - darkness),
                    max(72, g - darkness),
                    max(130, b - darkness),
                )
        for x in range(0, tile_sz, 2):
            pixels[x, 0] = water_foam

    if not (bitmask & DIR_SOUTH) and edge_widths["south"] > 0:
        ew = edge_widths["south"]
        for y in range(tile_sz - ew, tile_sz):
            dist = tile_sz - 1 - y
            gradient = dist / ew
            darkness = int((1.0 - gradient) * 30)
            for x in range(tile_sz):
                r, g, b = int(pixels[x, y][0]), int(pixels[x, y][1]), int(pixels[x, y][2])
                pixels[x, y] = (
                    max(32, r - darkness),
                    max(72, g - darkness),
                    max(130, b - darkness),
                )
        for x in range(0, tile_sz, 2):
            pixels[x, tile_sz - 1] = water_foam

    if not (bitmask & DIR_WEST) and edge_widths["west"] > 0:
        ew = edge_widths["west"]
        for x in range(ew):
            gradient = x / ew
            darkness = int((1.0 - gradient) * 30)
            for y in range(tile_sz):
                r, g, b = int(pixels[x, y][0]), int(pixels[x, y][1]), int(pixels[x, y][2])
                pixels[x, y] = (
                    max(32, r - darkness),
                    max(72, g - darkness),
                    max(130, b - darkness),
                )
        for y in range(0, tile_sz, 2):
            pixels[0, y] = water_foam

    if not (bitmask & DIR_EAST) and edge_widths["east"] > 0:
        ew = edge_widths["east"]
        for x in range(tile_sz - ew, tile_sz):
            dist = tile_sz - 1 - x
            gradient = dist / ew
            darkness = int((1.0 - gradient) * 30)
            for y in range(tile_sz):
                r, g, b = int(pixels[x, y][0]), int(pixels[x, y][1]), int(pixels[x, y][2])
                pixels[x, y] = (
                    max(32, r - darkness),
                    max(72, g - darkness),
                    max(130, b - darkness),
                )
        for y in range(0, tile_sz, 2):
            pixels[tile_sz - 1, y] = water_foam

    del pixels


def _texture_shallow(surface: pygame.Surface, tid: int, var: int, pal, bitmask: int = 0) -> None:
    """SHALLOW (10): Light blue shallow water with sandy bottom visible."""
    rng = random.Random(var * 211)
    base = (120, 185, 225)
    surface.fill(base)
    pixels = pygame.surfarray.pixels3d(surface)
    tile_sz = TILE_SIZE

    sand_color = (195, 180, 140)
    num_sand_patches = rng.randint(20, 35)
    for _ in range(num_sand_patches):
        sx = rng.randint(tile_sz // 16, tile_sz - tile_sz // 16)
        sy = rng.randint(tile_sz // 16, tile_sz - tile_sz // 16)
        size = rng.randint(2, 6)
        for dy in range(size):
            for dx in range(size):
                if 0 <= sx + dx < tile_sz and 0 <= sy + dy < tile_sz and rng.random() > 0.4:
                    pixels[sx + dx, sy + dy] = sand_color

    ripple_color = (150, 205, 240)
    ripple_spacing_y = max(4, tile_sz // 8)
    for y in range(ripple_spacing_y, tile_sz - ripple_spacing_y, ripple_spacing_y):
        for x in range(tile_sz):
            wy = y + int(math.sin(x * 0.5 + var) * 1.5)
            if 0 <= wy < tile_sz:
                pixels[x, wy] = ripple_color
    del pixels


def _texture_bridge(surface: pygame.Surface, tid: int, var: int, pal, bitmask: int = 0) -> None:
    """BRIDGE (11): Enhanced wooden/concrete bridge with texture and railings."""
    rng = random.Random(var * 241)
    tile_sz = TILE_SIZE
    water_color = (35, 70, 120)
    surface.fill(water_color)
    pixels = pygame.surfarray.pixels3d(surface)

    shadow_color = (25, 55, 95)
    pier_positions = [
        (tile_sz // 4, int(0.7 * tile_sz)),
        (int(0.58 * tile_sz), int(0.72 * tile_sz)),
    ]
    for pier_cx, pier_cy in pier_positions:
        pier_radius_x = max(3, tile_sz // 10)
        pier_radius_y = max(2, tile_sz // 14)
        for dy in range(-pier_radius_y, pier_radius_y + 1):
            for dx in range(-pier_radius_x, pier_radius_x + 1):
                sx, sy = pier_cx + dx, pier_cy + dy
                if 0 <= sx < tile_sz and 0 <= sy < tile_sz:
                    if (dx / pier_radius_x) ** 2 + (dy / pier_radius_y) ** 2 <= 1.0:
                        dist_ratio = math.sqrt(
                            (dx / pier_radius_x) ** 2 + (dy / pier_radius_y) ** 2
                        )
                        alpha_factor = 1.0 - dist_ratio * 0.5
                        pixels[sx, sy] = tuple(
                            int(
                                water_color[i] * (1 - alpha_factor) + shadow_color[i] * alpha_factor
                            )
                            for i in range(3)
                        )

    plank_color = (160, 120, 70)
    plank_dark = (130, 95, 55)
    deck_top = max(2, tile_sz // 8)
    deck_bottom = min(tile_sz - 2, int(0.54 * tile_sz))
    deck_left = max(1, tile_sz // 16)
    deck_right = min(tile_sz - 1, int(0.625 * tile_sz))

    for y in range(deck_top, deck_bottom):
        for x in range(deck_left, deck_right):
            pixels[x, y] = plank_color

    plank_spacing = max(3, tile_sz // 12)
    for y in range(deck_top, deck_bottom, plank_spacing):
        for x in range(deck_left, deck_right):
            if x < tile_sz and y < tile_sz:
                pixels[x, y] = plank_dark

    fine_plank_spacing = max(4, tile_sz // 10)
    fine_plank_color = (145, 108, 62)
    for y in range(deck_top + 2, deck_bottom - 1, fine_plank_spacing):
        for x in range(deck_left + 1, deck_right - 1):
            if x < tile_sz and y < tile_sz and rng.random() > 0.5:
                pixels[x, y] = fine_plank_color

    concrete_color = (150, 140, 130)
    concrete_dark = (130, 120, 110)
    concrete_spacing = max(6, tile_sz // 6)
    for y in range(deck_top + plank_spacing, deck_bottom - plank_spacing, concrete_spacing):
        for x in range(deck_left, deck_right):
            if x < tile_sz and y < tile_sz:
                if (y // plank_spacing) % 2 == 0:
                    pixels[x, y] = concrete_color
                else:
                    pixels[x, y] = concrete_dark

    grain_spacing_x = max(4, tile_sz // 8)
    for x in range(deck_left + grain_spacing_x, deck_right, grain_spacing_x):
        for y in range(deck_top, deck_bottom):
            if x < tile_sz and y < tile_sz:
                if rng.random() > 0.5:
                    pixels[x, y] = plank_dark
                elif rng.random() > 0.8:
                    pixels[x, y] = (175, 135, 85)

    beam_color = (110, 80, 45)
    beam_top = max(1, tile_sz // 12)
    beam_bottom = min(tile_sz - 1, int(0.58 * tile_sz))
    for y in range(beam_top, beam_bottom):
        if deck_left < tile_sz:
            pixels[deck_left, y] = beam_color
        if deck_left + 1 < tile_sz:
            pixels[deck_left + 1, y] = beam_color
        if deck_right - 1 >= 0:
            pixels[deck_right - 1, y] = beam_color
        if deck_right - 2 >= 0:
            pixels[deck_right - 2, y] = beam_color

    cross_beam_y_positions = [deck_top, deck_top + 1, deck_bottom - 1, deck_bottom - 2]
    for cross_y in cross_beam_y_positions:
        for x in range(deck_left, deck_right):
            if x < tile_sz and 0 <= cross_y < tile_sz:
                pixels[x, cross_y] = beam_color

    rail_post_spacing = max(5, tile_sz // 6)
    rail_post_top = max(1, tile_sz // 12)
    rail_post_bottom = min(tile_sz - 1, int(0.56 * tile_sz))

    top_rail_y = rail_post_top
    if top_rail_y < tile_sz:
        for x in range(deck_left, deck_right):
            if x < tile_sz:
                pixels[x, top_rail_y] = (90, 65, 35)

    bottom_rail_y = rail_post_bottom
    if bottom_rail_y < tile_sz:
        for x in range(deck_left, deck_right):
            if x < tile_sz:
                pixels[x, bottom_rail_y] = (90, 65, 35)

    for x in range(
        deck_left + rail_post_spacing, deck_right - rail_post_spacing // 2, rail_post_spacing
    ):
        for py in range(rail_post_top, min(rail_post_top + 3, tile_sz)):
            if 0 <= x < tile_sz and py < tile_sz:
                pixels[x, py] = beam_color
        for py in range(max(rail_post_bottom - 2, 0), rail_post_bottom):
            if 0 <= x < tile_sz and py < tile_sz:
                pixels[x, py] = beam_color

    del pixels
