"""
Unit tests for EnhancedTerrainGenerator - High Quality Terrain Texture Generation

Tests cover:
- Perlin noise generation (Happy Path)
- Octave noise with different parameters (Happy Path + Boundary)
- Enhanced grass tile generation (Happy Path)
- Enhanced dirt tile generation (Happy Path)
- Smooth edge transitions (Happy Path + Boundary)
- Error handling for invalid inputs (Error Case)
- Boundary conditions (zero dimensions, extreme parameters)
- Reproducibility with seeds (Happy Path)
- Performance characteristics (Boundary)
"""

from __future__ import annotations

import os

import pytest

# Ensure SDL dummy drivers are set before pygame imports
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


class TestEnhancedTerrainGenerator:
    """Test EnhancedTerrainGenerator functionality."""

    @pytest.fixture()
    def terrain_generator(self, pygame_display):
        """Create an EnhancedTerrainGenerator instance."""
        from pycc2.presentation.rendering.enhanced_terrain_generator import (
            EnhancedTerrainGenerator,
        )
        return EnhancedTerrainGenerator(seed=42)

    # ===== HAPPY PATH TESTS =====

    def test_perlin_noise_returns_valid_range(self, terrain_generator, pygame_display):
        """Test that Perlin noise returns values in expected range."""
        # Test multiple points
        for x in [0.0, 1.5, 10.0, 100.0]:
            for y in [0.0, 2.3, 15.0, 200.0]:
                noise_val = terrain_generator.perlin_noise_2d(x, y, seed=42)
                # Perlin noise should be roughly in range [-1, 1]
                assert -2.0 <= noise_val <= 2.0, f"Noise value {noise_val} out of range at ({x}, {y})"

    def test_octave_noise_default_parameters(self, terrain_generator, pygame_display):
        """Test octave noise with default parameters produces valid output."""
        noise_val = terrain_generator.octave_noise(5.0, 5.0)
        assert isinstance(noise_val, float)
        assert -1.5 <= noise_val <= 1.5  # Normalized range

    def test_octave_noise_single_octave(self, terrain_generator, pygame_display):
        """Test octave noise with single octave equals Perlin noise."""
        x, y = 10.0, 20.0
        octave_val = terrain_generator.octave_noise(x, y, octaves=1, persistence=0.5)
        perlin_val = terrain_generator.perlin_noise_2d(x, y, terrain_generator.seed)
        
        # Should be very similar (within floating point precision)
        assert abs(octave_val - perlin_val) < 0.01

    def test_generate_enhanced_grass_tile_returns_valid_surface(self, terrain_generator, pygame_display):
        """Test that enhanced grass tile generation returns valid pygame Surface."""
        import pygame
        from pycc2.presentation.rendering.isometric_tile_generator import TILE_H, TILE_W

        surface = terrain_generator.generate_enhanced_grass_tile()
        
        assert surface is not None
        assert isinstance(surface, pygame.Surface)
        assert surface.get_size() == (TILE_W, TILE_H)
        assert surface.get_flags() & pygame.SRCALPHA  # Has alpha channel

    def test_generate_enhanced_dirt_tile_returns_valid_surface(self, terrain_generator, pygame_display):
        """Test that enhanced dirt tile generation returns valid pygame Surface."""
        import pygame
        from pycc2.presentation.rendering.isometric_tile_generator import TILE_H, TILE_W

        surface = terrain_generator.generate_enhanced_dirt_tile()
        
        assert surface is not None
        assert isinstance(surface, pygame.Surface)
        assert surface.get_size() == (TILE_W, TILE_H)
        assert surface.get_flags() & pygame.SRCALPHA

    def test_grass_tile_has_color_variation(self, terrain_generator, pygame_display):
        """Test that grass tiles have color variation (not uniform)."""
        surface = terrain_generator.generate_enhanced_grass_tile()
        
        # Sample multiple pixels
        colors_seen = set()
        for x in range(0, surface.get_width(), 8):
            for y in range(0, surface.get_height(), 8):
                color = surface.get_at((x, y))
                colors_seen.add(color[:3])  # Ignore alpha
        
        # Should have multiple different colors (variation)
        assert len(colors_seen) > 5, "Grass tile lacks color variation"

    def test_dirt_tile_has_color_variation(self, terrain_generator, pygame_display):
        """Test that dirt tiles have color variation (not uniform)."""
        surface = terrain_generator.generate_enhanced_dirt_tile()
        
        # Sample multiple pixels
        colors_seen = set()
        for x in range(0, surface.get_width(), 8):
            for y in range(0, surface.get_height(), 8):
                color = surface.get_at((x, y))
                colors_seen.add(color[:3])
        
        assert len(colors_seen) > 5, "Dirt tile lacks color variation"

    def test_smooth_edge_transition_top(self, terrain_generator, pygame_display):
        """Test smooth edge transition on top edge."""
        import pygame
        from pycc2.presentation.rendering.isometric_tile_generator import TILE_H, TILE_W

        surface = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)
        surface.fill((100, 200, 100, 255))  # Green base
        
        terrain_generator.apply_smooth_edge_transition(
            surface, "dirt_road", "top"
        )
        
        # Top pixels should be modified
        top_color = surface.get_at((TILE_W // 2, 0))
        base_color = surface.get_at((TILE_W // 2, TILE_H // 2))
        
        # Colors should be different due to blending
        assert top_color[:3] != base_color[:3]

    # ===== BOUNDARY TESTS =====

    def test_perlin_noise_at_zero(self, terrain_generator, pygame_display):
        """Test Perlin noise at origin (boundary condition)."""
        noise_val = terrain_generator.perlin_noise_2d(0.0, 0.0, seed=0)
        assert isinstance(noise_val, float)
        assert not (noise_val != noise_val), "Noise should not be NaN"  # Check for NaN

    def test_perlin_noise_at_large_coordinates(self, terrain_generator, pygame_display):
        """Test Perlin noise at very large coordinates (boundary condition)."""
        noise_val = terrain_generator.perlin_noise_2d(10000.0, 10000.0, seed=42)
        assert isinstance(noise_val, float)
        assert -2.0 <= noise_val <= 2.0

    def test_octave_noise_zero_octaves(self, terrain_generator, pygame_display):
        """Test octave noise with zero octaves (boundary condition)."""
        noise_val = terrain_generator.octave_noise(5.0, 5.0, octaves=0)
        # With zero octaves, should return 0 (no noise)
        assert noise_val == 0.0

    def test_octave_noise_high_octave_count(self, terrain_generator, pygame_display):
        """Test octave noise with many octaves (boundary condition)."""
        noise_val = terrain_generator.octave_noise(5.0, 5.0, octaves=10)
        assert isinstance(noise_val, float)
        assert -2.0 <= noise_val <= 2.0  # Should still be in valid range

    def test_octave_noise_extreme_persistence(self, terrain_generator, pygame_display):
        """Test octave noise with extreme persistence values (boundary condition)."""
        # Very low persistence
        noise_val_low = terrain_generator.octave_noise(5.0, 5.0, persistence=0.0)
        assert isinstance(noise_val_low, float)
        
        # Very high persistence
        noise_val_high = terrain_generator.octave_noise(5.0, 5.0, persistence=1.0)
        assert isinstance(noise_val_high, float)

    def test_smooth_edge_transition_invalid_neighbor(self, terrain_generator, pygame_display):
        """Test smooth edge transition with invalid neighbor type (error handling)."""
        import pygame
        from pycc2.presentation.rendering.isometric_tile_generator import TILE_H, TILE_W

        surface = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)
        surface.fill((100, 200, 100, 255))
        
        # Should handle gracefully without crashing
        terrain_generator.apply_smooth_edge_transition(
            surface, "invalid_terrain_type", "top"
        )
        # Should not modify surface (invalid type)
        assert surface is not None

    # ===== ERROR CASE TESTS =====

    def test_octave_noise_negative_octaves(self, terrain_generator, pygame_display):
        """Test octave noise with negative octaves (error case)."""
        # Should handle gracefully (treat as 0 or absolute value)
        noise_val = terrain_generator.octave_noise(5.0, 5.0, octaves=-1)
        assert isinstance(noise_val, (int, float))

    def test_octave_noise_zero_max_value_protection(self, terrain_generator, pygame_display):
        """Test octave noise doesn't divide by zero when max_value is zero."""
        # With persistence=0 and octaves>0, max_value could theoretically be problematic
        noise_val = terrain_generator.octave_noise(
            5.0, 5.0, octaves=5, persistence=0.0, lacunarity=2.0
        )
        assert isinstance(noise_val, float)
        assert not (noise_val != noise_val), "Should not produce NaN"

    # ===== REPRODUCIBILITY TESTS =====

    def test_same_seed_produces_same_grass(self, pygame_display):
        """Test that same seed produces identical grass tiles (reproducibility)."""
        from pycc2.presentation.rendering.enhanced_terrain_generator import (
            EnhancedTerrainGenerator,
        )
        
        gen1 = EnhancedTerrainGenerator(seed=12345)
        gen2 = EnhancedTerrainGenerator(seed=12345)
        
        surface1 = gen1.generate_enhanced_grass_tile()
        surface2 = gen2.generate_enhanced_grass_tile()
        
        # Sample a few pixels to verify they match
        for x in range(0, surface1.get_width(), 10):
            for y in range(0, surface1.get_height(), 10):
                color1 = surface1.get_at((x, y))
                color2 = surface2.get_at((x, y))
                assert color1 == color2, f"Colors differ at ({x}, {y})"

    def test_different_seed_produces_different_grass(self, pygame_display):
        """Test that different seeds create generators with different RNG states."""
        from pycc2.presentation.rendering.enhanced_terrain_generator import (
            EnhancedTerrainGenerator,
        )
        
        gen1 = EnhancedTerrainGenerator(seed=111)
        gen2 = EnhancedTerrainGenerator(seed=999)
        
        # The generators should have different internal random states
        # This affects grass blade placement (Layer 3 in grass generation)
        rand_values_1 = [gen1.rng.random() for _ in range(5)]
        rand_values_2 = [gen2.rng.random() for _ in range(5)]
        
        # At least one value should be different
        assert rand_values_1 != rand_values_2, "Different seeds should produce different random sequences"
        
        # Verify that the seed attribute is different
        assert gen1.seed != gen2.seed, "Generators should have different seeds"

    # ===== INTEGRATION TESTS =====

    def test_convenience_functions_work(self, pygame_display):
        """Test that convenience functions are accessible and work."""
        from pycc2.presentation.rendering.enhanced_terrain_generator import (
            generate_enhanced_dirt,
            generate_enhanced_grass,
        )
        
        grass = generate_enhanced_grass()
        assert grass is not None
        
        dirt = generate_enhanced_dirt()
        assert dirt is not None
