"""E2E tutorial flow tests for the CC2 tutorial overlay."""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pygame
import pytest

from pycc2.presentation.ui.tutorial_system import (
    TutorialHintSystem,
    TutorialOverlay,
    TutorialStep,
    TutorialSystem,
)


@pytest.fixture(scope="module", autouse=True)
def pygame_env():
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture
def overlay():
    return TutorialOverlay()


def _key_event(key):
    event = MagicMock()
    event.type = pygame.KEYDOWN
    event.key = key
    return event


class TestTutorialStartsAtWelcomeStep:
    def test_starts_at_welcome(self, overlay):
        assert overlay.system.current_step is TutorialStep.WELCOME

    def test_no_completed_steps_at_start(self, overlay):
        assert len(overlay.system.completed_steps) == 0

    def test_overlay_visible_at_start(self, overlay):
        assert overlay.visible is True


class TestAdvanceThroughAllSteps:
    def test_space_walks_through_every_step(self, overlay):
        visited = []
        for _ in range(len(TutorialStep) - 1):
            visited.append(overlay.system.current_step)
            overlay.handle_input(_key_event(pygame.K_SPACE))
        visited.append(overlay.system.current_step)
        assert visited == list(TutorialStep)

    def test_last_step_disables_overlay(self, overlay):
        for _ in range(len(TutorialStep) - 1):
            overlay.handle_input(_key_event(pygame.K_SPACE))
        assert overlay.system.current_step is TutorialStep.TUTORIAL_COMPLETE
        overlay.handle_input(_key_event(pygame.K_SPACE))
        assert overlay.visible is False


class TestTutorialInputHandling:
    def test_escape_skips(self, overlay):
        overlay.handle_input(_key_event(pygame.K_ESCAPE))
        assert overlay.visible is False

    def test_other_keys_do_not_advance(self, overlay):
        overlay.handle_input(_key_event(pygame.K_a))
        assert overlay.system.current_step is TutorialStep.WELCOME

    def test_mouse_click_does_not_advance(self, overlay):
        event = MagicMock()
        event.type = pygame.MOUSEBUTTONDOWN
        event.button = 1
        overlay.handle_input(event)
        assert overlay.system.current_step is TutorialStep.WELCOME

    def test_input_ignored_after_skip(self, overlay):
        overlay.handle_input(_key_event(pygame.K_ESCAPE))
        overlay.handle_input(_key_event(pygame.K_SPACE))
        assert overlay.system.current_step is TutorialStep.TUTORIAL_COMPLETE


class TestTutorialStateManagement:
    def test_toggle_controls_visibility(self, overlay):
        assert overlay.visible is True
        overlay.toggle()
        assert overlay.visible is False
        overlay.toggle()
        assert overlay.visible is True

    def test_hide_then_show(self, overlay):
        overlay.hide()
        assert overlay.visible is False
        overlay.show()
        assert overlay.visible is True

    def test_reset_restores_first_step(self, overlay):
        overlay.handle_input(_key_event(pygame.K_SPACE))
        overlay.system.reset()
        assert overlay.system.current_step is TutorialStep.WELCOME

    def test_render_does_not_crash(self, overlay):
        surface = pygame.Surface((1280, 720))
        overlay.render(surface)


class TestTutorialHintSystem:
    def test_show_contextual_hint_sets_text(self):
        hints = TutorialHintSystem()
        hints.show_hint("los", "Hold Ctrl to see enemy line of sight")
        assert hints._current_hint == "Hold Ctrl to see enemy line of sight"

    def test_hint_expires_after_duration(self):
        hints = TutorialHintSystem()
        hints.show_hint("los", "Hold Ctrl")
        hints.update(6.0)
        assert hints._current_hint is None

    def test_hint_renders_when_active(self):
        hints = TutorialHintSystem()
        hints.show_hint("los", "Hold Ctrl")
        surface = pygame.Surface((1280, 720))
        hints.draw(surface)

    def test_hint_render_skips_when_expired(self):
        hints = TutorialHintSystem()
        hints.update(1.0)
        surface = pygame.Surface((1280, 720))
        hints.draw(surface)


class TestTutorialWiringWithGameLoopContract:
    def test_overlay_matches_protocol_members(self):
        overlay = TutorialOverlay()
        for member in ("visible", "toggle", "handle_input", "update", "render"):
            assert hasattr(overlay, member)

    def test_system_owns_progress(self):
        assert isinstance(TutorialOverlay().system, TutorialSystem)
