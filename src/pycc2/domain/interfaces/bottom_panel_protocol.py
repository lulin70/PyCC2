"""Protocol interface for CC2BottomPanel — decouples services from presentation."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IBottomPanel(Protocol):
    """Interface for the CC2-style bottom panel.

    Defines the contract that CC2BottomPanel must satisfy so that
    services (e.g. HUDManager) can depend on this abstraction
    instead of the concrete presentation class.
    """

    # Lifecycle ------------------------------------------------------------

    def initialize(self) -> None:
        """Initialize fonts and internal resources."""
        ...

    def show(self) -> None:
        """Show the panel."""
        ...

    def hide(self) -> None:
        """Hide the panel."""
        ...

    def update(self, dt: float) -> None:
        """Update panel animations / tooltips."""
        ...

    # Unit data ------------------------------------------------------------

    def set_selected_unit(self, unit_id: str | None) -> None:
        """Set the currently selected unit by ID."""
        ...

    def set_friendly_units(self, units: list) -> None:
        """Set the list of friendly units for roster display."""
        ...

    # Callbacks ------------------------------------------------------------

    def register_callback(self, command_id: str, callback: Callable) -> None:
        """Register a callback for a command button."""
        ...

    # Mouse interaction ----------------------------------------------------

    def set_mouse_pos(self, pos: tuple[int, int] | None) -> None:
        """Forward mouse position for hover / tooltip rendering."""
        ...

    def set_mouse_pressed(self, pressed: bool) -> None:
        """Forward mouse button state for press rendering."""
        ...

    def handle_click(self, screen_pos: tuple[int, int]) -> str | None:
        """Handle a mouse click. Return command ID if consumed, else None."""
        ...

    # Rendering ------------------------------------------------------------

    def render(
        self,
        surface: Any,
        camera: Any,
        game_map: Any,
        minimap: Any | None = None,
    ) -> None:
        """Render the full bottom panel including minimap."""
        ...
