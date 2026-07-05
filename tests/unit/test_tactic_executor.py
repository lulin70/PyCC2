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
    unit_type: UnitType = UnitType.INFANTRY_SQUAD,
    primary_weapon_id: str = "rifle",
    max_ammo: int = 30,
    vision_range: int = 6,
) -> Unit:
    """Build a real Unit with concrete components (no mocks).

    Default produces an INFANTRY_SQUAD; pass ``unit_type`` (and matching
    weapon/vision args) for other types such as AT_GUN_TEAM (engineer proxy
    for mine warfare).
    """
    return Unit(
        id=uid,
        name=uid,
        faction=Faction.ALLIES,
        unit_type=unit_type,
        health=HealthComponent(hp=hp, max_hp=hp),
        morale=MoraleComponent(value=morale_value, panic_threshold=20, rout_threshold=10),
        weapon=WeaponComponent(
            primary_weapon_id=primary_weapon_id,
            ammo_remaining=max_ammo,
            max_ammo=max_ammo,
        ),
        position=PositionComponent(tile_coord=pos),
        vision=VisionComponent(range_tiles=vision_range),
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


# ============================================================================
# Phase: v0.4.3 — TacticExecutor untested handler coverage (batch 2/4)
# Target: 5 medium-complexity handlers (REGROUP / DEPLOY_SMOKE /
#         DETECT_MINES / CALL_ARTILLERY / MELEE_ATTACK). Each involves a
#         single subsystem call (smoke_manager / mine_warfare /
#         artillery_manager / MeleeCombatSystem) or simple MOVE_TO delegation.
# DevSquad Testing Iron Rules followed:
#   - Rule 1 (Documentation First): signatures verified from
#     movement_mixin.py / smoke_mixin.py / engineering_mixin.py /
#     combat_mixin.py + ArtilleryManager / SmokeGrenadeCapability /
#     MeleeCombatSystem.can_melee preconditions before writing.
#   - Rule 2 (Failure Means Report): assertions express expected behavior,
#     not loosened to pass.
#   - Rule 3 (Dimension Completeness): each handler covers Happy + Error +
#     Boundary.
# ============================================================================


class TestTacticExecutorRegroup:
    """Cover _execute_regroup (movement_mixin).

    Behavior:
      - With target_position -> delegate to _execute_move_to (priority+7).
      - Without target_position -> log + return True (regroup in place).
      - Unknown unit -> False.
    """

    def test_regroup_with_target_moves_unit(self, executor, event_bus):
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_rg", TileCoord(0, 0))
        executor.register_unit(unit)
        intent = TacticIntent(
            unit_id="u_rg",
            tactic_type=TacticType.REGROUP,
            target_position=TileCoord(4, 4),
        )
        assert executor.execute(intent) is True
        assert unit.position.tile_coord == TileCoord(4, 4)
        assert any(e.get("unit_id") == "u_rg" for e in published)

    def test_regroup_without_target_returns_true_in_place(self, executor):
        unit = make_unit("u_rg_ip", TileCoord(2, 2))
        executor.register_unit(unit)
        intent = TacticIntent(unit_id="u_rg_ip", tactic_type=TacticType.REGROUP)
        assert executor.execute(intent) is True
        assert unit.position.tile_coord == TileCoord(2, 2)

    def test_regroup_unknown_unit_returns_false(self, executor):
        intent = TacticIntent(
            unit_id="ghost",
            tactic_type=TacticType.REGROUP,
            target_position=TileCoord(1, 1),
        )
        assert executor.execute(intent) is False


class TestTacticExecutorDeploySmoke:
    """Cover _execute_deploy_smoke (smoke_mixin).

    Behavior:
      - Consume smoke charge (if capability registered) + create
        SmokeDeployment on smoke_manager + publish event + return True.
      - Units without registered capability can still deploy (fallback).
      - Unknown unit / no target_position / empty capability -> False.
    """

    def test_deploy_smoke_without_capability_fallback_success(
        self, executor, event_bus
    ):
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_smoke_fb", TileCoord(0, 0))
        executor.register_unit(unit)

        intent = TacticIntent(
            unit_id="u_smoke_fb",
            tactic_type=TacticType.DEPLOY_SMOKE,
            target_position=TileCoord(3, 3),
        )
        assert executor.execute(intent) is True
        # Smoke deployment registered on smoke_manager
        assert len(executor.smoke_manager._deployments) >= 1
        smoke_events = [e for e in published if "smoke_position" in e]
        assert len(smoke_events) == 1
        assert smoke_events[0]["unit_id"] == "u_smoke_fb"
        assert smoke_events[0]["smoke_position"] == (3, 3)

    def test_deploy_smoke_with_capability_consumes_charge(
        self, executor, event_bus
    ):
        from pycc2.domain.ai.smoke_tactical_ai import SmokeGrenadeCapability

        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_smoke_cap", TileCoord(0, 0))
        executor.register_unit(unit)

        capability = SmokeGrenadeCapability.for_infantry_squad()
        assert capability.smoke_count == 2
        executor.register_smoke_capability("u_smoke_cap", capability)

        intent = TacticIntent(
            unit_id="u_smoke_cap",
            tactic_type=TacticType.DEPLOY_SMOKE,
            target_position=TileCoord(2, 2),
        )
        assert executor.execute(intent) is True
        # Charge consumed
        assert capability.smoke_count == 1
        # Event published
        smoke_events = [e for e in published if "smoke_position" in e]
        assert len(smoke_events) == 1

    def test_deploy_smoke_unknown_unit_returns_false(self, executor):
        intent = TacticIntent(
            unit_id="ghost",
            tactic_type=TacticType.DEPLOY_SMOKE,
            target_position=TileCoord(1, 1),
        )
        assert executor.execute(intent) is False

    def test_deploy_smoke_without_target_returns_false(self, executor):
        unit = make_unit("u_smoke_nt", TileCoord(0, 0))
        executor.register_unit(unit)
        intent = TacticIntent(
            unit_id="u_smoke_nt", tactic_type=TacticType.DEPLOY_SMOKE
        )
        assert executor.execute(intent) is False

    def test_deploy_smoke_with_empty_capability_returns_false(
        self, executor, event_bus
    ):
        from pycc2.domain.ai.smoke_tactical_ai import SmokeGrenadeCapability

        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_smoke_empty", TileCoord(0, 0))
        executor.register_unit(unit)

        capability = SmokeGrenadeCapability(smoke_count=0, max_smoke=2)
        assert capability.has_smoke is False
        executor.register_smoke_capability("u_smoke_empty", capability)

        intent = TacticIntent(
            unit_id="u_smoke_empty",
            tactic_type=TacticType.DEPLOY_SMOKE,
            target_position=TileCoord(1, 1),
        )
        assert executor.execute(intent) is False
        assert published == []


class TestTacticExecutorDetectMines:
    """Cover _execute_detect_mines (engineering_mixin).

    Behavior:
      - Call _mine_warfare_system.detect_mines(unit, game_map).
      - If mines detected -> publish event; always return True.
      - Unknown unit / no game_map -> False.
    """

    def test_detect_mines_no_mines_returns_true_no_event(
        self, executor_with_map, event_bus
    ):
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_dm", TileCoord(5, 5))
        executor_with_map.register_unit(unit)

        intent = TacticIntent(
            unit_id="u_dm", tactic_type=TacticType.DETECT_MINES
        )
        assert executor_with_map.execute(intent) is True
        detect_events = [e for e in published if e.get("action") == "mines_detected"]
        assert detect_events == []

    def test_detect_mines_unknown_unit_returns_false(self, executor_with_map):
        intent = TacticIntent(
            unit_id="ghost", tactic_type=TacticType.DETECT_MINES
        )
        assert executor_with_map.execute(intent) is False

    def test_detect_mines_without_game_map_returns_false(self, executor):
        unit = make_unit("u_dm_nm", TileCoord(5, 5))
        executor.register_unit(unit)
        intent = TacticIntent(
            unit_id="u_dm_nm", tactic_type=TacticType.DETECT_MINES
        )
        assert executor.execute(intent) is False


class TestTacticExecutorCallArtillery:
    """Cover _execute_call_artillery (combat_mixin).

    Behavior:
      - Check _artillery_manager.can_call_mission + start_mission.
      - Publish event + return True on success.
      - Unknown unit / no target / can_call_mission False -> False.
    """

    def test_call_artillery_success_publishes_event_and_decrements_missions(
        self, executor, event_bus
    ):
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_art", TileCoord(0, 0))
        executor.register_unit(unit)

        initial_missions = executor._artillery_manager.missions_remaining
        intent = TacticIntent(
            unit_id="u_art",
            tactic_type=TacticType.CALL_ARTILLERY,
            target_position=TileCoord(8, 8),
        )
        assert executor.execute(intent) is True
        assert (
            executor._artillery_manager.missions_remaining
            == initial_missions - 1
        )
        artillery_events = [
            e for e in published if e.get("action") == "call_artillery"
        ]
        assert len(artillery_events) == 1
        assert artillery_events[0]["unit_id"] == "u_art"
        assert artillery_events[0]["target_pos"] == (8, 8)

    def test_call_artillery_unknown_unit_returns_false(self, executor):
        intent = TacticIntent(
            unit_id="ghost",
            tactic_type=TacticType.CALL_ARTILLERY,
            target_position=TileCoord(1, 1),
        )
        assert executor.execute(intent) is False

    def test_call_artillery_without_target_returns_false(self, executor):
        unit = make_unit("u_art_nt", TileCoord(0, 0))
        executor.register_unit(unit)
        intent = TacticIntent(
            unit_id="u_art_nt", tactic_type=TacticType.CALL_ARTILLERY
        )
        assert executor.execute(intent) is False

    def test_call_artillery_second_call_while_active_returns_false(
        self, executor, event_bus
    ):
        """Boundary: same observer cannot call a second mission while the
        first is still active (can_call_mission returns False)."""
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_art_dup", TileCoord(0, 0))
        executor.register_unit(unit)

        intent = TacticIntent(
            unit_id="u_art_dup",
            tactic_type=TacticType.CALL_ARTILLERY,
            target_position=TileCoord(5, 5),
        )
        assert executor.execute(intent) is True  # First call succeeds

        second_intent = TacticIntent(
            unit_id="u_art_dup",
            tactic_type=TacticType.CALL_ARTILLERY,
            target_position=TileCoord(6, 6),
        )
        assert executor.execute(second_intent) is False  # Already active
        # Only the first call published an event
        artillery_events = [
            e for e in published if e.get("action") == "call_artillery"
        ]
        assert len(artillery_events) == 1


class TestTacticExecutorMeleeAttack:
    """Cover _execute_melee_attack (combat_mixin).

    Behavior:
      - Check MeleeCombatSystem.can_melee (alive + can_act + infantry type +
        adjacent + low ammo) + resolve_melee + publish event + return True.
      - Unknown attacker/target / can_melee False -> False.
    Note: resolve_melee uses random.random() — tests assert on handler
    behavior (event published, return True) not on random hit/miss outcomes.
    """

    def test_melee_attack_low_ammo_adjacent_publishes_event(
        self, executor, event_bus
    ):
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))

        # Attacker: low ammo (1/30 = 3.3% < 5% threshold) + adjacent to target
        attacker = make_unit("u_melee_atk", TileCoord(0, 0))
        attacker.weapon.ammo_remaining = 1  # ammo_ratio = 1/30 ≈ 0.033 < 0.05
        target = make_unit("u_melee_tgt", TileCoord(1, 1))  # dist=1 (adjacent)
        target.faction = Faction.AXIS
        executor.register_unit(attacker)
        executor.register_unit(target)

        intent = TacticIntent(
            unit_id="u_melee_atk",
            tactic_type=TacticType.MELEE_ATTACK,
            target_unit_id="u_melee_tgt",
        )
        assert executor.execute(intent) is True
        melee_events = [
            e for e in published if e.get("action") == "melee_attack"
        ]
        assert len(melee_events) == 1
        assert melee_events[0]["attacker_id"] == "u_melee_atk"
        assert melee_events[0]["defender_id"] == "u_melee_tgt"

    def test_melee_attack_unknown_attacker_returns_false(self, executor):
        target = make_unit("u_melee_t2", TileCoord(0, 0))
        executor.register_unit(target)
        intent = TacticIntent(
            unit_id="ghost",
            tactic_type=TacticType.MELEE_ATTACK,
            target_unit_id="u_melee_t2",
        )
        assert executor.execute(intent) is False

    def test_melee_attack_unknown_target_returns_false(self, executor):
        attacker = make_unit("u_melee_a3", TileCoord(0, 0))
        executor.register_unit(attacker)
        intent = TacticIntent(
            unit_id="u_melee_a3",
            tactic_type=TacticType.MELEE_ATTACK,
            target_unit_id="ghost",
        )
        assert executor.execute(intent) is False

    def test_melee_attack_full_ammo_returns_false(self, executor):
        """Boundary: can_melee returns False when attacker has full ammo
        (ammo_ratio >= AMMO_THRESHOLD of 0.05). Default make_unit has
        30/30 = 100% ammo."""
        attacker = make_unit("u_melee_full", TileCoord(0, 0))
        target = make_unit("u_melee_ft", TileCoord(1, 1))
        target.faction = Faction.AXIS
        executor.register_unit(attacker)
        executor.register_unit(target)

        intent = TacticIntent(
            unit_id="u_melee_full",
            tactic_type=TacticType.MELEE_ATTACK,
            target_unit_id="u_melee_ft",
        )
        assert executor.execute(intent) is False


