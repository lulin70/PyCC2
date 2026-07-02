from unittest.mock import MagicMock

import numpy as np
import pytest

from pycc2.domain.ai.tactic_executor import TacticExecutor
from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.terrain_type import TerrainType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.infrastructure.events.event_bus import EventBus


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def executor(event_bus):
    return TacticExecutor(event_bus=event_bus)


class TestTacticExecutorIdle:
    def test_execute_idle_success(self, executor):
        unit_mock = MagicMock()
        unit_mock.id = "unit_1"
        executor.register_unit(unit_mock)
        intent = TacticIntent(unit_id="unit_1", tactic_type=TacticType.IDLE)
        assert executor.execute(intent) is True

    def test_execute_idle_unknown_unit(self, executor):
        intent = TacticIntent(unit_id="nonexistent", tactic_type=TacticType.IDLE)
        assert executor.execute(intent) is False


class TestTacticExecutorMoveTo:
    def test_execute_move_to_publishes_event(self, executor, event_bus):
        published_events = []
        event_bus.subscribe(dict, lambda e: published_events.append(e))
        unit_mock = MagicMock()
        unit_mock.id = "unit_1"
        unit_mock.position.tile_coord = TileCoord(0, 0)
        executor.register_unit(unit_mock)
        intent = TacticIntent(
            unit_id="unit_1",
            tactic_type=TacticType.MOVE_TO,
            target_position=TileCoord(5, 5),
        )
        result = executor.execute(intent)
        assert result is True
        assert len(published_events) >= 1
        move_event = published_events[-1]
        assert move_event["unit_id"] == "unit_1"


class TestTacticExecutorAttack:
    def test_execute_attack_publishes_player_command(self, executor, event_bus):
        from pycc2.domain.interfaces.event_types import PlayerCommand

        published_events = []
        event_bus.subscribe(PlayerCommand, lambda e: published_events.append(e))
        unit_mock = MagicMock()
        unit_mock.id = "unit_1"
        target_mock = MagicMock()
        target_mock.id = "enemy_1"
        executor.register_unit(unit_mock)
        executor.register_unit(target_mock)
        intent = TacticIntent(
            unit_id="unit_1",
            tactic_type=TacticType.ATTACK,
            target_unit_id="enemy_1",
        )
        result = executor.execute(intent)
        assert result is True
        assert len(published_events) == 1
        assert published_events[0]["command"] == "attack"
        assert published_events[0]["unit_ids"] == ["unit_1"]
        assert published_events[0]["target_id"] == "enemy_1"


class TestTacticExecutorRetreat:
    def test_execute_retreat_moves_to_safe_position(self, executor, event_bus):
        published_events = []
        event_bus.subscribe(dict, lambda e: published_events.append(e))
        unit_mock = MagicMock()
        unit_mock.id = "unit_1"
        unit_mock.position.tile_coord = TileCoord(10, 10)
        executor.register_unit(unit_mock)
        intent = TacticIntent(unit_id="unit_1", tactic_type=TacticType.RETREAT)
        result = executor.execute(intent)
        assert result is True
        assert len(published_events) >= 1


class TestTacticExecutorHoldPosition:
    def test_execute_hold_position(self, executor):
        unit_mock = MagicMock()
        unit_mock.id = "unit_1"
        executor.register_unit(unit_mock)
        intent = TacticIntent(unit_id="unit_1", tactic_type=TacticType.HOLD_POSITION)
        result = executor.execute(intent)
        assert result is True


class TestTacticExecutorDefend:
    def test_execute_defend(self, executor):
        unit_mock = MagicMock()
        unit_mock.id = "unit_1"
        executor.register_unit(unit_mock)
        intent = TacticIntent(unit_id="unit_1", tactic_type=TacticType.DEFEND)
        result = executor.execute(intent)
        assert result is True


class TestTacticExecutorPatrol:
    def test_execute_patrol_with_destination(self, executor, event_bus):
        published_events = []
        event_bus.subscribe(dict, lambda e: published_events.append(e))
        unit_mock = MagicMock()
        unit_mock.id = "unit_1"
        unit_mock.position.tile_coord = TileCoord(0, 0)
        executor.register_unit(unit_mock)
        intent = TacticIntent(
            unit_id="unit_1",
            tactic_type=TacticType.PATROL,
            target_position=TileCoord(3, 3),
        )
        result = executor.execute(intent)
        assert result is True


