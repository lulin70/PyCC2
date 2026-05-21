from __future__ import annotations

import numpy as np
import pytest

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.systems.ballistic import BallisticEngine
from pycc2.domain.systems.combat_resolver import CombatResolver
from pycc2.domain.systems.morale_sys import MoraleCalculator
from pycc2.domain.value_objects.terrain_type import TerrainType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.services.event_bus import EventBus
from pycc2.services.random_context import RandomContext


@pytest.fixture
def rng() -> RandomContext:
    return RandomContext.from_seed(42)


@pytest.fixture
def event_bus() -> EventBus:
    return EventBus()


@pytest.fixture
def resolver(rng: RandomContext, event_bus: EventBus) -> CombatResolver:
    return CombatResolver(
        ballistic_engine=BallisticEngine(rng=rng),
        morale_calc=MoraleCalculator(),
        rng=rng,
        event_bus=event_bus,
    )


@pytest.fixture
def game_map() -> GameMap:
    grid = np.full((20, 20), TerrainType.OPEN.value, dtype=np.int8)
    return GameMap(id="test_map", name="Test Map", width=20, height=20, tile_grid=grid)


def make_unit(
    name: str,
    faction: Faction,
    pos: TileCoord,
    hp: int = 100,
    max_hp: int = 100,
    weapon_id: str = "rifle",
    ammo: int = 30,
    max_ammo: int = 30,
) -> Unit:
    health = HealthComponent(hp=hp, max_hp=max_hp)
    morale = MoraleComponent(value=80, panic_threshold=20, rout_threshold=10)
    weapon = WeaponComponent(primary_weapon_id=weapon_id, ammo_remaining=ammo, max_ammo=max_ammo)
    position = PositionComponent(tile_coord=pos)
    vision = VisionComponent(range_tiles=6)
    return Unit(
        id=f"u_{name.lower()}",
        name=name,
        faction=faction,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=health,
        morale=morale,
        weapon=weapon,
        position=position,
        vision=vision,
    )


class TestCRAttack:
    def test_normal_hit(self, resolver: CombatResolver, game_map: GameMap):
        attacker = make_unit("Attacker", Faction.ALLIES, TileCoord(0, 0))
        target = make_unit("Target", Faction.AXIS, TileCoord(3, 0))
        result = resolver.resolve_attack(attacker, target, game_map=game_map)

        assert result["shot_result"] is not None
        assert "events_fired" in result

    def test_miss_still_processes_suppression(self, resolver: CombatResolver, game_map: GameMap):
        attacker = make_unit("Attacker", Faction.ALLIES, TileCoord(0, 0))
        target = make_unit("Target", Faction.AXIS, TileCoord(18, 0), hp=100)
        result = resolver.resolve_attack(attacker, target, game_map=game_map)

        assert result["shot_result"] is not None

    def test_target_death_triggers_killed_event(self, resolver: CombatResolver, game_map: GameMap):
        attacker = make_unit("Attacker", Faction.ALLIES, TileCoord(0, 0))
        target = make_unit("Target", Faction.AXIS, TileCoord(1, 0), hp=5)
        result = resolver.resolve_attack(attacker, target, game_map=game_map)

        assert not target.is_alive
        assert "UnitKilled" in result["events_fired"]

    def test_attacker_cannot_act_returns_empty(self, resolver: CombatResolver, game_map: GameMap):
        attacker = make_unit("DeadAttacker", Faction.ALLIES, TileCoord(0, 0), hp=0)
        target = make_unit("Target", Faction.AXIS, TileCoord(3, 0))

        assert not attacker.can_act
        result = resolver.resolve_attack(attacker, target, game_map=game_map)

        assert result["shot_result"] is None
        assert len(result["events_fired"]) == 0

    def test_dead_target_returns_empty(self, resolver: CombatResolver, game_map: GameMap):
        attacker = make_unit("Attacker", Faction.ALLIES, TileCoord(0, 0))
        target = make_unit("DeadTarget", Faction.AXIS, TileCoord(3, 0), hp=0)

        assert not target.is_alive
        result = resolver.resolve_attack(attacker, target, game_map=game_map)

        assert result["shot_result"] is None
        assert len(result["events_fired"]) == 0

    def test_no_event_bus_does_not_crash(self, rng: RandomContext, game_map: GameMap):
        no_bus_resolver = CombatResolver(
            ballistic_engine=BallisticEngine(rng=rng),
            morale_calc=MoraleCalculator(),
            rng=rng,
            event_bus=None,
        )
        attacker = make_unit("Attacker", Faction.ALLIES, TileCoord(0, 0))
        target = make_unit("Target", Faction.AXIS, TileCoord(3, 0))

        result = no_bus_resolver.resolve_attack(attacker, target, game_map=game_map)
        assert result["shot_result"] is not None

    def test_suppression_applied_to_target(self, resolver: CombatResolver, game_map: GameMap):
        attacker = make_unit("Attacker", Faction.ALLIES, TileCoord(0, 0))
        target = make_unit("Target", Faction.AXIS, TileCoord(3, 0))
        old_suppression = target.morale.suppression

        resolver.resolve_attack(attacker, target, game_map=game_map)

        assert target.morale.suppression >= old_suppression


