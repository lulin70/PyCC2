"""Unit tests for isometric coordinate transforms."""

from pycc2.presentation.rendering.isometric_transform import (
    HEIGHT_SCALE,
    TILE_H,
    TILE_W,
    depth_sort_key,
    is_point_in_diamond,
    isometric_to_world,
    tile_diamond_corners,
    world_to_isometric,
)


class TestWorldToIsometric:
    def test_world_to_isometric_origin(self):
        """Origin (0,0) maps to screen (0,0)."""
        sx, sy = world_to_isometric(0, 0)
        assert sx == 0.0
        assert sy == 0.0

    def test_world_to_isometric_unit_x(self):
        """(1, 0) maps to (TILE_W/2, TILE_H/2) = (32, 16)."""
        sx, sy = world_to_isometric(1, 0)
        assert sx == TILE_W / 2
        assert sy == TILE_H / 2

    def test_world_to_isometric_unit_y(self):
        """(0, 1) maps to (-TILE_W/2, TILE_H/2) = (-32, 16)."""
        sx, sy = world_to_isometric(0, 1)
        assert sx == -TILE_W / 2
        assert sy == TILE_H / 2

    def test_world_to_isometric_diagonal(self):
        """(1, 1) maps to (0, TILE_H) = (0, 32)."""
        sx, sy = world_to_isometric(1, 1)
        assert sx == 0.0
        assert sy == TILE_H

    def test_world_to_isometric_negative(self):
        """Negative world coords produce negative screen offsets."""
        sx, sy = world_to_isometric(-1, -1)
        assert sx == 0.0
        assert sy == -TILE_H

    def test_world_to_isometric_mixed(self):
        """(3, 2) produces expected screen coords."""
        sx, sy = world_to_isometric(3, 2)
        # sx = (3-2) * 32 = 32, sy = (3+2) * 16 = 80
        assert sx == 32.0
        assert sy == 80.0


class TestIsometricToWorld:
    def test_isometric_to_world_roundtrip(self):
        """world -> iso -> world roundtrip preserves coordinates."""
        test_points = [
            (0, 0),
            (1, 0),
            (0, 1),
            (1, 1),
            (5, 3),
            (-2, 7),
            (10.5, 3.7),
        ]
        for wx, wy in test_points:
            sx, sy = world_to_isometric(wx, wy)
            rx, ry = isometric_to_world(sx, sy)
            assert abs(rx - wx) < 1e-9, f"Roundtrip failed for ({wx}, {wy}): got rx={rx}"
            assert abs(ry - wy) < 1e-9, f"Roundtrip failed for ({wx}, {wy}): got ry={ry}"

    def test_isometric_to_world_origin(self):
        """Screen (0, 0) maps back to world (0, 0)."""
        wx, wy = isometric_to_world(0, 0)
        assert wx == 0.0
        assert wy == 0.0


class TestHeightOffset:
    def test_height_offset(self):
        """Z-axis shifts screen_y upward by wz * HEIGHT_SCALE."""
        sx0, sy0 = world_to_isometric(5, 5, wz=0)
        sx1, sy1 = world_to_isometric(5, 5, wz=1)
        assert sx1 == sx0  # X unchanged
        assert sy1 == sy0 - HEIGHT_SCALE  # Y shifted up

    def test_height_offset_multiple_levels(self):
        """Multiple height levels shift proportionally."""
        sx0, sy0 = world_to_isometric(3, 4, wz=0)
        sx3, sy3 = world_to_isometric(3, 4, wz=3)
        assert sx3 == sx0
        assert sy3 == sy0 - 3 * HEIGHT_SCALE

    def test_inverse_with_height(self):
        """Roundtrip with non-zero wz works correctly."""
        wx, wy, wz = 5.0, 3.0, 2.0
        sx, sy = world_to_isometric(wx, wy, wz)
        rx, ry = isometric_to_world(sx, sy, wz)
        assert abs(rx - wx) < 1e-9
        assert abs(ry - wy) < 1e-9

    def test_inverse_with_height_zero_vs_nonzero(self):
        """Using wrong wz in inverse gives wrong result (sanity check)."""
        wx, wy, wz = 5.0, 3.0, 2.0
        sx, sy = world_to_isometric(wx, wy, wz)
        # Inverting with wz=0 should NOT recover original
        rx, ry = isometric_to_world(sx, sy, wz=0)
        assert not (abs(rx - wx) < 1e-3 and abs(ry - wy) < 1e-3)


