"""TD-066: CC2SmokeEffect integration into EffectRenderer tests.

Validates that EffectRenderer.spawn_smoke_screen creates BOTH:
  - Generic SMOKE_SCREEN particles (backward compat, upper layer)
  - CC2SmokeEffect instances (CC2-authentic irregular polygon blobs, base layer)

And that update/render lifecycle correctly manages the CC2SmokeEffect list.

Design follows the project's testing philosophy:
  - Real EffectRenderer + real CC2SmokeEffect (no Mock of the SUT).
  - Real pygame Surface for render tests (SDL dummy driver).
  - No skip/xfail — every scenario is exercised.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()

from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.presentation.rendering.camera import Camera
from pycc2.presentation.rendering.cc2_combat_effects import CC2SmokeEffect
from pycc2.presentation.rendering.effect_renderer import EffectRenderer


@pytest.fixture()
def effect_renderer(pygame_display):
    """Create an EffectRenderer instance for testing."""
    return EffectRenderer()


@pytest.fixture()
def camera():
    """Create a Camera centered at world origin."""
    return Camera(position=Vec2(0.0, 0.0), viewport_width=800, viewport_height=600)


class TestSpawnSmokeScreenCreatesCC2Effect:
    """TD-066: spawn_smoke_screen creates a CC2SmokeEffect instance."""

    def test_creates_cc2_smoke_effect(self, effect_renderer):
        pos = Vec2(100.0, 200.0)
        effect_renderer.spawn_smoke_screen(pos, radius=64.0)
        assert len(effect_renderer._cc2_smoke_effects) == 1
        effect = effect_renderer._cc2_smoke_effects[0]
        assert isinstance(effect, CC2SmokeEffect)
        assert effect.x == 100.0
        assert effect.y == 200.0

    def test_preserves_generic_particles(self, effect_renderer):
        """Generic SMOKE_SCREEN particles still emitted for backward compat."""
        pos = Vec2(100.0, 200.0)
        effect_renderer.spawn_smoke_screen(pos, radius=64.0)
        # ParticleEmitter should have emitted smoke_screen particles
        assert len(effect_renderer._particle_emitter.particles) > 0

    def test_multiple_spawn_calls_stack(self, effect_renderer):
        pos1 = Vec2(100.0, 200.0)
        pos2 = Vec2(300.0, 400.0)
        effect_renderer.spawn_smoke_screen(pos1, radius=64.0)
        effect_renderer.spawn_smoke_screen(pos2, radius=64.0)
        assert len(effect_renderer._cc2_smoke_effects) == 2

    def test_tile_size_scales_with_radius(self, effect_renderer):
        """Larger radius → larger tile_size → larger CC2 blob coverage."""
        pos = Vec2(0.0, 0.0)
        effect_renderer.spawn_smoke_screen(pos, radius=128.0)
        effect = effect_renderer._cc2_smoke_effects[0]
        # radius=128 → tile_size = max(8, 128/4) = 32
        assert effect.tile_size == 32

    def test_small_radius_clamps_tile_size(self, effect_renderer):
        """Very small radius clamps tile_size to minimum 8."""
        pos = Vec2(0.0, 0.0)
        effect_renderer.spawn_smoke_screen(pos, radius=16.0)
        effect = effect_renderer._cc2_smoke_effects[0]
        # radius=16 → 16/4=4, but clamped to max(8, 4) = 8
        assert effect.tile_size == 8


class TestUpdateEffectsPrunesCC2Smoke:
    """TD-066: update_effects updates + prunes expired CC2SmokeEffect instances."""

    def test_update_advances_cc2_smoke_tick(self, effect_renderer):
        pos = Vec2(100.0, 200.0)
        effect_renderer.spawn_smoke_screen(pos, radius=64.0)
        initial_tick = effect_renderer._cc2_smoke_effects[0].tick
        effect_renderer.update_effects()
        assert effect_renderer._cc2_smoke_effects[0].tick == initial_tick + 1

    def test_prunes_expired_cc2_smoke(self, effect_renderer):
        """After duration (120 ticks), CC2SmokeEffect is pruned."""
        pos = Vec2(100.0, 200.0)
        effect_renderer.spawn_smoke_screen(pos, radius=64.0)
        effect = effect_renderer._cc2_smoke_effects[0]
        # Fast-forward to expiry
        effect.tick = effect.duration
        assert not effect.alive
        effect_renderer.update_effects()
        assert len(effect_renderer._cc2_smoke_effects) == 0

    def test_update_keeps_alive_effects(self, effect_renderer):
        pos = Vec2(100.0, 200.0)
        effect_renderer.spawn_smoke_screen(pos, radius=64.0)
        for _ in range(50):
            effect_renderer.update_effects()
        assert len(effect_renderer._cc2_smoke_effects) == 1


class TestRenderEffectsDrawsCC2Smoke:
    """TD-066: render_effects renders CC2SmokeEffect as base layer."""

    def test_render_with_cc2_smoke_no_error(self, effect_renderer, camera):
        """Rendering with active CC2SmokeEffect doesn't raise."""
        pos = Vec2(0.0, 0.0)  # World origin = viewport center (camera at origin)
        effect_renderer.spawn_smoke_screen(pos, radius=64.0)
        surface = pygame.Surface((800, 600))
        surface.fill((0, 0, 0))
        effect_renderer.render_effects(surface, camera)

    def test_render_draws_pixels_for_cc2_smoke(self, effect_renderer, camera):
        """CC2SmokeEffect at world origin should draw non-black pixels at viewport center."""
        pos = Vec2(0.0, 0.0)  # World origin maps to screen (400, 300) = viewport center
        effect_renderer.spawn_smoke_screen(pos, radius=64.0)
        surface = pygame.Surface((800, 600))
        surface.fill((0, 0, 0))
        effect_renderer.render_effects(surface, camera)
        # Count non-black pixels in the center region (screen 350-450, 250-350)
        non_black = 0
        for px in range(350, 450):
            for py in range(250, 350):
                r, g, b, *_ = surface.get_at((px, py))
                if r > 0 or g > 0 or b > 0:
                    non_black += 1
        assert non_black > 0, "CC2SmokeEffect should render visible (non-black) pixels"

    def test_render_no_cc2_smoke_no_error(self, effect_renderer, camera):
        """Rendering with no CC2SmokeEffect doesn't raise."""
        surface = pygame.Surface((800, 600))
        surface.fill((0, 0, 0))
        effect_renderer.render_effects(surface, camera)
