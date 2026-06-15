"""Campaign UI Protocol — interface for campaign user interface.

Defines the contract that any campaign UI must satisfy for use by
the services layer. Covers the public API of CampaignUI as consumed
by game_loop.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ICampaignUI(Protocol):
    """Interface for campaign user interface rendering.

    Covers the methods and properties called by services (game_loop, etc.)
    on CampaignUI.
    """

    @property
    def is_visible(self) -> bool:
        """Whether the campaign UI is currently visible."""
        ...

    def render(self, screen: Any) -> None:
        """Render the campaign UI overlay."""
        ...
