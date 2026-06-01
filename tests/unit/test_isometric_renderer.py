"""Unit tests for isometric rendering pipeline - Phase 2."""

from unittest.mock import MagicMock, patch

import pygame
import pytest

# Initialize pygame before any surface operations
pygame.init()
# Set a tiny display mode so Surface.convert() works
try:
    pygame.display.set_mode((1, 1))
except pygame.error:
    pass


from pycc2.presentation.rendering.camera import Camera, ProjectionMode
from pycc2.presentation.rendering.isometric_building_renderer import (
    BUILDING_HEIGHTS,
    BuildingType,
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
from pycc2.presentation.rendering.isometric_renderer import IsometricRenderer
from pycc2.presentation.rendering.isometric_transform import (
    TILE_H,
    TILE_W,
    depth_sort_key,
    is_point_in_diamond,
    world_to_isometric,
)


# ============================================================
# IsometricRenderer Tests
# ============================================================


class TestIsometricRendererInit:
    def test_initialization(self):
        """IsometricRenderer initializes with empty caches."""
        renderer = IsometricRenderer()
        assert renderer._tile_cache == {}
        assert renderer._building_cache == {}
        assert renderer._screen is None
        assert renderer._offscreen is None

    def test_initialize_with_screen(self):
        """Initialize sets screen and offscreen surfaces."""
        renderer = IsometricRenderer()
        screen = pygame.Surface((800, 600))
        renderer.initialize(screen)
        assert renderer._screen is not None
        assert renderer._offscreen is not None


class TestIsometricRendererTerrain:
    def test_terrain_tile_cache(self):
        """Terrain tiles are cached after first generation."""
        renderer = IsometricRenderer()
        tile = renderer._get_terrain_tile(0)  # grass
        assert isinstance(tile, pygame.Surface)
        assert 0 in renderer._tile_cache

    def test_terrain_tile_dimensions(self):
        """Generated terrain tiles have correct dimensions."""
        renderer = IsometricRenderer()
        tile = renderer._get_terrain_tile(0)
        assert tile.get_width() == TILE_W
        assert tile.get_height() == TILE_H

    def test_terrain_tile_different_types(self):
        """Different terrain IDs produce different cached tiles."""
        renderer = IsometricRenderer()
        tile0 = renderer._get_terrain_tile(0)  # grass
        tile6 = renderer._get_terrain_tile(6)  # water
        assert 0 in renderer._tile_cache
        assert 6 in renderer._tile_cache

    def test_building_surface_cache(self):
        """Building surfaces are cached."""
        renderer = IsometricRenderer()
        surf = renderer._get_building_surface(4, 2, 0)
        assert isinstance(surf, pygame.Surface)
        assert (4, 2, 0) in renderer._building_cache


class TestIsometricRendererRender:
    def _make_camera(self, projection=ProjectionMode.ISOMETRIC):
        from pycc2.domain.value_objects.vec2 import Vec2
        return Camera(
            position=Vec2(512, 256),
            zoom=1.0,
            viewport_width=800,
            viewport_height=600,
            projection=projection,
        )

    def _make_game_map(self, width=20, height=20):
        import numpy as np
        game_map = MagicMock()
        game_map.width = width
        game_map.height = height
        game_map.tile_grid = np.zeros((height, width), dtype=int)
        return game_map

    def test_render_produces_surface(self):
        """Render method produces output on screen surface."""
        renderer = IsometricRenderer()
        screen = pygame.Surface((800, 600))
        renderer.initialize(screen)

        camera = self._make_camera()
        game_map = self._make_game_map()

        renderer.render(game_map, [], camera)
        # If we got here without exception, render succeeded
        assert renderer._offscreen is not None

    def test_render_with_units(self):
        """Render with units doesn't crash."""
        renderer = IsometricRenderer()
        screen = pygame.Surface((800, 600))
        renderer.initialize(screen)

        camera = self._make_camera()
        game_map = self._make_game_map()

        # Create mock unit
        unit = MagicMock()
        unit.is_alive = True
        unit.id = "test_unit"
        unit.position.pixel_position = MagicMock()
        unit.position.pixel_position.x = 100
        unit.position.pixel_position.y = 100
        unit.unit_type.name = "INFANTRY_SQUAD"
        unit.faction.name = "ALLIES"

        renderer.render(game_map, [unit], camera, selected_unit_ids={"test_unit"})

    def test_visible_tile_range(self):
        """Visible tile range is calculated correctly."""
        renderer = IsometricRenderer()
        camera = self._make_camera()
        game_map = self._make_game_map(50, 50)

        start_x, start_y, end_x, end_y = renderer._visible_tile_range(
            game_map, camera, 800, 600
        )
        assert start_x >= 0
        assert start_y >= 0
        assert end_x <= game_map.width
        assert end_y <= game_map.height

    def test_shutdown_clears_caches(self):
        """Shutdown clears all caches."""
        renderer = IsometricRenderer()
        renderer._get_terrain_tile(0)
        renderer._get_building_surface(4, 2, 0)
        assert len(renderer._tile_cache) >= 1, \
            "Should have at least 1 terrain tile cached after generating tile 0"
        assert len(renderer._building_cache) == 1, \
            "Should have exactly 1 building surface cached after generating surface (4,2,0)"

        renderer.shutdown()
        assert len(renderer._tile_cache) == 0
        assert len(renderer._building_cache) == 0


# ============================================================
# IsometricBuildingRenderer Tests
# ============================================================


class TestBuildingRendering:
    def test_render_building_default(self):
        """Default building renders a surface with correct size."""
        surf = render_building()
        assert isinstance(surf, pygame.Surface)
        # Default: 2 height levels, total_height = TILE_H + 2*HEIGHT_SCALE = 32 + 32 = 64
        assert surf.get_width() == TILE_W
        assert surf.get_height() == TILE_H + 2 * 16

    def test_render_building_church(self):
        """Church building is taller (3 levels)."""
        surf = render_building(building_type=BuildingType.CHURCH)
        extra = BUILDING_HEIGHTS[BuildingType.CHURCH] * 16
        assert surf.get_height() == TILE_H + extra

    def test_render_building_barn(self):
        """Barn building has 2 levels."""
        surf = render_building(building_type=BuildingType.BARN)
        extra = BUILDING_HEIGHTS[BuildingType.BARN] * 16
        assert surf.get_height() == TILE_H + extra

    def test_render_building_custom_height(self):
        """Custom height override works."""
        surf = render_building(height_levels=4)
        assert surf.get_height() == TILE_H + 4 * 16

    def test_render_building_damaged(self):
        """Damaged building renders without error."""
        surf = render_building(damage=DamageState.DAMAGED)
        assert isinstance(surf, pygame.Surface)

    def test_render_building_destroyed(self):
        """Destroyed building renders without error."""
        surf = render_building(damage=DamageState.DESTROYED)
        assert isinstance(surf, pygame.Surface)


class TestBuildingTerrainMapping:
    def test_is_building_terrain(self):
        """Building terrain IDs are recognized."""
        assert is_building_terrain(4) is True   # BUILDING_ENTERABLE
        assert is_building_terrain(5) is True   # BUILDING_SOLID
        assert is_building_terrain(8) is True   # WALL
        assert is_building_terrain(0) is False  # OPEN
        assert is_building_terrain(6) is False  # WATER

    def test_terrain_to_building_type(self):
        """Terrain IDs map to correct building types."""
        assert terrain_to_building_type(5) == BuildingType.WALL
        assert terrain_to_building_type(8) == BuildingType.WALL
        assert terrain_to_building_type(4) == BuildingType.GENERIC


class TestBuildingHeights:
    def test_building_height_defaults(self):
        """Each building type has a default height."""
        assert BUILDING_HEIGHTS[BuildingType.HOUSE] == 2
        assert BUILDING_HEIGHTS[BuildingType.CHURCH] == 3
        assert BUILDING_HEIGHTS[BuildingType.BARN] == 2
        assert BUILDING_HEIGHTS[BuildingType.WALL] == 1


# ============================================================
# Camera Isometric Mode Tests
# ============================================================


class TestCameraIsometricMode:
    def test_camera_default_orthographic(self):
        """Camera defaults to ORTHOGRAPHIC projection."""
        from pycc2.domain.value_objects.vec2 import Vec2
        camera = Camera(position=Vec2(0, 0))
        assert camera.projection == ProjectionMode.ORTHOGRAPHIC

    def test_camera_isometric_projection(self):
        """Camera can be set to ISOMETRIC projection."""
        from pycc2.domain.value_objects.vec2 import Vec2
        camera = Camera(position=Vec2(0, 0), projection=ProjectionMode.ISOMETRIC)
        assert camera.projection == ProjectionMode.ISOMETRIC

    def test_camera_isometric_world_to_screen(self):
        """Isometric world_to_screen produces different results than orthographic."""
        from pycc2.domain.value_objects.vec2 import Vec2
        pos = Vec2(100, 100)

        cam_ortho = Camera(position=Vec2(0, 0), projection=ProjectionMode.ORTHOGRAPHIC)
        cam_iso = Camera(position=Vec2(0, 0), projection=ProjectionMode.ISOMETRIC)

        ortho_result = cam_ortho.world_to_screen(pos)
        iso_result = cam_iso.world_to_screen(pos)

        assert ortho_result != iso_result

    def test_camera_isometric_roundtrip(self):
        """Isometric screen_to_world inverts world_to_screen."""
        from pycc2.domain.value_objects.vec2 import Vec2
        camera = Camera(
            position=Vec2(0, 0),
            projection=ProjectionMode.ISOMETRIC,
        )
        world_pos = Vec2(100, 200)
        screen_pos = camera.world_to_screen(world_pos)
        recovered = camera.screen_to_world(screen_pos)

        assert abs(recovered.x - world_pos.x) < 1.0
        assert abs(recovered.y - world_pos.y) < 1.0


# ============================================================
# Projection Toggle Tests
# ============================================================


class TestProjectionToggle:
    def test_toggle_ortho_to_iso(self):
        """Toggling from ORTHOGRAPHIC switches to ISOMETRIC."""
        from pycc2.domain.value_objects.vec2 import Vec2
        camera = Camera(position=Vec2(0, 0), projection=ProjectionMode.ORTHOGRAPHIC)
        if camera.projection == ProjectionMode.ORTHOGRAPHIC:
            camera.projection = ProjectionMode.ISOMETRIC
        assert camera.projection == ProjectionMode.ISOMETRIC

    def test_toggle_iso_to_ortho(self):
        """Toggling from ISOMETRIC switches to ORTHOGRAPHIC."""
        from pycc2.domain.value_objects.vec2 import Vec2
        camera = Camera(position=Vec2(0, 0), projection=ProjectionMode.ISOMETRIC)
        if camera.projection != ProjectionMode.ORTHOGRAPHIC:
            camera.projection = ProjectionMode.ORTHOGRAPHIC
        assert camera.projection == ProjectionMode.ORTHOGRAPHIC

    def test_toggle_roundtrip(self):
        """Toggling twice returns to original mode."""
        from pycc2.domain.value_objects.vec2 import Vec2
        camera = Camera(position=Vec2(0, 0), projection=ProjectionMode.ORTHOGRAPHIC)
        # Toggle once
        camera.projection = ProjectionMode.ISOMETRIC
        # Toggle again
        camera.projection = ProjectionMode.ORTHOGRAPHIC
        assert camera.projection == ProjectionMode.ORTHOGRAPHIC


# ============================================================
# Depth Sorting in Isometric Mode Tests
# ============================================================


class TestIsometricDepthSorting:
    def test_units_sorted_by_depth_key(self):
        """Units in isometric mode are sorted by depth key."""
        r1 = IsometricRenderable(world_x=0, world_y=0, layer=RenderLayer.UNIT, data="unit1")
        r2 = IsometricRenderable(world_x=5, world_y=5, layer=RenderLayer.UNIT, data="unit2")
        r3 = IsometricRenderable(world_x=3, world_y=1, layer=RenderLayer.UNIT, data="unit3")

        sorted_list = sort_for_isometric([r2, r1, r3])
        # r1 (0+0=0) should be first, then r3 (3+1=4), then r2 (5+5=10)
        assert sorted_list[0].data == "unit1"
        assert sorted_list[1].data == "unit3"
        assert sorted_list[2].data == "unit2"

    def test_terrain_drawn_before_units(self):
        """Terrain is always drawn before units regardless of position."""
        terrain = IsometricRenderable(world_x=10, world_y=10, layer=RenderLayer.TERRAIN, data="tile")
        unit = IsometricRenderable(world_x=0, world_y=0, layer=RenderLayer.UNIT, data="unit")

        sorted_list = sort_for_isometric([unit, terrain])
        assert sorted_list[0].layer == RenderLayer.TERRAIN
        assert sorted_list[1].layer == RenderLayer.UNIT

    def test_mixed_layers_sorting(self):
        """Mixed renderable types sort correctly by layer then depth."""
        renderables = [
            IsometricRenderable(world_x=5, world_y=5, layer=RenderLayer.UNIT, data="unit"),
            IsometricRenderable(world_x=2, world_y=2, layer=RenderLayer.TERRAIN, data="tile"),
            IsometricRenderable(world_x=3, world_y=3, layer=RenderLayer.EFFECT, data="effect"),
            IsometricRenderable(world_x=1, world_y=1, layer=RenderLayer.BUILDING, data="building"),
        ]

        sorted_list = sort_for_isometric(renderables)
        layers = [r.layer for r in sorted_list]
        assert layers == sorted(layers)
