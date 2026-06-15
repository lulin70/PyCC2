"""Save Controller Protocol — interface for save/load operations.

Defines the contract that any save controller must satisfy for use by
the services layer. Covers the public API of SaveController as consumed
by game_loop.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ISaveController(Protocol):
    """Interface for save and load operations.

    Covers the methods called by services (game_loop, pause_menu, etc.)
    on SaveController.
    """

    def quick_save(self, slot: int, game_loop: Any) -> bool:
        """Quick-save the game to the given slot. Return True on success."""
        ...

    def quick_load(self, slot: int, game_loop: Any) -> bool:
        """Quick-load the game from the given slot. Return True on success."""
        ...

    def list_saves(self) -> list:
        """List available save slots."""
        ...

    def initialize(self) -> None:
        """Initialize the save controller."""
        ...
