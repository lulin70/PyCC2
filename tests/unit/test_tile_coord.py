"""
Tests for TileCoord Value Object
"""

import math

import pytest

from pycc2.domain.value_objects.tile_coord import TileCoord


class TestTileCoordConstruction:
    def test_construct(self):
        tc = TileCoord(3, 5)
        assert tc.x == 3
        assert tc.y == 5

    def test_origin_factory(self):
        tc = TileCoord.origin()
        assert tc.x == 0
        assert tc.y == 0

    def test_from_tuple(self):
        tc = TileCoord.from_tuple((7, 9))
        assert tc.x == 7
        assert tc.y == 9


class TestTileCoordNeighbors:
    def test_neighbors_8_count(self):
        tc = TileCoord(5, 5)
        neighbors = tc.neighbors_8
        assert len(neighbors) == 8

    def test_neighbors_8_contains_expected(self):
        tc = TileCoord(0, 0)
        neighbors = tc.neighbors_8
        neighbor_set = {(n.x, n.y) for n in neighbors}
        expected = {
            (0, -1),
            (0, 1),
            (-1, 0),
            (1, 0),
            (-1, -1),
            (1, -1),
            (-1, 1),
            (1, 1),
        }
        assert neighbor_set == expected


class TestTileCoordDistances:
    def test_manhattan_distance(self):
        a = TileCoord(0, 0)
        b = TileCoord(3, 4)
        assert a.manhattan_distance(b) == 7

    def test_chebyshev_distance(self):
        a = TileCoord(0, 0)
        b = TileCoord(3, 4)
        assert a.chebyshev_distance(b) == 4

    def test_octile_distance_straight_line(self):
        a = TileCoord(0, 0)
        b = TileCoord(5, 0)
        dist = a.octile_distance(b)
        assert dist == pytest.approx(5.0)

    def test_octile_distance_diagonal(self):
        a = TileCoord(0, 0)
        b = TileCoord(3, 3)
        dist = a.octile_distance(b)
        expected = 3 + (math.sqrt(2) - 1) * 3
        assert dist == pytest.approx(expected)

    def test_octile_distance_mixed(self):
        a = TileCoord(0, 0)
        b = TileCoord(5, 3)
        dx, dy = 5, 3
        expected = max(dx, dy) + (math.sqrt(2) - 1) * min(dx, dy)
        dist = a.octile_distance(b)
        assert dist == pytest.approx(expected)


class TestTileCoordBounds:
    def test_is_within_bounds_true(self):
        tc = TileCoord(2, 3)
        assert tc.is_within_bounds(5, 5) is True

    def test_is_within_bounds_false_x(self):
        tc = TileCoord(5, 3)
        assert tc.is_within_bounds(5, 5) is False

    def test_is_within_bounds_false_y(self):
        tc = TileCoord(2, 5)
        assert tc.is_within_bounds(5, 5) is False

    def test_is_within_bounds_negative(self):
        tc = TileCoord(-1, 0)
        assert tc.is_within_bounds(5, 5) is False


class TestTileCoordOffsetAndOps:
    def test_offset_positive(self):
        tc = TileCoord(1, 2)
        result = tc.offset(3, 4)
        assert result.x == 4
        assert result.y == 6

    def test_offset_negative(self):
        tc = TileCoord(5, 5)
        result = tc.offset(-2, -3)
        assert result.x == 3
        assert result.y == 2

    def test_equality(self):
        a = TileCoord(1, 2)
        b = TileCoord(1, 2)
        c = TileCoord(1, 3)
        assert a == b
        assert a != c

    def test_hash(self):
        a = TileCoord(1, 2)
        b = TileCoord(1, 2)
        assert hash(a) == hash(b)

    def test_frozen_immutability(self):
        tc = TileCoord(1, 2)
        with pytest.raises(AttributeError):
            tc.x = 999
