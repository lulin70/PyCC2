"""
Tests for Combat Camera Controller.
"""

from pycc2.presentation.rendering.camera_effects import EffectStack, EffectType
from pycc2.presentation.rendering.combat_camera_controller import CombatCameraController


class TestCombatCameraController:
    def test_init(self):
        ctrl = CombatCameraController()
        assert ctrl._camera is None
        assert ctrl._effect_stack is None
        assert ctrl._enabled is True

    def test_set_effect_stack(self):
        ctrl = CombatCameraController()
        stack = EffectStack()
        ctrl.set_effect_stack(stack)
        assert ctrl._effect_stack is stack

    def test_set_enabled(self):
        ctrl = CombatCameraController()
        ctrl.set_enabled(False)
        assert not ctrl._enabled

    def test_on_unit_attacked_light_damage(self):
        ctrl = CombatCameraController()
        stack = EffectStack()
        ctrl.set_effect_stack(stack)
        ctrl._on_unit_attacked({"damage": 5})
        assert len(stack) == 1
        assert stack._effects[0].effect_type == EffectType.SHAKE

    def test_on_unit_attacked_medium_damage(self):
        ctrl = CombatCameraController()
        stack = EffectStack()
        ctrl.set_effect_stack(stack)
        ctrl._on_unit_attacked({"damage": 30})
        assert len(stack) == 1

    def test_on_unit_attacked_heavy_damage(self):
        ctrl = CombatCameraController()
        stack = EffectStack()
        ctrl.set_effect_stack(stack)
        ctrl._on_unit_attacked({"damage": 60})
        assert len(stack) == 2
        types = {e.effect_type for e in stack._effects}
        assert EffectType.SHAKE in types
        assert EffectType.ZOOM_IMPACT in types

    def test_on_unit_killed_axis(self):
        ctrl = CombatCameraController()
        stack = EffectStack()
        ctrl.set_effect_stack(stack)
        ctrl._on_unit_killed({"faction": "AXIS"})
        assert ctrl._kill_count == 1
        assert len(stack) >= 2

    def test_on_unit_killed_allies(self):
        ctrl = CombatCameraController()
        stack = EffectStack()
        ctrl.set_effect_stack(stack)
        ctrl._on_unit_killed({"faction": "ALLIES"})
        assert len(stack) == 1

    def test_on_battle_won(self):
        ctrl = CombatCameraController()
        stack = EffectStack()
        ctrl.set_effect_stack(stack)
        ctrl._on_battle_won({})
        types = {e.effect_type for e in stack._effects}
        assert EffectType.SCREEN_FREEZE in types
        assert EffectType.PUSH_PULL in types

    def test_on_explosion_small(self):
        ctrl = CombatCameraController()
        stack = EffectStack()
        ctrl.set_effect_stack(stack)
        ctrl._on_explosion({"intensity": 1.0})
        assert len(stack) == 1

    def test_on_explosion_large(self):
        ctrl = CombatCameraController()
        stack = EffectStack()
        ctrl.set_effect_stack(stack)
        ctrl._on_explosion({"intensity": 4.0})
        assert len(stack) == 3

    def test_disabled_no_effects(self):
        ctrl = CombatCameraController()
        stack = EffectStack()
        ctrl.set_effect_stack(stack)
        ctrl.set_enabled(False)
        ctrl._on_unit_attacked({"damage": 100})
        assert len(stack) == 0

    def test_no_stack_no_crash(self):
        ctrl = CombatCameraController()
        ctrl._on_unit_attacked({"damage": 100})

    def test_reset_kill_count(self):
        ctrl = CombatCameraController()
        ctrl._kill_count = 5
        ctrl.reset_kill_count()
        assert ctrl._kill_count == 0


class TestAchievementEventBridge:
    def test_init(self):
        from pycc2.domain.systems.achievement_system import AchievementManager
        from pycc2.services.achievement_event_bridge import AchievementEventBridge

        mgr = AchievementManager()
        bridge = AchievementEventBridge(mgr)
        assert bridge._battle_kills == 0

    def test_on_unit_killed_axis_triggers_first_blood(self):
        from pycc2.domain.systems.achievement_system import (
            Achievement,
            AchievementCategory,
            AchievementManager,
        )
        from pycc2.services.achievement_event_bridge import AchievementEventBridge

        mgr = AchievementManager()
        mgr.register(
            Achievement(
                achievement_id="first_blood",
                name="First Blood",
                description="d",
                category=AchievementCategory.COMBAT,
            )
        )
        bridge = AchievementEventBridge(mgr)
        bridge._on_unit_killed({"faction": "AXIS"})
        assert mgr.is_unlocked("first_blood")

    def test_on_unit_killed_tracks_sniper(self):
        from pycc2.domain.systems.achievement_system import (
            Achievement,
            AchievementCategory,
            AchievementManager,
        )
        from pycc2.services.achievement_event_bridge import AchievementEventBridge

        mgr = AchievementManager()
        mgr.register(
            Achievement(
                achievement_id="sharpshooter",
                name="Sharpshooter",
                description="d",
                category=AchievementCategory.COMBAT,
                max_progress=10,
            )
        )
        bridge = AchievementEventBridge(mgr)
        bridge._on_unit_killed({"faction": "AXIS", "attacker_role": "sniper"})
        assert mgr.get_progress("sharpshooter") == 1

    def test_on_unit_killed_tracks_tank(self):
        from pycc2.domain.systems.achievement_system import (
            Achievement,
            AchievementCategory,
            AchievementManager,
        )
        from pycc2.services.achievement_event_bridge import AchievementEventBridge

        mgr = AchievementManager()
        mgr.register(
            Achievement(
                achievement_id="tank_buster",
                name="Tank Buster",
                description="d",
                category=AchievementCategory.COMBAT,
                max_progress=5,
            )
        )
        bridge = AchievementEventBridge(mgr)
        bridge._on_unit_killed({"faction": "AXIS", "unit_type": "tank"})
        assert mgr.get_progress("tank_buster") == 1

    def test_on_battle_won_tracks_commander(self):
        from pycc2.domain.systems.achievement_system import (
            Achievement,
            AchievementCategory,
            AchievementManager,
        )
        from pycc2.services.achievement_event_bridge import AchievementEventBridge

        mgr = AchievementManager()
        mgr.register(
            Achievement(
                achievement_id="commander",
                name="Commander",
                description="d",
                category=AchievementCategory.CAMPAIGN,
                max_progress=25,
            )
        )
        bridge = AchievementEventBridge(mgr)
        bridge._on_battle_won({})
        assert mgr.get_progress("commander") == 1

    def test_on_battle_won_zero_casualties(self):
        from pycc2.domain.systems.achievement_system import (
            Achievement,
            AchievementCategory,
            AchievementManager,
        )
        from pycc2.services.achievement_event_bridge import AchievementEventBridge

        mgr = AchievementManager()
        mgr.register(
            Achievement(
                achievement_id="zero_casualties",
                name="Zero Casualties",
                description="d",
                category=AchievementCategory.SURVIVAL,
            )
        )
        bridge = AchievementEventBridge(mgr)
        bridge._on_battle_won({})
        assert mgr.is_unlocked("zero_casualties")

    def test_reset_battle_stats(self):
        from pycc2.domain.systems.achievement_system import AchievementManager
        from pycc2.services.achievement_event_bridge import AchievementEventBridge

        mgr = AchievementManager()
        bridge = AchievementEventBridge(mgr)
        bridge._battle_kills = 10
        bridge._battle_casualties = 3
        bridge._reset_battle_stats()
        assert bridge._battle_kills == 0
        assert bridge._battle_casualties == 0
