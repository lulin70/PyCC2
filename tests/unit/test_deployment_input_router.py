"""Tests for DeploymentInputRouter — click handling and input routing.

Uses a lightweight FakeDeploymentUI stub to avoid pygame/display dependencies
while testing the router's logic. Mirrors the StubDeploymentUI pattern from
test_deployment_manager.py.
"""

from __future__ import annotations

import pytest

from pycc2.presentation.ui.deployment_input_router import DeploymentInputRouter
from pycc2.presentation.ui.deployment_models import (
    DeploymentPhase,
    DeploymentState,
    DeploymentUnit,
)


class FakeDeploymentUI:
    """Minimal stub providing the attributes DeploymentInputRouter accesses."""

    def __init__(self):
        self._state = DeploymentState()
        self._state.phase = DeploymentPhase.DEPLOYING
        self._button_rect = None
        self._roster_width = 200
        self._roster_padding = 8
        self._roster_item_height = 30
        self._roster_category_height = 24
        self._roster_layout: list = []
        self._selected_unit_index = None
        self._detail_panel_btn_rect = None
        self._detail_panel_btn_action = None
        self._is_deployment_complete = False
        self._place_unit_result = True
        self._remove_unit_result = True
        self._screen_to_map_result = (5, 5)
        self._handle_right_click_result = None
        self.place_unit_calls: list = []
        self.remove_unit_calls: list = []
        self.right_click_calls: list = []

    def is_deployment_complete(self):
        return self._is_deployment_complete

    def place_unit(self, idx, mx, my):
        self.place_unit_calls.append((idx, mx, my))
        return self._place_unit_result

    def remove_unit(self, mx, my):
        self.remove_unit_calls.append((mx, my))
        return self._remove_unit_result

    def screen_to_map(self, sx, sy, ox=0, oy=0, ts=16):
        return self._screen_to_map_result

    def handle_right_click(self, sx, sy, ox=0, oy=0, ts=16):
        self.right_click_calls.append((sx, sy, ox, oy, ts))
        return self._handle_right_click_result


def _make_unit(unit_type="infantry", is_placed=False, position=None):
    return DeploymentUnit(
        unit_template_id=f"unit_{unit_type}",
        display_name=f"Test {unit_type}",
        unit_type=unit_type,
        deployment_cost=1,
        position=position,
        is_placed=is_placed,
    )


@pytest.fixture
def ui():
    return FakeDeploymentUI()


@pytest.fixture
def router(ui):
    return DeploymentInputRouter(ui)


class TestHandleClick:
    def test_wrong_phase_returns_none(self, router, ui):
        ui._state.phase = DeploymentPhase.PLANNING
        assert router.handle_click(10, 10) is None

    def test_button_click_deployment_complete(self, router, ui):
        ui._button_rect = (100, 100, 80, 30)
        ui._is_deployment_complete = True
        assert router.handle_click(120, 115) == "begin_battle"

    def test_button_click_not_complete(self, router, ui):
        ui._button_rect = (100, 100, 80, 30)
        ui._is_deployment_complete = False
        assert router.handle_click(120, 115) is None

    def test_roster_click_selects_unit(self, router, ui):
        ui._state.available_units = [_make_unit()]
        ui._roster_layout = [("unit", 0)]
        result = router.handle_click(50, 40)
        assert result == "select_unit:0"
        assert ui._selected_unit_index == 0

    def test_roster_click_placed_unit_not_selected(self, router, ui):
        ui._state.available_units = [_make_unit(is_placed=True)]
        ui._roster_layout = [("unit", 0)]
        result = router.handle_click(50, 40)
        assert result is None

    def test_roster_click_out_of_padding(self, router, ui):
        ui._roster_width = 200
        ui._roster_padding = 8
        result = router.handle_click(5, 40)
        assert result is None

    def test_roster_click_category_header(self, router, ui):
        ui._roster_layout = [("category", "INFANTRY")]
        result = router.handle_click(50, 40)
        assert result is None

    def test_map_click_returns_none(self, router, ui):
        result = router.handle_click(300, 100)
        assert result is None


