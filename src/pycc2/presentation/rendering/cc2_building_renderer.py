"""CC2-style oblique projection building renderer (facade).

D11 SRP 拆分后的 facade 模块。原 1215 行单文件已按职责拆分为 4 个子模块:
- cc2_building_common.py: 共享常量/枚举/辅助函数（DamageLevel / CC2_ROOF_COLORS / _deterministic_seed / _draw_pixel_digit / get_building_size / floors_to_building_type / should_show_interior）
- cc2_residential_renderer.py: render_cc2_building 主入口（标准住宅 OBLIQUE PROJECTION + dispatch）
- cc2_normandy_renderer.py: 诺曼底战役专属建筑（_render_normandy_farmhouse / _render_normandy_barn）
- cc2_special_renderer.py: 非住宅特殊建筑（_render_church / _render_wall / _render_barn / _render_building_interior）

本 facade 保留原 public API 不变，下游模块（building_renderer.py / 测试）
无需修改任何 import 语句，确保向后兼容。

Renders buildings in CC2's authentic OBLIQUE projection view with:
- Roof plane (top surface with texture)
- South wall face (bottom edge, darker, 1-2px tall)
- East wall face (right edge, darker, 1-2px wide)
- Roof edge trim (orange-brown border)
This matches CC2 screenshot analysis exactly.
"""

from pycc2.domain.value_objects.building_data import CC2BuildingType
from pycc2.presentation.rendering.cc2_building_common import (
    CC2_ROOF_COLORS,
    CC2_ROOF_VARIANTS,
    ROOF_NUMBER_COLOR,
    ROOF_TRIM_COLOR,
    WALL_FACE_MULTIPLIER,
    DamageLevel,
    floors_to_building_type,
    get_building_size,
    should_show_interior,
)
from pycc2.presentation.rendering.cc2_residential_renderer import render_cc2_building

__all__ = [
    "CC2BuildingType",
    "CC2_ROOF_COLORS",
    "CC2_ROOF_VARIANTS",
    "DamageLevel",
    "ROOF_NUMBER_COLOR",
    "ROOF_TRIM_COLOR",
    "WALL_FACE_MULTIPLIER",
    "floors_to_building_type",
    "get_building_size",
    "render_cc2_building",
    "should_show_interior",
]