class TestTacticExecutorSuppressFire:
    def test_execute_suppress_fire_without_engine(self, executor):
        intent = TacticIntent(
            unit_id="unit_1",
            tactic_type=TacticType.SUPPRESS_FIRE,
            target_unit_id="enemy_1",
        )
        unit_mock = MagicMock()
        unit_mock.id = "unit_1"
        target_mock = MagicMock()
        target_mock.id = "enemy_1"
        executor.register_unit(unit_mock)
        executor.register_unit(target_mock)
        result = executor.execute(intent)
        assert result is False


class TestTacticExecutorRegistration:
    def test_register_and_unregister(self, executor):
        unit_mock = MagicMock()
        unit_mock.id = "unit_1"
        executor.register_unit(unit_mock)
        assert "unit_1" in executor._unit_registry
        executor.unregister_unit("unit_1")
        assert "unit_1" not in executor._unit_registry


def make_unit(
    uid: str,
    pos: TileCoord,
    *,
    hp: int = 100,
    morale_value: int = 80,
) -> Unit:
    """Build a real infantry Unit with concrete components (no mocks)."""
    return Unit(
        id=uid,
        name=uid,
        faction=Faction.ALLIES,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=hp, max_hp=hp),
        morale=MoraleComponent(value=morale_value, panic_threshold=20, rout_threshold=10),
        weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=30, max_ammo=30),
        position=PositionComponent(tile_coord=pos),
        vision=VisionComponent(range_tiles=6),
    )


@pytest.fixture
def game_map() -> GameMap:
    grid = np.full((20, 20), TerrainType.OPEN.value, dtype=np.int8)
    return GameMap(id="test_map", name="Test Map", width=20, height=20, tile_grid=grid)


@pytest.fixture
def executor_with_map(event_bus, game_map) -> TacticExecutor:
    return TacticExecutor(event_bus=event_bus, game_map=game_map)


