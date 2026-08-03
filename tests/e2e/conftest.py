"""End-to-end test layer configuration.

D13 N-5 (P3): Layer-specific conftest for e2e tests.

E2E tests should:
- Verify complete user journeys (menu -> campaign -> deployment -> battle -> pause)
- Use the real GameLoop with headless pygame (SDL dummy drivers)
- Capture screenshots at each journey step for visual regression
- Be the slowest tier, run separately in CI (`e2e-tests` job)

Shared fixtures (pygame_display, mock_font, game_instance, FakeAIService,
FakeCombatDirector) remain in tests/conftest.py for backward compatibility.

This file provides the **shared GameLoopFactory + EventInjector** extracted
from test_e2e_full_coverage.py / test_ai_integration_e2e.py to eliminate
duplication (D13-N5 structural fix, v0.9.x). New e2e tests MUST use these
shared helpers instead of redefining their own factory.
"""

from __future__ import annotations

import os
from pathlib import Path

import pygame
import pytest

# Headless SDL drivers must be set before pygame import.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_JOYSTICK_DRIVER", "dummy")


def find_map_path() -> Path:
    """Return the first non-schema map JSON path under data/maps/.

    Shared helper — previously duplicated in every e2e factory file.
    """
    map_dir = Path("data/maps")
    for candidate in sorted(map_dir.glob("*.json")):
        if candidate.stem != "_schema":
            return candidate
    raise FileNotFoundError("No map files found in data/maps/")


class GameLoopFactory:
    """Creates a fully wired GameLoop for e2e testing.

    Shared factory extracted from test_e2e_full_coverage._GameLoopFactory and
    test_ai_integration_e2e._AIGameLoopFactory (which were near-identical).

    Exposes the assembled components as attributes so tests can interact with
    them directly:
      - game_loop, state, game_map, camera, wm, renderer, event_bus,
        interaction_controller, ai_service

    Helpers:
      - start_deployment(): enter deployment phase, return deployment_ui
      - place_n_units(n): programmatically place N units and complete deployment
      - run_ticks(count, dt): run N logic ticks, return list of errors
      - render_frame(**kwargs): render one frame, return success bool
      - shutdown(): clean shutdown
    """

    def __init__(self, screen, map_path: Path | None = None):
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
        from pycc2.presentation.rendering.window_config import (
            DisplayInfo,
            WindowManager,
        )
        from pycc2.presentation.ui.hint_manager import HintManager
        from pycc2.presentation.ui.keybind_manager import KeybindManager
        from pycc2.presentation.ui.settings_menu import SettingsMenu
        from pycc2.presentation.ui.tutorial_system import TutorialOverlay
        from pycc2.services.ai_service import AIService
        from pycc2.services.game_loop import GameLoop, GameState

        chosen_path = map_path if map_path is not None else find_map_path()
        self.game_map = GameMap.from_json(chosen_path)

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
        self.wm = wm
        self.renderer = renderer
        self.event_bus = event_bus
        self.interaction_controller = interaction_controller
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


class EventInjector:
    """Injects pygame events for testing.

    Shared helper — previously duplicated in test_e2e_full_coverage.py.
    """

    @staticmethod
    def click(x, y, button=1):
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(x, y), button=button))
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(x, y), button=button))

    @staticmethod
    def right_click(x, y):
        EventInjector.click(x, y, button=3)

    @staticmethod
    def key(k, mod=0):
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=mod))
        pygame.event.post(pygame.event.Event(pygame.KEYUP, key=k, mod=0))

    @staticmethod
    def mouse_move(x, y):
        pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION, pos=(x, y), rel=(0, 0)))

    @staticmethod
    def scroll(x, y, direction=1):
        pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, x=x, y=y, spin=direction))

    @staticmethod
    def mouse_drag(start_x, start_y, end_x, end_y):
        EventInjector.mouse_move(start_x, start_y)
        pygame.event.post(
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(start_x, start_y), button=1)
        )
        for i in range(1, 5):
            t = i / 5.0
            mx = int(start_x + (end_x - start_x) * t)
            my = int(start_y + (end_y - start_y) * t)
            EventInjector.mouse_move(mx, my)
        EventInjector.mouse_move(end_x, end_y)
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(end_x, end_y), button=1))


@pytest.fixture()
def game_loop_factory(pygame_display):
    """Yield a callable that builds a GameLoopFactory on a fresh screen.

    Usage in tests::

        def test_xxx(game_loop_factory):
            pygame.init()
            screen = pygame.display.set_mode((1280, 720))
            try:
                f = game_loop_factory(screen)
                f.start_deployment()
                ...
            finally:
                pygame.quit()
    """
    created: list[GameLoopFactory] = []

    def _make(screen, map_path: Path | None = None) -> GameLoopFactory:
        f = GameLoopFactory(screen, map_path=map_path)
        created.append(f)
        return f

    yield _make

    for f in created:
        try:
            f.shutdown()
        except Exception:
            pass
