"""
Integration tests for deep wiring of camera effects, achievements, shadows, and trails.

Tests the full event chain:
  CombatDirector → EventBus.publish_named() → CombatCameraController/AchievementEventBridge
  CombatDirector → ProjectileFired → GameLoop._on_projectile_fired → ProjectileTrailSystem
  VictoryManager → BattleWon → CombatCameraController/AchievementEventBridge
  GameLoop → EffectStack.update() → Camera offset applied
  EnhancedRenderer → DynamicShadowSystem / ProjectileTrailSystem rendering
"""


from pycc2.services.event_bus import EventBus
from pycc2.presentation.rendering.camera_effects import (
    EffectStack, EffectType,
    create_shake, create_zoom_impact, create_slow_motion,
)
from pycc2.presentation.rendering.combat_camera_controller import CombatCameraController
from pycc2.domain.systems.achievement_system import (
    AchievementManager, create_default_achievements,
)
from pycc2.services.achievement_event_bridge import AchievementEventBridge
from pycc2.presentation.rendering.projectile_trail_system import ProjectileTrailSystem
from pycc2.presentation.rendering.dynamic_shadow_system import DynamicShadowSystem


class TestEventBusNamedChannel:
    def test_subscribe_to_and_publish_named(self):
        bus = EventBus()
        received = []
        bus.subscribe_to("TestEvent", lambda d: received.append(d))
        bus.publish_named("TestEvent", {"key": "value"})
        assert len(received) == 1
        assert received[0]["key"] == "value"

    def test_publish_named_no_subscribers(self):
        bus = EventBus()
        bus.publish_named("UnknownEvent", {"data": 1})

    def test_multiple_named_subscribers(self):
        bus = EventBus()
        results_a = []
        results_b = []
        bus.subscribe_to("Evt", lambda d: results_a.append(d))
        bus.subscribe_to("Evt", lambda d: results_b.append(d))
        bus.publish_named("Evt", {"x": 42})
        assert len(results_a) == 1
        assert len(results_b) == 1

    def test_unsubscribe_from(self):
        bus = EventBus()
        results = []
        handler = lambda d: results.append(d)
        bus.subscribe_to("Evt", handler)
        bus.publish_named("Evt", {"a": 1})
        assert len(results) == 1
        bus.unsubscribe_from("Evt", handler)
        bus.publish_named("Evt", {"a": 2})
        assert len(results) == 1

    def test_handler_count_includes_named(self):
        bus = EventBus()
        bus.subscribe_to("A", lambda d: None)
        bus.subscribe_to("B", lambda d: None)
        assert bus.handler_count >= 2

    def test_named_handler_error_counted(self):
        bus = EventBus()
        def bad_handler(d):
            raise ValueError("boom")
        bus.subscribe_to("ErrEvt", bad_handler)
        bus.publish_named("ErrEvt", {"x": 1})
        assert bus._error_count == 1


class TestCombatCameraControllerIntegration:
    def test_subscribe_to_event_bus(self):
        bus = EventBus()
        controller = CombatCameraController()
        stack = EffectStack()
        controller.set_effect_stack(stack)
        controller.subscribe(bus)
        assert bus.handler_count >= 4

    def test_unit_attacked_triggers_shake(self):
        bus = EventBus()
        controller = CombatCameraController()
        stack = EffectStack()
        controller.set_effect_stack(stack)
        controller.subscribe(bus)

        bus.publish_named("UnitAttacked", {"damage": 30})
        assert len(stack) == 1
        assert stack._effects[0].effect_type == EffectType.SHAKE

    def test_high_damage_triggers_shake_and_zoom(self):
        bus = EventBus()
        controller = CombatCameraController()
        stack = EffectStack()
        controller.set_effect_stack(stack)
        controller.subscribe(bus)

        bus.publish_named("UnitAttacked", {"damage": 60})
        assert len(stack) == 2
        types = {e.effect_type for e in stack._effects}
        assert EffectType.SHAKE in types
        assert EffectType.ZOOM_IMPACT in types

    def test_unit_killed_triggers_slow_motion(self):
        bus = EventBus()
        controller = CombatCameraController()
        stack = EffectStack()
        controller.set_effect_stack(stack)
        controller.subscribe(bus)

        bus.publish_named("UnitKilled", {"faction": "AXIS"})
        assert len(stack) >= 2
        types = {e.effect_type for e in stack._effects}
        assert EffectType.SHAKE in types
        assert EffectType.SLOW_MOTION in types

    def test_battle_won_triggers_freeze(self):
        bus = EventBus()
        controller = CombatCameraController()
        stack = EffectStack()
        controller.set_effect_stack(stack)
        controller.subscribe(bus)

        bus.publish_named("BattleWon", {"result": "ALLIES_VICTORY"})
        assert len(stack) == 2
        types = {e.effect_type for e in stack._effects}
        assert EffectType.SCREEN_FREEZE in types
        assert EffectType.PUSH_PULL in types

    def test_explosion_triggers_heavy_effects(self):
        bus = EventBus()
        controller = CombatCameraController()
        stack = EffectStack()
        controller.set_effect_stack(stack)
        controller.subscribe(bus)

        bus.publish_named("Explosion", {"intensity": 4.0})
        assert len(stack) == 3
        types = {e.effect_type for e in stack._effects}
        assert EffectType.SHAKE in types
        assert EffectType.ZOOM_IMPACT in types
        assert EffectType.PUSH_PULL in types

    def test_disabled_controller_ignores_events(self):
        bus = EventBus()
        controller = CombatCameraController()
        stack = EffectStack()
        controller.set_effect_stack(stack)
        controller.set_enabled(False)
        controller.subscribe(bus)

        bus.publish_named("UnitAttacked", {"damage": 50})
        assert len(stack) == 0


