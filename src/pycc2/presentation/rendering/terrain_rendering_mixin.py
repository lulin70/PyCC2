"""Terrain rendering mixin — extracted from sprite_renderer.py (D11-2 SRP split).

Contains terrain-related rendering methods used by the SpriteRenderer facade:
  - _draw_debug_grid: debug grid placeholder (release builds never call this)
  - _generate_all_sprites: delegated sprite generation
  - _create_unit_sprite: delegated unit sprite creation
  - _generate_terrain_tiles: delegated terrain tile generation
  - _draw_terrain: draw cached terrain tiles via TileCache

This is a mixin — do not instantiate directly. The SpriteRenderer facade
inherits this mixin and provides all required attributes via SpriteRendererBase.
Class-level attribute declarations below tell mypy which facade fields the
mixin methods rely on.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pygame import Surface

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.presentation.rendering.sprite_cache_manager import SpriteCacheManager

__all__ = ["TerrainRenderingMixin"]


class TerrainRenderingMixin:
    """Terrain rendering methods. Inherited by the SpriteRenderer facade, not instantiated."""

    # -- Facade attributes used by terrain methods (no defaults; set by SpriteRendererBase) --
    TILE_SIZE: int
    draw_surface: Surface | None
    _cache_manager: SpriteCacheManager

    def _draw_debug_grid(self, game_map: GameMap, camera: Camera) -> None:
        """Debug grid placeholder (release builds never call this)."""
        if self.draw_surface is None:
            return

    # ====== 程序化精灵生成 (delegated) ======

    def _generate_all_sprites(self) -> None:
        """Delegated to SpriteCacheManager."""
        self._cache_manager._generate_all_sprites()

    def _create_unit_sprite(
        self,
        faction: str,
        unit_type: str,
        direction: int,
        turret_direction: int | None = None,
        state: str = "idle",
    ) -> Surface:
        """Delegated to SpriteCacheManager."""
        return self._cache_manager.create_unit_sprite(
            faction,
            unit_type,
            direction,
            turret_direction,
            state,
        )

    def _generate_terrain_tiles(self) -> None:
        """Delegated to SpriteCacheManager."""
        self._cache_manager._generate_terrain_tiles()

    # ====== 绘制方法 ======

    def _draw_terrain(self, game_map: GameMap, camera: Camera) -> None:
        """使用缓存的地形tile绘制地图（TileCache避免每帧transform.scale）"""
        surface = self.draw_surface
        if surface is None:
            return
        from pycc2.domain.value_objects.vec2 import Vec2

        bounds = camera.view_bounds
        sx = max(0, int(bounds[0].x // self.TILE_SIZE))
        ex = min(game_map.width, int((bounds[1].x // self.TILE_SIZE) + 2))
        sy = max(0, int(bounds[0].y // self.TILE_SIZE))
        ey = min(game_map.height, int((bounds[1].y // self.TILE_SIZE) + 2))

        tsz = int(self.TILE_SIZE * camera.zoom)
        if tsz <= 0:
            return

        for ty in range(sy, ey):
            for tx in range(sx, ex):
                tv = int(game_map.tile_grid[ty, tx])
                cached_surface = self._cache_manager.get_terrain_tile(tv, tsz)
                if cached_surface:
                    wx = tx * self.TILE_SIZE
                    wy = ty * self.TILE_SIZE
                    sp = camera.world_to_screen(Vec2(wx, wy))
                    surface.blit(cached_surface, (int(sp[0]), int(sp[1])))
