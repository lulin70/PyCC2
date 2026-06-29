from __future__ import annotations

import os
from unittest.mock import MagicMock, Mock, patch

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
from pycc2.infrastructure.events.event_bus import EventBus
from pycc2.presentation.input.handler import PygameInputHandler
from pycc2.presentation.rendering.camera import Camera
from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer
from pycc2.presentation.rendering.window_config import WindowManager
from pycc2.services.game_loop import GameLoop, GameState


@pytest.fixture(scope="module")
def pygame_env():
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    pygame.init()
    yield
    pygame.display.quit()


@pytest.fixture
def tutorial_map():
    width, height = 16, 16
    grid = np.zeros((height, width), dtype=np.int8)
    grid[4:6, 4:8] = 3
    grid[8:10, 8:12] = 5
    grid[12, :] = 1
    grid[:, 12] = 1
    grid[7, 7] = 11
    return GameMap(
        id="tutorial",
        name="Tutorial Map",
        width=width,
        height=height,
        tile_grid=grid,
    )


@pytest.fixture
def sample_units() -> list[Unit]:
    return [
        Unit(
            id="ally_infantry_1",
            name="Alpha Squad",
            faction=Faction.ALLIES,
            unit_type=UnitType.INFANTRY_SQUAD,
            health=HealthComponent(hp=100, max_hp=100),
            morale=MoraleComponent(value=85),
            weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=10, max_ammo=10),
            position=PositionComponent(tile_coord=TileCoord(3, 3)),
            vision=VisionComponent(range_tiles=5),
        ),
        Unit(
            id="axis_mg_1",
            name="MG Team",
            faction=Faction.AXIS,
            unit_type=UnitType.MACHINE_GUN_SQUAD,
            health=HealthComponent(hp=80, max_hp=80),
            morale=MoraleComponent(value=70),
            weapon=WeaponComponent(primary_weapon_id="mg42", ammo_remaining=50, max_ammo=50),
            position=PositionComponent(tile_coord=TileCoord(10, 10)),
            vision=VisionComponent(range_tiles=6),
        ),
        Unit(
            id="ally_commander",
            name="Cpt. Miller",
            faction=Faction.ALLIES,
            unit_type=UnitType.COMMANDER,
            health=HealthComponent(hp=100, max_hp=100),
            morale=MoraleComponent(value=95),
            weapon=WeaponComponent(primary_weapon_id="pistol", ammo_remaining=14, max_ammo=14),
            position=PositionComponent(tile_coord=TileCoord(5, 8)),
            vision=VisionComponent(range_tiles=7),
        ),
    ]


@pytest.fixture
def full_system(pygame_env, tutorial_map, sample_units, monkeypatch):
    wm = WindowManager()
    mock_screen = Mock()
    mock_screen.get_size.return_value = (1280, 720)
    monkeypatch.setattr(wm, "initialize", lambda: mock_screen)
    monkeypatch.setattr(wm, "get_screen", lambda: mock_screen)
    screen = wm.initialize()
    camera = Camera(
        position=Vec2(256.0, 256.0),
        viewport_width=1280,
        viewport_height=720,
    )
    renderer = EnhancedRenderer()
    renderer.initialize(screen)
    event_bus = EventBus()
    input_handler = PygameInputHandler(camera=camera, window_manager=wm)
    state = GameState(
        game_map=tutorial_map,
        units=sample_units,
        camera=camera,
    )
    game_loop = GameLoop(
        renderer=renderer,
        window_manager=wm,
        event_bus=event_bus,
        state=state,
        input_handler=input_handler,
    )
    return {
        "wm": wm,
        "camera": camera,
        "renderer": renderer,
        "event_bus": event_bus,
        "input_handler": input_handler,
        "state": state,
        "game_loop": game_loop,
        "screen": screen,
    }


class TestVerticalSlice01_InitChain:
    def test_vs01_complete_initialization_chain(self, full_system):
        assert full_system["wm"] is not None
        assert full_system["camera"] is not None
        assert full_system["renderer"] is not None
        assert full_system["game_loop"] is not None
        assert full_system["state"].running is True
        assert full_system["state"].tick == 0

    def test_vs01_shutdown_completes(self, full_system):
        full_system["game_loop"].shutdown()
        assert full_system["state"].running is False, "Game should not be running after shutdown"


class TestVerticalSlice02_MapLoading:
    def test_vs02_map_dimensions_16x16(self, tutorial_map):
        assert tutorial_map.width == 16
        assert tutorial_map.height == 16

    def test_vs02_map_contains_terrain_types(self, tutorial_map):
        assert int(tutorial_map.tile_grid[4, 4]) == 3
        assert int(tutorial_map.tile_grid[8, 8]) == 5
        assert int(tutorial_map.tile_grid[12, 0]) == 1
        assert int(tutorial_map.tile_grid[7, 7]) == 11


