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

import logging
import math
import random
from typing import TYPE_CHECKING, Any

import pygame

logger = logging.getLogger(__name__)

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

# Import shadow system for SE-direction shadows
from pycc2.presentation.rendering.shadow_system import ShadowRenderer


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
            0: self._make_palette((76, 124, 35),    # OPEN/GRASS - CC2 exact military green #4C7C23
                hue_range=12, sat_range=0.08),
            1: self._make_palette((139, 119, 101),   # ROAD - CC2: dirt/gravel appearance
                hue_range=8, sat_range=0.1),
            2: self._make_palette((58, 100, 24),     # GRASS - darker variant #3A6418
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
        """OPEN (0): CC2 authentic grass with visible grass blades and dirt spots."""
        rng = random.Random(var * 17)
        # CC2's main grass green
        base = CC2_TERRAIN_PALETTE['grass_base']
        ProceduralTextureGenerator._fill_with_variation(surface, base, rng, 12)

        pixels = pygame.surfarray.pixels3d(surface)
        tile_sz = ProceduralTextureGenerator.TILE_SIZE

        # Grass blade lines — 2-3 pixel tall vertical lines (visible grass blades)
        grass_dark = CC2_TERRAIN_PALETTE['grass_dark']
        num_blades = rng.randint(30, 50)  # More blades for visible texture
        for _ in range(num_blades):
            x = rng.randint(0, tile_sz - 1)
            y_start = rng.randint(0, tile_sz - 4)
            blade_len = rng.randint(2, 3)  # 2-3 pixel tall vertical grass blades
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

        # Light highlight patches (sunlight through canopy effect)
        grass_light = CC2_TERRAIN_PALETTE['grass_light']
        num_patches = rng.randint(6, 10)
        for _ in range(num_patches):
            cx = rng.randint(5, tile_sz - 5)
            cy = rng.randint(5, tile_sz - 5)
            radius = rng.randint(3, 5)
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    if dx*dx + dy*dy <= radius*radius:
                        px, py = cx + dx, cy + dy
                        if 0 <= px < tile_sz and 0 <= py < tile_sz:
                            dist_from_center = math.sqrt(dx*dx + dy*dy) / radius
                            if dist_from_center > 0.7:
                                blend_factor = (dist_from_center - 0.7) / 0.3
                                base_px = pixels[px, py]
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

        # Occasional brown dirt patches (3x3 clusters)
        dirt_color = CC2_TERRAIN_PALETTE.get('dirt_base', (139, 109, 59))
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

        track_color = CC2_TERRAIN_PALETTE['road_dark']
        num_tracks = rng.randint(2, 4)

        track_positions = sorted([
            tile_sz // 5 + i * (tile_sz // 5)
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

        # *** Dark crack lines (1-pixel wide horizontal/diagonal lines) ***
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
        surface: pygame.Surface, tid: int, var: int, pal: 'PaletteGenerator', bitmask: int = 0
    ) -> None:
        """GRASS (2): Medium green with visible grass blades and dirt spots - WWII Normandy meadow style."""
        rng = random.Random(var * 31)
        base = (105, 165, 55)
        ProceduralTextureGenerator._fill_with_variation(surface, base, rng, 14)

        pixels = pygame.surfarray.pixels3d(surface)
        tile_sz = ProceduralTextureGenerator.TILE_SIZE

        # *** Grass blades — 2-3 pixel tall vertical lines (visible grass blades) ***
        num_blades = rng.randint(40, 60)
        for _ in range(num_blades):
            x = rng.randint(0, tile_sz - 1)
            y_start = rng.randint(0, tile_sz - 4)
            blade_len = rng.randint(2, 3)  # 2-3 pixel tall vertical grass blades
            shade = rng.choice([
                (90, 150, 45),   # 深绿
                (120, 180, 65),  # 亮绿
                (85, 140, 40),   # 暗绿
                (110, 170, 55),  # 中绿
                (100, 160, 50),  # 标准绿
            ])
            for dy in range(blade_len):
                if 0 <= y_start + dy < tile_sz:
                    pixels[x, y_start + dy] = shade

        # *** Brown dirt patches (3x3 clusters) ***
        dirt_color = CC2_TERRAIN_PALETTE.get('dirt_base', (139, 109, 59))
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

        # *** Darker shadow patches ***
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
        roof_line_color = (92, 60, 35)  # Slightly darker for tile lines
        for x in range(tile_sz):
            for y in range(0, roof_height):
                pixels[x, y] = roof_color
            # Roof edge highlight
            if roof_height < tile_sz:
                pixels[x, roof_height] = (95, 62, 35)
        # Horizontal tile lines on roof (2-pixel spacing)
        for y in range(2, roof_height, 2):
            for x in range(tile_sz):
                pixels[x, y] = roof_line_color

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
        roof_line_color = (72, 67, 62)  # Slightly darker for tile lines
        for x in range(tile_sz):
            for y in range(0, roof_height):
                pixels[x, y] = roof_color
            if roof_height < tile_sz:
                pixels[x, roof_height] = (75, 70, 65)
        # Horizontal tile lines on roof (2-pixel spacing)
        for y in range(2, roof_height, 2):
            for x in range(tile_sz):
                pixels[x, y] = roof_line_color

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
        - Non-connected edges: draw shore/bank transition (darker gradient 4-6px) + foam line
        - Wave animation flows in consistent direction using position-based phase
        - Sparkle points distribute evenly across continuous water area
        """
        from pycc2.presentation.rendering.autotile_system import (
            DIR_NORTH, DIR_EAST, DIR_SOUTH, DIR_WEST,
            get_edge_transition_width,
        )
        
        rng = random.Random(var * 127)
        base = CC2_TERRAIN_PALETTE['water_base']
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
                    max(0, min(255, b + offset))
                )

        water_light = CC2_TERRAIN_PALETTE['water_light']
        num_waves = rng.randint(12, 20)

        for i in range(num_waves):
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

        water_dark = CC2_TERRAIN_PALETTE['water_dark']
        water_foam = CC2_TERRAIN_PALETTE['water_foam']
        edge_widths = get_edge_transition_width(tid, bitmask, tile_sz)

        if not (bitmask & DIR_NORTH) and edge_widths['north'] > 0:
            ew = edge_widths['north']
            for y in range(ew):
                gradient = y / ew
                darkness = int((1.0 - gradient) * 30)
                for x in range(tile_sz):
                    r, g, b = int(pixels[x, y][0]), int(pixels[x, y][1]), int(pixels[x, y][2])
                    pixels[x, y] = (
                        max(32, r - darkness),
                        max(72, g - darkness),
                        max(130, b - darkness)
                    )
            for x in range(0, tile_sz, 2):
                pixels[x, 0] = water_foam

        if not (bitmask & DIR_SOUTH) and edge_widths['south'] > 0:
            ew = edge_widths['south']
            for y in range(tile_sz - ew, tile_sz):
                dist = tile_sz - 1 - y
                gradient = dist / ew
                darkness = int((1.0 - gradient) * 30)
                for x in range(tile_sz):
                    r, g, b = int(pixels[x, y][0]), int(pixels[x, y][1]), int(pixels[x, y][2])
                    pixels[x, y] = (
                        max(32, r - darkness),
                        max(72, g - darkness),
                        max(130, b - darkness)
                    )
            for x in range(0, tile_sz, 2):
                pixels[x, tile_sz - 1] = water_foam

        if not (bitmask & DIR_WEST) and edge_widths['west'] > 0:
            ew = edge_widths['west']
            for x in range(ew):
                gradient = x / ew
                darkness = int((1.0 - gradient) * 30)
                for y in range(tile_sz):
                    r, g, b = int(pixels[x, y][0]), int(pixels[x, y][1]), int(pixels[x, y][2])
                    pixels[x, y] = (
                        max(32, r - darkness),
                        max(72, g - darkness),
                        max(130, b - darkness)
                    )
            for y in range(0, tile_sz, 2):
                pixels[0, y] = water_foam

        if not (bitmask & DIR_EAST) and edge_widths['east'] > 0:
            ew = edge_widths['east']
            for x in range(tile_sz - ew, tile_sz):
                dist = tile_sz - 1 - x
                gradient = dist / ew
                darkness = int((1.0 - gradient) * 30)
                for y in range(tile_sz):
                    r, g, b = int(pixels[x, y][0]), int(pixels[x, y][1]), int(pixels[x, y][2])
                    pixels[x, y] = (
                        max(32, r - darkness),
                        max(72, g - darkness),
                        max(130, b - darkness)
                    )
            for y in range(0, tile_sz, 2):
                pixels[tile_sz - 1, y] = water_foam

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
        """BRIDGE (11): Enhanced wooden/concrete bridge with texture, underwater shadows, and railings.

        P2-8 Enhancements:
        - Enhanced deck texture (wooden plank + concrete stripe patterns)
        - Underwater pier shadows (SE direction offset)
        - Rail post details (top and bottom rails with posts)
        """
        rng = random.Random(var * 241)
        tile_sz = ProceduralTextureGenerator.TILE_SIZE

        # Water underneath at edges (darker for shadow effect)
        water_color = (35, 70, 120)  # #234678 dark blue-grey
        surface.fill(water_color)
        pixels = pygame.surfarray.pixels3d(surface)

        # ===== P2-8 Enhancement 1: Underwater Pier Shadows (SE Direction) =====
        # Simulate pier supports under water with SE-offset dark ellipses
        shadow_color = (25, 55, 95)  # Darker than water
        pier_positions = [
            (tile_sz // 4, int(0.7 * tile_sz)),           # Left pier (SE of left beam)
            (int(0.58 * tile_sz), int(0.72 * tile_sz)),   # Right pier (SE of right beam)
        ]
        for pier_cx, pier_cy in pier_positions:
            # Elliptical shadow (wider horizontally, simulating perspective)
            pier_radius_x = max(3, tile_sz // 10)
            pier_radius_y = max(2, tile_sz // 14)
            for dy in range(-pier_radius_y, pier_radius_y + 1):
                for dx in range(-pier_radius_x, pier_radius_x + 1):
                    sx, sy = pier_cx + dx, pier_cy + dy
                    if 0 <= sx < tile_sz and 0 <= sy < tile_sz:
                        # Ellipse equation: (dx/rx)^2 + (dy/ry)^2 <= 1
                        if (dx / pier_radius_x) ** 2 + (dy / pier_radius_y) ** 2 <= 1.0:
                            # Gradient alpha from center to edge
                            dist_ratio = math.sqrt((dx / pier_radius_x) ** 2 + (dy / pier_radius_y) ** 2)
                            alpha_factor = 1.0 - dist_ratio * 0.5  # Faded at edges
                            pixels[sx, sy] = tuple(
                                int(water_color[i] * (1 - alpha_factor) + shadow_color[i] * alpha_factor)
                                for i in range(3)
                            )

        # Bridge deck - wooden planks (scaled position and size)
        plank_color = (160, 120, 70)
        plank_dark = (130, 95, 55)
        deck_top = max(2, tile_sz // 8)
        deck_bottom = min(tile_sz - 2, int(0.54 * tile_sz))
        deck_left = max(1, tile_sz // 16)
        deck_right = min(tile_sz - 1, int(0.625 * tile_sz))

        for y in range(deck_top, deck_bottom):
            for x in range(deck_left, deck_right):
                pixels[x, y] = plank_color

        # ===== P2-8 Enhancement 2a: Enhanced Wooden Plank Texture =====
        # Main horizontal plank gaps (more prominent)
        plank_spacing = max(3, tile_sz // 12)
        for y in range(deck_top, deck_bottom, plank_spacing):
            for x in range(deck_left, deck_right):
                if x < tile_sz and y < tile_sz:
                    pixels[x, y] = plank_dark

        # Secondary fine plank lines (every 4px for wood grain detail)
        fine_plank_spacing = max(4, tile_sz // 10)
        fine_plank_color = (145, 108, 62)  # Slightly lighter dark
        for y in range(deck_top + 2, deck_bottom - 1, fine_plank_spacing):
            for x in range(deck_left + 1, deck_right - 1):
                if x < tile_sz and y < tile_sz and rng.random() > 0.5:
                    pixels[x, y] = fine_plank_color

        # ===== P2-8 Enhancement 2b: Concrete Stripe Pattern (alternating planks) =====
        concrete_color = (150, 140, 130)  # Light gray concrete
        concrete_dark = (130, 120, 110)   # Concrete shadow
        concrete_spacing = max(6, tile_sz // 6)  # Every 6th plank is concrete
        for y in range(deck_top + plank_spacing, deck_bottom - plank_spacing, concrete_spacing):
            for x in range(deck_left, deck_right):
                if x < tile_sz and y < tile_sz:
                    # Alternate between concrete and dark concrete for texture
                    if (y // plank_spacing) % 2 == 0:
                        pixels[x, y] = concrete_color
                    else:
                        pixels[x, y] = concrete_dark

        # Plank grain (vertical lines per plank) - enhanced detail
        grain_spacing_x = max(4, tile_sz // 8)
        for x in range(deck_left + grain_spacing_x, deck_right, grain_spacing_x):
            for y in range(deck_top, deck_bottom):
                if x < tile_sz and y < tile_sz:
                    # More frequent grain with variation
                    if rng.random() > 0.5:
                        pixels[x, y] = plank_dark
                    elif rng.random() > 0.8:
                        # Occasional lighter grain highlight
                        pixels[x, y] = (175, 135, 85)

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

        # ===== P2-8 Enhancement 3: Rail Post Details =====
        rail_post_spacing = max(5, tile_sz // 6)
        rail_post_top = max(1, tile_sz // 12)
        rail_post_bottom = min(tile_sz - 1, int(0.56 * tile_sz))

        # Top rail line (horizontal bar connecting top posts)
        top_rail_y = rail_post_top
        if top_rail_y < tile_sz:
            for x in range(deck_left, deck_right):
                if x < tile_sz:
                    pixels[x, top_rail_y] = (90, 65, 35)  # Darker rail color

        # Bottom rail line (horizontal bar connecting bottom posts)
        bottom_rail_y = rail_post_bottom
        if bottom_rail_y < tile_sz:
            for x in range(deck_left, deck_right):
                if x < tile_sz:
                    pixels[x, bottom_rail_y] = (90, 65, 35)

        # Vertical rail posts (at regular intervals)
        for x in range(deck_left + rail_post_spacing, deck_right - rail_post_spacing // 2, rail_post_spacing):
            # Top post (connects to top rail)
            for py in range(rail_post_top, min(rail_post_top + 3, tile_sz)):
                if 0 <= x < tile_sz and py < tile_sz:
                    pixels[x, py] = beam_color

            # Bottom post (connects to bottom rail)
            for py in range(max(rail_post_bottom - 2, 0), rail_post_bottom):
                if 0 <= x < tile_sz and py < tile_sz:
                    pixels[x, py] = beam_color

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
        except Exception as e:
            logging.debug(f"Texture generation failed: {e}")

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
            'BARBED_WIRE': SpriteGenerator._draw_barbed_wire,  # P1-4 Fix: New
            'WRECKAGE_VEHICLE': SpriteGenerator._draw_wreckage,
            'CAMOUFLAGE_NET': SpriteGenerator._draw_camo_net,

            # CC2特色装饰物 (STEP B - 对照CC2截图新增)
            'WRECKAGE_PLANE': SpriteGenerator._draw_plane_wreckage,      # ✈️ 飞机残骸
            'BARRICADE_CONCRETE': SpriteGenerator._draw_concrete_barricade,  # 🚧 混凝土路障
            'BARRICADE_SANDBAG': SpriteGenerator._draw_sandbag_barricade,   # 🛡️ 沙袋路障
            'CRATER_CLUSTER': SpriteGenerator._draw_crater_cluster,         # 💣 弹坑群
            'DEBRIS_FIELD': SpriteGenerator._draw_debris_field,             # 🗑️ 碎片场
            'BURNING_WRECKAGE': SpriteGenerator._draw_burning_wreckage,     # 🔥 燃烧残骸
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
        """Draw sandbag wall (P1-4 Fix: Enhanced with texture detail)."""
        bag_color = (190, 170, 130)
        shadow = (150, 130, 90)
        highlight = (210, 195, 160)

        for y in range(14, 26):
            for x in range(2, 30):
                is_bag = (x // 4 + y // 2) % 2 == 0
                if is_bag:
                    # P1-4: Add texture variation
                    if (x * y + variant) % 5 == 0:
                        color = highlight
                    elif (x + y) % 7 == 0:
                        color = shadow
                    else:
                        color = bag_color
                    surface.set_at((x, y), color)
                elif y in [15, 17, 19, 21, 23, 25]:
                    # Shadow between bags
                    surface.set_at((x, y), (120, 110, 85))

    @staticmethod
    def _draw_barbed_wire(surface: pygame.Surface, variant: int) -> None:
        """Draw barbed wire obstacle (P1-4 Fix: New decoration type)."""
        wire_color = (180, 180, 180)
        dark_wire = (120, 120, 120)

        # Horizontal wires (3 strands)
        for strand_y in [10, 16, 22]:
            for x in range(4, 28):
                # P1-4: Wavy wire pattern
                wave = math.sin(x * 0.5 + variant) * 2
                y = int(strand_y + wave)
                if 0 <= y < 32:
                    surface.set_at((x, y), wire_color if x % 3 != 0 else dark_wire)

        # Barbs (small V-shapes every 6 pixels)
        for barb_x in range(6, 28, 6):
            barb_y_base = 16 + int(math.sin(barb_x * 0.5 + variant) * 2)
            # Up-pointing barb
            surface.set_at((barb_x, barb_y_base - 2), dark_wire)
            surface.set_at((barb_x - 1, barb_y_base - 1), dark_wire)
            surface.set_at((barb_x + 1, barb_y_base - 1), dark_wire)
            # Down-pointing barb (offset)
            if barb_x % 12 == 0:
                surface.set_at((barb_x, barb_y_base + 2), dark_wire)
                surface.set_at((barb_x - 1, barb_y_base + 1), dark_wire)
                surface.set_at((barb_x + 1, barb_y_base + 1), dark_wire)

        # Posts (every 12 pixels)
        for post_x in range(4, 28, 12):
            post_color = (100, 90, 80)
            for post_y in range(8, 24):
                surface.set_at((post_x, post_y), post_color)
                surface.set_at((post_x + 1, post_y), (120, 110, 100))
    
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

    # ===================================================================
    # CC2特色装饰物 (STEP B - 对照CC2截图实现)
    # ===================================================================

    @staticmethod
    def _draw_plane_wreckage(surface: pygame.Surface, variant: int) -> None:
        """Draw crashed aircraft wreckage (✈️ 飞机残骸).

        Based on CC2 screenshots: irregular wing+fuselage shape,
        dark metal color with rust patches, larger than vehicle wreckage.
        Common near airfields and drop zones.
        """
        fuselage_color = (55, 50, 45)
        wing_color = (60, 55, 50)
        rust = (110, 65, 25)
        dark_rust = (80, 45, 15)
        shadow = (35, 30, 25)

        # Fuselage (机身 - central elongated shape)
        fuselage_points = [
            (14, 8), (16, 7), (18, 8), (19, 12), (18, 20),
            (17, 24), (15, 26), (13, 24), (12, 20), (13, 12), (14, 8)
        ]

        for y in range(7, 27):
            for x in range(11, 21):
                if SpriteGenerator._point_in_polygon(x, y, fuselage_points):
                    # Rust variation
                    if (x + y + variant) % 9 == 0:
                        surface.set_at((x, y), rust)
                    elif (x * y) % 13 == 0:
                        surface.set_at((x, y), dark_rust)
                    else:
                        surface.set_at((x, y), fuselage_color)

        # Left wing (左翼 - swept back shape)
        left_wing = [
            (6, 14), (9, 13), (12, 14), (13, 16), (12, 18),
            (9, 17), (6, 16), (5, 15)
        ]
        for y in range(13, 19):
            for x in range(5, 14):
                if SpriteGenerator._point_in_polygon(x, y, left_wing):
                    shade = wing_color if (x + y) % 3 != 0 else shadow
                    surface.set_at((x, y), shade)

        # Right wing (右翼 - mirror of left)
        right_wing = [
            (26, 14), (23, 13), (20, 14), (19, 16), (20, 18),
            (23, 17), (26, 16), (27, 15)
        ]
        for y in range(13, 19):
            for x in range(19, 28):
                if SpriteGenerator._point_in_polygon(x, y, right_wing):
                    shade = wing_color if (x + y) % 3 != 0 else shadow
                    surface.set_at((x, y), shade)

        # Tail section (尾翼)
        for x in range(14, 19):
            surface.set_at((x, 6), dark_rust)

    @staticmethod
    def _draw_concrete_barricade(surface: pygame.Surface, variant: int) -> None:
        """Draw concrete anti-tank barricade (🚧 混凝土路障).

        Based on CC2 urban combat: X-shaped or angled concrete blocks,
        gray color with weathering, provides heavy cover.
        """
        concrete = (140, 135, 130)
        dark_concrete = (110, 105, 100)
        highlight = (160, 155, 150)
        shadow_edge = (90, 85, 80)

        # Main block (X-shaped barricade from top-down view looks like diamond)
        center_x, center_y = 16, 16

        # Diagonal bar 1 (top-left to bottom-right)
        for i in range(-6, 7):
            offset = abs(i)
            width = max(3, 5 - offset // 2)
            for w in range(-width, width + 1):
                px = center_x + i + w // 2
                py = center_y - i + w // 2
                if 4 <= px < 28 and 4 <= py < 28:
                    if w == -width or w == width:
                        surface.set_at((px, py), shadow_edge)
                    elif w == -width + 1 or w == width - 1:
                        surface.set_at((px, py), dark_concrete)
                    else:
                        surface.set_at((px, py), concrete if (i + w) % 4 != 0 else highlight)

        # Diagonal bar 2 (bottom-left to top-right)
        for i in range(-6, 7):
            offset = abs(i)
            width = max(3, 5 - offset // 2)
            for w in range(-width, width + 1):
                px = center_x + i + w // 2
                py = center_y + i + w // 2
                if 4 <= px < 28 and 4 <= py < 28:
                    if w == -width or w == width:
                        surface.set_at((px, py), shadow_edge)
                    elif w == -width + 1 or w == width - 1:
                        surface.set_at((px, py), dark_concrete)
                    else:
                        surface.set_at((px, py), concrete if (i - w) % 4 != 0 else highlight)

    @staticmethod
    def _draw_sandbag_barricade(surface: pygame.Surface, variant: int) -> None:
        """Draw sandbag defensive position (🛡️ 沙袋路障).

        Smaller than SANDBAG_WALL, used for individual firing positions.
        L-shaped or U-shaped layout visible from above.
        """
        bag_color = (160, 145, 110)
        bag_dark = (130, 115, 85)
        bag_shadow = (100, 90, 65)

        # U-shaped sandbag wall (3 sides)
        walls = [
            # Top wall (horizontal)
            [(8, 10), (8, 13), (24, 13), (24, 10)],
            # Left wall (vertical)
            [(8, 13), (11, 13), (11, 24), (8, 24)],
            # Right wall (vertical)
            [(21, 13), (24, 13), (24, 24), (21, 24)],
        ]

        for wall_idx, wall in enumerate(walls):
            for y in range(min(p[1] for p in wall), max(p[1] for p in wall)):
                for x in range(min(p[0] for p in wall), max(p[0] for p in wall)):
                    if SpriteGenerator._point_in_polygon(x, y, wall):
                        # Bag texture (individual bags ~3px each)
                        bag_idx = ((x - 8) // 3 + (y - 10) // 3 + variant) % 3
                        if bag_idx == 0:
                            color = bag_color
                        elif bag_idx == 1:
                            color = bag_dark
                        else:
                            color = bag_shadow

                        # Edge highlight
                        is_edge = (y == min(p[1] for p in wall) or
                                 y == max(p[1] for p in wall) - 1 or
                                 x == min(p[0] for p in wall) or
                                 x == max(p[0] for p in wall) - 1)
                        if is_edge:
                            color = tuple(min(255, c + 20) for c in color)

                        surface.set_at((x, y), color)

    @staticmethod
    def _draw_crater_cluster(surface: pygame.Surface, variant: int) -> None:
        """Draw cluster of impact craters (💣 弹坑群).

        Multiple small craters from artillery barrage or bombing.
        Based on CC2 screenshot 8: scattered dark circles on grass.
        """
        crater_base = (75, 65, 50)
        crater_dark = (55, 48, 35)
        crater_rim = (95, 85, 70)

        # Cluster pattern (3-5 small craters based on variant)
        rng = random.Random(variant * 42)
        num_craters = 3 + (variant % 3)
        positions = []

        for _ in range(num_craters):
            cx = rng.randint(8, 24)
            cy = rng.randint(8, 24)
            radius = rng.randint(3, 6)
            positions.append((cx, cy, radius))

        for cx, cy, radius in positions:
            for y in range(max(4, cy - radius - 2), min(28, cy + radius + 2)):
                for x in range(max(4, cx - radius - 2), min(28, cx + radius + 2)):
                    dist = math.sqrt((x - cx)**2 + (y - cy)**2)
                    if dist <= radius:
                        # Depth shading (darker toward center)
                        depth_factor = dist / radius
                        if depth_factor < 0.3:
                            color = crater_dark
                        elif depth_factor < 0.7:
                            color = crater_base
                        else:
                            color = crater_rim

                        # Rim highlight at edge
                        if dist > radius - 1.5:
                            color = tuple(min(255, c + 15) for c in crater_rim)

                        surface.set_at((x, y), color)

    @staticmethod
    def _draw_debris_field(surface: pygame.Surface, variant: int) -> None:
        """Draw scattered debris field (🗑️ 碎片场).

        Small irregular fragments from destroyed structures/vehicles.
        Random pixel noise with some structure.
        """
        debris_colors = [
            (80, 75, 70),   # Metal
            (100, 95, 88),  # Light metal
            (120, 110, 100),# Wood/plastic
            (60, 55, 50),   # Dark debris
            (90, 85, 75),   # Mixed material
        ]
        bg = (0, 0, 0, 0)  # Transparent

        rng = random.Random(variant * 137)

        # Scatter 40-60 debris pixels
        num_debris = 40 + (variant % 20)
        for _ in range(num_debris):
            x = rng.randint(4, 27)
            y = rng.randint(4, 27)
            color = debris_colors[rng.randint(0, len(debris_colors) - 1)]

            # Draw 1-3 pixel clusters
            size = rng.randint(1, 3)
            for dx in range(size):
                for dy in range(size):
                    px, py = x + dx, y + dy
                    if 4 <= px < 28 and 4 <= py < 28:
                        # Slight color variation per pixel
                        variation = rng.randint(-8, 8)
                        final_color = tuple(
                            max(0, min(255, c + variation)) for c in color
                        )
                        surface.set_at((px, py), final_color)

        # Add a few larger structural pieces (2-3 per debris field)
        for _ in range(2 + (variant % 2)):
            start_x = rng.randint(6, 22)
            start_y = rng.randint(6, 22)
            length = rng.randint(3, 7)
            angle = rng.uniform(0, math.pi * 2)

            for i in range(length):
                px = int(start_x + i * math.cos(angle))
                py = int(start_y + i * math.sin(angle))
                if 4 <= px < 28 and 4 <= py < 28:
                    surface.set_at((px, py), (70, 65, 58))

    @staticmethod
    def _draw_burning_wreckage(surface: pygame.Surface, variant: int) -> None:
        """Draw burning/destroyed wreckage (🔥 燃烧残骸).

        Vehicle or structure actively on fire.
        Dark hull with orange/red/yellow flame overlay.
        """
        hull_color = (50, 45, 40)
        flame_orange = (220, 120, 20)
        flame_red = (180, 50, 10)
        flame_yellow = (240, 200, 50)
        smoke_gray = (120, 120, 120)

        # Base wreckage hull (similar to _draw_wreckage but more damaged)
        hull_points = [
            (5, 20), (7, 16), (11, 14), (17, 13), (23, 14),
            (26, 17), (27, 22), (25, 26), (17, 27), (9, 26), (6, 23)
        ]

        for y in range(13, 28):
            for x in range(5, 28):
                if SpriteGenerator._point_in_polygon(x, y, hull_points):
                    surface.set_at((x, y), hull_color)

        # Flame areas (multiple fire points)
        fire_centers = [
            (12, 18), (18, 17), (22, 20)
        ]
        rng = random.Random(variant * 99)  # FIX: varant → variant

        for fcx, fcy in fire_centers[:2 + (variant % 2)]:
            # Flickering flames (irregular shapes)
            for y in range(fcy - 4, fcy + 5):
                for x in range(fcx - 4, fcx + 5):
                    dist = math.sqrt((x - fcx)**2 + (y - fcy)**2)
                    if dist <= 4.5 and rng.random() > 0.3:
                        # Color gradient: yellow core → orange → red edge
                        if dist < 1.5:
                            color = flame_yellow
                        elif dist < 2.8:
                            color = flame_orange
                        else:
                            color = flame_red

                        # Random flicker (some pixels transparent for flicker effect)
                        if rng.random() > 0.15:
                            surface.set_at((x, y), color)

        # Smoke plume (light gray pixels rising from fires)
        for smoke_y in range(8, 14):
            for smoke_x in range(10, 24):
                if rng.random() > 0.85:
                    alpha_smoke = (*smoke_gray, 150 - (smoke_y - 8) * 10)
                    surface.set_at((smoke_x, smoke_y), alpha_smoke)


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
        except Exception as e:
            logging.debug(f"Tile texture creation failed: {e}")
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

    def __init__(self, attack_line_system=None):
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
        self._transition_cache: dict[tuple[int, int, int, int, str], tuple[pygame.Surface, pygame.Rect]] = {}  # Cached terrain transition strips
        self._last_map_hash: int = 0  # Track map changes for cache invalidation
        self._frame_count = 0
        self._sprite_renderer = None  # 延迟初始化，等待display ready
        self._isometric_renderer = None  # Isometric renderer (lazy init)
        self._shadow_renderer = ShadowRenderer()  # SE-direction shadow system
        self._attack_line_system = attack_line_system  # P0-2 Fix: Dependency injection (was getattr hack)
    
    def initialize(self, screen: pygame.Surface) -> None:
        """Initialize renderer with display surface."""
        self._screen = screen
        try:
            # FIXED: Use SRCALPHA to support transparent shadows
            self._offscreen = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        except pygame.error as e:
            # Fallback for headless/testing environments without video mode set
            import warnings
            warnings.warn(f"Could not create SRCALPHA surface: {e}. Using convert() fallback.")
            self._offscreen = pygame.Surface(screen.get_size()).convert()

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

    def set_attack_line_system(self, attack_line_system) -> None:
        """Set attack line system (dependency injection setter - P0-2 Fix)."""
        self._attack_line_system = attack_line_system

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
            # FIXED: Use SRCALPHA to support transparent shadows
            self._offscreen = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)

        # STEP 1: Clear off-screen buffer
        self._offscreen.fill((34, 40, 48))  # Dark blue-gray background

        # STEP 2: Draw terrain — use enhanced texturing with simple fallback
        try:
            self._draw_enhanced_terrain(game_map, camera, debug_mode)
        except Exception as e:
            logger.warning(f"Enhanced terrain failed, falling back to simple: {e}")
            self._draw_simple_terrain(game_map, camera)

        # STEP 3: Draw grid ONLY in debug mode
        # ============================================================
        # ⚠️ RELEASE MODE GUARD: 以下debug绘制仅在 debug_mode=True 时执行
        # - _draw_grid(): 地形网格线（开发调试用）
        # - 性能影响: O(width*height) 线段绘制/帧
        # - 正式发布: debug_mode=False → 完全跳过，零开销
        # ============================================================
        if debug_mode:
            self._draw_grid(game_map, camera)

        # STEP 4: Draw decorations (minimal)
        self._draw_decorations(game_map, camera)

        # STEP 4.0: Draw ALL shadows FIRST (under everything - correct Z-order)
        self._render_building_shadows(game_map, camera)  # Building shadows BEFORE roofs
        self._render_tree_shadows(game_map, camera)      # Tree shadows BEFORE trees

        # STEP 4.4: Draw building roofs (CC2 top-down view — covers side-view terrain texture)
        self._draw_building_roofs(game_map, camera)

        # STEP 4.5: Draw building interiors (auto-switch when units are inside)
        self._draw_building_interiors(game_map, units, camera)

        # STEP 4.6: Draw building floor numbers on roof
        self._draw_building_floor_numbers(game_map, camera)

        # STEP 4.7: Draw Victory Location flags and edge arrows
        self._draw_vl_flags(game_map, camera)

        # STEP 4.8: Environment lighting pass (after terrain/buildings, before units)
        self._apply_environment_lighting(game_map, camera, units)

        # STEP 5: Draw units
        self._draw_units(units, camera, selected_unit_ids)

        # STEP 5.1: Draw unit and vehicle shadows (AFTER units rendered)
        self._render_unit_shadows(units, camera)

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
            0: (76, 124, 35),    # OPEN/GRASS - CC2 exact military green #4C7C23
            1: (139, 119, 101),  # ROAD - dirt brown
            2: (58, 100, 24),     # GRASS - darker green #3A6418
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

        # Terrain transition blending between different terrain types
        if not debug_mode and tile_screen_size >= 16:
            self._render_terrain_transitions(game_map, camera, start_x, end_x, start_y, end_y, tile_screen_size)

        # Draw terrain borders ONLY in debug mode (Issue 4: remove harsh grid lines in normal mode)
        # ============================================================
        # ⚠️ RELEASE MODE GUARD: 地形边界线仅在 debug_mode=True 时绘制
        # - _draw_terrain_borders(): 不同地形类型间的边界线
        # - 性能影响: O(visible_tiles) 边界检查/帧
        # - 正式发布: debug_mode=False → 完全跳过，零开销
        # ============================================================
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

    TERRAIN_BASE_COLORS = {
        0: (76, 112, 52),
        1: (139, 119, 101),
        2: (68, 105, 48),
        3: (45, 68, 33),
        4: (139, 115, 85),
        5: (120, 118, 115),
        6: (62, 87, 117),
        7: (85, 70, 55),
        8: (110, 108, 105),
        9: (135, 115, 80),
        10: (95, 145, 165),
        11: (160, 140, 100),
        12: (90, 85, 75),
    }

    def _render_terrain_transitions(
        self, game_map: GameMap, camera: Camera,
        start_x: int, end_x: int, start_y: int, end_y: int,
        tile_screen_size: int
    ) -> None:
        """Render gradient transition strips between adjacent tiles of different terrain types.

        P2-11 Enhanced Version:
        - Smooth color interpolation (linear blend from current to neighbor color)
        - Middle-color edge pixels (average of two terrain colors at boundary)
        - Directional alpha fading (softer transitions toward tile center)
        - Enhanced caching for performance

        For each tile, checks 4 neighbors (N/S/E/W). When a neighbor has a
        different terrain type, draws a 4-6px gradient strip on the shared edge
        that blends from the current tile's base color to the neighbor's base
        color, creating smooth visual transitions (e.g. grass→road, grass→water).

        Uses caching keyed by (tx, ty, current_terrain, neighbor_terrain, direction)
        to avoid per-frame recalculation. Cache is invalidated when the map changes.
        """
        if self._screen is None or self._offscreen is None or tile_screen_size < 8:
            return

        from pycc2.domain.value_objects.vec2 import Vec2

        try:
            current_map_hash = hash((game_map.width, game_map.height, id(game_map)))
            if current_map_hash != self._last_map_hash:
                self._transition_cache.clear()
        except Exception:
            pass

        # P2-11: Slightly wider transition strips for smoother blending
        strip_width = max(5, min(7, tile_screen_size // 8))

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                current = self._get_terrain_at(game_map, tx, ty)
                if current < 0:
                    continue

                neighbors = [
                    (tx, ty - 1, 'north'),
                    (tx, ty + 1, 'south'),
                    (tx + 1, ty, 'east'),
                    (tx - 1, ty, 'west'),
                ]

                for nx, ny, direction in neighbors:
                    if nx < 0 or ny < 0 or nx >= game_map.width or ny >= game_map.height:
                        continue
                    neighbor = self._get_terrain_at(game_map, nx, ny)
                    if neighbor < 0 or neighbor == current:
                        continue

                    cache_key = (tx, ty, current, neighbor, direction)
                    if cache_key in self._transition_cache:
                        cached_surf, cached_rect = self._transition_cache[cache_key]
                        self._offscreen.blit(cached_surf, cached_rect)
                        continue

                    color_from = self.TERRAIN_BASE_COLORS.get(current, (128, 128, 128))
                    color_to = self.TERRAIN_BASE_COLORS.get(neighbor, (128, 128, 128))

                    # P2-11 Enhancement: Calculate middle color (average of two terrain colors)
                    middle_color = (
                        (color_from[0] + color_to[0]) // 2,
                        (color_from[1] + color_to[1]) // 2,
                        (color_from[2] + color_to[2]) // 2,
                    )

                    world_x = tx * self.TILE_SIZE
                    world_y = ty * self.TILE_SIZE
                    screen_pos = camera.world_to_screen(Vec2(world_x, world_y))
                    base_x = int(screen_pos[0])
                    base_y = int(screen_pos[1])

                    if direction == 'north':
                        rect = pygame.Rect(base_x, base_y, tile_screen_size, strip_width)
                    elif direction == 'south':
                        rect = pygame.Rect(base_x, base_y + tile_screen_size - strip_width, tile_screen_size, strip_width)
                    elif direction == 'east':
                        rect = pygame.Rect(base_x + tile_screen_size - strip_width, base_y, strip_width, tile_screen_size)
                    else:
                        rect = pygame.Rect(base_x, base_y, strip_width, tile_screen_size)

                    strip_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)

                    # P2-11 Enhanced interpolation with middle-color emphasis
                    if direction in ('north', 'south'):
                        for col in range(rect.width):
                            t = col / max(1, rect.width - 1)  # 0.0 (from) → 1.0 (to)

                            # Smooth interpolation with sinusoidal easing for natural look
                            smooth_t = 0.5 * (1 - math.cos(t * math.pi))  # Ease in-out

                            # Color interpolation: from → middle → to
                            if t < 0.5:
                                # First half: blend from color_from to middle_color
                                local_t = t * 2  # 0.0 → 1.0
                                r = int(color_from[0] * (1 - local_t) + middle_color[0] * local_t)
                                g = int(color_from[1] * (1 - local_t) + middle_color[1] * local_t)
                                b = int(color_from[2] * (1 - local_t) + middle_color[2] * local_t)
                            else:
                                # Second half: blend from middle_color to color_to
                                local_t = (t - 0.5) * 2  # 0.0 → 1.0
                                r = int(middle_color[0] * (1 - local_t) + color_to[0] * local_t)
                                g = int(middle_color[1] * (1 - local_t) + color_to[1] * local_t)
                                b = int(middle_color[2] * (1 - local_t) + color_to[2] * local_t)

                            for row in range(rect.height):
                                edge_t = row / max(1, rect.height - 1)
                                # Directional alpha fade (stronger at edge, fades inward)
                                if direction == 'north':
                                    # North: stronger at top (row=0), fades downward
                                    alpha = int(140 * (1 - edge_t ** 0.7))
                                else:
                                    # South: stronger at bottom (row=max), fades upward
                                    alpha = int(140 * edge_t ** 0.7)

                                # P2-11: Boost alpha at exact boundary (middle of strip)
                                boundary_boost = 1.0
                                if 0.4 <= edge_t <= 0.6:
                                    boundary_boost = 1.3  # 30% brighter at boundary

                                alpha = int(min(255, alpha * boundary_boost))
                                alpha = max(0, min(255, alpha))
                                strip_surf.set_at((col, row), (r, g, b, alpha))
                    else:
                        for row in range(rect.height):
                            t = row / max(1, rect.height - 1)  # 0.0 (from) → 1.0 (to)

                            # Smooth interpolation with sinusoidal easing
                            smooth_t = 0.5 * (1 - math.cos(t * math.pi))

                            # Color interpolation: from → middle → to
                            if t < 0.5:
                                local_t = t * 2
                                r = int(color_from[0] * (1 - local_t) + middle_color[0] * local_t)
                                g = int(color_from[1] * (1 - local_t) + middle_color[1] * local_t)
                                b = int(color_from[2] * (1 - local_t) + middle_color[2] * local_t)
                            else:
                                local_t = (t - 0.5) * 2
                                r = int(middle_color[0] * (1 - local_t) + color_to[0] * local_t)
                                g = int(middle_color[1] * (1 - local_t) + color_to[1] * local_t)
                                b = int(middle_color[2] * (1 - local_t) + color_to[2] * local_t)

                            for col in range(rect.width):
                                edge_t = col / max(1, rect.width - 1)
                                # Directional alpha fade
                                if direction == 'west':
                                    # West: stronger at left (col=0), fades rightward
                                    alpha = int(140 * (1 - edge_t ** 0.7))
                                else:
                                    # East: stronger at right (col=max), fades leftward
                                    alpha = int(140 * edge_t ** 0.7)

                                # P2-11: Boost alpha at exact boundary
                                boundary_boost = 1.0
                                if 0.4 <= edge_t <= 0.6:
                                    boundary_boost = 1.3

                                alpha = int(min(255, alpha * boundary_boost))
                                alpha = max(0, min(255, alpha))
                                strip_surf.set_at((col, row), (r, g, b, alpha))

                    self._transition_cache[cache_key] = (strip_surf, rect)
                    self._offscreen.blit(strip_surf, rect)

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
        except Exception as e:
            logging.debug(f"Map hash/cache update failed: {e}")

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
                    except Exception as e:
                        logging.debug(f"Edge color blending failed: {e}")
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
        """Draw thin dark borders between tiles of different terrain types for readability.

        ⚠️ RELEASE MODE: 此方法仅在 debug_mode=True 时被调用 (见 _draw_enhanced_terrain L2510)
        在正式发布版本中，此方法不会被调用，不会产生任何性能开销。

        Debug功能：
        - 绘制不同地形类型之间的边界线
        - 帮助识别地形过渡区域
        - 用于地图编辑和调试

        性能注意：
        - 遍历所有可见tile并检查邻居
        - 仅在debug模式下启用
        - Release构建时完全跳过
        """
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
    
    def _apply_environment_lighting(self, game_map: GameMap, camera: Camera, units: list | None = None) -> None:
        """Apply environment lighting effects to the offscreen buffer.

        Adds:
        - Subtle shadow offset on northeast side of buildings (sun from southwest)
        - Slight warm tint to the overall scene
        - Slightly darker edges (vignette effect)
        - Unit shadow dots (small dark circles beneath each unit)
        """
        if self._offscreen is None:
            return

        screen_w, screen_h = self._offscreen.get_size()

        # 1. Building shadows (northeast offset, sun from southwest)
        self._draw_building_shadows(game_map, camera)

        # 2. Unit shadow dots (sun from southwest → shadow offset to northeast)
        if units:
            self._draw_unit_shadows(units, camera)

        # 3. Warm tint overlay (subtle orange-gold tint)
        try:
            warm_overlay = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
            warm_overlay.fill((255, 220, 160, 12))  # Very subtle warm tint
            self._offscreen.blit(warm_overlay, (0, 0))
        except Exception as e:
            logging.debug(f"Warm tint overlay failed: {e}")

        # 4. Vignette effect (darker edges)
        try:
            vignette = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
            # Draw semi-transparent dark borders that fade toward center
            edge_width = max(30, screen_w // 8)
            edge_height = max(30, screen_h // 8)
            # Top edge
            for i in range(edge_height):
                alpha = int(40 * (1.0 - i / edge_height))
                pygame.draw.line(vignette, (0, 0, 0, alpha), (0, i), (screen_w, i))
            # Bottom edge
            for i in range(edge_height):
                alpha = int(40 * (1.0 - i / edge_height))
                y = screen_h - 1 - i
                pygame.draw.line(vignette, (0, 0, 0, alpha), (0, y), (screen_w, y))
            # Left edge
            for i in range(edge_width):
                alpha = int(40 * (1.0 - i / edge_width))
                pygame.draw.line(vignette, (0, 0, 0, alpha), (i, 0), (i, screen_h))
            # Right edge
            for i in range(edge_width):
                alpha = int(40 * (1.0 - i / edge_width))
                x = screen_w - 1 - i
                pygame.draw.line(vignette, (0, 0, 0, alpha), (x, 0), (x, screen_h))
            self._offscreen.blit(vignette, (0, 0))
        except Exception as e:
            logging.debug(f"Vignette effect failed: {e}")

    def _draw_building_shadows(self, game_map: GameMap, camera: Camera) -> None:
        """Draw shadow strips on the northeast side of buildings (sun from southwest)."""
        if self._offscreen is None:
            return

        from pycc2.domain.value_objects.vec2 import Vec2

        bounds = camera.view_bounds
        start_x = max(0, int(bounds[0].x // self.TILE_SIZE))
        end_x = min(game_map.width, int((bounds[1].x // self.TILE_SIZE) + 2))
        start_y = max(0, int(bounds[0].y // self.TILE_SIZE))
        end_y = min(game_map.height, int((bounds[1].y // self.TILE_SIZE) + 2))

        shadow_offset = max(3, int(self.TILE_SIZE * camera.zoom * 0.12))
        shadow_alpha = 35  # Semi-transparent dark overlay (alpha ~30-40)

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                try:
                    etile = self._get_enhanced_tile(game_map, tx, ty)
                    if etile is not None:
                        terrain_val = etile.base_terrain
                    else:
                        terrain_val = int(game_map.tile_grid[ty, tx])

                    # Only add shadows for building tiles (4, 5)
                    if terrain_val not in (4, 5):
                        continue

                    world_x = tx * self.TILE_SIZE
                    world_y = ty * self.TILE_SIZE
                    sp = camera.world_to_screen(Vec2(world_x, world_y))
                    sx, sy = int(sp[0]), int(sp[1])
                    tile_screen_size = int(self.TILE_SIZE * camera.zoom)

                    # Shadow on northeast side (offset left and up — sun from southwest)
                    # Vertical shadow strip on the left side
                    shadow_surf = pygame.Surface(
                        (shadow_offset, tile_screen_size + shadow_offset),
                        pygame.SRCALPHA,
                    )
                    shadow_surf.fill((0, 0, 0, shadow_alpha))
                    self._offscreen.blit(
                        shadow_surf,
                        (sx - shadow_offset, sy - shadow_offset),
                    )

                    # Horizontal shadow strip on the top side
                    shadow_surf2 = pygame.Surface(
                        (tile_screen_size + shadow_offset, shadow_offset),
                        pygame.SRCALPHA,
                    )
                    shadow_surf2.fill((0, 0, 0, shadow_alpha))
                    self._offscreen.blit(
                        shadow_surf2,
                        (sx - shadow_offset, sy - shadow_offset),
                    )
                except Exception as e:
                    logging.debug(f"Building shadow draw failed: {e}")
                    continue

    def _draw_unit_shadows(self, units: list, camera: Camera) -> None:
        """Draw small shadow dots beneath each alive unit (sun from southwest → shadow to northeast)."""
        if self._offscreen is None:
            return

        from pycc2.domain.value_objects.vec2 import Vec2

        shadow_alpha = 35
        # Shadow offset: northeast direction (negative x, negative y in screen coords)
        offset_x = -max(2, int(4 * camera.zoom))
        offset_y = -max(2, int(4 * camera.zoom))

        for unit in units:
            if not unit.is_alive:
                continue
            pos = unit.position.pixel_position
            sp = camera.world_to_screen(pos)
            sx, sy = int(sp[0]) + offset_x, int(sp[1]) + offset_y
            radius = max(3, int(5 * camera.zoom))
            shadow_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.ellipse(
                shadow_surf,
                (0, 0, 0, shadow_alpha),
                (0, radius // 2, radius * 2, radius),
            )
            self._offscreen.blit(shadow_surf, (sx - radius, sy - radius))

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
        except Exception as e:
            logging.debug(f"Brightness adjustment failed: {e}")

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
                        except Exception as e:
                            logging.debug(f"Unit pixel_position conversion failed: {e}")

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
                        except Exception as e:
                            logging.debug(f"Unit tile_position conversion failed: {e}")

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
                except Exception as e:
                    logging.debug(f"Unit label rendering failed: {e}")

                # STEP 6: Selection indicator (VERY OBVIOUS when selected)
                is_selected = selected_unit_ids and unit.id in selected_unit_ids
                if is_selected:
                    # Pulsing yellow ring (large and obvious)
                    pulse = abs(math.sin(pygame.time.get_ticks() * 0.008)) * 8
                    select_radius = radius + 8 + int(pulse)

                    # Outer glow ring
                    pygame.draw.circle(self._offscreen, (255, 255, 0), (cx, cy), select_radius, 4)
                    pygame.draw.circle(self._offscreen, (255, 200, 0), (cx, cy), select_radius - 3, 2)

                # STEP 7: Damage visual effects (smoke/fire for damaged units)
                if hasattr(unit, 'is_damaged') and unit.is_damaged:
                    self._draw_damage_vfx(unit, cx, cy)

            except Exception as e:
                # CRITICAL: NEVER crash on a single unit - just skip it
                print(f"[WARN] Failed to render unit {idx}: {e}")
                continue

    def _draw_damage_vfx(self, unit: Unit, cx: int, cy: int) -> None:
        """STEP A-2: Render damage visual effects (smoke/fire) for damaged units.

        Based on unit.damage_state:
        - undamaged: No effects
        - light: Light gray smoke wisps (2-3 particles)
        - moderate: Thicker smoke (4-5 particles)
        - heavy: Thick smoke + orange fire glow (6+ particles)
        destroyed: Intense fire + thick black smoke
        """
        if not hasattr(unit, 'damage_state'):
            return

        state = unit.damage_state
        if state == "undamaged":
            return

        # Ensure VFX particles are generated
        if hasattr(unit, 'update_damage_vfx'):
            if not getattr(unit, '_smoke_particles', None):
                unit.update_damage_vfx()

        # Draw smoke particles
        smoke_particles = getattr(unit, '_smoke_particles', [])
        for particle in smoke_particles[:8]:  # Limit to 8 for performance
            px = cx + particle.get('x', 0)
            py = cy + particle.get('y', 0)
            alpha = particle.get('alpha', 100)
            size = particle.get('size', 3)

            # Smoke color: gray with transparency
            smoke_color = (120, 120, 120)

            # Create temporary surface for alpha blending
            smoke_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(smoke_surf, (*smoke_color, alpha), (size, size), size)
            self._offscreen.blit(smoke_surf, (px - size, py - size))

        # Draw fire particles (for heavy/destroyed)
        fire_particles = getattr(unit, '_fire_particles', [])
        for particle in fire_particles[:6]:  # Limit to 6 for performance
            px = cx + particle.get('x', 0)
            py = cy + particle.get('y', 0)
            color = particle.get('color', (220, 120, 20))
            size = particle.get('size', 3)

            # Fire glow effect (larger semi-transparent circle behind)
            glow_size = size + 2
            glow_surf = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*color, 80), (glow_size, glow_size), glow_size)
            self._offscreen.blit(glow_surf, (px - glow_size, py - glow_size))

            # Fire core (bright center)
            bright_color = tuple(min(255, c + 40) for c in color)
            core_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(core_surf, (*bright_color, 200), (size, size), size // 2 + 1)
            self._offscreen.blit(core_surf, (px - size, py - size))

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

    def _render_building_shadows(self, game_map: GameMap, camera: Camera) -> None:
        """Render SE-direction shadows for all buildings."""
        if self._offscreen is None or self._shadow_renderer is None:
            return

        try:
            # Iterate through map tiles to find buildings
            # FIXED: Use game_map.tile_grid[y, x] which returns integer terrain type
            # TerrainType: 4=BUILDING_ENTERABLE, 5=BUILDING_SOLID
            buildings_found = 0
            for y in range(game_map.height):
                for x in range(game_map.width):
                    # Get terrain type as integer from tile_grid
                    terrain_int = int(game_map.tile_grid[y, x])

                    # Check if this is a building tile (4 or 5)
                    has_building = terrain_int in (4, 5)  # BUILDING_ENTERABLE or BUILDING_SOLID

                    if has_building:
                        # Convert tile position to screen coordinates
                        from pycc2.domain.value_objects.vec2 import Vec2
                        world_pos = Vec2(x * self.TILE_SIZE, y * self.TILE_SIZE)
                        screen_pos = camera.world_to_screen(world_pos)
                        sx, sy = int(screen_pos[0]), int(screen_pos[1])

                        # Render building shadow (offset southeast)
                        self._shadow_renderer.render_building_shadow(
                            self._offscreen,
                            sx, sy,
                            self.TILE_SIZE,  # Building width ≈ tile size
                            self.TILE_SIZE // 2  # Approximate building height
                        )
                        buildings_found += 1

            if buildings_found > 0:
                logger.debug(f"Rendered {buildings_found} building shadows")
        except Exception as e:
            logger.warning(f"Failed to render building shadows: {e}")

    def _render_tree_shadows(self, game_map: GameMap, camera: Camera) -> None:
        """Render SE-direction shadows for trees/vegetation."""
        if self._offscreen is None or self._shadow_renderer is None:
            return

        try:
            # Iterate through map tiles to find trees
            # FIXED: Use game_map.tile_grid[y, x] which returns integer terrain type
            # TerrainType: 3=WOODS, 7=HEDGE
            trees_found = 0
            for y in range(game_map.height):
                for x in range(game_map.width):
                    # Get terrain type as integer from tile_grid
                    terrain_int = int(game_map.tile_grid[y, x])

                    # Check if this is a tree/vegetation tile (3 or 7)
                    is_tree = terrain_int in (3, 7)  # WOODS or HEDGE

                    if is_tree:
                        # Convert tile position to screen coordinates
                        from pycc2.domain.value_objects.vec2 import Vec2
                        world_pos = Vec2(x * self.TILE_SIZE, y * self.TILE_SIZE)
                        screen_pos = camera.world_to_screen(world_pos)
                        sx, sy = int(screen_pos[0]), int(screen_pos[1])

                        # Determine tree size based on terrain type
                        tree_size = "medium"
                        if terrain_int == 3:  # WOODS - larger forest areas
                            tree_size = "large"
                        elif terrain_int == 7:  # HEDGE - smaller individual hedges
                            tree_size = "small"

                        # Render tree shadow
                        self._shadow_renderer.render_tree_shadow(
                            self._offscreen,
                            sx, sy,
                            tree_size
                        )
                        trees_found += 1

            if trees_found > 0:
                logger.debug(f"Rendered {trees_found} tree shadows")
        except Exception as e:
            logger.warning(f"Failed to render tree shadows: {e}")

    def _render_unit_shadows(self, units: list[Unit], camera: Camera) -> None:
        """Render SE-direction shadows for all units and vehicles."""
        if self._offscreen is None or self._shadow_renderer is None:
            return

        if len(units) == 0:
            return

        try:
            for unit in units:
                # Get unit position with defensive coding
                cx, cy = None, None
                unit_w, unit_h = 16, 16  # Default unit size

                # Try to get pixel position
                if hasattr(unit, 'position') and unit.position is not None:
                    if hasattr(unit.position, 'pixel_position'):
                        try:
                            pos = camera.world_to_screen(unit.position.pixel_position)
                            cx, cy = int(pos[0]), int(pos[1])
                        except Exception:
                            pass

                    # Fallback to tile position
                    if (cx is None or cy is None) and hasattr(unit.position, 'tile_x'):
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

                if cx is None or cy is None:
                    continue

                # Determine unit type and size
                unit_type = getattr(unit, 'unit_type', 'infantry')
                unit_type_str = str(unit_type).lower()

                # Check if unit is hidden/sneaking
                is_hidden = getattr(unit, 'is_hidden', False) or \
                           getattr(unit, 'is_sneaking', False)

                # Detect vehicle vs infantry by type name or size
                is_vehicle = any(v in unit_type_str for v in 
                               ['tank', 'vehicle', 'halftrack', 'jeep', 'truck'])

                if is_vehicle:
                    # Get vehicle dimensions
                    unit_w = getattr(unit, 'width', 24) or 24
                    unit_h = getattr(unit, 'height', 16) or 16
                    
                    # Render vehicle shadow
                    self._shadow_renderer.render_vehicle_shadow(
                        self._offscreen,
                        cx, cy,
                        unit_w, unit_h,
                        is_hidden=is_hidden
                    )
                else:
                    # Render infantry shadow
                    self._shadow_renderer.render_unit_shadow(
                        self._offscreen,
                        cx, cy,
                        unit_type=unit_type_str,
                        is_hidden=is_hidden
                    )

        except Exception as e:
            logger.warning(f"Failed to render unit shadows: {e}")

    def _debug_render_shadow_bounds(self, game_map: GameMap, camera: Camera) -> None:
        """Draw red rectangles showing where shadows WOULD be rendered (debug visualization).

        This helps verify shadow positions without relying on subtle alpha.
        Call this from render() when debug_mode=True to see shadow placement.
        """
        if self._offscreen is None:
            return

        import pygame as pg

        try:
            # Debug colors for different shadow types
            BUILDING_DEBUG_COLOR = (255, 0, 0)      # Red for buildings
            TREE_DEBUG_COLOR = (0, 255, 0)           # Green for trees
            UNIT_DEBUG_COLOR = (0, 0, 255)           # Blue for units

            # Draw building shadow bounds
            for y in range(game_map.height):
                for x in range(game_map.width):
                    tile = game_map.get_tile(x, y)
                    if tile is None:
                        continue

                    # Same detection logic as _render_building_shadows
                    has_building = (
                        hasattr(tile, 'building') and tile.building is not None
                    ) or (
                        hasattr(tile, 'terrain_type') and
                        str(tile.terrain_type).lower() in ['building', 'house', 'barn', 'church']
                    )

                    if not has_building:
                        try:
                            tt = getattr(tile, 'terrain_type', None)
                            if tt is not None:
                                tt_val = int(tt) if isinstance(tt, (int, float)) else -1
                                if tt_val >= 20:
                                    has_building = True
                        except (ValueError, TypeError):
                            pass

                    if not has_building:
                        tile_name = str(getattr(tile, 'name', '')).lower()
                        if any(w in tile_name for w in ['build', 'house', 'church', 'barn', 'factory']):
                            has_building = True

                    if has_building:
                        world_pos = (x * self.TILE_SIZE, y * self.TILE_SIZE)
                        screen_pos = camera.world_to_screen(world_pos)
                        sx, sy = int(screen_pos[0]), int(screen_pos[1])

                        # Draw red rectangle where building shadow would appear
                        shadow_rect = pg.Rect(sx + 6, sy + self.TILE_SIZE // 2 + 3,
                                             max(24, int(self.TILE_SIZE * 0.9)), 6)
                        pg.draw.rect(self._offscreen, BUILDING_DEBUG_COLOR, shadow_rect, 2)

            # Draw tree shadow bounds
            for y in range(game_map.height):
                for x in range(game_map.width):
                    tile = game_map.get_tile(x, y)
                    if tile is None:
                        continue

                    terrain_str = str(getattr(tile, 'terrain_type', '')).lower()
                    is_tree = any(t in terrain_str for t in ['tree', 'forest', 'woods', 'hedgerow', 'orchard'])

                    if not is_tree:
                        try:
                            tt = getattr(tile, 'terrain_type', None)
                            if tt is not None:
                                tt_val = int(tt) if isinstance(tt, (int, float)) else -1
                                if 3 <= tt_val <= 7:
                                    is_tree = True
                        except (ValueError, TypeError):
                            pass

                    if not is_tree:
                        tile_name = str(getattr(tile, 'name', '')).lower()
                        if any(w in tile_name for w in ['tree', 'forest', 'wood', 'hedge', 'bush', 'orchard']):
                            is_tree = True

                    if is_tree:
                        world_pos = (x * self.TILE_SIZE, y * self.TILE_SIZE)
                        screen_pos = camera.world_to_screen(world_pos)
                        sx, sy = int(screen_pos[0]), int(screen_pos[1])

                        # Draw green rectangle where tree shadow would appear
                        shadow_rect = pg.Rect(sx + 5, sy + 3, 18, 8)
                        pg.draw.rect(self._offscreen, TREE_DEBUG_COLOR, shadow_rect, 2)

            logger.debug("Debug shadow bounds rendered (red=buildings, green=trees)")

        except Exception as e:
            logger.warning(f"Failed to debug render shadow bounds: {e}")

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

        # Get attack line system (injected via constructor - P0-2 Fix)
        import pygame as pg
        from pycc2.presentation.input.attack_line_system import AttackLineSystem, AttackLineStatus

        attack_line = self._attack_line_system
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

            # Red solid line for confirmed attacks (CC2 uses solid red)
            pg.draw.line(
                self._offscreen,
                (255, 50, 50),
                (int(source_screen[0]), int(source_screen[1])),
                (int(target_screen[0]), int(target_screen[1])),
                2,
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
        """Draw grid overlay for debugging.

        ⚠️ RELEASE MODE: 此方法仅在 debug_mode=True 时被调用 (见 render() L2246)
        在正式发布版本中，此方法不会被调用，不会产生任何性能开销。

        Debug功能：
        - 绘制地形网格线（灰色）
        - 显示tile边界
        - 用于开发调试和地图编辑

        性能注意：
        - 每帧绘制O(width*height)条线段
        - 仅在debug模式下启用
        - Release构建时完全跳过
        """
        if self._screen is None:
            return
        
        bounds = camera.view_bounds
        grid_color = (60, 80, 40, 80)  # Dim grey-green (was bright grey 100,100,100)
        
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
