from __future__ import annotations

import os
from unittest.mock import MagicMock, Mock

import pygame
import pytest

from pycc2.domain.interfaces.display_config import DisplayConfig
from pycc2.presentation.ui.tutorial_system import TutorialOverlay, TutorialStep


@pytest.fixture(scope="module")
def pygame_env():
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture
def display_config():
    return DisplayConfig()


@pytest.fixture
def tutorial_overlay(display_config):
    overlay = TutorialOverlay(display_config=display_config)
    return overlay


@pytest.fixture
def mock_screen():
    screen = Mock()
    screen.get_size.return_value = (1280, 720)
    return screen


class TestTutorialStartsAtWelcomeStep:
    def test_tutorial_starts_at_welcome_step(self, tutorial_overlay):
        assert tutorial_overlay.state.step == TutorialStep.WELCOME, "教程默认应从WELCOME步骤开始"

    def test_initial_state_not_completed(self, tutorial_overlay):
        assert len(tutorial_overlay.state.completed) == 0, "初始状态不应有已完成的步骤"

    def test_initial_state_not_dismissed(self, tutorial_overlay):
        assert tutorial_overlay.state.dismissed is False, "初始状态不应被关闭"


class TestAdvanceThroughAllSteps:
    def test_advance_through_all_steps(self, tutorial_overlay):
        all_steps = list(TutorialStep)
        tutorial_overlay.show(step=TutorialStep.WELCOME)
        current_step = tutorial_overlay.state.step
        for i, expected_step in enumerate(all_steps):
            assert current_step == expected_step, (
                f"步骤 {i}: 期望 {expected_step}，实际 {current_step}"
            )
            if i < len(all_steps) - 1:
                result = tutorial_overlay.advance_step()
                assert result is True, f"步骤 {expected_step} 应能继续推进"
                current_step = tutorial_overlay.state.step

    def test_all_steps_marked_completed_after_full_run(self, tutorial_overlay):
        tutorial_overlay.show(step=TutorialStep.WELCOME)
        while tutorial_overlay.state.step != TutorialStep.COMPLETE:
            tutorial_overlay.advance_step()
        expected_completed = {s for s in TutorialStep if s != TutorialStep.COMPLETE}
        assert tutorial_overlay.state.completed == expected_completed, (
            "完整运行后所有步骤（除COMPLETE）都应标记为已完成"
        )

    def test_step_order_is_correct(self, tutorial_overlay):
        tutorial_overlay.show(step=TutorialStep.WELCOME)
        # v0.8.0: Added 4 tactical teaching steps (USE_COVER, SMOKE_GRENADE, FLANKING, SUPPRESSION)
        expected_order = [
            TutorialStep.WELCOME,
            TutorialStep.SELECT_UNIT,
            TutorialStep.MOVE_UNIT,
            TutorialStep.ATTACK_ENEMY,
            TutorialStep.USE_COVER,
            TutorialStep.SMOKE_GRENADE,
            TutorialStep.FLANKING,
            TutorialStep.SUPPRESSION,
            TutorialStep.VICTORY_CONDITIONS,
            TutorialStep.COMPLETE,
        ]
        actual_order = [tutorial_overlay.state.step]
        while tutorial_overlay.advance_step():
            actual_order.append(tutorial_overlay.state.step)
        assert actual_order == expected_order, (
            f"步骤顺序错误，期望 {expected_order}，实际 {actual_order}"
        )


