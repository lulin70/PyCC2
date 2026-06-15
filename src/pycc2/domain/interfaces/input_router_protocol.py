"""Input Router Protocol — interface for input routing.

Defines the contract that any input router must satisfy for use by
the services layer. Covers the public API of InputRouter as consumed
by game_loop.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IInputRouter(Protocol):
    """Interface for input event routing.

    Covers the methods and properties called by services (game_loop, etc.)
    on InputRouter.
    """

    def route_input(self, event: Any) -> None:
        """Route an input event to the appropriate handler."""
        ...

    @property
    def input_handler(self) -> Any:
        """The current input handler (read/write)."""
        ...

    @input_handler.setter
    def input_handler(self, value: Any) -> None: ...
