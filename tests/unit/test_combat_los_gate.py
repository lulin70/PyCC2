"""Unit tests for the LOS gate in ``CombatDirector.execute_attack``.

Verifies that a blocked line of sight cancels the shot entirely: no ammo is
consumed, no ``UnitAttacked`` event is published, and the target takes no
damage. Also verifies shots still resolve when no LOS system is injected or
when the line is clear.
"""

from __future__ import annotations

import numpy as np

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.interfaces.display_config import DisplayConfig
from pycc2.domain.systems.ballistic import ShotResult
from pycc2.domain.systems.los_system import LOSSystem
from pycc2.domain.value_objects.terrain_type import TerrainType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.services.combat_director import CombatDirector

# ===========================================================================
# Helpers
# ===========================================================================


class RecordingEventBus:
    """Event bus stub that records every published event."""

    def __init__(self) -> None:
        self.events: list = []

    def subscribe(self, event_type, handler) -> None:
        pass

    def publish(self, event) -> None:
        self.events.append(event)

    def publish_named(self, name, data) -> None:
        self.events.append({"name": name, "data": data})

    def attacked_events(self) -> list:
        return [e for e in self.events if isinstance(e, dict) and "attacker_id" in e]


class FixedDamageBallistic:
    """Ballistic stub that always hits for a fixed damage amount."""

    def calculate_shot(self, attacker, target, game_map=None) -> ShotResult:
        return ShotResult(hit=True, damage_dealt=10.0)


def make_map(wall: tuple[int, int] | None = None) -> GameMap:
    """20x20 open map, optionally with a single wall tile."""
    grid = np.zeros((20, 20), dtype=np.int8)
    if wall is not None:
        grid[wall[1]][wall[0]] = TerrainType.WALL.value
    return GameMap(id="los_gate", name="LOS Gate", width=20, height=20, tile_grid=grid)


def make_unit(
    unit_id: str,
    faction: Faction,
    tile_x: int,
    tile_y: int,
    max_ammo: int = 120,
) -> Unit:
    """Create a real unit with ready weapon, vision, and health."""
    return Unit(
        id=unit_id,
        name=unit_id,
        faction=faction,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=100, max_hp=100),
        morale=MoraleComponent(value=85),
        weapon=WeaponComponent(
            primary_weapon_id="rifle",
            max_ammo=max_ammo,
            ammo_remaining=max_ammo,
        ),
        position=PositionComponent(tile_coord=TileCoord(tile_x, tile_y)),
        vision=VisionComponent(),
    )


def make_director(bus: RecordingEventBus) -> CombatDirector:
    """Create an initialized director with a deterministic ballistic engine."""
    director = CombatDirector(event_bus=bus, display_config=DisplayConfig())
    director.initialize()
    director.ballistic_engine = FixedDamageBallistic()
    return director


# ===========================================================================
# Tests
# ===========================================================================


class TestLosGate:
    def test_no_los_system_shot_resolves(self) -> None:
        bus = RecordingEventBus()
        director = make_director(bus)
        game_map = make_map()
        attacker = make_unit("ally1", Faction.ALLIES, 5, 5)
        target = make_unit("enemy1", Faction.AXIS, 8, 5)
        director.set_context([attacker, target], game_map)

        director.execute_attack(attacker, target)

        assert attacker.weapon.ammo_remaining == 119
        assert target.health.hp == 90
        attacked = bus.attacked_events()
        assert len(attacked) == 1
        assert attacked[0]["attacker_id"] == "ally1"
        assert attacked[0]["damage"] == 10.0

    def test_wall_blocks_shot_without_cost(self) -> None:
        bus = RecordingEventBus()
        director = make_director(bus)
        game_map = make_map(wall=(6, 5))
        director.set_los_system(LOSSystem(game_map))
        attacker = make_unit("ally1", Faction.ALLIES, 5, 5)
        target = make_unit("enemy1", Faction.AXIS, 8, 5)
        director.set_context([attacker, target], game_map)

        director.execute_attack(attacker, target)

        assert attacker.weapon.ammo_remaining == 120
        assert target.health.hp == 100
        assert bus.attacked_events() == []
        assert not any(
            e.get("name") == "ProjectileFired" for e in bus.events if isinstance(e, dict)
        )

    def test_clear_los_shot_resolves(self) -> None:
        bus = RecordingEventBus()
        director = make_director(bus)
        game_map = make_map()
        director.set_los_system(LOSSystem(game_map))
        attacker = make_unit("ally1", Faction.ALLIES, 5, 5)
        target = make_unit("enemy1", Faction.AXIS, 8, 5)
        director.set_context([attacker, target], game_map)

        director.execute_attack(attacker, target)

        assert attacker.weapon.ammo_remaining == 119
        assert target.health.hp == 90
        assert len(bus.attacked_events()) == 1
