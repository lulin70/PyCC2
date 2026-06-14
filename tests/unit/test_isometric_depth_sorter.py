"""Unit tests for isometric depth sorter."""

from dataclasses import dataclass
from typing import Any

from pycc2.presentation.rendering.isometric_depth_sorter import (
    IsometricRenderable,
    RenderLayer,
    effect_to_renderable,
    sort_for_isometric,
    tile_to_renderable,
    unit_to_renderable,
)

# ============================================================
# Helpers
# ============================================================


def _make_renderable(
    wx: float,
    wy: float,
    wz: float = 0.0,
    layer: RenderLayer = RenderLayer.TERRAIN,
    data: Any = None,
) -> IsometricRenderable:
    return IsometricRenderable(world_x=wx, world_y=wy, world_z=wz, layer=layer, data=data)


# ============================================================
# sort_for_isometric
# ============================================================


class TestSortEmptyList:
    def test_sort_empty_list(self):
        """Sorting an empty list returns an empty list."""
        result = sort_for_isometric([])
        assert result == []


class TestSortSingleItem:
    def test_sort_single_item(self):
        """Sorting a single-item list returns that item."""
        item = _make_renderable(3, 4)
        result = sort_for_isometric([item])
        assert result == [item]


class TestSortTerrainBeforeUnits:
    def test_sort_terrain_before_units(self):
        """Terrain at (5,5) is drawn before a unit at (0,0)."""
        terrain = _make_renderable(5, 5, layer=RenderLayer.TERRAIN)
        unit = _make_renderable(0, 0, layer=RenderLayer.UNIT)
        result = sort_for_isometric([unit, terrain])
        assert result[0] is terrain
        assert result[1] is unit


class TestSortBackToFront:
    def test_sort_back_to_front(self):
        """Objects at (0,0) drawn before (1,1) — farther first."""
        near = _make_renderable(1, 1, layer=RenderLayer.TERRAIN)
        far = _make_renderable(0, 0, layer=RenderLayer.TERRAIN)
        result = sort_for_isometric([near, far])
        assert result[0] is far
        assert result[1] is near


class TestSortLayerPriority:
    def test_sort_layer_priority(self):
        """Terrain always before units regardless of position."""
        terrain_far = _make_renderable(10, 10, layer=RenderLayer.TERRAIN)
        unit_near = _make_renderable(0, 0, layer=RenderLayer.UNIT)
        terrain_near = _make_renderable(0, 0, layer=RenderLayer.TERRAIN)
        unit_far = _make_renderable(10, 10, layer=RenderLayer.UNIT)
        result = sort_for_isometric([unit_near, terrain_far, unit_far, terrain_near])
        # All terrain first, then all units
        assert all(r.layer == RenderLayer.TERRAIN for r in result[:2])
        assert all(r.layer == RenderLayer.UNIT for r in result[2:])


class TestSortHeightAffectsOrder:
    def test_sort_height_affects_order(self):
        """Higher objects on the same tile are drawn after ground objects."""
        ground = _make_renderable(3, 3, wz=0.0, layer=RenderLayer.TERRAIN)
        elevated = _make_renderable(3, 3, wz=5.0, layer=RenderLayer.TERRAIN)
        result = sort_for_isometric([elevated, ground])
        assert result[0] is ground
        assert result[1] is elevated


class TestSortSamePositionDifferentLayers:
    def test_sort_same_position_different_layers(self):
        """Same world position but different layers: lower layer drawn first."""
        terrain = _make_renderable(5, 5, layer=RenderLayer.TERRAIN)
        decoration = _make_renderable(5, 5, layer=RenderLayer.DECORATION)
        building = _make_renderable(5, 5, layer=RenderLayer.BUILDING)
        unit = _make_renderable(5, 5, layer=RenderLayer.UNIT)
        effect = _make_renderable(5, 5, layer=RenderLayer.EFFECT)
        ui = _make_renderable(5, 5, layer=RenderLayer.UI_OVERLAY)
        result = sort_for_isometric([ui, effect, unit, building, decoration, terrain])
        assert result == [terrain, decoration, building, unit, effect, ui]


# ============================================================
# Conversion helpers
# ============================================================


class TestTileToRenderable:
    def test_tile_to_renderable(self):
        """tile_to_renderable creates a TERRAIN-layer renderable."""
        tile_data = {"type": "grass"}
        r = tile_to_renderable(3, 7, tile_data)
        assert r.world_x == 3.0
        assert r.world_y == 7.0
        assert r.world_z == 0.0
        assert r.layer == RenderLayer.TERRAIN
        assert r.data is tile_data


class TestUnitToRenderable:
    def test_unit_to_renderable(self):
        """unit_to_renderable uses unit.position for coords and UNIT layer."""

        @dataclass
        class MockPosition:
            x: float
            y: float
            z: float = 0.0

        @dataclass
        class MockUnit:
            position: MockPosition

        unit = MockUnit(position=MockPosition(x=4, y=2, z=1.5))
        r = unit_to_renderable(unit)
        assert r.world_x == 4.0
        assert r.world_y == 2.0
        assert r.world_z == 1.5
        assert r.layer == RenderLayer.UNIT
        assert r.data is unit

    def test_unit_to_renderable_no_z(self):
        """unit_to_renderable defaults z to 0.0 if position has no z."""

        @dataclass
        class MockPosition:
            x: float
            y: float

        @dataclass
        class MockUnit:
            position: MockPosition

        unit = MockUnit(position=MockPosition(x=1, y=2))
        r = unit_to_renderable(unit)
        assert r.world_z == 0.0


class TestEffectToRenderable:
    def test_effect_to_renderable(self):
        """effect_to_renderable creates an EFFECT-layer renderable."""
        effect_data = {"type": "explosion"}
        r = effect_to_renderable(6.5, 3.2, 2.0, effect_data)
        assert r.world_x == 6.5
        assert r.world_y == 3.2
        assert r.world_z == 2.0
        assert r.layer == RenderLayer.EFFECT
        assert r.data is effect_data