# ---------------------------------------------------------------------------
# Batch 2 — Engineering handlers (DIG_TRENCH / DEMOLISH_BRIDGE / LAY_MINE)
# ---------------------------------------------------------------------------


class TestTacticExecutorDigTrench:
    """Cover _execute_dig_trench (engineering_mixin).

    Behavior:
      - Unknown unit / no game_map -> False.
      - If TrenchDiggingSystem.can_dig False (e.g. already in trench) -> False.
      - First call (no progress) -> start_digging + publish "dig_trench_start"
        + return True.
      - Subsequent call (progress exists) -> tick; on completion publish
        "dig_trench_complete" + return True.
    """

    def test_dig_trench_start_publishes_start_event(
        self, executor_with_map, event_bus
    ):
        """Happy: first call on a diggable infantry publishes dig_trench_start."""
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_dt", TileCoord(5, 5))
        executor_with_map.register_unit(unit)

        intent = TacticIntent(unit_id="u_dt", tactic_type=TacticType.DIG_TRENCH)
        assert executor_with_map.execute(intent) is True

        start_events = [e for e in published if e.get("action") == "dig_trench_start"]
        assert len(start_events) == 1
        assert start_events[0]["unit_id"] == "u_dt"
        assert start_events[0]["position"] == (5, 5)
        # Progress tracker now exists
        assert executor_with_map._trench_digging.get_progress("u_dt") is not None

    def test_dig_trench_completion_publishes_complete_event(
        self, executor_with_map, event_bus
    ):
        """Happy: advancing progress to DIG_DURATION publishes dig_trench_complete.

        We seed progress one tick short of completion to avoid 90 redundant
        execute() calls; the handler's tick branch must still fire.
        """
        from pycc2.domain.ai.trench_digging import DIG_DURATION, DigProgress

        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_dt_c", TileCoord(7, 7))
        executor_with_map.register_unit(unit)

        # Seed progress just before completion
        executor_with_map._trench_digging._progress["u_dt_c"] = DigProgress(
            unit_id="u_dt_c",
            progress=DIG_DURATION - 1,
            position=TileCoord(7, 7),
        )

        intent = TacticIntent(unit_id="u_dt_c", tactic_type=TacticType.DIG_TRENCH)
        assert executor_with_map.execute(intent) is True

        complete_events = [
            e for e in published if e.get("action") == "dig_trench_complete"
        ]
        assert len(complete_events) == 1
        assert complete_events[0]["unit_id"] == "u_dt_c"
        assert complete_events[0]["position"] == (7, 7)
        # Progress cleared after completion
        assert executor_with_map._trench_digging.get_progress("u_dt_c") is None

    def test_dig_trench_unknown_unit_returns_false(self, executor_with_map):
        """Error: unknown unit_id -> False."""
        intent = TacticIntent(unit_id="ghost", tactic_type=TacticType.DIG_TRENCH)
        assert executor_with_map.execute(intent) is False

    def test_dig_trench_without_game_map_returns_false(self, executor, event_bus):
        """Error: no game_map set on executor -> False (no event published)."""
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_dt_nm", TileCoord(5, 5))
        executor.register_unit(unit)

        intent = TacticIntent(unit_id="u_dt_nm", tactic_type=TacticType.DIG_TRENCH)
        assert executor.execute(intent) is False
        assert published == []

    def test_dig_trench_unit_already_in_trench_returns_false(
        self, executor_with_map, event_bus, monkeypatch
    ):
        """Boundary: can_dig returns False -> handler exits early with False.

        We mock can_dig to return False (simulating 'already in trench' or
        any other can_dig failure) to verify the handler's early-exit
        behavior without coupling to can_dig's internal terrain checks.
        Avoids mutating GameMap.tiles_enhanced, which is a class-level
        default and can leak state across tests.
        """
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_dt_it", TileCoord(3, 3))
        executor_with_map.register_unit(unit)

        # Force can_dig to return False (e.g. unit already in trench)
        monkeypatch.setattr(
            executor_with_map._trench_digging, "can_dig", lambda *args: False
        )

        intent = TacticIntent(unit_id="u_dt_it", tactic_type=TacticType.DIG_TRENCH)
        assert executor_with_map.execute(intent) is False
        assert published == []
        # No progress started
        assert executor_with_map._trench_digging.get_progress("u_dt_it") is None

    def test_dig_trench_in_progress_tick_does_not_publish_until_complete(
        self, executor_with_map, event_bus
    ):
        """Boundary: a non-completing tick advances progress without event."""
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_dt_tick", TileCoord(9, 9))
        executor_with_map.register_unit(unit)

        # First call starts digging
        intent = TacticIntent(unit_id="u_dt_tick", tactic_type=TacticType.DIG_TRENCH)
        assert executor_with_map.execute(intent) is True
        start_count = sum(
            1 for e in published if e.get("action") == "dig_trench_start"
        )
        assert start_count == 1

        # Second call advances progress but does not complete
        assert executor_with_map.execute(intent) is True
        complete_events = [
            e for e in published if e.get("action") == "dig_trench_complete"
        ]
        assert complete_events == []
        progress = executor_with_map._trench_digging.get_progress("u_dt_tick")
        assert progress is not None and progress.progress >= 1


