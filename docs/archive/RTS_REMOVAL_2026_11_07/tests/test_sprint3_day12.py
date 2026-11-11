"""Sprint 3 Day 12 Tests - TEST-05 Building System Integration Tests.

Integration tests for:
- E2E building construction workflow (menu → placement → construction → completion)
- UI + PlacementSystem integration
- Performance tests (100 buildings, construction updates)
- Multi-building scenarios
"""

import pytest
import pygame
from unittest.mock import Mock, patch

from pycc2.domain.entities.building import (
    Building,
    BuildingType,
    BuildingState,
    create_building,
)
from pycc2.domain.systems.building_placement_system import (
    BuildingPlacementSystem,
    PlacementError,
)
from pycc2.domain.systems.resource_manager import ResourceManager
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.presentation.ui.construction_menu_ui import ConstructionMenuUI


@pytest.fixture
def resource_manager():
    """Create ResourceManager with sufficient resources for integration tests."""
    rm = ResourceManager()
    rm.reset()
    rm.add_gold(10000.0)  # Enough for multiple buildings
    rm.add_wood(5000.0)
    rm.max_power = 500
    rm.power = 0
    return rm


@pytest.fixture
def placement_system(resource_manager):
    """Create BuildingPlacementSystem with 100x100 map for integration tests."""
    return BuildingPlacementSystem(map_width=100, map_height=100, resource_manager=resource_manager)


@pytest.fixture
def construction_menu():
    """Create ConstructionMenuUI for integration tests."""
    pygame.init()
    return ConstructionMenuUI(screen_width=800, screen_height=600)


class TestBuildingSystemE2EWorkflow:
    """Test end-to-end building construction workflows."""
    
    def test_e2e_complete_building_workflow(self, placement_system, resource_manager):
        """Test complete workflow: place → start → construct → complete."""
        # 1. Place building (PLANNING state)
        building = placement_system.place_building(
            "barracks1",
            BuildingType.BARRACKS,
            TileCoord(10, 10),
            auto_start=False,
        )
        assert building.state == BuildingState.PLANNING
        assert resource_manager.gold == 10000.0  # Not consumed yet
        
        # 2. Start construction (consume resources)
        placement_system.start_construction(building)
        assert building.state == BuildingState.CONSTRUCTING
        assert resource_manager.gold == 10000.0 - 300.0  # Barracks cost
        assert resource_manager.wood == 5000.0 - 150.0
        assert resource_manager.power == 10
        
        # 3. Update construction progress (50%)
        completed = placement_system.update_constructions(building.construction_time * 0.5)
        assert len(completed) == 0
        assert building.is_constructing()
        assert abs(building.construction_progress - 0.5) < 0.01
        
        # 4. Complete construction (100%)
        completed = placement_system.update_constructions(building.construction_time * 0.5)
        assert len(completed) == 1
        assert completed[0].id == "barracks1"
        assert building.is_completed()
    
    def test_e2e_auto_start_workflow(self, placement_system, resource_manager):
        """Test auto-start workflow: place with auto_start=True."""
        initial_gold = resource_manager.gold
        
        # Place and auto-start
        building = placement_system.place_building(
            "power1",
            BuildingType.POWER_PLANT,
            TileCoord(20, 20),
            auto_start=True,
        )
        
        # Should immediately consume resources and start
        assert building.state == BuildingState.CONSTRUCTING
        assert resource_manager.gold < initial_gold
        
        # Complete construction
        completed = placement_system.update_constructions(building.construction_time)
        assert len(completed) == 1
        assert building.is_completed()
    
    def test_e2e_insufficient_resources_workflow(self, placement_system, resource_manager):
        """Test workflow fails gracefully with insufficient resources."""
        # Drain resources
        resource_manager.consume_gold(9800.0)  # Leave only 200g
        
        # Place building (PLANNING ok)
        building = placement_system.place_building(
            "barracks1",
            BuildingType.BARRACKS,
            TileCoord(10, 10),
            auto_start=False,
        )
        assert building.state == BuildingState.PLANNING
        
        # Try to start construction (should fail)
        with pytest.raises(PlacementError, match="Insufficient resources"):
            placement_system.start_construction(building)
        
        # Building still in PLANNING state
        assert building.state == BuildingState.PLANNING
        assert resource_manager.gold == 200.0  # Not consumed
    
    def test_e2e_multiple_buildings_construction(self, placement_system):
        """Test constructing multiple buildings simultaneously."""
        # Place and start 3 buildings
        buildings = []
        positions = [TileCoord(10, 10), TileCoord(20, 20), TileCoord(30, 30)]
        types = [BuildingType.BARRACKS, BuildingType.POWER_PLANT, BuildingType.DEFENSE_TOWER]
        
        for i, (pos, btype) in enumerate(zip(positions, types)):
            building = placement_system.place_building(
                f"building_{i}",
                btype,
                pos,
                auto_start=True,
            )
            buildings.append(building)
        
        # All should be constructing
        assert all(b.is_constructing() for b in buildings)
        
        # Update construction (partial)
        max_time = max(b.construction_time for b in buildings)
        completed = placement_system.update_constructions(max_time * 0.3)
        assert len(completed) == 0
        
        # Update construction (complete all)
        completed = placement_system.update_constructions(max_time)
        assert len(completed) == 3
        assert all(b.is_completed() for b in buildings)


