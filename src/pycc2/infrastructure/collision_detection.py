"""Optimized Collision Detection System - Sprint 3 Day 14 PERF-03.

Two-phase collision detection for performance:
1. Broad Phase: Spatial grid (AABB) to quickly eliminate non-colliding pairs
2. Narrow Phase: Precise circle-circle collision checks

Target: 100 units collision detection < 3ms
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class CircleCollider:
    """Circle collider for collision detection.

    Attributes:
        id: Unique identifier
        center_x: X position of center
        center_y: Y position of center
        radius: Collision radius
    """

    id: str
    center_x: float
    center_y: float
    radius: float

    def aabb(self) -> tuple[float, float, float, float]:
        """Get axis-aligned bounding box.

        Returns:
            (min_x, min_y, max_x, max_y)
        """
        return (
            self.center_x - self.radius,
            self.center_y - self.radius,
            self.center_x + self.radius,
            self.center_y + self.radius,
        )

    def intersects(self, other: CircleCollider) -> bool:
        """Check circle-circle intersection.

        Args:
            other: Another circle collider

        Returns:
            True if circles intersect
        """
        dx = other.center_x - self.center_x
        dy = other.center_y - self.center_y
        distance_sq = dx * dx + dy * dy
        radius_sum = self.radius + other.radius
        return distance_sq < (radius_sum * radius_sum)

    def distance_to(self, other: CircleCollider) -> float:
        """Calculate distance between centers.

        Args:
            other: Another circle collider

        Returns:
            Distance in pixels
        """
        dx = other.center_x - self.center_x
        dy = other.center_y - self.center_y
        return math.sqrt(dx * dx + dy * dy)


class CollisionDetectionSystem:
    """Optimized collision detection using two-phase approach.

    Responsibilities:
    - Broad phase: Use spatial grid for AABB culling
    - Narrow phase: Precise circle-circle collision checks
    - Provide collision pairs and query methods

    Attributes:
        colliders: List of all colliders
        spatial_grid: Optional spatial grid for broad phase
        use_spatial_optimization: Whether to use spatial grid
    """

    def __init__(
        self,
        use_spatial_optimization: bool = True,
        grid_cell_size: int = 64,
    ):
        """Initialize collision detection system.

        Args:
            use_spatial_optimization: Enable spatial grid (default True)
            grid_cell_size: Size of spatial grid cells (default 64 pixels)
        """
        self.colliders: list[CircleCollider] = []
        self.use_spatial_optimization = use_spatial_optimization
        self.grid_cell_size = grid_cell_size

        # Spatial grid will be lazily initialized
        self._spatial_grid: object | None = None

    def add_collider(self, collider: CircleCollider) -> None:
        """Add collider to system.

        Args:
            collider: Circle collider to add
        """
        self.colliders.append(collider)

    def remove_collider(self, collider_id: str) -> bool:
        """Remove collider from system.

        Args:
            collider_id: ID of collider to remove

        Returns:
            True if collider was removed
        """
        for i, c in enumerate(self.colliders):
            if c.id == collider_id:
                self.colliders.pop(i)
                return True
        return False

    def clear(self) -> None:
        """Remove all colliders."""
        self.colliders.clear()
        self._spatial_grid = None

    def detect_collisions_naive(self) -> list[tuple[CircleCollider, CircleCollider]]:
        """Naive O(n²) collision detection (for comparison).

        Returns:
            List of colliding collider pairs
        """
        collisions = []
        for i in range(len(self.colliders)):
            for j in range(i + 1, len(self.colliders)):
                c1 = self.colliders[i]
                c2 = self.colliders[j]
                if c1.intersects(c2):
                    collisions.append((c1, c2))
        return collisions

    def detect_collisions_optimized(self) -> list[tuple[CircleCollider, CircleCollider]]:
        """Optimized collision detection using spatial partitioning.

        Returns:
            List of colliding collider pairs
        """
        if not self.colliders:
            return []

        # Build spatial hash map (simple grid)
        # Grid cell size: max_radius * 2 for safety
        max_radius = max(c.radius for c in self.colliders)
        cell_size = max(self.grid_cell_size, int(max_radius * 2))

        # Map: (cell_x, cell_y) -> [collider_indices]
        grid: dict[tuple[int, int], list[int]] = {}

        # Broad phase: Insert colliders into grid cells
        for idx, collider in enumerate(self.colliders):
            min_x, min_y, max_x, max_y = collider.aabb()

            # Calculate grid cell range
            min_cell_x = int(min_x // cell_size)
            min_cell_y = int(min_y // cell_size)
            max_cell_x = int(max_x // cell_size)
            max_cell_y = int(max_y // cell_size)

            # Insert into all overlapping cells
            for cy in range(min_cell_y, max_cell_y + 1):
                for cx in range(min_cell_x, max_cell_x + 1):
                    if (cx, cy) not in grid:
                        grid[(cx, cy)] = []
                    grid[(cx, cy)].append(idx)

        # Narrow phase: Check collisions within each cell
        checked_pairs: set[tuple[int, int]] = set()
        collisions: list[tuple[CircleCollider, CircleCollider]] = []

        for cell_colliders in grid.values():
            # Check all pairs within this cell
            for i in range(len(cell_colliders)):
                for j in range(i + 1, len(cell_colliders)):
                    idx1 = cell_colliders[i]
                    idx2 = cell_colliders[j]

                    # Ensure canonical order (smaller idx first)
                    pair = (min(idx1, idx2), max(idx1, idx2))

                    # Skip if already checked
                    if pair in checked_pairs:
                        continue
                    checked_pairs.add(pair)

                    # Precise collision check
                    c1 = self.colliders[idx1]
                    c2 = self.colliders[idx2]
                    if c1.intersects(c2):
                        collisions.append((c1, c2))

        return collisions

    def detect_collisions(self) -> list[tuple[CircleCollider, CircleCollider]]:
        """Detect all collisions using optimal method.

        Returns:
            List of colliding collider pairs
        """
        if self.use_spatial_optimization:
            return self.detect_collisions_optimized()
        else:
            return self.detect_collisions_naive()

    def query_collisions_for(self, collider_id: str) -> list[CircleCollider]:
        """Query all colliders colliding with given collider.

        Args:
            collider_id: ID of collider to query

        Returns:
            List of colliding colliders
        """
        target = None
        for c in self.colliders:
            if c.id == collider_id:
                target = c
                break

        if not target:
            return []

        results = []
        for c in self.colliders:
            if c.id != collider_id and target.intersects(c):
                results.append(c)

        return results

    def query_point(self, x: float, y: float) -> list[CircleCollider]:
        """Query colliders containing a point.

        Args:
            x: Point X coordinate
            y: Point Y coordinate

        Returns:
            List of colliders containing the point
        """
        results = []
        for c in self.colliders:
            dx = x - c.center_x
            dy = y - c.center_y
            if (dx * dx + dy * dy) <= (c.radius * c.radius):
                results.append(c)
        return results

    def query_radius(
        self,
        center_x: float,
        center_y: float,
        radius: float,
    ) -> list[CircleCollider]:
        """Query colliders within radius of a point.

        Args:
            center_x: Center X coordinate
            center_y: Center Y coordinate
            radius: Query radius

        Returns:
            List of colliders within radius
        """
        results = []

        for c in self.colliders:
            dx = c.center_x - center_x
            dy = c.center_y - center_y
            distance_sq = dx * dx + dy * dy

            # Check if collider is within radius (including its own radius)
            check_radius = radius + c.radius
            if distance_sq <= (check_radius * check_radius):
                results.append(c)

        return results

    def get_statistics(self) -> dict:
        """Get system statistics for profiling.

        Returns:
            Dict with statistics
        """
        return {
            "total_colliders": len(self.colliders),
            "use_spatial_optimization": self.use_spatial_optimization,
            "grid_cell_size": self.grid_cell_size,
        }
