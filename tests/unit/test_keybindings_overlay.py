"""V-08 (Wave D3): Unit tests for KeybindingsOverlay.

Test dimensions (per DevSquad Testing Iron Rule 3):
1. Happy Path (≥50%): show/hide/toggle/on_key_down normal flow
2. Error Case (≥15%): non-toggle key when hidden (no-op), invalid game_state
3. Boundary (≥10%): empty key combo, double show/hide, idempotent calls
4. Performance (≥5%): render timing baseline
5. Configuration (≥5%): custom panel_alpha/text_bg_alpha
6. Integration (≥10%): GameState.paused interaction, real pygame.Surface render
"""

from __future__ import annotations

import os
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

pygame.init()

import pytest  # noqa: E402
from pygame import Surface  # noqa: E402
from pygame.font import Font  # noqa: E402

from pycc2.presentation.ui.keybind_manager import (  # noqa: E402
    DEFAULT_KEYBINDS,
)
from pycc2.presentation.ui.keybindings_overlay import (  # noqa: E402
    ACTION_CATEGORIES,
    DEFAULT_CATEGORY_ORDER,
    PANEL_ALPHA,
    PANEL_BG_COLOR,
    PANEL_BORDER_COLOR,
    ROW_HEIGHT,
    TEXT_BG_ALPHA,
    KeybindingsOverlay,
    categorize_action,
    is_toggle_key,
    key_combo_to_text,
)

# ============================================================================
# Fixtures
# ============================================================================


class _FakeGameState:
    """Minimal stand-in for GameState exposing only the .paused field.

    Using a fake here is acceptable because the overlay contract is narrow:
    it only reads/writes the ``paused`` boolean. We are NOT mocking away
    real pygame surfaces (Iron Rule: prefer real components).
    """

    def __init__(self, paused: bool = False) -> None:
        self.paused = paused


@pytest.fixture
def game_state() -> _FakeGameState:
    """Provide a fresh unpaused game state."""
    return _FakeGameState(paused=False)


@pytest.fixture
def overlay(game_state: _FakeGameState) -> KeybindingsOverlay:
    """Provide a fresh KeybindingsOverlay (hidden by default)."""
    return KeybindingsOverlay(game_state)


@pytest.fixture
def fonts() -> tuple[Font, Font, Font]:
    """Provide real pygame fonts for render tests (not Mock)."""
    font_title = Font(None, 32)
    font_category = Font(None, 22)
    font_key = Font(None, 18)
    return font_title, font_category, font_key


@pytest.fixture
def screen() -> Surface:
    """Provide a real pygame surface for render tests."""
    return Surface((1280, 720))


# ============================================================================
# 1. TestCategorization — action → category mapping (Happy Path + Config)
# ============================================================================


class TestCategorization:
    """Verify action → category mapping (V-08 Wave D3)."""

    def test_known_orders_actions_mapped_to_orders(self) -> None:
        """Verify: known order actions map to 'Orders' category."""
        for action in (
            "move",
            "move_fast",
            "sneak",
            "fire",
            "smoke",
            "defend",
            "hide",
            "cancel",
            "select_all",
        ):
            assert categorize_action(action) == "Orders", (
                f"Action {action!r} should map to 'Orders'"
            )

    def test_known_camera_actions_mapped_to_camera(self) -> None:
        """Verify: camera actions map to 'Camera' category."""
        for action in ("camera_up", "camera_down", "camera_left", "camera_right"):
            assert categorize_action(action) == "Camera", (
                f"Action {action!r} should map to 'Camera'"
            )

    def test_unknown_action_falls_back_to_other(self) -> None:
        """Verify: unknown actions fall back to 'Other' category."""
        assert categorize_action("nonexistent_action") == "Other"
        assert categorize_action("") == "Other"

    def test_all_default_keybinds_have_categories(self) -> None:
        """Verify: every DEFAULT_KEYBINDS action is mapped to a known category.

        This catches the regression of adding a new keybind without updating
        ACTION_CATEGORIES — it would land in 'Other' silently.
        """
        for action in DEFAULT_KEYBINDS:
            category = categorize_action(action)
            assert category in DEFAULT_CATEGORY_ORDER, (
                f"Action {action!r} mapped to unknown category {category!r}; "
                "either add it to ACTION_CATEGORIES or extend DEFAULT_CATEGORY_ORDER."
            )

    def test_action_categories_dict_keys_subset_of_default_keybinds(self) -> None:
        """Verify: ACTION_CATEGORIES doesn't reference non-existent actions."""
        for action in ACTION_CATEGORIES:
            assert action in DEFAULT_KEYBINDS, (
                f"ACTION_CATEGORIES references unknown action {action!r}"
            )


