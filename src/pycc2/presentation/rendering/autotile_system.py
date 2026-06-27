"""Autotile system for cross-tile visual continuity.

Uses bitmask approach: each tile checks its 4 cardinal neighbors (N/E/S/W)
and adjusts its edge rendering to create seamless connections with same-type neighbors.

Bitmask convention (4-bit, N-E-S-W):
    bit 0 (1) = North neighbor matches
    bit 1 (2) = East neighbor matches
    bit 2 (4) = South neighbor matches
    bit 3 (8) = West neighbor matches

Example: Road with neighbors N,E,S = bitmask 0b0111 = 7 → draw road connections on N,E,S edges
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap


# Direction constants for bitmask
DIR_NORTH = 1  # bit 0
DIR_EAST = 2  # bit 1
DIR_SOUTH = 4  # bit 2
DIR_WEST = 8  # bit 3

# Direction offsets: (dx, dy)
DIRECTION_OFFSETS = {
    DIR_NORTH: (0, -1),
    DIR_EAST: (1, 0),
    DIR_SOUTH: (0, 1),
    DIR_WEST: (-1, 0),
}

# Terrain types that support autotiling
AUTOTILE_TERRAIN_IDS = {1, 6, 7, 11}  # ROAD, WATER, HEDGE, BRIDGE


def get_neighbor_bitmap(game_map: GameMap, x: int, y: int, terrain_type: int | None = None) -> int:
    """Check 4 cardinal neighbors and return 4-bit bitmap of matching types.

    If terrain_type is None, use current tile's type.
    Returns int 0-15 representing which neighbors match.

    Args:
        game_map: Game map instance
        x: Tile X coordinate
        y: Tile Y coordinate
        terrain_type: Terrain type to check against (None = use current tile)

    Returns:
        int: 4-bit bitmask (N-E-S-W)

    """
    if terrain_type is None:
        terrain_type = _get_terrain_at(game_map, x, y)
        if terrain_type < 0:
            return 0

    bitmask = 0

    for direction, (dx, dy) in DIRECTION_OFFSETS.items():
        nx, ny = x + dx, y + dy
        neighbor_terrain = _get_terrain_at(game_map, nx, ny)

        if neighbor_terrain == terrain_type:
            bitmask |= direction

    return bitmask


def get_continuity_variant(terrain_id: int, bitmask: int) -> str:
    """Return variant key for given terrain + neighbor configuration.

    e.g., "road_7", "water_15", "hedge_3"
    This determines which pre-rendered or dynamically generated variant to use.

    Args:
        terrain_id: Terrain type ID
        bitmask: Neighbor bitmask (0-15)

    Returns:
        str: Variant key string

    """
    terrain_names = {
        0: "grass",
        1: "road",
        2: "grass_dark",
        3: "woods",
        4: "building_enterable",
        5: "building_solid",
        6: "water",
        7: "hedge",
        8: "wall",
        9: "rough",
        10: "shallow",
        11: "bridge",
        12: "crater",
    }

    name = terrain_names.get(terrain_id, f"terrain_{terrain_id}")
    return f"{name}_{bitmask}"


def _get_terrain_at(game_map: GameMap, x: int, y: int) -> int:
    """Get terrain type at tile coordinate, returns -1 for out of bounds."""
    if x < 0 or y < 0 or x >= game_map.width or y >= game_map.height:
        return -1

    try:
        # Try enhanced tile first
        if hasattr(game_map, "get_enhanced_tile"):
            tile_data = game_map.get_enhanced_tile(x, y)
            if tile_data is not None:
                from pycc2.domain.systems.enhanced_tile import EnhancedTile

                if isinstance(tile_data, EnhancedTile):
                    return tile_data.base_terrain
                elif isinstance(tile_data, dict):
                    return tile_data.get("base_terrain", -1)

        # Fallback to tile_grid
        return int(game_map.tile_grid[y, x])
    except (AttributeError, IndexError, TypeError, KeyError):
        return -1


def detect_building_clusters(game_map: GameMap) -> list[list[tuple[int, int]]]:
    """Find groups of adjacent building tiles using flood-fill/BFS.

    Returns list of clusters, each cluster is list of (x,y) coords.
    Building tiles are terrain IDs 4 (BUILDING_ENTERABLE) and 5 (BUILDING_SOLID).

    Args:
        game_map: Game map instance

    Returns:
        list: List of building clusters, each containing (x, y) coordinate tuples

    """
    BUILDING_IDS = {4, 5}
    visited = set()
    clusters = []

    for y in range(game_map.height):
        for x in range(game_map.width):
            if (x, y) in visited:
                continue

            terrain = _get_terrain_at(game_map, x, y)
            if terrain not in BUILDING_IDS:
                continue

            # BFS to find all connected building tiles
            cluster = []
            queue = deque([(x, y)])
            visited.add((x, y))

            while queue:
                cx, cy = queue.popleft()
                cluster.append((cx, cy))

                # Check 4 cardinal neighbors
                for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
                    nx, ny = cx + dx, cy + dy

                    if (nx, ny) in visited:
                        continue

                    if nx < 0 or ny < 0 or nx >= game_map.width or ny >= game_map.height:
                        continue

                    neighbor_terrain = _get_terrain_at(game_map, nx, ny)
                    if neighbor_terrain in BUILDING_IDS:
                        visited.add((nx, ny))
                        queue.append((nx, ny))

            if cluster:
                clusters.append(cluster)

    return clusters


def get_building_cluster_info(
    game_map: GameMap, x: int, y: int, clusters: list[list[tuple[int, int]]] | None = None
) -> dict:
    """Get cluster information for a specific building tile.

    Args:
        game_map: Game map instance
        x: Tile X coordinate
        y: Tile Y coordinate
        clusters: Pre-computed clusters (optional, will compute if None)

    Returns:
        dict: Cluster info with keys:
            - 'is_building': bool
            - 'cluster_index': int or None
            - 'is_root': bool (top-left corner of cluster)
            - 'position_in_cluster': tuple (local_x, local_y within cluster)
            - 'cluster_size': tuple (width, height)
            - 'has_north_neighbor': bool
            - 'has_east_neighbor': bool
            - 'has_south_neighbor': bool
            - 'has_west_neighbor': bool

    """
    default_result = {
        "is_building": False,
        "cluster_index": None,
        "is_root": False,
        "position_in_cluster": (0, 0),
        "cluster_size": (1, 1),
        "has_north_neighbor": False,
        "has_east_neighbor": False,
        "has_south_neighbor": False,
        "has_west_neighbor": False,
    }

    terrain = _get_terrain_at(game_map, x, y)
    if terrain not in {4, 5}:
        return default_result

    if clusters is None:
        clusters = detect_building_clusters(game_map)

    # Find which cluster this tile belongs to
    for idx, cluster in enumerate(clusters):
        if (x, y) in cluster:
            # Calculate cluster bounds
            min_x = min(cx for cx, cy in cluster)
            min_y = min(cy for cx, cy in cluster)
            max_x = max(cx for cx, cy in cluster)
            max_y = max(cy for cx, cy in cluster)

            # Check neighbors within same cluster
            has_north = (x, y - 1) in cluster
            has_east = (x + 1, y) in cluster
            has_south = (x, y + 1) in cluster
            has_west = (x - 1, y) in cluster

            return {
                "is_building": True,
                "cluster_index": idx,
                "is_root": (x == min_x and y == min_y),
                "position_in_cluster": (x - min_x, y - min_y),
                "cluster_size": (max_x - min_x + 1, max_y - min_y + 1),
                "has_north_neighbor": has_north,
                "has_east_neighbor": has_east,
                "has_south_neighbor": has_south,
                "has_west_neighbor": has_west,
            }

    return default_result


def is_autotile_terrain(terrain_id: int) -> bool:
    """Check if terrain type supports autotiling.

    Args:
        terrain_id: Terrain type ID

    Returns:
        bool: True if terrain supports autotiling

    """
    return terrain_id in AUTOTILE_TERRAIN_IDS


def get_connected_directions(bitmask: int) -> list[tuple[int, int]]:
    """Convert bitmask to list of connected direction vectors.

    Args:
        bitmask: 4-bit neighbor bitmask

    Returns:
        list: List of (dx, dy) tuples for each connected direction

    """
    directions = []

    if bitmask & DIR_NORTH:
        directions.append(DIRECTION_OFFSETS[DIR_NORTH])
    if bitmask & DIR_EAST:
        directions.append(DIRECTION_OFFSETS[DIR_EAST])
    if bitmask & DIR_SOUTH:
        directions.append(DIRECTION_OFFSETS[DIR_SOUTH])
    if bitmask & DIR_WEST:
        directions.append(DIRECTION_OFFSETS[DIR_WEST])

    return directions


def get_edge_transition_width(
    terrain_id: int, bitmask: int, base_tile_size: int = 48
) -> dict[str, int]:
    """Calculate edge transition widths for each direction based on connectivity.

    Connected edges have 0 transition width (seamless).
    Non-connected edges have transition width for shore/border effects.

    Args:
        terrain_id: Terrain type ID
        bitmask: Neighbor bitmask
        base_tile_size: Base tile size in pixels

    Returns:
        dict: Direction -> transition width mapping
            {'north': int, 'east': int, 'south': int, 'west': int}

    """
    # Base transition width scales with tile size
    base_width = max(4, base_tile_size // 10)

    return {
        "north": 0 if (bitmask & DIR_NORTH) else base_width,
        "east": 0 if (bitmask & DIR_EAST) else base_width,
        "south": 0 if (bitmask & DIR_SOUTH) else base_width,
        "west": 0 if (bitmask & DIR_WEST) else base_width,
    }


class AutotileCache:
    """Cache manager for autotile variants to avoid redundant generation."""

    def __init__(self):
        self._cache: dict[str, pygame.Surface] = {}
        self._building_clusters_cache: dict[str, list[list[tuple[int, int]]]] = {}

    def get_variant(
        self, terrain_id: int, bitmask: int, variation: int = 0
    ) -> pygame.Surface | None:
        """Get cached variant surface if exists."""
        key = self._make_cache_key(terrain_id, bitmask, variation)
        return self._cache.get(key)

    def set_variant(
        self, terrain_id: int, bitmask: int, variation: int, surface: pygame.Surface
    ) -> None:
        """Cache a generated variant surface."""
        key = self._make_cache_key(terrain_id, bitmask, variation)
        self._cache[key] = surface

    def clear(self) -> None:
        """Clear all cached variants."""
        self._cache.clear()
        self._building_clusters_cache.clear()

    def get_building_clusters(self, map_id: str) -> list[list[tuple[int, int]]] | None:
        """Get cached building clusters for a map."""
        return self._building_clusters_cache.get(map_id)

    def set_building_clusters(self, map_id: str, clusters: list[list[tuple[int, int]]]) -> None:
        """Cache building clusters for a map."""
        self._building_clusters_cache[map_id] = clusters

    @staticmethod
    def _make_cache_key(terrain_id: int, bitmask: int, variation: int) -> str:
        """Generate cache key from parameters."""
        return f"{terrain_id}_{bitmask}_{variation}"
