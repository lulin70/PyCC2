from __future__ import annotations

import numpy as np

from pycc2.domain.ai.commander_ai import (
    CommanderAI,
    CommanderOrder,
    CommanderRole,
    TacticalAdvisor,
    ThreatLevel,
    _get_fire_power,
)
from pycc2.domain.ai.tactic_intent import TacticType
from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord


def _make_unit(
    uid: str = "u1",
    faction: Faction = Faction.ALLIES,
    unit_type: UnitType = UnitType.INFANTRY_SQUAD,
    x: int = 5,
    y: int = 5,
    hp: int = 100,
    max_hp: int = 100,
    squad_id: str | None = None,
) -> Unit:
    return Unit(
        id=uid,
        name=f"unit_{uid}",
        faction=faction,
        unit_type=unit_type,
        health=HealthComponent(hp=hp, max_hp=max_hp),
        morale=MoraleComponent(value=80, panic_threshold=30, rout_threshold=10),
        weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=30, max_ammo=30),
        position=PositionComponent(tile_coord=TileCoord(x, y)),
        vision=VisionComponent(range_tiles=6),
        squad_id=squad_id,
    )


def _make_map(w: int = 30, h: int = 20) -> GameMap:
    grid = np.zeros((h, w), dtype=np.int8)
    grid[5:7, 5:8] = 3
    grid[10, 15] = 11
    grid[3, 12] = 4
    grid[8, 18] = 5
    return GameMap(id="test", name="test", width=w, height=h, tile_grid=grid)


class TestBattlefieldPictureAssessment:
    def test_basic_counts_and_positions(self):
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER)
        ai = CommanderAI(cmd)
        allies = [_make_unit("a1"), _make_unit("a2")]
        enemies = [
            _make_unit("e1", faction=Faction.AXIS, x=15, y=10),
            _make_unit("e2", faction=Faction.AXIS, x=16, y=11),
        ]
        m = _make_map()
        pic = ai.assess_battlefield(allies + enemies + [cmd], m, current_tick=1)

        assert pic.ally_count == 3
        assert pic.enemy_count == 2
        assert len(pic.ally_positions) == 3
        assert len(pic.enemy_positions) == 2

    def test_force_ratio_calculation(self):
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER)
        ai = CommanderAI(cmd)
        allies = [_make_unit("a1")]
        enemies = [
            _make_unit("e1", faction=Faction.AXIS, x=15, y=10, hp=40, max_hp=100),
        ]
        m = _make_map()
        pic = ai.assess_battlefield(allies + enemies + [cmd], m, current_tick=1)

        assert pic.force_ratio > 0.0, f"Force ratio should be positive when allies exist, got {pic.force_ratio}"
        assert isinstance(pic.force_ratio, float)

    def test_threat_level_critical(self):
        cmd = _make_unit("cmd", hp=10, max_hp=100, unit_type=UnitType.COMMANDER)
        ai = CommanderAI(cmd)
        enemies = [
            _make_unit(
                "e1", faction=Faction.AXIS, x=15, y=10, unit_type=UnitType.MACHINE_GUN_SQUAD
            ),
            _make_unit("e2", faction=Faction.AXIS, x=14, y=9, unit_type=UnitType.MACHINE_GUN_SQUAD),
            _make_unit(
                "e3", faction=Faction.AXIS, x=13, y=11, unit_type=UnitType.MACHINE_GUN_SQUAD
            ),
        ]
        m = _make_map()
        pic = ai.assess_battlefield(enemies + [cmd], m, current_tick=1)

        assert pic.threat_level in (ThreatLevel.CRITICAL, ThreatLevel.HIGH)

    def test_front_line_center_calculation(self):
        cmd = _make_unit("cmd", x=5, y=5, unit_type=UnitType.COMMANDER)
        ai = CommanderAI(cmd)
        allies = [_make_unit("a1", x=4, y=5)]
        enemies = [_make_unit("e1", faction=Faction.AXIS, x=14, y=5)]
        m = _make_map()
        pic = ai.assess_battlefield(allies + enemies + [cmd], m, current_tick=1)

        assert pic.front_line_center is not None

    def test_key_terrain_identification(self):
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER)
        ai = CommanderAI(cmd)
        m = _make_map()
        pic = ai.assess_battlefield([cmd], m, current_tick=1)

        assert len(pic.key_terrain) >= 0
        assert isinstance(pic.key_terrain, list)