class TestMissingHandlers:
    # --- _execute_flanking ---
    def test_flanking_with_target_moves_unit(self, executor, event_bus):
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_flank", TileCoord(0, 0))
        executor.register_unit(unit)
        intent = TacticIntent(
            unit_id="u_flank",
            tactic_type=TacticType.FLANKING,
            target_position=TileCoord(5, 5),
        )
        assert executor.execute(intent) is True
        assert unit.position.tile_coord == TileCoord(5, 5)
        assert any(e.get("unit_id") == "u_flank" for e in published)

    def test_flanking_unknown_unit_returns_false(self, executor):
        intent = TacticIntent(
            unit_id="ghost",
            tactic_type=TacticType.FLANKING,
            target_position=TileCoord(1, 1),
        )
        assert executor.execute(intent) is False

    def test_flanking_without_target_returns_true_no_move(self, executor, event_bus):
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_flank_nt", TileCoord(2, 2))
        executor.register_unit(unit)
        intent = TacticIntent(unit_id="u_flank_nt", tactic_type=TacticType.FLANKING)
        assert executor.execute(intent) is True
        assert unit.position.tile_coord == TileCoord(2, 2)
        assert published == []

    # --- _execute_coordinated_advance ---
    def test_coordinated_advance_with_target_moves_unit(self, executor, event_bus):
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_adv", TileCoord(0, 0))
        executor.register_unit(unit)
        intent = TacticIntent(
            unit_id="u_adv",
            tactic_type=TacticType.COORDINATED_ADVANCE,
            target_position=TileCoord(4, 4),
        )
        assert executor.execute(intent) is True
        assert unit.position.tile_coord == TileCoord(4, 4)
        assert any(e.get("unit_id") == "u_adv" for e in published)

    def test_coordinated_advance_unknown_unit_returns_false(self, executor):
        intent = TacticIntent(
            unit_id="ghost",
            tactic_type=TacticType.COORDINATED_ADVANCE,
            target_position=TileCoord(1, 1),
        )
        assert executor.execute(intent) is False

    def test_coordinated_advance_without_target_returns_true(self, executor):
        unit = make_unit("u_adv_nt", TileCoord(3, 3))
        executor.register_unit(unit)
        intent = TacticIntent(unit_id="u_adv_nt", tactic_type=TacticType.COORDINATED_ADVANCE)
        assert executor.execute(intent) is True
        assert unit.position.tile_coord == TileCoord(3, 3)

    # --- _execute_capture_vl ---
    def test_capture_vl_with_target_moves_unit(self, executor, event_bus):
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_cap", TileCoord(1, 1))
        executor.register_unit(unit)
        intent = TacticIntent(
            unit_id="u_cap",
            tactic_type=TacticType.CAPTURE_VL,
            target_position=TileCoord(7, 7),
        )
        assert executor.execute(intent) is True
        assert unit.position.tile_coord == TileCoord(7, 7)
        assert any(e.get("unit_id") == "u_cap" for e in published)

    def test_capture_vl_unknown_unit_returns_false(self, executor):
        intent = TacticIntent(
            unit_id="ghost",
            tactic_type=TacticType.CAPTURE_VL,
            target_position=TileCoord(2, 2),
        )
        assert executor.execute(intent) is False

    def test_capture_vl_without_target_returns_false(self, executor):
        unit = make_unit("u_cap_nt", TileCoord(0, 0))
        executor.register_unit(unit)
        intent = TacticIntent(unit_id="u_cap_nt", tactic_type=TacticType.CAPTURE_VL)
        assert executor.execute(intent) is False

    # --- _execute_defend_vl ---
    def test_defend_vl_unit_at_target_sets_defend_mode(self, executor):
        target = TileCoord(5, 5)
        unit = make_unit("u_def", target)
        executor.register_unit(unit)
        intent = TacticIntent(
            unit_id="u_def",
            tactic_type=TacticType.DEFEND_VL,
            target_position=target,
        )
        assert executor.execute(intent) is True
        assert unit._movement_mode == "defend"

    def test_defend_vl_unknown_unit_returns_false(self, executor):
        intent = TacticIntent(
            unit_id="ghost",
            tactic_type=TacticType.DEFEND_VL,
            target_position=TileCoord(1, 1),
        )
        assert executor.execute(intent) is False

    def test_defend_vl_unit_away_from_target_moves(self, executor, event_bus):
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_def_mv", TileCoord(0, 0))
        executor.register_unit(unit)
        intent = TacticIntent(
            unit_id="u_def_mv",
            tactic_type=TacticType.DEFEND_VL,
            target_position=TileCoord(6, 6),
        )
        assert executor.execute(intent) is True
        assert unit.position.tile_coord == TileCoord(6, 6)
        assert any(e.get("unit_id") == "u_def_mv" for e in published)

    def test_defend_vl_without_target_sets_defend_mode(self, executor):
        unit = make_unit("u_def_nt", TileCoord(2, 2))
        executor.register_unit(unit)
        intent = TacticIntent(unit_id="u_def_nt", tactic_type=TacticType.DEFEND_VL)
        assert executor.execute(intent) is True
        assert unit._movement_mode == "defend"

    # --- _execute_demolish_bridge ---
    def test_demolish_bridge_destroys_adjacent_bridge(self, executor_with_map, game_map, event_bus):
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        game_map.set_terrain(TileCoord(6, 5), TerrainType.BRIDGE)
        unit = make_unit("u_demo", TileCoord(5, 5))
        executor_with_map.register_unit(unit)
        intent = TacticIntent(unit_id="u_demo", tactic_type=TacticType.DEMOLISH_BRIDGE)
        assert executor_with_map.execute(intent) is True
        assert game_map.get_terrain(TileCoord(6, 5)) == TerrainType.BRIDGE_DESTROYED
        demo_events = [e for e in published if e.get("action") == "demolish_bridge"]
        assert len(demo_events) == 1
        assert (6, 5) in demo_events[0]["bridge_tiles"]

    def test_demolish_bridge_no_bridge_returns_false(self, executor_with_map):
        unit = make_unit("u_demo_nb", TileCoord(10, 10))
        executor_with_map.register_unit(unit)
        intent = TacticIntent(unit_id="u_demo_nb", tactic_type=TacticType.DEMOLISH_BRIDGE)
        assert executor_with_map.execute(intent) is False

    def test_demolish_bridge_unknown_unit_returns_false(self, executor_with_map):
        intent = TacticIntent(unit_id="ghost", tactic_type=TacticType.DEMOLISH_BRIDGE)
        assert executor_with_map.execute(intent) is False

    def test_demolish_bridge_without_game_map_returns_false(self, executor):
        unit = make_unit("u_demo_nm", TileCoord(5, 5))
        executor.register_unit(unit)
        intent = TacticIntent(unit_id="u_demo_nm", tactic_type=TacticType.DEMOLISH_BRIDGE)
        assert executor.execute(intent) is False
