"""Terrain tile generator facade.

Provides backward-compatible ``TerrainTileGenerator`` class that delegates to
submodule-level functions split out during Phase 2 P0-1 (2026-07-04):

  - ``terrain_tiles_natural``: grass / woods / water / open / shallow / rough / swamp / mud / sand / snow
  - ``terrain_tiles_road``: road
  - ``terrain_tiles_structures``: building / bridge / hedge / wall / bunker
  - ``terrain_tiles_battlefield``: crater / wire / trench

Public API is preserved: ``TerrainTileGenerator.generate_grass(...)`` and
``from pycc2.presentation.rendering.terrain_tile_generator import TerrainTileGenerator``
continue to work unchanged.
"""

from __future__ import annotations

from pycc2.presentation.rendering.pixel_canvas import PixelCanvas
from pycc2.presentation.rendering.terrain_tiles_battlefield import (
    generate_crater,
    generate_trench,
    generate_wire,
)
from pycc2.presentation.rendering.terrain_tiles_natural import (
    generate_grass,
    generate_mud,
    generate_open,
    generate_rough,
    generate_sand,
    generate_shallow,
    generate_snow,
    generate_swamp,
    generate_water,
    generate_woods,
)
from pycc2.presentation.rendering.terrain_tiles_road import generate_road
from pycc2.presentation.rendering.terrain_tiles_structures import (
    generate_bridge,
    generate_building,
    generate_bunker,
    generate_hedge,
    generate_wall,
)

# ============================================================
# 5. 地形瓦片生成器 (facade)
# ============================================================


class TerrainTileGenerator:
    """地形瓦片生成器 facade — 转发到 4 个子模块的模块级函数。

    所有 19 个 generate_* @staticmethod 保留原始签名，仅转发调用：
      - 10 个自然地形 → terrain_tiles_natural
      - 1 个道路      → terrain_tiles_road
      - 5 个人工建筑  → terrain_tiles_structures
      - 3 个战场      → terrain_tiles_battlefield
    """

    @staticmethod
    def generate_grass(size: int, variant: int = 0) -> PixelCanvas:
        return generate_grass(size, variant=variant)

    @staticmethod
    def generate_road(
        size: int, orientation: str = "horizontal", neighbors: dict | None = None
    ) -> PixelCanvas:
        return generate_road(size, orientation=orientation, neighbors=neighbors)

    @staticmethod
    def generate_woods(size: int, density: str = "medium") -> PixelCanvas:
        return generate_woods(size, density=density)

    @staticmethod
    def generate_building(size: int, building_type: str = "solid") -> PixelCanvas:
        return generate_building(size, building_type=building_type)

    @staticmethod
    def generate_bridge(size: int) -> PixelCanvas:
        return generate_bridge(size)

    @staticmethod
    def generate_water(
        size: int, tile_x: int = 0, tile_y: int = 0, neighbors: dict | None = None
    ) -> PixelCanvas:
        return generate_water(size, tile_x=tile_x, tile_y=tile_y, neighbors=neighbors)

    @staticmethod
    def generate_hedge(size: int) -> PixelCanvas:
        return generate_hedge(size)

    @staticmethod
    def generate_wall(size: int) -> PixelCanvas:
        return generate_wall(size)

    @staticmethod
    def generate_open(size: int) -> PixelCanvas:
        return generate_open(size)

    @staticmethod
    def generate_shallow(size: int) -> PixelCanvas:
        return generate_shallow(size)

    @staticmethod
    def generate_rough(size: int) -> PixelCanvas:
        return generate_rough(size)

    @staticmethod
    def generate_crater(size: int, variant: int = 0) -> PixelCanvas:
        return generate_crater(size, variant=variant)

    @staticmethod
    def generate_swamp(size: int, variant: int = 0) -> PixelCanvas:
        return generate_swamp(size, variant=variant)

    @staticmethod
    def generate_mud(size: int, variant: int = 0) -> PixelCanvas:
        return generate_mud(size, variant=variant)

    @staticmethod
    def generate_sand(size: int, variant: int = 0) -> PixelCanvas:
        return generate_sand(size, variant=variant)

    @staticmethod
    def generate_snow(size: int, variant: int = 0) -> PixelCanvas:
        return generate_snow(size, variant=variant)

    @staticmethod
    def generate_wire(size: int, variant: int = 0) -> PixelCanvas:
        return generate_wire(size, variant=variant)

    @staticmethod
    def generate_trench(size: int, variant: int = 0) -> PixelCanvas:
        return generate_trench(size, variant=variant)

    @staticmethod
    def generate_bunker(size: int, variant: int = 0) -> PixelCanvas:
        return generate_bunker(size, variant=variant)
