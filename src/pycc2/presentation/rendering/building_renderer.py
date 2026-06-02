"""
Building Renderer Sub-Module for CC2-Style Maps

Extracted from EnhancedRenderer via DELEGATE PATTERN.
Handles building-specific rendering operations:
- Building roofs (CC2 top-down view)
- Building interiors (auto-switch when units inside)
- Building floor numbers on roof

Dependencies are injected via parent_renderer reference.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pygame

from pycc2.presentation.rendering.cc2_building_renderer import (
    DamageLevel,
    floors_to_building_type,
    render_cc2_building,
    should_show_interior,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.presentation.rendering.camera import Camera


class BuildingRenderer:
    """Handles all building-related rendering operations (delegate pattern).

    Manages:
    - CC2-style top-down building roofs
    - Interior view overlay when units are inside
    - Floor count numbers on building tiles
    """

    MIN_FONT_SIZE = 10

    def __init__(self, parent_renderer):
        self._parent = parent_renderer

    def draw_building_roofs(self, game_map: GameMap, camera: Camera) -> None:
        if self._parent._offscreen is None:
            return

        tile_size = self._parent.TILE_SIZE
        bounds = camera.view_bounds
        start_x = max(0, int(bounds[0].x // tile_size))
        end_x = min(game_map.width, int((bounds[1].x // tile_size) + 2))
        start_y = max(0, int(bounds[0].y // tile_size))
        end_y = min(game_map.height, int((bounds[1].y // tile_size) + 2))

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                terrain_val = self._parent._get_terrain_at(game_map, tx, ty)
                if terrain_val != 4:
                    continue

                enhanced = game_map.get_enhanced_tile(tx, ty) if hasattr(game_map, 'get_enhanced_tile') else None
                floors = 1
                if enhanced and isinstance(enhanced, dict):
                    floors = int(enhanced.get("building_floors", 1))
                elif enhanced and hasattr(enhanced, 'building_floors'):
                    floors = int(getattr(enhanced, 'building_floors', 1))

                building_type = floors_to_building_type(floors)

                roof_surface = render_cc2_building(
                    building_type=building_type,
                    damage=DamageLevel.INTACT,
                    tile_size=tile_size,
                    interior_mode=False,
                )

                tile_screen_size = int(tile_size * camera.zoom)
                if tile_screen_size != tile_size:
                    tw, th = roof_surface.get_size()
                    target_w = int(tw * camera.zoom)
                    target_h = int(th * camera.zoom)
                    if target_w > 0 and target_h > 0:
                        roof_surface = pygame.transform.scale(
                            roof_surface, (target_w, target_h),
                        )

                from pycc2.domain.value_objects.vec2 import Vec2
                world_x = tx * tile_size
                world_y = ty * tile_size
                screen_pos = camera.world_to_screen(Vec2(world_x, world_y))

                self._parent._offscreen.blit(roof_surface, (int(screen_pos[0]), int(screen_pos[1])))

    def draw_building_interiors(
        self, game_map: GameMap, units: list[Unit], camera: Camera,
    ) -> None:
        if self._parent._screen is None or self._parent._offscreen is None:
            return
        if not units:
            return

        tile_size = self._parent.TILE_SIZE
        bounds = camera.view_bounds
        start_x = max(0, int(bounds[0].x // tile_size))
        end_x = min(game_map.width, int((bounds[1].x // tile_size) + 2))
        start_y = max(0, int(bounds[0].y // tile_size))
        end_y = min(game_map.height, int((bounds[1].y // tile_size) + 2))

        tile_screen_size = int(tile_size * camera.zoom)

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                terrain_val = self._parent._get_terrain_at(game_map, tx, ty)
                if terrain_val != 4:
                    continue

                if not should_show_interior((tx, ty), units, tile_size):
                    continue

                enhanced = game_map.get_enhanced_tile(tx, ty) if hasattr(game_map, 'get_enhanced_tile') else None
                floors = 1
                if enhanced and isinstance(enhanced, dict):
                    floors = int(enhanced.get("building_floors", 1))
                elif enhanced and hasattr(enhanced, 'building_floors'):
                    floors = int(getattr(enhanced, 'building_floors', 1))

                building_type = floors_to_building_type(floors)

                interior_surface = render_cc2_building(
                    building_type=building_type,
                    damage=DamageLevel.INTACT,
                    tile_size=tile_size,
                    interior_mode=True,
                    occupant_positions=[],
                )

                if tile_screen_size != tile_size:
                    tw, th = interior_surface.get_size()
                    target_w = int(tw * camera.zoom)
                    target_h = int(th * camera.zoom)
                    if target_w > 0 and target_h > 0:
                        interior_surface = pygame.transform.scale(
                            interior_surface, (target_w, target_h),
                        )

                from pycc2.domain.value_objects.vec2 import Vec2
                world_x = tx * tile_size
                world_y = ty * tile_size
                screen_pos = camera.world_to_screen(Vec2(world_x, world_y))

                self._parent._offscreen.blit(interior_surface, (int(screen_pos[0]), int(screen_pos[1])))

    def draw_building_floor_numbers(
        self, game_map: GameMap, camera: Camera,
    ) -> None:
        if self._parent._screen is None or self._parent._offscreen is None:
            return

        tile_size = self._parent.TILE_SIZE
        bounds = camera.view_bounds
        start_x = max(0, int(bounds[0].x // tile_size))
        end_x = min(game_map.width, int((bounds[1].x // tile_size) + 2))
        start_y = max(0, int(bounds[0].y // tile_size))
        end_y = min(game_map.height, int((bounds[1].y // tile_size) + 2))

        tile_screen_size = int(tile_size * camera.zoom)

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                terrain_val = self._parent._get_terrain_at(game_map, tx, ty)
                if terrain_val != 4:
                    continue

                enhanced = game_map.get_enhanced_tile(tx, ty) if hasattr(game_map, 'get_enhanced_tile') else None
                floors = None
                if enhanced and isinstance(enhanced, dict):
                    floors = enhanced.get("building_floors")
                elif enhanced and hasattr(enhanced, 'building_floors'):
                    floors = getattr(enhanced, 'building_floors', None)

                if floors is None or int(floors) <= 1:
                    continue

                from pycc2.domain.value_objects.vec2 import Vec2
                world_x = tx * tile_size
                world_y = ty * tile_size
                screen_pos = camera.world_to_screen(Vec2(world_x, world_y))

                font_size = max(self.MIN_FONT_SIZE, tile_screen_size // 3)
                font = pygame.font.SysFont("arial", font_size, bold=True)
                text = font.render(str(int(floors)), True, (255, 215, 0))
                text_rect = text.get_rect(
                    center=(int(screen_pos[0]) + tile_screen_size // 2,
                            int(screen_pos[1]) + tile_screen_size // 2),
                )
                self._parent._offscreen.blit(text, text_rect)
