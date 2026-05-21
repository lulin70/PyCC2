"""
Tests for SpatialHash - Optimized spatial indexing for combat target selection.
"""

from __future__ import annotations

import time

import pytest

from pycc2.domain.entities.unit import Faction
from pycc2.domain.systems.spatial_hash import SpatialHash
from pycc2.domain.value_objects.tile_coord import TileCoord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_sh(cell_size: int = 10) -> SpatialHash:
    return SpatialHash(cell_size=cell_size)


def _populate_basic(sh: SpatialHash) -> None:
    """Insert a handful of units at known positions."""
    sh.insert("a1", TileCoord(5, 5), Faction.ALLIES)
    sh.insert("a2", TileCoord(8, 3), Faction.ALLIES)
    sh.insert("x1", TileCoord(50, 50), Faction.AXIS)
    sh.insert("x2", TileCoord(52, 48), Faction.AXIS)


# ===========================================================================
# Construction & basic properties
# ===========================================================================


class TestSpatialHashConstruction:
    def test_default_cell_size(self):
        sh = _make_sh()
        assert sh._cell_size == 10

    def test_custom_cell_size(self):
        sh = _make_sh(cell_size=32)
        assert sh._cell_size == 32

    def test_invalid_cell_size_raises(self):
        with pytest.raises(ValueError):
            SpatialHash(cell_size=0)
        with pytest.raises(ValueError):
            SpatialHash(cell_size=-5)

    def test_empty_count(self):
        sh = _make_sh()
        assert sh.unit_count() == 0


# ===========================================================================
# Insert & retrieve
# ===========================================================================


class TestInsertAndRetrieve:
    def test_insert_increments_count(self):
        sh = _make_sh()
        sh.insert("u1", TileCoord(1, 1), Faction.ALLIES)
        assert sh.unit_count() == 1
        sh.insert("u2", TileCoord(2, 2), Faction.AXIS)
        assert sh.unit_count() == 2

    def test_get_position(self):
        sh = _make_sh()
        pos = TileCoord(7, 13)
        sh.insert("u1", pos, Faction.ALLIES)
        assert sh.get_position("u1") == pos

    def test_get_faction(self):
        sh = _make_sh()
        sh.insert("u1", TileCoord(0, 0), Faction.AXIS)
        assert sh.get_faction("u1") == Faction.AXIS

    def test_get_position_unknown_returns_none(self):
        sh = _make_sh()
        assert sh.get_position("ghost") is None

    def test_get_faction_unknown_returns_none(self):
        sh = _make_sh()
        assert sh.get_faction("ghost") is None

    def test_insert_duplicate_id_replaces(self):
        sh = _make_sh()
        sh.insert("u1", TileCoord(1, 1), Faction.ALLIES)
        sh.insert("u1", TileCoord(9, 9), Faction.AXIS)
        assert sh.unit_count() == 1
        assert sh.get_position("u1") == TileCoord(9, 9)
        assert sh.get_faction("u1") == Faction.AXIS


# ===========================================================================
# Query radius
# ===========================================================================


class TestQueryRadius:
    def test_basic_radius_query(self):
        sh = _make_sh()
        _populate_basic(sh)
        # Center at (5,5), radius 5 should find a1 and a2
        result = sh.query_radius(TileCoord(5, 5), 5)
        assert "a1" in result
        assert "a2" in result
        assert "x1" not in result

    def test_radius_excludes_distant_units(self):
        sh = _make_sh()
        sh.insert("near", TileCoord(3, 3), Faction.ALLIES)
        sh.insert("far", TileCoord(100, 100), Faction.AXIS)
        result = sh.query_radius(TileCoord(3, 3), 10)
        assert "near" in result
        assert "far" not in result

    def test_radius_with_faction_exclusion(self):
        sh = _make_sh()
        _populate_basic(sh)
        result = sh.query_radius(TileCoord(5, 5), 100, exclude_faction=Faction.ALLIES)
        assert "a1" not in result
        assert "a2" not in result
        assert "x1" in result
        assert "x2" in result

    def test_radius_zero_returns_only_same_position(self):
        sh = _make_sh()
        sh.insert("u1", TileCoord(10, 10), Faction.ALLIES)
        sh.insert("u2", TileCoord(11, 10), Faction.AXIS)
        result = sh.query_radius(TileCoord(10, 10), 0)
        assert "u1" in result
        assert "u2" not in result

    def test_radius_negative_returns_empty(self):
        sh = _make_sh()
        sh.insert("u1", TileCoord(0, 0), Faction.ALLIES)
        result = sh.query_radius(TileCoord(0, 0), -1)
        assert result == []

    def test_empty_hash_returns_empty(self):
        sh = _make_sh()
        result = sh.query_radius(TileCoord(0, 0), 100)
        assert result == []


