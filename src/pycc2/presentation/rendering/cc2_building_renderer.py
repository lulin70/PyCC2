"""CC2-style orthographic building renderer.

Renders buildings in CC2's authentic top-down view with pseudo-3D shadow strips.
This is the CORRECT building rendering style (NOT isometric).
"""

import pygame
import random
from enum import Enum


class CC2BuildingType(Enum):
    """Building types matching CC2 - 包含诺曼底战役特有建筑风格."""
    SMALL_HOUSE = "small_house"
    MEDIUM_HOUSE = "medium_house"
    LARGE_BUILDING = "large_building"
    BARN = "barn"
    CHURCH = "church"
    WALL = "wall"
    # 诺曼底战役特有建筑类型 - 基于历史建筑学研究
    NORMANDY_FARMHOUSE = "normandy_farmhouse"   # 诺曼底农舍: 2x2, 陡峭红瓦屋顶, 石墙
    NORMANDY_BARN = "normandy_barn"              # 诺曼底谷仓: 2x3, 大型, 棕色双开门


class DamageLevel(Enum):
    INTACT = 0
    LIGHT_DAMAGE = 1
    HEAVY_DAMAGE = 2
    DESTROYED = 3


CC2_ROOF_COLORS = {
    CC2BuildingType.SMALL_HOUSE: (184, 48, 32),
    CC2BuildingType.MEDIUM_HOUSE: (168, 44, 28),
    CC2BuildingType.LARGE_BUILDING: (80, 88, 96),
    CC2BuildingType.BARN: (139, 96, 64),
    CC2BuildingType.CHURCH: (200, 200, 200),
    CC2BuildingType.WALL: (112, 112, 112),
    # 诺曼底建筑屋顶颜色 - 基于历史照片和建筑学研究
    CC2BuildingType.NORMANDY_FARMHOUSE: (160, 42, 28),   # 深红瓦片屋顶 (历史特征!)
    CC2BuildingType.NORMANDY_BARN: (120, 75, 45),         # 棕色木质屋顶
}


# Window positions for each building type (relative to tile, used for firing arc restrictions)
# Each window has a 'wall' (cardinal direction it faces) and 'offset' (0.0-1.0 along that wall)
BUILDING_WINDOWS: dict[CC2BuildingType, list[dict]] = {
    CC2BuildingType.SMALL_HOUSE: [
        {'wall': 'north', 'offset': 0.5},
        {'wall': 'south', 'offset': 0.5},
        {'wall': 'east', 'offset': 0.5},
        {'wall': 'west', 'offset': 0.5},
    ],
    CC2BuildingType.MEDIUM_HOUSE: [
        {'wall': 'north', 'offset': 0.3},
        {'wall': 'north', 'offset': 0.7},
        {'wall': 'south', 'offset': 0.3},
        {'wall': 'south', 'offset': 0.7},
        {'wall': 'east', 'offset': 0.5},
        {'wall': 'west', 'offset': 0.5},
    ],
    CC2BuildingType.LARGE_BUILDING: [
        {'wall': 'north', 'offset': 0.2},
        {'wall': 'north', 'offset': 0.5},
        {'wall': 'north', 'offset': 0.8},
        {'wall': 'south', 'offset': 0.2},
        {'wall': 'south', 'offset': 0.5},
        {'wall': 'south', 'offset': 0.8},
        {'wall': 'east', 'offset': 0.3},
        {'wall': 'east', 'offset': 0.7},
        {'wall': 'west', 'offset': 0.3},
        {'wall': 'west', 'offset': 0.7},
    ],
    CC2BuildingType.BARN: [
        {'wall': 'north', 'offset': 0.5},
        {'wall': 'south', 'offset': 0.5},
        {'wall': 'east', 'offset': 0.3},
        {'wall': 'east', 'offset': 0.7},
        {'wall': 'west', 'offset': 0.3},
        {'wall': 'west', 'offset': 0.7},
    ],
    CC2BuildingType.CHURCH: [
        {'wall': 'north', 'offset': 0.5},
        {'wall': 'south', 'offset': 0.5},
        {'wall': 'east', 'offset': 0.3},
        {'wall': 'east', 'offset': 0.7},
        {'wall': 'west', 'offset': 0.3},
        {'wall': 'west', 'offset': 0.7},
    ],
    CC2BuildingType.WALL: [],
    CC2BuildingType.NORMANDY_FARMHOUSE: [
        {'wall': 'north', 'offset': 0.3},
        {'wall': 'north', 'offset': 0.7},
        {'wall': 'south', 'offset': 0.3},
        {'wall': 'south', 'offset': 0.7},
        {'wall': 'east', 'offset': 0.5},
        {'wall': 'west', 'offset': 0.5},
    ],
    CC2BuildingType.NORMANDY_BARN: [
        {'wall': 'north', 'offset': 0.5},
        {'wall': 'south', 'offset': 0.5},
        {'wall': 'east', 'offset': 0.3},
        {'wall': 'east', 'offset': 0.7},
        {'wall': 'west', 'offset': 0.3},
        {'wall': 'west', 'offset': 0.7},
    ],
}


