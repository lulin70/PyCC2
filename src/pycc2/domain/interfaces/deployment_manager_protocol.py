"""Deployment Manager Protocol — interface for deployment phase management.

Defines the contract that any deployment manager must satisfy for use by
the services layer. Covers the public API of DeploymentManager as consumed
by game_loop.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from .deployment_ui_protocol import IDeploymentUI


@runtime_checkable
class IDeploymentManager(Protocol):
    """Interface for deployment phase management.

    Covers the methods and properties called by services (game_loop, etc.)
    on DeploymentManager.
    """

    @property
    def is_active(self) -> bool:
        """Whether the deployment phase is currently active."""
        ...

    @property
    def deployment_ui(self) -> IDeploymentUI | None:
        """The current deployment UI instance, or None."""
        ...

    def start(
        self,
        map_data: Any,
        faction: str,
        game_settings: Any,
        display_config: Any,
        deployment_ui: Any,
    ) -> None:
        """Start the deployment phase with the given parameters."""
        ...

    def complete(self, ai_service: Any, state: Any) -> dict | None:
        """Complete the deployment phase and return placement data, or None."""
        ...

    def get_state(self) -> object | None:
        """Return the current deployment state, or None if not active."""
        ...

    def set_pending_order(self, unit_id: str, tx: int, ty: int) -> None:
        """Set a pending pre-battle order for the given unit."""
        ...
