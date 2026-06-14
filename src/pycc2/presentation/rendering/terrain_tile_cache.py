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
    'grass_base':      (65, 106, 30),
    'grass_light':     (77, 121, 37),
    'grass_dark':      (49, 85, 20),
    'grass_dry':       (117, 110, 51),
    'dirt_base':       (118, 93, 50),
    'dirt_dark':       (94, 72, 38),
    'dirt_light':      (136, 110, 64),
    'road_base':       (91, 84, 71),
    'road_stone':      (111, 106, 98),
    'road_dark':       (72, 66, 58),
    'water_base':      (41, 82, 136),
    'water_light':     (68, 119, 170),
    'water_dark':      (27, 61, 110),
    'water_foam':      (153, 178, 195),
    'hedgerow_base':   (27, 61, 20),
    'hedgerow_light':  (41, 75, 29),
    'hedgerow_dark':   (15, 44, 12),
    'embankment':      (58, 49, 32),
    'wall_base':       (95, 95, 95),
    'wall_dark':       (72, 72, 72),
    'crater_center':   (76, 63, 34),
    'crater_rim':      (104, 83, 48),
    'trench_main':     (58, 40, 24),
    'trench_embankment': (90, 72, 48),
    'building_ground': (119, 110, 94),
}

# Map terrain IDs to their base palette keys
TERRAIN_PALETTE_MAP = {
    0: 'grass_base',
    1: 'road_base',
    2: 'grass_dark',
    3: 'hedgerow_base',
    4: 'building_ground',
    5: 'wall_base',
    6: 'water_base',
    7: 'hedgerow_base',
    8: 'wall_base',
    9: 'dirt_base',
    10: 'water_light',
    11: 'dirt_light',
    12: 'crater_center',
    13: 'trench_main',
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
            renderer, terrain_type, autotile_mask, variation,
            height, tile_screen_size, enhanced_tile, tile_x, tile_y,
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
                texture = pygame.transform.scale(
                    texture, (tile_screen_size, tile_screen_size)
                )

            if autotile_mask > 0:
                self._apply_edge_smoothing(texture, terrain_type, autotile_mask)

            return texture
        except (ValueError, pygame.error) as e:
            logging.debug(f"Tile texture creation failed: {e}")
            return None

    def _apply_edge_smoothing(
        self, surface: pygame.Surface, terrain_type: int, mask: int
    ) -> None:
        """Apply smooth edge transitions based on autotile bitmask.

        Bitmask convention: N=1, E=2, S=4, W=8
        """
        tile_size = surface.get_width()
        blend_width = max(2, min(4, tile_size // 12))

        palette_key = TERRAIN_PALETTE_MAP.get(terrain_type, 'grass_base')
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
