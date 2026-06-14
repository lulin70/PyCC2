"""E2E Test: Deployment Phase Full Flow

Tests the complete deployment flow from start to battle transition:
1. Start deployment manager
2. Verify three zone types are defined
3. Verify force pool is generated
4. Deploy units to valid positions
5. Verify invalid positions are rejected
6. Set pre-battle orders
7. Verify pending orders are stored
8. Click Begin Battle
9. Verify transition to battle phase
10. Verify pending orders are applied to units
11. Verify deployed units exist in the game state
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_map_data(width: int = 30, height: int = 20) -> dict:
    """Create a simple map data dict for deployment testing."""
    tiles = [[0] * width for _ in range(height)]  # All open terrain
    return {
        "width": width,
        "height": height,
        "tiles": tiles,
        "friendly_zone": [(x, y) for y in range(height) for x in range(width // 3)],
        "enemy_zone": [(x, y) for y in range(height) for x in range(2 * width // 3, width)],
        "no_mans_land": [(x, y) for y in range(height) for x in range(width // 3, 2 * width // 3)],
    }


def _make_map_data_with_water(width: int = 30, height: int = 20) -> dict:
    """Map with water tiles in the friendly zone to test terrain rejection."""
    tiles = [[0] * width for _ in range(height)]
    # Place water at (1, 1) in friendly zone
    tiles[1][1] = 6  # TERRAIN_WATER
    # Place solid building at (2, 2) in friendly zone
    tiles[2][2] = 5  # TERRAIN_BUILDING_SOLID
    return {
        "width": width,
        "height": height,
        "tiles": tiles,
        "friendly_zone": [(x, y) for y in range(height) for x in range(width // 3)],
        "enemy_zone": [(x, y) for y in range(height) for x in range(2 * width // 3, width)],
        "no_mans_land": [(x, y) for y in range(height) for x in range(width // 3, 2 * width // 3)],
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDeploymentE2E:
    """Full E2E test for the deployment phase."""

    def test_01_start_deployment_manager(self):
        """Step 1: Start deployment manager and verify it activates."""
        from pycc2.services.deployment_manager import DeploymentManager

        dm = DeploymentManager()
        assert not dm.is_active

        map_data = _make_map_data()
        dm.start(map_data=map_data, faction="ally")

        assert dm.is_active
        assert dm.deployment_ui is not None

    def test_02_verify_three_zone_types(self):
        """Step 2: Verify three zone types (FRIENDLY, NO_MANS_LAND, ENEMY_CONTROLLED) are defined."""
        from pycc2.presentation.ui.deployment_ui import ZoneType
        from pycc2.services.deployment_manager import DeploymentManager

        dm = DeploymentManager()
        map_data = _make_map_data()
        dm.start(map_data=map_data, faction="ally")

        state = dm.get_state()
        assert state is not None

        # Verify all three zone types exist
        zone_types_found = set()
        if hasattr(state, "friendly_zone") and state.friendly_zone:
            zone_types_found.add(ZoneType.FRIENDLY)
        if hasattr(state, "enemy_zone") and state.enemy_zone:
            zone_types_found.add(ZoneType.ENEMY_CONTROLLED)
        if hasattr(state, "no_mans_land") and state.no_mans_land:
            zone_types_found.add(ZoneType.NO_MANS_LAND)

        assert ZoneType.FRIENDLY in zone_types_found, "FRIENDLY zone missing"
        assert ZoneType.ENEMY_CONTROLLED in zone_types_found, "ENEMY_CONTROLLED zone missing"
        assert ZoneType.NO_MANS_LAND in zone_types_found, "NO_MANS_LAND zone missing"

    def test_03_verify_force_pool_generated(self):
        """Step 3: Verify force pool is generated with available units."""
        from pycc2.services.deployment_manager import DeploymentManager

        dm = DeploymentManager()
        map_data = _make_map_data()
        dm.start(map_data=map_data, faction="ally")

        state = dm.get_state()
        assert state is not None
        assert len(state.available_units) >= 6, (
            f"Force pool should have at least 6 units, got {len(state.available_units)}"
        )

        # Verify unit categories exist
        unit_types = {u.unit_type for u in state.available_units}
        assert "infantry" in unit_types, "Should have infantry units"
        assert "support" in unit_types, "Should have support units"

    def test_04_deploy_units_to_valid_positions(self):
        """Step 4: Deploy units to valid positions (drag-drop simulation)."""
        from pycc2.services.deployment_manager import DeploymentManager

        dm = DeploymentManager()
        map_data = _make_map_data()
        dm.start(map_data=map_data, faction="ally")

        state = dm.get_state()
        # Place first available unit at (0, 0) — should be in friendly zone
        result = dm.deployment_ui.place_unit(0, 0, 0)
        assert result is True, "Should be able to place unit at (0,0) in friendly zone"

        # Place second unit at (1, 0)
        result = dm.deployment_ui.place_unit(1, 1, 0)
        assert result is True, "Should be able to place unit at (1,0) in friendly zone"

        # Verify units are placed
        assert len(state.placed_units) == 2

    def test_05_invalid_positions_rejected(self):
        """Step 5: Verify invalid positions are rejected (enemy zone, wrong terrain)."""
        from pycc2.services.deployment_manager import DeploymentManager

        dm = DeploymentManager()
        map_data = _make_map_data_with_water()
        dm.start(map_data=map_data, faction="ally")

        # Try to place in enemy zone (x=25 for a 30-wide map)
        result = dm.deployment_ui.place_unit(0, 25, 0)
        assert result is False, "Should NOT be able to place unit in enemy zone"

        # Try to place on water tile (1, 1)
        result = dm.deployment_ui.place_unit(0, 1, 1)
        assert result is False, "Should NOT be able to place unit on water"

        # Try to place on solid building (2, 2)
        result = dm.deployment_ui.place_unit(0, 2, 2)
        assert result is False, "Should NOT be able to place unit on solid building"

    def test_06_set_pre_battle_orders(self):
        """Step 6: Set pre-battle orders (right-click to set move target)."""
        from pycc2.services.deployment_manager import DeploymentManager

        dm = DeploymentManager()
        map_data = _make_map_data()
        dm.start(map_data=map_data, faction="ally")

        # Place a unit first
        dm.deployment_ui.place_unit(0, 0, 0)

        # Set pending order for the placed unit
        unit = dm.get_state().placed_units[0]
        dm.set_pending_order(unit.unit_template_id, 5, 5)

    def test_07_verify_pending_orders_stored(self):
        """Step 7: Verify pending orders are stored correctly."""
        from pycc2.services.deployment_manager import DeploymentManager

        dm = DeploymentManager()
        map_data = _make_map_data()
        dm.start(map_data=map_data, faction="ally")

        dm.deployment_ui.place_unit(0, 0, 0)
        unit = dm.get_state().placed_units[0]
        dm.set_pending_order(unit.unit_template_id, 5, 5)

        order = dm.get_pending_order(unit.unit_template_id)
        assert order is not None, "Pending order should be stored"
        assert order == (5, 5), f"Order should be (5,5), got {order}"

    def test_08_click_begin_battle(self):
        """Step 8: Click Begin Battle to finalize deployment."""
        from pycc2.services.deployment_manager import DeploymentManager

        dm = DeploymentManager()
        map_data = _make_map_data()
        dm.start(map_data=map_data, faction="ally")

        # Place at least one unit
        dm.deployment_ui.place_unit(0, 0, 0)

        # Verify deployment is complete enough
        assert dm.deployment_ui.is_deployment_complete()

        # Begin battle
        result = dm.deployment_ui.begin_battle()
        assert result is not None, "begin_battle() should return a result dict"

    def test_09_verify_transition_to_battle_phase(self):
        """Step 9: Verify transition to battle phase after begin_battle."""
        from pycc2.presentation.ui.deployment_ui import DeploymentPhase
        from pycc2.services.deployment_manager import DeploymentManager

        dm = DeploymentManager()
        map_data = _make_map_data()
        dm.start(map_data=map_data, faction="ally")

        dm.deployment_ui.place_unit(0, 0, 0)
        dm.deployment_ui.begin_battle()

        # Phase should be ACTIVE
        assert dm.deployment_ui.state.phase == DeploymentPhase.ACTIVE

    def test_10_verify_pending_orders_applied(self):
        """Step 10: Verify pending orders are applied to units after complete()."""
        import numpy as np

        from pycc2.domain.entities.game_map import GameMap
        from pycc2.presentation.rendering.camera import Camera
        from pycc2.services.deployment_manager import DeploymentManager
        from pycc2.services.game_loop import GameState

        dm = DeploymentManager()
        map_data = _make_map_data()
        dm.start(map_data=map_data, faction="ally")

        # Place a unit and set order
        dm.deployment_ui.place_unit(0, 0, 0)
        unit = dm.get_state().placed_units[0]
        dm.set_pending_order(unit.unit_template_id, 5, 5)

        # Create a GameState for complete()
        game_map = GameMap(
            id="test",
            name="test",
            width=30,
            height=20,
            tile_grid=np.zeros((20, 30), dtype=np.int8),
        )
        camera = Camera(position=None, viewport_width=800, viewport_height=600)
        state = GameState(game_map=game_map, units=[], camera=camera)

        result = dm.complete(ai_service=None, state=state)
        assert result is not None

        # Verify units were created
        assert len(state.units) >= 1, (
            f"Should have created at least 1 unit from deployment, got {len(state.units)}"
        )

        # Verify pending orders were included in result
        # Note: pending_orders are included in begin_battle() result,
        # but apply_pending_orders() clears them after applying.
        # The key verification is that units were created with move targets.
        assert "pending_orders" in result
        # Pending orders may be empty after apply (cleared by apply_pending_orders)
        # The real test is that units have move targets set
        units_with_targets = [u for u in state.units if u.move_target is not None]
        assert len(units_with_targets) >= 1, (
            f"At least one unit should have a move target from pending orders, got {len(units_with_targets)}"
        )

    def test_11_verify_deployed_units_in_game_state(self):
        """Step 11: Verify deployed units exist in the game state after complete()."""
        import numpy as np

        from pycc2.domain.entities.game_map import GameMap
        from pycc2.domain.entities.unit import Faction
        from pycc2.presentation.rendering.camera import Camera
        from pycc2.services.deployment_manager import DeploymentManager
        from pycc2.services.game_loop import GameState

        dm = DeploymentManager()
        map_data = _make_map_data()
        dm.start(map_data=map_data, faction="ally")

        # Place multiple units
        dm.deployment_ui.place_unit(0, 0, 0)
        dm.deployment_ui.place_unit(1, 1, 0)

        game_map = GameMap(
            id="test",
            name="test",
            width=30,
            height=20,
            tile_grid=np.zeros((20, 30), dtype=np.int8),
        )
        camera = Camera(position=None, viewport_width=800, viewport_height=600)
        state = GameState(game_map=game_map, units=[], camera=camera)

        dm.complete(ai_service=None, state=state)

        # Verify player units were created
        player_units = [u for u in state.units if u.faction == Faction.ALLIES]
        assert len(player_units) >= 2, (
            f"Should have at least 2 player units, got {len(player_units)}"
        )

        # Verify units have valid positions
        for u in player_units:
            assert u.position.tile_coord.x >= 0
            assert u.position.tile_coord.y >= 0

        # Verify deployment phase is no longer active
        assert not dm.is_active
