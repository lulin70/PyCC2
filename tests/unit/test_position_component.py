"""
Unit tests for PositionComponent
"""

from __future__ import annotations

import math

import pytest

from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.domain.value_objects.vec2 import Vec2


class TestPositionComponentConstruction:
    def test_default_construction(self):
        pos = PositionComponent(tile_coord=TileCoord(5, 3))
        assert pos.tile_coord == TileCoord(5, 3)
        assert pos.pixel_offset == Vec2.zero()
        assert pos.facing_rad == 0.0

    def test_custom_pixel_offset(self):
        offset = Vec2(10.0, 20.0)
        pos = PositionComponent(tile_coord=TileCoord(0, 0), pixel_offset=offset)
        assert pos.pixel_offset == offset

    def test_custom_facing(self):
        pos = PositionComponent(tile_coord=TileCoord(0, 0), facing_rad=math.pi / 4)
        assert pytest.approx(pos.facing_rad) == math.pi / 4


class TestPositionComponentPixelPosition:
    def test_pixel_position_at_origin(self):
        pos = PositionComponent(tile_coord=TileCoord(0, 0))
        expected = Vec2(0.0, 0.0)
        assert pos.pixel_position == expected

    def test_pixel_position_at_tile_1_1(self):
        pos = PositionComponent(tile_coord=TileCoord(1, 1))
        tile_size = Vec2.TILE_SIZE
        expected = Vec2(tile_size, tile_size)
        assert pos.pixel_position == expected

    def test_pixel_position_with_offset(self):
        offset = Vec2(16.0, 8.0)
        pos = PositionComponent(
            tile_coord=TileCoord(2, 3),
            pixel_offset=offset,
        )
        tile_vec = Vec2(2 * Vec2.TILE_SIZE, 3 * Vec2.TILE_SIZE)
        expected = tile_vec + offset
        assert pos.pixel_position == expected


class TestPositionComponentFacing:
    def test_set_facing_toward_vec2_east(self):
        pos = PositionComponent(tile_coord=TileCoord(0, 0))
        target = Vec2(100.0, 0.0)
        pos.set_facing_toward(target)
        assert pytest.approx(pos.facing_rad) == 0.0

    def test_set_facing_toward_vec2_north(self):
        pos = PositionComponent(tile_coord=TileCoord(0, 0))
        target = Vec2(0.0, -100.0)
        pos.set_facing_toward(target)
        assert pytest.approx(abs(pos.facing_rad)) == math.pi / 2

    def test_set_facing_toward_tile_coord(self):
        pos = PositionComponent(tile_coord=TileCoord(0, 0))
        target = TileCoord(10, 0)
        pos.set_facing_toward(target)
        assert pytest.approx(pos.facing_rad) == 0.0


class TestPositionComponentMovement:
    def test_move_to_tile(self):
        pos = PositionComponent(tile_coord=TileCoord(0, 0))
        new_tile = TileCoord(5, 7)
        pos.move_to_tile(new_tile)
        assert pos.tile_coord == new_tile
        assert pos.pixel_offset == Vec2.zero()

    def test_set_pixel_offset(self):
        pos = PositionComponent(tile_coord=TileCoord(3, 4))
        new_offset = Vec2(15.0, 25.0)
        pos.set_pixel_offset(new_offset)
        assert pos.pixel_offset == new_offset


class TestPositionComponentIntegration:
    def test_with_vec2_and_tilecoord(self):
        tile = TileCoord(2, 2)
        offset = Vec2(10.5, 20.5)
        pos = PositionComponent(tile_coord=tile, pixel_offset=offset)

        assert isinstance(pos.tile_coord, TileCoord)
        assert isinstance(pos.pixel_offset, Vec2)
        assert isinstance(pos.pixel_position, Vec2)

    def test_facing_radians_type(self):
        pos = PositionComponent(tile_coord=TileCoord(0, 0), facing_rad=math.pi / 3)
        assert isinstance(pos.facing_rad, float)