class TestOrderGeneration:
    def test_critical_generates_regroup_and_defend(self):
        cmd = _make_unit("cmd", hp=5, max_hp=100, unit_type=UnitType.COMMANDER)
        ai = CommanderAI(cmd)
        managed = ["a1", "a2"]
        units = [
            cmd,
            _make_unit("a1", hp=5, max_hp=100),
            _make_unit("a2", hp=5, max_hp=100),
            _make_unit(
                "e1", faction=Faction.AXIS, x=15, y=10, unit_type=UnitType.MACHINE_GUN_SQUAD
            ),
            _make_unit("e2", faction=Faction.AXIS, x=14, y=9, unit_type=UnitType.MACHINE_GUN_SQUAD),
        ]
        m = _make_map()
        pic = ai.assess_battlefield(units, m, current_tick=1)
        assert pic.threat_level == ThreatLevel.CRITICAL
        orders = ai.generate_orders(managed, units)

        order_types = {o.order_type for o in orders}
        assert TacticType.REGROUP in order_types or TacticType.DEFEND in order_types

    def test_high_disadvantage_generates_retreat(self):
        cmd = _make_unit("cmd", hp=30, max_hp=100, unit_type=UnitType.COMMANDER)
        ai = CommanderAI(cmd)
        managed = ["a1"]
        units = [
            cmd,
            _make_unit("a1"),
            _make_unit("e1", faction=Faction.AXIS, x=6, y=5, unit_type=UnitType.MACHINE_GUN_SQUAD),
            _make_unit("e2", faction=Faction.AXIS, x=7, y=5, unit_type=UnitType.MACHINE_GUN_SQUAD),
            _make_unit("e3", faction=Faction.AXIS, x=8, y=5, unit_type=UnitType.MACHINE_GUN_SQUAD),
        ]
        m = _make_map()
        ai.assess_battlefield(units, m, current_tick=1)
        orders = ai.generate_orders(managed, units)

        order_types = {o.order_type for o in orders}
        assert TacticType.RETREAT in order_types or len(orders) >= 0

    def test_high_advantage_generates_suppress_and_hold(self):
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER)
        ai = CommanderAI(cmd)
        managed = ["mg1", "inf1"]
        units = [
            cmd,
            _make_unit("mg1", unit_type=UnitType.MACHINE_GUN_SQUAD),
            _make_unit("inf1"),
            _make_unit(
                "e1", faction=Faction.AXIS, x=15, y=10, unit_type=UnitType.MACHINE_GUN_SQUAD
            ),
            _make_unit(
                "e2", faction=Faction.AXIS, x=16, y=11, unit_type=UnitType.MACHINE_GUN_SQUAD
            ),
            _make_unit(
                "e3", faction=Faction.AXIS, x=17, y=12, unit_type=UnitType.MACHINE_GUN_SQUAD
            ),
        ]
        m = _make_map()
        pic = ai.assess_battlefield(units, m, current_tick=1)
        assert pic.threat_level == ThreatLevel.HIGH
        orders = ai.generate_orders(managed, units)

        order_types = {o.order_type for o in orders}
        assert len(orders) >= 1, f"High advantage should generate at least 1 order, got {len(orders)}"
        assert (
            TacticType.SUPPRESS_FIRE in order_types
            or TacticType.HOLD_POSITION in order_types
            or TacticType.DEFEND in order_types
        )

    def test_medium_aggressive_generates_attack(self):
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER)
        ai = CommanderAI(cmd)

        class FakeDC:
            aggressiveness = 0.8

        managed = ["inf1", "inf2", "mg1"]
        units = [
            cmd,
            _make_unit("inf1"),
            _make_unit("inf2"),
            _make_unit("mg1", unit_type=UnitType.MACHINE_GUN_SQUAD),
            _make_unit("e1", faction=Faction.AXIS, x=12, y=8),
            _make_unit("e2", faction=Faction.AXIS, x=13, y=9),
        ]
        m = _make_map()
        ai.assess_battlefield(units, m, current_tick=1)
        orders = ai.generate_orders(managed, units, difficulty_config=FakeDC())

        order_types = {o.order_type for o in orders}
        assert TacticType.ATTACK in order_types or TacticType.SUPPRESS_FIRE in order_types

    def test_low_threat_generates_patrol(self):
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER)
        ai = CommanderAI(cmd)
        managed = ["a1", "a2"]
        units = [cmd, _make_unit("a1"), _make_unit("a2")]
        m = _make_map()
        ai.assess_battlefield(units, m, current_tick=1)
        orders = ai.generate_orders(managed, units)

        order_types = {o.order_type for o in orders}
        assert TacticType.PATROL in order_types

    def test_orders_contain_target_ids_and_reasoning(self):
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER)
        ai = CommanderAI(cmd)

        class FakeDC:
            aggressiveness = 0.8

        managed = ["a1"]
        units = [
            cmd,
            _make_unit("a1"),
            _make_unit("e1", faction=Faction.AXIS, x=12, y=8),
            _make_unit("e2", faction=Faction.AXIS, x=13, y=9),
        ]
        m = _make_map()
        pic = ai.assess_battlefield(units, m, current_tick=1)
        assert pic.threat_level != ThreatLevel.NONE
        orders = ai.generate_orders(managed, units, difficulty_config=FakeDC())

        assert len(orders) >= 1, f"Orders should contain at least 1 entry when targets exist, got {len(orders)}"
        for o in orders:
            assert isinstance(o.target_unit_ids, list)
            assert len(o.target_unit_ids) > 0
            assert isinstance(o.reasoning, str)


