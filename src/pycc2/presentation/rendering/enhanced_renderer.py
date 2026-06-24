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
- sprite_generator.py     : SpriteGenerator class (all programmatic sprite creation)
- particle_system.py      : TopDownParticleSystem class (explosions, smoke, etc.)
- lighting_system.py      : TopDownLightingConfig + LightingSystem (time-of-day, dynamic lights)
- terrain_renderer.py     : TerrainRenderer (enhanced terrain, transitions, edge smoothing)
- building_renderer.py    : BuildingRenderer (roofs, interiors, floor numbers)
- unit_renderer.py        : UnitRenderer (unit drawing, damage VFX)
- decoration_renderer.py  : DecorationRenderer (bushes, trees, wreckage, etc.)

BACKWARD COMPATIBILITY: All public APIs remain unchanged.
External code can continue importing from this file as before.

CC2 Visual Style Reference:
- Tile Size: 48×48 pixels (square, not diamond)
- Projection: Orthographic Top-Down
- Palette: Muted earthy military tones
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

import pygame

from pycc2.presentation.rendering.dirty_rect_tracker import _DirtyRectTracker
from pycc2.presentation.rendering.surface_pool import SurfacePool

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.presentation.rendering.camera import Camera

# Import autotile system for cross-tile visual continuity
from pycc2.presentation.rendering.autotile_system import (
    AutotileCache,
)
from pycc2.presentation.rendering.building_renderer import BuildingRenderer
from pycc2.presentation.rendering.camera import ProjectionMode
from pycc2.presentation.rendering.decoration_renderer import DecorationRenderer
from pycc2.presentation.rendering.environment_renderer import EnvironmentRenderer
from pycc2.presentation.rendering.flash_effect_system import FlashEffectSystem
from pycc2.presentation.rendering.lighting_effects import LightingEffectsSystem
from pycc2.presentation.rendering.lighting_system import LightingSystem, TopDownLightingConfig
from pycc2.presentation.rendering.palette_generator import PaletteGenerator

# Import extracted sub-modules (SRP refactoring)
from pycc2.presentation.rendering.particle_effects_renderer import ParticleEffectsRenderer
from pycc2.presentation.rendering.particle_system import TopDownParticleSystem
from pycc2.presentation.rendering.post_processing import PostProcessingEffects
from pycc2.presentation.rendering.procedural_texture_generator import ProceduralTextureGenerator
from pycc2.presentation.rendering.render_context import RenderContext
from pycc2.presentation.rendering.shadow_rendering_system import ShadowRenderingSystem

# Import shadow system for SE-direction shadows
from pycc2.presentation.rendering.shadow_system import ShadowRenderer
from pycc2.presentation.rendering.shell_casing_system import ShellCasingSystem

# Import refactored modules (backward-compatible re-exports)
from pycc2.presentation.rendering.sprite_generator import SpriteGenerator
from pycc2.presentation.rendering.terrain_renderer import TerrainRenderer
from pycc2.presentation.rendering.terrain_rendering_system import TerrainRenderingSystem
from pycc2.presentation.rendering.terrain_tile_cache import (
    TerrainTileCache,
)
from pycc2.presentation.rendering.ui_overlay_renderer import UIOverlayRenderer
from pycc2.presentation.rendering.unit_renderer import UnitRenderer
from pycc2.presentation.rendering.weather_system import WeatherSystem
from pycc2.presentation.ui.theme import ThemeManager

# ============================================================


