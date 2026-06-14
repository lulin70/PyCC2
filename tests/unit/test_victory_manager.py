"""
Unit Tests for VictoryManager

Tests victory condition evaluation, faction elimination detection,
and game-over state management.
"""

from unittest.mock import Mock

import pytest

from pycc2.services.victory_manager import VictoryManager

# ===========================================================================
# Stub helpers
# ===========================================================================


class StubEventBus:
    """Minimal event bus stub that records subscriptions."""

    def __init__(self):
        self.subscriptions = []

    def subscribe(self, event_type, handler):
        self.subscriptions.append((event_type, handler))


def _make_unit(unit_id, faction_name, alive=True, tile_x=5, tile_y=5):
    """Create a mock unit."""
    unit = Mock()
    unit.id = unit_id
    unit.is_alive = alive
    faction = Mock()
    faction.name = faction_name
    unit.faction = faction

    from pycc2.domain.value_objects.tile_coord import TileCoord

    pos = Mock()
    pos.tile_coord = TileCoord(tile_x, tile_y)
    unit.position = pos
    return unit


# ===========================================================================
# Tests
# ===========================================================================


@pytest.mark.unit
class TestVictoryManagerInit:
    """Test VictoryManager initialization."""

    def test_default_state(self):
        vm = VictoryManager()
        assert vm._game_result is None
        assert vm._game_over_tick == 0
        assert vm._show_post_battle is False
        assert vm._battle_stats is None
        assert vm._victory_evaluator is None

    def test_initialize_creates_evaluator(self):
        vm = VictoryManager()
        bus = StubEventBus()
        vm.initialize(bus)
        assert vm._victory_evaluator is not None
        assert vm._battle_stats is not None
        assert vm._game_result is None

    def test_initialize_subscribes_to_events(self):
        vm = VictoryManager()
        bus = StubEventBus()
        vm.initialize(bus)
        # Should have subscribed to UnitAttacked
        assert len(bus.subscriptions) >= 1


@pytest.mark.unit
class TestEvaluate:
    """Test victory condition evaluation."""

    def test_evaluate_returns_none_before_600_ticks(self):
        vm = VictoryManager()
        bus = StubEventBus()
        vm.initialize(bus)
        units = [_make_unit("u1", "ALLIES")]
        # Tick 30 is before the 600 minimum
        result = vm.evaluate(units, 30)
        assert result is None

    def test_evaluate_returns_none_when_no_evaluator(self):
        vm = VictoryManager()
        units = [_make_unit("u1", "ALLIES")]
        result = vm.evaluate(units, 900)
        assert result is None

    def test_evaluate_returns_none_on_non_30_multiple_tick(self):
        vm = VictoryManager()
        bus = StubEventBus()
        vm.initialize(bus)
        units = [_make_unit("u1", "ALLIES")]
        # Tick 601 is >= 600 but not a multiple of 30
        result = vm.evaluate(units, 601)
        assert result is None

    def test_evaluate_sets_game_result_on_victory(self):
        vm = VictoryManager()
        bus = StubEventBus()
        vm.initialize(bus)

        # Mock the evaluator to return a non-ONGOING result
        mock_result = Mock()
        mock_result.name = "ALLIES_WIN"
        vm._victory_evaluator.evaluate = Mock(return_value=(mock_result, "enemies eliminated"))

        units = [_make_unit("u1", "ALLIES")]
        result = vm.evaluate(units, 600)
        assert result is not None
        assert vm._game_result is mock_result
        assert vm._game_over_tick == 600
        assert vm._show_post_battle is True

    def test_evaluate_returns_none_on_ongoing(self):
        vm = VictoryManager()
        bus = StubEventBus()
        vm.initialize(bus)

        mock_result = Mock()
        mock_result.name = "ONGOING"
        vm._victory_evaluator.evaluate = Mock(return_value=(mock_result, ""))

        units = [_make_unit("u1", "ALLIES")]
        result = vm.evaluate(units, 600)
        assert result is None
        assert vm._game_result is None


@pytest.mark.unit
class TestReset:
    """Test reset functionality."""

    def test_reset_clears_game_state(self):
        vm = VictoryManager()
        vm._game_result = Mock()
        vm._game_over_tick = 500
        vm._show_post_battle = True

        vm.reset()
        assert vm._game_result is None
        assert vm._game_over_tick == 0
        assert vm._show_post_battle is False


@pytest.mark.unit
class TestProperties:
    """Test property accessors."""

    def test_game_result_property(self):
        vm = VictoryManager()
        assert vm.game_result is None
        mock_result = Mock()
        vm._game_result = mock_result
        assert vm.game_result is mock_result

    def test_show_post_battle_property(self):
        vm = VictoryManager()
        assert vm.show_post_battle is False
        vm._show_post_battle = True
        assert vm.show_post_battle is True

    def test_battle_stats_property_none_before_init(self):
        vm = VictoryManager()
        assert vm.battle_stats is None

    def test_battle_stats_property_after_init(self):
        vm = VictoryManager()
        bus = StubEventBus()
        vm.initialize(bus)
        assert vm.battle_stats is not None


@pytest.mark.unit
class TestBuildObjectivesFromMap:
    """Test objective building from game map."""

    def test_fallback_objective_when_no_map(self):
        vm = VictoryManager()
        objectives = vm._build_objectives_from_map()
        assert len(objectives) == 1
        assert objectives[0].id == "vl_center"

    def test_objectives_from_combat_director_map(self):
        vm = VictoryManager()

        # Mock combat_director with a game_map that has objectives
        # The source code does getattr(pos, 'x', pos[0]) which evaluates
        # pos[0] eagerly, so the position must be subscriptable.
        # But the code checks for .x first via getattr, so we need an
        # object that has both .x/.y AND is subscriptable.
        class SubscriptablePos:
            x = 10
            y = 10

            def __getitem__(self, idx):
                return (10, 10)[idx]

        mock_obj = Mock()
        mock_obj.position = SubscriptablePos()
        mock_obj.tile_coord = None
        mock_obj.id = "vl_1"
        mock_obj.name = "Bridge"
        mock_obj.radius = 3
        mock_obj.points = 200

        mock_map = Mock()
        mock_map.objectives = [mock_obj]

        mock_cd = Mock()
        mock_cd._game_map = mock_map
        vm._combat_director = mock_cd

        objectives = vm._build_objectives_from_map()
        assert len(objectives) >= 1
        assert objectives[0].id == "vl_1"