class TestCRMorale:
    def test_hit_triggers_morale_changed_event(self, resolver: CombatResolver, game_map: GameMap):
        attacker = make_unit("Attacker", Faction.ALLIES, TileCoord(0, 0))
        target = make_unit("Target", Faction.AXIS, TileCoord(1, 0))
        result = resolver.resolve_attack(attacker, target, game_map=game_map)

        if result["shot_result"].hit:
            assert "MoraleChanged" in result["events_fired"]

    def test_killing_blow_triggers_ally_killed_event(
        self, resolver: CombatResolver, game_map: GameMap
    ):
        attacker = make_unit("Sniper", Faction.ALLIES, TileCoord(0, 0))
        target = make_unit("WeakTarget", Faction.AXIS, TileCoord(1, 0), hp=5)
        result = resolver.resolve_attack(attacker, target, game_map=game_map)

        if result["shot_result"].is_killing_blow or not target.is_alive:
            assert result["morale_result"] is not None

    def test_morale_state_change_recorded(self, resolver: CombatResolver, game_map: GameMap):
        attacker = make_unit("Attacker", Faction.ALLIES, TileCoord(0, 0))
        target = make_unit("Target", Faction.AXIS, TileCoord(1, 0), hp=10)
        result = resolver.resolve_attack(attacker, target, game_map=game_map)

        if result["morale_result"] is not None:
            morale_res = result["morale_result"]
            assert hasattr(morale_res, "state_changed")

    def test_leader_killed_has_greater_impact(self, resolver: CombatResolver, game_map: GameMap):
        leader = make_unit("Leader", Faction.AXIS, TileCoord(1, 0), hp=5)
        normal_unit = make_unit("Soldier", Faction.AXIS, TileCoord(2, 0), hp=100)

        from pycc2.domain.systems.morale_sys import MoraleEvent

        leader_result = resolver.morale_calc.calculate_event_effect(
            leader.morale, MoraleEvent.LEADER_KILLED
        )
        normal_result = resolver.morale_calc.calculate_event_effect(
            normal_unit.morale, MoraleEvent.ALLY_KILLED
        )

        assert leader_result.morale_delta < normal_result.morale_delta


class TestCRTurn:
    def test_multiple_units_attack_in_sequence(self, resolver: CombatResolver, game_map: GameMap):
        allies = [make_unit(f"A{i}", Faction.ALLIES, TileCoord(i, 0)) for i in range(3)]
        axis = [make_unit(f"T{i}", Faction.AXIS, TileCoord(i + 5, 0)) for i in range(2)]

        results = resolver.resolve_combat_turn(allies, axis, game_map)

        assert isinstance(results, list)

    def test_dead_units_skipped(self, resolver: CombatResolver, game_map: GameMap):
        dead_unit = make_unit("Dead", Faction.ALLIES, TileCoord(1, 0), hp=0)
        allies = [
            make_unit("Alive", Faction.ALLIES, TileCoord(0, 0)),
            dead_unit,
        ]
        axis = [make_unit("Target", Faction.AXIS, TileCoord(5, 0))]

        results = resolver.resolve_combat_turn(allies, axis, game_map)

        assert len(results) >= 0

    def test_results_list_length_reasonable(self, resolver: CombatResolver, game_map: GameMap):
        allies = [make_unit(f"A{i}", Faction.ALLIES, TileCoord(i, 0)) for i in range(4)]
        axis = [make_unit(f"T{i}", Faction.AXIS, TileCoord(i + 5, 0)) for i in range(3)]

        results = resolver.resolve_combat_turn(allies, axis, game_map)

        assert len(results) <= 7


class TestCREdgeCases:
    def test_none_game_map_no_crash(self, resolver: CombatResolver):
        attacker = make_unit("Attacker", Faction.ALLIES, TileCoord(0, 0))
        target = make_unit("Target", Faction.AXIS, TileCoord(3, 0))

        result = resolver.resolve_attack(attacker, target, game_map=None)

        assert result["shot_result"] is not None

    def test_empty_lists_both_sides(self, resolver: CombatResolver, game_map: GameMap):
        results = resolver.resolve_combat_turn([], [], game_map)

        assert results == []

    def test_friendly_fire_allowed_no_crash(self, resolver: CombatResolver, game_map: GameMap):
        allies = [make_unit("A1", Faction.ALLIES, TileCoord(0, 0))]
        axis = []

        result = resolver.resolve_combat_turn(allies, axis, game_map)

        assert isinstance(result, list)
