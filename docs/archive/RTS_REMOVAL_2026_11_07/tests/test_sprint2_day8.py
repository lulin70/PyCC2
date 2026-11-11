"""Sprint 2 Day 8: FUNC-04 Resource Collection System Tests.

8 test cases covering:
- Resource manager (add/consume/validation)
- Harvester collection cycle (move → collect → return → drop-off)
- Edge cases (over-capacity, missing positions, invalid resources)
"""

import pytest
from unittest.mock import Mock

from pycc2.domain.entities.unit import UnitState
from pycc2.domain.state_machine import StateMachine
from pycc2.domain.systems.resource_collection_system import ResourceCollectionSystem
from pycc2.domain.systems.resource_manager import ResourceManager
from pycc2.domain.value_objects.tile_coord import TileCoord


@pytest.fixture(autouse=True)
def reset_resource_manager():
    """Reset ResourceManager singleton before each test."""
    manager = ResourceManager()
    manager.reset()
    yield
    manager.reset()


@pytest.fixture
def resource_manager():
    """Provide ResourceManager instance."""
    return ResourceManager()


@pytest.fixture
def harvester_unit():
    """Create a mock gold harvester unit for testing."""
    unit = Mock()
    unit.id = "harvester_1"
    unit.name = "Gold Miner"
    unit.is_harvester = True
    unit.resource_type = "gold"
    unit.carrying_resource_amount = 0.0
    unit.max_resource_capacity = 100.0
    unit.resource_source_pos = TileCoord(5, 5)  # Gold mine
    unit.base_drop_off_pos = TileCoord(15, 15)  # Base
    unit.move_target = None
    
    # Mock state machine
    unit.state_machine = Mock()
    unit.state_machine.current_state = UnitState.IDLE
    
    def change_state(new_state):
        unit.state_machine.current_state = new_state
    unit.state_machine.change_state = change_state
    
    # Mock position component
    unit.position = Mock()
    unit.position.tile_position = TileCoord(10, 10)
    
    # Mock set_move_target method
    def set_move_target(target):
        unit.move_target = target
    unit.set_move_target = set_move_target
    
    return unit


@pytest.fixture
def collection_system():
    """Provide ResourceCollectionSystem instance."""
    return ResourceCollectionSystem(collection_rate=10.0)  # 10/tick for faster testing


# === ResourceManager Tests (3 tests) ===


def test_resource_manager_singleton(resource_manager):
    """Test: ResourceManager is singleton (same instance)."""
    manager2 = ResourceManager()
    assert manager2 is resource_manager, "ResourceManager should be singleton"


def test_resource_manager_add_and_consume_gold(resource_manager):
    """Test: Add gold and consume for building."""
    resource_manager.add_gold(500.0)
    assert resource_manager.gold == 500.0
    
    success = resource_manager.consume_gold(200.0)
    assert success is True
    assert resource_manager.gold == 300.0
    
    # Try consuming more than available
    success = resource_manager.consume_gold(400.0)
    assert success is False
    assert resource_manager.gold == 300.0, "Gold should not change on failed consumption"


def test_resource_manager_can_afford(resource_manager):
    """Test: Check affordability for building costs."""
    resource_manager.add_gold(100.0)
    resource_manager.add_wood(50.0)
    
    # Affordable
    assert resource_manager.can_afford(gold_cost=50.0, wood_cost=30.0) is True
    
    # Not affordable (gold)
    assert resource_manager.can_afford(gold_cost=150.0, wood_cost=30.0) is False
    
    # Not affordable (wood)
    assert resource_manager.can_afford(gold_cost=50.0, wood_cost=60.0) is False


# === Harvester Collection Cycle Tests (5 tests) ===


def test_harvester_starts_move_to_resource(harvester_unit, collection_system):
    """Test: IDLE harvester starts moving to resource source."""
    harvester_unit.state_machine.change_state(UnitState.IDLE)
    harvester_unit.carrying_resource_amount = 0.0
    
    collection_system.update_harvester(harvester_unit, 0.1)
    
    assert harvester_unit.state_machine.current_state == UnitState.MOVING
    assert harvester_unit.move_target == harvester_unit.resource_source_pos


