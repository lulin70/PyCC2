"""Effect Stack Protocol — interface for screen effect stacking.

Defines the contract that any effect stack must satisfy for use by
the services layer. Covers the public API of EffectStack as consumed
by game_loop and camera systems.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class IEffectStack(Protocol):
    """Interface for screen effect stacking and composition.

    Covers the methods called by services (game_loop, combat_camera, etc.)
    on EffectStack.
    """

    def is_empty(self) -> bool:
        """Return True if no effects are active."""
        ...

    def get_total_offset(self) -> tuple[float, float]:
        """Return the combined screen offset from all active effects."""
        ...

    def get_time_scale(self) -> float:
        """Return the combined time scale from all active effects."""
        ...

    def update(self, dt: float) -> None:
        """Update all active effects by the given delta time."""
        ...