class TestHandleClickFull:
    def test_wrong_phase_returns_none(self, router, ui):
        ui._state.phase = DeploymentPhase.PLANNING
        assert router.handle_click_full(10, 10) is None

    def test_right_click_delegates(self, router, ui):
        ui._handle_right_click_result = "remove_unit:5,5"
        result = router.handle_click_full(300, 200, right_click=True)
        assert result == "remove_unit:5,5"
        assert len(ui.right_click_calls) == 1

    def test_button_click_complete(self, router, ui):
        ui._button_rect = (100, 100, 80, 30)
        ui._is_deployment_complete = True
        assert router.handle_click_full(120, 115) == "begin_battle"

    def test_button_click_not_complete(self, router, ui):
        ui._button_rect = (100, 100, 80, 30)
        ui._is_deployment_complete = False
        assert router.handle_click_full(120, 115) is None

    def test_detail_panel_remove(self, router, ui):
        ui._detail_panel_btn_rect = (100, 100, 80, 30)
        ui._detail_panel_btn_action = "remove"
        ui._selected_unit_index = 0
        unit = _make_unit(is_placed=True, position=(3, 4))
        ui._state.available_units = [unit]
        result = router.handle_click_full(120, 115)
        assert result == "detail_panel_remove:3,4"
        assert len(ui.remove_unit_calls) == 1

    def test_detail_panel_place(self, router, ui):
        ui._detail_panel_btn_rect = (100, 100, 80, 30)
        ui._detail_panel_btn_action = "place"
        ui._selected_unit_index = 0
        ui._state.available_units = [_make_unit()]
        result = router.handle_click_full(120, 115)
        assert result == "detail_panel_place_requested"

    def test_roster_click_selects_unplaced(self, router, ui):
        ui._state.available_units = [_make_unit()]
        ui._roster_layout = [("unit", 0)]
        result = router.handle_click_full(50, 40)
        assert result == "select_unit:0"

    def test_roster_click_views_placed(self, router, ui):
        ui._state.available_units = [_make_unit(is_placed=True)]
        ui._roster_layout = [("unit", 0)]
        result = router.handle_click_full(50, 40)
        assert result == "view_placed_unit:0"

    def test_map_click_place_unit(self, router, ui):
        ui._selected_unit_index = 0
        ui._state.available_units = [_make_unit()]
        ui._screen_to_map_result = (5, 5)
        ui._place_unit_result = True
        result = router.handle_click_full(300, 200)
        assert result == "place_unit:0"

    def test_map_click_place_fails(self, router, ui):
        ui._selected_unit_index = 0
        ui._state.available_units = [_make_unit()]
        ui._screen_to_map_result = (5, 5)
        ui._place_unit_result = False
        result = router.handle_click_full(300, 200)
        assert result is None

    def test_map_click_remove_unit(self, router, ui):
        ui._selected_unit_index = None
        ui._screen_to_map_result = (3, 4)
        ui._remove_unit_result = True
        result = router.handle_click_full(300, 200)
        assert result == "remove_unit:3,4"

    def test_map_click_remove_fails(self, router, ui):
        ui._selected_unit_index = None
        ui._screen_to_map_result = (3, 4)
        ui._remove_unit_result = False
        result = router.handle_click_full(300, 200)
        assert result is None

    def test_map_click_screen_to_map_none(self, router, ui):
        ui._selected_unit_index = 0
        ui._screen_to_map_result = None
        result = router.handle_click_full(300, 200)
        assert result is None

    def test_no_button_rect(self, router, ui):
        ui._button_rect = None
        ui._is_deployment_complete = True
        result = router.handle_click_full(120, 115)
        # Should fall through to roster/map checks
        assert result is None


class TestRosterIndexAt:
    def test_returns_unit_index(self, router, ui):
        ui._roster_layout = [("category", "INF"), ("unit", 0)]
        idx = router._roster_index_at(50, 65)
        assert idx == 0

    def test_returns_none_for_category(self, router, ui):
        ui._roster_layout = [("category", "INF")]
        idx = router._roster_index_at(50, 40)
        assert idx is None

    def test_returns_none_out_of_bounds(self, router, ui):
        ui._roster_padding = 8
        ui._roster_width = 200
        idx = router._roster_index_at(5, 40)
        assert idx is None

    def test_returns_none_empty_layout(self, router, ui):
        ui._roster_layout = []
        idx = router._roster_index_at(50, 40)
        assert idx is None

    def test_returns_second_unit(self, router, ui):
        ui._roster_layout = [
            ("category", "INF"),
            ("unit", 0),
            ("unit", 1),
        ]
        # category: y_offset 36..62; unit 0: 62..94; unit 1: 94..126 → click at 110
        idx = router._roster_index_at(50, 110)
        assert idx == 1


class TestIsInButton:
    def test_inside_button(self, router, ui):
        ui._button_rect = (100, 100, 80, 30)
        assert router._is_in_button(120, 115) is True

    def test_outside_button(self, router, ui):
        ui._button_rect = (100, 100, 80, 30)
        assert router._is_in_button(50, 50) is False

    def test_no_button(self, router, ui):
        ui._button_rect = None
        assert router._is_in_button(50, 50) is False
