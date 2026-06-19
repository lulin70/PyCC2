"""Weather System Protocol — interface for weather simulation.

Defines the contract that any weather system must satisfy for use by
the services layer. Covers the public API of WeatherSystem as consumed
by game_loop.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class IWeatherSystem(Protocol):
    """Interface for weather simulation and state.

    Covers the methods and properties called by services (game_loop, etc.)
    on WeatherSystem.
    """

    def update(self, dt: float) -> None:
        """Update weather state by the given delta time."""
        ...

    @property
    def weather_type(self) -> object:
        """The current weather type."""
        ...
