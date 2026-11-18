"""Unit tests for MC2-04 ``ContactMemory`` (docs/MC2_WAVE2_DESIGN_20261118.md §4).

Covers the design table: ghost recording (VISIBLE units are not recorded, a
visible→invisible transition pins the last sighting), expiry after
CONTACT_DECAY_TICKS, clear(), and observer-faction isolation. Real ``FogOfWar``
grids and real ``Unit`` objects drive every case.
"""

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
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.services.contact_memory import CONTACT_DECAY_TICKS, ContactMemory, UnitContact
from pycc2.services.fog_of_war_service import FogOfWarService


def make_map(width: int = 20, height: int = 20) -> GameMap:
    """Open terrain map with no LOS blockers."""
    grid = np.zeros((height, width), dtype=np.int8)
    return GameMap(id="cm", name="Contact Map", width=width, height=height, tile_grid=grid)


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


def observe_tick(
    memory: ContactMemory,
    service: FogOfWarService,
    units: list[Unit],
    game_map: GameMap,
    tick: int,
) -> bool:
    """Drive one fog update + contact observe at ``tick`` (game-loop rhythm)."""
    updated = service.update(units, game_map, tick)
    if updated:
        memory.observe(units, service.fog, tick, service.faction)
    return updated


@pytest.mark.unit
class TestConstants:
    def test_default_decay_is_600_ticks(self):
        assert CONTACT_DECAY_TICKS == 600
        assert ContactMemory.CONTACT_DECAY_TICKS == 600

    def test_custom_decay_ticks(self):
        memory = ContactMemory(decay_ticks=100)
        assert memory.ghosts("ALLIES") == []


@pytest.mark.unit
class TestGhostLifecycle:
    def test_visible_unit_is_not_recorded(self):
        memory = ContactMemory()
        service = FogOfWarService(20, 20)
        ally = make_unit("ally", Faction.ALLIES, 5, 5)
        enemy = make_unit("enemy", Faction.AXIS, 7, 5)
        game_map = make_map()

        observe_tick(memory, service, [ally, enemy], game_map, 10)

        assert memory.ghosts("ALLIES") == []
        assert service.fog.is_visible(TileCoord(7, 5))

    def test_leaving_vision_pins_ghost_at_last_sighting(self):
        memory = ContactMemory()
        service = FogOfWarService(20, 20)
        ally = make_unit("ally", Faction.ALLIES, 5, 5)
        enemy = make_unit("enemy", Faction.AXIS, 7, 5)
        game_map = make_map()

        observe_tick(memory, service, [ally, enemy], game_map, 10)
        enemy.move_to_tile(TileCoord(18, 18))
        observe_tick(memory, service, [ally, enemy], game_map, 15)

        ghosts = memory.ghosts("ALLIES")
        assert len(ghosts) == 1
        ghost = ghosts[0]
        assert isinstance(ghost, UnitContact)
        assert ghost.unit_id == "enemy"
        assert ghost.faction == "AXIS"
        assert ghost.last_seen_tile == (7, 5)
        assert ghost.last_seen_tick == 10

    def test_ghost_tile_tracks_last_seen_position(self):
        memory = ContactMemory()
        service = FogOfWarService(20, 20)
        ally = make_unit("ally", Faction.ALLIES, 5, 5)
        enemy = make_unit("enemy", Faction.AXIS, 7, 5)
        game_map = make_map()

        observe_tick(memory, service, [ally, enemy], game_map, 10)
        enemy.move_to_tile(TileCoord(8, 5))  # still visible
        observe_tick(memory, service, [ally, enemy], game_map, 15)
        enemy.move_to_tile(TileCoord(18, 18))  # leaves vision
        observe_tick(memory, service, [ally, enemy], game_map, 20)

        ghosts = memory.ghosts("ALLIES")
        assert len(ghosts) == 1
        assert ghosts[0].last_seen_tile == (8, 5)
        assert ghosts[0].last_seen_tick == 15

    def test_reacquired_unit_drops_ghost(self):
        memory = ContactMemory()
        service = FogOfWarService(20, 20)
        ally = make_unit("ally", Faction.ALLIES, 5, 5)
        enemy = make_unit("enemy", Faction.AXIS, 7, 5)
        game_map = make_map()

        observe_tick(memory, service, [ally, enemy], game_map, 10)
        enemy.move_to_tile(TileCoord(18, 18))
        observe_tick(memory, service, [ally, enemy], game_map, 15)
        assert len(memory.ghosts("ALLIES")) == 1

        enemy.move_to_tile(TileCoord(6, 5))  # back inside vision
        observe_tick(memory, service, [ally, enemy], game_map, 20)
        assert memory.ghosts("ALLIES") == []

    def test_never_seen_unit_leaves_no_ghost(self):
        memory = ContactMemory()
        service = FogOfWarService(20, 20)
        ally = make_unit("ally", Faction.ALLIES, 5, 5)
        far_enemy = make_unit("far", Faction.AXIS, 18, 18)
        game_map = make_map()

        observe_tick(memory, service, [ally, far_enemy], game_map, 10)
        far_enemy.move_to_tile(TileCoord(19, 19))
        observe_tick(memory, service, [ally, far_enemy], game_map, 15)

        assert memory.ghosts("ALLIES") == []