# ============================================================================
# 2. TestKeyComboFormatting — key constant → text conversion
# ============================================================================


class TestKeyComboFormatting:
    """Verify key_combo_to_text() (V-08 Wave D3)."""

    def test_empty_combo_returns_placeholder(self) -> None:
        """Verify: empty combo returns '—' placeholder."""
        assert key_combo_to_text(()) == "—"

    def test_single_letter_uppercased(self) -> None:
        """Verify: single letter key is uppercased (e.g. K_m → 'M')."""
        assert key_combo_to_text((pygame.K_m,)) == "M"
        assert key_combo_to_text((pygame.K_a,)) == "A"
        assert key_combo_to_text((pygame.K_z,)) == "Z"

    def test_ctrl_combo_joined_with_plus(self) -> None:
        """Verify: combo (Ctrl+A) is joined with '+'."""
        result = key_combo_to_text((pygame.K_LCTRL, pygame.K_a))
        assert result == "Ctrl+A"

    def test_shift_combo_joined_with_plus(self) -> None:
        """Verify: combo (Shift+A) is joined with '+'."""
        result = key_combo_to_text((pygame.K_LSHIFT, pygame.K_a))
        assert result == "Shift+A"

    def test_arrow_keys_have_readable_names(self) -> None:
        """Verify: arrow keys render as 'Up'/'Down'/'Left'/'Right'."""
        assert key_combo_to_text((pygame.K_UP,)) == "Up"
        assert key_combo_to_text((pygame.K_DOWN,)) == "Down"
        assert key_combo_to_text((pygame.K_LEFT,)) == "Left"
        assert key_combo_to_text((pygame.K_RIGHT,)) == "Right"

    def test_escape_renders_as_esc(self) -> None:
        """Verify: K_ESCAPE renders as 'Esc'."""
        assert key_combo_to_text((pygame.K_ESCAPE,)) == "Esc"

    def test_space_renders_as_space(self) -> None:
        """Verify: K_SPACE renders as 'Space'."""
        assert key_combo_to_text((pygame.K_SPACE,)) == "Space"

    def test_all_default_keybinds_have_nonempty_text(self) -> None:
        """Verify: every DEFAULT_KEYBINDS entry renders to a non-empty string."""
        for action, combo in DEFAULT_KEYBINDS.items():
            text = key_combo_to_text(combo)
            assert text and text != "—", (
                f"Action {action!r} with combo {combo} rendered to empty/placeholder text"
            )


# ============================================================================
# 3. TestIsToggleKey — ? key detection
# ============================================================================


