"""Integration tests for day_night_cycle wiring into GameLoop (v0.7.6 Wave 3).

Verifies the TD-077 INTEGRATE of ``day_night_cycle.GameTime`` into the game loop:
  - GameLoopAssembler wires a single GameTime into both ``_game_time`` (typed
    accessor) and ``_day_night_cycle`` (IDayNightCycle slot consumed by
    game_loop_updating.py).
  - ``GameLoop._update_logic(dt)`` advances the wired GameTime.
  - ``_update_audio_sync`` reads ``time_of_day`` (float 0.0–24.0) and forwards
    ``int(hour) % 24`` to ``IEnvironmentalAudio.set_time_of_day``.
  - ``_update_visual_effects`` reads ``time_of_day`` and forwards the
    normalized ``tod / 24.0`` to ``IDynamicShadowSystem.set_time_of_day``.
  - GameTime boundary behavior (total_seconds=0, time_scale=1.0, day wrap)
    and TimeOfDay phase transitions (DAWN/DAY/DUSK/NIGHT).

These are integration tests — they exercise the wiring between GameLoopAssembler,
GameTime, and the update-mixin adapter code as a connected subsystem. Pure
GameTime unit tests live in tests/unit/test_day_night_cycle.py.
"""

from __future__ import annotations

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
from pycc2.domain.systems.day_night_cycle import GameTime, TimeOfDay
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.infrastructure.events.event_bus import EventBus
from pycc2.presentation.rendering.camera import Camera
from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer
from pycc2.presentation.rendering.window_config import WindowManager
from pycc2.services.game_loop import GameLoop, GameState

# ============================================================================
# Test fixtures — mirror tests/unit/test_game_loop.py pattern
# ============================================================================


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
    return Mock(spec=EnhancedRenderer)


@pytest.fixture
def mock_window_manager():
    wm = Mock(spec=WindowManager)
    screen = Mock()
    screen.get_width.return_value = 1280
    screen.get_height.return_value = 720
    screen.get_size.return_value = (1280, 720)
    screen.blit = Mock()
    screen.get_rect.return_value = pygame.Rect(0, 0, 1280, 720)
    wm.get_screen.return_value = screen
    wm._screen = screen
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
    """Fully assembled GameLoop with day_night_cycle wired by GameLoopAssembler.

    EnvironmentalAudio is replaced with a Mock after construction so tests can
    assert on set_time_of_day calls deterministically (the real system may be
    unavailable in headless SDL dummy mode).
    """
    loop = GameLoop(
        renderer=mock_renderer,
        window_manager=mock_window_manager,
        event_bus=event_bus,
        state=game_state,
    )
    # Replace env audio with a Mock for deterministic assertion
    loop._environmental_audio = Mock()
    loop._environmental_audio.update = Mock()
    loop._environmental_audio.set_time_of_day = Mock()
    loop._environmental_audio.set_weather_rain = Mock()
    loop._environmental_audio.set_combat_intensity = Mock()
    # Neutralize victory evaluator so update_logic doesn't pause the game
    if loop._victory_manager is not None:
        loop._victory_manager._victory_evaluator = None
    return loop


def _run_update_logic(loop: GameLoop, dt: float = 0.1) -> None:
    """Call _update_logic with combat_director.update patched out.

    Patches combat_director.update / process_effects so the test exercises
    only the day-night/audio/shadow wiring, not real combat resolution.
    """
    with patch.object(loop._combat_director, "update"):
        with patch.object(loop._combat_director, "process_effects"):
            loop._update_logic(dt)


# ============================================================================
# Wave 3 — GameLoopAssembler wires GameTime into GameLoop
# ============================================================================


class TestGameTimeWiring:
    """GameLoopAssembler._init_day_night_cycle wires GameTime correctly."""

    def test_game_time_property_returns_instance(self, game_loop):
        """game_loop.game_time returns a GameTime instance (not None)."""
        assert game_loop.game_time is not None
        assert isinstance(game_loop.game_time, GameTime)

    def test_day_night_cycle_slot_is_same_instance_as_game_time(self, game_loop):
        """The IDayNightCycle slot aliases the same GameTime instance.

        This guarantees the v0.7.3 adapter code in game_loop_updating.py
        (which reads _day_night_cycle) operates on the wired GameTime.
        """
        assert game_loop._day_night_cycle is game_loop._game_time

    def test_game_time_starts_at_total_seconds_zero(self, game_loop):
        """Freshly wired GameTime starts at total_seconds=0 (midnight)."""
        assert game_loop.game_time.total_seconds == 0.0
        assert game_loop.game_time.hours == pytest.approx(0.0, abs=1e-9)

    def test_game_time_default_time_scale_is_600(self, game_loop):
        """Default time_scale=600.0 (1 real sec = 10 in-game minutes)."""
        assert game_loop.game_time.time_scale == 600.0


# ============================================================================
# Happy Path — GameTime.advance(dt) updates hours and time_phase
# ============================================================================


