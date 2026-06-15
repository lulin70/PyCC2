"""HUD Manager Protocol — interface for heads-up display management.

Defines the contract that any HUD manager must satisfy for use by
the services layer. Covers the public API of HUDManager as consumed
by game_loop.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IHUDManager(Protocol):
    """Interface for heads-up display rendering and updates.

    Covers the methods called by services (game_loop, etc.)
    on HUDManager.
    """

    def render(self, screen: Any, camera: Any, state: Any) -> None:
        """Render the HUD overlay."""
        ...

    def update(self, dt: float) -> None:
        """Update HUD state by the given delta time."""
        ...
