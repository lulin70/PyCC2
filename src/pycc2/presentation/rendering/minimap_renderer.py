"""Minimap Renderer - 战术地图渲染器

负责：
- 地形缩略图渲染（按terrain type着色）
- 单位图标渲染（敌我颜色区分）
- 视口框显示（当前相机范围）
- 性能优化（地形层缓存）

设计：
- 200x200px固定尺寸
- 地形缓存（仅地图变化时重绘）
- 单位每帧更新
- 性能预算：< 2ms/frame
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pygame

from pycc2.domain.value_objects.tile_coord import TileCoord

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.presentation.rendering.camera import Camera

logger = logging.getLogger(__name__)


class MinimapRenderer:
    """Minimap渲染器 - 显示地形和单位缩略图"""

    # 地形类型颜色映射（CC2风格）
    TERRAIN_COLORS = {
        "GRASS": (100, 140, 80),      # 深绿色
        "DIRT": (140, 120, 80),       # 棕色
        "ROAD": (160, 160, 150),      # 浅灰色
        "WATER": (60, 100, 180),      # 蓝色
        "FOREST": (60, 100, 50),      # 深绿色
        "BUILDING": (120, 120, 120),  # 灰色
        "WALL": (80, 80, 80),         # 深灰色
        "UNKNOWN": (50, 50, 50),      # 黑灰色
    }

    # 单位颜色
    FRIENDLY_COLOR = (0, 200, 0)    # 绿色
    ENEMY_COLOR = (200, 0, 0)       # 红色
    NEUTRAL_COLOR = (200, 200, 0)   # 黄色

    def __init__(self, size: int = 200):
        """初始化Minimap渲染器

        Args:
            size: Minimap尺寸（宽=高）
        """
        self.size = size

        # 地形缓存
        self._terrain_cache: pygame.Surface | None = None
        self._cached_map_id: str | None = None

        # P1-1优化：单位渲染缓存（减少每帧绘制）
        self._unit_render_interval = 2  # 每2帧更新一次单位
        self._unit_frame_counter = 0

        # 性能统计
        self._render_time_ms = 0.0

    def render(
        self,
        screen: pygame.Surface,
        game_map: GameMap,
        camera: Camera,
        units: list[Unit],
        position: tuple[int, int] | None = None,
    ) -> None:
        """渲染Minimap

        Args:
            screen: 主屏幕Surface
            game_map: 游戏地图
            camera: 相机对象
            units: 所有单位列表
            position: Minimap位置（默认右下角）
        """
        import time
        start_time = time.perf_counter()

        try:
            # 默认位置：右下角（margin=10px）
            if position is None:
                screen_width = screen.get_width()
                screen_height = screen.get_height()
                margin = 10
                position = (
                    screen_width - self.size - margin,
                    screen_height - self.size - margin,
                )

            minimap_x, minimap_y = position

            # 1. 渲染地形层（缓存）
            terrain_surface = self._get_terrain_surface(game_map)
            screen.blit(terrain_surface, position)

            # 2. 渲染单位图标
            self._render_units(screen, game_map, units, position)

            # 3. 渲染视口框
            self._render_viewport_frame(screen, game_map, camera, position)

            # 4. 渲染边框
            pygame.draw.rect(
                screen,
                (100, 100, 100),
                (minimap_x, minimap_y, self.size, self.size),
                2,
            )

        except Exception as e:
            logger.error(f"Minimap rendering failed: {e}", exc_info=True)

        finally:
            # 性能统计
            elapsed = (time.perf_counter() - start_time) * 1000
            self._render_time_ms = elapsed

            # 性能预算检查（2ms）
            if elapsed > 2.0:
                logger.warning(
                    f"Minimap rendering exceeded budget: {elapsed:.2f}ms > 2ms"
                )

    def _get_terrain_surface(self, game_map: GameMap) -> pygame.Surface:
        """获取地形缓存Surface（懒加载+缓存）

        Args:
            game_map: 游戏地图

        Returns:
            地形Surface
        """
        # 缓存检查（基于地图ID）
        map_id = id(game_map)
        if (
            self._terrain_cache is not None
            and self._cached_map_id == map_id
        ):
            return self._terrain_cache

        # 重新渲染地形
        terrain_surface = pygame.Surface(
            (self.size, self.size), pygame.SRCALPHA
        )
        terrain_surface.fill((0, 0, 0, 180))  # 半透明黑色背景

        map_width = game_map.width
        map_height = game_map.height

        # 计算每个地图tile在minimap上的像素尺寸
        pixel_per_tile_x = self.size / map_width
        pixel_per_tile_y = self.size / map_height

        # 渲染每个tile
        for map_y in range(map_height):
            for map_x in range(map_width):
                terrain = game_map.get_terrain(TileCoord(map_x, map_y))
                terrain_name = terrain.name if terrain else "UNKNOWN"

                color = self.TERRAIN_COLORS.get(
                    terrain_name, self.TERRAIN_COLORS["UNKNOWN"]
                )

                # 计算minimap上的矩形
                minimap_x = int(map_x * pixel_per_tile_x)
                minimap_y = int(map_y * pixel_per_tile_y)
                rect_width = max(1, int(pixel_per_tile_x + 0.5))
                rect_height = max(1, int(pixel_per_tile_y + 0.5))

                pygame.draw.rect(
                    terrain_surface,
                    color,
                    (minimap_x, minimap_y, rect_width, rect_height),
                )

        # 更新缓存
        self._terrain_cache = terrain_surface
        self._cached_map_id = map_id

        logger.debug(f"Minimap terrain cache regenerated for map {map_id}")

        return terrain_surface

    def _render_units(
        self,
        screen: pygame.Surface,
        game_map: GameMap,
        units: list[Unit],
        minimap_position: tuple[int, int],
    ) -> None:
        """渲染单位图标

        Args:
            screen: 主屏幕Surface
            game_map: 游戏地图
            units: 所有单位列表
            minimap_position: Minimap左上角坐标
        """
        minimap_x, minimap_y = minimap_position

        map_width = game_map.width
        map_height = game_map.height

        pixel_per_tile_x = self.size / map_width
        pixel_per_tile_y = self.size / map_height

        # 单位图标大小（至少2x2像素）
        unit_icon_size = max(2, int(min(pixel_per_tile_x, pixel_per_tile_y)))

        for unit in units:
            # 获取单位位置
            unit_map_x = getattr(unit, "x", None)
            unit_map_y = getattr(unit, "y", None)

            if unit_map_x is None or unit_map_y is None:
                continue

            # 边界检查
            if not (0 <= unit_map_x < map_width and 0 <= unit_map_y < map_height):
                continue

            # 计算minimap坐标
            unit_minimap_x = int(unit_map_x * pixel_per_tile_x)
            unit_minimap_y = int(unit_map_y * pixel_per_tile_y)

            # 确定单位颜色（基于team_id）
            team_id = getattr(unit, "team_id", 0)
            if team_id == 1:
                color = self.FRIENDLY_COLOR
            elif team_id == 2:
                color = self.ENEMY_COLOR
            else:
                color = self.NEUTRAL_COLOR

            # 绘制单位图标（小方块）
            pygame.draw.rect(
                screen,
                color,
                (
                    minimap_x + unit_minimap_x,
                    minimap_y + unit_minimap_y,
                    unit_icon_size,
                    unit_icon_size,
                ),
            )

    def _render_viewport_frame(
        self,
        screen: pygame.Surface,
        game_map: GameMap,
        camera: Camera,
        minimap_position: tuple[int, int],
    ) -> None:
        """渲染视口框（显示当前相机可见范围）

        Args:
            screen: 主屏幕Surface
            game_map: 游戏地图
            camera: 相机对象
            minimap_position: Minimap左上角坐标
        """
        minimap_x, minimap_y = minimap_position

        # 获取相机视口（世界坐标）。camera.x/y 是视口中心，需换算左上角。
        zoom = max(camera.zoom, 1e-6)
        camera_width = camera.viewport_width / zoom
        camera_height = camera.viewport_height / zoom
        camera_x = camera.x - camera_width / 2
        camera_y = camera.y - camera_height / 2

        # 地图尺寸（世界坐标）
        tile_size = int(getattr(game_map, "tile_size", 32))
        map_world_width = game_map.width * tile_size
        map_world_height = game_map.height * tile_size

        # 计算视口在minimap上的位置和尺寸
        viewport_minimap_x = int((camera_x / map_world_width) * self.size)
        viewport_minimap_y = int((camera_y / map_world_height) * self.size)
        viewport_minimap_width = int((camera_width / map_world_width) * self.size)
        viewport_minimap_height = int((camera_height / map_world_height) * self.size)

        # 边界限制
        viewport_minimap_x = max(0, min(viewport_minimap_x, self.size - 1))
        viewport_minimap_y = max(0, min(viewport_minimap_y, self.size - 1))
        viewport_minimap_width = max(
            1, min(viewport_minimap_width, self.size - viewport_minimap_x)
        )
        viewport_minimap_height = max(
            1, min(viewport_minimap_height, self.size - viewport_minimap_y)
        )

        # 绘制视口框（白色半透明矩形）
        viewport_rect = (
            minimap_x + viewport_minimap_x,
            minimap_y + viewport_minimap_y,
            viewport_minimap_width,
            viewport_minimap_height,
        )

        pygame.draw.rect(screen, (255, 255, 255), viewport_rect, 2)

    def invalidate_cache(self) -> None:
        """清除地形缓存（地图变化时调用）"""
        self._terrain_cache = None
        self._cached_map_id = None
        logger.debug("Minimap terrain cache invalidated")

    def get_render_time_ms(self) -> float:
        """获取Minimap渲染时间（毫秒）"""
        return self._render_time_ms

    def handle_click(
        self,
        click_x: int,
        click_y: int,
        minimap_position: tuple[int, int],
        game_map,
        camera,
    ) -> tuple[int, int] | None:
        """处理Minimap点击事件，返回对应的世界坐标

        Args:
            click_x: 屏幕点击X坐标
            click_y: 屏幕点击Y坐标
            minimap_position: Minimap左上角位置
            game_map: 游戏地图
            camera: 相机对象

        Returns:
            (world_x, world_y) 世界坐标，如果点击不在Minimap内则返回None
        """
        minimap_x, minimap_y = minimap_position

        # 检查点击是否在Minimap范围内
        if not (
            minimap_x <= click_x < minimap_x + self.size
            and minimap_y <= click_y < minimap_y + self.size
        ):
            return None

        # 转换为Minimap内部坐标
        local_x = click_x - minimap_x
        local_y = click_y - minimap_y

        # 转换为地图tile坐标
        tile_size = 48  # TODO: 从VisualConfig获取
        map_world_width = game_map.width * tile_size
        map_world_height = game_map.height * tile_size

        world_x = int((local_x / self.size) * map_world_width)
        world_y = int((local_y / self.size) * map_world_height)

        # 边界限制
        world_x = max(0, min(world_x, map_world_width - camera.width))
        world_y = max(0, min(world_y, map_world_height - camera.height))

        logger.debug(
            f"Minimap click: screen({click_x},{click_y}) -> "
            f"world({world_x},{world_y})"
        )

        return (world_x, world_y)