class TestGameTimeAdvance:
    """Happy path: advance(dt) progresses in-game time correctly."""

    def test_advance_increases_total_seconds(self):
        gt = GameTime()
        gt.advance(0.5)
        assert gt.total_seconds == pytest.approx(0.5, rel=1e-9)

    def test_advance_one_real_second_yields_ten_in_game_minutes(self):
        """time_scale=600 → 1 real sec × 600 / 3600 = 1/6 hour = 10 minutes."""
        gt = GameTime(time_scale=600.0)
        gt.advance(1.0)
        assert gt.hours == pytest.approx(10.0 / 60.0, rel=1e-9)
        assert gt.minutes == 10

    def test_advance_multiple_steps_accumulates(self):
        gt = GameTime(time_scale=600.0)
        for _ in range(10):
            gt.advance(0.1)
        assert gt.total_seconds == pytest.approx(1.0, rel=1e-9)
        # 1 real sec × 600 / 3600 = 1/6 hour ≈ 0.1667
        assert gt.hours == pytest.approx(1.0 / 6.0, rel=1e-9)

    def test_time_of_day_returns_float_in_zero_to_24_range(self):
        """IDayNightCycle.time_of_day contract: float in [0.0, 24.0)."""
        gt = GameTime(time_scale=600.0)
        for _ in range(100):
            gt.advance(1.0)
            tod = gt.time_of_day
            assert isinstance(tod, float)
            assert 0.0 <= tod < 24.0


# ============================================================================
# Boundary — total_seconds=0, time_scale=1.0, day wrap
# ============================================================================


class TestGameTimeBoundaries:
    """Boundary conditions: zero time, time_scale=1.0, midnight wrap."""

    def test_total_seconds_zero_yields_night_phase(self):
        """At t=0 (midnight), time_phase is NIGHT (h<5)."""
        gt = GameTime()
        assert gt.total_seconds == 0.0
        assert gt.hours == 0.0
        assert gt.time_phase is TimeOfDay.NIGHT

    def test_time_scale_one_makes_one_real_second_one_in_game_second(self):
        """time_scale=1.0 → 1 real sec = 1/3600 hour (1 in-game second)."""
        gt = GameTime(time_scale=1.0)
        gt.advance(3600.0)  # 1 real hour
        assert gt.hours == pytest.approx(1.0, rel=1e-9)

    def test_day_wraps_around_midnight(self):
        """Crossing 24h wraps back to 0 (modulo arithmetic in hours property)."""
        gt = GameTime(time_scale=600.0)
        # Set to 23:00 then advance 1 hour of in-game time
        # 1 in-game hour = 3600/600 = 6 real seconds
        gt.set_time(23.0)
        gt.advance(6.0)
        assert gt.hours < 1.0  # wrapped past midnight
        assert gt.hours >= 0.0

    def test_time_phase_transitions_during_one_full_day(self):
        """Advancing a full in-game day visits all 4 TimeOfDay phases.

        24 in-game hours = 24 × 3600 / 600 = 144 real seconds.
        """
        gt = GameTime(time_scale=600.0)
        seen_phases: set[TimeOfDay] = set()
        # Sample every 30 in-game minutes (0.5 hour) for a full day
        # 0.5 in-game hour = 1800/600 = 3 real seconds per step
        for _ in range(48):  # 48 × 0.5 = 24 hours
            gt.advance(3.0)
            seen_phases.add(gt.time_phase)
        assert seen_phases == {TimeOfDay.DAWN, TimeOfDay.DAY, TimeOfDay.DUSK, TimeOfDay.NIGHT}


# ============================================================================
# TimeOfDay phase boundary values (DAWN/DAY/DUSK/NIGHT)
# ============================================================================


class TestTimePhaseBoundaries:
    """TimeOfDay phase transitions occur at the documented hour boundaries."""

    @pytest.mark.parametrize(
        "hour,expected_phase",
        [
            # DAWN: 5 <= h < 7
            (5.0, TimeOfDay.DAWN),
            (5.5, TimeOfDay.DAWN),
            (6.999, TimeOfDay.DAWN),
            # DAY: 7 <= h < 18
            (7.0, TimeOfDay.DAY),
            (12.0, TimeOfDay.DAY),
            (17.999, TimeOfDay.DAY),
            # DUSK: 18 <= h < 20
            (18.0, TimeOfDay.DUSK),
            (19.0, TimeOfDay.DUSK),
            (19.999, TimeOfDay.DUSK),
            # NIGHT: h < 5 or h >= 20
            (20.0, TimeOfDay.NIGHT),
            (23.999, TimeOfDay.NIGHT),
            (0.0, TimeOfDay.NIGHT),
            (4.999, TimeOfDay.NIGHT),
        ],
    )
    def test_phase_boundary(self, hour, expected_phase):
        gt = GameTime(time_scale=600.0)
        gt.set_time(hour)
        assert gt.time_phase is expected_phase


# ============================================================================
# Integration — GameLoop._update_logic advances wired GameTime
# ============================================================================


