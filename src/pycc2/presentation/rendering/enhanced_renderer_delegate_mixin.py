"""Delegate mixin for EnhancedRenderer.

Holds legacy compatibility shims and high-level combat-effect proxies so that
EnhancedRenderer can stay focused on coordinator/wiring logic while keeping its
public API unchanged.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.presentation.rendering.combat_effects_coordinator import (
        CombatEffectsCoordinator,
    )
    from pycc2.presentation.rendering.environment_renderer import EnvironmentRenderer
    from pycc2.presentation.rendering.isometric_renderer import IsometricRenderer
    from pycc2.presentation.rendering.lighting_effects import LightingEffectsSystem
    from pycc2.presentation.rendering.renderer_state_manager import RendererStateManager
    from pycc2.presentation.rendering.terrain_rendering_system import TerrainRenderingSystem


class EnhancedRendererDelegateMixin:
    """Mixin providing legacy terrain helpers, isometric rendering delegate,
    dynamic-light delegates, and combat-effect proxy methods for EnhancedRenderer.

    These methods were extracted from EnhancedRenderer during the God Class
    refactoring to keep the coordinator file under 500 lines.
    """

    # Type stubs for attributes owned by EnhancedRenderer.  They are declared here
    # so mypy understands the mixin methods reference valid instance state.
    _state_manager: RendererStateManager
    _terrain_rendering_sys: TerrainRenderingSystem
    _lighting_effects_sys: LightingEffectsSystem
    _environment: EnvironmentRenderer
    _combat_effects: CombatEffectsCoordinator
    _isometric_renderer: IsometricRenderer | None

    # ------------------------------------------------------------------
    # Isometric rendering
    # ------------------------------------------------------------------

    def _render_isometric(
        self,
        game_map: GameMap,
        units: list[Unit],
        camera: Camera,
        selected_unit_ids: set[str] | None = None,
        debug_mode: bool = False,
    ) -> None:
        """Delegate rendering to IsometricRenderer when in ISOMETRIC mode."""
        if self._isometric_renderer is None:
            from pycc2.presentation.rendering.isometric_renderer import IsometricRenderer

            self._isometric_renderer = IsometricRenderer()
            if self._state_manager.screen is not None:
                self._isometric_renderer.initialize(self._state_manager.screen)

        if self._isometric_renderer is None:
            raise RuntimeError("IsometricRenderer failed to initialize")
        self._isometric_renderer.render(
            game_map=game_map,
            units=units,
            camera=camera,
            selected_unit_ids=selected_unit_ids,
            debug_mode=debug_mode,
        )

    # ------------------------------------------------------------------
    # Legacy terrain tile helpers (consumed by TerrainTileCache)
    # ------------------------------------------------------------------

    def _get_cached_texture(self, terrain_id: int, variation: int) -> pygame.Surface:
        """Get or generate cached terrain texture (kept for TerrainTileCache compatibility)."""
        return self._terrain_rendering_sys.get_cached_texture(terrain_id, variation)

    def _generate_cc2_style_tile(
        self, terrain_id: int, tile_x: int = 0, tile_y: int = 0, bitmask: int = 0
    ) -> pygame.Surface:
        """Generate a CC2-authentic 48×48 terrain tile (kept for TerrainTileCache compatibility)."""
        return self._terrain_rendering_sys._generate_cc2_style_tile(
            terrain_id, tile_x, tile_y, bitmask
        )

    def _apply_height_lighting(self, surface: pygame.Surface, height: int) -> pygame.Surface:
        """Apply height-based lighting (kept for TerrainTileCache compatibility)."""
        return self._lighting_effects_sys.apply_height_lighting(surface, height)

    # ------------------------------------------------------------------
    # Dynamic light delegates
    # ------------------------------------------------------------------

    def spawn_dynamic_light(
        self,
        position: tuple[int, int],
        radius: float,
        intensity: float,
        color: tuple[int, int, int] = (255, 255, 200),
        duration_ms: int = 200,
    ) -> None:
        """Delegate to EnvironmentRenderer for dynamic light registration."""
        self._environment.spawn_dynamic_light(position, radius, intensity, color, duration_ms)

    def update_dynamic_lights(self, dt_ms: int) -> None:
        """Delegate to EnvironmentRenderer for dynamic light lifecycle update."""
        self._environment.update_dynamic_lights(dt_ms)

    # ------------------------------------------------------------------
    # Combat effect proxy methods (forward to CombatEffectsCoordinator)
    # ------------------------------------------------------------------

    def spawn_hit_flash(self, unit_id: str) -> None:
        """Delegate to CombatEffectsCoordinator."""
        self._combat_effects.spawn_hit_flash(unit_id)

    def spawn_damage_number(self, position, damage: int, is_kill: bool = False) -> None:
        """Delegate to CombatEffectsCoordinator."""
        self._combat_effects.spawn_damage_number(position, damage, is_kill)

    def spawn_death_effect(self, unit_id: str, position) -> None:
        """Delegate to CombatEffectsCoordinator."""
        self._combat_effects.spawn_death_effect(unit_id, position)

    def spawn_smoke_screen(self, position, radius: float = 64.0) -> None:
        """Delegate to CombatEffectsCoordinator."""
        self._combat_effects.spawn_smoke_screen(position, radius)

    def spawn_dirt_splash(self, x: float, y: float, count: int = 8) -> None:
        """Delegate to CombatEffectsCoordinator."""
        self._combat_effects.spawn_dirt_splash(x, y, count)

    def spawn_blood_pool(self, x: float, y: float, size: int = 10) -> None:
        """Delegate to CombatEffectsCoordinator."""
        self._combat_effects.spawn_blood_pool(x, y, size)

    def spawn_hit_marker(self, x: float, y: float, damage_type: str = "normal") -> None:
        """Delegate to CombatEffectsCoordinator."""
        self._combat_effects.spawn_hit_marker(x, y, damage_type)

    def update_particles(self, dt_ms: int) -> None:
        """Delegate to CombatEffectsCoordinator."""
        self._combat_effects.update_particles(dt_ms)

    def spawn_explosion(
        self, position, max_radius=40, duration_ms=500, color=(255, 200, 50)
    ) -> None:
        """Delegate to CombatEffectsCoordinator."""
        self._combat_effects.spawn_explosion(position, max_radius, duration_ms, color)

    def spawn_muzzle_flash(self, position, direction) -> None:
        """Delegate to CombatEffectsCoordinator."""
        self._combat_effects.spawn_muzzle_flash(position, direction)

    def particle_count(self) -> int:
        """Delegate to CombatEffectsCoordinator."""
        return self._combat_effects.particle_count()
