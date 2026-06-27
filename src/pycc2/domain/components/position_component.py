"""Position Component

Manages entity position on the game grid.
Handles grid coordinates, pixel offset, and facing direction.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.domain.value_objects.vec2 import Vec2


@dataclass(slots=True)
class PositionComponent:
    """Stores entity tile coordinate, pixel offset, and facing direction."""

    tile_coord: TileCoord
    pixel_offset: Vec2 = field(default_factory=Vec2.zero)
    facing_rad: float = 0.0

    @property
    def x(self) -> int:
        """Legacy alias for tile x coordinate."""
        return self.tile_coord.x

    @property
    def y(self) -> int:
        """Legacy alias for tile y coordinate."""
        return self.tile_coord.y

    @property
    def pixel_position(self) -> Vec2:
        tile_vec = Vec2(
            self.tile_coord.x * Vec2.TILE_SIZE,
            self.tile_coord.y * Vec2.TILE_SIZE,
        )
        return tile_vec + self.pixel_offset

    def set_facing_toward(self, target: Vec2 | TileCoord) -> None:
        if isinstance(target, TileCoord):
            target_vec = Vec2(
                target.x * Vec2.TILE_SIZE,
                target.y * Vec2.TILE_SIZE,
            )
        else:
            target_vec = target

        current_pos = self.pixel_position
        dx = target_vec.x - current_pos.x
        dy = -(target_vec.y - current_pos.y)
        self.facing_rad = math.atan2(dy, dx)

    def move_to_tile(self, tile: TileCoord) -> None:
        self.tile_coord = tile
        self.pixel_offset = Vec2.zero()

    def set_pixel_offset(self, offset: Vec2) -> None:
        self.pixel_offset = offset
