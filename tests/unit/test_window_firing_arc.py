"""Unit tests for P3-2: Building window firing arc verification.

Tests that check_window_firing_arc correctly validates whether a unit inside
a building can fire through a window toward a target direction.

Window directions use screen coordinates (y increases downward):
  east=0 rad, south=pi/2, west=pi, north=-pi/2

Each wall has a 90-degree firing arc (±45 degrees).
"""

from __future__ import annotations

import math
import time

import pytest

from pycc2.domain.systems.los_system import LosStatus, LOSSystem
from pycc2.domain.value_objects.building_data import BUILDING_WINDOWS, CC2BuildingType
from pycc2.domain.value_objects.tile_coord import TileCoord

# ===========================================================================
# Helpers
# ===========================================================================


def _make_los() -> LOSSystem:
    """Create a minimal LOSSystem for testing check_window_firing_arc."""
    from unittest.mock import Mock

    game_map = Mock()
    game_map.width = 30
    game_map.height = 30
    game_map.get_terrain = lambda coord: type("T", (), {"name": "grass", "blocks_los": False})()
    game_map.get_enhanced_tile = lambda x, y: None
    game_map.is_within_bounds = lambda coord: True
    game_map.get_elevation = lambda coord: 0.0
    game_map.get_building_height = lambda coord: 0.0
    return LOSSystem(game_map)


# ===========================================================================
# Happy Path — window firing arc allows correct directions
# ===========================================================================


class TestWindowFiringArcCardinalDirections:
    """Verify firing arc for each cardinal direction."""

    @pytest.mark.parametrize(
        ("dx", "dy", "wall"),
        [
            (10, 0, "east"),
            (-10, 0, "west"),
            (0, 10, "south"),
            (0, -10, "north"),
        ],
    )
    def test_cardinal_direction_matches_window(self, dx: int, dy: int, wall: str) -> None:
        """Verify: firing toward a cardinal direction matches the corresponding window."""
        los = _make_los()
        result = los.check_window_firing_arc(5.0, 5.0, 5.0 + dx, 5.0 + dy, "small_house", 5, 5)
        assert result is True

    def test_small_house_all_directions_allowed(self) -> None:
        """Verify: small_house has 4 windows (N/S/E/W), all directions allowed."""
        windows = BUILDING_WINDOWS[CC2BuildingType.SMALL_HOUSE]
        walls = {w["wall"] for w in windows}
        assert walls == {"north", "south", "east", "west"}

        los = _make_los()
        for dx, dy in [(10, 0), (-10, 0), (0, 10), (0, -10)]:
            assert los.check_window_firing_arc(5.0, 5.0, 5.0 + dx, 5.0 + dy, "small_house", 5, 5)


class TestWindowFiringArcBuildingTypes:
    """Verify firing arc for each building type."""

    @pytest.mark.parametrize(
        ("building_type", "min_windows"),
        [
            ("small_house", 4),
            ("medium_house", 6),
            ("large_building", 10),
            ("barn", 6),
            ("church", 6),
            ("normandy_farmhouse", 6),
            ("normandy_barn", 6),
        ],
    )
    def test_building_type_has_windows(self, building_type: str, min_windows: int) -> None:
        """Verify: each building type defines the expected number of windows."""
        bt = CC2BuildingType(building_type)
        windows = BUILDING_WINDOWS[bt]
        assert len(windows) >= min_windows

    def test_large_building_all_directions(self) -> None:
        """Verify: large_building has windows on all 4 walls."""
        windows = BUILDING_WINDOWS[CC2BuildingType.LARGE_BUILDING]
        walls = {w["wall"] for w in windows}
        assert walls == {"north", "south", "east", "west"}

    def test_normandy_farmhouse_windows(self) -> None:
        """Verify: normandy_farmhouse has windows on all 4 walls."""
        windows = BUILDING_WINDOWS[CC2BuildingType.NORMANDY_FARMHOUSE]
        walls = {w["wall"] for w in windows}
        assert walls == {"north", "south", "east", "west"}


# ===========================================================================
# Error Case — unknown/empty building types
# ===========================================================================


class TestErrorCases:
    """Verify error handling for edge cases."""

    def test_unknown_building_type_allows_firing(self) -> None:
        """Verify: unknown building type allows firing (no restriction)."""
        los = _make_los()
        assert los.check_window_firing_arc(5.0, 5.0, 15.0, 5.0, "nonexistent_type", 5, 5)

    def test_empty_building_type_allows_firing(self) -> None:
        """Verify: empty string building type allows firing."""
        los = _make_los()
        assert los.check_window_firing_arc(5.0, 5.0, 15.0, 5.0, "", 5, 5)

    def test_wall_type_has_no_windows(self) -> None:
        """Verify: WALL type has empty window list (not enterable anyway)."""
        assert BUILDING_WINDOWS[CC2BuildingType.WALL] == []


