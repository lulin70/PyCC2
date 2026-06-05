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
import random
from collections import OrderedDict
from typing import TYPE_CHECKING, Any

import pygame

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.domain.systems.enhanced_tile import EnhancedTile

# Import autotile system for cross-tile visual continuity
from pycc2.presentation.rendering.autotile_system import (
    get_neighbor_bitmap,
    get_continuity_variant,
    detect_building_clusters,
    get_building_cluster_info,
    is_autotile_terrain,
    get_edge_transition_width,
    AutotileCache,
)
from pycc2.presentation.rendering.camera import ProjectionMode

# Import shadow system for SE-direction shadows
from pycc2.presentation.rendering.shadow_system import ShadowRenderer
from pycc2.presentation.rendering.shadow_rendering_system import ShadowRenderingSystem
from pycc2.presentation.rendering.lighting_effects import LightingEffectsSystem
from pycc2.presentation.rendering.terrain_rendering_system import TerrainRenderingSystem

# Import refactored modules (backward-compatible re-exports)
from pycc2.presentation.rendering.sprite_generator import SpriteGenerator
from pycc2.presentation.rendering.particle_system import TopDownParticleSystem
from pycc2.presentation.rendering.lighting_system import TopDownLightingConfig, LightingSystem
from pycc2.presentation.rendering.terrain_renderer import TerrainRenderer
from pycc2.presentation.rendering.unit_renderer import UnitRenderer
from pycc2.presentation.rendering.building_renderer import BuildingRenderer
from pycc2.presentation.rendering.decoration_renderer import DecorationRenderer
from pycc2.presentation.rendering.terrain_tile_cache import (
    TerrainTileCache,
    CC2_TERRAIN_PALETTE,
    TERRAIN_PALETTE_MAP,
)
from pycc2.presentation.rendering.palette_generator import PaletteGenerator
from pycc2.presentation.rendering.procedural_texture_generator import ProceduralTextureGenerator
from pycc2.presentation.rendering.sprite_generator import SpriteGenerator
from pycc2.presentation.rendering.rendering_utils import draw_dashed_line
from pycc2.presentation.rendering.render_context import RenderContext

# Import extracted sub-modules (SRP refactoring)
from pycc2.presentation.rendering.particle_effects_renderer import ParticleEffectsRenderer
from pycc2.presentation.rendering.environment_renderer import EnvironmentRenderer
from pycc2.presentation.rendering.ui_overlay_renderer import UIOverlayRenderer

