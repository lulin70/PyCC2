"""Palette generator for CC2-style terrain rendering.

Extracted from enhanced_renderer.py in v0.3.5 refactoring.
Generates 8-shade color palettes for each terrain type with lighting variation.

Dependencies:
- random (for deterministic palette generation)
"""

from __future__ import annotations

import random


class PaletteGenerator:
    """Generates rich color palettes for pixel art rendering.

    Creates harmonious color schemes for each terrain type with
    multiple shades for lighting variation.

    Attributes:
        _rng: Random number generator (deterministic if seed provided)
        palettes: Dict mapping terrain ID to 8-shade palette list

    """

    def __init__(self, seed: int | None = 42):
        """Initialize the PaletteGenerator."""
        self._rng = random.Random(seed) if seed is not None else random
        self.palettes = self._generate_all_palettes()

    def _generate_all_palettes(self) -> dict[int, list[tuple[int, int, int]]]:
        """Generate 8-shade palettes for all terrain types using CC2's realistic palette."""
        return {
            # Terrain ID: [shadow, dark, mid-dark, mid, mid-light, light, highlight, bright]
            0: self._make_palette((76, 124, 35), hue_range=12, sat_range=0.08),
            1: self._make_palette((139, 119, 101), hue_range=8, sat_range=0.1),
            2: self._make_palette((58, 100, 24), hue_range=15, sat_range=0.1),
            3: self._make_palette((45, 68, 33), hue_range=10, sat_range=0.06),
            4: self._make_palette((139, 115, 85), hue_range=6, sat_range=0.04),
            5: self._make_palette((120, 118, 115), hue_range=5, sat_range=0.03),
            6: self._make_palette((62, 87, 117), hue_range=6, sat_range=0.05),
            7: self._make_palette((85, 70, 55), hue_range=10, sat_range=0.08),
            8: self._make_palette((110, 108, 105), hue_range=5, sat_range=0.03),
            9: self._make_palette((135, 115, 80), hue_range=12, sat_range=0.1),
            10: self._make_palette((95, 145, 165), hue_range=8, sat_range=0.06),
            11: self._make_palette((160, 140, 100), hue_range=10, sat_range=0.08),
            12: self._make_palette((90, 85, 75), hue_range=8, sat_range=0.06),
            13: self._make_palette((58, 40, 24), hue_range=10, sat_range=0.08),
        }

    def _make_palette(
        self,
        base_color: tuple[int, int, int],
        hue_range: float = 10,
        sat_range: float = 0.1,
    ) -> list[tuple[int, int, int]]:
        """Generate 8-shade palette from base color."""
        palette = []
        r, g, b = base_color

        for i in range(8):
            factor = 0.3 + (i * 0.1)  # 0.3 to 1.0

            vary = self._rng.uniform(-hue_range, hue_range) if i > 0 else 0
            self._rng.uniform(-sat_range, sat_range) if i > 0 else 0

            new_r = max(0, min(255, int(r * factor + vary)))
            new_g = max(0, min(255, int(g * factor + vary * 0.8)))
            new_b = max(0, min(255, int(b * factor + vary * 1.2)))

            palette.append((new_r, new_g, new_b))

        return palette

    def get_color(self, terrain_id: int, shade: int = 4) -> tuple[int, int, int]:
        """Get specific shade for terrain type.

        Args:
            terrain_id: Terrain type identifier (0-13)
            Shade level: 0-7 (0=shadow, 7=bright)

        Returns:
            RGB tuple for the requested shade

        """
        if terrain_id not in self.palettes:
            return (128, 128, 128)

        palette = self.palettes[terrain_id]
        shade = max(0, min(7, shade))
        return palette[shade]


__all__ = ["PaletteGenerator"]
