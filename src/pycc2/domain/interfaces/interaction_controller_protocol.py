"""Interaction Controller Protocol — interface for game interaction.

Defines the contract that any interaction controller must satisfy for use by
the services layer. Covers the public methods of InteractionController as
consumed by game_loop, event_dispatcher, and hud_manager.
"""

from __future__ import annotations

from collections.abc import Callable
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
        self,
        screen_pos: tuple[float, float],
        units: list[Any],
        modifiers: Any = None,
        shift_held: bool = False,
    ) -> None: ...

    def handle_right_mouse_down(
        self, screen_pos: tuple[float, float], units: list[Any]
    ) -> None: ...

    def handle_right_mouse_up(
        self, screen_pos: tuple[float, float], units: list[Any]
    ) -> None: ...

    def handle_mouse_move(
        self, screen_pos: tuple[float, float], units: list[Any]
    ) -> None: ...

    def handle_drag_motion(self, screen_pos: tuple[float, float]) -> None: ...

    def handle_shortcut_key(self, key: int) -> None: ...

    def set_ctrl_held(self, held: bool) -> None: ...

    @property
    def ctrl_held(self) -> bool: ...

    @property
    def _is_right_dragging(self) -> bool: ...

    def hit_test(self, screen_pos: tuple[float, float], units: list[Any]) -> Any: ...

    def screen_to_tile(self, screen_pos: tuple[float, float]) -> Any: ...

    def render_overlay(self, screen: Any, camera: Any) -> None: ...

    @property
    def attack_line(self) -> Any: ...

    def register_on_move(self, callback: Callable[[set[str], Any], None]) -> None: ...

    def register_on_attack(self, callback: Callable[[set[str], str], None]) -> None: ...
