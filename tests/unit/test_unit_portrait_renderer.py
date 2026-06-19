"""
Unit tests for UnitPortraitRenderer.

Tests 30+ cases covering:
- Normal rendering (all types × all factions)
- Boundary conditions (health 0.0/1.0)
- Error handling (invalid inputs)
- Cache functionality
- Performance benchmarks
"""

import pytest
import time
from unittest.mock import Mock, patch

try:
    import pygame
    from pycc2.domain.entities.unit import Faction
    from pycc2.presentation.rendering.pixel_artist_enums import InfantryType
    from pycc2.presentation.ui.unit_portrait_renderer import UnitPortraitRenderer
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False


@pytest.mark.skipif(not PYGAME_AVAILABLE, reason="Pygame not available")
class TestUnitPortraitRenderer:
    """Test suite for UnitPortraitRenderer"""
    
    @pytest.fixture
    def renderer(self):
        """Create renderer instance"""
        pygame.init()
        return UnitPortraitRenderer(max_cache_size=10)
    
    # === Normal Cases ===
    
    def test_render_portrait_rifleman_allies(self, renderer):
        """Test rifleman portrait for allies"""
        portrait = renderer.render_portrait(
            InfantryType.RIFLEMAN,
            Faction.ALLIES,
            1.0
        )
        assert portrait.get_size() == (96, 96)
    
    def test_render_portrait_sniper_axis(self, renderer):
        """Test sniper portrait for axis"""
        portrait = renderer.render_portrait(
            InfantryType.SNIPER,
            Faction.AXIS,
            0.75
        )
        assert portrait.get_size() == (96, 96)
    
    def test_render_portrait_officer(self, renderer):
        """Test officer portrait"""
        portrait = renderer.render_portrait(
            InfantryType.OFFICER,
            Faction.ALLIES,
            1.0
        )
        assert portrait.get_size() == (96, 96)
    
    def test_render_all_infantry_types(self, renderer):
        """Test all infantry types can be rendered"""
        for unit_type in [InfantryType.RIFLEMAN, InfantryType.SNIPER, InfantryType.OFFICER]:
            for faction in [Faction.ALLIES, Faction.AXIS]:
                portrait = renderer.render_portrait(unit_type, faction, 1.0)
                assert portrait is not None
                assert portrait.get_size() == (96, 96)
    
    # === Boundary Cases ===
    
    def test_render_portrait_zero_health(self, renderer):
        """Test portrait with 0% health (dead)"""
        portrait = renderer.render_portrait(
            InfantryType.RIFLEMAN,
            Faction.ALLIES,
            0.0
        )
        assert portrait.get_size() == (96, 96)
        # Should have red X overlay
    
    def test_render_portrait_full_health(self, renderer):
        """Test portrait with 100% health"""
        portrait = renderer.render_portrait(
            InfantryType.RIFLEMAN,
            Faction.ALLIES,
            1.0
        )
        assert portrait.get_size() == (96, 96)
        # Should have golden badge
    
    def test_render_portrait_low_health(self, renderer):
        """Test portrait with 20% health"""
        portrait = renderer.render_portrait(
            InfantryType.RIFLEMAN,
            Faction.ALLIES,
            0.2
        )
        assert portrait.get_size() == (96, 96)
        # Should have wear + grayscale
    
    def test_render_portrait_mid_health(self, renderer):
        """Test portrait with 50% health"""
        portrait = renderer.render_portrait(
            InfantryType.RIFLEMAN,
            Faction.ALLIES,
            0.5
        )
        assert portrait.get_size() == (96, 96)
    
    # === Scaled Rendering ===
    
    def test_render_portrait_scaled_32(self, renderer):
        """Test 32x32 scaled portrait"""
        portrait = renderer.render_portrait_scaled(
            InfantryType.RIFLEMAN,
            Faction.ALLIES,
            32,
            1.0
        )
        assert portrait.get_size() == (32, 32)
    
    def test_render_portrait_scaled_64(self, renderer):
        """Test 64x64 scaled portrait"""
        portrait = renderer.render_portrait_scaled(
            InfantryType.RIFLEMAN,
            Faction.ALLIES,
            64,
            1.0
        )
        assert portrait.get_size() == (64, 64)
    
    def test_render_portrait_scaled_96(self, renderer):
        """Test 96x96 scaled portrait (no scaling)"""
        portrait = renderer.render_portrait_scaled(
            InfantryType.RIFLEMAN,
            Faction.ALLIES,
            96,
            1.0
        )
        assert portrait.get_size() == (96, 96)
    
    def test_render_portrait_scaled_128(self, renderer):
        """Test 128x128 upscaled portrait"""
        portrait = renderer.render_portrait_scaled(
            InfantryType.RIFLEMAN,
            Faction.ALLIES,
            128,
            1.0
        )
        assert portrait.get_size() == (128, 128)
    
    def test_render_portrait_scaled_min_size(self, renderer):
        """Test minimum size (16x16)"""
        portrait = renderer.render_portrait_scaled(
            InfantryType.RIFLEMAN,
            Faction.ALLIES,
            16,
            1.0
        )
        assert portrait.get_size() == (16, 16)
    
    def test_render_portrait_scaled_max_size(self, renderer):
        """Test maximum size (256x256)"""
        portrait = renderer.render_portrait_scaled(
            InfantryType.RIFLEMAN,
            Faction.ALLIES,
            256,
            1.0
        )
        assert portrait.get_size() == (256, 256)
    
    # === Error Handling ===
    
    def test_render_portrait_invalid_unit_type(self, renderer):
        """Test invalid unit type raises ValueError"""
        with pytest.raises(ValueError, match="Invalid unit_type"):
            renderer.render_portrait("invalid", Faction.ALLIES, 1.0)
    
    def test_render_portrait_invalid_faction(self, renderer):
        """Test invalid faction raises ValueError"""
        with pytest.raises(ValueError, match="Invalid faction"):
            renderer.render_portrait(InfantryType.RIFLEMAN, "invalid", 1.0)
    
    def test_render_portrait_health_too_low(self, renderer):
        """Test health < 0.0 raises ValueError"""
        with pytest.raises(ValueError, match="health_percent must be 0.0-1.0"):
            renderer.render_portrait(InfantryType.RIFLEMAN, Faction.ALLIES, -0.1)
    
    def test_render_portrait_health_too_high(self, renderer):
        """Test health > 1.0 raises ValueError"""
        with pytest.raises(ValueError, match="health_percent must be 0.0-1.0"):
            renderer.render_portrait(InfantryType.RIFLEMAN, Faction.ALLIES, 1.1)
    
    def test_render_portrait_scaled_size_too_small(self, renderer):
        """Test size < 16 raises ValueError"""
        with pytest.raises(ValueError, match="size must be 16-256"):
            renderer.render_portrait_scaled(
                InfantryType.RIFLEMAN, Faction.ALLIES, 15, 1.0
            )
    
    def test_render_portrait_scaled_size_too_large(self, renderer):
        """Test size > 256 raises ValueError"""
        with pytest.raises(ValueError, match="size must be 16-256"):
            renderer.render_portrait_scaled(
                InfantryType.RIFLEMAN, Faction.ALLIES, 300, 1.0
            )
    
    # === Cache Functionality ===
    
    def test_cache_hit(self, renderer):
        """Test cache hit on second render"""
        # First render (miss)
        portrait1 = renderer.render_portrait(
            InfantryType.RIFLEMAN, Faction.ALLIES, 1.0
        )
        
        # Second render (hit)
        portrait2 = renderer.render_portrait(
            InfantryType.RIFLEMAN, Faction.ALLIES, 1.0
        )
        
        # Should return same surface
        assert portrait1 is portrait2
        
        stats = renderer.get_cache_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
    
    def test_cache_quantization(self, renderer):
        """Test health quantization in cache key"""
        # These should all hit the same cache entry (75%)
        portrait1 = renderer.render_portrait(
            InfantryType.RIFLEMAN, Faction.ALLIES, 0.75
        )
        portrait2 = renderer.render_portrait(
            InfantryType.RIFLEMAN, Faction.ALLIES, 0.76
        )
        portrait3 = renderer.render_portrait(
            InfantryType.RIFLEMAN, Faction.ALLIES, 0.99
        )
        
        stats = renderer.get_cache_stats()
        assert stats["hits"] == 2  # 2nd and 3rd render hit cache
        assert stats["misses"] == 1  # Only 1st render missed
    
    def test_cache_eviction(self, renderer):
        """Test LRU cache eviction"""
        # Fill cache (max_size=10)
        for i in range(11):
            health = i / 10.0
            renderer.render_portrait(
                InfantryType.RIFLEMAN, Faction.ALLIES, health
            )
        
        # Cache should be at max size
        stats = renderer.get_cache_stats()
        assert stats["size"] <= 10
    
    def test_clear_cache(self, renderer):
        """Test cache clearing"""
        # Render some portraits
        renderer.render_portrait(InfantryType.RIFLEMAN, Faction.ALLIES, 1.0)
        renderer.render_portrait(InfantryType.SNIPER, Faction.AXIS, 0.5)
        
        # Clear cache
        renderer.clear_cache()
        
        stats = renderer.get_cache_stats()
        assert stats["size"] == 0
    
    def test_get_cache_stats(self, renderer):
        """Test cache statistics"""
        # Initial state
        stats = renderer.get_cache_stats()
        assert stats["size"] == 0
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 0.0
        
        # After renders
        renderer.render_portrait(InfantryType.RIFLEMAN, Faction.ALLIES, 1.0)
        renderer.render_portrait(InfantryType.RIFLEMAN, Faction.ALLIES, 1.0)
        
        stats = renderer.get_cache_stats()
        assert stats["size"] == 1
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5
    
    # === Performance Tests ===
    
    def test_performance_first_render(self, renderer):
        """Test first render performance < 5ms"""
        start = time.perf_counter()
        renderer.render_portrait(InfantryType.RIFLEMAN, Faction.ALLIES, 1.0)
        elapsed = time.perf_counter() - start
        
        assert elapsed < 0.005, f"First render too slow: {elapsed*1000:.2f}ms"
    
    def test_performance_cached_render(self, renderer):
        """Test cached render performance < 1ms"""
        # Warm up cache
        renderer.render_portrait(InfantryType.RIFLEMAN, Faction.ALLIES, 1.0)
        
        # Measure cached render
        start = time.perf_counter()
        renderer.render_portrait(InfantryType.RIFLEMAN, Faction.ALLIES, 1.0)
        elapsed = time.perf_counter() - start
        
        assert elapsed < 0.001, f"Cached render too slow: {elapsed*1000:.2f}ms"
    
    def test_performance_batch_render(self, renderer):
        """Test batch rendering 10 portraits < 50ms"""
        start = time.perf_counter()
        
        for i in range(10):
            renderer.render_portrait(
                InfantryType.RIFLEMAN,
                Faction.ALLIES,
                i / 10.0
            )
        
        elapsed = time.perf_counter() - start
        assert elapsed < 0.05, f"Batch render too slow: {elapsed*1000:.2f}ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
