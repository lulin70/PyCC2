"""单位选择管理器 - 处理单位选择、矩形选择框与编队管理

Sprint 2 Day 6实现：
- BUG-P1-01修复：正确的边界判断（<=而非<）
- FUNC-03实现：多单位矩形选择与编队系统
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit, Faction
    from pycc2.presentation.rendering.camera import Camera


@dataclass
class SelectionRect:
    """矩形选择框数据结构"""
    
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    
    @property
    def min_x(self) -> float:
        """矩形左边界（最小x）"""
        return min(self.start_x, self.end_x)
    
    @property
    def max_x(self) -> float:
        """矩形右边界（最大x）"""
        return max(self.start_x, self.end_x)
    
    @property
    def min_y(self) -> float:
        """矩形上边界（最小y）"""
        return min(self.start_y, self.end_y)
    
    @property
    def max_y(self) -> float:
        """矩形下边界（最大y）"""
        return max(self.start_y, self.end_y)
    
    @property
    def width(self) -> float:
        """矩形宽度"""
        return abs(self.end_x - self.start_x)
    
    @property
    def height(self) -> float:
        """矩形高度"""
        return abs(self.end_y - self.start_y)
    
    def contains_point(self, x: float, y: float) -> bool:
        """判断点是否在矩形内（BUG-P1-01修复：使用<=而非<）
        
        Args:
            x: 点的x坐标
            y: 点的y坐标
            
        Returns:
            True if the point is inside or on the boundary of the rectangle
        """
        return (self.min_x <= x <= self.max_x and
                self.min_y <= y <= self.max_y)


@dataclass
class UnitSelectionManager:
    """单位选择管理器 - 处理单位选择、矩形选择与编队
    
    Features:
    - 矩形拖拽选择
    - 单位编队（Ctrl+数字键1-9）
    - 快速切换编队（数字键）
    - 双击选择同类单位
    """
    
    camera: Camera
    
    # 选择状态
    selected_unit_ids: set[str] = field(default_factory=set)
    selection_rect_start: tuple[float, float] | None = None
    is_selecting: bool = False
    
    # 编队系统（FUNC-03）
    control_groups: dict[int, set[str]] = field(default_factory=dict)
    
    def start_selection(self, screen_x: float, screen_y: float) -> None:
        """开始矩形选择
        
        Args:
            screen_x: 屏幕x坐标
            screen_y: 屏幕y坐标
        """
        self.selection_rect_start = (screen_x, screen_y)
        self.is_selecting = True
        logger.debug(f"Selection started at ({screen_x:.0f}, {screen_y:.0f})")
    
    def update_selection(
        self,
        current_x: float,
        current_y: float,
        units: list[Unit],
        faction_filter: Faction | None = None,
    ) -> set[str]:
        """更新矩形选择（实时显示选中的单位）
        
        Args:
            current_x: 当前鼠标x坐标（屏幕）
            current_y: 当前鼠标y坐标（屏幕）
            units: 所有单位列表
            faction_filter: 阵营过滤（只选择己方单位）
            
        Returns:
            当前选中的单位ID集合
        """
        if not self.is_selecting or self.selection_rect_start is None:
            return set()
        
        # 创建选择矩形
        start_x, start_y = self.selection_rect_start
        rect = SelectionRect(start_x, start_y, current_x, current_y)
        
        # 获取矩形内的单位（使用修复后的边界判断）
        selected_ids = self.get_units_in_rect(rect, units, faction_filter)
        
        logger.debug(f"Selection rect: ({rect.min_x:.0f},{rect.min_y:.0f}) - ({rect.max_x:.0f},{rect.max_y:.0f}), selected: {len(selected_ids)}")
        
        return selected_ids
    
    def finish_selection(
        self,
        end_x: float,
        end_y: float,
        units: list[Unit],
        faction_filter: Faction | None = None,
        add_to_selection: bool = False,
    ) -> set[str]:
        """完成矩形选择
        
        Args:
            end_x: 结束x坐标（屏幕）
            end_y: 结束y坐标（屏幕）
            units: 所有单位列表
            faction_filter: 阵营过滤
            add_to_selection: 是否累加选择（Shift键）
            
        Returns:
            最终选中的单位ID集合
        """
        if not self.is_selecting or self.selection_rect_start is None:
            return set(self.selected_unit_ids)
        
        # 创建最终选择矩形
        start_x, start_y = self.selection_rect_start
        rect = SelectionRect(start_x, start_y, end_x, end_y)
        
        # 获取矩形内的单位
        new_selection = self.get_units_in_rect(rect, units, faction_filter)
        
        # 更新选择
        if add_to_selection:
            self.selected_unit_ids.update(new_selection)
        else:
            self.selected_unit_ids = new_selection
        
        # 重置选择状态
        self.is_selecting = False
        self.selection_rect_start = None
        
        logger.info(f"Selection finished: {len(self.selected_unit_ids)} units selected")
        
        return set(self.selected_unit_ids)
    
    def get_units_in_rect(
        self,
        rect: SelectionRect,
        units: list[Unit],
        faction_filter: Faction | None = None,
    ) -> set[str]:
        """获取矩形内的所有单位（BUG-P1-01修复：正确的边界判断）
        
        Args:
            rect: 选择矩形（屏幕坐标）
            units: 所有单位列表
            faction_filter: 阵营过滤
            
        Returns:
            矩形内的单位ID集合
            
        Implementation Notes:
            - 使用 <= 而非 < 进行边界判断（修复BUG-P1-01）
            - 单位中心点在矩形边界上时也会被选中
            - 先将单位世界坐标转换到屏幕坐标再判断
        """
        selected_ids: set[str] = set()
        
        for unit in units:
            # 阵营过滤
            if faction_filter is not None and unit.faction != faction_filter:
                continue
            
            # 获取单位屏幕坐标
            try:
                # 尝试获取单位位置
                if hasattr(unit, "position") and unit.position is not None:
                    if hasattr(unit.position, "pixel_position"):
                        world_pos = unit.position.pixel_position
                    elif hasattr(unit.position, "tile_position"):
                        # 将tile坐标转换为像素坐标
                        tile_x = getattr(unit.position, "tile_x", 0) or 0
                        tile_y = getattr(unit.position, "tile_y", 0) or 0
                        # 假设每个tile是32x32像素
                        from pycc2.domain.value_objects.vec2 import Vec2
                        world_pos = Vec2(tile_x * 32, tile_y * 32)
                    else:
                        continue
                else:
                    continue
                
                # 转换到屏幕坐标
                screen_pos = self.camera.world_to_screen(world_pos)
                screen_x = screen_pos[0]
                screen_y = screen_pos[1]
                
                # BUG-P1-01修复：使用 <= 而非 < 进行边界判断
                # 这确保边界上的单位也会被选中
                if rect.contains_point(screen_x, screen_y):
                    selected_ids.add(unit.id)
                    logger.debug(f"Unit {unit.id} at ({screen_x:.0f},{screen_y:.0f}) selected")
                
            except (AttributeError, ValueError, TypeError) as e:
                logger.warning(f"Failed to get unit position: {e}")
                continue
        
        return selected_ids
    
    def get_selection_rect_for_render(self) -> SelectionRect | None:
        """获取当前选择矩形用于渲染
        
        Returns:
            选择矩形（如果正在选择），否则None
        """
        if not self.is_selecting or self.selection_rect_start is None:
            return None
        
        # 注意：需要从外部传入当前鼠标位置
        # 这里只返回起始点，调用者需要自己构造完整矩形
        return None
    
    # === 编队系统（FUNC-03） ===
    
    def assign_control_group(self, group_number: int) -> None:
        """分配当前选择到编队
        
        Args:
            group_number: 编队号（1-9）
            
        Raises:
            ValueError: 如果编队号不在1-9范围内
        """
        if not 1 <= group_number <= 9:
            raise ValueError(f"Control group number must be 1-9, got {group_number}")
        
        if not self.selected_unit_ids:
            logger.warning(f"No units selected to assign to group {group_number}")
            return
        
        self.control_groups[group_number] = set(self.selected_unit_ids)
        logger.info(f"Assigned {len(self.selected_unit_ids)} units to control group {group_number}")
    
    def select_control_group(
        self,
        group_number: int,
        add_to_selection: bool = False,
    ) -> set[str]:
        """选择编队
        
        Args:
            group_number: 编队号（1-9）
            add_to_selection: 是否累加选择（Shift键）
            
        Returns:
            选中的单位ID集合
            
        Raises:
            ValueError: 如果编队号不在1-9范围内
        """
        if not 1 <= group_number <= 9:
            raise ValueError(f"Control group number must be 1-9, got {group_number}")
        
        group_ids = self.control_groups.get(group_number, set())
        
        if not group_ids:
            logger.debug(f"Control group {group_number} is empty")
            return set(self.selected_unit_ids) if add_to_selection else set()
        
        if add_to_selection:
            self.selected_unit_ids.update(group_ids)
        else:
            self.selected_unit_ids = set(group_ids)
        
        logger.info(f"Selected control group {group_number}: {len(self.selected_unit_ids)} units")
        
        return set(self.selected_unit_ids)
    
    def clear_selection(self) -> None:
        """清空选择"""
        self.selected_unit_ids.clear()
        self.is_selecting = False
        self.selection_rect_start = None
        logger.debug("Selection cleared")
    
    def add_to_selection(self, unit_id: str) -> None:
        """添加单位到选择（单击添加）
        
        Args:
            unit_id: 单位ID
        """
        self.selected_unit_ids.add(unit_id)
        logger.debug(f"Unit {unit_id} added to selection")
    
    def remove_from_selection(self, unit_id: str) -> None:
        """从选择中移除单位
        
        Args:
            unit_id: 单位ID
        """
        self.selected_unit_ids.discard(unit_id)
        logger.debug(f"Unit {unit_id} removed from selection")
    
    def is_unit_selected(self, unit_id: str) -> bool:
        """判断单位是否被选中
        
        Args:
            unit_id: 单位ID
            
        Returns:
            True if the unit is selected
        """
        return unit_id in self.selected_unit_ids
    
    def get_selected_unit_ids(self) -> set[str]:
        """获取当前选中的单位ID集合
        
        Returns:
            单位ID集合（副本）
        """
        return set(self.selected_unit_ids)
