"""
Unit Tests for LOS System

Tests line of sight calculation, blocking terrain detection,
Bresenham ray casting, and building visibility bonuses.
"""

import math
import pytest
from unittest.mock import Mock

from pycc2.domain.systems.los_system import Lossystem, LosStatus, LosResult
from pycc2.domain.value_objects.tile_coord import TileCoord


# ===========================================================================
# Stub helpers
# ===========================================================================

class StubTerrain:
    """Minimal terrain stub."""

    def __init__(self, name="grass", blocks_los=False):
        self.name = name
        self.blocks_los = blocks_los


def _make_game_map(terrain_map=None, enhanced_tiles=None, width=30, height=30):
    """Create a mock game map with configurable terrain."""
    game_map = Mock()
    game_map.width = width
    game_map.height = height

    if terrain_map is None:
        terrain_map = {}

    if enhanced_tiles is None:
        enhanced_tiles = {}

    def get_terrain(coord):
        return terrain_map.get((coord.x, coord.y), StubTerrain("grass", False))

    def get_enhanced_tile(x, y):
        return enhanced_tiles.get((x, y), None)

    def is_within_bounds(coord):
        return 0 <= coord.x < width and 0 <= coord.y < height

    game_map.get_terrain = get_terrain
    game_map.get_enhanced_tile = get_enhanced_tile
    game_map.is_within_bounds = is_within_bounds

    return game_map


# ===========================================================================
# Tests — Bresenham Line
# ===========================================================================

@pytest.mark.unit
class TestBresenhamLine:
    """Test the Bresenham line algorithm."""

    def test_horizontal_line(self):
        line = Lossystem._bresenham_line_enhanced(TileCoord(0, 0), TileCoord(3, 0))
        assert TileCoord(0, 0) in line
        assert TileCoord(3, 0) in line
        assert len(line) >= 4  # At least 4 points

    def test_vertical_line(self):
        line = Lossystem._bresenham_line_enhanced(TileCoord(0, 0), TileCoord(0, 3))
        assert TileCoord(0, 0) in line
        assert TileCoord(0, 3) in line

    def test_diagonal_line(self):
        line = Lossystem._bresenham_line_enhanced(TileCoord(0, 0), TileCoord(3, 3))
        assert TileCoord(0, 0) in line
        assert TileCoord(3, 3) in line

    def test_same_point(self):
        line = Lossystem._bresenham_line_enhanced(TileCoord(5, 5), TileCoord(5, 5))
        assert len(line) == 1
        assert line[0] == TileCoord(5, 5)


# ===========================================================================
# Tests — LOS Check
# ===========================================================================

@pytest.mark.unit
class TestCheckLos:
    """Test line of sight checking."""

    def test_clear_los_on_flat_terrain(self):
        game_map = _make_game_map()
        los = Lossystem(game_map)
        can_see, result = los.check_los(TileCoord(0, 0), TileCoord(5, 5))
        assert can_see is True
        assert result.status == LosStatus.CLEAR

    def test_out_of_range(self):
        game_map = _make_game_map()
        los = Lossystem(game_map)
        # Distance > 15 (default visual range)
        can_see, result = los.check_los(TileCoord(0, 0), TileCoord(20, 20))
        assert can_see is False
        assert result.status == LosStatus.OUT_OF_RANGE

    def test_blocked_by_terrain(self):
        # Place a blocking terrain at (3, 3)
        terrain_map = {
            (3, 3): StubTerrain("building_solid", blocks_los=True),
        }
        game_map = _make_game_map(terrain_map=terrain_map)
        los = Lossystem(game_map)
        can_see, result = los.check_los(TileCoord(1, 1), TileCoord(5, 5))
        assert can_see is False
        assert result.status == LosStatus.BLOCKED_TERRAIN

    def test_los_caching(self):
        game_map = _make_game_map()
        los = Lossystem(game_map)
        # First call
        can_see1, result1 = los.check_los(TileCoord(0, 0), TileCoord(5, 5))
        # Second call should hit cache
        can_see2, result2 = los.check_los(TileCoord(0, 0), TileCoord(5, 5))
        assert can_see1 == can_see2
        assert result1 is result2  # Same cached object

    def test_clear_cache(self):
        game_map = _make_game_map()
        los = Lossystem(game_map)
        los.check_los(TileCoord(0, 0), TileCoord(5, 5))
        assert len(los._cache) > 0
        los.clear_cache()
        assert len(los._cache) == 0


# ===========================================================================
# Tests — Height Blocking
# ===========================================================================