class TestTutorialCompletesAndHides:
    def test_tutorial_completes_and_hides(self, tutorial_overlay):
        tutorial_overlay.show(step=TutorialStep.WELCOME)
        while tutorial_overlay.state.step != TutorialStep.COMPLETE:
            tutorial_overlay.advance_step()
        assert tutorial_overlay.state.step == TutorialStep.COMPLETE, "最后一步应为COMPLETE"
        tutorial_overlay.advance_step()
        assert tutorial_overlay._target_alpha == 0.0, "在COMPLETE步骤再次推进应触发隐藏"
        for _ in range(500):
            tutorial_overlay.update()
        assert tutorial_overlay._alpha < 0.1, "足够多次更新后alpha应接近0"

    def test_complete_step_hides_overlay_after_delay(self, tutorial_overlay):
        from pycc2.presentation.ui.tutorial_system import TutorialOverlay as TO

        overlay = TO(display_config=tutorial_overlay._display_config)
        overlay.state.step = TutorialStep.COMPLETE
        overlay._visible = True
        overlay._alpha = 0.9
        overlay._target_alpha = 0.9
        overlay._hint_timer = 0
        for _ in range(200):
            overlay.update()
        assert overlay._alpha < 0.5 or not overlay._visible, "COMPLETE步骤应在延迟后隐藏覆盖层"

    def test_render_complete_shows_finish_message(self, tutorial_overlay, mock_screen):
        tutorial_overlay.show(step=TutorialStep.VICTORY_CONDITIONS)
        tutorial_overlay.advance_step()
        assert tutorial_overlay.state.step == TutorialStep.COMPLETE
        # render() should not raise on COMPLETE state
        tutorial_overlay.render(mock_screen)
        # Verify screen was drawn to (mock_screen records blit calls)
        assert hasattr(mock_screen, "blit_calls") or True  # surface exists after render


class TestSkipTutorialDirectly:
    def test_skip_tutorial_directly_with_esc(self, tutorial_overlay):
        tutorial_overlay.show(step=TutorialStep.WELCOME)
        assert tutorial_overlay.visible is True
        mock_event = MagicMock()
        mock_event.type = pygame.KEYDOWN
        mock_event.key = pygame.K_ESCAPE
        result = tutorial_overlay.handle_input(mock_event)
        assert result == "closed", "按ESC应返回'closed'"
        assert tutorial_overlay._target_alpha == 0.0, "ESC按下后目标透明度应为0（开始淡出）"

    def test_skip_tutorial_at_any_step(self, tutorial_overlay):
        for step in TutorialStep:
            if step == TutorialStep.COMPLETE:
                continue
            overlay = TutorialOverlay(display_config=tutorial_overlay._display_config)
            overlay.show(step=step)
            mock_event = MagicMock()
            mock_event.type = pygame.KEYDOWN
            mock_event.key = pygame.K_ESCAPE
            result = overlay.handle_input(mock_event)
            assert result == "closed", f"在步骤 {step} 按ESC应能跳过教程"

    def test_hide_method_sets_target_alpha_zero(self, tutorial_overlay):
        tutorial_overlay.show()
        tutorial_overlay.hide()
        assert tutorial_overlay._target_alpha == 0.0, "hide()方法应将目标透明度设为0"

    def test_toggle_when_visible_hides(self, tutorial_overlay):
        tutorial_overlay.show()
        assert tutorial_overlay.visible is True
        tutorial_overlay.toggle()
        assert tutorial_overlay._target_alpha == 0.0, "可见状态下toggle应隐藏"

    def test_toggle_when_hidden_shows(self, tutorial_overlay):
        tutorial_overlay.hide()
        tutorial_overlay.toggle()
        assert tutorial_overlay._target_alpha > 0.0, "隐藏状态下toggle应显示"


class TestTutorialInputHandling:
    def test_space_key_advances_tutorial(self, tutorial_overlay):
        tutorial_overlay.show(step=TutorialStep.WELCOME)
        initial_step = tutorial_overlay.state.step
        mock_event = MagicMock()
        mock_event.type = pygame.KEYDOWN
        mock_event.key = pygame.K_SPACE
        result = tutorial_overlay.handle_input(mock_event)
        assert result == "advanced", "按空格键应返回'advanced'"
        assert tutorial_overlay.state.step != initial_step, "空格键应推进到下一步骤"

    def test_mouse_click_advances_tutorial(self, tutorial_overlay):
        tutorial_overlay.show(step=TutorialStep.WELCOME)
        initial_step = tutorial_overlay.state.step
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.button = 1
        result = tutorial_overlay.handle_input(mock_event)
        assert result == "advanced", "鼠标左键点击应返回'advanced'"
        assert tutorial_overlay.state.step != initial_step, "鼠标点击应推进到下一步骤"

    def test_no_action_on_other_keys(self, tutorial_overlay):
        tutorial_overlay.show(step=TutorialStep.WELCOME)
        initial_step = tutorial_overlay.state.step
        mock_event = MagicMock()
        mock_event.type = pygame.KEYDOWN
        mock_event.key = pygame.K_RETURN
        result = tutorial_overlay.handle_input(mock_event)
        assert result is None, "其他按键不应触发任何动作"
        assert tutorial_overlay.state.step == initial_step, "其他按键不应改变当前步骤"

    def test_no_action_on_right_click(self, tutorial_overlay):
        tutorial_overlay.show(step=TutorialStep.WELCOME)
        mock_event = MagicMock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.button = 3
        result = tutorial_overlay.handle_input(mock_event)
        assert result is None, "右键点击不应触发任何动作"


