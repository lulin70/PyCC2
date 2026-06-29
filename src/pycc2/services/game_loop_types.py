"""Game Loop Types — extracted from game_loop.py (P5-1 batch 2).

Contains the GameState dataclass and frame-timing constants shared across
the game loop mixins and facade. This module has no pycc2 runtime imports
(only stdlib + TYPE_CHECKING) so it can be safely imported by all
game_loop_* modules without circular import risk.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.interfaces.camera_protocol import ICamera as Camera

# Fixed-timestep simulation constants
LOGIC_DT: float = 1.0 / 30.0  # 30 Hz logic tick
TARGET_FPS: int = 60
MAX_FRAME_TIME: float = 0.25  # Clamp to avoid spiral-of-death after pauses


@dataclass(slots=True)
class GameState:
    """Mutable snapshot of the current game world each frame operates on."""

    game_map: GameMap
    units: list[Unit]
    camera: Camera
    selected_unit_ids: set[str] = field(default_factory=set)
    tick: int = 0
    running: bool = True
    paused: bool = False
    debug_mode: bool = False
    side_turn: str = "allies"
    time_speed: float = 1.0
    current_weather: object | None = None  # WeatherType enum


__all__ = [
    "LOGIC_DT",
    "MAX_FRAME_TIME",
    "TARGET_FPS",
    "GameState",
]
