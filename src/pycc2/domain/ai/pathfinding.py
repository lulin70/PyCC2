"""AI System - 智能单位行为和路径规划

提供：
- A*路径规划算法
- 战术决策系统
- 单位AI控制器
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Tuple, Optional
from dataclasses import dataclass
import heapq

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit

from pycc2.domain.value_objects.tile_coord import TileCoord

logger = logging.getLogger(__name__)


@dataclass
class PathNode:
    """路径节点"""
    x: int
    y: int
    g_cost: float  # 从起点到当前节点的代价
    h_cost: float  # 从当前节点到终点的启发式估计
    f_cost: float  # g_cost + h_cost
    parent: Optional[PathNode] = None
    
    def __lt__(self, other):
        return self.f_cost < other.f_cost


class AStarPathfinder:
    """A*路径规划算法"""
    
    def __init__(self, game_map: GameMap):
        """初始化路径规划器
        
        Args:
            game_map: 游戏地图
        """
        self.game_map = game_map
        
    def find_path(
        self,
        start_x: int,
        start_y: int,
        goal_x: int,
        goal_y: int,
        unit: Optional[Unit] = None,
    ) -> List[Tuple[int, int]]:
        """使用A*算法查找路径
        
        Args:
            start_x: 起点X坐标
            start_y: 起点Y坐标
            goal_x: 终点X坐标
            goal_y: 终点Y坐标
            unit: 单位对象（用于检查地形通行性）
            
        Returns:
            路径点列表 [(x, y), ...]，如果无法到达则返回空列表
        """
        # BUG-P0-02修复：起点和终点都需要边界检查
        if not self._is_valid(start_x, start_y):
            logger.warning(f"Start position ({start_x},{start_y}) out of bounds")
            return []
        
        if not self._is_valid(goal_x, goal_y):
            logger.warning(f"Goal position ({goal_x},{goal_y}) out of bounds")
            return []
        
        # 起点终点相同
        if start_x == goal_x and start_y == goal_y:
            return [(start_x, start_y)]
        
        # 初始化
        open_set = []
        closed_set = set()
        
        start_node = PathNode(
            x=start_x,
            y=start_y,
            g_cost=0,
            h_cost=self._heuristic(start_x, start_y, goal_x, goal_y),
            f_cost=0
        )
        start_node.f_cost = start_node.g_cost + start_node.h_cost
        
        heapq.heappush(open_set, start_node)
        
        # A*主循环
        max_iterations = 1000
        iterations = 0
        
        while open_set and iterations < max_iterations:
            iterations += 1
            
            # 取出f_cost最小的节点
            current = heapq.heappop(open_set)
            
            # 到达终点
            if current.x == goal_x and current.y == goal_y:
                return self._reconstruct_path(current)
            
            # 加入closed_set
            closed_set.add((current.x, current.y))
            
            # 检查邻居节点
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:  # 4方向
                neighbor_x = current.x + dx
                neighbor_y = current.y + dy
                
                # 边界检查
                if not self._is_valid(neighbor_x, neighbor_y):
                    continue
                
                # 已访问
                if (neighbor_x, neighbor_y) in closed_set:
                    continue
                
                # 地形检查（简化版）
                if not self._is_walkable(neighbor_x, neighbor_y, unit):
                    continue
                
                # 计算代价
                g_cost = current.g_cost + self._movement_cost(
                    current.x, current.y, neighbor_x, neighbor_y, unit
                )
                h_cost = self._heuristic(neighbor_x, neighbor_y, goal_x, goal_y)
                f_cost = g_cost + h_cost
                
                # 创建邻居节点
                neighbor = PathNode(
                    x=neighbor_x,
                    y=neighbor_y,
                    g_cost=g_cost,
                    h_cost=h_cost,
                    f_cost=f_cost,
                    parent=current
                )
                
                heapq.heappush(open_set, neighbor)
        
        # 未找到路径
        logger.warning(
            f"Path not found from ({start_x},{start_y}) to ({goal_x},{goal_y}) "
            f"after {iterations} iterations"
        )
        return []
    
    def _heuristic(self, x1: int, y1: int, x2: int, y2: int) -> float:
        """启发式函数（曼哈顿距离）"""
        return abs(x1 - x2) + abs(y1 - y2)
    
    def _movement_cost(
        self, x1: int, y1: int, x2: int, y2: int, unit: Optional[Unit]
    ) -> float:
        """移动代价（根据地形类型）"""
        terrain = self.game_map.get_terrain(TileCoord(x2, y2))
        if terrain is None:
            return 999.0  # 不可通行
        
        # 基础代价
        base_cost = 1.0
        
        # 地形修正（使用TerrainType枚举）
        from pycc2.domain.value_objects.terrain_type import TerrainType
        if terrain == TerrainType.ROAD:
            return base_cost * 0.8  # 道路快速
        elif terrain == TerrainType.WOODS:
            return base_cost * 1.5  # 森林缓慢
        elif terrain == TerrainType.WATER:
            return base_cost * 3.0  # 水域很慢
        else:
            return base_cost
    
    def _is_valid(self, x: int, y: int) -> bool:
        """检查坐标是否有效"""
        return 0 <= x < self.game_map.width and 0 <= y < self.game_map.height
    
    def _is_walkable(self, x: int, y: int, unit: Optional[Unit]) -> bool:
        """检查地形是否可通行"""
        if not self._is_valid(x, y):
            return False
        
        terrain = self.game_map.get_terrain(TileCoord(x, y))
        if terrain is None:
            return False
        
        # 简化版：根据TerrainType判断
        # WALL和BUILDING_SOLID不可通行
        from pycc2.domain.value_objects.terrain_type import TerrainType
        return terrain not in [TerrainType.WALL, TerrainType.BUILDING_SOLID]
    
    def _reconstruct_path(self, node: PathNode) -> List[Tuple[int, int]]:
        """重建路径（从终点回溯到起点）"""
        path = []
        current = node
        while current is not None:
            path.append((current.x, current.y))
            current = current.parent
        return list(reversed(path))


class TacticalAI:
    """战术AI决策系统"""
    
    def __init__(self, game_map: GameMap):
        """初始化战术AI
        
        Args:
            game_map: 游戏地图
        """
        self.game_map = game_map
        self.pathfinder = AStarPathfinder(game_map)
    
    def decide_action(self, unit: Unit, enemies: List[Unit]) -> dict:
        """决定单位行动
        
        Args:
            unit: 当前单位
            enemies: 敌方单位列表
            
        Returns:
            行动字典 {"type": "move/attack/hold", "target": (x,y) or unit}
        """
        # 简化版决策树
        if not enemies:
            return {"type": "hold"}
        
        # 找最近的敌人
        closest_enemy = min(
            enemies,
            key=lambda e: abs(e.x - unit.x) + abs(e.y - unit.y)
        )
        
        distance = abs(closest_enemy.x - unit.x) + abs(closest_enemy.y - unit.y)
        
        # 决策逻辑
        if distance <= 1:
            return {"type": "attack", "target": closest_enemy}
        elif distance <= 5:
            # 靠近敌人
            path = self.pathfinder.find_path(
                unit.x, unit.y, closest_enemy.x, closest_enemy.y, unit
            )
            if len(path) > 1:
                return {"type": "move", "target": path[1]}
        
        return {"type": "hold"}