from dataclasses import dataclass


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

    def __init__(self, attack_line_system=None, lighting_config: TopDownLightingConfig | None = None):
        self._screen: pygame.Surface | None = None
        self._offscreen: pygame.Surface | None = None  # Off-screen buffer to eliminate flicker
        self._palette_gen = PaletteGenerator()
        self._texture_cache: dict[tuple[int, int], pygame.Surface] = {}
        self._scaled_texture_cache: dict[tuple[int, int, int], pygame.Surface] = {}
        self._height_lit_cache: dict[tuple[int, int, int, int], pygame.Surface] = {}
        self._sprite_cache: dict[str, pygame.Surface] = {}
        self._autotile_cache = AutotileCache()  # Cache for autotile variants
        self._terrain_tile_cache = TerrainTileCache(self.TILE_SIZE)  # Pre-computed terrain tile cache with edge smoothing
        self._building_clusters: list[list[tuple[int, int]]] | None = None  # Cached building clusters
        self._frame_count = 0
        self._sprite_renderer = None  # 延迟初始化，等待display ready
        self._isometric_renderer = None  # Isometric renderer (lazy init)
        self._shadow_renderer = ShadowRenderer()  # SE-direction shadow system
        self._shadow_rendering_sys = ShadowRenderingSystem(self._shadow_renderer, self.TILE_SIZE)  # Unified shadow coordinator
        self._attack_line_system = attack_line_system  # Dependency injection for attack line system
        self._particle_system = TopDownParticleSystem()  # Top-down particle effects system
        
        # Top-down lighting system configuration
        self._lighting_config = lighting_config or TopDownLightingConfig()
        
        # Initialize lighting effects system (time-of-day, CC2 grading, dynamic lights)
        self._lighting_effects_sys = LightingEffectsSystem(
            self._lighting_config, 
            self.TILE_SIZE,
            max_dynamic_lights=8
        )
        
        # Initialize terrain rendering system (extracted from EnhancedRenderer)
        self._terrain_rendering_sys = TerrainRenderingSystem(self, self.TILE_SIZE)

        # Surface object pool - eliminate per-frame allocation (PERF-001)
        # LRU eviction strategy: max 50 surfaces, evict least recently used
        self._surface_pool: OrderedDict[tuple[int, int], pygame.Surface] = OrderedDict()
        self._MAX_SURFACE_POOL_SIZE = 50
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

        self._enable_cc2_color_grading: bool = True
        self._hud = None
        self._hud_enabled: bool = True
    
    def initialize(self, screen: pygame.Surface) -> None:
        """Initialize renderer with display surface."""
        self._screen = screen
        try:
            # FIXED: Use SRCALPHA to support transparent shadows
            self._offscreen = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        except pygame.error as e:
            # Fallback for headless/testing environments without video mode set
            import warnings
            warnings.warn(f"Could not create SRCALPHA surface: {e}. Using convert() fallback.")
            self._offscreen = pygame.Surface(screen.get_size()).convert()

        # 现在display已初始化，可以创建SpriteRenderer加载PNG
        try:
            from pycc2.presentation.rendering.sprite_renderer import SpriteRenderer
            self._sprite_renderer = SpriteRenderer()
            self._sprite_renderer.initialize(screen)
            logger.info("✅ SpriteRenderer initialized with PNG support")
        except RuntimeError as e:
            import warnings
            warnings.warn(f"SpriteRenderer initialization failed: {e}")
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

    def _get_pooled_surface(self, size: tuple[int, int]) -> pygame.Surface:
        """Get or create a surface from the object pool with LRU eviction (PERF-001).

        Reuses existing surfaces to avoid per-frame allocation overhead.
        Implements LRU (Least Recently Used) eviction when pool exceeds max size.
        Surfaces are cleared before return for safe reuse.
        """
        if size in self._surface_pool:
            # Move to end (most recently used)
            self._surface_pool.move_to_end(size)
            surf = self._surface_pool[size]
            surf.fill(self.TRANSPARENT_BLACK)  # Clear for reuse
            return surf

        new_surf = pygame.Surface(size, pygame.SRCALPHA)

        # LRU eviction: remove oldest entry if at capacity
        if len(self._surface_pool) >= self._MAX_SURFACE_POOL_SIZE:
            evicted_size, evicted_surf = self._surface_pool.popitem(last=False)
            del evicted_surf  # Explicitly release memory

        self._surface_pool[size] = new_surf
        return new_surf

    def _invalidate_surface_cache(self) -> None:
        """Clear surface pool when screen size changes (PERF-001)."""
        self._surface_pool.clear()
        self._cached_warm_overlay = None
        self._cached_vignette = None
        self._cached_screen_size = None

    def _get_screen_overlays(self, screen_size: tuple[int, int]) -> tuple[pygame.Surface, pygame.Surface]:
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
        Main render method - STABLE VERSION with minimal complexity.

        Pipeline:
        1. Clear off-screen buffer (solid color, no alpha blending)
        2. Draw terrain (simple colored tiles, no textures)
        3. Draw units
        4. Atomic blit off-screen → display surface (eliminates flicker)
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

        # STEP 1: Clear off-screen buffer
        self._offscreen.fill((34, 40, 48))  # Dark blue-gray background

        # STEP 2: Draw terrain — use enhanced texturing with simple fallback
        try:
            self._terrain_rendering_sys.draw_enhanced_terrain(game_map, camera, debug_mode)
        except RuntimeError as e:
            logger.warning(f"Enhanced terrain failed, falling back to simple: {e}")
            self._terrain_rendering_sys.draw_simple_terrain(game_map, camera)

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
        self._shadow_rendering_sys.render_building_shadows(self._offscreen, game_map, camera)  # Building shadows BEFORE roofs
        self._shadow_rendering_sys.render_tree_shadows(self._offscreen, game_map, camera)      # Tree shadows BEFORE trees

        # STEP 4.0-DYN: Dynamic shadow overlay (time-of-day aware, augments existing shadows)
        if hasattr(self, '_dynamic_shadow_sys') and self._dynamic_shadow_sys is not None:
            self._render_dynamic_shadows(game_map, camera)

        # STEP 4.4: Draw building roofs (CC2 top-down view — covers side-view terrain texture)
        self._draw_building_roofs(game_map, camera)

        # STEP 4.5: Draw building interiors (auto-switch when units are inside)
        self._draw_building_interiors(game_map, units, camera)

        # STEP 4.6: Draw building floor numbers on roof
        self._draw_building_floor_numbers(game_map, camera)

        # STEP 4.7: Draw Victory Location flags and edge arrows
        self._draw_vl_flags(game_map, camera)

        # STEP 4.8: Environment lighting pass (after terrain/buildings, before units)
        self._apply_environment_lighting(game_map, camera, units)

        # STEP 5: Draw units
        self._draw_units(units, camera, selected_unit_ids)

        # STEP 5.1: Draw unit and vehicle shadows (AFTER units rendered)
        self._shadow_rendering_sys.render_unit_shadows(self._offscreen, units, camera)

        # STEP 5.5: Draw attack lines (CC2-style)
        self._draw_attack_lines(camera)

        # STEP 5.6: Draw queued command lines (Shift+right-click)
        self._draw_queued_commands(units, camera)

        # STEP 5.7: Render particle effects (explosions, smoke, muzzle flash, etc.)
        self._particle_system.render(self._offscreen)

        # STEP 5.7-TRAIL: Render projectile trails (bullet/shell/rocket/mortar)
        if hasattr(self, '_projectile_trail_sys') and self._projectile_trail_sys is not None:
            self._projectile_trail_sys.render(self._offscreen)

        # STEP 5.8: Top-down lighting system pass (time-of-day tint + dynamic lights)
        self._lighting_effects_sys.apply_time_of_day_tint(self._offscreen)
        self._lighting_effects_sys.render_dynamic_lights(self._offscreen)

        # STEP 5.9: Render CC2 three-panel HUD (if enabled and attached)
        if self._hud_enabled and self._hud is not None:
            self._hud.render(self._offscreen)

        # STEP 6: Atomic blit off-screen buffer → display surface
        self._screen.blit(self._offscreen, (0, 0))

        # DISABLED: All post-processing to prevent flickering and crashes
        # self._apply_post_processing()  # REMOVED - causes flickering

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
    
    def _draw_enhanced_terrain(self, game_map: GameMap, camera: Camera, debug_mode: bool = False) -> None:
        """Delegate to TerrainRenderer for enhanced terrain drawing."""
        self._terrain_renderer.draw_enhanced_terrain(game_map, camera, debug_mode)

    def _draw_building_roofs(
        self, game_map: GameMap, camera: Camera,
    ) -> None:
        """Delegate to BuildingRenderer for CC2-style building roofs."""
        self._building_renderer.draw_building_roofs(game_map, camera)

    def _draw_building_interiors(
        self, game_map: GameMap, units: list[Unit], camera: Camera,
    ) -> None:
        """Delegate to BuildingRenderer for building interior view."""
        self._building_renderer.draw_building_interiors(game_map, units, camera)

    def _draw_building_floor_numbers(
        self, game_map: GameMap, camera: Camera,
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
            if hasattr(game_map, 'get_enhanced_tile'):
                tile_data = game_map.get_enhanced_tile(x, y)
                if tile_data is not None:
                    # 延迟导入避免TYPE_CHECKING限制
                    from pycc2.domain.systems.enhanced_tile import EnhancedTile
                    if isinstance(tile_data, EnhancedTile):
                        return tile_data
                    elif isinstance(tile_data, dict):
                        return EnhancedTile.from_dict(tile_data)
            # 兼容旧属性名 enhanced_tiles（二维列表）
            if hasattr(game_map, 'enhanced_tiles') and game_map.enhanced_tiles:
                if 0 <= y < len(game_map.enhanced_tiles) and 0 <= x < len(game_map.enhanced_tiles[y]):
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
        self, 
        terrain_id: int, 
        tile_x: int = 0, 
        tile_y: int = 0,
        bitmask: int = 0
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
            terrain_id,
            variation=variation,
            palette=self._palette_gen,
            bitmask=bitmask
        )

    def _render_terrain_transitions(
        self, game_map: GameMap, camera: Camera,
        start_x: int, end_x: int, start_y: int, end_y: int,
        tile_screen_size: int
    ) -> None:
        """Delegate to TerrainRenderer for terrain transition strips."""
        self._terrain_renderer.render_terrain_transitions(
            game_map, camera, start_x, end_x, start_y, end_y, tile_screen_size
        )

    def _apply_terrain_edge_smoothing(
        self, game_map: GameMap, camera: Camera,
        start_x: int, end_x: int, start_y: int, end_y: int,
        tile_screen_size: int
    ) -> None:
        """Delegate to TerrainRenderer for terrain edge smoothing."""
        self._terrain_renderer.apply_terrain_edge_smoothing(
            game_map, camera, start_x, end_x, start_y, end_y, tile_screen_size
        )

    def _draw_terrain_borders(
        self, game_map: GameMap, camera: Camera,
        start_x: int, end_x: int, start_y: int, end_y: int
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
                        self._offscreen, border_color,
                        (sx + tile_screen_size, sy),
                        (sx + tile_screen_size, sy + tile_screen_size), 1
                    )

                # Bottom border
                bottom_terrain = self._get_terrain_at(game_map, tx, ty + 1)
                if bottom_terrain != current_terrain and bottom_terrain >= 0:
                    pygame.draw.line(
                        self._offscreen, border_color,
                        (sx, sy + tile_screen_size),
                        (sx + tile_screen_size, sy + tile_screen_size), 1
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
                sx, sy = camera.world_to_screen(
                    type('V', (), {'x': wx, 'y': wy})()
                )
                sx, sy = int(sx), int(sy)

                if tile_val == 3:
                    shadow_sys.render_building_shadow(
                        self._offscreen, sx, sy, ts, ts
                    )
                elif tile_val == 5:
                    shadow_sys.render_tree_shadow(
                        self._offscreen, sx, sy, tree_radius=12
                    )

    def _apply_environment_lighting(self, game_map: GameMap, camera: Camera, units: list | None = None) -> None:
        """Delegate to EnvironmentRenderer for environment lighting effects."""
        self._environment._apply_environment_lighting(game_map, camera, units)

    def _get_health_tinted_color(self, base_color: tuple, unit) -> tuple:
        """Delegate to EnvironmentRenderer for health-based color tinting."""
        return self._environment._get_health_tinted_color(base_color, unit)

    def _draw_direction_indicator(
        self, cx: int, cy: int, radius: int, unit_color: tuple
    ) -> None:
        """Delegate to UnitRenderer for direction arrow drawing."""
        # NOTE: unit param is resolved via closure in original callback context.
        # For direct calls, use self._unit_renderer.draw_direction_indicator(cx, cy, radius, color, unit).
        self._unit_renderer.draw_direction_indicator(cx, cy, radius, unit_color, unit)  # type: ignore[arg-type]

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

    def spawn_dynamic_light(self, position: tuple[int, int], 
                           radius: float, 
                           intensity: float,
                           color: tuple[int, int, int] = (255, 255, 200),
                           duration_ms: int = 200) -> None:
        """Delegate to EnvironmentRenderer for dynamic light registration."""
        self._environment.spawn_dynamic_light(
            position, radius, intensity, color, duration_ms
        )

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
                    sprite = self._get_cached_sprite(
                        deco.decoration_type.name,
                        deco.variant
                    )
                    
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
    
    def _draw_units(self, units: list[Unit], camera: Camera, selected_unit_ids: set[str] | None = None) -> None:
        """Delegate to UnitRenderer for unit drawing."""
        self._unit_renderer.draw_units(units, camera, selected_unit_ids)

    def _draw_damage_vfx(self, unit: Unit, cx: int, cy: int) -> None:
        """Delegate to UnitRenderer for damage visual effects."""
        self._unit_renderer.draw_damage_vfx(unit, cx, cy)

    def _draw_hexagon(
        self, cx: int, cy: int, radius: int, color: tuple[int, int, int],
        selected: bool = False
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

    # NOTE: spawn_explosion (ring+dynamic light version) defined below at L1299.
    # The sprite-only version was removed — ring version is strictly more capable.

    def spawn_smoke_screen(self, position, radius: float = 64.0) -> None:
        """Delegate to ParticleEffectsRenderer."""
        self._particle_effects.spawn_smoke_screen(position, radius)

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
        
    def spawn_explosion(self, position, max_radius=40, duration_ms=500, 
                        color=(255, 200, 50)) -> None:
        """Delegate to ParticleEffectsRenderer for explosion ring effect."""
        self._particle_effects.spawn_explosion_ring(
            position, max_radius, duration_ms, color
        )
        self.spawn_dynamic_light(position, radius=60, intensity=1.5, 
                                color=(255, 200, 100), duration_ms=duration_ms)
                                
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
        
        tile_size_scaled = int(self.TILE_SIZE * camera.zoom)
        
        for ty in range(start_y, end_y + 1):
            from pycc2.domain.value_objects.vec2 import Vec2
            start_pos = camera.world_to_screen(Vec2(start_x * self.TILE_SIZE, ty * self.TILE_SIZE))
            end_pos = camera.world_to_screen(Vec2(end_x * self.TILE_SIZE, ty * self.TILE_SIZE))
            pygame.draw.line(
                self._offscreen, grid_color[:3],
                (int(start_pos[0]), int(start_pos[1])),
                (int(end_pos[0]), int(end_pos[1])), 1
            )
        
        for tx in range(start_x, end_x + 1):
            start_pos = camera.world_to_screen(Vec2(tx * self.TILE_SIZE, start_y * self.TILE_SIZE))
            end_pos = camera.world_to_screen(Vec2(tx * self.TILE_SIZE, end_y * self.TILE_SIZE))
            pygame.draw.line(
                self._offscreen, grid_color[:3],
                (int(start_pos[0]), int(start_pos[1])),
                (int(end_pos[0]), int(end_pos[1])), 1
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
        if hasattr(self._terrain_renderer, '_transition_cache'):
            self._terrain_renderer._transition_cache.clear()
        if hasattr(self._terrain_renderer, '_edge_smooth_cache'):
            self._terrain_renderer._edge_smooth_cache.clear()

    def resize(self, width: int, height: int) -> None:
        """Handle window resize - reinitialize offscreen buffer."""
        if self._screen is not None:
            try:
                self._offscreen = pygame.Surface((width, height), pygame.SRCALPHA)
                self._invalidate_surface_cache()
            except (pygame.error, ValueError):
                logger.warning(f"Failed to resize offscreen buffer to {width}x{height}")
