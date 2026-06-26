"""Protocol interface for DeploymentUI — decouples services from presentation."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IDeploymentUI(Protocol):
    """Interface for deployment UI operations.

    Defines the contract that DeploymentUI must satisfy so that
    services (e.g. DeploymentManager, GameLoop) can depend on this
    abstraction instead of the concrete presentation class.
    """

    # Instance state -------------------------------------------------------

    @property
    def state(self) -> Any:
        """Return the internal deployment state object."""
        ...

    # Lifecycle ------------------------------------------------------------

    def start_deployment(self, map_data: dict, faction: str = "ally") -> None:
        """Initialize deployment phase with map zones and unit roster."""
        ...

    def start_deployment_with_settings(
        self,
        map_data: dict,
        faction: str = "ally",
        requisition_points: int = 2000,
        max_infantry: int = 9,
        max_support: int = 6,
        force_pool: list | None = None,
    ) -> None:
        """Initialize deployment with game settings controlling the force pool."""
        ...

    def begin_battle(self) -> dict:
        """Finalize deployment and return placement result dict."""
        ...

    def update_button_hover(self, mouse_x: int, mouse_y: int) -> None:
        """Update the Start Battle button hover state."""
        ...

    # Rendering / event handling -------------------------------------------

    def render(
        self,
        screen: Any,
        font: Any = None,
        map_offset_x: int = 0,
        map_offset_y: int = 0,
        tile_size: int = 16,
    ) -> None:
        """Render the deployment UI overlay."""
        ...

    def handle_event(self, event: Any) -> bool:
        """Handle a pygame event. Return True if consumed."""
        ...

    def handle_mouse_down(
        self,
        screen_x: int,
        screen_y: int,
        map_offset_x: int = 0,
        map_offset_y: int = 0,
        tile_size: int = 16,
    ) -> str | None:
        """Handle mouse button DOWN - start drag from roster unit."""
        ...

    def handle_mouse_move(
        self,
        screen_x: int,
        screen_y: int,
        map_offset_x: int = 0,
        map_offset_y: int = 0,
        tile_size: int = 16,
    ) -> None:
        """Handle mouse movement while dragging - update ghost position."""
        ...

    def handle_mouse_up(
        self,
        screen_x: int,
        screen_y: int,
        map_offset_x: int = 0,
        map_offset_y: int = 0,
        tile_size: int = 16,
    ) -> str | None:
        """Handle mouse button UP - complete drag (place or cancel)."""
        ...

    def handle_click_full(
        self,
        screen_x: int,
        screen_y: int,
        map_offset_x: int = 0,
        map_offset_y: int = 0,
        tile_size: int = 16,
        right_click: bool = False,
    ) -> str | None:
        """Full click handler converting screen coords to map coords automatically."""
        ...

    # Static helpers (delegated to deployment_factory) ---------------------

    @staticmethod
    def build_force_pool_from_settings(
        faction: str = "allied",
        requisition_points: int = 2000,
    ) -> list:
        """Build a force pool list for the given faction and RP budget."""
        ...

    @staticmethod
    def generate_ai_deployment(
        map_data: dict,
        faction: str = "axis",
        requisition_points: int = 1500,
    ) -> list[dict]:
        """Generate AI unit placements for the enemy side."""
        ...