class TestTacticExecutorDemolishBridge:
    """Cover _execute_demolish_bridge (engineering_mixin).

    Behavior:
      - Unknown unit / no game_map -> False.
      - Scan 3x3 around unit for BRIDGE terrain; if none -> False.
      - Found -> set each to BRIDGE_DESTROYED + publish "demolish_bridge"
        with bridge_tiles list + return True.
    """

    def test_demolish_bridge_destroys_adjacent_bridge_tile(
        self, executor_with_map, event_bus
    ):
        """Happy: one BRIDGE tile adjacent to unit is destroyed."""
        from pycc2.domain.value_objects.terrain_type import TerrainType

        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_db", TileCoord(5, 5))
        executor_with_map.register_unit(unit)

        # Plant a BRIDGE tile at (6, 5) — adjacent to unit
        executor_with_map.game_map.set_terrain(
            TileCoord(6, 5), TerrainType.BRIDGE
        )

        intent = TacticIntent(
            unit_id="u_db", tactic_type=TacticType.DEMOLISH_BRIDGE
        )
        assert executor_with_map.execute(intent) is True

        demolish_events = [
            e for e in published if e.get("action") == "demolish_bridge"
        ]
        assert len(demolish_events) == 1
        assert demolish_events[0]["unit_id"] == "u_db"
        assert (6, 5) in demolish_events[0]["bridge_tiles"]
        # Terrain actually mutated
        assert (
            executor_with_map.game_map.get_terrain(TileCoord(6, 5))
            == TerrainType.BRIDGE_DESTROYED
        )

    def test_demolish_bridge_finds_multiple_bridges_in_3x3(
        self, executor_with_map, event_bus
    ):
        """Happy: multiple BRIDGE tiles in 3x3 neighborhood all destroyed."""
        from pycc2.domain.value_objects.terrain_type import TerrainType

        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_db_multi", TileCoord(10, 10))
        executor_with_map.register_unit(unit)

        # Plant BRIDGE at three offsets within 3x3 (excluding unit's own tile)
        bridge_coords = [TileCoord(9, 9), TileCoord(11, 10), TileCoord(10, 11)]
        for c in bridge_coords:
            executor_with_map.game_map.set_terrain(c, TerrainType.BRIDGE)

        intent = TacticIntent(
            unit_id="u_db_multi", tactic_type=TacticType.DEMOLISH_BRIDGE
        )
        assert executor_with_map.execute(intent) is True

        demolish_events = [
            e for e in published if e.get("action") == "demolish_bridge"
        ]
        assert len(demolish_events) == 1
        reported = set(demolish_events[0]["bridge_tiles"])
        for c in bridge_coords:
            assert (c.x, c.y) in reported
            assert (
                executor_with_map.game_map.get_terrain(c)
                == TerrainType.BRIDGE_DESTROYED
            )

    def test_demolish_bridge_unknown_unit_returns_false(self, executor_with_map):
        """Error: unknown unit_id -> False."""
        intent = TacticIntent(
            unit_id="ghost", tactic_type=TacticType.DEMOLISH_BRIDGE
        )
        assert executor_with_map.execute(intent) is False

    def test_demolish_bridge_without_game_map_returns_false(
        self, executor, event_bus
    ):
        """Error: no game_map -> False (no event published)."""
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_db_nm", TileCoord(5, 5))
        executor.register_unit(unit)

        intent = TacticIntent(
            unit_id="u_db_nm", tactic_type=TacticType.DEMOLISH_BRIDGE
        )
        assert executor.execute(intent) is False
        assert published == []

    def test_demolish_bridge_no_bridge_nearby_returns_false(
        self, executor_with_map, event_bus
    ):
        """Boundary: no BRIDGE tile in 3x3 -> False, no event published."""
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_db_none", TileCoord(5, 5))
        executor_with_map.register_unit(unit)
        # game_map is all OPEN — no BRIDGE anywhere

        intent = TacticIntent(
            unit_id="u_db_none", tactic_type=TacticType.DEMOLISH_BRIDGE
        )
        assert executor_with_map.execute(intent) is False
        assert published == []

    def test_demolish_bridge_at_map_corner_scans_in_bounds(
        self, executor_with_map, event_bus
    ):
        """Boundary: unit at (0, 0) corner — 3x3 scan stays within 20x20 map."""
        from pycc2.domain.value_objects.terrain_type import TerrainType

        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_db_corner", TileCoord(0, 0))
        executor_with_map.register_unit(unit)

        # Plant BRIDGE at (1, 1) — within 3x3 of corner unit
        executor_with_map.game_map.set_terrain(
            TileCoord(1, 1), TerrainType.BRIDGE
        )

        intent = TacticIntent(
            unit_id="u_db_corner", tactic_type=TacticType.DEMOLISH_BRIDGE
        )
        assert executor_with_map.execute(intent) is True
        assert (
            executor_with_map.game_map.get_terrain(TileCoord(1, 1))
            == TerrainType.BRIDGE_DESTROYED
        )


