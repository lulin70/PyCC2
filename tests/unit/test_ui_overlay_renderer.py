"""Unit tests for UIOverlayRenderer.

Rendering happens on an offscreen ``pygame.Surface`` with the SDL dummy
video driver. Assertions are structural or sample a small region of
pixels, never the full frame, so the tests stay fast and deterministic.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from types import SimpleNamespace

import numpy as np
import pygame
import pytest

from pycc2.domain.entities.game_map import GameMap, MapObjective
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.presentation.input.attack_line_system import (
    AttackLineStatus,
    AttackLineSystem,
    AttackTarget,
)
from pycc2.presentation.rendering.camera import Camera
from pycc2.presentation.rendering.render_context import RenderContext
from pycc2.presentation.rendering.ui_overlay_renderer import UIOverlayRenderer

TILE_SIZE = 32


# ===========================================================================
# Fixtures / helpers
# ===========================================================================


@pytest.fixture(scope="module", autouse=True)
def _pygame_ready():
    pygame.init()
    pygame.font.init()
    yield


@pytest.fixture()
def surface() -> pygame.Surface:
    return pygame.Surface((800, 600))


@pytest.fixture()
def camera() -> Camera:
    return Camera(position=Vec2(0, 0), viewport_width=800, viewport_height=600)


@pytest.fixture()
def ctx(surface) -> RenderContext:
    return RenderContext(tile_size=TILE_SIZE, offscreen=surface)


@pytest.fixture()
def renderer(ctx) -> UIOverlayRenderer:
    return UIOverlayRenderer(ctx)


def _make_map(width: int = 8, height: int = 8) -> GameMap:
    return GameMap(
        id="test",
        name="test",
        width=width,
        height=height,
        tile_grid=np.zeros((height, width), dtype=np.int8),
    )


def _make_objective(
    tile_x: int,
    tile_y: int,
    owner: str | None = None,
    points: object = None,
) -> MapObjective:
    return MapObjective(
        id=f"vl_{tile_x}_{tile_y}",
        name="VL",
        position=TileCoord(tile_x, tile_y),
        owner=owner,
        points=points,  # type: ignore[arg-type]
    )


def _unit_at(tile_x: int, tile_y: int, vision=None) -> SimpleNamespace:
    return SimpleNamespace(
        position=SimpleNamespace(tile_coord=TileCoord(tile_x, tile_y)),
        vision=vision,
    )


def _has_color(surface, color, x0, x1, y0, y1) -> bool:
    region = pygame.surfarray.array3d(surface)[x0:x1, y0:y1]
    return bool(np.all(region == np.array(color, dtype=np.uint8), axis=2).any())


def _non_black_count(surface, x0, x1, y0, y1) -> int:
    region = pygame.surfarray.array3d(surface)[x0:x1, y0:y1]
    return int(np.any(region != 0, axis=2).sum())


class _FakeSpriteRenderer:
    """Minimal stand-in for SpriteRenderer used by draw_vl_flags."""

    def __init__(self, exc: Exception | None = None) -> None:
        self._target_surface = "original"
        self._exc = exc
        self.targets_at_call: list[object] = []
        self.calls: list[tuple[object, object]] = []

    def _draw_vl_flags(self, game_map, camera) -> None:
        self.targets_at_call.append(self._target_surface)
        self.calls.append((game_map, camera))
        if self._exc is not None:
            raise self._exc


# ===========================================================================
# Construction / dependency injection
# ===========================================================================


@pytest.mark.unit
class TestConstruction:
    def test_initial_state(self, renderer):
        assert renderer._attack_line_system is None
        assert renderer._los_overlay is None
        assert renderer._los_overlay_size == (0, 0)

    def test_set_attack_line_system(self, renderer):
        system = AttackLineSystem()
        renderer.set_attack_line_system(system)
        assert renderer._attack_line_system is system


# ===========================================================================
# draw_vl_flags
# ===========================================================================


@pytest.mark.unit
class TestDrawVlFlags:
    def test_returns_early_when_offscreen_is_none(self, camera):
        renderer = UIOverlayRenderer(RenderContext(tile_size=TILE_SIZE, offscreen=None))
        renderer.draw_vl_flags(_make_map(), camera)

    def test_delegates_to_sprite_renderer_and_restores_target(self, ctx, camera, surface):
        fake = _FakeSpriteRenderer()
        ctx.sprite_renderer = fake
        renderer = UIOverlayRenderer(ctx)
        game_map = _make_map()

        renderer.draw_vl_flags(game_map, camera)

        assert fake.calls == [(game_map, camera)]
        assert fake.targets_at_call == [surface]
        assert fake._target_surface == "original"

    def test_restores_target_when_sprite_renderer_raises(self, ctx, camera):
        fake = _FakeSpriteRenderer(exc=RuntimeError("render failure"))
        ctx.sprite_renderer = fake
        renderer = UIOverlayRenderer(ctx)

        with pytest.raises(RuntimeError, match="render failure"):
            renderer.draw_vl_flags(_make_map(), camera)

        assert fake._target_surface == "original"

    def test_fallback_with_no_objectives_draws_nothing(self, renderer, camera, surface):
        renderer.draw_vl_flags(_make_map(), camera)
        assert surface.get_at((416, 305))[:3] == (0, 0, 0)

    def test_fallback_draws_flag_pole(self, renderer, camera, surface):
        game_map = _make_map()
        game_map.objectives = [_make_objective(0, 0, owner="allies")]

        renderer.draw_vl_flags(game_map, camera)

        assert surface.get_at((416, 305))[:3] == (80, 80, 80)

    @pytest.mark.parametrize(
        ("owner", "expected"),
        [
            ("allies", (60, 100, 200)),
            ("axis", (200, 60, 60)),
            (None, (200, 200, 200)),
            ("neutral", (200, 200, 200)),
        ],
    )
    def test_fallback_flag_color_by_owner(self, renderer, camera, surface, owner, expected):
        game_map = _make_map()
        game_map.objectives = [_make_objective(0, 0, owner=owner)]

        renderer.draw_vl_flags(game_map, camera)

        assert surface.get_at((425, 300))[:3] == expected

    def test_fallback_draws_vp_number(self, renderer, camera, surface):
        game_map = _make_map()
        game_map.objectives = [_make_objective(0, 0, owner="axis", points=10)]

        renderer.draw_vl_flags(game_map, camera)

        assert _non_black_count(surface, 390, 445, 258, 292) > 0

    def test_fallback_draws_float_vp_number(self, renderer, camera, surface):
        game_map = _make_map()
        game_map.objectives = [_make_objective(0, 0, points=20.5)]

        renderer.draw_vl_flags(game_map, camera)

        assert _non_black_count(surface, 390, 445, 258, 292) > 0

    def test_vp_number_at_unscaled_pulse(self, renderer, camera, surface, monkeypatch):
        import pycc2.presentation.rendering.ui_overlay_renderer as overlay_module

        monkeypatch.setattr(overlay_module._time, "time", lambda: 0.0)
        game_map = _make_map()
        game_map.objectives = [_make_objective(0, 0, points=10)]

        renderer.draw_vl_flags(game_map, camera)

        assert _non_black_count(surface, 390, 445, 258, 292) > 0

    def test_font_failure_during_vp_number_is_ignored(self, renderer, camera, surface, monkeypatch):
        def _fail(*args, **kwargs):
            raise ValueError("font unavailable")

        monkeypatch.setattr(pygame.font, "Font", _fail)
        game_map = _make_map()
        game_map.objectives = [_make_objective(0, 0, points=10)]

        renderer.draw_vl_flags(game_map, camera)

        assert surface.get_at((416, 305))[:3] == (80, 80, 80)

    def test_fallback_skips_non_numeric_points(self, renderer, camera, surface):
        game_map = _make_map()
        game_map.objectives = [_make_objective(0, 0, points="ten")]

        renderer.draw_vl_flags(game_map, camera)

        assert _non_black_count(surface, 390, 445, 258, 292) == 0

    @pytest.mark.parametrize(
        ("owner", "expected"),
        [
            ("allies", (60, 100, 200)),
            ("axis", (200, 60, 60)),
            (None, (200, 200, 200)),
        ],
    )
    def test_off_screen_objective_draws_edge_arrow(
        self, renderer, camera, surface, owner, expected
    ):
        game_map = _make_map()
        game_map.objectives = [_make_objective(100, 100, owner=owner)]

        renderer.draw_vl_flags(game_map, camera)

        assert _has_color(surface, expected, 755, 781, 555, 581)

    def test_fallback_returns_early_without_offscreen(self, camera):
        ctx = RenderContext(tile_size=TILE_SIZE, offscreen=None)
        renderer = UIOverlayRenderer(ctx)

        renderer._draw_vl_flags_fallback(_make_map(), camera)

    def test_edge_arrows_without_offscreen(self, camera):
        ctx = RenderContext(tile_size=TILE_SIZE, offscreen=None)
        renderer = UIOverlayRenderer(ctx)

        renderer._draw_edge_arrows([(100, 100, "allies")], 800, 600, camera)

    def test_edge_arrows_empty_list(self, renderer, camera, surface):
        renderer._draw_edge_arrows([], 800, 600, camera)
        assert _non_black_count(surface, 0, 800, 0, 600) == 0

    def test_edge_arrows_clamp_to_screen_edges(self, renderer, camera, surface):
        renderer._draw_edge_arrows([(-5000, -5000, "axis")], 800, 600, camera)

        assert _has_color(surface, (200, 60, 60), 15, 60, 15, 60)


# ===========================================================================
# draw_grid
# ===========================================================================


@pytest.mark.unit
class TestDrawGrid:
    def test_returns_early_when_offscreen_is_none(self, camera):
        renderer = UIOverlayRenderer(RenderContext(tile_size=TILE_SIZE, offscreen=None))
        renderer.draw_grid(_make_map(), camera)

    def test_draws_grid_lines(self, renderer, camera, surface):
        renderer.draw_grid(_make_map(), camera)

        assert surface.get_at((400, 400))[:3] == (60, 80, 40)
        assert surface.get_at((500, 300))[:3] == (60, 80, 40)

    def test_small_map_is_clamped(self, renderer, camera, surface):
        renderer.draw_grid(_make_map(width=2, height=2), camera)

        assert surface.get_at((400, 300))[:3] == (60, 80, 40)

    def test_camera_zoomed_in(self, renderer, surface):
        zoomed = Camera(position=Vec2(0, 0), zoom=2.0, viewport_width=800, viewport_height=600)
        renderer.draw_grid(_make_map(), zoomed)

        assert _non_black_count(surface, 0, 800, 0, 600) > 0

    def test_camera_outside_map_draws_nothing(self, renderer, surface):
        far = Camera(position=Vec2(10000, 10000), viewport_width=800, viewport_height=600)
        renderer.draw_grid(_make_map(), far)

        assert _non_black_count(surface, 0, 800, 0, 600) == 0

    def test_camera_beyond_top_left_clamps_to_zero(self, renderer, surface):
        negative = Camera(position=Vec2(-100, -100), viewport_width=800, viewport_height=600)
        renderer.draw_grid(_make_map(), negative)

        assert _non_black_count(surface, 0, 800, 0, 600) > 0


# ===========================================================================
# draw_attack_lines
# ===========================================================================


@pytest.mark.unit
class TestDrawAttackLines:
    def _active_system(self, status: AttackLineStatus) -> AttackLineSystem:
        system = AttackLineSystem()
        system.begin_attack("u1", Vec2(100, 100))
        system.state.target = AttackTarget(position=Vec2(300, 100), status=status)
        return system

    def test_returns_early_when_offscreen_is_none(self, camera):
        renderer = UIOverlayRenderer(RenderContext(tile_size=TILE_SIZE, offscreen=None))
        renderer.set_attack_line_system(self._active_system(AttackLineStatus.CAN_ATTACK))
        renderer.draw_attack_lines(camera)

    def test_returns_early_without_attack_line_system(self, renderer, camera, surface):
        renderer.draw_attack_lines(camera)
        assert _non_black_count(surface, 0, 800, 0, 600) == 0

    def test_inactive_state_draws_nothing(self, renderer, camera, surface):
        renderer.set_attack_line_system(AttackLineSystem())
        renderer.draw_attack_lines(camera)

        assert _non_black_count(surface, 0, 800, 0, 600) == 0

    def test_active_without_source_draws_nothing(self, renderer, camera, surface):
        system = AttackLineSystem()
        system.state.active = True
        system.state.source_position = None
        renderer.set_attack_line_system(system)

        renderer.draw_attack_lines(camera)

        assert _non_black_count(surface, 0, 800, 0, 600) == 0

    def test_active_without_target_draws_nothing(self, renderer, camera, surface):
        system = AttackLineSystem()
        system.begin_attack("u1", Vec2(100, 100))
        system.state.target = None
        renderer.set_attack_line_system(system)

        renderer.draw_attack_lines(camera)

        assert _non_black_count(surface, 0, 800, 0, 600) == 0

    def test_can_attack_draws_green_line(self, renderer, camera, surface):
        renderer.set_attack_line_system(self._active_system(AttackLineStatus.CAN_ATTACK))

        renderer.draw_attack_lines(camera)

        assert surface.get_at((600, 400))[:3] == (0, 255, 0)
        assert _has_color(surface, (0, 255, 0), 690, 712, 388, 412)

    def test_out_of_range_draws_red_dashed_line_and_cross(self, renderer, camera, surface):
        renderer.set_attack_line_system(self._active_system(AttackLineStatus.OUT_OF_RANGE))

        renderer.draw_attack_lines(camera)

        assert _has_color(surface, (255, 50, 50), 490, 710, 390, 411)
        assert _has_color(surface, (255, 50, 50), 688, 714, 386, 415)

    def test_blocked_draws_orange_dashed_line_and_marker(self, renderer, camera, surface):
        renderer.set_attack_line_system(self._active_system(AttackLineStatus.BLOCKED))

        renderer.draw_attack_lines(camera)

        assert _has_color(surface, (255, 140, 0), 490, 710, 390, 411)
        assert _has_color(surface, (255, 140, 0), 685, 715, 380, 421)

    def test_unhandled_status_draws_no_active_line(self, renderer, camera, surface):
        renderer.set_attack_line_system(self._active_system(AttackLineStatus.HIT_HIGH))

        renderer.draw_attack_lines(camera)

        assert _non_black_count(surface, 0, 800, 0, 600) == 0

    def test_confirmed_attack_uses_confirmed_source(self, renderer, camera, surface):
        system = AttackLineSystem()
        system._confirmed_sources["u1"] = Vec2(100, 100)
        system._confirmed_attacks["u1"] = AttackTarget(position=Vec2(300, 100), unit_id="target-1")
        renderer.set_attack_line_system(system)

        renderer.draw_attack_lines(camera)

        assert surface.get_at((600, 400))[:3] == (255, 50, 50)

    def test_confirmed_attack_without_source(self, renderer, camera, surface):
        system = AttackLineSystem()
        system._confirmed_attacks["u1"] = AttackTarget(position=Vec2(300, 100), unit_id="target-1")
        renderer.set_attack_line_system(system)

        renderer.draw_attack_lines(camera)

        assert isinstance(surface, pygame.Surface)

    def test_confirmed_attack_without_unit_id_is_skipped(self, renderer, camera, surface):
        system = AttackLineSystem()
        system._confirmed_sources["u1"] = Vec2(100, 100)
        system._confirmed_attacks["u1"] = AttackTarget(position=Vec2(300, 100), unit_id=None)
        renderer.set_attack_line_system(system)

        renderer.draw_attack_lines(camera)

        assert _non_black_count(surface, 0, 800, 0, 600) == 0


# ===========================================================================
# draw_queued_commands
# ===========================================================================


@pytest.mark.unit
class TestDrawQueuedCommands:
    @staticmethod
    def _queued_unit(x: float, y: float, queue: list) -> SimpleNamespace:
        return SimpleNamespace(
            position=SimpleNamespace(pixel_position=Vec2(x, y)),
            has_queued_commands=True,
            _command_queue=queue,
        )

    def test_returns_early_when_offscreen_is_none(self, camera):
        renderer = UIOverlayRenderer(RenderContext(tile_size=TILE_SIZE, offscreen=None))
        unit = self._queued_unit(100, 100, [{"type": "move", "target_x": 2, "target_y": 2}])
        renderer.draw_queued_commands([unit], camera)

    def test_empty_unit_list(self, renderer, camera, surface):
        renderer.draw_queued_commands([], camera)
        assert _non_black_count(surface, 0, 800, 0, 600) == 0

    def test_unit_without_attribute_is_skipped(self, renderer, camera, surface):
        unit = SimpleNamespace(position=SimpleNamespace(pixel_position=Vec2(100, 100)))
        renderer.draw_queued_commands([unit], camera)

        assert _non_black_count(surface, 0, 800, 0, 600) == 0

    def test_unit_without_queued_commands_is_skipped(self, renderer, camera, surface):
        unit = self._queued_unit(100, 100, [{"target_x": 2, "target_y": 2}])
        unit.has_queued_commands = False

        renderer.draw_queued_commands([unit], camera)

        assert _non_black_count(surface, 0, 800, 0, 600) == 0

    def test_unit_without_pixel_position_is_skipped(self, renderer, camera, surface):
        unit = SimpleNamespace(
            position=SimpleNamespace(),
            has_queued_commands=True,
            _command_queue=[{"target_x": 2, "target_y": 2}],
        )

        renderer.draw_queued_commands([unit], camera)

        assert _non_black_count(surface, 0, 800, 0, 600) == 0

    def test_move_command_draws_cyan_dash_and_circle(self, renderer, camera, surface):
        unit = self._queued_unit(100, 100, [{"type": "move", "target_x": 2, "target_y": 2}])

        renderer.draw_queued_commands([unit], camera)

        assert _has_color(surface, (0, 220, 220), 430, 510, 315, 410)

    def test_attack_command_draws_orange_crosshair(self, renderer, camera, surface):
        unit = self._queued_unit(100, 100, [{"type": "attack", "target_x": 3, "target_y": 1}])

        renderer.draw_queued_commands([unit], camera)

        assert _has_color(surface, (255, 165, 0), 470, 520, 300, 360)

    def test_multiple_commands_draw_each_type(self, renderer, camera, surface):
        unit = self._queued_unit(
            100,
            100,
            [
                {"type": "move", "target_x": 2, "target_y": 2},
                {"type": "attack", "target_x": 3, "target_y": 1},
            ],
        )

        renderer.draw_queued_commands([unit], camera)

        assert _has_color(surface, (0, 220, 220), 430, 510, 315, 410)
        assert _has_color(surface, (255, 165, 0), 470, 520, 300, 360)

    def test_command_without_target_defaults_to_origin(self, renderer, camera, surface):
        unit = self._queued_unit(100, 100, [{"type": "move"}])

        renderer.draw_queued_commands([unit], camera)

        assert _has_color(surface, (0, 220, 220), 390, 510, 290, 410)

    def test_out_of_bounds_target_does_not_crash(self, renderer, camera, surface):
        unit = self._queued_unit(100, 100, [{"type": "move", "target_x": 1000, "target_y": 1000}])

        renderer.draw_queued_commands([unit], camera)

    def test_empty_command_queue_draws_nothing(self, renderer, camera, surface):
        unit = self._queued_unit(100, 100, [])

        renderer.draw_queued_commands([unit], camera)

        assert _non_black_count(surface, 0, 800, 0, 600) == 0

    def test_badge_font_failure_is_ignored(self, renderer, camera, surface, monkeypatch):
        def _fail(*args, **kwargs):
            raise AttributeError("font unavailable")

        monkeypatch.setattr(pygame.font, "Font", _fail)
        unit = self._queued_unit(100, 100, [{"type": "move", "target_x": 2, "target_y": 2}])

        renderer.draw_queued_commands([unit], camera)

        assert _has_color(surface, (0, 220, 220), 430, 510, 315, 410)


# ===========================================================================
# render_los_overlay
# ===========================================================================


@pytest.mark.unit
class TestRenderLosOverlay:
    @pytest.fixture()
    def camera(self) -> Camera:
        """Camera whose viewport origin maps to world origin.

        ``origin = -position * zoom + viewport / 2`` → (0, 0) for
        position (400, 300) on an 800×600 viewport at zoom 1.
        """
        return Camera(position=Vec2(400, 300), viewport_width=800, viewport_height=600)

    def test_returns_early_when_unit_is_none(self, renderer, camera, surface):
        renderer.render_los_overlay(surface, None, _make_map(), camera)
        assert _non_black_count(surface, 0, 800, 0, 600) == 0

    def test_returns_early_when_game_map_is_none(self, renderer, camera, surface):
        renderer.render_los_overlay(surface, _unit_at(4, 4), None, camera)
        assert _non_black_count(surface, 0, 800, 0, 600) == 0

    def test_draws_visible_tiles(self, renderer, camera, surface):
        renderer.render_los_overlay(surface, _unit_at(4, 4), _make_map(), camera)

        assert renderer._los_overlay_size == (8 * TILE_SIZE, 8 * TILE_SIZE)
        assert _non_black_count(surface, 0, 8 * TILE_SIZE, 0, 8 * TILE_SIZE) > 0

    def test_unit_center_tile_is_not_tinted(self, renderer, camera, surface):
        renderer.render_los_overlay(surface, _unit_at(4, 4), _make_map(), camera)

        center = (4 * TILE_SIZE, 4 * TILE_SIZE)
        assert surface.get_at(center)[:3] == (0, 0, 0)

    def test_uses_vision_range(self, renderer, camera, surface):
        unit = _unit_at(4, 4, vision=SimpleNamespace(range_tiles=1))

        renderer.render_los_overlay(surface, unit, _make_map(), camera)

        # Tiles farther than one step stay untouched.
        assert surface.get_at((0, 0))[:3] == (0, 0, 0)
        assert (
            _non_black_count(surface, 3 * TILE_SIZE, 6 * TILE_SIZE, 3 * TILE_SIZE, 6 * TILE_SIZE)
            > 0
        )

    def test_unit_at_map_corner_clamps_loop_bounds(self, renderer, camera, surface):
        renderer.render_los_overlay(surface, _unit_at(0, 0), _make_map(), camera)

        assert _non_black_count(surface, 0, 2 * TILE_SIZE, 0, 2 * TILE_SIZE) > 0

    def test_vision_range_larger_than_map(self, renderer, camera, surface):
        unit = _unit_at(4, 4, vision=SimpleNamespace(range_tiles=100))

        renderer.render_los_overlay(surface, unit, _make_map(), camera)

        assert renderer._los_overlay_size == (8 * TILE_SIZE, 8 * TILE_SIZE)
        assert _non_black_count(surface, 0, 8 * TILE_SIZE, 0, 8 * TILE_SIZE) > 0

    def test_blit_uses_camera_transform(self, renderer, surface):
        moved = Camera(position=Vec2(380, 280), viewport_width=800, viewport_height=600)

        renderer.render_los_overlay(surface, _unit_at(4, 4), _make_map(), moved)

        # origin = -380 + 400, -280 + 300 → (20, 20); sample tile (5,4) center
        assert surface.get_at(
            (5 * TILE_SIZE + 20 + TILE_SIZE // 2, 4 * TILE_SIZE + 20 + TILE_SIZE // 2)
        )[:3] != (0, 0, 0)

    def test_blit_scales_with_zoom(self, renderer, surface):
        zoomed = Camera(position=Vec2(400, 300), zoom=2.0, viewport_width=800, viewport_height=600)

        renderer.render_los_overlay(surface, _unit_at(4, 4), _make_map(), zoomed)

        # origin = -400*2 + 400, -300*2 + 300 → (-400, -300); sample tile (7,6) center
        assert surface.get_at(
            (7 * TILE_SIZE * 2 - 400 + TILE_SIZE, 6 * TILE_SIZE * 2 - 300 + TILE_SIZE)
        )[:3] != (0, 0, 0)

    def test_overlay_is_reused_for_same_size(self, renderer, camera, surface):
        renderer.render_los_overlay(surface, _unit_at(4, 4), _make_map(), camera)
        first_overlay = renderer._los_overlay

        renderer.render_los_overlay(surface, _unit_at(2, 2), _make_map(), camera)

        assert renderer._los_overlay is first_overlay

    def test_overlay_is_reallocated_for_new_map_size(self, renderer, camera):
        renderer.render_los_overlay(pygame.Surface((800, 600)), _unit_at(4, 4), _make_map(), camera)
        bigger = _make_map(width=12, height=12)

        renderer.render_los_overlay(pygame.Surface((800, 600)), _unit_at(6, 6), bigger, camera)

        assert renderer._los_overlay_size == (12 * TILE_SIZE, 12 * TILE_SIZE)


# ===========================================================================
# _draw_dashed_line
# ===========================================================================


@pytest.mark.unit
class TestDrawDashedLine:
    def test_returns_early_when_offscreen_is_none(self):
        renderer = UIOverlayRenderer(RenderContext(tile_size=TILE_SIZE, offscreen=None))
        renderer._draw_dashed_line((0, 0), (100, 0), (255, 0, 0))

    def test_draws_dashed_line(self, renderer, surface):
        renderer._draw_dashed_line((10, 50), (100, 50), (255, 0, 0))

        assert surface.get_at((12, 50))[:3] == (255, 0, 0)

    def test_custom_dash_length(self, renderer, surface):
        renderer._draw_dashed_line((10, 50), (100, 50), (0, 255, 0), dash_len=2)

        assert _has_color(surface, (0, 255, 0), 10, 100, 49, 52)

    def test_zero_length_line_is_noop(self, renderer, surface):
        renderer._draw_dashed_line((50, 50), (50, 50), (255, 0, 0))

        assert _non_black_count(surface, 0, 800, 0, 600) == 0

    def test_out_of_bounds_coordinates_are_clipped(self, renderer, surface):
        renderer._draw_dashed_line((-500, -500), (2000, 2000), (255, 0, 0))

        assert _non_black_count(surface, 0, 800, 0, 600) > 0
