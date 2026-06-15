"""Popup Manager Protocol — interface for combat popup indicators.

Defines the contract that any popup manager must satisfy for use by
the services layer. Covers the public API of PopupManager as consumed
by game_loop and combat systems.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IPopupManager(Protocol):
    """Interface for combat popup indicator management.

    Covers the methods called by services (combat_director, game_loop, etc.)
    on PopupManager.
    """

    def render(self, screen: Any, camera: Any) -> None:
        """Render all active popup indicators."""
        ...

    def add_taking_fire(self, x: float, y: float) -> None:
        """Add a 'taking fire' popup at the given position."""
        ...

    def add_breaking(self, x: float, y: float) -> None:
        """Add a 'breaking' popup at the given position."""
        ...

    def add_pinned(self, x: float, y: float) -> None:
        """Add a 'pinned' popup at the given position."""
        ...

    def add_out_of_ammo(self, x: float, y: float) -> None:
        """Add an 'out of ammo' popup at the given position."""
        ...

    def add_kia(self, x: float, y: float) -> None:
        """Add a 'KIA' popup at the given position."""
        ...
