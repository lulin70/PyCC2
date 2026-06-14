"""Interaction Controller Protocol — interface for game interaction.

Defines the contract that any interaction controller must satisfy for use by
the services layer. Covers the public methods of InteractionController as
consumed by game_loop, event_dispatcher, and hud_manager.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IInteractionController(Protocol):
    """Interface for interaction control.

    Covers the methods called by services on InteractionController.
    """

    @property
    def mode(self) -> Any: ...

    @property
    def camera(self) -> Any: ...

    @property
    def selected_unit_ids(self) -> set[str]: ...

    def set_mode(self, mode: Any, fast: bool = False, sneak: bool = False) -> None: ...

    def handle_left_click(
        self, screen_pos: tuple[float, float], units: list[Any], modifiers: Any = None
    ) -> set[str]: ...

    def handle_right_click(
        self, screen_pos: tuple[float, float], units: list[Any], modifiers: Any = None
    ) -> None: ...

    def handle_right_mouse_down(
        self, screen_pos: tuple[float, float], units: list[Any]
    ) -> None: ...

    def handle_right_mouse_up(self, screen_pos: tuple[float, float]) -> None: ...

    def handle_shortcut_key(self, key: int) -> None: ...

    def set_ctrl_held(self, held: bool) -> None: ...

    def hit_test(self, screen_pos: tuple[float, float], units: list[Any]) -> Any: ...

    def screen_to_tile(self, screen_pos: tuple[float, float]) -> Any: ...
