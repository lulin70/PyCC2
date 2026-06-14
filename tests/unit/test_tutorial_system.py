from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pycc2.domain.interfaces.display_config import DisplayConfig
from pycc2.presentation.ui.hint_manager import ActiveHint, HintManager, HINTS
from pycc2.presentation.ui.tutorial_system import (
    TutorialOverlay,
    TutorialStep,
    TutorialState,
)


@pytest.fixture
def display_config():
    return DisplayConfig()


@pytest.fixture
def tutorial_overlay(display_config):
    return TutorialOverlay(display_config)


@pytest.fixture
def hint_manager():
    return HintManager()


def _make_key_event(key):
    import pygame
    ev = MagicMock()
    ev.type = pygame.KEYDOWN
    ev.key = key
    return ev


def _make_mouse_event(button=1):
    import pygame
    ev = MagicMock()
    ev.type = pygame.MOUSEBUTTONDOWN
    ev.button = button
    return ev


class TestTutorialStateDefaults:

    def test_default_step_is_welcome(self):
        s = TutorialState()
        assert s.step == TutorialStep.WELCOME

    def test_completed_set_empty_by_default(self):
        s = TutorialState()
        assert len(s.completed) == 0

    def test_dismissed_false_by_default(self):
        s = TutorialState()
        assert s.dismissed is False

    def test_show_hints_true_by_default(self):
        s = TutorialState()
        assert s.show_hints is True

    def test_hint_cooldown_zero_by_default(self):
        s = TutorialState()
        assert s.hint_cooldown == 0


class TestTutorialStepEnum:

    def test_all_steps_defined(self):
        expected = {
            "WELCOME",
            "SELECT_UNIT",
            "MOVE_UNIT",
            "ATTACK_ENEMY",
            "VICTORY_CONDITIONS",
            "COMPLETE",
        }
        actual = {s.name for s in TutorialStep}
        assert actual == expected

    def test_step_count_is_six(self):
        assert len(TutorialStep) == 6


class TestTutorialOverlayShowHideToggle:

    def test_initially_not_visible(self, tutorial_overlay):
        assert tutorial_overlay.visible is False

    def test_show_makes_visible(self, tutorial_overlay):
        tutorial_overlay.show()
        assert tutorial_overlay.visible is True

    def test_show_with_specific_step(self, tutorial_overlay):
        tutorial_overlay.show(step=TutorialStep.MOVE_UNIT)
        assert tutorial_overlay.visible is True
        assert tutorial_overlay.state.step == TutorialStep.MOVE_UNIT

    def test_hide_sets_target_alpha_zero(self, tutorial_overlay):
        tutorial_overlay.show()
        tutorial_overlay.hide()
        assert tutorial_overlay._target_alpha == 0.0

    def test_toggle_from_hidden_shows(self, tutorial_overlay):
        tutorial_overlay.toggle()
        assert tutorial_overlay.visible is True

    def test_toggle_from_visible_hides(self, tutorial_overlay):
        tutorial_overlay.show()
        tutorial_overlay.toggle()
        assert tutorial_overlay._target_alpha == 0.0


class TestTutorialOverlayStepAdvancement:

    def test_advance_from_welcome_to_select_unit(self, tutorial_overlay):
        tutorial_overlay.state.step = TutorialStep.WELCOME
        result = tutorial_overlay.advance_step()
        assert result is True
        assert tutorial_overlay.state.step == TutorialStep.SELECT_UNIT

    def test_advance_through_all_steps(self, tutorial_overlay):
        steps = list(TutorialStep)
        for i in range(len(steps) - 1):
            result = tutorial_overlay.advance_step()
            assert result is True
        final_result = tutorial_overlay.advance_step()
        assert final_result is False
        assert tutorial_overlay.state.step == TutorialStep.COMPLETE

    def test_advance_marks_step_as_completed(self, tutorial_overlay):
        tutorial_overlay.advance_step()
        assert TutorialStep.WELCOME in tutorial_overlay.state.completed

    def test_space_key_advances_tutorial(self, tutorial_overlay):
        event = _make_key_event(32)
        result = tutorial_overlay.handle_input(event)
        assert result == 'advanced'
        assert tutorial_overlay.state.step == TutorialStep.SELECT_UNIT

    def test_mouse_click_advances_tutorial(self, tutorial_overlay):
        event = _make_mouse_event(1)
        result = tutorial_overlay.handle_input(event)
        assert result == 'advanced'

    def test_esc_closes_tutorial(self, tutorial_overlay):
        tutorial_overlay.show()
        event = _make_key_event(27)
        result = tutorial_overlay.handle_input(event)
        assert result == 'closed'

    def test_no_advancement_on_complete_step(self, tutorial_overlay):
        tutorial_overlay.state.step = TutorialStep.COMPLETE
        event = _make_key_event(32)
        result = tutorial_overlay.handle_input(event)
        assert result is None


