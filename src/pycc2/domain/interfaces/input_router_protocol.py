"""Input Router Protocol — interface for routing pygame events to game systems.

Defines the contract that any input router must satisfy for use by the
services layer. Covers the public API of InputRouter as consumed by
event_dispatcher and game_loop.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IInputRouter(Protocol):
    """Interface for input routing.

    Covers the methods and properties called by services on InputRouter.
    """

    @property
    def input_handler(self) -> Any: ...

    @input_handler.setter
    def input_handler(self, value: Any) -> None: ...

    @property
    def show_post_battle(self) -> bool: ...

    @show_post_battle.setter
    def show_post_battle(self, value: bool) -> None: ...

    command_bar: Any | None

    # v0.7.5 INTEGRATE: SquadGroupManager injection point (optional, None by default).
    # Concrete InputRouter adds this field; services layer assigns via assembler.
    squad_group_manager: Any | None

    def route_input(self, event: Any) -> Any: ...