class TestVerticalSlice03_UnitVisibility:
    def test_vs03_three_units_created(self, sample_units):
        assert len(sample_units) == 3

    def test_vs03_units_have_correct_positions(self, sample_units):
        assert sample_units[0].position.tile_coord == TileCoord(3, 3)
        assert sample_units[1].position.tile_coord == TileCoord(10, 10)
        assert sample_units[2].position.tile_coord == TileCoord(5, 8)

    def test_vs03_units_on_screen(self, full_system):
        camera = full_system["camera"]
        for unit in full_system["state"].units:
            screen_pos = camera.world_to_screen(unit.position.pixel_position)
            assert 0 <= screen_pos[0] <= camera.viewport_width
            assert 0 <= screen_pos[1] <= camera.viewport_height


class TestVerticalSlice04_CameraMovement:
    def test_vs04_wasd_moves_camera(self, full_system):
        camera = full_system["camera"]
        initial_pos = camera.position
        camera.move(10.0, 20.0)
        assert camera.position.x != initial_pos.x or camera.position.y != initial_pos.y

    def test_vs04_unit_screen_position_changes_after_move(self, full_system):
        camera = full_system["camera"]
        unit = full_system["state"].units[0]
        initial_screen = camera.world_to_screen(unit.position.pixel_position)
        camera.move(50.0, 0.0)
        new_screen = camera.world_to_screen(unit.position.pixel_position)
        assert initial_screen[0] != new_screen[0]


class TestVerticalSlice05_Zoom:
    def test_vs05_zoom_in_changes_value(self, full_system):
        camera = full_system["camera"]
        initial_zoom = camera.zoom
        camera.adjust_zoom(1.2, anchor=(640, 360))
        assert camera.zoom != initial_zoom

    def test_vs05_zoom_out_changes_value(self, full_system):
        camera = full_system["camera"]
        camera.zoom = 2.0
        initial_zoom = camera.zoom
        camera.adjust_zoom(0.8, anchor=(640, 360))
        assert camera.zoom < initial_zoom


class TestVerticalSlice06_PauseResume:
    def test_vs06_esc_toggles_pause(self, full_system):
        state = full_system["state"]
        initial_paused = state.paused
        import pygame as pg

        mock_event = MagicMock()
        mock_event.type = pg.KEYDOWN
        mock_event.key = pg.K_ESCAPE
        with patch.object(full_system["input_handler"], "process_event") as mock_process:
            from pycc2.presentation.input.handler import InputEvent

            mock_process.return_value = InputEvent(event_type="key_down", key=pg.K_ESCAPE)
            full_system["game_loop"]._handle_input(mock_event)
        assert state.paused != initial_paused

    def test_vs06_double_esc_resumes(self, full_system):
        state = full_system["state"]
        state.paused = False
        import pygame as pg

        mock_event = MagicMock()
        mock_event.type = pg.KEYDOWN
        mock_event.key = pg.K_ESCAPE
        with patch.object(full_system["input_handler"], "process_event") as mock_process:
            from pycc2.presentation.input.handler import InputEvent

            mock_process.return_value = InputEvent(event_type="key_down", key=pg.K_ESCAPE)
            full_system["game_loop"]._handle_input(mock_event)
            assert state.paused is True
            full_system["game_loop"]._handle_input(mock_event)
            assert state.paused is False


class TestVerticalSlice07_Fullscreen:
    def test_vs07_f11_toggle_no_crash(self, full_system):
        import pygame as pg

        mock_event = MagicMock()
        mock_event.type = pg.KEYDOWN
        mock_event.key = pg.K_F11
        try:
            result = full_system["input_handler"].process_event(mock_event)
            assert result is None
        except Exception as e:
            pytest.fail(f"F11 toggle crashed: {e}")


class TestVerticalSlice08_RunDuration:
    def test_vs08_run_10_seconds_no_exception(self, full_system, monkeypatch):
        full_system["state"].running = True
        start_time = 0.0
        call_count = [0]

        def mock_perf_counter():
            nonlocal start_time, call_count
            call_count[0] += 1
            if call_count[0] % 2 == 1:
                return start_time
            else:
                start_time += 0.016
                if start_time >= 10.0:
                    full_system["state"].running = False
                return start_time

        monkeypatch.setattr("pycc2.services.game_loop.time.perf_counter", mock_perf_counter)
        monkeypatch.setattr("pygame.event.get", lambda: [])
        monkeypatch.setattr("pygame.display.flip", lambda: None)
        monkeypatch.setattr(full_system["game_loop"]._hud_manager, "render", lambda *a, **kw: None)
        monkeypatch.setattr(full_system["renderer"], "render", lambda *args, **kwargs: None)

        try:
            full_system["game_loop"].run()
            assert full_system["state"].running is False
        except Exception as e:
            pytest.fail(f"Run crashed after 10 seconds: {e}")