class TestIsToggleKey:
    """Verify is_toggle_key() (V-08 Wave D3)."""

    def test_k_question_alone_matches(self) -> None:
        """Verify: K_QUESTION matches without any modifier."""
        assert is_toggle_key(pygame.K_QUESTION, 0) is True

    def test_k_question_with_shift_matches(self) -> None:
        """Verify: K_QUESTION matches even with SHIFT modifier."""
        assert is_toggle_key(pygame.K_QUESTION, pygame.KMOD_LSHIFT) is True

    def test_k_slash_with_shift_matches(self) -> None:
        """Verify: K_SLASH + SHIFT matches (US keyboard ? = Shift+/)."""
        assert is_toggle_key(pygame.K_SLASH, pygame.KMOD_LSHIFT) is True
        assert is_toggle_key(pygame.K_SLASH, pygame.KMOD_RSHIFT) is True

    def test_k_slash_without_shift_does_not_match(self) -> None:
        """Verify: K_SLASH alone (i.e. '/') does NOT match (it's not '?')."""
        assert is_toggle_key(pygame.K_SLASH, 0) is False

    def test_other_keys_do_not_match(self) -> None:
        """Verify: random other keys don't trigger toggle."""
        for key in (pygame.K_m, pygame.K_a, pygame.K_ESCAPE, pygame.K_RETURN):
            assert is_toggle_key(key, 0) is False

    def test_other_keys_with_shift_do_not_match(self) -> None:
        """Verify: random other keys with SHIFT don't trigger toggle."""
        for key in (pygame.K_m, pygame.K_a):
            assert is_toggle_key(key, pygame.KMOD_LSHIFT) is False


# ============================================================================
# 4. TestShowHideToggle — overlay state transitions (Happy Path + Boundary)
# ============================================================================


class TestShowHideToggle:
    """Verify show/hide/toggle behavior (V-08 Wave D3)."""

    def test_initial_state_is_hidden(self, overlay: KeybindingsOverlay) -> None:
        """Verify: overlay starts hidden."""
        assert overlay.visible is False

    def test_show_sets_visible_true(self, overlay: KeybindingsOverlay) -> None:
        """Verify: show() sets visible=True."""
        overlay.show()
        assert overlay.visible is True

    def test_hide_sets_visible_false(self, overlay: KeybindingsOverlay) -> None:
        """Verify: hide() sets visible=False."""
        overlay.show()
        overlay.hide()
        assert overlay.visible is False

    def test_hide_when_already_hidden_is_noop(
        self, overlay: KeybindingsOverlay, game_state: _FakeGameState
    ) -> None:
        """Verify: hide() when already hidden does nothing (no error)."""
        initial_paused = game_state.paused
        overlay.hide()
        assert overlay.visible is False
        assert game_state.paused == initial_paused

    def test_show_when_already_visible_is_noop(
        self, overlay: KeybindingsOverlay, game_state: _FakeGameState
    ) -> None:
        """Verify: show() when already visible does nothing."""
        overlay.show()
        paused_after_first_show = game_state.paused
        overlay.show()  # second call
        assert overlay.visible is True
        assert game_state.paused == paused_after_first_show

    def test_toggle_with_question_key_shows(
        self, overlay: KeybindingsOverlay
    ) -> None:
        """Verify: toggle(? key) shows the overlay when hidden."""
        overlay.toggle(key=pygame.K_QUESTION, mod=0)
        assert overlay.visible is True

    def test_toggle_with_question_key_hides(
        self, overlay: KeybindingsOverlay
    ) -> None:
        """Verify: toggle(? key) hides the overlay when visible."""
        overlay.show()
        overlay.toggle(key=pygame.K_QUESTION, mod=0)
        assert overlay.visible is False

    def test_toggle_with_slash_shift_shows(
        self, overlay: KeybindingsOverlay
    ) -> None:
        """Verify: toggle(Shift+/) shows the overlay."""
        overlay.toggle(key=pygame.K_SLASH, mod=pygame.KMOD_LSHIFT)
        assert overlay.visible is True

    def test_toggle_with_non_toggle_key_is_noop(
        self, overlay: KeybindingsOverlay
    ) -> None:
        """Verify: toggle() with non-? key does nothing."""
        overlay.toggle(key=pygame.K_m, mod=0)
        assert overlay.visible is False


# ============================================================================
# 5. TestPauseResumeIntegration — GameState.paused interaction
# ============================================================================


