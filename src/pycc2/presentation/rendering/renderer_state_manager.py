"""Renderer state manager - display surface, offscreen buffer, and cache lifecycle.

Extracted from EnhancedRenderer to keep the coordinator focused on public API
delegation and subsystem wiring. Manages:
- Display surface reference
- Offscreen rendering buffer
- Surface pool for temporary surfaces
- Post-processing effects instance
- Dirty rectangle tracker
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pygame

from pycc2.presentation.rendering.dirty_rect_tracker import _DirtyRectTracker
from pycc2.presentation.rendering.surface_pool import SurfacePool

if TYPE_CHECKING:
    from pycc2.presentation.rendering.post_processing import PostProcessingEffects

logger = logging.getLogger(__name__)


class RendererStateManager:
    """Manages renderer display/surface state and cache lifecycle."""

    TRANSPARENT_BLACK = (0, 0, 0, 0)

    def __init__(self, tile_size: int):
        self._tile_size = tile_size
        self._screen: pygame.Surface | None = None
        self._offscreen: pygame.Surface | None = None
        self._surface_pool = SurfacePool(max_size=50)
        self._post_processing: PostProcessingEffects | None = None
        self._dirty_tracker: _DirtyRectTracker | None = None

    @property
    def screen(self) -> pygame.Surface | None:
        return self._screen

    @property
    def offscreen(self) -> pygame.Surface | None:
        return self._offscreen

    @property
    def post_processing(self) -> PostProcessingEffects | None:
        return self._post_processing

    @property
    def dirty_tracker(self) -> _DirtyRectTracker | None:
        return self._dirty_tracker

    def initialize(self, screen: pygame.Surface) -> pygame.Surface:
        """Create offscreen buffer, post-processing, and dirty tracker."""
        self._screen = screen
        self._offscreen = self._create_offscreen(screen)
        self._post_processing = self._create_post_processing(screen)
        self._dirty_tracker = self._create_dirty_tracker(screen)
        return self._offscreen

    def _create_offscreen(self, screen: pygame.Surface) -> pygame.Surface:
        try:
            return pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        except pygame.error as e:
            import warnings

            warnings.warn(
                f"Could not create SRCALPHA surface: {e}. Using convert() fallback.",
                stacklevel=2,
            )
            return pygame.Surface(screen.get_size()).convert()

    def _create_post_processing(self, screen: pygame.Surface) -> PostProcessingEffects | None:
        try:
            from pycc2.presentation.rendering.post_processing import PostProcessingEffects

            sw, sh = screen.get_size()
            post_processing = PostProcessingEffects(sw, sh)
            post_processing.enable_color_grading()
            return post_processing
        except (pygame.error, ValueError, RuntimeError) as e:
            logger.warning("PostProcessingEffects init failed (non-critical): %s", e)
            return None

    def _create_dirty_tracker(self, screen: pygame.Surface) -> _DirtyRectTracker:
        sw, sh = screen.get_size()
        return _DirtyRectTracker(sw, sh)

    def ensure_offscreen(self) -> pygame.Surface | None:
        """Recreate offscreen buffer if screen size changed."""
        if self._screen is None:
            return None
        screen_size = self._screen.get_size()
        if self._offscreen is None or self._offscreen.get_size() != screen_size:
            self._offscreen = pygame.Surface(screen_size, pygame.SRCALPHA)
        return self._offscreen

    def resize(self, width: int, height: int) -> None:
        """Reinitialize offscreen buffer and dirty tracker on window resize."""
        if self._screen is None:
            return
        try:
            self._offscreen = pygame.Surface((width, height), pygame.SRCALPHA)
            self.invalidate_cache()
            self._dirty_tracker = _DirtyRectTracker(width, height)
        except (pygame.error, ValueError):
            logger.warning("Failed to resize offscreen buffer to %dx%d", width, height)

    def invalidate_cache(self) -> None:
        """Clear surface pool when screen size changes."""
        self._surface_pool.clear()

    def get_pooled_surface(self, size: tuple[int, int]) -> pygame.Surface:
        """Get or create a surface from the object pool with LRU eviction."""
        surf = self._surface_pool.get(size)
        surf.fill(self.TRANSPARENT_BLACK)
        return surf

    def shutdown(self) -> None:
        """Clear surface pool."""
        self._surface_pool.clear()
