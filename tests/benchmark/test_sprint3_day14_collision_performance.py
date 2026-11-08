"""Performance Tests for Collision Detection - Sprint 3 Day 14 PERF-03.

Benchmarks collision detection performance with varying unit counts.
Target: 100 units < 3ms
"""

import pytest
from pycc2.infrastructure.collision_detection import (
    CollisionDetectionSystem,
    CircleCollider,
)


class TestCollisionDetectionBasics:
    """Basic collision detection tests."""
    
    def test_circle_collider_aabb(self):
        """Test AABB calculation for circle collider."""
        collider = CircleCollider(
            id="test",
            center_x=100.0,
            center_y=200.0,
            radius=50.0,
        )
        
        min_x, min_y, max_x, max_y = collider.aabb()
        
        assert min_x == 50.0
        assert min_y == 150.0
        assert max_x == 150.0
        assert max_y == 250.0
    
    def test_circle_intersects_true(self):
        """Test circle intersection detection (overlapping)."""
        c1 = CircleCollider("c1", 0.0, 0.0, 10.0)
        c2 = CircleCollider("c2", 15.0, 0.0, 10.0)  # Overlaps by 5 units
        
        assert c1.intersects(c2)
        assert c2.intersects(c1)  # Symmetric
    
    def test_circle_intersects_false(self):
        """Test circle intersection detection (non-overlapping)."""
        c1 = CircleCollider("c1", 0.0, 0.0, 10.0)
        c2 = CircleCollider("c2", 50.0, 0.0, 10.0)  # Far apart
        
        assert not c1.intersects(c2)
        assert not c2.intersects(c1)
    
    def test_circle_distance_calculation(self):
        """Test distance between circle centers."""
        c1 = CircleCollider("c1", 0.0, 0.0, 10.0)
        c2 = CircleCollider("c2", 3.0, 4.0, 10.0)  # 3-4-5 triangle
        
        distance = c1.distance_to(c2)
        assert abs(distance - 5.0) < 0.001


class TestCollisionDetectionSystem:
    """Collision detection system tests."""
    
    def test_system_initialization(self):
        """Test system creation with options."""
        system = CollisionDetectionSystem(
            use_spatial_optimization=True,
            grid_cell_size=64,
        )
        
        assert system.use_spatial_optimization
        assert system.grid_cell_size == 64
        assert len(system.colliders) == 0
    
    def test_add_remove_colliders(self):
        """Test adding and removing colliders."""
        system = CollisionDetectionSystem()
        
        c1 = CircleCollider("c1", 0.0, 0.0, 10.0)
        c2 = CircleCollider("c2", 50.0, 0.0, 10.0)
        
        system.add_collider(c1)
        system.add_collider(c2)
        assert len(system.colliders) == 2
        
        system.remove_collider("c1")
        assert len(system.colliders) == 1
        assert system.colliders[0].id == "c2"
        
        system.clear()
        assert len(system.colliders) == 0
    
    def test_naive_collision_detection(self):
        """Test naive O(n²) collision detection."""
        system = CollisionDetectionSystem(use_spatial_optimization=False)
        
        # Two overlapping circles
        system.add_collider(CircleCollider("c1", 0.0, 0.0, 10.0))
        system.add_collider(CircleCollider("c2", 15.0, 0.0, 10.0))
        
        # One separate circle
        system.add_collider(CircleCollider("c3", 100.0, 100.0, 10.0))
        
        collisions = system.detect_collisions_naive()
        
        assert len(collisions) == 1
        assert collisions[0][0].id == "c1"
        assert collisions[0][1].id == "c2"
    
    def test_optimized_collision_detection(self):
        """Test optimized spatial hash collision detection."""
        system = CollisionDetectionSystem(use_spatial_optimization=True)
        
        # Two overlapping circles
        system.add_collider(CircleCollider("c1", 0.0, 0.0, 10.0))
        system.add_collider(CircleCollider("c2", 15.0, 0.0, 10.0))
        
        # One separate circle
        system.add_collider(CircleCollider("c3", 100.0, 100.0, 10.0))
        
        collisions = system.detect_collisions_optimized()
        
        assert len(collisions) == 1
        assert collisions[0][0].id == "c1"
        assert collisions[0][1].id == "c2"
    
    def test_collision_detection_consistency(self):
        """Test naive and optimized methods produce same results."""
        system_naive = CollisionDetectionSystem(use_spatial_optimization=False)
        system_optimized = CollisionDetectionSystem(use_spatial_optimization=True)
        
        # Create same colliders in both systems
        colliders = [
            CircleCollider("c1", 0.0, 0.0, 10.0),
            CircleCollider("c2", 15.0, 0.0, 10.0),
            CircleCollider("c3", 30.0, 0.0, 10.0),
            CircleCollider("c4", 100.0, 100.0, 10.0),
        ]
        
        for c in colliders:
            system_naive.add_collider(c)
            system_optimized.add_collider(c)
        
        collisions_naive = system_naive.detect_collisions()
        collisions_optimized = system_optimized.detect_collisions()
        
        # Compare collision counts
        assert len(collisions_naive) == len(collisions_optimized)
        
        # Extract collision pairs (unordered)
        pairs_naive = {(c1.id, c2.id) for c1, c2 in collisions_naive}
        pairs_optimized = {(c1.id, c2.id) for c1, c2 in collisions_optimized}
        
        assert pairs_naive == pairs_optimized
    
    def test_query_collisions_for_specific_collider(self):
        """Test querying collisions for a specific collider."""
        system = CollisionDetectionSystem()
        
        system.add_collider(CircleCollider("c1", 0.0, 0.0, 10.0))
        system.add_collider(CircleCollider("c2", 15.0, 0.0, 10.0))  # Overlaps c1
        system.add_collider(CircleCollider("c3", 25.0, 0.0, 10.0))  # Overlaps c2
        
        collisions_c1 = system.query_collisions_for("c1")
        collisions_c2 = system.query_collisions_for("c2")
        
        assert len(collisions_c1) == 1
        assert collisions_c1[0].id == "c2"
        
        assert len(collisions_c2) == 2
        assert {c.id for c in collisions_c2} == {"c1", "c3"}
    
    def test_query_point(self):
        """Test point-in-circle queries."""
        system = CollisionDetectionSystem()
        
        system.add_collider(CircleCollider("c1", 0.0, 0.0, 10.0))
        system.add_collider(CircleCollider("c2", 50.0, 0.0, 10.0))
        
        # Point inside c1
        results = system.query_point(5.0, 0.0)
        assert len(results) == 1
        assert results[0].id == "c1"
        
        # Point outside all circles
        results = system.query_point(100.0, 100.0)
        assert len(results) == 0
    
    def test_query_radius(self):
        """Test radius query."""
        system = CollisionDetectionSystem()
        
        system.add_collider(CircleCollider("c1", 0.0, 0.0, 10.0))
        system.add_collider(CircleCollider("c2", 50.0, 0.0, 10.0))
        system.add_collider(CircleCollider("c3", 100.0, 0.0, 10.0))
        
        # Query near c1 (should find c1 and c2)
        results = system.query_radius(center_x=20.0, center_y=0.0, radius=50.0)
        assert len(results) == 2
        assert {c.id for c in results} == {"c1", "c2"}
    
    def test_no_collisions(self):
        """Test case with no collisions."""
        system = CollisionDetectionSystem()
        
        # Widely spaced circles
        system.add_collider(CircleCollider("c1", 0.0, 0.0, 10.0))
        system.add_collider(CircleCollider("c2", 100.0, 0.0, 10.0))
        system.add_collider(CircleCollider("c3", 0.0, 100.0, 10.0))
        
        collisions = system.detect_collisions()
        assert len(collisions) == 0
    
    def test_multiple_collisions(self):
        """Test case with multiple collision pairs."""
        system = CollisionDetectionSystem()
        
        # Cluster of overlapping circles
        system.add_collider(CircleCollider("c1", 0.0, 0.0, 15.0))
        system.add_collider(CircleCollider("c2", 10.0, 0.0, 15.0))
        system.add_collider(CircleCollider("c3", 20.0, 0.0, 15.0))
        system.add_collider(CircleCollider("c4", 10.0, 10.0, 15.0))
        
        collisions = system.detect_collisions()
        
        # All 4 circles should have multiple overlaps
        assert len(collisions) >= 4  # At least 4 collision pairs


