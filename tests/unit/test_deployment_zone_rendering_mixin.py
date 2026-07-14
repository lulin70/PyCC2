"""Tests for DeploymentZoneRenderingMixin — zone overlay rendering.

Uses a lightweight FakeDeploymentUI stub and a minimal facade that inherits
the mixin, mirroring the StubDeploymentUI pattern from test_deployment_manager.py.
"""

from __future__ import annotations

import pygame
import pytest
from pygame import Surface

from pycc2.presentation.ui.deployment_models import (
    DeploymentPhase,
    DeploymentState,
    DeploymentUnit,
    ZoneType,
)
from pycc2.presentation.ui.deployment_zone_rendering_mixin import (
    DeploymentZoneRenderingMixin,
)


class FakeLOS:
    """Minimal LOS system stub."""

    def __init__(self):
        self.render_calls: list = []

    def render_los_preview(self, screen, ox, oy, ts):
        self.render_calls.append((screen, ox, oy, ts))


class FakeDeploymentUI:
    """Minimal stub providing the attributes DeploymentZoneRenderingMixin accesses."""

    def __init__(self):
        self._state = DeploymentState()
        self._state.phase = DeploymentPhase.DEPLOYING
        self._state.requisition_points = 20
        self._state.requisition_points_spent = 0
        self._map_width = 10
        self._map_height = 10
        self._zone_map = None
        self._overlay_cache = None
        self._overlay_tile_size = 0
        self._selected_unit_index = None
        self._terrain_at = 0
        self._font_small = None
        self._pending_orders: dict = {}
        self._los_system = FakeLOS()

    @property
    def requisition_remaining(self):
        return self._state.requisition_points - self._state.requisition_points_spent

    def _get_terrain_at(self, x, y):
        return self._terrain_at

    def _get_zone_at(self, x, y):
        if self._zone_map is not None and 0 <= x < self._map_width and 0 <= y < self._map_height:
            return self._zone_map[y][x]
        return ZoneType.FRIENDLY

    def can_place_at(self, unit, x, y, terrain):
        return terrain not in (5, 6)


class FakeCamera:
    def __init__(self, offset_x=0, offset_y=0):
        self.offset_x = offset_x
        self.offset_y = offset_y


class FakeGameMap:
    def __init__(self, width=10, height=10):
        self.width = width
        self.height = height


class ZoneFacade(DeploymentZoneRenderingMixin):
    """Minimal facade for testing the zone rendering mixin."""

    def __init__(self, ui):
        self._ui = ui
        self._zone_overlay_cache = None
        self._zone_overlay_cache_size = None
        self._highlight_surf_cache = None
        self._highlight_surf_cache_size = None

    def _draw_dashed_line(self, surface, color, start, end, dash_length=6, gap_length=4):
        pygame.draw.line(surface, color[:3], start, end, 1)

    def _draw_arrowhead(self, surface, color, start, end, size=8):
        pygame.draw.circle(surface, color, end, size)


def _make_unit(unit_type="infantry", is_placed=False, position=None, cost=1):
    return DeploymentUnit(
        unit_template_id=f"unit_{unit_type}",
        display_name=f"Test {unit_type}",
        unit_type=unit_type,
        deployment_cost=cost,
        position=position,
        is_placed=is_placed,
    )


@pytest.fixture
def ui(pygame_display):
    ui = FakeDeploymentUI()
    ui._zone_map = [[ZoneType.FRIENDLY for _ in range(10)] for _ in range(10)]
    ui._font_small = pygame.font.Font(None, 16)
    return ui


@pytest.fixture
def facade(ui):
    return ZoneFacade(ui)


@pytest.fixture
def surface():
    return Surface((800, 600))


class TestRenderDeploymentZones:
    def test_wrong_phase_no_render(self, facade, ui, surface):
        ui._state.phase = DeploymentPhase.PLANNING
        facade.render_deployment_zones(surface, FakeCamera(), FakeGameMap())

    def test_renders_friendly_zones(self, facade, ui, surface):
        facade.render_deployment_zones(surface, FakeCamera(), FakeGameMap(), tile_size=16)

    def test_renders_enemy_zones(self, facade, ui, surface):
        ui._zone_map = [[ZoneType.ENEMY_CONTROLLED] * 10 for _ in range(10)]
        facade.render_deployment_zones(surface, FakeCamera(), FakeGameMap(), tile_size=16)

    def test_renders_no_mans_land(self, facade, ui, surface):
        ui._zone_map = [[ZoneType.NO_MANS_LAND] * 10 for _ in range(10)]
        facade.render_deployment_zones(surface, FakeCamera(), FakeGameMap(), tile_size=16)

    def test_with_camera_offset(self, facade, ui, surface):
        facade.render_deployment_zones(
            surface, FakeCamera(offset_x=32, offset_y=32), FakeGameMap(), tile_size=16
        )

    def test_uses_game_map_dimensions(self, facade, ui, surface):
        facade.render_deployment_zones(
            surface, FakeCamera(), FakeGameMap(width=5, height=5), tile_size=16
        )