class TestTacticExecutorLayMine:
    """Cover _execute_lay_mine (engineering_mixin).

    Behavior:
      - Unknown unit / no game_map / no target_position -> False.
      - If target_position > 1 tile away -> delegate to _execute_move_to.
      - First call (no progress) -> start_laying + publish "lay_mine_start"
        + return True.
      - Subsequent call (progress exists) -> tick_laying; on completion
        publish "mine_laid" + return True.

    Note: can_lay_mine requires unit_type == AT_GUN_TEAM (engineer proxy),
    so happy-path tests use AT_GUN_TEAM units.
    """

    def test_lay_mine_start_publishes_start_event(
        self, executor_with_map, event_bus
    ):
        """Happy: AT_GUN_TEAM at target starts laying + publishes lay_mine_start."""
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit(
            "u_lm",
            TileCoord(5, 5),
            unit_type=UnitType.AT_GUN_TEAM,
            primary_weapon_id="at_gun",
            max_ammo=8,
            vision_range=6,
        )
        executor_with_map.register_unit(unit)

        intent = TacticIntent(
            unit_id="u_lm",
            tactic_type=TacticType.LAY_MINE,
            target_position=TileCoord(5, 5),  # Same tile -> dist=0
        )
        assert executor_with_map.execute(intent) is True

        start_events = [e for e in published if e.get("action") == "lay_mine_start"]
        assert len(start_events) == 1
        assert start_events[0]["unit_id"] == "u_lm"
        assert start_events[0]["mine_type"] == "AT_MINE"
        assert start_events[0]["position"] == (5, 5)
        assert executor_with_map._mine_warfare_system.get_lay_progress("u_lm") is not None

    def test_lay_mine_completion_publishes_mine_laid_event(
        self, executor_with_map, event_bus
    ):
        """Happy: advancing laying to MINE_LAY_TICKS publishes mine_laid."""
        from pycc2.domain.ai.mine_warfare import (
            MINE_LAY_TICKS,
            LayProgress,
            MineType,
        )

        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit(
            "u_lm_c",
            TileCoord(8, 8),
            unit_type=UnitType.AT_GUN_TEAM,
            primary_weapon_id="at_gun",
            max_ammo=8,
            vision_range=6,
        )
        executor_with_map.register_unit(unit)

        # Seed laying progress one tick short of completion
        executor_with_map._mine_warfare_system._lay_progress["u_lm_c"] = LayProgress(
            unit_id="u_lm_c",
            mine_type=MineType.AT_MINE,
            progress=MINE_LAY_TICKS - 1,
        )

        intent = TacticIntent(
            unit_id="u_lm_c",
            tactic_type=TacticType.LAY_MINE,
            target_position=TileCoord(8, 8),
        )
        assert executor_with_map.execute(intent) is True

        laid_events = [e for e in published if e.get("action") == "mine_laid"]
        assert len(laid_events) == 1
        assert laid_events[0]["unit_id"] == "u_lm_c"
        assert laid_events[0]["position"] == (8, 8)
        # A mine was actually added to the system
        assert len(executor_with_map._mine_warfare_system._mines) >= 1

    def test_lay_mine_unknown_unit_returns_false(self, executor_with_map):
        """Error: unknown unit_id -> False."""
        intent = TacticIntent(
            unit_id="ghost",
            tactic_type=TacticType.LAY_MINE,
            target_position=TileCoord(5, 5),
        )
        assert executor_with_map.execute(intent) is False

    def test_lay_mine_without_game_map_returns_false(self, executor, event_bus):
        """Error: no game_map -> False (no event published)."""
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit(
            "u_lm_nm",
            TileCoord(5, 5),
            unit_type=UnitType.AT_GUN_TEAM,
            primary_weapon_id="at_gun",
            max_ammo=8,
            vision_range=6,
        )
        executor.register_unit(unit)

        intent = TacticIntent(
            unit_id="u_lm_nm",
            tactic_type=TacticType.LAY_MINE,
            target_position=TileCoord(5, 5),
        )
        assert executor.execute(intent) is False
        assert published == []

    def test_lay_mine_without_target_position_returns_false(
        self, executor_with_map, event_bus
    ):
        """Error: target_position is None -> False (no event published)."""
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit(
            "u_lm_nt",
            TileCoord(5, 5),
            unit_type=UnitType.AT_GUN_TEAM,
            primary_weapon_id="at_gun",
            max_ammo=8,
            vision_range=6,
        )
        executor_with_map.register_unit(unit)

        intent = TacticIntent(unit_id="u_lm_nt", tactic_type=TacticType.LAY_MINE)
        assert executor_with_map.execute(intent) is False
        assert published == []

    def test_lay_mine_target_far_delegates_to_move_to(
        self, executor_with_map, event_bus
    ):
        """Boundary: target_position > 1 tile away -> _execute_move_to handles.

        _execute_move_to publishes a move event; lay_mine_start should NOT
        be published in this branch.
        """
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit(
            "u_lm_far",
            TileCoord(0, 0),
            unit_type=UnitType.AT_GUN_TEAM,
            primary_weapon_id="at_gun",
            max_ammo=8,
            vision_range=6,
        )
        executor_with_map.register_unit(unit)

        # Target 5 tiles away -> dist > 1 -> delegates to move_to
        intent = TacticIntent(
            unit_id="u_lm_far",
            tactic_type=TacticType.LAY_MINE,
            target_position=TileCoord(5, 5),
        )
        result = executor_with_map.execute(intent)
        # _execute_move_to returns True when it publishes a move event
        assert result is True
        # lay_mine_start must NOT be published in the move-delegation branch
        start_events = [e for e in published if e.get("action") == "lay_mine_start"]
        assert start_events == []

    def test_lay_mine_in_progress_tick_does_not_publish_until_complete(
        self, executor_with_map, event_bus
    ):
        """Boundary: a non-completing tick advances progress without mine_laid."""
        from pycc2.domain.ai.mine_warfare import LayProgress, MineType

        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit(
            "u_lm_tick",
            TileCoord(6, 6),
            unit_type=UnitType.AT_GUN_TEAM,
            primary_weapon_id="at_gun",
            max_ammo=8,
            vision_range=6,
        )
        executor_with_map.register_unit(unit)

        # Seed laying progress at 0 (just started, far from completion)
        executor_with_map._mine_warfare_system._lay_progress["u_lm_tick"] = LayProgress(
            unit_id="u_lm_tick",
            mine_type=MineType.AT_MINE,
            progress=0,
        )

        intent = TacticIntent(
            unit_id="u_lm_tick",
            tactic_type=TacticType.LAY_MINE,
            target_position=TileCoord(6, 6),
        )
        assert executor_with_map.execute(intent) is True

        laid_events = [e for e in published if e.get("action") == "mine_laid"]
        assert laid_events == []
        progress = executor_with_map._mine_warfare_system.get_lay_progress("u_lm_tick")
        assert progress is not None and progress.progress >= 1


# =============================================================================
# Batch 4a — Vehicle & logistics handlers (4 handlers, 25 tests)
# =============================================================================


class TestTacticExecutorMountTank:
    """Tests for _execute_mount_tank (vehicle_mixin).

    Covers: Happy (start_mount + event / already-riding idempotent) +
    Error (unknown rider / unknown tank) + Boundary (dist>2 delegates
    move_to / can_mount False returns False).
    """

    def test_mount_tank_start_publishes_event(self, executor, event_bus):
        """Happy: can_mount True + start_mount True → event published, True."""
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        rider = make_unit("u_mt_rider", TileCoord(3, 3))
        tank = make_unit("u_mt_tank", TileCoord(3, 4), unit_type=UnitType.TANK)
        executor.register_unit(rider)
        executor.register_unit(tank)

        intent = TacticIntent(
            unit_id="u_mt_rider",
            tactic_type=TacticType.MOUNT_TANK,
            target_unit_id="u_mt_tank",
        )
        assert executor.execute(intent) is True
        mount_events = [e for e in published if e.get("action") == "mount_tank"]
        assert len(mount_events) == 1
        assert mount_events[0]["unit_id"] == "u_mt_rider"
        assert mount_events[0]["tank_id"] == "u_mt_tank"

    def test_mount_tank_already_riding_returns_true(
        self, executor, event_bus, monkeypatch
    ):
        """Happy/Boundary: is_riding=True → idempotent True, no mount event."""
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        rider = make_unit("u_mt_ar", TileCoord(3, 3))
        tank = make_unit("u_mt_tank_ar", TileCoord(3, 4), unit_type=UnitType.TANK)
        executor.register_unit(rider)
        executor.register_unit(tank)

        monkeypatch.setattr(
            executor._tank_rider_system, "is_riding", lambda uid: True
        )

        intent = TacticIntent(
            unit_id="u_mt_ar",
            tactic_type=TacticType.MOUNT_TANK,
            target_unit_id="u_mt_tank_ar",
        )
        assert executor.execute(intent) is True
        mount_events = [e for e in published if e.get("action") == "mount_tank"]
        assert mount_events == []

    def test_mount_tank_unknown_unit_returns_false(self, executor):
        """Error: unknown rider unit_id → False."""
        intent = TacticIntent(
            unit_id="nonexistent",
            tactic_type=TacticType.MOUNT_TANK,
            target_unit_id="some_tank",
        )
        assert executor.execute(intent) is False

    def test_mount_tank_unknown_tank_returns_false(self, executor):
        """Error: rider exists but target_unit_id invalid → False."""
        rider = make_unit("u_mt_notank", TileCoord(3, 3))
        executor.register_unit(rider)
        intent = TacticIntent(
            unit_id="u_mt_notank",
            tactic_type=TacticType.MOUNT_TANK,
            target_unit_id="nonexistent_tank",
        )
        assert executor.execute(intent) is False

    def test_mount_tank_dist_gt_2_delegates_to_move_to(self, executor, event_bus):
        """Boundary: dist>2 → can_mount False → delegate to move_to."""
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        rider = make_unit("u_mt_far", TileCoord(3, 3))
        tank = make_unit("u_mt_tank_far", TileCoord(6, 6), unit_type=UnitType.TANK)
        executor.register_unit(rider)
        executor.register_unit(tank)

        intent = TacticIntent(
            unit_id="u_mt_far",
            tactic_type=TacticType.MOUNT_TANK,
            target_unit_id="u_mt_tank_far",
        )
        # dist = 3 > MOUNT_RANGE(2) → delegates to move_to
        result = executor.execute(intent)
        assert result is True
        mount_events = [e for e in published if e.get("action") == "mount_tank"]
        assert mount_events == []

    def test_mount_tank_cannot_mount_returns_false(
        self, executor, event_bus, monkeypatch
    ):
        """Boundary: can_mount False + dist<=2 (no move delegation) → False."""
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        rider = make_unit("u_mt_cant", TileCoord(3, 3))
        tank = make_unit("u_mt_tank_cant", TileCoord(3, 4), unit_type=UnitType.TANK)
        executor.register_unit(rider)
        executor.register_unit(tank)

        monkeypatch.setattr(
            executor._tank_rider_system, "can_mount", lambda *args: False
        )

        intent = TacticIntent(
            unit_id="u_mt_cant",
            tactic_type=TacticType.MOUNT_TANK,
            target_unit_id="u_mt_tank_cant",
        )
        # dist = 1 <= 2, can_mount False → no move delegation, return False
        assert executor.execute(intent) is False
        mount_events = [e for e in published if e.get("action") == "mount_tank"]
        assert mount_events == []


