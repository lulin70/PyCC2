"""Path Preview Renderer - 路径规划可视化预览

负责在游戏地图上绘制A*路径规划的预览线，帮助玩家可视化单位移动路径。

Architecture:
- 独立组件，可集成到UIOverlayRenderer
- 支持多条路径同时显示
- 性能预算：< 2ms/frame（单条路径<100节点）

Design:
- 路径线：半透明蓝色，宽度2px
- 路径点：小圆点（起点绿色，终点红色，中间蓝色）
- 可选：显示路径长度和移动代价
"""

# STATUS: ORPHAN (TD-080, 2026-11-14) — 0 external src references; superseded by services/path_preview.py (TD-077 INTEGRATE); see docs/TECH_DEBT.md TD-080

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pygame

from pycc2.domain.value_objects.vec2 import Vec2

if TYPE_CHECKING:
    from pycc2.presentation.rendering.camera import Camera

logger = logging.getLogger(__name__)


class PathPreviewRenderer:
    """路径预览渲染器（PERF-01优化：Surface缓存）"""

    def __init__(self):
        """初始化路径预览渲染器"""
        # 渲染配置
        self.path_line_color = (100, 150, 255, 200)  # 半透明蓝色
        self.path_line_width = 2

        self.start_point_color = (0, 255, 0)  # 绿色起点
        self.end_point_color = (255, 0, 0)  # 红色终点
        self.waypoint_color = (100, 150, 255)  # 蓝色中间点
        self.point_radius = 4

        # 性能统计
        self._render_time_ms = 0.0

        # PERF-01: Surface缓存（避免每帧创建）
        self._line_surface_cache: pygame.Surface | None = None
        self._text_cache: pygame.Surface | None = None
        self._cached_path: list[tuple[int, int]] | None = None
        self._screen_size_cache: tuple[int, int] | None = None

        # 字体（用于显示路径长度）
        try:
            self._font_small = pygame.font.Font(None, 14)
        except Exception as e:
            logger.warning(f"Failed to load font: {e}, using default")
            self._font_small = pygame.font.Font(None, 14)

    def render_path(
        self,
        screen: pygame.Surface,
        camera: Camera,
        path: list[tuple[int, int]],
        show_waypoints: bool = True,
        show_path_length: bool = False,
    ) -> None:
        """渲染单条路径（PERF-01优化：Surface缓存）

        Args:
            screen: 主屏幕Surface
            camera: 相机对象（用于世界坐标→屏幕坐标转换）
            path: 路径点列表 [(x, y), ...]（世界坐标）
            show_waypoints: 是否显示路径点
            show_path_length: 是否显示路径长度
        """
        if not path or len(path) < 2:
            return

        import time

        start_time = time.perf_counter()

        try:
            # PERF-01: 检查是否需要重绘（脏标记）
            screen_size = screen.get_size()
            path_changed = self._cached_path != path
            screen_size_changed = self._screen_size_cache != screen_size

            if path_changed or screen_size_changed:
                # 路径或屏幕尺寸变化，重建缓存
                self._cached_path = path
                self._screen_size_cache = screen_size

                # 1. 将世界坐标转换为屏幕坐标
                screen_points = []
                half_tile = Vec2.TILE_SIZE / 2
                for world_x, world_y in path:
                    screen_x, screen_y = camera.world_to_screen(
                        Vec2(world_x * Vec2.TILE_SIZE, world_y * Vec2.TILE_SIZE)
                    )
                    # 中心对齐（tile中心）
                    screen_x += half_tile
                    screen_y += half_tile
                    screen_points.append((screen_x, screen_y))

                # 2. 绘制路径线到缓存Surface
                if len(screen_points) >= 2:
                    # PERF-01: 复用或创建line_surface
                    if (
                        self._line_surface_cache is None
                        or self._line_surface_cache.get_size() != screen_size
                    ):
                        self._line_surface_cache = pygame.Surface(screen_size, pygame.SRCALPHA)
                    else:
                        # 清空缓存Surface
                        self._line_surface_cache.fill((0, 0, 0, 0))

                    pygame.draw.lines(
                        self._line_surface_cache,
                        self.path_line_color,
                        False,  # 不闭合
                        screen_points,
                        self.path_line_width,
                    )

                    # 3. 绘制路径点到缓存Surface（可选）
                    if show_waypoints:
                        for i, (sx, sy) in enumerate(screen_points):
                            # 确定颜色
                            if i == 0:
                                color = self.start_point_color
                            elif i == len(screen_points) - 1:
                                color = self.end_point_color
                            else:
                                color = self.waypoint_color

                            # 绘制圆点
                            pygame.draw.circle(
                                self._line_surface_cache,
                                color,
                                (int(sx), int(sy)),
                                self.point_radius,
                            )
                            # 外边框（黑色）
                            pygame.draw.circle(
                                self._line_surface_cache,
                                (0, 0, 0),
                                (int(sx), int(sy)),
                                self.point_radius,
                                1,
                            )

                # 4. 文字缓存（可选）
                if show_path_length and len(path) > 0:
                    length_text = self._font_small.render(
                        f"Path: {len(path)} tiles", True, (255, 255, 255)
                    )
                    end_x, end_y = screen_points[-1]
                    text_bg_rect = length_text.get_rect(topleft=(end_x + 10, end_y - 10))

                    # 创建文字缓存Surface
                    self._text_cache = pygame.Surface(
                        (text_bg_rect.width + 4, text_bg_rect.height + 2), pygame.SRCALPHA
                    )
                    self._text_cache.fill((0, 0, 0, 180))
                    self._text_cache.blit(length_text, (2, 1))
                    self._text_cache_position = (text_bg_rect.x - 2, text_bg_rect.y - 1)

            # PERF-01: 使用缓存绘制（无论是否重建）
            if self._line_surface_cache is not None:
                screen.blit(self._line_surface_cache, (0, 0))

            if show_path_length and self._text_cache is not None:
                screen.blit(self._text_cache, self._text_cache_position)

        except Exception as e:
            logger.error(f"Path rendering failed: {e}", exc_info=True)

        finally:
            # 性能统计
            elapsed = (time.perf_counter() - start_time) * 1000
            self._render_time_ms = elapsed

            # 性能预算检查（2ms）
            if elapsed > 2.0:
                logger.warning(
                    f"Path rendering exceeded budget: {elapsed:.2f}ms > 2ms "
                    f"(path length: {len(path)})"
                )

    def render_multiple_paths(
        self,
        screen: pygame.Surface,
        camera: Camera,
        paths: list[list[tuple[int, int]]],
        show_waypoints: bool = True,
    ) -> None:
        """渲染多条路径（批量）

        Args:
            screen: 主屏幕Surface
            camera: 相机对象
            paths: 路径列表（多条路径）
            show_waypoints: 是否显示路径点
        """
        for path in paths:
            self.render_path(screen, camera, path, show_waypoints, show_path_length=False)

    def get_render_time_ms(self) -> float:
        """获取上次渲染时间（毫秒）"""
        return self._render_time_ms