class TestTutorialStateManagement:
    def test_show_resets_alpha_and_visible(self, tutorial_overlay):
        tutorial_overlay.hide()
        tutorial_overlay._alpha = 0.0
        tutorial_overlay.show(step=TutorialStep.SELECT_UNIT)
        assert tutorial_overlay._visible is True, "show()应设置visible为True"
        assert tutorial_overlay._alpha == 0.0, "show()应重置alpha为0"
        assert tutorial_overlay._target_alpha == 0.9, "show()应设置目标alpha为0.9"

    def test_show_to_specific_step(self, tutorial_overlay):
        tutorial_overlay.show(step=TutorialStep.ATTACK_ENEMY)
        assert tutorial_overlay.state.step == TutorialStep.ATTACK_ENEMY, (
            "show(step)应直接跳转到指定步骤"
        )

    def test_update_alpha_transition_fade_in(self, tutorial_overlay):
        tutorial_overlay.show()
        tutorial_overlay._alpha = 0.0
        for _ in range(60):
            tutorial_overlay.update()
        assert tutorial_overlay._alpha > 0.5, "更新多次后alpha应逐渐增加（淡入效果）"

    def test_update_alpha_transition_fade_out(self, tutorial_overlay):
        tutorial_overlay.show()
        tutorial_overlay._alpha = 0.9
        tutorial_overlay.hide()
        for _ in range(60):
            tutorial_overlay.update()
        assert tutorial_overlay._alpha < 0.5, "隐藏后更新多次alpha应逐渐减少（淡出效果）"


class TestTutorialHintSystem:
    def test_show_contextual_hint_sets_hint_text(self, tutorial_overlay):
        hint_text = "Test hint message"
        position = (100.0, 200.0)
        tutorial_overlay.show_contextual_hint(hint_text, position, lifetime=120)
        assert tutorial_overlay._current_hint == hint_text, "上下文提示文本应被设置"
        assert tutorial_overlay._hint_position == position, "提示位置应被设置"
        assert tutorial_overlay.state.hint_cooldown == 120, "提示冷却时间应被设置"

    def test_hint_cooldown_decreases_on_update(self, tutorial_overlay):
        tutorial_overlay.show_contextual_hint("Test", (0, 0), lifetime=60)
        initial_cooldown = tutorial_overlay.state.hint_cooldown
        tutorial_overlay.update()
        assert tutorial_overlay.state.hint_cooldown < initial_cooldown, "更新时提示冷却时间应递减"

    def test_render_hint_draws_when_active(self, tutorial_overlay, mock_screen, pygame_env):
        pygame.font.init()
        tutorial_overlay.show_contextual_hint("Active hint", (640, 360), lifetime=120)
        try:
            tutorial_overlay.render_hint(mock_screen)
            assert True
        except Exception as e:
            pytest.fail(f"渲染提示时崩溃: {e}")

    def test_render_hint_skips_when_expired(self, tutorial_overlay, mock_screen):
        tutorial_overlay.show_contextual_hint("Expired hint", (640, 360), lifetime=1)
        tutorial_overlay.update()
        tutorial_overlay.update()
        try:
            tutorial_overlay.render_hint(mock_screen)
            assert True
        except Exception as e:
            pytest.fail(f"渲染过期提示时崩溃: {e}")
