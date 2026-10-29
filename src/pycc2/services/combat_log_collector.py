"""CombatLog Collector - Subscribe EventBus and collect combat events.

Bug 2 修复：重新接入 CombatLog 系统（v0.6.x 归档后未恢复）
"""

from __future__ import annotations

import logging
import time
from collections import deque
from typing import TYPE_CHECKING

from pycc2._archive.combat_log import CombatEvent, CombatEventType
from pycc2.infrastructure.events.event_bus import EventBus

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    pass  # EventBus now imported at runtime


class CombatLogCollector:
    """订阅 EventBus，收集战斗事件到内存队列。

    Features:
    - 订阅 UnitAttacked / UnitDestroyed / CommandIssued 等事件
    - 维护固定大小的事件队列（FIFO）
    - 提供最近 N 条事件查询接口

    Usage:
        collector = CombatLogCollector(event_bus, max_events=100)
        recent = collector.get_recent_events(20)
    """

    def __init__(self, event_bus: EventBus, max_events: int = 100):
        """Initialize CombatLogCollector.

        Args:
            event_bus: EventBus instance to subscribe
            max_events: Maximum events to keep in memory (FIFO)
        """
        self._event_bus = event_bus
        self._events: deque[CombatEvent] = deque(maxlen=max_events)
        self._subscribe_events()
        logger.info("CombatLogCollector initialized (max_events=%d)", max_events)

    def _subscribe_events(self):
        """Subscribe to EventBus events."""
        # 攻击相关
        self._event_bus.subscribe("UnitAttacked", self._on_unit_attacked)  # type: ignore[arg-type]
        self._event_bus.subscribe("UnitDestroyed", self._on_unit_destroyed)  # type: ignore[arg-type]
        self._event_bus.subscribe("UnitDamaged", self._on_unit_damaged)  # type: ignore[arg-type]

        # 命令相关
        self._event_bus.subscribe("CommandIssued", self._on_command_issued)  # type: ignore[arg-type]
        self._event_bus.subscribe("UnitMoved", self._on_unit_moved)  # type: ignore[arg-type]

        # 士气相关
        self._event_bus.subscribe("MoraleChanged", self._on_morale_changed)  # type: ignore[arg-type]
        self._event_bus.subscribe("UnitSurrendered", self._on_unit_surrendered)  # type: ignore[arg-type]

        # 状态相关
        self._event_bus.subscribe("UnitSuppressed", self._on_unit_suppressed)  # type: ignore[arg-type]

    def _on_unit_attacked(self, event_data: dict):
        """Handle UnitAttacked event."""
        self._events.append(CombatEvent(
            timestamp=time.time(),
            event_type=CombatEventType.ATTACK,
            source_name=event_data.get("attacker_name", "Unknown"),
            target_name=event_data.get("target_name", "Unknown"),
            damage=event_data.get("damage", 0),
        ))

    def _on_unit_destroyed(self, event_data: dict):
        """Handle UnitDestroyed event."""
        self._events.append(CombatEvent(
            timestamp=time.time(),
            event_type=CombatEventType.KILL,
            source_name=event_data.get("killer_name", "Unknown"),
            target_name=event_data.get("victim_name", "Unknown"),
            damage=event_data.get("final_damage", 0),
        ))

    def _on_unit_damaged(self, event_data: dict):
        """Handle UnitDamaged event."""
        hit = event_data.get("hit", True)
        self._events.append(CombatEvent(
            timestamp=time.time(),
            event_type=CombatEventType.HIT if hit else CombatEventType.MISS,
            source_name=event_data.get("attacker_name", "Unknown"),
            target_name=event_data.get("target_name", "Unknown"),
            damage=event_data.get("damage", 0) if hit else 0,
        ))

    def _on_command_issued(self, event_data: dict):
        """Handle CommandIssued event (攻击/移动命令)."""
        cmd_type = event_data.get("command_type", "UNKNOWN")
        unit_name = event_data.get("unit_name", "Unknown")

        # 只记录移动命令（攻击命令已在 UnitAttacked 记录）
        if cmd_type.upper() == "MOVE":
            self._events.append(CombatEvent(
                timestamp=time.time(),
                event_type=CombatEventType.MOVEMENT,
                source_name=unit_name,
                details=f"{unit_name} moving to {event_data.get('target_pos', '?')}",
            ))

    def _on_unit_moved(self, event_data: dict):
        """Handle UnitMoved event."""
        # 可选：记录单位移动完成（避免日志过多，当前不记录）
        pass

    def _on_morale_changed(self, event_data: dict):
        """Handle MoraleChanged event."""
        change = event_data.get("change", 0.0)
        if abs(change) >= 5.0:  # 只记录显著变化
            self._events.append(CombatEvent(
                timestamp=time.time(),
                event_type=CombatEventType.MORALE_CHANGE,
                source_name=event_data.get("unit_name", "Unknown"),
                details=f"Morale {'+' if change > 0 else ''}{change:.1f}",
                morale_change=change,
            ))

    def _on_unit_surrendered(self, event_data: dict):
        """Handle UnitSurrendered event."""
        self._events.append(CombatEvent(
            timestamp=time.time(),
            event_type=CombatEventType.SPECIAL,
            source_name=event_data.get("unit_name", "Unknown"),
            details=f"{event_data.get('unit_name', 'Unknown')} surrendered!",
        ))

    def _on_unit_suppressed(self, event_data: dict):
        """Handle UnitSuppressed event."""
        self._events.append(CombatEvent(
            timestamp=time.time(),
            event_type=CombatEventType.SUPPRESSION,
            target_name=event_data.get("unit_name", "Unknown"),
            details=f"{event_data.get('unit_name', 'Unknown')} is suppressed",
        ))

    def get_recent_events(self, count: int = 20) -> list[CombatEvent]:
        """Get most recent N events.

        Args:
            count: Number of recent events to return

        Returns:
            List of CombatEvent (newest last)
        """
        return list(self._events)[-count:]

    def get_all_events(self) -> list[CombatEvent]:
        """Get all events in memory."""
        return list(self._events)

    def clear(self):
        """Clear all events."""
        self._events.clear()
        logger.debug("CombatLog events cleared")
