"""Building Placement System - Sprint 3 Day 11 FUNC-05.

Validates building placement legality: collision detection, terrain checks, and resource validation.
Integrates with ResourceManager to consume resources during construction.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from pycc2.domain.entities.building import Building, BuildingState, create_building, BuildingType
from pycc2.domain.systems.resource_manager import ResourceManager
from pycc2.domain.value_objects.tile_coord import TileCoord

logger = logging.getLogger(__name__)


class PlacementError(Exception):
    """Raised when building placement is invalid."""
    pass


class BuildingPlacementSystem:
    """Manages building placement validation and construction lifecycle.
    
    Responsibilities:
    - Validate placement legality (collision, terrain, boundaries)
    - Consume resources via ResourceManager
    - Update building construction progress
    - Track all buildings in the game
    
    Attributes:
        buildings: List of all buildings
        map_width: Map width in tiles
        map_height: Map height in tiles
        resource_manager: ResourceManager singleton
    """
    
    def __init__(self, map_width: int, map_height: int, resource_manager: Optional[ResourceManager] = None):
        """Initialize placement system.
        
        Args:
            map_width: Map width in tiles
            map_height: Map height in tiles
            resource_manager: ResourceManager instance (or None to create default)
        """
        self.buildings: List[Building] = []
        self.map_width = map_width
        self.map_height = map_height
        self.resource_manager = resource_manager or ResourceManager()
    
    def can_place_building(self, building: Building) -> tuple[bool, str]:
        """Check if building can be placed at its current position.
        
        Validates:
        1. Map boundaries (building fully inside map)
        2. Terrain (all tiles are buildable - simplified: all passable)
        3. Collision (no overlap with existing buildings)
        
        Args:
            building: Building to validate
        
        Returns:
            (is_valid, error_message) tuple
        """
        # Check map boundaries
        if building.position.x < 0 or building.position.y < 0:
            return False, "Building outside map (negative coordinates)"
        
        if building.position.x + building.width > self.map_width:
            return False, f"Building exceeds map width ({building.position.x + building.width} > {self.map_width})"
        
        if building.position.y + building.height > self.map_height:
            return False, f"Building exceeds map height ({building.position.y + building.height} > {self.map_height})"
        
        # Check collision with existing buildings
        for existing in self.buildings:
            if existing.state == BuildingState.DESTROYED:
                continue  # Skip destroyed buildings
            
            if building.overlaps_with(existing):
                return False, f"Building overlaps with existing building {existing.id}"
        
        # Terrain checks would go here (simplified: assume all tiles buildable)
        
        return True, ""
    
    def place_building(
        self,
        building_id: str,
        building_type: BuildingType,
        position: TileCoord,
        owner_faction: str = "PLAYER",
        auto_start: bool = False,
    ) -> Building:
        """Place and optionally start building construction.
        
        Args:
            building_id: Unique building ID
            building_type: Type of building
            position: Top-left tile position
            owner_faction: Owner faction
            auto_start: If True, start construction immediately (consumes resources)
        
        Returns:
            Building instance in PLANNING or CONSTRUCTING state
        
        Raises:
            PlacementError: If placement is invalid
        """
        # Create building entity
        building = create_building(building_id, building_type, position, owner_faction)
        
        # Validate placement
        can_place, error = self.can_place_building(building)
        if not can_place:
            raise PlacementError(error)
        
        # Add to tracking list
        self.buildings.append(building)
        logger.info(f"Placed building {building_id} ({building_type.name}) at {position}")
        
        # Auto-start if requested
        if auto_start:
            self.start_construction(building)
        
        return building
    
    def start_construction(self, building: Building) -> None:
        """Start building construction (consumes resources).
        
        Args:
            building: Building to start (must be in PLANNING state)
        
        Raises:
            PlacementError: If building not in PLANNING state or insufficient resources
        """
        if building.state != BuildingState.PLANNING:
            raise PlacementError(f"Cannot start construction from {building.state}")
        
        # Check resources
        cost = building.cost
        if not self.resource_manager.can_afford(cost.gold, cost.wood, cost.power):
            resources = self.resource_manager.get_resources()
            raise PlacementError(
                f"Insufficient resources: need {cost.gold}g/{cost.wood}w/{cost.power}p, "
                f"have {resources['gold']}g/{resources['wood']}w/{resources['power']}/{resources['max_power']}p"
            )
        
        # Consume resources
        success = (
            self.resource_manager.consume_gold(cost.gold)
            and self.resource_manager.consume_wood(cost.wood)
            and self.resource_manager.consume_power(cost.power)
        )
        
        if not success:
            raise PlacementError("Resource consumption failed (race condition)")
        
        # Start construction
        building.start_construction()
        logger.info(f"Started construction of {building.id}")
    
    def update_constructions(self, delta_time: float) -> List[Building]:
        """Update all buildings under construction.
        
        Args:
            delta_time: Time elapsed since last update (seconds)
        
        Returns:
            List of buildings that completed construction this frame
        """
        completed = []
        
        for building in self.buildings:
            if building.is_constructing():
                was_constructing = True
                building.update_construction(delta_time)
                
                if building.is_completed() and was_constructing:
                    completed.append(building)
                    logger.info(f"Building {building.id} construction completed")
        
        return completed
    
    def get_building_by_id(self, building_id: str) -> Optional[Building]:
        """Get building by ID.
        
        Args:
            building_id: Building ID
        
        Returns:
            Building instance or None if not found
        """
        for building in self.buildings:
            if building.id == building_id:
                return building
        return None
    
    def remove_building(self, building_id: str) -> bool:
        """Remove building from tracking list.
        
        Args:
            building_id: Building ID to remove
        
        Returns:
            True if building was removed, False if not found
        """
        for i, building in enumerate(self.buildings):
            if building.id == building_id:
                self.buildings.pop(i)
                logger.info(f"Removed building {building_id}")
                return True
        return False
    
    def get_buildings_at(self, position: TileCoord) -> List[Building]:
        """Get all buildings occupying a specific tile.
        
        Args:
            position: Tile position
        
        Returns:
            List of buildings at this position
        """
        result = []
        for building in self.buildings:
            if building.state == BuildingState.DESTROYED:
                continue
            
            occupied_tiles = building.get_occupied_tiles()
            if position in occupied_tiles:
                result.append(building)
        
        return result
