"""V-06 (Wave D2): Easing functions for micro-animations.

Pure mathematical functions that map a normalized time t ∈ [0, 1] to a
progress value ∈ [0, 1] with non-linear curves, providing natural motion.

Wave B-rev P1 fix:
  - click 缩放时长 120-150ms (not 100ms, perceivable but not sluggish)
  - ease_out_cubic replaces linear (fast peak, slow return = natural motion)

Easing function selection (industry standard):
  - ease_out_cubic: click feedback, error flash (decelerating)
  - ease_in_out_sine: selection pulse, hover gradient (smooth S-curve)
  - ease_in_out_cubic: button hover (accelerating then decelerating)
  - ease_in_cubic: exit animations (accelerating away)
  - ease_out_back: bouncy entrance (slight overshoot)
  - linear: progress bars only (mechanical, avoid for organic motion)
"""

from __future__ import annotations

import math

# Twoπ constant for trigonomic easing (avoid repeated math.pi lookups)
_TAU: float = 2.0 * math.pi


# ---------------------------------------------------------------------------
# Cubic family (most common for UI micro-animations)
# ---------------------------------------------------------------------------


def ease_out_cubic(t: float) -> float:
    """Decelerating curve: fast start, slow end.

    Industry standard for click feedback and error flashes.
    Produces natural motion (object arrives gently at rest position).

    Args:
        t: Normalized time in [0, 1]. Values outside range are clamped.

    Returns:
        Eased progress in [0, 1].

    Examples:
        >>> ease_out_cubic(0.0)
        0.0
        >>> ease_out_cubic(0.5)
        0.875
        >>> ease_out_cubic(1.0)
        1.0
    """
    t = _clamp(t)
    return 1.0 - (1.0 - t) ** 3


def ease_in_cubic(t: float) -> float:
    """Accelerating curve: slow start, fast end.

    Suitable for exit animations (object accelerates away).

    Args:
        t: Normalized time in [0, 1]. Values outside range are clamped.

    Returns:
        Eased progress in [0, 1].
    """
    t = _clamp(t)
    return t**3


def ease_in_out_cubic(t: float) -> float:
    """Accelerating then decelerating (S-curve).

    Suitable for button hover (smooth transition both ways).

    Args:
        t: Normalized time in [0, 1]. Values outside range are clamped.

    Returns:
        Eased progress in [0, 1].

    Examples:
        >>> ease_in_out_cubic(0.0)
        0.0
        >>> ease_in_out_cubic(0.5)
        0.5
        >>> ease_in_out_cubic(1.0)
        1.0
    """
    t = _clamp(t)
    if t < 0.5:
        return 4.0 * t**3
    return 1.0 - ((-2.0 * t + 2.0) ** 3) / 2.0


# ---------------------------------------------------------------------------
# Sine family (smoothest, suitable for pulses)
# ---------------------------------------------------------------------------


def ease_in_out_sine(t: float) -> float:
    """Smooth S-curve using sine (no acceleration spikes).

    Ideal for selection pulse animations and hover color gradients.
    Smoother than cubic family (continuous first derivative).

    Args:
        t: Normalized time in [0, 1]. Values outside range are clamped.

    Returns:
        Eased progress in [0, 1].

    Examples:
        >>> ease_in_out_sine(0.0)
        0.0
        >>> ease_in_out_sine(0.5)
        0.5
        >>> ease_in_out_sine(1.0)
        1.0
    """
    t = _clamp(t)
    return -(math.cos(math.pi * t) - 1.0) / 2.0


def ease_out_sine(t: float) -> float:
    """Decelerating sine curve (gentle ease-out).

    Args:
        t: Normalized time in [0, 1]. Values outside range are clamped.

    Returns:
        Eased progress in [0, 1].
    """
    t = _clamp(t)
    return math.sin((t * math.pi) / 2.0)


def ease_in_sine(t: float) -> float:
    """Accelerating sine curve (gentle ease-in).

    Args:
        t: Normalized time in [0, 1]. Values outside range are clamped.

    Returns:
        Eased progress in [0, 1].
    """
    t = _clamp(t)
    return 1.0 - math.cos((t * math.pi) / 2.0)


# ---------------------------------------------------------------------------
# Back family (bouncy, with overshoot)
# ---------------------------------------------------------------------------

# Default overshoot constant for ease_out_back (industry standard)
_BACK_OVERSHOOT: float = 1.70158


def ease_out_back(t: float, s: float = _BACK_OVERSHOOT) -> float:
    """Bouncy decelerating curve with slight overshoot.

    Suitable for entrance animations (object arrives with bounce).

    Args:
        t: Normalized time in [0, 1]. Values outside range are clamped.
        s: Overshoot magnitude (default 1.70158 = industry standard).

    Returns:
        Eased progress (may slightly exceed 1.0 due to overshoot).
    """
    t = _clamp(t)
    return 1.0 + (s + 1.0) * (t - 1.0) ** 3 + s * (t - 1.0) ** 2


# ---------------------------------------------------------------------------
# Linear (baseline, use sparingly)
# ---------------------------------------------------------------------------


def linear(t: float) -> float:
    """Linear interpolation (no easing).

    Use ONLY for progress bars and mechanical indicators.
    Avoid for organic motion (looks robotic).

    Args:
        t: Normalized time in [0, 1]. Values outside range are clamped.

    Returns:
        Progress in [0, 1] (identity function on clamped input).
    """
    return _clamp(t)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _clamp(t: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Clamp value to [min_val, max_val] range.

    Args:
        t: Value to clamp.
        min_val: Minimum allowed value.
        max_val: Maximum allowed value.

    Returns:
        Clamped value.
    """
    if t < min_val:
        return min_val
    if t > max_val:
        return max_val
    return t


__all__ = [
    "ease_in_cubic",
    "ease_in_out_cubic",
    "ease_in_out_sine",
    "ease_in_sine",
    "ease_out_back",
    "ease_out_cubic",
    "ease_out_sine",
    "linear",
]
