from __future__ import annotations

import pytest

from pycc2.presentation.rendering.tile_cache import TileCache


class TestTileCacheInitial:
    def test_initial_state_empty(self):
        tc = TileCache()
        assert tc.stats["hits"] == 0
        assert tc.stats["misses"] == 0
        assert tc.hit_rate == 0.0
        assert tc.cached_tile_count == 0

    def test_get_tile_generates_on_miss(self):
        tc = TileCache()
        surface = tc.get_tile(0, 32)
        assert surface is not None
        assert tc.stats["misses"] == 1
        assert tc.stats["hits"] == 0
        assert tc.cached_tile_count == 1

    def test_get_tile_returns_cached_on_hit(self):
        tc = TileCache()
        s1 = tc.get_tile(0, 32)
        s2 = tc.get_tile(0, 32)
        assert s1 is s2
        assert tc.stats["hits"] == 1
        assert tc.stats["misses"] == 1


class TestTileCacheInvalidate:
    def test_invalidate_single_terrain(self):
        tc = TileCache()
        tc.get_tile(0, 32)
        tc.get_tile(1, 32)
        assert tc.cached_tile_count == 2
        tc.invalidate(terrain_id=0)
        assert tc.cached_tile_count == 1

    def test_invalidate_all_clears_everything(self):
        tc = TileCache()
        for tid in range(5):
            tc.get_tile(tid, 32)
        assert tc.cached_tile_count == 5
        tc.invalidate()
        assert tc.cached_tile_count == 0

    def test_invalidate_nonexistent_is_noop(self):
        tc = TileCache()
        tc.get_tile(0, 32)
        tc.invalidate(terrain_id=99)
        assert tc.cached_tile_count == 1


class TestTileCacheHitRate:
    def test_hit_rate_calculation(self):
        tc = TileCache()
        tc.get_tile(0, 32)
        for _ in range(9):
            tc.get_tile(0, 32)
        assert tc.stats["hits"] == 9
        assert tc.stats["misses"] == 1
        assert tc.hit_rate == pytest.approx(0.9)

    def test_hit_rate_zero_when_empty(self):
        tc = TileCache()
        assert tc.hit_rate == 0.0


class TestTileCacheSizeSeparation:
    def test_different_sizes_cached_separately(self):
        tc = TileCache()
        s32 = tc.get_tile(0, 32)
        s64 = tc.get_tile(0, 64)
        assert s32 is not s64
        assert tc.cached_tile_count == 2

    def test_same_size_same_terrain_returns_same_surface(self):
        tc = TileCache()
        s1 = tc.get_tile(3, 48)
        s2 = tc.get_tile(3, 48)
        assert s1 is s2


class TestTileCacheAllTerrainTypes:
    @pytest.mark.parametrize("tid", range(14))
    def test_all_14_terrain_types_can_be_cached(self, tid):
        tc = TileCache()
        surface = tc.get_tile(tid, 32)
        assert surface is not None
        assert surface.get_width() == 32
        assert surface.get_height() == 32

    def test_all_terrain_types_populate_cache(self):
        tc = TileCache()
        for tid in range(14):
            tc.get_tile(tid, 32)
        assert tc.cached_tile_count == 14
        assert tc.stats["misses"] == 14

    def test_after_caching_all_hits_work(self):
        tc = TileCache()
        for tid in range(14):
            tc.get_tile(tid, 32)
        for tid in range(14):
            tc.get_tile(tid, 32)
        assert tc.stats["hits"] == 14
        assert tc.stats["misses"] == 14


class TestTileCacheSurfaceProperties:
    def test_returned_surface_has_correct_size(self):
        tc = TileCache()
        surface = tc.get_tile(0, 48)
        assert surface.get_size() == (48, 48)

    def test_different_terrain_ids_produce_different_surfaces(self):
        tc = TileCache()
        s0 = tc.get_tile(0, 32)
        s6 = tc.get_tile(6, 32)
        assert s0 is not s6
