"""Suppression overlay renderer.

Extracted from EnhancedRenderer / ScreenEffectsRenderer to isolate:
- Morale-based suppression alpha calculation
- Red-edge vignette overlay rendering
- Cached overlay surface management

Dependencies are injected via constructor; no RenderContext coupling required.
"""

from __future__ import annotations

import logging
from typing import Any

import pygame

logger = logging.getLogger(__name__)


class SuppressionOverlayRenderer:
    """Renders the red-edge suppression overlay for pinned/broken player units."""

    MAX_ALPHA: float = 80.0
    DECAY: float = 120.0
    RAMP: float = 200.0
    BASE_ALPHA: float = 30.0
    PER_UNIT_ALPHA: float = 20.0

    def __init__(self) -> None:
        self._overlay_cache: pygame.Surface | None = None
        self._alpha: float = 0.0

    def update(self, dt: float, units: list[Any] | None = None) -> None:
        """Update suppression overlay alpha based on player unit morale states."""
        from pycc2.domain.systems.morale_system import MoraleState, MoraleSystem

        suppressed_count = 0
        if units is not None:
            for unit in units:
                if not getattr(unit, "is_alive", True):
                    continue
                if hasattr(unit, "side") and unit.side not in ("allies", "ally"):
                    continue
                morale = getattr(unit, "morale", None)
                if morale is not None:
                    morale_state = MoraleSystem.get_state(morale.value)
                    if morale_state in (MoraleState.PINNED, MoraleState.BROKEN):
                        suppressed_count += 1

        if suppressed_count > 0:
            target_alpha = min(
                self.MAX_ALPHA,
                self.BASE_ALPHA + suppressed_count * self.PER_UNIT_ALPHA,
            )
            self._alpha = min(target_alpha, self._alpha + self.RAMP * dt)
        else:
            self._alpha = max(0.0, self._alpha - self.DECAY * dt)

    def get_alpha(self) -> float:
        """Return current suppression overlay alpha."""
        return self._alpha

    def reset(self) -> None:
        """Reset suppression alpha to zero."""
        self._alpha = 0.0

    def render(
        self,
        offscreen: pygame.Surface | None,
        dirty_tracker: Any | None = None,
    ) -> None:
        """Render semi-transparent red edge overlay for suppression feedback."""
        if offscreen is None:
            return

        alpha = int(max(0, min(255, self._alpha)))
        if alpha < 2:
            return

        if dirty_tracker is not None:
            dirty_tracker.mark_full_dirty()

        sw, sh = offscreen.get_size()
        if (
            self._overlay_cache is None
            or self._overlay_cache.get_size() != (sw, sh)
        ):
            self._overlay_cache = pygame.Surface((sw, sh), pygame.SRCALPHA)

        overlay = self._overlay_cache
        overlay.fill((0, 0, 0, 0))

        edge_width = min(60, sw // 6)
        edge_height = min(60, sh // 6)
        red = (200, 30, 30)

        # Top edge
        for i in range(edge_height):
            a = int(alpha * (1.0 - i / edge_height))
            if a < 1:
                break
            pygame.draw.line(overlay, (*red, a), (0, i), (sw, i))

        # Bottom edge
        for i in range(edge_height):
            a = int(alpha * (1.0 - i / edge_height))
            if a < 1:
                break
            y = sh - 1 - i
            pygame.draw.line(overlay, (*red, a), (0, y), (sw, y))

        # Left edge
        for i in range(edge_width):
            a = int(alpha * (1.0 - i / edge_width))
            if a < 1:
                break
            pygame.draw.line(overlay, (*red, a), (i, 0), (i, sh))

        # Right edge
        for i in range(edge_width):
            a = int(alpha * (1.0 - i / edge_width))
            if a < 1:
                break
            x = sw - 1 - i
            pygame.draw.line(overlay, (*red, a), (x, 0), (x, sh))

        offscreen.blit(overlay, (0, 0))

    def invalidate_cache(self) -> None:
        """Clear cached overlay surface when screen size changes."""
        self._overlay_cache = None
