"""CC2-authentic procedural texture generator.

Extracted from enhanced_renderer.py in v0.3.6 refactoring.
Generates 48×48 pixel art terrain tiles matching original Close Combat 2 visuals.

Dependencies:
- pygame (Surface operations, surfarray)
- random (per-tile variation)
- PaletteGenerator (color palette generation)
- CC2_TERRAIN_PALETTE, TERRAIN_PALETTE_MAP (terrain color constants)
"""

from __future__ import annotations

import logging
import math
import random

import pygame

from .palette_generator import PaletteGenerator
from .terrain_tile_cache import CC2_TERRAIN_PALETTE


class ProceduralTextureGenerator:
    """
    Generates CC2-authentic pixel art textures procedurally.

    Creates 48×48 tile appearances matching original Close Combat 2 visuals.
    Each terrain type generates a visually distinct and recognizable tile
    with subtle per-tile variation to avoid repetitive patterns.
    """

    TILE_SIZE = 48  # CC2 authentic: 48×48 pixel tiles

    @classmethod
    def generate_terrain_texture(
        cls,
        terrain_id: int,
        variation: int = 0,
        palette: PaletteGenerator | None = None,
        bitmask: int = 0,
    ) -> pygame.Surface:
        """Generate a textured tile surface for given terrain type with autotile support.

        Args:
            terrain_id: Terrain type ID (0-13)
            variation: Variation seed for procedural generation
            palette: Color palette generator
            bitmask: Autotile neighbor bitmap for cross-tile continuity (0-15)
        """
        if palette is None:
            palette = PaletteGenerator()

        surface = pygame.Surface((cls.TILE_SIZE, cls.TILE_SIZE), pygame.SRCALPHA)

        texture_funcs = {
            0: cls._texture_open,
            1: cls._texture_road,
            2: cls._texture_grass,
            3: cls._texture_woods,
            4: cls._texture_building_enterable,
            5: cls._texture_building_solid,
            6: cls._texture_water,
            7: cls._texture_hedge,
            8: cls._texture_wall,
            9: cls._texture_rough,
            10: cls._texture_shallow,
            11: cls._texture_bridge,
            12: cls._texture_crater,
            13: cls._texture_trench,
        }

        func = texture_funcs.get(terrain_id, cls._texture_default)
        func(surface, terrain_id, variation, palette, bitmask)

        return surface

    @staticmethod
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

    @staticmethod
    def _texture_open(
        surface: pygame.Surface, tid: int, var: int, pal: PaletteGenerator, bitmask: int = 0
    ) -> None:
        """OPEN (0): CC2 authentic grass with visible grass blades and dirt spots."""
        rng = random.Random(var * 17)
        base = CC2_TERRAIN_PALETTE["grass_base"]
        ProceduralTextureGenerator._fill_with_variation(surface, base, rng, 12)

        pixels = pygame.surfarray.pixels3d(surface)
        tile_sz = ProceduralTextureGenerator.TILE_SIZE

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
                                    int(
                                        grass_light[0] * (1 - blend_factor) + r_base * blend_factor
                                    ),
                                    int(
                                        grass_light[1] * (1 - blend_factor) + g_base * blend_factor
                                    ),
                                    int(
                                        grass_light[2] * (1 - blend_factor) + b_base * blend_factor
                                    ),
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

    @staticmethod
    def _texture_road(
        surface: pygame.Surface, tid: int, var: int, pal: PaletteGenerator, bitmask: int = 0
    ) -> None:
        """ROAD (1): CC2 authentic gravel road with texture and autotile continuity."""
        from pycc2.presentation.rendering.autotile_system import (
            get_edge_transition_width,
        )

        rng = random.Random(var * 67)
        road_color = CC2_TERRAIN_PALETTE["road_base"]
        surface.fill(road_color)
        pixels = pygame.surfarray.pixels3d(surface)
        tile_sz = ProceduralTextureGenerator.TILE_SIZE

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
                gradient_factor = (
                    dist_from_west / edge_widths["west"] if edge_widths["west"] > 0 else 0
                )
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
                gradient_factor = (
                    dist_from_east / edge_widths["east"] if edge_widths["east"] > 0 else 0
                )
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

    @staticmethod
    def _texture_grass(
        surface: pygame.Surface, tid: int, var: int, pal: PaletteGenerator, bitmask: int = 0
    ) -> None:
        """GRASS (2): Medium green with visible grass blades and dirt spots."""
        rng = random.Random(var * 31)
        base = (105, 165, 55)
        ProceduralTextureGenerator._fill_with_variation(surface, base, rng, 14)

        pixels = pygame.surfarray.pixels3d(surface)
        tile_sz = ProceduralTextureGenerator.TILE_SIZE

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

    @staticmethod
    def _texture_woods(
        surface: pygame.Surface, tid: int, var: int, pal: PaletteGenerator, bitmask: int = 0
    ) -> None:
        """WOODS (3): CC2 very dark green forest with individual tree canopies visible."""
        rng = random.Random(var * 41)
        base = (45, 68, 33)
        surface.fill(base)
        pixels = pygame.surfarray.pixels3d(surface)
        tile_sz = ProceduralTextureGenerator.TILE_SIZE

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

    @staticmethod
    def _texture_building_enterable(
        surface: pygame.Surface, tid: int, var: int, pal: PaletteGenerator, bitmask: int = 0
    ) -> None:
        """BUILDING_ENTERABLE (4): CC2 earthy brown building with visible roof, door, windows."""
        rng = random.Random(var * 103)
        wall_color = (139, 115, 85)
        surface.fill(wall_color)
        pixels = pygame.surfarray.pixels3d(surface)
        tile_sz = ProceduralTextureGenerator.TILE_SIZE

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

    @staticmethod
    def _texture_building_solid(
        surface: pygame.Surface, tid: int, var: int, pal: PaletteGenerator, bitmask: int = 0
    ) -> None:
        """BUILDING_SOLID (5): Gray stone/brick building, no door, solid walls, roof line."""
        rng = random.Random(var * 109)
        wall_color = (140, 138, 135)
        surface.fill(wall_color)
        pixels = pygame.surfarray.pixels3d(surface)
        tile_sz = ProceduralTextureGenerator.TILE_SIZE

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

    @staticmethod
    def _texture_water(
        surface: pygame.Surface, tid: int, var: int, pal: PaletteGenerator, bitmask: int = 0
    ) -> None:
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
        tile_sz = ProceduralTextureGenerator.TILE_SIZE

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

    @staticmethod
    def _texture_hedge(
        surface: pygame.Surface, tid: int, var: int, pal: PaletteGenerator, bitmask: int = 0
    ) -> None:
        """HEDGE (7): CC2 authentic Normandy bocage hedgerow."""
        from pycc2.presentation.rendering.autotile_system import (
            DIR_EAST,
            DIR_NORTH,
            DIR_SOUTH,
            DIR_WEST,
            get_edge_transition_width,
        )

        rng = random.Random(var * 151)
        tile_sz = ProceduralTextureGenerator.TILE_SIZE
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

    @staticmethod
    def _texture_wall(
        surface: pygame.Surface, tid: int, var: int, pal: PaletteGenerator, bitmask: int = 0
    ) -> None:
        """WALL (8): Gray brick wall with mortar lines."""
        rng = random.Random(var * 173)
        wall_color = (130, 128, 125)
        surface.fill(wall_color)
        pixels = pygame.surfarray.pixels3d(surface)
        tile_sz = ProceduralTextureGenerator.TILE_SIZE

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

    @staticmethod
    def _texture_rough(
        surface: pygame.Surface, tid: int, var: int, pal: PaletteGenerator, bitmask: int = 0
    ) -> None:
        """ROUGH (9): Brown dirt/rubble with scattered rocks."""
        rng = random.Random(var * 193)
        base = (155, 130, 85)
        ProceduralTextureGenerator._fill_with_variation(surface, base, rng, 18)

        pixels = pygame.surfarray.pixels3d(surface)
        tile_sz = ProceduralTextureGenerator.TILE_SIZE

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

    @staticmethod
    def _texture_shallow(
        surface: pygame.Surface, tid: int, var: int, pal: PaletteGenerator, bitmask: int = 0
    ) -> None:
        """SHALLOW (10): Light blue shallow water with sandy bottom visible."""
        rng = random.Random(var * 211)
        base = (120, 185, 225)
        surface.fill(base)
        pixels = pygame.surfarray.pixels3d(surface)
        tile_sz = ProceduralTextureGenerator.TILE_SIZE

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

    @staticmethod
    def _texture_bridge(
        surface: pygame.Surface, tid: int, var: int, pal: PaletteGenerator, bitmask: int = 0
    ) -> None:
        """BRIDGE (11): Enhanced wooden/concrete bridge with texture and railings."""
        rng = random.Random(var * 241)
        tile_sz = ProceduralTextureGenerator.TILE_SIZE
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
                                    water_color[i] * (1 - alpha_factor)
                                    + shadow_color[i] * alpha_factor
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

    @staticmethod
    def _texture_crater(
        surface: pygame.Surface, tid: int, var: int, pal: PaletteGenerator, bitmask: int = 0
    ) -> None:
        """CRATER (12): CC2 authentic shell crater with elliptical depression and bright rim."""
        rng = random.Random(var * 331)
        tile_sz = ProceduralTextureGenerator.TILE_SIZE
        base = (90, 75, 60)
        ProceduralTextureGenerator._fill_with_variation(surface, base, rng, 10)

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
                                        int(
                                            rim_color[0] * brightness_factor + rng.randint(-10, 10)
                                        ),
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
                                        int(
                                            rim_color[2] * brightness_factor + rng.randint(-12, 12)
                                        ),
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

    @staticmethod
    def _texture_trench(
        surface: pygame.Surface, tid: int, var: int, pal: PaletteGenerator, bitmask: int = 0
    ) -> None:
        """TRENCH (13): Defensive earthwork line."""
        from pycc2.presentation.rendering.autotile_system import (
            DIR_EAST,
            DIR_WEST,
            get_edge_transition_width,
        )

        rng = random.Random(var * 397)
        tile_sz = ProceduralTextureGenerator.TILE_SIZE
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

    @staticmethod
    def _texture_default(
        surface: pygame.Surface, tid: int, var: int, pal: PaletteGenerator, bitmask: int = 0
    ) -> None:
        """Fallback simple noise texture."""
        rng = random.Random(var * 277)
        base = pal.get_color(tid, 4)
        ProceduralTextureGenerator._fill_with_variation(surface, base, rng, 15)


__all__ = ["ProceduralTextureGenerator"]
