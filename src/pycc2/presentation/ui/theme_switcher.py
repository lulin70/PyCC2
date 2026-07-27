"""Theme Switcher (V-10 Wave E2)

Manages runtime switching between CC2-faithful and Morandi visual skins.
Implements Wave B-rev UX safeguards to prevent disruptive theme changes
during combat.

Wave B-rev UX safeguards:
  - **Combat lock**: Theme switching disabled during combat
    (``can_switch()`` returns False when ``game_state.in_combat`` is True)
  - **Confirmation dialog**: User must confirm before theme switch
    (explains ~200ms sprite cache rebuild cost)
  - **Progress bar**: Visible when rebuild exceeds 200ms threshold
  - **Fade transition**: 100ms fade-out → rebuild → 100ms fade-in
    (smooth visual handoff, no jarring pop)

State machine:
    IDLE → request_switch() → CONFIRMING → confirm() → FADING_OUT
        → REBUILDING → FADING_IN → IDLE

Usage::

    switcher = ThemeSwitcher(theme_manager, game_state, visual_spec)
    if switcher.can_switch():
        switcher.request_switch("morandi")
    # UI layer polls switcher.state and renders confirmation dialog / progress bar

Reference: docs/VISUAL_POLISH_PLAN.md V-10 章节 (v2.1, Wave B-rev)
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from pycc2.presentation.rendering.palette_morandi import apply_morandi_palette
from pycc2.presentation.rendering.visual_spec import VisualSpec
from pycc2.presentation.visual_config import ThemeManager

if TYPE_CHECKING:
    from pycc2.services.game_loop_types import GameState


# ──────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────

TRANSITION_MS: int = 100  # fade-in/out duration (ms)
PROGRESS_THRESHOLD_MS: int = 200  # show progress bar if rebuild exceeds this
DEFAULT_THEME: str = "cc2_classic"
MORANDI_THEME: str = "morandi"
AVAILABLE_THEMES: tuple[str, ...] = (DEFAULT_THEME, MORANDI_THEME)


class ThemeSwitchState(Enum):
    """Theme switcher state machine states."""

    IDLE = "idle"  # No switch in progress
    CONFIRMING = "confirming"  # Waiting for user confirmation
    FADING_OUT = "fading_out"  # Fade-out animation (100ms)
    REBUILDING = "rebuilding"  # Rebuilding sprite caches (with progress bar)
    FADING_IN = "fading_in"  # Fade-in animation (100ms)


@dataclass(slots=True)
class SwitchResult:
    """Result of a theme switch operation.

    Attributes:
        success: True if switch completed without error.
        old_theme: Theme name before switch.
        new_theme: Theme name after switch (same as old_theme if failed).
        rebuild_duration_ms: Time spent rebuilding sprite caches (ms).
        progress_bar_shown: True if rebuild exceeded PROGRESS_THRESHOLD_MS.
        error: Error message if success is False, else None.
    """

    success: bool
    old_theme: str
    new_theme: str
    rebuild_duration_ms: float
    progress_bar_shown: bool
    error: str | None = None


class ThemeSwitcher:
    """Theme switching controller with combat lock + transition (V-10 Wave B-rev).

    Coordinates confirmation dialog, fade transition, sprite cache rebuild,
    and ThemeManager notification. The UI layer is responsible for rendering
    the confirmation dialog and progress bar based on ``state`` and
    ``rebuild_progress``.
    """

    TRANSITION_MS: int = TRANSITION_MS
    PROGRESS_THRESHOLD_MS: int = PROGRESS_THRESHOLD_MS

    def __init__(
        self,
        theme_manager: ThemeManager,
        game_state: GameState,
        visual_spec: VisualSpec,
        current_theme: str = DEFAULT_THEME,
    ) -> None:
        """Initialize the ThemeSwitcher.

        Args:
            theme_manager: ThemeManager to notify on theme change.
            game_state: Game state for combat lock check.
            visual_spec: VisualSpec to apply palette to.
            current_theme: Current theme name (default: "cc2_classic").
        """
        self._theme_manager = theme_manager
        self._game_state = game_state
        self._visual_spec = visual_spec
        self._current_theme: str = current_theme
        self._state: ThemeSwitchState = ThemeSwitchState.IDLE
        self._pending_theme: str | None = None
        self._rebuild_progress: float = 0.0  # 0.0 to 1.0
        self._fade_alpha: float = 0.0  # 0.0 (opaque) to 1.0 (fully faded out)
        self._last_result: SwitchResult | None = None
        self._rebuild_start_time: float = 0.0

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def current_theme(self) -> str:
        """Current active theme name."""
        return self._current_theme

    @property
    def state(self) -> ThemeSwitchState:
        """Current state machine state."""
        return self._state

    @property
    def pending_theme(self) -> str | None:
        """Theme waiting for confirmation (None if not in CONFIRMING state)."""
        return self._pending_theme if self._state == ThemeSwitchState.CONFIRMING else None

    @property
    def rebuild_progress(self) -> float:
        """Rebuild progress (0.0 to 1.0). Only meaningful in REBUILDING state."""
        return self._rebuild_progress

    @property
    def fade_alpha(self) -> float:
        """Fade alpha (0.0 = opaque, 1.0 = fully faded out). For UI rendering."""
        return self._fade_alpha

    @property
    def last_result(self) -> SwitchResult | None:
        """Last switch result (None if no switch has been attempted)."""
        return self._last_result

    # ------------------------------------------------------------------
    # Combat lock + availability
    # ------------------------------------------------------------------

    def can_switch(self) -> bool:
        """Check if theme switch is allowed right now.

        Wave B-rev: Disables switching during combat. Also blocks if a
        switch is already in progress.

        Returns:
            True if switch can be initiated, False otherwise.
        """
        if self._state != ThemeSwitchState.IDLE:
            return False
        return not getattr(self._game_state, "in_combat", False)

    def unavailable_reason(self) -> str:
        """Human-readable reason for why switch is unavailable.

        Returns:
            Reason string (empty if switch is available).
        """
        if self._state != ThemeSwitchState.IDLE:
            return f"Switch already in progress (state={self._state.value})"
        if getattr(self._game_state, "in_combat", False):
            return "战斗中不可切换视觉风格"
        return ""

    # ------------------------------------------------------------------
    # State machine transitions
    # ------------------------------------------------------------------

    def request_switch(self, new_theme: str) -> bool:
        """Request a theme switch (enters CONFIRMING state).

        Args:
            new_theme: Target theme name (must be in AVAILABLE_THEMES).

        Returns:
            True if request was accepted (entered CONFIRMING), False if
            blocked by combat lock or invalid theme.
        """
        if new_theme not in AVAILABLE_THEMES:
            return False
        if new_theme == self._current_theme:
            return False  # No-op: already on this theme
        if not self.can_switch():
            return False
        self._pending_theme = new_theme
        self._state = ThemeSwitchState.CONFIRMING
        return True

    def confirm(self) -> bool:
        """Confirm the pending theme switch (enters FADING_OUT state).

        Returns:
            True if confirmation was accepted, False if not in CONFIRMING state.
        """
        if self._state != ThemeSwitchState.CONFIRMING or self._pending_theme is None:
            return False
        self._state = ThemeSwitchState.FADING_OUT
        self._fade_alpha = 0.0
        return True

    def cancel(self) -> bool:
        """Cancel the pending theme switch (returns to IDLE).

        Returns:
            True if cancellation was accepted, False if not in CONFIRMING state.
        """
        if self._state != ThemeSwitchState.CONFIRMING:
            return False
        self._pending_theme = None
        self._state = ThemeSwitchState.IDLE
        return True

    def update(self, dt_ms: float) -> None:
        """Advance the state machine by ``dt_ms`` milliseconds.

        Must be called every frame by the UI layer. Handles fade-out →
        rebuild → fade-in transitions automatically.

        Args:
            dt_ms: Delta time in milliseconds since last update.
        """
        if self._state == ThemeSwitchState.FADING_OUT:
            self._fade_alpha = min(1.0, self._fade_alpha + dt_ms / self.TRANSITION_MS)
            if self._fade_alpha >= 1.0:
                self._begin_rebuild()

        elif self._state == ThemeSwitchState.REBUILDING:
            # Rebuild is synchronous in this implementation; progress is
            # time-based estimate for UI feedback only.
            elapsed_ms = (time.perf_counter() - self._rebuild_start_time) * 1000.0
            self._rebuild_progress = min(
                1.0, elapsed_ms / max(1.0, float(self.PROGRESS_THRESHOLD_MS))
            )
            # Rebuild is considered complete once progress reaches 1.0
            if self._rebuild_progress >= 1.0:
                self._begin_fade_in()

        elif self._state == ThemeSwitchState.FADING_IN:
            self._fade_alpha = max(0.0, self._fade_alpha - dt_ms / self.TRANSITION_MS)
            if self._fade_alpha <= 0.0:
                self._complete_switch()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _begin_rebuild(self) -> None:
        """Transition from FADING_OUT to REBUILDING: apply palette + notify."""
        assert self._pending_theme is not None  # noqa: S101
        self._state = ThemeSwitchState.REBUILDING
        self._rebuild_progress = 0.0
        self._rebuild_start_time = time.perf_counter()
        # Apply the new palette synchronously (actual rebuild would be
        # handled by ThemeManager listeners invalidating caches)
        if self._pending_theme == MORANDI_THEME:
            apply_morandi_palette(self._visual_spec)
        # For cc2_classic, rebuild a fresh VisualSpec (no restore helper needed
        # because VisualSpec.__init__ sets defaults)
        elif self._pending_theme == DEFAULT_THEME:
            fresh_spec = VisualSpec()
            # Copy all instance attributes from fresh spec
            for attr in vars(fresh_spec):
                setattr(self._visual_spec, attr, getattr(fresh_spec, attr))

    def _begin_fade_in(self) -> None:
        """Transition from REBUILDING to FADING_IN."""
        self._state = ThemeSwitchState.FADING_IN
        # Notify ThemeManager listeners (renderers invalidate caches)
        self._theme_manager.notify_theme_change()

    def _complete_switch(self) -> None:
        """Transition from FADING_IN to IDLE: finalize + record result."""
        assert self._pending_theme is not None  # noqa: S101
        rebuild_duration_ms = (time.perf_counter() - self._rebuild_start_time) * 1000.0
        progress_shown = rebuild_duration_ms >= float(self.PROGRESS_THRESHOLD_MS)
        old_theme = self._current_theme
        new_theme = self._pending_theme
        self._current_theme = new_theme
        self._pending_theme = None
        self._fade_alpha = 0.0
        self._rebuild_progress = 0.0
        self._state = ThemeSwitchState.IDLE
        self._last_result = SwitchResult(
            success=True,
            old_theme=old_theme,
            new_theme=new_theme,
            rebuild_duration_ms=rebuild_duration_ms,
            progress_bar_shown=progress_shown,
        )

    def force_complete(self) -> SwitchResult | None:
        """Force-complete the switch immediately (skip fade + rebuild animation).

        Intended for testing or when UI animations are not available.
        Applies the palette, notifies listeners, and records the result
        without going through the state machine.

        Returns:
            SwitchResult if a switch was pending, None otherwise.
        """
        if self._pending_theme is None:
            return None
        old_theme = self._current_theme
        new_theme = self._pending_theme
        start = time.perf_counter()
        if new_theme == MORANDI_THEME:
            apply_morandi_palette(self._visual_spec)
        elif new_theme == DEFAULT_THEME:
            fresh_spec = VisualSpec()
            for attr in vars(fresh_spec):
                setattr(self._visual_spec, attr, getattr(fresh_spec, attr))
        self._theme_manager.notify_theme_change()
        duration_ms = (time.perf_counter() - start) * 1000.0
        self._current_theme = new_theme
        self._pending_theme = None
        self._state = ThemeSwitchState.IDLE
        self._fade_alpha = 0.0
        self._rebuild_progress = 0.0
        self._last_result = SwitchResult(
            success=True,
            old_theme=old_theme,
            new_theme=new_theme,
            rebuild_duration_ms=duration_ms,
            progress_bar_shown=duration_ms >= float(self.PROGRESS_THRESHOLD_MS),
        )
        return self._last_result


__all__ = [
    "TRANSITION_MS",
    "PROGRESS_THRESHOLD_MS",
    "DEFAULT_THEME",
    "MORANDI_THEME",
    "AVAILABLE_THEMES",
    "ThemeSwitchState",
    "SwitchResult",
    "ThemeSwitcher",
]
