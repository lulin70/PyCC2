"""Tutorial system tests for the CC2 tutorial flow."""

from __future__ import annotations

from unittest.mock import MagicMock

import pygame
import pytest

from pycc2.presentation.ui.tutorial_system import (
    TutorialHintSystem,
    TutorialOverlay,
    TutorialStep,
    TutorialSystem,
)


@pytest.fixture(autouse=True)
def _pygame_init():
    """Initialize pygame for font and surface operations."""
    pygame.init()
    yield


def _key_event(key: int) -> MagicMock:
    event = MagicMock()
    event.type = pygame.KEYDOWN
    event.key = key
    return event


class TestTutorialSteps:
    def test_steps_are_cc2_only(self):
        """The step list must not contain deleted RTS mechanics."""
        names = {step.name for step in TutorialStep}
        assert "RESOURCE_COLLECTION" not in names
        assert "BUILDING_PLACEMENT" not in names
        assert "UNIT_TRAINING" not in names

    def test_core_cc2_steps_present(self):
        names = {step.name for step in TutorialStep}
        for required in (
            "LINE_OF_SIGHT",
            "COMBAT_BASICS",
            "SUPPRESSION",
            "VICTORY_OBJECTIVES",
        ):
            assert required in names

    def test_every_step_has_a_message(self):
        system = TutorialSystem()
        for step in TutorialStep:
            assert step in system._messages, f"Missing message for {step}"


class TestTutorialSystem:
    def test_starts_at_welcome(self):
        system = TutorialSystem()
        assert system.current_step is TutorialStep.WELCOME
        assert system.enabled is True

    def test_space_advances_step(self):
        system = TutorialSystem()
        system.update([_key_event(pygame.K_SPACE)])
        assert system.current_step is TutorialStep.CAMERA_MOVEMENT

    def test_escape_skips_tutorial(self):
        system = TutorialSystem()
        system.update([_key_event(pygame.K_ESCAPE)])
        assert system.enabled is False

    def test_advance_marks_completed(self):
        system = TutorialSystem()
        system.advance_step()
        assert TutorialStep.WELCOME in system.completed_steps

    def test_advancing_last_step_disables(self):
        system = TutorialSystem()
        for _ in range(len(TutorialStep)):
            system.advance_step()
        assert system.enabled is False

    def test_reset_restores_beginning(self):
        system = TutorialSystem()
        system.skip_tutorial()
        system.reset()
        assert system.enabled is True
        assert system.current_step is TutorialStep.WELCOME
        assert system.completed_steps == set()

    def test_draw_writes_pixels(self):
        surface = pygame.Surface((800, 600))
        TutorialSystem().draw(surface)
        assert surface.get_at((400, 300))[:3] != (0, 0, 0)


class TestTutorialOverlayAdapter:
    def test_visible_by_default(self):
        overlay = TutorialOverlay()
        assert overlay.visible is True

    def test_toggle_hides_and_shows(self):
        overlay = TutorialOverlay()
        overlay.toggle()
        assert overlay.visible is False
        overlay.toggle()
        assert overlay.visible is True

    def test_skip_makes_overlay_invisible(self):
        overlay = TutorialOverlay()
        overlay.handle_input(_key_event(pygame.K_ESCAPE))
        assert overlay.visible is False

    def test_handle_input_does_not_emit_commands(self):
        overlay = TutorialOverlay()
        assert overlay.handle_input(_key_event(pygame.K_SPACE)) is None

    def test_render_is_safe_for_none_surface(self):
        TutorialOverlay().render(None)

    def test_render_draws_when_visible(self):
        overlay = TutorialOverlay()
        surface = pygame.Surface((800, 600))
        overlay.render(surface)
        assert surface.get_at((400, 300))[:3] != (0, 0, 0)

    def test_render_skips_when_hidden(self):
        overlay = TutorialOverlay()
        overlay.hide()
        surface = pygame.Surface((800, 600))
        overlay.render(surface)
        assert surface.get_at((400, 300))[:3] == (0, 0, 0)


class TestTutorialHintSystem:
    def test_hint_shown_then_expires(self):
        hints = TutorialHintSystem()
        hints.show_hint("los", "Hold Ctrl to see line of sight")
        assert hints._current_hint is not None
        hints.update(6.0)
        assert hints._current_hint is None

    def test_hint_draw_safe_without_hint(self):
        surface = pygame.Surface((800, 600))
        TutorialHintSystem().draw(surface)
