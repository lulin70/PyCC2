"""Unit tests for EffectRenderer.

Tests effect spawning, state updates, accessors, and cleanup.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()

from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.presentation.rendering.animation_system import AnimationType, UnitAnimator
from pycc2.presentation.rendering.effect_renderer import EffectRenderer


@pytest.fixture()
def effect_renderer(pygame_display):
    """Create an EffectRenderer instance for testing."""
    return EffectRenderer()


# ====== Initialization ======


class TestEffectRenderer:
    # --- Initialization ---

    def test_init_default_state(self, effect_renderer):
        """Verify initial state: empty particles, empty damage numbers, empty flashes, etc."""
        assert len(effect_renderer.effect_particles) == 0
        assert len(effect_renderer.damage_numbers) == 0
        assert len(effect_renderer.flash_units) == 0
        assert len(effect_renderer.death_animations) == 0
        assert len(effect_renderer.unit_animators) == 0

    def test_animation_tick_starts_zero(self, effect_renderer):
        """Verify animation_tick starts at 0."""
        assert effect_renderer.animation_tick == 0

    # --- Effect spawning ---

    def test_spawn_hit_flash_adds_flash(self, effect_renderer):
        """Verify spawn_hit_flash adds to flash_units."""
        effect_renderer.spawn_hit_flash("unit_1")
        assert "unit_1" in effect_renderer.flash_units
        assert effect_renderer.flash_units["unit_1"] == 8

    def test_spawn_damage_number_adds_entry(self, effect_renderer):
        """Verify spawn_damage_number adds to damage_numbers."""
        pos = Vec2(100.0, 200.0)
        effect_renderer.spawn_damage_number(pos, damage=25)
        assert len(effect_renderer.damage_numbers) == 1
        assert effect_renderer.damage_numbers[0]["damage"] == 25
        assert effect_renderer.damage_numbers[0]["pos"] == (100.0, 200.0)

    def test_spawn_damage_number_respects_max(self, effect_renderer):
        """Verify exceeding MAX_DAMAGE_NUMBERS removes the oldest entry."""
        max_dn = EffectRenderer.MAX_DAMAGE_NUMBERS
        for i in range(max_dn + 5):
            pos = Vec2(float(i), 0.0)
            effect_renderer.spawn_damage_number(pos, damage=i)
        assert len(effect_renderer.damage_numbers) == max_dn
        # The oldest entries should have been removed; the last entry should be the most recent
        assert effect_renderer.damage_numbers[-1]["damage"] == max_dn + 4

    def test_spawn_death_effect_creates_animation(self, effect_renderer):
        """Verify spawn_death_effect creates death_animation and unit_animator."""
        pos = Vec2(100.0, 200.0)
        effect_renderer.spawn_death_effect("dead_unit", pos)
        assert "dead_unit" in effect_renderer.death_animations
        assert "dead_unit" in effect_renderer.unit_animators
        assert effect_renderer.unit_animators["dead_unit"].state.anim_type == AnimationType.DEATH
        assert effect_renderer.death_animations["dead_unit"]["progress"] == 0

    def test_spawn_explosion_no_error(self, effect_renderer):
        """Verify spawn_explosion does not raise exceptions."""
        pos = Vec2(100.0, 200.0)
        effect_renderer.spawn_explosion(pos, size="medium")

    def test_spawn_smoke_screen_no_error(self, effect_renderer):
        """Verify spawn_smoke_screen does not raise exceptions."""
        pos = Vec2(100.0, 200.0)
        effect_renderer.spawn_smoke_screen(pos, radius=64.0)

    # --- State updates ---

    def test_update_effects_reduces_flash_ticks(self, effect_renderer):
        """Verify update_effects reduces flash_units tick count."""
        effect_renderer.spawn_hit_flash("unit_1")
        initial_tick = effect_renderer.flash_units["unit_1"]
        effect_renderer.update_effects()
        assert effect_renderer.flash_units["unit_1"] == initial_tick - 1

    def test_update_effects_removes_expired_flash(self, effect_renderer):
        """Verify expired flash (tick <= 0) is removed after update."""
        effect_renderer.flash_units["unit_1"] = 0
        effect_renderer.update_effects()
        # tick 0 -> removed by expired check, then remaining keys decremented
        # But the expired check removes ticks <= 0 BEFORE decrementing,
        # so unit_1 with tick=0 gets removed first
        assert "unit_1" not in effect_renderer.flash_units

    def test_update_effects_removes_expired_damage_numbers(self, effect_renderer):
        """Verify expired damage numbers (life <= 0) are removed."""
        pos = Vec2(0.0, 0.0)
        effect_renderer.spawn_damage_number(pos, damage=10)
        # Set life to 1 so next update will decrement to 0 and remove it
        effect_renderer.damage_numbers[0]["life"] = 1
        effect_renderer.update_effects()
        assert len(effect_renderer.damage_numbers) == 0

    def test_update_effects_advances_death_animation(self, effect_renderer):
        """Verify death animation progress increments on update."""
        pos = Vec2(100.0, 200.0)
        effect_renderer.spawn_death_effect("unit_1", pos)
        assert effect_renderer.death_animations["unit_1"]["progress"] == 0
        effect_renderer.update_effects()
        assert effect_renderer.death_animations["unit_1"]["progress"] == 1

    def test_tick_increments_counter(self, effect_renderer):
        """Verify tick() increments animation_tick."""
        assert effect_renderer.animation_tick == 0
        effect_renderer.tick()
        assert effect_renderer.animation_tick == 1
        effect_renderer.tick()
        assert effect_renderer.animation_tick == 2

    # --- Accessors ---

    def test_ensure_animator_creates_new(self, effect_renderer):
        """Verify ensure_animator creates a new animator for unknown unit_id."""
        animator = effect_renderer.ensure_animator("unit_new")
        assert isinstance(animator, UnitAnimator)
        assert "unit_new" in effect_renderer.unit_animators

    def test_ensure_animator_returns_existing(self, effect_renderer):
        """Verify ensure_animator returns existing animator for known unit_id."""
        first = effect_renderer.ensure_animator("unit_1")
        second = effect_renderer.ensure_animator("unit_1")
        assert first is second

    def test_get_font_returns_font(self, effect_renderer):
        """Verify get_font returns a Font object (or None in headless)."""
        f = effect_renderer.get_font(16)
        # In headless/dummy SDL, font may not be available
        if f is not None:
            assert isinstance(f, pygame.font.Font)

    def test_get_font_caches(self, effect_renderer):
        """Verify get_font caches Font objects (same size returns same object)."""
        f1 = effect_renderer.get_font(16)
        f2 = effect_renderer.get_font(16)
        if f1 is not None and f2 is not None:
            assert f1 is f2

    # --- Cleanup ---

    def test_clear_empties_all_state(self, effect_renderer):
        """Verify clear() empties all effect state."""
        pos = Vec2(100.0, 200.0)
        effect_renderer.spawn_hit_flash("unit_1")
        effect_renderer.spawn_damage_number(pos, damage=10)
        effect_renderer.spawn_death_effect("unit_2", pos)

        assert len(effect_renderer.flash_units) > 0
        assert len(effect_renderer.damage_numbers) > 0
        assert len(effect_renderer.death_animations) > 0

        effect_renderer.clear()

        assert len(effect_renderer.flash_units) == 0
        assert len(effect_renderer.damage_numbers) == 0
        assert len(effect_renderer.effect_particles) == 0
        assert len(effect_renderer.death_animations) == 0
        assert len(effect_renderer.unit_animators) == 0


# ====== Crater Decal Tests (P2-6: dynamic crater rendering) ======


class TestCraterDecals:
    """Tests for persistent crater decals spawned by explosions.

    Validates P2-6 fix: explosions now leave a persistent ground decal
    (CC2-authentic behavior, see GAP_ANALYSIS V-03).
    """

    def test_spawn_explosion_creates_crater_decal(self, effect_renderer):
        """spawn_explosion should register a persistent crater decal."""
        pos = Vec2(100.0, 200.0)
        effect_renderer.spawn_explosion(pos, size="medium")
        assert len(effect_renderer._crater_decals) == 1
        decal = effect_renderer._crater_decals[0]
        assert decal["pos"] == (100.0, 200.0)
        assert decal["size"] == "medium"
        assert isinstance(decal["sprite"], pygame.Surface)

    def test_spawn_explosion_small_uses_small_crater(self, effect_renderer):
        """Small explosion should spawn a 32x32 crater sprite."""
        pos = Vec2(50.0, 50.0)
        effect_renderer.spawn_explosion(pos, size="small")
        assert len(effect_renderer._crater_decals) == 1
        sprite = effect_renderer._crater_decals[0]["sprite"]
        assert sprite.get_size() == (32, 32)

    def test_spawn_explosion_large_uses_large_crater(self, effect_renderer):
        """Large explosion should spawn a 48x48 crater sprite."""
        pos = Vec2(50.0, 50.0)
        effect_renderer.spawn_explosion(pos, size="large")
        assert len(effect_renderer._crater_decals) == 1
        sprite = effect_renderer._crater_decals[0]["sprite"]
        assert sprite.get_size() == (48, 48)

    def test_crater_decal_persists_across_update(self, effect_renderer):
        """Crater decals should NOT be removed by update_effects (persistent)."""
        pos = Vec2(100.0, 200.0)
        effect_renderer.spawn_explosion(pos, size="medium")
        assert len(effect_renderer._crater_decals) == 1
        # Run multiple update cycles
        for _ in range(100):
            effect_renderer.update_effects()
        # Crater should still be there
        assert len(effect_renderer._crater_decals) == 1

    def test_crater_decal_fifo_eviction(self, effect_renderer):
        """Exceeding _crater_decals_max should evict oldest (FIFO)."""
        max_decals = effect_renderer._crater_decals_max
        for i in range(max_decals + 5):
            pos = Vec2(float(i), 0.0)
            effect_renderer.spawn_explosion(pos, size="small")
        # Should be capped at max
        assert len(effect_renderer._crater_decals) == max_decals
        # Oldest should be evicted; first remaining should be at x=5
        assert effect_renderer._crater_decals[0]["pos"][0] == 5.0
        # Latest should be at x = max_decals + 4
        assert effect_renderer._crater_decals[-1]["pos"][0] == float(max_decals + 4)

    def test_clear_decals_removes_all(self, effect_renderer):
        """clear_decals should remove all crater decals without touching other state."""
        pos = Vec2(100.0, 200.0)
        effect_renderer.spawn_explosion(pos, size="medium")
        effect_renderer.spawn_hit_flash("unit_1")
        assert len(effect_renderer._crater_decals) == 1
        assert len(effect_renderer.flash_units) > 0

        effect_renderer.clear_decals()

        assert len(effect_renderer._crater_decals) == 0
        # Other state should be untouched
        assert len(effect_renderer.flash_units) > 0

    def test_render_decals_no_error_empty(self, effect_renderer, pygame_display):
        """render_decals should be a no-op when no decals exist."""
        from pycc2.domain.value_objects.vec2 import Vec2 as V2
        from pycc2.presentation.rendering.camera import Camera, ProjectionMode

        cam = Camera(
            position=V2(0.0, 0.0),
            zoom=1.0,
            viewport_width=800,
            viewport_height=600,
            projection=ProjectionMode.ORTHOGRAPHIC,
        )
        surface = pygame.Surface((800, 600))
        # No decals — should not raise
        effect_renderer.render_decals(surface, cam)

    def test_render_decals_draws_to_surface(self, effect_renderer, pygame_display):
        """render_decals should blit crater sprite onto the target surface."""
        from pycc2.domain.value_objects.vec2 import Vec2 as V2
        from pycc2.presentation.rendering.camera import Camera, ProjectionMode

        cam = Camera(
            position=V2(0.0, 0.0),
            zoom=1.0,
            viewport_width=800,
            viewport_height=600,
            projection=ProjectionMode.ORTHOGRAPHIC,
        )
        surface = pygame.Surface((800, 600))
        # Fill with a known background color
        bg_color = (10, 20, 30)
        surface.fill(bg_color)

        # Spawn explosion at world origin
        pos = Vec2(0.0, 0.0)
        effect_renderer.spawn_explosion(pos, size="medium")
        assert len(effect_renderer._crater_decals) == 1

        # Render decals
        effect_renderer.render_decals(surface, cam)

        # Camera at (0,0) maps world (0,0) to screen center (400, 300).
        # Crater sprite (32x32) is centered on that point, so check region
        # (384, 284) to (416, 316).
        non_bg_count = 0
        for px in range(384, 416):
            for py in range(284, 316):
                r, g, b, *_ = surface.get_at((px, py))
                if not (r == bg_color[0] and g == bg_color[1] and b == bg_color[2]):
                    non_bg_count += 1
        assert non_bg_count > 0, "render_decals did not draw any crater pixels"
