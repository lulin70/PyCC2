"""Unified Surface object pool with LRU eviction.
Eliminates duplicate pool implementations across sprite_renderer,
particle_system, and dynamic_shadow_system."""

from collections import OrderedDict
import pygame
from typing import Tuple


class SurfacePool:
    """LRU Surface pool to reuse pygame.Surface objects and reduce GC pressure."""

    def __init__(self, max_size: int = 30):
        self._pool: OrderedDict[Tuple[int, int], pygame.Surface] = OrderedDict()
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    def get(self, size: Tuple[int, int]) -> pygame.Surface:
        """Get or create a Surface of the given size. Marks as recently used (LRU)."""
        if size in self._pool:
            self._pool.move_to_end(size)  # LRU: mark as recently used
            self._hits += 1
            return self._pool[size]

        self._misses += 1
        surface = pygame.Surface(size, flags=pygame.SRCALPHA)
        self._pool[size] = surface

        # Evict oldest if over capacity
        if len(self._pool) > self._max_size:
            self._pool.popitem(last=False)  # Remove oldest (LRU)

        return surface

    def release(self, size: Tuple[int, int]) -> None:
        """Explicitly release a Surface back to pool (optional, GC will handle)."""
        pass  # Surfaces stay in pool until evicted by LRU

    def clear(self) -> None:
        """Clear all cached Surfaces."""
        self._pool.clear()

    @property
    def stats(self) -> dict:
        """Return pool statistics."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            "size": len(self._pool),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.1f}%",
        }
