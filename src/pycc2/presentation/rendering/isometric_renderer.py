"""Isometric renderer for PyCC2 - Phase 3 (optimized).

Integrates isometric tile generation, depth sorting, and building rendering
with the existing Camera's ProjectionMode.ISOMETRIC.

Phase 3 optimizations:
- Persistent tile cache with zoom-aware invalidation
- Pre-generated scaled tile cache (no per-frame scaling)
- Visible tile culling (only render on-screen tiles)
- Dirty rectangle tracking for selective redraws
- Performance metrics (tile count, draw time, cache hit rate)

Rendering pipeline:
1. Check dirty flag — skip redraw if nothing changed
2. Calculate visible tile range from camera
3. Blit pre-cached scaled tiles (no per-frame generation/scaling)
4. Depth-sort all renderables (terrain + buildings + units + effects)
5. Draw back-to-front using painter's algorithm
6. Draw UI overlays on top
"""

# ⚠️ EXPERIMENTAL FEATURE
# CC2 uses Orthographic Top-Down projection, NOT Isometric.
# This module provides an optional isometric mode for future/modding use.
# It is NOT the primary rendering path and should not be used for CC2-fidelity work.

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import pygame

from pycc2.presentation.rendering.isometric_building_renderer import (
    DamageState,
    is_building_terrain,
    render_building,
    terrain_to_building_type,
)
from pycc2.presentation.rendering.isometric_depth_sorter import (
    IsometricRenderable,
    RenderLayer,
    sort_for_isometric,
    tile_to_renderable,
    unit_to_renderable,
)
from pycc2.presentation.rendering.isometric_tile_generator import (
    generate_crater_tile,
    generate_dirt_tile,
    generate_grass_tile,
    generate_hedgerow_tile,
    generate_road_tile,
    generate_water_tile,
)
from pycc2.presentation.rendering.isometric_transform import (
    TILE_H,
    TILE_W,
)

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.presentation.rendering.camera import Camera

logger = logging.getLogger(__name__)

# Terrain ID to tile generator mapping
_TERRAIN_GENERATORS: dict[int, Callable[[], pygame.Surface]] = {
    0: generate_grass_tile,  # OPEN
    1: generate_road_tile,  # ROAD
    2: generate_grass_tile,  # GRASS
    3: generate_grass_tile,  # WOODS (uses grass base with darker tint)
    6: generate_water_tile,  # WATER
    7: generate_hedgerow_tile,  # HEDGE
    9: generate_dirt_tile,  # ROUGH
    10: generate_water_tile,  # SHALLOW
    12: generate_crater_tile,  # CRATER
}

# All unique terrain IDs that exist in the game
_ALL_TERRAIN_IDS = set(_TERRAIN_GENERATORS.keys())

# Zoom quantization: round zoom to nearest 0.05 to limit cache entries
_ZOOM_QUANT = 0.05


def _quantize_zoom(zoom: float) -> float:
    """Round zoom to nearest quantization step to limit cache size."""
    return round(zoom / _ZOOM_QUANT) * _ZOOM_QUANT


