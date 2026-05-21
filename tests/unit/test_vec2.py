"""
Tests for Vec2 Value Object
"""

import math

import pytest

from pycc2.domain.value_objects.vec2 import Vec2


class TestVec2Construction:
    def test_construct_with_defaults(self):
        v = Vec2()
        assert v.x == 0.0
        assert v.y == 0.0

    def test_construct_with_values(self):
        v = Vec2(3.0, 4.0)
        assert v.x == 3.0
        assert v.y == 4.0

    def test_zero_factory(self):
        v = Vec2.zero()
        assert v.x == 0.0
        assert v.y == 0.0

    def test_one_factory(self):
        v = Vec2.one()
        assert v.x == 1.0
        assert v.y == 1.0

    def test_from_tile_factory(self):
        v = Vec2.from_tile(2, 3)
        assert v.x == 64.0
        assert v.y == 96.0

    def test_tile_size_constant(self):
        assert Vec2.TILE_SIZE == 32.0


class TestVec2Operators:
    def test_addition(self):
        a = Vec2(1, 2)
        b = Vec2(3, 4)
        c = a + b
        assert c.x == 4.0
        assert c.y == 6.0

    def test_subtraction(self):
        a = Vec2(5, 7)
        b = Vec2(2, 3)
        c = a - b
        assert c.x == 3.0
        assert c.y == 4.0

    def test_scalar_multiplication(self):
        v = Vec2(2, 3)
        result = v * 3
        assert result.x == 6.0
        assert result.y == 9.0

    def test_scalar_division(self):
        v = Vec2(6, 9)
        result = v / 3
        assert result.x == 2.0
        assert result.y == 3.0

    def test_division_by_zero_raises(self):
        v = Vec2(1, 1)
        with pytest.raises(ValueError):
            _ = v / 0

    def test_negation(self):
        v = Vec2(1, -2)
        result = -v
        assert result.x == -1.0
        assert result.y == 2.0

    def test_abs(self):
        v = Vec2(-3, -4)
        result = abs(v)
        assert result.x == 3.0
        assert result.y == 4.0


class TestVec2Properties:
    def test_length(self):
        v = Vec2(3, 4)
        assert v.length == 5.0

    def test_length_zero_vector(self):
        v = Vec2.zero()
        assert v.length == 0.0

    def test_length_squared(self):
        v = Vec2(3, 4)
        assert v.length_squared == 25.0

    def test_normalized_unit_vector(self):
        v = Vec2(3, 4)
        n = v.normalized
        assert abs(n.length - 1.0) < 1e-9

    def test_normalized_zero_vector_returns_zero(self):
        v = Vec2.zero()
        n = v.normalized
        assert n == Vec2.zero()

    def test_perpendicular_counterclockwise(self):
        v = Vec2(1, 0)
        p = v.perpendicular
        assert p.x == pytest.approx(0.0)
        assert p.y == pytest.approx(1.0)


class TestVec2Methods:
    def test_distance_to(self):
        a = Vec2(0, 0)
        b = Vec2(3, 4)
        assert a.distance_to(b) == 5.0

    def test_dot_product(self):
        a = Vec2(1, 2)
        b = Vec2(3, 4)
        assert a.dot(b) == 11.0

    def test_cross_product(self):
        a = Vec2(1, 0)
        b = Vec2(0, 1)
        assert a.cross(b) == 1.0

    def test_lerp_at_t0(self):
        a = Vec2(0, 0)
        b = Vec2(10, 10)
        assert a.lerp(b, 0) == Vec2(0, 0)

    def test_lerp_at_t1(self):
        a = Vec2(0, 0)
        b = Vec2(10, 10)
        assert a.lerp(b, 1) == Vec2(10, 10)

    def test_lerp_at_half(self):
        a = Vec2(0, 0)
        b = Vec2(10, 10)
        result = a.lerp(b, 0.5)
        assert result.x == pytest.approx(5.0)
        assert result.y == pytest.approx(5.0)

    def test_angle_to_same_direction(self):
        a = Vec2(1, 0)
        b = Vec2(1, 0)
        assert a.angle_to(b) == pytest.approx(0.0)

    def test_angle_to_perpendicular(self):
        a = Vec2(1, 0)
        b = Vec2(0, 1)
        assert a.angle_to(b) == pytest.approx(math.pi / 2)

    def test_to_tile_coord(self):
        v = Vec2(64.0, 96.0)
        tile = v.to_tile_coord()
        assert tile == (2, 3)

    def test_to_tile_coord_origin(self):
        v = Vec2(0.0, 0.0)
        tile = v.to_tile_coord()
        assert tile == (0, 0)

    def test_clamp_length_within_limit(self):
        v = Vec2(3, 4)
        result = v.clamp_length(10)
        assert result == v

    def test_clamp_length_exceeds_limit(self):
        v = Vec2(30, 40)
        result = v.clamp_length(5)
        assert abs(result.length - 5.0) < 1e-9

    def test_rotate_90_degrees_pi_2(self):
        v = Vec2(1, 0)
        result = v.rotate(math.pi / 2)
        assert result.x == pytest.approx(0.0, abs=1e-9)
        assert result.y == pytest.approx(1.0, abs=1e-9)


class TestVec2SpecialCases:
    def test_equality(self):
        a = Vec2(1, 2)
        b = Vec2(1, 2)
        c = Vec2(1, 3)
        assert a == b
        assert a != c

    def test_hash_consistency(self):
        a = Vec2(1, 2)
        b = Vec2(1, 2)
        assert hash(a) == hash(b)

    def test_hash_usable_in_set(self):
        s = {Vec2(1, 2), Vec2(3, 4), Vec2(1, 2)}
        assert len(s) == 2

    def test_frozen_immutability(self):
        v = Vec2(1, 2)
        with pytest.raises(AttributeError):
            v.x = 999

    def test_iterable(self):
        v = Vec2(1, 2)
        components = list(v)
        assert components == [1.0, 2.0]
