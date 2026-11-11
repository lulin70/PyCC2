"""Sprint 3 Day 12 Tests - BUG-P1-03 Unit Avoidance System.

Tests for:
- Unit collision detection
- Avoidance velocity calculation
- Multi-unit movement without blocking
"""

import pytest

from pycc2.domain.systems.unit_avoidance_system import (
    SimpleUnit,
    UnitAvoidanceSystem,
    Vec2Simple,
)


class TestUnitAvoidanceSystemCollision:
    """Test collision detection."""

    def test_detect_collisions_no_overlap(self):
        """Test no collisions when units are separated."""
        avoidance = UnitAvoidanceSystem()
        units = [
            SimpleUnit("u1", Vec2Simple(0.0, 0.0), Vec2Simple(0.0, 0.0), radius=16.0),
            SimpleUnit("u2", Vec2Simple(100.0, 0.0), Vec2Simple(0.0, 0.0), radius=16.0),
        ]

        collisions = avoidance.detect_collisions(units)
        assert len(collisions) == 0

    def test_detect_collisions_overlap(self):
        """Test collision detection when units overlap."""
        avoidance = UnitAvoidanceSystem()
        units = [
            SimpleUnit("u1", Vec2Simple(0.0, 0.0), Vec2Simple(0.0, 0.0), radius=16.0),
            SimpleUnit("u2", Vec2Simple(20.0, 0.0), Vec2Simple(0.0, 0.0), radius=16.0),
        ]

        collisions = avoidance.detect_collisions(units)
        assert len(collisions) == 1
        assert ("u1", "u2") in collisions or ("u2", "u1") in collisions

    def test_detect_multiple_collisions(self):
        """Test detecting multiple collisions."""
        avoidance = UnitAvoidanceSystem()
        units = [
            SimpleUnit("u1", Vec2Simple(0.0, 0.0), Vec2Simple(0.0, 0.0), radius=16.0),
            SimpleUnit("u2", Vec2Simple(20.0, 0.0), Vec2Simple(0.0, 0.0), radius=16.0),
            SimpleUnit("u3", Vec2Simple(10.0, 10.0), Vec2Simple(0.0, 0.0), radius=16.0),
        ]

        collisions = avoidance.detect_collisions(units)
        assert len(collisions) >= 2  # u1-u2, u1-u3, u2-u3


class TestUnitAvoidanceSystemAvoidance:
    """Test avoidance velocity calculation."""

    def test_avoidance_velocity_no_neighbors(self):
        """Test no avoidance when no neighbors."""
        avoidance = UnitAvoidanceSystem()
        unit = SimpleUnit("u1", Vec2Simple(0.0, 0.0), Vec2Simple(10.0, 0.0), radius=16.0)

        avoidance_vel = avoidance.calculate_avoidance_velocity(unit, [])
        assert avoidance_vel.x == 0.0
        assert avoidance_vel.y == 0.0

    def test_avoidance_velocity_single_neighbor(self):
        """Test avoidance away from single neighbor."""
        avoidance = UnitAvoidanceSystem()
        unit = SimpleUnit("u1", Vec2Simple(0.0, 0.0), Vec2Simple(10.0, 0.0), radius=16.0)
        neighbor = SimpleUnit("u2", Vec2Simple(30.0, 0.0), Vec2Simple(10.0, 0.0), radius=16.0)

        avoidance_vel = avoidance.calculate_avoidance_velocity(unit, [neighbor])

        # Should push away from neighbor (negative x direction)
        assert avoidance_vel.x < 0.0
        assert abs(avoidance_vel.y) < 0.1  # Minimal y component

    def test_avoidance_velocity_multiple_neighbors(self):
        """Test avoidance with multiple neighbors."""
        avoidance = UnitAvoidanceSystem()
        unit = SimpleUnit("u1", Vec2Simple(0.0, 0.0), Vec2Simple(10.0, 0.0), radius=16.0)
        neighbors = [
            SimpleUnit("u2", Vec2Simple(30.0, 0.0), Vec2Simple(10.0, 0.0), radius=16.0),
            SimpleUnit("u3", Vec2Simple(0.0, 30.0), Vec2Simple(0.0, 10.0), radius=16.0),
        ]

        avoidance_vel = avoidance.calculate_avoidance_velocity(unit, neighbors)

        # Should have both x and y components (away from both neighbors)
        assert avoidance_vel.x < 0.0
        assert avoidance_vel.y < 0.0