# ===========================================================================
# Boundary — 45-degree arc edges
# ===========================================================================


class TestBoundaryConditions:
    """Verify boundary conditions at firing arc edges."""

    def test_45_degree_diagonal_allowed_for_small_house(self) -> None:
        """Verify: 45-degree diagonal passes through one of the window arcs.

        At 45 degrees, the angle is on the boundary between east (0±45)
        and south (90±45). Small_house has both east and south windows,
        so the shot should be allowed.
        """
        los = _make_los()
        # 45 degrees = pi/4 rad
        dx, dy = 10, 10
        assert los.check_window_firing_arc(5.0, 5.0, 5.0 + dx, 5.0 + dy, "small_house", 5, 5)

    def test_exact_45_degree_from_east(self) -> None:
        """Verify: exactly 45 degrees from east is at arc boundary."""
        los = _make_los()
        # angle = pi/4 = 45 degrees (between east and south)
        # east arc: -pi/4 to +pi/4 → pi/4 is at boundary
        # south arc: pi/4 to 3pi/4 → pi/4 is at boundary
        # Small house has both → allowed
        angle = math.pi / 4
        dx = math.cos(angle) * 10
        dy = math.sin(angle) * 10
        result = los.check_window_firing_arc(5.0, 5.0, 5.0 + dx, 5.0 + dy, "small_house", 5, 5)
        assert result is True

    def test_angle_diff_method(self) -> None:
        """Verify: _angle_diff computes shortest angular difference."""
        los = _make_los()
        assert los._angle_diff(0.0, 0.0) == pytest.approx(0.0)
        assert los._angle_diff(math.pi, -math.pi) == pytest.approx(0.0, abs=1e-10)
        assert los._angle_diff(math.pi / 2, 0.0) == pytest.approx(math.pi / 2)
        assert los._angle_diff(-math.pi / 2, 0.0) == pytest.approx(-math.pi / 2)
        # -pi and +pi are equivalent (same direction); check magnitude
        assert abs(los._angle_diff(0.0, math.pi)) == pytest.approx(math.pi, abs=1e-10)


# ===========================================================================
# Performance — firing arc check latency
# ===========================================================================


class TestPerformance:
    """Verify check_window_firing_arc performance."""

    def test_1000_arc_checks_under_50ms(self) -> None:
        """Verify: 1000 firing arc checks complete in under 50ms."""
        los = _make_los()
        start = time.perf_counter()
        for _ in range(1000):
            los.check_window_firing_arc(5.0, 5.0, 15.0, 5.0, "small_house", 5, 5)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 50.0, f"1000 checks took {elapsed_ms:.1f}ms (expected <50ms)"


# ===========================================================================
# Config — window offset validation
# ===========================================================================


class TestWindowOffsets:
    """Verify window offsets are within valid range."""

    @pytest.mark.parametrize("bt", list(CC2BuildingType))
    def test_window_offsets_in_range(self, bt: CC2BuildingType) -> None:
        """Verify: all window offsets are between 0.0 and 1.0."""
        windows = BUILDING_WINDOWS[bt]
        for w in windows:
            assert 0.0 <= w["offset"] <= 1.0
            assert w["wall"] in ("north", "south", "east", "west")


# ===========================================================================
# Integration — LOS with building shooter
# ===========================================================================


class TestLOSWithBuildingShooter:
    """Verify LOS integration with building window firing arc."""

    def test_shooter_in_building_fires_through_window(self) -> None:
        """Verify: shooter inside building can fire through window direction."""
        from unittest.mock import Mock

        game_map = Mock()
        game_map.width = 30
        game_map.height = 30
        building_terrain = type("T", (), {"name": "building_enterable", "blocks_los": False})()
        game_map.get_terrain = lambda coord: building_terrain
        game_map.get_enhanced_tile = lambda x, y: {
            "building_type": "small_house",
            "building_floors": 2,
        }
        game_map.is_within_bounds = lambda coord: True
        game_map.get_elevation = lambda coord: 0.0
        game_map.get_building_height = lambda coord: 2.0
        los = LOSSystem(game_map)

        from_coord = TileCoord(5, 5)
        to_coord = TileCoord(15, 5)  # due east → east window
        can_see, result = los.check_los(from_coord, to_coord)
        assert can_see
        assert result.status == LosStatus.CLEAR

    def test_angle_diff_wraps_correctly(self) -> None:
        """Verify: angle difference wraps around ±pi correctly."""
        los = _make_los()
        diff = los._angle_diff(3 * math.pi, 0.0)
        assert abs(diff) <= math.pi
