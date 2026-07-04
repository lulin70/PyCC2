"""InfantryAnimator - animation state manager for infantry sprites.

Extracted from infantry_pixel_renderer.py during Phase 2 P0-1 large file split (2026-07-04).
Manages frame cycling and state transitions (move/shoot/death/prone) at fixed intervals.
"""

from __future__ import annotations

from pycc2.presentation.rendering.pixel_artist_enums import InfantryAnimState


class InfantryAnimator:
    """Infantry animation state manager - manages frame cycling and state transitions.

    Automatically switches animation states based on unit behavior
    (move/shoot/death) and cycles walk frames at fixed intervals.
    """

    WALK_CYCLE_INTERVAL = 0.2  # Walk frame switch interval (seconds), ~5 FPS

    def __init__(self):
        """Initialize the InfantryAnimator."""
        self._frame: int = 0
        self._state: InfantryAnimState = InfantryAnimState.IDLE
        self._walk_timer: float = 0.0
        self._walk_cycle: list[InfantryAnimState] = [
            InfantryAnimState.WALK_1,
            InfantryAnimState.IDLE,
            InfantryAnimState.WALK_2,
            InfantryAnimState.IDLE,
        ]
        self._shoot_timer: float = 0.0
        self._shoot_duration: float = 0.15
        self._die_timer: float = 0.0
        self._die_duration: float = 0.3

    @property
    def state(self) -> InfantryAnimState:
        """Current animation state."""
        return self._state

    def update(
        self,
        dt: float,
        is_moving: bool = False,
        is_firing: bool = False,
        is_dead: bool = False,
        is_prone: bool = False,
    ) -> InfantryAnimState:
        """Update animation state based on unit behavior.

        Args:
            dt: Time since last update (seconds).
            is_moving: Whether the unit is moving.
            is_firing: Whether the unit is firing.
            is_dead: Whether the unit is dead.
            is_prone: Whether the unit is prone.

        Returns:
            Current InfantryAnimState.

        """
        if self._state == InfantryAnimState.DEAD:
            return self._state

        if is_dead:
            self._die_timer += dt
            if self._die_timer < self._die_duration:
                self._state = InfantryAnimState.DIE_1
            elif self._die_timer < self._die_duration * 2:
                self._state = InfantryAnimState.DIE_2
            else:
                self._state = InfantryAnimState.DEAD
            return self._state

        if is_firing:
            self._shoot_timer += dt
            self._state = InfantryAnimState.SHOOT
            if self._shoot_timer > self._shoot_duration:
                self._shoot_timer = 0.0
            return self._state
        else:
            self._shoot_timer = 0.0

        if is_prone:
            self._state = InfantryAnimState.PRONE
            return self._state

        if is_moving:
            self._walk_timer += dt
            if self._walk_timer > self.WALK_CYCLE_INTERVAL:
                self._walk_timer = 0.0
                self._frame = (self._frame + 1) % len(self._walk_cycle)
            self._state = self._walk_cycle[self._frame]
        else:
            self._walk_timer = 0.0
            self._frame = 0
            self._state = InfantryAnimState.IDLE

        return self._state

    def reset(self):
        """Reset animation state to initial values."""
        self._frame = 0
        self._state = InfantryAnimState.IDLE
        self._walk_timer = 0.0
        self._shoot_timer = 0.0
        self._die_timer = 0.0
