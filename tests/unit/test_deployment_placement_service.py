"""Tests for DeploymentPlacementService — unit placement and removal logic.

Uses a lightweight FakeDeploymentUI stub providing the state and helper
methods the service accesses. Mirrors the StubDeploymentUI pattern from
test_deployment_manager.py.
"""

from __future__ import annotations

import pytest

from pycc2.presentation.ui.deployment_models import (
    TERRAIN_BUILDING_SOLID,
    TERRAIN_OPEN,
    TERRAIN_ROAD,
    TERRAIN_WATER,
    DeploymentPhase,
    DeploymentState,
    DeploymentUnit,
    ZoneType,
)
from pycc2.presentation.ui.deployment_placement import DeploymentPlacementService


class FakeDeploymentUI:
    """Minimal stub providing the attributes DeploymentPlacementService accesses."""

    def __init__(self):
        self._state = DeploymentState()
        self._state.phase = DeploymentPhase.DEPLOYING
        self._state.requisition_points = 20
        self._state.requisition_points_spent = 0
        self._state.max_infantry = 5
        self._state.max_support = 3
        self._map_width = 20
        self._map_height = 20
        self._zone_map = None
        self._selected_unit_index = None
        self._terrain_at = TERRAIN_OPEN

    @property
    def requisition_remaining(self):
        return self._state.requisition_points - self._state.requisition_points_spent

    def _get_terrain_at(self, x, y):
        return self._terrain_at


def _make_unit(unit_type="infantry", cost=1, is_placed=False, position=None):
    return DeploymentUnit(
        unit_template_id=f"unit_{unit_type}",
        display_name=f"Test {unit_type}",
        unit_type=unit_type,
        deployment_cost=cost,
        position=position,
        is_placed=is_placed,
    )


def _make_zone_map(width=20, height=20, friendly=True):
    zone = ZoneType.FRIENDLY if friendly else ZoneType.ENEMY_CONTROLLED
    return [[zone for _ in range(width)] for _ in range(height)]


@pytest.fixture
def ui():
    ui = FakeDeploymentUI()
    ui._zone_map = _make_zone_map()
    return ui


@pytest.fixture
def service(ui):
    return DeploymentPlacementService(ui)


class TestPlaceUnit:
    def test_successful_placement(self, service, ui):
        unit = _make_unit()
        ui._state.available_units = [unit]
        assert service.place_unit(0, 5, 5) is True
        assert unit.is_placed is True
        assert unit.position == (5, 5)
        assert unit in ui._state.placed_units
        assert ui._state.requisition_points_spent == 1

    def test_wrong_phase(self, service, ui):
        ui._state.phase = DeploymentPhase.PLANNING
        ui._state.available_units = [_make_unit()]
        assert service.place_unit(0, 5, 5) is False

    def test_invalid_index_negative(self, service, ui):
        assert service.place_unit(-1, 5, 5) is False

    def test_invalid_index_out_of_bounds(self, service, ui):
        assert service.place_unit(99, 5, 5) is False

    def test_already_placed(self, service, ui):
        unit = _make_unit(is_placed=True, position=(3, 3))
        ui._state.available_units = [unit]
        assert service.place_unit(0, 5, 5) is False

    def test_insufficient_requisition(self, service, ui):
        unit = _make_unit(cost=100)
        ui._state.available_units = [unit]
        assert service.place_unit(0, 5, 5) is False

    def test_not_in_friendly_zone(self, service, ui):
        ui._zone_map = _make_zone_map(friendly=False)
        ui._state.available_units = [_make_unit()]
        assert service.place_unit(0, 5, 5) is False

    def test_water_terrain_blocked(self, service, ui):
        ui._terrain_at = TERRAIN_WATER
        ui._state.available_units = [_make_unit()]
        assert service.place_unit(0, 5, 5) is False

    def test_solid_building_blocked(self, service, ui):
        ui._terrain_at = TERRAIN_BUILDING_SOLID
        ui._state.available_units = [_make_unit()]
        assert service.place_unit(0, 5, 5) is False

    def test_road_terrain_allowed(self, service, ui):
        ui._terrain_at = TERRAIN_ROAD
        ui._state.available_units = [_make_unit()]
        assert service.place_unit(0, 5, 5) is True

    def test_tile_occupied(self, service, ui):
        existing = _make_unit(is_placed=True, position=(5, 5))
        ui._state.placed_units = [existing]
        ui._state.available_units = [_make_unit()]
        assert service.place_unit(0, 5, 5) is False

    def test_auto_transition_to_ready(self, service, ui):
        ui._state.phase = DeploymentPhase.DEPLOYING
        ui._state.available_units = [_make_unit()]
        service.place_unit(0, 5, 5)
        assert ui._state.phase == DeploymentPhase.READY

    def test_infantry_limit(self, service, ui):
        ui._state.max_infantry = 1
        ui._state.placed_units = [
            _make_unit(unit_type="infantry", is_placed=True, position=(1, 1))
        ]
        ui._state.available_units = [_make_unit(unit_type="infantry")]
        assert service.place_unit(0, 5, 5) is False

    def test_support_limit(self, service, ui):
        ui._state.max_support = 1
        ui._state.placed_units = [
            _make_unit(unit_type="support", is_placed=True, position=(1, 1))
        ]
        ui._state.available_units = [_make_unit(unit_type="support")]
        assert service.place_unit(0, 5, 5) is False

    def test_clears_selection(self, service, ui):
        ui._selected_unit_index = 0
        ui._state.available_units = [_make_unit()]
        service.place_unit(0, 5, 5)
        assert ui._selected_unit_index is None


