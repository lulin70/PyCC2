"""
Vec2 Value Object - Immutable 2D Vector
"""

from __future__ import annotations

import math
from collections.abc import Iterator
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class Vec2:
    x: float = 0.0
    y: float = 0.0

    TILE_SIZE: ClassVar[float] = 48.0  # CC2 authentic: 48×48 pixel tiles

    @classmethod
    def zero(cls) -> Vec2:
        return cls(0.0, 0.0)

    @classmethod
    def one(cls) -> Vec2:
        return cls(1.0, 1.0)

    @classmethod
    def from_tile(cls, tile_x: float, tile_y: float) -> Vec2:
        return cls(tile_x * cls.TILE_SIZE, tile_y * cls.TILE_SIZE)

    @property
    def length(self) -> float:
        return math.sqrt(self.x**2 + self.y**2)

    @property
    def length_squared(self) -> float:
        return self.x**2 + self.y**2

    @property
    def normalized(self) -> Vec2:
        mag = self.length
        if mag == 0:
            return Vec2.zero()
        return Vec2(self.x / mag, self.y / mag)

    @property
    def perpendicular(self) -> Vec2:
        return Vec2(-self.y, self.x)

    def distance_to(self, other: Vec2) -> float:
        return (self - other).length

    def dot(self, other: Vec2) -> float:
        return self.x * other.x + self.y * other.y

    def cross(self, other: Vec2) -> float:
        return self.x * other.y - self.y * other.x

    def lerp(self, other: Vec2, t: float) -> Vec2:
        t = max(0.0, min(1.0, t))
        return Vec2(
            self.x + (other.x - self.x) * t,
            self.y + (other.y - self.y) * t,
        )

    def angle_to(self, other: Vec2) -> float:
        dot_product = self.dot(other)
        det = self.cross(other)
        return math.atan2(det, dot_product)

    def to_tile_coord(self) -> tuple[int, int]:
        return (int(self.x / self.TILE_SIZE), int(self.y / self.TILE_SIZE))

    def clamp_length(self, max_length: float) -> Vec2:
        if self.length_squared <= max_length**2:
            return self
        return self.normalized * max_length

    def rotate(self, radians: float) -> Vec2:
        cos_a = math.cos(radians)
        sin_a = math.sin(radians)
        return Vec2(
            self.x * cos_a - self.y * sin_a,
            self.x * sin_a + self.y * cos_a,
        )

    def __add__(self, other: Vec2) -> Vec2:
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vec2) -> Vec2:
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float | int) -> Vec2:
        return Vec2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float | int) -> Vec2:
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float | int) -> Vec2:
        if scalar == 0:
            raise ValueError("Cannot divide by zero")
        return Vec2(self.x / scalar, self.y / scalar)

    def __neg__(self) -> Vec2:
        return Vec2(-self.x, -self.y)

    def __abs__(self) -> Vec2:
        return Vec2(abs(self.x), abs(self.y))

    def __iter__(self) -> Iterator[float]:
        yield self.x
        yield self.y
