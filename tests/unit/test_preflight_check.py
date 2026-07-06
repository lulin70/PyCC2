"""Unit tests for preflight_check module (TD-040).

Tests verify that run_preflight_check correctly detects None subsystems
at three tiers (critical / assembler / optional) and returns appropriate
PreflightResult.

Real component for happy path:
    The happy-path test uses a real GameLoop (via fixtures matching
    test_combat_loop.py pattern) to verify the check passes on a properly
    wired instance.

Synthetic objects for failure paths:
    Failure-path tests use SimpleNamespace (not Mock) to construct
    minimal objects with specific None attributes. This is appropriate
    because the test target is run_preflight_check's logic, not GameLoop
    behavior — we need to simulate wiring failures that cannot be
    reliably reproduced on a real GameLoop (whose __post_init__ always
    wires all subsystems).
"""

from __future__ import annotations

import os
from types import SimpleNamespace
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
from pycc2.infrastructure.diagnostics.preflight_check import (
    PreflightResult,
    run_preflight_check,
)
from pycc2.infrastructure.events.event_bus import EventBus
from pycc2.presentation.rendering.camera import Camera
from pycc2.presentation.rendering.sprite_renderer import SpriteRenderer
from pycc2.presentation.rendering.window_config import WindowManager

# ========================================================================
# Fixtures (matching test_combat_loop.py pattern for real GameLoop test)
# ========================================================================


@pytest.fixture
def real_game_map():
    """16×16 map with open terrain."""
    grid = np.zeros((16, 16), dtype=np.int8)
    return GameMap(id="test", name="Test Map", width=16, height=16, tile_grid=grid)


@pytest.fixture
def ally_unit() -> Unit:
    return Unit(
        id="ally_1",
        name="Ally Unit",
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
        position=PositionComponent(tile_coord=TileCoord(5, 5)),
        vision=VisionComponent(range_tiles=5),
    )


@pytest.fixture
def sprite_renderer(pygame_display):
    """Real SpriteRenderer (requires pygame_display for init ordering)."""
    import pygame

    if not pygame.font.get_init():
        pygame.font.init()
    return SpriteRenderer()


@pytest.fixture
def mock_window_manager():
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
def event_bus():
    return EventBus()


# ========================================================================
# PreflightResult dataclass tests
# ========================================================================


class TestPreflightResult:
    """Tests for PreflightResult dataclass."""

    def test_default_construction(self):
        """Contract: PreflightResult(ok=True) has empty failures list."""
        result = PreflightResult(ok=True)
        assert result.ok is True
        assert result.failures == []

    def test_with_failures(self):
        """Contract: PreflightResult(ok=False, failures=[...]) preserves failures."""
        result = PreflightResult(ok=False, failures=["subsystem X is None"])
        assert result.ok is False
        assert len(result.failures) == 1
        assert "subsystem X" in result.failures[0]

    def test_failures_independent_per_instance(self):
        """Contract: failures list is independent per instance (default_factory)."""
        a = PreflightResult(ok=False)
        b = PreflightResult(ok=False)
        a.failures.append("error A")
        assert b.failures == []


# ========================================================================
# run_preflight_check failure-path tests (synthetic objects)
# ========================================================================