def get_building_size(building_type: CC2BuildingType) -> tuple[int, int]:
    """Return (width_tiles, height_tiles) for a building type."""
    sizes = {
        CC2BuildingType.SMALL_HOUSE: (1, 1),
        CC2BuildingType.MEDIUM_HOUSE: (2, 2),
        CC2BuildingType.LARGE_BUILDING: (3, 3),
        CC2BuildingType.BARN: (2, 2),
        CC2BuildingType.CHURCH: (2, 2),
        CC2BuildingType.WALL: (1, 1),
        # 诺曼底建筑尺寸 - 基于历史建筑平面图
        CC2BuildingType.NORMANDY_FARMHOUSE: (2, 2),    # 标准农舍大小
        CC2BuildingType.NORMANDY_BARN: (2, 3),          # 长形谷仓 (更长!)
    }
    return sizes.get(building_type, (1, 1))


def floors_to_building_type(floors: int) -> CC2BuildingType:
    """Map floor count to building type automatically.

    Args:
        floors: Number of floors in the building

    Returns:
        Appropriate CC2BuildingType based on floor count
    """
    if floors <= 1:
        return CC2BuildingType.SMALL_HOUSE
    elif floors == 2:
        return CC2BuildingType.MEDIUM_HOUSE
    elif floors <= 4:
        return CC2BuildingType.LARGE_BUILDING
    else:
        return CC2BuildingType.LARGE_BUILDING


def should_show_interior(building_pos: tuple[int, int], units: list, tile_size: int = 48) -> bool:
    """Check if any unit is inside the building at the given tile position.

    When a unit occupies the same tile as a building, the building renderer
    should automatically switch to interior mode (showing floor + windows
    instead of roof). When all units leave, it switches back to roof mode.

    Args:
        building_pos: (x, y) tile coordinate of the building.
        units: List of unit objects (must have .position.tile_coord.x/y).
        tile_size: Tile size in pixels (unused, kept for API compatibility).

    Returns:
        True if any unit is inside the building tile.
    """
    for unit in units:
        if hasattr(unit, 'position') and hasattr(unit.position, 'tile_coord'):
            ux, uy = unit.position.tile_coord.x, unit.position.tile_coord.y
            bx, by = building_pos
            if ux == bx and uy == by:
                return True
    return False


