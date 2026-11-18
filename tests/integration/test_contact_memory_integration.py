"""Integration tests for MC2-04 contact ghosts (docs/MC2_WAVE2_DESIGN_20261118.md §4).

Covers the design table:
- fog 更新后残影生成与衰减: the real ``GameLoopUpdatingMixin._update_fog_of_war``
  hook drives fog + contact memory; ticks advance 600+ and ghosts expire.
- ghost 渲染不崩（dummy 驱动): ``UIOverlayRenderer.draw_contact_ghosts`` and the
  full ``EnhancedRenderer.render`` pipeline draw alpha-90 outlines headlessly.
- reset hooks: mission start (``start_deployment``) and save load
  (``quick_load``) clear the contact table.

Stub loops follow the SimpleNamespace convention of
test_trigger_migration_integration.py; rendering uses the shared
``pygame_display`` fixture from tests/conftest.py.
"""

from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

# Headless pygame (must precede any pygame import)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_JOYSTICK_DRIVER", "dummy")

import numpy as np
import pygame

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.presentation.rendering.camera import Camera
from pycc2.presentation.rendering.render_context import RenderContext
from pycc2.presentation.rendering.ui_overlay_renderer import UIOverlayRenderer
from pycc2.services.contact_memory import ContactMemory
from pycc2.services.fog_of_war_service import FogOfWarService
from pycc2.services.game_loop import GameLoop
from pycc2.services.game_loop_updating import GameLoopUpdatingMixin

MAP_SIZE = 20


def make_map(width: int = MAP_SIZE, height: int = MAP_SIZE) -> GameMap:
    grid = np.zeros((height, width), dtype=np.int8)
    return GameMap(id="cmi", name="Contact Map", width=width, height=height, tile_grid=grid)


def make_unit(unit_id: str, faction: Faction, tile_x: int, tile_y: int) -> Unit:
    return Unit(
        id=unit_id,
        name=unit_id,
        faction=faction,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=100, max_hp=100),
        morale=MoraleComponent(value=85),
        weapon=WeaponComponent(primary_weapon_id="rifle", max_ammo=10, ammo_remaining=10),
        position=PositionComponent(tile_coord=TileCoord(tile_x, tile_y)),
        vision=VisionComponent(range_tiles=4),
    )


def make_stub_loop(service, memory, units, game_map, tick=0):
    """Minimal loop stub carrying exactly what _update_fog_of_war touches."""
    return SimpleNamespace(
        state=SimpleNamespace(units=units, game_map=game_map, tick=tick),
        _deployment_manager=None,
        _fog_of_war_service=service,
        _contact_memory=memory,
    )


class RecordingMemory:
    """ContactMemory stand-in recording clear() calls for hook tests."""

    def __init__(self) -> None:
        self.clear_calls = 0

    def clear(self) -> None:
        self.clear_calls += 1


@pytest.fixture
def ghost_screen(pygame_display):
    """Fresh display surface per test.

    The session-scoped ``pygame_display`` screen can be quit by another test's
    cleanup (e.g. window_manager.shutdown). Re-calling set_mode restores a live
    display surface (same pattern as test_rendering_pipeline.py).
    """
    try:
        screen = pygame.display.set_mode((640, 480))
    except pygame.error:
        screen = pygame.Surface((640, 480), pygame.SRCALPHA)
    yield screen


