"""
Unit tests for EnhancedPostProcessing - Post-Processing Effects

Tests cover:
- Film grain application (Happy Path)
- Chromatic aberration (Happy Path)
- Enhanced vignette with multiple layers (Happy Path + Boundary)
- War atmosphere color grading (Happy Path)
- Depth blur simulation (Happy Path)
- Damage flash effect (Happy Path)
- Full post-processing pipeline (Happy Path)
- Error handling for invalid inputs (Error Case)
- Boundary conditions (zero intensity, extreme values)
- Performance with different surface sizes (Boundary)
"""

from __future__ import annotations

import os

import pytest

# Ensure SDL dummy drivers are set before pygame imports
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


class TestEnhancedPostProcessing:
    """Test EnhancedPostProcessing functionality."""

    @pytest.fixture()
    def post_processor(self, pygame_display):
        """Create an EnhancedPostProcessing instance."""
        from pycc2.presentation.rendering.enhanced_post_processing import (
            EnhancedPostProcessing,
        )

        return EnhancedPostProcessing()

    @pytest.fixture()
    def test_surface(self, pygame_display):
        """Create a test surface for post-processing."""
        import pygame

        surface = pygame.Surface((400, 300), pygame.SRCALPHA)
        # Fill with gradient for visual testing
        for y in range(300):
            color_value = int(255 * (y / 300))
            pygame.draw.line(
                surface, (color_value, color_value // 2, 255 - color_value), (0, y), (400, y)
            )
        return surface

    # ===== HAPPY PATH TESTS =====

    def test_apply_film_grain_returns_surface(self, post_processor, test_surface, pygame_display):
        """Test that film grain application returns a valid surface."""
        import pygame

        result = post_processor.apply_film_grain(test_surface, intensity=0.15)

        assert result is not None
        assert isinstance(result, pygame.Surface)
        assert result.get_size() == test_surface.get_size()

    def test_apply_film_grain_modifies_image(self, post_processor, test_surface, pygame_display):
        """Test that film grain actually modifies the image."""
        result = post_processor.apply_film_grain(test_surface, intensity=0.2)

        # Sample a few pixels to verify they changed
        original_color = test_surface.get_at((100, 100))
        result_color = result.get_at((100, 100))

        # Colors should be different (within reason)
        assert original_color != result_color or abs(original_color[0] - result_color[0]) > 0

    def test_apply_chromatic_aberration_returns_surface(
        self, post_processor, test_surface, pygame_display
    ):
        """Test that chromatic aberration returns a valid surface."""
        import pygame

        result = post_processor.apply_chromatic_aberration(test_surface, intensity=2.0)

        assert result is not None
        assert isinstance(result, pygame.Surface)
        assert result.get_size() == test_surface.get_size()

    def test_apply_enhanced_vignette_returns_surface(
        self, post_processor, test_surface, pygame_display
    ):
        """Test that vignette application returns a valid surface."""
        import pygame

        result = post_processor.apply_enhanced_vignette(
            test_surface, intensity=0.7, inner_radius=0.5, outer_radius=1.2
        )

        assert result is not None
        assert isinstance(result, pygame.Surface)
        assert result.get_size() == test_surface.get_size()

    def test_vignette_darkens_edges(self, post_processor, test_surface, pygame_display):
        """Test that vignette darkens edges more than center."""
        result = post_processor.apply_enhanced_vignette(test_surface, intensity=0.8)

        # Center should be brighter than edge
        center_color = result.get_at((200, 150))  # Center
        edge_color = result.get_at((10, 10))  # Top-left corner

        # Center should have higher brightness
        center_brightness = sum(center_color[:3])
        edge_brightness = sum(edge_color[:3])

        assert center_brightness > edge_brightness

    def test_apply_war_atmosphere_returns_surface(
        self, post_processor, test_surface, pygame_display
    ):
        """Test that war atmosphere application returns a valid surface."""
        import pygame

        result = post_processor.apply_war_atmosphere(
            test_surface, desaturation=0.4, contrast_boost=1.2, warmth=8
        )

        assert result is not None
        assert isinstance(result, pygame.Surface)
        assert result.get_size() == test_surface.get_size()

    def test_apply_depth_blur_returns_surface(self, post_processor, test_surface, pygame_display):
        """Test that depth blur returns a valid surface."""
        import pygame

        result = post_processor.apply_depth_blur(test_surface, focus_y=150, blur_radius=2)

        assert result is not None
        assert isinstance(result, pygame.Surface)
        assert result.get_size() == test_surface.get_size()

    def test_apply_damage_flash_returns_surface(self, post_processor, test_surface, pygame_display):
        """Test that damage flash returns a valid surface."""
        import pygame

        result = post_processor.apply_damage_flash(test_surface, intensity=0.5, color=(255, 0, 0))

        assert result is not None
        assert isinstance(result, pygame.Surface)
        assert result.get_size() == test_surface.get_size()

    def test_damage_flash_adds_red_tint(self, post_processor, test_surface, pygame_display):
        """Test that damage flash adds red tint to image."""
        result = post_processor.apply_damage_flash(test_surface, intensity=0.8, color=(255, 0, 0))

        # Sample pixel should have more red
        original = test_surface.get_at((200, 150))
        result_color = result.get_at((200, 150))

        # Red channel should be higher or equal
        assert result_color[0] >= original[0]

    def test_apply_full_post_processing_all_enabled(
        self, post_processor, test_surface, pygame_display
    ):
        """Test full post-processing pipeline with all effects enabled."""
        import pygame

        result = post_processor.apply_full_post_processing(
            test_surface,
            enable_grain=True,
            enable_vignette=True,
            enable_color_grade=True,
            enable_chromatic_aberration=True,
        )

        assert result is not None
        assert isinstance(result, pygame.Surface)
        assert result.get_size() == test_surface.get_size()

    def test_apply_full_post_processing_selective(
        self, post_processor, test_surface, pygame_display
    ):
        """Test full post-processing with selective effects."""
        import pygame

        result = post_processor.apply_full_post_processing(
            test_surface,
            enable_grain=True,
            enable_vignette=True,
            enable_color_grade=False,
            enable_chromatic_aberration=False,
        )

        assert result is not None
        assert isinstance(result, pygame.Surface)

    # ===== BOUNDARY TESTS =====

    def test_film_grain_zero_intensity(self, post_processor, test_surface, pygame_display):
        """Test film grain with zero intensity (boundary)."""
        result = post_processor.apply_film_grain(test_surface, intensity=0.0)

        # Should return surface with minimal or no changes
        assert result is not None
        assert result.get_size() == test_surface.get_size()

    def test_film_grain_high_intensity(self, post_processor, test_surface, pygame_display):
        """Test film grain with very high intensity (boundary)."""
        result = post_processor.apply_film_grain(test_surface, intensity=1.0)

        # Should still return valid surface (may be very noisy)
        assert result is not None
        assert result.get_size() == test_surface.get_size()

    def test_chromatic_aberration_zero_intensity(
        self, post_processor, test_surface, pygame_display
    ):
        """Test chromatic aberration with zero intensity (boundary)."""
        result = post_processor.apply_chromatic_aberration(test_surface, intensity=0.0)

        assert result is not None
        assert result.get_size() == test_surface.get_size()

    def test_chromatic_aberration_high_intensity(
        self, post_processor, test_surface, pygame_display
    ):
        """Test chromatic aberration with high intensity (boundary)."""
        result = post_processor.apply_chromatic_aberration(test_surface, intensity=10.0)

        assert result is not None
        assert result.get_size() == test_surface.get_size()

    def test_vignette_zero_intensity(self, post_processor, test_surface, pygame_display):
        """Test vignette with zero intensity (boundary)."""
        result = post_processor.apply_enhanced_vignette(test_surface, intensity=0.0)

        assert result is not None
        # With zero intensity, should have minimal darkening

    def test_vignette_extreme_radii(self, post_processor, test_surface, pygame_display):
        """Test vignette with extreme radius values (boundary)."""
        # Inner radius larger than outer (unusual but should handle)
        result = post_processor.apply_enhanced_vignette(
            test_surface, intensity=0.5, inner_radius=1.0, outer_radius=0.5
        )

        assert result is not None

    def test_war_atmosphere_zero_desaturation(self, post_processor, test_surface, pygame_display):
        """Test war atmosphere with zero desaturation (boundary)."""
        result = post_processor.apply_war_atmosphere(
            test_surface, desaturation=0.0, contrast_boost=1.0, warmth=0
        )

        assert result is not None

    def test_war_atmosphere_full_desaturation(self, post_processor, test_surface, pygame_display):
        """Test war atmosphere with full desaturation (boundary)."""
        result = post_processor.apply_war_atmosphere(
            test_surface, desaturation=1.0, contrast_boost=1.0, warmth=0
        )

        # Should be grayscale
        assert result is not None

    def test_depth_blur_zero_radius(self, post_processor, test_surface, pygame_display):
        """Test depth blur with zero radius (boundary)."""
        result = post_processor.apply_depth_blur(test_surface, focus_y=150, blur_radius=0)

        # Should return surface with no blur
        assert result is not None

    def test_depth_blur_focus_at_edge(self, post_processor, test_surface, pygame_display):
        """Test depth blur with focus at edge of image (boundary)."""
        result = post_processor.apply_depth_blur(test_surface, focus_y=0, blur_radius=2)

        assert result is not None

    def test_damage_flash_zero_intensity(self, post_processor, test_surface, pygame_display):
        """Test damage flash with zero intensity (boundary)."""
        result = post_processor.apply_damage_flash(test_surface, intensity=0.0)

        # Should return surface with no flash
        assert result is not None

    def test_damage_flash_max_intensity(self, post_processor, test_surface, pygame_display):
        """Test damage flash with maximum intensity (boundary)."""
        result = post_processor.apply_damage_flash(test_surface, intensity=1.0)

        assert result is not None

    # ===== ERROR CASE TESTS =====

    def test_negative_film_grain_intensity(self, post_processor, test_surface, pygame_display):
        """Test film grain with negative intensity (error case)."""
        # Negative intensity causes ValueError in numpy.random.normal
        # This is expected behavior - test that it raises the error
        import pytest

        with pytest.raises(ValueError):
            post_processor.apply_film_grain(test_surface, intensity=-0.1)

    def test_negative_vignette_intensity(self, post_processor, test_surface, pygame_display):
        """Test vignette with negative intensity (error case)."""
        result = post_processor.apply_enhanced_vignette(test_surface, intensity=-0.5)

        # Should handle gracefully (may brighten instead of darken)
        assert result is not None

    def test_extreme_contrast_boost(self, post_processor, test_surface, pygame_display):
        """Test war atmosphere with extreme contrast boost (error case)."""
        result = post_processor.apply_war_atmosphere(
            test_surface, desaturation=0.5, contrast_boost=10.0, warmth=0
        )

        # Should clip values properly and not crash
        assert result is not None

    def test_negative_warmth(self, post_processor, test_surface, pygame_display):
        """Test war atmosphere with negative warmth (error case - cool tint)."""
        result = post_processor.apply_war_atmosphere(
            test_surface, desaturation=0.3, contrast_boost=1.0, warmth=-20
        )

        assert result is not None

    def test_small_surface(self, post_processor, pygame_display):
        """Test post-processing on very small surface (error case)."""
        import pygame

        small_surface = pygame.Surface((10, 10), pygame.SRCALPHA)
        small_surface.fill((100, 150, 200, 255))

        result = post_processor.apply_film_grain(small_surface, intensity=0.1)

        assert result is not None
        assert result.get_size() == (10, 10)

    def test_single_pixel_surface(self, post_processor, pygame_display):
        """Test post-processing on 1x1 surface (boundary/error case)."""
        import pygame

        tiny_surface = pygame.Surface((1, 1), pygame.SRCALPHA)
        tiny_surface.fill((100, 100, 100, 255))

        # Should handle without crashing
        result = post_processor.apply_enhanced_vignette(tiny_surface, intensity=0.5)

        assert result is not None

    # ===== INTEGRATION TESTS =====

    def test_convenience_functions(self, test_surface, pygame_display):
        """Test convenience functions work correctly."""
        from pycc2.presentation.rendering.enhanced_post_processing import (
            apply_damage_effect,
            apply_enhanced_post_processing,
            apply_war_color_grade,
        )

        # Test apply_enhanced_post_processing
        result1 = apply_enhanced_post_processing(test_surface)
        assert result1 is not None

        # Test apply_war_color_grade
        result2 = apply_war_color_grade(test_surface)
        assert result2 is not None

        # Test apply_damage_effect
        result3 = apply_damage_effect(test_surface, intensity=0.5)
        assert result3 is not None

    def test_chained_effects(self, post_processor, test_surface, pygame_display):
        """Test applying multiple effects in sequence."""
        result = test_surface

        result = post_processor.apply_war_atmosphere(result)
        result = post_processor.apply_enhanced_vignette(result)
        result = post_processor.apply_film_grain(result)

        assert result is not None
        assert result.get_size() == test_surface.get_size()

    def test_post_processing_idempotence(self, post_processor, test_surface, pygame_display):
        """Test that applying effects twice doesn't break."""
        result1 = post_processor.apply_film_grain(test_surface, intensity=0.1)
        result2 = post_processor.apply_film_grain(result1, intensity=0.1)

        assert result2 is not None
        assert result2.get_size() == test_surface.get_size()
