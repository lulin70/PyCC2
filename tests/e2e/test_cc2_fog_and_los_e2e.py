"""E2E: fog-of-war and LOS wired into gameplay.

Simulates a real play session on a 64x64 map: a walled shot is rejected
without cost, vision follows a moving unit while explored ground persists,
and the fog overlay darkens only the tiles that are not currently visible.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_JOYSTICK_DRIVER", "dummy")

import pygame

pygame.init()

import numpy as np
import pytest

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.interfaces.display_config import DisplayConfig
from pycc2.domain.systems.los_system import LOSSystem
from pycc2.domain.value_objects.terrain_type import TerrainType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.infrastructure.events.event_bus import EventBus
from pycc2.infrastructure.events.event_protocol import UnitAttacked
from pycc2.presentation.rendering.camera import Camera
from pycc2.presentation.rendering.render_context import RenderContext
from pycc2.presentation.rendering.ui_overlay_renderer import UIOverlayRenderer
from pycc2.services.combat_director import CombatDirector
from pycc2.services.fog_of_war_service import FogOfWarService

MAP_SIZE = 64


def make_map(walls: tuple[tuple[int, int], ...] = ()) -> GameMap:
    """64x64 open map with optional wall tiles."""
    grid = np.zeros((MAP_SIZE, MAP_SIZE), dtype=np.int8)
    for x, y in walls:
        grid[y][x] = TerrainType.WALL.value
    return GameMap(id="e2e", name="E2E Map", width=MAP_SIZE, height=MAP_SIZE, tile_grid=grid)


def make_unit(unit_id: str, faction: Faction, tile_x: int, tile_y: int) -> Unit:
    """Create a ready-to-fire unit with vision."""
    return Unit(
        id=unit_id,
        name=unit_id,
        faction=faction,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=100, max_hp=100),
        morale=MoraleComponent(value=85),
        weapon=WeaponComponent(primary_weapon_id="rifle", max_ammo=120, ammo_remaining=120),
        position=PositionComponent(tile_coord=TileCoord(tile_x, tile_y)),
        vision=VisionComponent(range_tiles=6),
    )


@pytest.mark.e2e
class TestCombatLosE2E:
    def test_wall_blocks_shot_then_clear_line_fires(self) -> None:
        game_map = make_map(walls=((22, 20),))
        bus = EventBus()
        attacked: list = []
        bus.subscribe(UnitAttacked, attacked.append)

        director = CombatDirector(event_bus=bus, display_config=DisplayConfig())
        director.initialize()
        director.set_los_system(LOSSystem(game_map))

        blocked_attacker = make_unit("ally_blocked", Faction.ALLIES, 20, 20)
        blocked_target = make_unit("enemy_blocked", Faction.AXIS, 25, 20)
        director.set_context([blocked_attacker, blocked_target], game_map)

        director.execute_attack(blocked_attacker, blocked_target)

        assert blocked_attacker.weapon.ammo_remaining == 120
        assert blocked_target.health.hp == 100
        assert attacked == []

        clear_attacker = make_unit("ally_clear", Faction.ALLIES, 20, 30)
        clear_target = make_unit("enemy_clear", Faction.AXIS, 23, 30)
        director.set_context([clear_attacker, clear_target], game_map)

        director.execute_attack(clear_attacker, clear_target)

        # A clear line fires (the ballistic engine may fire internally on a
        # hit, so only require that ammo was consumed).
        assert clear_attacker.weapon.ammo_remaining < 120
        assert len(attacked) == 1
        assert attacked[0]["attacker_id"] == "ally_clear"


@pytest.mark.e2e
class TestFogOfWarE2E:
    def test_vision_follows_unit_and_explored_persists(self) -> None:
        game_map = make_map()
        service = FogOfWarService(MAP_SIZE, MAP_SIZE)
        scout = make_unit("scout", Faction.ALLIES, 10, 10)

        assert service.update([scout], game_map, 0) is True
        assert service.fog.is_visible(TileCoord(10, 10))

        scout.move_to_tile(TileCoord(40, 40))
        assert service.update([scout], game_map, 5) is True

        assert service.fog.is_visible(TileCoord(40, 40))
        assert service.fog.is_explored(TileCoord(10, 10))
        assert not service.fog.is_visible(TileCoord(10, 10))

    def test_fog_overlay_skips_uninitialized_grid(self) -> None:
        """Before the first visibility pass the overlay must not black out the map."""
        fog = FogOfWarService(MAP_SIZE, MAP_SIZE).fog
        surface = pygame.Surface((800, 600))
        surface.fill((255, 255, 255))
        camera = Camera(
            position=Vec2(30 * 32 + 16.0, 30 * 32 + 16.0),
            viewport_width=800,
            viewport_height=600,
        )
        overlay = UIOverlayRenderer(RenderContext(tile_size=32))
        overlay.draw_fog_of_war(surface, fog, camera)
        assert surface.get_at((400, 300))[:3] == (255, 255, 255)

    def test_fog_overlay_darkens_hidden_tiles_only(self) -> None:
        game_map = make_map()
        service = FogOfWarService(MAP_SIZE, MAP_SIZE)
        scout = make_unit("scout", Faction.ALLIES, 30, 30)
        assert service.update([scout], game_map, 0) is True

        surface = pygame.Surface((800, 600))
        surface.fill((255, 255, 255))
        camera = Camera(
            position=Vec2(30 * 32 + 16.0, 30 * 32 + 16.0),
            viewport_width=800,
            viewport_height=600,
        )
        overlay = UIOverlayRenderer(RenderContext(tile_size=32))
        overlay.draw_fog_of_war(surface, service.fog, camera)

        # Visible tile (30, 30) stays bright at screen centre.
        visible_pixel = surface.get_at((400, 300))
        assert visible_pixel[:3] == (255, 255, 255)
        # Hidden tile (40, 30) sits at screen x=720 and must be darkened.
        hidden_pixel = surface.get_at((720, 300))
        assert hidden_pixel[0] < 80