class TestDepthSortKey:
    def test_depth_sort_key_ordering(self):
        """Back-to-front ordering: smaller key = farther from viewer."""
        # (0,0) is farthest, (5,5) is closest
        key_00 = depth_sort_key(0, 0)
        key_50 = depth_sort_key(5, 0)
        key_05 = depth_sort_key(0, 5)
        key_55 = depth_sort_key(5, 5)
        assert key_00 < key_50
        assert key_00 < key_05
        assert key_50 < key_55
        assert key_05 < key_55

    def test_depth_sort_key_with_height(self):
        """Height adds a small contribution to sort key."""
        key_ground = depth_sort_key(5, 5, wz=0)
        key_elevated = depth_sort_key(5, 5, wz=1)
        assert key_elevated > key_ground

    def test_depth_sort_key_height_subtle(self):
        """Height contribution is subtle (0.01 per level) so it doesn't
        override the primary wx+wy ordering."""
        key_near_ground = depth_sort_key(1, 1, wz=0)
        key_far_elevated = depth_sort_key(0, 0, wz=100)
        # Even with wz=100, the far object should still be drawn first
        assert key_far_elevated < key_near_ground


class TestTileDiamondCorners:
    def test_tile_diamond_corners(self):
        """Verify 4 corners of diamond centered at (32, 16)."""
        corners = tile_diamond_corners(32, 16)
        assert len(corners) == 4
        # top
        assert corners[0] == (32, 0)
        # right
        assert corners[1] == (64, 16)
        # bottom
        assert corners[2] == (32, 32)
        # left
        assert corners[3] == (0, 16)

    def test_tile_diamond_corners_custom_center(self):
        """Corners with a custom center position."""
        corners = tile_diamond_corners(100, 50)
        assert corners[0] == (100, 50 - TILE_H / 2)
        assert corners[1] == (100 + TILE_W / 2, 50)
        assert corners[2] == (100, 50 + TILE_H / 2)
        assert corners[3] == (100 - TILE_W / 2, 50)


class TestIsPointInDiamond:
    def test_is_point_in_diamond_center(self):
        """Center point is inside the diamond."""
        assert is_point_in_diamond(32, 16, 32, 16) is True

    def test_is_point_in_diamond_outside(self):
        """Corner point (far outside) is outside the diamond."""
        # Top-left corner of bounding box is well outside
        assert is_point_in_diamond(0, 0, 32, 16) is False

    def test_is_point_in_diamond_top_vertex(self):
        """Top vertex is on the edge (should be inside)."""
        assert is_point_in_diamond(32, 0, 32, 16) is True

    def test_is_point_in_diamond_right_vertex(self):
        """Right vertex is on the edge (should be inside)."""
        assert is_point_in_diamond(64, 16, 32, 16) is True

    def test_is_point_in_diamond_slightly_inside(self):
        """Point slightly inside from edge is inside."""
        assert is_point_in_diamond(32, 8, 32, 16) is True

    def test_is_point_in_diamond_slightly_outside(self):
        """Point slightly outside from edge is outside."""
        assert is_point_in_diamond(32, -1, 32, 16) is False

    def test_is_point_in_diamond_custom_center(self):
        """Test with a non-origin center."""
        cx, cy = 100, 200
        # Center should be inside
        assert is_point_in_diamond(cx, cy, cx, cy) is True
        # Far outside
        assert is_point_in_diamond(cx - 50, cy - 50, cx, cy) is False


class TestConstants:
    def test_tile_dimensions(self):
        """Verify tile dimension constants."""
        assert TILE_W == 64
        assert TILE_H == 32
        assert TILE_W / TILE_H == 2  # 2:1 ratio

    def test_height_scale(self):
        """Verify height scale constant."""
        assert HEIGHT_SCALE == 16
