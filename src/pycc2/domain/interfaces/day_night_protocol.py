"""Day-Night Cycle Protocol — interface for day/night progression.

Defines the contract that any day-night cycle system must satisfy for
use by the services layer. Covers the public API of DayNightCycle
as consumed by game_loop.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class IDayNightCycle(Protocol):
    """Interface for day-night cycle progression.

    Covers the methods and properties called by services (game_loop, etc.)
    on DayNightCycle.
    """

    def advance(self, dt: float) -> None:
        """Advance the day-night cycle by the given delta time."""
        ...

    @property
    def time_of_day(self) -> float:
        """The current time of day (0.0–24.0)."""
        ...