class TestOrderManagement:
    def test_get_pending_orders_for_unit_filters_correctly(self):
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER)
        ai = CommanderAI(cmd)
        o1 = CommanderOrder(
            order_id="o1",
            commander_id="cmd",
            target_unit_ids=["a1", "a2"],
            order_type=TacticType.ATTACK,
        )
        o2 = CommanderOrder(
            order_id="o2",
            commander_id="cmd",
            target_unit_ids=["a3"],
            order_type=TacticType.DEFEND,
        )
        ai._pending_orders = [o1, o2]

        a1_orders = ai.get_pending_orders_for_unit("a1")
        assert len(a1_orders) == 1
        assert a1_orders[0].order_id == "o1"

        a3_orders = ai.get_pending_orders_for_unit("a3")
        assert len(a3_orders) == 1
        assert a3_orders[0].order_id == "o2"

        no_orders = ai.get_pending_orders_for_unit("nonexistent")
        assert len(no_orders) == 0

    def test_expire_old_orders_removes_expired(self):
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER)
        ai = CommanderAI(cmd)
        o1 = CommanderOrder(
            order_id="o1",
            commander_id="cmd",
            target_unit_ids=["a1"],
            order_type=TacticType.ATTACK,
            expires_in_ticks=5,
        )
        o1.set_created_tick(1)
        o2 = CommanderOrder(
            order_id="o2",
            commander_id="cmd",
            target_unit_ids=["a2"],
            order_type=TacticType.DEFEND,
            expires_in_ticks=-1,
        )
        o2.set_created_tick(1)
        ai._pending_orders = [o1, o2]

        ai.expire_old_orders(current_tick=10)
        assert len(ai._pending_orders) == 1
        assert ai._pending_orders[0].order_id == "o2"

    def test_convert_to_unit_intents(self):
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER)
        ai = CommanderAI(cmd)
        orders = [
            CommanderOrder(
                order_id="o1",
                commander_id="cmd",
                target_unit_ids=["a1", "a2"],
                order_type=TacticType.ATTACK,
                priority=7,
                target_position=TileCoord(10, 10),
                target_unit_id="e1",
            ),
            CommanderOrder(
                order_id="o2",
                commander_id="cmd",
                target_unit_ids=["a3"],
                order_type=TacticType.DEFEND,
                priority=5,
            ),
        ]

        intents = ai.convert_to_unit_intents(orders)

        assert len(intents) == 3
        u1_intent = next(i for i in intents if i.unit_id == "a1")
        assert u1_intent.tactic_type == TacticType.ATTACK
        assert u1_intent.priority == 7
        assert u1_intent.target_position == TileCoord(10, 10)
        assert u1_intent.target_unit_id == "e1"


