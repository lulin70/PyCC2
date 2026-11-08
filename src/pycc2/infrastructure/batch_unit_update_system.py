"""Batch Unit Update System - Sprint 2 Day 9 PERF-02.

Optimizes unit AI updates by batching operations and using spatial grid + viewport culling.
Target: 100 units updated in <5ms using spatial indexing and culling.
"""

from __future__ import annotations

import logging
import time
from typing import List, TYPE_CHECKING

from pycc2.infrastructure.spatial_grid import SpatialGrid
from pycc2.infrastructure.viewport_culler import ViewportCuller

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit

logger = logging.getLogger(__name__)


class BatchUnitUpdateSystem:
    """Batch updates units with spatial optimization.
    
    Combines spatial grid and viewport culling for maximum performance:
    1. Spatial grid: Fast neighbor queries O(k) instead of O(n²)
    2. Viewport culling: Only update visible units
    3. Batch updates: Process units in chunks to improve cache locality
    
    Performance target: 100 units in <5ms
    
    Attributes:
        spatial_grid: Spatial grid for fast queries
        viewport_culler: Viewport culling system
        batch_size: Number of units per batch (for cache locality)
    """
    
    def __init__(
        self,
        cell_size: int = 16,
        world_width: int = 256,
        world_height: int = 256,
        viewport_margin: int = 5,
        batch_size: int = 50,
    ):
        """Initialize batch update system.
        
        Args:
            cell_size: Spatial grid cell size (tiles)
            world_width: World width (tiles)
            world_height: World height (tiles)
            viewport_margin: Extra tiles around viewport
            batch_size: Units per batch for processing
        """
        self.spatial_grid = SpatialGrid(
            cell_size=cell_size,
            width=world_width,
            height=world_height,
        )
        self.viewport_culler = ViewportCuller(margin=viewport_margin)
        self.batch_size = batch_size
        
        # Performance tracking
        self.last_update_time_ms = 0.0
        self.last_updated_count = 0
    
    def rebuild_spatial_grid(self, units: List[Unit]) -> None:
        """Rebuild spatial grid with all units.
        
        Args:
            units: List of all units
        """
        self.spatial_grid.rebuild(units)
        logger.info(f"Spatial grid rebuilt with {len(units)} units")
    
    def update_units_batch(
        self,
        all_units: List[Unit],
        camera_min_x: int,
        camera_min_y: int,
        camera_max_x: int,
        camera_max_y: int,
        delta_time: float,
        update_func=None,
    ) -> dict:
        """Update visible units in batches with spatial optimization.
        
        Args:
            all_units: List of all units in game
            camera_min_x: Camera viewport min tile X
            camera_min_y: Camera viewport min tile Y
            camera_max_x: Camera viewport max tile X
            camera_max_y: Camera viewport max tile Y
            delta_time: Time elapsed since last update (seconds)
            update_func: Optional custom update function(unit, delta_time)
        
        Returns:
            Dict with performance statistics
        """
        start_time = time.perf_counter()
        
        # Step 1: Viewport culling
        visible_units = self.viewport_culler.get_visible_units(
            all_units,
            camera_min_x,
            camera_min_y,
            camera_max_x,
            camera_max_y,
        )
        
        # Step 2: Update spatial grid for visible units
        for unit in visible_units:
            self.spatial_grid.update(unit)
        
        # Step 3: Batch update visible units
        updated_count = 0
        for i in range(0, len(visible_units), self.batch_size):
            batch = visible_units[i:i + self.batch_size]
            for unit in batch:
                if update_func:
                    update_func(unit, delta_time)
                else:
                    # Default: basic position update
                    pass
                updated_count += 1
        
        # Step 4: Track performance
        end_time = time.perf_counter()
        self.last_update_time_ms = (end_time - start_time) * 1000
        self.last_updated_count = updated_count
        
        # Performance statistics
        stats = {
            "total_units": len(all_units),
            "visible_units": len(visible_units),
            "updated_units": updated_count,
            "culling_ratio": self.viewport_culler.get_culling_ratio(),
            "update_time_ms": self.last_update_time_ms,
            "units_per_ms": updated_count / self.last_update_time_ms if self.last_update_time_ms > 0 else 0,
        }
        
        # Log performance warning if target not met
        if updated_count >= 100 and self.last_update_time_ms >= 5.0:
            logger.warning(
                f"Performance target missed: {updated_count} units in {self.last_update_time_ms:.2f}ms "
                f"(target: <5ms for 100 units)"
            )
        
        return stats
    
    def get_nearby_units(self, unit: Unit, range_cells: int = 1) -> List[Unit]:
        """Get units near given unit using spatial grid.
        
        Args:
            unit: Center unit
            range_cells: Cell range for neighbors
        
        Returns:
            List of nearby units
        """
        return self.spatial_grid.get_neighbors(unit, range_cells)
    
    def get_units_in_radius(self, center_tile, radius: float) -> List[Unit]:
        """Get units within radius of position.
        
        Args:
            center_tile: Center TileCoord
            radius: Search radius (tiles)
        
        Returns:
            List of units within radius
        """
        return self.spatial_grid.query_radius(center_tile, radius)
    
    def get_performance_stats(self) -> dict:
        """Get performance statistics.
        
        Returns:
            Dict with last update performance metrics
        """
        grid_stats = self.spatial_grid.get_statistics()
        
        return {
            "last_update_time_ms": self.last_update_time_ms,
            "last_updated_count": self.last_updated_count,
            "culling_ratio": self.viewport_culler.get_culling_ratio(),
            "spatial_grid": grid_stats,
        }
