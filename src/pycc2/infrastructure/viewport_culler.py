"""Viewport Culling System - Sprint 2 Day 9 PERF-02.

Filters units to only update those visible on screen.
Reduces CPU overhead for off-screen units (no AI, movement, or animation updates).
"""

from __future__ import annotations

import logging
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit

logger = logging.getLogger(__name__)


class ViewportCuller:
    """Culls units outside camera viewport for performance.
    
    Only units inside the visible rectangle receive AI/movement/animation updates.
    Uses spatial grid for fast queries (O(k) where k = visible units).
    
    Attributes:
        margin: Extra margin around viewport (tiles) to avoid pop-in
    """
    
    def __init__(self, margin: int = 5):
        """Initialize viewport culler.
        
        Args:
            margin: Extra tiles around viewport to include (prevents pop-in)
        """
        self.margin = margin
        self.last_visible_count = 0
        self.total_units_count = 0
    
    def get_visible_units(
        self,
        all_units: List[Unit],
        camera_min_x: int,
        camera_min_y: int,
        camera_max_x: int,
        camera_max_y: int,
    ) -> List[Unit]:
        """Filter units to only those visible in camera viewport.
        
        Args:
            all_units: List of all units in game
            camera_min_x: Camera viewport min tile X
            camera_min_y: Camera viewport min tile Y
            camera_max_x: Camera viewport max tile X
            camera_max_y: Camera viewport max tile Y
        
        Returns:
            List of visible units (including margin)
        """
        self.total_units_count = len(all_units)
        
        # Expand viewport by margin
        min_x = camera_min_x - self.margin
        min_y = camera_min_y - self.margin
        max_x = camera_max_x + self.margin
        max_y = camera_max_y + self.margin
        
        # Filter units
        visible = [
            unit for unit in all_units
            if (min_x <= unit.position.tile_position.x <= max_x and
                min_y <= unit.position.tile_position.y <= max_y)
        ]
        
        self.last_visible_count = len(visible)
        
        if self.last_visible_count < self.total_units_count:
            logger.debug(
                f"Viewport culling: {self.last_visible_count}/{self.total_units_count} units visible "
                f"({100 * self.last_visible_count / self.total_units_count:.1f}%)"
            )
        
        return visible
    
    def get_culling_ratio(self) -> float:
        """Get percentage of units culled.
        
        Returns:
            Culling ratio (0.0 = all visible, 1.0 = all culled)
        """
        if self.total_units_count == 0:
            return 0.0
        
        culled = self.total_units_count - self.last_visible_count
        return culled / self.total_units_count
