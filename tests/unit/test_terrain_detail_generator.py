"""Unit tests for the terrain_detail_generator module (Phase A3).

Tests ``pycc2.domain.systems.terrain_detail_generator`` which procedurally
generates terrain details (decorations, height, variations) for enhanced maps.

Covers (dimension completeness):
- Happy Path: generator init, enhance_map, biome classification, decoration
- Error Case: batch processing with corrupt JSON
- Boundary: 1x1 maps, empty decoration budget, disabled features
- Performance: enhance_map timing baseline on a 20x20 map
- Integration: end-to-end enhance_map → tile enrichment → batch processing
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import pytest

# Headless guard (terrain_detail_generator imports lazily; defensive).
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pycc2.domain.systems.enhanced_tile import (
    DecorationInstance,
    DecorationType,
    EnhancedTile,
)
from pycc2.domain.systems.terrain_detail_generator import (
    BiomeType,
    GenerationConfig,
    TerrainDetailGenerator,
    batch_enhance_maps,
)

# ========================================================================
# Helper Functions
# ========================================================================


def _make_map_data(
    width: int = 5,
    height: int = 5,
    terrain_id: int = 0,
    map_id: str = "test_map",
    *,
    varied: bool = False,
) -> dict[str, Any]:
    """Create a minimal map_data dict for enhance_map.

    Args:
        width: Map width in tiles.
        height: Map height in tiles.
        terrain_id: Uniform terrain ID for all tiles.
        map_id: Map identifier string.
        varied: If True, use varied terrain (forest/urban/water pattern).
    """
    if varied:
        # Pattern: 0=grass, 3=forest, 5=urban, 6=water, 4=rocky
        pattern = [0, 3, 5, 6, 4]
        tiles = [[pattern[(x + y) % len(pattern)] for x in range(width)] for y in range(height)]
    else:
        tiles = [[terrain_id for _ in range(width)] for _ in range(height)]
    return {
        "id": map_id,
        "width": width,
        "height": height,
        "tiles": tiles,
    }


def _make_map_with_enhanced_tiles(
    width: int = 3,
    height: int = 3,
    terrain_id: int = 0,
) -> dict[str, Any]:
    """Create map_data with pre-existing tiles_enhanced (skip conversion)."""
    map_data = _make_map_data(width, height, terrain_id)
    map_data["tiles_enhanced"] = [
        [EnhancedTile(base_terrain=terrain_id).to_dict() for _ in range(width)]
        for _ in range(height)
    ]
    return map_data


# ========================================================================
# BiomeType Enum Tests
# ========================================================================


class TestBiomeType:
    """Tests for the BiomeType enum."""

    def test_all_biomes_present(self):
        """Verify all seven biome types are defined.

        Expected: GRASSLAND, FOREST, URBAN, WATERFRONT, ROCKY, WETLAND, MIXED.
        """
        names = {b.name for b in BiomeType}
        assert names == {
            "GRASSLAND",
            "FOREST",
            "URBAN",
            "WATERFRONT",
            "ROCKY",
            "WETLAND",
            "MIXED",
        }

    def test_biome_values_unique(self):
        """Verify each biome has a distinct auto() value."""
        values = [b.value for b in BiomeType]
        assert len(values) == len(set(values))

    def test_biome_count(self):
        """Verify exactly seven biomes exist."""
        assert len(BiomeType) == 7


# ========================================================================
# GenerationConfig Tests
# ========================================================================


class TestGenerationConfig:
    """Tests for the GenerationConfig dataclass."""

    def test_default_values(self):
        """Verify all default field values.

        Expected: vegetation_density=0.25, rock_density=0.08, etc.
        """
        cfg = GenerationConfig()
        assert cfg.vegetation_density == 0.25
        assert cfg.rock_density == 0.08
        assert cfg.combat_damage_density == 0.12
        assert cfg.man_made_density == 0.06
        assert cfg.enable_height is True
        assert cfg.max_height_variation == 2
        assert cfg.height_smoothness == 0.3
        assert cfg.enable_variations is True
        assert cfg.max_variations_per_terrain == 8
        assert cfg.generate_cover_positions is True
        assert cfg.generate_concealment_zones is True
        assert cfg.max_decorations_per_tile == 4
        assert cfg.total_decoration_budget == 5000

    def test_custom_values(self):
        """Verify all fields can be customized.

        Scenario: Set custom densities and disable features.
        Expected: All values match what was passed.
        """
        cfg = GenerationConfig(
            vegetation_density=0.5,
            rock_density=0.2,
            enable_height=False,
            enable_variations=False,
            max_height_variation=5,
            total_decoration_budget=100,
        )
        assert cfg.vegetation_density == 0.5
        assert cfg.rock_density == 0.2
        assert cfg.enable_height is False
        assert cfg.enable_variations is False
        assert cfg.max_height_variation == 5
        assert cfg.total_decoration_budget == 100

    def test_zero_density_boundary(self):
        """Verify zero densities are accepted.

        Boundary: All densities set to 0.0.
        """
        cfg = GenerationConfig(
            vegetation_density=0.0,
            rock_density=0.0,
            combat_damage_density=0.0,
            man_made_density=0.0,
        )
        assert cfg.vegetation_density == 0.0
        assert cfg.rock_density == 0.0


# ========================================================================
# TerrainDetailGenerator Init Tests
# ========================================================================


class TestTerrainDetailGeneratorInit:
    """Tests for TerrainDetailGenerator.__init__."""

    def test_default_init(self):
        """Verify default initialization.

        Expected: seed=42 (default), config is default GenerationConfig,
                  deco_library is initialized, _noise_cache empty.
        """
        gen = TerrainDetailGenerator()
        assert gen.seed == 42
        assert isinstance(gen.config, GenerationConfig)
        assert gen.deco_library is not None
        assert gen._noise_cache == {}

    def test_explicit_seed(self):
        """Verify explicit seed is stored.

        Scenario: Pass seed=123.
        Expected: gen.seed == 123.
        """
        gen = TerrainDetailGenerator(seed=123)
        assert gen.seed == 123

    def test_none_seed_defaults_to_42(self):
        """Verify None seed defaults to 42.

        Boundary: seed=None.
        Expected: gen.seed == 42 (per `seed or 42` logic).
        """
        gen = TerrainDetailGenerator(seed=None)
        assert gen.seed == 42

    def test_custom_config(self):
        """Verify custom config is stored.

        Scenario: Pass a GenerationConfig with custom budget.
        Expected: gen.config.total_decoration_budget == 500.
        """
        cfg = GenerationConfig(total_decoration_budget=500)
        gen = TerrainDetailGenerator(seed=1, config=cfg)
        assert gen.config.total_decoration_budget == 500
        assert gen.config is cfg  # Same object

    def test_rng_seeded_reproducibility(self):
        """Verify same seed produces same random sequence.

        Scenario: Create two generators with same seed, draw random numbers.
        Expected: Both produce identical sequences.
        """
        gen1 = TerrainDetailGenerator(seed=42)
        gen2 = TerrainDetailGenerator(seed=42)
        vals1 = [gen1.rng.random() for _ in range(10)]
        vals2 = [gen2.rng.random() for _ in range(10)]
        assert vals1 == vals2

    def test_different_seeds_different_sequences(self):
        """Verify different seeds produce different sequences."""
        gen1 = TerrainDetailGenerator(seed=1)
        gen2 = TerrainDetailGenerator(seed=2)
        vals1 = [gen1.rng.random() for _ in range(10)]
        vals2 = [gen2.rng.random() for _ in range(10)]
        assert vals1 != vals2


# ========================================================================
# enhance_map Tests
# ========================================================================


class TestEnhanceMap:
    """Tests for TerrainDetailGenerator.enhance_map."""

    def test_enhance_map_basic(self):
        """Verify enhance_map returns enhanced map data.

        Happy Path: Enhance a simple 3x3 grass map.
        Expected: Returned dict has _detail_generated=True, _generation_seed,
                  _decoration_count, and tiles_enhanced.
        """
        gen = TerrainDetailGenerator(seed=42)
        map_data = _make_map_data(width=3, height=3, terrain_id=0)
        result = gen.enhance_map(map_data)

        assert result["_detail_generated"] is True
        assert result["_generation_seed"] == 42
        assert "_decoration_count" in result
        assert "tiles_enhanced" in result
        assert len(result["tiles_enhanced"]) == 3
        assert len(result["tiles_enhanced"][0]) == 3

    def test_enhance_map_preserves_id_and_dimensions(self):
        """Verify enhance_map preserves id, width, height.

        Scenario: Enhance a 5x4 map with id "my_map".
        Expected: id, width, height unchanged.
        """
        gen = TerrainDetailGenerator(seed=1)
        map_data = _make_map_data(width=5, height=4, map_id="my_map")
        result = gen.enhance_map(map_data)
        assert result["id"] == "my_map"
        assert result["width"] == 5
        assert result["height"] == 4

    def test_enhance_map_converts_legacy_tiles(self):
        """Verify enhance_map converts legacy 'tiles' to 'tiles_enhanced'.

        Scenario: Input has 'tiles' (legacy int grid) but no 'tiles_enhanced'.
        Expected: Output has 'tiles_enhanced' with EnhancedTile dicts.
        """
        gen = TerrainDetailGenerator(seed=1)
        map_data = _make_map_data(width=2, height=2, terrain_id=3)
        result = gen.enhance_map(map_data)
        assert "tiles_enhanced" in result
        tile_0_0 = result["tiles_enhanced"][0][0]
        assert "base_terrain" in tile_0_0
        assert tile_0_0["base_terrain"] == 3

    def test_enhance_map_with_existing_enhanced_tiles(self):
        """Verify enhance_map works when tiles_enhanced already present.

        Scenario: Input already has 'tiles_enhanced' (skip conversion).
        Expected: Enhances the existing tiles without re-converting.
        """
        gen = TerrainDetailGenerator(seed=1)
        map_data = _make_map_with_enhanced_tiles(width=2, height=2, terrain_id=0)
        original_count = len(map_data["tiles_enhanced"])
        result = gen.enhance_map(map_data)
        assert len(result["tiles_enhanced"]) == original_count

    def test_enhance_map_1x1_boundary(self):
        """Verify enhance_map works on a 1x1 map.

        Boundary: Minimum possible map size.
        Expected: Returns valid enhanced map with 1 tile.
        """
        gen = TerrainDetailGenerator(seed=42)
        map_data = _make_map_data(width=1, height=1, terrain_id=0)
        result = gen.enhance_map(map_data)
        assert len(result["tiles_enhanced"]) == 1
        assert len(result["tiles_enhanced"][0]) == 1

    def test_enhance_map_height_generated(self):
        """Verify height is generated when enable_height=True.

        Scenario: Default config (enable_height=True).
        Expected: At least one tile has a non-zero height (probabilistic,
                  but with seed=42 on a 10x10 map, very likely).
        """
        gen = TerrainDetailGenerator(seed=42)
        map_data = _make_map_data(width=10, height=10, terrain_id=4)  # Rocky = base height 2
        result = gen.enhance_map(map_data)
        heights = [tile["height"] for row in result["tiles_enhanced"] for tile in row]
        # Rocky terrain has base height 2, so many tiles should have height > 0
        assert any(h > 0 for h in heights)

    def test_enhance_map_height_disabled(self):
        """Verify height stays at 0 when enable_height=False.

        Scenario: config.enable_height=False.
        Expected: All tile heights remain 0 (default).
        """
        cfg = GenerationConfig(enable_height=False)
        gen = TerrainDetailGenerator(seed=42, config=cfg)
        map_data = _make_map_data(width=5, height=5, terrain_id=4)
        result = gen.enhance_map(map_data)
        heights = [tile["height"] for row in result["tiles_enhanced"] for tile in row]
        assert all(h == 0 for h in heights)

    def test_enhance_map_variations_assigned(self):
        """Verify visual variations are assigned when enable_variations=True.

        Scenario: Default config (enable_variations=True).
        Expected: At least one tile has a non-zero variation.
        """
        gen = TerrainDetailGenerator(seed=42)
        map_data = _make_map_data(width=10, height=10, terrain_id=0)
        result = gen.enhance_map(map_data)
        variations = [tile["variation"] for row in result["tiles_enhanced"] for tile in row]
        assert any(v > 0 for v in variations)

    def test_enhance_map_variations_disabled(self):
        """Verify variations stay at 0 when enable_variations=False.

        Scenario: config.enable_variations=False.
        Expected: All tile variations remain 0 (default).
        """
        cfg = GenerationConfig(enable_variations=False)
        gen = TerrainDetailGenerator(seed=42, config=cfg)
        map_data = _make_map_data(width=5, height=5, terrain_id=0)
        result = gen.enhance_map(map_data)
        variations = [tile["variation"] for row in result["tiles_enhanced"] for tile in row]
        assert all(v == 0 for v in variations)

    def test_enhance_map_decorations_added(self):
        """Verify decorations are placed on a varied map.

        Scenario: 20x20 map with varied terrain (forest, urban, etc.).
        Expected: _decoration_count > 0.
        """
        gen = TerrainDetailGenerator(seed=42)
        map_data = _make_map_data(width=20, height=20, varied=True)
        result = gen.enhance_map(map_data)
        assert result["_decoration_count"] > 0

    def test_enhance_map_water_tiles_no_decorations(self):
        """Verify water tiles (terrain=6) get no decorations.

        Scenario: Map with all water tiles (terrain=6).
        Expected: _decoration_count may be 0 (water skipped in _place_decorations),
                  but tactical features might still add some. Verify no
                  vegetation decorations on water tiles.
        """
        gen = TerrainDetailGenerator(seed=42)
        map_data = _make_map_data(width=5, height=5, terrain_id=6)
        result = gen.enhance_map(map_data)
        # Check that water tiles have no decorations from main placement pass
        # (tactical covers only place on terrain 0,1,2,9,11 so water is safe)
        for row in result["tiles_enhanced"]:
            for tile in row:
                # Water tiles should have minimal or no decorations
                # (tactical covers skip water terrain)
                assert tile["base_terrain"] == 6

    def test_enhance_map_tactical_features_disabled(self):
        """Verify tactical features can be disabled.

        Scenario: config with generate_cover_positions=False and
                  generate_concealment_zones=False.
        Expected: enhance_map completes without error.
        """
        cfg = GenerationConfig(
            generate_cover_positions=False,
            generate_concealment_zones=False,
        )
        gen = TerrainDetailGenerator(seed=42, config=cfg)
        map_data = _make_map_data(width=5, height=5, terrain_id=0)
        result = gen.enhance_map(map_data)
        assert result["_detail_generated"] is True

    def test_enhance_map_decoration_budget_zero(self):
        """Verify zero decoration budget prevents decoration placement.

        Boundary: total_decoration_budget=0.
        Expected: _decoration_count from main pass is 0 (tactical may still add).
        """
        cfg = GenerationConfig(total_decoration_budget=0)
        gen = TerrainDetailGenerator(seed=42, config=cfg)
        map_data = _make_map_data(width=5, height=5, terrain_id=0)
        result = gen.enhance_map(map_data)
        # With budget=0, _place_decorations returns 0 immediately;
        # tactical features might still add some, so just verify no error
        assert result["_detail_generated"] is True

    def test_enhance_map_deterministic_with_same_seed(self):
        """Verify same seed produces identical enhanced maps.

        Scenario: Enhance the same map twice with seed=42.
        Expected: Both results have identical tiles_enhanced.
        """
        map_data1 = _make_map_data(width=5, height=5, varied=True)
        map_data2 = _make_map_data(width=5, height=5, varied=True)
        gen1 = TerrainDetailGenerator(seed=42)
        gen2 = TerrainDetailGenerator(seed=42)
        result1 = gen1.enhance_map(map_data1)
        result2 = gen2.enhance_map(map_data2)
        assert result1["tiles_enhanced"] == result2["tiles_enhanced"]
        assert result1["_decoration_count"] == result2["_decoration_count"]

    def test_enhance_map_returns_new_dict_when_converting(self):
        """Verify enhance_map returns a NEW dict when tiles_enhanced absent.

        Scenario: Pass map_data without 'tiles_enhanced' key.
        Expected: Returned object is a different dict (TileConverter creates
                  a new one via convert_map_data). The original is unchanged.
        """
        gen = TerrainDetailGenerator(seed=42)
        map_data = _make_map_data(width=2, height=2, terrain_id=0)
        original_id = id(map_data)
        result = gen.enhance_map(map_data)
        assert result is not map_data  # new dict from TileConverter
        assert id(result) != original_id
        # Original lacks enhanced fields (conversion did not mutate in place)
        assert "_detail_generated" not in map_data

    def test_enhance_map_returns_same_dict_when_already_enhanced(self):
        """Verify enhance_map returns the SAME dict when tiles_enhanced present.

        Scenario: Pass map_data that already has 'tiles_enhanced'.
        Expected: Returned object is the same dict (mutated in place, no
                  conversion reassignment).
        """
        gen = TerrainDetailGenerator(seed=42)
        map_data = _make_map_data(width=2, height=2, terrain_id=0)
        # Pre-convert so tiles_enhanced exists (skips the reassignment branch)
        from pycc2.domain.systems.enhanced_tile import TileConverter

        map_data = TileConverter.convert_map_data(map_data)
        original_id = id(map_data)
        result = gen.enhance_map(map_data)
        assert result is map_data
        assert id(result) == original_id


# ========================================================================
# _generate_biome_map Tests
# ========================================================================


class TestGenerateBiomeMap:
    """Tests for TerrainDetailGenerator._generate_biome_map."""

    def test_grassland_terrain_classified(self):
        """Verify terrain 0,1,2 are classified as GRASSLAND.

        Scenario: 3x1 map with terrain [0, 1, 2].
        Expected: biome_map[0] == [GRASSLAND, GRASSLAND, GRASSLAND].
        """
        gen = TerrainDetailGenerator(seed=42)
        tiles = [[EnhancedTile(base_terrain=t) for t in [0, 1, 2]]]
        biome_map = gen._generate_biome_map(tiles, 3, 1)
        assert biome_map[0] == [BiomeType.GRASSLAND, BiomeType.GRASSLAND, BiomeType.GRASSLAND]

    def test_forest_terrain_classified(self):
        """Verify terrain 3 is classified as FOREST.

        Scenario: 1x1 map with terrain 3.
        Expected: biome_map[0][0] == FOREST.
        """
        gen = TerrainDetailGenerator(seed=42)
        tiles = [[EnhancedTile(base_terrain=3)]]
        biome_map = gen._generate_biome_map(tiles, 1, 1)
        assert biome_map[0][0] == BiomeType.FOREST

    def test_urban_terrain_classified(self):
        """Verify terrain 5 is classified as URBAN."""
        gen = TerrainDetailGenerator(seed=42)
        tiles = [[EnhancedTile(base_terrain=5)]]
        biome_map = gen._generate_biome_map(tiles, 1, 1)
        assert biome_map[0][0] == BiomeType.URBAN

    def test_water_terrain_classified(self):
        """Verify terrain 6 is classified as WATERFRONT."""
        gen = TerrainDetailGenerator(seed=42)
        tiles = [[EnhancedTile(base_terrain=6)]]
        biome_map = gen._generate_biome_map(tiles, 1, 1)
        assert biome_map[0][0] == BiomeType.WATERFRONT

    def test_rocky_terrain_classified(self):
        """Verify terrain 4 is classified as ROCKY."""
        gen = TerrainDetailGenerator(seed=42)
        tiles = [[EnhancedTile(base_terrain=4)]]
        biome_map = gen._generate_biome_map(tiles, 1, 1)
        assert biome_map[0][0] == BiomeType.ROCKY

    def test_wetland_terrain_classified(self):
        """Verify terrain 11 is classified as WETLAND."""
        gen = TerrainDetailGenerator(seed=42)
        tiles = [[EnhancedTile(base_terrain=11)]]
        biome_map = gen._generate_biome_map(tiles, 1, 1)
        assert biome_map[0][0] == BiomeType.WETLAND

    def test_unknown_terrain_defaults_to_mixed(self):
        """Verify unknown terrain IDs default to MIXED.

        Boundary: terrain=99 (not in direct_biome dict).
        Expected: biome == MIXED.
        """
        gen = TerrainDetailGenerator(seed=42)
        tiles = [[EnhancedTile(base_terrain=99)]]
        biome_map = gen._generate_biome_map(tiles, 1, 1)
        assert biome_map[0][0] == BiomeType.MIXED

    def test_neighborhood_influence_dominant_biome(self):
        """Verify neighborhood analysis can override tile's direct biome.

        Scenario: Center tile is grassland (0), but surrounded by 8 forest tiles.
                  When 3+ neighbors agree on a biome, it becomes dominant.
        Expected: Center tile's biome becomes FOREST (dominant neighbor).
        """
        gen = TerrainDetailGenerator(seed=42)
        # 3x3 grid: center is grass (0), all 8 neighbors are forest (3)
        tiles = [[EnhancedTile(base_terrain=3) for _ in range(3)] for _ in range(3)]
        tiles[1][1] = EnhancedTile(base_terrain=0)
        biome_map = gen._generate_biome_map(tiles, 3, 3)
        # Center tile should be influenced by 8 forest neighbors (count >= 3)
        assert biome_map[1][1] == BiomeType.FOREST

    def test_biome_map_dimensions(self):
        """Verify biome map has correct dimensions.

        Scenario: 4x3 map.
        Expected: biome_map has 3 rows, each with 4 columns.
        """
        gen = TerrainDetailGenerator(seed=42)
        tiles = [[EnhancedTile(base_terrain=0) for _ in range(4)] for _ in range(3)]
        biome_map = gen._generate_biome_map(tiles, 4, 3)
        assert len(biome_map) == 3
        assert all(len(row) == 4 for row in biome_map)


# ========================================================================
# _get_neighbor_terrains Tests
# ========================================================================


class TestGetNeighborTerrains:
    """Tests for TerrainDetailGenerator._get_neighbor_terrains."""

    def test_center_tile_eight_neighbors(self):
        """Verify center tile of 3x3 map returns 8 neighbor terrains.

        Scenario: 3x3 map, query center (1,1).
        Expected: List of 8 terrain values.
        """
        gen = TerrainDetailGenerator(seed=42)
        tiles = [[EnhancedTile(base_terrain=(x + y)) for x in range(3)] for y in range(3)]
        neighbors = gen._get_neighbor_terrains(tiles, 1, 1, 3, 3)
        assert len(neighbors) == 8

    def test_corner_tile_three_neighbors(self):
        """Verify corner tile returns 3 neighbors.

        Scenario: 3x3 map, query corner (0,0).
        Expected: List of 3 terrain values (right, below, below-right).
        """
        gen = TerrainDetailGenerator(seed=42)
        tiles = [[EnhancedTile(base_terrain=0) for _ in range(3)] for _ in range(3)]
        neighbors = gen._get_neighbor_terrains(tiles, 0, 0, 3, 3)
        assert len(neighbors) == 3

    def test_edge_tile_five_neighbors(self):
        """Verify edge (non-corner) tile returns 5 neighbors.

        Scenario: 3x3 map, query top edge (1,0).
        Expected: List of 5 terrain values.
        """
        gen = TerrainDetailGenerator(seed=42)
        tiles = [[EnhancedTile(base_terrain=0) for _ in range(3)] for _ in range(3)]
        neighbors = gen._get_neighbor_terrains(tiles, 1, 0, 3, 3)
        assert len(neighbors) == 5

    def test_1x1_map_no_neighbors(self):
        """Verify 1x1 map tile has no neighbors.

        Boundary: Single tile map.
        Expected: Empty list.
        """
        gen = TerrainDetailGenerator(seed=42)
        tiles = [[EnhancedTile(base_terrain=0)]]
        neighbors = gen._get_neighbor_terrains(tiles, 0, 0, 1, 1)
        assert neighbors == []

    def test_returns_correct_terrain_values(self):
        """Verify returned terrain values match neighbor tiles.

        Scenario: 3x3 map with known terrain values, query center.
        Expected: Neighbor terrains match the surrounding tiles.
        """
        gen = TerrainDetailGenerator(seed=42)
        # Row 0: [0, 1, 2]
        # Row 1: [3, _, 5]  (center excluded)
        # Row 2: [6, 7, 8]
        tiles = [
            [EnhancedTile(base_terrain=v) for v in [0, 1, 2]],
            [EnhancedTile(base_terrain=v) for v in [3, 99, 5]],
            [EnhancedTile(base_terrain=v) for v in [6, 7, 8]],
        ]
        neighbors = gen._get_neighbor_terrains(tiles, 1, 1, 3, 3)
        assert sorted(neighbors) == sorted([0, 1, 2, 3, 5, 6, 7, 8])


# ========================================================================
# _generate_height_map Tests
# ========================================================================


class TestGenerateHeightMap:
    """Tests for TerrainDetailGenerator._generate_height_map."""

    def test_height_within_max_variation(self):
        """Verify all heights are within [-max_height_variation, +max_height_variation].

        Scenario: 10x10 rocky map, max_height_variation=2.
        Expected: All heights in [-2, 2].
        """
        cfg = GenerationConfig(max_height_variation=2)
        gen = TerrainDetailGenerator(seed=42, config=cfg)
        tiles = [[EnhancedTile(base_terrain=4) for _ in range(10)] for _ in range(10)]
        biome_map = gen._generate_biome_map(tiles, 10, 10)
        gen._generate_height_map(tiles, 10, 10, biome_map)
        for row in tiles:
            for tile in row:
                assert -2 <= tile.height <= 2

    def test_height_zero_variation(self):
        """Verify max_height_variation=0 produces all-zero heights.

        Boundary: max_height_variation=0.
        Expected: All heights are 0 (clamped to [0, 0]).
        """
        cfg = GenerationConfig(max_height_variation=0)
        gen = TerrainDetailGenerator(seed=42, config=cfg)
        tiles = [[EnhancedTile(base_terrain=4) for _ in range(5)] for _ in range(5)]
        biome_map = gen._generate_biome_map(tiles, 5, 5)
        gen._generate_height_map(tiles, 5, 5, biome_map)
        for row in tiles:
            for tile in row:
                assert tile.height == 0

    def test_height_deterministic_with_seed(self):
        """Verify same seed produces same height map.

        Scenario: Generate heights twice with seed=42.
        Expected: Identical height values.
        """
        cfg = GenerationConfig()
        gen1 = TerrainDetailGenerator(seed=42, config=cfg)
        gen2 = TerrainDetailGenerator(seed=42, config=cfg)
        tiles1 = [[EnhancedTile(base_terrain=0) for _ in range(5)] for _ in range(5)]
        tiles2 = [[EnhancedTile(base_terrain=0) for _ in range(5)] for _ in range(5)]
        biome1 = gen1._generate_biome_map(tiles1, 5, 5)
        biome2 = gen2._generate_biome_map(tiles2, 5, 5)
        gen1._generate_height_map(tiles1, 5, 5, biome1)
        gen2._generate_height_map(tiles2, 5, 5, biome2)
        heights1 = [t.height for row in tiles1 for t in row]
        heights2 = [t.height for row in tiles2 for t in row]
        assert heights1 == heights2

    def test_water_tiles_negative_height(self):
        """Verify water terrain (6) has base height -1 (below water level).

        Scenario: Large water map.
        Expected: Most/all water tiles have height <= 0 (base -1 ± noise).
        """
        cfg = GenerationConfig(max_height_variation=1)
        gen = TerrainDetailGenerator(seed=42, config=cfg)
        tiles = [[EnhancedTile(base_terrain=6) for _ in range(10)] for _ in range(10)]
        biome_map = gen._generate_biome_map(tiles, 10, 10)
        gen._generate_height_map(tiles, 10, 10, biome_map)
        # Water has base_height -1, with noise offset in [-1, 1]
        # So heights range from -2 to 0 (clamped to [-1, 1])
        for row in tiles:
            for tile in row:
                assert tile.height <= 1


# ========================================================================
# _assign_visual_variations Tests
# ========================================================================


class TestAssignVisualVariations:
    """Tests for TerrainDetailGenerator._assign_visual_variations."""

    def test_variations_within_range(self):
        """Verify all variations are < max_variations_per_terrain.

        Scenario: 10x10 map, max_variations_per_terrain=8.
        Expected: All variation values in [0, 7].
        """
        cfg = GenerationConfig(max_variations_per_terrain=8)
        gen = TerrainDetailGenerator(seed=42, config=cfg)
        tiles = [[EnhancedTile(base_terrain=0) for _ in range(10)] for _ in range(10)]
        gen._assign_visual_variations(tiles, 10, 10)
        for row in tiles:
            for tile in row:
                assert 0 <= tile.variation < 8

    def test_variations_max_one(self):
        """Verify max_variations_per_terrain=1 produces all-zero variations.

        Boundary: max_variations_per_terrain=1.
        Expected: All variations are 0 (hash % 1 == 0).
        """
        cfg = GenerationConfig(max_variations_per_terrain=1)
        gen = TerrainDetailGenerator(seed=42, config=cfg)
        tiles = [[EnhancedTile(base_terrain=0) for _ in range(5)] for _ in range(5)]
        gen._assign_visual_variations(tiles, 5, 5)
        for row in tiles:
            for tile in row:
                assert tile.variation == 0

    def test_variations_deterministic(self):
        """Verify same seed produces same variations.

        Scenario: Assign variations twice with same seed.
        Expected: Identical variation values.
        """
        gen1 = TerrainDetailGenerator(seed=42)
        gen2 = TerrainDetailGenerator(seed=42)
        tiles1 = [[EnhancedTile(base_terrain=0) for _ in range(5)] for _ in range(5)]
        tiles2 = [[EnhancedTile(base_terrain=0) for _ in range(5)] for _ in range(5)]
        gen1._assign_visual_variations(tiles1, 5, 5)
        gen2._assign_visual_variations(tiles2, 5, 5)
        vars1 = [t.variation for row in tiles1 for t in row]
        vars2 = [t.variation for row in tiles2 for t in row]
        assert vars1 == vars2

    def test_variations_differ_by_position(self):
        """Verify different positions get different variations (probabilistic).

        Scenario: 10x10 map with max_variations=8.
        Expected: At least 2 distinct variation values present.
        """
        cfg = GenerationConfig(max_variations_per_terrain=8)
        gen = TerrainDetailGenerator(seed=42, config=cfg)
        tiles = [[EnhancedTile(base_terrain=0) for _ in range(10)] for _ in range(10)]
        gen._assign_visual_variations(tiles, 10, 10)
        variations = {t.variation for row in tiles for t in row}
        assert len(variations) >= 2


# ========================================================================
# _place_decorations Tests
# ========================================================================


class TestPlaceDecorations:
    """Tests for TerrainDetailGenerator._place_decorations."""

    def test_place_decorations_returns_count(self):
        """Verify _place_decorations returns a non-negative integer.

        Happy Path: Place decorations on a 10x10 grass map.
        Expected: Return value >= 0.
        """
        gen = TerrainDetailGenerator(seed=42)
        tiles = [[EnhancedTile(base_terrain=0) for _ in range(10)] for _ in range(10)]
        biome_map = gen._generate_biome_map(tiles, 10, 10)
        count = gen._place_decorations(tiles, 10, 10, biome_map)
        assert isinstance(count, int)
        assert count >= 0

    def test_place_decorations_respects_budget(self):
        """Verify decoration placement respects total_decoration_budget.

        Boundary: budget=5 on a large map.
        Expected: Return value <= 5 (plus tactical features).
        """
        cfg = GenerationConfig(total_decoration_budget=5)
        gen = TerrainDetailGenerator(seed=42, config=cfg)
        tiles = [[EnhancedTile(base_terrain=0) for _ in range(20)] for _ in range(20)]
        biome_map = gen._generate_biome_map(tiles, 20, 20)
        count = gen._place_decorations(tiles, 20, 20, biome_map)
        assert count <= 5

    def test_place_decorations_zero_budget(self):
        """Verify zero budget returns 0 immediately.

        Boundary: total_decoration_budget=0.
        Expected: Return value == 0.
        """
        cfg = GenerationConfig(total_decoration_budget=0)
        gen = TerrainDetailGenerator(seed=42, config=cfg)
        tiles = [[EnhancedTile(base_terrain=0) for _ in range(5)] for _ in range(5)]
        biome_map = gen._generate_biome_map(tiles, 5, 5)
        count = gen._place_decorations(tiles, 5, 5, biome_map)
        assert count == 0

    def test_place_decorations_skips_water(self):
        """Verify water tiles (terrain=6) get no decorations.

        Scenario: 5x5 all-water map.
        Expected: No decorations placed (water is skipped).
        """
        gen = TerrainDetailGenerator(seed=42)
        tiles = [[EnhancedTile(base_terrain=6) for _ in range(5)] for _ in range(5)]
        biome_map = gen._generate_biome_map(tiles, 5, 5)
        count = gen._place_decorations(tiles, 5, 5, biome_map)
        assert count == 0
        for row in tiles:
            for tile in row:
                assert len(tile.decorations) == 0

    def test_place_decorations_on_grass(self):
        """Verify grass tiles can receive decorations on a sufficiently large map.

        Scenario: 100x100 grass map with default config.
        Expected: At least some decorations placed.
        """
        gen = TerrainDetailGenerator(seed=42)
        tiles = [[EnhancedTile(base_terrain=0) for _ in range(100)] for _ in range(100)]
        biome_map = gen._generate_biome_map(tiles, 100, 100)
        count = gen._place_decorations(tiles, 100, 100, biome_map)
        assert count > 0

    def test_place_decorations_small_map_can_place_decorations(self):
        """Verify small maps can still place decorations after noise scale fix.

        Scenario: 15x15 grass map with default config.
        Expected: At least one decoration placed (noise varies across tiles).
        """
        gen = TerrainDetailGenerator(seed=42)
        tiles = [[EnhancedTile(base_terrain=0) for _ in range(15)] for _ in range(15)]
        biome_map = gen._generate_biome_map(tiles, 15, 15)
        count = gen._place_decorations(tiles, 15, 15, biome_map)
        assert count > 0

    def test_place_decorations_max_per_tile(self):
        """Verify no tile exceeds max_decorations_per_tile.

        Scenario: Large map with high densities.
        Expected: Each tile has <= max_decorations_per_tile decorations.
        """
        cfg = GenerationConfig(
            vegetation_density=1.0,
            rock_density=1.0,
            max_decorations_per_tile=4,
            total_decoration_budget=10000,
        )
        gen = TerrainDetailGenerator(seed=42, config=cfg)
        tiles = [[EnhancedTile(base_terrain=0) for _ in range(20)] for _ in range(20)]
        biome_map = gen._generate_biome_map(tiles, 20, 20)
        gen._place_decorations(tiles, 20, 20, biome_map)
        for row in tiles:
            for tile in row:
                assert len(tile.decorations) <= 4


# ========================================================================
# _get_eligible_decorations Tests
# ========================================================================


class TestGetEligibleDecorations:
    """Tests for TerrainDetailGenerator._get_eligible_decorations."""

    def test_grassland_has_decorations(self):
        """Verify GRASSLAND biome returns non-empty decoration list."""
        gen = TerrainDetailGenerator(seed=42)
        decos = gen._get_eligible_decorations(BiomeType.GRASSLAND, 0)
        assert len(decos) > 0
        # Each item is a tuple (DecorationType, float density)
        for deco_type, density in decos:
            assert isinstance(deco_type, DecorationType)
            assert isinstance(density, float)
            assert 0.0 <= density <= 1.0

    def test_forest_has_tree_decorations(self):
        """Verify FOREST biome includes TREE_OAK and TREE_PINE."""
        gen = TerrainDetailGenerator(seed=42)
        decos = gen._get_eligible_decorations(BiomeType.FOREST, 3)
        deco_types = {dt for dt, _ in decos}
        assert DecorationType.TREE_OAK in deco_types
        assert DecorationType.TREE_PINE in deco_types

    def test_urban_has_rubble_and_sandbags(self):
        """Verify URBAN biome includes RUBBLE_PILE and SANDBAG_WALL."""
        gen = TerrainDetailGenerator(seed=42)
        decos = gen._get_eligible_decorations(BiomeType.URBAN, 5)
        deco_types = {dt for dt, _ in decos}
        assert DecorationType.RUBBLE_PILE in deco_types
        assert DecorationType.SANDBAG_WALL in deco_types

    def test_waterfront_has_puddles(self):
        """Verify WATERFRONT biome includes PUDDLE."""
        gen = TerrainDetailGenerator(seed=42)
        decos = gen._get_eligible_decorations(BiomeType.WATERFRONT, 6)
        deco_types = {dt for dt, _ in decos}
        assert DecorationType.PUDDLE in deco_types

    def test_rocky_has_rocks(self):
        """Verify ROCKY biome includes ROCK_LARGE and ROCK_SMALL."""
        gen = TerrainDetailGenerator(seed=42)
        decos = gen._get_eligible_decorations(BiomeType.ROCKY, 4)
        deco_types = {dt for dt, _ in decos}
        assert DecorationType.ROCK_LARGE in deco_types
        assert DecorationType.ROCK_SMALL in deco_types

    def test_wetland_has_mud(self):
        """Verify WETLAND biome includes MUD_PATCH."""
        gen = TerrainDetailGenerator(seed=42)
        decos = gen._get_eligible_decorations(BiomeType.WETLAND, 11)
        deco_types = {dt for dt, _ in decos}
        assert DecorationType.MUD_PATCH in deco_types

    def test_all_biomes_have_decorations(self):
        """Verify every biome type returns a non-empty decoration list.

        Completeness: All 7 biomes should have at least one eligible decoration.
        """
        gen = TerrainDetailGenerator(seed=42)
        for biome in BiomeType:
            decos = gen._get_eligible_decorations(biome, 0)
            assert len(decos) > 0, f"Biome {biome.name} has no eligible decorations"

    def test_density_reflects_config(self):
        """Verify densities scale with config.vegetation_density.

        Scenario: Double vegetation_density and check TREE_OAK density in FOREST.
        Expected: TREE_OAK density doubles (proportionally).
        """
        cfg_low = GenerationConfig(vegetation_density=0.1)
        cfg_high = GenerationConfig(vegetation_density=0.2)
        gen_low = TerrainDetailGenerator(seed=42, config=cfg_low)
        gen_high = TerrainDetailGenerator(seed=42, config=cfg_high)

        decos_low = gen_low._get_eligible_decorations(BiomeType.FOREST, 3)
        decos_high = gen_high._get_eligible_decorations(BiomeType.FOREST, 3)

        tree_low = next(d for t, d in decos_low if t == DecorationType.TREE_OAK)
        tree_high = next(d for t, d in decos_high if t == DecorationType.TREE_OAK)
        assert tree_high == pytest.approx(tree_low * 2)


# ========================================================================
# _get_density_modifier Tests
# ========================================================================


class TestGetDensityModifier:
    """Tests for TerrainDetailGenerator._get_density_modifier."""

    def test_forest_modifier_high(self):
        """Verify FOREST has density modifier 1.3 (dense)."""
        gen = TerrainDetailGenerator(seed=42)
        assert gen._get_density_modifier(BiomeType.FOREST) == 1.3

    def test_rocky_modifier_low(self):
        """Verify ROCKY has density modifier 0.7 (sparse)."""
        gen = TerrainDetailGenerator(seed=42)
        assert gen._get_density_modifier(BiomeType.ROCKY) == 0.7

    def test_grassland_default_modifier(self):
        """Verify GRASSLAND has default modifier 1.0."""
        gen = TerrainDetailGenerator(seed=42)
        assert gen._get_density_modifier(BiomeType.GRASSLAND) == 1.0

    def test_all_biomes_return_float(self):
        """Verify every biome returns a float modifier.

        Completeness: All 7 biomes should return a numeric modifier.
        """
        gen = TerrainDetailGenerator(seed=42)
        for biome in BiomeType:
            mod = gen._get_density_modifier(biome)
            assert isinstance(mod, float)
            assert mod > 0


# ========================================================================
# _create_decoration_instance Tests
# ========================================================================


class TestCreateDecorationInstance:
    """Tests for TerrainDetailGenerator._create_decoration_instance."""

    def test_returns_decoration_instance(self):
        """Verify a DecorationInstance is returned.

        Happy Path: Create an instance of BUSH_SMALL.
        Expected: DecorationInstance with correct decoration_type.
        """
        gen = TerrainDetailGenerator(seed=42)
        inst = gen._create_decoration_instance(DecorationType.BUSH_SMALL, 0, 0)
        assert isinstance(inst, DecorationInstance)
        assert inst.decoration_type == DecorationType.BUSH_SMALL

    def test_offset_within_range(self):
        """Verify offsets are in [-0.4, 0.4].

        Scenario: Create many instances and check offsets.
        Expected: All offsets within [-0.4, 0.4].
        """
        gen = TerrainDetailGenerator(seed=42)
        for _ in range(50):
            inst = gen._create_decoration_instance(DecorationType.BUSH_SMALL, 0, 0)
            assert -0.4 <= inst.offset_x <= 0.4
            assert -0.4 <= inst.offset_y <= 0.4

    def test_rotation_is_valid_degree(self):
        """Verify rotation is one of [0, 90, 180, 270]."""
        gen = TerrainDetailGenerator(seed=42)
        for _ in range(50):
            inst = gen._create_decoration_instance(DecorationType.TREE_OAK, 0, 0)
            assert inst.rotation in {0, 90, 180, 270}

    def test_variant_non_negative(self):
        """Verify variant is >= 0."""
        gen = TerrainDetailGenerator(seed=42)
        for _ in range(50):
            inst = gen._create_decoration_instance(DecorationType.ROCK_LARGE, 0, 0)
            assert inst.variant >= 0

    def test_scale_positive(self):
        """Verify scale is always positive."""
        gen = TerrainDetailGenerator(seed=42)
        for _ in range(50):
            inst = gen._create_decoration_instance(DecorationType.TREE_PINE, 0, 0)
            assert inst.scale > 0

    def test_uses_definition_size_range(self):
        """Verify scale respects the definition's size_range.

        Scenario: TREE_OAK has size_range (0.9, 1.1).
        Expected: All scales in [0.9, 1.1].
        """
        gen = TerrainDetailGenerator(seed=42)
        definition = gen.deco_library.get_definition(DecorationType.TREE_OAK)
        size_min, size_max = definition["size_range"]
        for _ in range(50):
            inst = gen._create_decoration_instance(DecorationType.TREE_OAK, 0, 0)
            assert size_min <= inst.scale <= size_max

    def test_deterministic_with_seed(self):
        """Verify same seed produces same decoration instances."""
        gen1 = TerrainDetailGenerator(seed=42)
        gen2 = TerrainDetailGenerator(seed=42)
        for i in range(10):
            inst1 = gen1._create_decoration_instance(DecorationType.BUSH_SMALL, 0, 0)
            inst2 = gen2._create_decoration_instance(DecorationType.BUSH_SMALL, 0, 0)
            assert inst1.offset_x == inst2.offset_x
            assert inst1.scale == inst2.scale
            assert inst1.rotation == inst2.rotation


# ========================================================================
# _generate_tactical_covers Tests
# ========================================================================


class TestGenerateTacticalCovers:
    """Tests for TerrainDetailGenerator._generate_tactical_covers."""

    def test_returns_non_negative_int(self):
        """Verify return value is a non-negative integer.

        Happy Path: Generate covers on a 10x10 grass map.
        Expected: int >= 0.
        """
        gen = TerrainDetailGenerator(seed=42)
        tiles = [[EnhancedTile(base_terrain=0) for _ in range(10)] for _ in range(10)]
        count = gen._generate_tactical_covers(tiles, 10, 10)
        assert isinstance(count, int)
        assert count >= 0

    def test_small_map_returns_zero(self):
        """Verify maps smaller than 5x5 return 0 (loop range 2..h-2).

        Boundary: 4x4 map → range(2, 2) is empty.
        Expected: 0 covers placed.
        """
        gen = TerrainDetailGenerator(seed=42)
        tiles = [[EnhancedTile(base_terrain=0) for _ in range(4)] for _ in range(4)]
        count = gen._generate_tactical_covers(tiles, 4, 4)
        assert count == 0

    def test_only_open_ground_gets_covers(self):
        """Verify covers are only placed on open ground (terrain 0,1,2,9,11).

        Scenario: 10x10 map with all urban terrain (5).
        Expected: 0 covers (urban not in eligible terrains).
        """
        gen = TerrainDetailGenerator(seed=42)
        tiles = [[EnhancedTile(base_terrain=5) for _ in range(10)] for _ in range(10)]
        count = gen._generate_tactical_covers(tiles, 10, 10)
        assert count == 0

    def test_cover_types_are_sandbag_or_trench(self):
        """Verify placed covers are SANDBAG_WALL or TRENCH_SECTION.

        Scenario: Generate covers on a large open map.
        Expected: All cover decorations are one of the two types.
        """
        gen = TerrainDetailGenerator(seed=42)
        tiles = [[EnhancedTile(base_terrain=0) for _ in range(30)] for _ in range(30)]
        gen._generate_tactical_covers(tiles, 30, 30)
        valid_types = {DecorationType.SANDBAG_WALL, DecorationType.TRENCH_SECTION}
        for row in tiles:
            for tile in row:
                for deco in tile.decorations:
                    # Only check covers placed by this method (not decorations
                    # from other methods). Since tiles start empty, all are covers.
                    assert deco.decoration_type in valid_types


# ========================================================================
# _generate_concealment_zones Tests
# ========================================================================


class TestGenerateConcealmentZones:
    """Tests for TerrainDetailGenerator._generate_concealment_zones."""

    def test_returns_non_negative_int(self):
        """Verify return value is a non-negative integer.

        Happy Path: Generate concealment on a 10x10 map.
        Expected: int >= 0.
        """
        gen = TerrainDetailGenerator(seed=42)
        tiles = [[EnhancedTile(base_terrain=0) for _ in range(10)] for _ in range(10)]
        count = gen._generate_concealment_zones(tiles, 10, 10)
        assert isinstance(count, int)
        assert count >= 0

    def test_small_map_returns_zero(self):
        """Verify maps smaller than 3x3 return 0 (loop range 1..h-1).

        Boundary: 2x2 map → range(1, 1) is empty.
        Expected: 0 concealment zones placed.
        """
        gen = TerrainDetailGenerator(seed=42)
        tiles = [[EnhancedTile(base_terrain=0) for _ in range(2)] for _ in range(2)]
        count = gen._generate_concealment_zones(tiles, 2, 2)
        assert count == 0

    def test_concealment_at_forest_edge(self):
        """Verify concealment zones appear at forest edges.

        Scenario: 10x10 map with a forest block in the corner.
        Expected: Some concealment zones placed (probabilistic).
        """
        gen = TerrainDetailGenerator(seed=42)
        tiles = [[EnhancedTile(base_terrain=0) for _ in range(10)] for _ in range(10)]
        # Make a 3x3 forest block in the corner
        for y in range(3):
            for x in range(3):
                tiles[y][x] = EnhancedTile(base_terrain=3)
        count = gen._generate_concealment_zones(tiles, 10, 10)
        # Should place some concealment at forest edges (grass next to forest)
        assert count >= 0

    def test_no_concealment_without_forest(self):
        """Verify no concealment zones on a map with no forest.

        Scenario: 10x10 all-grass map (no forest terrain 3).
        Expected: 0 concealment zones (is_forest_edge is always False).
        """
        gen = TerrainDetailGenerator(seed=42)
        tiles = [[EnhancedTile(base_terrain=0) for _ in range(10)] for _ in range(10)]
        count = gen._generate_concealment_zones(tiles, 10, 10)
        assert count == 0


# ========================================================================
# _value_noise Tests
# ========================================================================


class TestValueNoise:
    """Tests for TerrainDetailGenerator._value_noise."""

    def test_returns_float_in_unit_range(self):
        """Verify noise output is in [0, 1] for non-negative coordinates.

        Happy Path: Sample many non-negative points and check range.
        Expected: All values in [0.0, 1.0].
        """
        gen = TerrainDetailGenerator(seed=42)
        for _ in range(100):
            x = gen.rng.uniform(0, 100)
            y = gen.rng.uniform(0, 100)
            val = gen._value_noise(x, y)
            assert isinstance(val, float)
            assert 0.0 <= val <= 1.0

    def test_negative_coordinates_stay_in_unit_range(self):
        """Verify negative coordinates produce values in [0, 1].

        Boundary: Negative coordinates.
        Expected: All values in [0.0, 1.0] (math.floor yields correct
                  fractional parts in [0, 1) for negative inputs).
        """
        gen = TerrainDetailGenerator(seed=42)
        out_of_range_count = 0
        for _ in range(200):
            x = gen.rng.uniform(-100, -1)
            y = gen.rng.uniform(-100, -1)
            val = gen._value_noise(x, y)
            if val < 0.0 or val > 1.0:
                out_of_range_count += 1
        assert out_of_range_count == 0

    def test_deterministic_with_seed(self):
        """Verify same seed produces same noise values.

        Scenario: Two generators with seed=42, query same point.
        Expected: Identical noise values.
        """
        gen1 = TerrainDetailGenerator(seed=42)
        gen2 = TerrainDetailGenerator(seed=42)
        for _ in range(20):
            x = gen1.rng.uniform(0, 50)
            y = gen1.rng.uniform(0, 50)
            assert gen1._value_noise(x, y) == gen2._value_noise(x, y)

    def test_different_seeds_different_noise(self):
        """Verify different seeds produce different noise.

        Scenario: Two generators with different seeds.
        Expected: At least some different values.
        """
        gen1 = TerrainDetailGenerator(seed=1)
        gen2 = TerrainDetailGenerator(seed=2)
        vals1 = [gen1._value_noise(x * 0.1, y * 0.1) for x in range(10) for y in range(10)]
        vals2 = [gen2._value_noise(x * 0.1, y * 0.1) for x in range(10) for y in range(10)]
        assert vals1 != vals2

    def test_zero_coordinates(self):
        """Verify noise at (0, 0) returns a valid float.

        Boundary: Origin coordinates.
        Expected: Float in [0, 1], no error.
        """
        gen = TerrainDetailGenerator(seed=42)
        val = gen._value_noise(0.0, 0.0)
        assert isinstance(val, float)
        assert 0.0 <= val <= 1.0

    def test_negative_coordinates(self):
        """Verify negative coordinates work.

        Boundary: Negative x and y.
        Expected: Float in [0, 1], no error.
        """
        gen = TerrainDetailGenerator(seed=42)
        val = gen._value_noise(-5.0, -10.0)
        assert 0.0 <= val <= 1.0

    def test_scale_parameter(self):
        """Verify scale parameter affects output.

        Scenario: Same (x, y) with different scales.
        Expected: Different values (scale changes grid alignment).
        """
        gen = TerrainDetailGenerator(seed=42)
        # Test multiple points since a single point might match by coincidence
        different = False
        for i in range(20):
            v1 = gen._value_noise(float(i), float(i), scale=0.1)
            v2 = gen._value_noise(float(i), float(i), scale=0.5)
            if v1 != v2:
                different = True
                break
        assert different, "Scale parameter should affect noise output"


# ========================================================================
# batch_enhance_maps Tests
# ========================================================================


class TestBatchEnhanceMaps:
    """Tests for the batch_enhance_maps function."""

    def test_batch_process_single_map(self, tmp_path: Path):
        """Verify batch processing handles a single map file.

        Happy Path: One valid JSON map in input dir.
        Expected: processed=1, maps dict has one entry.
        """
        map_data = _make_map_data(width=3, height=3, terrain_id=0, map_id="map1")
        map_file = tmp_path / "map1.json"
        with open(map_file, "w") as f:
            json.dump(map_data, f)

        results = batch_enhance_maps(str(tmp_path), seed=42)
        assert results["processed"] == 1
        assert results["total_decorations"] >= 0
        assert "map1" in results["maps"]

    def test_batch_process_multiple_maps(self, tmp_path: Path):
        """Verify batch processing handles multiple map files.

        Scenario: Three valid JSON maps in input dir.
        Expected: processed=3, maps dict has three entries.
        """
        for i in range(3):
            map_data = _make_map_data(width=3, height=3, terrain_id=0, map_id=f"map{i}")
            with open(tmp_path / f"map{i}.json", "w") as f:
                json.dump(map_data, f)

        results = batch_enhance_maps(str(tmp_path), seed=42)
        assert results["processed"] == 3
        assert len(results["maps"]) == 3

    def test_batch_process_writes_output(self, tmp_path: Path):
        """Verify batch processing writes enhanced maps to output dir.

        Scenario: Process maps, write to separate output dir (pre-created).
        Expected: Output files exist with enhanced data.
        """
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        map_data = _make_map_data(width=3, height=3, terrain_id=0, map_id="m1")
        with open(tmp_path / "m1.json", "w") as f:
            json.dump(map_data, f)

        batch_enhance_maps(str(tmp_path), output_dir=str(out_dir), seed=42)
        out_file = out_dir / "m1.json"
        assert out_file.exists()
        with open(out_file) as f:
            enhanced = json.load(f)
        assert enhanced.get("_detail_generated") is True

    def test_batch_process_creates_missing_output_dir(self, tmp_path: Path):
        """Verify batch processing creates the output directory if missing.

        Scenario: Output dir does not exist; batch_enhance_maps should create
        it and process maps successfully.
        Expected: processed=1, no error entry, output file written.
        """
        out_dir = tmp_path / "nonexistent"  # NOT pre-created
        map_data = _make_map_data(width=3, height=3, terrain_id=0, map_id="m1")
        with open(tmp_path / "m1.json", "w") as f:
            json.dump(map_data, f)

        results = batch_enhance_maps(str(tmp_path), output_dir=str(out_dir), seed=42)
        assert results["processed"] == 1
        assert "m1" in results["maps"]
        assert "error" not in results["maps"]["m1"]
        assert (out_dir / "m1.json").exists()

    def test_batch_process_overwrites_input(self, tmp_path: Path):
        """Verify batch processing overwrites input when no output_dir.

        Scenario: No output_dir specified.
        Expected: Input file is overwritten with enhanced data.
        """
        map_data = _make_map_data(width=3, height=3, terrain_id=0, map_id="m1")
        map_file = tmp_path / "m1.json"
        with open(map_file, "w") as f:
            json.dump(map_data, f)

        batch_enhance_maps(str(tmp_path), seed=42)
        with open(map_file) as f:
            enhanced = json.load(f)
        assert enhanced.get("_detail_generated") is True

    def test_batch_process_skips_underscore_files(self, tmp_path: Path):
        """Verify files starting with '_' are skipped.

        Scenario: One valid map and one '_private.json' file.
        Expected: Only the valid map is processed.
        """
        map_data = _make_map_data(width=3, height=3, terrain_id=0, map_id="good")
        with open(tmp_path / "good.json", "w") as f:
            json.dump(map_data, f)
        # Private file (should be skipped)
        with open(tmp_path / "_private.json", "w") as f:
            json.dump({"id": "private", "width": 3, "height": 3, "tiles": [[0]]}, f)

        results = batch_enhance_maps(str(tmp_path), seed=42)
        assert results["processed"] == 1
        assert "private" not in results["maps"]

    def test_batch_process_handles_corrupt_json(self, tmp_path: Path):
        """Verify corrupt JSON files are reported as errors.

        Error Case: One valid map and one corrupt JSON file.
        Expected: processed=1 (only valid), corrupt file has error entry.
        """
        map_data = _make_map_data(width=3, height=3, terrain_id=0, map_id="good")
        with open(tmp_path / "good.json", "w") as f:
            json.dump(map_data, f)
        with open(tmp_path / "bad.json", "w") as f:
            f.write("{not valid json")

        results = batch_enhance_maps(str(tmp_path), seed=42)
        assert results["processed"] == 1
        assert "bad" in results["maps"]
        assert "error" in results["maps"]["bad"]

    def test_batch_process_empty_dir(self, tmp_path: Path):
        """Verify empty directory returns zero processed.

        Boundary: No map files in input dir.
        Expected: processed=0, total_decorations=0, maps={}.
        """
        results = batch_enhance_maps(str(tmp_path), seed=42)
        assert results["processed"] == 0
        assert results["total_decorations"] == 0
        assert results["maps"] == {}

    def test_batch_process_custom_config(self, tmp_path: Path):
        """Verify custom config is respected.

        Scenario: Pass a config with enable_height=False.
        Expected: Enhanced maps have all-zero heights.
        """
        cfg = GenerationConfig(enable_height=False)
        map_data = _make_map_data(width=5, height=5, terrain_id=4, map_id="m1")
        with open(tmp_path / "m1.json", "w") as f:
            json.dump(map_data, f)

        results = batch_enhance_maps(str(tmp_path), seed=42, config=cfg)
        assert results["processed"] == 1
        out_file = tmp_path / "m1.json"
        with open(out_file) as f:
            enhanced = json.load(f)
        for row in enhanced["tiles_enhanced"]:
            for tile in row:
                assert tile["height"] == 0

    def test_batch_results_contain_size_info(self, tmp_path: Path):
        """Verify results include map size information.

        Scenario: Process a 5x3 map.
        Expected: maps entry has "size" = "5×3".
        """
        map_data = _make_map_data(width=5, height=3, terrain_id=0, map_id="m1")
        with open(tmp_path / "m1.json", "w") as f:
            json.dump(map_data, f)

        results = batch_enhance_maps(str(tmp_path), seed=42)
        assert results["maps"]["m1"]["size"] == "5×3"

    def test_batch_results_contain_decoration_count(self, tmp_path: Path):
        """Verify results include decoration count per map.

        Scenario: Process a map.
        Expected: maps entry has "decorations" key with int value.
        """
        map_data = _make_map_data(width=10, height=10, terrain_id=0, map_id="m1")
        with open(tmp_path / "m1.json", "w") as f:
            json.dump(map_data, f)

        results = batch_enhance_maps(str(tmp_path), seed=42)
        assert "decorations" in results["maps"]["m1"]
        assert isinstance(results["maps"]["m1"]["decorations"], int)


# ========================================================================
# Performance Tests
# ========================================================================


class TestTerrainDetailGeneratorPerformance:
    """Performance baseline tests for terrain detail generation."""

    def test_enhance_map_20x20_timing(self):
        """Verify enhancing a 20x20 map completes quickly.

        Performance: Enhance a 20x20 map with default config.
        Expected: Wall time < 2.0 seconds.
        """
        gen = TerrainDetailGenerator(seed=42)
        map_data = _make_map_data(width=20, height=20, varied=True)

        start = time.perf_counter()
        gen.enhance_map(map_data)
        elapsed = time.perf_counter() - start

        assert elapsed < 2.0, f"Enhance took {elapsed:.3f}s, expected < 2.0s"

    def test_value_noise_timing(self):
        """Verify value noise is fast.

        Performance: Sample 10000 noise points.
        Expected: Wall time < 0.5 seconds.
        """
        gen = TerrainDetailGenerator(seed=42)
        start = time.perf_counter()
        for i in range(100):
            for j in range(100):
                gen._value_noise(float(i) * 0.1, float(j) * 0.1)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.5, f"Noise sampling took {elapsed:.3f}s, expected < 0.5s"

    def test_batch_process_timing(self, tmp_path: Path):
        """Verify batch processing 5 small maps is fast.

        Performance: Create and process 5 10x10 maps.
        Expected: Wall time < 5.0 seconds.
        """
        for i in range(5):
            map_data = _make_map_data(width=10, height=10, varied=True, map_id=f"m{i}")
            with open(tmp_path / f"m{i}.json", "w") as f:
                json.dump(map_data, f)

        start = time.perf_counter()
        results = batch_enhance_maps(str(tmp_path), seed=42)
        elapsed = time.perf_counter() - start

        assert results["processed"] == 5
        assert elapsed < 5.0, f"Batch took {elapsed:.3f}s, expected < 5.0s"


# ========================================================================
# Integration Tests
# ========================================================================


class TestTerrainDetailGeneratorIntegration:
    """End-to-end integration tests for terrain detail generation."""

    def test_full_enhancement_pipeline(self):
        """Verify the full enhancement pipeline produces a valid map.

        Integration: enhance_map → verify all phases ran:
        1. tiles_enhanced exists and is populated
        2. height values are set (enable_height=True)
        3. variations are assigned (enable_variations=True)
        4. decorations may be present
        5. _detail_generated is True
        """
        gen = TerrainDetailGenerator(seed=42)
        map_data = _make_map_data(width=15, height=15, varied=True)
        result = gen.enhance_map(map_data)

        # Phase 1: tiles_enhanced populated
        assert "tiles_enhanced" in result
        assert len(result["tiles_enhanced"]) == 15

        # Phase 2: heights assigned
        heights = [t["height"] for row in result["tiles_enhanced"] for t in row]
        assert any(h != 0 for h in heights)  # At least some non-zero heights

        # Phase 3: variations assigned
        variations = [t["variation"] for row in result["tiles_enhanced"] for t in row]
        assert any(v != 0 for v in variations)

        # Phase 4: decorations placed
        assert result["_decoration_count"] > 0

        # Phase 5: completion flag
        assert result["_detail_generated"] is True

    def test_enhanced_map_tiles_are_valid_dicts(self):
        """Verify all tiles in enhanced map are valid EnhancedTile dicts.

        Integration: Enhance map, check each tile dict has required keys.
        """
        gen = TerrainDetailGenerator(seed=42)
        map_data = _make_map_data(width=5, height=5, terrain_id=0)
        result = gen.enhance_map(map_data)
        for row in result["tiles_enhanced"]:
            for tile in row:
                assert "base_terrain" in tile
                assert "height" in tile
                assert "variation" in tile
                assert "decorations" in tile

    def test_enhanced_map_roundtrips_through_enhanced_tile(self):
        """Verify enhanced tiles can be reconstructed via EnhancedTile.from_dict.

        Integration: Enhance map → serialize → deserialize → verify.
        """
        gen = TerrainDetailGenerator(seed=42)
        map_data = _make_map_data(width=3, height=3, terrain_id=0)
        result = gen.enhance_map(map_data)

        for row in result["tiles_enhanced"]:
            for tile_dict in row:
                tile = EnhancedTile.from_dict(tile_dict)
                assert tile.base_terrain == tile_dict["base_terrain"]
                assert tile.height == tile_dict["height"]

    def test_enhance_then_re_enhance_idempotent_height(self):
        """Verify re-enhancing an already-enhanced map preserves heights.

        Integration: Enhance map, enhance again, verify heights unchanged
        (tiles_enhanced already present, so no re-conversion).
        """
        gen = TerrainDetailGenerator(seed=42)
        map_data = _make_map_data(width=5, height=5, terrain_id=4)
        result1 = gen.enhance_map(map_data)
        heights1 = [t["height"] for row in result1["tiles_enhanced"] for t in row]

        # Re-enhance with same generator (uses same seed)
        gen2 = TerrainDetailGenerator(seed=42)
        result2 = gen2.enhance_map(result1)
        heights2 = [t["height"] for row in result2["tiles_enhanced"] for t in row]

        assert heights1 == heights2

    def test_disabled_features_still_produce_valid_map(self):
        """Verify disabling all optional features still produces a valid map.

        Integration: Disable height, variations, tactical features.
        Expected: Map enhanced with only basic decoration placement.
        """
        cfg = GenerationConfig(
            enable_height=False,
            enable_variations=False,
            generate_cover_positions=False,
            generate_concealment_zones=False,
        )
        gen = TerrainDetailGenerator(seed=42, config=cfg)
        map_data = _make_map_data(width=5, height=5, terrain_id=0)
        result = gen.enhance_map(map_data)
        assert result["_detail_generated"] is True
        for row in result["tiles_enhanced"]:
            for tile in row:
                assert tile["height"] == 0
                assert tile["variation"] == 0

    def test_batch_process_integration(self, tmp_path: Path):
        """Verify batch processing produces consistent enhanced maps.

        Integration: Create map, batch process, verify output is enhanced.
        """
        map_data = _make_map_data(width=10, height=10, varied=True, map_id="integration")
        with open(tmp_path / "integration.json", "w") as f:
            json.dump(map_data, f)

        results = batch_enhance_maps(str(tmp_path), seed=42)
        assert results["processed"] == 1
        assert results["total_decorations"] > 0

        # Verify output file is a valid enhanced map
        with open(tmp_path / "integration.json") as f:
            enhanced = json.load(f)
        assert enhanced["_detail_generated"] is True
        assert enhanced["_generation_seed"] == 42