class TestCollisionPerformance:
    """Performance benchmarks for collision detection."""
    
    @pytest.mark.benchmark(group="collision")
    def test_collision_detection_10_units(self, benchmark):
        """Benchmark collision detection with 10 units."""
        system = CollisionDetectionSystem(use_spatial_optimization=True)
        
        # Create 10 units in a grid
        for i in range(10):
            system.add_collider(
                CircleCollider(f"unit{i}", i * 20.0, 0.0, 10.0)
            )
        
        result = benchmark(system.detect_collisions)
        assert isinstance(result, list)
    
    @pytest.mark.benchmark(group="collision")
    def test_collision_detection_50_units(self, benchmark):
        """Benchmark collision detection with 50 units."""
        system = CollisionDetectionSystem(use_spatial_optimization=True)
        
        # Create 50 units in a grid
        for i in range(50):
            x = (i % 10) * 20.0
            y = (i // 10) * 20.0
            system.add_collider(CircleCollider(f"unit{i}", x, y, 10.0))
        
        result = benchmark(system.detect_collisions)
        assert isinstance(result, list)
    
    @pytest.mark.benchmark(group="collision")
    def test_collision_detection_100_units_optimized(self, benchmark):
        """Benchmark collision detection with 100 units (optimized).
        
        Target: < 3ms per detection cycle
        """
        system = CollisionDetectionSystem(use_spatial_optimization=True)
        
        # Create 100 units in a 10x10 grid
        for i in range(100):
            x = (i % 10) * 30.0
            y = (i // 10) * 30.0
            system.add_collider(CircleCollider(f"unit{i}", x, y, 10.0))
        
        result = benchmark(system.detect_collisions)
        assert isinstance(result, list)
        
        # Note: Performance verified by benchmark output (Mean column)
        # Target: < 3ms = 3000us
    
    @pytest.mark.benchmark(group="collision")
    def test_collision_detection_100_units_naive(self, benchmark):
        """Benchmark collision detection with 100 units (naive) for comparison."""
        system = CollisionDetectionSystem(use_spatial_optimization=False)
        
        # Create 100 units in a 10x10 grid
        for i in range(100):
            x = (i % 10) * 30.0
            y = (i // 10) * 30.0
            system.add_collider(CircleCollider(f"unit{i}", x, y, 10.0))
        
        result = benchmark(system.detect_collisions)
        assert isinstance(result, list)
    
    @pytest.mark.benchmark(group="collision")
    def test_collision_detection_200_units(self, benchmark):
        """Benchmark collision detection with 200 units (stress test)."""
        system = CollisionDetectionSystem(use_spatial_optimization=True)
        
        # Create 200 units in a larger grid
        for i in range(200):
            x = (i % 20) * 30.0
            y = (i // 20) * 30.0
            system.add_collider(CircleCollider(f"unit{i}", x, y, 10.0))
        
        result = benchmark(system.detect_collisions)
        assert isinstance(result, list)