class EnhancedRenderer:
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

    # Rendering constants (extracted magic numbers for maintainability)
    WARM_OVERLAY_COLOR = (255, 220, 160, 12)  # Subtle orange-gold tint
    VIGNETTE_MIN_EDGE = 30  # Minimum vignette edge dimension (pixels)
    VIGNETTE_MAX_ALPHA = 40  # Maximum vignette darkness
    TRANSITION_STRIP_WIDTH_MIN = 5  # Minimum terrain transition strip width
    TRANSITION_STRIP_WIDTH_MAX = 7  # Maximum terrain transition strip width
    EDGE_SMOOTH_WIDTH_MIN = 2  # Minimum edge smoothing width
    EDGE_SMOOTH_WIDTH_MAX = 3  # Maximum edge smoothing width
    EDGE_SMOOTH_ALPHA_PEAK = 45  # Peak alpha for edge smoothing
    TRANSITION_ALPHA_PEAK = 140  # Peak alpha for terrain transitions
    MIN_FONT_SIZE = 10  # Minimum UI font size (pixels)
    TRANSPARENT_BLACK = (0, 0, 0, 0)  # Fully transparent color

    def __init__(
        self, attack_line_system=None, lighting_config: TopDownLightingConfig | None = None
    ):
        self._screen: pygame.Surface | None = None
        self._offscreen: pygame.Surface | None = None  # Off-screen buffer to eliminate flicker
        self._palette_gen = PaletteGenerator()
        self._texture_cache: dict[tuple[int, int], pygame.Surface] = {}
        self._scaled_texture_cache: dict[tuple[int, int, int], pygame.Surface] = {}
        self._height_lit_cache: dict[tuple[int, int, int, int], pygame.Surface] = {}
        self._sprite_cache: dict[str, pygame.Surface] = {}
        self._autotile_cache = AutotileCache()  # Cache for autotile variants
        self._terrain_tile_cache = TerrainTileCache(
            self.TILE_SIZE
        )  # Pre-computed terrain tile cache with edge smoothing
        self._building_clusters: list[list[tuple[int, int]]] | None = (
            None  # Cached building clusters
        )
        self._frame_count = 0
        self._sprite_renderer = None  # 延迟初始化，等待display ready
        self._isometric_renderer = None  # Isometric renderer (lazy init)
        self._shadow_renderer = ShadowRenderer()  # SE-direction shadow system
        self._shadow_rendering_sys = ShadowRenderingSystem(
            self._shadow_renderer, self.TILE_SIZE
        )  # Unified shadow coordinator
        self._attack_line_system = attack_line_system  # Dependency injection for attack line system
        self._particle_system = TopDownParticleSystem()  # Top-down particle effects system

        # Top-down lighting system configuration
        self._lighting_config = lighting_config or TopDownLightingConfig()

        # Initialize lighting effects system (time-of-day, CC2 grading, dynamic lights)
        self._lighting_effects_sys = LightingEffectsSystem(
            self._lighting_config, self.TILE_SIZE, max_dynamic_lights=8
        )

        # Initialize terrain rendering system (extracted from EnhancedRenderer)
        self._terrain_rendering_sys = TerrainRenderingSystem(self, self.TILE_SIZE)

        # Surface object pool - eliminate per-frame allocation (PERF-001)
        # LRU eviction strategy: max 50 surfaces, evict least recently used
        self._surface_pool = SurfacePool(max_size=50)
        self._cached_screen_size: tuple[int, int] | None = None
        self._cached_warm_overlay: pygame.Surface | None = None
        self._cached_vignette: pygame.Surface | None = None

        # Initialize refactored sub-module renderers via RenderContext (DI pattern)
        self._render_ctx = RenderContext(
            tile_size=self.TILE_SIZE,
            screen=self._screen,
            offscreen=self._offscreen,
            sprite_renderer=self._sprite_renderer,
            palette_gen=self._palette_gen,
            texture_cache=self._texture_cache,
            scaled_texture_cache=self._scaled_texture_cache,
            height_lit_cache=self._height_lit_cache,
            autotile_cache=self._autotile_cache,
            terrain_tile_cache=self._terrain_tile_cache,
            building_clusters=self._building_clusters,
            sprite_cache=self._sprite_cache,
            get_pooled_surface=self._get_pooled_surface,
            get_cached_texture=self._get_cached_texture,
            get_enhanced_tile=self._get_enhanced_tile,
            get_terrain_at=self._get_terrain_at,
            generate_cc2_style_tile=self._generate_cc2_style_tile,
            apply_height_lighting=self._apply_height_lighting,
            get_health_tinted_color=self._get_health_tinted_color,
            draw_direction_indicator=self._draw_direction_indicator,
            draw_movement_mode_overlay=self._draw_movement_mode_overlay,
            draw_terrain_borders=self._draw_terrain_borders,
            draw_decorations=self._draw_decorations,
        )
        self._terrain_renderer = TerrainRenderer(self._render_ctx)
        self._unit_renderer = UnitRenderer(self._render_ctx)
        self._building_renderer = BuildingRenderer(self._render_ctx)
        self._decoration_renderer = DecorationRenderer(self._render_ctx)
        self._lighting_system = LightingSystem(self._lighting_config)

        # Initialize extracted SRP modules (delegate pattern for backward compatibility)
        self._particle_effects = ParticleEffectsRenderer()
        self._environment = EnvironmentRenderer()
        self._ui_overlay = UIOverlayRenderer(self._render_ctx)

        # Post-processing effects (vignette + color grading / desaturation)
        # Created in initialize() when screen dimensions are known
        self._post_processing: PostProcessingEffects | None = None

        # Dirty rectangle tracker for partial display updates (PERF)
        # Set to None to disable; initialized in initialize() when screen size known
        self._dirty_tracker: _DirtyRectTracker | None = None

        self._enable_cc2_color_grading: bool = True
        self._hud = None
        self._hud_enabled: bool = True

        # P2-02: Death fade-out animation tracking
        # {unit_id: {"position": Vec2, "alpha": int, "start_time": int, "duration_ms": int}}
        self._fading_units: dict[str, dict] = {}

        # P2-03: Screen flash overlay system (white/red flash on explosion / kill)
        # Delegated to FlashEffectSystem
        self._flash_sys = FlashEffectSystem()

        # P2-04: Smooth unit position interpolation (lerp toward real position)
        self._unit_positions: dict[str, tuple[float, float]] = {}  # unit_id → displayed (x, y)

        # P3-01: Weather atmosphere overlay system
        # Delegated to WeatherSystem
        self._weather_sys = WeatherSystem()

        # P3-02: Shell casing ejection system
        # Delegated to ShellCasingSystem
        self._shell_sys = ShellCasingSystem()

        # Suppression overlay: red edge flash when player units are pinned/broken
        self._suppression_overlay_alpha: float = 0.0
        self._suppression_overlay_max_alpha: float = 80.0
        self._suppression_overlay_decay: float = 120.0  # alpha units per second

        # Cached full-screen overlay surfaces (avoid per-frame allocation)
        self._suppression_overlay_cache: pygame.Surface | None = None
        self._flash_surf_cache: pygame.Surface | None = None

    def initialize(self, screen: pygame.Surface) -> None:
        """Initialize renderer with display surface."""
        self._screen = screen
        try:
            # FIXED: Use SRCALPHA to support transparent shadows
            self._offscreen = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        except pygame.error as e:
            # Fallback for headless/testing environments without video mode set
            import warnings

            warnings.warn(
                f"Could not create SRCALPHA surface: {e}. Using convert() fallback.", stacklevel=2
            )
            self._offscreen = pygame.Surface(screen.get_size()).convert()

        # Initialize post-processing effects (desaturation, vignette)
        # This was a ghost feature: code existed but instance was never created
        try:
            sw, sh = screen.get_size()
            self._post_processing = PostProcessingEffects(sw, sh)
            self._post_processing.enable_color_grading()  # Enable CC2 war atmosphere desaturation
            logger.info("PostProcessingEffects initialized with color grading enabled")

            # Initialize dirty rectangle tracker for partial display updates
            self._dirty_tracker = _DirtyRectTracker(sw, sh)
            logger.info("DirtyRectTracker initialized (%dx%d, max_rects=16)", sw, sh)
        except (pygame.error, ValueError, RuntimeError) as e:
            logger.warning("PostProcessingEffects init failed (non-critical): %s", e)
            self._post_processing = None

        # 现在display已初始化，可以创建SpriteRenderer加载PNG
        try:
            from pycc2.presentation.rendering.sprite_renderer import SpriteRenderer

            self._sprite_renderer = SpriteRenderer()
            self._sprite_renderer.initialize(screen)
            logger.info("✅ SpriteRenderer initialized with PNG support")
        except RuntimeError as e:
            import warnings

            warnings.warn(f"SpriteRenderer initialization failed: {e}", stacklevel=2)
            self._sprite_renderer = None

        # Configure extracted sub-modules with dependencies (delegate pattern)
        self._particle_effects.set_dependencies(
            sprite_renderer=self._sprite_renderer,
            particle_system=self._particle_system,
            offscreen=self._offscreen,
            surface_pool_fn=self._get_pooled_surface,
        )

        self._environment.set_dependencies(
            lighting_effects_sys=self._lighting_effects_sys,
            lighting_config=self._lighting_config,
            offscreen=self._offscreen,
        )

        # Update RenderContext with initialized surfaces
        self._render_ctx.update_surfaces(self._screen, self._offscreen)
        self._render_ctx.sprite_renderer = self._sprite_renderer

        # Precache tank rotation surfaces (P0-4: size-based cache key enables cross-frame reuse)
        try:
            from pycc2.presentation.rendering.pixel_artist_3d import PixelArtist3D

            PixelArtist3D.precache_tank_rotations()
            logger.info("Tank rotation precache complete")
        except (pygame.error, ValueError, OSError) as e:
            logger.warning("Tank rotation precache skipped: %s", e)

        # Set default light fog atmosphere (P3-01: was ghost feature, now active)
        self.set_weather("light_fog")
        logger.info("Weather overlay set to default: light_fog")

        # Initialize ThemeManager with default theme for runtime theme switching
        # Ensure singleton exists first (registers default themes via __new__)
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

    def set_time_of_day(self, tod: str) -> None:
        """
        Set time of day for color grading.

        Args:
            tod: Time of day string - 'dawn'/'noon'/'dusk'/'night'

        Raises:
            ValueError: If tod is not a valid time of day
        """
        self._environment.set_time_of_day(tod)

    def set_light_intensity(self, intensity: float) -> None:
        """
        Set global light intensity.

        Args:
            intensity: Brightness level (0.0 = dark, 1.0 = normal, 2.0 = very bright)
        """
        self._environment.set_light_intensity(intensity)

    def get_lighting_config(self) -> TopDownLightingConfig:
        """
        Get current lighting configuration (read-only access).

        Returns:
            TopDownLightingConfig: Current lighting configuration
        """
        return self._environment.get_lighting_config()

    def set_cc2_color_grading(self, enable: bool) -> None:
        self._enable_cc2_color_grading = enable
        logger.debug(f"CC2 color grading: {'enabled' if enable else 'disabled'}")

    def set_hud(self, hud) -> None:
        self._hud = hud

    def enable_hud(self, enabled: bool = True) -> None:
        self._hud_enabled = enabled

    # ====== P2-03: Screen Flash Overlay System (delegated to FlashEffectSystem) ======

    def trigger_flash(
        self,
        color: tuple[int, int, int] = (255, 255, 255),
        intensity: float = 0.4,
        duration: float = 0.12,
    ) -> None:
        """Trigger a screen flash overlay effect.

        Args:
            color: RGB tuple for flash color (white for explosions, red for kills).
            intensity: Peak alpha multiplier (0.0–1.0).
            duration: Flash fade-out duration in seconds.
        """
        self._flash_sys.trigger(color, intensity, duration)

    def update_flash(self, dt: float) -> None:
        """Update screen flash alpha (call once per frame in update phase).

        Uses ease-out quad curve for natural fade-out feel.
        """
        self._flash_sys.update(dt)

    # ====== P2-04: Smooth Unit Position Interpolation ======

    LERP_SPEED = 12.0  # units per second — higher = snappier tracking

    def _smooth_positions(self, units: list, dt: float) -> None:
        """Lerp displayed unit positions toward real pixel positions.

        Call this once per frame before rendering units so they glide
        smoothly instead of snapping grid-to-grid.
        """
        alive_ids: set[str] = set()
        for unit in units:
            if not hasattr(unit, "id") or not hasattr(unit, "position"):
                continue
            if unit.position is None or not hasattr(unit.position, "pixel_position"):
                continue

            alive_ids.add(unit.id)

            try:
                real_x = float(unit.position.pixel_position.x)
                real_y = float(unit.position.pixel_position.y)
            except (AttributeError, TypeError):
                continue

            if unit.id not in self._unit_positions:
                # First seen — snap to real position immediately
                self._unit_positions[unit.id] = (real_x, real_y)
            else:
                dx = real_x - self._unit_positions[unit.id][0]
                dy = real_y - self._unit_positions[unit.id][1]
                dist = math.sqrt(dx * dx + dy * dy)
                if dist > 0.1:
                    step = min(self.LERP_SPEED * dt, dist)
                    self._unit_positions[unit.id] = (
                        self._unit_positions[unit.id][0] + dx * step / dist,
                        self._unit_positions[unit.id][1] + dy * step / dist,
                    )
                else:
                    # Close enough — snap to avoid endless micro-movement
                    self._unit_positions[unit.id] = (real_x, real_y)

        # Clean up dead / removed units
        self._unit_positions = {k: v for k, v in self._unit_positions.items() if k in alive_ids}

    def get_smooth_position(self, unit_id: str) -> tuple[float, float] | None:
        """Return the smoothed (lerped) position for a unit, or None if not tracked."""
        return self._unit_positions.get(unit_id)

    # ====== P3-01: Weather Atmosphere Overlay System (delegated to WeatherSystem) ======

    def set_weather(self, mode: str) -> None:
        """Set weather overlay mode: 'clear', 'light_fog', 'dust', or 'smoke'."""
        self._weather_sys.set_mode(mode)

    def update_weather(self, dt: float) -> None:
        """Update weather animation state each frame."""
        self._weather_sys.update(dt)

    # ====== P3-02: Shell Casing Ejection System (delegated to ShellCasingSystem) ======

    def spawn_shell_casing(self, x: float, y: float, direction_rad: float = 0) -> None:
        """Spawn a shell casing ejected from weapon position.

        Args:
            x: World X coordinate of ejection point.
            y: World Y coordinate of ejection point.
            direction_rad: Firing direction in radians (ejection is perpendicular).
        """
        self._shell_sys.spawn(x, y, direction_rad)

    def update_shell_casings(self, dt: float) -> None:
        """Update shell casing physics simulation."""
        self._shell_sys.update(dt)

    def update_suppression_overlay(self, dt: float, units: list | None = None) -> None:
        """Update suppression overlay alpha based on player unit morale states.

        When player-controlled units are PINNED or BROKEN, increase the red
        edge overlay alpha.  Alpha decays over time when no units are suppressed.

        Args:
            dt: Delta time in seconds.
            units: List of units to check for morale state (optional).
        """
        from pycc2.domain.systems.morale_system import MoraleState, MoraleSystem

        suppressed_count = 0
        if units is not None:
            for unit in units:
                if not unit.is_alive:
                    continue
                # Only count ally/player units
                if hasattr(unit, "side") and unit.side not in ("allies", "ally"):
                    continue
                if hasattr(unit, "morale") and unit.morale is not None:
                    morale_state = MoraleSystem.get_state(unit.morale.value)
                    if morale_state in (MoraleState.PINNED, MoraleState.BROKEN):
                        suppressed_count += 1

        if suppressed_count > 0:
            # Increase alpha proportional to number of suppressed units
            target_alpha = min(
                self._suppression_overlay_max_alpha,
                30.0 + suppressed_count * 20.0,
            )
            # Quick ramp-up
            self._suppression_overlay_alpha = min(
                target_alpha,
                self._suppression_overlay_alpha + 200.0 * dt,
            )
        else:
            # Decay alpha over time
            self._suppression_overlay_alpha = max(
                0.0,
                self._suppression_overlay_alpha - self._suppression_overlay_decay * dt,
            )

    def render_shell_casings(self, camera) -> None:
        """Render shell casings as small ellipses with fade-out."""
        self._shell_sys.render(self._offscreen, camera)

    def _render_suppression_overlay(self) -> None:
        """Render semi-transparent red edge overlay for suppression feedback.

        Draws a red vignette-like border that pulses when player units are
        PINNED or BROKEN.  The alpha is controlled by _suppression_overlay_alpha
        which ramps up when suppressed units exist and decays when they don't.
        """
        if self._offscreen is None:
            return

        sw, sh = self._offscreen.get_size()
        alpha = int(max(0, min(255, self._suppression_overlay_alpha)))
        if alpha < 2:
            return

        # Mark full dirty since this is a screen-wide overlay
        if self._dirty_tracker is not None:
            self._dirty_tracker.mark_full_dirty()

        # Reuse cached overlay surface (avoid per-frame allocation)
        if (
            self._suppression_overlay_cache is None
            or self._suppression_overlay_cache.get_size() != (sw, sh)
        ):
            self._suppression_overlay_cache = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay = self._suppression_overlay_cache
        overlay.fill((0, 0, 0, 0))  # Clear for reuse

        # Draw red gradient strips along all four edges
        edge_width = min(60, sw // 6)
        edge_height = min(60, sh // 6)
        red = (200, 30, 30)

        # Top edge
        for i in range(edge_height):
            a = int(alpha * (1.0 - i / edge_height))
            if a < 1:
                break
            pygame.draw.line(overlay, (*red, a), (0, i), (sw, i))

        # Bottom edge
        for i in range(edge_height):
            a = int(alpha * (1.0 - i / edge_height))
            if a < 1:
                break
            y = sh - 1 - i
            pygame.draw.line(overlay, (*red, a), (0, y), (sw, y))

        # Left edge
        for i in range(edge_width):
            a = int(alpha * (1.0 - i / edge_width))
            if a < 1:
                break
            pygame.draw.line(overlay, (*red, a), (i, 0), (i, sh))

        # Right edge
        for i in range(edge_width):
            a = int(alpha * (1.0 - i / edge_width))
            if a < 1:
                break
            x = sw - 1 - i
            pygame.draw.line(overlay, (*red, a), (x, 0), (x, sh))

        self._offscreen.blit(overlay, (0, 0))

    def _get_pooled_surface(self, size: tuple[int, int]) -> pygame.Surface:
        """Get or create a surface from the object pool with LRU eviction (PERF-001).

        Delegates to the shared SurfacePool for consistent LRU behavior across
        all rendering subsystems.
        """
        surf = self._surface_pool.get(size)
        surf.fill(self.TRANSPARENT_BLACK)  # Clear for reuse
        return surf

    def _invalidate_surface_cache(self) -> None:
        """Clear surface pool when screen size changes (PERF-001)."""
        self._surface_pool.clear()
        self._cached_warm_overlay = None
        self._cached_vignette = None
        self._cached_screen_size = None
        self._suppression_overlay_cache = None
        self._flash_surf_cache = None

    def _rebuild_overlay_cache(self, width: int, height: int) -> None:
        """Rebuild cached full-screen overlay surfaces when screen size changes."""
        self._suppression_overlay_cache = pygame.Surface((width, height), pygame.SRCALPHA)
        self._flash_surf_cache = pygame.Surface((width, height), pygame.SRCALPHA)

    def _get_screen_overlays(
        self, screen_size: tuple[int, int]
    ) -> tuple[pygame.Surface, pygame.Surface]:
        """Delegate to EnvironmentRenderer for cached overlay surfaces."""
        return self._environment._get_screen_overlays(screen_size)

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
        1. Clear off-screen buffer (solid color, no alpha blending)
        2. Draw terrain, buildings, shadows
        3. Draw units and combat overlays
        4. Draw weather, lighting, particles
        5. Draw HUD and screen effects
        6. Atomic blit off-screen → display surface (eliminates flicker)
        """
        if self._screen is None:
            return

        # Isometric rendering branch
        if camera.projection == ProjectionMode.ISOMETRIC:
            self._render_isometric(game_map, units, camera, selected_unit_ids, debug_mode)
            return

        # Orthographic rendering (original pipeline)
        self._frame_count += 1

        # Ensure off-screen buffer matches display surface size (handles resize)
        screen_w, screen_h = self._screen.get_size()
        if self._offscreen is None or self._offscreen.get_size() != (screen_w, screen_h):
            # FIXED: Use SRCALPHA to support transparent shadows
            self._offscreen = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
            self._render_ctx.update_surfaces(self._screen, self._offscreen)

        # STEP 1: Clear off-screen buffer (use theme background color)
        theme_bg = ThemeManager.get_current().colors.background
        self._offscreen.fill(theme_bg)

        # STEP 2-4: Terrain, buildings, shadows, environment lighting
        self._render_terrain(game_map, camera, debug_mode, units)

        # STEP 5: Units, fading ghosts, unit shadows, attack/command lines
        self._render_units(units, camera, selected_unit_ids)

        # STEP 5.7-5.8: Particles, trails, shell casings, lighting
        self._render_weather_and_lighting(camera)

        # STEP 5.9: HUD overlay
        self._render_hud()

        # STEP 6: Screen effects (flash, suppression, weather)
        self._render_effects()

        # STEP 7: Atomic blit off-screen buffer → display surface
        self._screen.blit(self._offscreen, (0, 0))

        # Post-processing (applied to display surface for flicker-free output)
        if hasattr(self, "_post_processing") and self._post_processing is not None:
            try:
                processed = self._post_processing.apply_all(self._screen, color_style="war")
                if processed is not None:
                    self._screen.blit(processed, (0, 0))
            except (pygame.error, ValueError, TypeError) as exc:
                logger.debug("Post-processing skipped: %s", exc)

        # ✅ FIX: 移除display.flip() - GameLoop.run()负责最终的flip
        # 原因: 双重flip导致画面闪烁和FPS降至19
        # Note: GameLoop.run()在line 257执行统一的display.flip()

    def _render_terrain(
        self,
        game_map: GameMap,
        camera: Camera,
        debug_mode: bool,
        units: list[Unit] | None = None,
    ) -> None:
        """Render terrain tiles, decorations, shadows, buildings, and environment lighting."""

        # STEP 2: Draw terrain — use enhanced texturing with simple fallback
        # Terrain covers most of the screen; if camera moved we need full redraw.
        try:
            self._terrain_rendering_sys.draw_enhanced_terrain(game_map, camera, debug_mode)
        except RuntimeError as e:
            logger.warning(f"Enhanced terrain failed, falling back to simple: {e}")
            self._terrain_rendering_sys.draw_simple_terrain(game_map, camera)

        # PERF: Terrain covers the entire visible viewport; camera movement or
        # tile redraw invalidates all pixels.  Keeping full-dirty here is correct
        # because the terrain pass touches every on-screen tile.
        if self._dirty_tracker is not None:
            self._dirty_tracker.mark_full_dirty()

        # STEP 3: Draw grid ONLY in debug mode
        # ============================================================
        # ⚠️ RELEASE MODE GUARD: 以下debug绘制仅在 debug_mode=True 时执行
        # - _draw_grid(): 地形网格线（开发调试用）
        # - 性能影响: O(width*height) 线段绘制/帧
        # - 正式发布: debug_mode=False → 完全跳过，零开销
        # ============================================================
        if debug_mode:
            self._draw_grid(game_map, camera)

        # STEP 4: Draw decorations (minimal)
        self._draw_decorations(game_map, camera)

        # STEP 4.0: Draw ALL shadows FIRST (under everything - correct Z-order)
        self._shadow_rendering_sys.render_building_shadows(
            self._offscreen, game_map, camera
        )  # Building shadows BEFORE roofs
        self._shadow_rendering_sys.render_tree_shadows(
            self._offscreen, game_map, camera
        )  # Tree shadows BEFORE trees

        # STEP 4.0-DYN: Dynamic shadow overlay (time-of-day aware, augments existing shadows)
        if hasattr(self, "_dynamic_shadow_sys") and self._dynamic_shadow_sys is not None:
            self._render_dynamic_shadows(game_map, camera)

        # STEP 4.4: Draw building roofs (CC2 top-down view — covers side-view terrain texture)
        self._draw_building_roofs(game_map, camera)

        # STEP 4.5: Draw building interiors (auto-switch when units are inside)
        self._draw_building_interiors(game_map, units or [], camera)

        # STEP 4.6: Draw building floor numbers on roof
        self._draw_building_floor_numbers(game_map, camera)

        # STEP 4.7: Draw Victory Location flags and edge arrows
        self._draw_vl_flags(game_map, camera)

        # STEP 4.8: Environment lighting pass (after terrain/buildings, before units)
        self._apply_environment_lighting(game_map, camera, units)

    def _render_units(
        self,
        units: list[Unit],
        camera: Camera,
        selected_unit_ids: set[str] | None = None,
    ) -> None:
        """Render all units, fading ghosts, unit shadows, attack and command lines."""

        # STEP 5: Draw units (positions already smoothed by _smooth_positions in update phase)
        self._draw_units(units, camera, selected_unit_ids)

        # PERF: Mark unit screen regions as dirty
        if self._dirty_tracker is not None and not self._dirty_tracker._full_redraw:
            for unit in units:
                if not hasattr(unit, "position") or unit.position is None:
                    continue
                try:
                    px = unit.position.pixel_position.x
                    py = unit.position.pixel_position.y
                except (AttributeError, TypeError):
                    continue
                sx = int(px - camera.x + self._offscreen.get_width() // 2)
                sy = int(py - camera.y + self._offscreen.get_height() // 2)
                # Bounding box with margin for unit sprite + selection ring
                self._dirty_tracker.mark_dirty(pygame.Rect(sx - 20, sy - 20, 40, 40))

        # STEP 5.05: Draw death fade-out ghosts (P2-02 — semi-transparent dying units)
        self._render_fading_units(camera)

        # STEP 5.1: Draw unit and vehicle shadows (AFTER units rendered)
        self._shadow_rendering_sys.render_unit_shadows(self._offscreen, units, camera)

        # STEP 5.5: Draw attack lines (CC2-style)
        self._draw_attack_lines(camera)

        # STEP 5.6: Draw queued command lines (Shift+right-click)
        self._draw_queued_commands(units, camera)

    def _render_weather_and_lighting(self, camera: Camera) -> None:
        """Render weather effects and lighting (particles, trails, shell casings, time-of-day)."""

        # STEP 5.7: Render particle effects (explosions, smoke, muzzle flash, etc.)
        self._particle_system.render(self._offscreen)

        # PERF: Mark particle screen regions as dirty (skip if already full-dirty)
        if self._dirty_tracker is not None and not self._dirty_tracker._full_redraw:
            if self._particle_system.active_count > 0:
                for prect in self._particle_system.get_dirty_rects():
                    self._dirty_tracker.mark_dirty(prect)

        # STEP 5.7-TRAIL: Render projectile trails (bullet/shell/rocket/mortar)
        if hasattr(self, "_projectile_trail_sys") and self._projectile_trail_sys is not None:
            self._projectile_trail_sys.render(self._offscreen)

        # P3-02: Render shell casings (ejected brass, physics-driven)
        self.render_shell_casings(camera)

        # STEP 5.8: Top-down lighting system pass (time-of-day tint + dynamic lights)
        self._lighting_effects_sys.apply_time_of_day_tint(self._offscreen)
        self._lighting_effects_sys.render_dynamic_lights(self._offscreen)

    def _render_effects(self) -> None:
        """Render visual effects (suppression, damage, flash, weather overlays)."""

        # P2-03: Screen flash overlay (after all rendering, before atomic flip)
        if self._flash_sys.is_active:
            # PERF: Flash is full-screen overlay → must dirty entire screen
            if self._dirty_tracker is not None:
                self._dirty_tracker.mark_full_dirty()
            # Reuse cached flash surface (avoid per-frame allocation)
            flash_size = self._offscreen.get_size()
            if self._flash_surf_cache is None or self._flash_surf_cache.get_size() != flash_size:
                self._flash_surf_cache = pygame.Surface(flash_size, pygame.SRCALPHA)
            flash_surf = self._flash_surf_cache
            flash_surf.fill((0, 0, 0, 0))  # Clear for reuse
            flash_surf.fill((*self._flash_sys.color, int(max(0, self._flash_sys.alpha))))
            self._offscreen.blit(flash_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        # Suppression overlay: red edge flash when player units are pinned/broken
        if self._suppression_overlay_alpha > 1.0:
            self._render_suppression_overlay()

        # P3-01: Weather atmosphere overlay (light_fog / dust / smoke) — delegated to WeatherSystem
        if self._weather_sys.mode != "clear":
            # PERF: weather overlays can be full-screen → mark full dirty
            if self._dirty_tracker is not None:
                self._dirty_tracker.mark_full_dirty()
            self._weather_sys.render(self._offscreen)

    def _render_hud(self) -> None:
        """Render HUD overlay."""
        if self._hud_enabled and self._hud is not None:
            self._hud.render(self._offscreen)
            # PERF: HUD updates every frame (selection, health bars, etc.)
            if self._dirty_tracker is not None and not self._dirty_tracker._full_redraw:
                # Mark bottom HUD area as dirty (CC2 three-panel layout at bottom)
                sw, sh = self._offscreen.get_size()
                self._dirty_tracker.mark_dirty(pygame.Rect(0, sh - 120, sw, 120))

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
            if self._screen is not None:
                self._isometric_renderer.initialize(self._screen)

        self._isometric_renderer.render(
            game_map=game_map,
            units=units,
            camera=camera,
            selected_unit_ids=selected_unit_ids,
            debug_mode=debug_mode,
        )

    def _draw_simple_terrain(self, game_map: GameMap, camera: Camera) -> None:
        """Delegate to TerrainRenderingSystem for simple solid-color terrain."""
        self._terrain_rendering_sys.draw_simple_terrain(game_map, camera)

    def _get_cached_texture(self, terrain_id: int, variation: int) -> pygame.Surface:
        """Get or generate cached terrain texture."""
        key = (terrain_id, variation)
        if key not in self._texture_cache:
            self._texture_cache[key] = ProceduralTextureGenerator.generate_terrain_texture(
                terrain_id, variation, self._palette_gen
            )
        return self._texture_cache[key]

    def _get_cached_sprite(self, deco_type_name: str, variant: int = 0) -> pygame.Surface:
        """Get or generate cached decoration sprite."""
        key = f"{deco_type_name}_{variant}"
        if key not in self._sprite_cache:
            self._sprite_cache[key] = SpriteGenerator.generate_sprite(deco_type_name, variant)
        return self._sprite_cache[key]

    def _draw_enhanced_terrain(
        self, game_map: GameMap, camera: Camera, debug_mode: bool = False
    ) -> None:
        """Delegate to TerrainRenderer for enhanced terrain drawing."""
        self._terrain_renderer.draw_enhanced_terrain(game_map, camera, debug_mode)

    def _draw_building_roofs(
        self,
        game_map: GameMap,
        camera: Camera,
    ) -> None:
        """Delegate to BuildingRenderer for CC2-style building roofs."""
        self._building_renderer.draw_building_roofs(game_map, camera)

    def _draw_building_interiors(
        self,
        game_map: GameMap,
        units: list[Unit],
        camera: Camera,
    ) -> None:
        """Delegate to BuildingRenderer for building interior view."""
        self._building_renderer.draw_building_interiors(game_map, units, camera)

    def _draw_building_floor_numbers(
        self,
        game_map: GameMap,
        camera: Camera,
    ) -> None:
        """Delegate to BuildingRenderer for floor count numbers."""
        self._building_renderer.draw_building_floor_numbers(game_map, camera)

    def _draw_vl_flags(self, game_map: GameMap, camera: Camera) -> None:
        """Delegate to UIOverlayRenderer for VL flags and edge arrows."""
        self._ui_overlay.draw_vl_flags(game_map, camera)

    def _get_enhanced_tile(self, game_map: GameMap, x: int, y: int):
        """Try to get enhanced tile data from map."""
        try:
            # 优先使用GameMap的API方法
            if hasattr(game_map, "get_enhanced_tile"):
                tile_data = game_map.get_enhanced_tile(x, y)
                if tile_data is not None:
                    # 延迟导入避免TYPE_CHECKING限制
                    from pycc2.domain.systems.enhanced_tile import EnhancedTile

                    if isinstance(tile_data, EnhancedTile):
                        return tile_data
                    elif isinstance(tile_data, dict):
                        return EnhancedTile.from_dict(tile_data)
            # 兼容旧属性名 enhanced_tiles（二维列表）
            if hasattr(game_map, "enhanced_tiles") and game_map.enhanced_tiles:
                if 0 <= y < len(game_map.enhanced_tiles) and 0 <= x < len(
                    game_map.enhanced_tiles[y]
                ):
                    return game_map.enhanced_tiles[y][x]
        except (AttributeError, IndexError, TypeError, KeyError):
            pass
        return None

    def _get_terrain_at(self, game_map: GameMap, x: int, y: int) -> int:
        """Get terrain type at tile coordinate, returns -1 for out of bounds."""
        if x < 0 or y < 0 or x >= game_map.width or y >= game_map.height:
            return -1
        enhanced_tile = self._get_enhanced_tile(game_map, x, y)
        if enhanced_tile:
            return enhanced_tile.base_terrain
        return int(game_map.tile_grid[y, x])

    def _generate_cc2_style_tile(
        self, terrain_id: int, tile_x: int = 0, tile_y: int = 0, bitmask: int = 0
    ) -> pygame.Surface:
        """
        Generate a CC2-authentic 48×48 terrain tile with autotile support.

        This is the main entry point for CC2-style terrain generation.
        Uses deterministic random seeds based on tile position for consistent
        regeneration (same position always produces same appearance).

        Args:
            terrain_id: Terrain type ID (0-12)
            tile_x: Tile X position (used for deterministic seed)
            tile_y: Tile Y position (used for deterministic seed)
            bitmask: Autotile neighbor bitmap (0-15) for cross-tile continuity

        Returns:
            pygame.Surface: 48×48 pixel surface with CC2-authentic terrain
        """
        # Deterministic seed from position ensures consistent regeneration
        # Adjacent tiles of same type will have different variations
        variation = tile_x * 7919 + tile_y * 104729 + terrain_id * 17

        # Use the existing ProceduralTextureGenerator with new CC2 palette and autotile support
        return ProceduralTextureGenerator.generate_terrain_texture(
            terrain_id, variation=variation, palette=self._palette_gen, bitmask=bitmask
        )

    def _render_terrain_transitions(
        self,
        game_map: GameMap,
        camera: Camera,
        start_x: int,
        end_x: int,
        start_y: int,
        end_y: int,
        tile_screen_size: int,
    ) -> None:
        """Delegate to TerrainRenderer for terrain transition strips."""
        self._terrain_renderer.render_terrain_transitions(
            game_map, camera, start_x, end_x, start_y, end_y, tile_screen_size
        )

    def _apply_terrain_edge_smoothing(
        self,
        game_map: GameMap,
        camera: Camera,
        start_x: int,
        end_x: int,
        start_y: int,
        end_y: int,
        tile_screen_size: int,
    ) -> None:
        """Delegate to TerrainRenderer for terrain edge smoothing."""
        self._terrain_renderer.apply_terrain_edge_smoothing(
            game_map, camera, start_x, end_x, start_y, end_y, tile_screen_size
        )

    def _draw_terrain_borders(
        self, game_map: GameMap, camera: Camera, start_x: int, end_x: int, start_y: int, end_y: int
    ) -> None:
        """Draw thin dark borders between tiles of different terrain types for readability.

        ⚠️ RELEASE MODE: 此方法仅在 debug_mode=True 时被调用 (见 _draw_enhanced_terrain L2510)
        在正式发布版本中，此方法不会被调用，不会产生任何性能开销。

        Debug功能：
        - 绘制不同地形类型之间的边界线
        - 帮助识别地形过渡区域
        - 用于地图编辑和调试

        性能注意：
        - 遍历所有可见tile并检查邻居
        - 仅在debug模式下启用
        - Release构建时完全跳过
        """
        if self._screen is None or self._offscreen is None:
            return

        from pycc2.domain.value_objects.vec2 import Vec2

        tile_screen_size = int(self.TILE_SIZE * camera.zoom)
        border_color = (20, 20, 20)

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                current_terrain = self._get_terrain_at(game_map, tx, ty)

                world_x = tx * self.TILE_SIZE
                world_y = ty * self.TILE_SIZE
                screen_pos = camera.world_to_screen(Vec2(world_x, world_y))
                sx = int(screen_pos[0])
                sy = int(screen_pos[1])

                # Right border
                right_terrain = self._get_terrain_at(game_map, tx + 1, ty)
                if right_terrain != current_terrain and right_terrain >= 0:
                    pygame.draw.line(
                        self._offscreen,
                        border_color,
                        (sx + tile_screen_size, sy),
                        (sx + tile_screen_size, sy + tile_screen_size),
                        1,
                    )

                # Bottom border
                bottom_terrain = self._get_terrain_at(game_map, tx, ty + 1)
                if bottom_terrain != current_terrain and bottom_terrain >= 0:
                    pygame.draw.line(
                        self._offscreen,
                        border_color,
                        (sx, sy + tile_screen_size),
                        (sx + tile_screen_size, sy + tile_screen_size),
                        1,
                    )

    def _render_dynamic_shadows(self, game_map: GameMap, camera: Camera) -> None:
        """Render dynamic time-of-day shadows for buildings and trees."""
        shadow_sys = self._dynamic_shadow_sys
        if shadow_sys is None:
            return

        view_tl, view_br = camera.view_bounds
        ts = self.TILE_SIZE
        start_col = max(0, int(view_tl.x / ts) - 1)
        end_col = min(game_map.width, int(view_br.x / ts) + 2)
        start_row = max(0, int(view_tl.y / ts) - 1)
        end_row = min(game_map.height, int(view_br.y / ts) + 2)

        for row in range(start_row, end_row):
            for col in range(start_col, end_col):
                tile_val = game_map.tile_grid[row, col]
                wx = col * ts + ts // 2
                wy = row * ts + ts // 2
                sx, sy = camera.world_to_screen(type("V", (), {"x": wx, "y": wy})())
                sx, sy = int(sx), int(sy)

                if tile_val == 3:
                    shadow_sys.render_building_shadow(self._offscreen, sx, sy, ts, ts)
                elif tile_val == 5:
                    shadow_sys.render_tree_shadow(self._offscreen, sx, sy, tree_radius=12)

    def _apply_environment_lighting(
        self, game_map: GameMap, camera: Camera, units: list | None = None
    ) -> None:
        """Delegate to EnvironmentRenderer for environment lighting effects."""
        self._environment._apply_environment_lighting(game_map, camera, units)

    def _get_health_tinted_color(self, base_color: tuple, unit) -> tuple:
        """Delegate to EnvironmentRenderer for health-based color tinting."""
        return self._environment._get_health_tinted_color(base_color, unit)

    def _draw_direction_indicator(
        self, cx: int, cy: int, radius: int, unit_color: tuple, unit=None
    ) -> None:
        """Delegate to UnitRenderer for direction arrow drawing."""
        if unit is not None:
            self._unit_renderer.draw_direction_indicator(cx, cy, radius, unit_color, unit)

    def _draw_movement_mode_overlay(
        self, unit, cx: int, cy: int, radius: int, base_color: tuple
    ) -> None:
        """Delegate to UnitRenderer for movement mode overlay."""
        self._unit_renderer.draw_movement_mode_overlay(unit, cx, cy, radius, base_color)

    def _apply_height_lighting(self, surface: pygame.Surface, height: int) -> pygame.Surface:
        """Delegate to EnvironmentRenderer for height-based lighting."""
        return self._environment._apply_height_lighting(surface, height)

    def _apply_time_of_day_tint(self, surface: pygame.Surface) -> pygame.Surface:
        """Delegate to EnvironmentRenderer for time-of-day color grading."""
        return self._environment._apply_time_of_day_tint(surface)

    def _apply_cc2_color_grading(self, surface: pygame.Surface) -> None:
        """Delegate to EnvironmentRenderer for CC2-style color grading."""
        self._environment._apply_cc2_color_grading(surface)

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

    def _render_dynamic_lights(self) -> None:
        """Delegate to EnvironmentRenderer for dynamic light rendering (legacy API)."""
        self._environment._render_dynamic_lights()

    def _draw_decorations(self, game_map: GameMap, camera: Camera) -> None:
        """Draw decoration sprites on map."""
        if self._screen is None or self._offscreen is None:
            return

        bounds = camera.view_bounds
        start_x = max(0, int(bounds[0].x // self.TILE_SIZE))
        end_x = min(game_map.width, int((bounds[1].x // self.TILE_SIZE) + 2))
        start_y = max(0, int(bounds[0].y // self.TILE_SIZE))
        end_y = min(game_map.height, int((bounds[1].y // self.TILE_SIZE) + 2))

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                enhanced_tile = self._get_enhanced_tile(game_map, tx, ty)

                if not enhanced_tile or not enhanced_tile.decorations:
                    continue

                for deco in enhanced_tile.decorations:
                    # Get sprite
                    sprite = self._get_cached_sprite(deco.decoration_type.name, deco.variant)

                    # Calculate position with sub-tile offset
                    base_x = tx * self.TILE_SIZE
                    base_y = ty * self.TILE_SIZE

                    offset_x = int(deco.offset_x * self.TILE_SIZE)
                    offset_y = int(deco.offset_y * self.TILE_SIZE)

                    world_x = base_x + offset_x
                    world_y = base_y + offset_y

                    from pycc2.domain.value_objects.vec2 import Vec2

                    screen_pos = camera.world_to_screen(Vec2(world_x, world_y))

                    # Scale sprite
                    sprite_size = int(self.TILE_SIZE * camera.zoom * deco.scale)
                    if sprite_size != 32:
                        sprite = pygame.transform.scale(sprite, (sprite_size, sprite_size))

                    # Rotate if needed
                    if deco.rotation != 0:
                        sprite = pygame.transform.rotate(sprite, -deco.rotation)

                    rect = sprite.get_rect()
                    rect.center = (int(screen_pos[0]), int(screen_pos[1]))
                    self._offscreen.blit(sprite, rect)

    def _draw_units(
        self, units: list[Unit], camera: Camera, selected_unit_ids: set[str] | None = None
    ) -> None:
        """Delegate to UnitRenderer for unit drawing (with P2-04 smooth positions)."""
        self._unit_renderer.draw_units(
            units, camera, selected_unit_ids, position_overrides=self._unit_positions
        )

    def _draw_damage_vfx(self, unit: Unit, cx: int, cy: int) -> None:
        """Delegate to UnitRenderer for damage visual effects."""
        self._unit_renderer.draw_damage_vfx(unit, cx, cy)

    def _draw_hexagon(
        self, cx: int, cy: int, radius: int, color: tuple[int, int, int], selected: bool = False
    ) -> None:
        """Delegate to UnitRenderer for hexagon-shaped unit drawing."""
        self._unit_renderer.draw_hexagon(cx, cy, radius, color, selected)

    def _draw_attack_lines(self, camera: Camera) -> None:
        """Delegate to UIOverlayRenderer for CC2-style attack lines."""
        self._ui_overlay.draw_attack_lines(camera)

    def render_los_overlay(self, surface: pygame.Surface, unit, game_map, camera) -> None:
        """Delegate to UIOverlayRenderer for LOS visualization."""
        self._ui_overlay.render_los_overlay(surface, unit, game_map, camera)

    # ====== Combat effect proxy methods (forward to ParticleEffectsRenderer) ======

    def spawn_hit_flash(self, unit_id: str) -> None:
        """Delegate to ParticleEffectsRenderer."""
        self._particle_effects.spawn_hit_flash(unit_id)

    def spawn_damage_number(self, position, damage: int, is_kill: bool = False) -> None:
        """Delegate to ParticleEffectsRenderer."""
        self._particle_effects.spawn_damage_number(position, damage, is_kill)

    # NOTE: spawn_muzzle_flash (ParticleSystem version) defined below at L1308.
    # The SpriteRenderer-only version was removed — ParticleSystem version is strictly more capable.

    def spawn_death_effect(self, unit_id: str, position) -> None:
        """Delegate to ParticleEffectsRenderer."""
        self._particle_effects.spawn_death_effect(unit_id, position)
        # P2-02: Trigger death fade-out animation
        self.start_death_fade(unit_id, position, duration_ms=500)

    # NOTE: spawn_explosion (ring+dynamic light version) defined below at L1299.
    # The sprite-only version was removed — ring version is strictly more capable.

    def spawn_smoke_screen(self, position, radius: float = 64.0) -> None:
        """Delegate to ParticleEffectsRenderer."""
        self._particle_effects.spawn_smoke_screen(position, radius)

    def spawn_dirt_splash(self, x: float, y: float, count: int = 8) -> None:
        """Delegate to ParticleEffectsRenderer for dirt splash particles on hit."""
        self._particle_effects.spawn_dirt_splash(x, y, count)

    def spawn_blood_pool(self, x: float, y: float, size: int = 10) -> None:
        """Delegate to ParticleEffectsRenderer for persistent blood pool stain."""
        self._particle_effects.spawn_blood_pool(x, y, size)

    def spawn_hit_marker(self, x: float, y: float, damage_type: str = "normal") -> None:
        """Delegate to ParticleEffectsRenderer for hit marker visual feedback."""
        self._particle_effects.spawn_hit_marker(x, y, damage_type)

    # ------------------------------------------------------------------
    # P2-02: Death fade-out animation
    # ------------------------------------------------------------------

    def start_death_fade(self, unit_id: str, position, duration_ms: int = 500) -> None:
        """Register a unit for death fade-out animation (alpha 255→0)."""
        import time as _time

        px = (
            position.x
            if hasattr(position, "x")
            else float(position[0])
            if hasattr(position, "__getitem__")
            else 0.0
        )
        py = (
            position.y
            if hasattr(position, "y")
            else float(position[1])
            if hasattr(position, "__getitem__")
            else 0.0
        )
        self._fading_units[unit_id] = {
            "x": px,
            "y": py,
            "start_time": _time.monotonic(),
            "duration": duration_ms / 1000.0,
            "alpha": 255,
        }

    def _render_fading_units(self, camera: Camera) -> None:
        """Render semi-transparent ghost for each dying unit; remove when fully faded."""
        import time as _time

        now = _time.monotonic()
        dead_ids = []
        for uid, state in self._fading_units.items():
            elapsed = now - state["start_time"]
            progress = min(1.0, elapsed / max(0.001, state["duration"]))
            alpha = int(255 * (1.0 - progress))  # linear fade
            if alpha <= 1:
                dead_ids.append(uid)
                continue
            sx = int(state["x"] - camera.x + self._offscreen.get_width() // 2)
            sy = int(state["y"] - camera.y + self._offscreen.get_height() // 2)
            size = 12
            color = (60, 55, 50, alpha)  # CC2 dark gray ghost
            try:
                pygame.draw.circle(self._offscreen, color, (sx, sy), size)
            except (pygame.error, ValueError) as exc:
                logger.debug("Fading unit draw skipped: %s", exc)
        for uid in dead_ids:
            del self._fading_units[uid]

    def _draw_queued_commands(self, units: list, camera: Camera) -> None:
        """Delegate to UIOverlayRenderer for queued command lines."""
        self._ui_overlay.draw_queued_commands(units, camera)

    # _draw_dashed_line moved to UIOverlayRenderer._draw_dashed_line()

    # ============================================================
    # Particle System Convenience Methods (Top-Down VFX) - Delegated
    # ============================================================

    def update_particles(self, dt_ms: int) -> None:
        """Delegate to ParticleEffectsRenderer for particle updates."""
        self._particle_effects.update_particles(dt_ms)

    def spawn_explosion(
        self, position, max_radius=40, duration_ms=500, color=(255, 200, 50)
    ) -> None:
        """Delegate to ParticleEffectsRenderer for explosion ring effect."""
        self._particle_effects.spawn_explosion_ring(position, max_radius, duration_ms, color)
        self.spawn_dynamic_light(
            position, radius=60, intensity=1.5, color=(255, 200, 100), duration_ms=duration_ms
        )

    def spawn_muzzle_flash(self, position, direction) -> None:
        """Delegate to ParticleEffectsRenderer for muzzle flash (ParticleSystem version)."""
        self._particle_effects.spawn_muzzle_flash_particle(position, direction)

    def particle_count(self) -> int:
        """Delegate to ParticleEffectsRenderer for particle count."""
        return self._particle_effects.particle_count()

    def _draw_grid(self, game_map: GameMap, camera: Camera) -> None:
        """Draw grid overlay for debugging.

        ⚠️ RELEASE MODE: 此方法仅在 debug_mode=True 时被调用 (见 render() L2246)
        在正式发布版本中，此方法不会被调用，不会产生任何性能开销。

        Debug功能：
        - 绘制地形网格线（灰色）
        - 显示tile边界
        - 用于开发调试和地图编辑

        性能注意：
        - 每帧绘制O(width*height)条线段
        - 仅在debug模式下启用
        - Release构建时完全跳过
        """
        if self._screen is None:
            return

        bounds = camera.view_bounds
        grid_color = (60, 80, 40, 80)  # Dim grey-green (was bright grey 100,100,100)

        start_x = max(0, int(bounds[0].x // self.TILE_SIZE))
        end_x = min(game_map.width, int((bounds[1].x // self.TILE_SIZE) + 2))
        start_y = max(0, int(bounds[0].y // self.TILE_SIZE))
        end_y = min(game_map.height, int((bounds[1].y // self.TILE_SIZE) + 2))

        int(self.TILE_SIZE * camera.zoom)

        for ty in range(start_y, end_y + 1):
            from pycc2.domain.value_objects.vec2 import Vec2

            start_pos = camera.world_to_screen(Vec2(start_x * self.TILE_SIZE, ty * self.TILE_SIZE))
            end_pos = camera.world_to_screen(Vec2(end_x * self.TILE_SIZE, ty * self.TILE_SIZE))
            pygame.draw.line(
                self._offscreen,
                grid_color[:3],
                (int(start_pos[0]), int(start_pos[1])),
                (int(end_pos[0]), int(end_pos[1])),
                1,
            )

        for tx in range(start_x, end_x + 1):
            start_pos = camera.world_to_screen(Vec2(tx * self.TILE_SIZE, start_y * self.TILE_SIZE))
            end_pos = camera.world_to_screen(Vec2(tx * self.TILE_SIZE, end_y * self.TILE_SIZE))
            pygame.draw.line(
                self._offscreen,
                grid_color[:3],
                (int(start_pos[0]), int(start_pos[1])),
                (int(end_pos[0]), int(end_pos[1])),
                1,
            )

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

    def resize(self, width: int, height: int) -> None:
        """Handle window resize - reinitialize offscreen buffer and dirty tracker."""
        if self._screen is not None:
            try:
                self._offscreen = pygame.Surface((width, height), pygame.SRCALPHA)
                self._invalidate_surface_cache()
                # Re-create dirty tracker with new dimensions
                if self._dirty_tracker is not None:
                    self._dirty_tracker = _DirtyRectTracker(width, height)
                # Sync new dimensions to weather system
                self._weather_sys.update_screen_size(width, height)
            except (pygame.error, ValueError):
                logger.warning(f"Failed to resize offscreen buffer to {width}x{height}")
