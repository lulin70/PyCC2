"""Integration tests for AI behavior driven through GameLoop (TD-037).

These tests verify that AI-controlled units are driven end-to-end through
the GameLoop fixed-timestep simulation, not just by direct calls to
``system.tick(unit)`` or ``evaluate_tick()``.

Why this file exists:
    TD-037 (🟡 PARTIAL) documented that ``tests/e2e/test_ai_behaviors_e2e.py``
    covers ammo pickup / weapon jam / surrender / squad degradation / NCO
    rally / smoke, but those tests bypass the GameLoop by calling
    ``system.tick(unit)`` directly. ``tests/integration/test_combat_loop.py``
    instantiates GameLoop but tests combat flow, not AI behavior end-to-end.

    This file fills the gap: it instantiates a real GameLoop with a real
    AIService, adds both player (ALLIES) and enemy (AXIS) units to the
    shared GameState, drives N ticks of ``_update_logic(dt)``, and asserts
    that:

    1. Enemy units are auto-registered with the AIService via the
       ``_ensure_ai_units_registered`` safety net (game_loop_updating.py
       L253-304).
    2. ``AIService.tick()`` is actually invoked by the GameLoop's
       ``_update_ai`` scheduler (game_loop_updating.py L306-320) after
       ``_ai_update_interval`` ticks.
    3. The full chain GameLoop → _update_logic → _update_ai →
       ai_service.tick → ai_service.execute_intents runs without raising.

Real components, no mocks:
    Per the project testing philosophy, the GameLoop, AIService,
    BehaviorTree (via UnitBTFactory), TacticExecutor, EventBus, and
    GameState are all real production classes. Only the WindowManager is
    a Mock (required for headless pygame), matching the pattern in
    ``test_combat_loop.py``.
"""

from __future__ import annotations

import os
from unittest.mock import Mock

import numpy as np
import pytest

# Headless pygame guard — GameLoop import chain pulls in pygame.
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
def ai_game_map():
    """16×16 map with open terrain (all zeros = OPEN)."""
    grid = np.zeros((16, 16), dtype=np.int8)
    return GameMap(id="ai_test", name="AI Test Map", width=16, height=16, tile_grid=grid)


@pytest.fixture
def player_unit() -> Unit:
    """Player-controlled ALLIES unit."""
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
    """AI-controlled AXIS unit (will be auto-registered with AIService)."""
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
def ai_camera():
    return Camera(position=Vec2(256.0, 256.0), viewport_width=1280, viewport_height=720)


@pytest.fixture
def ai_sprite_renderer(pygame_display):
    """Real SpriteRenderer (requires pygame_display fixture for init ordering)."""
    import pygame

    if not pygame.font.get_init():
        pygame.font.init()
    return SpriteRenderer()


@pytest.fixture
def ai_window_manager():
    """Mock WindowManager for headless pygame (same pattern as test_combat_loop)."""
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
def ai_event_bus():
    return EventBus()


@pytest.fixture
def ai_game_state(ai_game_map, player_unit, enemy_unit, ai_camera):
    """GameState with one player unit and one enemy unit."""
    return GameState(
        game_map=ai_game_map,
        units=[player_unit, enemy_unit],
        camera=ai_camera,
    )


@pytest.fixture
def ai_game_loop(
    ai_sprite_renderer,
    ai_window_manager,
    ai_event_bus,
    ai_game_state,
):
    """GameLoop with a REAL AIService attached.

    This is the key difference from ``combat_game_loop`` in
    ``test_combat_loop.py``: that fixture leaves ``ai_service=None``, so
    ``_update_ai`` is a no-op. This fixture attaches a real AIService so
    the GameLoop → AIService integration can be exercised end-to-end.
    """
    loop = GameLoop(
        renderer=ai_sprite_renderer,
        window_manager=ai_window_manager,
        event_bus=ai_event_bus,
        state=ai_game_state,
        use_full_hud=False,
        ai_service=AIService(event_bus=ai_event_bus),
    )
    return loop


# ========================================================================
# Integration tests: GameLoop → AIService end-to-end
# ========================================================================


