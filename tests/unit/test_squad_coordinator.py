import numpy as np

from pycc2.domain.ai.blackboard import Blackboard
from pycc2.domain.ai.squad_coordinator import SquadCoordinator, SquadOrder, SquadTactic
from pycc2.domain.ai.tactic_intent import TacticType
from pycc2.domain.entities.game_map import GameMap, MapObjective
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord


def _make_unit(
    uid: str,
    x: int = 0,
    y: int = 0,
    faction: Faction = Faction.ALLIES,
    health: int = 100,
    squad_id: str | None = None,
) -> Unit:
    from pycc2.domain.components.health_component import HealthComponent
    from pycc2.domain.components.morale_component import MoraleComponent
    from pycc2.domain.components.position_component import PositionComponent
    from pycc2.domain.components.vision_component import VisionComponent
    from pycc2.domain.components.weapon_component import WeaponComponent

    return Unit(
        id=uid,
        name=f"Unit_{uid}",
        faction=faction,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=health, max_hp=100),
        morale=MoraleComponent(value=100),
        weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=30, max_ammo=30),
        position=PositionComponent(tile_coord=TileCoord(x, y)),
        vision=VisionComponent(range_tiles=5),
        squad_id=squad_id,
    )


def _make_map(width: int = 20, height: int = 20) -> GameMap:
    return GameMap(
        id="test_map",
        name="Test",
        width=width,
        height=height,
        tile_grid=np.zeros((height, width), dtype=np.int8),
    )


class TestSquadRegistration:
    def test_register_squad(self):
        coord = SquadCoordinator()
        coord.register_squad("alpha", ["u1", "u2", "u3"])
        assert coord.active_squads == ["alpha"]
        assert coord.get_squad_for_unit("u1") == "alpha"
        assert coord.get_squad_for_unit("u4") is None

    def test_unregister_squad(self):
        coord = SquadCoordinator()
        coord.register_squad("alpha", ["u1", "u2"])
        coord.unregister_squad("alpha")
        assert coord.active_squads == []
        assert coord.get_squad_for_unit("u1") is None

    def test_register_multiple_squads(self):
        coord = SquadCoordinator()
        coord.register_squad("alpha", ["u1", "u2"])
        coord.register_squad("bravo", ["u3", "u4"])
        assert set(coord.active_squads) == {"alpha", "bravo"}
        assert coord.get_squad_for_unit("u3") == "bravo"

    def test_register_empty_squad(self):
        coord = SquadCoordinator()
        coord.register_squad("empty", [])
        assert "empty" in coord.active_squads


class TestFireConcentration:
    def _setup_fc_scenario(
        self,
    ) -> tuple[SquadCoordinator, dict[str, Blackboard], list[Unit], GameMap]:
        coord = SquadCoordinator()
        coord.register_squad("alpha", ["a1", "a2", "a3"])

        friends = [
            _make_unit("a1", x=2, y=10, squad_id="alpha"),
            _make_unit("a2", x=3, y=10, squad_id="alpha"),
            _make_unit("a3", x=4, y=10, squad_id="alpha"),
        ]
        enemies = [
            _make_unit("e1", x=10, y=10, faction=Faction.AXIS, health=80),
            _make_unit("e2", x=11, y=11, faction=Faction.AXIS, health=120),
        ]

        bbs: dict[str, Blackboard] = {}
        for u in friends:
            bb = Blackboard()
            bb.set("visible_enemies", [e.id for e in enemies])
            bbs[u.id] = bb

        all_units = friends + enemies
        game_map = _make_map()
        return coord, bbs, all_units, game_map

    def test_evaluate_returns_fire_concentration(self):
        coord = SquadCoordinator()
        coord.register_squad("alpha", ["a1", "a2", "a3"])
        friends = [
            _make_unit("a1", x=2, y=10, squad_id="alpha"),
            _make_unit("a2", x=3, y=10, squad_id="alpha"),
            _make_unit("a3", x=4, y=10, squad_id="alpha"),
        ]
        enemies = [
            _make_unit("e1", x=10, y=10, faction=Faction.AXIS, health=80),
        ]
        bbs: dict[str, Blackboard] = {}
        for u in friends:
            bb = Blackboard()
            bb.set("visible_enemies", [e.id for e in enemies])
            bbs[u.id] = bb
        order = coord.evaluate_squad_tactics("alpha", bbs, friends + enemies, _make_map())
        assert order is not None
        assert order.tactic == SquadTactic.FIRE_CONCENTRATION
        assert order.target_unit_id == "e1"
        assert len(order.assigned_units) == 3

    def test_distribute_fire_concentration(self):
        coord = SquadCoordinator()
        coord.register_squad("alpha", ["a1", "a2", "a3"])
        friends = [
            _make_unit("a1", x=2, y=10, squad_id="alpha"),
            _make_unit("a2", x=3, y=10, squad_id="alpha"),
            _make_unit("a3", x=4, y=10, squad_id="alpha"),
        ]
        enemies = [
            _make_unit("e1", x=10, y=10, faction=Faction.AXIS, health=80),
        ]
        bbs: dict[str, Blackboard] = {}
        for u in friends:
            bb = Blackboard()
            bb.set("visible_enemies", [e.id for e in enemies])
            bbs[u.id] = bb
        order = coord.evaluate_squad_tactics("alpha", bbs, friends + enemies, _make_map())
        assert order is not None
        intents = coord.distribute_squad_order(order)
        assert len(intents) >= 2, f"Fire concentration order should produce at least 2 intents, got {len(intents)}"
        types = {i.tactic_type for i in intents}
        assert TacticType.ATTACK in types
        assert TacticType.SUPPRESS_FIRE in types

    def test_targets_highest_health_enemy(self):
        coord, bbs, units, gm = self._setup_fc_scenario()
        order = coord.evaluate_squad_tactics("alpha", bbs, units, gm)
        assert order is not None
        assert order.target_unit_id == "e2"


