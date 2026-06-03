"""
Direction Enum

8-direction compass representation for grid-based movement and facing.
"""

from enum import Enum, auto
from typing import Optional


class Direction(Enum):
    N = 0
    NE = 1
    E = 2
    SE = 3
    S = 4
    SW = 5
    W = 6
    NW = 7

    NORTH = N
    NORTHEAST = NE
    EAST = E
    SOUTHEAST = SE
    SOUTH = S
    SOUTHWEST = SW
    WEST = W
    NORTHWEST = NW

    @property
    def offset(self) -> tuple[int, int]:
        """Get (dx, dy) offset for this direction."""
        offsets = {
            Direction.N: (0, -1),
            Direction.NE: (1, -1),
            Direction.E: (1, 0),
            Direction.SE: (1, 1),
            Direction.S: (0, 1),
            Direction.SW: (-1, 1),
            Direction.W: (-1, 0),
            Direction.NW: (-1, -1),
        }
        return offsets[self]

    @property
    def opposite(self) -> "Direction":
        """Get the opposite direction."""
        opposites = {
            Direction.N: Direction.S,
            Direction.S: Direction.N,
            Direction.E: Direction.W,
            Direction.W: Direction.E,
            Direction.NE: Direction.SW,
            Direction.SW: Direction.NE,
            Direction.SE: Direction.NW,
            Direction.NW: Direction.SE,
        }
        return opposites[self]

    @property
    def is_cardinal(self) -> bool:
        """Check if this is a cardinal direction (N/S/E/W)."""
        return self in {Direction.N, Direction.S, Direction.E, Direction.W}

    @property
    def is_diagonal(self) -> bool:
        """Check if this is a diagonal direction (NE/SE/SW/NW)."""
        return self in {Direction.NE, Direction.SE, Direction.SW, Direction.NW}

    @property
    def angle_degrees(self) -> float:
        """Get angle in degrees (0° = East, 90° = North)."""
        angles = {
            Direction.E: 0.0,
            Direction.NE: 45.0,
            Direction.N: 90.0,
            Direction.NW: 135.0,
            Direction.W: 180.0,
            Direction.SW: 225.0,
            Direction.S: 270.0,
            Direction.SE: 315.0,
        }
        return angles[self]

    @classmethod
    def from_offset(cls, dx: int, dy: int) -> Optional["Direction"]:
        """Get direction from offset vector. Returns None for (0, 0)."""
        if dx == 0 and dy == 0:
            return None

        # Normalize to -1, 0, 1 range
        dx_norm = max(-1, min(1, dx)) if dx != 0 else 0
        dy_norm = max(-1, min(1, dy)) if dy != 0 else 0

        for direction in cls:
            if direction.offset == (dx_norm, dy_norm):
                return direction
        return None

    @classmethod
    def from_angle(cls, degrees: float) -> "Direction":
        """Get nearest direction from angle in degrees."""
        normalized = degrees % 360
        angles = {
            Direction.E: 0.0,
            Direction.NE: 45.0,
            Direction.N: 90.0,
            Direction.NW: 135.0,
            Direction.W: 180.0,
            Direction.SW: 225.0,
            Direction.S: 270.0,
            Direction.SE: 315.0,
        }

        best_dir = Direction.E
        min_diff = 360.0

        for direction, angle in angles.items():
            diff = abs(normalized - angle)
            diff = min(diff, 360 - diff)
            if diff < min_diff:
                min_diff = diff
                best_dir = direction

        return best_dir

    def to_angle(self) -> float:
        angles = {
            Direction.E: 0.0,
            Direction.SE: 45.0,
            Direction.S: 90.0,
            Direction.SW: 135.0,
            Direction.W: 180.0,
            Direction.NW: 225.0,
            Direction.N: 270.0,
            Direction.NE: 315.0,
        }
        return angles[self]

    def to_unit_facing(self) -> float:
        return self.to_angle()

    @classmethod
    def get_cardinals(cls) -> list:
        """Get all cardinal directions in order [N, E, S, W]."""
        return [cls.N, cls.E, cls.S, cls.W]

    @classmethod
    def get_diagonals(cls) -> list:
        """Get all diagonal directions in order [NE, SE, SW, NW]."""
        return [cls.NE, cls.SE, cls.SW, cls.NW]

    @classmethod
    def get_all(cls) -> list:
        """Get all 8 directions starting from N clockwise."""
        return [cls.N, cls.NE, cls.E, cls.SE, cls.S, cls.SW, cls.W, cls.NW]

    def rotate_cw(self, steps: int = 1) -> "Direction":
        """Rotate clockwise by number of 45° steps."""
        all_dirs = self.get_all()
        idx = all_dirs.index(self)
        new_idx = (idx + steps) % 8
        return all_dirs[new_idx]

    def rotate_ccw(self, steps: int = 1) -> "Direction":
        """Rotate counter-clockwise by number of 45° steps."""
        return self.rotate_cw(-steps)

    def __repr__(self) -> str:
        return f"Direction.{self.name}"
