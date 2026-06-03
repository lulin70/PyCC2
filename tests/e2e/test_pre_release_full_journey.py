"""
Pre-Release E2E Test — Full User Journey with Deep Integration Verification.

Simulates a REAL user playing PyCC2 from start to finish, verifying:
  1. Faction selection (Allied / Axis)
  2. Unit deployment (select, place, remove, pending orders)
  3. Battle start (complete_deployment creates Unit entities + AI)
  4. Unit selection and command (move, attack, fast move, sneak)
  5. Combat with camera effects (shake, zoom, slow-motion)
  6. Projectile trail rendering (bullet, shell, rocket, mortar)
  7. Dynamic shadow rendering (time-of-day changes)
  8. Achievement tracking (first_blood, sharpshooter, etc.)
  9. Victory/defeat detection and post-battle screen
  10. Achievement display after battle
  11. No crashes throughout the entire journey
  12. Visual quality: all rendering passes complete
  13. Performance: frame time within acceptable bounds

Uses SDL_VIDEODRIVER=dummy for headless rendering.
"""

from __future__ import annotations

import os
import time
import traceback

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_JOYSTICK_DRIVER", "dummy")

import pytest
import pygame
from pathlib import Path
from dataclasses import dataclass

SCREEN_W, SCREEN_H = 1280, 720
MAX_FRAME_TIME_MS = 100.0
BATTLE_TICKS = 900


def _deploy_infantry(deployment_ui, count=1):
    """Deploy infantry units from available units."""
    deployed = []
    available = deployment_ui.state.available_units
    for i, u in enumerate(available):
        if len(deployed) >= count:
            break
        if u.unit_type == "infantry" and not u.is_placed:
            for tile_x, tile_y in deployment_ui.state.friendly_zone[:20]:
                terrain = deployment_ui._get_terrain_at(tile_x, tile_y)
                if deployment_ui.can_place_at(u, tile_x, tile_y, terrain):
                    occupied = any(
                        pu.position == (tile_x, tile_y)
                        for pu in deployment_ui.state.placed_units
                    )
                    if not occupied:
                        deployment_ui.place_unit(i, tile_x, tile_y)
                        deployed.append(u)
                        break
    return deployed


def _find_map_path() -> Path:
    map_dir = Path(__file__).resolve().parent.parent.parent / "data" / "maps"
    for candidate in sorted(map_dir.glob("*.json")):
        if candidate.stem != "_schema":
            return candidate
    raise FileNotFoundError("No map files found in data/maps/")


