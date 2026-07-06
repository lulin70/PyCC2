"""Unit tests for error recovery mechanisms (TD-039).

Tests verify that critical GameLoop paths degrade gracefully on failure:
1. AI tick failure → log warning + units idle this tick (no exception propagated)
2. Render failure → log error + skip this frame (no exception propagated)

These tests use Mock to inject failures into specific subsystem methods
(ai_service.tick, render_pipeline.render). This is appropriate because
the test target is the try/except degradation logic in _update_ai and
_render_scene, not the subsystem behavior itself — we need to simulate
failures that cannot be reliably reproduced on real components.
"""

from __future__ import annotations

import os
from unittest.mock import Mock

import numpy as np
import pytest

# Headless pygame guard.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

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
from pycc2.presentation.rendering.camera import Camera
from pycc2.presentation.rendering.sprite_renderer import SpriteRenderer
from pycc2.presentation.rendering.window_config import WindowManager
from pycc2.services.ai_service import AIService
from pycc2.services.game_loop import GameLoop, GameState

# ========================================================================
# Fixtures
# ========================================================================


@pytest.fixture
def error_recovery_game_map():
    grid = np.zeros((16, 16), dtype=np.int8)
    return GameMap(id="er_test", name="Error Recovery Map", width=16, height=16, tile_grid=grid)


@pytest.fixture
def player_unit() -> Unit:
    return Unit(
        id="player_1",
        name="Player Unit",
        faction=Faction.ALLIES,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=100, max_hp=100),
        morale=MoraleComponent(value=85),
        weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=10, max_ammo=10),
        position=PositionComponent(tile_coord=TileCoord(3, 3)),
        vision=VisionComponent(range_tiles=5),
    )


@pytest.fixture
def enemy_unit() -> Unit:
    return Unit(
        id="enemy_1",
        name="Enemy Unit",
        faction=Faction.AXIS,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=100, max_hp=100),
        morale=MoraleComponent(value=85),
        weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=10, max_ammo=10),
        position=PositionComponent(tile_coord=TileCoord(10, 10)),
        vision=VisionComponent(range_tiles=5),
    )


@pytest.fixture
def er_sprite_renderer(pygame_display):
    """Real SpriteRenderer (requires pygame_display for init ordering)."""
    import pygame

    if not pygame.font.get_init():
        pygame.font.init()
    return SpriteRenderer()


@pytest.fixture
def er_window_manager():
    """Mock WindowManager for headless pygame."""
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
def er_event_bus():
    return EventBus()


@pytest.fixture
def error_recovery_game_loop(
    er_sprite_renderer,
    er_window_manager,
    er_event_bus,
    error_recovery_game_map,
    player_unit,
    enemy_unit,
):
    """GameLoop with real AIService for error recovery testing."""
    camera = Camera(
        position=Vec2(256.0, 256.0),
        viewport_width=1280,
        viewport_height=720,
    )
    state = GameState(
        game_map=error_recovery_game_map,
        units=[player_unit, enemy_unit],
        camera=camera,
    )
    loop = GameLoop(
        renderer=er_sprite_renderer,
        window_manager=er_window_manager,
        event_bus=er_event_bus,
        state=state,
        use_full_hud=False,
        ai_service=AIService(event_bus=er_event_bus),
    )
    return loop


# ========================================================================
# AI tick error recovery tests (TD-039)
# ========================================================================


