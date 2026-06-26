"""
Enhanced Pixel Art Renderer for PyCC2 - Phase A5 (CC2 Authentic) [REFACTORED]

Renders maps with authentic Close Combat 2 visual style.
Features:
- 48×48 pixel tiles (matching original CC2)
- Orthographic top-down projection (NOT isometric)
- CC2-authentic terrain palette from screenshot analysis
- Procedural texture generation with per-tile variation
- Deterministic random seeds for consistent regeneration

REFACTORED ARCHITECTURE (2026-05):
This file now serves as the MAIN COORDINATOR that imports and delegates to specialized modules:
- sprite_generator.py             : SpriteGenerator class (all programmatic sprite creation)
- particle_system.py              : TopDownParticleSystem class (explosions, smoke, etc.)
- lighting_system.py              : TopDownLightingConfig + LightingSystem (time-of-day, dynamic lights)
- terrain_renderer.py             : TerrainRenderer (enhanced terrain, transitions, edge smoothing)
- terrain_rendering_system.py     : TerrainRenderingSystem (simple/enhanced terrain, tile helpers)
- building_renderer.py            : BuildingRenderer (roofs, interiors, floor numbers)
- unit_renderer.py                : UnitRenderer (unit drawing, damage VFX)
- decoration_renderer.py          : DecorationRenderer (bushes, trees, wreckage, etc.)
- ui_overlay_renderer.py          : UIOverlayRenderer (VL flags, attack lines, HUD, grid)
- environment_renderer.py         : EnvironmentRenderer (lighting, weather composition)
- screen_effects_renderer.py      : ScreenEffectsRenderer (flash, suppression, weather overlay)
- world_renderer.py               : WorldRenderer (terrain + units orchestration)
- unit_position_interpolator.py   : UnitPositionInterpolator (P2-04 smooth positions)
- unit_fade_renderer.py           : UnitFadeRenderer (P2-02 death fade ghosts)
- renderer_state_manager.py       : RendererStateManager (display/surface/cache lifecycle)
- combat_effects_coordinator.py   : CombatEffectsCoordinator (high-level combat VFX)
- atmosphere_controller.py        : AtmosphereController (weather/flash/shell state)

BACKWARD COMPATIBILITY: All public APIs remain unchanged.
External code can continue importing from this file as before.

CC2 Visual Style Reference:
- Tile Size: 48×48 pixels (square, not diamond)
- Projection: Orthographic Top-Down
- Palette: Muted earthy military tones
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pygame

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.presentation.rendering.isometric_renderer import IsometricRenderer
    from pycc2.presentation.rendering.sprite_renderer import SpriteRenderer

from pycc2.presentation.rendering.atmosphere_controller import AtmosphereController
from pycc2.presentation.rendering.autotile_system import AutotileCache
from pycc2.presentation.rendering.building_renderer import BuildingRenderer
from pycc2.presentation.rendering.camera import ProjectionMode
from pycc2.presentation.rendering.combat_effects_coordinator import CombatEffectsCoordinator
from pycc2.presentation.rendering.decoration_renderer import DecorationRenderer
from pycc2.presentation.rendering.enhanced_renderer_delegate_mixin import (
    EnhancedRendererDelegateMixin,
)
from pycc2.presentation.rendering.environment_renderer import EnvironmentRenderer
from pycc2.presentation.rendering.lighting_effects import LightingEffectsSystem
from pycc2.presentation.rendering.lighting_system import LightingSystem, TopDownLightingConfig
from pycc2.presentation.rendering.palette_generator import PaletteGenerator
from pycc2.presentation.rendering.particle_effects_renderer import ParticleEffectsRenderer
from pycc2.presentation.rendering.particle_system import TopDownParticleSystem
from pycc2.presentation.rendering.procedural_texture_generator import (
    ProceduralTextureGenerator,
)
from pycc2.presentation.rendering.render_context import RenderContext
from pycc2.presentation.rendering.renderer_state_manager import RendererStateManager
from pycc2.presentation.rendering.screen_effects_renderer import ScreenEffectsRenderer
from pycc2.presentation.rendering.shadow_rendering_system import ShadowRenderingSystem
from pycc2.presentation.rendering.shadow_system import ShadowRenderer
from pycc2.presentation.rendering.suppression_overlay_renderer import SuppressionOverlayRenderer
from pycc2.presentation.rendering.terrain_renderer import TerrainRenderer
from pycc2.presentation.rendering.terrain_rendering_system import TerrainRenderingSystem
from pycc2.presentation.rendering.terrain_tile_cache import TerrainTileCache
from pycc2.presentation.rendering.ui_overlay_renderer import UIOverlayRenderer
from pycc2.presentation.rendering.unit_fade_renderer import UnitFadeRenderer
from pycc2.presentation.rendering.unit_position_interpolator import UnitPositionInterpolator
from pycc2.presentation.rendering.unit_renderer import UnitRenderer
from pycc2.presentation.rendering.world_renderer import WorldRenderer
from pycc2.presentation.ui.theme import ThemeManager


class EnhancedRenderer(EnhancedRendererDelegateMixin):
    """
    CC2-Authentic terrain renderer for PyCC2 maps.

    Renders tiles with authentic Close Combat 2 visual style:
    - 48×48 pixel tiles (orthographic top-down)
    - CC2 terrain palette from screenshot analysis
    - Procedural texture generation with variation
    - Supports dual projection modes:
      * ORTHOGRAPHIC: Classic top-down rendering (default, CC2-style)
      * ISOMETRIC: 2:1 isometric diamond rendering
    """

    TILE_SIZE = 48  # CC2 authentic: 48×48 pixel tiles

    @property
    def _screen(self) -> pygame.Surface | None:
        """Backward-compatible delegate to RendererStateManager."""
        return self._state_manager.screen

    @property
    def _offscreen(self) -> pygame.Surface | None:
        """Backward-compatible delegate to RendererStateManager."""
        return self._state_manager.offscreen

    def __init__(
        self, attack_line_system=None, lighting_config: TopDownLightingConfig | None = None
    ):
        self._state_manager = RendererStateManager(self.TILE_SIZE)
        self._palette_gen = PaletteGenerator()
        self._texture_cache: dict[tuple[int, int], pygame.Surface] = {}
        self._scaled_texture_cache: dict[tuple[int, int, int], pygame.Surface] = {}
        self._height_lit_cache: dict[tuple[int, int, int, int], pygame.Surface] = {}
        self._sprite_cache: dict[str, pygame.Surface] = {}
        self._autotile_cache = AutotileCache()
        self._terrain_tile_cache = TerrainTileCache(self.TILE_SIZE)
        self._building_clusters: list[list[tuple[int, int]]] | None = None
        self._frame_count = 0
        self._sprite_renderer: SpriteRenderer | None = None
        self._isometric_renderer: IsometricRenderer | None = None
        self._shadow_renderer = ShadowRenderer()
        self._shadow_rendering_sys = ShadowRenderingSystem(self._shadow_renderer, self.TILE_SIZE)
        self._attack_line_system = attack_line_system
        self._particle_system = TopDownParticleSystem()

        self._lighting_config = lighting_config or TopDownLightingConfig()
        self._lighting_effects_sys = LightingEffectsSystem(
            self._lighting_config, self.TILE_SIZE, max_dynamic_lights=8
        )
        self._terrain_rendering_sys = TerrainRenderingSystem(self, self.TILE_SIZE)

        # RenderContext is initialized with callbacks to subsystem methods that already exist.
        # Callbacks pointing to UnitRenderer/DecorationRenderer are set after those are created.
        self._render_ctx = RenderContext(
            tile_size=self.TILE_SIZE,
            screen=self._state_manager.screen,
            offscreen=self._state_manager.offscreen,
            sprite_renderer=self._sprite_renderer,
            palette_gen=self._palette_gen,
            texture_cache=self._texture_cache,
            scaled_texture_cache=self._scaled_texture_cache,
            height_lit_cache=self._height_lit_cache,
            autotile_cache=self._autotile_cache,
            terrain_tile_cache=self._terrain_tile_cache,
            building_clusters=self._building_clusters,
            sprite_cache=self._sprite_cache,
            get_pooled_surface=self._state_manager.get_pooled_surface,
            get_cached_texture=self._terrain_rendering_sys.get_cached_texture,
            get_enhanced_tile=self._terrain_rendering_sys._get_enhanced_tile,
            get_terrain_at=self._terrain_rendering_sys.get_terrain_at,
            generate_cc2_style_tile=self._terrain_rendering_sys._generate_cc2_style_tile,
            apply_height_lighting=self._lighting_effects_sys.apply_height_lighting,
            get_health_tinted_color=self._lighting_effects_sys.get_health_tinted_color,
            draw_terrain_borders=self._terrain_rendering_sys.draw_terrain_borders,
        )

        self._terrain_renderer = TerrainRenderer(self._render_ctx)
        self._unit_renderer = UnitRenderer(self._render_ctx)
        self._building_renderer = BuildingRenderer(self._render_ctx)
        self._decoration_renderer = DecorationRenderer(self._render_ctx)
        self._lighting_system = LightingSystem(self._lighting_config)

        # Late-bind callbacks that need sub-renderer instances.
        self._render_ctx.draw_decorations = self._decoration_renderer.draw_decorations
        self._render_ctx.draw_direction_indicator = self._unit_renderer.draw_direction_indicator
        self._render_ctx.draw_movement_mode_overlay = self._unit_renderer.draw_movement_mode_overlay

        self._particle_effects = ParticleEffectsRenderer()
        self._environment = EnvironmentRenderer()
        self._ui_overlay = UIOverlayRenderer(self._render_ctx)

        self._enable_cc2_color_grading: bool = True
        self._hud = None
        self._hud_enabled: bool = True

        # Extracted SRP modules
        self._unit_position_interpolator = UnitPositionInterpolator()
        self._unit_fade_renderer = UnitFadeRenderer()
        self._screen_effects = ScreenEffectsRenderer()
        self._suppression_overlay = SuppressionOverlayRenderer()
        self._world_renderer: WorldRenderer | None = None

        self._atmosphere = AtmosphereController()

        self._combat_effects = CombatEffectsCoordinator(
            particle_effects=self._particle_effects,
            unit_fade_renderer=self._unit_fade_renderer,
            environment_renderer=self._environment,
        )

    def initialize(self, screen: pygame.Surface) -> None:
        """Initialize renderer with display surface."""
        offscreen = self._state_manager.initialize(screen)

        try:
            from pycc2.presentation.rendering.sprite_renderer import SpriteRenderer

            self._sprite_renderer = SpriteRenderer()
            self._sprite_renderer.initialize(screen)
            logger.info("SpriteRenderer initialized with PNG support")
        except RuntimeError as e:
            import warnings

            warnings.warn(f"SpriteRenderer initialization failed: {e}", stacklevel=2)
            self._sprite_renderer = None

        self._particle_effects.set_dependencies(
            sprite_renderer=self._sprite_renderer,
            particle_system=self._particle_system,
            offscreen=offscreen,
            surface_pool_fn=self._state_manager.get_pooled_surface,
        )
        self._environment.set_dependencies(
            lighting_effects_sys=self._lighting_effects_sys,
            lighting_config=self._lighting_config,
            offscreen=offscreen,
        )

        self._render_ctx.update_surfaces(screen, offscreen)
        self._render_ctx.sprite_renderer = self._sprite_renderer

        # Initialize the world-orchestration renderer now that all subsystems exist.
        self._world_renderer = WorldRenderer(
            terrain_rendering_sys=self._terrain_rendering_sys,
            decoration_renderer=self._decoration_renderer,
            shadow_rendering_sys=self._shadow_rendering_sys,
            dynamic_shadow_sys=getattr(self, "_dynamic_shadow_sys", None),
            building_renderer=self._building_renderer,
            ui_overlay_renderer=self._ui_overlay,
            environment_renderer=self._environment,
            unit_renderer=self._unit_renderer,
            unit_fade_renderer=self._unit_fade_renderer,
        )

        try:
            from pycc2.presentation.rendering.pixel_artist_3d import PixelArtist3D

            PixelArtist3D.precache_tank_rotations()
            logger.info("Tank rotation precache complete")
        except (pygame.error, ValueError, OSError) as e:
            logger.warning("Tank rotation precache skipped: %s", e)

        self.set_weather("light_fog")
        logger.info("Weather overlay set to default: light_fog")

        ThemeManager()
        ThemeManager.set_theme("default")
        logger.info("ThemeManager initialized with 'default' theme")

    def set_attack_line_system(self, attack_line_system) -> None:
        """Set attack line system (dependency injection setter - P0-2 Fix)."""
        self._attack_line_system = attack_line_system
        self._ui_overlay.set_attack_line_system(attack_line_system)

    def set_projectile_trail_system(self, trail_system) -> None:
        """Set projectile trail system (dependency injection setter)."""
        self._projectile_trail_sys = trail_system

    def set_dynamic_shadow_system(self, shadow_system) -> None:
        """Set dynamic shadow system (dependency injection setter)."""
        self._dynamic_shadow_sys = shadow_system
        if self._world_renderer is not None:
            self._world_renderer._dynamic_shadow_sys = shadow_system

    def set_time_of_day(self, tod: str) -> None:
        """Set time of day for color grading."""
        self._environment.set_time_of_day(tod)

    def set_light_intensity(self, intensity: float) -> None:
        """Set global light intensity."""
        self._environment.set_light_intensity(intensity)

    def get_lighting_config(self) -> TopDownLightingConfig:
        """Get current lighting configuration (read-only access)."""
        return self._environment.get_lighting_config()

    def set_cc2_color_grading(self, enable: bool) -> None:
        self._enable_cc2_color_grading = enable
        logger.debug("CC2 color grading: %s", "enabled" if enable else "disabled")

    def set_hud(self, hud) -> None:
        self._hud = hud

    def enable_hud(self, enabled: bool = True) -> None:
        self._hud_enabled = enabled

    # ====== P2-03: Screen Flash Overlay System ======

    def trigger_flash(
        self,
        color: tuple[int, int, int] = (255, 255, 255),
        intensity: float = 0.4,
        duration: float = 0.12,
    ) -> None:
        """Trigger a screen flash overlay effect."""
        self._atmosphere.trigger_flash(color, intensity, duration)

    def update_flash(self, dt: float) -> None:
        """Update screen flash alpha (call once per frame in update phase)."""
        self._atmosphere.update_flash(dt)

    # ====== P2-04: Smooth Unit Position Interpolation ======

    def _smooth_positions(self, units: list, dt: float) -> None:
        """Lerp displayed unit positions toward real pixel positions."""
        self._unit_position_interpolator.smooth_positions(units, dt)

    def get_smooth_position(self, unit_id: str) -> tuple[float, float] | None:
        """Return the smoothed (lerped) position for a unit, or None if not tracked."""
        return self._unit_position_interpolator.get_smooth_position(unit_id)

    # ====== P3-01: Weather Atmosphere Overlay System ======

    def set_weather(self, mode: str) -> None:
        """Set weather overlay mode: 'clear', 'light_fog', 'dust', or 'smoke'."""
        self._atmosphere.set_weather(mode)

    def update_weather(self, dt: float) -> None:
        """Update weather animation state each frame."""
        self._atmosphere.update_weather(dt)

    # ====== P3-02: Shell Casing Ejection System ======

    def spawn_shell_casing(self, x: float, y: float, direction_rad: float = 0) -> None:
        """Spawn a shell casing ejected from weapon position."""
        self._atmosphere.spawn_shell_casing(x, y, direction_rad)

    def update_shell_casings(self, dt: float) -> None:
        """Update shell casing physics simulation."""
        self._atmosphere.update_shell_casings(dt)

    def update_suppression_overlay(self, dt: float, units: list | None = None) -> None:
        """Update suppression overlay alpha based on player unit morale states."""
        self._suppression_overlay.update(dt, units)

    def render_shell_casings(self, camera) -> None:
        """Render shell casings as small ellipses with fade-out."""
        self._atmosphere.render_shell_casings(self._state_manager.offscreen, camera)

    def _get_pooled_surface(self, size: tuple[int, int]) -> pygame.Surface:
        """Get or create a surface from the object pool with LRU eviction."""
        return self._state_manager.get_pooled_surface(size)

    def _invalidate_surface_cache(self) -> None:
        """Clear surface pool when screen size changes."""
        self._state_manager.invalidate_cache()
        self._screen_effects.invalidate_cache()

    def render(
        self,
        game_map: GameMap,
        units: list[Unit],
        camera: Camera,
        alpha: float = 1.0,
        selected_unit_ids: set[str] | None = None,
        debug_mode: bool = False,
    ) -> None:
        """
        Main render entry point.

        Pipeline:
        1. Clear off-screen buffer
        2. Draw terrain, buildings, shadows
        3. Draw units and combat overlays
        4. Draw weather, lighting, particles
        5. Draw HUD and screen effects
        6. Atomic blit off-screen -> display surface
        """
        if self._state_manager.screen is None:
            return

        # Phase 6: record frame timing for FPS adaptive post-processing.
        self._state_manager.update_fps()

        if camera.projection == ProjectionMode.ISOMETRIC:
            self._render_isometric(game_map, units, camera, selected_unit_ids, debug_mode)
            return

        self._frame_count += 1

        offscreen = self._state_manager.ensure_offscreen()
        if offscreen is None:
            return
        screen = self._state_manager.screen
        self._render_ctx.update_surfaces(screen, offscreen)

        theme_bg = ThemeManager.get_current().colors.background
        offscreen.fill(theme_bg)

        if self._world_renderer is not None:
            self._world_renderer.render_terrain(
                offscreen, game_map, camera, debug_mode, units, self._state_manager.dirty_tracker
            )
            self._world_renderer.render_units(
                offscreen,
                units,
                camera,
                selected_unit_ids,
                self._unit_position_interpolator.get_all_positions(),
                self._state_manager.dirty_tracker,
                self._attack_line_system,
            )

        self._environment.render_weather_and_lighting(
            offscreen,
            camera,
            self._particle_system,
            getattr(self, "_projectile_trail_sys", None),
            self._atmosphere.shell_sys,
            self._state_manager.dirty_tracker,
        )

        self._ui_overlay.render_hud(self._hud, self._hud_enabled, self._state_manager.dirty_tracker)

        self._screen_effects.render_effects(
            offscreen,
            self._atmosphere.flash_sys,
            self._atmosphere.weather_sys,
            self._state_manager.dirty_tracker,
        )

        screen.blit(offscreen, (0, 0))

        post_processing = self._state_manager.post_processing
        if (
            post_processing is not None
            and self._enable_cc2_color_grading
            and self._state_manager.is_post_processing_active
        ):
            try:
                processed = post_processing.apply_all(screen, color_style="war")
                if processed is not None:
                    screen.blit(processed, (0, 0))
            except (pygame.error, ValueError, TypeError) as exc:
                logger.debug("Post-processing skipped: %s", exc)

    def render_los_overlay(self, surface: pygame.Surface, unit, game_map, camera) -> None:
        """Delegate to UIOverlayRenderer for LOS visualization."""
        self._ui_overlay.render_los_overlay(surface, unit, game_map, camera)

    def _draw_attack_lines(self, camera: Camera) -> None:
        """Backward-compatible delegate to UIOverlayRenderer."""
        self._ui_overlay.draw_attack_lines(camera)

    def shutdown(self) -> None:
        """Clean up renderer resources."""
        self._texture_cache.clear()
        self._scaled_texture_cache.clear()
        self._height_lit_cache.clear()
        self._sprite_cache.clear()
        self._autotile_cache.clear()
        self._terrain_tile_cache.clear()
        self._building_clusters = None
        if hasattr(self._terrain_renderer, "_transition_cache"):
            self._terrain_renderer._transition_cache.clear()
        if hasattr(self._terrain_renderer, "_edge_smooth_cache"):
            self._terrain_renderer._edge_smooth_cache.clear()
        self._state_manager.shutdown()
        self._unit_position_interpolator.clear()
        self._unit_fade_renderer.clear()
        self._screen_effects.invalidate_cache()

    def resize(self, width: int, height: int) -> None:
        """Handle window resize - reinitialize offscreen buffer and dirty tracker."""
        self._state_manager.resize(width, height)
        self._atmosphere.update_screen_size(width, height)
        self._screen_effects.invalidate_cache()
        self._render_ctx.update_surfaces(
            self._state_manager.screen, self._state_manager.offscreen
        )


# Backward-compatible re-exports for consumers that historically imported from
# this module. ProceduralTextureGenerator is intentionally not used internally.
__all__ = ["EnhancedRenderer", "ProceduralTextureGenerator"]
