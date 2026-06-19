"""Victory Manager Protocol — interface for victory evaluation.

Defines the contract that any victory manager must satisfy for use by
the services layer. Covers the public API of VictoryManager as consumed
by game_loop.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class IVictoryManager(Protocol):
    """Interface for victory evaluation and post-battle reporting.

    Covers the methods and properties called by services (game_loop, etc.)
    on VictoryManager.
    """

    def evaluate(self, units: list, tick: int) -> tuple | None:
        """Evaluate victory conditions. Return result tuple or None if undecided."""
        ...

    def update(self) -> None:
        """Update internal victory evaluation state."""
        ...

    def reset(self) -> None:
        """Reset victory state for a new battle."""
        ...

    @property
    def show_post_battle(self) -> bool:
        """Whether to show the post-battle screen."""
        ...

    @property
    def game_result(self) -> object | None:
        """The current game result, or None if no result yet."""
        ...

    @property
    def battle_stats(self) -> object:
        """Aggregate battle statistics."""
        ...
