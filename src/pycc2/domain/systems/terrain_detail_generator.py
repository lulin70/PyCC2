"""
Terrain Detail Generator for PyCC2 - Phase A3

Procedurally generates terrain details (decorations, variations, height)
for enhanced maps. Transforms bare expanded maps into visually rich
battlefields that surpass original CC2.

Key Features:
- Biome-aware decoration placement (forests get trees, urban gets rubble)
- Natural distribution using noise functions (avoids grid patterns)
- Tactical feature generation (cover positions, ambush spots)
- Height map generation for visual depth and LOS effects
- Visual variation system (prevents repetitive appearance)

Usage:
    generator = TerrainDetailGenerator(seed=42)
    enhanced_map = generator.enhance_map(map_data)
"""

# PLANNED: Not yet wired into game loop — reserved for future feature

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from .enhanced_tile import (
    DecorationInstance,
    DecorationLibrary,
    DecorationType,
    EnhancedTile,
    TileConverter,
)


class BiomeType(Enum):
    """Terrain biome categories for context-aware generation."""

    GRASSLAND = auto()
    FOREST = auto()
    URBAN = auto()
    WATERFRONT = auto()
    ROCKY = auto()
    WETLAND = auto()
    MIXED = auto()


@dataclass
class GenerationConfig:
    """Configuration parameters for detail generation."""

    # Decoration densities (0.0 to 1.0)
    vegetation_density: float = 0.25  # Trees, bushes, grass
    rock_density: float = 0.08  # Rocks, boulders
    combat_damage_density: float = 0.12  # Craters, rubble, burn marks
    man_made_density: float = 0.06  # Fences, signs, obstacles

    # Height variation
    enable_height: bool = True
    max_height_variation: int = 2  # Max height difference from base
    height_smoothness: float = 0.3  # Lower = smoother terrain

    # Visual variation
    enable_variations: bool = True
    max_variations_per_terrain: int = 8  # Visual variants per terrain type

    # Tactical features
    generate_cover_positions: bool = True  # Add tactical cover spots
    generate_concealment_zones: bool = True  # Add hiding spots

    # Performance limits
    max_decorations_per_tile: int = 4  # Safety limit
    total_decoration_budget: int = 5000  # Max total decorations per map


