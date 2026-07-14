"""Tests for DeploymentDragMixin — drag interaction and visual feedback.

Uses a lightweight FakeDeploymentUI stub and a minimal facade that inherits
the mixin, mirroring the StubDeploymentUI pattern from test_deployment_manager.py.
"""

from __future__ import annotations

import pygame
import pytest
from pygame import Surface

from pycc2.presentation.ui.deployment_drag_mixin import DeploymentDragMixin
from pycc2.presentation.ui.deployment_models import (
    DeploymentPhase,
    DeploymentState,
    DeploymentUnit,
)


class FakeDeploymentUI:
    """Minimal stub providing the attributes DeploymentDragMixin accesses."""

    def __init__(self):
        self._state = DeploymentState()
        self._state.phase = DeploymentPhase.DEPLOYING
        self._state.requisition_points = 20
        self._state.requisition_points_spent = 0
        self._roster_width = 200
        self._roster_index_result = 0
        self._selected_unit_index = None
        self._is_dragging = False
        self._dragging_unit = None
        self._dragging_unit_index = None
        self._drag_start_pos = None
        self._drag_current_pos = None
        self._ghost_surface = None
        self._highlight_surface_cache: dict = {}
        self._font_normal = None
        self._font_small = None
        self._font_large = None
        self._screen_to_map_result = (5, 5)
        self._terrain_at = 0
        self._place_unit_result = True
        self._ghost_surface_result = Surface((32, 32))
        self.place_unit_calls: list = []

    @property
    def requisition_remaining(self):
        return self._state.requisition_points - self._state.requisition_points_spent

    def _roster_index_at(self, x, y):
        return self._roster_index_result

    def screen_to_map(self, sx, sy, ox=0, oy=0, ts=16):
        return self._screen_to_map_result

    def _get_terrain_at(self, x, y):
        return self._terrain_at

    def can_place_at(self, unit, x, y, terrain):
        return terrain not in (5, 6)

    def place_unit(self, idx, x, y):
        self.place_unit_calls.append((idx, x, y))
        return self._place_unit_result

    def _create_ghost_surface(self, unit):
        return self._ghost_surface_result

    def _clear_drag_state(self):
        self._is_dragging = False
        self._dragging_unit = None
        self._dragging_unit_index = None
        self._drag_start_pos = None
        self._drag_current_pos = None
        self._ghost_surface = None


class FakeCamera:
    def __init__(self, offset_x=0, offset_y=0):
        self.offset_x = offset_x
        self.offset_y = offset_y


class FakeGameMap:
    def __init__(self, width=20, height=20):
        self.width = width
        self.height = height


class DragFacade(DeploymentDragMixin):
    """Minimal facade inheriting the mixin for testing."""

    def __init__(self, ui):
        self._ui = ui


def _make_unit(unit_type="infantry"):
    return DeploymentUnit(
        unit_template_id=f"unit_{unit_type}",
        display_name=f"Test {unit_type}",
        unit_type=unit_type,
        deployment_cost=1,
    )


@pytest.fixture
def ui(pygame_display):
    ui = FakeDeploymentUI()
    ui._state.available_units = [_make_unit()]
    return ui


@pytest.fixture
def facade(ui):
    return DragFacade(ui)


@pytest.fixture
def surface():
    return Surface((800, 600))