class TestPauseResumeIntegration:
    """Verify game state pause/resume behavior (V-08 Wave D3)."""

    def test_show_pauses_unpaused_game(
        self, overlay: KeybindingsOverlay, game_state: _FakeGameState
    ) -> None:
        """Verify: show() sets paused=True when game was running."""
        assert game_state.paused is False
        overlay.show()
        assert game_state.paused is True

    def test_hide_restores_unpaused_state(
        self, overlay: KeybindingsOverlay, game_state: _FakeGameState
    ) -> None:
        """Verify: hide() restores paused=False when game was running."""
        overlay.show()
        overlay.hide()
        assert game_state.paused is False

    def test_show_remembers_prior_paused_state(
        self, game_state: _FakeGameState
    ) -> None:
        """Verify: when game was already paused, hide() keeps it paused.

        This is the critical edge case: if the player paused for another
        reason and then opens the overlay, closing it shouldn't unpause.
        """
        game_state.paused = True
        overlay = KeybindingsOverlay(game_state)
        overlay.show()
        assert game_state.paused is True
        overlay.hide()
        assert game_state.paused is True  # restored to prior state

    def test_on_key_down_question_toggles_pause(
        self, overlay: KeybindingsOverlay, game_state: _FakeGameState
    ) -> None:
        """Verify: on_key_down(? key) toggles pause alongside visibility."""
        assert game_state.paused is False
        overlay.on_key_down(pygame.K_QUESTION, mod=0)
        assert overlay.visible is True
        assert game_state.paused is True
        overlay.on_key_down(pygame.K_QUESTION, mod=0)
        assert overlay.visible is False
        assert game_state.paused is False

    def test_on_key_down_other_key_dismisses_and_resumes(
        self, overlay: KeybindingsOverlay, game_state: _FakeGameState
    ) -> None:
        """Verify: any non-? key dismisses visible overlay and resumes."""
        overlay.show()
        assert game_state.paused is True
        overlay.on_key_down(pygame.K_ESCAPE, mod=0)
        assert overlay.visible is False
        assert game_state.paused is False

    def test_on_key_down_other_key_when_hidden_is_noop(
        self, overlay: KeybindingsOverlay, game_state: _FakeGameState
    ) -> None:
        """Verify: non-? key when hidden does nothing."""
        assert overlay.visible is False
        overlay.on_key_down(pygame.K_m, mod=0)
        assert overlay.visible is False
        assert game_state.paused is False


# ============================================================================
# 6. TestRender — real pygame.Surface rendering (Integration)
# ============================================================================


