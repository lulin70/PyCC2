"""
Render Context - Dependency injection container for sub-renderers.

Eliminates self._parent._ penetration coupling by providing
explicit interfaces for all shared rendering dependencies.
"""

from __future__ import annotations

from collections.abc import Callable

import pygame

from pycc2.presentation.rendering.autotile_system import AutotileCache
from pycc2.presentation.rendering.palette_generator import PaletteGenerator
from pycc2.presentation.rendering.terrain_tile_cache import TerrainTileCache


class RenderContext:
    """Holds all shared dependencies for sub-renderers.

    Instead of sub-renderers reaching through self._parent._xxx,
    they receive a RenderContext with explicit, typed references.
    """

    __slots__ = (
        "tile_size",
        "screen",
        "offscreen",
        "sprite_renderer",
        "palette_gen",
        "texture_cache",
        "scaled_texture_cache",
        "height_lit_cache",
        "autotile_cache",
        "terrain_tile_cache",
        "building_clusters",
        "sprite_cache",
        "get_pooled_surface",
        "get_cached_texture",
        "get_enhanced_tile",
        "get_terrain_at",
        "generate_cc2_style_tile",
        "apply_height_lighting",
        "get_health_tinted_color",
        "draw_direction_indicator",
        "draw_movement_mode_overlay",
        "draw_terrain_borders",
        "draw_decorations",
    )

    def __init__(
        self,
        tile_size: int,
        screen: pygame.Surface | None = None,
        offscreen: pygame.Surface | None = None,
        sprite_renderer: object | None = None,
        palette_gen: PaletteGenerator | None = None,
        texture_cache: dict | None = None,
        scaled_texture_cache: dict | None = None,
        height_lit_cache: dict | None = None,
        autotile_cache: AutotileCache | None = None,
        terrain_tile_cache: TerrainTileCache | None = None,
        building_clusters: list | None = None,
        sprite_cache: dict | None = None,
        get_pooled_surface: Callable[[tuple[int, int]], pygame.Surface] | None = None,
        get_cached_texture: Callable[[int, int], pygame.Surface] | None = None,
        get_enhanced_tile: Callable | None = None,
        get_terrain_at: Callable | None = None,
        generate_cc2_style_tile: Callable | None = None,
        apply_height_lighting: Callable | None = None,
        get_health_tinted_color: Callable | None = None,
        draw_direction_indicator: Callable | None = None,
        draw_movement_mode_overlay: Callable | None = None,
        draw_terrain_borders: Callable | None = None,
        draw_decorations: Callable | None = None,
    ):
        self.tile_size = tile_size
        self.screen = screen
        self.offscreen = offscreen
        self.sprite_renderer = sprite_renderer
        self.palette_gen = palette_gen
        self.texture_cache = texture_cache or {}
        self.scaled_texture_cache = scaled_texture_cache or {}
        self.height_lit_cache = height_lit_cache or {}
        self.autotile_cache = autotile_cache
        self.terrain_tile_cache = terrain_tile_cache
        self.building_clusters = building_clusters
        self.sprite_cache = sprite_cache or {}
        self.get_pooled_surface = get_pooled_surface
        self.get_cached_texture = get_cached_texture
        self.get_enhanced_tile = get_enhanced_tile
        self.get_terrain_at = get_terrain_at
        self.generate_cc2_style_tile = generate_cc2_style_tile
        self.apply_height_lighting = apply_height_lighting
        self.get_health_tinted_color = get_health_tinted_color
        self.draw_direction_indicator = draw_direction_indicator
        self.draw_movement_mode_overlay = draw_movement_mode_overlay
        self.draw_terrain_borders = draw_terrain_borders
        self.draw_decorations = draw_decorations

    def update_surfaces(
        self, screen: pygame.Surface | None, offscreen: pygame.Surface | None
    ) -> None:
        self.screen = screen
        self.offscreen = offscreen

    def update_building_clusters(self, clusters: list | None) -> None:
        self.building_clusters = clusters
