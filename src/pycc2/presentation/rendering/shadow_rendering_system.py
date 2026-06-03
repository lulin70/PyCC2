"""
阴影渲染系统 (Shadow Rendering System)

从 EnhancedRenderer 中提取的阴影渲染逻辑。
负责统一管理建筑、树木、单位的阴影渲染，使用 ShadowRenderer 类实现。

职责分离：
- EnhancedRenderer: 主渲染流程协调
- ShadowRenderingSystem: 阴影细节渲染委托
- ShadowRenderer (lighting_system.py): 底层阴影绘制原语

Created: v0.3.9 (extracted from enhanced_renderer.py ~230 lines)
"""

import logging
from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.presentation.rendering.lighting_system import ShadowRenderer

logger = logging.getLogger(__name__)


class ShadowRenderingSystem:
    """
    统一阴影渲染系统。

    封装所有阴影相关的渲染逻辑，提供清晰的接口给 EnhancedRenderer 调用。
    
    使用示例:
        shadow_sys = ShadowRenderingSystem(shadow_renderer, tile_size=32)
        shadow_sys.render_all_shadows(offscreen_surface, game_map, camera, units)
    """

    def __init__(self, shadow_renderer: 'ShadowRenderer', tile_size: int = 32):
        """
        初始化阴影渲染系统。

        Args:
            shadow_renderer: ShadowRenderer 实例（来自 lighting_system.py）
            tile_size: 地图瓦片大小（像素）
        """
        self._shadow_renderer = shadow_renderer
        self.TILE_SIZE = tile_size

    def render_building_shadows(
        self, 
        surface: pygame.Surface, 
        game_map: 'GameMap', 
        camera: 'Camera'
    ) -> int:
        """
        渲染所有建筑的东南方向阴影。

        统一阴影方向：使用 ShadowRenderer 类，阴影投射向东南（右下）
        与 TopDownLightingConfig.light_angle = -π/4（左上光源）保持一致

        Args:
            surface: 目标渲染表面（offscreen buffer）
            game_map: 游戏地图
            camera: 相机对象

        Returns:
            渲染的建筑阴影数量
        """
        if surface is None or self._shadow_renderer is None:
            return 0

        try:
            buildings_found = 0
            for y in range(game_map.height):
                for x in range(game_map.width):
                    terrain_int = int(game_map.tile_grid[y, x])

                    # TerrainType: 4=BUILDING_ENTERABLE, 5=BUILDING_SOLID
                    has_building = terrain_int in (4, 5)

                    if has_building:
                        from pycc2.domain.value_objects.vec2 import Vec2
                        world_pos = Vec2(x * self.TILE_SIZE, y * self.TILE_SIZE)
                        screen_pos = camera.world_to_screen(world_pos)
                        sx, sy = int(screen_pos[0]), int(screen_pos[1])

                        self._shadow_renderer.render_building_shadow(
                            surface,
                            sx, sy,
                            self.TILE_SIZE,
                            self.TILE_SIZE // 2
                        )
                        buildings_found += 1

            if buildings_found > 0:
                logger.debug(f"Rendered {buildings_found} building shadows")

            return buildings_found
        except RuntimeError as e:
            logger.warning(f"Failed to render building shadows: {e}")
            return 0

    def render_tree_shadows(
        self, 
        surface: pygame.Surface, 
        game_map: 'GameMap', 
        camera: 'Camera'
    ) -> int:
        """
        渲染所有树木/植被的东南方向阴影。

        Args:
            surface: 目标渲染表面
            game_map: 游戏地图
            camera: 相机对象

        Returns:
            渲染的树木阴影数量
        """
        if surface is None or self._shadow_renderer is None:
            return 0

        try:
            trees_found = 0
            for y in range(game_map.height):
                for x in range(game_map.width):
                    terrain_int = int(game_map.tile_grid[y, x])

                    # TerrainType: 3=WOODS, 7=HEDGE
                    is_tree = terrain_int in (3, 7)

                    if is_tree:
                        from pycc2.domain.value_objects.vec2 import Vec2
                        world_pos = Vec2(x * self.TILE_SIZE, y * self.TILE_SIZE)
                        screen_pos = camera.world_to_screen(world_pos)
                        sx, sy = int(screen_pos[0]), int(screen_pos[1])

                        # 根据地形类型确定树木大小
                        tree_size = "medium"
                        if terrain_int == 3:  # WOODS
                            tree_size = "large"
                        elif terrain_int == 7:  # HEDGE
                            tree_size = "small"

                        self._shadow_renderer.render_tree_shadow(
                            surface,
                            sx, sy,
                            tree_size
                        )
                        trees_found += 1

            if trees_found > 0:
                logger.debug(f"Rendered {trees_found} tree shadows")

            return trees_found
        except RuntimeError as e:
            logger.warning(f"Failed to render tree shadows: {e}")
            return 0

    def render_unit_shadows(
        self, 
        surface: pygame.Surface, 
        units: list['Unit'], 
        camera: 'Camera'
    ) -> int:
        """
        渲染所有单位和载具的阴影。

        支持多种单位类型检测：
        - 载具：tank, vehicle, halftrack, jeep, truck
        - 步兵：其他所有类型

        支持隐藏/潜行状态检测（阴影会变淡）

        Args:
            surface: 目标渲染表面
            units: 单位列表
            camera: 相机对象

        Returns:
            渲染的单位阴影数量
        """
        if surface is None or self._shadow_renderer is None:
            return 0

        if len(units) == 0:
            return 0

        try:
            units_rendered = 0
            for unit in units:
                cx, cy = self._get_unit_screen_position(unit, camera)
                
                if cx is None or cy is None:
                    continue

                unit_type_str = self._get_unit_type_string(unit)
                is_hidden = self._check_unit_hidden(unit)
                is_vehicle = self._detect_vehicle(unit_type_str)

                if is_vehicle:
                    unit_w = getattr(unit, 'width', 24) or 24
                    unit_h = getattr(unit, 'height', 16) or 16
                    
                    self._shadow_renderer.render_vehicle_shadow(
                        surface,
                        cx, cy,
                        unit_w, unit_h,
                        is_hidden=is_hidden
                    )
                else:
                    self._shadow_renderer.render_unit_shadow(
                        surface,
                        cx, cy,
                        unit_type=unit_type_str,
                        is_hidden=is_hidden
                    )
                
                units_rendered += 1

            if units_rendered > 0:
                logger.debug(f"Rendered {units_rendered} unit shadows")

            return units_rendered
        except RuntimeError as e:
            logger.warning(f"Failed to render unit shadows: {e}")
            return 0

    def debug_render_shadow_bounds(
        self, 
        surface: pygame.Surface, 
        game_map: 'GameMap', 
        camera: 'Camera'
    ) -> None:
        """
        调试模式：绘制阴影位置的边界框（不依赖透明度）。

        用于验证阴影位置是否正确，在 debug_mode=True 时调用。

        Args:
            surface: 目标渲染表面
            game_map: 游戏地图
            camera: 相机对象
        """
        if surface is None:
            return

        import pygame as pg

        try:
            BUILDING_DEBUG_COLOR = (255, 0, 0)      # Red for buildings
            TREE_DEBUG_COLOR = (0, 255, 0)           # Green for trees
            UNIT_DEBUG_COLOR = (0, 0, 255)           # Blue for units

            # 绘制建筑阴影边界
            for y in range(game_map.height):
                for x in range(game_map.width):
                    tile = game_map.get_tile(x, y)
                    if tile is None:
                        continue

                    if self._is_building_tile(tile):
                        world_pos = (x * self.TILE_SIZE, y * self.TILE_SIZE)
                        screen_pos = camera.world_to_screen(world_pos)
                        sx, sy = int(screen_pos[0]), int(screen_pos[1])

                        shadow_rect = pg.Rect(
                            sx + 6, 
                            sy + self.TILE_SIZE // 2 + 3,
                            max(24, int(self.TILE_SIZE * 0.9)), 
                            6
                        )
                        pg.draw.rect(surface, BUILDING_DEBUG_COLOR, shadow_rect, 2)

            # 绘制树木阴影边界
            for y in range(game_map.height):
                for x in range(game_map.width):
                    tile = game_map.get_tile(x, y)
                    if tile is None:
                        continue

                    if self._is_tree_tile(tile):
                        world_pos = (x * self.TILE_SIZE, y * self.TILE_SIZE)
                        screen_pos = camera.world_to_screen(world_pos)
                        sx, sy = int(screen_pos[0]), int(screen_pos[1])

                        shadow_radius = max(6, int(self.TILE_SIZE * 0.25))
                        pg.draw.circle(surface, TREE_DEBUG_COLOR, (sx + 4, sy + 2), shadow_radius, 2)

        except Exception as e:
            logger.debug(f"Debug shadow bounds rendering failed: {e}")

    def _get_unit_screen_position(
        self, 
        unit: 'Unit', 
        camera: 'Camera'
    ) -> tuple[int | None, int | None]:
        """
        获取单位在屏幕上的坐标（带防御性编程）。

        支持多种位置获取策略：
        1. pixel_position（优先）
        2. tile_position / tile_x, tile_y（回退）

        Args:
            unit: 单位对象
            camera: 相机对象

        Returns:
            (cx, cy) 屏幕坐标，如果无法获取则返回 (None, None)
        """
        cx, cy = None, None

        if hasattr(unit, 'position') and unit.position is not None:
            if hasattr(unit.position, 'pixel_position'):
                try:
                    pos = camera.world_to_screen(unit.position.pixel_position)
                    cx, cy = int(pos[0]), int(pos[1])
                except (AttributeError, ValueError):
                    pass

            if (cx is None or cy is None) and hasattr(unit.position, 'tile_x'):
                try:
                    tile_x = getattr(unit.position, 'tile_x', None)
                    tile_y = getattr(unit.position, 'tile_y', None)
                    if tile_x is not None and tile_y is not None:
                        from pycc2.domain.value_objects.vec2 import Vec2
                        world_pos = Vec2(tile_x * 16, tile_y * 16)
                        pos = camera.world_to_screen(world_pos)
                        cx, cy = int(pos[0]), int(pos[1])
                except Exception as e:
                    logger.warning("Unit position lookup failed: %s", e)

        return cx, cy

    @staticmethod
    def _get_unit_type_string(unit: 'Unit') -> str:
        """获取单位类型的字符串表示。"""
        unit_type = getattr(unit, 'unit_type', 'infantry')
        return str(unit_type).lower()

    @staticmethod
    def _check_unit_hidden(unit: 'Unit') -> bool:
        """检查单位是否处于隐藏/潜行状态。"""
        return getattr(unit, 'is_hidden', False) or \
               getattr(unit, 'is_sneaking', False)

    @staticmethod
    def _detect_vehicle(unit_type_str: str) -> bool:
        """检测是否为载具类型。"""
        return any(v in unit_type_str for v in 
                   ['tank', 'vehicle', 'halftrack', 'jeep', 'truck'])

    @staticmethod
    def _is_building_tile(tile) -> bool:
        """检查瓦片是否为建筑类型。"""
        has_building = (
            hasattr(tile, 'building') and tile.building is not None
        ) or (
            hasattr(tile, 'terrain_type') and
            str(tile.terrain_type).lower() in ['building', 'house', 'barn', 'church']
        )

        if not has_building:
            try:
                tt = getattr(tile, 'terrain_type', None)
                if tt is not None:
                    tt_val = int(tt) if isinstance(tt, (int, float)) else -1
                    if tt_val >= 20:
                        has_building = True
            except (ValueError, TypeError):
                pass

        if not has_building:
            tile_name = str(getattr(tile, 'name', '')).lower()
            if any(w in tile_name for w in ['build', 'house', 'church', 'barn', 'factory']):
                has_building = True

        return has_building

    @staticmethod
    def _is_tree_tile(tile) -> bool:
        """检查瓦片是否为树木/植被类型."""
        terrain_str = str(getattr(tile, 'terrain_type', '')).lower()
        is_tree = any(t in terrain_str for t in 
                      ['tree', 'forest', 'woods', 'hedgerow', 'orchard'])

        if not is_tree:
            try:
                tt = getattr(tile, 'terrain_type', None)
                if tt is not None:
                    tt_val = int(tt) if isinstance(tt, (int, float)) else -1
                    if 3 <= tt_val <= 7:
                        is_tree = True
            except (ValueError, TypeError):
                pass

        if not is_tree:
            tile_name = str(getattr(tile, 'name', '')).lower()
            if any(w in tile_name for w in ['tree', 'forest', 'wood', 'hedge', 'bush', 'orchard']):
                is_tree = True

        return is_tree