class TestGameLoopUpdateAdvancesTime:
    """_update_logic(dt) drives the wired GameTime forward each tick."""

    def test_update_logic_advances_total_seconds(self, game_loop):
        """A single _update_logic(dt) call advances game_time.total_seconds by dt."""
        initial = game_loop.game_time.total_seconds
        _run_update_logic(game_loop, dt=0.1)
        assert game_loop.game_time.total_seconds == pytest.approx(initial + 0.1, rel=1e-9)

    def test_update_logic_multiple_ticks_accumulate(self, game_loop):
        """Multiple ticks accumulate time correctly."""
        initial = game_loop.game_time.total_seconds
        for _ in range(5):
            _run_update_logic(game_loop, dt=0.1)
        assert game_loop.game_time.total_seconds == pytest.approx(initial + 0.5, rel=1e-9)

    def test_update_logic_does_not_advance_when_paused(self, game_loop):
        """When state.paused is True, _update_logic returns early (no time advance)."""
        game_loop.state.paused = True
        initial = game_loop.game_time.total_seconds
        _run_update_logic(game_loop, dt=0.1)
        assert game_loop.game_time.total_seconds == initial


# ============================================================================
# Integration — environmental audio receives int hour from time_of_day
# ============================================================================


class TestEnvironmentalAudioSync:
    """_update_audio_sync forwards int(time_of_day) % 24 to env audio."""

    def test_set_time_of_day_called_with_int_hour(self, game_loop):
        """After _update_logic, env_audio.set_time_of_day receives an int in [0, 24)."""
        # Advance to ~6.5 in-game hours (DAWN)
        # 6.5 in-game hours = 6.5 × 3600 / 600 = 39 real seconds
        game_loop.game_time.advance(39.0)
        _run_update_logic(game_loop, dt=0.016)

        game_loop._environmental_audio.set_time_of_day.assert_called()
        call_args = game_loop._environmental_audio.set_time_of_day.call_args
        hour = call_args.args[0]
        assert isinstance(hour, int)
        assert 0 <= hour < 24
        # ~6.5 hours → int(6.5) % 24 == 6
        assert hour == 6

    def test_set_time_of_day_wraps_past_midnight(self, game_loop):
        """Hour wraps via % 24 when time_of_day exceeds 24 (cannot happen due to
        hours modulo, but the adapter applies % 24 defensively)."""
        # Set time to 23.9 in-game hours
        game_loop.game_time.set_time(23.9)
        _run_update_logic(game_loop, dt=0.016)

        call_args = game_loop._environmental_audio.set_time_of_day.call_args
        hour = call_args.args[0]
        assert 0 <= hour < 24
        assert hour == 23

    def test_set_time_of_day_zero_at_midnight(self, game_loop):
        """At t=0 (midnight), env_audio.set_time_of_day receives 0."""
        _run_update_logic(game_loop, dt=0.016)
        call_args = game_loop._environmental_audio.set_time_of_day.call_args
        hour = call_args.args[0]
        assert hour == 0


# ============================================================================
# Integration — dynamic shadow system receives normalized float from time_of_day
# ============================================================================


class TestDynamicShadowSync:
    """_update_visual_effects forwards time_of_day / 24.0 to shadow system.

    Uses dt=0.0 in _update_logic so the assertion verifies the normalization
    formula (tod / 24.0) in isolation — _update_weather still calls
    advance(0.0) which is a no-op, leaving time_of_day at the value we set.
    """

    def test_set_time_of_day_called_with_normalized_float(self, game_loop):
        """Shadow system receives a float in [0.0, 1.0] = time_of_day / 24.0."""
        shadow_mock = Mock()
        game_loop._dynamic_shadow_sys = shadow_mock

        # Advance to exactly 12.0 in-game hours (noon) → 12 × 3600 / 600 = 72 real sec
        game_loop.game_time.advance(72.0)
        # dt=0.0 so _update_weather does not advance time further before shadow read
        _run_update_logic(game_loop, dt=0.0)

        shadow_mock.set_time_of_day.assert_called()
        call_args = shadow_mock.set_time_of_day.call_args
        normalized = call_args.args[0]
        assert isinstance(normalized, float)
        assert 0.0 <= normalized <= 1.0
        # 12.0 / 24.0 == 0.5
        assert normalized == pytest.approx(0.5, abs=1e-9)

    def test_set_time_of_day_midnight_yields_zero(self, game_loop):
        """At midnight (hour=0), shadow receives 0.0."""
        shadow_mock = Mock()
        game_loop._dynamic_shadow_sys = shadow_mock

        _run_update_logic(game_loop, dt=0.0)

        call_args = shadow_mock.set_time_of_day.call_args
        normalized = call_args.args[0]
        assert normalized == pytest.approx(0.0, abs=1e-9)

    def test_set_time_of_day_dusk_yields_correct_normalized(self, game_loop):
        """At 19.0 hours (DUSK), shadow receives 19/24 ≈ 0.7917."""
        shadow_mock = Mock()
        game_loop._dynamic_shadow_sys = shadow_mock

        game_loop.game_time.set_time(19.0)
        _run_update_logic(game_loop, dt=0.0)

        call_args = shadow_mock.set_time_of_day.call_args
        normalized = call_args.args[0]
        assert normalized == pytest.approx(19.0 / 24.0, rel=1e-9)