def render_cc2_building(
    building_type: CC2BuildingType,
    damage: DamageLevel = DamageLevel.INTACT,
    tile_size: int = 48,
    show_number: bool = False,
    number: str | None = None,
    interior_mode: bool = False,  # *** NEW: Interior mode (floor + windows) ***
    occupant_positions: list[tuple[int, int]] | None = None,  # *** NEW: Unit positions inside ***
) -> pygame.Surface:
    """Render a CC2-style building in orthographic top-down view.

    支持两种模式:
    1. **屋顶模式** (默认): 显示屋顶平面（单位在外部时）
    2. **室内模式** (interior_mode=True): 显示地板+窗户轮廓（单位进入时）

    CC2原版机制:
    - 单位进入建筑 → 切换到室内视图
    - 地板纹理 (棋盘格/木地板)
    - 窗户白线轮廓 (影响LOS和射击角度)
    - 反坦克炮等重型武器受窗户位置限制

    Args:
        building_type: Type of building (determines size/color).
        damage: Damage level (affects color/cracks).
        tile_size: Size of one tile in pixels (default 48).
        show_number: Whether to show floor count on roof.
        number: The floor count string to display (e.g., "1", "2", "3", "5").
        interior_mode: If True, render floor instead of roof (CC2 interior view).
        occupant_positions: List of (x,y) positions for units inside (for LOS visualization).

    Returns:
        A pygame.Surface with the building rendered in CC2 style.
    """
    tw, th = get_building_size(building_type)
    w = tw * tile_size
    h = th * tile_size
    surface = pygame.Surface((w, h), pygame.SRCALPHA)

    # *** 室内模式路径 (CC2 Interior View!) ***
    if interior_mode:
        return _render_building_interior(
            surface, w, h, tile_size, building_type, damage,
            occupant_positions or []
        )

    # *** 屋顶模式 (标准外观) ***
    # 诺曼底建筑特殊渲染路径
    if building_type == CC2BuildingType.NORMANDY_FARMHOUSE:
        return _render_normandy_farmhouse(surface, w, h, tile_size, damage, show_number, number)
    elif building_type == CC2BuildingType.NORMANDY_BARN:
        return _render_normandy_barn(surface, w, h, tile_size, damage, show_number, number)

    # 标准CC2建筑渲染（原有逻辑）
    roof_color = CC2_ROOF_COLORS[building_type]
    if damage == DamageLevel.LIGHT_DAMAGE:
        roof_color = tuple(max(0, c - 20) for c in roof_color)
    elif damage == DamageLevel.HEAVY_DAMAGE:
        roof_color = tuple(max(0, c - 45) for c in roof_color)
    elif damage == DamageLevel.DESTROYED:
        roof_color = tuple(max(0, c - 70) for c in roof_color)
    surface.fill(roof_color)

    shadow_color = tuple(max(0, c - 50) for c in roof_color)
    shadow_width = max(2, tile_size // 12)
    pygame.draw.rect(surface, shadow_color, (0, h - shadow_width, w, shadow_width))
    pygame.draw.rect(surface, shadow_color, (w - shadow_width, 0, shadow_width, h))

    if show_number and number:
        font_size = min(w, h) // 2
        font = pygame.font.SysFont("arial", font_size, bold=True)
        text = font.render(number, True, (255, 215, 0))
        text_rect = text.get_rect(center=(w // 2, h // 2))
        surface.blit(text, text_rect)

    if damage.value >= DamageLevel.LIGHT_DAMAGE.value:
        crack_color = (40, 36, 32)
        rng = random.Random(hash(str(building_type) + str(damage)))
        num_cracks = damage.value * 2
        for _ in range(num_cracks):
            x1 = rng.randint(5, w - 5)
            y1 = rng.randint(5, h - 5)
            x2 = x1 + rng.randint(-15, 15)
            y2 = y1 + rng.randint(-15, 15)
            pygame.draw.line(surface, crack_color, (x1, y1), (x2, y2), 1)

    return surface


def _render_normandy_farmhouse(
    surface: pygame.Surface, w: int, h: int, tile_size: int,
    damage: DamageLevel, show_number: bool, number: str | None
) -> pygame.Surface:
    """渲染诺曼底农舍 - CC2正交顶部俯视 (TOP-DOWN VIEW!)

    *** 关键修正: 从伪3D侧视改为纯顶部俯视 ***
    CC2使用Orthographic Top-Down投影，建筑显示为:
    - 屋顶平面（矩形/多边形，不是三角形坡顶!）
    - 烟囱（从上方看的矩形）
    - 天窗/屋顶窗（如果可见）
    - 不显示侧面墙体!

    诺曼底农舍历史特征（俯视角度）:
    - 屋顶形状: 矩形或L形（双坡屋顶从上方看呈矩形）
    - 深红瓦片屋顶 (#A02A1C)
    - 石砌烟囱（突出于屋顶平面）
    - 可能的天窗（暗色矩形）
    """
    import math

    # 诺曼底农舍调色板 - 屋顶为主色调（俯视只看得到屋顶!）
    red_tile_roof = (160, 42, 28)           # 深红瓦片屋顶 (主色)
    red_tile_light = (185, 60, 45)          # 屋顶高光（瓦片反光）
    red_tile_dark = (130, 32, 20)           # 屋顶暗部（瓦片间隙）
    chimney_stone = (100, 95, 88)           # 石砌烟囱（俯视颜色偏暗）
    chimney_dark = (80, 75, 68)             # 烟囱阴影
    skylight_color = (50, 55, 65)           # 天窗（暗色玻璃）

    # 应用损毁效果（影响屋顶颜色）
    if damage == DamageLevel.LIGHT_DAMAGE:
        red_tile_roof = tuple(max(0, c - 18) for c in red_tile_roof)
        red_tile_dark = tuple(max(0, c - 25) for c in red_tile_dark)
    elif damage == DamageLevel.HEAVY_DAMAGE:
        red_tile_roof = tuple(max(0, c - 40) for c in red_tile_roof)
        red_tile_dark = tuple(max(0, c - 50) for c in red_tile_dark)
    elif damage == DamageLevel.DESTROYED:
        red_tile_roof = tuple(max(0, c - 65) for c in red_tile_roof)
        red_tile_dark = tuple(max(0, c - 75) for c in red_tile_dark)

    cx, cy = w // 2, h // 2

    # *** 1. 主屋顶平面 (矩形 - TOP-DOWN VIEW!) ***
    # 诺曼底农舍屋顶从上方看是矩形（略小于建筑 footprint）
    roof_margin = tile_size // 8  # 屋檐伸出量
    roof_rect = (
        roof_margin,
        roof_margin,
        w - 2 * roof_margin,
        h - 2 * roof_margin
    )
    pygame.draw.rect(surface, red_tile_roof, roof_rect)

    # *** 2. 屋顶纹理 (瓦片线条 - 俯视角度的瓦片排列!) ***
    # 诺曼底屋顶通常有横向或斜向瓦片纹理
    tile_rng = random.Random(hash("normandy_rooftop_tiles"))
    # 横向瓦片线（每隔4-6px一条）
    for ty in range(roof_margin + 4, h - roof_margin - 2, tile_rng.randint(4, 6)):
        pygame.draw.line(surface, red_tile_dark,
                        (roof_margin + 2, ty),
                        (w - roof_margin - 2, ty), 1)
    # 偶尔的纵向瓦片缝（增加真实感）
    for _ in range(tile_rng.randint(2, 4)):
        vx = tile_rng.randint(roof_margin + 6, w - roof_margin - 6)
        pygame.draw.line(surface, red_tile_light,
                        (vx, roof_margin + 2),
                        (vx, h - roof_margin - 2), 1)

    # *** 3. 屋脊线 (屋顶中央的隆起线 - 俯视看像一条线!) ***
    ridge_y = cy
    ridge_color = tuple(max(0, c - 25) for c in red_tile_roof)  # 比屋顶稍暗
    pygame.draw.line(surface, ridge_color,
                    (roof_margin + 4, ridge_y),
                    (w - roof_margin - 4, ridge_y), 2)

    # *** 4. 烟囱 (从上方看的矩形 - 突出于屋顶!) ***
    chimney_w = max(8, tile_size // 5)
    chimney_h = max(12, tile_size // 4)
    chimney_x = cx + w // 7   # 偏右位置（典型）
    chimney_y = cy - h // 6  # 靠近屋脊

    # 烟囱主体
    pygame.draw.rect(surface, chimney_stone,
                     (chimney_x, chimney_y, chimney_w, chimney_h))
    # 烟囱阴影（右侧和下侧）
    pygame.draw.rect(surface, chimney_dark,
                     (chimney_x + chimney_w - 1, chimney_y, 1, chimney_h))
    pygame.draw.rect(surface, chimney_dark,
                     (chimney_x, chimney_y + chimney_h - 1, chimney_w, 1))
    # 烟囱顶部装饰（石砌边缘）
    pygame.draw.rect(surface, (115, 108, 100),
                     (chimney_x - 1, chimney_y - 1, chimney_w + 2, 3), 1)

    # *** 5. 天窗 (可选 - 诺曼底老房子常有) ***
    if random.Random(hash("skylight")).random() > 0.4:
        sky_w = max(10, tile_size // 4)
        sky_h = max(8, tile_size // 5)
        sky_x = cx - w // 5
        sky_y = cy + h // 8
        pygame.draw.rect(surface, skylight_color,
                         (sky_x, sky_y, sky_w, sky_h))
        # 天窗边框
        pygame.draw.rect(surface, chimney_dark,
                         (sky_x, sky_y, sky_w, sky_h), 1)

    # *** 6. 楼层数字 (如果启用) ***
    if show_number and number:
        font_size = min(w, h) // 2
        font = pygame.font.SysFont("arial", font_size, bold=True)
        text = font.render(number, True, (255, 215, 0))  # 金黄色数字
        text_rect = text.get_rect(center=(cx, cy))
        surface.blit(text, text_rect)

    # *** 7. 损坏效果 (屋顶破洞/缺失瓦片!) ***
    if damage.value >= DamageLevel.LIGHT_DAMAGE.value:
        crack_color = (40, 36, 32)
        rng = random.Random(hash(str(damage) + "farmhouse"))
        num_cracks = damage.value * 3
        for _ in range(num_cracks):
            x1 = rng.randint(roof_margin + 5, w - roof_margin - 5)
            y1 = rng.randint(roof_margin + 5, h - roof_margin - 5)
            length = rng.randint(5, 15)
            angle = rng.uniform(0, 2 * math.pi)
            x2 = x1 + int(length * math.cos(angle))
            y2 = y1 + int(length * math.sin(angle))
            pygame.draw.line(surface, crack_color, (x1, y1), (x2, y2), 1)
        # 重度损坏: 屋顶缺失区域（暗色斑块）
        if damage.value >= DamageLevel.HEAVY_DAMAGE.value:
            for _ in range(damage.value):
                hole_x = rng.randint(roof_margin + 8, w - roof_margin - 16)
                hole_y = rng.randint(roof_margin + 8, h - roof_margin - 16)
                hole_w = rng.randint(8, 16)
                hole_h = rng.randint(8, 16)
                pygame.draw.rect(surface, (30, 28, 24),
                               (hole_x, hole_y, hole_w, hole_h))

    # Shadow strips (consistent with standard building rendering)
    shadow_color = tuple(max(0, c - 50) for c in red_tile_roof)
    shadow_width = max(2, tile_size // 12)
    pygame.draw.rect(surface, shadow_color, (0, h - shadow_width, w, shadow_width))
    pygame.draw.rect(surface, shadow_color, (w - shadow_width, 0, shadow_width, h))

    return surface


def _render_normandy_barn(
    surface: pygame.Surface, w: int, h: int, tile_size: int,
    damage: DamageLevel, show_number: bool, number: str | None
) -> pygame.Surface:
    """渲染诺曼底谷仓 - CC2正交顶部俯视 (TOP-DOWN VIEW!)

    *** 关键修正: 从伪3D侧视改为纯顶部俯视 ***
    CC2使用Orthographic Top-Down投影，谷仓显示为:
    - 屋顶平面（长矩形，不是三角形坡顶!）
    - 双开门（从上方看是两个并排矩形）
    - 通风口（屋顶小矩形）
    - 不显示侧面墙体!

    诺曼底谷仓历史特征（俯视角度）:
    - 长形屋顶 (2×3 tiles)
    - 棕色木质/金属屋顶 (#784B2D)
    - 大型双开门（一端）
    - 屋顶通风口
    """
    import math

    # 诺曼底谷仓调色板 - 屋顶为主色调
    barn_wood_roof = (120, 75, 45)          # 棕色木质屋顶 (主色!)
    barn_wood_light = (145, 95, 60)         # 屋顶高光
    barn_wood_dark = (95, 58, 33)           # 屋顶暗部（木板间隙）
    door_color = (90, 62, 38)               # 双开门棕色
    door_dark = (68, 46, 28)                # 门暗部/缝隙
    vent_color = (50, 52, 48)               # 通风口暗色

    # 应用损毁效果
    if damage == DamageLevel.LIGHT_DAMAGE:
        barn_wood_roof = tuple(max(0, c - 15) for c in barn_wood_roof)
        barn_wood_dark = tuple(max(0, c - 22) for c in barn_wood_dark)
    elif damage == DamageLevel.HEAVY_DAMAGE:
        barn_wood_roof = tuple(max(0, c - 35) for c in barn_wood_roof)
        barn_wood_dark = tuple(max(0, c - 42) for c in barn_wood_dark)
    elif damage == DamageLevel.DESTROYED:
        barn_wood_roof = tuple(max(0, c - 60) for c in barn_wood_roof)
        barn_wood_dark = tuple(max(0, c - 67) for c in barn_wood_dark)

    cx, cy = w // 2, h // 2

    # *** 1. 主屋顶平面 (长矩形 - TOP-DOWN VIEW!) ***
    roof_margin = tile_size // 8
    roof_rect = (
        roof_margin,
        roof_margin,
        w - 2 * roof_margin,
        h - 2 * roof_margin
    )
    pygame.draw.rect(surface, barn_wood_roof, roof_rect)

    # *** 2. 屋顶纹理 (木板线条 - 谷仓通常是纵向木板!) ***
    wood_rng = random.Random(hash("barn_wood_grain"))
    # 纵向木纹线（每隔5-8px一条）
    for wx in range(roof_margin + 5, w - roof_margin - 2, wood_rng.randint(5, 8)):
        pygame.draw.line(surface, barn_wood_dark,
                        (wx, roof_margin + 2),
                        (wx, h - roof_margin - 2), 1)
    # 偶尔的横向支撑梁
    for _ in range(wood_rng.randint(3, 5)):
        by = wood_rng.randint(roof_margin + 8, h - roof_margin - 8)
        pygame.draw.line(surface, barn_wood_light,
                        (roof_margin + 2, by),
                        (w - roof_margin - 2, by), 1)

    # *** 3. 屋脊线 (长形谷仓的中央隆起!) ***
    ridge_y = cy
    ridge_color = tuple(max(0, c - 20) for c in barn_wood_roof)
    pygame.draw.line(surface, ridge_color,
                    (roof_margin + 4, ridge_y),
                    (w - roof_margin - 4, ridge_y), 2)

    # *** 4. 双开门 (从上方看的两个并排矩形!) ***
    door_w = max(16, tile_size // 2.5)
    door_h = max(20, tile_size // 2.2)
    door_x = cx - door_w // 2
    door_y = h - roof_margin - door_h - 2  # 靠近底部（门在一端）

    # 左门扇
    pygame.draw.rect(surface, door_color,
                     (door_x, door_y, door_w // 2 - 2, door_h))
    # 右门扇
    pygame.draw.rect(surface, door_color,
                     (door_x + door_w // 2 + 2, door_y, door_w // 2 - 2, door_h))
    # 门边框和中间缝
    pygame.draw.rect(surface, door_dark,
                     (door_x, door_y, door_w, door_h), 1)
    pygame.draw.line(surface, door_dark,
                    (door_x + door_w // 2, door_y),
                    (door_x + door_w // 2, door_y + door_h), 1)

    # *** 5. 通风口 (屋顶小矩形 - 俯视可见!) ***
    vent_w = max(10, tile_size // 4)
    vent_h = max(6, tile_size // 7)
    vent_x = cx - vent_w // 2
    vent_y = roof_margin + tile_size // 6
    pygame.draw.rect(surface, vent_color,
                     (vent_x, vent_y, vent_w, vent_h))
    pygame.draw.rect(surface, (40, 42, 38),
                     (vent_x, vent_y, vent_w, vent_h), 1)

    # *** 6. 楼层数字 (如果启用) ***
    if show_number and number:
        font_size = min(w, h) // 2
        font = pygame.font.SysFont("arial", font_size, bold=True)
        text = font.render(number, True, (255, 215, 0))  # 金黄色数字
        text_rect = text.get_rect(center=(cx, cy))
        surface.blit(text, text_rect)

    # *** 7. 损坏效果 (屋顶破洞/木板缺失!) ***
    if damage.value >= DamageLevel.LIGHT_DAMAGE.value:
        crack_color = (42, 36, 30)
        rng = random.Random(hash(str(damage) + "barn"))
        num_cracks = damage.value * 3
        for _ in range(num_cracks):
            x1 = rng.randint(roof_margin + 5, w - roof_margin - 5)
            y1 = rng.randint(roof_margin + 5, h - roof_margin - 5)
            length = rng.randint(6, 18)
            angle = rng.uniform(0, 2 * math.pi)
            x2 = x1 + int(length * math.cos(angle))
            y2 = y1 + int(length * math.sin(angle))
            pygame.draw.line(surface, crack_color, (x1, y1), (x2, y2), 1)
        # 重度损坏: 木板缺失区域
        if damage.value >= DamageLevel.HEAVY_DAMAGE.value:
            for _ in range(damage.value):
                hole_x = rng.randint(roof_margin + 10, w - roof_margin - 20)
                hole_y = rng.randint(roof_margin + 10, h - roof_margin - 20)
                hole_w = rng.randint(12, 20)
                hole_h = rng.randint(10, 18)
                pygame.draw.rect(surface, (25, 22, 18),
                               (hole_x, hole_y, hole_w, hole_h))

    # Shadow strips (consistent with standard building rendering)
    shadow_color = tuple(max(0, c - 50) for c in barn_wood_roof)
    shadow_width = max(2, tile_size // 12)
    pygame.draw.rect(surface, shadow_color, (0, h - shadow_width, w, shadow_width))
    pygame.draw.rect(surface, shadow_color, (w - shadow_width, 0, shadow_width, h))

    return surface


def _render_building_interior(
    surface: pygame.Surface,
    w: int,
    h: int,
    tile_size: int,
    building_type: CC2BuildingType,
    damage: DamageLevel,
    occupant_positions: list[tuple[int, int]],
) -> pygame.Surface:
    """Render building INTERIOR view (CC2-style floor + windows).

    *** 核心功能: CC2建筑内部系统 ***
    当单位进入建筑时，CC2切换到此视图:
    - 地板纹理（棋盘格或木地板）
    - 窗户白线轮廓（影响LOS和射击角度）
    - 墙壁暗色边框
    - 占据者位置标记

    CC2原版机制（基于截图分析）:
    - 反坦克炮等重型武器受窗户位置限制
    - 从窗户射出的攻击线有特定角度
    - 室内单位获得掩护加成
    """
    import math

    # === 调色板: 室内模式颜色 ===
    # 地板颜色（基于CC2截图中的棋盘格地板）
    floor_light = (180, 170, 155)   # 浅色木地板/石板
    floor_dark = (145, 135, 122)     # 深色木地板/石板（棋盘格交替!）
    floor_wood = (160, 120, 80)      # 纯木质地板（谷仓等）

    # 窗户和墙壁
    window_outline = (255, 255, 255) # 白色窗户轮廓（CC2特征!）
    wall_color = (90, 85, 78)       # 内部墙壁暗色
    wall_thickness = max(3, tile_size // 10)

    # 门
    door_color = (100, 70, 45)      # 木门颜色

    # 占据者标记
    occupant_marker = (0, 200, 0)   # 绿色圆圈（表示单位位置）

    cx, cy = w // 2, h // 2

    # === 1. 地板纹理（棋盘格/木地板）===
    check_size = max(8, tile_size // 5)  # 棋盘格大小

    # 根据建筑类型选择地板风格
    if building_type in [CC2BuildingType.NORMANDY_BARN, CC2BuildingType.BARN]:
        # 谷仓: 纯木质地板（纵向木板）
        surface.fill(floor_wood)
        wood_rng = random.Random(hash("interior_wood_floor"))
        for wx in range(check_size // 2, w, wood_rng.randint(6, 10)):
            pygame.draw.line(surface,
                           tuple(max(0, c - 20) for c in floor_wood),
                           (wx, 0), (wx, h), 1)
    else:
        # 其他建筑: 棋盘格地板（诺曼底房屋常见石板地）
        for gx in range(0, w, check_size):
            for gy in range(0, h, check_size):
                is_light = ((gx // check_size) + (gy // check_size)) % 2 == 0
                color = floor_light if is_light else floor_dark
                rect = pygame.Rect(gx, gy,
                                  min(check_size, w - gx),
                                  min(check_size, h - gy))
                pygame.draw.rect(surface, color, rect)

        # 地板缝隙线（增加真实感）
        seam_color = tuple(max(0, c - 25) for c in floor_dark)
        for sx in range(0, w, check_size):
            pygame.draw.line(surface, seam_color, (sx, 0), (sx, h), 1)
        for sy in range(0, h, check_size):
            pygame.draw.line(surface, seam_color, (0, sy), (w, sy), 1)

    # === 2. 墙壁边框（内部视角的墙壁）===
    pygame.draw.rect(surface, wall_color,
                     (0, 0, w, wall_thickness))  # 上墙
    pygame.draw.rect(surface, wall_color,
                     (0, h - wall_thickness, w, wall_thickness))  # 下墙
    pygame.draw.rect(surface, wall_color,
                     (0, 0, wall_thickness, h))  # 左墙
    pygame.draw.rect(surface, wall_color,
                     (w - wall_thickness, 0, wall_thickness, h))  # 右墙

    # === 3. 窗户白线轮廓（CC2核心特征！）===
    # 窗户数量根据建筑大小决定
    num_windows = max(1, (w * h) // (tile_size * tile_size * 2))
    window_w = max(12, tile_size // 3)
    window_h = max(8, tile_size // 5)

    win_rng = random.Random(hash(f"interior_windows_{building_type.name}"))
    for i in range(num_windows):
        # 窗户位置（分布在四周墙壁上）
        if i % 4 == 0:  # 上墙窗户
            wx = win_rng.randint(wall_thickness + 8, w - wall_thickness - window_w - 8)
            wy = wall_thickness + 2
        elif i % 4 == 1:  # 下墙窗户
            wx = win_rng.randint(wall_thickness + 8, w - wall_thickness - window_w - 8)
            wy = h - wall_thickness - window_h - 2
        elif i % 4 == 2:  # 左墙窗户
            wx = wall_thickness + 2
            wy = win_rng.randint(wall_thickness + 8, h - wall_thickness - window_h - 8)
        else:  # 右墙窗户
            wx = w - wall_thickness - window_w - 2
            wy = win_rng.randint(wall_thickness + 8, h - wall_thickness - window_h - 8)

        # 绘制白色窗户轮廓（CC2特征！）
        pygame.draw.rect(surface, window_outline,
                         (wx, wy, window_w, window_h), 2)
        # 窗户玻璃（半透明深色）
        glass_color = (60, 70, 90, 180)
        pygame.draw.rect(surface, glass_color,
                         (wx + 2, wy + 2, window_w - 4, window_h - 4))
        # 窗户十字框（有些窗户有的装饰）
        if win_rng.random() > 0.5:
            pygame.draw.line(surface, window_outline,
                            (wx + window_w // 2, wy),
                            (wx + window_w // 2, wy + window_h), 1)
            pygame.draw.line(surface, window_outline,
                            (wx, wy + window_h // 2),
                            (wx + window_w, wy + window_h // 2), 1)

    # === 4. 门的位置标记 ===
    door_w = max(14, tile_size // 3)
    door_h = max(20, tile_size // 2.2)
    door_x = cx - door_w // 2
    door_y = h - wall_thickness - door_h - 2

    pygame.draw.rect(surface, door_color,
                     (door_x, door_y, door_w, door_h))
    pygame.draw.rect(surface, tuple(max(0, c - 30) for c in door_color),
                     (door_x, door_y, door_w, door_h), 2)

    # === 5. 占据者位置标记（如果提供）===
    for ox, oy in occupant_positions:
        if 0 <= ox < w and 0 <= oy < h:
            # 绿色圆圈表示单位位置
            pygame.draw.circle(surface, occupant_marker, (ox, oy), 6, 2)
            # 小方向指示器
            pygame.draw.circle(surface, (0, 180, 0), (ox, oy), 3)

    # === 6. 损坏效果（室内损坏：地板裂缝/破洞）===
    if damage.value >= DamageLevel.LIGHT_DAMAGE.value:
        crack_color = (50, 45, 40)
        dmg_rng = random.Random(hash(f"interior_damage_{damage.value}"))
        num_cracks = damage.value * 4
        for _ in range(num_cracks):
            x1 = dmg_rng.randint(wall_thickness + 10, w - wall_thickness - 10)
            y1 = dmg_rng.randint(wall_thickness + 10, h - wall_thickness - 10)
            length = dmg_rng.randint(8, 20)
            angle = dmg_rng.uniform(0, 2 * math.pi)
            x2 = x1 + int(length * math.cos(angle))
            y2 = y1 + int(length * math.sin(angle))
            pygame.draw.line(surface, crack_color, (x1, y1), (x2, y2), 1)
        # 重度损坏: 地板破洞
        if damage.value >= DamageLevel.HEAVY_DAMAGE.value:
            for _ in range(damage.value):
                hx = dmg_rng.randint(wall_thickness + 15, w - wall_thickness - 25)
                hy = dmg_rng.randint(wall_thickness + 15, h - wall_thickness - 25)
                hw = dmg_rng.randint(15, 25)
                hh = dmg_rng.randint(15, 25)
                pygame.draw.rect(surface, (30, 28, 24),
                               (hx, hy, hw, hh))
                # 破洞边缘
                pygame.draw.rect(surface, (60, 55, 48),
                               (hx, hy, hw, hh), 2)

    return surface
