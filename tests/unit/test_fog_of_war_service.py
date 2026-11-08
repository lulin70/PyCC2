"""Unit tests for ``FogOfWarService`` tick gating and observer selection."""

from __future__ import annotations

import numpy as np

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.services.fog_of_war_service import FogOfWarService


def make_map(width: int = 20, height: int = 20) -> GameMap:
    """Open terrain map with no LOS blockers."""
    grid = np.zeros((height, width), dtype=np.int8)
    return GameMap(id="fow", name="Fog Map", width=width, height=height, tile_grid=grid)


def make_unit(
    unit_id: str,
    faction: Faction,
    tile_x: int,
    tile_y: int,
    vision_range: int = 4,
    alive: bool = True,
) -> Unit:
    """Create a real unit with vision at the given tile."""
    unit = Unit(
        id=unit_id,
        name=unit_id,
        faction=faction,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=100, max_hp=100),
        morale=MoraleComponent(value=85),
        weapon=WeaponComponent(primary_weapon_id="rifle", max_ammo=10, ammo_remaining=10),
        position=PositionComponent(tile_coord=TileCoord(tile_x, tile_y)),
        vision=VisionComponent(range_tiles=vision_range),
    )
    if not alive:
        unit.take_damage(unit.health.max_hp)
    return unit


class TestTickGating:
    def test_non_update_tick_returns_false(self) -> None:
        service = FogOfWarService(20, 20)
        unit = make_unit("ally", Faction.ALLIES, 5, 5)
        assert service.update([unit], make_map(), 1) is False
        assert service.fog.is_hidden(TileCoord(5, 5))

    def test_update_on_multiple_of_five(self) -> None:
        service = FogOfWarService(20, 20)
        unit = make_unit("ally", Faction.ALLIES, 5, 5)
        game_map = make_map()
        assert service.update([unit], game_map, 0) is True
        assert service.fog.is_visible(TileCoord(5, 5))
        assert service.update([unit], game_map, 3) is False
        assert service.update([unit], game_map, 5) is True

    def test_same_tick_is_not_recomputed(self) -> None:
        service = FogOfWarService(20, 20)
        unit = make_unit("ally", Faction.ALLIES, 5, 5)
        game_map = make_map()
        assert service.update([unit], game_map, 0) is True
        assert service.update([unit], game_map, 0) is False


class TestFactionFilter:
    def test_enemy_faction_does_not_reveal(self) -> None:
        service = FogOfWarService(20, 20)
        enemy = make_unit("enemy", Faction.AXIS, 5, 5)
        game_map = make_map()
        assert service.update([enemy], game_map, 0) is True
        assert service.fog.is_hidden(TileCoord(5, 5))

    def test_dead_unit_does_not_reveal(self) -> None:
        service = FogOfWarService(20, 20)
        dead = make_unit("ally", Faction.ALLIES, 5, 5, alive=False)
        assert service.update([dead], make_map(), 0) is True
        assert service.fog.is_hidden(TileCoord(5, 5))


class TestEnableToggle:
    def test_disabled_service_does_not_update(self) -> None:
        service = FogOfWarService(20, 20, enabled=False)
        unit = make_unit("ally", Faction.ALLIES, 5, 5)
        assert service.update([unit], make_map(), 0) is False
        assert service.fog.is_hidden(TileCoord(5, 5))

    def test_toggle_flips_state(self) -> None:
        service = FogOfWarService(20, 20)
        assert service.toggle() is False
        assert service.enabled is False
        assert service.toggle() is True
        assert service.enabled is True

    def test_set_enabled(self) -> None:
        service = FogOfWarService(20, 20)
        service.set_enabled(False)
        assert service.enabled is False


class TestMultiObserver:
    def test_two_observers_reveal_union(self) -> None:
        service = FogOfWarService(20, 20)
        first = make_unit("ally1", Faction.ALLIES, 2, 2)
        second = make_unit("ally2", Faction.ALLIES, 17, 17)
        assert service.update([first, second], make_map(), 0) is True
        assert service.fog.is_visible(TileCoord(2, 2))
        assert service.fog.is_visible(TileCoord(17, 17))

    def test_second_observer_keeps_first_visibility(self) -> None:
        service = FogOfWarService(20, 20)
        first = make_unit("ally1", Faction.ALLIES, 2, 2)
        second = make_unit("ally2", Faction.ALLIES, 17, 17)
        assert service.update([first, second], make_map(), 0) is True
        # Reposition observers: the first stays, the second moves away.
        second.move_to_tile(TileCoord(15, 15))
        assert service.update([first, second], make_map(), 5) is True
        assert service.fog.is_visible(TileCoord(2, 2))
        assert service.fog.is_visible(TileCoord(15, 15))
