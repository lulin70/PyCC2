"""TileCoord Value Object - Immutable Grid Coordinate"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class TileCoord:
    """Immutable integer grid coordinate with distance and neighbor helpers."""

    x: int
    y: int

    DIRECTION_OFFSETS: ClassVar[dict[str, tuple[int, int]]] = {
        "N": (0, -1),
        "S": (0, 1),
        "E": (1, 0),
        "W": (-1, 0),
        "NE": (1, -1),
        "NW": (-1, -1),
        "SE": (1, 1),
        "SW": (-1, 1),
    }

    @classmethod
    def origin(cls) -> TileCoord:
        """Return the origin coordinate (0, 0)."""
        return cls(0, 0)

    @classmethod
    def from_tuple(cls, t: tuple[int, int]) -> TileCoord:
        """Create a TileCoord from a (x, y) tuple."""
        return cls(t[0], t[1])

    @property
    def neighbors_8(self) -> list[TileCoord]:
        """Return the 8 surrounding neighbor coordinates (N, S, E, W, diagonals)."""
        return [
            TileCoord(self.x, self.y - 1),
            TileCoord(self.x, self.y + 1),
            TileCoord(self.x - 1, self.y),
            TileCoord(self.x + 1, self.y),
            TileCoord(self.x - 1, self.y - 1),
            TileCoord(self.x + 1, self.y - 1),
            TileCoord(self.x - 1, self.y + 1),
            TileCoord(self.x + 1, self.y + 1),
        ]

    def manhattan_distance(self, other: TileCoord) -> int:
        """Return the Manhattan (grid) distance to another coordinate."""
        return abs(self.x - other.x) + abs(self.y - other.y)

    def chebyshev_distance(self, other: TileCoord) -> int:
        """Return the Chebyshev (king-move) distance to another coordinate."""
        return max(abs(self.x - other.x), abs(self.y - other.y))

    def octile_distance(self, other: TileCoord) -> float:
        """Return the octile distance (8-direction pathfinding heuristic)."""
        dx = abs(self.x - other.x)
        dy = abs(self.y - other.y)
        return max(dx, dy) + (math.sqrt(2) - 1) * min(dx, dy)

    def is_within_bounds(self, width: int, height: int) -> bool:
        """Return whether this coordinate lies within the given map dimensions."""
        return 0 <= self.x < width and 0 <= self.y < height

    def offset(self, dx: int, dy: int) -> TileCoord:
        """Return a new coordinate shifted by the given delta."""
        return TileCoord(self.x + dx, self.y + dy)
