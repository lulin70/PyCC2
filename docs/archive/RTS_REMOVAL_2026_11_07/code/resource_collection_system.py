"""Resource Collection System - Sprint 2 Day 8 FUNC-04.

Manages harvester AI: unit → resource source → collect → return to base → drop off → repeat.
Integrates with ResourceManager for resource deposit and Unit state machine for COLLECTING state.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pycc2.domain.entities.unit import UnitState
from pycc2.domain.systems.resource_manager import ResourceManager
from pycc2.domain.value_objects.tile_coord import TileCoord

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit

logger = logging.getLogger(__name__)


class ResourceCollectionSystem:
    """System managing harvester collection cycles.
    
    Cycle: IDLE → move to resource → COLLECTING (harvest) → move to base → drop off → repeat
    
    Attributes:
        collection_rate: Resource collected per tick (default 2.0/tick)
        collection_distance: Max distance to collect from source (default 1.5 tiles)
        drop_off_distance: Max distance to drop off at base (default 2.0 tiles)
    """
    
    def __init__(
        self,
        collection_rate: float = 2.0,
        collection_distance: float = 1.5,
        drop_off_distance: float = 2.0,
    ):
        """Initialize resource collection system.
        
        Args:
            collection_rate: Resource per tick when collecting
            collection_distance: Max distance to start collecting
            drop_off_distance: Max distance to drop off resources
        """
        self.collection_rate = collection_rate
        self.collection_distance = collection_distance
        self.drop_off_distance = drop_off_distance
        self.resource_manager = ResourceManager()
    
    def update_harvester(self, unit: Unit, delta_time: float) -> None:
        """Update harvester unit AI (called every tick).
        
        Args:
            unit: Harvester unit to update
            delta_time: Time elapsed since last update (seconds)
        """
        if not unit.is_harvester or unit.state_machine.current_state == UnitState.DEAD:
            return
        
        current_state = unit.state_machine.current_state
        
        # Cycle phase 1: Move to resource source
        if current_state == UnitState.IDLE and unit.carrying_resource_amount == 0:
            self._start_move_to_resource(unit)
        
        # Cycle phase 2: Collect resource
        elif current_state == UnitState.MOVING and self._at_resource_source(unit):
            self._start_collecting(unit)
        
        elif current_state == UnitState.COLLECTING:
            self._collect_resource(unit)
        
        # Cycle phase 3: Return to base
        elif current_state == UnitState.COLLECTING and unit.carrying_resource_amount >= unit.max_resource_capacity:
            self._start_return_to_base(unit)
        
        # Cycle phase 4: Drop off at base
        elif current_state == UnitState.MOVING and self._at_base(unit) and unit.carrying_resource_amount > 0:
            self._drop_off_resource(unit)
    
    def _start_move_to_resource(self, unit: Unit) -> None:
        """Start moving to resource source.
        
        Args:
            unit: Harvester unit
        """
        if unit.resource_source_pos is None:
            logger.warning(f"Harvester {unit.id} has no resource source assigned")
            return
        
        unit.set_move_target(unit.resource_source_pos)
        unit.state_machine.change_state(UnitState.MOVING)
        logger.debug(f"Harvester {unit.id} moving to resource at {unit.resource_source_pos}")
    
    def _at_resource_source(self, unit: Unit) -> bool:
        """Check if unit is at resource source.
        
        Args:
            unit: Harvester unit
        
        Returns:
            True if within collection_distance of resource source
        """
        if unit.resource_source_pos is None:
            return False
        
        distance = unit.position.tile_position.octile_distance(unit.resource_source_pos)
        return distance <= self.collection_distance
    
    def _start_collecting(self, unit: Unit) -> None:
        """Start collecting resource.
        
        Args:
            unit: Harvester unit
        """
        unit.state_machine.change_state(UnitState.COLLECTING)
        logger.debug(f"Harvester {unit.id} started collecting {unit.resource_type}")
    
    def _collect_resource(self, unit: Unit) -> None:
        """Collect resource (called every tick while COLLECTING).
        
        Args:
            unit: Harvester unit
        """
        amount_to_collect = min(
            self.collection_rate,
            unit.max_resource_capacity - unit.carrying_resource_amount
        )
        
        unit.carrying_resource_amount += amount_to_collect
        logger.debug(
            f"Harvester {unit.id} collected {amount_to_collect} {unit.resource_type}. "
            f"Carrying: {unit.carrying_resource_amount}/{unit.max_resource_capacity}"
        )
        
        # When full, return to base
        if unit.carrying_resource_amount >= unit.max_resource_capacity:
            self._start_return_to_base(unit)
    
    def _start_return_to_base(self, unit: Unit) -> None:
        """Start returning to base for drop-off.
        
        Args:
            unit: Harvester unit
        """
        if unit.base_drop_off_pos is None:
            logger.warning(f"Harvester {unit.id} has no base drop-off position assigned")
            return
        
        unit.set_move_target(unit.base_drop_off_pos)
        unit.state_machine.change_state(UnitState.MOVING)
        logger.debug(f"Harvester {unit.id} returning to base at {unit.base_drop_off_pos}")
    
    def _at_base(self, unit: Unit) -> bool:
        """Check if unit is at base for drop-off.
        
        Args:
            unit: Harvester unit
        
        Returns:
            True if within drop_off_distance of base
        """
        if unit.base_drop_off_pos is None:
            return False
        
        distance = unit.position.tile_position.octile_distance(unit.base_drop_off_pos)
        return distance <= self.drop_off_distance
    
    def _drop_off_resource(self, unit: Unit) -> None:
        """Drop off resource at base and add to ResourceManager.
        
        Args:
            unit: Harvester unit
        """
        if unit.resource_type == "gold":
            self.resource_manager.add_gold(unit.carrying_resource_amount)
        elif unit.resource_type == "wood":
            self.resource_manager.add_wood(unit.carrying_resource_amount)
        else:
            logger.error(f"Unknown resource type: {unit.resource_type}")
        
        logger.info(
            f"Harvester {unit.id} dropped off {unit.carrying_resource_amount} {unit.resource_type} at base"
        )
        
        # Reset for next cycle
        unit.carrying_resource_amount = 0.0
        unit.state_machine.change_state(UnitState.IDLE)
        
        # Auto-restart cycle
        self._start_move_to_resource(unit)
