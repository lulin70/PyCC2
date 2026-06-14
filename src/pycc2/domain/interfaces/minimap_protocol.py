"""Protocol interface for Minimap — decouples services from presentation."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IMinimap(Protocol):
    """Interface for minimap rendering and interaction.

    Defines the contract that Minimap must satisfy so that
    services (e.g. HUDManager) can depend on this abstraction
    instead of the concrete presentation class.
    """

    # Properties -----------------------------------------------------------

    @property
    def is_visible(self) -> bool:
        """Whether the minimap is currently visible."""
        ...

    # Map setup ------------------------------------------------------------

    def set_map(self, game_map: Any) -> None:
        """Set the game map for rendering."""
        ...

    def set_projection_mode(self, is_isometric: bool) -> None:
        """Set the minimap projection mode."""
        ...

    def update_units(self, units: list) -> None:
        """Update unit positions for minimap display."""
        ...

    def set_selected_unit(self, unit_id: str | None) -> None:
        """Set the currently selected unit ID for highlight rendering."""
        ...

    def set_camera_viewport(self, viewport: tuple[float, float, float, float] | None) -> None:
        """Set camera viewport rectangle in world coordinates (x, y, width, height)."""
        ...

    # Visibility -----------------------------------------------------------

    def show(self) -> None:
        """Show the minimap with fade-in effect."""
        ...

    def hide(self) -> None:
        """Hide the minimap with fade-out effect."""
        ...

    def update(self, dt: float) -> None:
        """Update fade transition animation state."""
        ...

    # Rendering & interaction ----------------------------------------------

    def render(self, surface: Any, x: int, y: int) -> None:
        """Render minimap at screen position (x, y)."""
        ...

    def handle_click(self, screen_pos: tuple[int, int], camera: Any) -> bool:
        """Handle a mouse click on the minimap. Return True if consumed."""
        ...
