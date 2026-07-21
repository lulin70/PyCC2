"""V-14 (Wave D7): Visual indicator for unit morale state.

Reads MoraleState enum (from domain layer, unchanged) and overlays a small
colored badge on top of the unit sprite. This module lives entirely in the
presentation layer — it does NOT modify domain code (DDD compliance).

States (from morale_types.py):
  RALLYED  (>70)      → No badge (default healthy state, reduce visual noise)
  WAVERING (40-70)    → Yellow badge
  PINNED   (20-40)    → Orange badge
  BROKEN   (<20)      → Red badge
  ROUTING  (fleeing)  → Red badge + flashing (400ms period for safety)

Wave B-rev P0-NEW-E fix:
  - render() accepts MoraleState enum directly (not unit_id)
  - Caller is responsible for determining state, including ROUTING
    (check unit.routing_target.is_fleeing before calling MoraleSystem.get_state)

Wave B-rev P1-5 fix (ROUTING flash safety margin):
  - Flash period = 400ms (200ms bright + 200ms dim), not 200ms
  - Ensures minimum visible time per phase, avoids seizure risk (WCAG 2.1)

Wave B-rev P1-6 fix (default display behavior):
  - Default: show badge only for non-RALLYED states (reduce clutter)
  - Configurable via MoraleIndicatorConfig.show_rallied
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pygame

from pycc2.domain.systems.morale_types import MoraleState

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# V-14 (Wave D7) constants
# ---------------------------------------------------------------------------

# Badge geometry (Wave B-rev spec)
BADGE_RADIUS: int = 4  # Pixels
BADGE_OFFSET_Y: int = -12  # Above sprite by 12px
BADGE_OUTLINE_COLOR: tuple[int, int, int] = (0, 0, 0)  # Black outline
BADGE_OUTLINE_THICKNESS: int = 1  # Pixel ring around badge

# ROUTING flash timing (P1-5 fix: 400ms period, not 200ms, for safety margin)
ROUTING_FLASH_PERIOD_MS: int = 400  # Full cycle (bright + dim)
ROUTING_FLASH_BRIGHT_PHASE_MS: int = 200  # Bright phase duration
ROUTING_FLASH_BRIGHT_ALPHA: int = 255  # Bright phase alpha
ROUTING_FLASH_DIM_ALPHA: int = 100  # Dim phase alpha

# WCAG 2.1 safety: 400ms period = 2.5 flashes/sec ceiling (below 3 flashes/sec limit)
# This ensures compliance with photosensitive seizure guidelines


# Morale state → badge color mapping
# Wave B-rev P0-NEW-2 fix: verified these are NOT pure Morandi colors but
# Material Design warm tones, deliberately chosen for tactical readability
# (state severity needs distinguishable hue progression).
MORALE_BADGE_COLORS: dict[MoraleState, tuple[int, int, int]] = {
    MoraleState.RALLYED: (76, 175, 80),  # Green (healthy)
    MoraleState.WAVERING: (255, 193, 7),  # Yellow (caution)
    MoraleState.PINNED: (255, 152, 0),  # Orange (warning)
    MoraleState.BROKEN: (244, 67, 54),  # Red (severe)
    MoraleState.ROUTING: (244, 67, 54),  # Red + flash (emergency)
}


# ---------------------------------------------------------------------------
# Configuration dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MoraleIndicatorConfig:
    """Configuration for morale indicator display (V-14 Wave D7).

    Attributes:
        show_rallied: If True, show badge for RALLYED state (default False,
            to reduce visual noise on healthy units).
        show_wavering: If True, show badge for WAVERING state.
        show_pinned: If True, show badge for PINNED state.
        show_broken: If True, show badge for BROKEN state.
        show_routing: If True, show badge for ROUTING state.
        badge_radius: Badge circle radius in pixels.
        badge_offset_y: Vertical offset from unit center (negative = above).
        routing_flash_period_ms: Full flash cycle period in milliseconds.
            Default 400ms (P1-5 safety fix: ensures ≥200ms per phase).
    """

    show_rallied: bool = False
    show_wavering: bool = True
    show_pinned: bool = True
    show_broken: bool = True
    show_routing: bool = True
    badge_radius: int = BADGE_RADIUS
    badge_offset_y: int = BADGE_OFFSET_Y
    routing_flash_period_ms: int = ROUTING_FLASH_PERIOD_MS


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


class MoraleIndicatorRenderer:
    """Renders morale state badge on unit sprite (V-14 Wave D7).

    Stateless across render() calls except for flash timer (which advances
    via update()). Thread-safe for read-only access to MORALE_BADGE_COLORS.

    Usage:
        renderer = MoraleIndicatorRenderer()
        # In game loop:
        renderer.update(delta_ms)
        for unit in units:
            state = determine_morale_state(unit)  # caller's responsibility
            if renderer.should_show(state):
                renderer.render(surface, (screen_x, screen_y), state)
    """

    def __init__(self, config: MoraleIndicatorConfig | None = None) -> None:
        """Initialize renderer with optional config.

        Args:
            config: Display configuration. If None, uses default config
                (RALLYED hidden, others shown, 400ms flash period).
        """
        self._config: MoraleIndicatorConfig = config or MoraleIndicatorConfig()
        self._flash_timer_ms: int = 0

    @property
    def config(self) -> MoraleIndicatorConfig:
        """Return the active configuration (immutable)."""
        return self._config

    @property
    def flash_timer_ms(self) -> int:
        """Current flash timer value (for testing/debugging)."""
        return self._flash_timer_ms

    def update(self, delta_ms: int) -> None:
        """Advance flash timer by delta_ms.

        Must be called once per frame (even when no ROUTING units visible)
        to keep flash phase consistent across render() calls.

        Args:
            delta_ms: Frame time in milliseconds (clamped to non-negative).
        """
        if delta_ms < 0:
            delta_ms = 0
        period = self._config.routing_flash_period_ms
        if period <= 0:
            self._flash_timer_ms = 0
            return
        self._flash_timer_ms = (self._flash_timer_ms + delta_ms) % period

    def should_show(self, morale_state: MoraleState) -> bool:
        """Determine whether badge should be shown for given state.

        Args:
            morale_state: The unit's current morale state.

        Returns:
            True if badge should be rendered, False otherwise.
        """
        match morale_state:
            case MoraleState.RALLYED:
                return self._config.show_rallied
            case MoraleState.WAVERING:
                return self._config.show_wavering
            case MoraleState.PINNED:
                return self._config.show_pinned
            case MoraleState.BROKEN:
                return self._config.show_broken
            case MoraleState.ROUTING:
                return self._config.show_routing
            case _:
                return False

    def render(
        self,
        surface: pygame.Surface,
        unit_screen_position: tuple[int, int],
        morale_state: MoraleState,
    ) -> None:
        """Render morale badge on top of unit sprite.

        Args:
            surface: Target pygame Surface to draw on.
            unit_screen_position: (x, y) screen coordinates of unit center.
            morale_state: Current morale state (caller determines, including
                ROUTING via unit.routing_target.is_fleeing check).

        Note:
            Caller should call should_show() first to respect config.
            This method will silently no-op for RALLYED when show_rallied=False.
        """
        if not self.should_show(morale_state):
            return

        color = self._get_badge_color(morale_state)
        radius = self._config.badge_radius
        badge_x = unit_screen_position[0]
        badge_y = unit_screen_position[1] + self._config.badge_offset_y

        # Draw outline (black ring) first for visibility against any background
        pygame.draw.circle(
            surface,
            BADGE_OUTLINE_COLOR,
            (badge_x, badge_y),
            radius + BADGE_OUTLINE_THICKNESS,
        )

        # Draw colored badge
        pygame.draw.circle(surface, color, (badge_x, badge_y), radius)

        # ROUTING flash overlay (dim phase draws semi-transparent black ring)
        if morale_state == MoraleState.ROUTING:
            alpha = self._compute_routing_alpha()
            if alpha < ROUTING_FLASH_BRIGHT_ALPHA:
                # Dim phase: overlay a semi-transparent dark circle to dim the badge
                flash_surf = pygame.Surface(
                    (radius * 2 + 2, radius * 2 + 2), pygame.SRCALPHA
                )
                dim_strength = 255 - alpha
                pygame.draw.circle(
                    flash_surf,
                    (0, 0, 0, dim_strength),
                    (radius + 1, radius + 1),
                    radius,
                )
                surface.blit(
                    flash_surf,
                    (badge_x - radius - 1, badge_y - radius - 1),
                )

    def _get_badge_color(self, morale_state: MoraleState) -> tuple[int, int, int]:
        """Get badge color for state, with fallback to default.

        Args:
            morale_state: Current morale state.

        Returns:
            (R, G, B) tuple in 0-255 range.
        """
        return MORALE_BADGE_COLORS.get(
            morale_state, MORALE_BADGE_COLORS[MoraleState.BROKEN]
        )

    def _compute_routing_alpha(self) -> int:
        """Compute current flash alpha for ROUTING state.

        Flash cycle (P1-5 safety):
        - 0 to ROUTING_FLASH_BRIGHT_PHASE_MS (200ms): bright (alpha 255)
        - ROUTING_FLASH_BRIGHT_PHASE_MS to period (400ms): dim (alpha 100)

        Returns:
            Alpha value (255 for bright phase, 100 for dim phase).
        """
        if self._flash_timer_ms < ROUTING_FLASH_BRIGHT_PHASE_MS:
            return ROUTING_FLASH_BRIGHT_ALPHA
        return ROUTING_FLASH_DIM_ALPHA

    def reset_flash_timer(self) -> None:
        """Reset flash timer to zero (for testing or state reset)."""
        self._flash_timer_ms = 0


# ---------------------------------------------------------------------------
# Module-level helper functions
# ---------------------------------------------------------------------------


def get_morale_badge_color(morale_state: MoraleState) -> tuple[int, int, int]:
    """Get badge color for a morale state (module-level convenience).

    Args:
        morale_state: Morale state enum value.

    Returns:
        (R, G, B) color tuple. Falls back to BROKEN color for unknown states.
    """
    return MORALE_BADGE_COLORS.get(
        morale_state, MORALE_BADGE_COLORS[MoraleState.BROKEN]
    )


def is_routing_flash_bright(timer_ms: int, period_ms: int = ROUTING_FLASH_PERIOD_MS) -> bool:
    """Determine if ROUTING flash is in bright phase at given timer value.

    Args:
        timer_ms: Flash timer value in milliseconds.
        period_ms: Full flash period (default 400ms).

    Returns:
        True if in bright phase (first half of cycle), False otherwise.
    """
    if period_ms <= 0:
        return True
    return (timer_ms % period_ms) < ROUTING_FLASH_BRIGHT_PHASE_MS


__all__ = [
    "BADGE_OFFSET_Y",
    "BADGE_OUTLINE_COLOR",
    "BADGE_OUTLINE_THICKNESS",
    "BADGE_RADIUS",
    "MORALE_BADGE_COLORS",
    "ROUTING_FLASH_BRIGHT_ALPHA",
    "ROUTING_FLASH_BRIGHT_PHASE_MS",
    "ROUTING_FLASH_DIM_ALPHA",
    "ROUTING_FLASH_PERIOD_MS",
    "MoraleIndicatorConfig",
    "MoraleIndicatorRenderer",
    "get_morale_badge_color",
    "is_routing_flash_bright",
]