@pytest.mark.unit
class TestHeightBlocking:
    """Test height-based LOS blocking."""

    def test_elevation_blocks_los(self):
        # Place a tall hill at (3, 3)
        enhanced_tiles = {
            (3, 3): {"elevation": 5.0, "building_height": 0.0},
            (1, 1): {"elevation": 0.0, "building_height": 0.0},
            (5, 5): {"elevation": 0.0, "building_height": 0.0},
        }
        game_map = _make_game_map(enhanced_tiles=enhanced_tiles)
        los = Lossystem(game_map)
        can_see, result = los.check_los(TileCoord(1, 1), TileCoord(5, 5))
        # The tall hill should block LOS
        assert can_see is False
        assert result.status == LosStatus.BLOCKED_HEIGHT

    def test_high_observer_sees_further(self):
        # Observer on high ground should have range bonus
        enhanced_tiles = {
            (0, 0): {"elevation": 3.0, "building_height": 0.0},
            (14, 0): {"elevation": 0.0, "building_height": 0.0},
        }
        game_map = _make_game_map(enhanced_tiles=enhanced_tiles)
        los = Lossystem(game_map)
        can_see, result = los.check_los(TileCoord(0, 0), TileCoord(14, 0))
        # With elevation bonus, should be within range
        assert can_see is True


# ===========================================================================
# Tests — Building Visibility Bonus
# ===========================================================================

@pytest.mark.unit
class TestBuildingVisibilityBonus:
    """Test building floor-based visibility bonus."""

    def test_no_building_data(self):
        game_map = _make_game_map()
        bonus = Lossystem.get_building_visibility_bonus(5, 5, game_map)
        assert bonus == 1.0

    def test_one_floor_no_bonus(self):
        enhanced_tiles = {(5, 5): {"building_floors": 1}}
        game_map = _make_game_map(enhanced_tiles=enhanced_tiles)
        bonus = Lossystem.get_building_visibility_bonus(5, 5, game_map)
        assert bonus == 1.0

    def test_two_floors_bonus(self):
        enhanced_tiles = {(5, 5): {"building_floors": 2}}
        game_map = _make_game_map(enhanced_tiles=enhanced_tiles)
        bonus = Lossystem.get_building_visibility_bonus(5, 5, game_map)
        assert bonus == 1.25

    def test_five_plus_floors_max_bonus(self):
        enhanced_tiles = {(5, 5): {"building_floors": 6}}
        game_map = _make_game_map(enhanced_tiles=enhanced_tiles)
        bonus = Lossystem.get_building_visibility_bonus(5, 5, game_map)
        assert bonus == 2.0


# ===========================================================================
# Tests — Attack Line Integration
# ===========================================================================

@pytest.mark.unit
class TestAttackLineIntegration:
    """Test LOS result to attack line status conversion."""

    def _make_los(self):
        return Lossystem(_make_game_map())

    def test_clear_to_can_attack(self):
        result = LosResult(status=LosStatus.CLEAR, can_see=True)
        assert self._make_los().integrate_to_attack_line_status(result) == "CAN_ATTACK"

    def test_blocked_to_blocked(self):
        result = LosResult(status=LosStatus.BLOCKED_TERRAIN, can_see=False)
        assert self._make_los().integrate_to_attack_line_status(result) == "BLOCKED"

    def test_out_of_range(self):
        result = LosResult(status=LosStatus.OUT_OF_RANGE, can_see=False)
        assert self._make_los().integrate_to_attack_line_status(result) == "OUT_OF_RANGE"

    def test_partial_to_can_attack(self):
        result = LosResult(status=LosStatus.PARTIAL, can_see=True)
        assert self._make_los().integrate_to_attack_line_status(result) == "CAN_ATTACK"


# ===========================================================================
# Tests — Angle Difference
# ===========================================================================

@pytest.mark.unit
class TestAngleDiff:
    """Test the angle difference helper."""

    def test_same_angle(self):
        assert abs(Lossystem._angle_diff(0.0, 0.0)) < 0.001

    def test_opposite_angle(self):
        diff = Lossystem._angle_diff(math.pi, 0.0)
        assert abs(abs(diff) - math.pi) < 0.001

    def test_wrapping(self):
        diff = Lossystem._angle_diff(-math.pi, math.pi)
        assert abs(diff) < 0.001


# ===========================================================================
# Tests — Get Blocking Terrain
# ===========================================================================

@pytest.mark.unit
class TestGetBlockingTerrain:
    """Test blocking terrain identification."""

    def test_no_blocking_returns_empty(self):
        game_map = _make_game_map()
        los = Lossystem(game_map)
        blocking = los.get_blocking_terrain(TileCoord(0, 0), TileCoord(3, 0))
        assert blocking == []

    def test_blocking_returns_coord(self):
        terrain_map = {
            (2, 0): StubTerrain("building_solid", blocks_los=True),
        }
        game_map = _make_game_map(terrain_map=terrain_map)
        los = Lossystem(game_map)
        blocking = los.get_blocking_terrain(TileCoord(0, 0), TileCoord(5, 0))
        assert len(blocking) > 0
