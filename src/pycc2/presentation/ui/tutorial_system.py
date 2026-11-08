"""Tutorial System - New player onboarding and guidance.

Provides:
- Step-by-step tutorial overlays
- Contextual hints for game mechanics
- Progressive feature unlocking
- Tutorial completion tracking
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable

import pygame


class TutorialStep(Enum):
    """Tutorial progression steps."""

    # Basic Controls
    WELCOME = auto()
    CAMERA_MOVEMENT = auto()
    UNIT_SELECTION = auto()
    UNIT_MOVEMENT = auto()

    # CC2 Core Mechanics
    LINE_OF_SIGHT = auto()
    COMBAT_BASICS = auto()
    SUPPRESSION = auto()
    VICTORY_OBJECTIVES = auto()

    # Advanced
    HOTKEYS_INTRO = auto()
    TUTORIAL_COMPLETE = auto()


@dataclass
class TutorialMessage:
    """Tutorial message displayed to player."""

    title: str
    content: str
    position: tuple[int, int]  # Screen position (x, y)
    highlight_rect: pygame.Rect | None = None  # Optional UI element to highlight
    completion_check: Callable[[], bool] | None = None  # Function to check if step completed


class TutorialSystem:
    """Manages tutorial progression and hints."""

    def __init__(self) -> None:
        """Initialize tutorial system."""
        self.enabled = True
        self.current_step = TutorialStep.WELCOME
        self.completed_steps: set[TutorialStep] = set()
        self._messages = self._initialize_messages()
        self._font = pygame.font.Font(None, 28)
        self._title_font = pygame.font.Font(None, 36)

    def _initialize_messages(self) -> dict[TutorialStep, TutorialMessage]:
        """Initialize tutorial messages for each step."""
        return {
            TutorialStep.WELCOME: TutorialMessage(
                title="Welcome to PyCC2!",
                content="This tutorial will teach you the basics.\nPress SPACE to continue.",
                position=(400, 300),
            ),
            TutorialStep.CAMERA_MOVEMENT: TutorialMessage(
                title="Camera Movement",
                content="Use WASD or Arrow keys to move the camera.\nTry moving the camera now!",
                position=(50, 50),
            ),
            TutorialStep.UNIT_SELECTION: TutorialMessage(
                title="Unit Selection",
                content="Click on a unit to select it.\nOr drag a box to select multiple units.",
                position=(50, 50),
            ),
            TutorialStep.UNIT_MOVEMENT: TutorialMessage(
                title="Unit Movement",
                content="Right-click on the map to move selected units.\nTry moving your unit now!",
                position=(50, 50),
            ),
            TutorialStep.LINE_OF_SIGHT: TutorialMessage(
                title="Line of Sight",
                content="Hold Ctrl to see what each unit can see.\nTerrain and buildings block line of sight.",
                position=(50, 50),
            ),
            TutorialStep.COMBAT_BASICS: TutorialMessage(
                title="Combat",
                content="Right-click an enemy in line of sight to fire.\nCover and range affect the result.",
                position=(50, 50),
            ),
            TutorialStep.SUPPRESSION: TutorialMessage(
                title="Morale and Suppression",
                content="Heavy fire suppresses a unit.\nA suppressed unit moves slower and shoots worse.",
                position=(50, 50),
            ),
            TutorialStep.VICTORY_OBJECTIVES: TutorialMessage(
                title="Victory Conditions",
                content="Capture the victory locations marked by flags.\nHold them until the timer ends to win.",
                position=(50, 50),
            ),
            TutorialStep.HOTKEYS_INTRO: TutorialMessage(
                title="Keyboard Shortcuts",
                content="Press Ctrl+1-9 to create control groups.\nPress 1-9 to select control groups quickly!",
                position=(50, 50),
            ),
            TutorialStep.TUTORIAL_COMPLETE: TutorialMessage(
                title="Tutorial Complete!",
                content="You've learned the basics of PyCC2!\nPress ESC to disable tutorial hints anytime.",
                position=(400, 300),
            ),
        }

    def advance_step(self) -> None:
        """Advance to next tutorial step."""
        if not self.enabled:
            return

        self.completed_steps.add(self.current_step)

        # Get next step
        steps = list(TutorialStep)
        current_idx = steps.index(self.current_step)
        if current_idx < len(steps) - 1:
            self.current_step = steps[current_idx + 1]
        else:
            self.enabled = False

    def skip_tutorial(self) -> None:
        """Skip tutorial entirely."""
        self.enabled = False
        self.current_step = TutorialStep.TUTORIAL_COMPLETE

    def reset(self) -> None:
        """Reset tutorial to beginning."""
        self.enabled = True
        self.current_step = TutorialStep.WELCOME
        self.completed_steps.clear()

    def update(self, events: list[pygame.event.Event]) -> None:
        """Update tutorial system.

        Args:
            events: Pygame events to process
        """
        if not self.enabled:
            return

        # Check for SPACE key to advance
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.advance_step()
                elif event.key == pygame.K_ESCAPE:
                    self.skip_tutorial()

    def draw(self, surface: pygame.Surface) -> None:
        """Draw current tutorial message.

        Args:
            surface: Pygame surface to draw on
        """
        if not self.enabled or self.current_step not in self._messages:
            return

        message = self._messages[self.current_step]

        # Draw semi-transparent overlay
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))

        # Draw message box
        box_width, box_height = 700, 300
        box_x = (surface.get_width() - box_width) // 2
        box_y = (surface.get_height() - box_height) // 2

        pygame.draw.rect(
            surface, (40, 40, 60), (box_x, box_y, box_width, box_height), border_radius=10
        )
        pygame.draw.rect(
            surface, (100, 150, 255), (box_x, box_y, box_width, box_height), 3, border_radius=10
        )

        # Draw title
        title_surf = self._title_font.render(message.title, True, (255, 255, 100))
        title_rect = title_surf.get_rect(centerx=surface.get_width() // 2, top=box_y + 30)
        surface.blit(title_surf, title_rect)

        # Draw content (multi-line)
        content_lines = message.content.split("\n")
        y_offset = box_y + 100
        for line in content_lines:
            line_surf = self._font.render(line, True, (255, 255, 255))
            line_rect = line_surf.get_rect(centerx=surface.get_width() // 2, top=y_offset)
            surface.blit(line_surf, line_rect)
            y_offset += 40

        # Draw highlight rect if provided
        if message.highlight_rect:
            pygame.draw.rect(surface, (255, 255, 0), message.highlight_rect, 3)

        # Draw progress indicator
        progress_text = f"Step {list(TutorialStep).index(self.current_step) + 1} of {len(TutorialStep)}"
        progress_surf = self._font.render(progress_text, True, (180, 180, 180))
        progress_rect = progress_surf.get_rect(
            centerx=surface.get_width() // 2, bottom=box_y + box_height - 20
        )
        surface.blit(progress_surf, progress_rect)


class TutorialHintSystem:
    """Contextual hint system for advanced features."""

    def __init__(self) -> None:
        """Initialize hint system."""
        self.hints_shown: set[str] = set()
        self._hint_duration = 5.0  # Show hints for 5 seconds
        self._current_hint: str | None = None
        self._hint_timer = 0.0
        self._font = pygame.font.Font(None, 24)

    def show_hint(self, hint_id: str, hint_text: str) -> None:
        """Show a contextual hint.

        Args:
            hint_id: Unique identifier for this hint
            hint_text: Text to display
        """
        if hint_id in self.hints_shown:
            return

        self._current_hint = hint_text
        self._hint_timer = self._hint_duration
        self.hints_shown.add(hint_id)

    def update(self, dt: float) -> None:
        """Update hint timer.

        Args:
            dt: Delta time in seconds
        """
        if self._hint_timer > 0:
            self._hint_timer -= dt
            if self._hint_timer <= 0:
                self._current_hint = None

    def draw(self, surface: pygame.Surface) -> None:
        """Draw current hint.

        Args:
            surface: Pygame surface to draw on
        """
        if not self._current_hint:
            return

        # Draw hint at bottom of screen
        hint_surf = self._font.render(f"💡 Hint: {self._current_hint}", True, (255, 255, 100))
        hint_rect = hint_surf.get_rect(centerx=surface.get_width() // 2, bottom=surface.get_height() - 20)

        # Draw background
        bg_rect = hint_rect.inflate(20, 10)
        pygame.draw.rect(surface, (40, 40, 40, 200), bg_rect, border_radius=5)
        surface.blit(hint_surf, hint_rect)


class TutorialOverlay:
    """Adapter that exposes TutorialSystem through the ITutorialOverlay protocol.

    GameLoop and EventDispatcher depend on the protocol (visible / toggle /
    handle_input / update / render). TutorialSystem owns the content and the
    progression rules. This class only forwards calls.
    """

    def __init__(self, display_config=None) -> None:
        """Initialize the overlay.

        Args:
            display_config: Optional DisplayConfig. Kept for call-site
                compatibility; the tutorial does not read display settings.
        """
        self._display_config = display_config
        self._system = TutorialSystem()
        self._visible = True

    @property
    def visible(self) -> bool:
        """Return True when the overlay accepts input and draws."""
        return self._visible and self._system.enabled

    @property
    def system(self) -> TutorialSystem:
        """Return the wrapped tutorial system."""
        return self._system

    def toggle(self) -> None:
        """Show or hide the overlay."""
        self._visible = not self._visible

    def show(self) -> None:
        """Show the overlay."""
        self._visible = True

    def hide(self) -> None:
        """Hide the overlay."""
        self._visible = False

    def handle_input(self, event) -> str | None:
        """Forward one input event to the tutorial system.

        Returns:
            None. The tutorial does not emit command strings.
        """
        if not self.visible:
            return None
        self._system.update([event])
        return None

    def update(self) -> None:
        """Sync visibility. The system has no per-frame timer."""
        if not self._system.enabled:
            self._visible = False

    def render(self, screen) -> None:
        """Draw the current tutorial message."""
        if self.visible and screen is not None:
            self._system.draw(screen)
