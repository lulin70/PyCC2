"""
Decoration Renderer Module for CC2-Style Maps

Handles rendering of map decorations including:
- Bushes, Trees, Rocks, Rubble, Craters, Trenches
- Sandbag walls, Barbed wire, Vehicle wreckage
- CC2-specific decorations (crater clusters, debris fields, burning wreckage)

Dependencies are injected via RenderContext.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pygame

from pycc2.presentation.rendering.render_context import RenderContext

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.presentation.rendering.camera import Camera


class DecorationRenderer:
    """Handles all decoration rendering on the map.

    Uses SpriteGenerator for programmatic sprite creation.
    Manages decoration placement and caching.
    """

    def __init__(self, ctx: RenderContext):
        self._ctx = ctx
        from pycc2.presentation.rendering.sprite_generator import SpriteGenerator
        self._sprite_gen = SpriteGenerator

    def draw_decorations(self, game_map: GameMap, camera: Camera) -> None:
        if self._ctx.draw_decorations:
            self._ctx.draw_decorations(game_map, camera)

    def get_sprite(self, deco_type_name: str, variant: int = 0) -> pygame.Surface:
        return self._sprite_gen.generate_sprite(deco_type_name, variant)

    def cache_sprite(self, deco_type_name: str, variant: int = 0) -> pygame.Surface:
        cache_key = f"{deco_type_name}_{variant}"

        if self._ctx.sprite_cache:
            if cache_key not in self._ctx.sprite_cache:
                self._ctx.sprite_cache[cache_key] = self.get_sprite(deco_type_name, variant)
            return self._ctx.sprite_cache[cache_key]
        else:
            return self.get_sprite(deco_type_name, variant)
