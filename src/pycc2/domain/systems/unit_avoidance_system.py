"""Unit Avoidance System - Sprint 3 Day 12 BUG-P1-03.

Simple avoidance mechanism to prevent units from blocking each other during movement.
Uses velocity vector adjustment based on collision detection.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Vec2Simple:
    """Simple 2D vector for avoidance calculations."""

    x: float
    y: float

    def length(self) -> float:
        """Calculate vector magnitude."""
        return math.sqrt(self.x**2 + self.y**2)

    def normalize(self) -> Vec2Simple:
        """Return normalized unit vector."""
        mag = self.length()
        if mag < 0.001:
            return Vec2Simple(0.0, 0.0)
        return Vec2Simple(self.x / mag, self.y / mag)

    def __add__(self, other: Vec2Simple) -> Vec2Simple:
        return Vec2Simple(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vec2Simple) -> Vec2Simple:
        return Vec2Simple(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Vec2Simple:
        return Vec2Simple(self.x * scalar, self.y * scalar)


@dataclass
class SimpleUnit:
    """Simplified unit for avoidance system.

    Attributes:
        id: Unit identifier
        position: Current position (x, y)
        velocity: Current velocity vector (pixels/second)
        radius: Collision radius (pixels)
    """

    id: str
    position: Vec2Simple
    velocity: Vec2Simple
    radius: float = 16.0  # Default unit radius


class UnitAvoidanceSystem:
    """Simple avoidance system using velocity adjustment.

    Algorithm:
    1. Detect nearby units within avoidance distance
    2. Calculate separation vector (away from neighbors)
    3. Adjust velocity to blend original + separation

    Attributes:
        avoidance_distance: Distance to start avoiding (pixels)
        avoidance_strength: Strength of avoidance force (0.0-1.0)
        max_neighbors: Maximum neighbors to consider per unit
    """

    def __init__(
        self,
        avoidance_distance: float = 48.0,
        avoidance_strength: float = 0.3,
        max_neighbors: int = 5,
    ):
        """Initialize avoidance system.

        Args:
            avoidance_distance: Distance to start avoiding (pixels)
            avoidance_strength: Strength of avoidance force (0.0-1.0)
            max_neighbors: Maximum neighbors to consider per unit
        """
        self.avoidance_distance = avoidance_distance
        self.avoidance_strength = avoidance_strength
        self.max_neighbors = max_neighbors

    def detect_collisions(self, units: list[SimpleUnit]) -> list[tuple[str, str]]:
        """Detect all unit-unit collisions.

        Args:
            units: List of units to check

        Returns:
            List of (unit_id1, unit_id2) collision pairs
        """
        collisions = []

        for i in range(len(units)):
            for j in range(i + 1, len(units)):
                unit1 = units[i]
                unit2 = units[j]

                # Calculate distance
                dx = unit2.position.x - unit1.position.x
                dy = unit2.position.y - unit1.position.y
                distance = math.sqrt(dx**2 + dy**2)

                # Check collision (sum of radii)
                if distance < (unit1.radius + unit2.radius):
                    collisions.append((unit1.id, unit2.id))

        return collisions

    def calculate_avoidance_velocity(
        self,
        unit: SimpleUnit,
        neighbors: list[SimpleUnit],
    ) -> Vec2Simple:
        """Calculate avoidance velocity for a unit.

        Args:
            unit: Unit to calculate avoidance for
            neighbors: Nearby units to avoid

        Returns:
            Avoidance velocity vector
        """
        if not neighbors:
            return Vec2Simple(0.0, 0.0)

        # Calculate separation vector (average away from neighbors)
        separation = Vec2Simple(0.0, 0.0)
        count = 0

        for neighbor in neighbors[: self.max_neighbors]:
            # Vector from neighbor to unit
            dx = unit.position.x - neighbor.position.x
            dy = unit.position.y - neighbor.position.y
            distance = math.sqrt(dx**2 + dy**2)

            if distance < self.avoidance_distance and distance > 0.001:
                # Weight by inverse distance (closer = stronger)
                weight = 1.0 - (distance / self.avoidance_distance)
                separation.x += (dx / distance) * weight
                separation.y += (dy / distance) * weight
                count += 1

        if count == 0:
            return Vec2Simple(0.0, 0.0)

        # Average separation
        separation.x /= count
        separation.y /= count

        # Normalize and scale by avoidance strength
        separation_normalized = separation.normalize()
        return separation_normalized * self.avoidance_strength * 100.0  # Scale for velocity

    def update_velocities(self, units: list[SimpleUnit]) -> None:
        """Update all unit velocities with avoidance.

        Args:
            units: List of units to update
        """
        # Store avoidance adjustments separately
        avoidance_adjustments = {}

        for unit in units:
            # Find neighbors within avoidance distance
            neighbors = []
            for other in units:
                if other.id == unit.id:
                    continue

                dx = other.position.x - unit.position.x
                dy = other.position.y - unit.position.y
                distance = math.sqrt(dx**2 + dy**2)

                if distance < self.avoidance_distance:
                    neighbors.append(other)

            # Calculate avoidance (don't apply yet)
            avoidance_vel = self.calculate_avoidance_velocity(unit, neighbors)
            avoidance_adjustments[unit.id] = avoidance_vel

            logger.debug(
                f"Unit {unit.id}: avoidance=({avoidance_vel.x:.1f},{avoidance_vel.y:.1f}), "
                f"neighbors={len(neighbors)}"
            )

        # Apply avoidance adjustments (after all calculated)
        # Note: In real implementation, this would be applied during movement
        # For now, we temporarily store in a separate field or apply with damping

    def apply_velocity(
        self, unit: SimpleUnit, delta_time: float, avoidance_vel: Vec2Simple | None = None
    ) -> None:
        """Apply velocity to unit position with optional avoidance blend.

        Args:
            unit: Unit to update
            delta_time: Time step (seconds)
            avoidance_vel: Optional avoidance velocity to blend
        """
        if avoidance_vel is None:
            avoidance_vel = Vec2Simple(0.0, 0.0)

        # Blend original velocity with avoidance (for this frame only)
        effective_vel_x = unit.velocity.x + avoidance_vel.x
        effective_vel_y = unit.velocity.y + avoidance_vel.y

        unit.position.x += effective_vel_x * delta_time
        unit.position.y += effective_vel_y * delta_time

    def update(self, units: list[SimpleUnit], delta_time: float) -> None:
        """Update all units with avoidance and movement.

        Args:
            units: List of units
            delta_time: Time step (seconds)
        """
        # 1. Calculate avoidance velocities for all units
        avoidance_adjustments = {}

        for unit in units:
            # Find neighbors within avoidance distance
            neighbors = []
            for other in units:
                if other.id == unit.id:
                    continue

                dx = other.position.x - unit.position.x
                dy = other.position.y - unit.position.y
                distance = math.sqrt(dx**2 + dy**2)

                if distance < self.avoidance_distance:
                    neighbors.append(other)

            # Calculate avoidance
            avoidance_vel = self.calculate_avoidance_velocity(unit, neighbors)
            avoidance_adjustments[unit.id] = avoidance_vel

        # 2. Apply velocities to positions with avoidance blend
        for unit in units:
            avoidance_vel = avoidance_adjustments[unit.id]
            self.apply_velocity(unit, delta_time, avoidance_vel)