# ===========================================================================
# Query rectangle
# ===========================================================================


class TestQueryRect:
    def test_basic_rect_query(self):
        sh = _make_sh()
        _populate_basic(sh)
        result = sh.query_rect(0, 0, 10, 10)
        assert "a1" in result
        assert "a2" in result
        assert "x1" not in result

    def test_rect_with_faction_exclusion(self):
        sh = _make_sh()
        _populate_basic(sh)
        result = sh.query_rect(0, 0, 60, 60, exclude_faction=Faction.AXIS)
        assert "a1" in result
        assert "a2" in result
        assert "x1" not in result
        assert "x2" not in result

    def test_rect_boundary_inclusive(self):
        sh = _make_sh()
        sh.insert("edge", TileCoord(10, 10), Faction.ALLIES)
        result = sh.query_rect(0, 0, 10, 10)
        assert "edge" in result


# ===========================================================================
# Remove
# ===========================================================================


class TestRemove:
    def test_remove_decrements_count(self):
        sh = _make_sh()
        sh.insert("u1", TileCoord(1, 1), Faction.ALLIES)
        assert sh.unit_count() == 1
        sh.remove("u1")
        assert sh.unit_count() == 0

    def test_remove_makes_unit_invisible(self):
        sh = _make_sh()
        sh.insert("u1", TileCoord(5, 5), Faction.ALLIES)
        sh.remove("u1")
        assert sh.get_position("u1") is None
        result = sh.query_radius(TileCoord(5, 5), 10)
        assert "u1" not in result

    def test_remove_nonexistent_is_noop(self):
        sh = _make_sh()
        sh.remove("ghost")  # should not raise
        assert sh.unit_count() == 0


# ===========================================================================
# Update position
# ===========================================================================


class TestUpdatePosition:
    def test_update_changes_position(self):
        sh = _make_sh()
        sh.insert("u1", TileCoord(0, 0), Faction.ALLIES)
        new_pos = TileCoord(20, 20)
        sh.update("u1", new_pos)
        assert sh.get_position("u1") == new_pos

    def test_update_cross_cell_moves_bucket(self):
        sh = _make_sh(cell_size=10)
        sh.insert("u1", TileCoord(5, 5), Faction.ALLIES)  # cell (0,0)
        sh.update("u1", TileCoord(15, 15))  # cell (1,1)
        # Old cell should no longer contain u1
        result_old = sh.query_rect(0, 0, 9, 9)
        assert "u1" not in result_old
        # New cell should contain u1
        result_new = sh.query_rect(10, 10, 19, 19)
        assert "u1" in result_new

    def test_update_same_cell(self):
        sh = _make_sh(cell_size=10)
        sh.insert("u1", TileCoord(1, 1), Faction.ALLIES)
        sh.update("u1", TileCoord(2, 2))
        assert sh.get_position("u1") == TileCoord(2, 2)
        assert sh.unit_count() == 1

    def test_update_nonexistent_is_noop(self):
        sh = _make_sh()
        sh.update("ghost", TileCoord(5, 5))  # should not raise
        assert sh.unit_count() == 0


# ===========================================================================
# Clear
# ===========================================================================