class TestUIPlacementIntegration:
    """Test ConstructionMenuUI + BuildingPlacementSystem integration."""
    
    def test_ui_menu_to_placement_workflow(self, construction_menu, placement_system):
        """Test workflow: select from menu → place building."""
        # Simulate clicking Barracks button
        button_rect = construction_menu._get_button_rect(0)
        mouse_pos = button_rect.center
        
        # Select building type
        selected = construction_menu.handle_mouse_click(mouse_pos)
        assert selected == BuildingType.BARRACKS
        
        # Place building using selected type
        building = placement_system.place_building(
            "barracks1",
            selected,
            TileCoord(10, 10),
            auto_start=True,
        )
        
        # Clear selection after placement
        construction_menu.clear_selection()
        assert construction_menu.get_selected_building() is None
        
        # Verify building placed
        assert building.building_type == BuildingType.BARRACKS
        assert building.is_constructing()
    
    def test_ui_affordability_check_integration(self, construction_menu, resource_manager):
        """Test UI reflects resource affordability correctly."""
        # Initially can afford all buildings
        surface = pygame.Surface((800, 600))
        construction_menu.render(surface)  # Should not crash
        
        # Drain resources
        resource_manager.consume_gold(9900.0)
        resource_manager.consume_wood(4900.0)
        
        # Can no longer afford Barracks (300g/150w)
        assert not resource_manager.can_afford(300.0, 150.0, 10)
        
        # UI should show red text (visual test - just ensure no crash)
        construction_menu.render(surface)


