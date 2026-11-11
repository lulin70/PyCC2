"""Tests for scenario special rules and bridge demolition (P1-5)."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.scenario_rules import ScenarioRules
from pycc2.domain.value_objects.terrain_type import TerrainType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.presentation.ui.deployment_models import ZoneType
from pycc2.presentation.ui.deployment_placement import DeploymentPlacementService
from pycc2.services.combat_director import CombatDirector
from pycc2.services.game_loop import GameLoop


class _StubEventBus:
    def subscribe(self, event_type, handler):
        pass

    def publish(self, event):
        pass


class _StubGameTime:
    def __init__(self) -> None:
        self.hour: float | None = None

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


def _unit(x: int = 0, y: int = 0, has_demolitions: bool = False) -> Unit:
    unit = Unit(
        id="u1",
        name="Engineer",
        faction=Faction.ALLIES,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=100, max_hp=100),
        morale=MoraleComponent(value=80),
        weapon=WeaponComponent(primary_weapon_id="rifle", max_ammo=120, ammo_remaining=120),
        position=PositionComponent(tile_coord=TileCoord(x, y)),
        vision=VisionComponent(),
    )
    unit.has_demolitions = has_demolitions
    return unit


def _placement_service() -> DeploymentPlacementService:
    ui = SimpleNamespace(
        _airdrop_deployment=False,
        _zone_map=[[ZoneType.NO_MANS_LAND] * 10 for _ in range(10)],
        _map_width=10,
        _map_height=10,
    )
    return DeploymentPlacementService(ui)


class TestScenarioRulesParsing:
    def test_parse_list(self):
        rules = ScenarioRules.from_map_data({"special_rules": ["night_fighting", "amphibious"]})
        assert rules.has("night_fighting")
        assert rules.has("NIGHT_FIGHTING")
        assert not rules.has("airdrop_deployment")

    def test_parse_string(self):
        rules = ScenarioRules.from_map_data({"special_rules": "night_fighting"})
        assert rules.has("night_fighting")

    def test_parse_dict_keeps_truthy_keys(self):
        rules = ScenarioRules.from_map_data(
            {"special_rules": {"amphibious": True, "bridge_destructible": False}}
        )
        assert rules.has("amphibious")
        assert not rules.has("bridge_destructible")

    def test_missing_rules_yield_empty_set(self):
        assert ScenarioRules.from_map_data({}).rules == frozenset()


class TestApplyScenarioRules:
    def _stub_loop(self):
        return SimpleNamespace(
            _game_time=_StubGameTime(),
            state=SimpleNamespace(game_map=_map()),
            _combat_director=CombatDirector(event_bus=_StubEventBus(), display_config=object()),
        )

    def test_night_fighting_sets_night_clock(self):
        loop = self._stub_loop()
        GameLoop._apply_scenario_rules(loop, {"special_rules": ["night_fighting"]})
        assert loop._game_time.hour == 22.0

    def test_amphibious_allows_water(self):
        loop = self._stub_loop()
        water = TileCoord(2, 2)
        loop.state.game_map.set_terrain(water, TerrainType.WATER)
        assert loop.state.game_map.is_passable(water) is False

        GameLoop._apply_scenario_rules(loop, {"special_rules": ["amphibious"]})
        amphibious = SimpleNamespace(is_amphibious=True)
        foot = SimpleNamespace(is_amphibious=False)
        assert loop.state.game_map.is_passable(water) is False
        assert loop.state.game_map.is_passable_for(water, amphibious) is True
        assert loop.state.game_map.is_passable_for(water, foot) is False

    def test_bridge_destructible_flag(self):
        loop = self._stub_loop()
        GameLoop._apply_scenario_rules(loop, {"special_rules": ["bridge_destructible"]})
        assert loop._combat_director.bridge_destructible is True

        GameLoop._apply_scenario_rules(loop, {"special_rules": []})
        assert loop._combat_director.bridge_destructible is False

    def test_air_support_level_configures_director(self):
        loop = self._stub_loop()
        GameLoop._apply_scenario_rules(loop, {"special_rules": ["limited_air_support"]})
        assert loop.state.air_support_level == "limited"
        assert loop._combat_director._air_strikes_remaining == 1

        GameLoop._apply_scenario_rules(loop, {"special_rules": ["no_air_support"]})
        assert loop._combat_director._air_strikes_remaining == 0


class TestAirdropPlacement:
    def test_neutral_zone_blocked_by_default(self):
        service = _placement_service()
        unit = SimpleNamespace()
        assert service.can_place_at(unit, 1, 1, int(TerrainType.OPEN)) is False

    def test_airdrop_allows_neutral_zone(self):
        service = _placement_service()
        service._ui._airdrop_deployment = True
        unit = SimpleNamespace()
        assert service.can_place_at(unit, 1, 1, int(TerrainType.OPEN)) is True

    def test_airdrop_still_blocks_water(self):
        service = _placement_service()
        service._ui._airdrop_deployment = True
        unit = SimpleNamespace()
        assert service.can_place_at(unit, 1, 1, int(TerrainType.WATER)) is False


class TestBridgeDemolition:
    def _director(self, bridge_destructible: bool = True) -> CombatDirector:
        return CombatDirector(
            event_bus=_StubEventBus(),
            display_config=object(),
            bridge_destructible=bridge_destructible,
        )

    def test_engineer_destroys_adjacent_bridge(self):
        game_map = _map()
        bridge = TileCoord(6, 5)
        game_map.set_terrain(bridge, TerrainType.BRIDGE)
        unit = _unit(5, 5, has_demolitions=True)
        director = self._director()

        director.handle_player_command(
            {"command": "demolish", "unit_ids": ["u1"]}, [unit], game_map
        )

        assert game_map.get_terrain(bridge) == TerrainType.BRIDGE_DESTROYED

    def test_unit_without_demolitions_leaves_bridge(self):
        game_map = _map()
        bridge = TileCoord(6, 5)
        game_map.set_terrain(bridge, TerrainType.BRIDGE)
        unit = _unit(5, 5, has_demolitions=False)

        self._director().handle_player_command(
            {"command": "demolish", "unit_ids": ["u1"]}, [unit], game_map
        )

        assert game_map.get_terrain(bridge) == TerrainType.BRIDGE

    def test_scenario_disables_demolition(self):
        game_map = _map()
        bridge = TileCoord(6, 5)
        game_map.set_terrain(bridge, TerrainType.BRIDGE)
        unit = _unit(5, 5, has_demolitions=True)

        self._director(bridge_destructible=False).handle_player_command(
            {"command": "demolish", "unit_ids": ["u1"]}, [unit], game_map
        )

        assert game_map.get_terrain(bridge) == TerrainType.BRIDGE


class _RecordingReinforcementService:
    def __init__(self) -> None:
        self.kwargs: dict | None = None

    def update(self, **kwargs):
        self.kwargs = kwargs
        return []


class TestPF12RuleConsumers:
    """Every special rule must change runtime state (PF-12)."""

    def _objective(self, oid: str) -> SimpleNamespace:
        return SimpleNamespace(
            id=oid,
            name=oid,
            position=(2, 2),
            radius=1,
            required=True,
            owner=None,
            points=10,
        )

    def _loop(
        self,
        rules: list[str],
        units: list[Unit],
        objectives: list | None = None,
        owners: dict | None = None,
        air: str = "full",
        decay: float = 1.0,
    ) -> SimpleNamespace:
        game_map = _map()
        game_map.objectives = objectives or []
        loop = SimpleNamespace(
            state=SimpleNamespace(
                game_map=game_map,
                units=units,
                air_support_level=air,
                tick=0,
            ),
            _scenario_rules=ScenarioRules.from_map_data({"special_rules": rules}),
            _victory_manager=SimpleNamespace(get_vl_owners=lambda: owners or {}),
            _scenario_data={
                "spawn_points": [
                    {"side": "allies", "position": [0, 0]},
                    {"side": "axis", "position": [19, 19]},
                ]
            },
            _logistics_counter=59,
            _supply_decay=decay,
            _combined_arms_counter=0,
            _reinforcement_service=None,
            _deployment_manager=None,
        )
        loop._matching_vl_ids = lambda *needles: GameLoop._matching_vl_ids(loop, *needles)
        loop._vl_owner_map = lambda: GameLoop._vl_owner_map(loop)
        return loop

    def _ammo_unit(self, faction=Faction.ALLIES, x: int = 1, y: int = 1) -> Unit:
        return Unit(
            id=f"u_{faction.name}_{x}_{y}",
            name="Rifle",
            faction=faction,
            unit_type=UnitType.INFANTRY_SQUAD,
            health=HealthComponent(hp=100, max_hp=100),
            morale=MoraleComponent(value=80),
            weapon=WeaponComponent(
                primary_weapon_id="rifle",
                max_ammo=120,
                ammo_remaining=120,
                reserve_ammo=200,
            ),
            position=PositionComponent(tile_coord=TileCoord(x, y)),
            vision=VisionComponent(),
        )

    def test_supply_dwindling_stops_resupply(self):
        unit = self._ammo_unit()
        loop = self._loop(["supply_dwindling"], [unit], decay=0.0)
        GameLoop._update_logistics(loop)
        assert unit.weapon.reserve_ammo == 200

    def test_supply_dwindling_decays_factor(self):
        unit = self._ammo_unit()
        loop = self._loop(["supply_dwindling"], [unit], decay=1.0)
        GameLoop._update_logistics(loop)
        assert unit.weapon.reserve_ammo == 212
        assert loop._supply_decay == 0.85

    def test_corridor_lost_blocks_resupply(self):
        unit = self._ammo_unit()
        loop = self._loop(
            ["corridor_must_remain_open"],
            [unit],
            objectives=[self._objective("vl_corridor")],
            owners={"vl_corridor": "axis"},
        )
        GameLoop._update_logistics(loop)
        assert unit.weapon.reserve_ammo == 200

    def test_corridor_held_keeps_resupply(self):
        unit = self._ammo_unit()
        loop = self._loop(
            ["corridor_must_remain_open"],
            [unit],
            objectives=[self._objective("vl_corridor")],
            owners={"vl_corridor": "allies"},
        )
        GameLoop._update_logistics(loop)
        assert unit.weapon.reserve_ammo == 212

    def test_no_air_support_blocks_allied_resupply(self):
        ally = self._ammo_unit()
        axis = self._ammo_unit(Faction.AXIS, 19, 18)
        loop = self._loop(["no_air_support"], [ally, axis], air="none")
        GameLoop._update_logistics(loop)
        assert ally.weapon.reserve_ammo == 200
        assert axis.weapon.reserve_ammo == 212

    def test_limited_air_support_halves_resupply(self):
        ally = self._ammo_unit()
        loop = self._loop(["limited_air_support"], [ally], air="limited")
        GameLoop._update_logistics(loop)
        assert ally.weapon.reserve_ammo == 206

    def test_lz_rule_blocks_allied_reinforcements(self):
        service = _RecordingReinforcementService()
        loop = self._loop(
            ["lz_must_hold_for_reinforcements"],
            [],
            objectives=[self._objective("vl_lz")],
            owners={"vl_lz": "axis"},
        )
        loop._reinforcement_service = service
        loop._deployment_manager = SimpleNamespace(create_reinforcement_unit=lambda **kw: None)
        GameLoop._update_reinforcements(loop)
        assert service.kwargs["allowed_sides"] == {"axis"}

    def test_lz_held_allows_all_reinforcements(self):
        service = _RecordingReinforcementService()
        loop = self._loop(
            ["lz_must_hold_for_reinforcements"],
            [],
            objectives=[self._objective("vl_lz")],
            owners={"vl_lz": "allies"},
        )
        loop._reinforcement_service = service
        loop._deployment_manager = SimpleNamespace(create_reinforcement_unit=lambda **kw: None)
        GameLoop._update_reinforcements(loop)
        assert service.kwargs["allowed_sides"] is None

    def test_limited_reinforcements_caps_side(self):
        service = _RecordingReinforcementService()
        loop = self._loop(["limited_reinforcements"], [])
        loop._reinforcement_service = service
        loop._deployment_manager = SimpleNamespace(create_reinforcement_unit=lambda **kw: None)
        GameLoop._update_reinforcements(loop)
        assert service.kwargs["max_per_side"] == 2

    def test_fanatic_defenders_raise_axis_morale(self):
        axis = self._ammo_unit(Faction.AXIS, 19, 18)
        ally = self._ammo_unit()
        axis.morale.value = 5
        ally.morale.value = 5
        loop = self._loop(["fanatic_defenders"], [axis, ally])
        GameLoop._update_scenario_effects(loop)
        assert axis.morale.value == 30
        assert ally.morale.value == 5

    def test_combined_arms_bonus_near_armor(self):
        infantry = self._ammo_unit()
        tank = Unit(
            id="tank",
            name="Tank",
            faction=Faction.ALLIES,
            unit_type=UnitType.TANK,
            health=HealthComponent(hp=100, max_hp=100),
            morale=MoraleComponent(value=80),
            weapon=WeaponComponent(primary_weapon_id="cannon", max_ammo=40, ammo_remaining=40),
            position=PositionComponent(tile_coord=TileCoord(7, 5)),
            vision=VisionComponent(),
        )
        infantry.position.tile_coord = TileCoord(5, 5)
        loop = self._loop(["combined_arms_bonus"], [infantry, tank])
        for _ in range(30):
            GameLoop._update_scenario_effects(loop)
        assert infantry.scenario_accuracy_mod == 1.10
        assert tank.scenario_accuracy_mod == 1.10

    def test_combined_arms_bonus_absent_when_unsupported(self):
        infantry = self._ammo_unit()
        loop = self._loop(["combined_arms_bonus"], [infantry])
        for _ in range(30):
            GameLoop._update_scenario_effects(loop)
        assert infantry.scenario_accuracy_mod == 1.0

    def test_fortified_positions_cover_bonus(self):
        axis = self._ammo_unit(Faction.AXIS, 19, 18)
        ally = self._ammo_unit()
        loop = self._loop(["fortified_positions"], [axis, ally])
        GameLoop._apply_scenario_start_effects(loop)
        assert axis.scenario_cover_mod == 0.75
        assert ally.scenario_cover_mod == 1.0

    def test_initial_scatter_moves_units(self):
        first = self._ammo_unit(x=5, y=5)
        second = self._ammo_unit(Faction.AXIS, 15, 15)
        loop = self._loop(["initial_scatter"], [first, second])
        GameLoop._apply_scenario_start_effects(loop)
        assert (first.position.tile_coord.x, first.position.tile_coord.y) != (5, 5)
        assert (second.position.tile_coord.x, second.position.tile_coord.y) != (15, 15)
        assert first.position.tile_coord != second.position.tile_coord

    def test_must_hold_all_vls_draws_when_one_vl_lost(self):
        from pycc2.domain.systems.victory_conditions import (
            GameResult,
            Objective,
            VictoryConditionType,
        )
        from pycc2.domain.systems.victory_conditions import (
            VictoryConditionEvaluator as Evaluator,
        )

        evaluator = Evaluator(
            conditions=[VictoryConditionType.OCCUPY_OBJECTIVE],
            objectives=[
                Objective(id="vl1", name="VL1", position=(2, 2), radius=1, points=50),
                Objective(id="vl2", name="VL2", position=(15, 15), radius=1, points=50),
            ],
            time_limit_ticks=10,
        )
        evaluator.require_all_vls = True
        ally = self._ammo_unit(x=2, y=2)
        axis = self._ammo_unit(Faction.AXIS, 15, 15)
        result, reason = evaluator.evaluate([ally, axis], tick=10)
        assert result == GameResult.DRAW
        assert "not all VLs" in reason

    def test_must_hold_all_vls_wins_when_all_held(self):
        from pycc2.domain.systems.victory_conditions import (
            GameResult,
            Objective,
            VictoryConditionType,
        )
        from pycc2.domain.systems.victory_conditions import (
            VictoryConditionEvaluator as Evaluator,
        )

        evaluator = Evaluator(
            conditions=[VictoryConditionType.OCCUPY_OBJECTIVE],
            objectives=[Objective(id="vl1", name="VL1", position=(2, 2), radius=1, points=50)],
            time_limit_ticks=10,
        )
        evaluator.require_all_vls = True
        ally = self._ammo_unit(x=2, y=2)
        axis = self._ammo_unit(Faction.AXIS, 18, 18)
        result, _ = evaluator.evaluate([ally, axis], tick=10)
        assert result == GameResult.ALLIES_VICTORY