@pytest.mark.unit
class TestDecay:
    def _pin_ghost(self) -> tuple[ContactMemory, GameMap, Unit, Unit]:
        memory = ContactMemory()
        service = FogOfWarService(20, 20)
        ally = make_unit("ally", Faction.ALLIES, 5, 5)
        enemy = make_unit("enemy", Faction.AXIS, 7, 5)
        game_map = make_map()
        observe_tick(memory, service, [ally, enemy], game_map, 10)
        enemy.move_to_tile(TileCoord(18, 18))
        observe_tick(memory, service, [ally, enemy], game_map, 15)
        return memory, game_map, ally, enemy

    def test_ghost_alive_before_decay(self):
        memory, game_map, ally, enemy = self._pin_ghost()
        # last_seen_tick=10 → alive while now - 10 <= 600
        assert len(memory.ghosts("ALLIES", tick=610)) == 1

    def test_ghost_expired_after_decay_window(self):
        memory, game_map, ally, enemy = self._pin_ghost()
        assert memory.ghosts("ALLIES", tick=611) == []

    def test_observe_prunes_expired_ghosts(self):
        memory, game_map, ally, enemy = self._pin_ghost()
        observe_tick(
            memory,
            service=FogOfWarService(20, 20),
            units=[ally, enemy],
            game_map=game_map,
            tick=700,
        )
        assert memory.ghosts("ALLIES") == []

    def test_custom_decay_window(self):
        memory = ContactMemory(decay_ticks=50)
        service = FogOfWarService(20, 20)
        ally = make_unit("ally", Faction.ALLIES, 5, 5)
        enemy = make_unit("enemy", Faction.AXIS, 7, 5)
        game_map = make_map()
        observe_tick(memory, service, [ally, enemy], game_map, 10)
        enemy.move_to_tile(TileCoord(18, 18))
        observe_tick(memory, service, [ally, enemy], game_map, 15)
        assert len(memory.ghosts("ALLIES", tick=60)) == 1
        assert memory.ghosts("ALLIES", tick=61) == []


@pytest.mark.unit
class TestClear:
    def test_clear_drops_all_ghosts(self):
        memory = ContactMemory()
        service = FogOfWarService(20, 20)
        ally = make_unit("ally", Faction.ALLIES, 5, 5)
        enemy = make_unit("enemy", Faction.AXIS, 7, 5)
        game_map = make_map()
        observe_tick(memory, service, [ally, enemy], game_map, 10)
        enemy.move_to_tile(TileCoord(18, 18))
        observe_tick(memory, service, [ally, enemy], game_map, 15)
        assert len(memory.ghosts("ALLIES")) == 1

        memory.clear()
        assert memory.ghosts("ALLIES") == []

    def test_clear_forgets_sightings(self):
        """After clear(), an invisible unit is unknown again — no ghost revives."""
        memory = ContactMemory()
        service = FogOfWarService(20, 20)
        ally = make_unit("ally", Faction.ALLIES, 5, 5)
        enemy = make_unit("enemy", Faction.AXIS, 7, 5)
        game_map = make_map()
        observe_tick(memory, service, [ally, enemy], game_map, 10)

        memory.clear()
        enemy.move_to_tile(TileCoord(18, 18))
        observe_tick(memory, service, [ally, enemy], game_map, 20)
        assert memory.ghosts("ALLIES") == []


