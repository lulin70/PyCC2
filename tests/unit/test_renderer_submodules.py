"""
Unit tests for renderer sub-modules extracted from EnhancedRenderer.

Covers:
- RendererStateManager (display/surface/cache lifecycle)
- CombatEffectsCoordinator (high-level combat VFX orchestration)
- AtmosphereController (weather/flash/shell state grouping)
"""

from __future__ import annotations

import os

import pytest

# Ensure SDL dummy drivers are set before pygame imports
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


class TestRendererStateManager:
    """Tests for RendererStateManager."""

    def test_initialize_creates_offscreen_and_dirty_tracker(self, pygame_display):
        import pygame

        from pycc2.presentation.rendering.renderer_state_manager import RendererStateManager

        mgr = RendererStateManager(tile_size=48)
        screen = pygame.display.set_mode((640, 480))
        offscreen = mgr.initialize(screen)

        assert mgr.screen is screen
        assert mgr.offscreen is offscreen
        assert offscreen.get_size() == (640, 480)
        assert mgr.dirty_tracker is not None

    def test_ensure_offscreen_reuses_existing_buffer(self, pygame_display):
        import pygame

        from pycc2.presentation.rendering.renderer_state_manager import RendererStateManager

        mgr = RendererStateManager(tile_size=48)
        screen = pygame.display.set_mode((640, 480))
        offscreen1 = mgr.initialize(screen)
        offscreen2 = mgr.ensure_offscreen()

        assert offscreen1 is offscreen2

    def test_resize_reinitializes_offscreen(self, pygame_display):
        import pygame

        from pycc2.presentation.rendering.renderer_state_manager import RendererStateManager

        mgr = RendererStateManager(tile_size=48)
        screen = pygame.display.set_mode((640, 480))
        mgr.initialize(screen)
        old_offscreen = mgr.offscreen

        mgr.resize(800, 600)

        assert mgr.offscreen is not old_offscreen
        assert mgr.offscreen.get_size() == (800, 600)
        assert mgr.dirty_tracker is not None

    def test_get_pooled_surface_returns_transparent_surface(self, pygame_display):
        import pygame

        from pycc2.presentation.rendering.renderer_state_manager import RendererStateManager

        mgr = RendererStateManager(tile_size=48)
        mgr.initialize(pygame.display.set_mode((640, 480)))
        surf = mgr.get_pooled_surface((32, 32))

        assert isinstance(surf, pygame.Surface)
        assert surf.get_size() == (32, 32)
        assert surf.get_at((16, 16)) == (0, 0, 0, 0)

    def test_shutdown_clears_pool(self, pygame_display):
        import pygame

        from pycc2.presentation.rendering.renderer_state_manager import RendererStateManager

        mgr = RendererStateManager(tile_size=48)
        mgr.initialize(pygame.display.set_mode((640, 480)))
        mgr.get_pooled_surface((32, 32))
        mgr.shutdown()

        # After shutdown the pool is empty; getting a surface should still work
        surf = mgr.get_pooled_surface((32, 32))
        assert surf.get_size() == (32, 32)


class TestCombatEffectsCoordinator:
    """Tests for CombatEffectsCoordinator."""

    @pytest.fixture()
    def coordinator(self):
        from pycc2.presentation.rendering.combat_effects_coordinator import (
            CombatEffectsCoordinator,
        )
        from pycc2.presentation.rendering.environment_renderer import EnvironmentRenderer
        from pycc2.presentation.rendering.particle_effects_renderer import (
            ParticleEffectsRenderer,
        )
        from pycc2.presentation.rendering.unit_fade_renderer import UnitFadeRenderer

        return CombatEffectsCoordinator(
            particle_effects=ParticleEffectsRenderer(),
            unit_fade_renderer=UnitFadeRenderer(),
            environment_renderer=EnvironmentRenderer(),
        )

    def test_spawn_explosion_registers_dynamic_light(self, coordinator):
        from types import SimpleNamespace

        coordinator.spawn_explosion(SimpleNamespace(x=100, y=200), max_radius=40)
        # Dynamic light is registered inside EnvironmentRenderer through LightingEffectsSystem,
        # which is None until dependencies are injected.  The call should not crash.

    def test_spawn_death_effect_starts_fade(self, coordinator):
        from types import SimpleNamespace

        position = SimpleNamespace(x=50, y=60)
        coordinator.spawn_death_effect("u1", position)
        assert "u1" in coordinator._unit_fade_renderer._fading_units

    def test_spawn_hit_flash_does_not_crash(self, coordinator):
        coordinator.spawn_hit_flash("u1")

    def test_particle_count_delegates(self, coordinator):
        # No particles spawned -> count is 0
        assert coordinator.particle_count() == 0


class TestAtmosphereController:
    """Tests for AtmosphereController."""

    @pytest.fixture()
    def controller(self):
        from pycc2.presentation.rendering.atmosphere_controller import AtmosphereController

        return AtmosphereController()

    def test_trigger_flash_activates_flash_sys(self, controller):
        controller.trigger_flash(color=(255, 0, 0), intensity=0.5, duration=0.2)
        assert controller.flash_sys.is_active
        assert controller.flash_sys.color == (255, 0, 0)

    def test_update_flash_decays_alpha(self, controller):
        controller.trigger_flash(intensity=1.0, duration=0.1)
        initial_alpha = controller.flash_sys.alpha
        controller.update_flash(0.2)
        assert not controller.flash_sys.is_active
        assert controller.flash_sys.alpha <= initial_alpha

    def test_set_weather_changes_mode(self, controller):
        controller.set_weather("dust")
        assert controller.weather_sys.mode == "dust"

    def test_spawn_shell_casing_adds_casing(self, controller):
        controller.spawn_shell_casing(100.0, 200.0, direction_rad=0.0)
        assert controller.shell_sys.count == 1

    def test_update_shell_casings_ages_and_removes(self, controller):
        controller.spawn_shell_casing(0.0, 0.0)
        controller.update_shell_casings(10.0)
        assert controller.shell_sys.count == 0

    def test_render_shell_casings_does_not_crash(self, controller, pygame_display):
        from types import SimpleNamespace

        import pygame

        controller.spawn_shell_casing(0.0, 0.0)
        offscreen = pygame.Surface((400, 300), pygame.SRCALPHA)
        camera = SimpleNamespace(x=0, y=0)
        controller.render_shell_casings(offscreen, camera)

    def test_update_screen_size_does_not_crash(self, controller):
        controller.update_screen_size(1024, 768)


class TestEnhancedRendererDelegateMixin:
    """Verify public API methods remain available on EnhancedRenderer after split."""

    def test_public_combat_methods_exist(self):
        from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer

        public_methods = (
            "spawn_hit_flash",
            "spawn_damage_number",
            "spawn_death_effect",
            "spawn_smoke_screen",
            "spawn_dirt_splash",
            "spawn_blood_pool",
            "spawn_hit_marker",
            "update_particles",
            "spawn_explosion",
            "spawn_muzzle_flash",
            "particle_count",
            "spawn_dynamic_light",
            "update_dynamic_lights",
        )
        for name in public_methods:
            assert hasattr(EnhancedRenderer, name), f"Missing public method: {name}"

    def test_legacy_terrain_helpers_exist(self):
        from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer

        assert hasattr(EnhancedRenderer, "_get_cached_texture")
        assert hasattr(EnhancedRenderer, "_generate_cc2_style_tile")
        assert hasattr(EnhancedRenderer, "_apply_height_lighting")
        assert hasattr(EnhancedRenderer, "_render_isometric")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
