"""Animation Controller - 管理单位动画状态切换（Phase 2.3）

负责：
- 跟踪每个单位的当前动画状态（idle/walk/attack）
- 根据单位行为自动切换状态
- 管理动画帧更新

设计原则：
- 无状态设计：每帧根据Unit当前状态计算，不持久化
- 简单优先：只支持3个基础状态，无复杂状态机
- 性能优化：缓存计算结果，避免重复查询
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit

logger = logging.getLogger(__name__)


class AnimationController:
    """动画控制器 - 根据单位状态计算当前应显示的动画"""

    # 动画状态定义
    STATE_IDLE = "idle"
    STATE_WALK = "walk"
    STATE_ATTACK = "attack"

    # 攻击动画持续时间（秒）- 攻击后短暂维持attack状态
    ATTACK_ANIMATION_DURATION = 0.3

    def __init__(self):
        """初始化动画控制器"""
        # 记录单位最后攻击时间（用于攻击动画延续）
        self._last_attack_time: dict[str, float] = {}

    def get_animation_state(self, unit: Unit, current_time: float) -> str:
        """获取单位当前应显示的动画状态

        Args:
            unit: 要查询的单位
            current_time: 当前游戏时间（秒）

        Returns:
            动画状态字符串: "idle", "walk", "attack"

        """
        # 优先级1: 正在攻击或刚攻击完（攻击动画）
        if self._is_attacking(unit, current_time):
            return self.STATE_ATTACK

        # 优先级2: 正在移动（行走动画）
        if self._is_moving(unit):
            return self.STATE_WALK

        # 优先级3: 默认待机（待机动画）
        return self.STATE_IDLE

    def mark_attack(self, unit_id: str, current_time: float) -> None:
        """标记单位发起攻击（用于触发攻击动画）

        Args:
            unit_id: 单位ID
            current_time: 攻击发生的游戏时间（秒）

        """
        self._last_attack_time[unit_id] = current_time

    def _is_attacking(self, unit: Unit, current_time: float) -> bool:
        """判断单位是否正在攻击或处于攻击动画状态

        检查条件：
        1. 单位当前状态是ATTACKING
        2. 或最近ATTACK_ANIMATION_DURATION秒内触发过攻击

        """
        # 检查状态机状态（如果单位有state属性）
        if hasattr(unit, "state"):
            from pycc2.domain.entities.unit import UnitState

            if unit.state == UnitState.ATTACKING:
                return True

        # 检查最近攻击时间
        if hasattr(unit, "id"):
            last_attack = self._last_attack_time.get(unit.id, 0.0)
            if current_time - last_attack < self.ATTACK_ANIMATION_DURATION:
                return True

        return False

    def _is_moving(self, unit: Unit) -> bool:
        """判断单位是否正在移动

        检查条件：
        1. 单位当前状态是MOVING
        2. 或有移动目标（move_target）
        3. 或速度大于阈值

        """
        # 检查状态机状态
        if hasattr(unit, "state"):
            from pycc2.domain.entities.unit import UnitState

            if unit.state == UnitState.MOVING:
                return True

        # 检查移动目标
        if hasattr(unit, "move_target") and unit.move_target is not None:
            return True

        # 检查速度（如果单位有velocity属性）
        if hasattr(unit, "velocity"):
            # 速度阈值：0.1像素/帧
            if abs(unit.velocity.x) > 0.1 or abs(unit.velocity.y) > 0.1:
                return True

        return False

    def clear_cache(self) -> None:
        """清空攻击时间缓存（游戏重置/关卡切换时调用）"""
        self._last_attack_time.clear()

    def cleanup_old_entries(self, current_time: float, max_age: float = 10.0) -> None:
        """清理过期的攻击时间记录（防止内存泄漏）

        Args:
            current_time: 当前游戏时间（秒）
            max_age: 记录保留时间（秒），默认10秒

        """
        to_remove = [
            unit_id
            for unit_id, attack_time in self._last_attack_time.items()
            if current_time - attack_time > max_age
        ]
        for unit_id in to_remove:
            del self._last_attack_time[unit_id]