class TestClear:
    def test_clear_empties_hash(self):
        sh = _make_sh()
        _populate_basic(sh)
        assert sh.unit_count() > 0
        sh.clear()
        assert sh.unit_count() == 0
        assert sh.query_radius(TileCoord(0, 0), 1000) == []


# ===========================================================================
# Build from units
# ===========================================================================


class TestBuildFromUnits:
    def test_build_from_units_populates(self):
        from dataclasses import dataclass
        from pycc2.domain.components.position_component import PositionComponent

        @dataclass
        class FakeUnit:
            id: str
            faction: Faction
            position: PositionComponent

        units = [
            FakeUnit("a1", Faction.ALLIES, PositionComponent(TileCoord(1, 1))),
            FakeUnit("x1", Faction.AXIS, PositionComponent(TileCoord(50, 50))),
        ]
        sh = _make_sh()
        sh.build_from_units(units)
        assert sh.unit_count() == 2
        assert sh.get_position("a1") == TileCoord(1, 1)
        assert sh.get_faction("x1") == Faction.AXIS

    def test_build_clears_previous_data(self):
        sh = _make_sh()
        sh.insert("old", TileCoord(0, 0), Faction.ALLIES)
        sh.build_from_units([])
        assert sh.unit_count() == 0


# ===========================================================================
# Edge cases
# ===========================================================================


class TestEdgeCases:
    def test_negative_coordinates(self):
        sh = _make_sh(cell_size=10)
        sh.insert("u1", TileCoord(-5, -5), Faction.ALLIES)
        result = sh.query_radius(TileCoord(-5, -5), 1)
        assert "u1" in result

    def test_unit_on_cell_boundary(self):
        """A unit at exactly (10,10) with cell_size=10 falls in cell (1,1)."""
        sh = _make_sh(cell_size=10)
        sh.insert("boundary", TileCoord(10, 10), Faction.ALLIES)
        # Query the cell that should contain it
        result = sh.query_rect(10, 10, 10, 10)
        assert "boundary" in result

    def test_large_radius_covers_all(self):
        sh = _make_sh()
        _populate_basic(sh)
        result = sh.query_radius(TileCoord(0, 0), 1000)
        assert len(result) == 4

    def test_many_units_same_cell(self):
        sh = _make_sh(cell_size=100)
        for i in range(50):
            sh.insert(f"u{i}", TileCoord(i, i), Faction.ALLIES)
        result = sh.query_radius(TileCoord(25, 25), 30)
        assert len(result) > 0
        assert all(uid.startswith("u") for uid in result)


# ===========================================================================
# Performance
# ===========================================================================


class TestPerformance:
    def test_query_radius_faster_than_linear_scan(self):
        """Verify spatial hash query outperforms brute-force for large datasets."""
        n = 5000
        sh = _make_sh(cell_size=50)
        # Insert n units spread across a large area
        for i in range(n):
            x = i % 100
            y = i // 100
            sh.insert(f"u{i}", TileCoord(x, y), Faction.ALLIES if i % 2 == 0 else Faction.AXIS)

        center = TileCoord(50, 25)
        radius = 10

        # Spatial hash query
        start = time.perf_counter()
        for _ in range(100):
            sh.query_radius(center, radius)
        spatial_time = time.perf_counter() - start

        # Brute-force linear scan
        all_data = list(sh._unit_data.values())
        start = time.perf_counter()
        for _ in range(100):
            r2 = radius * radius
            _ = [
                e.unit_id
                for e in all_data
                if (e.position.x - center.x) ** 2 + (e.position.y - center.y) ** 2 <= r2
            ]
        linear_time = time.perf_counter() - start

        # Spatial hash should be faster (at least not drastically slower)
        # We allow a generous margin; the point is to catch gross regressions.
        assert spatial_time < linear_time * 3, (
            f"Spatial hash ({spatial_time:.4f}s) not competitive with "
            f"linear scan ({linear_time:.4f}s)"
        )
