"""Shadow System Protocol — interface for dynamic shadow rendering.

Defines the contract that any dynamic shadow system must satisfy for
use by the services layer. Covers the public API of DynamicShadowSystem
as consumed by game_loop.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class IDynamicShadowSystem(Protocol):
    """Interface for dynamic shadow rendering based on time of day.

    Covers the methods called by services (game_loop, etc.)
    on DynamicShadowSystem.
    """

    def set_time_of_day(self, tod: float) -> None:
        """Set the time of day for shadow direction and length."""
        ...
