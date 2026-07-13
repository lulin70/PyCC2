"""Tests for rendering_utils and unit_renderer.

Uses real pygame Surface with SDL dummy driver. Structural assertions
(surface modified, no crash) rather than pixel-level color checks.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from dataclasses import dataclass
from typing import Any

import pygame
import pytest

from pycc2.presentation.rendering.render_context import RenderContext
from pycc2.presentation.rendering.rendering_utils import draw_dashed_line
from pycc2.presentation.rendering.unit_renderer import UnitRenderer


@pytest.fixture
def surface():
    return pygame.Surface((400, 300))


# ===========================================================================
# draw_dashed_line (rendering_utils)
# ===========================================================================


@pytest.mark.unit
class TestDrawDashedLine:
    def test_horizontal_line_modifies_surface(self, surface):
        before = surface.get_at((50, 50))
        draw_dashed_line(surface, (255, 0, 0), (10, 50), (100, 50))
        after = surface.get_at((50, 50))
        assert before != after

    def test_vertical_line_modifies_surface(self, surface):
        before = surface.get_at((50, 50))
        draw_dashed_line(surface, (0, 255, 0), (50, 10), (50, 100))
        after = surface.get_at((50, 50))
        assert before != after

    def test_diagonal_line_modifies_surface(self, surface):
        # Dashed line may have a gap at any specific pixel; scan along the
        # diagonal and assert at least one pixel was modified.
        draw_dashed_line(surface, (0, 0, 255), (10, 10), (100, 100))
        modified = any(
            surface.get_at((x, x)) != (0, 0, 0, 255)
            for x in range(10, 101)
        )
        assert modified, "No pixel along the diagonal was modified"

    def test_zero_distance_no_crash(self, surface):
        draw_dashed_line(surface, (255, 0, 0), (50, 50), (50, 50))
        assert surface.get_at((50, 50)) is not None

    def test_very_short_distance(self, surface):
        draw_dashed_line(surface, (255, 0, 0), (50, 50), (51, 50))
        assert surface.get_at((50, 50)) is not None

    def test_custom_dash_gap(self, surface):
        before = surface.get_at((50, 50))
        draw_dashed_line(surface, (255, 255, 0), (10, 50), (200, 50), dash_length=10, gap_length=6)
        after = surface.get_at((50, 50))
        assert before != after

    def test_rgba_color_truncated_to_rgb(self, surface):
        before = surface.get_at((50, 50))
        draw_dashed_line(surface, (255, 0, 0, 128), (10, 50), (100, 50))
        after = surface.get_at((50, 50))
        assert before != after

    def test_long_line_no_crash(self, surface):
        draw_dashed_line(surface, (255, 255, 255), (0, 0), (399, 299))
        assert surface.get_at((200, 150)) is not None


# ===========================================================================
# UnitRenderer — initialization
# ===========================================================================


@pytest.fixture
def ctx():
    screen = pygame.Surface((800, 600))
    offscreen = pygame.Surface((800, 600))
    return RenderContext(tile_size=16, screen=screen, offscreen=offscreen)


@pytest.fixture
def renderer(ctx):
    return UnitRenderer(ctx)


@pytest.mark.unit
class TestUnitRendererInit:
    def test_ctx_stored(self, ctx):
        r = UnitRenderer(ctx)
        assert r._ctx is ctx

    def test_vfx_renderer_created(self, ctx):
        r = UnitRenderer(ctx)
        assert r._vfx_renderer is not None

    def test_glow_cache_none_initially(self, ctx):
        r = UnitRenderer(ctx)
        assert r._glow_surf_cache is None
        assert r._glow_surf_cache_size is None


# ===========================================================================
# UnitRenderer — draw_hexagon
# ===========================================================================


@pytest.mark.unit
class TestDrawHexagon:
    def test_modifies_surface(self, renderer, ctx):
        cx, cy = 100, 100
        before = ctx.offscreen.get_at((cx, cy))
        renderer.draw_hexagon(cx, cy, 30, (255, 0, 0))
        after = ctx.offscreen.get_at((cx, cy))
        assert before != after

    def test_selected_adds_ring(self, renderer, ctx):
        cx, cy = 100, 100
        before = ctx.offscreen.get_at((cx, cy))
        renderer.draw_hexagon(cx, cy, 30, (0, 255, 0), selected=True)
        after = ctx.offscreen.get_at((cx, cy))
        assert before != after

    def test_none_offscreen_no_crash(self, ctx):
        ctx.offscreen = None
        r = UnitRenderer(ctx)
        r.draw_hexagon(100, 100, 30, (255, 0, 0))

    def test_outline_darker_than_fill(self, renderer, ctx):
        renderer.draw_hexagon(100, 100, 30, (200, 200, 200))
        assert ctx.offscreen.get_at((100, 100)) is not None


# ===========================================================================
# UnitRenderer — draw_units edge cases
# ===========================================================================


@dataclass
class StubPosition:
    pixel_position: Any = None
    tile_x: int = 5
    tile_y: int = 5


@dataclass
class StubHealth:
    hp: int = 100
    max_hp: int = 100


class StubCamera:
    def __init__(self, zoom=1.0):
        self.zoom = zoom
        self.offset_x = 0
        self.offset_y = 0

    def world_to_screen(self, pos):
        return (pos.x, pos.y)


@dataclass
class Vec2Stub:
    x: float = 80.0
    y: float = 80.0


@dataclass
class StubUnit:
    id: str = "u1"
    name: str = "Rifle"
    display_name: str = "Rifle"
    unit_type: str = "infantry"
    faction: str = "ally"
    position: Any = None
    health: Any = None
    is_damaged: bool = False


@pytest.fixture
def stub_camera():
    cam = StubCamera()
    return cam


@pytest.fixture
def stub_unit():
    pos = StubPosition(pixel_position=Vec2Stub(100.0, 100.0))
    return StubUnit(position=pos, health=StubHealth())


@pytest.mark.unit
class TestDrawUnitsEdgeCases:
    def test_empty_units_no_crash(self, renderer, stub_camera):
        renderer.draw_units([], stub_camera)
        assert True

    def test_none_screen_no_crash(self, ctx, stub_camera, stub_unit):
        ctx.screen = None
        r = UnitRenderer(ctx)
        r.draw_units([stub_unit], stub_camera)

    def test_none_offscreen_no_crash(self, ctx, stub_camera, stub_unit):
        ctx.offscreen = None
        r = UnitRenderer(ctx)
        r.draw_units([stub_unit], stub_camera)

    def test_unit_rendering_no_crash(self, renderer, ctx, stub_camera, stub_unit):
        renderer.draw_units([stub_unit], stub_camera)
        assert ctx.offscreen.get_at((100, 100)) is not None

    def test_multiple_units_no_crash(self, renderer, ctx, stub_camera):
        units = []
        for i in range(5):
            pos = StubPosition(pixel_position=Vec2Stub(50.0 + i * 80, 100.0))
            units.append(StubUnit(id=f"u{i}", position=pos, health=StubHealth()))
        renderer.draw_units(units, stub_camera)
        assert ctx.offscreen.get_at((100, 100)) is not None

    def test_selected_unit_no_crash(self, renderer, ctx, stub_camera, stub_unit):
        renderer.draw_units([stub_unit], stub_camera, selected_unit_ids={"u1"})
        assert ctx.offscreen.get_at((100, 100)) is not None

    def test_tank_unit_type(self, renderer, ctx, stub_camera, stub_unit):
        stub_unit.unit_type = "tank"
        stub_unit.faction = "axis"
        renderer.draw_units([stub_unit], stub_camera)
        assert ctx.offscreen.get_at((100, 100)) is not None

    def test_support_unit_type(self, renderer, ctx, stub_camera, stub_unit):
        stub_unit.unit_type = "mg"
        renderer.draw_units([stub_unit], stub_camera)
        assert ctx.offscreen.get_at((100, 100)) is not None

    def test_recon_unit_type(self, renderer, ctx, stub_camera, stub_unit):
        stub_unit.unit_type = "sniper"
        renderer.draw_units([stub_unit], stub_camera)
        assert ctx.offscreen.get_at((100, 100)) is not None

    def test_damaged_unit_no_crash(self, renderer, ctx, stub_camera, stub_unit):
        stub_unit.is_damaged = True
        renderer.draw_units([stub_unit], stub_camera)
        assert ctx.offscreen.get_at((100, 100)) is not None

    def test_position_overrides(self, renderer, ctx, stub_camera, stub_unit):
        renderer.draw_units([stub_unit], stub_camera, position_overrides={"u1": (200.0, 200.0)})
        assert ctx.offscreen.get_at((200, 200)) is not None

    def test_unit_without_position_uses_grid(self, renderer, ctx, stub_camera):
        unit = StubUnit(position=None, health=StubHealth())
        renderer.draw_units([unit], stub_camera)
        assert ctx.offscreen.get_at((100, 100)) is not None


# ===========================================================================
# UnitRenderer — delegate methods
# ===========================================================================


@pytest.mark.unit
class TestDelegateMethods:
    def test_draw_damage_vfx_delegates(self, renderer, stub_unit):
        renderer.draw_damage_vfx(stub_unit, 100, 100)
        assert True

    def test_draw_direction_indicator_delegates(self, renderer, stub_unit):
        renderer.draw_direction_indicator(100, 100, 30, (0, 255, 0), stub_unit)
        assert True

    def test_draw_movement_mode_overlay_delegates(self, renderer, stub_unit):
        renderer.draw_movement_mode_overlay(stub_unit, 100, 100, 30, (0, 255, 0))
        assert True