class TestTutorialStepsContent:

    def test_welcome_has_title_and_lines(self):
        content = TutorialOverlay.STEPS[TutorialStep.WELCOME]
        assert "title" in content
        assert "lines" in content
        assert len(content["lines"]) >= 1, f"WELCOME step should have at least 1 line, got {len(content['lines'])}"
        assert content["title"] == "Welcome to PyCC2"

    def test_select_unit_content_valid(self):
        content = TutorialOverlay.STEPS[TutorialStep.SELECT_UNIT]
        assert "Select" in content["title"]
        assert any("GREEN" in line for line in content["lines"])

    def test_move_unit_content_valid(self):
        content = TutorialOverlay.STEPS[TutorialStep.MOVE_UNIT]
        assert "Move" in content["title"]
        assert any("RIGHT-CLICK" in line for line in content["lines"])

    def test_attack_enemy_content_valid(self):
        content = TutorialOverlay.STEPS[TutorialStep.ATTACK_ENEMY]
        assert "Engage" in content["title"] or "Attack" in content["title"]

    def test_victory_conditions_content_valid(self):
        content = TutorialOverlay.STEPS[TutorialStep.VICTORY_CONDITIONS]
        assert "Victory" in content["title"]
        assert any("Commander" in line for line in content["lines"])

    def test_all_five_main_steps_have_content(self):
        main_steps = [
            TutorialStep.WELCOME,
            TutorialStep.SELECT_UNIT,
            TutorialStep.MOVE_UNIT,
            TutorialStep.ATTACK_ENEMY,
            TutorialStep.VICTORY_CONDITIONS,
        ]
        for step in main_steps:
            assert step in TutorialOverlay.STEPS
            assert "title" in TutorialOverlay.STEPS[step]
            assert "lines" in TutorialOverlay.STEPS[step]
            assert len(TutorialOverlay.STEPS[step]["lines"]) >= 1, f"Step {step} should have at least 1 line"


class TestFadeAnimation:

    def test_fade_in_on_show(self, tutorial_overlay):
        tutorial_overlay.show()
        assert tutorial_overlay._alpha == 0.0
        assert tutorial_overlay._target_alpha == 0.9

    def test_fade_out_on_hide(self, tutorial_overlay):
        tutorial_overlay.show()
        tutorial_overlay._alpha = 0.9
        tutorial_overlay.hide()
        assert tutorial_overlay._target_alpha == 0.0

    def test_update_increases_alpha_when_fading_in(self, tutorial_overlay):
        tutorial_overlay.show()
        alpha_before = tutorial_overlay._alpha
        for _ in range(10):
            tutorial_overlay.update()
        assert tutorial_overlay._alpha > alpha_before

    def test_update_decreases_alpha_when_fading_out(self, tutorial_overlay):
        tutorial_overlay.show()
        for _ in range(50):
            tutorial_overlay.update()
        tutorial_overlay.hide()
        alpha_before = tutorial_overlay._alpha
        for _ in range(10):
            tutorial_overlay.update()
        assert tutorial_overlay._alpha < alpha_before

    def test_alpha_clamps_to_target(self, tutorial_overlay):
        tutorial_overlay.show()
        for _ in range(200):
            tutorial_overlay.update()
        assert abs(tutorial_overlay._alpha - 0.9) < 0.02


class TestHintManagerBasics:

    def test_initially_enabled(self, hint_manager):
        assert hint_manager.enabled is True

    def test_disable_clears_hints(self, hint_manager):
        hint_manager.show_hint("test", 100, 100)
        hint_manager.set_enabled(False)
        assert hint_manager.enabled is False
        assert len(hint_manager._hints) == 0

    def test_re_enable(self, hint_manager):
        hint_manager.set_enabled(False)
        hint_manager.set_enabled(True)
        assert hint_manager.enabled is True

    def test_show_hint_adds_to_list(self, hint_manager):
        hint_manager.show_hint("hello", 50, 60)
        assert len(hint_manager._hints) == 1
        assert hint_manager._hints[0].text == "hello"

    def test_show_hint_ignored_when_disabled(self, hint_manager):
        hint_manager.set_enabled(False)
        hint_manager.show_hint("ignored", 0, 0)
        assert len(hint_manager._hints) == 0


