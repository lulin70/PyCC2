"""
Tests for Enhanced Tile System (Phase A2)

Covers EnhancedTile creation/fields, DecorationType enum,
DecorationInstance tactical properties, and tile computed properties
(cover, concealment, movement cost, LOS blocking).
"""

from __future__ import annotations

import pytest

from pycc2.domain.systems.enhanced_tile import (
    DecorationInstance,
    DecorationLibrary,
    DecorationType,
    EnhancedTile,
    TileConverter,
)

# ========================================================================
# DecorationType Enum Tests
# ========================================================================


class TestDecorationType:
    """Tests for the DecorationType enum."""

    def test_decoration_type_values_are_unique(self):
        values = [dt.value for dt in DecorationType]
        assert len(values) == len(set(values)), "All DecorationType auto values must be unique"

    def test_decoration_type_has_expected_categories(self):
        """Verify all thematic layers are represented."""
        vegetation = [dt for dt in DecorationType if dt.name.startswith(("BUSH", "TREE", "GRASS", "CROPS", "HEDGE", "FLOWER"))]
        geology = [dt for dt in DecorationType if dt.name.startswith(("ROCK", "RUBBLE", "SAND", "MUD", "PUDDLE"))]
        man_made = [dt for dt in DecorationType if dt.name.startswith(("FENCE", "TRENCH", "SANDBAG", "SIGN", "ROAD_BLOCK", "CRATE"))]
        combat = [dt for dt in DecorationType if dt.name.startswith(("CRATER", "BURN", "WRECKAGE", "BUILDING_RUIN", "SHELL"))]
        assert len(vegetation) >= 5, f"Expected >=5 vegetation types, got {len(vegetation)}"
        assert len(geology) >= 3, f"Expected >=3 geology types, got {len(geology)}"
        assert len(man_made) >= 3, f"Expected >=3 man-made types, got {len(man_made)}"
        assert len(combat) >= 3, f"Expected >=3 combat damage types, got {len(combat)}"

    def test_decoration_type_total_count(self):
        """At least 30 decoration types defined."""
        assert len(DecorationType) >= 30

    def test_decoration_type_access_by_name(self):
        assert DecorationType["TREE_OAK"] is not None
        assert DecorationType["ROCK_LARGE"] is not None
        assert DecorationType["TRENCH_SECTION"] is not None


# ========================================================================
# DecorationInstance Tests
# ========================================================================


class TestDecorationInstance:
    """Tests for DecorationInstance dataclass and tactical properties."""

    def test_default_fields(self):
        d = DecorationInstance(decoration_type=DecorationType.BUSH_SMALL)
        assert d.offset_x == 0.0
        assert d.offset_y == 0.0
        assert d.scale == 1.0
        assert d.rotation == 0
        assert d.variant == 0

    def test_custom_fields(self):
        d = DecorationInstance(
            decoration_type=DecorationType.TREE_PINE,
            offset_x=0.3,
            offset_y=-0.2,
            scale=1.1,
            rotation=90,
            variant=2,
        )
        assert d.offset_x == 0.3
        assert d.rotation == 90
        assert d.variant == 2

    def test_tactical_properties_default_cover_zero(self):
        """Decorations without explicit type mapping should have cover_bonus=0."""
        d = DecorationInstance(decoration_type=DecorationType.GRASS_TUFT)
        props = d.get_tactical_properties()
        assert props["cover_bonus"] == 0
        assert props["concealment_bonus"] == 0

    def test_tactical_properties_tree_oak(self):
        d = DecorationInstance(decoration_type=DecorationType.TREE_OAK)
        props = d.get_tactical_properties()
        assert props["cover_bonus"] == 2
        assert props["concealment_bonus"] == 0.3
        assert props["blocks_los"] is True

    def test_tactical_properties_rock_large(self):
        d = DecorationInstance(decoration_type=DecorationType.ROCK_LARGE)
        props = d.get_tactical_properties()
        assert props["cover_bonus"] == 3
        assert props["movement_cost"] == 1.5

    def test_tactical_properties_trench_section(self):
        d = DecorationInstance(decoration_type=DecorationType.TRENCH_SECTION)
        props = d.get_tactical_properties()
        assert props["cover_bonus"] == 3
        assert props["concealment_bonus"] == 0.4
        assert props["movement_cost"] == 0.8

    def test_tactical_properties_fence_wire_not_destructible(self):
        d = DecorationInstance(decoration_type=DecorationType.FENCE_WIRE)
        props = d.get_tactical_properties()
        assert props["destructible"] is False
        assert props["movement_cost"] == 1.5


