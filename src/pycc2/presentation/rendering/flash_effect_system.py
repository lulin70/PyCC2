"""
Screen Flash Overlay Effect System for PyCC2 renderer.

Extracted from EnhancedRenderer (God Class refactoring).
Manages transient full-screen flash overlays used for visual feedback
(explosions, kills, damage events).

Responsibilities:
- Trigger flash effects with configurable color, intensity, and duration
- Update flash alpha each frame using ease-out quad curve for natural fade
- Expose current flash state for the main render loop to composite

State is fully self-contained; the render loop reads color/alpha to draw
the overlay — no direct surface dependency.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class FlashEffectSystem:
    """Transient screen flash overlay manager.

    Lifecycle:
        trigger_flash() → set color/intensity/duration
        update_flash(dt) → decay alpha each frame
        render loop reads .color / .alpha → draws overlay if active
    """

    def __init__(self) -> None:
        self._color: tuple[int, int, int] | None = None
        self._alpha: float = 0.0
        self._duration: float = 0.0
        self._elapsed: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def trigger(
        self,
        color: tuple[int, int, int] = (255, 255, 255),
        intensity: float = 0.4,
        duration: float = 0.12,
    ) -> None:
        """Trigger a screen flash overlay effect.

        Args:
            color: RGB tuple for flash color (white for explosions, red for kills).
            intensity: Peak alpha multiplier (0.0–1.0).
            duration: Flash fade-out duration in seconds.
        """
        self._color = color
        self._alpha = intensity * 255
        self._duration = duration
        self._elapsed = 0.0
        logger.debug(
            "Screen flash triggered: color=%s, intensity=%.2f, duration=%.2fs",
            color, intensity, duration,
        )

    def update(self, dt: float) -> None:
        """Update screen flash alpha (call once per frame in update phase).

        Uses ease-out quad curve for natural fade-out feel:
        alpha starts at peak and decays rapidly at first, then slows.

        Args:
            dt: Delta time in seconds since last frame.
        """
        if self._color is None:
            return
        self._elapsed += dt
        progress = min(1.0, self._elapsed / self._duration)
        # Ease-out quad fade: fast start, slow end
        self._alpha = (1.0 - (1.0 - progress) ** 2) * (-255)  # 255 → 0
        if progress >= 1.0:
            self._color = None
            self._alpha = 0.0

    # ------------------------------------------------------------------
    # Read-only properties (consumed by render loop)
    # ------------------------------------------------------------------

    @property
    def color(self) -> tuple[int, int, int] | None:
        """Current flash color, or None if no flash is active."""
        return self._color

    @property
    def alpha(self) -> float:
        """Current flash alpha value (0–255 range). Positive means active."""
        return self._alpha

    @property
    def is_active(self) -> bool:
        """Whether a flash effect is currently in progress."""
        return self._color is not None and self._alpha > 0
