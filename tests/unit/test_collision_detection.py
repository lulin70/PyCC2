"""Unit tests for the two-phase collision detection system."""

from __future__ import annotations

import math

import pytest

from pycc2.infrastructure.collision_detection import (
    CircleCollider,
    CollisionDetectionSystem,
)


def _c(collider_id: str, x: float, y: float, radius: float = 10.0) -> CircleCollider:
    return CircleCollider(id=collider_id, center_x=x, center_y=y, radius=radius)


# ===========================================================================
# CircleCollider
# ===========================================================================


@pytest.mark.unit
class TestCircleCollider:
    def test_aabb(self):
        collider = _c("a", 50.0, 60.0, 10.0)
        assert collider.aabb() == (40.0, 50.0, 60.0, 70.0)

    def test_aabb_with_zero_radius(self):
        collider = _c("a", 5.0, 7.0, 0.0)
        assert collider.aabb() == (5.0, 7.0, 5.0, 7.0)

    def test_intersects_overlapping_circles(self):
        assert _c("a", 0, 0, 10).intersects(_c("b", 5, 0, 10)) is True

    def test_intersects_same_center(self):
        assert _c("a", 0, 0, 10).intersects(_c("b", 0, 0, 1)) is True

    def test_touching_circles_do_not_intersect(self):
        # Strict inequality: exactly tangent distance is not a collision.
        assert _c("a", 0, 0, 10).intersects(_c("b", 20, 0, 10)) is False

    def test_separate_circles_do_not_intersect(self):
        assert _c("a", 0, 0, 5).intersects(_c("b", 100, 100, 5)) is False

    def test_intersects_is_symmetric(self):
        first = _c("a", 0, 0, 10)
        second = _c("b", 7, 7, 10)
        assert first.intersects(second) == second.intersects(first)

    def test_distance_to(self):
        assert _c("a", 0, 0).distance_to(_c("b", 3, 4)) == pytest.approx(5.0)

    def test_distance_to_self_is_zero(self):
        collider = _c("a", 12.0, -8.0)
        assert collider.distance_to(collider) == pytest.approx(0.0)

    def test_distance_to_uses_center_only(self):
        # Radii are ignored by distance_to.
        assert _c("a", 0, 0, 50).distance_to(_c("b", 6, 8, 1)) == pytest.approx(10.0)
        assert _c("a", 0, 0).distance_to(_c("b", 6, 8)) == pytest.approx(math.hypot(6, 8))


# ===========================================================================
# Collider management
# ===========================================================================


@pytest.mark.unit
class TestColliderManagement:
    def test_add_collider(self):
        system = CollisionDetectionSystem()
        collider = _c("a", 0, 0)

        system.add_collider(collider)

        assert system.colliders == [collider]

    def test_remove_existing_collider(self):
        system = CollisionDetectionSystem()
        system.add_collider(_c("a", 0, 0))
        system.add_collider(_c("b", 100, 100))

        assert system.remove_collider("a") is True
        assert [c.id for c in system.colliders] == ["b"]

    def test_remove_unknown_collider_returns_false(self):
        system = CollisionDetectionSystem()
        system.add_collider(_c("a", 0, 0))

        assert system.remove_collider("missing") is False
        assert len(system.colliders) == 1

    def test_remove_from_empty_system(self):
        assert CollisionDetectionSystem().remove_collider("a") is False

    def test_clear_removes_colliders(self):
        system = CollisionDetectionSystem()
        system.add_collider(_c("a", 0, 0))

        system.clear()

        assert system.colliders == []


# ===========================================================================
# Naive detection
# ===========================================================================


