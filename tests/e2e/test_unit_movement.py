"""
E2E Test: Unit Movement

Tests the complete unit movement workflow to verify units move to
the correct destination without jumping to (0,0) or other incorrect positions.

This test addresses the P0 bug reported by users:
"战斗单元移动出问题，移动后单位出现在左上角"
"""
import pytest
from pycc2.domain.entities.unit import Unit, Faction, UnitType
from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.value_objects.tile_coord import TileCoord


class TestUnitMovementE2E:
    """End-to-end tests for unit movement functionality."""
    
    def test_unit_moves_to_correct_position(self):
        """
        CRITICAL: Unit should move to the clicked destination, not (0,0).
        
        User Journey:
        1. Select a unit at initial position (10, 15)
        2. Click on map at destination (22, 10)
        3. Unit should move to (22, 10), NOT (0, 0)
        
        Bug Report:
        - User reported units jumping to left-upper corner after move command
        - Logs show: "[COMMAND] Moving 1 unit(s) to (22, 10)"
        - But unit appears at wrong position
        """
        # Setup: Create a unit at starting position
        initial_x, initial_y = 10, 15
        unit = self._create_test_unit("player_1", initial_x, initial_y)
        
        # Action: Move unit to destination
        destination_x, destination_y = 22, 10
        unit.position.move_to_tile(TileCoord(destination_x, destination_y))
        
        # Assert: Unit is at destination, not (0,0) or initial position
        actual_pos = (unit.position.tile_coord.x, unit.position.tile_coord.y)
        
        assert actual_pos != (0, 0), (
            f"BUG REPRODUCED: Unit jumped to (0,0) instead of ({destination_x}, {destination_y})"
        )
        assert actual_pos != (initial_x, initial_y), (
            "Unit did not move from initial position"
        )
        assert actual_pos == (destination_x, destination_y), (
            f"Unit at {actual_pos}, expected ({destination_x}, {destination_y})"
        )
    
    def test_multiple_units_move_independently(self):
        """
        Multiple units should maintain their own positions after movement.
        
        Ensures that moving one unit doesn't affect others or cause
        position corruption.
        """
        # Setup: Create three units at different positions
        unit1 = self._create_test_unit("player_1", 5, 5)
        unit2 = self._create_test_unit("player_2", 10, 10)
        unit3 = self._create_test_unit("player_3", 15, 15)
        
        # Action: Move each unit to different destinations
        unit1.position.move_to_tile(TileCoord(8, 8))
        unit2.position.move_to_tile(TileCoord(12, 12))
        unit3.position.move_to_tile(TileCoord(18, 18))
        
        # Assert: Each unit is at its own destination
        pos1 = (unit1.position.tile_coord.x, unit1.position.tile_coord.y)
        pos2 = (unit2.position.tile_coord.x, unit2.position.tile_coord.y)
        pos3 = (unit3.position.tile_coord.x, unit3.position.tile_coord.y)
        
        assert pos1 == (8, 8), f"Unit1 at {pos1}, expected (8, 8)"
        assert pos2 == (12, 12), f"Unit2 at {pos2}, expected (12, 12)"
        assert pos3 == (18, 18), f"Unit3 at {pos3}, expected (18, 18)"
        
        # No unit should be at (0,0) unless intentionally moved there
        assert pos1 != (0, 0)
        assert pos2 != (0, 0)
        assert pos3 != (0, 0)
    
    def test_unit_movement_with_screen_to_map_coords(self):
        """
        Test coordinate conversion from screen clicks to map positions.
        
        The bug might be in coordinate transformation, where screen
        coordinates are not properly converted to map tile coordinates.
        """
        # This test will need actual camera/viewport system
        # Placeholder for now - will be implemented once we find the actual code
        pytest.skip("Requires camera/viewport system - to be implemented")
    
    def test_unit_preserves_state_after_movement(self):
        """
        Unit should preserve all attributes except position after moving.
        
        Ensures movement doesn't reset or corrupt unit state.
        """
        # Setup
        unit = self._create_test_unit("player_1", 10, 10)
        
        # Store original values
        original_health = unit.health.hp
        original_morale = unit.morale.value
        
        # Action: Move unit
        unit.position.move_to_tile(TileCoord(15, 15))
        
        # Assert: Position changed, other attributes preserved
        new_pos = (unit.position.tile_coord.x, unit.position.tile_coord.y)
        assert new_pos == (15, 15)
        assert unit.health.hp == original_health, "Health should not change during movement"
        assert unit.morale.value == original_morale, "Morale should not change during movement"
    
    def _create_test_unit(self, unit_id: str, x: int, y: int) -> Unit:
        """Helper to create a test unit with all required components."""
        return Unit(
            id=unit_id,
            name=f"Test Unit {unit_id}",
            faction=Faction.ALLIES,
            unit_type=UnitType.INFANTRY_SQUAD,
            health=HealthComponent(hp=100, max_hp=100),
            morale=MoraleComponent(value=100),
            weapon=WeaponComponent(
                primary_weapon_id="rifle",
                max_ammo=30,
                ammo_remaining=30
            ),
            position=PositionComponent(tile_coord=TileCoord(x, y)),
            vision=VisionComponent()
        )


class TestUnitMovementIntegration:
    """Integration tests for movement with game systems."""
    
    def test_movement_command_from_input(self):
        """
        Test full pipeline: User click → Input processing → Unit movement.
        
        This simulates the actual game flow when user clicks to move a unit.
        """
        pytest.skip("Requires full game loop integration - Phase 2")
    
    def test_movement_with_pathfinding(self):
        """
        Test movement with obstacle avoidance and pathfinding.
        """
        pytest.skip("Requires pathfinding system - Phase 2")
    
    def test_movement_animation_sync(self):
        """
        Verify sprite position syncs with unit logical position.
        
        Bug might be: unit.position updates correctly, but sprite
        rendering uses wrong coordinates.
        """
        pytest.skip("Requires rendering system integration - Phase 2")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
