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


# CC2 Authentic Terrain Palette (from screenshot pixel analysis)
# ============================================================
# v0.5.2 P1: Corrected based on pixel-level analysis of 13 CC2 original screenshots.
# Previous v0.3 values were ~35% TOO BRIGHT (not too dark as formerly commented).
# CC2 actual dominant colors extracted from assets/CC2-snapshot/:
#   grass dominant: RGB(64,96,32)  grass dark: RGB(48,80,16)
#   olive shadow:   RGB(48,48,0)   dark soil:  RGB(32,32,0)
CC2_TERRAIN_PALETTE = {
    # Grass — CC2 screenshot actual dominant colors
    "grass_base": (64, 96, 32),  # CC2 dominant military green #406020 (was 94,153,48 — too bright)
    "grass_light": (64, 112, 32),  # CC2 sunlit green #407020 (was 112,175,58 — too bright)
    "grass_dark": (48, 80, 16),  # CC2 shadow green #305010 (was 72,120,36 — too bright)
    "grass_dry": (96, 96, 32),  # CC2 dry olive #606020 (was 156,145,68 — too bright)
    "grass_shadow": (32, 64, 0),  # CC2 deep shadow #204000 (NEW — was missing)
    "olive_shadow": (48, 48, 0),  # CC2 dark olive transition #303000 (NEW — was missing)
    # Dirt
    "dirt_base": (96, 64, 32),  # CC2 dirt #604020 (was 162,128,68 — too bright)
    "dirt_dark": (64, 48, 16),  # CC2 dark soil #403010 (was 128,100,52 — too bright)
    "dirt_light": (128, 96, 48),  # CC2 light dirt #806030 (was 186,152,86 — too bright)
    # Road
    "road_base": (80, 72, 64),  # CC2 gravel road #504840 (was 128,118,102 — too bright)
    "road_stone": (96, 96, 96),  # CC2 cobblestone #606060 (was 156,148,138 — too bright)
    "road_dark": (48, 48, 48),  # CC2 worn road #303030 (was 102,94,82 — too bright)
    # Water
    "water_base": (48, 88, 140),  # CC2 river blue #30588C (was 56,112,186 — slightly bright)
    "water_light": (72, 128, 168),  # CC2 bright water #4880A8 (was 92,160,226 — too bright)
    "water_dark": (32, 64, 100),  # CC2 deep water #204064 (was 38,82,148 — slightly bright)
    "water_foam": (180, 210, 230),  # CC2 foam #B4D2E6 (was 206,238,255 — too bright)
    # Hedgerow (already close to CC2)
    "hedgerow_base": (38, 85, 28),  # Normandy hedge #26551C
    "hedgerow_light": (58, 105, 40),  # Hedge highlight #3A6928
    "hedgerow_dark": (22, 62, 16),  # Hedge shadow #163E10
    # Terrain features
    "embankment": (64, 56, 36),  # CC2 dirt embankment #403824 (was 78,66,44 — slightly bright)
    "wall_base": (90, 90, 90),  # CC2 stone wall #5A5A5A (was 130,130,130 — too bright)
    "wall_dark": (64, 64, 64),  # CC2 dark stone #404040 (was 100,100,100 — too bright)
    "crater_center": (72, 60, 32),  # CC2 crater bottom #483C20 (was 104,86,46 — slightly bright)
    "crater_rim": (104, 84, 48),  # CC2 crater edge #685430 (was 142,114,64 — slightly bright)
    "trench_main": (64, 44, 24),  # CC2 trench floor #402C18 (was 78,54,32 — slightly bright)
    "trench_embankment": (96, 76, 48),  # CC2 trench wall #604C30 (was 122,98,64 — slightly bright)
    "building_ground": (112, 104, 88),  # CC2 building floor #706858 (was 160,148,126 — too bright)
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
        """Initialize the TerrainTileCache."""
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