@pytest.mark.unit
class TestFactionIsolation:
    def test_observer_tables_are_isolated(self):
        memory = ContactMemory()
        allies_fog = FogOfWarService(20, 20, faction=Faction.ALLIES)
        axis_fog = FogOfWarService(20, 20, faction=Faction.AXIS)
        game_map = make_map()
        ally = make_unit("ally", Faction.ALLIES, 5, 5)
        enemy = make_unit("enemy", Faction.AXIS, 7, 5)

        # Each side sees the other's unit once (tick 10), then both sides lose
        # sight at tick 15.
        observe_tick(memory, allies_fog, [ally, enemy], game_map, 10)
        observe_tick(memory, axis_fog, [ally, enemy], game_map, 10)
        ally.move_to_tile(TileCoord(18, 2))
        enemy.move_to_tile(TileCoord(2, 18))
        observe_tick(memory, allies_fog, [ally, enemy], game_map, 15)
        observe_tick(memory, axis_fog, [ally, enemy], game_map, 15)

        allies_ghosts = memory.ghosts("ALLIES")
        axis_ghosts = memory.ghosts("AXIS")
        assert [g.unit_id for g in allies_ghosts] == ["enemy"]
        assert [g.unit_id for g in axis_ghosts] == ["ally"]
        assert allies_ghosts[0].faction == "AXIS"
        assert axis_ghosts[0].faction == "ALLIES"

    def test_unknown_faction_has_no_ghosts(self):
        memory = ContactMemory()
        service = FogOfWarService(20, 20)
        ally = make_unit("ally", Faction.ALLIES, 5, 5)
        enemy = make_unit("enemy", Faction.AXIS, 7, 5)
        game_map = make_map()
        observe_tick(memory, service, [ally, enemy], game_map, 10)
        enemy.move_to_tile(TileCoord(18, 18))
        observe_tick(memory, service, [ally, enemy], game_map, 15)

        assert memory.ghosts("AXIS") == []

    def test_enum_and_string_observer_keys_match(self):
        memory = ContactMemory()
        service = FogOfWarService(20, 20)
        ally = make_unit("ally", Faction.ALLIES, 5, 5)
        enemy = make_unit("enemy", Faction.AXIS, 7, 5)
        game_map = make_map()
        observe_tick(memory, service, [ally, enemy], game_map, 10)
        enemy.move_to_tile(TileCoord(18, 18))
        observe_tick(memory, service, [ally, enemy], game_map, 15)

        assert memory.ghosts(Faction.ALLIES) == memory.ghosts("ALLIES")


@pytest.mark.unit
class TestDeadUnits:
    def test_visible_unit_dying_leaves_no_ghost(self):
        memory = ContactMemory()
        service = FogOfWarService(20, 20)
        ally = make_unit("ally", Faction.ALLIES, 5, 5)
        enemy = make_unit("enemy", Faction.AXIS, 7, 5)
        game_map = make_map()
        observe_tick(memory, service, [ally, enemy], game_map, 10)

        enemy.take_damage(enemy.health.max_hp)
        observe_tick(memory, service, [ally, enemy], game_map, 15)
        assert memory.ghosts("ALLIES") == []

    def test_ghosted_unit_dying_drops_ghost(self):
        memory = ContactMemory()
        service = FogOfWarService(20, 20)
        ally = make_unit("ally", Faction.ALLIES, 5, 5)
        enemy = make_unit("enemy", Faction.AXIS, 7, 5)
        game_map = make_map()
        observe_tick(memory, service, [ally, enemy], game_map, 10)
        enemy.move_to_tile(TileCoord(18, 18))
        observe_tick(memory, service, [ally, enemy], game_map, 15)
        assert len(memory.ghosts("ALLIES")) == 1

        enemy.take_damage(enemy.health.max_hp)
        observe_tick(memory, service, [ally, enemy], game_map, 20)
        assert memory.ghosts("ALLIES") == []