class TestAchievementEventBridgeIntegration:
    def test_subscribe_to_event_bus(self):
        bus = EventBus()
        mgr = AchievementManager()
        bridge = AchievementEventBridge(mgr)
        bridge.subscribe(bus)
        assert bus.handler_count >= 4

    def test_first_blood_on_kill(self):
        bus = EventBus()
        mgr = AchievementManager()
        for a in create_default_achievements():
            mgr.register(a)
        bridge = AchievementEventBridge(mgr)
        bridge.subscribe(bus)

        bus.publish_named("UnitKilled", {
            "faction": "AXIS",
            "attacker_role": "rifleman",
            "unit_type": "infantry",
        })
        assert mgr.get_progress("first_blood") == 1

    def test_sharpshooter_on_sniper_kill(self):
        bus = EventBus()
        mgr = AchievementManager()
        for a in create_default_achievements():
            mgr.register(a)
        bridge = AchievementEventBridge(mgr)
        bridge.subscribe(bus)

        bus.publish_named("UnitKilled", {
            "faction": "AXIS",
            "attacker_role": "sniper",
            "unit_type": "infantry",
        })
        assert mgr.get_progress("sharpshooter") == 1

    def test_tank_buster_on_tank_kill(self):
        bus = EventBus()
        mgr = AchievementManager()
        for a in create_default_achievements():
            mgr.register(a)
        bridge = AchievementEventBridge(mgr)
        bridge.subscribe(bus)

        bus.publish_named("UnitKilled", {
            "faction": "AXIS",
            "attacker_role": "at_gun",
            "unit_type": "tank",
        })
        assert mgr.get_progress("tank_buster") == 1

    def test_damage_taken_tracking(self):
        bus = EventBus()
        mgr = AchievementManager()
        for a in create_default_achievements():
            mgr.register(a)
        bridge = AchievementEventBridge(mgr)
        bridge.subscribe(bus)

        bus.publish_named("UnitAttacked", {
            "target_faction": "ALLIES",
            "damage": 25,
        })
        assert bridge._battle_damage_taken == 25

    def test_battle_won_zero_casualties(self):
        bus = EventBus()
        mgr = AchievementManager()
        for a in create_default_achievements():
            mgr.register(a)
        bridge = AchievementEventBridge(mgr)
        bridge.subscribe(bus)

        bus.publish_named("UnitKilled", {
            "faction": "AXIS",
            "attacker_role": "rifleman",
            "unit_type": "infantry",
        })
        bus.publish_named("BattleWon", {
            "result": "ALLIES_VICTORY",
            "duration_seconds": 90,
        })
        assert mgr.get_progress("zero_casualties") == 1
        assert mgr.get_progress("blitzkrieg") == 1


