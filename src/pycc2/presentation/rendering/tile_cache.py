"""Tile Cache System

Pre-renders and caches scaled terrain tile surfaces to avoid per-frame transform.scale() calls.
Improves rendering performance by storing generated tiles in a two-level dictionary keyed by terrain_id and size.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pygame


class TileCache:
    """Pre-renders and caches scaled terrain tile surfaces to avoid per-frame transform.scale()"""

    def __init__(self):
        self._cache: dict[int, dict[int, pygame.Surface]] = {}
        self._cache_hits: int = 0
        self._cache_misses: int = 0

    def get_tile(self, terrain_id: int, size: int) -> pygame.Surface:
        """Get cached tile surface, or generate and cache it."""
        if terrain_id not in self._cache:
            self._cache[terrain_id] = {}

        if size in self._cache[terrain_id]:
            self._cache_hits += 1
            return self._cache[terrain_id][size]

        self._cache_misses += 1
        from pycc2.presentation.rendering.pixel_artist import create_terrain_tile

        canvas = create_terrain_tile(terrain_id, size)
        surface = canvas.to_surface()
        self._cache[terrain_id][size] = surface
        return surface

    def invalidate(self, terrain_id: int | None = None) -> None:
        """Invalidate cache entries. If terrain_id is None, clear all."""
        if terrain_id is not None:
            self._cache.pop(terrain_id, None)
        else:
            self._cache.clear()

    @property
    def stats(self) -> dict[str, int]:
        return {"hits": self._cache_hits, "misses": self._cache_misses}

    @property
    def hit_rate(self) -> float:
        total = self._cache_hits + self._cache_misses
        return self._cache_hits / max(total, 1)

    @property
    def cached_tile_count(self) -> int:
        return sum(len(sizes) for sizes in self._cache.values())