# ========================================================================
# EnhancedTile Tests
# ========================================================================


class TestEnhancedTile:
    """Tests for EnhancedTile creation, fields, and computed properties."""

    def test_creation_default_fields(self):
        tile = EnhancedTile(base_terrain=0)
        assert tile.base_terrain == 0
        assert tile.height == 0
        assert tile.variation == 0
        assert tile.decorations == []
        assert tile.max_decorations == 4

    def test_creation_custom_fields(self):
        tile = EnhancedTile(base_terrain=3, height=2, variation=5)
        assert tile.base_terrain == 3
        assert tile.height == 2
        assert tile.variation == 5

    def test_add_decoration_within_limit(self):
        tile = EnhancedTile(base_terrain=0)
        d = DecorationInstance(decoration_type=DecorationType.BUSH_SMALL)
        assert tile.add_decoration(d) is True
        assert len(tile.decorations) == 1

    def test_add_decoration_exceeds_limit(self):
        tile = EnhancedTile(base_terrain=0, max_decorations=2)
        tile.add_decoration(DecorationInstance(decoration_type=DecorationType.BUSH_SMALL))
        tile.add_decoration(DecorationInstance(decoration_type=DecorationType.BUSH_DENSE))
        result = tile.add_decoration(DecorationInstance(decoration_type=DecorationType.GRASS_TUFT))
        assert result is False
        assert len(tile.decorations) == 2

    def test_remove_decoration_existing(self):
        tile = EnhancedTile(base_terrain=0)
        tile.add_decoration(DecorationInstance(decoration_type=DecorationType.TREE_OAK))
        assert tile.remove_decoration(DecorationType.TREE_OAK) is True
        assert len(tile.decorations) == 0

    def test_remove_decoration_nonexistent(self):
        tile = EnhancedTile(base_terrain=0)
        assert tile.remove_decoration(DecorationType.TREE_PINE) is False

    def test_total_cover_bonus_open_terrain(self):
        tile = EnhancedTile(base_terrain=0)
        assert tile.total_cover_bonus == 0

    def test_total_cover_bonus_forest_terrain(self):
        tile = EnhancedTile(base_terrain=3)
        assert tile.total_cover_bonus == 1

    def test_total_cover_bonus_with_decoration(self):
        tile = EnhancedTile(base_terrain=0)
        tile.add_decoration(DecorationInstance(decoration_type=DecorationType.ROCK_LARGE))
        assert tile.total_cover_bonus == 3

    def test_total_concealment_open_terrain(self):
        tile = EnhancedTile(base_terrain=0)
        assert tile.total_concealment == 0.0

    def test_total_concealment_forest_terrain(self):
        tile = EnhancedTile(base_terrain=3)
        conc = tile.total_concealment
        assert 0.1 < conc <= 0.95

    def test_effective_movement_cost_open(self):
        tile = EnhancedTile(base_terrain=0)
        assert tile.effective_movement_cost == 1.0

    def test_effective_movement_cost_water_impassable(self):
        tile = EnhancedTile(base_terrain=6)
        assert tile.effective_movement_cost == 999.0

    def test_effective_movement_cost_height_penalty(self):
        tile = EnhancedTile(base_terrain=0, height=3)
        cost = tile.effective_movement_cost
        assert cost > 1.0  # Height adds penalty

    def test_blocks_line_of_sight_building(self):
        tile = EnhancedTile(base_terrain=5)
        assert tile.blocks_line_of_sight() is True

    def test_blocks_line_of_sight_open(self):
        tile = EnhancedTile(base_terrain=0)
        assert tile.blocks_line_of_sight() is False

    def test_blocks_line_of_sight_tree_decoration(self):
        tile = EnhancedTile(base_terrain=0)
        tile.add_decoration(DecorationInstance(decoration_type=DecorationType.TREE_OAK))
        assert tile.blocks_line_of_sight() is True

    def test_to_legacy_int(self):
        tile = EnhancedTile(base_terrain=7, height=2)
        assert tile.to_legacy_int() == 7

    def test_from_legacy(self):
        tile = EnhancedTile.from_legacy(3)
        assert tile.base_terrain == 3
        assert tile.height == 0
        assert tile.decorations == []

    def test_to_dict_and_from_dict_roundtrip(self):
        tile = EnhancedTile(base_terrain=3, height=1, variation=2)
        tile.add_decoration(DecorationInstance(
            decoration_type=DecorationType.TREE_OAK,
            offset_x=0.1,
            offset_y=-0.1,
            scale=1.05,
            rotation=90,
            variant=1,
        ))
        d = tile.to_dict()
        restored = EnhancedTile.from_dict(d)
        assert restored.base_terrain == 3
        assert restored.height == 1
        assert restored.variation == 2
        assert len(restored.decorations) == 1
        assert restored.decorations[0].decoration_type == DecorationType.TREE_OAK
        assert restored.decorations[0].rotation == 90

    def test_cache_invalidation_on_add_decoration(self):
        tile = EnhancedTile(base_terrain=0)
        cover_before = tile.total_cover_bonus
        tile.add_decoration(DecorationInstance(decoration_type=DecorationType.SANDBAG_WALL))
        cover_after = tile.total_cover_bonus
        assert cover_after > cover_before

    def test_cache_invalidation_on_remove_decoration(self):
        tile = EnhancedTile(base_terrain=0)
        tile.add_decoration(DecorationInstance(decoration_type=DecorationType.ROCK_LARGE))
        cover_with = tile.total_cover_bonus
        tile.remove_decoration(DecorationType.ROCK_LARGE)
        cover_without = tile.total_cover_bonus
        assert cover_without < cover_with


