"""
Terrain Renderer Module for CC2-Style Maps

Handles all terrain rendering including:
- Tile drawing and texturing
- Autotile edge smoothing
- Building roofs, interiors, and floor numbers
- Terrain transitions and borders
- VL (Victory Location) flags
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
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.domain.systems.enhanced_tile import EnhancedTile


class TerrainRenderer:
    """Handles all terrain-related rendering operations.

    This class is responsible for:
    - Drawing terrain tiles with CC2-style textures
    - Managing autotile edge transitions
    - Rendering buildings (roofs, interiors, floor numbers)
    - Drawing VL flags and terrain decorations
    """

    def __init__(self, parent_renderer):
        """Initialize with reference to parent EnhancedRenderer for shared state."""
        self._parent = parent_renderer

    def draw_terrain(self, game_map: GameMap, camera: Camera, debug_mode: bool = False) -> None:
        """Main terrain drawing entry point.

        Delegates to appropriate method based on renderer configuration.
        """
        if hasattr(self._parent, '_draw_enhanced_terrain'):
            self._parent._draw_enhanced_terrain(game_map, camera, debug_mode)
        else:
            self._parent._draw_simple_terrain(game_map, camera)

    def get_cached_texture(self, terrain_id: int, variation: int = 0):
        """Get cached texture for a terrain type."""
        return self._parent._get_cached_texture(terrain_id, variation)

    def generate_cc2_style_tile(self, terrain_type: int, tile_x: int = 0,
                                tile_y: int = 0, autotile_mask: int = 0):
        """Generate a CC2-style textured tile."""
        return self._parent._generate_cc2_style_tile(terrain_type, tile_x, tile_y, autotile_mask)

    def apply_edge_smoothing(self, surface: pygame.Surface,
                              terrain_type: int, autotile_mask: int) -> None:
        """Apply edge smoothing to a tile for autotile continuity."""
        if hasattr(self._parent, '_apply_terrain_edge_smoothing'):
            self._parent._apply_terrain_edge_smoothing(surface, terrain_type, autotile_mask)