class TerrainDetailGenerator:
    """
    Procedural terrain detail generator.

    Uses multiple noise layers and rule-based placement to create natural-looking,
    tactically interesting terrain details that make maps feel alive.
    """

    def __init__(self, seed: int | None = None, config: GenerationConfig | None = None):
        self.rng = random.Random(seed)
        self.seed = seed or 42
        self.config = config or GenerationConfig()
        self.deco_library = DecorationLibrary()

        # Pre-generate noise grids for consistency
        self._noise_cache: dict[str, list[list[float]]] = {}

    def enhance_map(self, map_data: dict[str, Any]) -> dict[str, Any]:
        """
        Enhance a map with procedural details.

        Args:
            map_data: Map data dictionary (legacy or already expanded)

        Returns:
            Enhanced map data with decorations, height, and variation
        """
        width = map_data["width"]
        height = map_data["height"]

        logger.info("🎨 Generating terrain details for %s (%d×%d)", map_data["id"], width, height)

        # Convert to enhanced tile format if needed
        if "tiles_enhanced" not in map_data:
            map_data = TileConverter.convert_map_data(map_data)

        # Load enhanced tiles
        enhanced_tiles = [
            [EnhancedTile.from_dict(td) for td in row] for row in map_data["tiles_enhanced"]
        ]

        # Generate biome map for context-aware placement
        biome_map = self._generate_biome_map(enhanced_tiles, width, height)

        # Phase 1: Height map generation
        if self.config.enable_height:
            self._generate_height_map(enhanced_tiles, width, height, biome_map)
            logger.debug("  ✓ Height map generated")

        # Phase 2: Visual variation assignment
        if self.config.enable_variations:
            self._assign_visual_variations(enhanced_tiles, width, height)
            logger.debug("  ✓ Visual variations assigned")

        # Phase 3: Decoration placement (main detail pass)
        deco_count = self._place_decorations(enhanced_tiles, width, height, biome_map)
        logger.debug("  ✓ %s decorations placed", deco_count)

        # Phase 4: Tactical feature generation
        tactical_count = 0
        if self.config.generate_cover_positions:
            tactical_count += self._generate_tactical_covers(enhanced_tiles, width, height)
        if self.config.generate_concealment_zones:
            tactical_count += self._generate_concealment_zones(enhanced_tiles, width, height)
        logger.debug("  ✓ %s tactical features added", tactical_count)

        # Update map data with enhanced tiles
        map_data["tiles_enhanced"] = [[tile.to_dict() for tile in row] for row in enhanced_tiles]
        map_data["_detail_generated"] = True
        map_data["_generation_seed"] = self.seed
        map_data["_decoration_count"] = deco_count + tactical_count

        logger.info("✅ Enhancement complete: %s total details added", deco_count + tactical_count)

        return map_data

    def _generate_biome_map(
        self, tiles: list[list[EnhancedTile]], w: int, h: int
    ) -> list[list[BiomeType]]:
        """
        Classify each tile into a biome category based on terrain type
        and neighborhood analysis.
        """
        biome_grid = [[BiomeType.MIXED for _ in range(w)] for _ in range(h)]

        for y in range(h):
            for x in range(w):
                terrain = tiles[y][x].base_terrain

                # Direct classification from terrain type
                direct_biome = {
                    0: BiomeType.GRASSLAND,
                    1: BiomeType.GRASSLAND,
                    2: BiomeType.GRASSLAND,
                    3: BiomeType.FOREST,
                    4: BiomeType.ROCKY,
                    5: BiomeType.URBAN,
                    6: BiomeType.WATERFRONT,
                    10: BiomeType.WATERFRONT,
                    7: BiomeType.GRASSLAND,  # Trench can appear anywhere
                    9: BiomeType.MIXED,  # Rough ground
                    8: BiomeType.URBAN,  # Urban variant
                    11: BiomeType.WETLAND,  # Beach/sand
                }

                primary = direct_biome.get(terrain, BiomeType.MIXED)

                # Neighborhood influence (smooth boundaries)
                neighbors = self._get_neighbor_terrains(tiles, x, y, w, h)
                neighbor_biomes = [direct_biome.get(n, BiomeType.MIXED) for n in neighbors]

                # If most neighbors agree, use dominant biome
                if len(neighbor_biomes) >= 3:
                    from collections import Counter

                    counts = Counter(neighbor_biomes)
                    dominant, count = counts.most_common(1)[0]
                    if count >= 3:
                        primary = dominant

                biome_grid[y][x] = primary

        return biome_grid

    def _get_neighbor_terrains(
        self, tiles: list[list[EnhancedTile]], x: int, y: int, w: int, h: int
    ) -> list[int]:
        """Get terrain types of neighboring tiles."""
        neighbors = []
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    neighbors.append(tiles[ny][nx].base_terrain)
        return neighbors

    def _generate_height_map(
        self, tiles: list[list[EnhancedTile]], w: int, h: int, biome_map: list[list[BiomeType]]
    ) -> None:
        """Generate natural-looking height variation across the map."""

        # Base height from terrain type
        base_heights = {
            0: 0,
            1: 0,
            2: 0,  # Flat ground
            3: 1,  # Forest slightly elevated
            4: 2,  # Rocky/hilly
            5: 0,
            8: 0,  # Buildings on flat ground
            6: -1,  # Below water level
            7: -1,  # Trenches depressed
            9: 1,  # Rough ground uneven
            11: 0,  # Beach flat
        }

        # Generate smooth noise for natural variation
        noise_scale = self.config.height_smoothness
        for y in range(h):
            for x in range(w):
                base = base_heights.get(tiles[y][x].base_terrain, 0)

                # Add Perlin-like noise
                noise_val = self._value_noise(x * noise_scale, y * noise_scale, scale=0.1)
                noise_offset = int((noise_val - 0.5) * self.config.max_height_variation * 2)

                # Clamp to allowed range
                final_height = max(
                    -self.config.max_height_variation,
                    min(self.config.max_height_variation, base + noise_offset),
                )

                tiles[y][x].height = final_height

    def _assign_visual_variations(self, tiles: list[list[EnhancedTile]], w: int, h: int) -> None:
        """Assign visual variation IDs to break up monotony."""
        for y in range(h):
            for x in range(w):
                terrain = tiles[y][x].base_terrain

                # Use position-based hash for deterministic but varied results
                hash_val = hash(x * 17 + y * 31 + terrain * 7 + self.seed) % 100
                variation = hash_val % self.config.max_variations_per_terrain

                tiles[y][x].variation = variation

    def _place_decorations(
        self, tiles: list[list[EnhancedTile]], w: int, h: int, biome_map: list[list[BiomeType]]
    ) -> int:
        """
        Place decorations based on biome rules and noise distribution.

        Returns total number of decorations placed.
        """
        total_placed = 0
        budget_remaining = self.config.total_decoration_budget

        for y in range(h):
            for x in range(w):
                if budget_remaining <= 0:
                    return total_placed

                tile = tiles[y][x]
                biome = biome_map[y][x]
                terrain = tile.base_terrain

                # Skip water tiles (no decorations on water)
                if terrain in [6]:  # Deep water
                    continue

                # Determine which decoration categories can appear here
                possible_decos = self._get_eligible_decorations(biome, terrain)
                if not possible_decos:
                    continue

                # Use noise to determine placement probability
                placement_noise = self._value_noise(x * 0.15, y * 0.15, scale=0.08)

                for deco_type, density in possible_decos:
                    if budget_remaining <= 0:
                        break

                    # Probabilistic placement based on density setting
                    adjusted_density = density * self._get_density_modifier(biome)

                    if placement_noise < adjusted_density:
                        # Create decoration instance with random variation
                        instance = self._create_decoration_instance(deco_type, x, y)

                        if tile.add_decoration(instance):
                            total_placed += 1
                            budget_remaining -= 1

                        # Advance noise to avoid clustering same type
                        placement_noise += 0.3

        return total_placed

    def _get_eligible_decorations(
        self, biome: BiomeType, terrain: int
    ) -> list[tuple[DecorationType, float]]:
        """
        Get list of (decoration_type, base_density) tuples eligible for this location.
        """
        rules = {
            BiomeType.GRASSLAND: [
                (DecorationType.BUSH_SMALL, self.config.vegetation_density * 0.4),
                (DecorationType.BUSH_DENSE, self.config.vegetation_density * 0.15),
                (DecorationType.GRASS_TUFT, self.config.vegetation_density * 0.3),
                (DecorationType.TREE_OAK, self.config.vegetation_density * 0.08),
                (DecorationType.ROCK_SMALL, self.config.rock_density * 0.6),
                (DecorationType.PUDDLE, 0.03),  # Occasional puddles
                (DecorationType.PATH_DIRT, 0.05),  # Dirt paths
                (DecorationType.SIGN_POST, self.config.man_made_density * 0.3),
            ],
            BiomeType.FOREST: [
                (DecorationType.TREE_OAK, self.config.vegetation_density * 0.3),
                (DecorationType.TREE_PINE, self.config.vegetation_density * 0.25),
                (DecorationType.BUSH_DENSE, self.config.vegetation_density * 0.35),
                (DecorationType.HEDGE_ROW, self.config.vegetation_density * 0.1),
                (DecorationType.ROCK_LARGE, self.config.rock_density * 0.4),
                (DecorationType.FLOWER_PATCH, 0.04),
            ],
            BiomeType.URBAN: [
                (DecorationType.RUBBLE_PILE, self.config.combat_damage_density * 0.5),
                (DecorationType.CRATER_SMALL, self.config.combat_damage_density * 0.2),
                (DecorationType.BURN_MARK, self.config.combat_damage_density * 0.3),
                (DecorationType.SANDBAG_WALL, self.config.man_made_density * 0.4),
                (DecorationType.FENCE_WIRE, self.config.man_made_density * 0.3),
                (DecorationType.CRATE_STACK, self.config.man_made_density * 0.2),
                (DecorationType.WRECKAGE_VEHICLE, 0.02),  # Rare vehicle wreckage
                (DecorationType.ROAD_BLOCK, self.config.man_made_density * 0.15),
            ],
            BiomeType.WATERFRONT: [
                (DecorationType.BUSH_DENSE, self.config.vegetation_density * 0.3),
                (DecorationType.ROCK_SMALL, self.config.rock_density * 0.5),
                (DecorationType.PUDDLE, 0.12),  # More puddles near water
                (DecorationType.MUD_PATCH, 0.08),
                (DecorationType.BUSH_DENSE, 0.06),  # Reeds at water edge (use bush as substitute)
            ],
            BiomeType.ROCKY: [
                (DecorationType.ROCK_LARGE, self.config.rock_density * 0.6),
                (DecorationType.ROCK_SMALL, self.config.rock_density * 0.8),
                (DecorationType.BUSH_SMALL, self.config.vegetation_density * 0.15),
                (DecorationType.GRASS_TUFT, 0.08),
            ],
            BiomeType.WETLAND: [
                (DecorationType.BUSH_DENSE, self.config.vegetation_density * 0.25),
                (DecorationType.GRASS_TUFT, self.config.vegetation_density * 0.35),
                (DecorationType.PUDDLE, 0.18),
                (DecorationType.MUD_PATCH, 0.15),
            ],
            BiomeType.MIXED: [
                (DecorationType.BUSH_SMALL, self.config.vegetation_density * 0.2),
                (DecorationType.ROCK_SMALL, self.config.rock_density * 0.3),
                (DecorationType.GRASS_TUFT, 0.12),
            ],
        }

        return rules.get(biome, [])

    def _get_density_modifier(self, biome: BiomeType) -> float:
        """Adjust decoration density based on biome characteristics."""
        modifiers = {
            BiomeType.FOREST: 1.3,  # Forests are dense
            BiomeType.URBAN: 0.9,  # Urban has less nature
            BiomeType.WATERFRONT: 1.1,  # Water edges have some vegetation
            BiomeType.ROCKY: 0.7,  # Sparse rock areas
            BiomeType.WETLAND: 1.2,  # Wetlands lush
        }
        return modifiers.get(biome, 1.0)

    def _create_decoration_instance(
        self, deco_type: DecorationType, tile_x: int, tile_y: int
    ) -> DecorationInstance:
        """Create a decoration instance with randomized properties."""
        definition = self.deco_library.get_definition(deco_type)
        size_min, size_max = definition.get("size_range", (0.8, 1.2))
        num_variants = definition.get("variants", 1)

        return DecorationInstance(
            decoration_type=deco_type,
            offset_x=self.rng.uniform(-0.4, 0.4),
            offset_y=self.rng.uniform(-0.4, 0.4),
            scale=self.rng.uniform(size_min, size_max),
            rotation=self.rng.choice([0, 90, 180, 270]),
            variant=self.rng.randint(0, max(0, num_variants - 1)),
        )

    def _generate_tactical_covers(self, tiles: list[list[EnhancedTile]], w: int, h: int) -> int:
        """
                Generate tactical cover positions (sandbags, trenches, etc.)
        in strategic locations.

                Places near objectives, between open areas, and along likely approach routes.
        """
        placed = 0

        # Find open areas that need cover
        for y in range(2, h - 2):
            for x in range(2, w - 2):
                tile = tiles[y][x]

                # Only place on open ground
                if tile.base_terrain not in [0, 1, 2, 9, 11]:
                    continue

                # Check if this is an exposed position (few neighboring covers)
                neighbor_covers = sum(
                    1
                    for dy in [-1, 0, 1]
                    for dx in [-1, 0, 1]
                    if (dx != 0 or dy != 0)
                    and 0 <= x + dx < w
                    and 0 <= y + dy < h
                    and tiles[y + dy][x + dx].total_cover_bonus >= 2
                )

                # If exposed and noise says yes, add cover
                if neighbor_covers <= 1:
                    cover_noise = self._value_noise(x * 0.1, y * 0.1, scale=0.05)
                    if cover_noise > 0.85:
                        # Choose cover type based on context
                        if self.rng.random() < 0.6:
                            deco_type = DecorationType.SANDBAG_WALL
                        else:
                            deco_type = DecorationType.TRENCH_SECTION

                        instance = self._create_decoration_instance(deco_type, x, y)
                        if tile.add_decoration(instance):
                            placed += 1

        return placed

    def _generate_concealment_zones(self, tiles: list[list[EnhancedTile]], w: int, h: int) -> int:
        """
        Generate concealment zones (bushes, camo nets) for ambush positions.

        Focuses on edges of forests, near roads, and in transition areas.
        """
        placed = 0

        for y in range(1, h - 1):
            for x in range(1, w - 1):
                tile = tiles[y][x]

                # Look for transition zones (forest next to open)
                is_forest_edge = tile.base_terrain in [0, 1, 2] and any(
                    tiles[y + dy][x + dx].base_terrain == 3
                    for dy in [-1, 0, 1]
                    for dx in [-1, 0, 1]
                    if (dx != 0 or dy != 0) and 0 <= x + dx < w and 0 <= y + dy < h
                )

                if is_forest_edge:
                    conceal_noise = self._value_noise(x * 0.12, y * 0.12, scale=0.06)
                    if conceal_noise > 0.8:
                        # Add dense bush or camo net
                        if self.rng.random() < 0.7:
                            deco_type = DecorationType.BUSH_DENSE
                        else:
                            deco_type = DecorationType.CAMOUFLAGE_NET

                        instance = self._create_decoration_instance(deco_type, x, y)
                        if tile.add_decoration(instance):
                            placed += 1

        return placed

    def _value_noise(self, x: float, y: float, scale: float = 0.1) -> float:
        """
        Simple value noise function for deterministic randomness.

        Returns value in [0, 1] range.
        """
        xi = int(x * scale)
        yi = int(y * scale)
        xf = (x * scale) - xi
        yf = (y * scale) - yi

        # Hash-based pseudo-random values at grid points
        def hash_noise(ix: int, iy: int) -> float:
            n = (ix * 374761393 + iy * 668265263 + self.seed * 1274126177) & 0x7FFFFFFF
            return (n >> 16) / 32767.0

        # Bilinear interpolation
        n00 = hash_noise(xi, yi)
        n10 = hash_noise(xi + 1, yi)
        n01 = hash_noise(xi, yi + 1)
        n11 = hash_noise(xi + 1, yi + 1)

        # Smoothstep interpolation
        sx = xf * xf * (3 - 2 * xf)
        sy = yf * yf * (3 - 2 * yf)

        ix0 = n00 + (n10 - n00) * sx
        ix1 = n01 + (n11 - n01) * sx

        return ix0 + (ix1 - ix0) * sy