class IsometricRenderer:
    """Main isometric rendering module with Phase 3 optimizations.

    Renders terrain, buildings, units, and effects in isometric projection.
    Integrates with Camera's ProjectionMode.ISOMETRIC.

    Performance features:
    - Pre-generated base tiles at initialize() time
    - Zoom-aware scaled tile cache (invalidated on zoom change)
    - Visible tile culling
    - Dirty rectangle tracking
    - Performance stats collection
    """

    def __init__(self) -> None:
        # Base (unscaled) tile surfaces — generated once at initialize()
        self._tile_cache: dict[int, pygame.Surface] = {}
        self._building_cache: dict[tuple[int, int, int], pygame.Surface] = {}

        # Scaled tile cache: key = (terrain_id, quantized_zoom) -> scaled Surface
        self._scaled_tile_cache: dict[tuple[int, float], pygame.Surface] = {}
        # Scaled building cache: key = (terrain_id, height, damage, quantized_zoom)
        self._scaled_building_cache: dict[tuple[int, int, int, float], pygame.Surface] = {}

        self._screen: pygame.Surface | None = None
        self._offscreen: pygame.Surface | None = None

        # Zoom tracking for cache invalidation
        self._last_zoom: float = -1.0

        # Dirty rectangle system
        self._dirty: bool = True  # Start dirty so first frame renders

        # Performance metrics
        self._tile_count: int = 0
        self._draw_time_ms: float = 0.0
        self._cache_hits: int = 0
        self._cache_misses: int = 0
        self._frame_count: int = 0

    def initialize(self, screen: pygame.Surface) -> None:
        """Initialize renderer with display surface and pre-generate all tiles."""
        self._screen = screen
        try:
            self._offscreen = pygame.Surface(screen.get_size()).convert()
        except pygame.error:
            self._offscreen = pygame.Surface(screen.get_size(), pygame.SRCALPHA)

        # Pre-generate all base terrain tiles
        self._pregenerate_tiles()

        # Pre-generate common building surfaces
        self._pregenerate_buildings()

        logger.info(
            "IsometricRenderer initialized: %d terrain tiles, %d buildings pre-cached",
            len(self._tile_cache),
            len(self._building_cache),
        )

    def _pregenerate_tiles(self) -> None:
        """Pre-generate all terrain tile types at base resolution."""
        for terrain_id, generator in _TERRAIN_GENERATORS.items():
            if terrain_id not in self._tile_cache:
                self._tile_cache[terrain_id] = generator()

    def _pregenerate_buildings(self) -> None:
        """Pre-generate common building surfaces at base resolution."""
        # Pre-generate buildings for all building terrain IDs with common configs
        for terrain_id in (4, 5, 8):  # BUILDING_ENTERABLE, BUILDING_SOLID, WALL
            for height_levels in (1, 2, 3):  # Common heights
                for damage_state in (0, 1, 2):  # INTACT, DAMAGED, DESTROYED
                    cache_key = (terrain_id, height_levels, damage_state)
                    if cache_key not in self._building_cache:
                        building_type = terrain_to_building_type(terrain_id)
                        damage_map = {
                            0: DamageState.INTACT,
                            1: DamageState.DAMAGED,
                            2: DamageState.DESTROYED,
                        }
                        damage = damage_map.get(damage_state, DamageState.INTACT)
                        self._building_cache[cache_key] = render_building(
                            building_type=building_type,
                            height_levels=height_levels,
                            damage=damage,
                        )

    def _invalidate_scaled_cache(self) -> None:
        """Clear all scaled caches (called when zoom changes)."""
        self._scaled_tile_cache.clear()
        self._scaled_building_cache.clear()

    def mark_dirty(self) -> None:
        """Mark the entire screen as needing redraw.

        Call this when: camera moves, unit moves, combat effect occurs,
        or any visual change happens.
        """
        self._dirty = True

    @property
    def is_dirty(self) -> bool:
        """Whether the screen needs redrawing."""
        return self._dirty

    def get_performance_stats(self) -> dict[str, Any]:
        """Return current performance statistics.

        Returns:
            Dict with keys:
            - tile_count: Number of tiles rendered last frame
            - draw_time_ms: Time spent in render() last frame (ms)
            - cache_hit_rate: Ratio of cache hits to total lookups (0.0-1.0)
            - frame_count: Total frames rendered
            - base_cache_size: Number of base (unscaled) cached tiles
            - scaled_cache_size: Number of scaled cached surfaces

        """
        total = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total if total > 0 else 0.0
        return {
            "tile_count": self._tile_count,
            "draw_time_ms": self._draw_time_ms,
            "cache_hit_rate": hit_rate,
            "frame_count": self._frame_count,
            "base_cache_size": len(self._tile_cache) + len(self._building_cache),
            "scaled_cache_size": len(self._scaled_tile_cache) + len(self._scaled_building_cache),
        }

    def render(
        self,
        game_map: GameMap,
        units: list[Unit],
        camera: Camera,
        selected_unit_ids: set[str] | None = None,
        debug_mode: bool = False,
    ) -> None:
        """Main render method for isometric view.

        Args:
            game_map: The game map to render.
            units: List of units to render.
            camera: Camera with ISOMETRIC projection.
            selected_unit_ids: Set of selected unit IDs for highlighting.
            debug_mode: If True, draw debug overlays.

        """
        if self._screen is None:
            return

        t_start = time.perf_counter()

        screen_w, screen_h = self._screen.get_size()
        if self._offscreen is None or self._offscreen.get_size() != (screen_w, screen_h):
            self._offscreen = pygame.Surface((screen_w, screen_h)).convert()
            self._dirty = True

        # Check if zoom changed — invalidate scaled cache if so
        quantized_zoom = _quantize_zoom(camera.zoom)
        if quantized_zoom != self._last_zoom:
            self._invalidate_scaled_cache()
            self._last_zoom = quantized_zoom
            self._dirty = True

        # If not dirty, skip full redraw (just re-blit the offscreen buffer)
        if not self._dirty:
            self._screen.blit(self._offscreen, (0, 0))
            return

        self._offscreen.fill((34, 40, 48))

        # Reset per-frame counters
        self._cache_hits = 0
        self._cache_misses = 0
        self._tile_count = 0

        # Calculate visible tile range
        start_x, start_y, end_x, end_y = self._visible_tile_range(
            game_map, camera, screen_w, screen_h
        )

        # Collect all renderables
        renderables: list[IsometricRenderable] = []

        # Add terrain tiles
        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                terrain_id = self._get_terrain_at(game_map, tx, ty)
                renderables.append(tile_to_renderable(tx, ty, terrain_id))
                self._tile_count += 1

        # Add units
        for unit in units:
            try:
                renderables.append(unit_to_renderable(unit))
            except (AttributeError, ValueError, TypeError) as e:
                logging.debug("Unit to renderable conversion failed: %s", e)
                continue

        # Sort back-to-front
        sorted_renderables = sort_for_isometric(renderables)

        # Draw sorted renderables using pre-scaled cached surfaces
        for renderable in sorted_renderables:
            if renderable.layer == RenderLayer.TERRAIN:
                terrain_id = renderable.data if renderable.data is not None else 0
                self._draw_terrain_tile(
                    renderable.world_x,
                    renderable.world_y,
                    terrain_id,
                    camera,
                    game_map,
                    quantized_zoom,
                )
            elif renderable.layer == RenderLayer.UNIT:
                self._draw_unit_isometric(renderable.data, camera, selected_unit_ids)

        # Debug grid overlay
        if debug_mode:
            self._draw_debug_grid(game_map, camera, start_x, end_x, start_y, end_y)

        # Blit to screen
        self._screen.blit(self._offscreen, (0, 0))

        # Mark clean after rendering
        self._dirty = False
        self._frame_count += 1

        # Record draw time
        t_end = time.perf_counter()
        self._draw_time_ms = (t_end - t_start) * 1000.0

        # Warn if below 30 FPS
        if self._draw_time_ms > 33.0:
            logger.warning(
                "Isometric render took %.1fms (>33ms, below 30 FPS). "
                "tile_count=%d, cache_hit_rate=%.1f%%",
                self._draw_time_ms,
                self._tile_count,
                self._cache_hits / max(1, self._cache_hits + self._cache_misses) * 100,
            )

    def _visible_tile_range(
        self,
        game_map: GameMap,
        camera: Camera,
        screen_w: int,
        screen_h: int,
    ) -> tuple[int, int, int, int]:
        """Calculate the range of visible tiles in isometric view.

        Returns (start_x, start_y, end_x, end_y) tile coordinates.
        """
        # Convert screen corners to world coords to find visible range
        # Add generous padding since isometric projection is diamond-shaped
        margin = max(TILE_W, TILE_H) * 2 / camera.zoom

        top_left = camera.screen_to_world((0.0, 0.0))
        top_right = camera.screen_to_world((float(screen_w), 0.0))
        bottom_left = camera.screen_to_world((0.0, float(screen_h)))
        bottom_right = camera.screen_to_world((float(screen_w), float(screen_h)))

        # Find min/max world coords with margin
        all_wx = [top_left.x, top_right.x, bottom_left.x, bottom_right.x]
        all_wy = [top_left.y, top_right.y, bottom_left.y, bottom_right.y]

        min_wx = min(all_wx) - margin
        max_wx = max(all_wx) + margin
        min_wy = min(all_wy) - margin
        max_wy = max(all_wy) + margin

        # Convert world pixel coords to tile coords
        # Camera returns world coords in pixel space; divide by TILE_SIZE (32)
        tile_size = 32
        start_x = max(0, int(min_wx / tile_size) - 1)
        start_y = max(0, int(min_wy / tile_size) - 1)
        end_x = min(game_map.width, int(max_wx / tile_size) + 2)
        end_y = min(game_map.height, int(max_wy / tile_size) + 2)

        return (start_x, start_y, end_x, end_y)

    def _get_terrain_at(self, game_map: GameMap, x: int, y: int) -> int:
        """Get terrain type at tile coordinate."""
        if x < 0 or y < 0 or x >= game_map.width or y >= game_map.height:
            return 0
        try:
            return int(game_map.tile_grid[y, x])
        except (IndexError, TypeError):
            return 0

    def _get_terrain_tile(self, terrain_id: int) -> pygame.Surface:
        """Get a base (unscaled) terrain tile from cache.

        All tiles are pre-generated at initialize() time, so this should
        always hit the cache.
        """
        if terrain_id not in self._tile_cache:
            # Fallback: generate on-demand if somehow missing
            generator = _TERRAIN_GENERATORS.get(terrain_id, generate_grass_tile)
            self._tile_cache[terrain_id] = generator()
            self._cache_misses += 1
        else:
            self._cache_hits += 1
        return self._tile_cache[terrain_id]

    def _get_scaled_terrain_tile(self, terrain_id: int, quantized_zoom: float) -> pygame.Surface:
        """Get a pre-scaled terrain tile from cache, or create and cache it."""
        cache_key = (terrain_id, quantized_zoom)
        if cache_key in self._scaled_tile_cache:
            self._cache_hits += 1
            return self._scaled_tile_cache[cache_key]

        self._cache_misses += 1
        base_tile = self._get_terrain_tile(terrain_id)
        scaled_w = int(base_tile.get_width() * quantized_zoom)
        scaled_h = int(base_tile.get_height() * quantized_zoom)
        if scaled_w > 0 and scaled_h > 0:
            scaled = pygame.transform.scale(base_tile, (scaled_w, scaled_h))
        else:
            scaled = base_tile
        self._scaled_tile_cache[cache_key] = scaled
        return scaled

    def _get_building_surface(
        self, terrain_id: int, height_levels: int, damage_state: int
    ) -> pygame.Surface:
        """Get or generate a cached building surface (base resolution)."""
        cache_key = (terrain_id, height_levels, damage_state)
        if cache_key in self._building_cache:
            self._cache_hits += 1
            return self._building_cache[cache_key]

        self._cache_misses += 1
        building_type = terrain_to_building_type(terrain_id)
        damage_map = {0: DamageState.INTACT, 1: DamageState.DAMAGED, 2: DamageState.DESTROYED}
        damage = damage_map.get(damage_state, DamageState.INTACT)
        self._building_cache[cache_key] = render_building(
            building_type=building_type,
            height_levels=height_levels,
            damage=damage,
        )
        return self._building_cache[cache_key]

    def _get_scaled_building_surface(
        self,
        terrain_id: int,
        height_levels: int,
        damage_state: int,
        quantized_zoom: float,
    ) -> pygame.Surface:
        """Get a pre-scaled building surface from cache, or create and cache it."""
        cache_key = (terrain_id, height_levels, damage_state, quantized_zoom)
        if cache_key in self._scaled_building_cache:
            self._cache_hits += 1
            return self._scaled_building_cache[cache_key]

        self._cache_misses += 1
        base_surf = self._get_building_surface(terrain_id, height_levels, damage_state)
        scaled_w = int(base_surf.get_width() * quantized_zoom)
        scaled_h = int(base_surf.get_height() * quantized_zoom)
        if scaled_w > 0 and scaled_h > 0:
            scaled = pygame.transform.scale(base_surf, (scaled_w, scaled_h))
        else:
            scaled = base_surf
        self._scaled_building_cache[cache_key] = scaled
        return scaled

    def _draw_terrain_tile(
        self,
        tile_x: float,
        tile_y: float,
        terrain_id: int,
        camera: Camera,
        game_map: GameMap,
        quantized_zoom: float,
    ) -> None:
        """Draw a single isometric terrain tile using pre-scaled cache."""
        if self._offscreen is None:
            return

        from pycc2.domain.value_objects.vec2 import Vec2

        # World position in pixels
        world_x = tile_x * 32
        world_y = tile_y * 32

        # Get screen position via camera (handles isometric transform)
        screen_pos = camera.world_to_screen(Vec2(world_x, world_y))
        sx = int(screen_pos[0])
        sy = int(screen_pos[1])

        # Screen culling: skip tiles completely off-screen
        screen_w, screen_h = self._offscreen.get_size()
        max_tile_dim = int(max(TILE_W, TILE_H) * quantized_zoom) + 32  # extra margin for buildings
        if sx < -max_tile_dim or sx > screen_w + max_tile_dim:
            return
        if sy < -max_tile_dim or sy > screen_h + max_tile_dim:
            return

        # Check if building terrain
        if is_building_terrain(terrain_id):
            # Get height from enhanced tile if available
            height_levels = 2  # default
            damage_state = 0  # INTACT
            try:
                if hasattr(game_map, "get_enhanced_tile"):
                    etile = game_map.get_enhanced_tile(int(tile_x), int(tile_y))
                    if etile is not None:
                        if hasattr(etile, "height"):
                            height_levels = max(1, etile.height)
                        if hasattr(etile, "damage_state"):
                            damage_state = etile.damage_state
            except (AttributeError, ValueError, TypeError) as e:
                logging.debug("Building tile info lookup failed: %s", e)

            scaled = self._get_scaled_building_surface(
                terrain_id, height_levels, damage_state, quantized_zoom
            )
            scaled_w = scaled.get_width()
            scaled_h = scaled.get_height()
            # Offset: building top face center aligns with tile center
            offset_x = scaled_w // 2
            offset_y = int(TILE_H / 2 * quantized_zoom)  # align top face center
            self._offscreen.blit(scaled, (sx - offset_x, sy - offset_y))
        else:
            # Regular terrain tile — use pre-scaled cache
            scaled = self._get_scaled_terrain_tile(terrain_id, quantized_zoom)
            scaled_w = scaled.get_width()
            scaled_h = scaled.get_height()
            # Center the diamond on the screen position
            offset_x = scaled_w // 2
            offset_y = scaled_h // 2
            self._offscreen.blit(scaled, (sx - offset_x, sy - offset_y))

    def _draw_unit_isometric(
        self,
        unit: Any,
        camera: Camera,
        selected_unit_ids: set[str] | None,
    ) -> None:
        """Draw a unit at its isometric screen position."""
        if self._offscreen is None or unit is None:
            return

        try:
            if not getattr(unit, "is_alive", True):
                return

            from pycc2.domain.value_objects.vec2 import Vec2

            # Get unit world position
            pos = getattr(unit, "position", None)
            if pos is None:
                return

            pixel_pos = getattr(pos, "pixel_position", None)
            if pixel_pos is not None:
                world_pos = pixel_pos
            else:
                tile_x = getattr(pos, "tile_x", 0) or 0
                tile_y = getattr(pos, "tile_y", 0) or 0
                world_pos = Vec2(tile_x * 32, tile_y * 32)

            # Convert to isometric screen position
            screen_pos = camera.world_to_screen(world_pos)
            sx, sy = int(screen_pos[0]), int(screen_pos[1])

            # Determine unit type for visual
            unit_type_str = ""
            if hasattr(unit, "unit_type"):
                ut = unit.unit_type
                unit_type_str = ut.name.upper() if hasattr(ut, "name") else str(ut).upper()

            faction = ""
            if hasattr(unit, "faction"):
                f = unit.faction
                faction = f.name.lower() if hasattr(f, "name") else str(f).lower()

            # Draw unit marker
            radius = max(6, int(10 * camera.zoom))

            if "TANK" in unit_type_str or "VEHICLE" in unit_type_str:
                color = (255, 200, 0)
                # Hexagon for tanks
                import math

                points = []
                for i in range(6):
                    angle = math.pi / 3 * i
                    px = sx + int(radius * math.cos(angle))
                    py = sy + int(radius * math.sin(angle))
                    points.append((px, py))
                pygame.draw.polygon(self._offscreen, color, points)
                pygame.draw.polygon(self._offscreen, (255, 255, 255), points, 2)
            else:
                # Circle for infantry
                color = (74, 144, 217) if faction == "allies" else (217, 74, 74)
                pygame.draw.circle(self._offscreen, color, (sx, sy), radius)
                pygame.draw.circle(self._offscreen, (255, 255, 255), (sx, sy), radius, 2)

            # Selection ring
            is_selected = selected_unit_ids and unit.id in selected_unit_ids
            if is_selected:
                select_radius = radius + 4
                pygame.draw.circle(self._offscreen, (255, 255, 0), (sx, sy), select_radius, 2)

        except (pygame.error, ValueError, TypeError) as e:
            logging.debug("Isometric unit rendering failed: %s", e)
            return

    def _draw_debug_grid(
        self,
        game_map: GameMap,
        camera: Camera,
        start_x: int,
        end_x: int,
        start_y: int,
        end_y: int,
    ) -> None:
        """Draw isometric grid overlay for debugging."""
        if self._offscreen is None:
            return

        from pycc2.domain.value_objects.vec2 import Vec2

        grid_color = (100, 100, 100)

        for ty in range(start_y, end_y + 1):
            # Horizontal lines in world space become diagonal in iso
            start_world = Vec2(start_x * 32, ty * 32)
            end_world = Vec2(end_x * 32, ty * 32)
            sp1 = camera.world_to_screen(start_world)
            sp2 = camera.world_to_screen(end_world)
            pygame.draw.line(
                self._offscreen,
                grid_color,
                (int(sp1[0]), int(sp1[1])),
                (int(sp2[0]), int(sp2[1])),
                1,
            )

        for tx in range(start_x, end_x + 1):
            start_world = Vec2(tx * 32, start_y * 32)
            end_world = Vec2(tx * 32, end_y * 32)
            sp1 = camera.world_to_screen(start_world)
            sp2 = camera.world_to_screen(end_world)
            pygame.draw.line(
                self._offscreen,
                grid_color,
                (int(sp1[0]), int(sp1[1])),
                (int(sp2[0]), int(sp2[1])),
                1,
            )

    def shutdown(self) -> None:
        """Clean up renderer resources."""
        self._tile_cache.clear()
        self._building_cache.clear()
        self._scaled_tile_cache.clear()
        self._scaled_building_cache.clear()