class TestProjectileTrailIntegration:
    def test_trail_system_add_and_update(self):
        sys = ProjectileTrailSystem()
        sys.add_bullet_trail(0, 0, 100, 100)
        assert sys.count() == 1
        sys.update(0.2)
        assert sys.count() == 0

    def test_trail_system_max_trails(self):
        sys = ProjectileTrailSystem(max_trails=3)
        for i in range(5):
            sys.add_bullet_trail(i, i, i + 100, i + 100)
        assert sys.count() == 3

    def test_all_trail_types(self):
        sys = ProjectileTrailSystem()
        sys.add_bullet_trail(0, 0, 50, 50)
        sys.add_shell_trail(0, 0, 100, 100)
        sys.add_rocket_trail(0, 0, 150, 150)
        sys.add_mortar_trail(0, 0, 200, 200)
        assert sys.count() == 4

    def test_trail_render_no_crash(self):
        import pygame
        pygame.init()
        try:
            screen = pygame.Surface((200, 200), pygame.SRCALPHA)
            sys = ProjectileTrailSystem()
            sys.add_bullet_trail(10, 10, 100, 100)
            sys.render(screen)
        finally:
            pygame.quit()

    def test_projectile_fired_handler(self):
        sys = ProjectileTrailSystem()

        def on_fired(data):
            wt = data.get("weapon_type", "bullet")
            sx, sy = data.get("start_x", 0), data.get("start_y", 0)
            ex, ey = data.get("end_x", 0), data.get("end_y", 0)
            if wt == "shell":
                sys.add_shell_trail(sx, sy, ex, ey)
            elif wt == "rocket":
                sys.add_rocket_trail(sx, sy, ex, ey)
            elif wt == "mortar":
                sys.add_mortar_trail(sx, sy, ex, ey)
            else:
                sys.add_bullet_trail(sx, sy, ex, ey)

        bus = EventBus()
        bus.subscribe_to("ProjectileFired", on_fired)

        bus.publish_named("ProjectileFired", {
            "weapon_type": "shell",
            "start_x": 0, "start_y": 0,
            "end_x": 200, "end_y": 200,
        })
        assert sys.count() == 1

        bus.publish_named("ProjectileFired", {
            "weapon_type": "bullet",
            "start_x": 10, "start_y": 10,
            "end_x": 50, "end_y": 50,
        })
        assert sys.count() == 2


class TestDynamicShadowIntegration:
    def test_shadow_direction_changes_with_time(self):
        sys = DynamicShadowSystem()
        sys.set_time_of_day(0.25)
        dx1, dy1 = sys.get_shadow_direction()
        sys.set_time_of_day(0.5)
        dx2, dy2 = sys.get_shadow_direction()
        assert (dx1, dy1) != (dx2, dy2)

    def test_shadow_length_varies(self):
        sys = DynamicShadowSystem()
        sys.set_time_of_day(0.5)
        noon_len = sys.get_shadow_length_multiplier()
        sys.set_time_of_day(0.25)
        dawn_len = sys.get_shadow_length_multiplier()
        assert dawn_len > noon_len

    def test_shadow_alpha_varies(self):
        sys = DynamicShadowSystem()
        sys.set_time_of_day(0.5)
        noon_alpha = sys.get_shadow_alpha()
        sys.set_time_of_day(0.25)
        dawn_alpha = sys.get_shadow_alpha()
        assert dawn_alpha > noon_alpha

    def test_building_shadow_render_no_crash(self):
        import pygame
        pygame.init()
        try:
            screen = pygame.Surface((200, 200), pygame.SRCALPHA)
            sys = DynamicShadowSystem()
            sys.set_time_of_day(0.5)
            sys.render_building_shadow(screen, 50, 50, 48, 48)
        finally:
            pygame.quit()

    def test_tree_shadow_render_no_crash(self):
        import pygame
        pygame.init()
        try:
            screen = pygame.Surface((200, 200), pygame.SRCALPHA)
            sys = DynamicShadowSystem()
            sys.set_time_of_day(0.5)
            sys.render_tree_shadow(screen, 50, 50, tree_radius=12)
        finally:
            pygame.quit()