@pytest.mark.integration
class TestFogDrivenGhostFlow:
    def test_ghost_appears_when_enemy_leaves_vision(self):
        service = FogOfWarService(MAP_SIZE, MAP_SIZE)
        memory = ContactMemory()
        ally = make_unit("ally", Faction.ALLIES, 5, 5)
        enemy = make_unit("enemy", Faction.AXIS, 7, 5)
        game_map = make_map()
        loop = make_stub_loop(service, memory, [ally, enemy], game_map, tick=0)

        GameLoopUpdatingMixin._update_fog_of_war(loop)
        assert memory.ghosts("ALLIES") == []

        enemy.move_to_tile(TileCoord(18, 18))
        loop.state.tick = 5
        GameLoopUpdatingMixin._update_fog_of_war(loop)

        ghosts = memory.ghosts("ALLIES")
        assert len(ghosts) == 1
        assert ghosts[0].unit_id == "enemy"
        assert ghosts[0].last_seen_tile == (7, 5)
        assert ghosts[0].last_seen_tick == 0

    def test_ghost_decays_after_600_ticks(self):
        service = FogOfWarService(MAP_SIZE, MAP_SIZE)
        memory = ContactMemory()
        ally = make_unit("ally", Faction.ALLIES, 5, 5)
        enemy = make_unit("enemy", Faction.AXIS, 7, 5)
        game_map = make_map()
        loop = make_stub_loop(service, memory, [ally, enemy], game_map, tick=0)

        GameLoopUpdatingMixin._update_fog_of_war(loop)
        enemy.move_to_tile(TileCoord(18, 18))
        loop.state.tick = 5
        GameLoopUpdatingMixin._update_fog_of_war(loop)
        assert len(memory.ghosts("ALLIES")) == 1

        for tick in range(10, 601, 5):
            loop.state.tick = tick
            GameLoopUpdatingMixin._update_fog_of_war(loop)
            assert len(memory.ghosts("ALLIES")) == 1, f"ghost lost early at tick {tick}"

        loop.state.tick = 615
        GameLoopUpdatingMixin._update_fog_of_war(loop)
        assert memory.ghosts("ALLIES") == []

    def test_stub_loop_without_contact_memory_does_not_crash(self):
        """getattr guard: stub loops without _contact_memory keep working."""
        service = FogOfWarService(MAP_SIZE, MAP_SIZE)
        ally = make_unit("ally", Faction.ALLIES, 5, 5)
        game_map = make_map()
        loop = SimpleNamespace(
            state=SimpleNamespace(units=[ally], game_map=game_map, tick=0),
            _deployment_manager=None,
            _fog_of_war_service=service,
        )

        GameLoopUpdatingMixin._update_fog_of_war(loop)  # must not raise
        assert service.fog.is_visible(TileCoord(5, 5))

    def test_fog_service_none_returns_early(self):
        loop = SimpleNamespace(
            state=SimpleNamespace(units=[], game_map=None, tick=0),
            _deployment_manager=None,
            _fog_of_war_service=None,
            _contact_memory=ContactMemory(),
        )
        GameLoopUpdatingMixin._update_fog_of_war(loop)  # must not raise


@pytest.mark.integration
class TestGhostRendering:
    def _ghost_memory(self) -> ContactMemory:
        service = FogOfWarService(MAP_SIZE, MAP_SIZE)
        memory = ContactMemory()
        ally = make_unit("ally", Faction.ALLIES, 5, 5)
        enemy = make_unit("enemy", Faction.AXIS, 7, 5)
        game_map = make_map()
        service.update([ally, enemy], game_map, 10)
        memory.observe([ally, enemy], service.fog, 10, service.faction)
        enemy.move_to_tile(TileCoord(18, 18))
        service.update([ally], game_map, 15)
        memory.observe([ally, enemy], service.fog, 15, service.faction)
        return memory

    def test_ghost_outline_drawn_with_alpha_90(self, pygame_display):
        memory = self._ghost_memory()
        ghosts = memory.ghosts("ALLIES")
        assert len(ghosts) == 1

        surface = pygame.Surface((640, 480))
        surface.fill((255, 255, 255))
        # Camera centred on the ghost tile (7, 5): its screen rect is
        # (304, 224, 32, 32) with tile_size 32 and zoom 1.0.
        camera = Camera(
            position=Vec2(7 * 32 + 16.0, 5 * 32 + 16.0), viewport_width=640, viewport_height=480
        )
        overlay = UIOverlayRenderer(RenderContext(tile_size=32))

        overlay.draw_contact_ghosts(surface, ghosts, camera)

        # Ghost outline blends with the white background at alpha 90
        # (axis red → reddish tint); the tile interior stays background.
        assert overlay.GHOST_ALPHA == 90
        edge = surface.get_at((320, 224))
        assert edge[0] > edge[1] and edge[0] > edge[2], "ghost outline pixel must tint red"
        centre = surface.get_at((320, 240))
        assert centre[:3] == (255, 255, 255), "outline only — tile interior stays background"

    def test_no_ghosts_leaves_surface_untouched(self, pygame_display):
        surface = pygame.Surface((640, 480))
        surface.fill((255, 255, 255))
        camera = Camera(position=Vec2(256.0, 256.0), viewport_width=640, viewport_height=480)
        overlay = UIOverlayRenderer(RenderContext(tile_size=32))

        overlay.draw_contact_ghosts(surface, [], camera)
        assert surface.get_at((320, 240))[:3] == (255, 255, 255)

    def test_expired_ghost_is_not_drawn(self, pygame_display):
        memory = self._ghost_memory()
        surface = pygame.Surface((640, 480))
        surface.fill((255, 255, 255))
        camera = Camera(
            position=Vec2(7 * 32 + 16.0, 5 * 32 + 16.0), viewport_width=640, viewport_height=480
        )
        overlay = UIOverlayRenderer(RenderContext(tile_size=32))

        overlay.draw_contact_ghosts(surface, memory.ghosts("ALLIES", tick=10_000), camera)
        assert surface.get_at((320, 224))[:3] == (255, 255, 255)

    def test_render_query_is_read_only(self, pygame_display):
        memory = self._ghost_memory()
        before = len(memory.ghosts("ALLIES"))
        surface = pygame.Surface((640, 480))
        camera = Camera(position=Vec2(256.0, 256.0), viewport_width=640, viewport_height=480)
        overlay = UIOverlayRenderer(RenderContext(tile_size=32))

        overlay.draw_contact_ghosts(surface, memory.ghosts("ALLIES"), camera)

        assert len(memory.ghosts("ALLIES")) == before

    def test_full_render_pipeline_with_ghosts_does_not_crash(self, ghost_screen):
        from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer

        renderer = EnhancedRenderer()
        renderer.initialize(ghost_screen)
        renderer.set_contact_memory(self._ghost_memory(), "ALLIES")

        units = [make_unit("ally", Faction.ALLIES, 5, 5)]
        renderer.render(
            game_map=make_map(),
            units=units,
            camera=Camera(position=Vec2(240.0, 176.0), viewport_width=640, viewport_height=480),
            alpha=1.0,
            selected_unit_ids=set(),
            debug_mode=False,
            paused=False,
            tick=15,
        )

    def test_set_contact_memory_stores_observer(self, pygame_display):
        from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer

        renderer = EnhancedRenderer()
        memory = ContactMemory()
        renderer.set_contact_memory(memory, "AXIS")
        assert renderer._contact_memory is memory
        assert renderer._contact_observer_faction == "AXIS"


