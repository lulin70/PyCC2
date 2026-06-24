"""CC2 Pixel Artist — re-export shell.

This module provides backward-compatible imports for:
  - create_unit_sprite()
  - create_terrain_tile()
  - All palette/canvas/generator classes

Sub-modules:
  - pixel_canvas.py: CCPalette, PaletteSet, PixelCanvas, add_noise, dither_pattern
  - unit_sprite_generator.py: UnitSpriteSpec, UnitSpriteGenerator
  - terrain_tile_generator.py: TerrainTileGenerator
"""

from __future__ import annotations

# -- Re-exports --------------------------------------------------------
from pycc2.presentation.rendering.pixel_canvas import (  # noqa: F401
    CCPalette,
    PaletteSet,
    PixelCanvas,
    add_noise,
    dither_pattern,
)
from pycc2.presentation.rendering.terrain_tile_generator import (  # noqa: F401
    TerrainTileGenerator,
)
from pycc2.presentation.rendering.unit_sprite_generator import (  # noqa: F401
    UnitSpriteGenerator,
    UnitSpriteSpec,
)

# ============================================================
# 6. 工厂函数 — 对外统一接口
# ============================================================


def create_unit_sprite(
    faction: str,
    unit_type: str,
    direction: int = 0,
    size: int = 24,
    frame: int = 0,
    state: str = "idle",
) -> PixelCanvas:
    """便捷函数：创建单位精灵"""
    spec = UnitSpriteSpec(
        faction=faction,
        unit_type=unit_type,
        direction=direction,
        size=size,
        frame_offset=frame,
        state=state,
    )
    return UnitSpriteGenerator.generate(spec)


def create_terrain_tile(
    terrain_id: int, size: int = 48, tile_x: int = 0, tile_y: int = 0, neighbors: dict | None = None
) -> PixelCanvas:
    """便捷函数：创建地形瓦片

    Args:
        terrain_id: 地形类型ID
        size: 瓦片尺寸
        tile_x: 瓦片世界X坐标(用于跨瓦片连续性)
        tile_y: 瓦片世界Y坐标(用于跨瓦片连续性)
        neighbors: 邻居信息字典, 键为 "north"/"east"/"south"/"west",
                   值为 True(同类型邻居) 或 False(非同类型邻居)
    """
    if terrain_id == 1:
        return TerrainTileGenerator.generate_road(size, neighbors=neighbors)
    if terrain_id == 6:
        return TerrainTileGenerator.generate_water(
            size, tile_x=tile_x, tile_y=tile_y, neighbors=neighbors
        )
    generators = {
        0: lambda s: TerrainTileGenerator.generate_open(s),
        2: lambda s: TerrainTileGenerator.generate_grass(s, variant=2),
        3: lambda s: TerrainTileGenerator.generate_woods(s, "medium"),
        4: lambda s: TerrainTileGenerator.generate_building(s, "enterable"),
        5: lambda s: TerrainTileGenerator.generate_building(s, "solid"),
        7: lambda s: TerrainTileGenerator.generate_hedge(s),
        8: lambda s: TerrainTileGenerator.generate_wall(s),
        9: lambda s: TerrainTileGenerator.generate_rough(s),
        10: lambda s: TerrainTileGenerator.generate_shallow(s),
        11: lambda s: TerrainTileGenerator.generate_bridge(s),
        12: lambda s: TerrainTileGenerator.generate_crater(s),
        13: lambda s: TerrainTileGenerator.generate_swamp(s),
        14: lambda s: TerrainTileGenerator.generate_bridge(s),
        15: lambda s: TerrainTileGenerator.generate_crater(s, variant=5),
        16: lambda s: TerrainTileGenerator.generate_trench(s),
        17: lambda s: TerrainTileGenerator.generate_mud(s),
        18: lambda s: TerrainTileGenerator.generate_sand(s),
        19: lambda s: TerrainTileGenerator.generate_snow(s),
        20: lambda s: TerrainTileGenerator.generate_wire(s),
        21: lambda s: TerrainTileGenerator.generate_bunker(s),
    }
    gen = generators.get(terrain_id, lambda s: TerrainTileGenerator.generate_open(s))
    return gen(size)