class TestRenderZoneOverlays:
    def test_no_zone_map(self, facade, ui, surface):
        ui._zone_map = None
        facade._render_zone_overlays(surface, 0, 0, 16)

    def test_renders_overlays(self, facade, ui, surface):
        ui._zone_map = [
            [ZoneType.FRIENDLY, ZoneType.NO_MANS_LAND],
            [ZoneType.ENEMY_CONTROLLED, ZoneType.FRIENDLY],
        ]
        ui._map_width = 2
        ui._map_height = 2
        facade._render_zone_overlays(surface, 0, 0, 16)

    def test_caches_overlay(self, facade, ui, surface):
        ui._zone_map = [[ZoneType.FRIENDLY] * 10 for _ in range(10)]
        facade._render_zone_overlays(surface, 0, 0, 16)
        assert ui._overlay_cache is not None
        facade._render_zone_overlays(surface, 0, 0, 16)

    def test_rebuilds_on_tile_size_change(self, facade, ui, surface):
        ui._zone_map = [[ZoneType.FRIENDLY] * 10 for _ in range(10)]
        facade._render_zone_overlays(surface, 0, 0, 16)
        first_cache = ui._overlay_cache
        facade._render_zone_overlays(surface, 0, 0, 32)
        assert ui._overlay_tile_size == 32
        assert ui._overlay_cache is not first_cache


class TestRenderPlacementHighlights:
    def test_no_selection(self, facade, ui, surface):
        ui._selected_unit_index = None
        facade._render_placement_highlights(surface, 0, 0, 16)

    def test_selected_placed_unit(self, facade, ui, surface):
        ui._state.available_units = [_make_unit(is_placed=True)]
        ui._selected_unit_index = 0
        facade._render_placement_highlights(surface, 0, 0, 16)

    def test_highlights_valid_tiles(self, facade, ui, surface):
        ui._state.available_units = [_make_unit()]
        ui._selected_unit_index = 0
        facade._render_placement_highlights(surface, 0, 0, 16)

    def test_insufficient_rp(self, facade, ui, surface):
        ui._state.available_units = [_make_unit(cost=100)]
        ui._selected_unit_index = 0
        facade._render_placement_highlights(surface, 0, 0, 16)

    def test_index_out_of_bounds(self, facade, ui, surface):
        ui._selected_unit_index = 99
        facade._render_placement_highlights(surface, 0, 0, 16)

    def test_occupied_tile_skipped(self, facade, ui, surface):
        ui._state.available_units = [_make_unit()]
        ui._state.placed_units = [_make_unit(is_placed=True, position=(0, 0))]
        ui._selected_unit_index = 0
        facade._render_placement_highlights(surface, 0, 0, 16)


class TestRenderPlacedUnits:
    def test_no_placed_units(self, facade, ui, surface):
        facade._render_placed_units(surface, 0, 0, 16)

    def test_infantry_marker(self, facade, ui, surface):
        ui._state.placed_units = [_make_unit("infantry", is_placed=True, position=(1, 1))]
        facade._render_placed_units(surface, 0, 0, 16)

    def test_support_marker(self, facade, ui, surface):
        ui._state.placed_units = [_make_unit("support", is_placed=True, position=(1, 1))]
        facade._render_placed_units(surface, 0, 0, 16)

    def test_vehicle_marker(self, facade, ui, surface):
        ui._state.placed_units = [_make_unit("vehicle", is_placed=True, position=(1, 1))]
        facade._render_placed_units(surface, 0, 0, 16)

    def test_recon_marker(self, facade, ui, surface):
        ui._state.placed_units = [_make_unit("recon", is_placed=True, position=(1, 1))]
        facade._render_placed_units(surface, 0, 0, 16)

    def test_unknown_type_marker(self, facade, ui, surface):
        ui._state.placed_units = [_make_unit("unknown", is_placed=True, position=(1, 1))]
        facade._render_placed_units(surface, 0, 0, 16)

    def test_unit_without_position_skipped(self, facade, ui, surface):
        unit = _make_unit(is_placed=True, position=None)
        ui._state.placed_units = [unit]
        facade._render_placed_units(surface, 0, 0, 16)

    def test_large_tile_renders_label(self, facade, ui, surface):
        ui._state.placed_units = [_make_unit("infantry", is_placed=True, position=(1, 1))]
        facade._render_placed_units(surface, 0, 0, 32)


class TestRenderPendingOrders:
    def test_no_orders(self, facade, ui, surface):
        facade._render_pending_orders(surface, 0, 0, 16)

    def test_with_orders(self, facade, ui, surface):
        unit = _make_unit("infantry", is_placed=True, position=(1, 1))
        ui._state.placed_units = [unit]
        ui._pending_orders = {unit.unit_template_id: (3, 3)}
        facade._render_pending_orders(surface, 0, 0, 16)

    def test_order_for_unplaced_unit_skipped(self, facade, ui, surface):
        unit = _make_unit("infantry", is_placed=False, position=None)
        ui._state.placed_units = [unit]
        ui._pending_orders = {unit.unit_template_id: (3, 3)}
        facade._render_pending_orders(surface, 0, 0, 16)

    def test_order_for_unknown_unit_skipped(self, facade, ui, surface):
        unit = _make_unit("infantry", is_placed=True, position=(1, 1))
        ui._state.placed_units = [unit]
        ui._pending_orders = {"nonexistent": (3, 3)}
        facade._render_pending_orders(surface, 0, 0, 16)


class TestRenderLOSPreview:
    def test_delegates_to_los_system(self, facade, ui, surface):
        facade._render_los_preview(surface, 0, 0, 16)
        assert len(ui._los_system.render_calls) == 1
