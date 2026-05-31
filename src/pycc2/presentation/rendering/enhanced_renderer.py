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
- terrain_renderer.py     : TerrainRenderer (tile drawing, autotile, buildings)
- unit_renderer.py        : UnitRenderer (unit drawing, health colors, shadows)
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

# Import shadow system for SE-direction shadows
from pycc2.presentation.rendering.shadow_system import ShadowRenderer

# Import refactored modules (backward-compatible re-exports)
from pycc2.presentation.rendering.sprite_generator import SpriteGenerator
from pycc2.presentation.rendering.particle_system import TopDownParticleSystem
from pycc2.presentation.rendering.lighting_system import TopDownLightingConfig, LightingSystem
from pycc2.presentation.rendering.terrain_renderer import TerrainRenderer
from pycc2.presentation.rendering.unit_renderer import UnitRenderer
from pycc2.presentation.rendering.decoration_renderer import DecorationRenderer
from pycc2.presentation.rendering.terrain_tile_cache import (
    TerrainTileCache,
    CC2_TERRAIN_PALETTE,
    TERRAIN_PALETTE_MAP,
)
from pycc2.presentation.rendering.palette_generator import PaletteGenerator
from pycc2.presentation.rendering.procedural_texture_generator import ProceduralTextureGenerator
from pycc2.presentation.rendering.sprite_generator import SpriteGenerator

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
        self._edge_smooth_cache: dict[tuple[int, int], pygame.Surface] = {}  # Cached edge smoothing surfaces
        self._edge_smooth_dirty: bool = True  # Flag to indicate cache needs rebuild
        self._transition_cache: dict[tuple[int, int, int, int, str], tuple[pygame.Surface, pygame.Rect]] = {}  # Cached terrain transition strips
        self._last_map_hash: int = 0  # Track map changes for cache invalidation
        self._frame_count = 0
        self._sprite_renderer = None  # 延迟初始化，等待display ready
        self._isometric_renderer = None  # Isometric renderer (lazy init)
        self._shadow_renderer = ShadowRenderer()  # SE-direction shadow system
        self._attack_line_system = attack_line_system  # P0-2 Fix: Dependency injection (was getattr hack)
        self._particle_system = TopDownParticleSystem()  # Top-down particle effects system
        
        # Top-down lighting system configuration
        self._lighting_config = lighting_config or TopDownLightingConfig()
        self._dynamic_lights: list[dict] = []  # Temporary dynamic lights (explosions, muzzle flashes, etc.)
        self._max_dynamic_lights = 8  # Performance limit: max concurrent dynamic lights
        self._tod_tint_cache: pygame.Surface | None = None  # Cache for time-of-day tint surface
        self._last_time_of_day: str = self._lighting_config.time_of_day  # Track ToD changes

        # Initialize refactored sub-module renderers (coordinator pattern)
        self._terrain_renderer = TerrainRenderer(self)
        self._unit_renderer = UnitRenderer(self)
        self._decoration_renderer = DecorationRenderer(self)
        self._lighting_system = LightingSystem(self._lighting_config)

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

    def set_attack_line_system(self, attack_line_system) -> None:
        """Set attack line system (dependency injection setter - P0-2 Fix)."""
        self._attack_line_system = attack_line_system

    def set_time_of_day(self, tod: str) -> None:
        """
        Set time of day for color grading.
        
        Args:
            tod: Time of day string - 'dawn'/'noon'/'dusk'/'night'
        
        Raises:
            ValueError: If tod is not a valid time of day
        """
        valid_times = ['dawn', 'noon', 'dusk', 'night']
        if tod not in valid_times:
            raise ValueError(f"Invalid time of day: '{tod}'. Must be one of {valid_times}")
        
        self._lighting_config.time_of_day = tod
        logger.debug(f"Lighting: Time of day set to '{tod}'")

    def set_light_intensity(self, intensity: float) -> None:
        """
        Set global light intensity.
        
        Args:
            intensity: Brightness level (0.0 = dark, 1.0 = normal, 2.0 = very bright)
        """
        self._lighting_config.light_intensity = max(0.0, min(2.0, intensity))
        logger.debug(f"Lighting: Intensity set to {self._lighting_config.light_intensity:.2f}")

    def get_lighting_config(self) -> TopDownLightingConfig:
        """
        Get current lighting configuration (read-only access).
        
        Returns:
            TopDownLightingConfig: Current lighting configuration
        """
        return self._lighting_config

    def set_cc2_color_grading(self, enable: bool) -> None:
        self._enable_cc2_color_grading = enable
        logger.debug(f"CC2 color grading: {'enabled' if enable else 'disabled'}")

    def set_hud(self, hud) -> None:
        self._hud = hud

    def enable_hud(self, enabled: bool = True) -> None:
        self._hud_enabled = enabled

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
        from pycc2.presentation.rendering.camera import ProjectionMode
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

        # STEP 1: Clear off-screen buffer
        self._offscreen.fill((34, 40, 48))  # Dark blue-gray background

        # STEP 2: Draw terrain — use enhanced texturing with simple fallback
        try:
            self._draw_enhanced_terrain(game_map, camera, debug_mode)
        except RuntimeError as e:
            logger.warning(f"Enhanced terrain failed, falling back to simple: {e}")
            self._draw_simple_terrain(game_map, camera)

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
        self._render_building_shadows(game_map, camera)  # Building shadows BEFORE roofs
        self._render_tree_shadows(game_map, camera)      # Tree shadows BEFORE trees

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
        self._render_unit_shadows(units, camera)

        # STEP 5.5: Draw attack lines (CC2-style)
        self._draw_attack_lines(camera)

        # STEP 5.6: Draw queued command lines (Shift+right-click)
        self._draw_queued_commands(units, camera)

        # STEP 5.7: Render particle effects (explosions, smoke, muzzle flash, etc.)
        self._particle_system.render(self._offscreen)

        # STEP 5.8: Top-down lighting system pass (time-of-day tint + dynamic lights)
        # Apply time-of-day color grading (dawn/noon/dusk/night)
        self._apply_time_of_day_tint(self._offscreen)
        
        # Render dynamic point lights (explosions, muzzle flashes, ability effects)
        self._render_dynamic_lights()

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
        """Draw terrain using simple solid colors - MAXIMUM STABILITY.

        Uses predefined CC2-accurate colors without any procedural generation.
        This is the classic "256-color era" look that is rock-solid stable.
        """
        if self._screen is None or self._offscreen is None:
            return

        # CC2 Classic Color Palette (verified accurate)
        TERRAIN_COLORS = {
            0: (76, 124, 35),    # OPEN/GRASS - CC2 exact military green #4C7C23
            1: (139, 119, 101),  # ROAD - dirt brown
            2: (58, 100, 24),     # GRASS - darker green #3A6418
            3: (45, 68, 33),      # WOODS - very dark forest green
            4: (139, 115, 85),    # BUILDING_ENTERABLE - earthy brown
            5: (120, 118, 115),   # BUILDING_SOLID - gray stone
            6: (62, 87, 117),     # WATER - muted blue
            7: (85, 70, 55),      # HEDGE - dark brown-green
            8: (110, 108, 105),   # WALL - gray brick
            9: (135, 115, 80),    # ROUGH - tan/brown
            10: (95, 145, 165),   # SHALLOW - light blue-green
            11: (160, 140, 100),  # BRIDGE - wooden brown
            12: (90, 85, 75),     # CRATER - dark gray-brown
        }

        bounds = camera.view_bounds
        start_x = max(0, int(bounds[0].x // self.TILE_SIZE))
        end_x = min(game_map.width, int((bounds[1].x // self.TILE_SIZE) + 2))
        start_y = max(0, int(bounds[0].y // self.TILE_SIZE))
        end_y = min(game_map.height, int((bounds[1].y // self.TILE_SIZE) + 2))

        tile_screen_size = int(self.TILE_SIZE * camera.zoom)

        # Pre-calculate rect for batch drawing (much faster than individual blits)
        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                try:
                    # Get terrain type safely — use _get_enhanced_tile for compatibility
                    etile = self._get_enhanced_tile(game_map, tx, ty)
                    if etile is not None:
                        terrain_val = etile.base_terrain
                    else:
                        terrain_val = int(game_map.tile_grid[ty, tx])

                    # Clamp to valid range
                    terrain_val = max(0, min(12, terrain_val))

                    # Get color from palette
                    color = TERRAIN_COLORS.get(terrain_val, (128, 128, 128))

                    # Calculate screen position
                    world_x = tx * self.TILE_SIZE
                    world_y = ty * self.TILE_SIZE

                    from pycc2.domain.value_objects.vec2 import Vec2
                    screen_pos = camera.world_to_screen(Vec2(world_x, world_y))

                    # Draw solid rectangle (NO texture generation)
                    rect = pygame.Rect(
                        int(screen_pos[0]),
                        int(screen_pos[1]),
                        tile_screen_size,
                        tile_screen_size
                    )
                    pygame.draw.rect(self._offscreen, color, rect)

                except (AttributeError, ValueError) as e:
                    # Skip this tile on any error to prevent crash
                    continue
    
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
        """Draw terrain tiles with texturing and height-based lighting, with autotile support."""
        if self._screen is None:
            return

        # Update building clusters cache if needed
        if self._building_clusters is None:
            self._building_clusters = detect_building_clusters(game_map)

        bounds = camera.view_bounds
        start_x = max(0, int(bounds[0].x // self.TILE_SIZE))
        end_x = min(game_map.width, int((bounds[1].x // self.TILE_SIZE) + 2))
        start_y = max(0, int(bounds[0].y // self.TILE_SIZE))
        end_y = min(game_map.height, int((bounds[1].y // self.TILE_SIZE) + 2))

        tile_screen_size = int(self.TILE_SIZE * camera.zoom)

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                # Get enhanced tile data if available
                enhanced_tile = self._get_enhanced_tile(game_map, tx, ty)

                if enhanced_tile:
                    terrain_val = enhanced_tile.base_terrain
                    variation = enhanced_tile.variation
                    height = enhanced_tile.height
                else:
                    # Fallback to legacy integer
                    terrain_val = int(game_map.tile_grid[ty, tx])
                    variation = 0
                    height = 0

                # Calculate autotile bitmask for continuous terrains
                bitmask = 0
                if is_autotile_terrain(terrain_val):
                    bitmask = get_neighbor_bitmap(game_map, tx, ty, terrain_val)

                # Use TerrainTileCache for pre-computed tiles with edge smoothing
                texture = self._terrain_tile_cache.get_tile(
                    terrain_type=terrain_val,
                    autotile_mask=bitmask,
                    variation=variation,
                    height=height,
                    tile_screen_size=tile_screen_size,
                    renderer=self,
                    enhanced_tile=enhanced_tile,
                    tile_x=tx,
                    tile_y=ty,
                )

                # Fallback to original rendering if cache miss without renderer
                if texture is None:
                    if bitmask != 0:
                        cache_key = (terrain_val, variation, bitmask)
                        if cache_key not in self._autotile_cache._cache:
                            texture = self._generate_cc2_style_tile(terrain_val, tx, ty, bitmask)
                            self._autotile_cache.set_variant(terrain_val, bitmask, variation, texture)
                        else:
                            texture = self._autotile_cache.get_variant(terrain_val, bitmask, variation)

                        if tile_screen_size != self.TILE_SIZE:
                            scale_key = (terrain_val, variation, bitmask, tile_screen_size)
                            if scale_key not in self._scaled_texture_cache:
                                base_texture = self._autotile_cache.get_variant(terrain_val, bitmask, variation)
                                if base_texture:
                                    self._scaled_texture_cache[scale_key] = pygame.transform.scale(
                                        base_texture, (tile_screen_size, tile_screen_size)
                                    )
                            texture = self._scaled_texture_cache.get(scale_key, texture)
                    elif height != 0:
                        cache_key = (terrain_val, variation, height, tile_screen_size)
                        if cache_key in self._height_lit_cache:
                            texture = self._height_lit_cache[cache_key]
                        else:
                            base_texture = self._get_cached_texture(terrain_val, variation)
                            texture = self._apply_height_lighting(base_texture, height)
                            if tile_screen_size != self.TILE_SIZE:
                                texture = pygame.transform.scale(texture, (tile_screen_size, tile_screen_size))
                            self._height_lit_cache[cache_key] = texture
                    else:
                        if tile_screen_size != self.TILE_SIZE:
                            scale_key = (terrain_val, variation, tile_screen_size)
                            if scale_key not in self._scaled_texture_cache:
                                base_texture = self._get_cached_texture(terrain_val, variation)
                                self._scaled_texture_cache[scale_key] = pygame.transform.scale(
                                    base_texture, (tile_screen_size, tile_screen_size)
                                )
                            texture = self._scaled_texture_cache[scale_key]
                        else:
                            texture = self._get_cached_texture(terrain_val, variation)

                # Calculate screen position
                world_x = tx * self.TILE_SIZE
                world_y = ty * self.TILE_SIZE

                from pycc2.domain.value_objects.vec2 import Vec2
                screen_pos = camera.world_to_screen(Vec2(world_x, world_y))

                rect = pygame.Rect(int(screen_pos[0]), int(screen_pos[1]), tile_screen_size, tile_screen_size)
                self._offscreen.blit(texture, rect)

        # RE-ENABLED: Terrain edge smoothing with caching for performance
        # Only rebuilds cache when map changes, not every frame
        if not debug_mode and tile_screen_size >= 16:
            self._apply_terrain_edge_smoothing(game_map, camera, start_x, end_x, start_y, end_y, tile_screen_size)

        # Terrain transition blending between different terrain types
        if not debug_mode and tile_screen_size >= 16:
            self._render_terrain_transitions(game_map, camera, start_x, end_x, start_y, end_y, tile_screen_size)

        # Draw terrain borders ONLY in debug mode (Issue 4: remove harsh grid lines in normal mode)
        # ============================================================
        # ⚠️ RELEASE MODE GUARD: 地形边界线仅在 debug_mode=True 时绘制
        # - _draw_terrain_borders(): 不同地形类型间的边界线
        # - 性能影响: O(visible_tiles) 边界检查/帧
        # - 正式发布: debug_mode=False → 完全跳过，零开销
        # ============================================================
        if debug_mode:
            self._draw_terrain_borders(game_map, camera, start_x, end_x, start_y, end_y)

    def _draw_building_roofs(
        self, game_map: GameMap, camera: Camera,
    ) -> None:
        """Draw CC2-style top-down building roofs over all building tiles.

        This covers the side-view terrain texture with the correct CC2
        orthographic roof view (colored rectangle + pseudo-3D shadow strips).
        When units are inside, _draw_building_interiors will override with
        the interior view in the next step.
        """
        if self._offscreen is None:
            return

        from pycc2.presentation.rendering.cc2_building_renderer import (
            render_cc2_building,
            floors_to_building_type,
            DamageLevel,
        )

        bounds = camera.view_bounds
        start_x = max(0, int(bounds[0].x // self.TILE_SIZE))
        end_x = min(game_map.width, int((bounds[1].x // self.TILE_SIZE) + 2))
        start_y = max(0, int(bounds[0].y // self.TILE_SIZE))
        end_y = min(game_map.height, int((bounds[1].y // self.TILE_SIZE) + 2))

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                terrain_val = self._get_terrain_at(game_map, tx, ty)
                if terrain_val != 4:  # Only BUILDING_ENTERABLE
                    continue

                # Determine building type from floor count
                enhanced = game_map.get_enhanced_tile(tx, ty) if hasattr(game_map, 'get_enhanced_tile') else None
                floors = 1
                if enhanced and isinstance(enhanced, dict):
                    floors = int(enhanced.get("building_floors", 1))
                elif enhanced and hasattr(enhanced, 'building_floors'):
                    floors = int(getattr(enhanced, 'building_floors', 1))

                building_type = floors_to_building_type(floors)

                # Render roof (default mode = roof, not interior)
                roof_surface = render_cc2_building(
                    building_type=building_type,
                    damage=DamageLevel.INTACT,
                    tile_size=self.TILE_SIZE,
                    interior_mode=False,
                )

                # Scale if zoomed
                tile_screen_size = int(self.TILE_SIZE * camera.zoom)
                if tile_screen_size != self.TILE_SIZE:
                    tw, th = roof_surface.get_size()
                    target_w = int(tw * camera.zoom)
                    target_h = int(th * camera.zoom)
                    if target_w > 0 and target_h > 0:
                        roof_surface = pygame.transform.scale(
                            roof_surface, (target_w, target_h),
                        )

                # Blit roof at screen position
                from pycc2.domain.value_objects.vec2 import Vec2
                world_x = tx * self.TILE_SIZE
                world_y = ty * self.TILE_SIZE
                screen_pos = camera.world_to_screen(Vec2(world_x, world_y))

                self._offscreen.blit(roof_surface, (int(screen_pos[0]), int(screen_pos[1])))

    def _draw_building_interiors(
        self, game_map: GameMap, units: list[Unit], camera: Camera,
    ) -> None:
        """Overlay building interior view when units are inside a building.

        CC2 mechanism: when a unit enters a building tile, the building
        renderer automatically switches to interior mode (showing floor +
        windows instead of roof). When all units leave, it reverts to roof.
        """
        if self._screen is None or self._offscreen is None:
            return
        if not units:
            return

        from pycc2.presentation.rendering.cc2_building_renderer import (
            should_show_interior,
            render_cc2_building,
            floors_to_building_type,
            DamageLevel,
        )

        bounds = camera.view_bounds
        start_x = max(0, int(bounds[0].x // self.TILE_SIZE))
        end_x = min(game_map.width, int((bounds[1].x // self.TILE_SIZE) + 2))
        start_y = max(0, int(bounds[0].y // self.TILE_SIZE))
        end_y = min(game_map.height, int((bounds[1].y // self.TILE_SIZE) + 2))

        tile_screen_size = int(self.TILE_SIZE * camera.zoom)

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                # Only process building_enterable tiles (terrain ID 4)
                terrain_val = self._get_terrain_at(game_map, tx, ty)
                if terrain_val != 4:
                    continue

                # Check if any unit is inside this building tile
                if not should_show_interior((tx, ty), units, self.TILE_SIZE):
                    continue

                # Determine building type from floor count in enhanced tile data
                enhanced = game_map.get_enhanced_tile(tx, ty) if hasattr(game_map, 'get_enhanced_tile') else None
                floors = 1
                if enhanced and isinstance(enhanced, dict):
                    floors = int(enhanced.get("building_floors", 1))
                elif enhanced and hasattr(enhanced, 'building_floors'):
                    floors = int(getattr(enhanced, 'building_floors', 1))

                building_type = floors_to_building_type(floors)

                # Render interior view
                interior_surface = render_cc2_building(
                    building_type=building_type,
                    damage=DamageLevel.INTACT,
                    tile_size=self.TILE_SIZE,
                    interior_mode=True,
                    occupant_positions=[],
                )

                # Scale to screen size if needed
                if tile_screen_size != self.TILE_SIZE:
                    tw, th = interior_surface.get_size()
                    target_w = int(tw * camera.zoom)
                    target_h = int(th * camera.zoom)
                    if target_w > 0 and target_h > 0:
                        interior_surface = pygame.transform.scale(
                            interior_surface, (target_w, target_h),
                        )

                # Blit interior surface at screen position
                from pycc2.domain.value_objects.vec2 import Vec2
                world_x = tx * self.TILE_SIZE
                world_y = ty * self.TILE_SIZE
                screen_pos = camera.world_to_screen(Vec2(world_x, world_y))

                self._offscreen.blit(interior_surface, (int(screen_pos[0]), int(screen_pos[1])))

    def _draw_building_floor_numbers(
        self, game_map: GameMap, camera: Camera,
    ) -> None:
        """Draw floor count numbers on building roof tiles.

        The number displayed matches the `building_floors` data from the
        map tile, which also drives the LOS visibility bonus.
        """
        if self._screen is None or self._offscreen is None:
            return

        bounds = camera.view_bounds
        start_x = max(0, int(bounds[0].x // self.TILE_SIZE))
        end_x = min(game_map.width, int((bounds[1].x // self.TILE_SIZE) + 2))
        start_y = max(0, int(bounds[0].y // self.TILE_SIZE))
        end_y = min(game_map.height, int((bounds[1].y // self.TILE_SIZE) + 2))

        tile_screen_size = int(self.TILE_SIZE * camera.zoom)

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                terrain_val = self._get_terrain_at(game_map, tx, ty)
                if terrain_val != 4:  # Only building_enterable
                    continue

                # Read building_floors from enhanced tile data
                enhanced = game_map.get_enhanced_tile(tx, ty) if hasattr(game_map, 'get_enhanced_tile') else None
                floors = None
                if enhanced and isinstance(enhanced, dict):
                    floors = enhanced.get("building_floors")
                elif enhanced and hasattr(enhanced, 'building_floors'):
                    floors = getattr(enhanced, 'building_floors', None)

                if floors is None or int(floors) <= 1:
                    continue  # Don't show number for single-floor buildings

                # Draw floor number on the roof
                from pycc2.domain.value_objects.vec2 import Vec2
                world_x = tx * self.TILE_SIZE
                world_y = ty * self.TILE_SIZE
                screen_pos = camera.world_to_screen(Vec2(world_x, world_y))

                font_size = max(10, tile_screen_size // 3)
                font = pygame.font.SysFont("arial", font_size, bold=True)
                text = font.render(str(int(floors)), True, (255, 215, 0))  # Gold number
                text_rect = text.get_rect(
                    center=(int(screen_pos[0]) + tile_screen_size // 2,
                            int(screen_pos[1]) + tile_screen_size // 2),
                )
                self._offscreen.blit(text, text_rect)

    def _draw_vl_flags(self, game_map: GameMap, camera: Camera) -> None:
        """Draw Victory Location flags and edge arrows on the map.

        Delegates to SpriteRenderer if available, otherwise draws directly.
        """
        if self._offscreen is None:
            return

        # Delegate to SpriteRenderer which has the VL flag drawing methods
        if self._sprite_renderer is not None:
            # Point SpriteRenderer at our offscreen buffer temporarily
            original_target = self._sprite_renderer._target_surface
            self._sprite_renderer._target_surface = self._offscreen
            try:
                self._sprite_renderer._draw_vl_flags(game_map, camera)
            finally:
                self._sprite_renderer._target_surface = original_target
            return

        # Fallback: simple direct drawing if no SpriteRenderer
        import math
        import time as _time
        from pycc2.domain.value_objects.vec2 import Vec2

        objectives = getattr(game_map, 'objectives', [])
        if not objectives:
            return

        screen_w = self._offscreen.get_width()
        screen_h = self._offscreen.get_height()
        off_screen_vls: list[tuple[int, int, str]] = []

        for obj in objectives:
            tile_x = obj.position.x * self.TILE_SIZE + self.TILE_SIZE // 2
            tile_y = obj.position.y * self.TILE_SIZE + self.TILE_SIZE // 2
            sp = camera.world_to_screen(Vec2(tile_x, tile_y))
            sx, sy = int(sp[0]), int(sp[1])

            owner = getattr(obj, 'owner', None) or 'neutral'
            margin = 60
            on_screen = (-margin < sx < screen_w + margin and -margin < sy < screen_h + margin)

            if on_screen:
                # Simple flag drawing
                pygame.draw.line(self._offscreen, (80, 80, 80), (sx, sy), (sx, sy - 20), 2)
                if owner == 'allies':
                    flag_color = (60, 100, 200)
                elif owner == 'axis':
                    flag_color = (200, 60, 60)
                else:
                    flag_color = (200, 200, 200)
                flag_points = [
                    (sx + 1, sy - 20), (sx + 14, sy - 17),
                    (sx + 13, sy - 10), (sx + 1, sy - 13),
                ]
                pygame.draw.polygon(self._offscreen, flag_color, flag_points)
                pygame.draw.polygon(self._offscreen, (0, 0, 0), flag_points, 1)

                # V02增强: 显示VP数字（大号黄色+阴影描边+缩放动画）
                vp_value = getattr(obj, 'points', None)
                if vp_value is not None and isinstance(vp_value, (int, float)):
                    try:
                        font = pygame.font.Font(None, 38)  # 38px bold (原28→38)
                        vp_text = str(int(vp_value))

                        # 脉冲动画效果（缩放+透明度双重效果）
                        pulse_scale = math.sin(_time.time() * 3.0) * 0.05 + 1.0  # 缩放因子 0.95~1.05
                        pulse_alpha = int(200 + 55 * abs(math.sin(_time.time() * 2.0)))

                        # 绘制黑色描边（4方向1px偏移，更清晰锐利）
                        text_color = (255, 220, 100)  # 亮金黄色 RGB(255, 220, 100)

                        base_x = sx - font.size(vp_text)[0] // 2
                        base_y = sy - 40

                        for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
                            outline_surf = font.render(vp_text, True, (0, 0, 0))
                            outline_surf.set_alpha(pulse_alpha)
                            offset_x = int(base_x + dx * pulse_scale)
                            offset_y = int(base_y + dy * pulse_scale)
                            self._offscreen.blit(outline_surf, (offset_x, offset_y))

                        # 绘制主文字（亮金黄色+缩放动画）
                        text_surf = font.render(vp_text, True, text_color)
                        text_surf.set_alpha(pulse_alpha)

                        if pulse_scale != 1.0:
                            new_w = int(text_surf.get_width() * pulse_scale)
                            new_h = int(text_surf.get_height() * pulse_scale)
                            text_surf = pygame.transform.scale(text_surf, (new_w, new_h))

                        final_x = int(base_x - (text_surf.get_width() - font.size(vp_text)[0]) // 2)
                        final_y = int(base_y - (text_surf.get_height() - font.size(vp_text)[1]) // 2)
                        self._offscreen.blit(text_surf, (final_x, final_y))
                    except (AttributeError, ValueError):
                        pass  # 字体渲染失败时静默跳过
            else:
                off_screen_vls.append((tile_x, tile_y, owner))

        # Edge arrows for off-screen VLs
        arrow_margin = 30
        for wx, wy, owner in off_screen_vls:
            sp = camera.world_to_screen(Vec2(wx, wy))
            sx, sy = sp[0], sp[1]
            cx = max(arrow_margin, min(screen_w - arrow_margin, sx))
            cy = max(arrow_margin, min(screen_h - arrow_margin, sy))
            color = (60, 100, 200) if owner == 'allies' else (200, 60, 60) if owner == 'axis' else (200, 200, 200)
            angle = math.atan2(sy - cy, sx - cx)
            arrow_size = 10
            tip_x = cx + arrow_size * math.cos(angle)
            tip_y = cy + arrow_size * math.sin(angle)
            left_x = cx + arrow_size * math.cos(angle + 2.5)
            left_y = cy + arrow_size * math.sin(angle + 2.5)
            right_x = cx + arrow_size * math.cos(angle - 2.5)
            right_y = cy + arrow_size * math.sin(angle - 2.5)
            pygame.draw.polygon(self._offscreen, color, [
                (int(tip_x), int(tip_y)),
                (int(left_x), int(left_y)),
                (int(right_x), int(right_y)),
            ])

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

    TERRAIN_BASE_COLORS = {
        0: (76, 112, 52),
        1: (139, 119, 101),
        2: (68, 105, 48),
        3: (45, 68, 33),
        4: (139, 115, 85),
        5: (120, 118, 115),
        6: (62, 87, 117),
        7: (85, 70, 55),
        8: (110, 108, 105),
        9: (135, 115, 80),
        10: (95, 145, 165),
        11: (160, 140, 100),
        12: (90, 85, 75),
    }

    def _render_terrain_transitions(
        self, game_map: GameMap, camera: Camera,
        start_x: int, end_x: int, start_y: int, end_y: int,
        tile_screen_size: int
    ) -> None:
        """Render gradient transition strips between adjacent tiles of different terrain types.

        P2-11 Enhanced Version:
        - Smooth color interpolation (linear blend from current to neighbor color)
        - Middle-color edge pixels (average of two terrain colors at boundary)
        - Directional alpha fading (softer transitions toward tile center)
        - Enhanced caching for performance

        For each tile, checks 4 neighbors (N/S/E/W). When a neighbor has a
        different terrain type, draws a 4-6px gradient strip on the shared edge
        that blends from the current tile's base color to the neighbor's base
        color, creating smooth visual transitions (e.g. grass→road, grass→water).

        Uses caching keyed by (tx, ty, current_terrain, neighbor_terrain, direction)
        to avoid per-frame recalculation. Cache is invalidated when the map changes.
        """
        if self._screen is None or self._offscreen is None or tile_screen_size < 8:
            return

        from pycc2.domain.value_objects.vec2 import Vec2

        try:
            current_map_hash = hash((game_map.width, game_map.height, id(game_map)))
            if current_map_hash != self._last_map_hash:
                self._transition_cache.clear()
        except (ValueError, TypeError):
            pass

        # P2-11: Slightly wider transition strips for smoother blending
        strip_width = max(5, min(7, tile_screen_size // 8))

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                current = self._get_terrain_at(game_map, tx, ty)
                if current < 0:
                    continue

                neighbors = [
                    (tx, ty - 1, 'north'),
                    (tx, ty + 1, 'south'),
                    (tx + 1, ty, 'east'),
                    (tx - 1, ty, 'west'),
                ]

                for nx, ny, direction in neighbors:
                    if nx < 0 or ny < 0 or nx >= game_map.width or ny >= game_map.height:
                        continue
                    neighbor = self._get_terrain_at(game_map, nx, ny)
                    if neighbor < 0 or neighbor == current:
                        continue

                    cache_key = (tx, ty, current, neighbor, direction)
                    if cache_key in self._transition_cache:
                        cached_surf, cached_rect = self._transition_cache[cache_key]
                        self._offscreen.blit(cached_surf, cached_rect)
                        continue

                    color_from = self.TERRAIN_BASE_COLORS.get(current, (128, 128, 128))
                    color_to = self.TERRAIN_BASE_COLORS.get(neighbor, (128, 128, 128))

                    # P2-11 Enhancement: Calculate middle color (average of two terrain colors)
                    middle_color = (
                        (color_from[0] + color_to[0]) // 2,
                        (color_from[1] + color_to[1]) // 2,
                        (color_from[2] + color_to[2]) // 2,
                    )

                    world_x = tx * self.TILE_SIZE
                    world_y = ty * self.TILE_SIZE
                    screen_pos = camera.world_to_screen(Vec2(world_x, world_y))
                    base_x = int(screen_pos[0])
                    base_y = int(screen_pos[1])

                    if direction == 'north':
                        rect = pygame.Rect(base_x, base_y, tile_screen_size, strip_width)
                    elif direction == 'south':
                        rect = pygame.Rect(base_x, base_y + tile_screen_size - strip_width, tile_screen_size, strip_width)
                    elif direction == 'east':
                        rect = pygame.Rect(base_x + tile_screen_size - strip_width, base_y, strip_width, tile_screen_size)
                    else:
                        rect = pygame.Rect(base_x, base_y, strip_width, tile_screen_size)

                    strip_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)

                    # P2-11 Enhanced interpolation with middle-color emphasis
                    if direction in ('north', 'south'):
                        for col in range(rect.width):
                            t = col / max(1, rect.width - 1)  # 0.0 (from) → 1.0 (to)

                            # Smooth interpolation with sinusoidal easing for natural look
                            smooth_t = 0.5 * (1 - math.cos(t * math.pi))  # Ease in-out

                            # Color interpolation: from → middle → to
                            if t < 0.5:
                                # First half: blend from color_from to middle_color
                                local_t = t * 2  # 0.0 → 1.0
                                r = int(color_from[0] * (1 - local_t) + middle_color[0] * local_t)
                                g = int(color_from[1] * (1 - local_t) + middle_color[1] * local_t)
                                b = int(color_from[2] * (1 - local_t) + middle_color[2] * local_t)
                            else:
                                # Second half: blend from middle_color to color_to
                                local_t = (t - 0.5) * 2  # 0.0 → 1.0
                                r = int(middle_color[0] * (1 - local_t) + color_to[0] * local_t)
                                g = int(middle_color[1] * (1 - local_t) + color_to[1] * local_t)
                                b = int(middle_color[2] * (1 - local_t) + color_to[2] * local_t)

                            for row in range(rect.height):
                                edge_t = row / max(1, rect.height - 1)
                                # Directional alpha fade (stronger at edge, fades inward)
                                if direction == 'north':
                                    # North: stronger at top (row=0), fades downward
                                    alpha = int(140 * (1 - edge_t ** 0.7))
                                else:
                                    # South: stronger at bottom (row=max), fades upward
                                    alpha = int(140 * edge_t ** 0.7)

                                # P2-11: Boost alpha at exact boundary (middle of strip)
                                boundary_boost = 1.0
                                if 0.4 <= edge_t <= 0.6:
                                    boundary_boost = 1.3  # 30% brighter at boundary

                                alpha = int(min(255, alpha * boundary_boost))
                                alpha = max(0, min(255, alpha))
                                strip_surf.set_at((col, row), (r, g, b, alpha))
                    else:
                        for row in range(rect.height):
                            t = row / max(1, rect.height - 1)  # 0.0 (from) → 1.0 (to)

                            # Smooth interpolation with sinusoidal easing
                            smooth_t = 0.5 * (1 - math.cos(t * math.pi))

                            # Color interpolation: from → middle → to
                            if t < 0.5:
                                local_t = t * 2
                                r = int(color_from[0] * (1 - local_t) + middle_color[0] * local_t)
                                g = int(color_from[1] * (1 - local_t) + middle_color[1] * local_t)
                                b = int(color_from[2] * (1 - local_t) + middle_color[2] * local_t)
                            else:
                                local_t = (t - 0.5) * 2
                                r = int(middle_color[0] * (1 - local_t) + color_to[0] * local_t)
                                g = int(middle_color[1] * (1 - local_t) + color_to[1] * local_t)
                                b = int(middle_color[2] * (1 - local_t) + color_to[2] * local_t)

                            for col in range(rect.width):
                                edge_t = col / max(1, rect.width - 1)
                                # Directional alpha fade
                                if direction == 'west':
                                    # West: stronger at left (col=0), fades rightward
                                    alpha = int(140 * (1 - edge_t ** 0.7))
                                else:
                                    # East: stronger at right (col=max), fades leftward
                                    alpha = int(140 * edge_t ** 0.7)

                                # P2-11: Boost alpha at exact boundary
                                boundary_boost = 1.0
                                if 0.4 <= edge_t <= 0.6:
                                    boundary_boost = 1.3

                                alpha = int(min(255, alpha * boundary_boost))
                                alpha = max(0, min(255, alpha))
                                strip_surf.set_at((col, row), (r, g, b, alpha))

                    self._transition_cache[cache_key] = (strip_surf, rect)
                    self._offscreen.blit(strip_surf, rect)

    def _apply_terrain_edge_smoothing(
        self, game_map: GameMap, camera: Camera,
        start_x: int, end_x: int, start_y: int, end_y: int,
        tile_screen_size: int
    ) -> None:
        """Apply subtle edge smoothing between different terrain types for CC2-like natural look.

        Creates 2-3 pixel wide semi-transparent overlays at terrain boundaries
        to soften harsh edges. Uses caching to avoid per-frame recalculation.

        Performance optimizations:
        - Only processes non-autotile terrain boundaries (grass-dirt, grass-road)
        - Caches smoothed edges and only rebuilds when map changes
        - Skips tiles where all neighbors are same terrain type
        """
        if self._screen is None or self._offscreen is None or tile_screen_size < 8:
            return

        from pycc2.domain.value_objects.vec2 import Vec2

        # Check if cache needs rebuild (simple hash-based dirty check)
        try:
            current_map_hash = hash((game_map.width, game_map.height, id(game_map)))
            if current_map_hash != self._last_map_hash or self._edge_smooth_dirty:
                self._edge_smooth_cache.clear()
                self._terrain_tile_cache.invalidate()  # Invalidate tile cache when map changes
                self._last_map_hash = current_map_hash
                self._edge_smooth_dirty = False
        except (ValueError, TypeError) as e:
            logging.debug(f"Map hash/cache update failed: {e}")

        # Autotile terrains that handle their own edges (skip these)
        autotile_terrains = {5, 6, 7}
        # Non-autotile terrain transitions that benefit from smoothing
        smoothable_pairs = {
            (0, 1), (1, 0), (0, 2), (2, 0), (1, 2), (2, 1),
            (0, 3), (3, 0), (1, 3), (3, 1),
        }

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                current = self._get_terrain_at(game_map, tx, ty)
                if current < 0 or current in autotile_terrains:
                    continue

                neighbors = [
                    (tx + 1, ty, 'right'), (tx - 1, ty, 'left'),
                    (tx, ty + 1, 'down'), (tx, ty - 1, 'up'),
                ]

                for nx, ny, direction in neighbors:
                    if nx < start_x or nx >= end_x or ny < start_y or ny >= end_y:
                        continue

                    neighbor = self._get_terrain_at(game_map, nx, ny)
                    if neighbor < 0 or neighbor == current or neighbor in autotile_terrains:
                        continue
                    if (current, neighbor) not in smoothable_pairs:
                        continue

                    cache_key = (min(tx, nx), min(ty, ny), max(tx, nx), max(ty, ny))
                    if cache_key in self._edge_smooth_cache:
                        cached_surf, cached_rect = self._edge_smooth_cache[cache_key]
                        self._offscreen.blit(cached_surf, cached_rect, special_flags=pygame.BLEND_RGBA_ADD)
                        continue

                    world_x = tx * self.TILE_SIZE
                    world_y = ty * self.TILE_SIZE
                    screen_pos = camera.world_to_screen(Vec2(world_x, world_y))
                    base_x = int(screen_pos[0])
                    base_y = int(screen_pos[1])

                    try:
                        pal = self._palette_gen
                        color1 = pal.get_color(current, 4)
                        color2 = pal.get_color(neighbor, 4)
                        blend_color = (
                            (color1[0] + color2[0]) // 2,
                            (color1[1] + color2[1]) // 2,
                            (color1[2] + color2[2]) // 2,
                            45,
                        )
                    except (ValueError, TypeError) as e:
                        logging.debug(f"Edge color blending failed: {e}")
                        blend_color = (80, 80, 80, 45)

                    edge_width = max(2, min(3, tile_screen_size // 16))

                    if direction in ('right', 'left'):
                        edge_x = base_x + (tile_screen_size if direction == 'left' else 0)
                        edge_rect = pygame.Rect(edge_x, base_y, edge_width, tile_screen_size)
                    else:
                        edge_y = base_y + (tile_screen_size if direction == 'up' else 0)
                        edge_rect = pygame.Rect(base_x, edge_y, tile_screen_size, edge_width)

                    edge_surf = pygame.Surface((edge_rect.width, edge_rect.height), pygame.SRCALPHA)

                    for i in range(edge_rect.width if direction in ('right', 'left') else edge_rect.height):
                        alpha = int(45 * (1 - abs(i - (edge_width // 2)) / max(1, edge_width)))
                        alpha = max(10, min(45, alpha))

                        if direction in ('right', 'left'):
                            pygame.draw.line(edge_surf, (*blend_color[:3], alpha), (i, 0), (i, edge_rect.height))
                        else:
                            pygame.draw.line(edge_surf, (*blend_color[:3], alpha), (0, i), (edge_rect.width, i))

                    self._edge_smooth_cache[cache_key] = (edge_surf, edge_rect)
                    self._offscreen.blit(edge_surf, edge_rect, special_flags=pygame.BLEND_RGBA_ADD)

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
    
    def _apply_environment_lighting(self, game_map: GameMap, camera: Camera, units: list | None = None) -> None:
        """Apply environment lighting effects to the offscreen buffer.

        Adds:
        - Subtle shadow offset on northeast side of buildings (sun from southwest)
        - Slight warm tint to the overall scene
        - Slightly darker edges (vignette effect)
        - Unit shadow dots (small dark circles beneath each unit)
        """
        if self._offscreen is None:
            return

        screen_w, screen_h = self._offscreen.get_size()

        # 1. Building shadows (northeast offset, sun from southwest)
        self._draw_building_shadows(game_map, camera)

        # 2. Unit shadow dots (sun from southwest → shadow offset to northeast)
        if units:
            self._draw_unit_shadows(units, camera)

        # 3. Warm tint overlay (subtle orange-gold tint)
        try:
            warm_overlay = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
            warm_overlay.fill((255, 220, 160, 12))  # Very subtle warm tint
            self._offscreen.blit(warm_overlay, (0, 0))
        except (ValueError, pygame.error) as e:
            logging.debug(f"Warm tint overlay failed: {e}")

        # 4. Vignette effect (darker edges)
        try:
            vignette = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
            # Draw semi-transparent dark borders that fade toward center
            edge_width = max(30, screen_w // 8)
            edge_height = max(30, screen_h // 8)
            # Top edge
            for i in range(edge_height):
                alpha = int(40 * (1.0 - i / edge_height))
                pygame.draw.line(vignette, (0, 0, 0, alpha), (0, i), (screen_w, i))
            # Bottom edge
            for i in range(edge_height):
                alpha = int(40 * (1.0 - i / edge_height))
                y = screen_h - 1 - i
                pygame.draw.line(vignette, (0, 0, 0, alpha), (0, y), (screen_w, y))
            # Left edge
            for i in range(edge_width):
                alpha = int(40 * (1.0 - i / edge_width))
                pygame.draw.line(vignette, (0, 0, 0, alpha), (i, 0), (i, screen_h))
            # Right edge
            for i in range(edge_width):
                alpha = int(40 * (1.0 - i / edge_width))
                x = screen_w - 1 - i
                pygame.draw.line(vignette, (0, 0, 0, alpha), (x, 0), (x, screen_h))
            self._offscreen.blit(vignette, (0, 0))
        except (ValueError, pygame.error) as e:
            logging.debug(f"Vignette effect failed: {e}")

    def _draw_building_shadows(self, game_map: GameMap, camera: Camera) -> None:
        """Draw shadow strips on the northeast side of buildings (sun from southwest)."""
        if self._offscreen is None:
            return

        from pycc2.domain.value_objects.vec2 import Vec2

        bounds = camera.view_bounds
        start_x = max(0, int(bounds[0].x // self.TILE_SIZE))
        end_x = min(game_map.width, int((bounds[1].x // self.TILE_SIZE) + 2))
        start_y = max(0, int(bounds[0].y // self.TILE_SIZE))
        end_y = min(game_map.height, int((bounds[1].y // self.TILE_SIZE) + 2))

        shadow_offset = max(3, int(self.TILE_SIZE * camera.zoom * 0.12))
        shadow_alpha = 35  # Semi-transparent dark overlay (alpha ~30-40)

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                try:
                    etile = self._get_enhanced_tile(game_map, tx, ty)
                    if etile is not None:
                        terrain_val = etile.base_terrain
                    else:
                        terrain_val = int(game_map.tile_grid[ty, tx])

                    # Only add shadows for building tiles (4, 5)
                    if terrain_val not in (4, 5):
                        continue

                    world_x = tx * self.TILE_SIZE
                    world_y = ty * self.TILE_SIZE
                    sp = camera.world_to_screen(Vec2(world_x, world_y))
                    sx, sy = int(sp[0]), int(sp[1])
                    tile_screen_size = int(self.TILE_SIZE * camera.zoom)

                    # Shadow on northeast side (offset left and up — sun from southwest)
                    # Vertical shadow strip on the left side
                    shadow_surf = pygame.Surface(
                        (shadow_offset, tile_screen_size + shadow_offset),
                        pygame.SRCALPHA,
                    )
                    shadow_surf.fill((0, 0, 0, shadow_alpha))
                    self._offscreen.blit(
                        shadow_surf,
                        (sx - shadow_offset, sy - shadow_offset),
                    )

                    # Horizontal shadow strip on the top side
                    shadow_surf2 = pygame.Surface(
                        (tile_screen_size + shadow_offset, shadow_offset),
                        pygame.SRCALPHA,
                    )
                    shadow_surf2.fill((0, 0, 0, shadow_alpha))
                    self._offscreen.blit(
                        shadow_surf2,
                        (sx - shadow_offset, sy - shadow_offset),
                    )
                except (ValueError, pygame.error) as e:
                    logging.debug(f"Building shadow draw failed: {e}")
                    continue

    def _draw_unit_shadows(self, units: list, camera: Camera) -> None:
        """
        Draw enhanced perspective ellipse shadows beneath each alive unit.

        Features:
        - Perspective-correct elliptical shadows (wider than tall for 45° view)
        - Soft edge falloff using multi-layer alpha blending
        - Size scaling based on unit type (tank > infantry)
        - Dynamic alpha based on HP (dying units have fainter shadows)
        
        统一阴影方向：左上45°光源（light_angle=-π/4）→ 阴影投射向右下（+x, +y）
        与 TopDownLightingConfig 配置保持一致
        """
        if self._offscreen is None:
            return

        from pycc2.domain.value_objects.vec2 import Vec2

        base_shadow_alpha = int(35 * self._lighting_config.shadow_darkness)  # Use config value
        # Shadow offset: southeast direction (positive x, positive y in screen coords)
        # Light from top-left (-π/4) → shadow to bottom-right (+x, +y)
        offset_x = max(2, int(4 * camera.zoom))
        offset_y = max(2, int(4 * camera.zoom))

        for unit in units:
            if not unit.is_alive:
                continue

            pos = unit.position.pixel_position
            sp = camera.world_to_screen(pos)
            sx, sy = int(sp[0]) + offset_x, int(sp[1]) + offset_y

            base_radius = max(3, int(5 * camera.zoom))

            unit_type_str = "infantry"
            if hasattr(unit, 'unit_type'):
                unit_type_str = str(unit.unit_type).lower()
            elif hasattr(unit, 'category'):
                unit_type_str = str(unit.category).lower()

            is_large_unit = any(t in unit_type_str for t in ["tank", "armor", "sherman", "vehicle"])
            shadow_width = base_radius * (2.2 if is_large_unit else 1.8)
            shadow_height = base_radius * (0.7 if is_large_unit else 0.5)

            hp_ratio = 1.0
            if hasattr(unit, 'health') and unit.health:
                try:
                    hp_ratio = unit.health.hp / max(unit.health.max_hp, 1)
                except (AttributeError, ZeroDivisionError):
                    pass

            shadow_alpha = int(base_shadow_alpha * max(0.3, hp_ratio))

            surf_w = int(shadow_width * 2) + 8
            surf_h = int(shadow_height * 2) + 8
            shadow_surf = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
            center_x, center_y = surf_w // 2, surf_h // 2

            for layer in range(3):
                layer_factor = 1.0 - (layer * 0.25)
                layer_alpha = int(shadow_alpha * layer_factor)
                layer_w = int(shadow_width * (1.0 + layer * 0.3))
                layer_h = int(shadow_height * (1.0 + layer * 0.2))

                rect = (
                    center_x - layer_w,
                    center_y - layer_h,
                    layer_w * 2,
                    layer_h * 2,
                )
                pygame.draw.ellipse(shadow_surf, (0, 0, 0, layer_alpha), rect)

            self._offscreen.blit(shadow_surf, (sx - center_x, sy - center_y))

    def _get_health_tinted_color(self, base_color: tuple, unit) -> tuple:
        """Apply health-based color tinting to unit color.

        Color gradient: Healthy (100%) → Wounded (50%) → Critical (10%)
        - >75% HP: Normal brightness
        - 50-75% HP: Slightly darker + yellowish tint
        - 25-50% HP: Noticeable red-orange tint
        - <25% HP: Deep red tone (critical)
        """
        color = base_color

        hp_ratio = 1.0
        if hasattr(unit, 'health') and unit.health:
            try:
                hp_ratio = unit.health.hp / max(unit.health.max_hp, 1)
            except (AttributeError, ZeroDivisionError):
                pass

        if hp_ratio > 0.75:
            pass
        elif hp_ratio > 0.5:
            color = (
                min(255, int(color[0] * 1.1)),
                color[1],
                int(color[2] * 0.8),
            )
        elif hp_ratio > 0.25:
            color = (
                min(255, int(color[0] * 1.2)),
                int(color[1] * 0.7),
                int(color[2] * 0.5),
            )
        else:
            color = (
                min(255, int(color[0] * 1.3)),
                int(color[1] * 0.4),
                int(color[2] * 0.3),
            )

        return color

    def _draw_direction_indicator(
        self, cx: int, cy: int, radius: int, unit_color: tuple
    ) -> None:
        """Draw a direction arrow on top of unit showing facing direction.

        Arrow length = radius * 0.6, color contrasts with unit color.
        Uses unit.facing_direction or unit.direction, defaults to up (-π/2).
        """
        if self._offscreen is None:
            return

        facing = -math.pi / 2
        if hasattr(unit, 'facing_direction'):
            facing = unit.facing_direction
        elif hasattr(unit, 'direction'):
            facing = unit.direction

        arrow_length = max(4, int(radius * 0.6))
        arrow_width = max(2, arrow_length // 3)

        end_x = cx + int(arrow_length * math.cos(facing))
        end_y = cy + int(arrow_length * math.sin(facing))

        brightness = sum(unit_color[:3]) / 3
        arrow_color = (0, 0, 0) if brightness > 127 else (255, 255, 255)

        pygame.draw.line(self._offscreen, arrow_color, (cx, cy), (end_x, end_y), 2)

        left_angle = facing + math.pi - (math.pi / 6)
        right_angle = facing + math.pi + (math.pi / 6)

        left_x = end_x + int(arrow_width * math.cos(left_angle))
        left_y = end_y + int(arrow_width * math.sin(left_angle))
        right_x = end_x + int(arrow_width * math.cos(right_angle))
        right_y = end_y + int(arrow_width * math.sin(right_angle))

        pygame.draw.polygon(
            self._offscreen,
            arrow_color,
            [(end_x, end_y), (left_x, left_y), (right_x, right_y)],
        )

    def _draw_movement_mode_overlay(
        self, unit, cx: int, cy: int, radius: int, base_color: tuple
    ) -> None:
        """Draw visual overlay for movement mode states.

        Modes:
        - fast_move: Motion trail (semi-transparent copy offset backward)
        - sneak: Reduced opacity + edge blur effect
        - defend: Shield indicator ring or armor arc
        - normal: No overlay
        """
        if self._offscreen is None:
            return

        movement_mode = getattr(unit, "movement_mode", "normal")

        if movement_mode == "fast_move":
            facing = -math.pi / 2
            if hasattr(unit, "facing_direction"):
                facing = unit.facing_direction
            elif hasattr(unit, "direction"):
                facing = unit.direction

            offset_dist = 3
            trail_cx = cx - int(offset_dist * math.cos(facing))
            trail_cy = cy - int(offset_dist * math.sin(facing))

            trail_size = radius * 2 + 4
            trail_surf = pygame.Surface((trail_size, trail_size), pygame.SRCALPHA)
            trail_center = trail_size // 2

            trail_color = (*base_color[:3], 100)

            trail_radius = max(3, radius - 2)
            pygame.draw.circle(trail_surf, trail_color, (trail_center, trail_center), trail_radius)

            self._offscreen.blit(
                trail_surf,
                (trail_cx - trail_center, trail_cy - trail_center),
            )

        elif movement_mode == "sneak":
            alpha_surface = pygame.Surface((radius * 2 + 10, radius * 2 + 10), pygame.SRCALPHA)
            center = radius + 5

            sneak_color = (*base_color[:3], 140)
            pygame.draw.circle(alpha_surface, sneak_color, (center, center), radius)

            edge_alpha = 80
            for i in range(3):
                edge_r = radius + 2 + i
                edge_color = (*base_color[:3], edge_alpha - i * 20)
                pygame.draw.circle(alpha_surface, edge_color, (center, center), edge_r, 1)

            self._offscreen.blit(alpha_surface, (cx - center, cy - center))

        elif movement_mode == "defend":
            shield_color = (100, 200, 255, 180)
            shield_surf = pygame.Surface((radius * 2 + 20, radius * 2 + 20), pygame.SRCALPHA)
            center = radius + 10

            inner_r = radius + 4
            outer_r = radius + 8

            pygame.draw.arc(
                shield_surf,
                shield_color,
                (
                    center - outer_r,
                    center - outer_r,
                    outer_r * 2,
                    outer_r * 2,
                ),
                math.pi * 0.75,
                math.pi * 2.25,
                3,
            )
            pygame.draw.arc(
                shield_surf,
                (*shield_color[:3], 120),
                (
                    center - inner_r,
                    center - inner_r,
                    inner_r * 2,
                    inner_r * 2,
                ),
                math.pi * 0.75,
                math.pi * 2.25,
                2,
            )

            self._offscreen.blit(shield_surf, (cx - center, cy - center))

    def _apply_height_lighting(self, surface: pygame.Surface, height: int) -> pygame.Surface:
        """Apply lighting adjustments based on tile height (fast numpy version)."""
        if height == 0:
            return surface

        result = surface.copy()
        brightness_factor = 1.0 + (height * 0.08)

        try:
            import numpy as np
            arr = pygame.surfarray.pixels3d(result)
            # Convert to float first to avoid uint8 overflow during multiply
            float_arr = arr.astype(np.float32) * brightness_factor
            np.clip(float_arr, 0, 255, out=float_arr)
            arr[:] = float_arr.astype(np.uint8)
            del arr
        except (ValueError, IndexError) as e:
            logging.debug(f"Brightness adjustment failed: {e}")

        return result

    def _apply_time_of_day_tint(self, surface: pygame.Surface) -> pygame.Surface:
        """
        Apply time-of-day color grading to the rendered scene.
        
        顶部视角专用 - 根据时间段调整整体色调：
        - dawn: 暖橙色，略暗
        - noon: 明亮（默认，不做处理）
        - dusk: 深橙红色，较暗
        - night: 蓝黑色调，很暗
        
        Performance optimization: Only re-generates tint when time_of_day changes.
        """
        config = self._lighting_config
        
        # Check if ToD changed (cache optimization)
        if config.time_of_day == self._last_time_of_day and self._tod_tint_cache is not None:
            # Apply cached tint
            surface.blit(self._tod_tint_cache, (0, 0))
            return surface
        
        # Update cache tracking
        self._last_time_of_day = config.time_of_day
        
        # Generate new tint overlay based on time of day
        if config.time_of_day == "dawn":
            # 黎明：暖橙色色调，略暗
            overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            overlay.fill((255, 180, 120, 25))  # 暖橙
            surface.blit(overlay, (0, 0))
            self._tod_tint_cache = overlay
            
        elif config.time_of_day == "noon":
            # 正午：明亮，轻微去饱和（不做处理或轻微提亮）
            self._tod_tint_cache = None  # No tint needed for noon
            
        elif config.time_of_day == "dusk":
            # 黄昏：深橙红色调，较暗
            overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            overlay.fill((200, 100, 50, 35))  # 深橙红
            surface.blit(overlay, (0, 0))
            self._tod_tint_cache = overlay
            
        elif config.time_of_day == "night":
            # 夜晚：蓝黑色调，很暗
            overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            overlay.fill((20, 30, 60, 80))  # 深蓝黑
            surface.blit(overlay, (0, 0))
            self._tod_tint_cache = overlay
            
        else:
            # Unknown time of day - no tint
            self._tod_tint_cache = None
            
        return surface

    def _apply_cc2_color_grading(self, surface: pygame.Surface) -> None:
        """应用CC2风格的色调分级（降低饱和度+轻微去亮）
        
        CC2 1997年游戏特征：
        - 整体偏暗（CRT显示器时代的设计习惯）
        - 低饱和度（像素艺术限制）
        - 轻微偏暖色调
        - 对比度适中（不是现代的高对比）
        """
        import numpy as np
        
        # 将surface转换为numpy数组进行像素操作
        arr = pygame.surfarray.array3d(surface).copy().astype(np.float32)
        
        # 1. 降低亮度 (乘以0.92)
        arr = arr * 0.92
        
        # 2. 降低饱和度 (向灰度混合15%)
        gray = np.mean(arr, axis=2, keepdims=True)
        arr = arr * 0.85 + gray * 0.15
        
        # 3. 轻微偏暖 (增加红色通道5%)
        arr[:,:,0] = np.clip(arr[:,:,0] * 1.05, 0, 255)
        
        # 4. 轻微增加对比度 (S-curve midtone boost)
        arr = np.clip(arr * 1.05 - 10, 0, 255)
        
        # 转回uint8并写回surface
        arr = arr.astype(np.uint8)
        pygame.surfarray.blit_array(surface, arr.swapaxes(0,1))

    def spawn_dynamic_light(self, position: tuple[int, int], 
                           radius: float, 
                           intensity: float,
                           color: tuple[int, int, int] = (255, 255, 200),
                           duration_ms: int = 200) -> None:
        """
        Register a dynamic point light source.
        
        用于临时动态光源（爆炸闪光、枪口焰、技能特效等）
        
        Args:
            position: Screen coordinates (x, y) of light center
            radius: Light radius in pixels (capped at MAX_DYNAMIC_LIGHT_RADIUS for performance)
            intensity: Brightness factor (0.0-1.0)
            color: RGB color tuple (default: warm white)
            duration_ms: Lifetime in milliseconds (default: 200ms for muzzle flash)
        """
        if not self._lighting_config.enable_dynamic_lights:
            return
            
        # Performance cap: enforce maximum concurrent lights
        if len(self._dynamic_lights) >= self._max_dynamic_lights:
            # Remove oldest light to make room
            self._dynamic_lights.pop(0)
            
        # Cap radius to prevent huge surfaces
        MAX_RADIUS = 200
        capped_radius = min(radius, MAX_RADIUS)
        
        self._dynamic_lights.append({
            'position': position,
            'radius': capped_radius,
            'intensity': max(0.0, min(1.0, intensity)),
            'color': color,
            'remaining_ms': duration_ms,
            'max_duration': duration_ms,
        })

    def update_dynamic_lights(self, dt_ms: int) -> None:
        """
        Update dynamic light lifecycles.
        
        Should be called from game loop's update() method.
        
        Args:
            dt_ms: Delta time in milliseconds since last frame
        """
        if not self._lighting_config.enable_dynamic_lights:
            return
            
        expired = []
        for light in self._dynamic_lights:
            light['remaining_ms'] -= dt_ms
            if light['remaining_ms'] <= 0:
                expired.append(light)
                
        for light in expired:
            self._dynamic_lights.remove(light)

    def _render_dynamic_lights(self) -> None:
        """
        Render all active dynamic lights to offscreen buffer.
        
        Uses radial gradient with multiple concentric circles for smooth falloff.
        Applies additive blending (BLEND_RGBA_ADD) for glow effect.
        
        Performance considerations:
        - Max 8 concurrent lights (enforced by spawn_dynamic_light)
        - Radius capped at 200px
        - Uses optimized multi-layer circle rendering
        """
        if not self._lighting_config.enable_dynamic_lights or not self._offscreen:
            return
            
        for light in self._dynamic_lights:
            # Calculate lifecycle progress (1.0 = just spawned, 0.0 = about to expire)
            progress = light['remaining_ms'] / light['max_duration']
            
            # Intensity fades over time (linear falloff)
            current_intensity = light['intensity'] * progress
            
            # Radius expands then contracts (visual effect)
            radius = int(light['radius'] * (2.0 - progress * 0.5))
            
            # Create surface for this light
            light_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            
            # Radial gradient with multiple concentric circles (4 layers)
            # Each layer has different opacity for smooth falloff
            for r_factor in [1.0, 0.7, 0.4, 0.2]:
                r = int(radius * r_factor)
                if r <= 0:
                    continue
                    
                # Alpha decreases toward center (outer layers more transparent)
                alpha = int(current_intensity * 255 * (1.0 - r_factor) * 0.5)
                alpha = min(255, max(0, alpha))  # Clamp to valid range
                
                color = (*light['color'], alpha)
                pygame.draw.circle(light_surf, color, (radius, radius), r)
            
            # Blit to offscreen buffer with additive blending (glow effect)
            pos = light['position']
            self._offscreen.blit(
                light_surf, 
                (pos[0] - radius, pos[1] - radius),
                special_flags=pygame.BLEND_RGBA_ADD
            )
    
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
        """Draw units using SpriteRenderer with PNG support, fallback to simple shapes."""
        if self._screen is None or self._offscreen is None:
            return

        if len(units) == 0:
            return

        # 如果SpriteRenderer已初始化，使用它（支持PNG精灵）
        if self._sprite_renderer is not None:
            # 设置SpriteRenderer绘制到offscreen buffer（消除临时替换hack）
            self._sprite_renderer._target_surface = self._offscreen
            
            # 使用SpriteRenderer绘制单位（会加载PNG）
            self._sprite_renderer._draw_units(units, camera, selected_unit_ids)
            
            # 恢复默认绘制目标
            self._sprite_renderer._target_surface = None
            return
        else:
            logger.warning("[EnhancedRenderer] SpriteRenderer is None! Using fallback shapes (no PNG sprites)")
        
        # Fallback: 如果SpriteRenderer未初始化，使用简单形状
        screen_w, screen_h = self._screen.get_size()

        # Draw each unit with EXTREME defensive coding
        for idx, unit in enumerate(units):
            try:
                # STEP 1: Get unit position (with multiple fallback strategies)
                cx, cy = None, None

                # Strategy A: Use pixel_position if available
                if hasattr(unit, 'position') and unit.position is not None:
                    if hasattr(unit.position, 'pixel_position'):
                        try:
                            pos = camera.world_to_screen(unit.position.pixel_position)
                            cx, cy = int(pos[0]), int(pos[1])
                        except (ValueError, TypeError) as e:
                            logging.debug(f"Unit pixel_position conversion failed: {e}")

                # Strategy B: Use tile_position as fallback
                if (cx is None or cy is None) and hasattr(unit, 'position') and unit.position is not None:
                    if hasattr(unit.position, 'tile_position') or hasattr(unit.position, 'tile_x'):
                        try:
                            tile_x = getattr(unit.position, 'tile_x', None)
                            tile_y = getattr(unit.position, 'tile_y', None)
                            if tile_x is not None and tile_y is not None:
                                from pycc2.domain.value_objects.vec2 import Vec2
                                world_pos = Vec2(tile_x * 16, tile_y * 16)
                                pos = camera.world_to_screen(world_pos)
                                cx, cy = int(pos[0]), int(pos[1])
                        except (ValueError, TypeError) as e:
                            logging.debug(f"Unit tile_position conversion failed: {e}")

                # Strategy C: Last resort - use index-based positioning (grid layout)
                if cx is None or cy is None:
                    # Place units in a visible grid pattern as emergency fallback
                    grid_x = (idx % 10) * 60 + 100  # Spread across screen
                    grid_y = (idx // 10) * 60 + 100
                    cx, cy = grid_x, grid_y

                # STEP 2: Skip if way off-screen (but be generous with bounds)
                if cx < -50 or cx > screen_w + 50 or cy < -50 or cy > screen_h + 50:
                    continue  # Unit is off-screen, skip it

                # STEP 3: Determine unit type for visual styling
                unit_name = ""
                unit_type_str = "infantry"  # Default

                if hasattr(unit, 'display_name'):
                    unit_name = str(unit.display_name)[:4]
                elif hasattr(unit, 'name'):
                    unit_name = str(unit.name)[:4]
                else:
                    unit_name = f"U{idx}"  # Fallback: use index

                if hasattr(unit, 'unit_type'):
                    unit_type_str = str(unit.unit_type).lower()
                elif hasattr(unit, 'category'):
                    unit_type_str = str(unit.category).lower()

                # STEP 4: Draw shape based on type (SIMPLE and RELIABLE)
                base_radius = max(12, int(15 * camera.zoom))

                # Make colors BRIGHT and VISIBLE (no subtle tones!)
                if "tank" in unit_type_str or "armor" in unit_type_str or "sherman" in unit_type_str or "vehicle" in unit_type_str:
                    # HEXAGON for tanks (BRIGHT YELLOW-ORANGE)
                    color = (255, 200, 0)  # Very bright yellow
                    radius = base_radius + 6
                    points = []
                    for i in range(6):
                        angle = math.pi / 3 * i
                        x = cx + int(radius * math.cos(angle))
                        y = cy + int(radius * math.sin(angle))
                        points.append((x, y))

                    color = self._get_health_tinted_color(color, unit)
                    pygame.draw.polygon(self._offscreen, color, points)
                    pygame.draw.polygon(self._offscreen, (255, 255, 255), points, 3)

                elif "mg" in unit_type_str or "machine" in unit_type_str or "at" in unit_type_str or "support" in unit_type_str:
                    # TRIANGLE for support (BRIGHT CYAN-BLUE)
                    color = (0, 220, 255)  # Bright cyan
                    radius = base_radius + 3
                    points = []
                    for i in range(3):
                        angle = math.pi / 3 * 2 * i - math.pi / 2
                        x = cx + int(radius * math.cos(angle))
                        y = cy + int(radius * math.sin(angle))
                        points.append((x, y))

                    color = self._get_health_tinted_color(color, unit)
                    pygame.draw.polygon(self._offscreen, color, points)
                    pygame.draw.polygon(self._offscreen, (255, 255, 255), points, 2)

                elif "sniper" in unit_type_str or "recon" in unit_type_str or "scout" in unit_type_str:
                    # DIAMOND for recon (BRIGHT MAGENTA-PURPLE)
                    color = (255, 0, 255)  # Bright magenta
                    radius = base_radius - 2
                    half = radius // 2
                    points = [
                        (cx, cy - radius),
                        (cx + half, cy),
                        (cx, cy + radius),
                        (cx - half, cy),
                    ]

                    color = self._get_health_tinted_color(color, unit)
                    pygame.draw.polygon(self._offscreen, color, points)
                    pygame.draw.polygon(self._offscreen, (255, 200, 255), points, 2)

                else:
                    # DEFAULT: CIRCLE for infantry (BRIGHT GREEN)
                    color = (0, 255, 80)  # Bright neon green
                    radius = base_radius

                    color = self._get_health_tinted_color(color, unit)
                    pygame.draw.circle(self._offscreen, color, (cx, cy), radius)
                    pygame.draw.circle(self._offscreen, (255, 255, 255), (cx, cy), radius, 2)

                # STEP 5: Draw label (CRITICAL for identification)
                try:
                    font = pygame.font.Font(None, max(16, int(18 * camera.zoom)))
                    label_surf = font.render(unit_name, True, (255, 255, 255))  # White text
                    label_x = cx - label_surf.get_width() // 2
                    label_y = cy + radius + 3

                    # Black background for readability
                    bg_padding = 3
                    bg_rect = pygame.Rect(
                        label_x - bg_padding,
                        label_y - bg_padding,
                        label_surf.get_width() + 2 * bg_padding,
                        label_surf.get_height() + 2 * bg_padding
                    )
                    pygame.draw.rect(self._offscreen, (0, 0, 0), bg_rect, border_radius=3)
                    pygame.draw.rect(self._offscreen, (100, 100, 100), bg_rect, width=1, border_radius=3)

                    # Blit text
                    self._offscreen.blit(label_surf, (label_x, label_y))
                except (ValueError, pygame.error) as e:
                    logging.debug(f"Unit label rendering failed: {e}")

                # STEP 6: Selection indicator (ENHANCED dual-layer glow + corner markers)
                is_selected = selected_unit_ids and unit.id in selected_unit_ids
                if is_selected:
                    pulse = abs(math.sin(pygame.time.get_ticks() * 0.008)) * 8
                    select_radius = radius + 8 + int(pulse)

                    outer_glow_radius = radius + 15 + int(pulse * 0.7)
                    glow_surf = pygame.Surface(
                        (outer_glow_radius * 2 + 10, outer_glow_radius * 2 + 10),
                        pygame.SRCALPHA,
                    )
                    glow_center = outer_glow_radius + 5
                    pygame.draw.circle(
                        glow_surf,
                        (255, 255, 255, 40),
                        (glow_center, glow_center),
                        outer_glow_radius,
                    )
                    self._offscreen.blit(
                        glow_surf,
                        (cx - glow_center, cy - glow_center),
                    )

                    inner_ring_radius = radius + 5 + int(pulse)
                    pygame.draw.circle(
                        self._offscreen,
                        (255, 255, 0),
                        (cx, cy),
                        inner_ring_radius,
                        3,
                    )
                    pygame.draw.circle(
                        self._offscreen,
                        (0, 255, 255),
                        (cx, cy),
                        inner_ring_radius - 2,
                        2,
                    )

                    corner_size = 8
                    corner_offset = radius + 12 + int(pulse * 0.5)
                    corner_color = (255, 255, 0)
                    corners = [
                        (cx - corner_offset, cy - corner_offset),  # top-left
                        (cx + corner_offset, cy - corner_offset),  # top-right
                        (cx - corner_offset, cy + corner_offset),  # bottom-left
                        (cx + corner_offset, cy + corner_offset),  # bottom-right
                    ]
                    for corner_x, corner_y in corners:
                        pygame.draw.line(
                            self._offscreen,
                            corner_color,
                            (corner_x, corner_y),
                            (corner_x + corner_size, corner_y),
                            2,
                        )
                        pygame.draw.line(
                            self._offscreen,
                            corner_color,
                            (corner_x, corner_y),
                            (corner_x, corner_y + corner_size),
                            2,
                        )

                # STEP 7: Direction indicator (shows unit facing)
                self._draw_direction_indicator(cx, cy, radius, color)

                # STEP 8: Movement mode overlay (fast_move/sneak/defend visualization)
                self._draw_movement_mode_overlay(unit, cx, cy, radius, color)

                # STEP 9: Damage visual effects (smoke/fire for damaged units)
                if hasattr(unit, 'is_damaged') and unit.is_damaged:
                    self._draw_damage_vfx(unit, cx, cy)

            except (AttributeError, ValueError) as e:
                # CRITICAL: NEVER crash on a single unit - just skip it
                logger.warning("Failed to render unit %s: %s", idx, e)
                continue

    def _draw_damage_vfx(self, unit: Unit, cx: int, cy: int) -> None:
        """STEP A-2: Render damage visual effects (smoke/fire) for damaged units.

        Based on unit.damage_state:
        - undamaged: No effects
        - light: Light gray smoke wisps (2-3 particles)
        - moderate: Thicker smoke (4-5 particles)
        - heavy: Thick smoke + orange fire glow (6+ particles)
        destroyed: Intense fire + thick black smoke
        """
        if not hasattr(unit, 'damage_state'):
            return

        state = unit.damage_state
        if state == "undamaged":
            return

        # Ensure VFX particles are generated
        if hasattr(unit, 'update_damage_vfx'):
            if not getattr(unit, '_smoke_particles', None):
                unit.update_damage_vfx()

        # Draw smoke particles
        smoke_particles = getattr(unit, '_smoke_particles', [])
        for particle in smoke_particles[:8]:  # Limit to 8 for performance
            px = cx + particle.get('x', 0)
            py = cy + particle.get('y', 0)
            alpha = particle.get('alpha', 100)
            size = particle.get('size', 3)

            # Smoke color: gray with transparency
            smoke_color = (120, 120, 120)

            # Create temporary surface for alpha blending
            smoke_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(smoke_surf, (*smoke_color, alpha), (size, size), size)
            self._offscreen.blit(smoke_surf, (px - size, py - size))

        # Draw fire particles (for heavy/destroyed)
        fire_particles = getattr(unit, '_fire_particles', [])
        for particle in fire_particles[:6]:  # Limit to 6 for performance
            px = cx + particle.get('x', 0)
            py = cy + particle.get('y', 0)
            color = particle.get('color', (220, 120, 20))
            size = particle.get('size', 3)

            # Fire glow effect (larger semi-transparent circle behind)
            glow_size = size + 2
            glow_surf = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*color, 80), (glow_size, glow_size), glow_size)
            self._offscreen.blit(glow_surf, (px - glow_size, py - glow_size))

            # Fire core (bright center)
            bright_color = tuple(min(255, c + 40) for c in color)
            core_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(core_surf, (*bright_color, 200), (size, size), size // 2 + 1)
            self._offscreen.blit(core_surf, (px - size, py - size))

    def _draw_hexagon(
        self, cx: int, cy: int, radius: int, color: tuple[int, int, int],
        selected: bool = False
    ) -> None:
        """Draw a hexagon-shaped unit (mimics CC2 style)."""
        if self._screen is None:
            return
        
        points = []
        for i in range(6):
            angle = math.pi / 3 * i - math.pi / 6
            x = cx + int(radius * math.cos(angle))
            y = cy + int(radius * math.sin(angle))
            points.append((x, y))
        
        # Fill
        pygame.draw.polygon(self._offscreen, color, points)
        
        # Outline (darker)
        outline_color = (
            max(0, color[0] - 50),
            max(0, color[1] - 50),
            max(0, color[2] - 50)
        )
        pygame.draw.polygon(self._offscreen, outline_color, points, 2)
        
        # Selection indicator
        if selected:
            select_color = (255, 255, 0)
            pygame.draw.circle(self._offscreen, select_color, (cx, cy), radius + 3, 2)

    def _render_building_shadows(self, game_map: GameMap, camera: Camera) -> None:
        """
        Render SE-direction shadows for all buildings.
        
        统一阴影方向：使用 ShadowRenderer 类，阴影投射向东南（右下）
        与 TopDownLightingConfig.light_angle = -π/4（左上光源）保持一致
        """
        if self._offscreen is None or self._shadow_renderer is None:
            return

        try:
            # Iterate through map tiles to find buildings
            # FIXED: Use game_map.tile_grid[y, x] which returns integer terrain type
            # TerrainType: 4=BUILDING_ENTERABLE, 5=BUILDING_SOLID
            buildings_found = 0
            for y in range(game_map.height):
                for x in range(game_map.width):
                    # Get terrain type as integer from tile_grid
                    terrain_int = int(game_map.tile_grid[y, x])

                    # Check if this is a building tile (4 or 5)
                    has_building = terrain_int in (4, 5)  # BUILDING_ENTERABLE or BUILDING_SOLID

                    if has_building:
                        # Convert tile position to screen coordinates
                        from pycc2.domain.value_objects.vec2 import Vec2
                        world_pos = Vec2(x * self.TILE_SIZE, y * self.TILE_SIZE)
                        screen_pos = camera.world_to_screen(world_pos)
                        sx, sy = int(screen_pos[0]), int(screen_pos[1])

                        # Render building shadow (offset southeast)
                        self._shadow_renderer.render_building_shadow(
                            self._offscreen,
                            sx, sy,
                            self.TILE_SIZE,  # Building width ≈ tile size
                            self.TILE_SIZE // 2  # Approximate building height
                        )
                        buildings_found += 1

            if buildings_found > 0:
                logger.debug(f"Rendered {buildings_found} building shadows")
        except RuntimeError as e:
            logger.warning(f"Failed to render building shadows: {e}")

    def _render_tree_shadows(self, game_map: GameMap, camera: Camera) -> None:
        """
        Render SE-direction shadows for trees/vegetation.
        
        统一阴影方向：使用 ShadowRenderer 类，阴影投射向东南（右下）
        与 TopDownLightingConfig.light_angle = -π/4（左上光源）保持一致
        """
        if self._offscreen is None or self._shadow_renderer is None:
            return

        try:
            # Iterate through map tiles to find trees
            # FIXED: Use game_map.tile_grid[y, x] which returns integer terrain type
            # TerrainType: 3=WOODS, 7=HEDGE
            trees_found = 0
            for y in range(game_map.height):
                for x in range(game_map.width):
                    # Get terrain type as integer from tile_grid
                    terrain_int = int(game_map.tile_grid[y, x])

                    # Check if this is a tree/vegetation tile (3 or 7)
                    is_tree = terrain_int in (3, 7)  # WOODS or HEDGE

                    if is_tree:
                        # Convert tile position to screen coordinates
                        from pycc2.domain.value_objects.vec2 import Vec2
                        world_pos = Vec2(x * self.TILE_SIZE, y * self.TILE_SIZE)
                        screen_pos = camera.world_to_screen(world_pos)
                        sx, sy = int(screen_pos[0]), int(screen_pos[1])

                        # Determine tree size based on terrain type
                        tree_size = "medium"
                        if terrain_int == 3:  # WOODS - larger forest areas
                            tree_size = "large"
                        elif terrain_int == 7:  # HEDGE - smaller individual hedges
                            tree_size = "small"

                        # Render tree shadow
                        self._shadow_renderer.render_tree_shadow(
                            self._offscreen,
                            sx, sy,
                            tree_size
                        )
                        trees_found += 1

            if trees_found > 0:
                logger.debug(f"Rendered {trees_found} tree shadows")
        except RuntimeError as e:
            logger.warning(f"Failed to render tree shadows: {e}")

    def _render_unit_shadows(self, units: list[Unit], camera: Camera) -> None:
        """Render SE-direction shadows for all units and vehicles."""
        if self._offscreen is None or self._shadow_renderer is None:
            return

        if len(units) == 0:
            return

        try:
            for unit in units:
                # Get unit position with defensive coding
                cx, cy = None, None
                unit_w, unit_h = 16, 16  # Default unit size

                # Try to get pixel position
                if hasattr(unit, 'position') and unit.position is not None:
                    if hasattr(unit.position, 'pixel_position'):
                        try:
                            pos = camera.world_to_screen(unit.position.pixel_position)
                            cx, cy = int(pos[0]), int(pos[1])
                        except (AttributeError, ValueError):
                            pass

                    # Fallback to tile position
                    if (cx is None or cy is None) and hasattr(unit.position, 'tile_x'):
                        try:
                            tile_x = getattr(unit.position, 'tile_x', None)
                            tile_y = getattr(unit.position, 'tile_y', None)
                            if tile_x is not None and tile_y is not None:
                                from pycc2.domain.value_objects.vec2 import Vec2
                                world_pos = Vec2(tile_x * 16, tile_y * 16)
                                pos = camera.world_to_screen(world_pos)
                                cx, cy = int(pos[0]), int(pos[1])
                        except Exception:
                            pass

                if cx is None or cy is None:
                    continue

                # Determine unit type and size
                unit_type = getattr(unit, 'unit_type', 'infantry')
                unit_type_str = str(unit_type).lower()

                # Check if unit is hidden/sneaking
                is_hidden = getattr(unit, 'is_hidden', False) or \
                           getattr(unit, 'is_sneaking', False)

                # Detect vehicle vs infantry by type name or size
                is_vehicle = any(v in unit_type_str for v in 
                               ['tank', 'vehicle', 'halftrack', 'jeep', 'truck'])

                if is_vehicle:
                    # Get vehicle dimensions
                    unit_w = getattr(unit, 'width', 24) or 24
                    unit_h = getattr(unit, 'height', 16) or 16
                    
                    # Render vehicle shadow
                    self._shadow_renderer.render_vehicle_shadow(
                        self._offscreen,
                        cx, cy,
                        unit_w, unit_h,
                        is_hidden=is_hidden
                    )
                else:
                    # Render infantry shadow
                    self._shadow_renderer.render_unit_shadow(
                        self._offscreen,
                        cx, cy,
                        unit_type=unit_type_str,
                        is_hidden=is_hidden
                    )

        except RuntimeError as e:
            logger.warning(f"Failed to render unit shadows: {e}")

    def _debug_render_shadow_bounds(self, game_map: GameMap, camera: Camera) -> None:
        """Draw red rectangles showing where shadows WOULD be rendered (debug visualization).

        This helps verify shadow positions without relying on subtle alpha.
        Call this from render() when debug_mode=True to see shadow placement.
        """
        if self._offscreen is None:
            return

        import pygame as pg

        try:
            # Debug colors for different shadow types
            BUILDING_DEBUG_COLOR = (255, 0, 0)      # Red for buildings
            TREE_DEBUG_COLOR = (0, 255, 0)           # Green for trees
            UNIT_DEBUG_COLOR = (0, 0, 255)           # Blue for units

            # Draw building shadow bounds
            for y in range(game_map.height):
                for x in range(game_map.width):
                    tile = game_map.get_tile(x, y)
                    if tile is None:
                        continue

                    # Same detection logic as _render_building_shadows
                    has_building = (
                        hasattr(tile, 'building') and tile.building is not None
                    ) or (
                        hasattr(tile, 'terrain_type') and
                        str(tile.terrain_type).lower() in ['building', 'house', 'barn', 'church']
                    )

                    if not has_building:
                        try:
                            tt = getattr(tile, 'terrain_type', None)
                            if tt is not None:
                                tt_val = int(tt) if isinstance(tt, (int, float)) else -1
                                if tt_val >= 20:
                                    has_building = True
                        except (ValueError, TypeError):
                            pass

                    if not has_building:
                        tile_name = str(getattr(tile, 'name', '')).lower()
                        if any(w in tile_name for w in ['build', 'house', 'church', 'barn', 'factory']):
                            has_building = True

                    if has_building:
                        world_pos = (x * self.TILE_SIZE, y * self.TILE_SIZE)
                        screen_pos = camera.world_to_screen(world_pos)
                        sx, sy = int(screen_pos[0]), int(screen_pos[1])

                        # Draw red rectangle where building shadow would appear
                        shadow_rect = pg.Rect(sx + 6, sy + self.TILE_SIZE // 2 + 3,
                                             max(24, int(self.TILE_SIZE * 0.9)), 6)
                        pg.draw.rect(self._offscreen, BUILDING_DEBUG_COLOR, shadow_rect, 2)

            # Draw tree shadow bounds
            for y in range(game_map.height):
                for x in range(game_map.width):
                    tile = game_map.get_tile(x, y)
                    if tile is None:
                        continue

                    terrain_str = str(getattr(tile, 'terrain_type', '')).lower()
                    is_tree = any(t in terrain_str for t in ['tree', 'forest', 'woods', 'hedgerow', 'orchard'])

                    if not is_tree:
                        try:
                            tt = getattr(tile, 'terrain_type', None)
                            if tt is not None:
                                tt_val = int(tt) if isinstance(tt, (int, float)) else -1
                                if 3 <= tt_val <= 7:
                                    is_tree = True
                        except (ValueError, TypeError):
                            pass

                    if not is_tree:
                        tile_name = str(getattr(tile, 'name', '')).lower()
                        if any(w in tile_name for w in ['tree', 'forest', 'wood', 'hedge', 'bush', 'orchard']):
                            is_tree = True

                    if is_tree:
                        world_pos = (x * self.TILE_SIZE, y * self.TILE_SIZE)
                        screen_pos = camera.world_to_screen(world_pos)
                        sx, sy = int(screen_pos[0]), int(screen_pos[1])

                        # Draw green rectangle where tree shadow would appear
                        shadow_rect = pg.Rect(sx + 5, sy + 3, 18, 8)
                        pg.draw.rect(self._offscreen, TREE_DEBUG_COLOR, shadow_rect, 2)

            logger.debug("Debug shadow bounds rendered (red=buildings, green=trees)")

        except (ValueError, pygame.error) as e:
            logger.warning(f"Failed to debug render shadow bounds: {e}")

    def _draw_attack_lines(self, camera: Camera) -> None:
        """Draw CC2-style attack lines with color coding.

        Green line = Can attack (in range, clear LOS)
        Red/Orange line = Cannot attack (out of range or blocked)
        Yellow dashed = Tracking unit target
        """
        if self._offscreen is None:
            return

        # Get attack line system from game state or global
        import pygame as pg
        from pycc2.presentation.input.attack_line_system import AttackLineSystem, AttackLineStatus

        # Get attack line system (injected via constructor - P0-2 Fix)
        import pygame as pg
        from pycc2.presentation.input.attack_line_system import AttackLineSystem, AttackLineStatus

        attack_line = self._attack_line_system
        if not attack_line:
            return

        # Draw active attack line (while in ATTACK mode)
        if attack_line.state.active and attack_line.state.source_position:
            source = attack_line.state.source_position
            target_state = attack_line.state.target

            if target_state:
                # Convert world to screen coordinates
                src_screen = camera.world_to_screen(source)
                tgt_screen = camera.world_to_screen(target_state.position)

                # Get color based on status
                status = target_state.status
                color = attack_line.get_line_color(status)

                # Draw line
                start_pos = (int(src_screen[0]), int(src_screen[1]))
                end_pos = (int(tgt_screen[0]), int(tgt_screen[1]))

                if status == AttackLineStatus.CAN_ATTACK:
                    # Solid green line
                    pg.draw.line(self._offscreen, color[:3], start_pos, end_pos, 2)
                    # Draw circle at target
                    pg.draw.circle(self._offscreen, (0, 255, 0), end_pos, 6, 2)
                elif status == AttackLineStatus.OUT_OF_RANGE:
                    # Dashed red line
                    self._draw_dashed_line(start_pos, end_pos, (255, 50, 50), dash_len=8)
                    # X mark at target
                    size = 6
                    pg.draw.line(self._offscreen, (255, 50, 50),
                                (end_pos[0]-size, end_pos[1]-size),
                                (end_pos[0]+size, end_pos[1]+size), 2)
                    pg.draw.line(self._offscreen, (255, 50, 50),
                                (end_pos[0]-size, end_pos[1]+size),
                                (end_pos[0]+size, end_pos[1]-size), 2)
                elif status == AttackLineStatus.BLOCKED:
                    # Orange dashed line
                    self._draw_dashed_line(start_pos, end_pos, (255, 140, 0), dash_len=8)
                    # Block icon at target
                    pg.draw.circle(self._offscreen, (255, 140, 0), end_pos, 8, 2)
                    pg.draw.line(self._offscreen, (255, 140, 0),
                                (end_pos[0]-4, end_pos[1]),
                                (end_pos[0]+4, end_pos[1]), 2)

                # Draw range circle around source
                if hasattr(attack_line, 'COLOR_CAN_ATTACK'):
                    pass  # Already used above

        # Draw confirmed attacks (tracking lines)
        for unit_id, confirmed_target in attack_line._confirmed_attacks.items():
            if not confirmed_target.unit_id:
                continue  # Only draw tracking lines for unit targets

            # Source: attacker position (from _active_source or confirmed_target)
            source_pos = getattr(attack_line, '_active_source', None)
            if source_pos is not None:
                source_screen = camera.world_to_screen(source_pos)
            else:
                # Fallback: use confirmed_target position (may be slightly off)
                source_screen = camera.world_to_screen(confirmed_target.position)
            # Target position is updated by update_tracking()
            target_screen = camera.world_to_screen(confirmed_target.position)

            # Red solid line for confirmed attacks (CC2 uses solid red)
            pg.draw.line(
                self._offscreen,
                (255, 50, 50),
                (int(source_screen[0]), int(source_screen[1])),
                (int(target_screen[0]), int(target_screen[1])),
                2,
            )

    def render_los_overlay(self, surface: pygame.Surface, unit, game_map, camera) -> None:
        """Render line-of-sight visualization for the selected unit.

        Called when Ctrl key is held down. Shows visible/hidden areas.
        """
        if unit is None or game_map is None:
            return

        from pycc2.domain.systems.los_system import Lossystem
        from pycc2.domain.value_objects.tile_coord import TileCoord

        los = Lossystem(game_map)
        ux = unit.position.tile_coord.x
        uy = unit.position.tile_coord.y
        tile_size = self.TILE_SIZE

        # Create a semi-transparent overlay
        overlay = pygame.Surface(
            (game_map.width * tile_size, game_map.height * tile_size),
            pygame.SRCALPHA,
        )

        # Check LOS from unit to each tile in range
        vision_range = getattr(unit, 'vision', None)
        max_range = vision_range.range if vision_range else 10

        for ty in range(max(0, uy - max_range), min(game_map.height, uy + max_range + 1)):
            for tx in range(max(0, ux - max_range), min(game_map.width, ux + max_range + 1)):
                if tx == ux and ty == uy:
                    continue

                from_coord = TileCoord(ux, uy)
                to_coord = TileCoord(tx, ty)
                can_see, _ = los.check_los(from_coord, to_coord, max_range)
                screen_x = tx * tile_size
                screen_y = ty * tile_size

                if can_see:
                    # Visible - light green tint
                    pygame.draw.rect(overlay, (0, 255, 0, 25), (screen_x, screen_y, tile_size, tile_size))
                else:
                    # Blocked - dark red tint
                    pygame.draw.rect(overlay, (255, 0, 0, 40), (screen_x, screen_y, tile_size, tile_size))

        # Blit overlay offset by camera
        cam_x = int(camera.offset_x) if hasattr(camera, 'offset_x') else 0
        cam_y = int(camera.offset_y) if hasattr(camera, 'offset_y') else 0
        surface.blit(overlay, (-cam_x, -cam_y))

    # ====== Combat effect proxy methods (forward to SpriteRenderer) ======

    def spawn_hit_flash(self, unit_id: str) -> None:
        if self._sprite_renderer:
            self._sprite_renderer.spawn_hit_flash(unit_id)

    def spawn_damage_number(self, position, damage: int, is_kill: bool = False) -> None:
        if self._sprite_renderer:
            self._sprite_renderer.spawn_damage_number(position, damage, is_kill)

    def spawn_muzzle_flash(self, position, direction: float) -> None:
        if self._sprite_renderer:
            self._sprite_renderer.spawn_muzzle_flash(position, direction)

    def spawn_death_effect(self, unit_id: str, position) -> None:
        if self._sprite_renderer:
            self._sprite_renderer.spawn_death_effect(unit_id, position)

    def spawn_explosion(self, position, size: str = "medium") -> None:
        if self._sprite_renderer:
            self._sprite_renderer.spawn_explosion(position, size)

    def spawn_smoke_screen(self, position, radius: float = 64.0) -> None:
        if self._sprite_renderer:
            self._sprite_renderer.spawn_smoke_screen(position, radius)

    def _draw_queued_commands(self, units: list, camera: Camera) -> None:
        """Draw dashed lines for queued commands (Shift+right-click).

        Cyan dashed lines show queued move waypoints.
        Orange dashed lines show queued attack targets.
        """
        if self._offscreen is None:
            return

        from pycc2.domain.value_objects.vec2 import Vec2

        for unit in units:
            if not hasattr(unit, 'has_queued_commands') or not unit.has_queued_commands:
                continue

            # Get unit screen position
            upos = unit.position.pixel_position if hasattr(unit.position, 'pixel_position') else None
            if upos is None:
                continue

            prev_screen = camera.world_to_screen(upos)

            for cmd in unit._command_queue:
                tx = cmd.get('target_x', 0)
                ty = cmd.get('target_y', 0)
                target_world = Vec2(tx * 32, ty * 32)  # tile to pixel
                target_screen = camera.world_to_screen(target_world)

                start_pos = (int(prev_screen[0]), int(prev_screen[1]))
                end_pos = (int(target_screen[0]), int(target_screen[1]))

                cmd_type = cmd.get('type', 'move')
                if cmd_type == 'attack':
                    # Orange dashed for queued attacks
                    self._draw_dashed_line(start_pos, end_pos, (255, 165, 0), dash_len=6)
                else:
                    # Cyan dashed for queued moves
                    self._draw_dashed_line(start_pos, end_pos, (0, 220, 220), dash_len=6)

                # Draw small waypoint circle
                import pygame as pg
                pg.draw.circle(self._offscreen, (0, 220, 220), end_pos, 4, 1)

                prev_screen = target_screen

    def _draw_dashed_line(
        self,
        start: tuple[int, int],
        end: tuple[int, int],
        color: tuple[int, int, int],
        dash_len: int = 8,
    ) -> None:
        """Draw a dashed line."""
        import math as _math
        x1, y1 = start
        x2, y2 = end
        dx = x2 - x1
        dy = y2 - y1
        distance = _math.sqrt(dx*dx + dy*dy)

        if distance == 0:
            return

        dashes = int(distance / dash_len)
        for i in range(0, dashes, 2):
            start_i = i * dash_len
            end_i = min((i + 1) * dash_len, int(distance))
            sx = x1 + dx * start_i / distance
            sy = y1 + dy * start_i / distance
            ex = x1 + dx * end_i / distance
            ey = y1 + dy * end_i / distance
            import pygame as pg
            pg.draw.line(self._offscreen, color, (int(sx), int(sy)), (int(ex), int(ey)), 2)

    # ============================================================
    # Particle System Convenience Methods (Top-Down VFX)
    # ============================================================
    
    def update_particles(self, dt_ms: int) -> None:
        """Update all particle effects - call from game loop.
        
        Args:
            dt_ms: Delta time in milliseconds since last frame
        """
        self._particle_system.update(dt_ms)
        
    def spawn_explosion(self, position, max_radius=40, duration_ms=500, 
                        color=(255, 200, 50)) -> None:
        """Spawn explosion ring effect at position.
        
        CC2 Authentic: Yellow/orange circular expanding ring (not 3D fireball)
        Automatically triggers dynamic light effect.
        
        Args:
            position: (x, y) world coordinates or Vec2
            max_radius: Maximum ring radius in pixels (default 40)
            duration_ms: Animation duration (default 500ms)
            color: Base color tuple (default yellow-orange)
        """
        x = position[0] if hasattr(position, '__getitem__') else position.x
        y = position[1] if hasattr(position, '__getitem__') else position.y
        
        self._particle_system.spawn_explosion_ring(x, y, max_radius, duration_ms, color)
        
        self.spawn_dynamic_light(position, radius=60, intensity=1.5, 
                                color=(255, 200, 100), duration_ms=duration_ms)
                                
    def spawn_muzzle_flash(self, position, direction) -> None:
        """Spawn muzzle flash effect at firing unit position.
        
        CC2 Authentic: White dot flash + short line along fire direction
        
        Args:
            position: (x, y) world coordinates or Vec2
            direction: Firing angle in radians
        """
        x = position[0] if hasattr(position, '__getitem__') else position.x
        y = position[1] if hasattr(position, '__getitem__') else position.y
        
        self._particle_system.spawn_muzzle_flash(x, y, direction)
        
    def spawn_hit_marker(self, position, damage_type='normal', duration_ms=300) -> None:
        """Spawn hit marker effect at target position.
        
        Args:
            position: (x, y) world coordinates or Vec2
            damage_type: 'normal'|'critical'|'armor_penetrate'|'ricochet'
            duration_ms: Marker display duration (default 300ms)
        """
        x = position[0] if hasattr(position, '__getitem__') else position.x
        y = position[1] if hasattr(position, '__getitem__') else position.y
        
        self._particle_system.spawn_hit_marker(x, y, damage_type, duration_ms)
        
    def spawn_smoke_cloud(self, position, max_radius=25, duration_ms=2000,
                          color=(180, 180, 170)) -> None:
        """Spawn smoke cloud effect at position.
        
        CC2 Authentic: Circular gray-white cloud with drift and turbulence
        
        Args:
            position: (x, y) world coordinates or Vec2
            max_radius: Maximum cloud radius (default 25)
            duration_ms: Cloud lifetime (default 2000ms)
            color: Cloud color (default gray-white)
        """
        x = position[0] if hasattr(position, '__getitem__') else position.x
        y = position[1] if hasattr(position, '__getitem__') else position.y
        
        self._particle_system.spawn_smoke_cloud(x, y, max_radius, duration_ms, color)
        
    def spawn_dirt_splash(self, position, count=12, spread_radius=20) -> None:
        """Spawn dirt splash particles at impact point.
        
        Top-down feature: Particles radiate outward in circular pattern (no gravity)
        
        Args:
            position: (x, y) world coordinates or Vec2
            count: Number of dirt particles (default 12)
            spread_radius: Spread distance (default 20)
        """
        x = position[0] if hasattr(position, '__getitem__') else position.x
        y = position[1] if hasattr(position, '__getitem__') else position.y
        
        self._particle_system.spawn_dirt_splash(x, y, count, spread_radius)
        
    def spawn_blood_pool(self, position, size=8) -> None:
        """Spawn persistent blood pool stain on ground.
        
        Args:
            position: (x, y) world coordinates or Vec2
            size: Pool size (default 8)
        """
        x = position[0] if hasattr(position, '__getitem__') else position.x
        y = position[1] if hasattr(position, '__getitem__') else position.y
        
        self._particle_system.spawn_blood_pool(x, y, size)
        
    @property
    def particle_count(self) -> int:
        """Get current active particle count for performance monitoring."""
        return self._particle_system.active_count

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
    
    def _apply_post_processing(self) -> None:
        """Apply minimal post-processing effects for performance.

        DISABLED heavy effects (color grading, film grain) that cause flickering.
        Only keep subtle vignette for cinematic feel, applied very infrequently.
        """
        if self._screen is None:
            return

        # ONLY apply vignette every 10 frames to prevent flickering
        if self._frame_count % 10 != 0:
            return

        w, h = self._screen.get_size()

        # Simple vignette only - no color grading or film grain
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        cx, cy = w // 2, h // 2
        max_dist = math.sqrt(cx**2 + cy**2)

        # Very sparse sampling for performance
        for y in range(0, h, 8):
            for x in range(0, w, 8):
                dist = math.sqrt((x - cx)**2 + (y - cy)**2) / max_dist
                if dist > 0.7:
                    alpha = int((dist - 0.7) * 20)  # Very subtle
                    if alpha > 0:
                        overlay.set_at((x, y), (15, 12, 8, alpha))

        self._offscreen.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        # DISABLED: Color grading (causes flickering on some systems)
        # DISABLED: Film grain (causes visual noise)
        # DISABLED: Contrast enhancement (causes brightness oscillation)
    
    def _detect_building_clusters(self, game_map: GameMap) -> list[list[tuple[int, int]]]:
        """Find groups of adjacent building tiles using flood-fill/BFS.
        
        Returns list of clusters, each cluster is list of (x,y) coords.
        Building tiles are terrain IDs 4 (BUILDING_ENTERABLE) and 5 (BUILDING_SOLID).
        
        This method caches results to avoid recomputation during rendering.
        
        Args:
            game_map: Game map instance
            
        Returns:
            list: List of building clusters, each containing (x, y) coordinate tuples
        """
        # Use cached result if available
        if self._building_clusters is not None:
            return self._building_clusters
        
        # Compute and cache building clusters
        self._building_clusters = detect_building_clusters(game_map)
        return self._building_clusters
    
    def invalidate_building_cluster_cache(self) -> None:
        """Invalidate the building cluster cache (call when map changes)."""
        self._building_clusters = None

    def shutdown(self) -> None:
        """Clean up renderer resources."""
        self._texture_cache.clear()
        self._scaled_texture_cache.clear()
        self._height_lit_cache.clear()
        self._sprite_cache.clear()
        self._autotile_cache.clear()
        self._terrain_tile_cache.clear()
        self._building_clusters = None  # Clear cluster cache

    def resize(self, width: int, height: int) -> None:
        """Handle window resize."""
        pass
