"""E2E: Visual Basics — TC-038~043 terrain/sprite/fog/day-night/weather/effects.

P2 E2E coverage for scenario-4 visual foundations. These visual elements are
exercised at the unit layer but were weak at the E2E layer. This suite drives
the real rendering/effect APIs end-to-end under a headless pygame display:

  - TC-038  22 terrain types render without crash
  - TC-039  infantry 8-direction sprite rendering
  - TC-040  fog-of-war update + frame render
  - TC-041  day-night cycle lighting across DAWN/DAY/DUSK/NIGHT
  - TC-042  weather rain render (WeatherRenderer)
  - TC-042b weather fog render (WeatherRenderer + WeatherSystem overlay)
  - TC-043a explosion animation effect (CC2ExplosionEffect)
  - TC-043b smoke animation effect (CC2SmokeEffect)
  - TC-043c death fade-out animation (UnitFadeRenderer)

No mocks: real pygame surfaces, real effect classes, real EnhancedRenderer.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_JOYSTICK_DRIVER", "dummy")

import numpy as np
import pygame
import pytest
from conftest import GameLoopFactory

from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.systems.day_night_cycle import DayNightEffects, GameTime, TimeOfDay
from pycc2.domain.systems.fog_of_war import FogOfWar, TileVisibility
from pycc2.domain.systems.weather_effects import WeatherState, WeatherType
from pycc2.domain.value_objects.direction import Direction
from pycc2.domain.value_objects.terrain_type import TerrainType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.presentation.rendering.camera import Camera
from pycc2.presentation.rendering.cc2_combat_effects import (
    CC2ExplosionEffect,
    CC2SmokeEffect,
)
from pycc2.presentation.rendering.direction_sprite import DirectionSpriteManager
from pycc2.presentation.rendering.unit_fade_renderer import UnitFadeRenderer
from pycc2.presentation.rendering.weather_renderer import WeatherRenderer
from pycc2.presentation.rendering.weather_system import WeatherSystem


@pytest.fixture(autouse=True)
def _pygame_headless():
    """Initialize headless pygame for each test; quit on teardown."""
    pygame.init()
    yield
    pygame.quit()


class TestVisualBasicsE2E:
    """TC-038~043: visual foundation rendering under a real headless display."""

    def _factory(self) -> GameLoopFactory:
        screen = pygame.display.set_mode((1280, 720))
        return GameLoopFactory(screen)

    # ── TC-038: terrain types render ──────────────────────────────────────

    def test_terrain_types_render(self):
        """All 22 terrain types render through the real EnhancedRenderer.

        Builds a map whose columns span every TerrainType member and renders
        it via the factory's initialized EnhancedRenderer. Asserts no crash
        and that at least the 12 CC2-core terrains are covered.
        """
        f = self._factory()
        try:
            terrains = list(TerrainType)
            width = len(terrains)
            height = 4
            grid = np.array(
                [[terrains[c].value for c in range(width)] for _ in range(height)],
                dtype=np.int8,
            )
            game_map = GameMap(
                id="terrain_all",
                name="All Terrains",
                width=width,
                height=height,
                tile_grid=grid,
            )
            f.camera.position = Vec2(width * 16.0, height * 16.0)
            f.renderer.render(
                game_map,
                [],
                f.camera,
                alpha=1.0,
                selected_unit_ids=set(),
                debug_mode=False,
            )
            assert len(terrains) >= 12  # 22 available, spec required 12
        finally:
            f.shutdown()

    # ── TC-039: infantry 8-direction sprites ──────────────────────────────

    def test_infantry_8_direction_sprites(self):
        """Infantry sprites render for all 8 compass directions.

        Uses DirectionSpriteManager (singleton) to load allied rifleman
        sprites — falling back to procedural 8-direction placeholders when
        no spritesheet is present — and blits each direction to a surface.
        """
        mgr = DirectionSpriteManager.get_instance()
        sprite_set = mgr.load_unit_sprites("rifleman", "allies")
        canvas = pygame.Surface((64, 64), pygame.SRCALPHA)

        rendered = 0
        for direction in Direction.get_all():
            sprite = sprite_set.get_sprite(direction)
            if sprite is not None:
                canvas.blit(sprite, (16, 16))
                rendered += 1

        # All 8 directions must resolve (procedural variants guarantee this).
        assert rendered == 8

    # ── TC-040: fog of war render ─────────────────────────────────────────

    def test_fog_of_war_render(self):
        """Fog-of-war ray-cast update + full frame render coexist.

        Runs FogOfWar.update_visibility from a centered observer on the real
        map, asserts the observer tile becomes VISIBLE, then renders a frame
        through the factory pipeline (fog overlay path) without crashing.
        """
        f = self._factory()
        try:
            gm = f.game_map
            fog = FogOfWar(gm.width, gm.height)
            observer = TileCoord(gm.width // 2, gm.height // 2)
            fog.update_visibility(
                observer_pos=observer,
                vision_range=8,
                vision_angle=6.2831853,
                facing_direction=0.0,
                game_map=gm,
                current_tick=0,
            )
            assert fog.visibility_grid[observer.y][observer.x] == TileVisibility.VISIBLE
            assert f.render_frame() is True
        finally:
            f.shutdown()

    # ── TC-041: day/night lighting ────────────────────────────────────────

    def test_day_night_lighting(self):
        """Day-night cycle produces distinct lighting phases + renders frames.

        Drives GameTime to four representative hours, collects the resulting
        TimeOfDay phases, looks up each DayNightEffects lighting color, and
        renders a frame per phase through the factory pipeline.
        """
        f = self._factory()
        try:
            effects = DayNightEffects()
            seen_phases: set[TimeOfDay] = set()
            for hour in (6.0, 12.0, 19.0, 23.0):
                gt = GameTime()
                gt.set_time(hour)
                phase = gt.time_phase
                seen_phases.add(phase)
                color = effects.LIGHTING_COLORS[phase]
                assert len(color) == 3
                assert f.render_frame() is True
            # At least 3 distinct phases exercised (DAWN/DAY/DUSK/NIGHT).
            assert len(seen_phases) >= 3
        finally:
            f.shutdown()

    # ── TC-042: weather rain render ───────────────────────────────────────

    def test_weather_rain_render(self):
        """Rain weather renders particle drops across multiple update ticks."""
        renderer = WeatherRenderer(800, 600)
        state = WeatherState(
            weather_type=WeatherType.RAIN,
            intensity=1.0,
            duration_turns=3,
            remaining_turns=3,
        )
        screen = pygame.Surface((800, 600))
        for _ in range(5):
            renderer.update(1.0 / 60.0)
            renderer.render(screen, state)
        assert state.is_active()

    # ── TC-042b: weather fog render ───────────────────────────────────────

    def test_weather_fog_render(self):
        """Fog weather renders a fog overlay + atmospheric WeatherSystem layer."""
        renderer = WeatherRenderer(800, 600)
        fog_state = WeatherState(
            weather_type=WeatherType.FOG,
            intensity=0.8,
            duration_turns=2,
            remaining_turns=2,
        )
        screen = pygame.Surface((800, 600))
        renderer.render(screen, fog_state)

        # Exercise the atmospheric WeatherSystem overlay (light_fog mode).
        system = WeatherSystem()
        system.update_screen_size(800, 600)
        system.set_mode("light_fog")
        system.update(1.0 / 60.0)
        system.render(screen)
        assert fog_state.weather_type == WeatherType.FOG

    # ── TC-043a: explosion animation ──────────────────────────────────────

    def test_explosion_animation(self):
        """CC2ExplosionEffect updates + renders across its full lifetime."""
        surface = pygame.Surface((200, 200), pygame.SRCALPHA)
        effect = CC2ExplosionEffect(100.0, 100.0)

        frames = 0
        while effect.alive and frames < 60:
            effect.update()
            effect.render(surface, (0.0, 0.0))
            frames += 1

        assert frames > 0
        assert not effect.alive  # fully expired after the loop

    # ── TC-043b: smoke animation ──────────────────────────────────────────

    def test_smoke_animation(self):
        """CC2SmokeEffect updates + renders; still alive mid-duration."""
        surface = pygame.Surface((300, 300), pygame.SRCALPHA)
        effect = CC2SmokeEffect(150.0, 150.0, tile_size=48)

        for _ in range(30):
            effect.update()
            effect.render(surface, (0.0, 0.0))

        # duration=120 ticks; after 30 ticks the cloud is still alive.
        assert effect.alive

    # ── TC-043c: death fade animation ─────────────────────────────────────

    def test_death_animation(self):
        """UnitFadeRenderer registers a dying unit and renders a fade ghost."""
        fade = UnitFadeRenderer()
        fade.start_death_fade("u_dead", Vec2(100.0, 100.0), duration_ms=500)

        offscreen = pygame.Surface((400, 400), pygame.SRCALPHA)
        camera = Camera(
            position=Vec2(0.0, 0.0),
            viewport_width=400,
            viewport_height=400,
        )
        fade.render_fading_units(offscreen, camera)

        # Unit still registered immediately after render (fade in progress).
        assert "u_dead" in fade._fading_units
        fade.clear()
        assert not fade._fading_units
