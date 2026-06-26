"""HUD Manager Protocol — interface for heads-up display management.

Defines the contract that any HUD manager must satisfy for use by
the services layer. Covers the public API of HUDManager as consumed
by game_loop.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from .minimap_protocol import IMinimap


@runtime_checkable
class IHUDManager(Protocol):
    """Interface for heads-up display rendering and updates.

    Covers the methods called by services (game_loop, etc.)
    on HUDManager.
    """

    @property
    def minimap(self) -> "IMinimap | None":
        """The minimap instance, or None if not initialized."""
        ...

    def render(self, screen: Any, camera: Any, state: Any) -> None:
        """Render the HUD overlay."""
        ...

    def update(self, dt: float) -> None:
        """Update HUD state by the given delta time."""
        ...

    def set_mouse_pos(self, mouse_pos: tuple[int, int]) -> None:
        """Forward current mouse position for hover/tooltip tracking."""
        ...

    def set_mouse_pressed(self, pressed: bool) -> None:
        """Forward mouse button pressed state for press feedback."""
        ...
