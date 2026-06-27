"""Projectile Entity

Represents an in-flight projectile (bullet, grenade, etc.)
with position, velocity, and impact calculation.
"""

import math
from dataclasses import dataclass
from enum import Enum, auto


class ProjectileType(Enum):
    """Types of projectiles."""

    BULLET = auto()
    GRENADE = auto()
    MORTAR = auto()
    ROCKET = auto()


@dataclass
class Projectile:
    """In-flight projectile entity.

    Attributes:
        projectile_id: Unique identifier
        proj_type: Type of projectile
        shooter_id: ID of the firing unit
        target_id: ID of target unit (if targeted)
        start_pos: Starting position (world coordinates)
        target_pos: Target position or current position
        current_pos: Current flight position
        damage: Base damage on impact
        speed: Flight speed (tiles per second)
        is_active: Whether projectile is still in flight
        has_hit: Whether projectile has hit something

    """

    projectile_id: str
    proj_type: ProjectileType
    shooter_id: str
    target_id: str | None
    start_pos: tuple[float, float]
    target_pos: tuple[float, float]
    current_pos: tuple[float, float]
    damage: float
    speed: float = 10.0
    is_active: bool = True
    has_hit: bool = False

    @property
    def distance_traveled(self) -> float:
        """Calculate total distance traveled from start."""
        dx = self.current_pos[0] - self.start_pos[0]
        dy = self.current_pos[1] - self.start_pos[1]
        return math.sqrt(dx**2 + dy**2)

    @property
    def distance_remaining(self) -> float:
        """Calculate remaining distance to target."""
        dx = self.target_pos[0] - self.current_pos[0]
        dy = self.target_pos[1] - self.current_pos[1]
        return math.sqrt(dx**2 + dy**2)

    @property
    def progress(self) -> float:
        """Get flight progress as 0.0 to 1.0."""
        total = self.distance_traveled + self.distance_remaining
        if total == 0:
            return 1.0
        return self.distance_traveled / total

    def update(self, dt: float) -> bool:
        """Update projectile position.

        Args:
            dt: Delta time in seconds

        Returns:
            True if projectile reached target this frame

        """
        if not self.is_active or self.has_hit:
            return False

        if self.distance_remaining < 0.1:
            self.current_pos = self.target_pos
            self.has_hit = True
            self.is_active = False
            return True

        direction_x = self.target_pos[0] - self.current_pos[0]
        direction_y = self.target_pos[1] - self.current_pos[1]
        dist = math.sqrt(direction_x**2 + direction_y**2)

        if dist > 0:
            direction_x /= dist
            direction_y /= dist

        move_dist = self.speed * dt
        new_dist = min(move_dist, self.distance_remaining)

        self.current_pos = (
            self.current_pos[0] + direction_x * new_dist,
            self.current_pos[1] + direction_y * new_dist,
        )

        if self.distance_remaining <= 0.1:
            self.has_hit = True
            self.is_active = False
            return True

        return False

    def mark_hit(self) -> None:
        """Mark projectile as having hit target."""
        self.has_hit = True
        self.is_active = False

    def mark_miss(self) -> None:
        """Mark projectile as missed (continue until out of range)."""
        self.has_hit = False

    def __repr__(self) -> str:
        status = "ACTIVE" if self.is_active else ("HIT" if self.has_hit else "MISSED")
        return (
            f"Projectile(id={self.projectile_id}, type={self.proj_type.name}, "
            f"status={status}, progress={self.progress:.1%})"
        )