class TestRender:
    """Verify rendering produces valid output (V-08 Wave D3)."""

    def test_render_when_hidden_does_nothing(
        self,
        overlay: KeybindingsOverlay,
        screen: Surface,
        fonts: tuple[Font, Font, Font],
    ) -> None:
        """Verify: render() when hidden does not modify surface.

        Hidden overlay should not draw anything — the surface should
        remain identical to its pre-render state.
        """
        # Fill surface with a sentinel color
        sentinel = (123, 45, 67)
        screen.fill(sentinel)

        overlay.render(screen, *fonts)

        # Verify surface unchanged
        pixel = screen.get_at((640, 360))
        assert pixel[:3] == sentinel, (
            f"Hidden overlay modified surface: pixel(640,360)={pixel[:3]}, expected {sentinel}"
        )

    def test_render_when_visible_modifies_surface(
        self,
        overlay: KeybindingsOverlay,
        screen: Surface,
        fonts: tuple[Font, Font, Font],
    ) -> None:
        """Verify: render() when visible draws the panel onto the surface."""
        screen.fill((0, 0, 0))  # black background
        overlay.show()
        overlay.render(screen, *fonts)

        # The panel area should now have non-black pixels (panel bg + content)
        # Sample the center pixel (panel is centered)
        center_pixel = screen.get_at((640, 360))
        assert center_pixel[:3] != (0, 0, 0), (
            f"Visible overlay did not draw on center pixel: {center_pixel[:3]}"
        )

    def test_render_no_crash_with_minimal_surface(
        self,
        overlay: KeybindingsOverlay,
        fonts: tuple[Font, Font, Font],
    ) -> None:
        """Verify: render() doesn't crash on a tiny surface.

        Boundary case: surface smaller than PANEL_MARGIN should not
        raise — it should still render (clamped/handled gracefully).
        """
        tiny = Surface((100, 100))
        overlay.show()
        # Should not raise
        overlay.render(tiny, *fonts)

    def test_render_no_crash_with_large_surface(
        self,
        overlay: KeybindingsOverlay,
        fonts: tuple[Font, Font, Font],
    ) -> None:
        """Verify: render() doesn't crash on a large surface (4K)."""
        large = Surface((3840, 2160))
        overlay.show()
        overlay.render(large, *fonts)

    def test_render_includes_all_categories(
        self,
        overlay: KeybindingsOverlay,
        screen: Surface,
        fonts: tuple[Font, Font, Font],
    ) -> None:
        """Verify: render() draws all expected categories.

        We can't easily OCR text from a pygame surface, but we can verify
        the surface has substantial non-background pixels in the panel area.
        """
        screen.fill((0, 0, 0))
        overlay.show()
        overlay.render(screen, *fonts)

        # Count non-black pixels in panel area
        non_black = 0
        for x in range(100, 1180, 20):
            for y in range(100, 620, 20):
                if screen.get_at((x, y))[:3] != (0, 0, 0):
                    non_black += 1
        # Should have substantial content (at least 50 sampled points)
        assert non_black > 50, (
            f"Rendered panel has insufficient content: only {non_black} non-black pixels sampled"
        )


# ============================================================================
# 7. TestConfiguration — custom alpha values
# ============================================================================


class TestConfiguration:
    """Verify custom configuration (V-08 Wave D3)."""

    def test_default_panel_alpha_is_180(
        self, overlay: KeybindingsOverlay
    ) -> None:
        """Verify: default panel_alpha is 180 (Wave B-rev spec)."""
        assert overlay.panel_alpha == PANEL_ALPHA == 180

    def test_default_text_bg_alpha_is_153(
        self, overlay: KeybindingsOverlay
    ) -> None:
        """Verify: default text_bg_alpha is 153 (Wave B-rev spec)."""
        assert overlay.text_bg_alpha == TEXT_BG_ALPHA == 153

    def test_custom_panel_alpha(self, game_state: _FakeGameState) -> None:
        """Verify: panel_alpha can be overridden."""
        overlay = KeybindingsOverlay(game_state, panel_alpha=200)
        assert overlay.panel_alpha == 200

    def test_custom_text_bg_alpha(self, game_state: _FakeGameState) -> None:
        """Verify: text_bg_alpha can be overridden."""
        overlay = KeybindingsOverlay(game_state, text_bg_alpha=100)
        assert overlay.text_bg_alpha == 100

    def test_custom_alphas_affect_render(
        self,
        game_state: _FakeGameState,
        screen: Surface,
        fonts: tuple[Font, Font, Font],
    ) -> None:
        """Verify: different alpha values produce different render output.

        Performance/Config integration: render with high alpha vs low alpha
        and verify the panel background color differs.
        """
        # High alpha (more opaque)
        overlay_high = KeybindingsOverlay(game_state, panel_alpha=255)
        overlay_high.show()
        screen.fill((0, 0, 0))
        overlay_high.render(screen, *fonts)
        high_pixel = screen.get_at((640, 360))[:3]
        overlay_high.hide()

        # Low alpha (more transparent)
        overlay_low = KeybindingsOverlay(game_state, panel_alpha=30)
        overlay_low.show()
        screen.fill((0, 0, 0))
        overlay_low.render(screen, *fonts)
        low_pixel = screen.get_at((640, 360))[:3]
        overlay_low.hide()

        # Higher alpha should produce a color closer to PANEL_BG_COLOR
        # (less of the black background showing through)
        def color_distance(c1: tuple, c2: tuple) -> int:
            return sum(abs(a - b) for a, b in zip(c1, c2, strict=False))

        high_dist = color_distance(high_pixel, PANEL_BG_COLOR)
        low_dist = color_distance(low_pixel, PANEL_BG_COLOR)
        assert high_dist < low_dist, (
            f"High alpha ({high_dist=}) should be closer to PANEL_BG_COLOR "
            f"than low alpha ({low_dist=})"
        )


