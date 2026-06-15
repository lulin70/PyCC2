"""Environmental Audio Protocol — interface for ambient sound.

Defines the contract that any environmental audio system must satisfy
for use by the services layer. Covers the public API of
EnvironmentalAudio as consumed by game_loop.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class IEnvironmentalAudio(Protocol):
    """Interface for environmental / ambient audio management.

    Covers the methods called by services (game_loop, etc.)
    on EnvironmentalAudio.
    """

    def update(self, dt: float) -> None:
        """Update ambient audio state by the given delta time."""
        ...

    def set_time_of_day(self, hour: int) -> None:
        """Set the time of day for ambient sound selection."""
        ...

    def set_weather_rain(self, is_raining: bool) -> None:
        """Enable or disable rain ambient sounds."""
        ...

    def set_combat_intensity(self, intensity: float) -> None:
        """Set the combat intensity level for ambient sounds."""
        ...

    def stop_all(self) -> None:
        """Stop all ambient sounds."""
        ...
