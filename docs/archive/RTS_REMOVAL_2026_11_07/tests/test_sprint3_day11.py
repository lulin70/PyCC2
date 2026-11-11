"""Sprint 3 Day 11 Tests - FUNC-05 Building Construction System.

Tests for:
- Building entity state machine
- BuildingPlacementSystem (collision detection, resource consumption)
- ConstructionMenuUI (button interactions)
"""

import pytest
import pygame
from unittest.mock import Mock

from pycc2.domain.entities.building import (
    Building,
    BuildingType,
    BuildingState,
    BuildingCost,
    create_building,
    BUILDING_PRESETS,
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
    """Create ResourceManager with sufficient resources."""
    rm = ResourceManager()
    rm.reset()
    rm.add_gold(1000.0)
    rm.add_wood(500.0)
    rm.max_power = 100
    rm.power = 0
    return rm


@pytest.fixture
def placement_system(resource_manager):
    """Create BuildingPlacementSystem with 50x50 map."""
    return BuildingPlacementSystem(map_width=50, map_height=50, resource_manager=resource_manager)


@pytest.fixture
def construction_menu():
    """Create ConstructionMenuUI for 800x600 screen."""
    pygame.init()
    return ConstructionMenuUI(screen_width=800, screen_height=600)


class TestBuildingEntity:
    """Test Building entity state machine."""
    
    def test_building_creation_with_preset(self):
        """Test building creation with preset values."""
        building = create_building("barracks1", BuildingType.BARRACKS, TileCoord(10, 10))
        
        assert building.id == "barracks1"
        assert building.building_type == BuildingType.BARRACKS
        assert building.position == TileCoord(10, 10)
        assert building.width == 3  # Barracks preset
        assert building.height == 3
        assert building.state == BuildingState.PLANNING
        assert building.construction_progress == 0.0
        assert building.cost.gold == 300
        assert building.cost.wood == 150
        assert building.cost.power == 10
    
    def test_building_state_machine_workflow(self):
        """Test building lifecycle: PLANNING → CONSTRUCTING → COMPLETED."""
        building = create_building("tower1", BuildingType.DEFENSE_TOWER, TileCoord(5, 5))
        
        # Initial state
        assert building.state == BuildingState.PLANNING
        assert not building.is_constructing()
        assert not building.is_completed()
        
        # Start construction
        building.start_construction()
        assert building.state == BuildingState.CONSTRUCTING
        assert building.is_constructing()
        assert building.construction_progress == 0.0
        
        # Update construction (50% progress)
        building.update_construction(building.construction_time * 0.5)
        assert building.is_constructing()
        assert abs(building.construction_progress - 0.5) < 0.01
        
        # Complete construction
        building.update_construction(building.construction_time * 0.5)
        assert building.is_completed()
        assert building.state == BuildingState.COMPLETED
        assert building.construction_progress == 1.0
    
    def test_building_occupied_tiles(self):
        """Test get_occupied_tiles() returns correct tile list."""
        building = create_building("power1", BuildingType.POWER_PLANT, TileCoord(10, 20))
        # Power plant is 2x2
        
        tiles = building.get_occupied_tiles()
        assert len(tiles) == 4
        assert TileCoord(10, 20) in tiles
        assert TileCoord(11, 20) in tiles
        assert TileCoord(10, 21) in tiles
        assert TileCoord(11, 21) in tiles
    
    def test_building_overlap_detection(self):
        """Test overlaps_with() collision detection."""
        building1 = create_building("b1", BuildingType.BARRACKS, TileCoord(10, 10))  # 3x3
        building2 = create_building("b2", BuildingType.BARRACKS, TileCoord(12, 12))  # 3x3 (overlaps)
        building3 = create_building("b3", BuildingType.BARRACKS, TileCoord(15, 15))  # 3x3 (no overlap)
        
        assert building1.overlaps_with(building2)
        assert building2.overlaps_with(building1)
        assert not building1.overlaps_with(building3)
        assert not building3.overlaps_with(building1)
    
    def test_building_take_damage(self):
        """Test building damage and destruction."""
        building = create_building("tower1", BuildingType.DEFENSE_TOWER, TileCoord(5, 5))
        building.max_hp = 100
        building.hp = 100
        
        # Take damage
        building.take_damage(30)
        assert building.hp == 70
        assert building.state != BuildingState.DESTROYED
        
        # Destroy building
        building.take_damage(80)
        assert building.hp == 0
        assert building.state == BuildingState.DESTROYED


class TestBuildingPlacementSystem:
    """Test BuildingPlacementSystem logic."""
    
    def test_placement_validation_success(self, placement_system):
        """Test valid building placement."""
        building = create_building("barracks1", BuildingType.BARRACKS, TileCoord(10, 10))
        
        can_place, error = placement_system.can_place_building(building)
        assert can_place
        assert error == ""
    
    def test_placement_validation_out_of_bounds(self, placement_system):
        """Test placement fails when building exceeds map boundaries."""
        # Building at (48, 48) with 3x3 size exceeds 50x50 map
        building = create_building("barracks1", BuildingType.BARRACKS, TileCoord(48, 48))
        
        can_place, error = placement_system.can_place_building(building)
        assert not can_place
        assert "exceeds map" in error.lower()
    
    def test_placement_validation_collision(self, placement_system):
        """Test placement fails when building overlaps existing building."""
        # Place first building
        building1 = placement_system.place_building("b1", BuildingType.BARRACKS, TileCoord(10, 10))
        
        # Try to place overlapping building
        building2 = create_building("b2", BuildingType.BARRACKS, TileCoord(12, 12))
        can_place, error = placement_system.can_place_building(building2)
        assert not can_place
        assert "overlaps" in error.lower()
    
    def test_place_building_success(self, placement_system, resource_manager):
        """Test successful building placement without auto-start."""
        building = placement_system.place_building(
            "barracks1",
            BuildingType.BARRACKS,
            TileCoord(10, 10),
            auto_start=False,
        )
        
        assert building.id == "barracks1"
        assert building.state == BuildingState.PLANNING
        assert len(placement_system.buildings) == 1
        
        # Resources not consumed yet
        assert resource_manager.gold == 1000.0
        assert resource_manager.wood == 500.0
    
    def test_start_construction_consumes_resources(self, placement_system, resource_manager):
        """Test start_construction() consumes resources from ResourceManager."""
        building = placement_system.place_building(
            "barracks1",
            BuildingType.BARRACKS,
            TileCoord(10, 10),
            auto_start=False,
        )
        
        # Start construction
        placement_system.start_construction(building)
        
        assert building.state == BuildingState.CONSTRUCTING
        assert resource_manager.gold == 1000.0 - 300.0  # Barracks cost 300g
        assert resource_manager.wood == 500.0 - 150.0  # Barracks cost 150w
        assert resource_manager.power == 10  # Barracks consume 10p
    
    def test_start_construction_insufficient_resources(self, placement_system, resource_manager):
        """Test start_construction() fails with insufficient resources."""
        # Drain resources
        resource_manager.consume_gold(900.0)
        
        building = placement_system.place_building(
            "barracks1",
            BuildingType.BARRACKS,
            TileCoord(10, 10),
            auto_start=False,
        )
        
        # Should fail
        with pytest.raises(PlacementError, match="Insufficient resources"):
            placement_system.start_construction(building)
        
        assert building.state == BuildingState.PLANNING
    
    def test_update_constructions(self, placement_system):
        """Test update_constructions() progresses building construction."""
        building = placement_system.place_building(
            "tower1",
            BuildingType.DEFENSE_TOWER,
            TileCoord(10, 10),
            auto_start=True,
        )
        
        construction_time = building.construction_time
        
        # Update 50%
        completed = placement_system.update_constructions(construction_time * 0.5)
        assert len(completed) == 0
        assert building.is_constructing()
        assert abs(building.construction_progress - 0.5) < 0.01
        
        # Update to 100%
        completed = placement_system.update_constructions(construction_time * 0.5)
        assert len(completed) == 1
        assert completed[0].id == "tower1"
        assert building.is_completed()
    
    def test_get_buildings_at_position(self, placement_system):
        """Test get_buildings_at() returns buildings at specific tile."""
        building = placement_system.place_building(
            "power1",
            BuildingType.POWER_PLANT,
            TileCoord(10, 10),
            auto_start=False,
        )
        
        # Check occupied tiles
        buildings = placement_system.get_buildings_at(TileCoord(10, 10))
        assert len(buildings) == 1
        assert buildings[0].id == "power1"
        
        buildings = placement_system.get_buildings_at(TileCoord(11, 11))
        assert len(buildings) == 1
        
        # Check unoccupied tile
        buildings = placement_system.get_buildings_at(TileCoord(20, 20))
        assert len(buildings) == 0


class TestConstructionMenuUI:
    """Test ConstructionMenuUI interactions."""
    
    def test_menu_initialization(self, construction_menu):
        """Test construction menu initializes with correct position and buttons."""
        assert construction_menu.selected_building is None
        assert construction_menu.hovered_index is None
        assert len(construction_menu.building_types) == 3
        
        # Check position is bottom-right
        assert construction_menu.position[0] > 300  # Right side
        assert construction_menu.position[1] > 400  # Bottom side
    
    def test_menu_button_click_selection(self, construction_menu):
        """Test clicking button selects building type."""
        # Get first button position (Barracks)
        button_rect = construction_menu._get_button_rect(0)
        mouse_pos = button_rect.center
        
        # Click button
        selected = construction_menu.handle_mouse_click(mouse_pos)
        assert selected == BuildingType.BARRACKS
        assert construction_menu.get_selected_building() == BuildingType.BARRACKS
        
        # Click again to deselect
        selected = construction_menu.handle_mouse_click(mouse_pos)
        assert selected is None
        assert construction_menu.get_selected_building() is None
    
    def test_menu_hover_detection(self, construction_menu):
        """Test mouse hover updates hovered_index."""
        # Hover over second button (Power Plant)
        button_rect = construction_menu._get_button_rect(1)
        mouse_pos = button_rect.center
        
        construction_menu.handle_mouse_motion(mouse_pos)
        assert construction_menu.hovered_index == 1
        
        # Move away
        construction_menu.handle_mouse_motion((0, 0))
        assert construction_menu.hovered_index is None
    
    def test_menu_clear_selection(self, construction_menu):
        """Test clear_selection() resets selected building."""
        # Select building
        button_rect = construction_menu._get_button_rect(0)
        construction_menu.handle_mouse_click(button_rect.center)
        assert construction_menu.selected_building is not None
        
        # Clear selection
        construction_menu.clear_selection()
        assert construction_menu.selected_building is None
    
    def test_menu_render_without_crash(self, construction_menu):
        """Test render() executes without errors."""
        surface = pygame.Surface((800, 600))
        
        # Should not raise exception
        construction_menu.render(surface)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