class TestHandleDeploymentDrag:
    def test_wrong_phase_ignores(self, facade, ui):
        ui._state.phase = DeploymentPhase.PLANNING
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (50, 40)})
        facade.handle_deployment_drag(event, FakeCamera(), FakeGameMap())
        assert ui._is_dragging is False

    def test_mouse_down_starts_drag(self, facade, ui):
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (50, 40)})
        facade.handle_deployment_drag(event, FakeCamera(), FakeGameMap())
        assert ui._is_dragging is True
        assert ui._dragging_unit is not None
        assert ui._selected_unit_index == 0

    def test_mouse_down_placed_unit_no_drag(self, facade, ui):
        ui._state.available_units[0].is_placed = True
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (50, 40)})
        facade.handle_deployment_drag(event, FakeCamera(), FakeGameMap())
        assert ui._is_dragging is False

    def test_mouse_motion_updates_pos(self, facade, ui):
        down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (50, 40)})
        facade.handle_deployment_drag(down, FakeCamera(), FakeGameMap())
        motion = pygame.event.Event(pygame.MOUSEMOTION, {"pos": (100, 80)})
        facade.handle_deployment_drag(motion, FakeCamera(), FakeGameMap())
        assert ui._drag_current_pos == (100, 80)

    def test_mouse_up_places_unit(self, facade, ui):
        down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (50, 40)})
        facade.handle_deployment_drag(down, FakeCamera(), FakeGameMap())
        up = pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": 1, "pos": (300, 200)})
        facade.handle_deployment_drag(up, FakeCamera(), FakeGameMap(), tile_size=48)
        assert len(ui.place_unit_calls) == 1
        assert ui._is_dragging is False

    def test_mouse_up_invalid_placement(self, facade, ui):
        ui._terrain_at = 6
        down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (50, 40)})
        facade.handle_deployment_drag(down, FakeCamera(), FakeGameMap())
        up = pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": 1, "pos": (300, 200)})
        facade.handle_deployment_drag(up, FakeCamera(), FakeGameMap(), tile_size=48)
        assert len(ui.place_unit_calls) == 0
        assert ui._is_dragging is False

    def test_right_click_ignored(self, facade, ui):
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 3, "pos": (50, 40)})
        facade.handle_deployment_drag(event, FakeCamera(), FakeGameMap())
        assert ui._is_dragging is False

    def test_motion_without_drag_ignored(self, facade, ui):
        motion = pygame.event.Event(pygame.MOUSEMOTION, {"pos": (100, 80)})
        facade.handle_deployment_drag(motion, FakeCamera(), FakeGameMap())
        assert ui._is_dragging is False


class TestRenderDragFeedback:
    def test_not_dragging_no_render(self, facade, ui, surface):
        facade._render_drag_feedback(surface)

    def test_dragging_renders_feedback(self, facade, ui, surface):
        ui._is_dragging = True
        ui._drag_current_pos = (300, 200)
        ui._dragging_unit = _make_unit()
        ui._ghost_surface = Surface((32, 32))
        facade._render_drag_feedback(surface, tile_size=16)

    def test_dragging_no_ghost_surface(self, facade, ui, surface):
        ui._is_dragging = True
        ui._drag_current_pos = (300, 200)
        ui._dragging_unit = _make_unit()
        ui._ghost_surface = None
        facade._render_drag_feedback(surface, tile_size=16)

    def test_dragging_in_roster_area(self, facade, ui, surface):
        ui._is_dragging = True
        ui._drag_current_pos = (50, 40)
        ui._dragging_unit = _make_unit()
        ui._ghost_surface = Surface((32, 32))
        facade._render_drag_feedback(surface, tile_size=16)

    def test_dragging_null_current_pos(self, facade, ui, surface):
        ui._is_dragging = True
        ui._drag_current_pos = None
        facade._render_drag_feedback(surface, tile_size=16)


class TestEnsureFonts:
    def test_with_font_param(self, facade, ui):
        font = pygame.font.Font(None, 20)
        ui._font_normal = None
        ui._font_small = None
        ui._font_large = None
        facade._ensure_fonts(font)
        assert ui._font_normal is font

    def test_without_font_param(self, facade, ui):
        ui._font_normal = None
        ui._font_small = None
        ui._font_large = None
        facade._ensure_fonts(None)
        assert ui._font_normal is not None
        assert ui._font_small is not None
        assert ui._font_large is not None

    def test_existing_fonts_preserved(self, facade, ui):
        existing = pygame.font.Font(None, 20)
        ui._font_normal = existing
        facade._ensure_fonts(None)
        assert ui._font_normal is existing

    def test_small_and_large_created_if_none(self, facade, ui):
        font = pygame.font.Font(None, 20)
        ui._font_normal = None
        ui._font_small = None
        ui._font_large = None
        facade._ensure_fonts(font)
        assert ui._font_small is not None
        assert ui._font_large is not None
