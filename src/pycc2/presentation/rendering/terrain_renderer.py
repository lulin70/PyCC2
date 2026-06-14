"""
Terrain Renderer Sub-Module for CC2-Style Maps

Handles terrain-specific rendering operations:
- Enhanced terrain tile drawing with autotile support
- Terrain transition gradient strips
- Terrain edge smoothing

Dependencies are injected via RenderContext.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pygame

from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.presentation.rendering.autotile_system import (
    detect_building_clusters,
    get_neighbor_bitmap,
    is_autotile_terrain,
)
from pycc2.presentation.rendering.render_context import RenderContext

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.presentation.rendering.camera import Camera


class TerrainRenderer:
    """Handles all terrain-related rendering operations.

    Owns terrain-specific caches:
    - _transition_cache: gradient strips between terrain types
    - _edge_smooth_cache: edge smoothing surfaces
    - _last_map_hash: map change detection for cache invalidation
    """

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

    TRANSITION_STRIP_WIDTH_MIN = 5
    TRANSITION_STRIP_WIDTH_MAX = 7
    EDGE_SMOOTH_WIDTH_MIN = 2
    EDGE_SMOOTH_WIDTH_MAX = 3
    EDGE_SMOOTH_ALPHA_PEAK = 45
    TRANSITION_ALPHA_PEAK = 140

    def __init__(self, ctx: RenderContext):
        self._ctx = ctx
        self._transition_cache: dict[
            tuple[int, int, int, int, str], tuple[pygame.Surface, pygame.Rect]
        ] = {}
        self._edge_smooth_cache: dict[tuple[int, int], pygame.Surface] = {}
        self._edge_smooth_dirty: bool = True
        self._last_map_hash: int = 0

    def draw_enhanced_terrain(
        self, game_map: GameMap, camera: Camera, debug_mode: bool = False
    ) -> None:
        if self._ctx.screen is None:
            return

        if self._ctx.building_clusters is None:
            clusters = detect_building_clusters(game_map)
            self._ctx.update_building_clusters(clusters)

        tile_size = self._ctx.tile_size
        bounds = camera.view_bounds
        start_x = max(0, int(bounds[0].x // tile_size))
        end_x = min(game_map.width, int((bounds[1].x // tile_size) + 2))
        start_y = max(0, int(bounds[0].y // tile_size))
        end_y = min(game_map.height, int((bounds[1].y // tile_size) + 2))

        tile_screen_size = int(tile_size * camera.zoom)

        screen_w, screen_h = self._ctx.offscreen.get_size() if self._ctx.offscreen else (800, 600)
        margin = tile_screen_size

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                world_x = tx * tile_size
                world_y = ty * tile_size
                screen_pos = camera.world_to_screen(Vec2(world_x, world_y))
                sx, sy = int(screen_pos[0]), int(screen_pos[1])

                if (
                    sx + tile_screen_size < -margin
                    or sx > screen_w + margin
                    or sy + tile_screen_size < -margin
                    or sy > screen_h + margin
                ):
                    continue

                enhanced_tile = (
                    self._ctx.get_enhanced_tile(game_map, tx, ty)
                    if self._ctx.get_enhanced_tile
                    else None
                )

                if enhanced_tile:
                    terrain_val = enhanced_tile.base_terrain
                    variation = enhanced_tile.variation
                    height = enhanced_tile.height
                else:
                    terrain_val = int(game_map.tile_grid[ty, tx])
                    variation = 0
                    height = 0

                bitmask = 0
                if is_autotile_terrain(terrain_val):
                    bitmask = get_neighbor_bitmap(game_map, tx, ty, terrain_val)

                texture = None
                if self._ctx.terrain_tile_cache:
                    texture = self._ctx.terrain_tile_cache.get_tile(
                        terrain_type=terrain_val,
                        autotile_mask=bitmask,
                        variation=variation,
                        height=height,
                        tile_screen_size=tile_screen_size,
                        renderer=None,
                        enhanced_tile=enhanced_tile,
                        tile_x=tx,
                        tile_y=ty,
                    )

                if texture is None:
                    if bitmask != 0:
                        cache_key = (terrain_val, variation, bitmask)
                        if (
                            self._ctx.autotile_cache
                            and cache_key not in self._ctx.autotile_cache._cache
                        ):
                            texture = (
                                self._ctx.generate_cc2_style_tile(terrain_val, tx, ty, bitmask)
                                if self._ctx.generate_cc2_style_tile
                                else None
                            )
                            if texture and self._ctx.autotile_cache:
                                self._ctx.autotile_cache.set_variant(
                                    terrain_val, bitmask, variation, texture
                                )
                        elif self._ctx.autotile_cache:
                            texture = self._ctx.autotile_cache.get_variant(
                                terrain_val, bitmask, variation
                            )

                        if tile_screen_size != tile_size:
                            scale_key = (terrain_val, variation, bitmask, tile_screen_size)
                            if scale_key not in self._ctx.scaled_texture_cache:
                                base_texture = (
                                    self._ctx.autotile_cache.get_variant(
                                        terrain_val, bitmask, variation
                                    )
                                    if self._ctx.autotile_cache
                                    else None
                                )
                                if base_texture:
                                    self._ctx.scaled_texture_cache[scale_key] = (
                                        pygame.transform.scale(
                                            base_texture, (tile_screen_size, tile_screen_size)
                                        )
                                    )
                            texture = self._ctx.scaled_texture_cache.get(scale_key, texture)
                    elif height != 0:
                        cache_key = (terrain_val, variation, height, tile_screen_size)
                        if cache_key in self._ctx.height_lit_cache:
                            texture = self._ctx.height_lit_cache[cache_key]
                        else:
                            base_texture = (
                                self._ctx.get_cached_texture(terrain_val, variation)
                                if self._ctx.get_cached_texture
                                else None
                            )
                            if base_texture:
                                texture = (
                                    self._ctx.apply_height_lighting(base_texture, height)
                                    if self._ctx.apply_height_lighting
                                    else base_texture
                                )
                                if tile_screen_size != tile_size:
                                    texture = pygame.transform.scale(
                                        texture, (tile_screen_size, tile_screen_size)
                                    )
                                self._ctx.height_lit_cache[cache_key] = texture
                    else:
                        if tile_screen_size != tile_size:
                            scale_key = (terrain_val, variation, tile_screen_size)
                            if scale_key not in self._ctx.scaled_texture_cache:
                                base_texture = (
                                    self._ctx.get_cached_texture(terrain_val, variation)
                                    if self._ctx.get_cached_texture
                                    else None
                                )
                                if base_texture:
                                    self._ctx.scaled_texture_cache[scale_key] = (
                                        pygame.transform.scale(
                                            base_texture, (tile_screen_size, tile_screen_size)
                                        )
                                    )
                            texture = self._ctx.scaled_texture_cache.get(scale_key, texture)
                        else:
                            texture = (
                                self._ctx.get_cached_texture(terrain_val, variation)
                                if self._ctx.get_cached_texture
                                else None
                            )

                if texture is not None and self._ctx.offscreen is not None:
                    rect = pygame.Rect(sx, sy, tile_screen_size, tile_screen_size)
                    self._ctx.offscreen.blit(texture, rect)

        if not debug_mode and tile_screen_size >= 16:
            self.apply_terrain_edge_smoothing(
                game_map, camera, start_x, end_x, start_y, end_y, tile_screen_size
            )

        if not debug_mode and tile_screen_size >= 16:
            self.render_terrain_transitions(
                game_map, camera, start_x, end_x, start_y, end_y, tile_screen_size
            )

        if debug_mode and self._ctx.draw_terrain_borders:
            self._ctx.draw_terrain_borders(game_map, camera, start_x, end_x, start_y, end_y)

    def render_terrain_transitions(
        self,
        game_map: GameMap,
        camera: Camera,
        start_x: int,
        end_x: int,
        start_y: int,
        end_y: int,
        tile_screen_size: int,
    ) -> None:
        if self._ctx.screen is None or self._ctx.offscreen is None or tile_screen_size < 8:
            return

        try:
            current_map_hash = hash((game_map.width, game_map.height, id(game_map)))
            if current_map_hash != self._last_map_hash:
                self._transition_cache.clear()
        except (ValueError, TypeError):
            pass

        strip_width = max(
            self.TRANSITION_STRIP_WIDTH_MIN,
            min(self.TRANSITION_STRIP_WIDTH_MAX, tile_screen_size // 8),
        )

        get_terrain = self._ctx.get_terrain_at
        if get_terrain is None:
            return

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                current = get_terrain(game_map, tx, ty)
                if current < 0:
                    continue

                neighbors = [
                    (tx, ty - 1, "north"),
                    (tx, ty + 1, "south"),
                    (tx + 1, ty, "east"),
                    (tx - 1, ty, "west"),
                ]

                for nx, ny, direction in neighbors:
                    if nx < 0 or ny < 0 or nx >= game_map.width or ny >= game_map.height:
                        continue
                    neighbor = get_terrain(game_map, nx, ny)
                    if neighbor < 0 or neighbor == current:
                        continue

                    cache_key = (tx, ty, current, neighbor, direction)
                    if cache_key in self._transition_cache:
                        cached_surf, cached_rect = self._transition_cache[cache_key]
                        self._ctx.offscreen.blit(cached_surf, cached_rect)
                        continue

                    color_from = self.TERRAIN_BASE_COLORS.get(current, (128, 128, 128))
                    color_to = self.TERRAIN_BASE_COLORS.get(neighbor, (128, 128, 128))

                    middle_color = (
                        (color_from[0] + color_to[0]) // 2,
                        (color_from[1] + color_to[1]) // 2,
                        (color_from[2] + color_to[2]) // 2,
                    )

                    world_x = tx * self._ctx.tile_size
                    world_y = ty * self._ctx.tile_size
                    screen_pos = camera.world_to_screen(Vec2(world_x, world_y))
                    base_x = int(screen_pos[0])
                    base_y = int(screen_pos[1])

                    if direction == "north":
                        rect = pygame.Rect(base_x, base_y, tile_screen_size, strip_width)
                    elif direction == "south":
                        rect = pygame.Rect(
                            base_x,
                            base_y + tile_screen_size - strip_width,
                            tile_screen_size,
                            strip_width,
                        )
                    elif direction == "east":
                        rect = pygame.Rect(
                            base_x + tile_screen_size - strip_width,
                            base_y,
                            strip_width,
                            tile_screen_size,
                        )
                    else:
                        rect = pygame.Rect(base_x, base_y, strip_width, tile_screen_size)

                    strip_surf = (
                        self._ctx.get_pooled_surface((rect.width, rect.height))
                        if self._ctx.get_pooled_surface
                        else pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                    )

                    if direction in ("north", "south"):
                        for col in range(rect.width):
                            t = col / max(1, rect.width - 1)

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

                            for row in range(rect.height):
                                edge_t = row / max(1, rect.height - 1)
                                if direction == "north":
                                    alpha = int(self.TRANSITION_ALPHA_PEAK * (1 - edge_t**0.7))
                                else:
                                    alpha = int(self.TRANSITION_ALPHA_PEAK * edge_t**0.7)

                                boundary_boost = 1.0
                                if 0.4 <= edge_t <= 0.6:
                                    boundary_boost = 1.3

                                alpha = int(min(255, alpha * boundary_boost))
                                alpha = max(0, min(255, alpha))
                                strip_surf.set_at((col, row), (r, g, b, alpha))
                    else:
                        for row in range(rect.height):
                            t = row / max(1, rect.height - 1)

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
                                if direction == "west":
                                    alpha = int(self.TRANSITION_ALPHA_PEAK * (1 - edge_t**0.7))
                                else:
                                    alpha = int(self.TRANSITION_ALPHA_PEAK * edge_t**0.7)

                                boundary_boost = 1.0
                                if 0.4 <= edge_t <= 0.6:
                                    boundary_boost = 1.3

                                alpha = int(min(255, alpha * boundary_boost))
                                alpha = max(0, min(255, alpha))
                                strip_surf.set_at((col, row), (r, g, b, alpha))

                    self._transition_cache[cache_key] = (strip_surf, rect)
                    self._ctx.offscreen.blit(strip_surf, rect)

    def apply_terrain_edge_smoothing(
        self,
        game_map: GameMap,
        camera: Camera,
        start_x: int,
        end_x: int,
        start_y: int,
        end_y: int,
        tile_screen_size: int,
    ) -> None:
        if self._ctx.screen is None or self._ctx.offscreen is None or tile_screen_size < 8:
            return

        try:
            current_map_hash = hash((game_map.width, game_map.height, id(game_map)))
            if current_map_hash != self._last_map_hash or self._edge_smooth_dirty:
                self._edge_smooth_cache.clear()
                if self._ctx.terrain_tile_cache:
                    self._ctx.terrain_tile_cache.invalidate()
                self._last_map_hash = current_map_hash
                self._edge_smooth_dirty = False
        except (ValueError, TypeError) as e:
            logging.debug(f"Map hash/cache update failed: {e}")

        autotile_terrains = {5, 6, 7}
        smoothable_pairs = {
            (0, 1),
            (1, 0),
            (0, 2),
            (2, 0),
            (1, 2),
            (2, 1),
            (0, 3),
            (3, 0),
            (1, 3),
            (3, 1),
        }

        get_terrain = self._ctx.get_terrain_at
        if get_terrain is None:
            return

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                current = get_terrain(game_map, tx, ty)
                if current < 0 or current in autotile_terrains:
                    continue

                neighbors = [
                    (tx + 1, ty, "right"),
                    (tx - 1, ty, "left"),
                    (tx, ty + 1, "down"),
                    (tx, ty - 1, "up"),
                ]

                for nx, ny, direction in neighbors:
                    if nx < start_x or nx >= end_x or ny < start_y or ny >= end_y:
                        continue

                    neighbor = get_terrain(game_map, nx, ny)
                    if neighbor < 0 or neighbor == current or neighbor in autotile_terrains:
                        continue
                    if (current, neighbor) not in smoothable_pairs:
                        continue

                    cache_key = (min(tx, nx), min(ty, ny), max(tx, nx), max(ty, ny))
                    if cache_key in self._edge_smooth_cache:
                        cached_surf, cached_rect = self._edge_smooth_cache[cache_key]
                        self._ctx.offscreen.blit(
                            cached_surf, cached_rect, special_flags=pygame.BLEND_RGBA_ADD
                        )
                        continue

                    world_x = tx * self._ctx.tile_size
                    world_y = ty * self._ctx.tile_size
                    screen_pos = camera.world_to_screen(Vec2(world_x, world_y))
                    base_x = int(screen_pos[0])
                    base_y = int(screen_pos[1])

                    try:
                        pal = self._ctx.palette_gen
                        color1 = pal.get_color(current, 4)
                        color2 = pal.get_color(neighbor, 4)
                        blend_color = (
                            (color1[0] + color2[0]) // 2,
                            (color1[1] + color2[1]) // 2,
                            (color1[2] + color2[2]) // 2,
                            45,
                        )
                    except (ValueError, TypeError) as e:
                        logging.debug(f"Edge color blending failed: {e}")
                        blend_color = (80, 80, 80, 45)

                    edge_width = max(
                        self.EDGE_SMOOTH_WIDTH_MIN,
                        min(self.EDGE_SMOOTH_WIDTH_MAX, tile_screen_size // 16),
                    )

                    if direction in ("right", "left"):
                        edge_x = base_x + (tile_screen_size if direction == "left" else 0)
                        edge_rect = pygame.Rect(edge_x, base_y, edge_width, tile_screen_size)
                    else:
                        edge_y = base_y + (tile_screen_size if direction == "up" else 0)
                        edge_rect = pygame.Rect(base_x, edge_y, tile_screen_size, edge_width)

                    edge_surf = (
                        self._ctx.get_pooled_surface((edge_rect.width, edge_rect.height))
                        if self._ctx.get_pooled_surface
                        else pygame.Surface((edge_rect.width, edge_rect.height), pygame.SRCALPHA)
                    )

                    for i in range(
                        edge_rect.width if direction in ("right", "left") else edge_rect.height
                    ):
                        alpha = int(
                            self.EDGE_SMOOTH_ALPHA_PEAK
                            * (1 - abs(i - (edge_width // 2)) / max(1, edge_width))
                        )
                        alpha = max(10, min(self.EDGE_SMOOTH_ALPHA_PEAK, alpha))

                        if direction in ("right", "left"):
                            pygame.draw.line(
                                edge_surf, (*blend_color[:3], alpha), (i, 0), (i, edge_rect.height)
                            )
                        else:
                            pygame.draw.line(
                                edge_surf, (*blend_color[:3], alpha), (0, i), (edge_rect.width, i)
                            )

                    self._edge_smooth_cache[cache_key] = (edge_surf, edge_rect)
                    self._ctx.offscreen.blit(
                        edge_surf, edge_rect, special_flags=pygame.BLEND_RGBA_ADD
                    )
