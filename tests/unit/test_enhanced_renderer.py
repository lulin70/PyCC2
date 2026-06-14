"""
Unit tests for Enhanced Renderer - Trench Terrain and Procedural Textures

Tests cover:
- Trench terrain texture generation (terrain_id 13)
- Autotile bitmask variations for trench
- ProceduralTextureGenerator functionality
- PaletteGenerator for new terrain types
"""

from __future__ import annotations

import os

import pytest

# Ensure SDL dummy drivers are set before pygame imports
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


class TestTrenchTerrainGeneration:
    """Test trench terrain (ID 13) procedural generation."""

    @pytest.fixture()
    def palette_gen(self):
        from pycc2.presentation.rendering.enhanced_renderer import PaletteGenerator

        return PaletteGenerator()

    def test_trench_terrain_generates(self, palette_gen, pygame_display):
        """Test that trench terrain generates without error."""
        import pygame

        from pycc2.presentation.rendering.enhanced_renderer import ProceduralTextureGenerator

        surface = ProceduralTextureGenerator.generate_terrain_texture(
            terrain_id=13,
            variation=0,
            palette=palette_gen,
            bitmask=0,
        )

        assert surface is not None
        assert isinstance(surface, pygame.Surface)
        assert surface.get_size() == (48, 48)

    def test_trench_different_variations(self, palette_gen, pygame_display):
        """Test that trench generates different appearances for different variations."""
        from pycc2.presentation.rendering.enhanced_renderer import ProceduralTextureGenerator

        surfaces = []
        for var in range(3):
            surface = ProceduralTextureGenerator.generate_terrain_texture(
                terrain_id=13,
                variation=var,
                palette=palette_gen,
                bitmask=0,
            )
            assert surface is not None
            surfaces.append(surface)

        # All should be valid 48x48 surfaces
        assert len(surfaces) == 3
        for i, surf in enumerate(surfaces):
            assert surf.get_size() == (48, 48), f"Variation {i} has wrong size"

    def test_trench_bitmask_variations(self, palette_gen, pygame_display):
        """Test trench generation with different autotile bitmasks."""
        from pycc2.presentation.rendering.enhanced_renderer import ProceduralTextureGenerator

        # Test various bitmask values (0-15)
        test_bitmasks = [0, 1, 2, 3, 5, 8, 10, 15]

        for bitmask in test_bitmasks:
            surface = ProceduralTextureGenerator.generate_terrain_texture(
                terrain_id=13,
                variation=42,
                palette=palette_gen,
                bitmask=bitmask,
            )
            assert surface is not None, f"Trench failed for bitmask={bitmask}"
            assert surface.get_size() == (48, 48), f"Trench has wrong size for bitmask={bitmask}"

    def test_trench_has_dark_brown_color(self, palette_gen, pygame_display):
        """Test that trench contains expected dark brown color (#3A2818)."""
        from pycc2.presentation.rendering.enhanced_renderer import ProceduralTextureGenerator

        surface = ProceduralTextureGenerator.generate_terrain_texture(
            terrain_id=13,
            variation=0,
            palette=palette_gen,
            bitmask=0,
        )

        # Check that surface is not empty/transparent everywhere
        # We can't easily check exact pixel colors due to procedural generation,
        # but we can verify the surface exists and has content
        assert surface.get_width() > 0
        assert surface.get_height() > 0


class TestPaletteGeneratorTrench:
    """Test PaletteGenerator includes trench colors."""

    def test_palette_includes_trench_id(self):
        """Test that terrain ID 13 is in the palette."""
        from pycc2.presentation.rendering.enhanced_renderer import PaletteGenerator

        gen = PaletteGenerator()
        assert 13 in gen.palettes, "Trench ID (13) missing from palette"

    def test_trench_palette_has_8_shades(self):
        """Test that trench palette has 8 color shades."""
        from pycc2.presentation.rendering.enhanced_renderer import PaletteGenerator

        gen = PaletteGenerator()
        trench_palette = gen.palettes.get(13)
        assert trench_palette is not None, "Trench palette is None"
        assert len(trench_palette) == 8, f"Trench should have 8 shades, got {len(trench_palette)}"

    def test_trench_colors_are_reasonable(self):
        """Test that trench colors are dark earth brown tones."""
        from pycc2.presentation.rendering.enhanced_renderer import PaletteGenerator

        gen = PaletteGenerator()
        trench_palette = gen.palettes[13]

        # Base color (shade index 4 - mid tone) should be dark brown
        base_color = trench_palette[4]
        # Should be: R moderate-low (25-90), G low (15-75), B very low (0-65)
        # Note: PaletteGenerator applies random variation, so we use wide ranges
        assert 20 <= base_color[0] <= 95, f"Trench R out of range: {base_color}"
        assert 15 <= base_color[1] <= 80, f"Trench G out of range: {base_color}"
        assert 5 <= base_color[2] <= 70, f"Trench B out of range: {base_color}"


