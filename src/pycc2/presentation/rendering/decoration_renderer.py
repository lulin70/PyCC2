"""Decoration Renderer Module for CC2-Style Maps

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
        """Draw decoration sprites on map."""
        if self._ctx.offscreen is None:
            return

        bounds = camera.view_bounds
        tile_size = self._ctx.tile_size
        start_x = max(0, int(bounds[0].x // tile_size))
        end_x = min(game_map.width, int((bounds[1].x // tile_size) + 2))
        start_y = max(0, int(bounds[0].y // tile_size))
        end_y = min(game_map.height, int((bounds[1].y // tile_size) + 2))

        get_enhanced_tile = self._ctx.get_enhanced_tile
        if get_enhanced_tile is None:
            return

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                enhanced_tile = get_enhanced_tile(game_map, tx, ty)

                if not enhanced_tile or not enhanced_tile.decorations:
                    continue

                for deco in enhanced_tile.decorations:
                    sprite = self.cache_sprite(deco.decoration_type.name, deco.variant)

                    # Calculate position with sub-tile offset
                    base_x = tx * tile_size
                    base_y = ty * tile_size

                    offset_x = int(deco.offset_x * tile_size)
                    offset_y = int(deco.offset_y * tile_size)

                    world_x = base_x + offset_x
                    world_y = base_y + offset_y

                    from pycc2.domain.value_objects.vec2 import Vec2

                    screen_pos = camera.world_to_screen(Vec2(world_x, world_y))

                    # Scale sprite
                    sprite_size = int(tile_size * camera.zoom * deco.scale)
                    if sprite_size != 32:
                        sprite = pygame.transform.scale(sprite, (sprite_size, sprite_size))

                    # Rotate if needed
                    if deco.rotation != 0:
                        sprite = pygame.transform.rotate(sprite, -deco.rotation)

                    rect = sprite.get_rect()
                    rect.center = (int(screen_pos[0]), int(screen_pos[1]))
                    self._ctx.offscreen.blit(sprite, rect)

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
