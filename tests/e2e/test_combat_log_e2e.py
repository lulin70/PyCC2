"""E2E Tests for Bug 2 (CombatLog) - Combat log panel display and event recording.

验证 CombatLog 系统重新接入后的功能：
- 右下角日志面板可见
- 攻击/击杀/移动事件正确记录
- 滚动功能可用（可选）
"""

import time

import pytest


class TestCombatLogE2E:
    """Bug 2 (CombatLog missing) E2E verification."""

    def test_combat_log_panel_visible(self, init_game_with_units):
        """验证战斗日志面板可见（右下角）。"""
        game_loop = init_game_with_units  # fixture 直接返回 game_loop

        # 验证 CombatLogPanel 已初始化
        assert hasattr(game_loop, "combat_log_panel"), "CombatLogPanel not initialized"
        assert hasattr(game_loop, "combat_log_collector"), "CombatLogCollector not initialized"

        panel = game_loop.combat_log_panel

        # 验证面板位置（右下角）
        assert panel.x > 0, f"Panel x position invalid: {panel.x}"
        assert panel.y > 0, f"Panel y position invalid: {panel.y}"
        assert panel.PANEL_WIDTH == 350
        assert panel.PANEL_HEIGHT == 200

    def test_combat_log_records_attack_events(self, init_game_with_units):
        """验证攻击事件被正确记录。"""
        game_loop = init_game_with_units  # fixture 直接返回 game_loop
        collector = game_loop.combat_log_collector

        # 清空现有事件
        collector.clear()

        # 模拟攻击事件
        game_loop.event_bus.publish_named(
            "UnitAttacked",
            {"attacker_name": "US Infantry", "target_name": "German MG", "damage": 15},
        )

        time.sleep(0.1)  # 等待事件处理

        # 验证事件记录
        events = collector.get_recent_events(10)
        assert len(events) >= 1, f"Attack event not recorded, got {len(events)} events"

        attack_event = events[-1]
        assert attack_event.event_type.name == "ATTACK"
        assert "US Infantry" in attack_event.source_name
        assert "German MG" in attack_event.target_name
        assert attack_event.damage == 15

    def test_combat_log_records_kill_events(self, init_game_with_units):
        """验证击杀事件被正确记录。"""
        game_loop = init_game_with_units  # fixture 直接返回 game_loop
        collector = game_loop.combat_log_collector

        collector.clear()

        # 模拟击杀事件
        game_loop.event_bus.publish_named(
            "UnitDestroyed",
            {"killer_name": "US Sniper", "victim_name": "German Officer", "final_damage": 100},
        )

        time.sleep(0.1)

        events = collector.get_recent_events(10)
        assert len(events) >= 1

        kill_event = events[-1]
        assert kill_event.event_type.name == "KILL"
        assert "US Sniper" in kill_event.source_name
        assert "German Officer" in kill_event.target_name
        assert kill_event.damage == 100

    def test_combat_log_scrollable(self, init_game_with_units):
        """验证日志面板支持滚动。"""
        game_loop = init_game_with_units  # fixture 直接返回 game_loop
        panel = game_loop.combat_log_panel

        # 初始滚动位置
        initial_offset = panel._scroll_offset
        assert initial_offset == 0, "Initial scroll offset should be 0"

        # 模拟向上滚动
        panel.handle_scroll(1)
        assert panel._scroll_offset == 1, f"Scroll up failed: offset={panel._scroll_offset}"

        # 模拟向下滚动
        panel.handle_scroll(-1)
        assert panel._scroll_offset == 0, f"Scroll down failed: offset={panel._scroll_offset}"

        # 重置滚动
        panel.handle_scroll(5)
        panel.reset_scroll()
        assert panel._scroll_offset == 0, "Reset scroll failed"

    def test_combat_log_event_types_coverage(self, init_game_with_units):
        """验证所有事件类型都能正确记录。"""
        game_loop = init_game_with_units  # fixture 直接返回 game_loop
        collector = game_loop.combat_log_collector

        collector.clear()

        # 模拟 9 种事件类型
        test_events = [
            ("UnitAttacked", {"attacker_name": "A", "target_name": "B", "damage": 10}),
            ("UnitDestroyed", {"killer_name": "C", "victim_name": "D", "final_damage": 50}),
            ("UnitDamaged", {"attacker_name": "E", "target_name": "F", "hit": True, "damage": 20}),
            ("CommandIssued", {"command_type": "MOVE", "unit_name": "G", "target_pos": "(10,20)"}),
            ("MoraleChanged", {"unit_name": "H", "change": -10.0}),
            ("UnitSurrendered", {"unit_name": "I"}),
            ("UnitSuppressed", {"unit_name": "J"}),
        ]

        for event_name, event_data in test_events:
            game_loop.event_bus.publish_named(event_name, event_data)  # 修复：使用 publish_named
            time.sleep(0.05)

        events = collector.get_all_events()
        assert len(events) >= 7, f"Expected 7+ events, got {len(events)}"

        # 验证事件类型覆盖
        event_types = {e.event_type.name for e in events}
        expected_types = {
            "ATTACK",
            "KILL",
            "HIT",
            "MOVEMENT",
            "MORALE_CHANGE",
            "SPECIAL",
            "SUPPRESSION",
        }
        assert expected_types.issubset(event_types), (
            f"Missing event types: {expected_types - event_types}"
        )


# Fixtures（需要在 conftest.py 中定义或内联定义）


@pytest.fixture
def init_game_with_units():
    """Initialize GameLoop with test units and EventBus."""
    from pathlib import Path

    import pygame
    from conftest import GameLoopFactory

    pygame.init()
    screen = pygame.display.set_mode((1280, 720))

    # 使用最简单的测试地图
    test_map = Path(__file__).parent.parent.parent / "data" / "maps" / "tutorial.json"

    factory = GameLoopFactory(screen, map_path=str(test_map))
    return factory.game_loop