class TestBoundingOverwatch:
    def _setup_bo_scenario(
        self,
    ) -> tuple[SquadCoordinator, dict[str, Blackboard], list[Unit], GameMap]:
        coord = SquadCoordinator()
        coord.register_squad("alpha", ["a1", "a2", "a3", "a4"])

        friends = [
            _make_unit("a1", x=5, y=5, squad_id="alpha"),
            _make_unit("a2", x=6, y=5, squad_id="alpha"),
            _make_unit("a3", x=5, y=6, squad_id="alpha"),
            _make_unit("a4", x=6, y=6, squad_id="alpha"),
        ]
        bbs: dict[str, Blackboard] = {}
        for u in friends:
            bb = Blackboard()
            bb.set("has_unknown_ahead", True)
            bbs[u.id] = bb
        game_map = _make_map()
        return coord, bbs, friends, game_map

    def test_evaluate_returns_bounding_overwatch(self):
        coord, bbs, units, gm = self._setup_bo_scenario()
        order = coord.evaluate_squad_tactics("alpha", bbs, units, gm)
        assert order is not None
        assert order.tactic == SquadTactic.BOUNDING_OVERWATCH
        assert order.target_position is not None

    def test_distribute_alternating_groups(self):
        coord, bbs, units, gm = self._setup_bo_scenario()
        order = coord.evaluate_squad_tactics("alpha", bbs, units, gm)
        assert order is not None
        intents1 = coord.distribute_squad_order(order)
        intents2 = coord.distribute_squad_order(order)
        move_types_1 = [i.tactic_type for i in intents1 if i.tactic_type == TacticType.MOVE_TO]
        move_types_2 = [i.tactic_type for i in intents2 if i.tactic_type == TacticType.MOVE_TO]
        assert len(move_types_1) >= 1, f"First distribute should have at least 1 MOVE_TO intent"
        assert len(move_types_2) >= 1, f"Second distribute should have at least 1 MOVE_TO intent"


class TestCrossfire:
    def _setup_cf_scenario(
        self,
    ) -> tuple[SquadCoordinator, dict[str, Blackboard], list[Unit], GameMap]:
        coord = SquadCoordinator()
        coord.register_squad("alpha", ["a1", "a2", "a3"])

        friends = [
            _make_unit("a1", x=2, y=8, squad_id="alpha"),
            _make_unit("a2", x=2, y=12, squad_id="alpha"),
            _make_unit("a3", x=8, y=10, squad_id="alpha"),
        ]
        enemies = [
            _make_unit("e1", x=10, y=10, faction=Faction.AXIS, health=90),
            _make_unit("e2", x=10, y=9, faction=Faction.AXIS, health=60),
        ]
        bbs: dict[str, Blackboard] = {}
        for u in friends:
            bb = Blackboard()
            bb.set("visible_enemies", [e.id for e in enemies])
            bbs[u.id] = bb
        game_map = _make_map()
        return coord, bbs, friends + enemies, game_map

    def test_evaluate_returns_crossfire_with_multiple_enemies(self):
        coord, bbs, units, gm = self._setup_cf_scenario()
        order = coord.evaluate_squad_tactics("alpha", bbs, units, gm)
        assert order is not None
        assert order.tactic == SquadTactic.CROSSFIRE

    def test_distribute_crossfire_positions_units(self):
        coord, bbs, units, gm = self._setup_cf_scenario()
        order = coord.evaluate_squad_tactics("alpha", bbs, units, gm)
        assert order is not None
        intents = coord.distribute_squad_order(order)
        move_intents = [i for i in intents if i.tactic_type == TacticType.MOVE_TO]
        attack_intents = [i for i in intents if i.tactic_type == TacticType.ATTACK]
        assert len(move_intents) >= 1
        assert len(attack_intents) >= 1


