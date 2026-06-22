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