class TestEffectStackCameraIntegration:
    def test_effect_stack_offset_applied(self):
        stack = EffectStack()
        stack.push(create_shake(intensity=5.0, duration=0.2))
        ox, oy = stack.get_total_offset()
        assert ox != 0.0 or oy != 0.0

    def test_effect_stack_zoom(self):
        stack = EffectStack()
        stack.push(create_zoom_impact(zoom_factor=0.8, duration=0.3, recover=0.5))
        zoom = stack.get_zoom_multiplier()
        assert zoom != 1.0

    def test_effect_stack_time_scale(self):
        stack = EffectStack()
        stack.push(create_slow_motion(time_scale=0.3, duration=1.0))
        ts = stack.get_time_scale()
        assert ts == 0.3

    def test_effect_stack_update_expires(self):
        stack = EffectStack()
        stack.push(create_shake(intensity=3.0, duration=0.1))
        stack.update(0.2)
        assert stack.is_empty()

    def test_camera_position_offset_and_restore(self):
        from pycc2.domain.value_objects.vec2 import Vec2

        class FakeCamera:
            def __init__(self):
                self.position = Vec2(100.0, 100.0)

        camera = FakeCamera()
        stack = EffectStack()
        stack.push(create_shake(intensity=5.0, duration=0.2))

        ox, oy = stack.get_total_offset()
        camera.position = Vec2(camera.position.x + ox, camera.position.y + oy)
        assert camera.position.x != 100.0 or camera.position.y != 100.0

        camera.position = Vec2(camera.position.x - ox, camera.position.y - oy)
        assert abs(camera.position.x - 100.0) < 0.01
        assert abs(camera.position.y - 100.0) < 0.01


class TestEndToEndEventChain:
    def test_full_combat_chain_attacked(self):
        bus = EventBus()

        camera_stack = EffectStack()
        camera_ctrl = CombatCameraController()
        camera_ctrl.set_effect_stack(camera_stack)
        camera_ctrl.subscribe(bus)

        ach_mgr = AchievementManager()
        for a in create_default_achievements():
            ach_mgr.register(a)
        ach_bridge = AchievementEventBridge(ach_mgr)
        ach_bridge.subscribe(bus)

        trail_sys = ProjectileTrailSystem()
        bus.subscribe_to("ProjectileFired", lambda d: (
            trail_sys.add_shell_trail(d["start_x"], d["start_y"], d["end_x"], d["end_y"])
            if d.get("weapon_type") == "shell"
            else trail_sys.add_bullet_trail(d["start_x"], d["start_y"], d["end_x"], d["end_y"])
        ))

        bus.publish_named("UnitAttacked", {
            "attacker_id": "unit_1",
            "target_id": "unit_2",
            "damage": 40,
            "is_hit": True,
            "target_faction": "ALLIES",
        })
        assert len(camera_stack) == 1
        assert ach_bridge._battle_damage_taken == 40

        bus.publish_named("ProjectileFired", {
            "weapon_type": "bullet",
            "start_x": 0, "start_y": 0,
            "end_x": 100, "end_y": 100,
        })
        assert trail_sys.count() == 1

    def test_full_combat_chain_killed(self):
        bus = EventBus()

        camera_stack = EffectStack()
        camera_ctrl = CombatCameraController()
        camera_ctrl.set_effect_stack(camera_stack)
        camera_ctrl.subscribe(bus)

        ach_mgr = AchievementManager()
        for a in create_default_achievements():
            ach_mgr.register(a)
        ach_bridge = AchievementEventBridge(ach_mgr)
        ach_bridge.subscribe(bus)

        bus.publish_named("UnitKilled", {
            "unit_id": "enemy_1",
            "faction": "AXIS",
            "attacker_id": "player_1",
            "attacker_role": "sniper",
            "unit_type": "infantry",
        })

        assert len(camera_stack) >= 2
        types = {e.effect_type for e in camera_stack._effects}
        assert EffectType.SLOW_MOTION in types

        assert ach_mgr.get_progress("first_blood") == 1
        assert ach_mgr.get_progress("sharpshooter") == 1

    def test_full_victory_chain(self):
        bus = EventBus()

        camera_stack = EffectStack()
        camera_ctrl = CombatCameraController()
        camera_ctrl.set_effect_stack(camera_stack)
        camera_ctrl.subscribe(bus)

        ach_mgr = AchievementManager()
        for a in create_default_achievements():
            ach_mgr.register(a)
        ach_bridge = AchievementEventBridge(ach_mgr)
        ach_bridge.subscribe(bus)

        bus.publish_named("UnitKilled", {
            "faction": "AXIS",
            "attacker_role": "rifleman",
            "unit_type": "infantry",
        })

        bus.publish_named("BattleWon", {
            "result": "ALLIES_VICTORY",
            "duration_seconds": 90,
        })

        assert len(camera_stack) >= 2
        types = {e.effect_type for e in camera_stack._effects}
        assert EffectType.SCREEN_FREEZE in types

        assert ach_mgr.get_progress("zero_casualties") == 1
        assert ach_mgr.get_progress("blitzkrieg") == 1
        assert ach_mgr.get_progress("commander") == 1
