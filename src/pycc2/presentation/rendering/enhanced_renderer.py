"""
Enhanced Pixel Art Renderer for PyCC2 - Phase A5 (CC2 Authentic)

Renders maps with authentic Close Combat 2 visual style.
Features:
- 48×48 pixel tiles (matching original CC2)
- Orthographic top-down projection (NOT isometric)
- CC2-authentic terrain palette from screenshot analysis
- Procedural texture generation with per-tile variation
- Deterministic random seeds for consistent regeneration

CC2 Visual Style Reference:
- Tile Size: 48×48 pixels (square, not diamond)
- Projection: Orthographic Top-Down
- Palette: Muted earthy military tones
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

# Import autotile system for cross-tile visual continuity
from pycc2.presentation.rendering.autotile_system import (
    get_neighbor_bitmap,
    get_continuity_variant,
    detect_building_clusters,
    get_building_cluster_info,
    is_autotile_terrain,
    get_edge_transition_width,
    AutotileCache,
)


# ============================================================
# CC2 Authentic Terrain Palette (from screenshot analysis)
# ============================================================
CC2_TERRAIN_PALETTE = {
    # Grass variants
    'grass_base':      (76, 124, 35),   # Main grass green
    'grass_light':     (90, 142, 43),   # Highlight patches
    'grass_dark':      (58, 100, 24),   # Shadow/depressions
    'grass_dry':       (138, 130, 60),  # Dry patch

    # Dirt/Rough
    'dirt_base':       (139, 109, 59),  # Dirt road/rough ground
    'dirt_dark':       (110, 85, 45),   # Dark dirt
    'dirt_light':      (160, 130, 75),  # Light dirt highlight

    # Road (cobblestone/gravel)
    'road_base':       (107, 99, 84),   # Gravel road gray-brown
    'road_stone':      (130, 125, 115), # Cobblestone
    'road_dark':       (85, 78, 68),    # Road shadow

    # Water
    'water_base':      (48, 96, 160),   # River blue
    'water_light':     (80, 140, 200),  # Wave highlights
    'water_dark':      (32, 72, 130),   # Deep water
    'water_foam':      (180, 210, 230), # Shore foam

    # Hedgerow (Normandy bocage) - 历史准确性增强版
    # 参考: 诺曼底战役历史数据 - Bocage地形特征:
    # - 土堤宽度: 1.8-3米 (非常宽!)
    # - 土堤高度: 1-1.5米 (很高!)
    # - 顶部植被: 额外2+米茂密生长
    # - 密度: 每8平方公里约3900个树篱田地 (极其密集!)
    # 结论: 树篱应非常突出、厚重、深色、形成天然"墙壁"
    'hedgerow_base':   (32, 72, 24),    # 更深的密集树篱绿 (原42,84,32)
    'hedgerow_light':  (48, 88, 34),   # 树篱高光 (稍亮)
    'hedgerow_dark':   (18, 52, 14),    # 树篱阴影 (更深! 原26,62,20)
    'embankment':      (68, 58, 38),    # 土堤棕色 (新增 - 历史特征!)

    # Wall
    'wall_base':       (112, 112, 112), # Stone wall gray
    'wall_dark':       (85, 85, 85),    # Wall shadow

    # Crater (shell hole)
    'crater_center':   (90, 74, 40),    # Crater bottom (dark)
    'crater_rim':      (122, 98, 56),   # Crater edge (lighter)

    # Trench (defensive earthwork)
    'trench_main':     (58, 40, 24),    # Dark brown main trench #3A2818
    'trench_embankment': (90, 72, 48),  # Lighter embankment #5A4830

    # Building ground
    'building_ground': (140, 130, 110), # Building footprint base
}

# Map terrain IDs to their base palette keys
TERRAIN_PALETTE_MAP = {
    0: 'grass_base',       # OPEN/GRASS
    1: 'road_base',        # ROAD
    2: 'grass_dark',       # GRASS (darker variant)
    3: 'hedgerow_base',    # WOODS (use dark hedge color for forest)
    4: 'building_ground',  # BUILDING_ENTERABLE
    5: 'wall_base',        # BUILDING_SOLID (stone)
    6: 'water_base',       # WATER
    7: 'hedgerow_base',    # HEDGE
    8: 'wall_base',        # WALL
    9: 'dirt_base',        # ROUGH
    10: 'water_light',     # SHALLOW
    11: 'dirt_light',      # BRIDGE
    12: 'crater_center',   # CRATER
    13: 'trench_main',     # TRENCH (defensive earthwork)
}


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
            12: self._make_palette((90, 85, 75),     # CRATER - dark gray-brown
                hue_range=8, sat_range=0.06),
            13: self._make_palette((58, 40, 24),      # TRENCH - dark earth brown
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
        palette: 'PaletteGenerator' | None = None,
        bitmask: int = 0
    ) -> pygame.Surface:
        """Generate a textured tile surface for given terrain type with autotile support.
        
        Args:
            terrain_id: Terrain type ID (0-12)
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
    def _fill_with_variation(surface: pygame.Surface, base_color: tuple, rng: random.Random, intensity: int = 12) -> None:
        """Fill surface with base color and subtle pixel-level variation (±10% brightness)."""
        surface.fill(base_color)
        try:
            pixels = pygame.surfarray.pixels3d(surface)
            w, h = surface.get_size()
            for y in range(h):
                for x in range(w):
                    # CC2-style: ±10% brightness random noise per pixel
                    offset = rng.randint(-intensity, intensity)
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
        surface: pygame.Surface, tid: int, var: int, pal: 'PaletteGenerator', bitmask: int = 0
    ) -> None:
        """OPEN (0): CC2 authentic grass with color variation and grass blade lines."""
        rng = random.Random(var * 17)
        # CC2's main grass green
        base = CC2_TERRAIN_PALETTE['grass_base']
        ProceduralTextureGenerator._fill_with_variation(surface, base, rng, 12)

        pixels = pygame.surfarray.pixels3d(surface)
        tile_sz = ProceduralTextureGenerator.TILE_SIZE

        # Grass blade lines (small dark green strokes suggesting grass texture)
        # CC2 spec: 15-25 per 48×48 tile, 2-4px short lines at random angles
        grass_dark = CC2_TERRAIN_PALETTE['grass_dark']
        num_blades = rng.randint(20, 35)  # Increased for 48×48 density
        for _ in range(num_blades):
            x = rng.randint(0, tile_sz - 1)
            y = rng.randint(0, tile_sz - 1)
            # Draw short grass blade line (2-4 pixels)
            length = rng.randint(2, 4)
            angle = rng.uniform(-0.5, 0.5)  # Wider angle range for natural look
            for i in range(length):
                px = int(x + i * math.cos(angle))
                py = int(y + i * math.sin(angle))
                if 0 <= px < tile_sz and 0 <= py < tile_sz:
                    shade_var = rng.randint(-8, 8)  # Slightly more variation
                    pixels[px, py] = (
                        max(0, min(255, grass_dark[0] + shade_var)),
                        max(0, min(255, grass_dark[1] + shade_var)),
                        max(0, min(255, grass_dark[2] + shade_var)),
                    )

        # Light highlight patches (sunlight through canopy effect)
        # CC2 spec: ~5-8 per tile, 6-10px diameter (radius 3-5)
        grass_light = CC2_TERRAIN_PALETTE['grass_light']
        num_patches = rng.randint(6, 10)
        for _ in range(num_patches):
            cx = rng.randint(5, tile_sz - 5)
            cy = rng.randint(5, tile_sz - 5)
            radius = rng.randint(3, 5)  # Larger patches for 48×48
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    if dx*dx + dy*dy <= radius*radius:
                        px, py = cx + dx, cy + dy
                        if 0 <= px < tile_sz and 0 <= py < tile_sz:
                            # Soft edge transition
                            dist_from_center = math.sqrt(dx*dx + dy*dy) / radius
                            if dist_from_center > 0.7:
                                # Blend to base color at edges
                                blend_factor = (dist_from_center - 0.7) / 0.3
                                base_px = pixels[px, py]
                                # Handle both numpy array and tuple access patterns
                                try:
                                    r_base = int(base_px[0][0]) if hasattr(base_px[0], '__len__') else int(base_px[0])
                                    g_base = int(base_px[1][0]) if hasattr(base_px[1], '__len__') else int(base_px[1])
                                    b_base = int(base_px[2][0]) if hasattr(base_px[2], '__len__') else int(base_px[2])
                                except (IndexError, TypeError):
                                    r_base, g_base, b_base = int(base_px[0]), int(base_px[1]), int(base_px[2])

                                pixels[px, py] = (
                                    int(grass_light[0] * (1 - blend_factor) + r_base * blend_factor),
                                    int(grass_light[1] * (1 - blend_factor) + g_base * blend_factor),
                                    int(grass_light[2] * (1 - blend_factor) + b_base * blend_factor),
                                )
                            else:
                                pixels[px, py] = grass_light

        # Occasional dry patches (natural ground variation)
        # CC2 spec: 2-3 per tile, brownish color #8A7840
        grass_dry = CC2_TERRAIN_PALETTE['grass_dry']
        num_dry = rng.randint(2, 4)
        for _ in range(num_dry):
            cx = rng.randint(6, tile_sz - 6)
            cy = rng.randint(6, tile_sz - 6)
            radius = rng.randint(2, 4)  # Slightly larger dry patches
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    if dx*dx + dy*dy <= radius*radius and rng.random() > 0.3:
                        px, py = cx + dx, cy + dy
                        if 0 <= px < tile_sz and 0 <= py < tile_sz:
                            pixels[px, py] = grass_dry

        del pixels

    @staticmethod
    def _texture_road(
        surface: pygame.Surface, tid: int, var: int, pal: 'PaletteGenerator', bitmask: int = 0
    ) -> None:
        """ROAD (1): CC2 authentic gravel road with texture and autotile continuity.
        
        Autotile behavior:
        - Connected edges (bitmask set): road extends to edge with no dark border
        - Non-connected edges: dark transition strip (4-6px) for terrain blending
        - Tire tracks align across connected tiles using bitmask as phase offset
        """
        from pycc2.presentation.rendering.autotile_system import (
            DIR_NORTH, DIR_EAST, DIR_SOUTH, DIR_WEST,
            get_edge_transition_width,
        )
        
        rng = random.Random(var * 67)
        # CC2's gravel road gray-brown
        road_color = CC2_TERRAIN_PALETTE['road_base']
        surface.fill(road_color)
        pixels = pygame.surfarray.pixels3d(surface)
        tile_sz = ProceduralTextureGenerator.TILE_SIZE

        # Calculate edge transitions based on autotile connectivity
        edge_widths = get_edge_transition_width(tid, bitmask, tile_sz)

        # Darker edges only on NON-connected sides (autotile improvement)
        # CC2 spec: Edge gradient darker edges (road_base * 0.75) fading inward over 4-6px
        road_dark = CC2_TERRAIN_PALETTE['road_dark']
        
        # North edge (only if not connected to road neighbor)
        if edge_widths['north'] > 0:
            for x in range(tile_sz):
                for y in range(edge_widths['north']):
                    gradient_factor = y / edge_widths['north'] if edge_widths['north'] > 0 else 0
                    darkness = int((1.0 - gradient_factor) * 40)
                    if rng.random() > 0.3:
                        r, g, b = int(pixels[x, y][0]), int(pixels[x, y][1]), int(pixels[x, y][2])
                        pixels[x, y] = (max(0, r - darkness), max(0, g - darkness), max(0, b - darkness))
        
        # South edge (only if not connected to road neighbor)
        if edge_widths['south'] > 0:
            for x in range(tile_sz):
                for y in range(tile_sz - edge_widths['south'], tile_sz):
                    dist_from_south = tile_sz - 1 - y
                    gradient_factor = dist_from_south / edge_widths['south'] if edge_widths['south'] > 0 else 0
                    darkness = int((1.0 - gradient_factor) * 40)
                    if rng.random() > 0.3:
                        r, g, b = int(pixels[x, y][0]), int(pixels[x, y][1]), int(pixels[x, y][2])
                        pixels[x, y] = (max(0, r - darkness), max(0, g - darkness), max(0, b - darkness))

        # West edge (only if not connected to road neighbor)
        if edge_widths['west'] > 0:
            for x in range(edge_widths['west']):
                dist_from_west = x
                gradient_factor = dist_from_west / edge_widths['west'] if edge_widths['west'] > 0 else 0
                darkness = int((1.0 - gradient_factor) * 40)
                if rng.random() > 0.3:
                    for y in range(tile_sz):
                        r, g, b = int(pixels[x, y][0]), int(pixels[x, y][1]), int(pixels[x, y][2])
                        pixels[x, y] = (max(0, r - darkness), max(0, g - darkness), max(0, b - darkness))

        # East edge (only if not connected to road neighbor)
        if edge_widths['east'] > 0:
            for x in range(tile_sz - edge_widths['east'], tile_sz):
                dist_from_east = tile_sz - 1 - x
                gradient_factor = dist_from_east / edge_widths['east'] if edge_widths['east'] > 0 else 0
                darkness = int((1.0 - gradient_factor) * 40)
                if rng.random() > 0.3:
                    for y in range(tile_sz):
                        r, g, b = int(pixels[x, y][0]), int(pixels[x, y][1]), int(pixels[x, y][2])
                        pixels[x, y] = (max(0, r - darkness), max(0, g - darkness), max(0, b - darkness))

        # *** Gravel/pebble texture - 高密度碎石颗粒 (60-85 for 48×48) ***
        # CC2 spec: ~50-70 dots per 48×48 tile (enhanced)
        road_stone = CC2_TERRAIN_PALETTE['road_stone']
        num_pebbles = rng.randint(60, 85)  # 提升碎石密度!
        for _ in range(num_pebbles):
            px = rng.randint(max(2, min(edge_widths.values())), tile_sz - max(2, min(edge_widths.values())) - 2)
            py = rng.randint(max(2, min(edge_widths.values())), tile_sz - max(2, min(edge_widths.values())) - 2)
            pebble_var = rng.randint(-18, 18)  # 更多颜色变化
            pixels[px, py] = tuple(max(0, min(255, c + pebble_var)) for c in road_stone)
            # 更频繁的大颗粒（cluster effect增强）
            if rng.random() > 0.55:
                dx, dy = rng.choice([(1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, -1)])
                if max(2, min(edge_widths.values())) <= px + dx < tile_sz - max(2, min(edge_widths.values())) and \
                   max(2, min(edge_widths.values())) <= py + dy < tile_sz - max(2, min(edge_widths.values())):
                    pixels[px + dx, py + dy] = tuple(max(0, min(255, c + pebble_var - 10)) for c in road_stone)

        # *** Subtle tire track marks with AUTOTILE ALIGNMENT - 增强版 ***
        # Use bitmask value as phase seed so tracks line up across connected tiles
        # CC2 spec: 2-4 parallel darker lines running along the road direction
        track_color = CC2_TERRAIN_PALETTE['road_dark']
        num_tracks = rng.randint(2, 4)  # Variable number of tracks

        # Autotile alignment: use bitmask to offset track positions for continuity
        track_phase_offset = (bitmask * 3) % (tile_sz // 3)  # Deterministic offset from connectivity
        track_positions = sorted([
            (tile_sz // 5 + track_phase_offset + i * (tile_sz // 5)) % (tile_sz - 8)
            for i in range(num_tracks)
        ])

        for track_y in track_positions:
            for x in range(tile_sz):
                # *** 更自然的断续效果 (30%断点率) ***
                if rng.random() > 0.3:
                    # Only draw tracks within non-edge area
                    min_edge = max(3, min(edge_widths.values()))
                    if min_edge <= track_y < tile_sz - min_edge:
                        # Main track line (variable width 1-2px)
                        pixels[x, track_y] = track_color
                        # Track shadow/wear (adjacent pixel - 更频繁)
                        if 0 <= track_y + 1 < tile_sz and rng.random() > 0.4:
                            pixels[x, track_y + 1] = tuple(max(0, c + 12) for c in track_color)
                        # 偶尔的宽轮胎痕迹（双像素宽）
                        if rng.random() > 0.85 and 0 <= track_y - 1 < tile_sz:
                            pixels[x, track_y - 1] = tuple(max(0, c + 8) for c in track_color)

        del pixels

    @staticmethod
    def _texture_grass(
        surface: pygame.Surface, tid: int, var: int, pal: 'PaletteGenerator', bitmask: int = 0
    ) -> None:
        """GRASS (2): Medium green with dense grass blade texture - WWII Normandy meadow style.

        增强版纹理密度（目标: 接近CC2原版的多层次草叶效果）
        """
        rng = random.Random(var * 31)
        base = (105, 165, 55)
        ProceduralTextureGenerator._fill_with_variation(surface, base, rng, 14)

        pixels = pygame.surfarray.pixels3d(surface)
        tile_sz = ProceduralTextureGenerator.TILE_SIZE

        # *** Grass blades - 高密度垂直草叶 (35-55 blades for 48×48) ***
        num_blades = rng.randint(35, 55)  # 提升密度!
        for _ in range(num_blades):
            x = rng.randint(0, tile_sz - 1)
            y_start = rng.randint(0, tile_sz - 10)
            length = rng.randint(4, 8)  # 更长的草叶
            # 多层颜色变化（更自然的绿色渐变）
            shade = rng.choice([
                (90, 150, 45),   # 深绿
                (120, 180, 65),  # 亮绿
                (85, 140, 40),   # 暗绿
                (110, 170, 55),  # 中绿
                (100, 160, 50),  # 标准绿
            ])
            for dy in range(length):
                if 0 <= y_start + dy < tile_sz:
                    # 草叶宽度变化（1-2px）增加真实感
                    blade_width = 1 if rng.random() > 0.3 else 2
                    for dx in range(blade_width):
                        if 0 <= x + dx < tile_sz:
                            pixels[x + dx, y_start + dy] = shade

        # *** 更大的暗色斑块（土壤/阴影区域）***
        num_patches = rng.randint(6, 11)  # 增加斑块数量
        for _ in range(num_patches):
            cx = rng.randint(tile_sz // 10, tile_sz - tile_sz // 10)
            cy = rng.randint(tile_sz // 10, tile_sz - tile_sz // 10)
            patch_size_y = rng.randint(3, 6)
            patch_size_x = rng.randint(3, 6)
            for ddy in range(patch_size_y):
                for ddx in range(patch_size_x):
                    if 0 <= cx + ddx < tile_sz and 0 <= cy + ddy < tile_sz:
                        pixels[cx + ddx, cy + ddy] = (80, 130, 35)
        del pixels

    @staticmethod
    def _texture_woods(
        surface: pygame.Surface, tid: int, var: int, pal: 'PaletteGenerator', bitmask: int = 0
    ) -> None:
        """WOODS (3): CC2 very dark green forest with individual tree canopies visible."""
        rng = random.Random(var * 41)
        # CC2's very dark forest green
        base = (45, 68, 33)
        surface.fill(base)
        pixels = pygame.surfarray.pixels3d(surface)
        tile_sz = ProceduralTextureGenerator.TILE_SIZE

        try:
            import numpy as np

            # Subtle noise for forest floor variation - use numpy for safe operations
            for y in range(tile_sz):
                for x in range(tile_sz):
                    offset = rng.randint(-8, 8)  # More variation for larger tile
                    r, g, b = int(pixels[x, y][0]), int(pixels[x, y][1]), int(pixels[x, y][2])
                    # Clamp to [0, 255] using numpy-safe method
                    new_r = max(0, min(255, r + offset))
                    new_g = max(0, min(255, g + offset))
                    new_b = max(0, min(255, b + offset))
                    pixels[x, y] = (new_r, new_g, new_b)

            # Individual tree canopies (6-12 trees per tile for 48×48 density)
            num_trees = rng.randint(6, 12)  # More trees for larger tile
            for _ in range(num_trees):
                cx = rng.randint(tile_sz // 8, tile_sz - tile_sz // 8)
                cy = rng.randint(tile_sz // 8, tile_sz - tile_sz // 8)
                radius = rng.randint(7, 13)  # Larger trees for 48×48

                # Draw tree canopy as circle with shading
                for y in range(max(0, cy - radius), min(tile_sz, cy + radius + 1)):
                    for x in range(max(0, cx - radius), min(tile_sz, cx + radius + 1)):
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
                trunk_y = min(tile_sz - 1, cy + radius - 3)
                if 0 <= cx < tile_sz and 0 <= trunk_y < tile_sz:
                    pixels[cx, trunk_y] = (65, 48, 28)

            # Shadow dots under trees (adds depth)
            for _ in range(num_trees):
                sx = rng.randint(tile_sz // 10, tile_sz - tile_sz // 10)
                sy = rng.randint(int(0.7 * tile_sz), tile_sz - 1)
                pixels[sx, sy] = (28, 45, 20)
        except Exception as e:
            # Fallback: just use base color if numpy operations fail
            pass
        finally:
            del pixels

    @staticmethod
    def _texture_building_enterable(
        surface: pygame.Surface, tid: int, var: int, pal: 'PaletteGenerator', bitmask: int = 0
    ) -> None:
        """BUILDING_ENTERABLE (4): CC2 earthy brown building with visible roof, door, windows."""
        rng = random.Random(var * 103)

        # CC2's earthy brown/tan building walls
        wall_color = (139, 115, 85)
        surface.fill(wall_color)
        pixels = pygame.surfarray.pixels3d(surface)
        tile_sz = ProceduralTextureGenerator.TILE_SIZE

        # Roof line at top (darker brown, pitched roof appearance) - scaled for 48×48
        roof_color = (110, 75, 45)
        roof_height = tile_sz // 6  # Proportional roof height
        for x in range(tile_sz):
            for y in range(0, roof_height):
                pixels[x, y] = roof_color
            # Roof edge highlight
            if roof_height < tile_sz:
                pixels[x, roof_height] = (95, 62, 35)

        # Wall texture - subtle brick pattern hints - scaled for larger tile
        brick_color = (130, 108, 78)
        brick_spacing_y = max(3, tile_sz // 12)  # Adaptive spacing
        brick_width = max(5, tile_sz // 7)
        brick_offset = max(3, brick_width // 2)

        for y in range(roof_height + 1, tile_sz, brick_spacing_y):
            offset = brick_offset if ((y - roof_height - 1) // brick_spacing_y) % 2 == 0 else 0
            for x in range(offset, tile_sz - brick_width + 1, brick_width * 2):
                if rng.random() > 0.5:
                    for dx in range(brick_width - 1):
                        if x + dx < tile_sz and y < tile_sz:
                            pixels[x + dx, y] = brick_color

        # Door (center bottom, clearly visible) - scaled position and size
        door_color = (90, 58, 33)
        door_top = int(0.42 * tile_sz)
        door_bottom = min(tile_sz - 1, int(0.65 * tile_sz))
        door_left = tile_sz // 3
        door_right = 2 * tile_sz // 3

        for y in range(door_top, door_bottom):
            for x in range(door_left, door_right):
                pixels[x, y] = door_color
        # Door frame (darker outline)
        frame_color = (70, 45, 25)
        for y in range(door_top, door_bottom):
            if door_left < tile_sz:
                pixels[door_left, y] = frame_color
            if door_right < tile_sz:
                pixels[door_right - 1, y] = frame_color
        for x in range(door_left, door_right):
            if door_top < tile_sz:
                pixels[x, door_top] = frame_color

        # Window (upper area, light blue-white) - scaled size
        window_color = (150, 185, 215)
        window_top = int(0.21 * tile_sz)
        window_bottom = int(0.33 * tile_sz)
        window_left = tile_sz // 8
        window_right = tile_sz // 4

        for y in range(window_top, window_bottom):
            for x in range(window_left, window_right):
                pixels[x, y] = window_color
        # Window frame
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

        # Second window (right side) - scaled position
        second_window_left = 3 * tile_sz // 5
        second_window_right = 7 * tile_sz // 10

        for y in range(window_top, window_bottom):
            for x in range(second_window_left, second_window_right):
                pixels[x, y] = window_color
        # Window frame
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
        surface: pygame.Surface, tid: int, var: int, pal: 'PaletteGenerator', bitmask: int = 0
    ) -> None:
        """BUILDING_SOLID (5): Gray stone/brick building, no door, solid walls, roof line."""
        rng = random.Random(var * 109)

        # Stone walls - gray
        wall_color = (140, 138, 135)
        surface.fill(wall_color)
        pixels = pygame.surfarray.pixels3d(surface)
        tile_sz = ProceduralTextureGenerator.TILE_SIZE

        # Roof line at top (dark gray) - scaled
        roof_color = (90, 85, 80)
        roof_height = max(2, tile_sz // 10)
        for x in range(tile_sz):
            for y in range(0, roof_height):
                pixels[x, y] = roof_color
            if roof_height < tile_sz:
                pixels[x, roof_height] = (75, 70, 65)

        # Stone block pattern - scaled for 48×48
        stone_dark = (120, 118, 115)
        stone_light = (155, 152, 148)
        block_height = max(4, tile_sz // 10)
        block_width = max(6, tile_sz // 6)
        mortar_offset = max(2, block_width // 3)

        for y in range(roof_height + 1, tile_sz, block_height):
            offset = mortar_offset if ((y - roof_height - 1) // block_height) % 2 == 0 else 0
            for x in range(offset, tile_sz - block_width + 1, block_width * 2):
                # Stone block
                for dy in range(block_height - 1):
                    for dx in range(block_width - 1):
                        if x + dx < tile_sz and y + dy < tile_sz:
                            color = stone_dark if rng.random() > 0.5 else stone_light
                            pixels[x + dx, y + dy] = color
            # Mortar lines
            for x in range(tile_sz):
                if y < tile_sz:
                    pixels[x, y] = (100, 98, 95)

        # No door - solid walls. Add a small vent/window slit - scaled position
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
        surface: pygame.Surface, tid: int, var: int, pal: 'PaletteGenerator', bitmask: int = 0
    ) -> None:
        """WATER (6): CC2 authentic water with wave animation hints and autotile continuity.
        
        Autotile behavior:
        - Connected edges (bitmask set): pure water color to edge, no shore transition
        - Non-connected edges: draw shore/bank transition (darker gradient 4-6px)
        - Wave animation flows in consistent direction using position-based phase
        - Sparkle points distribute evenly across continuous water area
        """
        from pycc2.presentation.rendering.autotile_system import get_edge_transition_width
        
        rng = random.Random(var * 127)
        # CC2's river blue
        base = CC2_TERRAIN_PALETTE['water_base']
        surface.fill(base)
        pixels = pygame.surfarray.pixels3d(surface)
        tile_sz = ProceduralTextureGenerator.TILE_SIZE

        # Subtle depth variation (±10 brightness noise for organic feel)
        for y in range(tile_sz):
            for x in range(tile_sz):
                offset = rng.randint(-10, 10)  # Slightly more variation
                r, g, b = int(pixels[x, y][0]), int(pixels[x, y][1]), int(pixels[x, y][2])
                pixels[x, y] = (
                    max(0, min(255, r + offset)),
                    max(0, min(255, g + offset)),
                    max(0, min(255, b + offset))
                )

        # Wave animation hints with AUTOTILE CONTINUITY
        # Use position-based phase so waves align across connected tiles
        # CC2 spec: Short horizontal bright lines (water_light #508CC8), 4-8px long, 1px thick, ~8-15 per tile
        water_light = CC2_TERRAIN_PALETTE['water_light']
        num_waves = rng.randint(12, 20)  # Increased for 48×48 density
        
        # Autotile phase alignment for waves
        wave_phase_offset = bitmask * 7  # Deterministic phase from connectivity pattern
        
        for i in range(num_waves):
            wy = rng.randint(3, tile_sz - 3)
            wx_start = rng.randint(2, tile_sz - 6)
            wave_len = rng.randint(4, 8)  # CC2 spec: 4-8px long waves
            
            for j in range(wave_len):
                wx = wx_start + j
                if 0 <= wx < tile_sz:
                    # Slight vertical wiggle for natural wave appearance
                    # Autotile: add phase offset based on bitmask for continuity
                    wy_offset = int(math.sin((i * 0.7 + var * 0.5) + (wave_phase_offset * 0.1)) * 1.5)
                    if 0 <= wy + wy_offset < tile_sz:
                        pixels[wx, wy + wy_offset] = water_light

        # Sparkle highlights (few bright dots reflecting sunlight)
        # CC2 spec: Bright white pixels (#B8D8F8) simulating sun reflection
        sparkle_color = (184, 216, 248)  # #B8D8F8
        num_sparkles = rng.randint(5, 9)  # More sparkles for larger tile
        for _ in range(num_sparkles):
            sx = rng.randint(4, tile_sz - 4)
            sy = rng.randint(4, tile_sz - 4)
            pixels[sx, sy] = sparkle_color
            # Occasional adjacent sparkle pixel for brighter effect
            if rng.random() > 0.7:
                dx, dy = rng.choice([(1, 0), (0, 1)])
                if 0 <= sx + dx < tile_sz and 0 <= sy + dy < tile_sz:
                    pixels[sx + dx, sy + dy] = (200, 225, 240)  # Slightly dimmer adjacent

        # Shore/bank transitions ONLY on non-connected edges (autotile improvement)
        # CC2 spec: Darker near banks (water_dark #204882), lighter in center
        water_dark = CC2_TERRAIN_PALETTE['water_dark']
        
        # Calculate which edges need shore transition
        edge_widths = get_edge_transition_width(tid, bitmask, tile_sz)

        # Apply shore transition only where NOT connected to water neighbor
        if any(width > 0 for width in edge_widths.values()):
            for x in range(tile_sz):
                for y in range(tile_sz):
                    # Check distance from each edge
                    dist_from_left = x
                    dist_from_right = tile_sz - 1 - x
                    dist_from_top = y
                    dist_from_bottom = tile_sz - 1 - y
                    
                    # Find minimum distance to any non-connected edge
                    min_dist_to_edge = tile_sz  # Start with large value
                    
                    if edge_widths['west'] > 0 and dist_from_left < edge_widths['west']:
                        min_dist_to_edge = min(min_dist_to_edge, dist_from_left)
                    
                    if edge_widths['east'] > 0 and dist_from_right < edge_widths['east']:
                        min_dist_to_edge = min(min_dist_to_edge, dist_from_right)
                    
                    if edge_widths['north'] > 0 and dist_from_top < edge_widths['north']:
                        min_dist_to_edge = min(min_dist_to_edge, dist_from_top)
                    
                    if edge_widths['south'] > 0 and dist_from_bottom < edge_widths['south']:
                        min_dist_to_edge = min(min_dist_to_edge, dist_from_bottom)
                    
                    # If close to a non-connected edge, apply darkening
                    if min_dist_to_edge < tile_sz and rng.random() > 0.5:
                        # Determine which edge is closest and use its width
                        current_edge_width = 0
                        if edge_widths['west'] > 0:
                            current_edge_width = edge_widths['west']
                        elif edge_widths['east'] > 0:
                            current_edge_width = edge_widths['east']
                        elif edge_widths['north'] > 0:
                            current_edge_width = edge_widths['north']
                        elif edge_widths['south'] > 0:
                            current_edge_width = edge_widths['south']
                        
                        if current_edge_width > 0:
                            gradient = min_dist_to_edge / current_edge_width
                            darkness = int((1.0 - gradient) * 25)
                            
                            if darkness > 0:
                                r, g, b = int(pixels[x, y][0]), int(pixels[x, y][1]), int(pixels[x, y][2])
                                pixels[x, y] = (
                                    max(32, r - darkness),  # Don't go darker than water_dark
                                    max(72, g - darkness),
                                    max(130, b - darkness)
                                )

        del pixels

    @staticmethod
    def _texture_hedge(
        surface: pygame.Surface, tid: int, var: int, pal: 'PaletteGenerator', bitmask: int = 0
    ) -> None:
        """HEDGE (7): CC2 authentic Normandy bocage hedgerow - 历史准确性增强版

        基于诺曼底战役历史数据的Bocage特征:
        - 土堤宽度: 1.8-3米 (对应像素8-12px宽!)
        - 土堤高度: 1-1.5米 (非常高的视觉障碍!)
        - 顶部植被: 额外2+米茂密生长 (密集叶片纹理!)
        - 历史密度: ~3900个树篱田地/8sqkm (形成天然"墙壁")

        视觉增强（相比原版）:
        - 更厚: base_width从4-8px增加到8-14px
        - 更暗: 使用更深的绿色调色板
        - 更多纹理: 叶片斑点数量增加50%
        - 更突出的土堤: 添加棕色土堤底层

        Autotile behavior:
        - Connected edges (bitmask set): hedge extends smoothly to tile boundary (no gap)
        - Non-connected edges: hedge has ragged end (tapered termination)
        """
        from pycc2.presentation.rendering.autotile_system import (
            DIR_NORTH, DIR_EAST, DIR_SOUTH, DIR_WEST,
            get_edge_transition_width,
        )

        rng = random.Random(var * 151)
        tile_sz = ProceduralTextureGenerator.TILE_SIZE

        # Background: slightly lighter ground visible at edges
        ground_color = (90, 130, 55)  # 稍暗的草地背景（对比更强）
        surface.fill(ground_color)
        pixels = pygame.surfarray.pixels3d(surface)

        # Hedgerow colors (使用增强版深色调色板!)
        hedge_dark = CC2_TERRAIN_PALETTE['hedgerow_dark']      # (18, 52, 14) - 非常深!
        hedge_base = CC2_TERRAIN_PALETTE['hedgerow_base']       # (32, 72, 24) - 深绿
        hedge_light = CC2_TERRAIN_PALETTE['hedgerow_light']     # (48, 88, 34) - 高光
        embankment_color = CC2_TERRAIN_PALETTE.get('embankment', (68, 58, 38))  # 土堤棕色

        # Calculate edge connectivity for tapering
        edge_widths = get_edge_transition_width(tid, bitmask, tile_sz)

        center_y = tile_sz // 2
        # *** 历史准确性增强: 更厚的树篱 (10-16px代替8-14px)! ***
        base_width = rng.randint(10, 16)  # 进一步增加厚度!

        # Create top edge using random walk with AUTOTILE coordination
        # *** 增强版: 更大的随机偏移 (±3px) 实现更不规则的bocage锯齿边缘 ***
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

            # *** 增加随机偏移范围 (±3px) - 更自然的bocage不规则边缘 ***
            y += coord_rng.randint(-3, 3)

            y = max(tile_sz // 6, min(5 * tile_sz // 6, y))

        # Create bottom edge using random walk (independent of top for irregularity)
        # *** 同样增加底部边缘的不规则性 ***
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

            # *** 底部边缘也使用±3px偏移 ***
            y += coord_rng.randint(-3, 3)

            y = max(tile_sz // 6, min(5 * tile_sz // 6, y))

        # Fill the irregular hedge area between edges with EMBANKMENT LAYER first!
        # *** 新增: 土堤底层 (历史特征!) ***
        embankment_offset = 2  # 土堤在主植被层下方扩展2px
        for x in range(tile_sz):
            if x < len(top_edge) and x < len(bottom_edge):
                y_top = top_edge[x][1] - embankment_offset
                y_bottom = bottom_edge[x][1] + embankment_offset

                if y_top > y_bottom:
                    y_top, y_bottom = y_bottom, y_top

                for y in range(y_top, y_bottom):
                    if 0 <= y < tile_sz:
                        # 土堤颜色（只在边缘区域显示，中心被植被覆盖）
                        edge_dist = min(abs(y - y_top), abs(y - y_bottom))
                        if edge_dist <= embankment_offset + 1:
                            pixels[x, y] = embankment_color

        # Fill main hedge vegetation area (覆盖在土堤之上!)
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
                            pixels[x, y] = hedge_dark      # 密集阴影区域 (22%)
                        elif r > 0.35:
                            pixels[x, y] = hedge_base       # 主树篱颜色 (45%)
                        elif r > 0.15:
                            pixels[x, y] = hedge_light      # 高光区域 (20%)
                        else:
                            # *** 新增: 超高光叶片斑点 (13%) - 增加视觉层次! ***
                            pixels[x, y] = (65, 105, 42)   # 亮绿色叶片高光

        # *** 新增: 额外的叶片细节斑点 (模拟密集灌木丛中的透光效果) ***
        num_leaf_clusters = rng.randint(15, 25)  # 大量叶片簇!
        for _ in range(num_leaf_clusters):
            lx = rng.randint(tile_sz // 8, 7 * tile_sz // 8)
            ly = rng.randint(tile_sz // 6, 5 * tile_sz // 6)
            cluster_size = rng.randint(2, 4)  # 小型叶片簇

            # 检查是否在树篱区域内（近似检查）
            if lx < len(top_edge) and ly > top_edge[min(lx, len(top_edge)-1)][1] and \
               ly < bottom_edge[min(lx, len(bottom_edge)-1)][1]:
                leaf_color = rng.choice([
                    (55, 95, 35),   # 中绿
                    (70, 115, 45),   # 亮绿
                    (40, 75, 28),    # 暗绿
                    (85, 130, 50),   # 很亮的叶尖
                ])
                for dy in range(cluster_size):
                    for dx in range(cluster_size):
                        if 0 <= lx + dx < tile_sz and 0 <= ly + dy < tile_sz:
                            if rng.random() > 0.4:  # 稀疏分布
                                pixels[lx + dx, ly + dy] = leaf_color

        # Apply TAPERING on non-connected edges (autotile feature)
        if edge_widths['west'] > 0 and not (bitmask & DIR_WEST):
            taper_width = min(edge_widths['west'], 10)  # 增加锥度宽度!
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

        if edge_widths['east'] > 0 and not (bitmask & DIR_EAST):
            taper_width = min(edge_widths['east'], 10)
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

        # Add overlapping bushy circles/ovals for organic texture
        # *** 历史准确性增强: 更多灌木丛 (9-15个代替5-9个)! ***
        num_bushes = rng.randint(9, 15)  # 增加数量以获得更密集外观!
        for _ in range(num_bushes):
            cx = rng.randint(tile_sz // 6, 5 * tile_sz // 6)
            cy = rng.randint(tile_sz // 4, 3 * tile_sz // 4)

            radius_x = rng.randint(5, 10)   # 更大的灌木半径!
            radius_y = rng.randint(4, 9)    # 更大的灌木半径!

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

        # Leaf detail: Small light-green speckles scattered within
        # *** 历史准确性增强: 大幅增加叶片细节 (45-75个代替30-50个)! ***
        leaf_color = (52, 98, 36)  # 稍微调整的叶片色
        num_leaves = rng.randint(45, 75)  # 增加50%以上的叶片数量!
        for _ in range(num_leaves):
            lx = rng.randint(2, tile_sz - 3)
            ly = rng.randint(tile_sz // 5, 4 * tile_sz // 5)

            if lx < len(top_edge) and lx < len(bottom_edge):
                y_top = top_edge[lx][1]
                y_bottom = bottom_edge[lx][1]
                if y_top <= ly <= y_bottom:
                    pixels[lx, ly] = leaf_color
                    # Occasional adjacent leaf pixel for clumping effect (增加聚集概率!)
                    if rng.random() > 0.65:  # 原来是0.75，现在是0.65 (更多聚集!)
                        dx, dy = rng.choice([(1, 0), (0, 1), (-1, 0), (0, -1)])
                        if 0 <= lx + dx < tile_sz and 0 <= ly + dy < tile_sz:
                            pixels[lx + dx, ly + dy] = (
                                min(255, leaf_color[0] + 15),
                                min(255, leaf_color[1] + 10),
                                min(255, leaf_color[2] + 12)
                            )

        del pixels

    @staticmethod
    def _texture_wall(
        surface: pygame.Surface, tid: int, var: int, pal: 'PaletteGenerator', bitmask: int = 0
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

        # Brick pattern with mortar lines - scaled for 48×48
        brick_height = max(4, tile_sz // 10)
        brick_width = max(8, tile_sz // 4)
        brick_offset = max(5, brick_width - 3)

        for y in range(0, tile_sz, brick_height):
            offset = brick_offset if (y // brick_height) % 2 == 0 else 0
            # Mortar line
            for x in range(tile_sz):
                if y < tile_sz:
                    pixels[x, y] = mortar_color
            # Bricks
            for bx in range(offset, tile_sz - brick_width + 1, brick_width * 2):
                for dy in range(1, brick_height):
                    for dx in range(1, brick_width - 1):
                        if bx + dx < tile_sz and y + dy < tile_sz:
                            color = brick_dark if rng.random() > 0.5 else brick_light
                            pixels[bx + dx, y + dy] = color
                # Vertical mortar
                if bx + brick_width - 1 < tile_sz:
                    for dy in range(1, brick_height):
                        if y + dy < tile_sz:
                            pixels[bx + brick_width - 1, y + dy] = mortar_color

        # Top cap (slightly wider/darker) - scaled
        for x in range(tile_sz):
            pixels[x, 0] = (80, 78, 75)
            if 1 < tile_sz:
                pixels[x, 1] = (100, 98, 95)
        del pixels

    @staticmethod
    def _texture_rough(
        surface: pygame.Surface, tid: int, var: int, pal: 'PaletteGenerator', bitmask: int = 0
    ) -> None:
        """ROUGH (9): Brown dirt/rubble with scattered rocks."""
        rng = random.Random(var * 193)
        base = (155, 130, 85)
        ProceduralTextureGenerator._fill_with_variation(surface, base, rng, 18)

        pixels = pygame.surfarray.pixels3d(surface)
        tile_sz = ProceduralTextureGenerator.TILE_SIZE

        # Scattered rocks - increased for 48×48
        rock_colors = [(120, 115, 105), (140, 135, 125), (100, 95, 85)]
        num_rocks = rng.randint(12, 20)  # More rocks for larger tile
        for _ in range(num_rocks):
            rx = rng.randint(tile_sz // 16, tile_sz - tile_sz // 16)
            ry = rng.randint(tile_sz // 16, tile_sz - tile_sz // 16)
            size = rng.randint(2, 5)  # Slightly larger rocks
            rock_color = rng.choice(rock_colors)
            for dy in range(size):
                for dx in range(size):
                    if 0 <= rx + dx < tile_sz and 0 <= ry + dy < tile_sz:
                        pixels[rx + dx, ry + dy] = rock_color

        # Dirt patches - scaled
        num_patches = rng.randint(7, 12)  # More patches for larger tile
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
        surface: pygame.Surface, tid: int, var: int, pal: 'PaletteGenerator', bitmask: int = 0
    ) -> None:
        """SHALLOW (10): Light blue shallow water with sandy bottom visible."""
        rng = random.Random(var * 211)
        base = (120, 185, 225)
        surface.fill(base)
        pixels = pygame.surfarray.pixels3d(surface)
        tile_sz = ProceduralTextureGenerator.TILE_SIZE

        # Sandy bottom showing through - increased for 48×48
        sand_color = (195, 180, 140)
        num_sand_patches = rng.randint(20, 35)  # More sand patches for larger tile
        for _ in range(num_sand_patches):
            sx = rng.randint(tile_sz // 16, tile_sz - tile_sz // 16)
            sy = rng.randint(tile_sz // 16, tile_sz - tile_sz // 16)
            size = rng.randint(2, 6)  # Larger sand patches
            for dy in range(size):
                for dx in range(size):
                    if 0 <= sx + dx < tile_sz and 0 <= sy + dy < tile_sz and rng.random() > 0.4:
                        pixels[sx + dx, sy + dy] = sand_color

        # Gentle wave ripples - scaled frequency and amplitude
        ripple_color = (150, 205, 240)
        ripple_spacing_y = max(4, tile_sz // 8)  # Adaptive spacing
        for y in range(ripple_spacing_y, tile_sz - ripple_spacing_y, ripple_spacing_y):
            for x in range(tile_sz):
                wy = y + int(math.sin(x * 0.5 + var) * 1.5)  # Slightly more wave amplitude
                if 0 <= wy < tile_sz:
                    pixels[x, wy] = ripple_color
        del pixels

    @staticmethod
    def _texture_bridge(
        surface: pygame.Surface, tid: int, var: int, pal: 'PaletteGenerator', bitmask: int = 0
    ) -> None:
        """BRIDGE (11): Brown wooden planks with support beams, clearly a bridge."""
        rng = random.Random(var * 241)

        # Water underneath at edges
        water_color = (40, 110, 200)
        surface.fill(water_color)
        pixels = pygame.surfarray.pixels3d(surface)
        tile_sz = ProceduralTextureGenerator.TILE_SIZE

        # Bridge deck - wooden planks (scaled position and size)
        plank_color = (160, 120, 70)
        plank_dark = (130, 95, 55)
        deck_top = max(2, tile_sz // 8)  # Scaled deck boundaries
        deck_bottom = min(tile_sz - 2, int(0.54 * tile_sz))
        deck_left = max(1, tile_sz // 16)
        deck_right = min(tile_sz - 1, int(0.625 * tile_sz))

        for y in range(deck_top, deck_bottom):
            for x in range(deck_left, deck_right):
                pixels[x, y] = plank_color

        # Plank lines (horizontal gaps between planks) - scaled spacing
        plank_spacing = max(3, tile_sz // 12)
        for y in range(deck_top, deck_bottom, plank_spacing):
            for x in range(deck_left, deck_right):
                if x < tile_sz and y < tile_sz:
                    pixels[x, y] = plank_dark

        # Plank grain (vertical lines per plank) - scaled
        grain_spacing_x = max(4, tile_sz // 8)
        for x in range(deck_left + grain_spacing_x, deck_right, grain_spacing_x):
            for y in range(deck_top, deck_bottom):
                if x < tile_sz and y < tile_sz and rng.random() > 0.6:
                    pixels[x, y] = plank_dark

        # Support beams (vertical beams on sides) - scaled size and position
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

        # Cross beams - scaled
        cross_beam_y_positions = [deck_top, deck_top + 1, deck_bottom - 1, deck_bottom - 2]
        for cross_y in cross_beam_y_positions:
            for x in range(deck_left, deck_right):
                if x < tile_sz and 0 <= cross_y < tile_sz:
                    pixels[x, cross_y] = beam_color

        # Rail posts - scaled frequency and position
        rail_post_spacing = max(5, tile_sz // 6)
        rail_post_top = max(1, tile_sz // 12)
        rail_post_bottom = min(tile_sz - 1, int(0.56 * tile_sz))

        for x in range(deck_left + rail_post_spacing, deck_right - rail_post_spacing // 2, rail_post_spacing):
            if rail_post_top < tile_sz:
                pixels[x, rail_post_top] = beam_color
            if rail_post_top + 1 < tile_sz:
                pixels[x, rail_post_top + 1] = beam_color
            if rail_post_bottom < tile_sz:
                pixels[x, rail_post_bottom] = beam_color
            if rail_post_bottom - 1 < tile_sz:
                pixels[x, rail_post_bottom - 1] = beam_color
        del pixels

    @staticmethod
    def _texture_crater(
        surface: pygame.Surface, tid: int, var: int, pal: 'PaletteGenerator', bitmask: int = 0
    ) -> None:
        """CRATER (12): CC2 authentic shell crater with elliptical depression and bright rim."""
        rng = random.Random(var * 331)
        tile_sz = ProceduralTextureGenerator.TILE_SIZE
        # Dark earth base
        base = (90, 75, 60)
        ProceduralTextureGenerator._fill_with_variation(surface, base, rng, 10)  # More variation

        try:
            pixels = pygame.surfarray.pixels3d(surface)
            cx, cy = tile_sz // 2, tile_sz // 2

            # CC2 crater is elliptical (not circular) - wider than tall
            # CC2 spec: Shape: ELLIPTICAL (wider than tall, ratio ~1.4:1)
            radius_x = tile_sz // 2 - 3   # Horizontal radius (wider)
            radius_y = int(radius_x / 1.4)  # Vertical radius (shorter for 1.4:1 ratio)

            # Ensure minimum size
            radius_y = max(6, radius_y)

            # Draw crater: dark center, lighter rim (elliptical shape with smooth gradients)
            for y in range(tile_sz):
                for x in range(tile_sz):
                    # Normalized distance from center (elliptical)
                    if radius_x > 0 and radius_y > 0:
                        norm_dist = ((x - cx) / radius_x) ** 2 + ((y - cy) / radius_y) ** 2

                        if norm_dist < 0.15:
                            # Deep center - darkest depression
                            # CC2 spec: Dark depression #5A4628 (90, 74, 40)
                            shade = max(0, int(CC2_TERRAIN_PALETTE['crater_center'][0] + rng.randint(-8, 8)))
                            pixels[x, y] = (
                                shade,
                                max(0, shade - 14),
                                max(0, shade - 24)
                            )
                        elif norm_dist < 0.45:
                            # Inner slope - gradient from dark to mid
                            t = (norm_dist - 0.15) / 0.30
                            base_r = CC2_TERRAIN_PALETTE['crater_center'][0]
                            rim_r = CC2_TERRAIN_PALETTE['crater_rim'][0]
                            shade = int(base_r + t * (rim_r - base_r) + rng.randint(-6, 6))
                            pixels[x, y] = (
                                min(255, shade),
                                min(255, max(0, shade - 6)),
                                min(255, max(0, shade - 16))
                            )
                        elif norm_dist < 0.85:
                            # Raised rim area approaching bright edge
                            t = (norm_dist - 0.45) / 0.40
                            base_r = CC2_TERRAIN_PALETTE['crater_rim'][0]
                            # CC2 spec: Bright edge highlight #9E8248 (158, 130, 72)
                            bright_rim_color = (158, 130, 72)
                            shade = int(CC2_TERRAIN_PALETTE['crater_rim'][0] + t * (bright_rim_color[0] - CC2_TERRAIN_PALETTE['crater_rim'][0]))
                            pixels[x, y] = (
                                min(255, shade + rng.randint(-6, 6)),
                                min(255, max(0, shade - 4 + rng.randint(-5, 5))),
                                min(255, max(0, shade - 12 + rng.randint(-5, 5)))
                            )
                        elif norm_dist < 1.0:
                            # Outer bright rim - the most visible feature!
                            # CC2 spec: Rim: Bright edge highlight #9E8248, 3-5px wide
                            rim_color = (158, 130, 72)  # #9E8248
                            brightness_factor = 1.0 - (norm_dist - 0.85) / 0.15  # Fade at outer edge
                            pixels[x, y] = (
                                min(255, int(rim_color[0] * brightness_factor + rng.randint(-10, 10))),
                                min(255, int(rim_color[1] * brightness_factor + rng.randint(-8, 8))),
                                min(255, int(rim_color[2] * brightness_factor + rng.randint(-12, 12)))
                            )

            # Add scattered small rocks around rim for realism
            # CC2 spec: Debris: Small rock/dirt particles around rim (random gray/brown dots)
            num_debris = tile_sz // 2  # More debris for larger tile
            for _ in range(num_debris):
                angle = rng.uniform(0, 2 * math.pi)
                # Distribute debris mainly around the rim area (0.75 to 1.25 normalized distance)
                dist = radius_x * rng.uniform(0.80, 1.20)
                rx = int(cx + math.cos(angle) * dist)
                ry = int(cy + math.sin(angle) * dist * (radius_y / max(radius_x, 1)))

                if 0 <= rx < tile_sz and 0 <= ry < tile_sz:
                    # Random rock/dirt colors (gray-brown palette)
                    rock_color = (
                        rng.randint(100, 150),
                        rng.randint(85, 130),
                        rng.randint(65, 110)
                    )
                    pixels[rx, ry] = rock_color

                    # Rock cluster (2-3 pixels for natural look)
                    if rng.random() > 0.55:
                        cluster_size = rng.randint(2, 3)
                        for _ in range(cluster_size):
                            dx, dy = rng.choice([(1, 0), (0, 1), (-1, 0), (0, -1), (1, 1)])
                            if 0 <= rx + dx < tile_sz and 0 <= ry + dy < tile_sz:
                                pixels[rx + dx, ry + dy] = tuple(
                                    max(0, c - rng.randint(10, 20)) for c in rock_color
                                )

            del pixels
        except Exception:
            pass

    @staticmethod
    def _texture_trench(
        surface: pygame.Surface, tid: int, var: int, pal: 'PaletteGenerator', bitmask: int = 0
    ) -> None:
        """TRENCH (13): Defensive earthwork line.

        CC2 appearance from screenshots:
        - Dark brown/black narrow line (3-5px wide)
        - Irregular/wavy path across tile (not perfectly straight)
        - Slight embankment on both sides (1-2px lighter color ridge)
        - Dirt piles at ends if not connected to adjacent trench
        - Autotile support: connected edges = continuous trench,
          disconnected = tapered end

        Color: #3A2818 (dark earth brown) main trench, #5A4830 embankment
        """
        from pycc2.presentation.rendering.autotile_system import (
            DIR_NORTH, DIR_EAST, DIR_SOUTH, DIR_WEST,
            get_edge_transition_width,
        )

        rng = random.Random(var * 397)
        tile_sz = ProceduralTextureGenerator.TILE_SIZE

        # Background: lighter ground visible around trench
        ground_color = (100, 85, 65)
        surface.fill(ground_color)
        pixels = pygame.surfarray.pixels3d(surface)

        # Trench colors
        trench_main = CC2_TERRAIN_PALETTE['trench_main']      # #3A2818 dark brown
        trench_embankment = CC2_TERRAIN_PALETTE['trench_embankment']  # #5A4830 lighter

        # Calculate edge connectivity for autotile tapering
        edge_widths = get_edge_transition_width(tid, bitmask, tile_sz)

        # CC2 spec: Create IRREGULAR wavy trench line across tile
        # Use random walk algorithm for natural appearance with autotile coordination

        center_x = tile_sz // 2
        base_y = tile_sz // 2
        trench_width = rng.randint(3, 5)  # 3-5px wide as per spec

        # Generate wavy trench center line using random walk
        trench_center_points = []
        x = 0
        y = base_y

        # Autotile coordination: use bitmask to influence start/end positions
        if bitmask & DIR_WEST:
            # Connected from west: start at right side to continue neighbor's line
            y = int(tile_sz * 0.4) + rng.randint(-2, 2)
        elif bitmask & DIR_EAST:
            # Connected to east: prepare for eastward continuation
            pass

        while x < tile_sz:
            trench_center_points.append((x, y))
            x += 1

            # Autotile coordination: use shared seed based on connectivity
            coord_seed = var * 397 + bitmask * 23 + x * 7
            coord_rng = random.Random(coord_seed)

            # Random walk step (small vertical variation for waviness)
            y += coord_rng.randint(-1, 1)

            # Keep within reasonable bounds (don't go too close to edges)
            y = max(tile_sz // 6, min(5 * tile_sz // 6, y))

        # Draw trench: main dark line + embankment on both sides
        for point in trench_center_points:
            px, py = point[0], int(point[1])

            # Main trench channel (dark brown, trench_width pixels wide)
            for offset in range(-trench_width // 2, trench_width // 2 + 1):
                draw_x = px + offset
                if 0 <= draw_x < tile_sz and 0 <= py < tile_sz:
                    # Center is darkest, slight variation for texture
                    dist_from_center = abs(offset)
                    if dist_from_center == 0:
                        pixels[draw_x, py] = trench_main
                    else:
                        # Slightly lighter toward edges
                        shade_var = rng.randint(-5, 5)
                        pixels[draw_x, py] = (
                            min(255, trench_main[0] + dist_from_center * 8 + shade_var),
                            min(255, trench_main[1] + dist_from_center * 6 + shade_var),
                            min(255, trench_main[2] + dist_from_center * 4 + shade_var),
                        )

            # Embankment ridges (1-2px lighter color on both sides of trench)
            for emb_offset in [-(trench_width // 2 + 1), (trench_width // 2 + 1)]:
                emb_x = px + emb_offset
                if 0 <= emb_x < tile_sz and 0 <= py < tile_sz:
                    pixels[emb_x, py] = trench_embankment
                    # Occasional second row for thicker embankment
                    if rng.random() > 0.6:
                        emb_x2 = px + emb_offset + (1 if emb_offset > 0 else -1)
                        if 0 <= emb_x2 < tile_sz and 0 < py < tile_sz:
                            pixels[emb_x2, py] = (
                                trench_embankment[0] - 10,
                                trench_embankment[1] - 8,
                                trench_embankment[2] - 6,
                            )

        # Apply AUTOTILE TAPERING on non-connected edges
        # West edge tapering (if not connected west)
        if edge_widths['west'] > 0 and not (bitmask & DIR_WEST):
            taper_width = min(edge_widths['west'], 10)
            for x in range(taper_width):
                taper_factor = x / taper_width  # 0 at left edge, 1 inward
                for y in range(tile_sz):
                    if rng.random() > taper_factor * 0.7:
                        r, g, b = int(pixels[x, y][0]), int(pixels[x, y][1]), int(pixels[x, y][2])
                        # Blend toward ground color at tapered end
                        pixels[x, y] = (
                            int(r + (ground_color[0] - r) * (1 - taper_factor)),
                            int(g + (ground_color[1] - g) * (1 - taper_factor)),
                            int(b + (ground_color[2] - b) * (1 - taper_factor)),
                        )
            # Add dirt pile at west end (if not connected)
            dirt_pile_cx = 3
            dirt_pile_cy = base_y
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    dp_x = dirt_pile_cx + dx
                    dp_y = dirt_pile_cy + dy
                    if 0 <= dp_x < tile_sz and 0 <= dp_y < tile_sz:
                        if dx*dx + dy*dy <= 4:
                            pixels[dp_x, dp_y] = (110, 90, 60)

        # East edge tapering (if not connected east)
        if edge_widths['east'] > 0 and not (bitmask & DIR_EAST):
            taper_width = min(edge_widths['east'], 10)
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
            # Add dirt pile at east end (if not connected)
            dirt_pile_cx = tile_sz - 4
            dirt_pile_cy = base_y
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    dp_x = dirt_pile_cx + dx
                    dp_y = dirt_pile_cy + dy
                    if 0 <= dp_x < tile_sz and 0 <= dp_y < tile_sz:
                        if dx*dx + dy*dy <= 4:
                            pixels[dp_x, dp_y] = (110, 90, 60)

        # North/South connections (vertical trench segments)
        # These would be handled by rotating the pattern or using adjacent tiles

        # Add small rocks/debris scattered in trench (realism detail)
        num_debris = rng.randint(3, 7)
        for _ in range(num_debris):
            debris_x = rng.randint(tile_sz // 4, 3 * tile_sz // 4)
            # Find approximate trench position at this x coordinate
            if debris_x < len(trench_center_points):
                approx_ty = int(trench_center_points[debris_x][1])
                debris_y = approx_ty + rng.randint(-trench_width // 2, trench_width // 2)
                if 0 <= debris_x < tile_sz and 0 <= debris_y < tile_sz:
                    pixels[debris_x, debris_y] = (45, 35, 25)  # Dark rock

        del pixels

    @staticmethod
    def _texture_default(
        surface: pygame.Surface, tid: int, var: int, pal: 'PaletteGenerator', bitmask: int = 0
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


class TerrainTileCache:
    """Pre-computed terrain tile cache for smooth rendering.

    Pre-renders all unique terrain tiles (with autotile edge smoothing)
    at startup and caches them for fast per-frame blitting.

    Cache key: (terrain_type, autotile_mask, variation, height, tile_screen_size)
    Cache invalidation: only when map changes (rare).
    LRU eviction when cache exceeds MAX_ENTRIES.
    """

    MAX_ENTRIES = 10000

    def __init__(self, tile_size: int = 48):
        self._tile_size = tile_size
        self._cache: dict[tuple, pygame.Surface] = {}
        self._access_order: list[tuple] = []  # For LRU tracking

    def get_tile(
        self,
        terrain_type: int,
        autotile_mask: int = 0,
        variation: int = 0,
        height: int = 0,
        tile_screen_size: int = 48,
        renderer: EnhancedRenderer | None = None,
        enhanced_tile: Any | None = None,
        tile_x: int = 0,
        tile_y: int = 0,
    ) -> pygame.Surface | None:
        """Get a cached terrain tile, creating it if needed.

        Returns None if renderer is not provided and tile is not cached.
        """
        key = (terrain_type, autotile_mask, variation, height, tile_screen_size)

        if key in self._cache:
            # LRU: move to end (most recently used)
            self._access_order.remove(key)
            self._access_order.append(key)
            return self._cache[key]

        if renderer is None:
            return None

        surface = self._render_tile(
            renderer, terrain_type, autotile_mask, variation,
            height, tile_screen_size, enhanced_tile, tile_x, tile_y,
        )
        if surface is not None:
            self._put(key, surface)
        return surface

    def _put(self, key: tuple, surface: pygame.Surface) -> None:
        """Insert into cache with LRU eviction."""
        if len(self._cache) >= self.MAX_ENTRIES and key not in self._cache:
            # Evict oldest entry
            oldest = self._access_order.pop(0)
            self._cache.pop(oldest, None)
        self._cache[key] = surface
        self._access_order.append(key)

    def _render_tile(
        self,
        renderer: EnhancedRenderer,
        terrain_type: int,
        autotile_mask: int,
        variation: int,
        height: int,
        tile_screen_size: int,
        enhanced_tile: Any | None,
        tile_x: int,
        tile_y: int,
    ) -> pygame.Surface | None:
        """Render a single terrain tile with edge smoothing via the renderer."""
        try:
            # Get base texture using the renderer's existing logic
            if autotile_mask != 0:
                texture = renderer._generate_cc2_style_tile(
                    terrain_type, tile_x, tile_y, autotile_mask
                )
            else:
                texture = renderer._get_cached_texture(terrain_type, variation)

            if texture is None:
                return None

            # Apply height lighting if needed
            if height != 0:
                texture = renderer._apply_height_lighting(texture, height)

            # Scale to screen size if needed
            if tile_screen_size != self._tile_size:
                texture = pygame.transform.scale(
                    texture, (tile_screen_size, tile_screen_size)
                )

            # Apply autotile edge smoothing directly onto the tile surface
            if autotile_mask > 0:
                self._apply_edge_smoothing(texture, terrain_type, autotile_mask)

            return texture
        except Exception:
            return None

    def _apply_edge_smoothing(
        self, surface: pygame.Surface, terrain_type: int, mask: int
    ) -> None:
        """Apply smooth edge transitions based on autotile bitmask.

        Bitmask convention: N=1, E=2, S=4, W=8
        For each edge that is NOT connected (bit not set), add a subtle
        fade-to-background blend to soften the tile boundary.
        """
        tile_size = surface.get_width()
        blend_width = max(2, min(4, tile_size // 12))

        # Get a darker version of the terrain color for edge blending
        palette_key = TERRAIN_PALETTE_MAP.get(terrain_type, 'grass_base')
        base_color = CC2_TERRAIN_PALETTE.get(palette_key, (76, 124, 35))
        edge_color = (
            max(0, base_color[0] - 30),
            max(0, base_color[1] - 30),
            max(0, base_color[2] - 30),
        )

        # N (bit 0): if NOT connected, blend top edge
        if not (mask & 1):
            for i in range(blend_width):
                alpha = int(35 * (1 - i / blend_width))
                line_surf = pygame.Surface((tile_size, 1), pygame.SRCALPHA)
                line_surf.fill((*edge_color, alpha))
                surface.blit(line_surf, (0, i))

        # E (bit 1): if NOT connected, blend right edge
        if not (mask & 2):
            for i in range(blend_width):
                alpha = int(35 * (1 - i / blend_width))
                line_surf = pygame.Surface((1, tile_size), pygame.SRCALPHA)
                line_surf.fill((*edge_color, alpha))
                surface.blit(line_surf, (tile_size - 1 - i, 0))

        # S (bit 2): if NOT connected, blend bottom edge
        if not (mask & 4):
            for i in range(blend_width):
                alpha = int(35 * (1 - i / blend_width))
                line_surf = pygame.Surface((tile_size, 1), pygame.SRCALPHA)
                line_surf.fill((*edge_color, alpha))
                surface.blit(line_surf, (0, tile_size - 1 - i))

        # W (bit 3): if NOT connected, blend left edge
        if not (mask & 8):
            for i in range(blend_width):
                alpha = int(35 * (1 - i / blend_width))
                line_surf = pygame.Surface((1, tile_size), pygame.SRCALPHA)
                line_surf.fill((*edge_color, alpha))
                surface.blit(line_surf, (i, 0))

    def invalidate(self) -> None:
        """Invalidate entire cache (call when map changes)."""
        self._cache.clear()
        self._access_order.clear()

    def clear(self) -> None:
        """Clear all cached tiles."""
        self._cache.clear()
        self._access_order.clear()

    @property
    def size(self) -> int:
        """Current number of cached tiles."""
        return len(self._cache)


class EnhancedRenderer:
    """
    CC2-Authentic terrain renderer for PyCC2 maps.

    Renders tiles with authentic Close Combat 2 visual style:
    - 48×48 pixel tiles (orthographic top-down)
    - CC2 terrain palette from screenshot analysis
    - Procedural texture generation with variation
    - Supports dual projection modes:
      * ORTHOGRAPHIC: Classic top-down rendering (default, CC2-style)
      * ISOMETRIC: 2:1 isometric diamond rendering
    """

    TILE_SIZE = 48  # CC2 authentic: 48×48 pixel tiles

    def __init__(self):
        self._screen: pygame.Surface | None = None
        self._offscreen: pygame.Surface | None = None  # Off-screen buffer to eliminate flicker
        self._palette_gen = PaletteGenerator()
        self._texture_cache: dict[tuple[int, int], pygame.Surface] = {}
        self._scaled_texture_cache: dict[tuple[int, int, int], pygame.Surface] = {}
        self._height_lit_cache: dict[tuple[int, int, int, int], pygame.Surface] = {}
        self._sprite_cache: dict[str, pygame.Surface] = {}
        self._autotile_cache = AutotileCache()  # Cache for autotile variants
        self._terrain_tile_cache = TerrainTileCache(self.TILE_SIZE)  # Pre-computed terrain tile cache with edge smoothing
        self._building_clusters: list[list[tuple[int, int]]] | None = None  # Cached building clusters
        self._edge_smooth_cache: dict[tuple[int, int], pygame.Surface] = {}  # Cached edge smoothing surfaces
        self._edge_smooth_dirty: bool = True  # Flag to indicate cache needs rebuild
        self._last_map_hash: int = 0  # Track map changes for cache invalidation
        self._frame_count = 0
        self._sprite_renderer = None  # 延迟初始化，等待display ready
        self._isometric_renderer = None  # Isometric renderer (lazy init)
    
    def initialize(self, screen: pygame.Surface) -> None:
        """Initialize renderer with display surface."""
        self._screen = screen
        try:
            self._offscreen = pygame.Surface(screen.get_size()).convert()
        except pygame.error as e:
            # Fallback for headless/testing environments without video mode set
            import warnings
            warnings.warn(f"Could not convert surface (no video mode?): {e}. Using SRCALPHA fallback.")
            self._offscreen = pygame.Surface(screen.get_size(), pygame.SRCALPHA)

        # 现在display已初始化，可以创建SpriteRenderer加载PNG
        try:
            from pycc2.presentation.rendering.sprite_renderer import SpriteRenderer
            self._sprite_renderer = SpriteRenderer()
            self._sprite_renderer.initialize(screen)
            print("[EnhancedRenderer] ✅ SpriteRenderer initialized with PNG support")
        except Exception as e:
            import warnings
            warnings.warn(f"SpriteRenderer initialization failed: {e}")
            self._sprite_renderer = None
    
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

        # Isometric rendering branch
        from pycc2.presentation.rendering.camera import ProjectionMode
        if camera.projection == ProjectionMode.ISOMETRIC:
            self._render_isometric(game_map, units, camera, selected_unit_ids, debug_mode)
            return

        # Orthographic rendering (original pipeline)
        self._frame_count += 1

        # Ensure off-screen buffer matches display surface size (handles resize)
        screen_w, screen_h = self._screen.get_size()
        if self._offscreen is None or self._offscreen.get_size() != (screen_w, screen_h):
            self._offscreen = pygame.Surface((screen_w, screen_h)).convert()

        # STEP 1: Clear off-screen buffer
        self._offscreen.fill((34, 40, 48))  # Dark blue-gray background

        # STEP 2: Draw terrain — use enhanced texturing with simple fallback
        try:
            self._draw_enhanced_terrain(game_map, camera, debug_mode)
        except Exception as e:
            import logging
            logging.getLogger("pycc2").warning(f"Enhanced terrain failed, falling back to simple: {e}")
            self._draw_simple_terrain(game_map, camera)

        # STEP 3: Draw grid ONLY in debug mode
        if debug_mode:
            self._draw_grid(game_map, camera)

        # STEP 4: Draw decorations (minimal)
        self._draw_decorations(game_map, camera)

        # STEP 4.4: Draw building roofs (CC2 top-down view — covers side-view terrain texture)
        self._draw_building_roofs(game_map, camera)

        # STEP 4.5: Draw building interiors (auto-switch when units are inside)
        self._draw_building_interiors(game_map, units, camera)

        # STEP 4.6: Draw building floor numbers on roof
        self._draw_building_floor_numbers(game_map, camera)

        # STEP 4.7: Draw Victory Location flags and edge arrows
        self._draw_vl_flags(game_map, camera)

        # STEP 5: Draw units
        self._draw_units(units, camera, selected_unit_ids)

        # STEP 5.5: Draw attack lines (CC2-style)
        self._draw_attack_lines(camera)

        # STEP 5.6: Draw queued command lines (Shift+right-click)
        self._draw_queued_commands(units, camera)

        # STEP 6: Atomic blit off-screen buffer → display surface
        self._screen.blit(self._offscreen, (0, 0))

        # DISABLED: All post-processing to prevent flickering and crashes
        # self._apply_post_processing()  # REMOVED - causes flickering

    def _render_isometric(
        self,
        game_map: GameMap,
        units: list[Unit],
        camera: Camera,
        selected_unit_ids: set[str] | None = None,
        debug_mode: bool = False,
    ) -> None:
        """Delegate rendering to IsometricRenderer when in ISOMETRIC mode."""
        if self._isometric_renderer is None:
            from pycc2.presentation.rendering.isometric_renderer import IsometricRenderer
            self._isometric_renderer = IsometricRenderer()
            if self._screen is not None:
                self._isometric_renderer.initialize(self._screen)

        self._isometric_renderer.render(
            game_map=game_map,
            units=units,
            camera=camera,
            selected_unit_ids=selected_unit_ids,
            debug_mode=debug_mode,
        )

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
                    # Get terrain type safely — use _get_enhanced_tile for compatibility
                    etile = self._get_enhanced_tile(game_map, tx, ty)
                    if etile is not None:
                        terrain_val = etile.base_terrain
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
        """Draw terrain tiles with texturing and height-based lighting, with autotile support."""
        if self._screen is None:
            return

        # Update building clusters cache if needed
        if self._building_clusters is None:
            self._building_clusters = detect_building_clusters(game_map)

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

                # Calculate autotile bitmask for continuous terrains
                bitmask = 0
                if is_autotile_terrain(terrain_val):
                    bitmask = get_neighbor_bitmap(game_map, tx, ty, terrain_val)

                # Use TerrainTileCache for pre-computed tiles with edge smoothing
                texture = self._terrain_tile_cache.get_tile(
                    terrain_type=terrain_val,
                    autotile_mask=bitmask,
                    variation=variation,
                    height=height,
                    tile_screen_size=tile_screen_size,
                    renderer=self,
                    enhanced_tile=enhanced_tile,
                    tile_x=tx,
                    tile_y=ty,
                )

                # Fallback to original rendering if cache miss without renderer
                if texture is None:
                    if bitmask != 0:
                        cache_key = (terrain_val, variation, bitmask)
                        if cache_key not in self._autotile_cache._cache:
                            texture = self._generate_cc2_style_tile(terrain_val, tx, ty, bitmask)
                            self._autotile_cache.set_variant(terrain_val, bitmask, variation, texture)
                        else:
                            texture = self._autotile_cache.get_variant(terrain_val, bitmask, variation)

                        if tile_screen_size != self.TILE_SIZE:
                            scale_key = (terrain_val, variation, bitmask, tile_screen_size)
                            if scale_key not in self._scaled_texture_cache:
                                base_texture = self._autotile_cache.get_variant(terrain_val, bitmask, variation)
                                if base_texture:
                                    self._scaled_texture_cache[scale_key] = pygame.transform.scale(
                                        base_texture, (tile_screen_size, tile_screen_size)
                                    )
                            texture = self._scaled_texture_cache.get(scale_key, texture)
                    elif height != 0:
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

        # RE-ENABLED: Terrain edge smoothing with caching for performance
        # Only rebuilds cache when map changes, not every frame
        if not debug_mode and tile_screen_size >= 16:
            self._apply_terrain_edge_smoothing(game_map, camera, start_x, end_x, start_y, end_y, tile_screen_size)

        # Draw terrain borders ONLY in debug mode (Issue 4: remove harsh grid lines in normal mode)
        if debug_mode:
            self._draw_terrain_borders(game_map, camera, start_x, end_x, start_y, end_y)

    def _draw_building_roofs(
        self, game_map: GameMap, camera: Camera,
    ) -> None:
        """Draw CC2-style top-down building roofs over all building tiles.

        This covers the side-view terrain texture with the correct CC2
        orthographic roof view (colored rectangle + pseudo-3D shadow strips).
        When units are inside, _draw_building_interiors will override with
        the interior view in the next step.
        """
        if self._offscreen is None:
            return

        from pycc2.presentation.rendering.cc2_building_renderer import (
            render_cc2_building,
            floors_to_building_type,
            DamageLevel,
        )

        bounds = camera.view_bounds
        start_x = max(0, int(bounds[0].x // self.TILE_SIZE))
        end_x = min(game_map.width, int((bounds[1].x // self.TILE_SIZE) + 2))
        start_y = max(0, int(bounds[0].y // self.TILE_SIZE))
        end_y = min(game_map.height, int((bounds[1].y // self.TILE_SIZE) + 2))

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                terrain_val = self._get_terrain_at(game_map, tx, ty)
                if terrain_val != 4:  # Only BUILDING_ENTERABLE
                    continue

                # Determine building type from floor count
                enhanced = game_map.get_enhanced_tile(tx, ty) if hasattr(game_map, 'get_enhanced_tile') else None
                floors = 1
                if enhanced and isinstance(enhanced, dict):
                    floors = int(enhanced.get("building_floors", 1))
                elif enhanced and hasattr(enhanced, 'building_floors'):
                    floors = int(getattr(enhanced, 'building_floors', 1))

                building_type = floors_to_building_type(floors)

                # Render roof (default mode = roof, not interior)
                roof_surface = render_cc2_building(
                    building_type=building_type,
                    damage=DamageLevel.INTACT,
                    tile_size=self.TILE_SIZE,
                    interior_mode=False,
                )

                # Scale if zoomed
                tile_screen_size = int(self.TILE_SIZE * camera.zoom)
                if tile_screen_size != self.TILE_SIZE:
                    tw, th = roof_surface.get_size()
                    target_w = int(tw * camera.zoom)
                    target_h = int(th * camera.zoom)
                    if target_w > 0 and target_h > 0:
                        roof_surface = pygame.transform.scale(
                            roof_surface, (target_w, target_h),
                        )

                # Blit roof at screen position
                from pycc2.domain.value_objects.vec2 import Vec2
                world_x = tx * self.TILE_SIZE
                world_y = ty * self.TILE_SIZE
                screen_pos = camera.world_to_screen(Vec2(world_x, world_y))

                self._offscreen.blit(roof_surface, (int(screen_pos[0]), int(screen_pos[1])))

    def _draw_building_interiors(
        self, game_map: GameMap, units: list[Unit], camera: Camera,
    ) -> None:
        """Overlay building interior view when units are inside a building.

        CC2 mechanism: when a unit enters a building tile, the building
        renderer automatically switches to interior mode (showing floor +
        windows instead of roof). When all units leave, it reverts to roof.
        """
        if self._screen is None or self._offscreen is None:
            return
        if not units:
            return

        from pycc2.presentation.rendering.cc2_building_renderer import (
            should_show_interior,
            render_cc2_building,
            floors_to_building_type,
            DamageLevel,
        )

        bounds = camera.view_bounds
        start_x = max(0, int(bounds[0].x // self.TILE_SIZE))
        end_x = min(game_map.width, int((bounds[1].x // self.TILE_SIZE) + 2))
        start_y = max(0, int(bounds[0].y // self.TILE_SIZE))
        end_y = min(game_map.height, int((bounds[1].y // self.TILE_SIZE) + 2))

        tile_screen_size = int(self.TILE_SIZE * camera.zoom)

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                # Only process building_enterable tiles (terrain ID 4)
                terrain_val = self._get_terrain_at(game_map, tx, ty)
                if terrain_val != 4:
                    continue

                # Check if any unit is inside this building tile
                if not should_show_interior((tx, ty), units, self.TILE_SIZE):
                    continue

                # Determine building type from floor count in enhanced tile data
                enhanced = game_map.get_enhanced_tile(tx, ty) if hasattr(game_map, 'get_enhanced_tile') else None
                floors = 1
                if enhanced and isinstance(enhanced, dict):
                    floors = int(enhanced.get("building_floors", 1))
                elif enhanced and hasattr(enhanced, 'building_floors'):
                    floors = int(getattr(enhanced, 'building_floors', 1))

                building_type = floors_to_building_type(floors)

                # Render interior view
                interior_surface = render_cc2_building(
                    building_type=building_type,
                    damage=DamageLevel.INTACT,
                    tile_size=self.TILE_SIZE,
                    interior_mode=True,
                    occupant_positions=[],
                )

                # Scale to screen size if needed
                if tile_screen_size != self.TILE_SIZE:
                    tw, th = interior_surface.get_size()
                    target_w = int(tw * camera.zoom)
                    target_h = int(th * camera.zoom)
                    if target_w > 0 and target_h > 0:
                        interior_surface = pygame.transform.scale(
                            interior_surface, (target_w, target_h),
                        )

                # Blit interior surface at screen position
                from pycc2.domain.value_objects.vec2 import Vec2
                world_x = tx * self.TILE_SIZE
                world_y = ty * self.TILE_SIZE
                screen_pos = camera.world_to_screen(Vec2(world_x, world_y))

                self._offscreen.blit(interior_surface, (int(screen_pos[0]), int(screen_pos[1])))

    def _draw_building_floor_numbers(
        self, game_map: GameMap, camera: Camera,
    ) -> None:
        """Draw floor count numbers on building roof tiles.

        The number displayed matches the `building_floors` data from the
        map tile, which also drives the LOS visibility bonus.
        """
        if self._screen is None or self._offscreen is None:
            return

        bounds = camera.view_bounds
        start_x = max(0, int(bounds[0].x // self.TILE_SIZE))
        end_x = min(game_map.width, int((bounds[1].x // self.TILE_SIZE) + 2))
        start_y = max(0, int(bounds[0].y // self.TILE_SIZE))
        end_y = min(game_map.height, int((bounds[1].y // self.TILE_SIZE) + 2))

        tile_screen_size = int(self.TILE_SIZE * camera.zoom)

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                terrain_val = self._get_terrain_at(game_map, tx, ty)
                if terrain_val != 4:  # Only building_enterable
                    continue

                # Read building_floors from enhanced tile data
                enhanced = game_map.get_enhanced_tile(tx, ty) if hasattr(game_map, 'get_enhanced_tile') else None
                floors = None
                if enhanced and isinstance(enhanced, dict):
                    floors = enhanced.get("building_floors")
                elif enhanced and hasattr(enhanced, 'building_floors'):
                    floors = getattr(enhanced, 'building_floors', None)

                if floors is None or int(floors) <= 1:
                    continue  # Don't show number for single-floor buildings

                # Draw floor number on the roof
                from pycc2.domain.value_objects.vec2 import Vec2
                world_x = tx * self.TILE_SIZE
                world_y = ty * self.TILE_SIZE
                screen_pos = camera.world_to_screen(Vec2(world_x, world_y))

                font_size = max(10, tile_screen_size // 3)
                font = pygame.font.SysFont("arial", font_size, bold=True)
                text = font.render(str(int(floors)), True, (255, 215, 0))  # Gold number
                text_rect = text.get_rect(
                    center=(int(screen_pos[0]) + tile_screen_size // 2,
                            int(screen_pos[1]) + tile_screen_size // 2),
                )
                self._offscreen.blit(text, text_rect)

    def _draw_vl_flags(self, game_map: GameMap, camera: Camera) -> None:
        """Draw Victory Location flags and edge arrows on the map.

        Delegates to SpriteRenderer if available, otherwise draws directly.
        """
        if self._offscreen is None:
            return

        # Delegate to SpriteRenderer which has the VL flag drawing methods
        if self._sprite_renderer is not None:
            # Point SpriteRenderer at our offscreen buffer temporarily
            original_target = self._sprite_renderer._target_surface
            self._sprite_renderer._target_surface = self._offscreen
            try:
                self._sprite_renderer._draw_vl_flags(game_map, camera)
            finally:
                self._sprite_renderer._target_surface = original_target
            return

        # Fallback: simple direct drawing if no SpriteRenderer
        import math
        import time as _time
        from pycc2.domain.value_objects.vec2 import Vec2

        objectives = getattr(game_map, 'objectives', [])
        if not objectives:
            return

        screen_w = self._offscreen.get_width()
        screen_h = self._offscreen.get_height()
        off_screen_vls: list[tuple[int, int, str]] = []

        for obj in objectives:
            tile_x = obj.position.x * self.TILE_SIZE + self.TILE_SIZE // 2
            tile_y = obj.position.y * self.TILE_SIZE + self.TILE_SIZE // 2
            sp = camera.world_to_screen(Vec2(tile_x, tile_y))
            sx, sy = int(sp[0]), int(sp[1])

            owner = getattr(obj, 'owner', None) or 'neutral'
            margin = 60
            on_screen = (-margin < sx < screen_w + margin and -margin < sy < screen_h + margin)

            if on_screen:
                # Simple flag drawing
                pygame.draw.line(self._offscreen, (80, 80, 80), (sx, sy), (sx, sy - 20), 2)
                if owner == 'allies':
                    flag_color = (60, 100, 200)
                elif owner == 'axis':
                    flag_color = (200, 60, 60)
                else:
                    flag_color = (200, 200, 200)
                flag_points = [
                    (sx + 1, sy - 20), (sx + 14, sy - 17),
                    (sx + 13, sy - 10), (sx + 1, sy - 13),
                ]
                pygame.draw.polygon(self._offscreen, flag_color, flag_points)
                pygame.draw.polygon(self._offscreen, (0, 0, 0), flag_points, 1)
            else:
                off_screen_vls.append((tile_x, tile_y, owner))

        # Edge arrows for off-screen VLs
        arrow_margin = 30
        for wx, wy, owner in off_screen_vls:
            sp = camera.world_to_screen(Vec2(wx, wy))
            sx, sy = sp[0], sp[1]
            cx = max(arrow_margin, min(screen_w - arrow_margin, sx))
            cy = max(arrow_margin, min(screen_h - arrow_margin, sy))
            color = (60, 100, 200) if owner == 'allies' else (200, 60, 60) if owner == 'axis' else (200, 200, 200)
            angle = math.atan2(sy - cy, sx - cx)
            arrow_size = 10
            tip_x = cx + arrow_size * math.cos(angle)
            tip_y = cy + arrow_size * math.sin(angle)
            left_x = cx + arrow_size * math.cos(angle + 2.5)
            left_y = cy + arrow_size * math.sin(angle + 2.5)
            right_x = cx + arrow_size * math.cos(angle - 2.5)
            right_y = cy + arrow_size * math.sin(angle - 2.5)
            pygame.draw.polygon(self._offscreen, color, [
                (int(tip_x), int(tip_y)),
                (int(left_x), int(left_y)),
                (int(right_x), int(right_y)),
            ])

    def _get_enhanced_tile(self, game_map: GameMap, x: int, y: int):
        """Try to get enhanced tile data from map."""
        try:
            # 优先使用GameMap的API方法
            if hasattr(game_map, 'get_enhanced_tile'):
                tile_data = game_map.get_enhanced_tile(x, y)
                if tile_data is not None:
                    # 延迟导入避免TYPE_CHECKING限制
                    from pycc2.domain.systems.enhanced_tile import EnhancedTile
                    if isinstance(tile_data, EnhancedTile):
                        return tile_data
                    elif isinstance(tile_data, dict):
                        return EnhancedTile.from_dict(tile_data)
            # 兼容旧属性名 enhanced_tiles（二维列表）
            if hasattr(game_map, 'enhanced_tiles') and game_map.enhanced_tiles:
                if 0 <= y < len(game_map.enhanced_tiles) and 0 <= x < len(game_map.enhanced_tiles[y]):
                    return game_map.enhanced_tiles[y][x]
        except (AttributeError, IndexError, TypeError, KeyError):
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

    def _generate_cc2_style_tile(
        self, 
        terrain_id: int, 
        tile_x: int = 0, 
        tile_y: int = 0,
        bitmask: int = 0
    ) -> pygame.Surface:
        """
        Generate a CC2-authentic 48×48 terrain tile with autotile support.

        This is the main entry point for CC2-style terrain generation.
        Uses deterministic random seeds based on tile position for consistent
        regeneration (same position always produces same appearance).

        Args:
            terrain_id: Terrain type ID (0-12)
            tile_x: Tile X position (used for deterministic seed)
            tile_y: Tile Y position (used for deterministic seed)
            bitmask: Autotile neighbor bitmap (0-15) for cross-tile continuity

        Returns:
            pygame.Surface: 48×48 pixel surface with CC2-authentic terrain
        """
        # Deterministic seed from position ensures consistent regeneration
        # Adjacent tiles of same type will have different variations
        variation = tile_x * 7919 + tile_y * 104729 + terrain_id * 17

        # Use the existing ProceduralTextureGenerator with new CC2 palette and autotile support
        return ProceduralTextureGenerator.generate_terrain_texture(
            terrain_id,
            variation=variation,
            palette=self._palette_gen,
            bitmask=bitmask
        )

    def _apply_terrain_edge_smoothing(
        self, game_map: GameMap, camera: Camera,
        start_x: int, end_x: int, start_y: int, end_y: int,
        tile_screen_size: int
    ) -> None:
        """Apply subtle edge smoothing between different terrain types for CC2-like natural look.

        Creates 2-3 pixel wide semi-transparent overlays at terrain boundaries
        to soften harsh edges. Uses caching to avoid per-frame recalculation.

        Performance optimizations:
        - Only processes non-autotile terrain boundaries (grass-dirt, grass-road)
        - Caches smoothed edges and only rebuilds when map changes
        - Skips tiles where all neighbors are same terrain type
        """
        if self._screen is None or self._offscreen is None or tile_screen_size < 8:
            return

        from pycc2.domain.value_objects.vec2 import Vec2

        # Check if cache needs rebuild (simple hash-based dirty check)
        try:
            current_map_hash = hash((game_map.width, game_map.height, id(game_map)))
            if current_map_hash != self._last_map_hash or self._edge_smooth_dirty:
                self._edge_smooth_cache.clear()
                self._terrain_tile_cache.invalidate()  # Invalidate tile cache when map changes
                self._last_map_hash = current_map_hash
                self._edge_smooth_dirty = False
        except Exception:
            pass

        # Autotile terrains that handle their own edges (skip these)
        autotile_terrains = {5, 6, 7}
        # Non-autotile terrain transitions that benefit from smoothing
        smoothable_pairs = {
            (0, 1), (1, 0), (0, 2), (2, 0), (1, 2), (2, 1),
            (0, 3), (3, 0), (1, 3), (3, 1),
        }

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                current = self._get_terrain_at(game_map, tx, ty)
                if current < 0 or current in autotile_terrains:
                    continue

                neighbors = [
                    (tx + 1, ty, 'right'), (tx - 1, ty, 'left'),
                    (tx, ty + 1, 'down'), (tx, ty - 1, 'up'),
                ]

                for nx, ny, direction in neighbors:
                    if nx < start_x or nx >= end_x or ny < start_y or ny >= end_y:
                        continue

                    neighbor = self._get_terrain_at(game_map, nx, ny)
                    if neighbor < 0 or neighbor == current or neighbor in autotile_terrains:
                        continue
                    if (current, neighbor) not in smoothable_pairs:
                        continue

                    cache_key = (min(tx, nx), min(ty, ny), max(tx, nx), max(ty, ny))
                    if cache_key in self._edge_smooth_cache:
                        cached_surf, cached_rect = self._edge_smooth_cache[cache_key]
                        self._offscreen.blit(cached_surf, cached_rect, special_flags=pygame.BLEND_RGBA_ADD)
                        continue

                    world_x = tx * self.TILE_SIZE
                    world_y = ty * self.TILE_SIZE
                    screen_pos = camera.world_to_screen(Vec2(world_x, world_y))
                    base_x = int(screen_pos[0])
                    base_y = int(screen_pos[1])

                    try:
                        pal = self._palette_gen
                        color1 = pal.get_color(current, 4)
                        color2 = pal.get_color(neighbor, 4)
                        blend_color = (
                            (color1[0] + color2[0]) // 2,
                            (color1[1] + color2[1]) // 2,
                            (color1[2] + color2[2]) // 2,
                            45,
                        )
                    except Exception:
                        blend_color = (80, 80, 80, 45)

                    edge_width = max(2, min(3, tile_screen_size // 16))

                    if direction in ('right', 'left'):
                        edge_x = base_x + (tile_screen_size if direction == 'left' else 0)
                        edge_rect = pygame.Rect(edge_x, base_y, edge_width, tile_screen_size)
                    else:
                        edge_y = base_y + (tile_screen_size if direction == 'up' else 0)
                        edge_rect = pygame.Rect(base_x, edge_y, tile_screen_size, edge_width)

                    edge_surf = pygame.Surface((edge_rect.width, edge_rect.height), pygame.SRCALPHA)

                    for i in range(edge_rect.width if direction in ('right', 'left') else edge_rect.height):
                        alpha = int(45 * (1 - abs(i - (edge_width // 2)) / max(1, edge_width)))
                        alpha = max(10, min(45, alpha))

                        if direction in ('right', 'left'):
                            pygame.draw.line(edge_surf, (*blend_color[:3], alpha), (i, 0), (i, edge_rect.height))
                        else:
                            pygame.draw.line(edge_surf, (*blend_color[:3], alpha), (0, i), (edge_rect.width, i))

                    self._edge_smooth_cache[cache_key] = (edge_surf, edge_rect)
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
            # Convert to float first to avoid uint8 overflow during multiply
            float_arr = arr.astype(np.float32) * brightness_factor
            np.clip(float_arr, 0, 255, out=float_arr)
            arr[:] = float_arr.astype(np.uint8)
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
        """Draw units using SpriteRenderer with PNG support, fallback to simple shapes."""
        if self._screen is None or self._offscreen is None:
            return

        if len(units) == 0:
            return

        # 如果SpriteRenderer已初始化，使用它（支持PNG精灵）
        if self._sprite_renderer is not None:
            # 设置SpriteRenderer绘制到offscreen buffer（消除临时替换hack）
            self._sprite_renderer._target_surface = self._offscreen
            
            # 使用SpriteRenderer绘制单位（会加载PNG）
            self._sprite_renderer._draw_units(units, camera, selected_unit_ids)
            
            # 恢复默认绘制目标
            self._sprite_renderer._target_surface = None
            return
        else:
            import logging
            logger = logging.getLogger("pycc2")
            logger.warning("[EnhancedRenderer] SpriteRenderer is None! Using fallback shapes (no PNG sprites)")
        
        # Fallback: 如果SpriteRenderer未初始化，使用简单形状
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

    def _draw_attack_lines(self, camera: Camera) -> None:
        """Draw CC2-style attack lines with color coding.

        Green line = Can attack (in range, clear LOS)
        Red/Orange line = Cannot attack (out of range or blocked)
        Yellow dashed = Tracking unit target
        """
        if self._offscreen is None:
            return

        # Get attack line system from game state or global
        import pygame as pg
        from pycc2.presentation.input.attack_line_system import AttackLineSystem, AttackLineStatus

        # Try to get attack line state from interaction_controller
        # This is accessed via a global reference for now
        # TODO: Pass attack_line_system as parameter
        attack_line = getattr(self, '_attack_line_system', None)
        if not attack_line:
            return

        # Draw active attack line (while in ATTACK mode)
        if attack_line.state.active and attack_line.state.source_position:
            source = attack_line.state.source_position
            target_state = attack_line.state.target

            if target_state:
                # Convert world to screen coordinates
                src_screen = camera.world_to_screen(source)
                tgt_screen = camera.world_to_screen(target_state.position)

                # Get color based on status
                status = target_state.status
                color = attack_line.get_line_color(status)

                # Draw line
                start_pos = (int(src_screen[0]), int(src_screen[1]))
                end_pos = (int(tgt_screen[0]), int(tgt_screen[1]))

                if status == AttackLineStatus.CAN_ATTACK:
                    # Solid green line
                    pg.draw.line(self._offscreen, color[:3], start_pos, end_pos, 2)
                    # Draw circle at target
                    pg.draw.circle(self._offscreen, (0, 255, 0), end_pos, 6, 2)
                elif status == AttackLineStatus.OUT_OF_RANGE:
                    # Dashed red line
                    self._draw_dashed_line(start_pos, end_pos, (255, 50, 50), dash_len=8)
                    # X mark at target
                    size = 6
                    pg.draw.line(self._offscreen, (255, 50, 50),
                                (end_pos[0]-size, end_pos[1]-size),
                                (end_pos[0]+size, end_pos[1]+size), 2)
                    pg.draw.line(self._offscreen, (255, 50, 50),
                                (end_pos[0]-size, end_pos[1]+size),
                                (end_pos[0]+size, end_pos[1]-size), 2)
                elif status == AttackLineStatus.BLOCKED:
                    # Orange dashed line
                    self._draw_dashed_line(start_pos, end_pos, (255, 140, 0), dash_len=8)
                    # Block icon at target
                    pg.draw.circle(self._offscreen, (255, 140, 0), end_pos, 8, 2)
                    pg.draw.line(self._offscreen, (255, 140, 0),
                                (end_pos[0]-4, end_pos[1]),
                                (end_pos[0]+4, end_pos[1]), 2)

                # Draw range circle around source
                if hasattr(attack_line, 'COLOR_CAN_ATTACK'):
                    pass  # Already used above

        # Draw confirmed attacks (tracking lines)
        for unit_id, confirmed_target in attack_line._confirmed_attacks.items():
            if not confirmed_target.unit_id:
                continue  # Only draw tracking lines for unit targets

            # Source: attacker position (from _active_source or confirmed_target)
            source_pos = getattr(attack_line, '_active_source', None)
            if source_pos is not None:
                source_screen = camera.world_to_screen(source_pos)
            else:
                # Fallback: use confirmed_target position (may be slightly off)
                source_screen = camera.world_to_screen(confirmed_target.position)
            # Target position is updated by update_tracking()
            target_screen = camera.world_to_screen(confirmed_target.position)

            # Yellow dashed line for tracking
            self._draw_dashed_line(
                (int(source_screen[0]), int(source_screen[1])),
                (int(target_screen[0]), int(target_screen[1])),
                (255, 255, 0),
                dash_len=6,
            )

    def render_los_overlay(self, surface: pygame.Surface, unit, game_map, camera) -> None:
        """Render line-of-sight visualization for the selected unit.

        Called when Ctrl key is held down. Shows visible/hidden areas.
        """
        if unit is None or game_map is None:
            return

        from pycc2.domain.systems.los_system import Lossystem
        from pycc2.domain.value_objects.tile_coord import TileCoord

        los = Lossystem(game_map)
        ux = unit.position.tile_coord.x
        uy = unit.position.tile_coord.y
        tile_size = self.TILE_SIZE

        # Create a semi-transparent overlay
        overlay = pygame.Surface(
            (game_map.width * tile_size, game_map.height * tile_size),
            pygame.SRCALPHA,
        )

        # Check LOS from unit to each tile in range
        vision_range = getattr(unit, 'vision', None)
        max_range = vision_range.range if vision_range else 10

        for ty in range(max(0, uy - max_range), min(game_map.height, uy + max_range + 1)):
            for tx in range(max(0, ux - max_range), min(game_map.width, ux + max_range + 1)):
                if tx == ux and ty == uy:
                    continue

                from_coord = TileCoord(ux, uy)
                to_coord = TileCoord(tx, ty)
                can_see, _ = los.check_los(from_coord, to_coord, max_range)
                screen_x = tx * tile_size
                screen_y = ty * tile_size

                if can_see:
                    # Visible - light green tint
                    pygame.draw.rect(overlay, (0, 255, 0, 25), (screen_x, screen_y, tile_size, tile_size))
                else:
                    # Blocked - dark red tint
                    pygame.draw.rect(overlay, (255, 0, 0, 40), (screen_x, screen_y, tile_size, tile_size))

        # Blit overlay offset by camera
        cam_x = int(camera.offset_x) if hasattr(camera, 'offset_x') else 0
        cam_y = int(camera.offset_y) if hasattr(camera, 'offset_y') else 0
        surface.blit(overlay, (-cam_x, -cam_y))

    # ====== Combat effect proxy methods (forward to SpriteRenderer) ======

    def spawn_hit_flash(self, unit_id: str) -> None:
        if self._sprite_renderer:
            self._sprite_renderer.spawn_hit_flash(unit_id)

    def spawn_damage_number(self, position, damage: int, is_kill: bool = False) -> None:
        if self._sprite_renderer:
            self._sprite_renderer.spawn_damage_number(position, damage, is_kill)

    def spawn_muzzle_flash(self, position, direction: float) -> None:
        if self._sprite_renderer:
            self._sprite_renderer.spawn_muzzle_flash(position, direction)

    def spawn_death_effect(self, unit_id: str, position) -> None:
        if self._sprite_renderer:
            self._sprite_renderer.spawn_death_effect(unit_id, position)

    def spawn_explosion(self, position, size: str = "medium") -> None:
        if self._sprite_renderer:
            self._sprite_renderer.spawn_explosion(position, size)

    def spawn_smoke_screen(self, position, radius: float = 64.0) -> None:
        if self._sprite_renderer:
            self._sprite_renderer.spawn_smoke_screen(position, radius)

    def _draw_queued_commands(self, units: list, camera: Camera) -> None:
        """Draw dashed lines for queued commands (Shift+right-click).

        Cyan dashed lines show queued move waypoints.
        Orange dashed lines show queued attack targets.
        """
        if self._offscreen is None:
            return

        from pycc2.domain.value_objects.vec2 import Vec2

        for unit in units:
            if not hasattr(unit, 'has_queued_commands') or not unit.has_queued_commands:
                continue

            # Get unit screen position
            upos = unit.position.pixel_position if hasattr(unit.position, 'pixel_position') else None
            if upos is None:
                continue

            prev_screen = camera.world_to_screen(upos)

            for cmd in unit._command_queue:
                tx = cmd.get('target_x', 0)
                ty = cmd.get('target_y', 0)
                target_world = Vec2(tx * 32, ty * 32)  # tile to pixel
                target_screen = camera.world_to_screen(target_world)

                start_pos = (int(prev_screen[0]), int(prev_screen[1]))
                end_pos = (int(target_screen[0]), int(target_screen[1]))

                cmd_type = cmd.get('type', 'move')
                if cmd_type == 'attack':
                    # Orange dashed for queued attacks
                    self._draw_dashed_line(start_pos, end_pos, (255, 165, 0), dash_len=6)
                else:
                    # Cyan dashed for queued moves
                    self._draw_dashed_line(start_pos, end_pos, (0, 220, 220), dash_len=6)

                # Draw small waypoint circle
                import pygame as pg
                pg.draw.circle(self._offscreen, (0, 220, 220), end_pos, 4, 1)

                prev_screen = target_screen

    def _draw_dashed_line(
        self,
        start: tuple[int, int],
        end: tuple[int, int],
        color: tuple[int, int, int],
        dash_len: int = 8,
    ) -> None:
        """Draw a dashed line."""
        import math as _math
        x1, y1 = start
        x2, y2 = end
        dx = x2 - x1
        dy = y2 - y1
        distance = _math.sqrt(dx*dx + dy*dy)

        if distance == 0:
            return

        dashes = int(distance / dash_len)
        for i in range(0, dashes, 2):
            start_i = i * dash_len
            end_i = min((i + 1) * dash_len, int(distance))
            sx = x1 + dx * start_i / distance
            sy = y1 + dy * start_i / distance
            ex = x1 + dx * end_i / distance
            ey = y1 + dy * end_i / distance
            import pygame as pg
            pg.draw.line(self._offscreen, color, (int(sx), int(sy)), (int(ex), int(ey)), 2)

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
    
    def _detect_building_clusters(self, game_map: GameMap) -> list[list[tuple[int, int]]]:
        """Find groups of adjacent building tiles using flood-fill/BFS.
        
        Returns list of clusters, each cluster is list of (x,y) coords.
        Building tiles are terrain IDs 4 (BUILDING_ENTERABLE) and 5 (BUILDING_SOLID).
        
        This method caches results to avoid recomputation during rendering.
        
        Args:
            game_map: Game map instance
            
        Returns:
            list: List of building clusters, each containing (x, y) coordinate tuples
        """
        # Use cached result if available
        if self._building_clusters is not None:
            return self._building_clusters
        
        # Compute and cache building clusters
        self._building_clusters = detect_building_clusters(game_map)
        return self._building_clusters
    
    def invalidate_building_cluster_cache(self) -> None:
        """Invalidate the building cluster cache (call when map changes)."""
        self._building_clusters = None

    def shutdown(self) -> None:
        """Clean up renderer resources."""
        self._texture_cache.clear()
        self._scaled_texture_cache.clear()
        self._height_lit_cache.clear()
        self._sprite_cache.clear()
        self._autotile_cache.clear()
        self._terrain_tile_cache.clear()
        self._building_clusters = None  # Clear cluster cache

    def resize(self, width: int, height: int) -> None:
        """Handle window resize."""
        pass
