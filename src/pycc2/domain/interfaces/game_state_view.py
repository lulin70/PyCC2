"""Minimal read/write view of game state for presentation-layer consumers.

Breaks the circular dependency where ``presentation/input/input_router.py``
needs attributes from ``services/game_loop.GameState`` but must not import
from the services layer.

Only the attributes actually consumed by downstream code are declared here.
``services.game_loop.GameState`` satisfies this protocol implicitly.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class GameStateView(Protocol):
    """Structural interface for the subset of GameState that input/rendering needs."""

    running: bool
    paused: bool
    debug_mode: bool

    # These use getattr() in callers so they are optional at type level
    # but always present on the real GameState dataclass.
    units: list  # list[Unit]
    selected_unit_ids: set  # set[str]
