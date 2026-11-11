"""End-to-end checks for the CC2 mechanics additions.

Simulates a real user flow: issue PlayerCommand events, then verify the
simulation reacts through the real EventBus and CombatDirector.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

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


def _make_unit(uid: str, faction: Faction, x: int, y: int, hp: int = 100) -> Unit:
    return Unit(
        id=uid,
        name=uid,
        faction=faction,
        unit_type=UnitType.INFANTRY_SQUAD,
        position=PositionComponent(tile_coord=TileCoord(x, y)),
        vision=VisionComponent(),
        health=HealthComponent(hp=hp, max_hp=hp),
        weapon=WeaponComponent(primary_weapon_id="rifle", max_ammo=120, ammo_remaining=120),
        morale=MoraleComponent(value=75),
    )


def _make_river_map(width: int = 3, height: int = 3) -> GameMap:
    grid = np.full((height, width), TerrainType.GRASS.value, dtype=np.int8)
    grid[1, :] = TerrainType.WATER.value
    game_map = GameMap(id="river", name="River", width=width, height=height, tile_grid=grid)
    game_map.amphibious_passable = True
    return game_map


def _make_director(units: list[Unit], game_map: GameMap) -> tuple[CombatDirector, EventBus]:
    bus = EventBus()
    director = CombatDirector(event_bus=bus, display_config=object())
    director.initialize()
    director.set_context(units, game_map)
    return director, bus


@pytest.mark.e2e
class TestCC2MechanicsE2E:
    """Real command flow: EventBus -> CombatDirector -> unit state."""

    def test_amphibious_unit_crosses_river_by_move_command(self):
        game_map = _make_river_map()
        amphibious = _make_unit("amph", Faction.ALLIES, 1, 0)
        amphibious.is_amphibious = True
        director, bus = _make_director([amphibious], game_map)

        bus.publish(PlayerCommand(command="move", unit_ids=["amph"], target=(1, 2)))

        assert "amph" in director._move_orders
        path = list(director._move_orders["amph"]["path"])
        assert any(game_map.get_terrain(coord) == TerrainType.WATER for coord in path)

    def test_foot_unit_cannot_cross_river(self):
        game_map = _make_river_map()
        foot = _make_unit("foot", Faction.ALLIES, 1, 0)
        director, bus = _make_director([foot], game_map)

        bus.publish(PlayerCommand(command="move", unit_ids=["foot"], target=(1, 2)))

        assert "foot" not in director._move_orders

    def test_air_strike_damages_axis_unit_and_spends_one_sortie(self):
        game_map = GameMap(
            id="flat",
            name="Flat",
            width=12,
            height=12,
            tile_grid=np.full((12, 12), TerrainType.GRASS.value, dtype=np.int8),
        )
        enemy = _make_unit("axis1", Faction.AXIS, 5, 5)
        director, bus = _make_director([enemy], game_map)

        bus.publish(PlayerCommand(command="air_strike", unit_ids=[], target=(5, 5)))

        assert enemy.health.hp == 55
        assert director._air_strikes_remaining == 2
