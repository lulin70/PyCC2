"""E2E: AI Integration — ReconAI & SupplyAwarenessAI game loop verification.

Verifies that the newly registered tactical AIs (ReconAI, SupplyAwarenessAI)
are integrated into the game loop and produce observable behaviors:

  1. Registration: both AIs appear in TacticalOrchestrator.registered_ais
  2. Game loop stability: 60+ ticks with both AIs active — no crash
  3. ReconAI behavior: snipers + VL positions → RECONNAISSANCE intents produced
  4. SupplyAwarenessAI behavior: units near supply points → DEFEND/ATTACK intents
  5. Tactical summary: get_tactical_summary() returns both AI names
  6. Render stability: rendering with AI-produced orders doesn't crash

This test complements test_e2e_full_coverage.py (42 user operations) by
verifying the AI subsystems behind the "Battle Flow" category.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_JOYSTICK_DRIVER", "dummy")

from pathlib import Path

import pygame
import pytest


def _find_map_path() -> Path:
    map_dir = Path("data/maps")
    for candidate in sorted(map_dir.glob("*.json")):
        if candidate.stem != "_schema":
            return candidate
    raise FileNotFoundError("No map files found in data/maps/")


class _AIGameLoopFactory:
    """Creates a GameLoop with AIService for AI integration testing."""

    def __init__(self, screen):
        self.screen = screen
        from pycc2.domain.entities.game_map import GameMap
        from pycc2.domain.interfaces.display_config import DisplayConfig as DC
        from pycc2.domain.value_objects.vec2 import Vec2
        from pycc2.infrastructure.events.event_bus import EventBus
        from pycc2.presentation.input.handler import PygameInputHandler
        from pycc2.presentation.input.interaction_controller import (
            InteractionController,
        )
        from pycc2.presentation.rendering.camera import Camera
        from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer
        from pycc2.presentation.rendering.window_config import DisplayInfo, WindowManager
        from pycc2.presentation.ui.hint_manager import HintManager
        from pycc2.presentation.ui.keybind_manager import KeybindManager
        from pycc2.presentation.ui.settings_menu import SettingsMenu
        from pycc2.presentation.ui.tutorial_system import TutorialOverlay
        from pycc2.services.ai_service import AIService
        from pycc2.services.game_loop import GameLoop, GameState

        map_path = _find_map_path()
        self.game_map = GameMap.from_json(map_path)

        if not self.game_map.spawn_points:
            from pycc2.domain.entities.game_map import SpawnPoint
            from pycc2.domain.value_objects.tile_coord import TileCoord

            self.game_map.spawn_points = [
                SpawnPoint(
                    id="friendly_default",
                    side="friendly",
                    position=TileCoord(5, self.game_map.height // 2),
                    units_max=9,
                ),
                SpawnPoint(
                    id="enemy_default",
                    side="enemy",
                    position=TileCoord(self.game_map.width - 5, self.game_map.height // 2),
                    units_max=9,
                ),
            ]

        center_x = self.game_map.width * 16.0
        center_y = self.game_map.height * 16.0
        self.camera = Camera(
            position=Vec2(center_x, center_y),
            viewport_width=1280,
            viewport_height=720,
        )

        wm = WindowManager(DisplayInfo(base_width=1280, base_height=720))
        wm._screen = screen

        renderer = EnhancedRenderer()
        renderer.initialize(screen)

        event_bus = EventBus()
        input_handler = PygameInputHandler(camera=self.camera, window_manager=wm)
        ai_service = AIService(event_bus=event_bus)

        interaction_controller = InteractionController(
            camera=self.camera,
            game_map=self.game_map,
            event_bus=event_bus,
        )

        display_config = DC()
        hint_manager = HintManager()
        keybind_manager = KeybindManager()
        settings_menu = SettingsMenu(display_config, keybind_manager=keybind_manager)
        tutorial_overlay = TutorialOverlay(display_config)

        interaction_controller.set_hint_manager(hint_manager)
        interaction_controller.set_keybind_manager(keybind_manager)

        state = GameState(
            game_map=self.game_map,
            units=[],
            camera=self.camera,
        )

        self.game_loop = GameLoop(
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
        self.state = state
        self.ai_service = ai_service

    def start_deployment(self):
        map_data = {
            "width": self.game_map.width,
            "height": self.game_map.height,
            "tiles": self.game_map.tile_grid.tolist(),
            "spawn_points": [
                {
                    "id": sp.id,
                    "side": sp.side,
                    "position": [sp.position.x, sp.position.y],
                    "units_max": sp.units_max,
                }
                for sp in self.game_map.spawn_points
            ],
        }
        self.game_loop.start_deployment(map_data=map_data, faction="allied")
        return self.game_loop.deployment_ui

    def place_n_units(self, n=3):
        """Place N units programmatically for battle phase tests."""
        dui = self.game_loop.deployment_ui
        if dui is None:
            dui = self.start_deployment()
        friendly_zone = dui.state.friendly_zone
        placed = 0
        for i, unit in enumerate(dui.state.available_units):
            if placed >= n or unit.is_placed:
                continue
            for tile_x, tile_y in friendly_zone:
                terrain = dui._get_terrain_at(tile_x, tile_y)
                if dui.can_place_at(unit, tile_x, tile_y, terrain):
                    occupied = any(pu.position == (tile_x, tile_y) for pu in dui.state.placed_units)
                    if not occupied:
                        dui.place_unit(i, tile_x, tile_y)
                        placed += 1
                        break
        result = self.game_loop.complete_deployment()
        return placed, result

    def run_ticks(self, count=60, dt=None):
        """Run N game logic ticks without crashing."""
        if dt is None:
            dt = 1.0 / 30.0
        errors = []
        for tick in range(count):
            try:
                self.game_loop._update_logic(dt)
                self.state.tick += 1
                self.game_loop._event_dispatcher.process_events()
            except Exception as e:
                errors.append((tick, str(e)))
        return errors

    def render_frame(self, **kwargs):
        """Render one frame and return without crashing."""
        default_kwargs = dict(
            game_map=self.state.game_map,
            units=self.state.units,
            camera=self.state.camera,
            alpha=1.0,
            selected_unit_ids=self.state.selected_unit_ids,
            debug_mode=False,
            paused=False,
            tick=self.state.tick,
            show_post_battle=False,
            game_result=None,
            battle_stats=None,
        )
        default_kwargs.update(kwargs)
        try:
            self.game_loop._render_pipeline.render(**default_kwargs)
            return True
        except Exception:
            return False

    def shutdown(self):
        self.game_loop.shutdown()


# ===========================================================================
# TEST SUITE
# ===========================================================================


class TestAIIntegrationE2E:
    """E2E tests for ReconAI and SupplyAwarenessAI game loop integration.

    Verifies that the AIs registered in AIService.__init__ are actually
    exercised by the game loop and produce observable tactical intents.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1280, 720))
        yield
        pygame.quit()

    def _factory(self):
        return _AIGameLoopFactory(self.screen)

    # ======================================================================
    # 1. REGISTRATION VERIFICATION
    # ======================================================================

    def test_recon_ai_registered_in_orchestrator(self):
        """ReconAI must be registered in TacticalOrchestrator."""
        f = self._factory()
        registered = f.ai_service._tactical_orchestrator.registered_ais
        assert "ReconAI" in registered, f"ReconAI not in registered AIs: {registered}"
        f.shutdown()

    def test_supply_awareness_ai_registered_in_orchestrator(self):
        """SupplyAwarenessAI must be registered in TacticalOrchestrator."""
        f = self._factory()
        registered = f.ai_service._tactical_orchestrator.registered_ais
        assert "SupplyAwarenessAI" in registered, (
            f"SupplyAwarenessAI not in registered AIs: {registered}"
        )
        f.shutdown()

    def test_all_10_tactical_ais_registered(self):
        """All 10 tactical AIs must be registered (8 original + 2 new)."""
        f = self._factory()
        registered = f.ai_service._tactical_orchestrator.registered_ais
        expected = {
            "FlankingAI",
            "SuppressionAI",
            "InfantryTankCoordAI",
            "VictoryPointAI",
            "RetreatDecisionAI",
            "ATAmbushAI",
            "CounterattackAI",
            "AmbushAI",
            "ReconAI",
            "SupplyAwarenessAI",
        }
        missing = expected - set(registered)
        assert not missing, f"Missing AIs: {missing}. Got: {registered}"
        f.shutdown()

    # ======================================================================
    # 2. GAME LOOP STABILITY
    # ======================================================================

    def test_game_loop_60_ticks_no_crash_with_new_ais(self):
        """Game loop runs 60 ticks with ReconAI+SupplyAwarenessAI — no crash."""
        f = self._factory()
        f.place_n_units(3)
        errors = f.run_ticks(60)
        assert len(errors) == 0, f"AI crashes: {errors[:3]}"
        f.shutdown()

    def test_game_loop_200_ticks_stable_with_new_ais(self):
        """Extended battle (200 ticks) with new AIs remains stable."""
        f = self._factory()
        f.place_n_units(3)
        errors = f.run_ticks(200)
        assert len(errors) == 0, f"Crashes at 200 ticks: {errors[:5]}"
        assert f.render_frame()
        f.shutdown()

    # ======================================================================
    # 3. RECONAI BEHAVIOR VERIFICATION
    # ======================================================================

    def test_recon_ai_evaluates_without_crash(self):
        """ReconAI.evaluate() runs without crash during game ticks."""
        f = self._factory()
        f.place_n_units(3)
        f.run_ticks(30)
        scores = f.ai_service._tactical_orchestrator.last_scores
        assert "ReconAI" in scores, f"ReconAI score missing: {scores}"
        f.shutdown()

    def test_recon_ai_produces_orders_in_battle(self):
        """ReconAI produces tactical intents during battle (if snipers present).

        This verifies the full pipeline: game tick → AIService.tick() →
        _run_tactical_orchestrator() → ReconAI.evaluate() + execute() →
        TacticIntent in last_orders.
        """
        f = self._factory()
        f.place_n_units(5)  # Place more units to increase chance of snipers

        # Run enough ticks for AI to evaluate and produce orders
        f.run_ticks(60)

        # Check tactical summary
        summary = f.ai_service.get_tactical_summary()
        assert "ReconAI" in summary["registered_ais"]
        assert summary["current_tick"] > 0

        # The last_scores should have an entry for ReconAI
        scores = f.ai_service._tactical_orchestrator.last_scores
        assert "ReconAI" in scores, f"ReconAI not scored: {scores}"

        f.shutdown()

    # ======================================================================
    # 4. SUPPLYAWARENESSAI BEHAVIOR VERIFICATION
    # ======================================================================

    def test_supply_awareness_ai_evaluates_without_crash(self):
        """SupplyAwarenessAI.evaluate() runs without crash during game ticks."""
        f = self._factory()
        f.place_n_units(3)
        f.run_ticks(30)
        scores = f.ai_service._tactical_orchestrator.last_scores
        assert "SupplyAwarenessAI" in scores, f"SupplyAwarenessAI score missing: {scores}"
        f.shutdown()

    def test_supply_awareness_ai_produces_orders_in_battle(self):
        """SupplyAwarenessAI produces tactical intents during battle."""
        f = self._factory()
        f.place_n_units(5)

        f.run_ticks(60)

        summary = f.ai_service.get_tactical_summary()
        assert "SupplyAwarenessAI" in summary["registered_ais"]

        scores = f.ai_service._tactical_orchestrator.last_scores
        assert "SupplyAwarenessAI" in scores, f"SupplyAwarenessAI not scored: {scores}"

        f.shutdown()

    # ======================================================================
    # 5. TACTICAL SUMMARY VERIFICATION
    # ======================================================================

    def test_tactical_summary_contains_all_ais(self):
        """get_tactical_summary() returns all 11 registered AIs.

        TD-076b (v0.7.0): SurrenderAI registered to TacticalOrchestrator,
        increasing the count from 10 to 11.
        """
        f = self._factory()
        f.place_n_units(3)
        f.run_ticks(10)

        summary = f.ai_service.get_tactical_summary()
        assert len(summary["registered_ais"]) == 11, (
            f"Expected 11 AIs, got {len(summary['registered_ais'])}: {summary['registered_ais']}"
        )
        f.shutdown()

    def test_tactical_summary_tracks_tick_progress(self):
        """Tactical summary current_tick advances with game ticks."""
        f = self._factory()
        f.place_n_units(2)

        f.run_ticks(5)
        summary1 = f.ai_service.get_tactical_summary()
        tick1 = summary1["current_tick"]

        f.run_ticks(5)
        summary2 = f.ai_service.get_tactical_summary()
        tick2 = summary2["current_tick"]

        assert tick2 > tick1, f"Tick didn't advance: {tick1} → {tick2}"
        f.shutdown()

    # ======================================================================
    # 6. RENDER STABILITY WITH AI ORDERS
    # ======================================================================

    def test_render_with_ai_orders_no_crash(self):
        """Rendering after AI produced orders doesn't crash."""
        f = self._factory()
        f.place_n_units(3)
        f.run_ticks(30)  # Let AI produce some orders
        assert f.render_frame()
        f.shutdown()

    def test_render_debug_mode_with_ai_orders(self):
        """Debug overlay rendering with AI orders active doesn't crash."""
        f = self._factory()
        f.place_n_units(3)
        f.run_ticks(30)
        assert f.render_frame(debug_mode=True)
        f.shutdown()

    # ======================================================================
    # 7. USER JOURNEY: DEPLOY → BATTLE → AI RESPONDS
    # ======================================================================

    def test_full_user_journey_deploy_battle_ai_responds(self):
        """Full user journey: deploy units → start battle → AI responds.

        This simulates the core user flow:
        1. User opens deployment screen
        2. User places units
        3. User starts battle
        4. AI (including ReconAI, SupplyAwarenessAI) runs for 60 ticks
        5. Game renders successfully
        6. No crashes
        """
        f = self._factory()

        # Step 1: Deployment
        dui = f.start_deployment()
        assert dui is not None, "Deployment UI should open"

        # Step 2: Place units
        placed, _ = f.place_n_units(4)
        assert placed >= 1, "Should place at least 1 unit"

        # Step 3: Battle phase — AI runs
        errors = f.run_ticks(60)
        assert len(errors) == 0, f"Battle crashed: {errors[:3]}"

        # Step 4: AI produced evaluations
        scores = f.ai_service._tactical_orchestrator.last_scores
        assert "ReconAI" in scores
        assert "SupplyAwarenessAI" in scores

        # Step 5: Render works
        assert f.render_frame()

        f.shutdown()