class TestTacticExecutorDismountTank:
    """Tests for _execute_dismount_tank (vehicle_mixin).

    Covers: Happy (dismount + event) + Error (unknown unit) + Boundary
    (not-riding idempotent / target_position sets instant flag).
    """

    @staticmethod
    def _advance_to_riding(executor: TacticExecutor, rider: Unit, tank: Unit) -> None:
        """Advance mount progress to RIDING state via real TankRiderSystem.tick."""
        from pycc2.domain.ai.tank_riders import MOUNT_TICKS

        executor._tank_rider_system.start_mount(rider, tank)
        for _ in range(MOUNT_TICKS):
            executor._tank_rider_system.tick([rider, tank])

    def test_dismount_tank_publishes_event(self, executor, event_bus):
        """Happy: is_riding=True + start_dismount True → event published, True."""
        rider = make_unit("u_dt_rider", TileCoord(3, 3))
        tank = make_unit("u_dt_tank", TileCoord(3, 4), unit_type=UnitType.TANK)
        executor.register_unit(rider)
        executor.register_unit(tank)
        self._advance_to_riding(executor, rider, tank)
        assert executor._tank_rider_system.is_riding(rider.id) is True

        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        intent = TacticIntent(
            unit_id="u_dt_rider",
            tactic_type=TacticType.DISMOUNT_TANK,
        )
        assert executor.execute(intent) is True
        dismount_events = [e for e in published if e.get("action") == "dismount_tank"]
        assert len(dismount_events) == 1
        assert dismount_events[0]["unit_id"] == "u_dt_rider"
        assert dismount_events[0]["tank_id"] == "u_dt_tank"

    def test_dismount_tank_not_riding_returns_true(self, executor, event_bus):
        """Boundary: is_riding=False → idempotent True, no dismount event."""
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        rider = make_unit("u_dt_notriding", TileCoord(3, 3))
        executor.register_unit(rider)

        intent = TacticIntent(
            unit_id="u_dt_notriding",
            tactic_type=TacticType.DISMOUNT_TANK,
        )
        assert executor.execute(intent) is True
        dismount_events = [e for e in published if e.get("action") == "dismount_tank"]
        assert dismount_events == []

    def test_dismount_tank_unknown_unit_returns_false(self, executor):
        """Error: unknown rider unit_id → False."""
        intent = TacticIntent(
            unit_id="nonexistent",
            tactic_type=TacticType.DISMOUNT_TANK,
        )
        assert executor.execute(intent) is False

    def test_dismount_tank_with_target_position_is_instant(self, executor, event_bus):
        """Boundary: target_position set → instant=True (under-fire dismount)."""
        rider = make_unit("u_dt_instant", TileCoord(3, 3))
        tank = make_unit("u_dt_tank_instant", TileCoord(3, 4), unit_type=UnitType.TANK)
        executor.register_unit(rider)
        executor.register_unit(tank)
        self._advance_to_riding(executor, rider, tank)

        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        intent = TacticIntent(
            unit_id="u_dt_instant",
            tactic_type=TacticType.DISMOUNT_TANK,
            target_position=TileCoord(4, 4),
        )
        assert executor.execute(intent) is True
        dismount_events = [e for e in published if e.get("action") == "dismount_tank"]
        assert len(dismount_events) == 1
        assert dismount_events[0]["instant"] is True

    def test_dismount_tank_without_target_position_not_instant(
        self, executor, event_bus
    ):
        """Boundary: no target_position → instant=False (normal dismount)."""
        rider = make_unit("u_dt_slow", TileCoord(3, 3))
        tank = make_unit("u_dt_tank_slow", TileCoord(3, 4), unit_type=UnitType.TANK)
        executor.register_unit(rider)
        executor.register_unit(tank)
        self._advance_to_riding(executor, rider, tank)

        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        intent = TacticIntent(
            unit_id="u_dt_slow",
            tactic_type=TacticType.DISMOUNT_TANK,
        )
        assert executor.execute(intent) is True
        dismount_events = [e for e in published if e.get("action") == "dismount_tank"]
        assert len(dismount_events) == 1
        assert dismount_events[0]["instant"] is False


class TestTacticExecutorHealWounded:
    """Tests for _execute_heal_wounded (logistics_mixin).

    Covers: Happy (heal + event) + Error (unknown medic / non-medic /
    unknown patient / dead patient) + Boundary (hp_ratio>=cap / dist>adjacent
    delegates move_to).
    """

    def test_heal_wounded_heals_patient_and_publishes_event(
        self, executor, event_bus
    ):
        """Happy: MEDIC_TEAM + wounded patient adjacent → heal + event, True."""
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        medic = make_unit("u_hw_medic", TileCoord(3, 3), unit_type=UnitType.MEDIC_TEAM)
        patient = make_unit("u_hw_patient", TileCoord(3, 4), hp=50)
        patient.health = HealthComponent(hp=20, max_hp=50)  # hp_ratio=0.4 < 0.7
        executor.register_unit(medic)
        executor.register_unit(patient)

        initial_hp = patient.health.hp
        intent = TacticIntent(
            unit_id="u_hw_medic",
            tactic_type=TacticType.HEAL_WOUNDED,
            target_unit_id="u_hw_patient",
        )
        assert executor.execute(intent) is True
        heal_events = [e for e in published if e.get("action") == "heal"]
        assert len(heal_events) == 1
        assert heal_events[0]["medic_id"] == "u_hw_medic"
        assert heal_events[0]["patient_id"] == "u_hw_patient"
        assert patient.health.hp > initial_hp

    def test_heal_wounded_unknown_medic_returns_false(self, executor):
        """Error: unknown medic unit_id → False."""
        intent = TacticIntent(
            unit_id="nonexistent",
            tactic_type=TacticType.HEAL_WOUNDED,
            target_unit_id="some_patient",
        )
        assert executor.execute(intent) is False

    def test_heal_wounded_non_medic_unit_returns_false(self, executor):
        """Error: unit_type != MEDIC_TEAM → False."""
        unit = make_unit("u_hw_notmedic", TileCoord(3, 3))  # INFANTRY_SQUAD
        patient = make_unit("u_hw_p2", TileCoord(3, 4))
        executor.register_unit(unit)
        executor.register_unit(patient)
        intent = TacticIntent(
            unit_id="u_hw_notmedic",
            tactic_type=TacticType.HEAL_WOUNDED,
            target_unit_id="u_hw_p2",
        )
        assert executor.execute(intent) is False

    def test_heal_wounded_unknown_patient_returns_false(self, executor):
        """Error: medic exists but target_unit_id invalid → False."""
        medic = make_unit("u_hw_medic2", TileCoord(3, 3), unit_type=UnitType.MEDIC_TEAM)
        executor.register_unit(medic)
        intent = TacticIntent(
            unit_id="u_hw_medic2",
            tactic_type=TacticType.HEAL_WOUNDED,
            target_unit_id="nonexistent_patient",
        )
        assert executor.execute(intent) is False

    def test_heal_wounded_dead_patient_returns_false(self, executor, event_bus):
        """Error: patient.is_alive=False → False."""
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        medic = make_unit("u_hw_medic3", TileCoord(3, 3), unit_type=UnitType.MEDIC_TEAM)
        patient = make_unit("u_hw_dead", TileCoord(3, 4), hp=50)
        patient.take_damage(50)  # hp: 50→0, triggers die() → is_alive=False
        executor.register_unit(medic)
        executor.register_unit(patient)

        intent = TacticIntent(
            unit_id="u_hw_medic3",
            tactic_type=TacticType.HEAL_WOUNDED,
            target_unit_id="u_hw_dead",
        )
        assert executor.execute(intent) is False
        heal_events = [e for e in published if e.get("action") == "heal"]
        assert heal_events == []

    def test_heal_wounded_patient_at_heal_cap_returns_true(self, executor, event_bus):
        """Boundary: patient hp_ratio >= HEAL_CAP_RATIO → True, no heal event."""
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        medic = make_unit("u_hw_medic4", TileCoord(3, 3), unit_type=UnitType.MEDIC_TEAM)
        patient = make_unit("u_hw_capped", TileCoord(3, 4), hp=50)
        # hp_ratio = 50/50 = 1.0 >= HEAL_CAP_RATIO(0.7) → no treatment needed
        executor.register_unit(medic)
        executor.register_unit(patient)

        intent = TacticIntent(
            unit_id="u_hw_medic4",
            tactic_type=TacticType.HEAL_WOUNDED,
            target_unit_id="u_hw_capped",
        )
        assert executor.execute(intent) is True
        heal_events = [e for e in published if e.get("action") == "heal"]
        assert heal_events == []

    def test_heal_wounded_dist_gt_adjacent_delegates_to_move_to(
        self, executor, event_bus
    ):
        """Boundary: dist > HEAL_ADJACENT_RANGE(1) → delegate to move_to."""
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        medic = make_unit("u_hw_medic5", TileCoord(3, 3), unit_type=UnitType.MEDIC_TEAM)
        patient = make_unit("u_hw_far_patient", TileCoord(6, 6), hp=50)
        patient.health = HealthComponent(hp=20, max_hp=50)  # wounded
        executor.register_unit(medic)
        executor.register_unit(patient)

        intent = TacticIntent(
            unit_id="u_hw_medic5",
            tactic_type=TacticType.HEAL_WOUNDED,
            target_unit_id="u_hw_far_patient",
        )
        # dist = 3 > 1 → delegates to move_to
        result = executor.execute(intent)
        assert result is True
        heal_events = [e for e in published if e.get("action") == "heal"]
        assert heal_events == []


