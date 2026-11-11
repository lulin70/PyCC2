"""Integration tests for CC2 mechanics commands through the real EventBus."""

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
from pycc2.domain.value_objects.terrain_type import TerrainType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.infrastructure.events.event_bus import EventBus
from pycc2.infrastructure.events.event_protocol import PlayerCommand
from pycc2.services.combat_director import CombatDirector


def _make_unit(uid: str, faction: Faction, x: int, y: int) -> Unit:
    return Unit(
        id=uid,
        name=uid,
        faction=faction,
        unit_type=UnitType.INFANTRY_SQUAD,
        position=PositionComponent(tile_coord=TileCoord(x, y)),
        vision=VisionComponent(),
        health=HealthComponent(hp=100, max_hp=100),
        weapon=WeaponComponent(primary_weapon_id="rifle", max_ammo=120, ammo_remaining=120),
        morale=MoraleComponent(value=75),
    )


def _make_map(width: int = 6, height: int = 6) -> GameMap:
    grid = np.full((height, width), TerrainType.GRASS.value, dtype=np.int8)
    return GameMap(id="cc2_mech", name="CC2 Mech", width=width, height=height, tile_grid=grid)


def _make_director() -> tuple[CombatDirector, EventBus]:
    bus = EventBus()
    director = CombatDirector(event_bus=bus, display_config=object())
    director.initialize()
    return director, bus


@pytest.mark.integration
class TestCC2MechanicsThroughEventBus:
    """Commands must reach the director through PlayerCommand dispatch."""

    def test_build_bridge_command_creates_bridge(self):
        game_map = _make_map()
        game_map.set_terrain(TileCoord(2, 1), TerrainType.WATER)
        engineer = _make_unit("eng1", Faction.ALLIES, 1, 1)
        engineer.has_demolitions = True
        engineer.template_id = "us_engineer_squad"
        director, bus = _make_director()
        director.set_context([engineer], game_map)

        bus.publish(PlayerCommand(command="build_bridge", unit_ids=["eng1"]))

        assert game_map.get_terrain(TileCoord(2, 1)) == TerrainType.BRIDGE

    def test_air_strike_command_damages_enemy(self):
        game_map = _make_map(width=12, height=12)
        enemy = _make_unit("axis1", Faction.AXIS, 5, 5)
        director, bus = _make_director()
        director.set_context([enemy], game_map)

        bus.publish(PlayerCommand(command="air_strike", unit_ids=[], target=(5, 5)))

        assert enemy.health.hp == 55
        assert director._air_strikes_remaining == 2

    def test_air_strike_respects_scenario_limit(self):
        game_map = _make_map(width=12, height=12)
        enemy = _make_unit("axis1", Faction.AXIS, 5, 5)
        director, bus = _make_director()
        director.configure_air_support("limited")
        director.set_context([enemy], game_map)

        bus.publish(PlayerCommand(command="air_strike", unit_ids=[], target=(5, 5)))
        bus.publish(PlayerCommand(command="air_strike", unit_ids=[], target=(5, 5)))

        assert enemy.health.hp == 55
        assert director._air_strikes_remaining == 0
