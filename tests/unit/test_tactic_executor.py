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


# ============================================================================
# Phase: v0.4.3 — TacticExecutor untested handler coverage (batch 1/4)
# Target: 5 simplest handlers (SET_AMBUSH / BREAK_AMBUSH / COUNTER_ATTACK /
#         TAKE_COVER / SURRENDER). See TD-064 in TECH_DEBT.md for the
#         tactic_executor split prerequisite (lock behavior via tests first).
# DevSquad Testing Iron Rules followed:
#   - Rule 1 (Documentation First): signatures verified from
#     combat_mixin.py / defense_mixin.py / logistics_mixin.py before writing.
#   - Rule 2 (Failure Means Report): assertions express expected behavior,
#     not loosened to pass.
#   - Rule 3 (Dimension Completeness): each handler covers Happy + Error +
#     Boundary.
# ============================================================================


class TestTacticExecutorSetAmbush:
    """Cover _execute_set_ambush (combat_mixin).

    Behavior: set_movement_mode("sneak") + return True; unknown unit -> False.
    """

    def test_set_ambush_switches_unit_to_sneak_mode(self, executor):
        unit = make_unit("u_ambush", TileCoord(0, 0))
        executor.register_unit(unit)
        intent = TacticIntent(unit_id="u_ambush", tactic_type=TacticType.SET_AMBUSH)
        assert executor.execute(intent) is True
        assert unit._movement_mode == "sneak"

    def test_set_ambush_unknown_unit_returns_false(self, executor):
        intent = TacticIntent(unit_id="ghost", tactic_type=TacticType.SET_AMBUSH)
        assert executor.execute(intent) is False

    def test_set_ambush_is_idempotent_when_already_sneak(self, executor):
        unit = make_unit("u_ambush_idem", TileCoord(1, 1))
        unit.set_movement_mode("sneak")
        executor.register_unit(unit)
        intent = TacticIntent(
            unit_id="u_ambush_idem", tactic_type=TacticType.SET_AMBUSH
        )
        assert executor.execute(intent) is True
        assert unit._movement_mode == "sneak"


class TestTacticExecutorBreakAmbush:
    """Cover _execute_break_ambush (combat_mixin).

    Behavior: restore "normal" mode + delegate to _execute_attack with same
    target_unit_id / target_position / path. Returns _execute_attack's result.
    """

    def test_break_ambush_restores_normal_and_publishes_attack(
        self, executor, event_bus
    ):
        from pycc2.domain.interfaces.event_types import PlayerCommand

        published: list[PlayerCommand] = []
        event_bus.subscribe(PlayerCommand, lambda e: published.append(e))

        attacker = make_unit("u_ambush_atk", TileCoord(0, 0))
        attacker.set_movement_mode("sneak")
        target = make_unit("u_ambush_tgt", TileCoord(5, 5))
        target.faction = Faction.AXIS  # ensure opposite faction for clarity
        executor.register_unit(attacker)
        executor.register_unit(target)

        intent = TacticIntent(
            unit_id="u_ambush_atk",
            tactic_type=TacticType.BREAK_AMBUSH,
            target_unit_id="u_ambush_tgt",
        )
        assert executor.execute(intent) is True
        assert attacker._movement_mode == "normal"
        assert len(published) == 1
        assert published[0]["command"] == "attack"
        assert published[0]["unit_ids"] == ["u_ambush_atk"]
        assert published[0]["target_id"] == "u_ambush_tgt"

    def test_break_ambush_unknown_unit_returns_false(self, executor, event_bus):
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        intent = TacticIntent(
            unit_id="ghost",
            tactic_type=TacticType.BREAK_AMBUSH,
            target_unit_id="enemy_1",
        )
        assert executor.execute(intent) is False
        assert published == []

    def test_break_ambush_without_target_returns_false_but_mode_reset(
        self, executor
    ):
        """Boundary: no target_unit_id -> _execute_attack returns False because
        target is None. Movement mode is still reset to "normal" before
        delegation."""
        unit = make_unit("u_ambush_nt", TileCoord(2, 2))
        unit.set_movement_mode("sneak")
        executor.register_unit(unit)
        intent = TacticIntent(
            unit_id="u_ambush_nt", tactic_type=TacticType.BREAK_AMBUSH
        )
        assert executor.execute(intent) is False
        # Mode reset happens before delegation, so it should be "normal" now.
        assert unit._movement_mode == "normal"