def _make_synthetic_game_loop(**overrides):
    """Build a minimal object with all subsystems set to non-None sentinels.

    Tests can override specific attributes to None to simulate wiring failures.
    """
    sentinel = object()  # non-None sentinel
    base = SimpleNamespace(
        renderer=sentinel,
        window_manager=sentinel,
        event_bus=sentinel,
        state=sentinel,
        display_config=sentinel,
        _combat_director=sentinel,
        _render_pipeline=sentinel,
        _event_dispatcher=sentinel,
        ai_service=sentinel,
        sound_system=sentinel,
        input_handler=sentinel,
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


class TestPreflightCheckFailures:
    """Verify run_preflight_check detects None subsystems at each tier."""

    def test_all_present_returns_ok(self):
        """Contract: all subsystems non-None → ok=True, empty failures."""
        gl = _make_synthetic_game_loop()
        result = run_preflight_check(gl)
        assert result.ok is True
        assert result.failures == []

    @pytest.mark.parametrize(
        "subsystem",
        ["renderer", "window_manager", "event_bus", "state", "display_config"],
    )
    def test_critical_subsystem_none_fails(self, subsystem):
        """Contract: any critical subsystem None → ok=False with named failure."""
        gl = _make_synthetic_game_loop(**{subsystem: None})
        result = run_preflight_check(gl)
        assert result.ok is False
        assert len(result.failures) == 1
        assert subsystem in result.failures[0]
        assert "Critical" in result.failures[0]

    @pytest.mark.parametrize(
        "subsystem",
        ["_combat_director", "_render_pipeline", "_event_dispatcher"],
    )
    def test_assembler_subsystem_none_fails(self, subsystem):
        """Contract: any assembler subsystem None → ok=False with named failure."""
        gl = _make_synthetic_game_loop(**{subsystem: None})
        result = run_preflight_check(gl)
        assert result.ok is False
        assert len(result.failures) == 1
        assert subsystem in result.failures[0]
        assert "Assembler" in result.failures[0]

    @pytest.mark.parametrize(
        "subsystem",
        ["ai_service", "sound_system", "input_handler"],
    )
    def test_optional_subsystem_none_does_not_fail(self, subsystem):
        """Contract: optional subsystem None → ok=True (headless mode acceptable)."""
        gl = _make_synthetic_game_loop(**{subsystem: None})
        result = run_preflight_check(gl)
        assert result.ok is True
        assert result.failures == []

    def test_multiple_critical_failures_all_reported(self):
        """Contract: multiple None subsystems → all failures reported in list."""
        gl = _make_synthetic_game_loop(renderer=None, event_bus=None)
        result = run_preflight_check(gl)
        assert result.ok is False
        assert len(result.failures) == 2
        assert any("renderer" in f for f in result.failures)
        assert any("event_bus" in f for f in result.failures)

    def test_mixed_tier_failures_all_reported(self):
        """Contract: failures across tiers (critical + assembler) all reported."""
        gl = _make_synthetic_game_loop(
            renderer=None,  # critical
            _combat_director=None,  # assembler
        )
        result = run_preflight_check(gl)
        assert result.ok is False
        assert len(result.failures) == 2
        assert any("Critical" in f and "renderer" in f for f in result.failures)
        assert any("Assembler" in f and "_combat_director" in f for f in result.failures)

    def test_optional_none_does_not_mask_critical_failure(self):
        """Contract: optional None + critical None → ok=False (critical dominates)."""
        gl = _make_synthetic_game_loop(
            ai_service=None,  # optional
            renderer=None,  # critical
        )
        result = run_preflight_check(gl)
        assert result.ok is False
        assert len(result.failures) == 1
        assert "renderer" in result.failures[0]


# ========================================================================
# run_preflight_check happy-path test (real GameLoop)
# ========================================================================


class TestPreflightCheckRealGameLoop:
    """Verify run_preflight_check passes on a real, properly-wired GameLoop."""

    def test_real_game_loop_passes_preflight(
        self,
        pygame_display,
        real_game_map,
        ally_unit,
        enemy_unit,
        sprite_renderer,
        mock_window_manager,
        event_bus,
    ):
        """Contract: real GameLoop (post-assemble) passes preflight check.

        This is the end-to-end contract: GameLoopAssembler wires all
        subsystems, and run_preflight_check confirms they are all non-None.
        """
        from pycc2.services.game_loop import GameLoop, GameState

        camera = Camera(
            position=Vec2(256.0, 256.0),
            viewport_width=1280,
            viewport_height=720,
        )
        state = GameState(
            game_map=real_game_map,
            units=[ally_unit, enemy_unit],
            camera=camera,
        )
        loop = GameLoop(
            renderer=sprite_renderer,
            window_manager=mock_window_manager,
            event_bus=event_bus,
            state=state,
            use_full_hud=False,
        )

        result = run_preflight_check(loop)

        assert result.ok is True, f"Preflight failures: {result.failures}"
        assert result.failures == []
