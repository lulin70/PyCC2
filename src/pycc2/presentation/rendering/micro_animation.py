"""V-06 (Wave D2): Micro-animation scheduler and controller.

Manages short-lived UI animations (hover/click/selection/error) with
configurable duration, easing function, and start/end values.

Wave B-rev P1 fix:
  - click duration: 120-150ms (golden range, perceivable but not sluggish)
  - hover duration: 200ms (smooth transition)
  - selection pulse: 1000ms (1s loop with ease_in_out_sine)
  - error flash: 300ms × 2 (with ease_out_cubic)

Design:
  - AnimationType enum: HOVER / CLICK / SELECTION_PULSE / ERROR_FLASH
  - Animation dataclass: start_time, duration_ms, easing_fn, from_val, to_val
  - MicroAnimationController: register/cancel/update animations, compute values
  - Thread-safe for single-threaded game loop (no locking needed)

File split (2026-07-21):
  This module was originally written into ``animation_system.py`` during
  Wave D2 V-06 implementation, which broke 3 dependent files
  (effect_renderer.py / sprite_renderer_base.py / particle_pool.py) that
  import the legacy UnitAnimator/ScreenShake/ParticleEmitter API from
  ``animation_system.py``. Per SRP principle, the V-06 micro-animation
  subsystem now lives in this dedicated module, and ``animation_system.py``
  was restored to its pre-V-06 state (legacy unit animation API).

Usage:
    controller = MicroAnimationController()
    controller.start("button_1", AnimationType.CLICK, duration_ms=130)
    # In render loop:
    controller.update(current_time_ms)
    scale = controller.get_value("button_1", default=1.0)
    # scale will be 0.94 → 1.0 via ease_out_cubic over 130ms
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto

from pycc2.presentation.rendering.easing import (
    ease_in_out_cubic,
    ease_in_out_sine,
    ease_out_cubic,
)

# ---------------------------------------------------------------------------
# V-06 (Wave D2) constants
# ---------------------------------------------------------------------------

# Default durations (Wave B-rev spec, in milliseconds)
DEFAULT_HOVER_DURATION_MS: int = 200
DEFAULT_CLICK_DURATION_MS: int = 130  # P1 fix: 120-150ms golden range
DEFAULT_SELECTION_PULSE_DURATION_MS: int = 1000
DEFAULT_ERROR_FLASH_DURATION_MS: int = 300

# Click animation scale range (button press feedback)
CLICK_SCALE_FROM: float = 0.94
CLICK_SCALE_TO: float = 1.0

# Hover alpha range (background gradient)
HOVER_ALPHA_FROM: float = 0.0
HOVER_ALPHA_TO: float = 1.0

# Selection pulse alpha range
SELECTION_PULSE_ALPHA_MIN: int = 100
SELECTION_PULSE_ALPHA_MAX: int = 200

# Error flash color (red)
ERROR_FLASH_COLOR: tuple[int, int, int] = (244, 67, 54)
ERROR_FLASH_MAX_ITERATIONS: int = 2  # Flash twice


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AnimationType(Enum):
    """Types of micro-animations managed by the controller."""

    HOVER = auto()  # Mouse hover over button (color/alpha gradient)
    CLICK = auto()  # Button click feedback (scale 0.94 → 1.0)
    SELECTION_PULSE = auto()  # Selection box pulse (alpha 100 → 200 → 100)
    ERROR_FLASH = auto()  # Error target flash (red blink, 2 iterations)


# ---------------------------------------------------------------------------
# Animation dataclass
# ---------------------------------------------------------------------------


# Type alias for easing function signature
EasingFn = Callable[[float], float]


@dataclass(slots=True)
class Animation:
    """A single micro-animation instance.

    Attributes:
        animation_type: Type of animation (determines default values).
        start_time_ms: Animation start time (game clock, milliseconds).
        duration_ms: Total duration in milliseconds.
        easing_fn: Easing function to apply (maps t ∈ [0,1] → progress).
        from_value: Start value (e.g., 0.94 for click scale).
        to_value: End value (e.g., 1.0 for click scale).
        iterations: Number of times to repeat (1 = single play, 2 = flash twice).
        completed: True if animation has finished (read-only via property).
    """

    animation_type: AnimationType
    start_time_ms: float
    duration_ms: int
    easing_fn: EasingFn
    from_value: float
    to_value: float
    iterations: int = 1
    _completed: bool = field(default=False, init=False)
    _current_value: float = field(default=0.0, init=False)

    @property
    def completed(self) -> bool:
        """True if animation has finished all iterations."""
        return self._completed

    def compute_progress(self, current_time_ms: float) -> float:
        """Compute eased progress at current time.

        Args:
            current_time_ms: Current game clock time in milliseconds.

        Returns:
            Eased progress value in [from_value, to_value] range.
            If animation completed, returns to_value.
        """
        elapsed_ms = current_time_ms - self.start_time_ms
        if elapsed_ms < 0:
            return self.from_value  # Not started yet

        total_duration_ms = self.duration_ms * self.iterations
        if elapsed_ms >= total_duration_ms:
            self._completed = True
            return self.to_value

        # Compute iteration progress
        iteration_index = int(elapsed_ms / self.duration_ms)
        iteration_elapsed_ms = elapsed_ms - (iteration_index * self.duration_ms)
        t = iteration_elapsed_ms / self.duration_ms if self.duration_ms > 0 else 1.0

        # Apply easing
        eased_t = self.easing_fn(t)

        # Interpolate between from and to
        return self.from_value + (self.to_value - self.from_value) * eased_t


# ---------------------------------------------------------------------------
# Animation factory functions
# ---------------------------------------------------------------------------


def create_hover_animation(
    start_time_ms: float,
    duration_ms: int = DEFAULT_HOVER_DURATION_MS,
    from_alpha: float = HOVER_ALPHA_FROM,
    to_alpha: float = HOVER_ALPHA_TO,
) -> Animation:
    """Create a hover animation (color/alpha gradient).

    Args:
        start_time_ms: Animation start time.
        duration_ms: Duration in milliseconds (default 200ms).
        from_alpha: Starting alpha (default 0.0).
        to_alpha: Ending alpha (default 1.0).

    Returns:
        Animation instance configured for hover.
    """
    return Animation(
        animation_type=AnimationType.HOVER,
        start_time_ms=start_time_ms,
        duration_ms=duration_ms,
        easing_fn=ease_in_out_cubic,
        from_value=from_alpha,
        to_value=to_alpha,
    )


def create_click_animation(
    start_time_ms: float,
    duration_ms: int = DEFAULT_CLICK_DURATION_MS,
    from_scale: float = CLICK_SCALE_FROM,
    to_scale: float = CLICK_SCALE_TO,
) -> Animation:
    """Create a click animation (scale 0.94 → 1.0).

    Args:
        start_time_ms: Animation start time.
        duration_ms: Duration in milliseconds (default 130ms, P1 golden range).
        from_scale: Starting scale (default 0.94).
        to_scale: Ending scale (default 1.0).

    Returns:
        Animation instance configured for click feedback.
    """
    return Animation(
        animation_type=AnimationType.CLICK,
        start_time_ms=start_time_ms,
        duration_ms=duration_ms,
        easing_fn=ease_out_cubic,
        from_value=from_scale,
        to_value=to_scale,
    )


def create_selection_pulse_animation(
    start_time_ms: float,
    duration_ms: int = DEFAULT_SELECTION_PULSE_DURATION_MS,
) -> Animation:
    """Create a selection pulse animation (alpha 100 → 200 → 100).

    Uses ease_in_out_sine for smooth pulse (continuous first derivative).

    Args:
        start_time_ms: Animation start time.
        duration_ms: Duration for one pulse cycle (default 1000ms).

    Returns:
        Animation instance configured for selection pulse.
    """
    return Animation(
        animation_type=AnimationType.SELECTION_PULSE,
        start_time_ms=start_time_ms,
        duration_ms=duration_ms,
        easing_fn=ease_in_out_sine,
        from_value=SELECTION_PULSE_ALPHA_MIN,
        to_value=SELECTION_PULSE_ALPHA_MAX,
    )


def create_error_flash_animation(
    start_time_ms: float,
    duration_ms: int = DEFAULT_ERROR_FLASH_DURATION_MS,
    iterations: int = ERROR_FLASH_MAX_ITERATIONS,
) -> Animation:
    """Create an error flash animation (red blink, 2 iterations).

    Args:
        start_time_ms: Animation start time.
        duration_ms: Duration per flash (default 300ms).
        iterations: Number of flashes (default 2).

    Returns:
        Animation instance configured for error feedback.
    """
    return Animation(
        animation_type=AnimationType.ERROR_FLASH,
        start_time_ms=start_time_ms,
        duration_ms=duration_ms,
        easing_fn=ease_out_cubic,
        from_value=0.0,  # Invisible
        to_value=1.0,  # Fully visible
        iterations=iterations,
    )


# ---------------------------------------------------------------------------
# MicroAnimationController
# ---------------------------------------------------------------------------


class MicroAnimationController:
    """Manages micro-animations for UI elements (V-06 Wave D2).

    Each UI element registers animations by unique key (e.g., "button_1").
    Only one animation per type per key is active at a time; starting a new
    animation of the same type replaces the existing one.

    Usage:
        controller = MicroAnimationController()
        controller.start("button_1", AnimationType.CLICK, start_time_ms=1000)
        # In render loop:
        controller.update(1010)  # Advance to 1010ms
        scale = controller.get_value("button_1", default=1.0)
    """

    def __init__(self) -> None:
        """Initialize empty controller."""
        # key → {AnimationType → Animation}
        self._animations: dict[str, dict[AnimationType, Animation]] = {}

    @property
    def active_count(self) -> int:
        """Number of currently active animations (not completed)."""
        count = 0
        for type_map in self._animations.values():
            for anim in type_map.values():
                if not anim.completed:
                    count += 1
        return count

    def start(
        self,
        key: str,
        animation_type: AnimationType,
        start_time_ms: float,
        duration_ms: int | None = None,
        from_value: float | None = None,
        to_value: float | None = None,
        iterations: int = 1,
    ) -> Animation:
        """Start a new animation for a UI element.

        Args:
            key: Unique identifier for the UI element (e.g., "button_1").
            animation_type: Type of animation to start.
            start_time_ms: Animation start time (game clock).
            duration_ms: Custom duration. If None, uses type default.
            from_value: Custom start value. If None, uses type default.
            to_value: Custom end value. If None, uses type default.
            iterations: Number of iterations (default 1).

        Returns:
            The created Animation instance.
        """
        # Resolve defaults based on animation type
        anim = self._build_animation(
            animation_type,
            start_time_ms,
            duration_ms,
            from_value,
            to_value,
            iterations,
        )

        if key not in self._animations:
            self._animations[key] = {}
        self._animations[key][animation_type] = anim
        return anim

    def _build_animation(
        self,
        animation_type: AnimationType,
        start_time_ms: float,
        duration_ms: int | None,
        from_value: float | None,
        to_value: float | None,
        iterations: int,
    ) -> Animation:
        """Build an Animation instance with type-appropriate defaults."""
        if animation_type == AnimationType.HOVER:
            return Animation(
                animation_type=animation_type,
                start_time_ms=start_time_ms,
                duration_ms=duration_ms or DEFAULT_HOVER_DURATION_MS,
                easing_fn=ease_in_out_cubic,
                from_value=from_value if from_value is not None else HOVER_ALPHA_FROM,
                to_value=to_value if to_value is not None else HOVER_ALPHA_TO,
                iterations=iterations,
            )
        if animation_type == AnimationType.CLICK:
            return Animation(
                animation_type=animation_type,
                start_time_ms=start_time_ms,
                duration_ms=duration_ms or DEFAULT_CLICK_DURATION_MS,
                easing_fn=ease_out_cubic,
                from_value=from_value if from_value is not None else CLICK_SCALE_FROM,
                to_value=to_value if to_value is not None else CLICK_SCALE_TO,
                iterations=iterations,
            )
        if animation_type == AnimationType.SELECTION_PULSE:
            return Animation(
                animation_type=animation_type,
                start_time_ms=start_time_ms,
                duration_ms=duration_ms or DEFAULT_SELECTION_PULSE_DURATION_MS,
                easing_fn=ease_in_out_sine,
                from_value=from_value if from_value is not None else SELECTION_PULSE_ALPHA_MIN,
                to_value=to_value if to_value is not None else SELECTION_PULSE_ALPHA_MAX,
                iterations=iterations,
            )
        # ERROR_FLASH
        return Animation(
            animation_type=animation_type,
            start_time_ms=start_time_ms,
            duration_ms=duration_ms or DEFAULT_ERROR_FLASH_DURATION_MS,
            easing_fn=ease_out_cubic,
            from_value=from_value if from_value is not None else 0.0,
            to_value=to_value if to_value is not None else 1.0,
            iterations=iterations,
        )

    def cancel(self, key: str, animation_type: AnimationType | None = None) -> bool:
        """Cancel animation(s) for a UI element.

        Args:
            key: UI element identifier.
            animation_type: Specific type to cancel. If None, cancels all types.

        Returns:
            True if any animation was cancelled, False if none existed.
        """
        if key not in self._animations:
            return False

        if animation_type is None:
            # Cancel all animations for this key
            count = len(self._animations[key])
            del self._animations[key]
            return count > 0

        if animation_type in self._animations[key]:
            del self._animations[key][animation_type]
            if not self._animations[key]:
                del self._animations[key]
            return True
        return False

    def get_value(self, key: str, animation_type: AnimationType, default: float = 0.0) -> float:
        """Get current animated value for a UI element.

        Does NOT advance time — call update() first with current game clock.

        Args:
            key: UI element identifier.
            animation_type: Type of animation to query.
            default: Value to return if animation doesn't exist or completed.

        Returns:
            Current animated value, or default if not active.
        """
        type_map = self._animations.get(key)
        if type_map is None:
            return default
        anim = type_map.get(animation_type)
        if anim is None:
            return default
        if anim.completed:
            return default
        return anim._current_value

    def update(self, current_time_ms: float) -> None:
        """Advance all animations to current time.

        Must be called once per frame BEFORE get_value() calls.

        Args:
            current_time_ms: Current game clock in milliseconds.
        """
        for type_map in self._animations.values():
            for anim in type_map.values():
                if not anim.completed:
                    value = anim.compute_progress(current_time_ms)
                    anim._current_value = value

    def cleanup_completed(self) -> int:
        """Remove all completed animations.

        Returns:
            Number of animations removed.
        """
        removed = 0
        empty_keys: list[str] = []
        for key, type_map in self._animations.items():
            completed_types = [t for t, a in type_map.items() if a.completed]
            for t in completed_types:
                del type_map[t]
                removed += 1
            if not type_map:
                empty_keys.append(key)
        for key in empty_keys:
            del self._animations[key]
        return removed

    def clear(self) -> None:
        """Remove all animations (reset controller)."""
        self._animations.clear()


__all__ = [
    "CLICK_SCALE_FROM",
    "CLICK_SCALE_TO",
    "DEFAULT_CLICK_DURATION_MS",
    "DEFAULT_ERROR_FLASH_DURATION_MS",
    "DEFAULT_HOVER_DURATION_MS",
    "DEFAULT_SELECTION_PULSE_DURATION_MS",
    "ERROR_FLASH_COLOR",
    "ERROR_FLASH_MAX_ITERATIONS",
    "HOVER_ALPHA_FROM",
    "HOVER_ALPHA_TO",
    "SELECTION_PULSE_ALPHA_MAX",
    "SELECTION_PULSE_ALPHA_MIN",
    "Animation",
    "AnimationType",
    "EasingFn",
    "MicroAnimationController",
    "create_click_animation",
    "create_error_flash_animation",
    "create_hover_animation",
    "create_selection_pulse_animation",
]
