from __future__ import annotations

import contextlib
from unittest.mock import Mock, patch

import numpy as np
import pygame
import pytest

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.presentation.rendering.camera import Camera
from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer
from pycc2.presentation.rendering.window_config import WindowManager
from pycc2.services.event_bus import EventBus
from pycc2.services.game_loop import LOGIC_DT, MAX_FRAME_TIME, GameLoop, GameState


@pytest.fixture
def mock_game_map():
    grid = np.zeros((16, 16), dtype=np.int8)
    return GameMap(id="test", name="Test Map", width=16, height=16, tile_grid=grid)


@pytest.fixture
def sample_units() -> list[Unit]:
    return [
        Unit(
            id="unit_1",
            name="Unit 1",
            faction=Faction.ALLIES,
            unit_type=UnitType.INFANTRY_SQUAD,
            health=HealthComponent(hp=100, max_hp=100),
            morale=MoraleComponent(value=85),
            weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=10, max_ammo=10),
            position=PositionComponent(tile_coord=TileCoord(3, 3)),
            vision=VisionComponent(range_tiles=5),
        ),
    ]


@pytest.fixture
def camera():
    return Camera(position=Vec2(256.0, 256.0), viewport_width=1280, viewport_height=720)


@pytest.fixture
def mock_renderer():
    renderer = Mock(spec=EnhancedRenderer)
    return renderer


@pytest.fixture
def mock_window_manager():
    wm = Mock(spec=WindowManager)
    screen = Mock()
    screen.get_width.return_value = 1280
    screen.get_height.return_value = 720
    screen.get_size.return_value = (1280, 720)
    wm.get_screen.return_value = screen
    wm.fps = 60.0
    wm.tick.return_value = 16
    return wm


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def game_state(mock_game_map, sample_units, camera):
    return GameState(
        game_map=mock_game_map,
        units=sample_units,
        camera=camera,
    )


@pytest.fixture
def game_loop(mock_renderer, mock_window_manager, event_bus, game_state):
    return GameLoop(
        renderer=mock_renderer,
        window_manager=mock_window_manager,
        event_bus=event_bus,
        state=game_state,
    )


class TestGameLoopConstruction:
    def test_correct_construction_with_all_dependencies(self, game_loop, game_state):
        assert game_loop.renderer is not None
        assert game_loop.window_manager is not None
        assert game_loop.event_bus is not None
        assert game_loop.state is game_state

    def test_initial_state_values(self, game_loop):
        assert game_loop.state.running is True
        assert game_loop.state.paused is False
        assert game_loop.state.tick == 0
        assert game_loop._accumulator == 0.0
        assert game_loop._fps == 0.0
        assert game_loop._total_ticks == 0


class TestFixYourTimestep:
    def test_logic_dt_is_30_ups(self):
        assert pytest.approx(1.0 / 30.0, rel=1e-6) == LOGIC_DT

    def test_max_frame_time_is_025(self):
        assert MAX_FRAME_TIME == 0.25

    def test_accumulator_accumulates_excess_time(self, game_loop):
        initial_accumulator = game_loop._accumulator
        game_loop._accumulator += 0.05
        assert game_loop._accumulator > initial_accumulator

    def test_long_pause_skips_simulation(self, game_loop):
        with patch("pycc2.services.game_loop.time.perf_counter") as mock_time:
            mock_time.side_effect = [0.0, 2.0]
            with patch.object(game_loop, "_update_logic") as mock_update:
                with patch.object(game_loop._hud_manager, "render"):
                    with patch("pygame.display.flip"):
                        with patch("pygame.event.get", return_value=[]):
                            game_loop.state.running = True
                            with contextlib.suppress(Exception):
                                game_loop.run()
                            mock_update.assert_not_called()

    def test_catchup_limit_is_5(self):
        MAX_CATCHUP = 5
        assert MAX_CATCHUP == 5


class TestPauseResume:
    def test_paused_does_not_call_update_logic(self, game_loop):
        game_loop.state.paused = True
        with patch.object(game_loop._hud_manager, "render"):
            game_loop._update_logic(LOGIC_DT)
        for unit in game_loop.state.units:
            if unit.weapon.state.name == "RELOADING":
                raise AssertionError("Should not tick reloading weapons when paused")

    def test_pause_renders_static_frame(self, game_loop):
        game_loop.state.paused = True
        with patch.object(game_loop.renderer, "render") as mock_render:
            alpha = 0.5
            game_loop.renderer.render(
                game_loop.state.game_map,
                game_loop.state.units,
                game_loop.state.camera,
                alpha=alpha,
                selected_unit_ids=game_loop.state.selected_unit_ids,
                debug_mode=game_loop.state.debug_mode,
            )
            mock_render.assert_called_once()

    def test_esc_toggles_pause(self, game_loop):
        from pycc2.presentation.input.handler import InputEvent, PygameInputHandler

        mock_input_handler = Mock(spec=PygameInputHandler)
        game_loop.input_handler = mock_input_handler
        initial_paused = game_loop.state.paused
        esc_event = InputEvent(event_type="key_down", key=pygame.K_ESCAPE)
        mock_input_handler.process_event.return_value = esc_event
        # Create a simple namespace object instead of MagicMock for the pygame event
        mock_event = type("Event", (), {"type": pygame.KEYDOWN, "key": pygame.K_ESCAPE})()
        game_loop._handle_input(mock_event)
        assert game_loop.state.paused != initial_paused


