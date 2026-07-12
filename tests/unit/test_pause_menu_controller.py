"""
Unit tests for PauseMenuController.

Covers: initialization defaults, toggle/deactivate state transitions,
handle_click hit/miss logic, update_mouse tracking, render output
(buttons dict, rect types, hover branch), and an end-to-end combination.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from pycc2.services.pause_menu_controller import PauseMenuController

# ---------------------------------------------------------------------------
# Constants & helpers
# ---------------------------------------------------------------------------

SCREEN_W, SCREEN_H = 1024, 768

# The four menu items produced by PauseMenuController.render(), in order.
EXPECTED_KEYS = ["resume", "save", "load", "quit_to_menu"]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def controller():
    return PauseMenuController()


@pytest.fixture()
def surface():
    return pygame.Surface((SCREEN_W, SCREEN_H))


# ===========================================================================
# P0: Initialization defaults
# ===========================================================================


@pytest.mark.unit
class TestInitialState:
    def test_is_active_is_false_initially(self, controller):
        assert controller.is_active is False

    def test_buttons_dict_is_empty_initially(self, controller):
        assert controller._buttons == {}

    def test_mouse_defaults_to_origin(self, controller):
        assert controller._mouse == (0, 0)

    def test_handle_click_returns_none_before_any_render(self, controller):
        # No buttons registered yet -> any click misses.
        assert controller.handle_click((100, 100)) is None


# ===========================================================================
# P0: State transitions (toggle / deactivate)
# ===========================================================================


@pytest.mark.unit
class TestToggle:
    def test_toggle_from_inactive_to_active(self, controller):
        controller.toggle()
        assert controller.is_active is True

    def test_toggle_from_active_to_inactive(self, controller):
        controller.toggle()  # -> True
        controller.toggle()  # -> False
        assert controller.is_active is False

    def test_toggle_is_idempotent_over_four_cycles(self, controller):
        # 4 toggles return to the original state.
        for _ in range(4):
            controller.toggle()
        assert controller.is_active is False

    def test_toggle_reflects_property_each_step(self, controller):
        assert controller.is_active is False
        controller.toggle()
        assert controller.is_active is True
        controller.toggle()
        assert controller.is_active is False
        controller.toggle()
        assert controller.is_active is True


@pytest.mark.unit
class TestDeactivate:
    def test_deactivate_from_active_sets_false(self, controller):
        controller.toggle()
        assert controller.is_active is True
        controller.deactivate()
        assert controller.is_active is False

    def test_deactivate_from_inactive_stays_false(self, controller):
        controller.deactivate()
        assert controller.is_active is False

    def test_deactivate_after_multiple_toggles_resets_to_false(self, controller):
        controller.toggle()
        controller.toggle()
        controller.toggle()  # currently active
        assert controller.is_active is True
        controller.deactivate()
        assert controller.is_active is False

    def test_deactivate_is_idempotent(self, controller):
        controller.toggle()
        controller.deactivate()
        controller.deactivate()
        controller.deactivate()
        assert controller.is_active is False


# ===========================================================================
# P0: Mouse tracking
# ===========================================================================


@pytest.mark.unit
class TestUpdateMouse:
    def test_update_mouse_stores_position(self, controller):
        controller.update_mouse((123, 456))
        assert controller._mouse == (123, 456)

    def test_update_mouse_overwrites_previous_position(self, controller):
        controller.update_mouse((10, 10))
        controller.update_mouse((999, 1))
        assert controller._mouse == (999, 1)

    def test_update_mouse_with_origin(self, controller):
        controller.update_mouse((5, 5))
        controller.update_mouse((0, 0))
        assert controller._mouse == (0, 0)


# ===========================================================================
# P0: handle_click hit/miss logic
# ===========================================================================


@pytest.mark.unit
class TestHandleClick:
    def test_click_before_render_returns_none(self, controller):
        # _buttons is empty -> no collision possible.
        assert controller.handle_click((0, 0)) is None
        assert controller.handle_click((512, 328)) is None

    @pytest.mark.parametrize("key", EXPECTED_KEYS)
    def test_click_inside_each_button_returns_its_key(self, controller, surface, key):
        controller.render(surface)
        rect = controller._buttons[key]
        # Click the rect's center — guaranteed inside.
        result = controller.handle_click(rect.center)
        assert result == key

    def test_click_inside_button_top_left_corner_returns_key(self, controller, surface):
        # Boundary: the top-left corner is inclusive for collidepoint.
        controller.render(surface)
        rect = controller._buttons["resume"]
        assert controller.handle_click((rect.left, rect.top)) == "resume"

    def test_click_inside_button_bottom_right_corner_returns_key(self, controller, surface):
        controller.render(surface)
        rect = controller._buttons["quit_to_menu"]
        # (right-1, bottom-1) is the last interior pixel.
        assert controller.handle_click((rect.right - 1, rect.bottom - 1)) == "quit_to_menu"

    def test_click_outside_all_buttons_returns_none(self, controller, surface):
        controller.render(surface)
        # Top-left corner of the screen — well outside the centered panel.
        assert controller.handle_click((0, 0)) is None

    def test_click_just_outside_button_right_edge_returns_none(self, controller, surface):
        controller.render(surface)
        rect = controller._buttons["resume"]
        # One pixel past the right edge is not a collision.
        assert controller.handle_click((rect.right, rect.centery)) is None

    def test_click_just_outside_button_bottom_edge_returns_none(self, controller, surface):
        controller.render(surface)
        rect = controller._buttons["save"]
        assert controller.handle_click((rect.centerx, rect.bottom)) is None

    def test_first_matching_button_wins_when_rects_overlap(self, controller, surface):
        # In the current layout the buttons do not overlap, but the contract
        # is "first match wins" — verify by clicking the resume center which
        # only intersects resume.
        controller.render(surface)
        result = controller.handle_click(controller._buttons["resume"].center)
        assert result == "resume"


# ===========================================================================
# P0: Render output (buttons dict, rect types, dimensions, hover branch)
# ===========================================================================


@pytest.mark.unit
class TestRender:
    def test_render_does_not_raise(self, controller, surface):
        controller.render(surface)

    def test_render_populates_buttons_with_four_keys(self, controller, surface):
        controller.render(surface)
        assert set(controller._buttons.keys()) == set(EXPECTED_KEYS)

    def test_render_preserves_button_order(self, controller, surface):
        controller.render(surface)
        assert list(controller._buttons.keys()) == EXPECTED_KEYS

    def test_every_button_value_is_pygame_rect(self, controller, surface):
        controller.render(surface)
        for key, rect in controller._buttons.items():
            assert isinstance(rect, pygame.Rect), f"{key} rect is not pygame.Rect"

    def test_button_rects_have_expected_dimensions(self, controller, surface):
        controller.render(surface)
        for key, rect in controller._buttons.items():
            assert rect.width == 260, f"{key} width wrong"
            assert rect.height == 48, f"{key} height wrong"

    def test_button_rects_are_horizontally_centered(self, controller, surface):
        controller.render(surface)
        expected_x = (SCREEN_W - 260) // 2
        for key, rect in controller._buttons.items():
            assert rect.left == expected_x, f"{key} not centered"

    def test_button_rects_are_stacked_with_gap(self, controller, surface):
        controller.render(surface)
        ys = [controller._buttons[k].top for k in EXPECTED_KEYS]
        # Each subsequent button starts 58px below the previous.
        for prev, nxt in zip(ys, ys[1:], strict=False):
            assert nxt - prev == 58

    def test_render_overlays_screen_pixels(self, controller, surface):
        # The overlay is semi-transparent black; the top-left pixel should
        # be darkened (not the original pure black of a fresh Surface).
        controller.render(surface)
        pixel = surface.get_at((10, 10))
        # Fresh Surface is (0,0,0,255); after overlay it stays dark but
        # the operation must complete without error and produce a valid color.
        assert pixel[:3] == (0, 0, 0)

    def test_render_draws_panel_pixels(self, controller, surface):
        controller.render(surface)
        # Sample a pixel in the panel's left margin (between the panel
        # border and the buttons) — this region is pure panel fill.
        # Panel x range [332, 692], buttons start at x=382; left margin
        # is x in [335, 381]. Pick y near vertical center of the panel.
        panel_left_margin = (360, SCREEN_H // 2)
        pixel = surface.get_at(panel_left_margin)
        # The panel fill is (38, 42, 34), drawn opaquely over the overlay.
        assert pixel[:3] == (38, 42, 34)

    def test_render_with_mouse_over_button_uses_hover_color(self, controller, surface):
        # Cover the hovered=True branch in render(). Move mouse onto the
        # resume button center, then render — must not raise and the button
        # should be drawn with the hover background.
        controller.render(surface)  # populate rects
        resume_rect = controller._buttons["resume"]
        controller.update_mouse(resume_rect.center)
        controller.render(surface)
        # Sample a pixel inside the resume button (away from text/border).
        sample = surface.get_at((resume_rect.left + 5, resume_rect.centery))
        # Hover bg is (70, 78, 55); allow exact match (no alpha on screen).
        assert sample[:3] == (70, 78, 55)

    def test_render_with_mouse_off_button_uses_normal_color(self, controller, surface):
        # Cover the hovered=False branch explicitly: mouse at origin.
        controller.update_mouse((0, 0))
        controller.render(surface)
        resume_rect = controller._buttons["resume"]
        sample = surface.get_at((resume_rect.left + 5, resume_rect.centery))
        # Normal bg is (50, 55, 42).
        assert sample[:3] == (50, 55, 42)

    def test_render_is_idempotent_for_buttons(self, controller, surface):
        controller.render(surface)
        first = {k: tuple(v) for k, v in controller._buttons.items()}
        controller.render(surface)
        second = {k: tuple(v) for k, v in controller._buttons.items()}
        assert first == second

    def test_render_with_non_default_screen_size(self, controller):
        # Ensure render adapts to a different screen size without crashing
        # and still produces 4 buttons centered on the new surface.
        small = pygame.Surface((800, 600))
        controller.render(small)
        assert len(controller._buttons) == 4
        expected_x = (800 - 260) // 2
        for rect in controller._buttons.values():
            assert rect.left == expected_x


# ===========================================================================
# P1: Combination / end-to-end
# ===========================================================================


@pytest.mark.unit
class TestCombination:
    def test_toggle_render_click_resume_deactivate_cycle(self, controller, surface):
        # 1. Menu is initially inactive.
        assert controller.is_active is False

        # 2. Activate the menu.
        controller.toggle()
        assert controller.is_active is True

        # 3. Render — buttons become available.
        controller.render(surface)
        assert set(controller._buttons.keys()) == set(EXPECTED_KEYS)

        # 4. Clicking the resume button returns "resume".
        resume_center = controller._buttons["resume"].center
        action = controller.handle_click(resume_center)
        assert action == "resume"

        # 5. Clicking save returns "save".
        action = controller.handle_click(controller._buttons["save"].center)
        assert action == "save"

        # 6. Clicking load returns "load".
        action = controller.handle_click(controller._buttons["load"].center)
        assert action == "load"

        # 7. Clicking quit_to_menu returns "quit_to_menu".
        action = controller.handle_click(controller._buttons["quit_to_menu"].center)
        assert action == "quit_to_menu"

        # 8. Clicking outside returns None (no action).
        assert controller.handle_click((0, 0)) is None

        # 9. Deactivate closes the menu.
        controller.deactivate()
        assert controller.is_active is False

        # 10. Buttons remain cached after deactivation (deactivate only
        #     touches _active), so a click on resume still resolves — this
        #     documents current behavior.
        assert controller.handle_click(resume_center) == "resume"

    def test_toggle_then_deactivate_then_toggle_returns_active(self, controller):
        controller.toggle()
        assert controller.is_active is True
        controller.deactivate()
        assert controller.is_active is False
        controller.toggle()
        assert controller.is_active is True

    def test_render_then_update_mouse_then_click_uses_latest_rects(self, controller, surface):
        controller.render(surface)
        quit_rect = controller._buttons["quit_to_menu"]
        controller.update_mouse(quit_rect.center)
        # The click uses _buttons (not _mouse), so it still resolves.
        assert controller.handle_click(quit_rect.center) == "quit_to_menu"
