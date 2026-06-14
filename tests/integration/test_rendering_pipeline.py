"""Integration tests: Rendering pipeline.

Tests that EnhancedRenderer and SpriteRenderer work together,
terrain textures render without crashing, unit sprites exist for
key types, attack lines render, and combat effect proxy methods exist.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np
import pygame
import pytest

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
from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer
from pycc2.presentation.rendering.sprite_renderer import SpriteRenderer

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def pygame_screen():
    """Create a pygame surface for headless rendering."""
    pygame.init()
    try:
        screen = pygame.display.set_mode((800, 600))
    except pygame.error:
        screen = pygame.Surface((800, 600), pygame.SRCALPHA)
    yield screen
    pygame.quit()


@pytest.fixture
def game_map():
    grid = np.zeros((16, 16), dtype=np.int8)
    return GameMap(id="test", name="Test Map", width=16, height=16, tile_grid=grid)


@pytest.fixture
def mixed_terrain_map():
    """Map with various terrain types for texture rendering tests."""
    grid = np.zeros((16, 16), dtype=np.int8)
    # Row 0-3: open (0)
    # Row 4-7: road (1)
    grid[4:8, :] = 1
    # Row 8-11: woods (3)
    grid[8:12, :] = 3
    # Row 12-15: water (6)
    grid[12:16, :] = 6
    return GameMap(id="mixed", name="Mixed Map", width=16, height=16, tile_grid=grid)


@pytest.fixture
def camera():
    return Camera(position=Vec2(256.0, 256.0), viewport_width=800, viewport_height=600)


@pytest.fixture
def ally_unit():
    return Unit(
        id="ally_1",
        name="Ally Unit",
        faction=Faction.ALLIES,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=100, max_hp=100),
        morale=MoraleComponent(value=85),
        weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=10, max_ammo=10),
        position=PositionComponent(tile_coord=TileCoord(3, 3)),
        vision=VisionComponent(range_tiles=5),
    )


@pytest.fixture
def enhanced_renderer(pygame_screen):
    renderer = EnhancedRenderer()
    renderer.initialize(pygame_screen)
    return renderer


@pytest.fixture
def sprite_renderer():
    return SpriteRenderer()


# ── Tests ─────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestEnhancedRendererWithSpriteRenderer:
    def test_enhanced_renderer_initializes(self, enhanced_renderer):
        """EnhancedRenderer should initialize without crashing."""
        assert enhanced_renderer._screen is not None

    def test_sprite_renderer_in_enhanced_renderer(self, enhanced_renderer):
        """EnhancedRenderer should have a SpriteRenderer after initialization."""
        # SpriteRenderer may or may not initialize depending on display availability
        # but the attribute should exist
        assert hasattr(enhanced_renderer, "_sprite_renderer")

    def test_render_does_not_crash(self, enhanced_renderer, game_map, camera, ally_unit):
        """Full render call should not crash."""
        enhanced_renderer.render(
            game_map=game_map,
            units=[ally_unit],
            camera=camera,
        )

    def test_render_with_selection(self, enhanced_renderer, game_map, camera, ally_unit):
        """Rendering with selected units should not crash."""
        enhanced_renderer.render(
            game_map=game_map,
            units=[ally_unit],
            camera=camera,
            selected_unit_ids={"ally_1"},
        )

    def test_render_empty_units(self, enhanced_renderer, game_map, camera):
        """Rendering with no units should not crash."""
        enhanced_renderer.render(
            game_map=game_map,
            units=[],
            camera=camera,
        )


@pytest.mark.integration
class TestTerrainTextureRendering:
    def test_render_open_terrain(self, enhanced_renderer, game_map, camera):
        """Rendering open terrain (type 0) should not crash."""
        enhanced_renderer.render(game_map=game_map, units=[], camera=camera)

    def test_render_mixed_terrain(self, enhanced_renderer, mixed_terrain_map, camera):
        """Rendering mixed terrain types should not crash."""
        enhanced_renderer.render(game_map=mixed_terrain_map, units=[], camera=camera)

    def test_render_road_terrain(self, enhanced_renderer, camera):
        """Rendering road terrain should not crash."""
        grid = np.ones((16, 16), dtype=np.int8)
        road_map = GameMap(id="road", name="Road Map", width=16, height=16, tile_grid=grid)
        enhanced_renderer.render(game_map=road_map, units=[], camera=camera)

    def test_render_woods_terrain(self, enhanced_renderer, camera):
        """Rendering woods terrain should not crash."""
        grid = np.full((16, 16), 3, dtype=np.int8)
        woods_map = GameMap(id="woods", name="Woods Map", width=16, height=16, tile_grid=grid)
        enhanced_renderer.render(game_map=woods_map, units=[], camera=camera)

    def test_render_water_terrain(self, enhanced_renderer, camera):
        """Rendering water terrain should not crash."""
        grid = np.full((16, 16), 6, dtype=np.int8)
        water_map = GameMap(id="water", name="Water Map", width=16, height=16, tile_grid=grid)
        enhanced_renderer.render(game_map=water_map, units=[], camera=camera)


@pytest.mark.integration
class TestUnitSpriteRendering:
    def test_infantry_squad_sprite_exists(self, sprite_renderer):
        """INFANTRY_SQUAD sprites should be in the sprite cache."""
        key = "allies_INFANTRY_SQUAD_d0"
        assert key in sprite_renderer._sprite_cache

    def test_tank_sprite_exists(self, sprite_renderer):
        """TANK sprites should be in the sprite cache."""
        key = "allies_TANK_d0"
        assert key in sprite_renderer._sprite_cache

    def test_at_gun_team_sprite_exists(self, sprite_renderer):
        """AT_GUN_TEAM sprites should be in the sprite cache."""
        key = "allies_AT_GUN_TEAM_d0"
        assert key in sprite_renderer._sprite_cache

    def test_mortar_team_sprite_exists(self, sprite_renderer):
        """MORTAR_TEAM sprites should be in the sprite cache."""
        key = "allies_MORTAR_TEAM_d0"
        assert key in sprite_renderer._sprite_cache

    def test_all_factions_have_infantry_sprites(self, sprite_renderer):
        """All factions should have infantry sprites."""
        for faction in ["allies", "axis", "polish"]:
            key = f"{faction}_INFANTRY_SQUAD_d0"
            assert key in sprite_renderer._sprite_cache, f"Missing sprite: {key}"

    def test_all_directions_generated(self, sprite_renderer):
        """All 8 directions should be generated for infantry."""
        for direction in range(8):
            key = f"allies_INFANTRY_SQUAD_d{direction}"
            assert key in sprite_renderer._sprite_cache, f"Missing sprite: {key}"

    def test_render_unit_with_sprite(self, pygame_screen, camera):
        """Rendering a unit using SpriteRenderer should not crash."""
        sr = SpriteRenderer()
        sr.initialize(pygame_screen)

        unit = Unit(
            id="ally_1",
            name="Ally Unit",
            faction=Faction.ALLIES,
            unit_type=UnitType.INFANTRY_SQUAD,
            health=HealthComponent(hp=100, max_hp=100),
            morale=MoraleComponent(value=85),
            weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=10, max_ammo=10),
            position=PositionComponent(tile_coord=TileCoord(3, 3)),
            vision=VisionComponent(range_tiles=5),
        )

        grid = np.zeros((16, 16), dtype=np.int8)
        game_map = GameMap(id="test", name="Test", width=16, height=16, tile_grid=grid)

        sr.render(game_map=game_map, units=[unit], camera=camera)


@pytest.mark.integration
class TestAttackLineRendering:
    def test_draw_attack_lines_method_exists(self, enhanced_renderer):
        """EnhancedRenderer should have _draw_attack_lines method."""
        assert hasattr(enhanced_renderer, "_draw_attack_lines")
        assert callable(enhanced_renderer._draw_attack_lines)

    def test_draw_attack_lines_no_attack_line_system(self, enhanced_renderer, camera):
        """Drawing attack lines without an attack line system should not crash."""
        # No attack line system set — should return gracefully
        enhanced_renderer._draw_attack_lines(camera)

    def test_draw_dashed_line_method_exists(self, enhanced_renderer):
        """UIOverlayRenderer should have _draw_dashed_line method (extracted from EnhancedRenderer in v0.3.28)."""
        from pycc2.presentation.rendering.ui_overlay_renderer import UIOverlayRenderer

        ui_overlay = enhanced_renderer._ui_overlay
        assert isinstance(ui_overlay, UIOverlayRenderer)
        assert hasattr(ui_overlay, "_draw_dashed_line")
        assert callable(ui_overlay._draw_dashed_line)


@pytest.mark.integration
class TestCombatEffectProxies:
    def test_spawn_hit_flash_exists(self, enhanced_renderer):
        """spawn_hit_flash proxy method should exist."""
        assert hasattr(enhanced_renderer, "spawn_hit_flash")
        assert callable(enhanced_renderer.spawn_hit_flash)

    def test_spawn_damage_number_exists(self, enhanced_renderer):
        """spawn_damage_number proxy method should exist."""
        assert hasattr(enhanced_renderer, "spawn_damage_number")
        assert callable(enhanced_renderer.spawn_damage_number)

    def test_spawn_muzzle_flash_exists(self, enhanced_renderer):
        """spawn_muzzle_flash proxy method should exist."""
        assert hasattr(enhanced_renderer, "spawn_muzzle_flash")
        assert callable(enhanced_renderer.spawn_muzzle_flash)

    def test_spawn_death_effect_exists(self, enhanced_renderer):
        """spawn_death_effect proxy method should exist."""
        assert hasattr(enhanced_renderer, "spawn_death_effect")
        assert callable(enhanced_renderer.spawn_death_effect)

    def test_spawn_hit_flash_does_not_crash(self, enhanced_renderer):
        """Calling spawn_hit_flash should not crash even without SpriteRenderer."""
        enhanced_renderer.spawn_hit_flash("test_unit")

    def test_spawn_damage_number_does_not_crash(self, enhanced_renderer):
        """Calling spawn_damage_number should not crash."""
        enhanced_renderer.spawn_damage_number(Vec2(100, 100), 25)

    def test_spawn_muzzle_flash_does_not_crash(self, enhanced_renderer):
        """Calling spawn_muzzle_flash should not crash."""
        enhanced_renderer.spawn_muzzle_flash(Vec2(100, 100), 0.5)

    def test_spawn_death_effect_does_not_crash(self, enhanced_renderer):
        """Calling spawn_death_effect should not crash."""
        enhanced_renderer.spawn_death_effect("test_unit", Vec2(100, 100))


@pytest.mark.integration
class TestDebugRendering:
    def test_render_debug_mode(self, enhanced_renderer, game_map, camera, ally_unit):
        """Rendering in debug mode should not crash."""
        enhanced_renderer.render(
            game_map=game_map,
            units=[ally_unit],
            camera=camera,
            debug_mode=True,
        )

    def test_render_multiple_units(self, enhanced_renderer, game_map, camera):
        """Rendering multiple units should not crash."""
        units = []
        for i in range(5):
            unit = Unit(
                id=f"unit_{i}",
                name=f"Unit {i}",
                faction=Faction.ALLIES if i % 2 == 0 else Faction.AXIS,
                unit_type=UnitType.INFANTRY_SQUAD,
                health=HealthComponent(hp=100, max_hp=100),
                morale=MoraleComponent(value=85),
                weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=10, max_ammo=10),
                position=PositionComponent(tile_coord=TileCoord(i + 1, i + 1)),
                vision=VisionComponent(range_tiles=5),
            )
            units.append(unit)

        enhanced_renderer.render(game_map=game_map, units=units, camera=camera)