class TestTacticExecutorRallyNco:
    """Tests for _execute_rally_nco (logistics_mixin).

    Covers: Happy (rally + event) + Error (unknown NCO / no nco_rally
    configured / unknown target) + Boundary (dist>5 with/without
    target_position / can_rally False).
    """

    def test_rally_nco_success_publishes_event(self, executor, event_bus):
        """Happy: COMMANDER + can_rally True + dist<=5 + target BROKEN → event."""
        from pycc2.domain.ai.squad_degradation import (
            RALLY_RESTORE_MORALE,
            NCORallyBehavior,
        )

        executor.nco_rally = NCORallyBehavior()
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        nco = make_unit("u_rn_nco", TileCoord(3, 3), unit_type=UnitType.COMMANDER)
        # morale_value=5 → state=BROKEN (< 20 threshold)
        target = make_unit("u_rn_target", TileCoord(3, 4), morale_value=5)
        executor.register_unit(nco)
        executor.register_unit(target)

        intent = TacticIntent(
            unit_id="u_rn_nco",
            tactic_type=TacticType.RALLY_NCO,
            target_unit_id="u_rn_target",
        )
        assert executor.execute(intent) is True
        rally_events = [e for e in published if "rallied_unit_id" in e]
        assert len(rally_events) == 1
        assert rally_events[0]["nco_id"] == "u_rn_nco"
        assert rally_events[0]["rallied_unit_id"] == "u_rn_target"
        assert target.morale.value == RALLY_RESTORE_MORALE

    def test_rally_nco_unknown_nco_returns_false(self, executor):
        """Error: unknown NCO unit_id → False."""
        from pycc2.domain.ai.squad_degradation import NCORallyBehavior

        executor.nco_rally = NCORallyBehavior()
        intent = TacticIntent(
            unit_id="nonexistent",
            tactic_type=TacticType.RALLY_NCO,
            target_unit_id="some_target",
        )
        assert executor.execute(intent) is False

    def test_rally_nco_no_nco_rally_configured_returns_false(self, executor):
        """Error: nco_rally is None (default) → False."""
        # executor.nco_rally is None by default
        nco = make_unit("u_rn_nco2", TileCoord(3, 3), unit_type=UnitType.COMMANDER)
        target = make_unit("u_rn_target2", TileCoord(3, 4), morale_value=5)
        executor.register_unit(nco)
        executor.register_unit(target)
        intent = TacticIntent(
            unit_id="u_rn_nco2",
            tactic_type=TacticType.RALLY_NCO,
            target_unit_id="u_rn_target2",
        )
        assert executor.execute(intent) is False

    def test_rally_nco_unknown_target_returns_false(self, executor):
        """Error: NCO exists but target_unit_id invalid → False."""
        from pycc2.domain.ai.squad_degradation import NCORallyBehavior

        executor.nco_rally = NCORallyBehavior()
        nco = make_unit("u_rn_nco3", TileCoord(3, 3), unit_type=UnitType.COMMANDER)
        executor.register_unit(nco)
        intent = TacticIntent(
            unit_id="u_rn_nco3",
            tactic_type=TacticType.RALLY_NCO,
            target_unit_id="nonexistent_target",
        )
        assert executor.execute(intent) is False

    def test_rally_nco_dist_gt_5_with_target_position_delegates_move_to(
        self, executor, event_bus
    ):
        """Boundary: dist>5 + target_position set → delegate move_to, return False."""
        from pycc2.domain.ai.squad_degradation import NCORallyBehavior

        executor.nco_rally = NCORallyBehavior()
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        nco = make_unit("u_rn_nco_far", TileCoord(3, 3), unit_type=UnitType.COMMANDER)
        target = make_unit("u_rn_target_far", TileCoord(10, 10), morale_value=5)
        executor.register_unit(nco)
        executor.register_unit(target)

        intent = TacticIntent(
            unit_id="u_rn_nco_far",
            tactic_type=TacticType.RALLY_NCO,
            target_unit_id="u_rn_target_far",
            target_position=TileCoord(9, 9),
        )
        # dist = 7 > 5 → delegates move_to (priority+8), returns False
        result = executor.execute(intent)
        assert result is False
        rally_events = [e for e in published if "rallied_unit_id" in e]
        assert rally_events == []

    def test_rally_nco_dist_gt_5_without_target_position_returns_false(
        self, executor, event_bus
    ):
        """Boundary: dist>5 + no target_position → False (no move delegation)."""
        from pycc2.domain.ai.squad_degradation import NCORallyBehavior

        executor.nco_rally = NCORallyBehavior()
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        nco = make_unit("u_rn_nco_far2", TileCoord(3, 3), unit_type=UnitType.COMMANDER)
        target = make_unit("u_rn_target_far2", TileCoord(10, 10), morale_value=5)
        executor.register_unit(nco)
        executor.register_unit(target)

        intent = TacticIntent(
            unit_id="u_rn_nco_far2",
            tactic_type=TacticType.RALLY_NCO,
            target_unit_id="u_rn_target_far2",
        )
        # dist = 7 > 5, no target_position → return False
        result = executor.execute(intent)
        assert result is False
        rally_events = [e for e in published if "rallied_unit_id" in e]
        assert rally_events == []

    def test_rally_nco_cannot_rally_returns_false(self, executor, event_bus):
        """Boundary: can_rally False (morale < threshold) → False."""
        from pycc2.domain.ai.squad_degradation import NCORallyBehavior

        executor.nco_rally = NCORallyBehavior()
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        # NCO morale_value=30 < RALLY_MORALE_THRESHOLD(50) → can_rally False
        nco = make_unit(
            "u_rn_lowmorale",
            TileCoord(3, 3),
            unit_type=UnitType.COMMANDER,
            morale_value=30,
        )
        target = make_unit("u_rn_target3", TileCoord(3, 4), morale_value=5)
        executor.register_unit(nco)
        executor.register_unit(target)

        intent = TacticIntent(
            unit_id="u_rn_lowmorale",
            tactic_type=TacticType.RALLY_NCO,
            target_unit_id="u_rn_target3",
        )
        assert executor.execute(intent) is False
        rally_events = [e for e in published if "rallied_unit_id" in e]
        assert rally_events == []