class TestRemoveUnit:
    def test_successful_removal(self, service, ui):
        unit = _make_unit(is_placed=True, position=(5, 5))
        ui._state.placed_units = [unit]
        ui._state.requisition_points_spent = 1
        assert service.remove_unit(5, 5) is True
        assert unit.is_placed is False
        assert unit.position is None
        assert unit not in ui._state.placed_units
        assert ui._state.requisition_points_spent == 0

    def test_not_found(self, service, ui):
        assert service.remove_unit(10, 10) is False

    def test_reverts_phase_to_deploying(self, service, ui):
        unit = _make_unit(is_placed=True, position=(5, 5))
        ui._state.placed_units = [unit]
        ui._state.phase = DeploymentPhase.READY
        service.remove_unit(5, 5)
        assert ui._state.phase == DeploymentPhase.DEPLOYING

    def test_keeps_phase_if_units_remain(self, service, ui):
        u1 = _make_unit(is_placed=True, position=(5, 5))
        u2 = _make_unit(is_placed=True, position=(6, 6))
        ui._state.placed_units = [u1, u2]
        ui._state.phase = DeploymentPhase.READY
        service.remove_unit(5, 5)
        assert ui._state.phase == DeploymentPhase.READY


class TestCanPlaceAt:
    def test_open_terrain_friendly_zone(self, service, ui):
        unit = _make_unit()
        assert service.can_place_at(unit, 5, 5, TERRAIN_OPEN) is True

    def test_water_blocked(self, service, ui):
        unit = _make_unit()
        assert service.can_place_at(unit, 5, 5, TERRAIN_WATER) is False

    def test_solid_building_blocked(self, service, ui):
        unit = _make_unit()
        assert service.can_place_at(unit, 5, 5, TERRAIN_BUILDING_SOLID) is False

    def test_not_in_friendly_zone(self, service, ui):
        ui._zone_map = _make_zone_map(friendly=False)
        unit = _make_unit()
        assert service.can_place_at(unit, 5, 5, TERRAIN_OPEN) is False

    def test_road_allowed(self, service, ui):
        unit = _make_unit()
        assert service.can_place_at(unit, 5, 5, TERRAIN_ROAD) is True


class TestIsInFriendlyZone:
    def test_in_zone(self, service, ui):
        assert service._is_in_friendly_zone(5, 5) is True

    def test_out_of_bounds_x(self, service, ui):
        assert service._is_in_friendly_zone(-1, 5) is False
        assert service._is_in_friendly_zone(20, 5) is False

    def test_out_of_bounds_y(self, service, ui):
        assert service._is_in_friendly_zone(5, -1) is False
        assert service._is_in_friendly_zone(5, 20) is False

    def test_no_zone_map(self, service, ui):
        ui._zone_map = None
        assert service._is_in_friendly_zone(5, 5) is False


class TestCheckUnitLimits:
    def test_infantry_under_limit(self, service, ui):
        unit = _make_unit(unit_type="infantry")
        assert service._check_unit_limits(unit) is True

    def test_infantry_at_limit(self, service, ui):
        ui._state.max_infantry = 1
        ui._state.placed_units = [
            _make_unit(unit_type="infantry", is_placed=True, position=(1, 1))
        ]
        unit = _make_unit(unit_type="infantry")
        assert service._check_unit_limits(unit) is False

    def test_support_under_limit(self, service, ui):
        unit = _make_unit(unit_type="support")
        assert service._check_unit_limits(unit) is True

    def test_support_at_limit(self, service, ui):
        ui._state.max_support = 1
        ui._state.placed_units = [
            _make_unit(unit_type="support", is_placed=True, position=(1, 1))
        ]
        unit = _make_unit(unit_type="support")
        assert service._check_unit_limits(unit) is False

    def test_vehicle_counts_as_support(self, service, ui):
        ui._state.max_support = 1
        ui._state.placed_units = [
            _make_unit(unit_type="vehicle", is_placed=True, position=(1, 1))
        ]
        unit = _make_unit(unit_type="support")
        assert service._check_unit_limits(unit) is False

    def test_recon_counts_as_infantry(self, service, ui):
        ui._state.max_infantry = 1
        ui._state.placed_units = [
            _make_unit(unit_type="recon", is_placed=True, position=(1, 1))
        ]
        unit = _make_unit(unit_type="recon")
        assert service._check_unit_limits(unit) is False

    def test_unknown_type_returns_false(self, service, ui):
        unit = _make_unit(unit_type="unknown")
        assert service._check_unit_limits(unit) is False
