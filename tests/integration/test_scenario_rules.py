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
        assert loop.state.game_map.is_passable(water) is True

    def test_bridge_destructible_flag(self):
        loop = self._stub_loop()
        GameLoop._apply_scenario_rules(loop, {"special_rules": ["bridge_destructible"]})
        assert loop._combat_director.bridge_destructible is True

        GameLoop._apply_scenario_rules(loop, {"special_rules": []})
        assert loop._combat_director.bridge_destructible is False


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