# ============================================================================
# Phase: v0.4.3 — TacticExecutor untested handler coverage (batch 4b)
# Target: 3 highest-complexity handlers (SCAVENGE_AMMO / CLEAR_BUILDING /
#         ASSAULT_FORTIFIED) — multi-step state machines and complex
#         preconditions. Completes TD-064 handler coverage (19/19 + DEMOLISH_BRIDGE).
# DevSquad Testing Iron Rules followed:
#   - Rule 1 (Documentation First): signatures verified from
#     logistics_mixin.py / combat_mixin.py / building_clearing.py /
#     ammo_pickup.py / engineer_assault.py before writing.
#   - Rule 2 (Failure Means Report): assertions express expected behavior,
#     not loosened to pass.
#   - Rule 3 (Dimension Completeness): each handler covers Happy + Error +
#     Boundary.
# ============================================================================


class TestTacticExecutorScavengeAmmo:
    """Tests for _execute_scavenge_ammo (logistics_mixin).

    Covers: Happy (start_pickup SUCCESS + event / already picking up idempotent
    / target_unit_id source match) + Error (unknown unit / no target_position
    / no source) + Boundary (dist>1 delegate move_to / WRONG_STANCE).
    """

    def test_scavenge_ammo_unknown_unit_returns_false(self, executor):
        """Error: unknown unit_id → False."""
        intent = TacticIntent(
            unit_id="nonexistent",
            tactic_type=TacticType.SCAVENGE_AMMO,
            target_position=TileCoord(3, 3),
        )
        assert executor.execute(intent) is False

    def test_scavenge_ammo_no_target_position_returns_false(self, executor):
        """Error: target_position is None → False (warning logged)."""
        unit = make_unit("u_sa_notp", TileCoord(3, 3))
        executor.register_unit(unit)
        intent = TacticIntent(
            unit_id="u_sa_notp",
            tactic_type=TacticType.SCAVENGE_AMMO,
        )
        assert executor.execute(intent) is False

    def test_scavenge_ammo_dist_gt_1_delegates_to_move_to(
        self, executor, event_bus
    ):
        """Boundary: dist > 1 → delegate to _execute_move_to, no scavenge event."""
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_sa_far", TileCoord(0, 0))
        executor.register_unit(unit)
        intent = TacticIntent(
            unit_id="u_sa_far",
            tactic_type=TacticType.SCAVENGE_AMMO,
            target_position=TileCoord(5, 5),
        )
        # dist = 5 > 1 → delegates to move_to
        result = executor.execute(intent)
        assert result is True
        scavenge_events = [e for e in published if "source_id" in e]
        assert scavenge_events == []

    def test_scavenge_ammo_no_source_returns_false(self, executor, event_bus):
        """Error: fallen_cache empty (no sources) → False."""
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_sa_nosrc", TileCoord(3, 3))
        executor.register_unit(unit)
        # Unit at target position, but no fallen units registered in cache
        intent = TacticIntent(
            unit_id="u_sa_nosrc",
            tactic_type=TacticType.SCAVENGE_AMMO,
            target_position=TileCoord(3, 3),
        )
        assert executor.execute(intent) is False
        scavenge_events = [e for e in published if "source_id" in e]
        assert scavenge_events == []

    def test_scavenge_ammo_start_pickup_success_publishes_event(
        self, executor, event_bus, monkeypatch
    ):
        """Happy: fallen comrade registered + stance PRONE → SUCCESS + event."""
        from pycc2.domain.ai.ammo_pickup import AmmoPickupSystem
        from pycc2.domain.systems.combat_mechanics_enhanced import Stance

        # AmmoPickupSystem._get_unit_stance is a staticmethod; replace with
        # PRONE so start_pickup does not reject STANDING default stance.
        monkeypatch.setattr(
            AmmoPickupSystem,
            "_get_unit_stance",
            staticmethod(lambda u: Stance.PRONE),
        )

        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_sa_ok", TileCoord(3, 3))
        executor.register_unit(unit)

        # Register a fallen comrade at the same position (friendly)
        fallen = make_unit("u_fallen", TileCoord(3, 3))
        fallen.faction = Faction.ALLIES  # same faction → FALLEN_COMRADE
        executor._ammo_pickup.fallen_cache.register(fallen, current_tick=0)

        intent = TacticIntent(
            unit_id="u_sa_ok",
            tactic_type=TacticType.SCAVENGE_AMMO,
            target_position=TileCoord(3, 3),
        )
        assert executor.execute(intent) is True
        scavenge_events = [e for e in published if "source_id" in e]
        assert len(scavenge_events) == 1
        assert scavenge_events[0]["unit_id"] == "u_sa_ok"
        assert scavenge_events[0]["source_id"] == "u_fallen"
        assert scavenge_events[0]["source_type"] == "FALLEN_COMRADE"

    def test_scavenge_ammo_already_picking_up_returns_true(self, executor):
        """Happy idempotent: _active_pickups has unit → True without re-starting."""
        from pycc2.domain.ai.ammo_pickup import AmmoSourceType, PickupState

        unit = make_unit("u_sa_inprogress", TileCoord(3, 3))
        executor.register_unit(unit)
        # Pre-populate active pickup state for this unit
        executor._ammo_pickup._active_pickups[unit.id] = PickupState(
            unit_id=unit.id,
            source_id="u_fallen2",
            source_type=AmmoSourceType.FALLEN_COMRADE,
            ticks_remaining=2,
            target_position=TileCoord(3, 3),
        )

        intent = TacticIntent(
            unit_id="u_sa_inprogress",
            tactic_type=TacticType.SCAVENGE_AMMO,
            target_position=TileCoord(3, 3),
        )
        assert executor.execute(intent) is True

    def test_scavenge_ammo_wrong_stance_returns_false(self, executor, event_bus):
        """Boundary: stance STANDING (default) → WRONG_STANCE → False."""
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_sa_standing", TileCoord(3, 3))
        executor.register_unit(unit)

        # Register a fallen comrade at the same position
        fallen = make_unit("u_fallen3", TileCoord(3, 3))
        fallen.faction = Faction.ALLIES
        executor._ammo_pickup.fallen_cache.register(fallen, current_tick=0)

        intent = TacticIntent(
            unit_id="u_sa_standing",
            tactic_type=TacticType.SCAVENGE_AMMO,
            target_position=TileCoord(3, 3),
        )
        # No monkeypatch → stance STANDING → WRONG_STANCE → False
        assert executor.execute(intent) is False
        scavenge_events = [e for e in published if "source_id" in e]
        assert scavenge_events == []

    def test_scavenge_ammo_target_unit_id_matches_specific_source(
        self, executor, event_bus, monkeypatch
    ):
        """Happy: target_unit_id selects specific source among multiple."""
        from pycc2.domain.ai.ammo_pickup import AmmoPickupSystem
        from pycc2.domain.systems.combat_mechanics_enhanced import Stance

        monkeypatch.setattr(
            AmmoPickupSystem,
            "_get_unit_stance",
            staticmethod(lambda u: Stance.PRONE),
        )

        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_sa_pick", TileCoord(3, 3))
        executor.register_unit(unit)

        # Register two fallen comrades at adjacent tiles (within FRIENDLY_RANGE=5)
        fallen_a = make_unit("u_fallen_a", TileCoord(3, 4))
        fallen_a.faction = Faction.ALLIES
        fallen_b = make_unit("u_fallen_b", TileCoord(4, 3))
        fallen_b.faction = Faction.ALLIES
        executor._ammo_pickup.fallen_cache.register(fallen_a, current_tick=0)
        executor._ammo_pickup.fallen_cache.register(fallen_b, current_tick=0)

        intent = TacticIntent(
            unit_id="u_sa_pick",
            tactic_type=TacticType.SCAVENGE_AMMO,
            target_position=TileCoord(3, 3),
            target_unit_id="u_fallen_b",  # explicitly pick fallen_b
        )
        assert executor.execute(intent) is True
        scavenge_events = [e for e in published if "source_id" in e]
        assert len(scavenge_events) == 1
        assert scavenge_events[0]["source_id"] == "u_fallen_b"