@pytest.mark.unit
class TestNaiveDetection:
    def test_empty_system(self):
        assert CollisionDetectionSystem().detect_collisions_naive() == []

    def test_single_collider_has_no_pairs(self):
        system = CollisionDetectionSystem()
        system.add_collider(_c("a", 0, 0))
        assert system.detect_collisions_naive() == []

    def test_overlapping_pair_detected(self):
        system = CollisionDetectionSystem()
        first = _c("a", 0, 0, 10)
        second = _c("b", 5, 0, 10)
        system.add_collider(first)
        system.add_collider(second)

        assert system.detect_collisions_naive() == [(first, second)]

    def test_non_overlapping_pair_not_detected(self):
        system = CollisionDetectionSystem()
        system.add_collider(_c("a", 0, 0))
        system.add_collider(_c("b", 500, 500))

        assert system.detect_collisions_naive() == []

    def test_multiple_pairs_order_follows_index_order(self):
        system = CollisionDetectionSystem()
        first = _c("a", 0, 0, 10)
        second = _c("b", 5, 0, 10)
        third = _c("c", 10, 0, 10)
        for collider in (first, second, third):
            system.add_collider(collider)

        assert system.detect_collisions_naive() == [
            (first, second),
            (first, third),
            (second, third),
        ]


# ===========================================================================
# Optimized detection
# ===========================================================================


@pytest.mark.unit
class TestOptimizedDetection:
    def test_empty_system(self):
        assert CollisionDetectionSystem().detect_collisions_optimized() == []

    def test_single_collider_has_no_pairs(self):
        system = CollisionDetectionSystem()
        system.add_collider(_c("a", 0, 0))
        assert system.detect_collisions_optimized() == []

    def test_matches_naive_results(self):
        system = CollisionDetectionSystem(grid_cell_size=32)
        colliders = [
            _c("a", 0, 0, 10),
            _c("b", 5, 0, 10),
            _c("c", 200, 200, 10),
            _c("d", 205, 205, 10),
            _c("e", 1000, 1000, 10),
        ]
        for collider in colliders:
            system.add_collider(collider)

        naive = {tuple(sorted((c1.id, c2.id))) for c1, c2 in system.detect_collisions_naive()}
        optimized = {
            tuple(sorted((c1.id, c2.id))) for c1, c2 in system.detect_collisions_optimized()
        }

        assert optimized == naive == {("a", "b"), ("c", "d")}

    def test_pair_spanning_multiple_cells_reported_once(self):
        # Large radii force each collider into several grid cells, so the
        # same pair is visited more than once during narrow phase.
        system = CollisionDetectionSystem(grid_cell_size=16)
        first = _c("a", 50, 50, 60)
        second = _c("b", 60, 60, 60)
        system.add_collider(first)
        system.add_collider(second)

        assert system.detect_collisions_optimized() == [(first, second)]

    def test_large_radius_grows_cell_size(self):
        system = CollisionDetectionSystem(grid_cell_size=8)
        first = _c("a", 0, 0, 100)
        second = _c("b", 10, 10, 100)
        system.add_collider(first)
        system.add_collider(second)

        assert system.detect_collisions_optimized() == [(first, second)]

    def test_pair_in_same_cell_without_intersection_is_not_reported(self):
        system = CollisionDetectionSystem(grid_cell_size=64)
        system.add_collider(_c("a", 10, 10, 5))
        system.add_collider(_c("b", 50, 50, 5))

        assert system.detect_collisions_optimized() == []

    def test_negative_coordinates_supported(self):
        system = CollisionDetectionSystem(grid_cell_size=64)
        first = _c("a", -50, -50, 10)
        second = _c("b", -45, -45, 10)
        system.add_collider(first)
        system.add_collider(second)

        assert system.detect_collisions_optimized() == [(first, second)]


# ===========================================================================
# Dispatch
# ===========================================================================


@pytest.mark.unit
class TestDetectCollisionsDispatch:
    def test_uses_optimized_when_enabled(self, monkeypatch):
        system = CollisionDetectionSystem(use_spatial_optimization=True)
        called = []
        monkeypatch.setattr(
            system, "detect_collisions_optimized", lambda: called.append("optimized") or []
        )
        monkeypatch.setattr(system, "detect_collisions_naive", lambda: called.append("naive") or [])

        assert system.detect_collisions() == []
        assert called == ["optimized"]

    def test_uses_naive_when_disabled(self, monkeypatch):
        system = CollisionDetectionSystem(use_spatial_optimization=False)
        called = []
        monkeypatch.setattr(
            system, "detect_collisions_optimized", lambda: called.append("optimized") or []
        )
        monkeypatch.setattr(system, "detect_collisions_naive", lambda: called.append("naive") or [])

        assert system.detect_collisions() == []
        assert called == ["naive"]


