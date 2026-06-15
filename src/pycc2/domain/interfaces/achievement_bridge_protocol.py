"""Achievement Bridge Protocol — interface for achievement system bridging.

Defines the contract that any achievement bridge must satisfy for use by
the services layer. Covers the public API of AchievementBridge as consumed
by game_loop.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IAchievementBridge(Protocol):
    """Interface for bridging game events to the achievement system.

    Covers the methods and properties called by services (game_loop, etc.)
    on AchievementBridge.
    """

    @property
    def _manager(self) -> object:
        """The underlying achievement manager instance."""
        ...

    def subscribe(self, event_bus: Any) -> None:
        """Subscribe to events on the given event bus."""
        ...
