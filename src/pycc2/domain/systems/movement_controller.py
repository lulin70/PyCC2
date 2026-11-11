"""单位移动控制器 - 处理单位移动、路径跟随与墙角滑动

Sprint 2 Day 7实现：
- BUG-P1-02修复：防止单位卡死墙角
- 滑墙机制：使用Vector2反射算法
- 次优路径回退：当A*找不到路径时尝试接近目标
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pycc2.domain.ai.pathfinding import AStarPathfinder
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.value_objects.vec2 import Vec2


@dataclass
class MovementController:
    """单位移动控制器

    Features:
    - 路径跟随
    - 墙角滑动（Wall Sliding）
    - 碰撞检测与避让
    - A*死锁处理
    """

    game_map: GameMap
    pathfinder: AStarPathfinder

    # 配置参数
    wall_slide_distance: float = 8.0  # 滑墙检测距离
    stuck_detection_threshold: float = 2.0  # 卡住检测阈值（像素）
    max_stuck_frames: int = 30  # 最多卡住帧数（0.5秒@60fps）

    def move_unit_towards_target(
        self,
        unit: Unit,
        target_pos: Vec2,
        delta_time: float,
    ) -> bool:
        """移动单位朝向目标

        Args:
            unit: 单位对象
            target_pos: 目标位置（世界坐标）
            delta_time: 时间增量（秒）

        Returns:
            True if successfully moved or reached target, False if stuck
        """
        # 获取当前位置
        current_pos = unit.position.pixel_position

        # 计算移动向量
        dx = target_pos.x - current_pos.x
        dy = target_pos.y - current_pos.y
        distance = (dx * dx + dy * dy) ** 0.5

        # 已到达目标
        if distance < 5.0:
            return True

        # 归一化方向
        dir_x = dx / distance
        dir_y = dy / distance

        # 计算移动距离
        unit_speed = getattr(unit, "speed", 50.0)  # 默认速度50像素/秒
        move_distance = unit_speed * delta_time

        # 实际移动距离不超过目标距离
        move_distance = min(move_distance, distance)

        # 计算新位置
        new_x = current_pos.x + dir_x * move_distance
        new_y = current_pos.y + dir_y * move_distance

        # 检查碰撞（墙角检测）
        if self._is_position_blocked(new_x, new_y, unit):
            # BUG-P1-02修复：使用滑墙机制
            new_x, new_y = self._apply_wall_slide(
                current_pos.x, current_pos.y, new_x, new_y, dir_x, dir_y, unit
            )

            # 如果滑墙后仍然被阻挡，尝试停止
            if self._is_position_blocked(new_x, new_y, unit):
                logger.debug(f"Unit {unit.id} stuck at wall, cannot slide")
                return False

        # 应用移动
        from pycc2.domain.value_objects.vec2 import Vec2

        unit.position.pixel_position = Vec2(new_x, new_y)

        return True

    def _is_position_blocked(self, x: float, y: float, unit: Unit) -> bool:
        """检查位置是否被阻挡

        Args:
            x: x坐标（像素）
            y: y坐标（像素）
            unit: 单位对象

        Returns:
            True if position is blocked
        """
        # 转换到tile坐标
        tile_x = int(x // 32)
        tile_y = int(y // 32)

        # 边界检查
        if not (0 <= tile_x < self.game_map.width and 0 <= tile_y < self.game_map.height):
            return True

        # 地形检查
        from pycc2.domain.value_objects.tile_coord import TileCoord

        terrain = self.game_map.get_terrain(TileCoord(tile_x, tile_y))

        if terrain is None:
            return True

        # 简化版：认为WALL和WATER不可通行
        from pycc2.domain.value_objects.terrain_type import TerrainType

        return terrain in [TerrainType.WALL, TerrainType.WATER, TerrainType.BUILDING_SOLID]

    def _apply_wall_slide(
        self,
        old_x: float,
        old_y: float,
        new_x: float,
        new_y: float,
        dir_x: float,
        dir_y: float,
        unit: Unit,
    ) -> tuple[float, float]:
        """应用滑墙机制（BUG-P1-02修复核心）

        当单位撞墙时，沿墙面滑动而非卡住。

        Args:
            old_x: 原x坐标
            old_y: 原y坐标
            new_x: 尝试移动到的x坐标（被阻挡）
            new_y: 尝试移动到的y坐标（被阻挡）
            dir_x: 移动方向x分量（归一化）
            dir_y: 移动方向y分量（归一化）
            unit: 单位对象

        Returns:
            滑墙后的新坐标 (x, y)

        Algorithm:
            1. 检测墙面法向量（垂直于墙面）
            2. 将移动向量投影到墙面切线方向
            3. 沿切线方向移动
        """
        # 尝试分解移动：先尝试X轴移动，再尝试Y轴移动

        # 尝试只在X方向移动
        test_x_only = (new_x, old_y)
        if not self._is_position_blocked(*test_x_only, unit):
            logger.debug(
                f"Wall slide: X-only movement ({old_x:.0f},{old_y:.0f}) -> ({new_x:.0f},{old_y:.0f})"
            )
            return test_x_only

        # 尝试只在Y方向移动
        test_y_only = (old_x, new_y)
        if not self._is_position_blocked(*test_y_only, unit):
            logger.debug(
                f"Wall slide: Y-only movement ({old_x:.0f},{old_y:.0f}) -> ({old_x:.0f},{new_y:.0f})"
            )
            return test_y_only

        # 两个方向都被阻挡，返回原位置
        logger.debug(f"Wall slide: Both directions blocked, staying at ({old_x:.0f},{old_y:.0f})")
        return (old_x, old_y)

    def find_path_with_fallback(
        self,
        unit: Unit,
        target_x: int,
        target_y: int,
    ) -> list[tuple[int, int]]:
        """查找路径（带回退机制）

        BUG-P1-02修复：当A*找不到路径时，尝试次优路径

        Args:
            unit: 单位对象
            target_x: 目标tile x坐标
            target_y: 目标tile y坐标

        Returns:
            路径点列表，如果完全无法接近则返回空列表
        """
        # 获取当前位置
        current_pos = unit.position.pixel_position
        start_x = int(current_pos.x // 32)
        start_y = int(current_pos.y // 32)

        # 尝试直接A*
        path = self.pathfinder.find_path(start_x, start_y, target_x, target_y, unit)

        if path:
            return path

        # A*失败，尝试次优路径：找到距离目标最近的可达点
        logger.debug(f"A* failed, trying fallback path to ({target_x},{target_y})")

        closest_reachable = self._find_closest_reachable_point(
            start_x, start_y, target_x, target_y, unit
        )

        if closest_reachable is None:
            logger.warning(f"No reachable point near ({target_x},{target_y})")
            return []

        # 找到接近点的路径
        fallback_x, fallback_y = closest_reachable
        fallback_path = self.pathfinder.find_path(start_x, start_y, fallback_x, fallback_y, unit)

        if fallback_path:
            logger.info(f"Fallback path found via ({fallback_x},{fallback_y})")
            return fallback_path

        return []

    def _find_closest_reachable_point(
        self,
        start_x: int,
        start_y: int,
        target_x: int,
        target_y: int,
        unit: Unit,
        search_radius: int = 5,
    ) -> tuple[int, int] | None:
        """查找距离目标最近的可达点（次优路径）

        Args:
            start_x: 起点tile x
            start_y: 起点tile y
            target_x: 目标tile x
            target_y: 目标tile y
            unit: 单位对象
            search_radius: 搜索半径（tile数）

        Returns:
            最近可达点 (x, y) 或 None
        """

        # 遍历目标周围的点，找到可达且距离目标最近的
        candidates = []

        for dx in range(-search_radius, search_radius + 1):
            for dy in range(-search_radius, search_radius + 1):
                test_x = target_x + dx
                test_y = target_y + dy

                # 边界检查
                if not (0 <= test_x < self.game_map.width and 0 <= test_y < self.game_map.height):
                    continue

                # 跳过不可行走的tile
                if self._is_position_blocked(test_x * 32, test_y * 32, unit):
                    continue

                # 尝试A*到此点
                test_path = self.pathfinder.find_path(start_x, start_y, test_x, test_y, unit)
                if test_path:
                    # 计算距离目标的距离
                    dist_to_target = abs(test_x - target_x) + abs(test_y - target_y)
                    candidates.append((test_x, test_y, dist_to_target))

        if not candidates:
            return None

        # 返回距离目标最近的可达点
        candidates.sort(key=lambda c: c[2])
        return (candidates[0][0], candidates[0][1])