class TestHintLifecycle:

    def test_update_decrements_lifetime(self, hint_manager):
        hint_manager.show_hint("test", 0, 0, lifetime=10)
        initial = hint_manager._hints[0].lifetime
        hint_manager.update()
        assert hint_manager._hints[0].lifetime == initial - 1

    def test_hint_removed_after_lifetime_expires(self, hint_manager):
        hint_manager.show_hint("short", 0, 0, lifetime=1)
        hint_manager.update()
        hint_manager.update()
        assert len(hint_manager._hints) == 0

    def test_multiple_hints_independent_lifecycle(self, hint_manager):
        hint_manager.show_hint("a", 0, 0, lifetime=20)
        hint_manager.show_hint("b", 0, 0, lifetime=5)
        for _ in range(6):
            hint_manager.update()
        assert len(hint_manager._hints) == 1
        assert hint_manager._hints[0].text == "a"

    def test_active_hint_fields(self):
        h = ActiveHint(text="hi", x=1.0, y=2.0, lifetime=100, max_lifetime=100)
        assert h.text == "hi"
        assert h.x == 1.0
        assert h.y == 2.0
        assert h.lifetime == 100
        assert h.max_lifetime == 100


class TestHintsDict:

    def test_hints_dict_not_empty(self):
        assert len(HINTS) >= 6, f"HINTS dict should have at least 6 entries (first_select, right_click_move, etc.), got {len(HINTS)}"

    def test_contains_expected_keys(self):
        expected_keys = {
            "first_select",
            "right_click_move",
            "right_click_attack",
            "low_hp",
            "out_of_ammo",
            "enemy_commander_spotted",
        }
        assert set(HINTS.keys()) == expected_keys

    def test_each_hint_is_tuple_of_three(self):
        for key, val in HINTS.items():
            assert isinstance(val, tuple)
            assert len(val) == 3
            assert isinstance(val[0], str)

    def test_low_hp_hint_text(self):
        assert "HP" in HINTS["low_hp"][0]


class TestRenderNoCrash:

    @patch("pygame.font.Font")
    @patch("pygame.Surface")
    def test_render_with_mock_screen(self, mock_surface_cls, mock_font_cls, tutorial_overlay, display_config):
        tutorial_overlay.show()
        mock_screen = MagicMock()
        mock_screen.get_size.return_value = (800, 600)
        tutorial_overlay.render(mock_screen)

    @patch("pygame.font.Font")
    def test_render_hint_with_mock_screen(self, mock_font_cls, tutorial_overlay):
        mock_screen = MagicMock()
        tutorial_overlay.show_contextual_hint("test hint", (400, 300), lifetime=60)
        tutorial_overlay.render_hint(mock_screen)

    @patch("pygame.font.Font")
    def test_hint_manager_render_with_mock_screen(self, mock_font_cls, hint_manager):
        mock_screen = MagicMock()
        hint_manager.show_hint("hint text", 100, 100)
        hint_manager.render(mock_screen)


class TestContextualHintIntegration:

    def test_show_contextual_hint_sets_state(self, tutorial_overlay):
        tutorial_overlay.show_contextual_hint("Move here!", (200, 150), lifetime=90)
        assert tutorial_overlay._current_hint == "Move here!"
        assert tutorial_overlay._hint_position == (200, 150)
        assert tutorial_overlay.state.hint_cooldown == 90

    def test_render_hint_skips_when_cooldown_zero(self, tutorial_overlay):
        tutorial_overlay.state.hint_cooldown = 0
        tutorial_overlay._current_hint = ""
        mock_screen = MagicMock()
        tutorial_overlay.render_hint(mock_screen)

    def test_hint_cooldown_decrements_on_update(self, tutorial_overlay):
        tutorial_overlay.state.hint_cooldown = 50
        tutorial_overlay.update()
        assert tutorial_overlay.state.hint_cooldown == 49


class TestCompleteStepAutoHide:

    def test_complete_step_auto_hides_after_delay(self, tutorial_overlay):
        tutorial_overlay.state.step = TutorialStep.COMPLETE
        tutorial_overlay.show()
        tutorial_overlay._alpha = 0.9
        tutorial_overlay._target_alpha = 0.9
        for _ in range(200):
            tutorial_overlay.update()
        assert tutorial_overlay._target_alpha == 0.0
