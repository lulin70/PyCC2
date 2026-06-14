"""Unit tests for Autotile System - Cross-tile visual continuity.

Tests the bitmask-based neighbor detection and autotile variant generation
for roads, rivers, bridges, hedgerows, and multi-tile buildings.
"""

import numpy as np
import pytest

from pycc2.domain.entities.game_map import GameMap
from pycc2.presentation.rendering.autotile_system import (
    DIR_EAST,
    DIR_NORTH,
    DIR_SOUTH,
    DIR_WEST,
    AutotileCache,
    detect_building_clusters,
    get_building_cluster_info,
    get_connected_directions,
    get_continuity_variant,
    get_edge_transition_width,
    get_neighbor_bitmap,
    is_autotile_terrain,
)


@pytest.fixture
def sample_game_map() -> GameMap:
    """Create a sample game map for testing."""
    # 10x10 map with various terrain types for testing
    # Layout:
    # Row 0:  [grass][road][road][road][grass][water][water][water][grass][hedge]
    # Row 1:  [grass][road][road][road][grass][water][water][water][grass][hedge]
    # Row 2:  [grass][road][road][road][grass][grass][grass][grass][grass][hedge]
    # Row 3:  [bldg][bldg][bldg][bldg][grass][grass][grass][grass][grass][grass]
    # Row 4:  [bldg][bldg][bldg][bldg][grass][grass][grass][grass][grass][grass]
    # Row 5-9: all grass

    tile_grid = np.array(
        [
            [0, 1, 1, 1, 0, 6, 6, 6, 0, 7],
            [0, 1, 1, 1, 0, 6, 6, 6, 0, 7],
            [0, 1, 1, 1, 0, 0, 0, 0, 0, 7],
            [4, 4, 5, 5, 0, 0, 0, 0, 0, 0],
            [4, 4, 5, 5, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ],
        dtype=np.int8,
    )

    return GameMap(id="test_map", name="Test Map", width=10, height=10, tile_grid=tile_grid)


class TestNeighborBitmap:
    """Tests for get_neighbor_bitmap function."""

    def test_get_neighbor_bitmap_isolated_tile(self, sample_game_map: GameMap):
        """Isolated road tile surrounded by different terrain should return 0.

        Test case: Position (2, 0) has road neighbors on E and S but N is grass (out of bounds = -1).
        Actually let's use a truly isolated position.
        """
        # Create a map with isolated road tile
        isolated_grid = np.zeros((5, 5), dtype=np.int8)
        isolated_grid[2, 2] = 1  # Single road in center

        isolated_map = GameMap(
            id="isolated", name="Isolated", width=5, height=5, tile_grid=isolated_grid
        )

        bitmap = get_neighbor_bitmap(isolated_map, 2, 2, terrain_type=1)
        assert bitmap == 0, f"Expected 0 for isolated tile, got {bitmap}"

    def test_get_neighbor_bitmap_fully_connected(self, sample_game_map: GameMap):
        """Road tile with all 4 neighbors same type should return 15 (0b1111)."""
        # Position (2, 1) in sample map: road with N(2,0)=road, E(3,1)=road, S(2,2)=road, W(1,1)=road
        bitmap = get_neighbor_bitmap(sample_game_map, 2, 1, terrain_type=1)
        assert bitmap == 15, f"Expected 15 for fully connected, got {bitmap}"

    def test_get_neighbor_bitmap_north_only(self, sample_game_map: GameMap):
        """Tile with only north neighbor matching should return 1 (bit 0)."""
        # Create custom map for this test
        test_grid = np.zeros((5, 5), dtype=np.int8)
        test_grid[1, 2] = 6  # Water at (2,1) - center
        test_grid[0, 2] = 6  # Water at (2,0) - north neighbor
        # Other neighbors are grass (0)

        test_map = GameMap(
            id="north_only", name="North Only", width=5, height=5, tile_grid=test_grid
        )

        bitmap = get_neighbor_bitmap(test_map, 2, 1, terrain_type=6)
        assert bitmap == DIR_NORTH, f"Expected {DIR_NORTH} for north-only, got {bitmap}"

    def test_get_neighbor_bitmap_line_horizontal(self, sample_game_map: GameMap):
        """Horizontal line of roads: E+W neighbors connected should return 10 (0b1010)."""
        # Position (2, 0): road with E(3,0)=road, W(1,0)=road, N=out of bounds, S(2,1)=road
        # Actually this has N,S,E,W all connected except N which is out of bounds
        # Let's test position (2, 1) which should have all 4 neighbors
        # For horizontal line test, create specific scenario

        test_grid = np.zeros((3, 5), dtype=np.int8)
        test_grid[1, 1] = 1  # Road at center
        test_grid[1, 0] = 1  # Road to west
        test_grid[1, 2] = 1  # Road to east
        # North and south are grass (0)

        test_map = GameMap(
            id="horizontal", name="Horizontal Line", width=5, height=3, tile_grid=test_grid
        )

        bitmap = get_neighbor_bitmap(test_map, 1, 1, terrain_type=1)
        expected = DIR_EAST | DIR_WEST  # Should have east and west
        assert bitmap == expected, f"Expected {expected} for horizontal line, got {bitmap}"

    def test_get_neighbor_bitmap_out_of_bounds(self, sample_game_map: GameMap):
        """Neighbors out of map bounds should not set bits."""
        # Corner position (0, 0): grass, north and west are out of bounds
        bitmap = get_neighbor_bitmap(sample_game_map, 0, 0, terrain_type=0)
        # East (1,0) = road (1), South (0,1) = grass (0) ✓
        # So only south bit should be set if we're checking for grass
        # But (1,0) is road not grass, so only south matches
        assert bitmap == DIR_SOUTH, f"Expected {DIR_SOUTH} for corner grass, got {bitmap}"


class TestContinuityVariant:
    """Tests for get_continuity_variant function."""

    def test_road_variant_format(self):
        """Road variants should follow 'road_{bitmask}' format."""
        for bitmask in range(16):
            variant = get_continuity_variant(1, bitmask)
            assert variant == f"road_{bitmask}", f"Expected 'road_{bitmask}', got '{variant}'"

    def test_water_variant_count(self):
        """Should generate unique variants for all 16 bitmask values."""
        variants = {get_continuity_variant(6, b) for b in range(16)}
        assert len(variants) == 16, "Should have 16 unique water variants"

    def test_hedge_variant_uniqueness(self):
        """Each bitmask should produce a unique hedge variant key."""
        variants = [get_continuity_variant(7, b) for b in range(16)]
        assert len(set(variants)) == 16, "All hedge variants should be unique"


class TestBuildingClusterDetection:
    """Tests for building cluster detection functionality."""

    def test_building_cluster_detection_2x2(self):
        """4 adjacent building tiles should form 1 cluster of 4."""
        grid = np.zeros((6, 6), dtype=np.int8)
        # 2x2 building block at top-left
        grid[0:2, 0:2] = 4  # BUILDING_ENTERABLE
        # Another 2x2 block
        grid[0:2, 3:5] = 5  # BUILDING_SOLID

        test_map = GameMap(
            id="buildings_2x2", name="Buildings 2x2", width=6, height=6, tile_grid=grid
        )

        clusters = detect_building_clusters(test_map)

        # Should find 2 clusters: one 2x2 enterable, one 2x2 solid
        assert len(clusters) == 2, f"Expected 2 clusters, got {len(clusters)}"

        # First cluster should have 4 tiles
        assert len(clusters[0]) == 4, f"First cluster should have 4 tiles, got {len(clusters[0])}"

        # Second cluster should also have 4 tiles
        assert len(clusters[1]) == 4, f"Second cluster should have 4 tiles, got {len(clusters[1])}"

    def test_building_cluster_detection_two_separate(self):
        """Two separate 1x1 buildings not touching should form 2 clusters of 1 each."""
        grid = np.zeros((5, 5), dtype=np.int8)
        grid[1, 1] = 4  # Building at (1,1)
        grid[3, 3] = 5  # Building at (3,3)

        test_map = GameMap(
            id="separate_buildings", name="Separate Buildings", width=5, height=5, tile_grid=grid
        )

        clusters = detect_building_clusters(test_map)

        assert len(clusters) == 2, f"Expected 2 clusters, got {len(clusters)}"
        assert len(clusters[0]) == 1, "First cluster should have 1 tile"
        assert len(clusters[1]) == 1, "Second cluster should have 1 tile"

    def test_building_cluster_info(self, sample_game_map: GameMap):
        """get_building_cluster_info should return correct metadata for building tiles."""
        clusters = detect_building_clusters(sample_game_map)
        info = get_building_cluster_info(sample_game_map, 0, 3, clusters)

        assert info["is_building"], "Should identify as building"
        assert info["cluster_index"] is not None, "Should belong to a cluster"
        assert info["cluster_size"] == (4, 2), (
            f"Expected cluster size (4,2), got {info['cluster_size']}"
        )

    def test_non_building_cluster_info(self, sample_game_map: GameMap):
        """get_building_cluster_info for non-building tile should return defaults."""
        info = get_building_cluster_info(sample_game_map, 5, 5)

        assert not info["is_building"], "Non-building should return is_building=False"
        assert info["cluster_index"] is None, "Non-building should have no cluster index"


class TestAutotileTerrain:
    """Tests for terrain type autotile support detection."""

    def test_road_is_autotile(self):
        """Road terrain (ID=1) should support autotiling."""
        assert is_autotile_terrain(1)

    def test_water_is_autotile(self):
        """Water terrain (ID=6) should support autotiling."""
        assert is_autotile_terrain(6)

    def test_hedge_is_autotile(self):
        """Hedge terrain (ID=7) should support autotiling."""
        assert is_autotile_terrain(7)

    def test_bridge_is_autotile(self):
        """Bridge terrain (ID=11) should support autotiling."""
        assert is_autotile_terrain(11)

    def test_grass_is_not_autotile(self):
        """Grass terrain (ID=0) should NOT support autotiling."""
        assert not is_autotile_terrain(0)

    def test_building_is_not_autotile(self):
        """Building terrain (ID=4,5) should NOT support autotiling (uses cluster system instead)."""
        assert not is_autotile_terrain(4)
        assert not is_autotile_terrain(5)


class TestConnectedDirections:
    """Tests for direction conversion utilities."""

    def test_no_connections_empty_list(self):
        """Bitmask 0 should return empty direction list."""
        directions = get_connected_directions(0)
        assert directions == []

    def test_all_connections_four_directions(self):
        """Bitmask 15 (all bits) should return 4 directions."""
        directions = get_connected_directions(15)
        assert len(directions) == 4
        assert (0, -1) in directions  # North
        assert (1, 0) in directions  # East
        assert (0, 1) in directions  # South
        assert (-1, 0) in directions  # West

    def test_north_only_single_direction(self):
        """Bitmask 1 (north only) should return single north direction."""
        directions = get_connected_directions(DIR_NORTH)
        assert len(directions) == 1
        assert directions[0] == (0, -1)


class TestEdgeTransitionWidth:
    """Tests for edge transition width calculation."""

    def test_fully_connected_zero_transitions(self):
        """Fully connected tile (bitmask=15) should have zero transition widths."""
        widths = get_edge_transition_width(1, 15, 48)

        assert widths["north"] == 0
        assert widths["east"] == 0
        assert widths["south"] == 0
        assert widths["west"] == 0

    def test_isolated_full_transitions(self):
        """Isolated tile (bitmask=0) should have full transition widths on all edges."""
        widths = get_edge_transition_width(1, 0, 48)

        # Base width should be ~4-6 pixels for 48px tile
        assert widths["north"] > 0
        assert widths["east"] > 0
        assert widths["south"] > 0
        assert widths["west"] > 0

        # All should be equal for isolated tile
        assert widths["north"] == widths["east"] == widths["south"] == widths["west"]

    def test_partial_connectivity_mixed_widths(self):
        """Partially connected tile should have zero on connected edges, positive on others."""
        # Connected N and E only
        bitmask = DIR_NORTH | DIR_EAST  # value = 3
        widths = get_edge_transition_width(6, bitmask, 48)

        assert widths["north"] == 0, "Connected north should have 0 transition"
        assert widths["east"] == 0, "Connected east should have 0 transition"
        assert widths["south"] > 0, "Disconnected south should have positive transition"
        assert widths["west"] > 0, "Disconnected west should have positive transition"


class TestAutotileCache:
    """Tests for AutotileCache caching mechanism."""

    def test_cache_set_and_get(self):
        """Cache should store and retrieve values correctly."""
        cache = AutotileCache()

        test_surface = "test_surface_value"  # Using string as mock surface
        cache.set_variant(1, 7, 42, test_surface)

        retrieved = cache.get_variant(1, 7, 42)
        assert retrieved == test_surface, "Should retrieve cached value"

    def test_cache_miss_returns_none(self):
        """Cache should return None for non-existent keys."""
        cache = AutotileCache()

        result = cache.get_variant(999, 999, 999)
        assert result is None, "Cache miss should return None"

    def test_cache_clear(self):
        """Clear should remove all cached items."""
        cache = AutotileCache()

        cache.set_variant(1, 0, 0, "value1")
        cache.set_variant(6, 15, 1, "value2")

        cache.clear()

        assert cache.get_variant(1, 0, 0) is None
        assert cache.get_variant(6, 15, 1) is None

    def test_building_cluster_caching(self):
        """Building clusters should be cacheable by map ID."""
        cache = AutotileCache()

        test_clusters = [[(0, 0), (1, 0)], [(3, 3)]]

        cache.set_building_clusters("map_001", test_clusters)
        retrieved = cache.get_building_clusters("map_001")

        assert retrieved == test_clusters, "Should retrieve cached clusters"
        assert cache.get_building_clusters("nonexistent") is None


class TestBitmaskConsistency:
    """Tests for deterministic behavior of autotile system."""

    def test_bitmask_deterministic(self, sample_game_map: GameMap):
        """Same input should always produce same output (deterministic)."""
        # Call multiple times with same parameters
        results = [get_neighbor_bitmap(sample_game_map, 2, 1, terrain_type=1) for _ in range(10)]

        # All results should be identical
        assert all(r == results[0] for r in results), "Results should be deterministic"

    def test_variant_key_deterministic(self):
        """Variant key generation should be deterministic."""
        keys = [get_continuity_variant(1, 7) for _ in range(20)]

        assert all(k == "road_7" for k in keys), "All variant keys should be identical"

    def test_edge_widths_scale_with_tile_size(self):
        """Transition widths should scale proportionally with tile size."""
        widths_small = get_edge_transition_width(1, 0, 32)
        widths_large = get_edge_transition_width(1, 0, 64)

        # Larger tile should have proportionally larger transitions
        assert widths_large["north"] >= widths_small["north"], (
            "Larger tiles should have equal or larger transition widths"
        )


class TestIntegrationScenarios:
    """Integration tests for realistic autotile scenarios."""

    def test_straight_road_segment(self, sample_game_map: GameMap):
        """Horizontal road segment should show proper connectivity."""
        # Check middle of 3-tile horizontal road at row 0
        bitmap_center = get_neighbor_bitmap(sample_game_map, 2, 0, terrain_type=1)
        bitmap_west = get_neighbor_bitmap(sample_game_map, 1, 0, terrain_type=1)
        bitmap_east = get_neighbor_bitmap(sample_game_map, 3, 0, terrain_type=1)

        # Center tile should connect to both sides
        assert bitmap_center & DIR_WEST, "Center should connect west"
        assert bitmap_center & DIR_EAST, "Center should connect east"

        # West end should only connect east (to center)
        assert bitmap_west & DIR_EAST, "West end should connect east"
        assert not (bitmap_west & DIR_WEST), "West end should NOT connect west (grass)"

        # East end should only connect west (to center)
        assert bitmap_east & DIR_WEST, "East end should connect west"
        assert not (bitmap_east & DIR_EAST), "East end should NOT connect east (grass)"

    def test_river_with_shore(self, sample_game_map: GameMap):
        """Water tiles should detect shore transitions correctly."""
        # Check water tile at edge of river (next to grass)
        # Position (6, 0): water, west is water, east is water, south is water, north is out of bounds
        bitmap_corner = get_neighbor_bitmap(sample_game_map, 6, 0, terrain_type=6)

        # Should have east and south connections (both water)
        assert bitmap_corner & DIR_EAST, "Water should connect to adjacent water east"
        assert bitmap_corner & DIR_SOUTH, "Water should connect to adjacent water south"

        # Check water tile at (6, 2) which is surrounded by grass on 3 sides
        # Actually (6,2) is grass in our map, let's check (6,1) which has water below
        bitmap_shore = get_neighbor_bitmap(sample_game_map, 6, 1, terrain_type=6)

        # This tile should have fewer connections (south is grass)
        assert not (bitmap_shore & DIR_SOUTH), "South of this water tile is grass"

    def test_hedge_continuity(self, sample_game_map: GameMap):
        """Hedge tiles should form continuous vertical line."""
        # Column 9 has vertical hedge from row 0-2
        bitmap_top = get_neighbor_bitmap(sample_game_map, 9, 0, terrain_type=7)
        bitmap_mid = get_neighbor_bitmap(sample_game_map, 9, 1, terrain_type=7)
        bitmap_bot = get_neighbor_bitmap(sample_game_map, 9, 2, terrain_type=7)

        # Middle hedge should connect up and down
        assert bitmap_mid & DIR_NORTH, "Middle hedge should connect north"
        assert bitmap_mid & DIR_SOUTH, "Middle hedge should connect south"

        # Top hedge should only connect south
        assert bitmap_top & DIR_SOUTH, "Top hedge should connect south"
        assert not (bitmap_top & DIR_NORTH), (
            "Top hedge should NOT connect north (out of bounds/grass)"
        )

        # Bottom hedge should only connect north
        assert bitmap_bot & DIR_NORTH, "Bottom hedge should connect north"
        assert not (bitmap_bot & DIR_SOUTH), "Bottom hedge should NOT connect south (grass)"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