# ========================================================================
# DecorationLibrary Tests
# ========================================================================


class TestDecorationLibrary:
    """Tests for DecorationLibrary metadata definitions."""

    def test_library_has_definitions(self):
        lib = DecorationLibrary()
        assert len(lib.definitions) >= 12, f"Decoration library should have at least 12 definitions (one per major decoration type), got {len(lib.definitions)}"

    def test_library_get_definition_existing(self):
        lib = DecorationLibrary()
        defn = lib.get_definition(DecorationType.TREE_OAK)
        assert "sprite_sheet" in defn
        assert "draw_layer" in defn

    def test_library_get_definition_missing_returns_default(self):
        lib = DecorationLibrary()
        defn = lib.get_definition(DecorationType.GRAVE_MARKER)
        assert "sprite_sheet" in defn
        assert defn["sprite_sheet"] == "default.png"


# ========================================================================
# TileConverter Tests
# ========================================================================


class TestTileConverter:
    """Tests for TileConverter legacy/enhanced format conversion."""

    def test_convert_grid_to_enhanced(self):
        legacy = [[0, 1, 3], [5, 6, 0]]
        enhanced = TileConverter.convert_grid_to_enhanced(legacy)
        assert len(enhanced) == 2
        assert len(enhanced[0]) == 3
        assert enhanced[0][0].base_terrain == 0
        assert enhanced[1][0].base_terrain == 5

    def test_convert_grid_to_legacy(self):
        enhanced = [
            [EnhancedTile(base_terrain=0), EnhancedTile(base_terrain=3)],
            [EnhancedTile(base_terrain=5), EnhancedTile(base_terrain=1)],
        ]
        legacy = TileConverter.convert_grid_to_legacy(enhanced)
        assert legacy == [[0, 3], [5, 1]]

    def test_roundtrip_legacy_enhanced_legacy(self):
        original = [[0, 1], [3, 5]]
        enhanced = TileConverter.convert_grid_to_enhanced(original)
        restored = TileConverter.convert_grid_to_legacy(enhanced)
        assert restored == original

    def test_convert_map_data(self):
        map_data = {
            "tiles": [[0, 1], [3, 5]],
            "width": 2,
            "height": 2,
        }
        result = TileConverter.convert_map_data(map_data)
        assert "tiles_enhanced" in result
        assert result["_format_version"] == "enhanced_v1"
        assert len(result["tiles_enhanced"]) == 2

    def test_convert_map_data_missing_tiles_raises(self):
        with pytest.raises(ValueError, match="tiles"):
            TileConverter.convert_map_data({})
