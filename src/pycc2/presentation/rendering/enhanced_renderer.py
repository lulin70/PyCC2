"""
Enhanced Pixel Art Renderer for PyCC2 - Phase A4

Renders enhanced maps with pixel art aesthetics that surpass original CC2.
Features procedural texture generation, dynamic lighting, decoration sprites,
and atmospheric effects - all generated in code (no external assets needed).

Rendering Pipeline:
1. Base terrain layer (textured with variations)
2. Height shading (dynamic shadows/highlights)
3. Decoration sprites (trees, rocks, buildings, etc.)
4. Unit layer (soldiers, vehicles)
5. Effects layer (muzzle flash, explosions, weather)
6. Post-processing (color grading, vignette)

Visual Style: Enhanced Pixel Art
- Crisp 32x32 base tiles with sub-pixel detail
- Rich color palette (16+ colors per biome)
- Smooth height-based lighting
- Decorative sprite overlays
- Atmospheric depth effects
"""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING, Any

import pygame

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.domain.systems.enhanced_tile import EnhancedTile


class PaletteGenerator:
    """
    Generates rich color palettes for pixel art rendering.
    
    Creates harmonious color schemes for each terrain type with
    multiple shades for lighting variation.
    """
    
    def __init__(self, seed: int | None = 42):
        self._rng = random.Random(seed) if seed is not None else random
        self.palettes = self._generate_all_palettes()
    
    def _generate_all_palettes(self) -> dict[int, list[tuple[int, int, int]]]:
        """Generate 8-shade palettes for all terrain types using CC2's realistic palette."""
        return {
            # Terrain ID: [shadow, dark, mid-dark, mid, mid-light, light, highlight, bright]
            # Using CC2's actual muted, earthy color palette
            0: self._make_palette((76, 112, 52),    # OPEN/GRASS - CC2: not bright green
                hue_range=12, sat_range=0.08),
            1: self._make_palette((139, 119, 101),   # ROAD - CC2: dirt/gravel appearance
                hue_range=8, sat_range=0.1),
            2: self._make_palette((68, 105, 48),     # GRASS - darker variant
                hue_range=15, sat_range=0.1),
            3: self._make_palette((45, 68, 33),      # WOODS - CC2: very dark green
                hue_range=10, sat_range=0.06),
            4: self._make_palette((139, 115, 85),    # BUILDING_ENTERABLE - CC2: earthy brown
                hue_range=6, sat_range=0.04),
            5: self._make_palette((120, 118, 115),   # BUILDING_SOLID - gray stone
                hue_range=5, sat_range=0.03),
            6: self._make_palette((62, 87, 117),     # WATER - CC2: muted blue
                hue_range=6, sat_range=0.05),
            7: self._make_palette((85, 70, 55),      # HEDGE - dark brown-green
                hue_range=10, sat_range=0.08),
            8: self._make_palette((110, 108, 105),   # WALL - gray brick
                hue_range=5, sat_range=0.03),
            9: self._make_palette((135, 115, 80),    # ROUGH - brown/tan
                hue_range=12, sat_range=0.1),
            10: self._make_palette((95, 145, 165),   # SHALLOW - light blue-green
                hue_range=8, sat_range=0.06),
            11: self._make_palette((160, 140, 100),  # BRIDGE - wooden brown
                hue_range=10, sat_range=0.08),
        }
    
    def _make_palette(
        self, base_color: tuple[int, int, int],
        hue_range: float = 10, sat_range: float = 0.1
    ) -> list[tuple[int, int, int]]:
        """Generate 8-shade palette from base color."""
        palette = []
        r, g, b = base_color
        
        for i in range(8):
            factor = 0.3 + (i * 0.1)  # 0.3 to 1.0
            
            # Add slight variation for organic feel
            vary = self._rng.uniform(-hue_range, hue_range) if i > 0 else 0
            sat_vary = self._rng.uniform(-sat_range, sat_range) if i > 0 else 0
            
            new_r = max(0, min(255, int(r * factor + vary)))
            new_g = max(0, min(255, int(g * factor + vary * 0.8)))
            new_b = max(0, min(255, int(b * factor + vary * 1.2)))
            
            palette.append((new_r, new_g, new_b))
        
        return palette
    
    def get_color(self, terrain_id: int, shade: int = 4) -> tuple[int, int, int]:
        """Get specific shade for terrain type."""
        if terrain_id not in self.palettes:
            return (128, 128, 128)
        
        palette = self.palettes[terrain_id]
        shade = max(0, min(7, shade))
        return palette[shade]


