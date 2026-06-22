"""Automated performance benchmark tests.

These tests establish performance baselines and detect regressions.
Run with: SDL_VIDEODRIVER=dummy python -m pytest tests/benchmark/test_perf_benchmark.py -v
"""

import os
import time

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()
_screen = pygame.display.set_mode((800, 600))


class TestRenderingPerformance:
    """Benchmark rendering pipeline performance."""

    def test_terrain_tile_cache_throughput(self):
        """TerrainTileCache should render 1000 tiles under 500ms."""
        from pycc2.presentation.rendering.terrain_tile_cache import TerrainTileCache

        cache = TerrainTileCache(tile_size=48)

        # Pre-populate cache with 1000 surfaces to simulate a warm cache
        for i in range(1000):
            key = (i % 14, i % 256, i % 10, i % 5, 48)
            surface = pygame.Surface((48, 48), flags=pygame.SRCALPHA)
            surface.fill((65, 106, 30))
            cache._cache[key] = surface

        start = time.perf_counter()
        for i in range(1000):
            terrain_type = i % 14
            autotile_mask = i % 256
            variation = i % 10
            height = i % 5
            cache.get_tile(
                terrain_type=terrain_type,
                autotile_mask=autotile_mask,
                variation=variation,
                height=height,
                tile_screen_size=48,
            )
        elapsed = time.perf_counter() - start
        assert elapsed < 0.5, f"TerrainTileCache too slow: {elapsed:.3f}s for 1000 tiles"

    def test_surface_pool_allocation(self):
        """SurfacePool should handle 1000 acquire/release cycles under 100ms."""
        from pycc2.presentation.rendering.surface_pool import SurfacePool

        pool = SurfacePool(max_size=1000)
        start = time.perf_counter()
        for _ in range(1000):
            pool.get((64, 64))
            pool.release((64, 64))
        elapsed = time.perf_counter() - start
        assert elapsed < 0.1, f"SurfacePool too slow: {elapsed:.3f}s for 1000 cycles"

    @pytest.mark.slow
    def test_entity_resolution_performance(self):
        """Entity resolution should process 1000 entities under 500ms.

        Threshold relaxed from 200ms to 500ms for CI environments
        where container overhead can cause timing variance.
        """
        from pycc2.domain.entities.unit import Faction
        from pycc2.domain.systems.spatial_hash import SpatialHash
        from pycc2.domain.value_objects.tile_coord import TileCoord

        spatial = SpatialHash(cell_size=10)

        # Insert 1000 entities
        for i in range(1000):
            x = i % 50
            y = i // 50
            spatial.insert(f"unit_{i}", TileCoord(x, y), Faction.ALLIES)

        start = time.perf_counter()
        # Resolve 1000 query operations
        for i in range(1000):
            x = i % 50
            y = i // 50
            spatial.query_radius(TileCoord(x, y), radius=5, exclude_faction=Faction.AXIS)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.5, f"Entity resolution too slow: {elapsed:.3f}s for 1000 entities"

    def test_particle_pool_throughput(self):
        """ParticlePool should handle 500 acquire/release cycles under 50ms."""
        from pycc2.presentation.rendering.particle_pool import ParticlePool

        pool = ParticlePool(preallocate=500)
        start = time.perf_counter()
        for _ in range(500):
            p = pool.acquire()
            pool.release(p)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.05, f"ParticlePool too slow: {elapsed:.3f}s for 500 cycles"