class TestFlanking:
    def _setup_fk_scenario(
        self,
    ) -> tuple[SquadCoordinator, dict[str, Blackboard], list[Unit], GameMap]:
        coord = SquadCoordinator()
        coord.register_squad("alpha", ["a1", "a2", "a3"])

        friends = [
            _make_unit("a1", x=10, y=10, squad_id="alpha"),
            _make_unit("a2", x=11, y=10, squad_id="alpha"),
            _make_unit("a3", x=12, y=8, squad_id="alpha"),
        ]
        enemies = [
            _make_unit("e1", x=12, y=10, faction=Faction.AXIS, health=100),
        ]
        bbs: dict[str, Blackboard] = {}
        for u in friends:
            bb = Blackboard()
            bb.set("visible_enemies", [e.id for e in enemies])
            bbs[u.id] = bb
        game_map = _make_map()
        return coord, bbs, friends + enemies, game_map

    def test_evaluate_returns_flanking_when_applicable(self):
        coord, bbs, units, gm = self._setup_fk_scenario()
        order = coord.evaluate_squad_tactics("alpha", bbs, units, gm)
        assert order is not None
        assert order.tactic == SquadTactic.FLANKING

    def test_distribute_flanking_has_main_and_flank_force(self):
        coord, bbs, units, gm = self._setup_fk_scenario()
        order = coord.evaluate_squad_tactics("alpha", bbs, units, gm)
        assert order is not None
        intents = coord.distribute_squad_order(order)
        suppress = [i for i in intents if i.tactic_type == TacticType.SUPPRESS_FIRE]
        flank_move = [i for i in intents if i.tactic_type == TacticType.MOVE_TO]
        flank_attack = [i for i in intents if i.tactic_type == TacticType.ATTACK]
        assert len(suppress) >= 1
        assert len(flank_move) >= 1
        assert len(flank_attack) >= 1


class TestDefensiveLine:
    def test_evaluate_defensive_line_near_objective(self):
        coord = SquadCoordinator()
        coord.register_squad("alpha", ["a1", "a2"])
        friends = [
            _make_unit("a1", x=8, y=8, squad_id="alpha"),
            _make_unit("a2", x=10, y=8, squad_id="alpha"),
        ]
        game_map = _make_map()
        game_map.objectives.append(
            MapObjective(id="obj1", name="Key Point", position=TileCoord(10, 10))
        )
        bbs: dict[str, Blackboard] = {u.id: Blackboard() for u in friends}
        order = coord.evaluate_squad_tactics("alpha", bbs, friends, game_map)
        assert order is not None
        assert order.tactic == SquadTactic.DEFENSIVE_LINE

    def test_distribute_defensive_line_spreads_units(self):
        coord = SquadCoordinator()
        coord.register_squad("alpha", ["a1", "a2", "a3"])
        friends = [
            _make_unit("a1", x=8, y=8, squad_id="alpha"),
            _make_unit("a2", x=10, y=8, squad_id="alpha"),
            _make_unit("a3", x=12, y=8, squad_id="alpha"),
        ]
        game_map = _make_map()
        game_map.objectives.append(
            MapObjective(id="obj1", name="Key Point", position=TileCoord(10, 10))
        )
        bbs: dict[str, Blackboard] = {u.id: Blackboard() for u in friends}
        order = coord.evaluate_squad_tactics("alpha", bbs, friends, game_map)
        assert order is not None
        intents = coord.distribute_squad_order(order)
        move_intents = [i for i in intents if i.tactic_type == TacticType.MOVE_TO]
        defend_intents = [i for i in intents if i.tactic_type == TacticType.DEFEND]
        assert len(move_intents) == 3
        assert len(defend_intents) == 3