def test_harvester_collects_resource_at_source(harvester_unit, collection_system):
    """Test: Harvester collects resource when at source."""
    # Position at resource source
    harvester_unit.position.tile_position = TileCoord(5, 5)
    harvester_unit.state_machine.change_state(UnitState.MOVING)
    harvester_unit.carrying_resource_amount = 0.0
    
    # First update: transition to COLLECTING
    collection_system.update_harvester(harvester_unit, 0.1)
    assert harvester_unit.state_machine.current_state == UnitState.COLLECTING
    
    # Second update: collect resource
    collection_system.update_harvester(harvester_unit, 0.1)
    assert harvester_unit.carrying_resource_amount == 10.0, "Should collect 10.0 resource (collection_rate)"


def test_harvester_returns_to_base_when_full(harvester_unit, collection_system):
    """Test: Harvester returns to base when carrying capacity is full."""
    harvester_unit.position.tile_position = TileCoord(5, 5)
    harvester_unit.state_machine.change_state(UnitState.COLLECTING)
    harvester_unit.carrying_resource_amount = 95.0  # Almost full
    
    # Collect to full capacity
    collection_system.update_harvester(harvester_unit, 0.1)
    
    assert harvester_unit.state_machine.current_state == UnitState.MOVING
    assert harvester_unit.move_target == harvester_unit.base_drop_off_pos


def test_harvester_drops_off_resource_at_base(harvester_unit, collection_system, resource_manager):
    """Test: Harvester drops off resource at base and adds to ResourceManager."""
    # Position at base
    harvester_unit.position.tile_position = TileCoord(15, 15)
    harvester_unit.state_machine.change_state(UnitState.MOVING)
    harvester_unit.carrying_resource_amount = 100.0
    
    initial_gold = resource_manager.gold
    
    collection_system.update_harvester(harvester_unit, 0.1)
    
    assert resource_manager.gold == initial_gold + 100.0, "Gold should increase by 100"
    assert harvester_unit.carrying_resource_amount == 0.0, "Should reset carrying amount"
    assert harvester_unit.state_machine.current_state == UnitState.MOVING, "Should auto-restart cycle"


def test_harvester_full_collection_cycle(harvester_unit, collection_system, resource_manager):
    """Test: Complete harvester cycle (move → collect → return → drop-off → repeat)."""
    harvester_unit.state_machine.change_state(UnitState.IDLE)
    harvester_unit.carrying_resource_amount = 0.0
    
    # Phase 1: Start move to resource
    collection_system.update_harvester(harvester_unit, 0.1)
    assert harvester_unit.state_machine.current_state == UnitState.MOVING
    
    # Phase 2: Arrive at resource and start collecting
    harvester_unit.position.tile_position = TileCoord(5, 5)
    collection_system.update_harvester(harvester_unit, 0.1)
    assert harvester_unit.state_machine.current_state == UnitState.COLLECTING
    
    # Phase 3: Collect until full (10 updates at 10.0/tick = 100.0)
    for _ in range(10):
        collection_system.update_harvester(harvester_unit, 0.1)
    
    assert harvester_unit.carrying_resource_amount == 100.0
    assert harvester_unit.state_machine.current_state == UnitState.MOVING  # Returning to base
    
    # Phase 4: Drop off at base
    harvester_unit.position.tile_position = TileCoord(15, 15)
    collection_system.update_harvester(harvester_unit, 0.1)
    
    assert resource_manager.gold == 100.0
    assert harvester_unit.carrying_resource_amount == 0.0
    assert harvester_unit.state_machine.current_state == UnitState.MOVING  # Auto-restarted


# === Edge Cases (2 tests) ===


def test_harvester_handles_missing_resource_source(harvester_unit, collection_system, caplog):
    """Test: Harvester logs warning when resource_source_pos is None."""
    harvester_unit.resource_source_pos = None
    harvester_unit.state_machine.change_state(UnitState.IDLE)
    
    collection_system.update_harvester(harvester_unit, 0.1)
    
    assert "no resource source assigned" in caplog.text.lower()
    assert harvester_unit.state_machine.current_state == UnitState.IDLE  # Should not change state


def test_resource_manager_rejects_negative_amounts(resource_manager):
    """Test: ResourceManager raises error for negative amounts."""
    with pytest.raises(ValueError, match="Cannot add negative gold"):
        resource_manager.add_gold(-50.0)
    
    with pytest.raises(ValueError, match="Cannot add negative wood"):
        resource_manager.add_wood(-30.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