# ===========================================================================
# Queries
# ===========================================================================


@pytest.mark.unit
class TestQueries:
    def test_query_collisions_for_returns_overlaps(self):
        system = CollisionDetectionSystem()
        target = _c("target", 0, 0, 10)
        near = _c("near", 5, 0, 10)
        far = _c("far", 500, 500, 10)
        for collider in (target, near, far):
            system.add_collider(collider)

        assert system.query_collisions_for("target") == [near]

    def test_query_collisions_for_unknown_id(self):
        system = CollisionDetectionSystem()
        system.add_collider(_c("a", 0, 0))
        assert system.query_collisions_for("missing") == []

    def test_query_collisions_for_isolated_collider(self):
        system = CollisionDetectionSystem()
        system.add_collider(_c("a", 0, 0, 10))
        system.add_collider(_c("b", 500, 500, 10))
        assert system.query_collisions_for("a") == []

    def test_query_point_inside(self):
        system = CollisionDetectionSystem()
        collider = _c("a", 10, 10, 5)
        system.add_collider(collider)

        assert system.query_point(12, 12) == [collider]

    def test_query_point_on_boundary_is_inclusive(self):
        system = CollisionDetectionSystem()
        collider = _c("a", 0, 0, 5)
        system.add_collider(collider)

        assert system.query_point(5, 0) == [collider]

    def test_query_point_outside(self):
        system = CollisionDetectionSystem()
        system.add_collider(_c("a", 0, 0, 5))
        assert system.query_point(50, 50) == []

    def test_query_point_returns_all_containing_colliders(self):
        system = CollisionDetectionSystem()
        first = _c("a", 0, 0, 10)
        second = _c("b", 2, 2, 10)
        system.add_collider(first)
        system.add_collider(second)

        assert system.query_point(1, 1) == [first, second]

    def test_query_radius_within(self):
        system = CollisionDetectionSystem()
        center_collider = _c("a", 0, 0, 1)
        nearby = _c("b", 10, 0, 1)
        far = _c("c", 100, 0, 1)
        for collider in (center_collider, nearby, far):
            system.add_collider(collider)

        assert system.query_radius(0, 0, 12) == [center_collider, nearby]

    def test_query_radius_includes_collider_extent(self):
        system = CollisionDetectionSystem()
        collider = _c("a", 10, 0, 5)
        system.add_collider(collider)

        # Distance 10 <= query radius 5 + collider radius 5.
        assert system.query_radius(0, 0, 5) == [collider]

    def test_query_radius_boundary_is_inclusive(self):
        system = CollisionDetectionSystem()
        collider = _c("a", 10, 0, 0)
        system.add_collider(collider)

        assert system.query_radius(0, 0, 10) == [collider]

    def test_query_radius_zero_returns_only_containing(self):
        system = CollisionDetectionSystem()
        inside = _c("a", 0, 0, 5)
        outside = _c("b", 10, 0, 1)
        system.add_collider(inside)
        system.add_collider(outside)

        assert system.query_radius(0, 0, 0) == [inside]

    def test_query_radius_empty_system(self):
        assert CollisionDetectionSystem().query_radius(0, 0, 100) == []


# ===========================================================================
# Statistics
# ===========================================================================


@pytest.mark.unit
class TestStatistics:
    def test_statistics_report_configuration(self):
        system = CollisionDetectionSystem(use_spatial_optimization=False, grid_cell_size=48)
        system.add_collider(_c("a", 0, 0))
        system.add_collider(_c("b", 10, 0))

        assert system.get_statistics() == {
            "total_colliders": 2,
            "use_spatial_optimization": False,
            "grid_cell_size": 48,
        }

    def test_statistics_on_empty_system(self):
        assert CollisionDetectionSystem().get_statistics()["total_colliders"] == 0