class TestTacticExecutorClearBuilding:
    """Tests for _execute_clear_building (combat_mixin).

    Covers: Happy (adjacent + event with/without defenders) + Error (unknown
    unit / no game_map / no target_position) + Boundary (dist>1 delegate
    move_to / find_adjacent_approach_pos returns None).
    """

    def test_clear_building_unknown_unit_returns_false(self, executor_with_map):
        """Error: unknown unit_id → False."""
        intent = TacticIntent(
            unit_id="nonexistent",
            tactic_type=TacticType.CLEAR_BUILDING,
            target_position=TileCoord(5, 5),
        )
        assert executor_with_map.execute(intent) is False

    def test_clear_building_without_game_map_returns_false(self, executor):
        """Error: game_map is None → False."""
        unit = make_unit("u_cb_nomap", TileCoord(5, 5))
        executor.register_unit(unit)
        intent = TacticIntent(
            unit_id="u_cb_nomap",
            tactic_type=TacticType.CLEAR_BUILDING,
            target_position=TileCoord(5, 5),
        )
        assert executor.execute(intent) is False

    def test_clear_building_without_target_position_returns_false(
        self, executor_with_map
    ):
        """Error: target_position is None → False."""
        unit = make_unit("u_cb_notp", TileCoord(5, 5))
        executor_with_map.register_unit(unit)
        intent = TacticIntent(
            unit_id="u_cb_notp",
            tactic_type=TacticType.CLEAR_BUILDING,
        )
        assert executor_with_map.execute(intent) is False

    def test_clear_building_dist_gt_1_delegates_to_move_to(
        self, executor_with_map, event_bus
    ):
        """Boundary: dist > 1 → delegate to _execute_move_to, no clear event."""
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_cb_far", TileCoord(0, 0))
        executor_with_map.register_unit(unit)
        intent = TacticIntent(
            unit_id="u_cb_far",
            tactic_type=TacticType.CLEAR_BUILDING,
            target_position=TileCoord(5, 5),
        )
        # dist = 5 > 1, game_map is all OPEN → find_adjacent_approach_pos
        # returns a passable tile → delegates to move_to
        result = executor_with_map.execute(intent)
        assert result is True
        clear_events = [e for e in published if e.get("action") == "clear_building"]
        assert clear_events == []

    def test_clear_building_adjacent_no_defenders_publishes_event(
        self, executor_with_map, event_bus
    ):
        """Happy: dist=1, no defenders → publish event with grenade_effects=0."""
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_cb_nodef", TileCoord(5, 5))
        executor_with_map.register_unit(unit)
        intent = TacticIntent(
            unit_id="u_cb_nodef",
            tactic_type=TacticType.CLEAR_BUILDING,
            target_position=TileCoord(5, 6),  # dist=1
        )
        assert executor_with_map.execute(intent) is True
        clear_events = [e for e in published if e.get("action") == "clear_building"]
        assert len(clear_events) == 1
        assert clear_events[0]["unit_id"] == "u_cb_nodef"
        assert clear_events[0]["grenade_effects"] == 0
        # Unit moved into the building
        assert unit.position.tile_coord == TileCoord(5, 6)

    def test_clear_building_adjacent_with_defenders_publishes_event(
        self, executor_with_map, event_bus
    ):
        """Happy: dist=1, enemy defenders present → grenade hits + event."""
        from pycc2.domain.ai.building_clearing import GRENADE_BUILDING_DAMAGE

        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_cb_atk", TileCoord(5, 5))
        # Enemy defender at target_position, hp=100 (will survive GRENADE_BUILDING_DAMAGE=30)
        defender = make_unit("u_cb_def", TileCoord(5, 6), hp=100)
        defender.faction = Faction.AXIS  # opposite faction → counted as defender
        executor_with_map.register_unit(unit)
        executor_with_map.register_unit(defender)

        intent = TacticIntent(
            unit_id="u_cb_atk",
            tactic_type=TacticType.CLEAR_BUILDING,
            target_position=TileCoord(5, 6),  # dist=1
        )
        assert executor_with_map.execute(intent) is True
        clear_events = [e for e in published if e.get("action") == "clear_building"]
        assert len(clear_events) == 1
        assert clear_events[0]["grenade_effects"] == 1
        # Defender took GRENADE_BUILDING_DAMAGE damage
        assert defender.health.hp == 100 - GRENADE_BUILDING_DAMAGE
        # Unit moved into the building
        assert unit.position.tile_coord == TileCoord(5, 6)

    def test_clear_building_dist_gt_1_no_approach_returns_false(
        self, executor_with_map, game_map, event_bus, monkeypatch
    ):
        """Boundary: dist>1 + find_adjacent_approach_pos returns None → False."""
        from pycc2.domain.ai.building_clearing import BuildingClearingAI

        # Force find_adjacent_approach_pos to return None (no passable approach)
        monkeypatch.setattr(
            BuildingClearingAI,
            "find_adjacent_approach_pos",
            staticmethod(lambda b, u, m: None),
        )

        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_cb_noapproach", TileCoord(0, 0))
        executor_with_map.register_unit(unit)
        intent = TacticIntent(
            unit_id="u_cb_noapproach",
            tactic_type=TacticType.CLEAR_BUILDING,
            target_position=TileCoord(5, 5),  # dist=5 > 1
        )
        assert executor_with_map.execute(intent) is False
        clear_events = [e for e in published if e.get("action") == "clear_building"]
        assert clear_events == []


class TestTacticExecutorAssaultFortified:
    """Tests for _execute_assault_fortified (combat_mixin).

    Covers: Happy (adjacent publish event / active assault publish event) +
    Error (unknown unit / no game_map / no target_position) + Boundary (dist>1
    delegate move_to).
    """

    def test_assault_fortified_unknown_unit_returns_false(self, executor_with_map):
        """Error: unknown unit_id → False."""
        intent = TacticIntent(
            unit_id="nonexistent",
            tactic_type=TacticType.ASSAULT_FORTIFIED,
            target_position=TileCoord(5, 5),
        )
        assert executor_with_map.execute(intent) is False

    def test_assault_fortified_without_game_map_returns_false(self, executor):
        """Error: game_map is None → False."""
        unit = make_unit("u_af_nomap", TileCoord(5, 5))
        executor.register_unit(unit)
        intent = TacticIntent(
            unit_id="u_af_nomap",
            tactic_type=TacticType.ASSAULT_FORTIFIED,
            target_position=TileCoord(5, 5),
        )
        assert executor.execute(intent) is False

    def test_assault_fortified_without_target_position_returns_false(
        self, executor_with_map
    ):
        """Error: target_position is None → False."""
        unit = make_unit("u_af_notp", TileCoord(5, 5))
        executor_with_map.register_unit(unit)
        intent = TacticIntent(
            unit_id="u_af_notp",
            tactic_type=TacticType.ASSAULT_FORTIFIED,
        )
        assert executor_with_map.execute(intent) is False

    def test_assault_fortified_dist_gt_1_delegates_to_move_to(
        self, executor_with_map, event_bus
    ):
        """Boundary: dist > 1, no active assault → delegate to _execute_move_to."""
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_af_far", TileCoord(0, 0))
        executor_with_map.register_unit(unit)
        intent = TacticIntent(
            unit_id="u_af_far",
            tactic_type=TacticType.ASSAULT_FORTIFIED,
            target_position=TileCoord(5, 5),  # dist=5 > 1
        )
        # dist > 1, no active assault → delegates to move_to, returns True
        result = executor_with_map.execute(intent)
        assert result is True
        assault_events = [e for e in published if e.get("action") == "assault_fortified"]
        assert assault_events == []

    def test_assault_fortified_adjacent_publishes_event(
        self, executor_with_map, event_bus
    ):
        """Happy: dist=1 (adjacent), no active assault → publish event + True."""
        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_af_adj", TileCoord(5, 5))
        executor_with_map.register_unit(unit)
        intent = TacticIntent(
            unit_id="u_af_adj",
            tactic_type=TacticType.ASSAULT_FORTIFIED,
            target_position=TileCoord(5, 6),  # dist=1
        )
        assert executor_with_map.execute(intent) is True
        assault_events = [e for e in published if e.get("action") == "assault_fortified"]
        assert len(assault_events) == 1
        assert assault_events[0]["unit_id"] == "u_af_adj"
        assert assault_events[0]["target_position"] == (5, 6)

    def test_assault_fortified_with_active_assault_publishes_event(
        self, executor_with_map, event_bus
    ):
        """Happy: active assault exists (dist>1) → skip move, publish event + True."""
        from unittest.mock import MagicMock

        published: list[dict] = []
        event_bus.subscribe(dict, lambda e: published.append(e))
        unit = make_unit("u_af_active", TileCoord(0, 0))
        executor_with_map.register_unit(unit)
        # Pre-populate _assaults dict so assault is not None → skip move_to
        executor_with_map._engineer_assault_ai._assaults[unit.id] = MagicMock()

        intent = TacticIntent(
            unit_id="u_af_active",
            tactic_type=TacticType.ASSAULT_FORTIFIED,
            target_position=TileCoord(5, 5),  # dist=5 > 1, but active assault
        )
        assert executor_with_map.execute(intent) is True
        assault_events = [e for e in published if e.get("action") == "assault_fortified"]
        assert len(assault_events) == 1
        assert assault_events[0]["unit_id"] == "u_af_active"