class ProceduralTextureGenerator:
    """
    Generates pixel art textures procedurally.

    Creates varied tile appearances without external image files,
    using noise patterns and geometric primitives.
    Each terrain type generates a visually distinct and recognizable tile.
    """

    TILE_SIZE = 32

    @classmethod
    def generate_terrain_texture(
        cls, terrain_id: int, variation: int = 0, palette: 'PaletteGenerator' | None = None
    ) -> pygame.Surface:
        """Generate a textured tile surface for given terrain type."""
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
        }

        func = texture_funcs.get(terrain_id, cls._texture_default)
        func(surface, terrain_id, variation, palette)

        return surface

    @staticmethod
    def _fill_with_variation(surface: pygame.Surface, base_color: tuple, rng: random.Random, intensity: int = 12) -> None:
        """Fill surface with base color and subtle pixel-level variation."""
        surface.fill(base_color)
        try:
            pixels = pygame.surfarray.pixels3d(surface)
            w, h = surface.get_size()
            for y in range(h):
                for x in range(w):
                    offset = rng.randint(-intensity, intensity)
                    # Safe: convert to int first to avoid uint8 overflow
                    r, g, b = int(pixels[x, y][0]), int(pixels[x, y][1]), int(pixels[x, y][2])
                    new_r = max(0, min(255, r + offset))
                    new_g = max(0, min(255, g + offset))
                    new_b = max(0, min(255, b + offset))
                    pixels[x, y] = (new_r, new_g, new_b)
            del pixels
        except Exception as e:
            pass  # Fallback: just use base color

    @staticmethod
    def _texture_open(
        surface: pygame.Surface, tid: int, var: int, pal: 'PaletteGenerator'
    ) -> None:
        """OPEN (0): CC2 realistic grass with rich texture and natural variation."""
        rng = random.Random(var * 17)
        # CC2's muted grass green - slightly darker for more realism
        base = (72, 108, 50)
        ProceduralTextureGenerator._fill_with_variation(surface, base, rng, 10)

        pixels = pygame.surfarray.pixels3d(surface)

        # Dense grass blade pattern (more blades for richer texture)
        for _ in range(35):
            x = rng.randint(0, 31)
            y = rng.randint(0, 31)
            blade_color = (64, 100, 44)  # Darker green
            pixels[x, y] = blade_color
            # Grass clusters (2-4 pixels) - more natural grouping
            if rng.random() > 0.5:
                cluster_size = rng.randint(2, 4)
                for i in range(cluster_size):
                    dx, dy = [(1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, -1)][i % 6]
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < 32 and 0 <= ny < 32:
                        shade_var = rng.randint(-8, 8)
                        pixels[nx, ny] = (
                            max(0, min(255, blade_color[0] + shade_var)),
                            max(0, min(255, blade_color[1] + shade_var + 5)),
                            max(0, min(255, blade_color[2] + shade_var)),
                        )

        # Light patches (sunlight through trees effect)
        for _ in range(8):
            x = rng.randint(2, 28)
            y = rng.randint(2, 28)
            light_color = (85, 125, 58)
            pixels[x, y] = light_color
            if rng.random() > 0.6:
                for d in [(1, 0), (0, 1)]:
                    nx, ny = x + d[0], y + d[1]
                    if 0 <= nx < 32 and 0 <= ny < 32:
                        pixels[nx, ny] = (90, 130, 62)

        # Small dirt patches (realistic ground variation)
        for _ in range(3):
            cx, cy = rng.randint(4, 26), rng.randint(4, 26)
            dirt_color = (95, 85, 65)
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < 32 and 0 <= ny < 32 and rng.random() > 0.3:
                        pixels[nx, ny] = dirt_color

        del pixels

    @staticmethod
    def _texture_road(
        surface: pygame.Surface, tid: int, var: int, pal: 'PaletteGenerator'
    ) -> None:
        """ROAD (1): CC2 realistic dirt/gravel road with texture, not solid gray."""
        rng = random.Random(var * 67)
        # CC2's dirt/gravel brown-gray
        road_color = (139, 119, 101)
        surface.fill(road_color)
        pixels = pygame.surfarray.pixels3d(surface)

        # Natural edge blending (darker toward edges)
        for x in range(32):
            edge_factor = min(x, 31 - x) / 15.0
            if edge_factor < 0.6 and rng.random() > 0.4:
                darkness = int((0.6 - edge_factor) * 30)
                for y in range(32):
                    r, g, b = pixels[x, y]
                    pixels[x, y] = (max(0, r - darkness), max(0, g - darkness), max(0, b - darkness))

        # Tire track marks (subtle, darker strips)
        track_color = (120, 105, 88)
        for x in range(32):
            if rng.random() > 0.4:
                pixels[x, 10] = track_color
                pixels[x, 11] = (125, 110, 93)
                pixels[x, 21] = track_color
                pixels[x, 22] = (125, 110, 93)

        # Gravel/pebble texture (scattered light dots)
        for _ in range(20):
            px = rng.randint(2, 29)
            py = rng.randint(2, 29)
            pebble_var = rng.randint(-12, 12)
            pixels[px, py] = tuple(
                max(0, min(255, c + pebble_var)) for c in (155, 140, 120)
            )

        # No center line - CC2 roads are unpaved dirt roads
        del pixels

    @staticmethod
    def _texture_grass(
        surface: pygame.Surface, tid: int, var: int, pal: 'PaletteGenerator'
    ) -> None:
        """GRASS (2): Medium green with grass blade texture, darker than OPEN."""
        rng = random.Random(var * 31)
        base = (105, 165, 55)
        ProceduralTextureGenerator._fill_with_variation(surface, base, rng, 14)

        pixels = pygame.surfarray.pixels3d(surface)
        # Grass blades - vertical streaks
        for _ in range(16):
            x = rng.randint(0, 31)
            y_start = rng.randint(0, 26)
            length = rng.randint(3, 6)
            shade = rng.choice([(90, 150, 45), (120, 180, 65), (85, 140, 40)])
            for dy in range(length):
                if 0 <= y_start + dy < 32:
                    pixels[x, y_start + dy] = shade

        # Darker patches
        for _ in range(4):
            cx = rng.randint(4, 27)
            cy = rng.randint(4, 27)
            for dy in range(rng.randint(2, 4)):
                for dx in range(rng.randint(2, 4)):
                    if 0 <= cx + dx < 32 and 0 <= cy + dy < 32:
                        pixels[cx + dx, cy + dy] = (80, 130, 35)
        del pixels

    @staticmethod
    def _texture_woods(
        surface: pygame.Surface, tid: int, var: int, pal: 'PaletteGenerator'
    ) -> None:
        """WOODS (3): CC2 very dark green forest with individual tree canopies visible."""
        rng = random.Random(var * 41)
        # CC2's very dark forest green
        base = (45, 68, 33)
        surface.fill(base)
        pixels = pygame.surfarray.pixels3d(surface)

        try:
            import numpy as np

            # Subtle noise for forest floor variation - use numpy for safe operations
            for y in range(32):
                for x in range(32):
                    offset = rng.randint(-6, 6)
                    r, g, b = int(pixels[x, y][0]), int(pixels[x, y][1]), int(pixels[x, y][2])
                    # Clamp to [0, 255] using numpy-safe method
                    new_r = max(0, min(255, r + offset))
                    new_g = max(0, min(255, g + offset))
                    new_b = max(0, min(255, b + offset))
                    pixels[x, y] = (new_r, new_g, new_b)

            # Individual tree canopies (4-8 trees per tile, clearly distinguishable)
            num_trees = rng.randint(4, 8)
            for _ in range(num_trees):
                cx = rng.randint(4, 28)
                cy = rng.randint(4, 28)
                radius = rng.randint(5, 9)

                # Draw tree canopy as circle with shading
                for y in range(max(0, cy - radius), min(32, cy + radius + 1)):
                    for x in range(max(0, cx - radius), min(32, cx + radius + 1)):
                        dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                        if dist < radius:
                            if dist > radius * 0.75:
                                pixels[x, y] = (30, 52, 22)   # Dark outer edge
                            elif dist > radius * 0.5:
                                pixels[x, y] = (40, 62, 28)   # Mid tone
                            elif dist > radius * 0.25:
                                pixels[x, y] = (50, 78, 35)   # Lighter inner
                            else:
                                pixels[x, y] = (58, 90, 42)   # Highlight center

                # Tree trunk hint (small brown dot at base of canopy)
                trunk_y = min(31, cy + radius - 2)
                if 0 <= cx < 32 and 0 <= trunk_y < 32:
                    pixels[cx, trunk_y] = (65, 48, 28)

            # Shadow dots under trees (adds depth)
            for _ in range(num_trees):
                sx = rng.randint(2, 29)
                sy = rng.randint(24, 31)
                pixels[sx, sy] = (28, 45, 20)
        except Exception as e:
            # Fallback: just use base color if numpy operations fail
            pass
        finally:
            del pixels

    @staticmethod
    def _texture_building_enterable(
        surface: pygame.Surface, tid: int, var: int, pal: 'PaletteGenerator'
    ) -> None:
        """BUILDING_ENTERABLE (4): CC2 earthy brown building with visible roof, door, windows."""
        rng = random.Random(var * 103)

        # CC2's earthy brown/tan building walls
        wall_color = (139, 115, 85)
        surface.fill(wall_color)
        pixels = pygame.surfarray.pixels3d(surface)

        # Roof line at top (darker brown, pitched roof appearance)
        roof_color = (110, 75, 45)
        for x in range(32):
            for y in range(0, 7):
                pixels[x, y] = roof_color
            # Roof edge highlight
            pixels[x, 7] = (95, 62, 35)

        # Wall texture - subtle brick pattern hints
        brick_color = (130, 108, 78)
        for y in range(8, 32, 4):
            offset = 4 if (y // 4) % 2 == 0 else 0
            for x in range(offset, 32, 8):
                if rng.random() > 0.5:
                    for dx in range(6):
                        if x + dx < 32 and y < 32:
                            pixels[x + dx, y] = brick_color

        # Door (center bottom, clearly visible)
        door_color = (90, 58, 33)
        for y in range(20, 31):
            for x in range(13, 19):
                pixels[x, y] = door_color
        # Door frame (darker outline)
        frame_color = (70, 45, 25)
        for y in range(20, 31):
            pixels[13, y] = frame_color
            pixels[18, y] = frame_color
        for x in range(13, 19):
            pixels[x, 20] = frame_color

        # Window (upper area, light blue-white)
        window_color = (150, 185, 215)
        for y in range(10, 16):
            for x in range(5, 11):
                pixels[x, y] = window_color
        # Window frame
        for y in range(10, 16):
            pixels[5, y] = frame_color
            pixels[10, y] = frame_color
        for x in range(5, 11):
            pixels[x, 10] = frame_color
            pixels[x, 15] = frame_color

        # Second window (right side)
        for y in range(10, 16):
            for x in range(21, 27):
                pixels[x, y] = window_color
        # Window frame
        for y in range(10, 16):
            pixels[21, y] = frame_color
            pixels[26, y] = frame_color
        for x in range(21, 27):
            pixels[x, 10] = frame_color
            pixels[x, 15] = frame_color
        del pixels

    @staticmethod
    def _texture_building_solid(
        surface: pygame.Surface, tid: int, var: int, pal: 'PaletteGenerator'
    ) -> None:
        """BUILDING_SOLID (5): Gray stone/brick building, no door, solid walls, roof line."""
        rng = random.Random(var * 109)

        # Stone walls - gray
        wall_color = (140, 138, 135)
        surface.fill(wall_color)
        pixels = pygame.surfarray.pixels3d(surface)

        # Roof line at top (dark gray)
        roof_color = (90, 85, 80)
        for x in range(32):
            for y in range(0, 5):
                pixels[x, y] = roof_color
            pixels[x, 5] = (75, 70, 65)

        # Stone block pattern
        stone_dark = (120, 118, 115)
        stone_light = (155, 152, 148)
        for y in range(6, 32, 5):
            offset = 3 if (y // 5) % 2 == 0 else 0
            for x in range(offset, 32, 8):
                # Stone block
                for dy in range(4):
                    for dx in range(7):
                        if x + dx < 32 and y + dy < 32:
                            color = stone_dark if rng.random() > 0.5 else stone_light
                            pixels[x + dx, y + dy] = color
            # Mortar lines
            for x in range(32):
                if y < 32:
                    pixels[x, y] = (100, 98, 95)

        # No door - solid walls. Add a small vent/window slit
        vent_color = (60, 60, 65)
        for y in range(10, 14):
            for x in range(14, 18):
                pixels[x, y] = vent_color
        del pixels

    @staticmethod
    def _texture_water(
        surface: pygame.Surface, tid: int, var: int, pal: 'PaletteGenerator'
    ) -> None:
        """WATER (6): CC2 muted blue with subtle wave pattern and depth variation."""
        rng = random.Random(var * 127)
        # CC2's muted blue
        base = (62, 87, 117)
        surface.fill(base)
        pixels = pygame.surfarray.pixels3d(surface)

        try:
            # Depth variation (subtle, not dramatic) - safe pixel operations
            for y in range(32):
                for x in range(32):
                    offset = rng.randint(-7, 7)
                    r, g, b = int(pixels[x, y][0]), int(pixels[x, y][1]), int(pixels[x, y][2])
                    new_r = max(0, min(255, r + offset))
                    new_g = max(0, min(255, g + offset))
                    new_b = max(0, min(255, b + offset))
                    pixels[x, y] = (new_r, new_g, new_b)

            # Wave pattern - gentle horizontal streaks (lighter blue)
            wave_light = (82, 112, 142)
            wave_mid = (72, 100, 130)
            for y in range(3, 29, 6):
                wave_offset = rng.randint(-1, 1)
                for x in range(0, 32):
                    wy = y + wave_offset + int(math.sin(x * 0.3 + var) * 1.0)
                    if 0 <= wy < 32:
                        pixels[x, wy] = wave_light
                        if wy + 1 < 32:
                            pixels[x, wy + 1] = wave_mid

            # Subtle sparkle highlights (fewer than before - more realistic)
            for _ in range(3):
                sx = rng.randint(3, 28)
                sy = rng.randint(3, 28)
                pixels[sx, sy] = (120, 160, 195)

            # Deeper areas near edges (shoreline hint)
            for x in range(32):
                if rng.random() > 0.6:
                    pixels[x, 0] = (52, 75, 102)
                    pixels[x, 31] = (52, 75, 102)
            for y in range(32):
                if rng.random() > 0.6:
                    pixels[0, y] = (52, 75, 102)
                    pixels[31, y] = (52, 75, 102)
        except Exception as e:
            pass  # Fallback to base color
        finally:
            del pixels

    @staticmethod
    def _texture_hedge(
        surface: pygame.Surface, tid: int, var: int, pal: 'PaletteGenerator'
    ) -> None:
        """HEDGE (7): Dark green hedge row, dense vegetation line."""
        rng = random.Random(var * 151)

        # Background - slightly lighter green (ground visible at edges)
        ground_color = (100, 140, 60)
        surface.fill(ground_color)
        pixels = pygame.surfarray.pixels3d(surface)

        # Dense hedge band across middle
        hedge_dark = (25, 75, 20)
        hedge_mid = (35, 95, 30)
        hedge_light = (50, 115, 40)

        for y in range(8, 24):
            for x in range(32):
                # Irregular hedge edges
                edge_jitter = rng.randint(-2, 2)
                if 8 + edge_jitter <= y <= 24 + edge_jitter:
                    r = rng.random()
                    if r > 0.7:
                        pixels[x, y] = hedge_dark
                    elif r > 0.3:
                        pixels[x, y] = hedge_mid
                    else:
                        pixels[x, y] = hedge_light

        # Leaf texture - small dots
        for _ in range(20):
            lx = rng.randint(0, 31)
            ly = rng.randint(8, 23)
            pixels[lx, ly] = (60, 130, 50)
        del pixels

    @staticmethod
    def _texture_wall(
        surface: pygame.Surface, tid: int, var: int, pal: 'PaletteGenerator'
    ) -> None:
        """WALL (8): Gray brick wall with mortar lines."""
        rng = random.Random(var * 173)

        wall_color = (130, 128, 125)
        surface.fill(wall_color)
        pixels = pygame.surfarray.pixels3d(surface)

        mortar_color = (95, 92, 88)
        brick_dark = (115, 112, 108)
        brick_light = (145, 142, 138)

        # Brick pattern with mortar lines
        for y in range(0, 32, 6):
            offset = 5 if (y // 6) % 2 == 0 else 0
            # Mortar line
            for x in range(32):
                if y < 32:
                    pixels[x, y] = mortar_color
            # Bricks
            for bx in range(offset, 32, 11):
                for dy in range(1, 6):
                    for dx in range(1, 10):
                        if bx + dx < 32 and y + dy < 32:
                            color = brick_dark if rng.random() > 0.5 else brick_light
                            pixels[bx + dx, y + dy] = color
                # Vertical mortar
                if bx + 10 < 32:
                    for dy in range(1, 6):
                        if y + dy < 32:
                            pixels[bx + 10, y + dy] = mortar_color

        # Top cap (slightly wider/darker)
        for x in range(32):
            pixels[x, 0] = (80, 78, 75)
            pixels[x, 1] = (100, 98, 95)
        del pixels

    @staticmethod
    def _texture_rough(
        surface: pygame.Surface, tid: int, var: int, pal: 'PaletteGenerator'
    ) -> None:
        """ROUGH (9): Brown dirt/rubble with scattered rocks."""
        rng = random.Random(var * 193)
        base = (155, 130, 85)
        ProceduralTextureGenerator._fill_with_variation(surface, base, rng, 18)

        pixels = pygame.surfarray.pixels3d(surface)

        # Scattered rocks
        rock_colors = [(120, 115, 105), (140, 135, 125), (100, 95, 85)]
        for _ in range(8):
            rx = rng.randint(2, 28)
            ry = rng.randint(2, 28)
            size = rng.randint(2, 4)
            rock_color = rng.choice(rock_colors)
            for dy in range(size):
                for dx in range(size):
                    if 0 <= rx + dx < 32 and 0 <= ry + dy < 32:
                        pixels[rx + dx, ry + dy] = rock_color

        # Dirt patches
        for _ in range(5):
            dx = rng.randint(4, 26)
            dy = rng.randint(4, 26)
            dirt_color = (135, 110, 70)
            for ddy in range(rng.randint(2, 4)):
                for ddx in range(rng.randint(2, 4)):
                    if 0 <= dx + ddx < 32 and 0 <= dy + ddy < 32:
                        pixels[dx + ddx, dy + ddy] = dirt_color
        del pixels

    @staticmethod
    def _texture_shallow(
        surface: pygame.Surface, tid: int, var: int, pal: 'PaletteGenerator'
    ) -> None:
        """SHALLOW (10): Light blue shallow water with sandy bottom visible."""
        rng = random.Random(var * 211)
        base = (120, 185, 225)
        surface.fill(base)
        pixels = pygame.surfarray.pixels3d(surface)

        # Sandy bottom showing through
        sand_color = (195, 180, 140)
        for _ in range(15):
            sx = rng.randint(2, 29)
            sy = rng.randint(2, 29)
            size = rng.randint(2, 5)
            for dy in range(size):
                for dx in range(size):
                    if 0 <= sx + dx < 32 and 0 <= sy + dy < 32 and rng.random() > 0.4:
                        pixels[sx + dx, sy + dy] = sand_color

        # Gentle wave ripples
        ripple_color = (150, 205, 240)
        for y in range(3, 29, 6):
            for x in range(32):
                wy = y + int(math.sin(x * 0.5 + var) * 1.2)
                if 0 <= wy < 32:
                    pixels[x, wy] = ripple_color
        del pixels

    @staticmethod
    def _texture_bridge(
        surface: pygame.Surface, tid: int, var: int, pal: 'PaletteGenerator'
    ) -> None:
        """BRIDGE (11): Brown wooden planks with support beams, clearly a bridge."""
        rng = random.Random(var * 241)

        # Water underneath at edges
        water_color = (40, 110, 200)
        surface.fill(water_color)
        pixels = pygame.surfarray.pixels3d(surface)

        # Bridge deck - wooden planks
        plank_color = (160, 120, 70)
        plank_dark = (130, 95, 55)
        for y in range(6, 26):
            for x in range(2, 30):
                pixels[x, y] = plank_color

        # Plank lines (horizontal gaps between planks)
        for y in range(6, 26, 4):
            for x in range(2, 30):
                pixels[x, y] = plank_dark

        # Plank grain (vertical lines per plank)
        for x in range(4, 30, 6):
            for y in range(6, 26):
                if rng.random() > 0.6:
                    pixels[x, y] = plank_dark

        # Support beams (vertical beams on sides)
        beam_color = (110, 80, 45)
        for y in range(4, 28):
            pixels[2, y] = beam_color
            pixels[3, y] = beam_color
            pixels[29, y] = beam_color
            pixels[28, y] = beam_color

        # Cross beams
        for x in range(4, 28):
            pixels[x, 6] = beam_color
            pixels[x, 7] = beam_color
            pixels[x, 25] = beam_color
            pixels[x, 24] = beam_color

        # Rail posts
        for x in range(6, 28, 8):
            pixels[x, 4] = beam_color
            pixels[x, 5] = beam_color
            pixels[x, 27] = beam_color
            pixels[x, 26] = beam_color
        del pixels

    @staticmethod
    def _texture_default(
        surface: pygame.Surface, tid: int, var: int, pal: 'PaletteGenerator'
    ) -> None:
        """Fallback simple noise texture."""
        rng = random.Random(var * 277)
        base = pal.get_color(tid, 4)
        ProceduralTextureGenerator._fill_with_variation(surface, base, rng, 15)


class SpriteGenerator:
    """
    Generates pixel art sprites for decorations programmatically.
    
    Each decoration type has a drawing function that creates
    recognizable icons at small sizes (up to 32x32 pixels).
    """
    
    @staticmethod
    def generate_sprite(deco_type_name: str, variant: int = 0) -> pygame.Surface:
        """Generate sprite surface for a decoration type."""
        size = 32
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))  # Transparent background
        
        sprite_funcs = {
            'BUSH_SMALL': SpriteGenerator._draw_bush_small,
            'BUSH_DENSE': SpriteGenerator._draw_bush_dense,
            'TREE_OAK': SpriteGenerator._draw_tree_oak,
            'TREE_PINE': SpriteGenerator._draw_tree_pine,
            'ROCK_LARGE': SpriteGenerator._draw_rock_large,
            'ROCK_SMALL': SpriteGenerator._draw_rock_small,
            'RUBBLE_PILE': SpriteGenerator._draw_rubble,
            'CRATER_SMALL': SpriteGenerator._draw_crater_small,
            'CRATER_LARGE': SpriteGenerator._draw_crater_large,
            'TRENCH_SECTION': SpriteGenerator._draw_trench,
            'SANDBAG_WALL': SpriteGenerator._draw_sandbag,
            'WRECKAGE_VEHICLE': SpriteGenerator._draw_wreckage,
            'CAMOUFLAGE_NET': SpriteGenerator._draw_camo_net,
        }
        
        draw_func = sprite_funcs.get(deco_type_name, SpriteGenerator._draw_placeholder)
        draw_func(surface, variant)
        
        return surface
    
    @staticmethod
    def _draw_bush_small(surface: pygame.Surface, variant: int) -> None:
        """Draw small bush (circle of green pixels)."""
        color = (34, 120, 34)
        dark = (24, 90, 24)
        cx, cy = 16, 20
        for y in range(8, 24):
            for x in range(8, 24):
                dist = math.sqrt((x-cx)**2 + (y-cy)**2)
                if dist < 7:
                    surface.set_at((x, y), color if dist > 4 else dark)
    
    @staticmethod
    def _draw_bush_dense(surface: pygame.Surface, variant: int) -> None:
        """Draw dense bush (larger, irregular shape)."""
        color = (28, 100, 28)
        dark = (18, 70, 18)
        points = [
            (10, 22), (13, 18), (16, 16), (19, 17), (22, 20),
            (23, 24), (20, 26), (16, 27), (12, 26), (9, 24)
        ]
        
        # Fill polygon
        for y in range(16, 28):
            for x in range(9, 24):
                if SpriteGenerator._point_in_polygon(x, y, points):
                    shade = color if (x+y+variant) % 3 != 0 else dark
                    surface.set_at((x, y), shade)
    
    @staticmethod
    def _point_in_polygon(x: int, y: int, polygon: list[tuple[int, int]]) -> bool:
        """Check if point is inside polygon (ray casting)."""
        n = len(polygon)
        inside = False
        j = n - 1
        for i in range(n):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside
    
    @staticmethod
    def _draw_tree_oak(surface: pygame.Surface, variant: int) -> None:
        """Draw deciduous tree (trunk + round canopy)."""
        # Trunk (brown)
        trunk_color = (101, 67, 33)
        for y in range(18, 28):
            for x in range(14, 18):
                surface.set_at((x, y), trunk_color)
        
        # Canopy (green circle)
        canopy_colors = [(46, 125, 50), (36, 105, 40), (56, 145, 60)]
        cx, cy = 16, 12
        for y in range(2, 20):
            for x in range(4, 28):
                dist = math.sqrt((x-cx)**2 + (y-cy)**2)
                if dist < 10:
                    color_idx = int(dist / 3) % 3
                    surface.set_at((x, y), canopy_colors[color_idx])
    
    @staticmethod
    def _draw_tree_pine(surface: pygame.Surface, variant: int) -> None:
        """Draw coniferous tree (triangular)."""
        # Trunk
        trunk_color = (87, 53, 23)
        for y in range(22, 28):
            for x in range(14, 18):
                surface.set_at((x, y), trunk_color)
        
        # Triangular foliage (layered triangles)
        foliage_colors = [(20, 90, 25), (30, 110, 35), (25, 100, 30)]
        layers = [(16, 18, 10), (16, 12, 7), (16, 6, 4)]  # (cx, cy, half_width)
        
        for idx, (lcx, lcy, lw) in enumerate(layers):
            color = foliage_colors[idx]
            for y in range(lcy - lw*2, lcy + 2):
                width_at_y = int(lw * (1 - abs(y - lcy) / (lw*2 + 1)))
                for x in range(lcx - width_at_y, lcx + width_at_y + 1):
                    if 0 <= x < 32 and 0 <= y < 32:
                        surface.set_at((x, y), color)
    
    @staticmethod
    def _draw_rock_large(surface: pygame.Surface, variant: int) -> None:
        """Draw large boulder."""
        colors = [(128, 128, 128), (108, 108, 108), (148, 148, 148)]
        points = [
            (8, 24), (10, 18), (14, 14), (18, 12), (22, 14),
            (25, 18), (26, 23), (24, 26), (18, 27), (12, 26), (9, 25)
        ]
        
        for y in range(12, 28):
            for x in range(8, 27):
                if SpriteGenerator._point_in_polygon(x, y, points):
                    color_idx = (x + y + variant) % 3
                    surface.set_at((x, y), colors[color_idx])
        
        # Highlight
        surface.set_at((16, 14), (180, 180, 180))
        surface.set_at((17, 15), (170, 170, 170))
    
    @staticmethod
    def _draw_rock_small(surface: pygame.Surface, variant: int) -> None:
        """Draw small rock cluster."""
        color = (118, 118, 118)
        # Main rock
        points = [(12, 24), (14, 20), (18, 19), (21, 21), (22, 25), (19, 26), (14, 25)]
        for y in range(19, 27):
            for x in range(12, 23):
                if SpriteGenerator._point_in_polygon(x, y, points):
                    surface.set_at((x, y), color)
        
        # Small adjacent rock
        surface.set_at((22, 23), (138, 138, 138))
        surface.set_at((23, 24), (128, 128, 128))
    
    @staticmethod
    def _draw_rubble(surface: pygame.Surface, variant: int) -> None:
        """Draw rubble pile (debris)."""
        rng = random.Random(variant * 313)
        colors = [(100, 95, 90), (80, 75, 70), (120, 115, 110), (60, 55, 50)]
        
        for _ in range(15):
            px = rng.randint(8, 24)
            py = rng.randint(18, 28)
            size = rng.randint(1, 3)
            color = rng.choice(colors)
            for dy in range(size):
                for dx in range(size):
                    if 0 <= px+dx < 32 and 0 <= py+dy < 32:
                        surface.set_at((px+dx, py+dy), color)
    
    @staticmethod
    def _draw_crater_small(surface: pygame.Surface, variant: int) -> None:
        """Draw small shell crater (ellipse with shadow)."""
        # Dark interior
        cx, cy = 16, 20
        for y in range(16, 26):
            for x in range(10, 22):
                norm_dist = ((x-cx)/6)**2 + ((y-cy)/4)**2
                if norm_dist < 1:
                    shade = int(40 + norm_dist * 30)
                    surface.set_at((x, y), (shade, shade-5, shade-10))
        
        # Raised rim (lighter)
        rim_color = (140, 135, 130)
        for angle in range(0, 360, 20):
            rad = math.radians(angle)
            rx = int(cx + 7 * math.cos(rad))
            ry = int(cy + 5 * math.sin(rad))
            if 0 <= rx < 32 and 0 <= ry < 32:
                surface.set_at((rx, ry), rim_color)
    
    @staticmethod
    def _draw_crater_large(surface: pygame.Surface, variant: int) -> None:
        """Draw large bomb crater."""
        # Dark center
        cx, cy = 16, 18
        for y in range(8, 28):
            for x in range(4, 28):
                norm_dist = ((x-cx)/12)**2 + ((y-cy)/8)**2
                if norm_dist < 1:
                    shade = int(35 + norm_dist * 40)
                    surface.set_at((x, y), (shade, shade-8, shade-15))
        
        # Rim
        rim_color = (130, 125, 120)
        for angle in range(0, 360, 12):
            rad = math.radians(angle)
            rx = int(cx + 13 * math.cos(rad))
            ry = int(cy + 10 * math.sin(rad))
            if 0 <= rx < 32 and 0 <= ry < 32:
                surface.set_at((rx, ry), rim_color)
                if 0 <= rx+1 < 32:
                    surface.set_at((rx+1, ry), rim_color)
    
    @staticmethod
    def _draw_trench(surface: pygame.Surface, variant: int) -> None:
        """Draw trench section (rectangular depression)."""
        # Dark interior
        for y in range(20, 28):
            for x in range(4, 28):
                surface.set_at((x, y), (70, 60, 50))
        
        # Sandbag wall on top edge
        bag_color = (180, 160, 120)
        for x in range(4, 28, 3):
            for y in range(18, 21):
                surface.set_at((x, y), bag_color)
                if x+1 < 28:
                    surface.set_at((x+1, y), bag_color)
                if x+2 < 28:
                    surface.set_at((x+2, y), (160, 140, 100))
    
    @staticmethod
    def _draw_sandbag(surface: pygame.Surface, variant: int) -> None:
        """Draw sandbag wall."""
        bag_color = (190, 170, 130)
        shadow = (150, 130, 90)
        
        for y in range(16, 24):
            for x in range(2, 30):
                is_bag = (x // 4 + y // 2) % 2 == 0
                color = bag_color if is_bag else shadow
                surface.set_at((x, y), color)
    
    @staticmethod
    def _draw_wreckage(surface: pygame.Surface, variant: int) -> None:
        """Draw destroyed vehicle hull."""
        hull_color = (60, 55, 50)
        dark = (40, 35, 30)
        rust = (100, 60, 30)
        
        # Main hull shape (irregular)
        hull_points = [
            (6, 22), (8, 18), (12, 16), (18, 15), (24, 16),
            (26, 19), (27, 23), (25, 26), (18, 27), (10, 26), (7, 24)
        ]
        
        for y in range(15, 28):
            for x in range(6, 28):
                if SpriteGenerator._point_in_polygon(x, y, hull_points):
                    color = hull_color
                    if (x+y+variant) % 7 == 0:
                        color = rust
                    elif (x*y) % 11 == 0:
                        color = dark
                    surface.set_at((x, y), color)
        
        # Gun barrel stub
        for x in range(20, 28):
            surface.set_at((x, 17), dark)
    
    @staticmethod
    def _draw_camo_net(surface: pygame.Surface, variant: int) -> None:
        """Draw camouflage netting."""
        colors = [(45, 90, 45), (60, 75, 35), (35, 65, 40)]
        rng = random.Random(variant * 373)
        
        # Net pattern (grid with holes)
        for y in range(8, 24):
            for x in range(4, 28):
                if (x + y) % 3 == 0:
                    surface.set_at((x, y), (80, 75, 70))  # Net string
                else:
                    color = colors[rng.randint(0, 2)]
                    if rng.random() > 0.3:
                        surface.set_at((x, y), color)
    
    @staticmethod
    def _draw_placeholder(surface: pygame.Surface, variant: int) -> None:
        """Generic placeholder sprite."""
        color = (150, 150, 150)
        for y in range(10, 22):
            for x in range(10, 22):
                if (x+y) % 2 == 0:
                    surface.set_at((x, y), color)


class EnhancedRenderer:
    """
    Enhanced pixel art renderer for PyCC2 maps.
    
    Renders enhanced tile data with textures, lighting, decorations,
    and atmospheric effects. Designed to surpass original CC2 visuals.
    """
    
    TILE_SIZE = 32
    
    def __init__(self):
        self._screen: pygame.Surface | None = None
        self._offscreen: pygame.Surface | None = None  # Off-screen buffer to eliminate flicker
        self._palette_gen = PaletteGenerator()
        self._texture_cache: dict[tuple[int, int], pygame.Surface] = {}
        self._scaled_texture_cache: dict[tuple[int, int, int], pygame.Surface] = {}
        self._height_lit_cache: dict[tuple[int, int, int, int], pygame.Surface] = {}
        self._sprite_cache: dict[str, pygame.Surface] = {}
        self._frame_count = 0
    
    def initialize(self, screen: pygame.Surface) -> None:
        """Initialize renderer with display surface."""
        self._screen = screen
        self._offscreen = pygame.Surface(screen.get_size()).convert()
    
    def render(
        self,
        game_map: GameMap,
        units: list[Unit],
        camera: Camera,
        alpha: float = 1.0,
        selected_unit_ids: set[str] | None = None,
        debug_mode: bool = False,
    ) -> None:
        """
        Main render method - STABLE VERSION with minimal complexity.

        Pipeline:
        1. Clear off-screen buffer (solid color, no alpha blending)
        2. Draw terrain (simple colored tiles, no textures)
        3. Draw units
        4. Atomic blit off-screen → display surface (eliminates flicker)
        """
        if self._screen is None:
            return

        self._frame_count += 1

        # Ensure off-screen buffer matches display surface size (handles resize)
        screen_w, screen_h = self._screen.get_size()
        if self._offscreen is None or self._offscreen.get_size() != (screen_w, screen_h):
            self._offscreen = pygame.Surface((screen_w, screen_h)).convert()

        # STEP 1: Clear off-screen buffer
        self._offscreen.fill((34, 40, 48))  # Dark blue-gray background

        # STEP 2: Draw terrain using SIMPLE solid colors (CC2 classic 256-color style)
        self._draw_simple_terrain(game_map, camera)

        # STEP 3: Draw grid ONLY in debug mode
        if debug_mode:
            self._draw_grid(game_map, camera)

        # STEP 4: Draw decorations (minimal)
        self._draw_decorations(game_map, camera)

        # STEP 5: Draw units
        self._draw_units(units, camera, selected_unit_ids)

        # STEP 6: Atomic blit off-screen buffer → display surface
        self._screen.blit(self._offscreen, (0, 0))

        # DISABLED: All post-processing to prevent flickering and crashes
        # self._apply_post_processing()  # REMOVED - causes flickering

    def _draw_simple_terrain(self, game_map: GameMap, camera: Camera) -> None:
        """Draw terrain using simple solid colors - MAXIMUM STABILITY.

        Uses predefined CC2-accurate colors without any procedural generation.
        This is the classic "256-color era" look that is rock-solid stable.
        """
        if self._screen is None or self._offscreen is None:
            return

        # CC2 Classic Color Palette (verified accurate)
        TERRAIN_COLORS = {
            0: (76, 112, 52),    # OPEN/GRASS - muted olive green
            1: (139, 119, 101),  # ROAD - dirt brown
            2: (68, 105, 48),     # GRASS - darker green
            3: (45, 68, 33),      # WOODS - very dark forest green
            4: (139, 115, 85),    # BUILDING_ENTERABLE - earthy brown
            5: (120, 118, 115),   # BUILDING_SOLID - gray stone
            6: (62, 87, 117),     # WATER - muted blue
            7: (85, 70, 55),      # HEDGE - dark brown-green
            8: (110, 108, 105),   # WALL - gray brick
            9: (135, 115, 80),    # ROUGH - tan/brown
            10: (95, 145, 165),   # SHALLOW - light blue-green
            11: (160, 140, 100),  # BRIDGE - wooden brown
            12: (90, 85, 75),     # CRATER - dark gray-brown
        }

        bounds = camera.view_bounds
        start_x = max(0, int(bounds[0].x // self.TILE_SIZE))
        end_x = min(game_map.width, int((bounds[1].x // self.TILE_SIZE) + 2))
        start_y = max(0, int(bounds[0].y // self.TILE_SIZE))
        end_y = min(game_map.height, int((bounds[1].y // self.TILE_SIZE) + 2))

        tile_screen_size = int(self.TILE_SIZE * camera.zoom)

        # Pre-calculate rect for batch drawing (much faster than individual blits)
        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                try:
                    # Get terrain type safely
                    if hasattr(game_map, 'enhanced_tiles') and game_map.enhanced_tiles:
                        if 0 <= ty < len(game_map.enhanced_tiles) and 0 <= tx < len(game_map.enhanced_tiles[ty]):
                            enhanced_tile = game_map.enhanced_tiles[ty][tx]
                            if enhanced_tile:
                                terrain_val = enhanced_tile.base_terrain
                            else:
                                terrain_val = int(game_map.tile_grid[ty, tx])
                        else:
                            terrain_val = int(game_map.tile_grid[ty, tx])
                    else:
                        terrain_val = int(game_map.tile_grid[ty, tx])

                    # Clamp to valid range
                    terrain_val = max(0, min(12, terrain_val))

                    # Get color from palette
                    color = TERRAIN_COLORS.get(terrain_val, (128, 128, 128))

                    # Calculate screen position
                    world_x = tx * self.TILE_SIZE
                    world_y = ty * self.TILE_SIZE

                    from pycc2.domain.value_objects.vec2 import Vec2
                    screen_pos = camera.world_to_screen(Vec2(world_x, world_y))

                    # Draw solid rectangle (NO texture generation)
                    rect = pygame.Rect(
                        int(screen_pos[0]),
                        int(screen_pos[1]),
                        tile_screen_size,
                        tile_screen_size
                    )
                    pygame.draw.rect(self._offscreen, color, rect)

                except Exception as e:
                    # Skip this tile on any error to prevent crash
                    continue
    
    def _get_cached_texture(self, terrain_id: int, variation: int) -> pygame.Surface:
        """Get or generate cached terrain texture."""
        key = (terrain_id, variation)
        if key not in self._texture_cache:
            self._texture_cache[key] = ProceduralTextureGenerator.generate_terrain_texture(
                terrain_id, variation, self._palette_gen
            )
        return self._texture_cache[key]
    
    def _get_cached_sprite(self, deco_type_name: str, variant: int = 0) -> pygame.Surface:
        """Get or generate cached decoration sprite."""
        key = f"{deco_type_name}_{variant}"
        if key not in self._sprite_cache:
            self._sprite_cache[key] = SpriteGenerator.generate_sprite(deco_type_name, variant)
        return self._sprite_cache[key]
    
    def _draw_enhanced_terrain(self, game_map: GameMap, camera: Camera, debug_mode: bool = False) -> None:
        """Draw terrain tiles with texturing and height-based lighting."""
        if self._screen is None:
            return

        bounds = camera.view_bounds
        start_x = max(0, int(bounds[0].x // self.TILE_SIZE))
        end_x = min(game_map.width, int((bounds[1].x // self.TILE_SIZE) + 2))
        start_y = max(0, int(bounds[0].y // self.TILE_SIZE))
        end_y = min(game_map.height, int((bounds[1].y // self.TILE_SIZE) + 2))

        tile_screen_size = int(self.TILE_SIZE * camera.zoom)

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                # Get enhanced tile data if available
                enhanced_tile = self._get_enhanced_tile(game_map, tx, ty)

                if enhanced_tile:
                    terrain_val = enhanced_tile.base_terrain
                    variation = enhanced_tile.variation
                    height = enhanced_tile.height
                else:
                    # Fallback to legacy integer
                    terrain_val = int(game_map.tile_grid[ty, tx])
                    variation = 0
                    height = 0

                # Get textured surface — use height-lit cache when height != 0
                if height != 0:
                    cache_key = (terrain_val, variation, height, tile_screen_size)
                    if cache_key in self._height_lit_cache:
                        texture = self._height_lit_cache[cache_key]
                    else:
                        base_texture = self._get_cached_texture(terrain_val, variation)
                        texture = self._apply_height_lighting(base_texture, height)
                        if tile_screen_size != self.TILE_SIZE:
                            texture = pygame.transform.scale(texture, (tile_screen_size, tile_screen_size))
                        self._height_lit_cache[cache_key] = texture
                else:
                    # No height modification — use scaled texture cache
                    if tile_screen_size != self.TILE_SIZE:
                        scale_key = (terrain_val, variation, tile_screen_size)
                        if scale_key not in self._scaled_texture_cache:
                            base_texture = self._get_cached_texture(terrain_val, variation)
                            self._scaled_texture_cache[scale_key] = pygame.transform.scale(
                                base_texture, (tile_screen_size, tile_screen_size)
                            )
                        texture = self._scaled_texture_cache[scale_key]
                    else:
                        texture = self._get_cached_texture(terrain_val, variation)

                # Calculate screen position
                world_x = tx * self.TILE_SIZE
                world_y = ty * self.TILE_SIZE

                from pycc2.domain.value_objects.vec2 import Vec2
                screen_pos = camera.world_to_screen(Vec2(world_x, world_y))

                rect = pygame.Rect(int(screen_pos[0]), int(screen_pos[1]), tile_screen_size, tile_screen_size)
                self._offscreen.blit(texture, rect)

        # DISABLED: Terrain edge smoothing - causes severe performance issues during drag operations
        # The smoothing system recalculates edges every frame, which is too expensive
        # when combined with drag-and-drop rendering. Re-enable only if performance allows.
        # if not debug_mode and tile_screen_size >= 16:
        #     self._apply_terrain_edge_smoothing(game_map, camera, start_x, end_x, start_y, end_y, tile_screen_size)

        # Draw terrain borders ONLY in debug mode (Issue 4: remove harsh grid lines in normal mode)
        if debug_mode:
            self._draw_terrain_borders(game_map, camera, start_x, end_x, start_y, end_y)
    
    def _get_enhanced_tile(self, game_map: GameMap, x: int, y: int) -> EnhancedTile | None:
        """Try to get enhanced tile data from map."""
        try:
            if hasattr(game_map, 'enhanced_tiles'):
                if 0 <= y < len(game_map.enhanced_tiles) and 0 <= x < len(game_map.enhanced_tiles[y]):
                    return game_map.enhanced_tiles[y][x]
        except (AttributeError, IndexError):
            pass
        return None

    def _get_terrain_at(self, game_map: GameMap, x: int, y: int) -> int:
        """Get terrain type at tile coordinate, returns -1 for out of bounds."""
        if x < 0 or y < 0 or x >= game_map.width or y >= game_map.height:
            return -1
        enhanced_tile = self._get_enhanced_tile(game_map, x, y)
        if enhanced_tile:
            return enhanced_tile.base_terrain
        return int(game_map.tile_grid[y, x])

    def _apply_terrain_edge_smoothing(
        self, game_map: GameMap, camera: Camera,
        start_x: int, end_x: int, start_y: int, end_y: int,
        tile_screen_size: int
    ) -> None:
        """Apply subtle edge smoothing between different terrain types for CC2-like natural look.

        Creates 1-2 pixel wide semi-transparent overlays at terrain boundaries
        to soften harsh edges without blurring the entire map.
        """
        if self._screen is None or tile_screen_size < 8:
            return

        from pycc2.domain.value_objects.vec2 import Vec2

        # Only process every other tile for performance (skip if already processed)
        smoothing_surface = pygame.Surface((tile_screen_size * 2, tile_screen_size * 2), pygame.SRCALPHA)

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                current = self._get_terrain_at(game_map, tx, ty)

                # Check all 4 neighbors
                neighbors = [
                    (tx + 1, ty),  # right
                    (tx - 1, ty),  # left
                    (tx, ty + 1),  # down
                    (tx, ty - 1),  # up
                ]

                for nx, ny in neighbors:
                    if nx < start_x or nx >= end_x or ny < start_y or ny >= end_y:
                        continue

                    neighbor = self._get_terrain_at(game_map, nx, ny)
                    if neighbor != current and neighbor >= 0:
                        # Found a terrain boundary - draw subtle edge softening
                        world_x = tx * self.TILE_SIZE
                        world_y = ty * self.TILE_SIZE
                        screen_pos = camera.world_to_screen(Vec2(world_x, world_y))
                        base_x = int(screen_pos[0])
                        base_y = int(screen_pos[1])

                        # Determine which edge
                        edge_x = tile_screen_size if nx > tx else (0 if nx < tx else tile_screen_size // 2)
                        edge_y = tile_screen_size if ny > ty else (0 if ny < ty else tile_screen_size // 2)

                        # Calculate blend color (average of two terrain colors)
                        try:
                            pal = self._palette_gen
                            color1 = pal.get_color(current, 4)  # mid-tone
                            color2 = pal.get_color(neighbor, 4)
                            blend_color = (
                                (color1[0] + color2[0]) // 2,
                                (color1[1] + color2[1]) // 2,
                                (color1[2] + color2[2]) // 2,
                                60,  # Semi-transparent
                            )
                        except Exception:
                            blend_color = (80, 80, 80, 60)

                        # Draw 1-2 pixel wide soft edge
                        edge_width = max(1, tile_screen_size // 16)

                        if nx != tx:  # Vertical edge (left/right neighbor)
                            edge_rect = pygame.Rect(
                                base_x + (edge_x if edge_x <= tile_screen_size // 2 else 0),
                                base_y,
                                edge_width,
                                tile_screen_size,
                            )
                        else:  # Horizontal edge (top/bottom neighbor)
                            edge_rect = pygame.Rect(
                                base_x,
                                base_y + (edge_y if edge_y <= tile_screen_size // 2 else 0),
                                tile_screen_size,
                                edge_width,
                            )

                        # Draw semi-transparent overlay for softening
                        edge_surf = pygame.Surface((edge_rect.width, edge_rect.height), pygame.SRCALPHA)
                        edge_surf.fill(blend_color)
                        self._offscreen.blit(edge_surf, edge_rect, special_flags=pygame.BLEND_RGBA_ADD)

    def _draw_terrain_borders(
        self, game_map: GameMap, camera: Camera,
        start_x: int, end_x: int, start_y: int, end_y: int
    ) -> None:
        """Draw thin dark borders between tiles of different terrain types for readability."""
        if self._screen is None or self._offscreen is None:
            return

        from pycc2.domain.value_objects.vec2 import Vec2
        tile_screen_size = int(self.TILE_SIZE * camera.zoom)
        border_color = (20, 20, 20)

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                current_terrain = self._get_terrain_at(game_map, tx, ty)

                world_x = tx * self.TILE_SIZE
                world_y = ty * self.TILE_SIZE
                screen_pos = camera.world_to_screen(Vec2(world_x, world_y))
                sx = int(screen_pos[0])
                sy = int(screen_pos[1])

                # Right border
                right_terrain = self._get_terrain_at(game_map, tx + 1, ty)
                if right_terrain != current_terrain and right_terrain >= 0:
                    pygame.draw.line(
                        self._offscreen, border_color,
                        (sx + tile_screen_size, sy),
                        (sx + tile_screen_size, sy + tile_screen_size), 1
                    )

                # Bottom border
                bottom_terrain = self._get_terrain_at(game_map, tx, ty + 1)
                if bottom_terrain != current_terrain and bottom_terrain >= 0:
                    pygame.draw.line(
                        self._offscreen, border_color,
                        (sx, sy + tile_screen_size),
                        (sx + tile_screen_size, sy + tile_screen_size), 1
                    )
    
    def _apply_height_lighting(self, surface: pygame.Surface, height: int) -> pygame.Surface:
        """Apply lighting adjustments based on tile height (fast numpy version)."""
        if height == 0:
            return surface

        result = surface.copy()
        brightness_factor = 1.0 + (height * 0.08)

        try:
            import numpy as np
            arr = pygame.surfarray.pixels3d(result)
            np.multiply(arr, brightness_factor, out=arr, casting='unsafe')
            np.clip(arr, 0, 255, out=arr)
            del arr
        except Exception:
            pass  # fallback: return unmodified

        return result
    
    def _draw_decorations(self, game_map: GameMap, camera: Camera) -> None:
        """Draw decoration sprites on map."""
        if self._screen is None or self._offscreen is None:
            return
        
        bounds = camera.view_bounds
        start_x = max(0, int(bounds[0].x // self.TILE_SIZE))
        end_x = min(game_map.width, int((bounds[1].x // self.TILE_SIZE) + 2))
        start_y = max(0, int(bounds[0].y // self.TILE_SIZE))
        end_y = min(game_map.height, int((bounds[1].y // self.TILE_SIZE) + 2))
        
        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                enhanced_tile = self._get_enhanced_tile(game_map, tx, ty)
                
                if not enhanced_tile or not enhanced_tile.decorations:
                    continue
                
                for deco in enhanced_tile.decorations:
                    # Get sprite
                    sprite = self._get_cached_sprite(
                        deco.decoration_type.name,
                        deco.variant
                    )
                    
                    # Calculate position with sub-tile offset
                    base_x = tx * self.TILE_SIZE
                    base_y = ty * self.TILE_SIZE
                    
                    offset_x = int(deco.offset_x * self.TILE_SIZE)
                    offset_y = int(deco.offset_y * self.TILE_SIZE)
                    
                    world_x = base_x + offset_x
                    world_y = base_y + offset_y
                    
                    from pycc2.domain.value_objects.vec2 import Vec2
                    screen_pos = camera.world_to_screen(Vec2(world_x, world_y))
                    
                    # Scale sprite
                    sprite_size = int(self.TILE_SIZE * camera.zoom * deco.scale)
                    if sprite_size != 32:
                        sprite = pygame.transform.scale(sprite, (sprite_size, sprite_size))
                    
                    # Rotate if needed
                    if deco.rotation != 0:
                        sprite = pygame.transform.rotate(sprite, -deco.rotation)
                    
                    rect = sprite.get_rect()
                    rect.center = (int(screen_pos[0]), int(screen_pos[1]))
                    self._offscreen.blit(sprite, rect)
    
    def _draw_units(self, units: list[Unit], camera: Camera, selected_unit_ids: set[str] | None = None) -> None:
        """Draw units with MAXIMUM visibility - CRITICAL for gameplay.

        Uses simple, reliable rendering that CANNOT fail.
        Every unit MUST be visible regardless of data issues.
        """
        if self._screen is None or self._offscreen is None:
            return

        # DEBUG: Count units
        if len(units) == 0:
            return  # No units to draw (shouldn't happen in battle)

        screen_w, screen_h = self._screen.get_size()

        # Draw each unit with EXTREME defensive coding
        for idx, unit in enumerate(units):
            try:
                # STEP 1: Get unit position (with multiple fallback strategies)
                cx, cy = None, None

                # Strategy A: Use pixel_position if available
                if hasattr(unit, 'position') and unit.position is not None:
                    if hasattr(unit.position, 'pixel_position'):
                        try:
                            pos = camera.world_to_screen(unit.position.pixel_position)
                            cx, cy = int(pos[0]), int(pos[1])
                        except Exception:
                            pass

                # Strategy B: Use tile_position as fallback
                if (cx is None or cy is None) and hasattr(unit, 'position') and unit.position is not None:
                    if hasattr(unit.position, 'tile_position') or hasattr(unit.position, 'tile_x'):
                        try:
                            tile_x = getattr(unit.position, 'tile_x', None)
                            tile_y = getattr(unit.position, 'tile_y', None)
                            if tile_x is not None and tile_y is not None:
                                from pycc2.domain.value_objects.vec2 import Vec2
                                world_pos = Vec2(tile_x * 16, tile_y * 16)
                                pos = camera.world_to_screen(world_pos)
                                cx, cy = int(pos[0]), int(pos[1])
                        except Exception:
                            pass

                # Strategy C: Last resort - use index-based positioning (grid layout)
                if cx is None or cy is None:
                    # Place units in a visible grid pattern as emergency fallback
                    grid_x = (idx % 10) * 60 + 100  # Spread across screen
                    grid_y = (idx // 10) * 60 + 100
                    cx, cy = grid_x, grid_y

                # STEP 2: Skip if way off-screen (but be generous with bounds)
                if cx < -50 or cx > screen_w + 50 or cy < -50 or cy > screen_h + 50:
                    continue  # Unit is off-screen, skip it

                # STEP 3: Determine unit type for visual styling
                unit_name = ""
                unit_type_str = "infantry"  # Default

                if hasattr(unit, 'display_name'):
                    unit_name = str(unit.display_name)[:4]
                elif hasattr(unit, 'name'):
                    unit_name = str(unit.name)[:4]
                else:
                    unit_name = f"U{idx}"  # Fallback: use index

                if hasattr(unit, 'unit_type'):
                    unit_type_str = str(unit.unit_type).lower()
                elif hasattr(unit, 'category'):
                    unit_type_str = str(unit.category).lower()

                # STEP 4: Draw shape based on type (SIMPLE and RELIABLE)
                base_radius = max(12, int(15 * camera.zoom))

                # Make colors BRIGHT and VISIBLE (no subtle tones!)
                if "tank" in unit_type_str or "armor" in unit_type_str or "sherman" in unit_type_str or "vehicle" in unit_type_str:
                    # HEXAGON for tanks (BRIGHT YELLOW-ORANGE)
                    color = (255, 200, 0)  # Very bright yellow
                    radius = base_radius + 6
                    points = []
                    for i in range(6):
                        angle = math.pi / 3 * i
                        x = cx + int(radius * math.cos(angle))
                        y = cy + int(radius * math.sin(angle))
                        points.append((x, y))
                    pygame.draw.polygon(self._offscreen, color, points)
                    pygame.draw.polygon(self._offscreen, (255, 255, 255), points, 3)

                elif "mg" in unit_type_str or "machine" in unit_type_str or "at" in unit_type_str or "support" in unit_type_str:
                    # TRIANGLE for support (BRIGHT CYAN-BLUE)
                    color = (0, 220, 255)  # Bright cyan
                    radius = base_radius + 3
                    points = []
                    for i in range(3):
                        angle = math.pi / 3 * 2 * i - math.pi / 2
                        x = cx + int(radius * math.cos(angle))
                        y = cy + int(radius * math.sin(angle))
                        points.append((x, y))
                    pygame.draw.polygon(self._offscreen, color, points)
                    pygame.draw.polygon(self._offscreen, (255, 255, 255), points, 2)

                elif "sniper" in unit_type_str or "recon" in unit_type_str or "scout" in unit_type_str:
                    # DIAMOND for recon (BRIGHT MAGENTA-PURPLE)
                    color = (255, 0, 255)  # Bright magenta
                    radius = base_radius - 2
                    half = radius // 2
                    points = [
                        (cx, cy - radius),
                        (cx + half, cy),
                        (cx, cy + radius),
                        (cx - half, cy),
                    ]
                    pygame.draw.polygon(self._offscreen, color, points)
                    pygame.draw.polygon(self._offscreen, (255, 200, 255), points, 2)

                else:
                    # DEFAULT: CIRCLE for infantry (BRIGHT GREEN)
                    color = (0, 255, 80)  # Bright neon green
                    radius = base_radius
                    pygame.draw.circle(self._offscreen, color, (cx, cy), radius)
                    pygame.draw.circle(self._offscreen, (255, 255, 255), (cx, cy), radius, 2)

                # STEP 5: Draw label (CRITICAL for identification)
                try:
                    font = pygame.font.Font(None, max(16, int(18 * camera.zoom)))
                    label_surf = font.render(unit_name, True, (255, 255, 255))  # White text
                    label_x = cx - label_surf.get_width() // 2
                    label_y = cy + radius + 3

                    # Black background for readability
                    bg_padding = 3
                    bg_rect = pygame.Rect(
                        label_x - bg_padding,
                        label_y - bg_padding,
                        label_surf.get_width() + 2 * bg_padding,
                        label_surf.get_height() + 2 * bg_padding
                    )
                    pygame.draw.rect(self._offscreen, (0, 0, 0), bg_rect, border_radius=3)
                    pygame.draw.rect(self._offscreen, (100, 100, 100), bg_rect, width=1, border_radius=3)

                    # Blit text
                    self._offscreen.blit(label_surf, (label_x, label_y))
                except Exception:
                    pass  # Skip label if font fails

                # STEP 6: Selection indicator (VERY OBVIOUS when selected)
                is_selected = selected_unit_ids and unit.id in selected_unit_ids
                if is_selected:
                    # Pulsing yellow ring (large and obvious)
                    pulse = abs(math.sin(pygame.time.get_ticks() * 0.008)) * 8
                    select_radius = radius + 8 + int(pulse)

                    # Outer glow ring
                    pygame.draw.circle(self._offscreen, (255, 255, 0), (cx, cy), select_radius, 4)
                    pygame.draw.circle(self._offscreen, (255, 200, 0), (cx, cy), select_radius - 3, 2)

            except Exception as e:
                # CRITICAL: NEVER crash on a single unit - just skip it
                print(f"[WARN] Failed to render unit {idx}: {e}")
                continue
    
    def _draw_hexagon(
        self, cx: int, cy: int, radius: int, color: tuple[int, int, int],
        selected: bool = False
    ) -> None:
        """Draw a hexagon-shaped unit (mimics CC2 style)."""
        if self._screen is None:
            return
        
        points = []
        for i in range(6):
            angle = math.pi / 3 * i - math.pi / 6
            x = cx + int(radius * math.cos(angle))
            y = cy + int(radius * math.sin(angle))
            points.append((x, y))
        
        # Fill
        pygame.draw.polygon(self._offscreen, color, points)
        
        # Outline (darker)
        outline_color = (
            max(0, color[0] - 50),
            max(0, color[1] - 50),
            max(0, color[2] - 50)
        )
        pygame.draw.polygon(self._offscreen, outline_color, points, 2)
        
        # Selection indicator
        if selected:
            select_color = (255, 255, 0)
            pygame.draw.circle(self._offscreen, select_color, (cx, cy), radius + 3, 2)
    
    def _draw_grid(self, game_map: GameMap, camera: Camera) -> None:
        """Draw grid overlay for debugging."""
        if self._screen is None:
            return
        
        bounds = camera.view_bounds
        grid_color = (100, 100, 100, 100)
        
        start_x = max(0, int(bounds[0].x // self.TILE_SIZE))
        end_x = min(game_map.width, int((bounds[1].x // self.TILE_SIZE) + 2))
        start_y = max(0, int(bounds[0].y // self.TILE_SIZE))
        end_y = min(game_map.height, int((bounds[1].y // self.TILE_SIZE) + 2))
        
        tile_size_scaled = int(self.TILE_SIZE * camera.zoom)
        
        for ty in range(start_y, end_y + 1):
            from pycc2.domain.value_objects.vec2 import Vec2
            start_pos = camera.world_to_screen(Vec2(start_x * self.TILE_SIZE, ty * self.TILE_SIZE))
            end_pos = camera.world_to_screen(Vec2(end_x * self.TILE_SIZE, ty * self.TILE_SIZE))
            pygame.draw.line(
                self._offscreen, grid_color[:3],
                (int(start_pos[0]), int(start_pos[1])),
                (int(end_pos[0]), int(end_pos[1])), 1
            )
        
        for tx in range(start_x, end_x + 1):
            start_pos = camera.world_to_screen(Vec2(tx * self.TILE_SIZE, start_y * self.TILE_SIZE))
            end_pos = camera.world_to_screen(Vec2(tx * self.TILE_SIZE, end_y * self.TILE_SIZE))
            pygame.draw.line(
                self._offscreen, grid_color[:3],
                (int(start_pos[0]), int(start_pos[1])),
                (int(end_pos[0]), int(end_pos[1])), 1
            )
    
    def _apply_post_processing(self) -> None:
        """Apply minimal post-processing effects for performance.

        DISABLED heavy effects (color grading, film grain) that cause flickering.
        Only keep subtle vignette for cinematic feel, applied very infrequently.
        """
        if self._screen is None:
            return

        # ONLY apply vignette every 10 frames to prevent flickering
        if self._frame_count % 10 != 0:
            return

        w, h = self._screen.get_size()

        # Simple vignette only - no color grading or film grain
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        cx, cy = w // 2, h // 2
        max_dist = math.sqrt(cx**2 + cy**2)

        # Very sparse sampling for performance
        for y in range(0, h, 8):
            for x in range(0, w, 8):
                dist = math.sqrt((x - cx)**2 + (y - cy)**2) / max_dist
                if dist > 0.7:
                    alpha = int((dist - 0.7) * 20)  # Very subtle
                    if alpha > 0:
                        overlay.set_at((x, y), (15, 12, 8, alpha))

        self._offscreen.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        # DISABLED: Color grading (causes flickering on some systems)
        # DISABLED: Film grain (causes visual noise)
        # DISABLED: Contrast enhancement (causes brightness oscillation)
    
    def shutdown(self) -> None:
        """Clean up renderer resources."""
        self._texture_cache.clear()
        self._scaled_texture_cache.clear()
        self._height_lit_cache.clear()
        self._sprite_cache.clear()

    def resize(self, width: int, height: int) -> None:
        """Handle window resize."""
        pass