class TestUnitAvoidanceSystemIntegration:
    """Test integrated avoidance + movement."""

    def test_update_moves_units(self):
        """Test update moves units with avoidance."""
        avoidance = UnitAvoidanceSystem()
        units = [
            SimpleUnit("u1", Vec2Simple(0.0, 0.0), Vec2Simple(10.0, 0.0), radius=16.0),
            SimpleUnit("u2", Vec2Simple(30.0, 0.0), Vec2Simple(-10.0, 0.0), radius=16.0),
        ]

        initial_pos_u1 = units[0].position.x

        avoidance.update(units, delta_time=0.1)

        # Position should change (moved by velocity + avoidance)
        assert units[0].position.x != initial_pos_u1

    def test_apply_velocity_moves_unit(self):
        """Test apply_velocity updates position."""
        avoidance = UnitAvoidanceSystem()
        unit = SimpleUnit("u1", Vec2Simple(0.0, 0.0), Vec2Simple(100.0, 0.0), radius=16.0)

        avoidance.apply_velocity(unit, delta_time=0.1)

        # Position should move by velocity * dt
        assert abs(unit.position.x - 10.0) < 0.1
        assert abs(unit.position.y - 0.0) < 0.1

    def test_10_units_no_deadlock(self):
        """Test 10 units moving together without deadlock (BUG-P1-03 validation)."""
        avoidance = UnitAvoidanceSystem()

        # Create 10 units in a tight grid
        units = []
        for i in range(10):
            units.append(
                SimpleUnit(
                    f"u{i}",
                    Vec2Simple(i * 20.0, 0.0),
                    Vec2Simple(50.0, 10.0),  # All moving in same direction
                    radius=16.0,
                )
            )

        # Update for 100 frames (simulate 1.6 seconds @ 60fps)
        for frame in range(100):
            avoidance.update(units, delta_time=0.016)

        # All units should have moved forward
        for unit in units:
            assert unit.position.x > 20.0, f"Unit {unit.id} did not move"

        # No units should be stuck at initial position
        for i, unit in enumerate(units):
            initial_x = i * 20.0
            assert unit.position.x > initial_x + 10.0, f"Unit {unit.id} barely moved"


class TestUnitAvoidanceSystemPerformance:
    """Test performance with many units."""

    @pytest.mark.timing
    def test_performance_100_units(self):
        """Test updating 100 units runs fast enough."""
        import time

        avoidance = UnitAvoidanceSystem()

        # Create 100 units in a 10x10 grid
        units = []
        for i in range(10):
            for j in range(10):
                units.append(
                    SimpleUnit(
                        f"u{i}_{j}",
                        Vec2Simple(i * 50.0, j * 50.0),
                        Vec2Simple(10.0, 10.0),
                        radius=16.0,
                    )
                )

        # Benchmark single update
        start_time = time.perf_counter()
        avoidance.update(units, delta_time=0.016)
        elapsed = time.perf_counter() - start_time

        # Should update 100 units in <10ms (target for 60fps stability)
        assert elapsed < 0.01, f"Update took {elapsed * 1000:.2f}ms (target: <10ms)"


class TestVec2Simple:
    """Test Vec2Simple utility class."""

    def test_vec2_length(self):
        """Test vector magnitude calculation."""
        v = Vec2Simple(3.0, 4.0)
        assert abs(v.length() - 5.0) < 0.01

    def test_vec2_normalize(self):
        """Test vector normalization."""
        v = Vec2Simple(3.0, 4.0)
        normalized = v.normalize()
        assert abs(normalized.length() - 1.0) < 0.01

    def test_vec2_operations(self):
        """Test vector arithmetic operations."""
        v1 = Vec2Simple(1.0, 2.0)
        v2 = Vec2Simple(3.0, 4.0)

        # Addition
        v_add = v1 + v2
        assert v_add.x == 4.0
        assert v_add.y == 6.0

        # Subtraction
        v_sub = v2 - v1
        assert v_sub.x == 2.0
        assert v_sub.y == 2.0

        # Scalar multiplication
        v_mul = v1 * 2.0
        assert v_mul.x == 2.0
        assert v_mul.y == 4.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
