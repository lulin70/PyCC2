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

    def toggle(self) -> None:
        """Toggle pause menu active state."""
        ...

    def deactivate(self) -> None:
        """Deactivate the pause menu."""
        ...

    def update_mouse(self, mouse_pos: tuple[int, int]) -> None:
        """Update mouse hover state."""
        ...

    def handle_click(self, mouse_pos: tuple[int, int]) -> str | None:
        """Handle a mouse click. Return selected action or None."""
        ...

    def render(self, screen: Any) -> None:
        """Render the pause menu overlay."""
        ...