# ============================================================================
# 8. TestPerformance — render timing baseline
# ============================================================================


class TestPerformance:
    """Verify render performance (V-08 Wave D3)."""

    def test_render_completes_under_50ms(
        self,
        overlay: KeybindingsOverlay,
        screen: Surface,
        fonts: tuple[Font, Font, Font],
    ) -> None:
        """Verify: render() completes under 50ms (20+ FPS headroom on 60FPS).

        Performance baseline: at 60 FPS, each frame has ~16.6ms budget.
        The overlay should consume < 50ms (3 frame budgets) to allow
        smooth fade-in/out and avoid jank during toggle.
        """
        overlay.show()
        start = time.perf_counter()
        # Run 10 iterations to amortize any one-time setup costs
        for _ in range(10):
            overlay.render(screen, *fonts)
        elapsed_ms = (time.perf_counter() - start) * 1000
        per_render_ms = elapsed_ms / 10
        assert per_render_ms < 50, (
            f"Render too slow: {per_render_ms:.1f}ms/render (threshold 50ms)"
        )


# ============================================================================
# 9. TestConstants — verify Wave B-rev spec values
# ============================================================================


class TestConstants:
    """Verify Wave B-rev spec values are enforced (V-08 Wave D3)."""

    def test_panel_alpha_is_70_percent(self) -> None:
        """Verify: PANEL_ALPHA = 180 ≈ 70% opacity (180/255 ≈ 0.706)."""
        assert PANEL_ALPHA == 180
        assert 0.69 < PANEL_ALPHA / 255 < 0.71

    def test_text_bg_alpha_is_60_percent(self) -> None:
        """Verify: TEXT_BG_ALPHA = 153 ≈ 60% opacity (153/255 = 0.6)."""
        assert TEXT_BG_ALPHA == 153
        assert 0.59 < TEXT_BG_ALPHA / 255 < 0.61

    def test_panel_bg_color_is_dark(self) -> None:
        """Verify: PANEL_BG_COLOR is a dark color (low brightness)."""
        r, g, b = PANEL_BG_COLOR
        assert r < 50 and g < 50 and b < 50, (
            f"PANEL_BG_COLOR {PANEL_BG_COLOR} is not dark enough for an overlay"
        )

    def test_panel_border_color_visible(self) -> None:
        """Verify: PANEL_BORDER_COLOR is distinguishable from PANEL_BG_COLOR."""
        bg = PANEL_BG_COLOR
        border = PANEL_BORDER_COLOR
        # Border should be brighter than bg
        assert sum(border) > sum(bg), (
            f"Border {border} not brighter than bg {bg}"
        )

    def test_row_height_reasonable(self) -> None:
        """Verify: ROW_HEIGHT is in a reasonable range for text rows."""
        assert 16 <= ROW_HEIGHT <= 32, (
            f"ROW_HEIGHT {ROW_HEIGHT} out of reasonable range [16, 32]"
        )

    def test_default_category_order_has_expected_entries(self) -> None:
        """Verify: DEFAULT_CATEGORY_ORDER contains the expected categories."""
        assert "Orders" in DEFAULT_CATEGORY_ORDER
        assert "Camera" in DEFAULT_CATEGORY_ORDER
        assert "Other" in DEFAULT_CATEGORY_ORDER