def batch_enhance_maps(
    input_dir: str,
    output_dir: str | None = None,
    seed: int = 42,
    config: GenerationConfig | None = None,
) -> dict[str, Any]:
    """
    Batch process all maps in a directory.

    Args:
        input_dir: Directory containing map JSON files
        output_dir: Output directory (defaults to overwriting)
        seed: Random seed for reproducible results
        config: Generation configuration

    Returns:
        Summary statistics of enhancement process
    """
    in_path = Path(input_dir)
    out_path = Path(output_dir) if output_dir else in_path

    generator = TerrainDetailGenerator(seed=seed, config=config)

    results = {"processed": 0, "total_decorations": 0, "maps": {}}

    for map_file in sorted(in_path.glob("*.json")):
        if map_file.name.startswith("_"):
            continue

        try:
            with open(map_file) as f:
                map_data = json.load(f)

            enhanced = generator.enhance_map(map_data)

            out_file = out_path / map_file.name
            with open(out_file, "w") as f:
                json.dump(enhanced, f, indent=2)

            results["processed"] += 1
            results["total_decorations"] += enhanced.get("_decoration_count", 0)
            results["maps"][map_data["id"]] = {
                "size": f"{enhanced['width']}×{enhanced['height']}",
                "decorations": enhanced.get("_decoration_count", 0),
            }

        except (json.JSONDecodeError, OSError, ValueError, TypeError) as e:
            logger.error("❌ Error processing %s: %s", map_file.name, e)
            results["maps"][map_file.stem] = {"error": str(e)}

    return results


if __name__ == "__main__":
    # Default: enhance all maps in data/maps directory
    default_input = str(Path(__file__).resolve().parent.parent.parent.parent / "data" / "maps")

    logger.debug("=" * 80)
    logger.debug("🎨 PYCC2 TERRAIN DETAIL GENERATOR - PHASE A3")
    logger.debug("   Procedurally generating battlefield details")
    logger.debug("=" * 80)
    logger.debug("")

    results = batch_enhance_maps(default_input)

    logger.debug("")
    logger.debug("=" * 80)
    logger.debug("🎉 BATCH ENHANCEMENT COMPLETE")
    logger.debug("   Maps processed: %s", results["processed"])
    logger.debug("   Total decorations generated: %s", results["total_decorations"])
    logger.debug("=" * 80)
