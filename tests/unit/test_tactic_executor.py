from unittest.mock import MagicMock

import pytest

from pycc2.domain.ai.tactic_executor import TacticExecutor
from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.services.event_bus import EventBus


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