@pytest.mark.integration
class TestResetHooks:
    def test_start_deployment_clears_contacts(self):
        memory = RecordingMemory()
        loop = SimpleNamespace(
            _deployment_manager=SimpleNamespace(start=Mock()),
            _scenario_data={},
            _apply_scenario_weather=lambda map_data: None,
            _apply_scenario_rules=lambda map_data: None,
            _contact_memory=memory,
            display_config=None,
            _deployment_ui_factory=lambda width, height: None,
            tutorial_overlay=None,
        )

        GameLoop.start_deployment(loop, map_data={"width": 10, "height": 10}, faction="allied")

        assert memory.clear_calls == 1

    def test_quick_load_clears_contacts_on_success(self):
        memory = RecordingMemory()
        loop = SimpleNamespace(
            _save_controller=SimpleNamespace(quick_load=Mock(return_value=True)),
            _victory_manager=None,
            _contact_memory=memory,
        )

        assert GameLoop.quick_load(loop, slot=0) is True
        assert memory.clear_calls == 1

    def test_quick_load_failure_keeps_contacts(self):
        memory = RecordingMemory()
        loop = SimpleNamespace(
            _save_controller=SimpleNamespace(quick_load=Mock(return_value=False)),
            _victory_manager=None,
            _contact_memory=memory,
        )

        assert GameLoop.quick_load(loop, slot=0) is False
        assert memory.clear_calls == 0

    def test_hooks_tolerate_missing_contact_memory(self):
        """getattr guard: stub loops without _contact_memory keep working."""
        loop = SimpleNamespace(
            _deployment_manager=SimpleNamespace(start=Mock()),
            _scenario_data={},
            _apply_scenario_weather=lambda map_data: None,
            _apply_scenario_rules=lambda map_data: None,
            display_config=None,
            _deployment_ui_factory=lambda width, height: None,
            tutorial_overlay=None,
        )
        GameLoop.start_deployment(loop, map_data={}, faction="allied")  # must not raise

        load_loop = SimpleNamespace(
            _save_controller=SimpleNamespace(quick_load=Mock(return_value=True)),
            _victory_manager=None,
        )
        assert GameLoop.quick_load(load_loop, slot=0) is True
