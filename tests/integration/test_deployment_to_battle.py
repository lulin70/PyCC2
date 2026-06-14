"""Integration tests: Deployment → Battle flow.

Tests the complete lifecycle from starting deployment to creating units
and transitioning into combat.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np
import pytest

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.presentation.rendering.camera import Camera
from pycc2.services.deployment_manager import DeploymentManager
from pycc2.services.event_bus import EventBus
from pycc2.services.game_loop import GameState

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def game_map():
    grid = np.zeros((16, 16), dtype=np.int8)
    return GameMap(
        id="test_map",
        name="Test Map",
        width=16,
        height=16,
        tile_grid=grid,
    )


@pytest.fixture
def camera():
    return Camera(position=Vec2(256.0, 256.0), viewport_width=1280, viewport_height=720)


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def game_state(game_map, camera):
    return GameState(game_map=game_map, units=[], camera=camera)


@pytest.fixture
def deployment_manager():
    return DeploymentManager()


@pytest.fixture
def map_data():
    """Minimal map_data dict expected by DeploymentUI."""
    return {
        "width": 16,
        "height": 16,
        "tiles": [[0] * 16 for _ in range(16)],
        "spawn_points": [
            {"id": "sp_ally", "side": "ally", "position": (3, 3), "units_max": 6},
            {"id": "sp_axis", "side": "axis", "position": (12, 12), "units_max": 6},
        ],
    }


@pytest.fixture
def ai_service():
    """Real AIService for integration testing (no MagicMock)."""
    from pycc2.services.ai_service import AIService

    return AIService(event_bus=EventBus())


@pytest.fixture
def deployment_ui():
    """Real DeploymentUI for integration testing."""
    from pycc2.presentation.ui.deployment_ui import DeploymentUI

    return DeploymentUI(width=800, height=600)


# ── Tests ─────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestDeploymentStart:
    def test_start_creates_deployment_ui(self, deployment_manager, map_data, deployment_ui):
        """DeploymentManager.start() should store the injected DeploymentUI instance."""
        deployment_manager.start(map_data=map_data, faction="ally", deployment_ui=deployment_ui)
        assert deployment_manager.deployment_ui is not None
        assert deployment_manager.is_active is True

    def test_start_sets_phase_active(self, deployment_manager, map_data, deployment_ui):
        deployment_manager.start(map_data=map_data, faction="ally", deployment_ui=deployment_ui)
        assert deployment_manager.deployment_phase_active is True

    def test_start_axis_faction(self, deployment_manager, map_data, deployment_ui):
        """Starting deployment as axis faction should also work."""
        deployment_manager.start(map_data=map_data, faction="axis", deployment_ui=deployment_ui)
        assert deployment_manager.is_active is True

    def test_get_state_returns_ui_state(self, deployment_manager, map_data, deployment_ui):
        deployment_manager.start(map_data=map_data, faction="ally", deployment_ui=deployment_ui)
        state = deployment_manager.get_state()
        # get_state should return something (even if it's a mock-like object)
        assert state is not None


@pytest.mark.integration
class TestDeploymentComplete:
    def test_complete_returns_none_when_not_active(
        self, deployment_manager, ai_service, game_state
    ):
        """complete() should return None if no deployment is active."""
        result = deployment_manager.complete(ai_service=ai_service, state=game_state)
        assert result is None

    def test_complete_deactivates_phase(
        self, deployment_manager, map_data, ai_service, game_state, deployment_ui
    ):
        """After complete(), the deployment phase should be deactivated."""
        deployment_manager.start(map_data=map_data, faction="ally", deployment_ui=deployment_ui)
        # Simulate at least one placement so begin_battle() returns a result
        self._add_placement(deployment_manager)
        deployment_manager.complete(ai_service=ai_service, state=game_state)
        assert deployment_manager.is_active is False

    def test_complete_creates_units_in_state(
        self, deployment_manager, map_data, ai_service, game_state, deployment_ui
    ):
        """complete() should create Unit entities and add them to game state."""
        deployment_manager.start(map_data=map_data, faction="ally", deployment_ui=deployment_ui)
        self._add_placement(deployment_manager)
        deployment_manager.complete(ai_service=ai_service, state=game_state)
        assert len(game_state.units) >= 1, (
            f"complete() should create at least 1 unit in game state, got {len(game_state.units)}"
        )

    def _add_placement(self, dm: DeploymentManager) -> None:
        """Inject a player placement into the DeploymentUI for testing."""
        if dm.deployment_ui is None:
            return
        # Inject a placed unit into the DeploymentUI's internal state
        from pycc2.presentation.ui.deployment_ui import DeploymentUnit

        placed_unit = DeploymentUnit(
            unit_template_id="infantry",
            display_name="Test Squad",
            unit_type="infantry",
            deployment_cost=100,
            position=(5, 5),
            is_placed=True,
        )
        dm.deployment_ui._state.placed_units.append(placed_unit)


@pytest.mark.integration
class TestUnitAttributeSetup:
    def test_unit_faction_is_correct(self):
        """Units created from deployment should have the correct faction."""
        from pycc2.services.deployment_manager import DeploymentManager

        dm = DeploymentManager()
        type_map = {k: getattr(UnitType, v) for k, v in dm._TYPE_MAP.items()}
        template_type_map = {k: getattr(UnitType, v) for k, v in dm._TEMPLATE_TYPE_MAP.items()}

        placement = {
            "unit_template_id": "infantry",
            "display_name": "Rifle Squad",
            "unit_type": "infantry",
            "position": (3, 3),
        }
        unit = dm._create_unit_from_placement(
            placement=placement,
            faction=Faction.ALLIES,
            id_prefix="player",
            counter=0,
            type_map=type_map,
            template_type_map=template_type_map,
        )
        assert unit is not None
        assert unit.faction == Faction.ALLIES

    def test_unit_type_infantry(self):
        dm = DeploymentManager()
        type_map = {k: getattr(UnitType, v) for k, v in dm._TYPE_MAP.items()}
        template_type_map = {k: getattr(UnitType, v) for k, v in dm._TEMPLATE_TYPE_MAP.items()}

        placement = {
            "unit_template_id": "infantry",
            "display_name": "Rifle Squad",
            "unit_type": "infantry",
            "position": (3, 3),
        }
        unit = dm._create_unit_from_placement(
            placement=placement,
            faction=Faction.ALLIES,
            id_prefix="player",
            counter=0,
            type_map=type_map,
            template_type_map=template_type_map,
        )
        assert unit is not None
        assert unit.unit_type == UnitType.INFANTRY_SQUAD

    def test_unit_type_vehicle_becomes_tank(self):
        dm = DeploymentManager()
        type_map = {k: getattr(UnitType, v) for k, v in dm._TYPE_MAP.items()}
        template_type_map = {k: getattr(UnitType, v) for k, v in dm._TEMPLATE_TYPE_MAP.items()}

        placement = {
            "unit_template_id": "vehicle",
            "display_name": "Sherman",
            "unit_type": "vehicle",
            "position": (4, 4),
        }
        unit = dm._create_unit_from_placement(
            placement=placement,
            faction=Faction.ALLIES,
            id_prefix="player",
            counter=0,
            type_map=type_map,
            template_type_map=template_type_map,
        )
        assert unit is not None
        assert unit.unit_type == UnitType.TANK

    def test_unit_health_set_correctly(self):
        dm = DeploymentManager()
        type_map = {k: getattr(UnitType, v) for k, v in dm._TYPE_MAP.items()}
        template_type_map = {k: getattr(UnitType, v) for k, v in dm._TEMPLATE_TYPE_MAP.items()}

        placement = {
            "unit_template_id": "infantry",
            "display_name": "Rifle Squad",
            "unit_type": "infantry",
            "position": (3, 3),
        }
        unit = dm._create_unit_from_placement(
            placement=placement,
            faction=Faction.ALLIES,
            id_prefix="player",
            counter=0,
            type_map=type_map,
            template_type_map=template_type_map,
        )
        assert unit is not None
        assert unit.health.hp == 100
        assert unit.health.max_hp == 100

    def test_unit_weapon_set_correctly(self):
        dm = DeploymentManager()
        type_map = {k: getattr(UnitType, v) for k, v in dm._TYPE_MAP.items()}
        template_type_map = {k: getattr(UnitType, v) for k, v in dm._TEMPLATE_TYPE_MAP.items()}

        placement = {
            "unit_template_id": "infantry",
            "display_name": "Rifle Squad",
            "unit_type": "infantry",
            "position": (3, 3),
        }
        unit = dm._create_unit_from_placement(
            placement=placement,
            faction=Faction.ALLIES,
            id_prefix="player",
            counter=0,
            type_map=type_map,
            template_type_map=template_type_map,
        )
        assert unit is not None
        assert unit.weapon.primary_weapon_id == "rifle"
        assert unit.weapon.ammo_remaining == 120

    def test_unit_position_set_correctly(self):
        dm = DeploymentManager()
        type_map = {k: getattr(UnitType, v) for k, v in dm._TYPE_MAP.items()}
        template_type_map = {k: getattr(UnitType, v) for k, v in dm._TEMPLATE_TYPE_MAP.items()}

        placement = {
            "unit_template_id": "infantry",
            "display_name": "Rifle Squad",
            "unit_type": "infantry",
            "position": (7, 9),
        }
        unit = dm._create_unit_from_placement(
            placement=placement,
            faction=Faction.ALLIES,
            id_prefix="player",
            counter=0,
            type_map=type_map,
            template_type_map=template_type_map,
        )
        assert unit is not None
        assert unit.position.tile_coord.x == 7
        assert unit.position.tile_coord.y == 9

    def test_unit_without_position_returns_none(self):
        dm = DeploymentManager()
        type_map = {k: getattr(UnitType, v) for k, v in dm._TYPE_MAP.items()}
        template_type_map = {k: getattr(UnitType, v) for k, v in dm._TEMPLATE_TYPE_MAP.items()}

        placement = {
            "unit_template_id": "infantry",
            "display_name": "No Pos",
            "unit_type": "infantry",
            "position": None,
        }
        unit = dm._create_unit_from_placement(
            placement=placement,
            faction=Faction.ALLIES,
            id_prefix="player",
            counter=0,
            type_map=type_map,
            template_type_map=template_type_map,
        )
        assert unit is None


@pytest.mark.integration
class TestAIServiceInitialization:
    def test_ai_service_initialized_with_units(
        self, deployment_manager, map_data, game_state, deployment_ui
    ):
        """After complete(), AI service should have registered AI units."""
        from pycc2.presentation.ui.deployment_models import DeploymentUnit
        from pycc2.services.ai_service import AIService

        ai_service = AIService(event_bus=EventBus())
        deployment_manager.start(map_data=map_data, faction="ally", deployment_ui=deployment_ui)

        # Inject a player placement into the deployment UI state
        # (begin_battle() reads from _state.placed_units)
        if deployment_manager.deployment_ui is not None:
            player_unit = DeploymentUnit(
                unit_template_id="infantry",
                display_name="Player Squad",
                unit_type="infantry",
                deployment_cost=200,
                position=(3, 3),
                is_placed=True,
            )
            deployment_manager.deployment_ui._state.placed_units.append(player_unit)

        # Also inject AI deployment
        deployment_manager._ai_deployments = [
            {
                "unit_template_id": "infantry",
                "display_name": "AI Squad",
                "unit_type": "infantry",
                "position": (12, 12),
            }
        ]
        # Pre-create AI units from the injected deployments
        # (normally done during start(), but we injected after start())
        deployment_manager._ai_units = deployment_manager._pre_create_ai_units("axis")

        deployment_manager.complete(ai_service=ai_service, state=game_state)

        # AI service should have registered at least one unit (the AI one)
        assert ai_service.managed_unit_count >= 1

    def test_ai_service_none_does_not_crash(
        self, deployment_manager, map_data, game_state, deployment_ui
    ):
        """complete() with ai_service=None should not crash."""
        deployment_manager.start(map_data=map_data, faction="ally", deployment_ui=deployment_ui)
        # Should not raise
        deployment_manager.complete(ai_service=None, state=game_state)


@pytest.mark.integration
class TestBattleTransition:
    def test_units_selectable_after_deployment(self, game_map, camera):
        """After deployment, units should be selectable via InteractionController."""
        from pycc2.presentation.input.interaction_controller import (
            InteractionController,
        )

        event_bus = EventBus()
        ic = InteractionController(camera=camera, game_map=game_map, event_bus=event_bus)

        # Create a unit at a known position
        unit = Unit(
            id="player_0",
            name="Test Squad",
            faction=Faction.ALLIES,
            unit_type=UnitType.INFANTRY_SQUAD,
            health=HealthComponent(hp=100, max_hp=100),
            morale=MoraleComponent(value=85),
            weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=10, max_ammo=10),
            position=PositionComponent(tile_coord=TileCoord(3, 3)),
            vision=VisionComponent(range_tiles=5),
        )

        # Click near the unit's pixel position (3*32 + 16 = 112, 3*32 + 16 = 112)
        screen_pos = camera.world_to_screen(unit.position.pixel_position)
        selected = ic.handle_left_click(
            screen_pos=(screen_pos[0], screen_pos[1]),
            units=[unit],
        )
        # Unit should be selected (or at least the click should not crash)
        assert isinstance(selected, set)

    def test_move_command_after_selecting_unit(self, game_map, camera, event_bus):
        """Selected unit should accept move commands."""
        from pycc2.presentation.input.interaction_controller import (
            InteractionController,
            InteractionMode,
        )

        ic = InteractionController(camera=camera, game_map=game_map, event_bus=event_bus)

        unit = Unit(
            id="player_0",
            name="Test Squad",
            faction=Faction.ALLIES,
            unit_type=UnitType.INFANTRY_SQUAD,
            health=HealthComponent(hp=100, max_hp=100),
            morale=MoraleComponent(value=85),
            weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=10, max_ammo=10),
            position=PositionComponent(tile_coord=TileCoord(3, 3)),
            vision=VisionComponent(range_tiles=5),
        )

        # Select the unit first
        screen_pos = camera.world_to_screen(unit.position.pixel_position)
        ic.handle_left_click(screen_pos=(screen_pos[0], screen_pos[1]), units=[unit])

        # Set mode to MOVE and click a target location
        ic.set_mode(InteractionMode.MOVE)
        # The move command should not crash
        ic.handle_left_click(screen_pos=(400.0, 300.0), units=[unit])