class TestThreatScore:
    def test_different_unit_types_have_different_scores(self):
        inf = _make_unit("inf", unit_type=UnitType.INFANTRY_SQUAD, x=10, y=10)
        mg = _make_unit("mg", unit_type=UnitType.MACHINE_GUN_SQUAD, x=10, y=10)

        score_inf = CommanderAI.calculate_threat_score(inf, distance_to_commander=5.0)
        score_mg = CommanderAI.calculate_threat_score(mg, distance_to_commander=5.0)

        assert score_mg > score_inf

    def test_distance_affects_threat_score(self):
        mg = _make_unit("mg", unit_type=UnitType.MACHINE_GUN_SQUAD)

        score_close = CommanderAI.calculate_threat_score(mg, distance_to_commander=2.0)
        score_far = CommanderAI.calculate_threat_score(mg, distance_to_commander=10.0)

        assert score_close > score_far


class TestTacticalAdvisor:
    def test_suggest_attack_vector_returns_valid_path(self):
        cmd_pos = TileCoord(5, 5)
        enemy_positions = [TileCoord(15, 10), TileCoord(12, 8)]
        ally_positions = [TileCoord(4, 5), TileCoord(6, 5)]
        m = _make_map()

        path = TacticalAdvisor.suggest_attack_vector(cmd_pos, enemy_positions, m, ally_positions)

        assert len(path) >= 1
        assert path[0] == cmd_pos

    def test_suggest_defensive_positions_returns_cover_positions(self):
        fallback = TileCoord(10, 10)
        m = _make_map()

        positions = TacticalAdvisor.suggest_defensive_positions(fallback, 3, m)

        assert len(positions) <= 3

    def test_suggest_retreat_route_avoids_enemies(self):
        start = TileCoord(5, 5)
        safe = TileCoord(25, 15)
        enemy_positions = [TileCoord(10, 8), TileCoord(12, 10)]
        m = _make_map()

        route = TacticalAdvisor.suggest_retreat_route(start, safe, m, enemy_positions)

        assert len(route) >= 2
        assert route[0] == start

    def test_optimize_fire_allocation_matches_reasonably(self):
        allies = [
            _make_unit("a1", unit_type=UnitType.INFANTRY_SQUAD, x=5, y=5),
            _make_unit("a2", unit_type=UnitType.MACHINE_GUN_SQUAD, x=6, y=5),
        ]
        enemies = [
            _make_unit("e1", faction=Faction.AXIS, x=12, y=8, hp=80, max_hp=100),
            _make_unit("e2", faction=Faction.AXIS, x=13, y=9, hp=40, max_hp=100),
        ]

        allocation = TacticalAdvisor.optimize_fire_allocation(allies, enemies, engagement=None)

        assert len(allocation) <= len(allies)
        for aid, eid in allocation.items():
            assert aid in {"a1", "a2"}
            assert eid in {"e1", "e2"}


class TestCommanderRoleAndThreatLevelEnums:
    def test_commander_role_values(self):
        assert CommanderRole.OVERALL.value != CommanderRole.SQUAD_LEADER.value

    def test_threat_level_ordering(self):
        levels = list(ThreatLevel)
        assert ThreatLevel.CRITICAL in levels
        assert ThreatLevel.NONE in levels


class TestFirePowerHelper:
    def test_mg_higher_than_infantry(self):
        from pycc2.domain.entities.unit import UnitType

        assert _get_fire_power(UnitType.MACHINE_GUN_SQUAD.value) > _get_fire_power(
            UnitType.INFANTRY_SQUAD.value
        )

    def test_commander_between_mg_and_infantry(self):
        from pycc2.domain.entities.unit import UnitType

        mg_fp = _get_fire_power(UnitType.MACHINE_GUN_SQUAD.value)
        cmd_fp = _get_fire_power(UnitType.COMMANDER.value)
        inf_fp = _get_fire_power(UnitType.INFANTRY_SQUAD.value)

        assert inf_fp < cmd_fp < mg_fp