class TestAIGameLoopIntegration:
    """Verify AI units are driven through GameLoop._update_logic.

    These tests close the TD-037 gap: AI behavior is exercised through
    the GameLoop fixed-timestep simulation, not just direct system.tick()
    calls.
    """

    def test_ai_service_attached_to_game_loop(self, ai_game_loop):
        """Contract: the GameLoop has a real AIService attached.

        Without this, _update_ai is a no-op and AI units never tick.
        """
        assert ai_game_loop.ai_service is not None
        assert isinstance(ai_game_loop.ai_service, AIService)
        assert ai_game_loop.ai_service.managed_unit_count == 0

    def test_enemy_units_auto_registered_via_update_logic(
        self,
        ai_game_loop,
        enemy_unit,
    ):
        """Contract: _update_logic auto-registers enemy units with AIService.

        GameLoop._update_ai calls _ensure_ai_units_registered (L308) which
        detects AXIS units not yet in AIService and registers them with
        a behavior tree from UnitBTFactory.

        Scenario: GameLoop has 1 ALLIES + 1 AXIS unit. AIService starts empty.
        Expected: after 1 _update_logic call, enemy_unit is registered.
        """
        assert ai_game_loop.ai_service.managed_unit_count == 0

        ai_game_loop._update_logic(1.0 / 30.0)

        assert ai_game_loop.ai_service.managed_unit_count == 1
        assert enemy_unit.id in ai_game_loop.ai_service._unit_entities

    def test_ai_tick_executed_after_update_interval(
        self,
        ai_game_loop,
    ):
        """Contract: AIService.tick() is invoked after _ai_update_interval ticks.

        GameLoop._update_ai (L310-320) increments _ai_tick_counter each call
        and only invokes ai_service.tick() when the counter reaches
        _ai_update_interval (default 3). After tick(), the counter resets.

        Scenario: Call _update_logic 3 times (default interval).
        Expected: ai_service._current_tick increments (tick was executed).
        """
        initial_tick = ai_game_loop.ai_service._current_tick

        # Tick 1 — registers units, counter=1
        ai_game_loop._update_logic(1.0 / 30.0)
        # Tick 2 — counter=2
        ai_game_loop._update_logic(1.0 / 30.0)
        # Tick 3 — counter reaches 3 → tick executed → counter resets to 0
        ai_game_loop._update_logic(1.0 / 30.0)

        assert ai_game_loop.ai_service._current_tick > initial_tick

    def test_full_ai_chain_runs_without_error(self, ai_game_loop):
        """Contract: GameLoop → _update_ai → tick → execute_intents runs clean.

        End-to-end smoke: drive 10 ticks (3+ AI tick cycles) and verify no
        exception is raised. This exercises the full chain including
        BehaviorTree evaluation, TacticIntent generation (if any), and
        TacticExecutor execution.
        """
        # Drive 10 ticks = ~3 AI tick cycles (interval=3).
        for _ in range(10):
            ai_game_loop._update_logic(1.0 / 30.0)

        # If we got here without raising, the chain works end-to-end.
        assert ai_game_loop.ai_service.managed_unit_count >= 1
        assert ai_game_loop.ai_service._current_tick >= 1

    def test_ai_tick_counter_resets_after_execution(self, ai_game_loop):
        """Contract: _ai_tick_counter resets to 0 after tick() is executed.

        GameLoop._update_ai (L312-320): when _ai_tick_counter reaches
        _ai_update_interval, tick() runs and counter resets to 0.

        Scenario: Call _update_logic exactly _ai_update_interval times.
        Expected: _ai_tick_counter == 0 (reset after execution).
        """
        interval = ai_game_loop._ai_update_interval

        for _ in range(interval):
            ai_game_loop._update_logic(1.0 / 30.0)

        # After exactly `interval` calls, tick executed and counter reset.
        assert ai_game_loop._ai_tick_counter == 0

    def test_ai_continues_ticking_across_multiple_cycles(self, ai_game_loop):
        """Contract: AI ticks repeatedly across multiple cycles.

        Scenario: Drive 9 _update_logic calls (3 full AI tick cycles at
        interval=3).
        Expected: ai_service._current_tick >= 3 (3 tick executions).
        """
        for _ in range(9):
            ai_game_loop._update_logic(1.0 / 30.0)

        # 9 calls / interval 3 = 3 tick executions.
        assert ai_game_loop.ai_service._current_tick >= 3
