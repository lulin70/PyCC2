"""
Decoration Renderer Module for CC2-Style Maps

Handles rendering of map decorations including:
- Bushes (small, dense)
- Trees (oak, pine)
- Rocks (large, small)
- Rubble piles
- Craters (small, large)
- Trenches
- Sandbag walls and barricades
- Barbed wire
- Vehicle/plane wreckage
- Camouflage nets
- CC2-specific decorations (crater clusters, debris fields, burning wreckage)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pygame

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.presentation.rendering.camera import Camera


class DecorationRenderer:
    """Handles all decoration rendering on the map.

    Uses SpriteGenerator for programmatic sprite creation.
    Manages decoration placement and caching.
    """

    def __init__(self, parent_renderer):
        """Initialize with reference to parent EnhancedRenderer."""
        self._parent = parent_renderer
        from pycc2.presentation.rendering.sprite_generator import SpriteGenerator
        self._sprite_gen = SpriteGenerator

    def draw_decorations(self, game_map: GameMap, camera: Camera) -> None:
        """Main decoration drawing entry point.

        Iterates through map decorations and renders each one
        at the appropriate screen position.
        """
        if hasattr(self._parent, '_draw_decorations'):
            self._parent._draw_decorations(game_map, camera)

    def get_sprite(self, deco_type_name: str, variant: int = 0) -> pygame.Surface:
        """Get or generate a sprite for a decoration type.

        Args:
            deco_type_name: Type identifier (e.g., 'BUSH_SMALL', 'TREE_OAK')
            variant: Visual variation index

        Returns:
            Pygame Surface with the rendered sprite
        """
        return self._sprite_gen.generate_sprite(deco_type_name, variant)

    def cache_sprite(self, deco_type_name: str, variant: int = 0) -> pygame.Surface:
        """Get cached sprite or generate and cache it."""
        cache_key = f"{deco_type_name}_{variant}"

        if hasattr(self._parent, '_sprite_cache'):
            if cache_key not in self._parent._sprite_cache:
                self._parent._sprite_cache[cache_key] = self.get_sprite(deco_type_name, variant)
            return self._parent._sprite_cache[cache_key]
        else:
            return self.get_sprite(deco_type_name, variant)