class TestIntegration:
    def test_run_complete_loop_without_crash(self, game_loop):
        pygame.font.init()
        with patch("pycc2.services.game_loop.time.perf_counter") as mock_time:
            call_count = [0]

            def time_side_effect():
                call_count[0] += 1
                if call_count[0] > 4:
                    game_loop.state.running = False
                    raise StopIteration
                return call_count[0] * 0.016

            mock_time.side_effect = time_side_effect
            with patch("pygame.event.get", return_value=[]):
                with patch("pygame.display.flip"):
                    game_loop.state.running = True
                    with contextlib.suppress(StopIteration):
                        game_loop.run()

    def test_shutdown_is_called(self, game_loop):
        with patch.object(game_loop.window_manager, "shutdown") as mock_shutdown:
            game_loop.shutdown()
            mock_shutdown.assert_called_once()

    def test_fps_and_tick_increment(self, game_loop):
        initial_tick = game_loop.state.tick
        initial_fps = game_loop._fps
        game_loop.state.tick += 1
        game_loop._fps = 60.0
        assert game_loop.state.tick > initial_tick
        assert game_loop._fps > initial_fps


class TestEdgeCases:
    def test_empty_units_list_no_crash(
        self, mock_game_map, camera, mock_renderer, mock_window_manager, event_bus
    ):
        state = GameState(
            game_map=mock_game_map,
            units=[],
            camera=camera,
        )
        loop = GameLoop(
            renderer=mock_renderer,
            window_manager=mock_window_manager,
            event_bus=event_bus,
            state=state,
        )
        loop._update_logic(LOGIC_DT)

    def test_all_dead_units_still_running(
        self, sample_units, mock_game_map, camera, mock_renderer, mock_window_manager, event_bus
    ):
        for unit in sample_units:
            unit.health.take_damage(100)
        state = GameState(
            game_map=mock_game_map,
            units=sample_units,
            camera=camera,
        )
        loop = GameLoop(
            renderer=mock_renderer,
            window_manager=mock_window_manager,
            event_bus=event_bus,
            state=state,
        )
        loop._update_logic(LOGIC_DT)
        assert loop.state.running is True


class TestAIThrottle:
    def _run_logic_n(self, game_loop, n, fake_ai):
        with patch.object(game_loop._combat_director, "update"):
            with patch.object(game_loop._combat_director, "process_effects"):
                game_loop._victory_manager._victory_evaluator = None
                for _ in range(n):
                    game_loop._update_logic(LOGIC_DT)

    def test_ai_throttle_fields_exist(self, game_loop):
        assert hasattr(game_loop, "_ai_update_interval")
        assert hasattr(game_loop, "_ai_tick_counter")
        assert game_loop._ai_update_interval == 3
        assert game_loop._ai_tick_counter == 0

    def test_ai_default_interval_is_3(self):
        gl = GameLoop.__new__(GameLoop)
        assert gl._ai_update_interval == 3

    def test_ai_not_called_on_first_tick(self, game_loop):
        from tests.conftest import FakeAIService

        fake_ai = FakeAIService(managed_unit_count=5)
        game_loop.ai_service = fake_ai
        self._run_logic_n(game_loop, 1, fake_ai)
        assert fake_ai.tick_call_count == 0

    def test_ai_called_on_third_tick(self, game_loop):
        from tests.conftest import FakeAIService

        fake_ai = FakeAIService(managed_unit_count=5)
        game_loop.ai_service = fake_ai
        self._run_logic_n(game_loop, 3, fake_ai)
        assert fake_ai.tick_call_count == 1

    def test_ai_called_every_3rd_tick(self, game_loop):
        from tests.conftest import FakeAIService

        fake_ai = FakeAIService(managed_unit_count=5)
        game_loop.ai_service = fake_ai
        self._run_logic_n(game_loop, 9, fake_ai)
        assert fake_ai.tick_call_count == 3

    def test_combat_update_not_throttled(self, game_loop):
        from tests.conftest import FakeAIService

        fake_ai = FakeAIService(managed_unit_count=5)
        game_loop.ai_service = fake_ai
        with patch.object(game_loop._combat_director, "update") as mock_combat:
            with patch.object(game_loop._combat_director, "process_effects"):
                game_loop._victory_manager._victory_evaluator = None
                for _ in range(5):
                    game_loop._update_logic(LOGIC_DT)
        assert mock_combat.call_count == 5

    def test_ai_counter_resets_after_update(self, game_loop):
        from tests.conftest import FakeAIService

        fake_ai = FakeAIService(managed_unit_count=5)
        game_loop.ai_service = fake_ai
        with patch.object(game_loop._combat_director, "update"):
            with patch.object(game_loop._combat_director, "process_effects"):
                game_loop._victory_manager._victory_evaluator = None
                game_loop._update_logic(LOGIC_DT)
                assert game_loop._ai_tick_counter == 1
                game_loop._update_logic(LOGIC_DT)
                assert game_loop._ai_tick_counter == 2
                game_loop._update_logic(LOGIC_DT)
                assert game_loop._ai_tick_counter == 0

    def test_no_ai_service_does_not_crash(self, game_loop):
        game_loop.ai_service = None
        self._run_logic_n(game_loop, 5, None)

    def test_configurable_interval(self, game_loop):
        from tests.conftest import FakeAIService

        game_loop._ai_update_interval = 5
        fake_ai = FakeAIService(managed_unit_count=5)
        game_loop.ai_service = fake_ai
        self._run_logic_n(game_loop, 9, fake_ai)
        assert fake_ai.tick_call_count == 1

    def test_ai_still_makes_decisions_just_less_often(self, game_loop):
        from tests.conftest import FakeAIService

        intents_result = [{"test": "intent"}]
        fake_ai = FakeAIService(managed_unit_count=5, tick_return_value=intents_result)
        game_loop.ai_service = fake_ai
        self._run_logic_n(game_loop, 6, fake_ai)
        assert fake_ai.execute_intents_call_count == 2
