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

    def render(self, screen: Any, camera: Any) -> None:
        """Render the deployment UI overlay."""
        ...

    def handle_event(self, event: Any) -> bool:
        """Handle a pygame event. Return True if consumed."""
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
