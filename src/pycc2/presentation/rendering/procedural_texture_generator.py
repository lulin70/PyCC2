"""CC2-authentic procedural texture generator.

Extracted from enhanced_renderer.py in v0.3.6 refactoring.
Generates 48×48 pixel art terrain tiles matching original Close Combat 2 visuals.

Dependencies:
- pygame (Surface operations, surfarray)
- random (per-tile variation)
- PaletteGenerator (color palette generation)
- CC2_TERRAIN_PALETTE, TERRAIN_PALETTE_MAP (terrain color constants)

Texture functions are split into focused sub-modules:
- texture_basic: open ground, roads, grass, fallback
- texture_water_bridge: water, shallow, bridge
- texture_vegetation: woods, hedge, rough
- texture_structures: buildings, wall, crater, trench
"""

from __future__ import annotations

import pygame

from ..visual_config import DEFAULT_VISUAL_CONFIG
from .palette_generator import PaletteGenerator
from .texture_basic import (
    _texture_default,
    _texture_grass,
    _texture_open,
    _texture_road,
)
from .texture_structures import (
    _texture_building_enterable,
    _texture_building_solid,
    _texture_crater,
    _texture_trench,
    _texture_wall,
)
from .texture_vegetation import (
    _texture_hedge,
    _texture_rough,
    _texture_woods,
)
from .texture_water_bridge import (
    _texture_bridge,
    _texture_shallow,
    _texture_water,
)


class ProceduralTextureGenerator:
    """Generates CC2-authentic pixel art textures procedurally.

    Creates 48×48 tile appearances matching original Close Combat 2 visuals.
    Each terrain type generates a visually distinct and recognizable tile
    with subtle per-tile variation to avoid repetitive patterns.
    """

    # V-01 (Wave C3b): TILE_SIZE migrated to DEFAULT_VISUAL_CONFIG for theme hot-reload.
    TILE_SIZE = DEFAULT_VISUAL_CONFIG.dimensions.TILE_SIZE  # CC2 authentic: 48×48 pixel tiles

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
            0: _texture_open,
            1: _texture_road,
            2: _texture_grass,
            3: _texture_woods,
            4: _texture_building_enterable,
            5: _texture_building_solid,
            6: _texture_water,
            7: _texture_hedge,
            8: _texture_wall,
            9: _texture_rough,
            10: _texture_shallow,
            11: _texture_bridge,
            12: _texture_crater,
            13: _texture_trench,
        }

        func = texture_funcs.get(terrain_id, _texture_default)
        func(surface, terrain_id, variation, palette, bitmask)

        return surface


__all__ = ["ProceduralTextureGenerator"]
