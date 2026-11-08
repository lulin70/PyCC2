"""Acceptance tests for CC2 parity (G1-G3 + W5 mechanisms).

Each test exercises a user-visible rule through the runtime entry point.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.squad import MemberState, Squad, SquadType
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.systems.ballistic import BallisticEngine
from pycc2.domain.systems.fog_of_war import FogOfWar, TileVisibility
from pycc2.domain.systems.los_system import LOSSystem
from pycc2.domain.systems.victory_conditions import (
    GameResult,
    Objective,
    VictoryConditionEvaluator,
    VictoryConditionType,
)
from pycc2.domain.systems.weather_effects import WeatherEffects, WeatherState, WeatherType
from pycc2.domain.value_objects.ammo_type import AmmoType
from pycc2.domain.value_objects.terrain_type import TerrainType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.presentation.ui.deployment_models import ZoneType
from pycc2.presentation.ui.deployment_placement import DeploymentPlacementService
from pycc2.services.combat_director import CombatDirector
from pycc2.services.game_loop import GameLoop
from pycc2.services.game_loop_updating import GameLoopUpdatingMixin
from pycc2.services.reinforcement_service import ReinforcementService


class _FixedRng:
    def uniform(self, low: float, high: float) -> float:
        return (low + high) / 2.0

    def gaussian(self, mu: float, sigma: float) -> float:
        return mu


class _EventBus:
    def __init__(self) -> None:
        self.published: list[object] = []

    def subscribe(self, event_type, handler):
        pass

    def publish(self, event):
        self.published.append(event)

    def publish_named(self, name, data):
        self.published.append({"name": name, "data": data})


class _GameTime:
    def __init__(self) -> None:
        self.hour = 12.0

    def set_time(self, hour: float) -> None:
        self.hour = hour


def _map(width: int = 20, height: int = 20) -> GameMap:
    return GameMap(
        id="test",
        name="Test Map",
        width=width,
        height=height,
        tile_grid=np.zeros((height, width), dtype=np.int8),
    )


def _unit(
    unit_id: str = "u1",
    faction: Faction = Faction.ALLIES,
    unit_type: UnitType = UnitType.INFANTRY_SQUAD,
    weapon_id: str = "rifle",
    x: int = 0,
    y: int = 0,
    hp: int = 100,
) -> Unit:
    return Unit(
        id=unit_id,
        name=unit_id,
        faction=faction,
        unit_type=unit_type,
        health=HealthComponent(hp=hp, max_hp=100),
        morale=MoraleComponent(value=80),
        weapon=WeaponComponent(primary_weapon_id=weapon_id, max_ammo=20, ammo_remaining=20),
        position=PositionComponent(tile_coord=TileCoord(x, y)),
        vision=VisionComponent(),
    )


def _squad_unit() -> Unit:
    squad = Squad(
        squad_id="u1",
        squad_type=SquadType.RIFLE_SQUAD,
        faction="allies",
        initial_size=10,
    )
    unit = _unit()
    unit.squad_ref = squad
    return unit


def _director() -> CombatDirector:
    director = CombatDirector(event_bus=_EventBus(), display_config=object())
    director.ballistic_engine = BallisticEngine(rng=_FixedRng())
    return director


# ---------------------------------------------------------------------------
# G1: line of sight
# ---------------------------------------------------------------------------


def test_g1_wall_blocks_line_of_sight():
    game_map = _map()
    game_map.set_terrain(TileCoord(1, 0), TerrainType.WALL)

    assert game_map.has_line_of_sight(TileCoord(0, 0), TileCoord(2, 0)) is False
    assert game_map.has_line_of_sight(TileCoord(0, 0), TileCoord(0, 3)) is True


# ---------------------------------------------------------------------------
# G2: fog of war three states
# ---------------------------------------------------------------------------


def test_g2_fog_has_hidden_explored_visible_states():
    game_map = _map(10, 10)
    fog = FogOfWar(10, 10)

    fog.update_visibility(
        observer_pos=TileCoord(0, 0),
        vision_range=3,
        vision_angle=360.0,
        facing_direction=0.0,
        game_map=game_map,
    )

    assert fog.is_visible(TileCoord(0, 0)) is True
    assert fog.get_visibility(TileCoord(9, 9)) == TileVisibility.HIDDEN

    fog.clear_current_visibility()

    assert fog.is_visible(TileCoord(0, 0)) is False
    assert fog.is_explored(TileCoord(0, 0)) is True


# ---------------------------------------------------------------------------
# G3: four victory conditions
# ---------------------------------------------------------------------------


def test_g3_elimination_victory():
    allies = _unit("a1", Faction.ALLIES)
    axis = _unit("x1", Faction.AXIS, x=10, hp=0)
    evaluator = VictoryConditionEvaluator(conditions=[VictoryConditionType.ELIMINATE_ALL_ENEMIES])

    result, _ = evaluator.evaluate([allies, axis], tick=600)

    assert result == GameResult.ALLIES_VICTORY


def test_g3_vl_capture_victory():
    objective = Objective(id="vl1", name="Bridge", position=(5, 5), radius=1)
    allies = _unit("a1", Faction.ALLIES, x=5, y=5)
    axis = _unit("x1", Faction.AXIS, x=15, y=15)
    evaluator = VictoryConditionEvaluator(
        conditions=[VictoryConditionType.OCCUPY_OBJECTIVE],
        objectives=[objective],
    )

    result, _ = evaluator.evaluate([allies, axis], tick=100)

    assert result == GameResult.ALLIES_VICTORY


def test_g3_time_limit_victory():
    held = Objective(id="vl1", name="Bridge", position=(5, 5), radius=1, points=100)
    enemy = Objective(id="vl2", name="Church", position=(15, 15), radius=1, points=100)
    allies = _unit("a1", Faction.ALLIES, x=5, y=5)
    axis = _unit("x1", Faction.AXIS, x=10, y=0)
    evaluator = VictoryConditionEvaluator(
        conditions=[VictoryConditionType.OCCUPY_OBJECTIVE, VictoryConditionType.TIME_LIMIT],
        objectives=[held, enemy],
        time_limit_ticks=100,
    )

    assert evaluator.evaluate([allies, axis], tick=50)[0] == GameResult.ONGOING
    assert evaluator.evaluate([allies, axis], tick=100)[0] == GameResult.ALLIES_VICTORY


def test_g3_morale_collapse_victory():
    allies = _unit("a1", Faction.ALLIES)
    axis = _unit("x1", Faction.AXIS, x=10)
    allies.morale.value = 80
    axis.morale.value = 10
    evaluator = VictoryConditionEvaluator(
        conditions=[VictoryConditionType.FORCE_MORALE_COLLAPSE],
        force_morale_threshold=40,
    )

    result, _ = evaluator.evaluate([allies, axis], tick=100)

    assert result == GameResult.ALLIES_VICTORY


# ---------------------------------------------------------------------------
# W5 mechanisms
# ---------------------------------------------------------------------------


def test_mechanism_squad_casualties_reduce_accuracy():
    wounded = _squad_unit()
    for member in wounded.squad_ref.members:
        member.state = MemberState.WOUNDED
        member.hp = 35

    target = _unit("t1", Faction.AXIS, x=3)
    engine = BallisticEngine(rng=_FixedRng())
    healthy_unit = _squad_unit()

    healthy_shot = engine.calculate_shot(healthy_unit, target)
    wounded_shot = engine.calculate_shot(wounded, target)

    assert wounded_shot.actual_accuracy < healthy_shot.actual_accuracy


def test_mechanism_damage_maps_to_squad_members():
    unit = _squad_unit()

    unit.take_damage(50)

    assert unit.squad_ref.wounded_count == 5
    assert unit.squad_effectiveness < 1.0


def test_mechanism_suppression_pins_members(monkeypatch):
    monkeypatch.setattr("pycc2.domain.entities.squad.random.random", lambda: 0.0)
    unit = _squad_unit()

    pinned = unit.apply_squad_suppression(1.0)

    assert pinned == unit.squad_ref.size
    assert unit.squad_ref.pinned_count == pinned


def test_mechanism_reinforcements_arrive_by_turn():
    scenario = {
        "spawn_points": [{"side": "allies", "position": [0, 0]}],
        "forces": {
            "allies": {
                "reinforcements": [
                    {"template_id": "uk_rifle_section", "arrival_turn": 2, "from_direction": "west"}
                ]
            }
        },
    }
    service = ReinforcementService.from_scenario(scenario)
    units: list[Unit] = []

    def factory(template_id, faction, position, counter):
        return _unit(f"reinforce_{counter}", faction, x=position[0], y=position[1])

    assert service.update(899, units, _map(), factory) == []
    spawned = service.update(900, units, _map(), factory)

    assert len(spawned) == 1
    assert len(units) == 1


def test_mechanism_empty_magazine_triggers_reload():
    unit = _unit()
    unit.weapon.ammo_remaining = 0
    unit.weapon.reserve_ammo = 50
    unit.weapon.fire()  # Moves the weapon into OUT_OF_AMMO.
    director = _director()

    director.update([unit], _map(), 0.033)
    assert unit.weapon.is_reloading is True

    for _ in range(91):
        director.update([unit], _map(), 0.033)

    assert unit.weapon.ammo_remaining == unit.weapon.max_ammo


def test_mechanism_logistics_restores_reserve():
    unit = _unit(x=1, y=1)
    unit.weapon.reserve_ammo = 10
    loop = SimpleNamespace(
        _logistics_counter=59,
        _scenario_data={"spawn_points": [{"side": "allies", "position": [0, 0]}]},
        state=SimpleNamespace(units=[unit]),
    )

    GameLoopUpdatingMixin._update_logistics(loop)

    assert unit.weapon.reserve_ammo > 10


def test_mechanism_fog_reduces_los():
    game_map = _map()
    los = LOSSystem(game_map, weather_effects=WeatherEffects())
    start, end = TileCoord(0, 0), TileCoord(10, 0)

    los.set_weather(WeatherType.CLEAR)
    assert los.check_los(start, end)[0] is True
    los.set_weather(WeatherType.FOG)
    assert los.check_los(start, end)[0] is False


def test_mechanism_rain_reduces_accuracy():
    game_map = _map()
    attacker = _unit()
    target = _unit("t1", Faction.AXIS, x=5)
    engine = BallisticEngine(rng=_FixedRng())
    game_map.weather_state = WeatherState(weather_type=WeatherType.CLEAR)
    clear_shot = engine.calculate_shot(attacker, target, game_map=game_map)
    game_map.weather_state = WeatherState(weather_type=WeatherType.RAIN)
    rain_shot = engine.calculate_shot(attacker, target, game_map=game_map)

    assert rain_shot.actual_accuracy < clear_shot.actual_accuracy


def test_mechanism_night_fighting_sets_clock():
    loop = SimpleNamespace(
        _game_time=_GameTime(),
        state=SimpleNamespace(game_map=_map()),
        _combat_director=_director(),
    )

    GameLoop._apply_scenario_rules(loop, {"special_rules": ["night_fighting"]})

    assert loop._game_time.hour == 22.0


def test_mechanism_airdrop_allows_deployment():
    ui = SimpleNamespace(
        _airdrop_deployment=True,
        _zone_map=[[ZoneType.NO_MANS_LAND] * 10 for _ in range(10)],
        _map_width=10,
        _map_height=10,
    )
    service = DeploymentPlacementService(ui)

    assert service.can_place_at(SimpleNamespace(), 1, 1, int(TerrainType.OPEN)) is True


def test_mechanism_engineer_destroys_bridge():
    game_map = _map()
    bridge = TileCoord(6, 5)
    game_map.set_terrain(bridge, TerrainType.BRIDGE)
    engineer = _unit(x=5, y=5)
    engineer.has_demolitions = True

    _director().handle_player_command(
        {"command": "demolish", "unit_ids": ["u1"]}, [engineer], game_map
    )

    assert game_map.get_terrain(bridge) == TerrainType.BRIDGE_DESTROYED


def test_mechanism_amphibious_allows_water():
    game_map = _map()
    water = TileCoord(2, 2)
    game_map.set_terrain(water, TerrainType.WATER)
    loop = SimpleNamespace(
        _game_time=_GameTime(),
        state=SimpleNamespace(game_map=game_map),
        _combat_director=_director(),
    )

    assert game_map.is_passable(water) is False
    GameLoop._apply_scenario_rules(loop, {"special_rules": ["amphibious"]})
    assert game_map.is_passable(water) is True


def test_mechanism_ap_he_changes_damage():
    engine = BallisticEngine(rng=_FixedRng())

    def shot(ammo: AmmoType, target: Unit) -> float:
        attacker = _unit(weapon_id="tank_cannon", unit_type=UnitType.TANK)
        attacker.weapon.ammo_type = ammo
        result = engine.calculate_shot(attacker, target)
        assert result.hit is True
        return result.damage_dealt

    infantry = _unit("i1", Faction.AXIS, x=3)
    vehicle = _unit("v1", Faction.AXIS, unit_type=UnitType.TANK, x=3)

    assert shot(AmmoType.HE, infantry) > shot(AmmoType.AP, infantry)
    assert shot(AmmoType.AP, vehicle) > shot(AmmoType.HE, vehicle)


def test_mechanism_fire_mode_gates_shots():
    attacker = _unit()
    target = _unit("t1", Faction.AXIS, x=3)
    attacker.fire_mode = "hold"
    director = _director()

    director.execute_attack(attacker, target)

    assert attacker.weapon.ammo_remaining == 20


def test_mechanism_kill_grants_experience():
    from pycc2.domain.components.veterancy_component import VeterancyComponent
    from pycc2.domain.systems.victory_conditions import BattleStats

    attacker = _unit("a1", Faction.ALLIES)
    attacker.veterancy = VeterancyComponent()
    target = _unit("x1", Faction.AXIS, x=3, hp=0)
    stats = BattleStats()

    _director().record_stats(
        {"attacker_id": "a1", "target_id": "x1", "damage": 100, "killed": True},
        [attacker, target],
        stats,
    )

    assert attacker.veterancy.kills == 1
    assert attacker.veterancy.xp > 0


def test_mechanism_turret_turns_independently_of_hull():
    tank = _unit("tk1", Faction.ALLIES, UnitType.TANK, weapon_id="tank_cannon")
    tank.position.facing_rad = 0.0  # Hull faces East
    target = _unit("tg1", Faction.AXIS, x=0, y=5)  # Target is to the South

    _director().execute_attack(tank, target)

    assert tank.position.facing_rad == 0.0  # Hull does not rotate
    assert tank.turret_facing is not None
    assert abs(tank.turret_facing - 270.0) < 1.0  # Turret faces South


def test_mechanism_crew_wipe_abandons_vehicle():
    tank = _unit("tk2", Faction.ALLIES, UnitType.TANK, weapon_id="tank_cannon")
    assert tank.crew is not None

    for _ in range(6):
        tank.apply_crew_damage(1000)
        if tank.crew_abandoned:
            break

    assert tank.is_abandoned is True
    assert tank.is_alive is False


def test_mechanism_mortar_fires_with_friendly_observer():
    game_map = _map()
    game_map.set_terrain(TileCoord(1, 0), TerrainType.WALL)  # Blocks mortar LOS
    mortar = _unit("m1", Faction.ALLIES, UnitType.MORTAR_TEAM, weapon_id="mortar")
    target = _unit("t1", Faction.AXIS, x=3, y=0)
    observer = _unit("o1", Faction.ALLIES, x=5, y=0)

    director = _director()
    director.set_context([mortar, observer], game_map)
    director.set_los_system(LOSSystem(game_map))
    director.execute_attack(mortar, target)

    assert mortar.weapon.ammo_remaining < 20  # Shot was fired


def test_mechanism_mortar_waits_without_observer():
    game_map = _map()
    game_map.set_terrain(TileCoord(1, 0), TerrainType.WALL)
    mortar = _unit("m2", Faction.ALLIES, UnitType.MORTAR_TEAM, weapon_id="mortar")
    target = _unit("t2", Faction.AXIS, x=3, y=0)

    director = _director()
    director.set_context([mortar], game_map)
    director.set_los_system(LOSSystem(game_map))
    director.execute_attack(mortar, target)

    assert mortar.weapon.ammo_remaining == 20  # Shot was cancelled
