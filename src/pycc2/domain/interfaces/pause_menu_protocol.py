"""Pause Menu Protocol — interface for the pause menu.

Defines the contract that any pause menu must satisfy for use by
the services layer. Covers the public API of PauseMenu as consumed
by game_loop.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IPauseMenu(Protocol):
    """Interface for the pause menu overlay.

    Covers the methods and properties called by services (game_loop, etc.)
    on PauseMenu.
    """

    @property
    def is_active(self) -> bool:
        """Whether the pause menu is currently active."""
        ...

    def render(self, screen: Any) -> None:
        """Render the pause menu overlay."""
        ...