class TestAITickErrorRecovery:
    """Verify _update_ai degrades gracefully when ai_service.tick fails.

    TD-039 contract: AI tick failure → log warning + units idle this tick.
    The exception must NOT propagate to _update_logic (which would crash
    the game loop).
    """

    def test_ai_tick_exception_does_not_propagate(self, error_recovery_game_loop):
        """Contract: ai_service.tick raising Exception does not crash _update_ai."""
        loop = error_recovery_game_loop
        # Register enemy unit first so managed_unit_count > 0.
        loop._update_logic(1.0 / 30.0)
        assert loop.ai_service.managed_unit_count >= 1

        # Inject failure: make tick() raise RuntimeError.
        loop.ai_service.tick = Mock(side_effect=RuntimeError("BehaviorTree crashed"))

        # Must NOT raise — _update_ai should catch and log warning.
        loop._update_ai(1.0 / 30.0)

    def test_ai_tick_counter_resets_after_failure(self, error_recovery_game_loop):
        """Contract: _ai_tick_counter resets to 0 even after AI tick failure.

        This prevents immediate retry on next tick (which would likely fail
        again and spam logs).
        """
        loop = error_recovery_game_loop
        loop._update_logic(1.0 / 30.0)  # register units, counter=1
        loop.ai_service.tick = Mock(side_effect=RuntimeError("crash"))

        # Drive enough ticks to trigger AI tick (interval=3).
        loop._update_logic(1.0 / 30.0)  # counter=2
        loop._update_logic(1.0 / 30.0)  # counter=3 → tick fails → counter resets

        assert loop._ai_tick_counter == 0

    def test_ai_execute_intents_exception_does_not_propagate(
        self,
        error_recovery_game_loop,
    ):
        """Contract: ai_service.execute_intents failure also degrades gracefully."""
        loop = error_recovery_game_loop
        loop._update_logic(1.0 / 30.0)
        assert loop.ai_service.managed_unit_count >= 1

        # tick() returns intents, but execute_intents() raises.
        loop.ai_service.tick = Mock(return_value=["fake_intent"])
        loop.ai_service.execute_intents = Mock(side_effect=RuntimeError("exec crash"))

        # Must NOT raise.
        loop._update_ai(1.0 / 30.0)

    def test_ai_tick_failure_does_not_crash_full_update_logic(
        self,
        error_recovery_game_loop,
    ):
        """Contract: full _update_logic call survives AI tick failure.

        End-to-end: _update_logic calls _update_ai among other things.
        A failure in _update_ai must not prevent _update_victory and
        other update steps from running.
        """
        loop = error_recovery_game_loop
        loop._update_logic(1.0 / 30.0)  # register units
        loop.ai_service.tick = Mock(side_effect=RuntimeError("crash"))

        # Drive 10 ticks — none should raise.
        for _ in range(10):
            loop._update_logic(1.0 / 30.0)

        # Game loop is still alive.
        assert loop.state is not None


# ========================================================================
# Render error recovery tests (TD-039)
# ========================================================================


class TestRenderErrorRecovery:
    """Verify _render_scene degrades gracefully when render_pipeline.render fails.

    TD-039 contract: Render failure → log error + skip this frame.
    The exception must NOT propagate to the game loop (which would crash
    the game).
    """

    def test_render_exception_does_not_propagate(self, error_recovery_game_loop):
        """Contract: render_pipeline.render raising Exception does not crash _render_scene."""
        loop = error_recovery_game_loop
        assert loop._render_pipeline is not None

        # Inject failure: make render() raise RuntimeError.
        loop._render_pipeline.render = Mock(side_effect=RuntimeError("render crash"))

        screen = Mock()
        # Must NOT raise — _render_scene should catch and log error.
        loop._render_scene(screen, alpha=0.5)

    def test_render_failure_skips_remaining_steps(self, error_recovery_game_loop):
        """Contract: if Step 1 (render_pipeline) fails, Steps 2+3 are skipped.

        This is implicit in the try/except structure: once the exception is
        caught, the rest of the try block is skipped.
        """
        loop = error_recovery_game_loop
        render_call_count = 0

        def failing_render(*args, **kwargs):
            nonlocal render_call_count
            render_call_count += 1
            raise RuntimeError("render crash")

        loop._render_pipeline.render = failing_render

        # Also mock weather/lighting to verify they are NOT called.
        if loop._weather_renderer is not None:
            loop._weather_renderer.render = Mock()

        screen = Mock()
        loop._render_scene(screen, alpha=0.5)

        # render_pipeline.render was called (and failed).
        assert render_call_count == 1
        # weather_renderer.render was NOT called (skipped due to exception).
        if loop._weather_renderer is not None:
            loop._weather_renderer.render.assert_not_called()

    def test_render_failure_does_not_crash_game_loop(
        self,
        error_recovery_game_loop,
    ):
        """Contract: full _render_scene call survives render failure.

        End-to-end: the game loop can continue running even if rendering
        fails every frame.
        """
        loop = error_recovery_game_loop
        loop._render_pipeline.render = Mock(side_effect=RuntimeError("persistent crash"))

        screen = Mock()
        # Drive 10 render calls — none should raise.
        for _ in range(10):
            loop._render_scene(screen, alpha=0.5)

        # Game loop is still alive.
        assert loop.state is not None

    def test_render_pipeline_none_returns_early(self, error_recovery_game_loop):
        """Contract: _render_pipeline=None → early return (not an error)."""
        loop = error_recovery_game_loop
        original_pipeline = loop._render_pipeline
        loop._render_pipeline = None

        screen = Mock()
        # Must NOT raise — just returns early.
        loop._render_scene(screen, alpha=0.5)

        # Restore for cleanup.
        loop._render_pipeline = original_pipeline
