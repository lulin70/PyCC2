"""
Operation Feedback Manager

Provides visual and audio feedback for user operations.
Shows confirmation messages, warnings, errors, etc.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto

import pygame
from pygame import Surface
from pygame.font import Font


class FeedbackType(Enum):
    """Types of feedback messages."""

    INFO = auto()
    SUCCESS = auto()
    WARNING = auto()
    ERROR = auto()
    COMBAT = auto()


@dataclass
class FeedbackMessage:
    """Single feedback message with lifetime."""

    text: str
    feedback_type: FeedbackType
    timestamp: float
    duration: float = 3.0
    position: tuple = (None, None)

    @property
    def is_expired(self) -> bool:
        """Check if message has exceeded its display duration."""
        return time.time() - self.timestamp > self.duration

    @property
    def remaining_time(self) -> float:
        """Get remaining display time."""
        return max(0, self.duration - (time.time() - self.timestamp))


class FeedbackManager:
    """Manages operation feedback messages."""

    def __init__(self):
        self._messages: list[FeedbackMessage] = []
        self._font: Font | None = None
        self._callbacks: dict[FeedbackType, Callable] = {}

        self._colors = {
            FeedbackType.INFO: (200, 200, 200),
            FeedbackType.SUCCESS: (80, 200, 80),
            FeedbackType.WARNING: (230, 180, 50),
            FeedbackType.ERROR: (230, 80, 80),
            FeedbackType.COMBAT: (255, 150, 50),
        }

    def initialize(self) -> None:
        """Initialize feedback system."""
        pygame.font.init()
        self._font = pygame.font.Font(None, 24)

    def show_message(
        self,
        text: str,
        feedback_type: FeedbackType = FeedbackType.INFO,
        duration: float = 3.0,
        position: tuple = (None, None),
    ) -> None:
        """Display a feedback message."""
        message = FeedbackMessage(
            text=text,
            feedback_type=feedback_type,
            timestamp=time.time(),
            duration=duration,
            position=position,
        )
        self._messages.append(message)

        callback = self._callbacks.get(feedback_type)
        if callback:
            callback(message)

    def show_info(self, text: str, **kwargs) -> None:
        """Show info message."""
        self.show_message(text, FeedbackType.INFO, **kwargs)

    def show_success(self, text: str, **kwargs) -> None:
        """Show success message."""
        self.show_message(text, FeedbackType.SUCCESS, **kwargs)

    def show_warning(self, text: str, **kwargs) -> None:
        """Show warning message."""
        self.show_message(text, FeedbackType.WARNING, **kwargs)

    def show_error(self, text: str, **kwargs) -> None:
        """Show error message."""
        self.show_message(text, FeedbackType.ERROR, **kwargs)

    def show_combat(self, text: str, **kwargs) -> None:
        """Show combat-related message."""
        self.show_message(text, FeedbackType.COMBAT, **kwargs)

    def register_callback(self, feedback_type: FeedbackType, callback: Callable) -> None:
        """Register callback for specific feedback type."""
        self._callbacks[feedback_type] = callback

    def render(self, surface: Surface) -> None:
        """Render all active feedback messages."""
        if not self._font:
            return

        self._messages = [m for m in self._messages if not m.is_expired]

        center_x = surface.get_width() // 2
        start_y = surface.get_height() // 3

        for i, message in enumerate(self._messages):
            alpha = min(1.0, message.remaining_time / 0.5)
            color = self._colors.get(message.feedback_type, (200, 200, 200))

            text_surface = self._font.render(message.text, True, color)
            text_rect = text_surface.get_rect(center=(center_x, start_y + i * 30))

            bg_padding = 10
            bg_rect = text_rect.inflate(bg_padding * 2, bg_padding)
            bg_surface = Surface(bg_rect.size, pygame.SRCALPHA)
            bg_surface.fill((0, 0, 0, int(180 * alpha)))
            surface.blit(bg_surface, bg_rect.topleft)

            surface.blit(text_surface, text_rect)

    def clear(self) -> None:
        """Clear all feedback messages."""
        self._messages.clear()

    def cleanup(self) -> None:
        """Clean up resources."""
        self._messages.clear()