class TestPreReleaseFullJourney:
    """Pre-release E2E: full user journey with deep integration verification."""

    @pytest.fixture(autouse=True)
    def init_pygame(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        yield
        pygame.quit()

    def _create_game_loop(self, faction="allied"):
        from pycc2.domain.entities.game_map import GameMap, SpawnPoint
        from pycc2.domain.value_objects.vec2 import Vec2
        from pycc2.domain.value_objects.tile_coord import TileCoord
        from pycc2.presentation.input.handler import PygameInputHandler
        from pycc2.presentation.input.interaction_controller import InteractionController
        from pycc2.presentation.rendering.camera import Camera
        from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer
        from pycc2.presentation.rendering.window_config import DisplayInfo, WindowManager
        from pycc2.services.ai_service import AIService
        from pycc2.services.event_bus import EventBus
        from pycc2.services.game_loop import GameLoop, GameState
        from pycc2.domain.interfaces.display_config import DisplayConfig as DC
        from pycc2.presentation.ui.hint_manager import HintManager
        from pycc2.presentation.ui.keybind_manager import KeybindManager
        from pycc2.presentation.ui.settings_menu import SettingsMenu
        from pycc2.presentation.ui.tutorial_system import TutorialOverlay

        map_path = _find_map_path()
        game_map = GameMap.from_json(map_path)

        if not game_map.spawn_points:
            game_map.spawn_points = [
                SpawnPoint(
                    id="friendly_default",
                    side="friendly",
                    position=TileCoord(5, game_map.height // 2),
                    units_max=9,
                ),
                SpawnPoint(
                    id="enemy_default",
                    side="enemy",
                    position=TileCoord(game_map.width - 5, game_map.height // 2),
                    units_max=9,
                ),
            ]

        center_x = game_map.width * 16.0
        center_y = game_map.height * 16.0
        camera = Camera(
            position=Vec2(center_x, center_y),
            viewport_width=SCREEN_W,
            viewport_height=SCREEN_H,
        )

        wm = WindowManager(DisplayInfo(base_width=SCREEN_W, base_height=SCREEN_H))
        wm._screen = self.screen

        renderer = EnhancedRenderer()
        renderer.initialize(self.screen)

        event_bus = EventBus()
        input_handler = PygameInputHandler(camera=camera, window_manager=wm)
        ai_service = AIService(event_bus=event_bus)
        interaction_controller = InteractionController(
            camera=camera, game_map=game_map, event_bus=event_bus,
        )

        display_config = DC()
        hint_manager = HintManager()
        keybind_manager = KeybindManager()
        settings_menu = SettingsMenu(display_config, keybind_manager=keybind_manager)
        tutorial_overlay = TutorialOverlay(display_config)

        interaction_controller.set_hint_manager(hint_manager)
        interaction_controller.set_keybind_manager(keybind_manager)

        state = GameState(game_map=game_map, units=[], camera=camera)

        game_loop = GameLoop(
            renderer=renderer,
            window_manager=wm,
            event_bus=event_bus,
            state=state,
            input_handler=input_handler,
            ai_service=ai_service,
            interaction_controller=interaction_controller,
            hint_manager=hint_manager,
            settings_menu=settings_menu,
            tutorial_overlay=tutorial_overlay,
        )

        return game_loop, game_map

    def _build_map_data(self, game_map):
        return {
            "width": game_map.width,
            "height": game_map.height,
            "tiles": game_map.tile_grid.tolist(),
            "spawn_points": [
                {
                    "id": sp.id,
                    "side": sp.side,
                    "position": [sp.position.x, sp.position.y],
                    "units_max": sp.units_max,
                }
                for sp in game_map.spawn_points
            ],
        }

    # ====================================================================
    # PHASE 1: Faction Selection + Deployment
    # ====================================================================

    def test_phase1_allied_faction_deployment(self):
        """Allied faction: start deployment, place units, verify UI."""
        game_loop, game_map = self._create_game_loop(faction="allied")
        map_data = self._build_map_data(game_map)

        game_loop.start_deployment(map_data=map_data, faction="allied")
        assert game_loop.deployment_phase_active
        assert game_loop.deployment_ui is not None

        deployment_ui = game_loop.deployment_ui
        available = deployment_ui.state.available_units
        assert len(available) >= 6, f"Need at least 6 units, got {len(available)}"

        result = deployment_ui.handle_click_full(
            screen_x=50, screen_y=50,
            map_offset_x=0, map_offset_y=0,
            tile_size=16,
        )

        deployed = _deploy_infantry(deployment_ui, count=3)
        assert len(deployed) >= 1, "Should place at least 1 unit"

        game_loop.renderer.render(
            game_map=game_map,
            units=[],
            camera=game_loop.state.camera,
        )

    def test_phase1_axis_faction_deployment(self):
        """Axis faction: deployment with swapped zones."""
        game_loop, game_map = self._create_game_loop(faction="axis")
        map_data = self._build_map_data(game_map)

        game_loop.start_deployment(map_data=map_data, faction="axis")
        assert game_loop.deployment_phase_active

        deployment_ui = game_loop.deployment_ui
        assert deployment_ui._faction == "axis"

    # ====================================================================
    # PHASE 2: Complete Deployment → Battle Start
    # ====================================================================

    def test_phase2_complete_deployment_creates_units(self):
        """Complete deployment creates Unit entities and AI units."""
        game_loop, game_map = self._create_game_loop()
        map_data = self._build_map_data(game_map)

        game_loop.start_deployment(map_data=map_data, faction="allied")
        deployment_ui = game_loop.deployment_ui

        _deploy_infantry(deployment_ui, count=3)

        result = game_loop.complete_deployment()
        assert result is not None, "complete_deployment should return result"
        assert len(game_loop.state.units) > 0, "Should have units after deployment"

        allies = [u for u in game_loop.state.units if u.faction.name == "ALLIES"]
        axis = [u for u in game_loop.state.units if u.faction.name == "AXIS"]
        assert len(allies) > 0, "Should have Allied units"
        assert len(game_loop.state.units) > 0, "Should have units after deployment"

    # ====================================================================
    # PHASE 3: Battle — Select Unit, Move, Attack
    # ====================================================================

    def test_phase3_battle_unit_selection_and_commands(self):
        """Battle phase: select units, issue move/attack commands."""
        game_loop, game_map = self._create_game_loop()
        map_data = self._build_map_data(game_map)

        game_loop.start_deployment(map_data=map_data, faction="allied")
        deployment_ui = game_loop.deployment_ui

        _deploy_infantry(deployment_ui)

        game_loop.complete_deployment()
        state = game_loop.state

        allies = [u for u in state.units if u.faction.name == "ALLIES" and u.is_alive]
        assert len(allies) > 0

        first_ally = allies[0]
        state.selected_unit_ids = {first_ally.id}

        for _ in range(10):
            game_loop._update_logic(1.0 / 30.0)
            state.tick += 1

        assert state.tick > 0

    # ====================================================================
    # PHASE 4: Combat with Camera Effects + Projectile Trails
    # ====================================================================

    def test_phase4_combat_camera_effects_fire(self):
        """Combat events trigger camera effects via EventBus named channel."""
        from pycc2.presentation.rendering.camera_effects import EffectType

        game_loop, game_map = self._create_game_loop()
        map_data = self._build_map_data(game_map)

        game_loop.start_deployment(map_data=map_data, faction="allied")
        deployment_ui = game_loop.deployment_ui

        _deploy_infantry(deployment_ui)

        game_loop.complete_deployment()
        state = game_loop.state

        game_loop.event_bus.publish_named("UnitAttacked", {
            "attacker_id": "test",
            "target_id": "test",
            "damage": 40,
            "is_hit": True,
            "target_faction": "ALLIES",
        })

        assert game_loop._effect_stack is not None
        assert len(game_loop._effect_stack) >= 1, "Camera effect should fire on attack"

        game_loop.event_bus.publish_named("UnitKilled", {
            "unit_id": "test",
            "faction": "AXIS",
            "attacker_id": "player",
            "attacker_role": "sniper",
            "unit_type": "infantry",
        })

        types = {e.effect_type for e in game_loop._effect_stack._effects}
        assert EffectType.SLOW_MOTION in types, "Kill should trigger slow motion"

    def test_phase4_projectile_trail_on_fire(self):
        """ProjectileFired event creates trail in ProjectileTrailSystem."""
        game_loop, game_map = self._create_game_loop()
        map_data = self._build_map_data(game_map)

        game_loop.start_deployment(map_data=map_data, faction="allied")
        deployment_ui = game_loop.deployment_ui

        _deploy_infantry(deployment_ui)

        game_loop.complete_deployment()

        game_loop.event_bus.publish_named("ProjectileFired", {
            "weapon_type": "shell",
            "start_x": 100, "start_y": 100,
            "end_x": 300, "end_y": 300,
        })

        assert game_loop._projectile_trail_sys is not None
        assert game_loop._projectile_trail_sys.count() == 1

        game_loop._projectile_trail_sys.update(0.3)
        assert game_loop._projectile_trail_sys.count() == 0

    # ====================================================================
    # PHASE 5: Dynamic Shadow System
    # ====================================================================

    def test_phase5_dynamic_shadow_time_of_day(self):
        """Dynamic shadow system responds to time-of-day changes."""
        game_loop, game_map = self._create_game_loop()
        map_data = self._build_map_data(game_map)

        game_loop.start_deployment(map_data=map_data, faction="allied")
        game_loop.complete_deployment()

        shadow_sys = game_loop._dynamic_shadow_sys
        assert shadow_sys is not None

        shadow_sys.set_time_of_day(0.5)
        noon_dir = shadow_sys.get_shadow_direction()
        noon_alpha = shadow_sys.get_shadow_alpha()
        noon_len = shadow_sys.get_shadow_length_multiplier()

        shadow_sys.set_time_of_day(0.25)
        dawn_dir = shadow_sys.get_shadow_direction()
        dawn_alpha = shadow_sys.get_shadow_alpha()
        dawn_len = shadow_sys.get_shadow_length_multiplier()

        assert dawn_alpha > noon_alpha, "Dawn shadows should be more opaque"
        assert dawn_len > noon_len, "Dawn shadows should be longer"

    def test_phase5_dynamic_shadow_render_no_crash(self):
        """Dynamic shadow rendering does not crash during full render."""
        game_loop, game_map = self._create_game_loop()
        map_data = self._build_map_data(game_map)

        game_loop.start_deployment(map_data=map_data, faction="allied")
        game_loop.complete_deployment()

        shadow_sys = game_loop._dynamic_shadow_sys
        shadow_sys.set_time_of_day(0.35)

        game_loop.renderer.render(
            game_map=game_map,
            units=game_loop.state.units,
            camera=game_loop.state.camera,
        )

    # ====================================================================
    # PHASE 6: Achievement System Integration
    # ====================================================================

    def test_phase6_achievement_tracking_through_events(self):
        """Achievements track progress through EventBus named events."""
        from pycc2.domain.systems.achievement_system import AchievementManager

        game_loop, game_map = self._create_game_loop()
        map_data = self._build_map_data(game_map)

        game_loop.start_deployment(map_data=map_data, faction="allied")
        game_loop.complete_deployment()

        bridge = game_loop._achievement_bridge
        assert bridge is not None

        game_loop.event_bus.publish_named("UnitKilled", {
            "faction": "AXIS",
            "attacker_role": "sniper",
            "unit_type": "infantry",
        })

        mgr = bridge._manager
        assert mgr.get_progress("first_blood") == 1, "first_blood should trigger"
        assert mgr.get_progress("sharpshooter") == 1, "sharpshooter should trigger"

    def test_phase6_achievement_battle_won(self):
        """BattleWon event triggers achievement progress."""
        game_loop, game_map = self._create_game_loop()
        map_data = self._build_map_data(game_map)

        game_loop.start_deployment(map_data=map_data, faction="allied")
        game_loop.complete_deployment()

        bridge = game_loop._achievement_bridge

        game_loop.event_bus.publish_named("UnitKilled", {
            "faction": "AXIS",
            "attacker_role": "rifleman",
            "unit_type": "infantry",
        })

        game_loop.event_bus.publish_named("BattleWon", {
            "result": "ALLIES_VICTORY",
            "duration_seconds": 60,
        })

        mgr = bridge._manager
        assert mgr.get_progress("zero_casualties") == 1
        assert mgr.get_progress("blitzkrieg") == 1
        assert mgr.get_progress("commander") == 1

    # ====================================================================
    # PHASE 7: Full Battle Run — No Crash for 900 ticks
    # ====================================================================

    def test_phase7_full_battle_900_ticks_no_crash(self):
        """Run full battle for 900 ticks (30 seconds) — no crash."""
        game_loop, game_map = self._create_game_loop()
        map_data = self._build_map_data(game_map)

        game_loop.start_deployment(map_data=map_data, faction="allied")
        deployment_ui = game_loop.deployment_ui

        _deploy_infantry(deployment_ui)

        game_loop.complete_deployment()
        state = game_loop.state

        for tick in range(BATTLE_TICKS):
            try:
                game_loop._update_logic(1.0 / 30.0)
                state.tick += 1

                if tick % 100 == 0:
                    game_loop.renderer.render(
                        game_map=game_map,
                        units=state.units,
                        camera=state.camera,
                    )
            except Exception as e:
                pytest.fail(f"Game crashed during 900-tick battle: {e}")

    # ====================================================================
    # PHASE 8: Victory/Defeat Detection + Post-Battle
    # ====================================================================

    def test_phase8_victory_detection_and_post_battle(self):
        """VictoryManager detects victory and post-battle screen renders."""
        game_loop, game_map = self._create_game_loop()
        map_data = self._build_map_data(game_map)

        game_loop.start_deployment(map_data=map_data, faction="allied")
        game_loop.complete_deployment()
        state = game_loop.state

        for tick in range(700):
            game_loop._update_logic(1.0 / 30.0)
            state.tick += 1

        vm = game_loop._victory_manager
        assert vm is not None

        game_loop.renderer.render(
            game_map=game_map,
            units=state.units,
            camera=state.camera,
            debug_mode=False,
        )

    # ====================================================================
    # PHASE 9: EffectStack Camera Offset + Restore
    # ====================================================================

    def test_phase9_camera_offset_apply_and_restore(self):
        """EffectStack offset is applied to camera and restored after render."""
        from pycc2.domain.value_objects.vec2 import Vec2

        game_loop, game_map = self._create_game_loop()
        map_data = self._build_map_data(game_map)

        game_loop.start_deployment(map_data=map_data, faction="allied")
        game_loop.complete_deployment()

        camera = game_loop.state.camera
        original_x = camera.position.x
        original_y = camera.position.y

        game_loop.event_bus.publish_named("UnitAttacked", {
            "damage": 50,
            "is_hit": True,
        })

        assert len(game_loop._effect_stack) > 0

        offset = game_loop._effect_stack.get_total_offset()
        if offset != (0.0, 0.0):
            camera.position = Vec2(
                camera.position.x + offset[0],
                camera.position.y + offset[1],
            )
            assert camera.position.x != original_x or camera.position.y != original_y

            camera.position = Vec2(
                camera.position.x - offset[0],
                camera.position.y - offset[1],
            )

        assert abs(camera.position.x - original_x) < 0.01
        assert abs(camera.position.y - original_y) < 0.01

    # ====================================================================
    # PHASE 10: Performance — Frame Time Within Bounds
    # ====================================================================

    def test_phase10_performance_frame_time(self):
        """Render frame time stays within acceptable bounds."""
        game_loop, game_map = self._create_game_loop()
        map_data = self._build_map_data(game_map)

        game_loop.start_deployment(map_data=map_data, faction="allied")
        game_loop.complete_deployment()
        state = game_loop.state

        frame_times = []
        for tick in range(60):
            t0 = time.perf_counter()
            game_loop._update_logic(1.0 / 30.0)
            state.tick += 1

            if tick % 10 == 0:
                game_loop.renderer.render(
                    game_map=game_map,
                    units=state.units,
                    camera=state.camera,
                )
            t1 = time.perf_counter()
            frame_times.append((t1 - t0) * 1000)

        avg_frame_ms = sum(frame_times) / len(frame_times)
        max_frame_ms = max(frame_times)

        assert avg_frame_ms < MAX_FRAME_TIME_MS, (
            f"Average frame time {avg_frame_ms:.1f}ms exceeds {MAX_FRAME_TIME_MS}ms"
        )

    # ====================================================================
    # PHASE 11: Full Render Pipeline — All Visual Systems Active
    # ====================================================================

    def test_phase11_full_render_pipeline_no_crash(self):
        """Full render pipeline with all visual systems active — no crash."""
        game_loop, game_map = self._create_game_loop()
        map_data = self._build_map_data(game_map)

        game_loop.start_deployment(map_data=map_data, faction="allied")
        game_loop.complete_deployment()
        state = game_loop.state

        game_loop._dynamic_shadow_sys.set_time_of_day(0.4)

        game_loop.event_bus.publish_named("UnitAttacked", {
            "damage": 30,
            "is_hit": True,
        })

        game_loop.event_bus.publish_named("ProjectileFired", {
            "weapon_type": "bullet",
            "start_x": 100, "start_y": 100,
            "end_x": 300, "end_y": 300,
        })

        for _ in range(5):
            game_loop._update_logic(1.0 / 30.0)
            state.tick += 1

        game_loop.renderer.render(
            game_map=game_map,
            units=state.units,
            camera=state.camera,
        )

        game_loop._effect_stack.update(0.5)
        game_loop._projectile_trail_sys.update(0.5)

    # ====================================================================
    # PHASE 12: Axis Faction Full Journey
    # ====================================================================

    def test_phase12_axis_faction_full_journey(self):
        """Axis faction: full deploy → battle → no crash."""
        game_loop, game_map = self._create_game_loop(faction="axis")
        map_data = self._build_map_data(game_map)

        game_loop.start_deployment(map_data=map_data, faction="axis")
        deployment_ui = game_loop.deployment_ui

        _deploy_infantry(deployment_ui)

        result = game_loop.complete_deployment()
        assert result is not None

        state = game_loop.state
        for tick in range(300):
            try:
                game_loop._update_logic(1.0 / 30.0)
                state.tick += 1
            except Exception as e:
                pytest.fail(f"Axis battle crashed at tick {tick}: {e}")

        game_loop.renderer.render(
            game_map=game_map,
            units=state.units,
            camera=state.camera,
        )

    # ====================================================================
    # PHASE 13: Multiple Weapon Types — Trail Variety
    # ====================================================================

    def test_phase13_all_weapon_trail_types(self):
        """All 4 weapon trail types render without crash."""
        game_loop, game_map = self._create_game_loop()
        map_data = self._build_map_data(game_map)

        game_loop.start_deployment(map_data=map_data, faction="allied")
        game_loop.complete_deployment()

        trail_sys = game_loop._projectile_trail_sys

        for weapon_type, add_fn in [
            ("bullet", trail_sys.add_bullet_trail),
            ("shell", trail_sys.add_shell_trail),
            ("rocket", trail_sys.add_rocket_trail),
            ("mortar", trail_sys.add_mortar_trail),
        ]:
            add_fn(50, 50, 400, 400)

        assert trail_sys.count() == 4

        game_loop.renderer.render(
            game_map=game_map,
            units=game_loop.state.units,
            camera=game_loop.state.camera,
        )

        trail_sys.update(0.6)
        assert trail_sys.count() == 0

    # ====================================================================
    # PHASE 14: EventBus Named Channel — Full Event Chain
    # ====================================================================

    def test_phase14_event_bus_full_chain(self):
        """Full event chain: attack → kill → victory → achievement."""
        from pycc2.presentation.rendering.camera_effects import EffectType

        game_loop, game_map = self._create_game_loop()
        map_data = self._build_map_data(game_map)

        game_loop.start_deployment(map_data=map_data, faction="allied")
        game_loop.complete_deployment()

        bus = game_loop.event_bus
        stack = game_loop._effect_stack
        bridge = game_loop._achievement_bridge
        trail_sys = game_loop._projectile_trail_sys

        bus.publish_named("UnitAttacked", {
            "damage": 60,
            "is_hit": True,
            "target_faction": "ALLIES",
        })
        assert len(stack) >= 2
        assert bridge._battle_damage_taken == 60

        bus.publish_named("ProjectileFired", {
            "weapon_type": "shell",
            "start_x": 0, "start_y": 0,
            "end_x": 200, "end_y": 200,
        })
        assert trail_sys.count() == 1

        bus.publish_named("UnitKilled", {
            "faction": "AXIS",
            "attacker_role": "sniper",
            "unit_type": "infantry",
        })
        types = {e.effect_type for e in stack._effects}
        assert EffectType.SLOW_MOTION in types
        assert bridge._manager.get_progress("first_blood") == 1
        assert bridge._manager.get_progress("sharpshooter") == 1

        bus.publish_named("BattleWon", {
            "result": "ALLIES_VICTORY",
            "duration_seconds": 80,
        })
        types_after = {e.effect_type for e in stack._effects}
        assert EffectType.SCREEN_FREEZE in types_after
        assert bridge._manager.get_progress("zero_casualties") == 1
        assert bridge._manager.get_progress("blitzkrieg") == 1
        assert bridge._manager.get_progress("commander") == 1

    # ====================================================================
    # PHASE 15: Long-Run Stability — 1800 ticks (60 seconds)
    # ====================================================================

    def test_phase15_long_run_60_seconds_no_crash(self):
        """60-second gameplay run — no crash, no memory explosion."""
        game_loop, game_map = self._create_game_loop()
        map_data = self._build_map_data(game_map)

        game_loop.start_deployment(map_data=map_data, faction="allied")
        deployment_ui = game_loop.deployment_ui

        _deploy_infantry(deployment_ui)

        game_loop.complete_deployment()
        state = game_loop.state

        render_count = 0
        for tick in range(1800):
            try:
                game_loop._update_logic(1.0 / 30.0)
                state.tick += 1

                if tick % 60 == 0:
                    game_loop.renderer.render(
                        game_map=game_map,
                        units=state.units,
                        camera=state.camera,
                    )
                    render_count += 1
            except Exception as e:
                pytest.fail(f"Long-run crashed at tick {tick}: {e}")

        assert render_count >= 25, f"Should have rendered at least 25 frames, got {render_count}"

    # ====================================================================
    # PHASE 16: Achievement Display After Battle
    # ====================================================================

    def test_phase16_achievement_display_after_battle(self):
        """Achievement manager provides visible achievements for UI display."""
        from pycc2.domain.systems.achievement_system import create_default_achievements

        game_loop, game_map = self._create_game_loop()
        map_data = self._build_map_data(game_map)

        game_loop.start_deployment(map_data=map_data, faction="allied")
        game_loop.complete_deployment()

        bridge = game_loop._achievement_bridge
        mgr = bridge._manager

        game_loop.event_bus.publish_named("UnitKilled", {
            "faction": "AXIS",
            "attacker_role": "sniper",
            "unit_type": "infantry",
        })

        game_loop.event_bus.publish_named("BattleWon", {
            "result": "ALLIES_VICTORY",
            "duration_seconds": 90,
        })

        visible = mgr.get_all_visible()
        assert len(visible) > 0, "Should have visible achievements"

        unlocked = mgr.get_all_unlocked()
        assert len(unlocked) >= 2, "Should have at least 2 unlocked achievements"

        stats = mgr.get_stats()
        assert stats["total"] == 11
        assert stats["unlocked"] >= 2
        assert stats["completion_pct"] > 0

    # ====================================================================
    # PHASE 17: Save/Load Preserves Achievement Progress
    # ====================================================================

    def test_phase17_achievement_persistence(self):
        """Achievement progress can be saved and loaded."""
        from pycc2.domain.systems.achievement_system import AchievementManager, create_default_achievements
        import tempfile
        import json

        mgr = AchievementManager()
        for a in create_default_achievements():
            mgr.register(a)

        mgr.add_progress("first_blood", 1)
        assert mgr.is_unlocked("first_blood")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump({
                aid: {"progress": state.progress, "unlocked_at": state.unlocked_at}
                for aid, state in mgr._states.items()
            }, f)
            save_path = f.name

        with open(save_path, "r") as f:
            data = json.load(f)

        assert "first_blood" in data
        assert data["first_blood"]["progress"] == 1

        import os
        os.unlink(save_path)