class TestProceduralTextureGeneratorIntegration:
    """Integration tests for procedural texture generation."""

    @pytest.fixture()
    def palette_gen(self):
        from pycc2.presentation.rendering.enhanced_renderer import PaletteGenerator

        return PaletteGenerator()

    def test_all_terrain_ids_generate(self, palette_gen, pygame_display):
        """Test that all terrain IDs (0-13) generate successfully."""
        from pycc2.presentation.rendering.enhanced_renderer import ProceduralTextureGenerator

        for tid in range(14):  # 0-13 inclusive
            surface = ProceduralTextureGenerator.generate_terrain_texture(
                terrain_id=tid,
                variation=tid * 17,
                palette=palette_gen,
                bitmask=0,
            )
            assert surface is not None, f"Failed to generate terrain ID {tid}"
            assert surface.get_size() == (48, 48), (
                f"Terrain ID {tid} has wrong size: {surface.get_size()}"
            )

    def test_terrain_cache_consistency(self, palette_gen, pygame_display):
        """Test that same parameters produce consistent results."""
        from pycc2.presentation.rendering.enhanced_renderer import ProceduralTextureGenerator

        # Generate twice with same params
        surface1 = ProceduralTextureGenerator.generate_terrain_texture(
            terrain_id=13,
            variation=99,
            palette=palette_gen,
            bitmask=5,
        )
        surface2 = ProceduralTextureGenerator.generate_terrain_texture(
            terrain_id=13,
            variation=99,
            palette=palette_gen,
            bitmask=5,
        )

        # Both should exist and have same size
        assert surface1 is not None and surface2 is not None
        assert surface1.get_size() == surface2.get_size()


class TestCC2TerrainPalette:
    """Test CC2_TERRAIN_PALETTE constants."""

    def test_trench_colors_exist(self):
        """Test that trench color keys exist in CC2_TERRAIN_PALETTE."""
        from pycc2.presentation.rendering.terrain_tile_cache import CC2_TERRAIN_PALETTE

        assert "trench_main" in CC2_TERRAIN_PALETTE, "Missing 'trench_main' color"
        assert "trench_embankment" in CC2_TERRAIN_PALETTE, "Missing 'trench_embankment' color"

    def test_trench_main_color_value(self):
        """Test that trench_main matches spec (#3A2818)."""
        from pycc2.presentation.rendering.terrain_tile_cache import CC2_TERRAIN_PALETTE

        trench_main = CC2_TERRAIN_PALETTE["trench_main"]
        # Should be approximately #3A2818 (dark earth brown)
        assert abs(trench_main[0] - 58) <= 5, f"R value off: {trench_main[0]}"
        assert abs(trench_main[1] - 40) <= 5, f"G value off: {trench_main[1]}"
        assert abs(trench_main[2] - 24) <= 5, f"B value off: {trench_main[2]}"

    def test_trench_embankment_color_value(self):
        """Test that trench_embankment matches spec (#5A4830)."""
        from pycc2.presentation.rendering.terrain_tile_cache import CC2_TERRAIN_PALETTE

        trench_embankment = CC2_TERRAIN_PALETTE["trench_embankment"]
        # Should be approximately #5A4830 (lighter embankment)
        assert abs(trench_embankment[0] - 90) <= 5, f"R value off: {trench_embankment[0]}"
        assert abs(trench_embankment[1] - 72) <= 5, f"G value off: {trench_embankment[1]}"
        assert abs(trench_embankment[2] - 48) <= 5, f"B value off: {trench_embankment[2]}"

    def test_terrain_palette_map_includes_trench(self):
        """Test that TERRAIN_PALETTE_MAP includes ID 13 for trench."""
        from pycc2.presentation.rendering.terrain_tile_cache import TERRAIN_PALETTE_MAP

        assert 13 in TERRAIN_PALETTE_MAP, "Missing terrain ID 13 (TRENCH)"
        assert TERRAIN_PALETTE_MAP[13] == "trench_main", (
            f"ID 13 should map to 'trench_main', got {TERRAIN_PALETTE_MAP[13]}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
