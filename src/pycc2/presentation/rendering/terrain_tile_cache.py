"""Terrain tile cache with LRU eviction and autotile edge smoothing.

Extracted from enhanced_renderer.py in v0.3.5 refactoring.
Provides pre-computed terrain tile caching for smooth rendering performance.

Dependencies:
- pygame (Surface operations)
- EnhancedRenderer (for tile generation callbacks - TYPE_CHECKING only)
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from typing import TYPE_CHECKING, Any

import pygame

if TYPE_CHECKING:
    from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer


# CC2 Authentic Terrain Palette (from screenshot analysis)
# ============================================================
CC2_TERRAIN_PALETTE = {
    # CC2 authentic palette — brightened to match original game screenshots
    # Reference: Close Combat 2 (1999) Normandy campaign maps
    # Previous values were ~20% too dark; these match CC2's vibrant outdoor lighting
    "grass_base": (94, 153, 48),       # Bright military green #609930 (was 65,106,30)
    "grass_light": (112, 175, 58),      # Sunlit grass #70AF3A (was 77,121,37)
    "grass_dark": (72, 120, 36),        # Shadow grass #487824 (was 49,85,20)
    "grass_dry": (156, 145, 68),        # Dry summer grass #9C9144 (was 117,110,51)
    "dirt_base": (162, 128, 68),        # Tilled earth #A28044 (was 118,93,50)
    "dirt_dark": (128, 100, 52),        # Dark soil #806434 (was 94,72,38)
    "dirt_light": (186, 152, 86),       # Light dirt #BA9856 (was 136,110,64)
    "road_base": (128, 118, 102),       # Gravel road #807666 (was 91,84,71)
    "road_stone": (156, 148, 138),      # Cobblestone #9C948A (was 111,106,98)
    "road_dark": (102, 94, 82),         # Worn road #665E52 (was 72,66,58)
    "water_base": (56, 112, 186),       # Deep river blue #3870BA (was 41,82,136)
    "water_light": (92, 160, 226),      # Bright water #5CA0E2 (was 68,119,170)
    "water_dark": (38, 82, 148),        # Deep water #265294 (was 27,61,110)
    "water_foam": (206, 238, 255),      # White foam #CEEEFF (was 153,178,195)
    "hedgerow_base": (38, 85, 28),      # Normandy hedge #26551C (was 27,61,20)
    "hedgerow_light": (58, 105, 40),    # Hedge highlight #3A6928 (was 41,75,29)
    "hedgerow_dark": (22, 62, 16),      # Hedge shadow #163E10 (was 15,44,12)
    "embankment": (78, 66, 44),         # Dirt embankment #4E422C (was 58,49,32)
    "wall_base": (130, 130, 130),       # Stone wall #828282 (was 95,95,95)
    "wall_dark": (100, 100, 100),       # Dark stone #646464 (was 72,72,72)
    "crater_center": (104, 86, 46),     # Crater bottom #68562E (was 76,63,34)
    "crater_rim": (142, 114, 64),       # Crater edge #8E7240 (was 104,83,48)
    "trench_main": (78, 54, 32),        # Trench floor #4E3620 (was 58,40,24)
    "trench_embankment": (122, 98, 64), # Trench wall #7A6240 (was 90,72,48)
    "building_ground": (160, 148, 126), # Building floor #A0947E (was 119,110,94)
}

# Map terrain IDs to their base palette keys
TERRAIN_PALETTE_MAP = {
    0: "grass_base",
    1: "road_base",
    2: "grass_dark",
    3: "hedgerow_base",
    4: "building_ground",
    5: "wall_base",
    6: "water_base",
    7: "hedgerow_base",
    8: "wall_base",
    9: "dirt_base",
    10: "water_light",
    11: "dirt_light",
    12: "crater_center",
    13: "trench_main",
}


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
        self._cache: OrderedDict[tuple, pygame.Surface] = OrderedDict()

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
            self._cache.move_to_end(key)
            return self._cache[key]

        if renderer is None:
            return None

        surface = self._render_tile(
            renderer,
            terrain_type,
            autotile_mask,
            variation,
            height,
            tile_screen_size,
            enhanced_tile,
            tile_x,
            tile_y,
        )
        if surface is not None:
            self._put(key, surface)
        return surface

    def _put(self, key: tuple, surface: pygame.Surface) -> None:
        """Insert into cache with LRU eviction."""
        if key in self._cache:
            self._cache.move_to_end(key)
            self._cache[key] = surface
            return
        if len(self._cache) >= self.MAX_ENTRIES:
            self._cache.popitem(last=False)
        self._cache[key] = surface

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
            if autotile_mask != 0:
                texture = renderer._generate_cc2_style_tile(
                    terrain_type, tile_x, tile_y, autotile_mask
                )
            else:
                texture = renderer._get_cached_texture(terrain_type, variation)

            if texture is None:
                return None

            if height != 0:
                texture = renderer._apply_height_lighting(texture, height)

            if tile_screen_size != self._tile_size:
                texture = pygame.transform.scale(texture, (tile_screen_size, tile_screen_size))

            if autotile_mask > 0:
                self._apply_edge_smoothing(texture, terrain_type, autotile_mask)

            return texture
        except (ValueError, pygame.error) as e:
            logging.debug(f"Tile texture creation failed: {e}")
            return None

    def _apply_edge_smoothing(self, surface: pygame.Surface, terrain_type: int, mask: int) -> None:
        """Apply smooth edge transitions based on autotile bitmask.

        Bitmask convention: N=1, E=2, S=4, W=8
        """
        tile_size = surface.get_width()
        blend_width = max(2, min(4, tile_size // 12))

        palette_key = TERRAIN_PALETTE_MAP.get(terrain_type, "grass_base")
        base_color = CC2_TERRAIN_PALETTE.get(palette_key, (76, 124, 35))
        edge_color = (
            max(0, base_color[0] - 30),
            max(0, base_color[1] - 30),
            max(0, base_color[2] - 30),
        )

        # N (bit 0)
        if not (mask & 1):
            for i in range(blend_width):
                alpha = int(35 * (1 - i / blend_width))
                line_surf = pygame.Surface((tile_size, 1), pygame.SRCALPHA)
                line_surf.fill((*edge_color, alpha))
                surface.blit(line_surf, (0, i))

        # E (bit 1)
        if not (mask & 2):
            for i in range(blend_width):
                alpha = int(35 * (1 - i / blend_width))
                line_surf = pygame.Surface((1, tile_size), pygame.SRCALPHA)
                line_surf.fill((*edge_color, alpha))
                surface.blit(line_surf, (tile_size - 1 - i, 0))

        # S (bit 2)
        if not (mask & 4):
            for i in range(blend_width):
                alpha = int(35 * (1 - i / blend_width))
                line_surf = pygame.Surface((tile_size, 1), pygame.SRCALPHA)
                line_surf.fill((*edge_color, alpha))
                surface.blit(line_surf, (0, tile_size - 1 - i))

        # W (bit 3)
        if not (mask & 8):
            for i in range(blend_width):
                alpha = int(35 * (1 - i / blend_width))
                line_surf = pygame.Surface((1, tile_size), pygame.SRCALPHA)
                line_surf.fill((*edge_color, alpha))
                surface.blit(line_surf, (i, 0))

    def invalidate(self) -> None:
        """Invalidate entire cache (call when map changes)."""
        self._cache.clear()

    def clear(self) -> None:
        """Clear all cached tiles."""
        self._cache.clear()

    @property
    def size(self) -> int:
        """Current number of cached tiles."""
        return len(self._cache)


__all__ = [
    "TerrainTileCache",
    "CC2_TERRAIN_PALETTE",
    "TERRAIN_PALETTE_MAP",
]