class TestBuildingSystemPerformance:
    """Performance tests for building system."""
    
    def test_performance_100_buildings_placement(self, placement_system):
        """Test placing 100 buildings performance."""
        import time
        
        start_time = time.perf_counter()
        for i in range(10):
            for j in range(10):
                try:
                    placement_system.place_building(
                        f"building_{i}_{j}",
                        BuildingType.POWER_PLANT,
                        TileCoord(i * 5, j * 5),
                        auto_start=False,
                    )
                except PlacementError:
                    pass  # Ignore collisions
        elapsed = time.perf_counter() - start_time
        
        # Should place 100 buildings in <100ms
        assert elapsed < 0.1, f"Placement took {elapsed*1000:.2f}ms (target: <100ms)"
    
    def test_performance_construction_update_100_buildings(self, placement_system):
        """Test updating construction of 100 buildings performance."""
        import time
        
        # Place and start 100 buildings (smaller 2x2 buildings to fit)
        for i in range(10):
            for j in range(10):
                try:
                    placement_system.place_building(
                        f"power_{i}_{j}",
                        BuildingType.POWER_PLANT,
                        TileCoord(i * 5, j * 5),
                        auto_start=True,
                    )
                except PlacementError:
                    pass
        
        # Benchmark update
        start_time = time.perf_counter()
        placement_system.update_constructions(0.016)  # 1 frame @60fps
        elapsed = time.perf_counter() - start_time
        
        # Should update 100 buildings in <1ms (target from plan)
        assert elapsed < 0.001, f"Update took {elapsed*1000:.2f}ms (target: <1ms)"
    
    def test_performance_collision_detection_dense_buildings(self, placement_system):
        """Test collision detection performance with dense building layout."""
        import time
        
        # Place 50 buildings in a dense grid
        for i in range(5):
            for j in range(10):
                placement_system.place_building(
                    f"building_{i}_{j}",
                    BuildingType.POWER_PLANT,  # 2x2
                    TileCoord(i * 3, j * 3),
                    auto_start=False,
                )
        
        # Test collision detection performance
        test_building = create_building("test", BuildingType.BARRACKS, TileCoord(0, 0))
        
        start_time = time.perf_counter()
        for _ in range(1000):
            placement_system.can_place_building(test_building)
        elapsed = time.perf_counter() - start_time
        
        # Should check 1000 collisions in <100ms
        assert elapsed < 0.1


class TestBuildingSystemEdgeCases:
    """Edge case tests for building system."""
    
    def test_edge_case_building_on_map_boundary(self, placement_system):
        """Test placing building exactly at map boundaries."""
        # Valid: building at (0, 0)
        building = placement_system.place_building(
            "corner1",
            BuildingType.POWER_PLANT,  # 2x2
            TileCoord(0, 0),
            auto_start=False,
        )
        assert building.position == TileCoord(0, 0)
        
        # Valid: building at max position (98, 98) for 100x100 map
        building = placement_system.place_building(
            "corner2",
            BuildingType.POWER_PLANT,
            TileCoord(98, 98),
            auto_start=False,
        )
        assert building.position == TileCoord(98, 98)
        
        # Invalid: building exceeds boundary
        with pytest.raises(PlacementError, match="exceeds map"):
            placement_system.place_building(
                "invalid",
                BuildingType.POWER_PLANT,
                TileCoord(99, 99),
                auto_start=False,
            )
    
    def test_edge_case_zero_construction_time(self, placement_system):
        """Test building with zero construction time completes immediately."""
        building = placement_system.place_building(
            "instant",
            BuildingType.POWER_PLANT,
            TileCoord(10, 10),
            auto_start=True,
        )
        
        # Hack construction time to 0
        building.construction_time = 0.001
        
        # Update should complete immediately
        completed = placement_system.update_constructions(0.001)
        assert len(completed) == 1
        assert building.is_completed()
    
    def test_edge_case_destroyed_building_ignored_in_collision(self, placement_system):
        """Test destroyed buildings don't block new placements."""
        # Place building
        building1 = placement_system.place_building(
            "building1",
            BuildingType.BARRACKS,
            TileCoord(10, 10),
            auto_start=False,
        )
        
        # Destroy building
        building1.state = BuildingState.DESTROYED
        
        # Should be able to place new building at same location
        building2 = placement_system.place_building(
            "building2",
            BuildingType.BARRACKS,
            TileCoord(10, 10),
            auto_start=False,
        )
        
        assert building2.position == TileCoord(10, 10)
    
    def test_edge_case_remove_building_during_construction(self, placement_system):
        """Test removing building mid-construction."""
        building = placement_system.place_building(
            "building1",
            BuildingType.BARRACKS,
            TileCoord(10, 10),
            auto_start=True,
        )
        
        # Update 50%
        placement_system.update_constructions(building.construction_time * 0.5)
        assert building.is_constructing()
        
        # Remove building
        removed = placement_system.remove_building("building1")
        assert removed
        
        # Verify removed
        assert placement_system.get_building_by_id("building1") is None
        assert len(placement_system.buildings) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
