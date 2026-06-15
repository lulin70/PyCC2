"""Combat Camera Protocol — interface for combat camera effects.

Defines the contract that any combat camera must satisfy for use by
the services layer. Covers the public API of CombatCamera as consumed
by game_loop.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ICombatCamera(Protocol):
    """Interface for combat camera effects and shake.

    Covers the methods called by services (game_loop, event_dispatcher, etc.)
    on CombatCamera.
    """

    def set_effect_stack(self, stack: Any) -> None:
        """Set the effect stack for camera shake composition."""
        ...

    def subscribe(self, event_bus: Any) -> None:
        """Subscribe to combat events on the given event bus."""
        ...
