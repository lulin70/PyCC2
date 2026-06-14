"""Input Handler Protocol — interface for input handling.

Defines the contract that any input handler must satisfy for use by the
services layer. Covers the public methods of PygameInputHandler and
InputRouter as consumed by game_loop and event_dispatcher.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IInputHandler(Protocol):
    """Interface for input handling.

    Covers the methods called by services on PygameInputHandler.
    """

    def process_event(self, event: Any) -> Any: ...

    def get_camera_movement(self) -> tuple[float, float]: ...