class TestCooldownManagement:
    def test_cooldown_blocks_evaluation(self):
        coord = SquadCoordinator()
        coord.register_squad("alpha", ["a1", "a2"])
        coord._cooldowns["alpha"] = 5
        friends = [
            _make_unit("a1", x=5, y=5, squad_id="alpha"),
            _make_unit("a2", x=6, y=5, squad_id="alpha"),
        ]
        bbs: dict[str, Blackboard] = {u.id: Blackboard() for u in friends}
        order = coord.evaluate_squad_tactics("alpha", bbs, friends, _make_map())
        assert order is None

    def test_tick_decrements_cooldown(self):
        coord = SquadCoordinator()
        coord._cooldowns["alpha"] = 3
        coord.tick()
        assert coord._cooldowns["alpha"] == 2
        coord.tick()
        coord.tick()
        assert coord._cooldowns["alpha"] == 0


class TestEdgeCases:
    def test_empty_squad_returns_none(self):
        coord = SquadCoordinator()
        coord.register_squad("empty", [])
        bbs: dict[str, Blackboard] = {}
        order = coord.evaluate_squad_tactics("empty", bbs, [], _make_map())
        assert order is None

    def test_single_member_squad_returns_none(self):
        coord = SquadCoordinator()
        coord.register_squad("lone", ["u1"])
        u = _make_unit("u1", squad_id="lone")
        bbs: dict[str, Blackboard] = {"u1": Blackboard()}
        order = coord.evaluate_squad_tactics("lone", bbs, [u], _make_map())
        assert order is None

    def test_unknown_squad_returns_none(self):
        coord = SquadCoordinator()
        bbs: dict[str, Blackboard] = {}
        order = coord.evaluate_squad_tactics("nonexistent", bbs, [], _make_map())
        assert order is None

    def test_no_visible_enemies_returns_none(self):
        coord = SquadCoordinator()
        coord.register_squad("alpha", ["a1", "a2"])
        friends = [_make_unit("a1", squad_id="alpha"), _make_unit("a2", squad_id="alpha")]
        bbs: dict[str, Blackboard] = {"a1": Blackboard(), "a2": Blackboard()}
        order = coord.evaluate_squad_tactics("alpha", bbs, friends, _make_map())
        assert order is None

    def test_dead_units_excluded_from_orders(self):
        coord = SquadCoordinator()
        coord.register_squad("alpha", ["a1", "a2", "a3", "a4"])
        friends = [
            _make_unit("a1", squad_id="alpha", health=0),
            _make_unit("a2", x=10, y=10, squad_id="alpha", health=100),
            _make_unit("a3", x=11, y=10, squad_id="alpha", health=100),
            _make_unit("a4", x=12, y=8, squad_id="alpha", health=100),
        ]
        enemies = [_make_unit("e1", x=14, y=10, faction=Faction.AXIS)]
        bbs: dict[str, Blackboard] = {}
        for u in friends:
            if u.is_alive:
                bb = Blackboard()
                bb.set("visible_enemies", ["e1"])
                bbs[u.id] = bb
        order = coord.evaluate_squad_tactics("alpha", bbs, friends + enemies, _make_map())
        assert order is not None
        assert "a1" not in order.assigned_units

    def test_distribute_order_with_no_units(self):
        coord = SquadCoordinator()
        order = SquadOrder(squad_id="empty", tactic=SquadTactic.FIRE_CONCENTRATION)
        intents = coord.distribute_squad_order(order)
        assert intents == []

    def test_all_squad_tactics_exist(self):
        expected = {
            SquadTactic.FIRE_CONCENTRATION,
            SquadTactic.BOUNDING_OVERWATCH,
            SquadTactic.CROSSFIRE,
            SquadTactic.DEFENSIVE_LINE,
            SquadTactic.FLANKING,
        }
        assert set(SquadTactic) == expected


class TestSquadOrderDataclass:
    def test_default_values(self):
        order = SquadOrder(squad_id="s1", tactic=SquadTactic.FIRE_CONCENTRATION)
        assert order.target_unit_id is None
        assert order.target_position is None
        assert order.assigned_units == []
        assert order.priority == 5

    def test_custom_values(self):
        pos = TileCoord(5, 10)
        order = SquadOrder(
            squad_id="s2",
            tactic=SquadTactic.FLANKING,
            target_unit_id="enemy_1",
            target_position=pos,
            assigned_units=["u1", "u2"],
            priority=8,
        )
        assert order.squad_id == "s2"
        assert order.tactic == SquadTactic.FLANKING
        assert order.target_unit_id == "enemy_1"
        assert order.target_position == pos
        assert order.assigned_units == ["u1", "u2"]
        assert order.priority == 8