class TestTacticExecutorCounterAttack:
    """Cover _execute_counter_attack (combat_mixin).

    Behavior: construct ATTACK intent with priority+5 and delegate to
    _execute_attack. Does NOT call _get_unit directly — relies on
    _execute_attack to validate unit/target.
    """

    def test_counter_attack_delegates_to_attack_with_priority_boost(
        self, executor, event_bus
    ):
        from pycc2.domain.interfaces.event_types import PlayerCommand

        published: list[PlayerCommand] = []
        event_bus.subscribe(PlayerCommand, lambda e: published.append(e))

        attacker = make_unit("u_ca_atk", TileCoord(0, 0))
        target = make_unit("u_ca_tgt", TileCoord(5, 5))
        target.faction = Faction.AXIS
        executor.register_unit(attacker)
        executor.register_unit(target)

        intent = TacticIntent(
            unit_id="u_ca_atk",
            tactic_type=TacticType.COUNTER_ATTACK,
            target_unit_id="u_ca_tgt",
            priority=10,
        )
        assert executor.execute(intent) is True
        assert len(published) == 1
        assert published[0]["command"] == "attack"
        assert published[0]["target_id"] == "u_ca_tgt"

    def test_counter_attack_unknown_unit_returns_false(self, executor):
        """Error: unknown unit -> _execute_attack returns False (no target)."""
        intent = TacticIntent(
            unit_id="ghost",
            tactic_type=TacticType.COUNTER_ATTACK,
            target_unit_id="enemy_1",
        )
        assert executor.execute(intent) is False

    def test_counter_attack_without_target_returns_false(self, executor):
        """Boundary: no target_unit_id -> _execute_attack returns False
        because target is None."""
        unit = make_unit("u_ca_nt", TileCoord(0, 0))
        executor.register_unit(unit)
        intent = TacticIntent(
            unit_id="u_ca_nt", tactic_type=TacticType.COUNTER_ATTACK
        )
        assert executor.execute(intent) is False


class TestTacticExecutorTakeCover:
    """Cover _execute_take_cover (defense_mixin).

    Behavior:
      - With target_position -> delegate to _execute_move_to (priority+5).
      - Without target_position -> log + return True (cover in place).
      - Unknown unit -> False.
    """

    def test_take_cover_with_target_moves_unit(self, executor, event_bus):
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_tc", TileCoord(0, 0))
        executor.register_unit(unit)
        intent = TacticIntent(
            unit_id="u_tc",
            tactic_type=TacticType.TAKE_COVER,
            target_position=TileCoord(3, 3),
        )
        assert executor.execute(intent) is True
        assert unit.position.tile_coord == TileCoord(3, 3)
        assert any(e.get("unit_id") == "u_tc" for e in published)

    def test_take_cover_without_target_returns_true_in_place(self, executor):
        unit = make_unit("u_tc_ip", TileCoord(2, 2))
        executor.register_unit(unit)
        intent = TacticIntent(
            unit_id="u_tc_ip", tactic_type=TacticType.TAKE_COVER
        )
        assert executor.execute(intent) is True
        # Unit stays in place.
        assert unit.position.tile_coord == TileCoord(2, 2)

    def test_take_cover_unknown_unit_returns_false(self, executor):
        intent = TacticIntent(
            unit_id="ghost",
            tactic_type=TacticType.TAKE_COVER,
            target_position=TileCoord(1, 1),
        )
        assert executor.execute(intent) is False


class TestTacticExecutorSurrender:
    """Cover _execute_surrender (logistics_mixin).

    Behavior:
      - force_transition(SURRENDERED) + zero ammo + publish event + return True.
      - Already SURRENDERED or DEAD -> return False (no-op).
      - Unknown unit -> False.
    """

    def test_surrender_transitions_state_zeros_ammo_publishes_event(
        self, executor, event_bus
    ):
        from pycc2.domain.entities.unit import UnitState

        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))

        unit = make_unit("u_sur", TileCoord(4, 4))
        assert unit.weapon.ammo_remaining == 30  # default from make_unit
        executor.register_unit(unit)

        intent = TacticIntent(unit_id="u_sur", tactic_type=TacticType.SURRENDER)
        assert executor.execute(intent) is True
        assert unit.state_machine.current is UnitState.SURRENDERED
        assert unit.weapon.ammo_remaining == 0

        surrender_events = [e for e in published if e.get("action") == "surrender"]
        assert len(surrender_events) == 1
        assert surrender_events[0]["unit_id"] == "u_sur"
        assert surrender_events[0]["position"] == (4, 4)

    def test_surrender_unknown_unit_returns_false(self, executor, event_bus):
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        intent = TacticIntent(unit_id="ghost", tactic_type=TacticType.SURRENDER)
        assert executor.execute(intent) is False
        assert published == []

    def test_surrender_when_already_surrendered_returns_false(
        self, executor, event_bus
    ):
        from pycc2.domain.entities.unit import UnitState

        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))

        unit = make_unit("u_sur_dup", TileCoord(1, 1))
        unit.state_machine.force_transition(UnitState.SURRENDERED)
        unit.weapon.ammo_remaining = 0
        executor.register_unit(unit)

        intent = TacticIntent(
            unit_id="u_sur_dup", tactic_type=TacticType.SURRENDER
        )
        assert executor.execute(intent) is False
        # No new event published.
        assert published == []

    def test_surrender_when_dead_returns_false(self, executor, event_bus):
        from pycc2.domain.entities.unit import UnitState

        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))

        unit = make_unit("u_sur_dead", TileCoord(1, 1))
        unit.state_machine.force_transition(UnitState.DEAD)
        executor.register_unit(unit)

        intent = TacticIntent(
            unit_id="u_sur_dead", tactic_type=TacticType.SURRENDER
        )
        assert executor.execute(intent) is False
        assert published == []
