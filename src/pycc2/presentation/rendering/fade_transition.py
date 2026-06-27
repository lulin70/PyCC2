"""Fade Transition Utility

Lightweight alpha-based fade-in/fade-out manager for UI panels.
Provides smooth show/hide transitions instead of instant pop-in/pop-out.
"""

import logging

logger = logging.getLogger(__name__)


class FadeTransition:
    """Simple alpha-based fade transition for UI panels.

    Manages a floating-point alpha value (0.0 = fully hidden, 1.0 = fully visible)
    that linearly interpolates toward a target alpha each frame via update(dt).
    """

    def __init__(self, fade_duration: float = 0.2):
        self._alpha: float = 0.0
        self._target_alpha: float = 0.0
        self._fade_duration = fade_duration
        self._visible: bool = False

    def show(self) -> None:
        """Start fade-in."""
        self._visible = True
        self._target_alpha = 1.0

    def hide(self) -> None:
        """Start fade-out."""
        self._target_alpha = 0.0

    @property
    def is_visible(self) -> bool:
        return self._visible and self._alpha > 0.01

    @property
    def alpha(self) -> float:
        return self._alpha

    @property
    def is_fading(self) -> bool:
        return abs(self._alpha - self._target_alpha) > 0.01

    def update(self, dt: float) -> None:
        speed = 1.0 / max(0.001, self._fade_duration)
        if self._alpha < self._target_alpha:
            self._alpha = min(self._target_alpha, self._alpha + speed * dt)
        elif self._alpha > self._target_alpha:
            self._alpha = max(self._target_alpha, self._alpha - speed * dt)
        if self._alpha <= 0.01 and self._target_alpha <= 0.01:
            self._visible = False
            self._alpha = 0.0

    def reset(self, visible: bool = False) -> None:
        """Reset to a known state (skip animation)."""
        if visible:
            self._alpha = 1.0
            self._target_alpha = 1.0
            self._visible = True
        else:
            self._alpha = 0.0
            self._target_alpha = 0.0
            self._visible = False
