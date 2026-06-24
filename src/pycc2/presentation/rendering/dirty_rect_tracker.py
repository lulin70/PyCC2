"""Dirty Rectangle Tracker for partial display updates.

Only regions marked dirty are passed to ``pygame.display.update(rects)``,
avoiding a full-screen blit to the GPU when only small areas changed.
Falls back to full ``flip()`` when too many rects accumulate or when
a full-dirty event occurs (camera move, screen flash, etc.).

Thread-safety: single-threaded render loop — no locking needed.
"""

from __future__ import annotations

import pygame


class _DirtyRectTracker:
    """Track dirty screen regions for partial display updates.

    Only regions marked dirty are passed to ``pygame.display.update(rects)``,
    avoiding a full-screen blit to the GPU when only small areas changed.
    Falls back to full ``flip()`` when too many rects accumulate or when
    a full-dirty event occurs (camera move, screen flash, etc.).

    Thread-safety: single-threaded render loop — no locking needed.
    """

    __slots__ = ("_dirty_rects", "_full_redraw", "_screen_rect", "_max_rects")

    def __init__(self, screen_w: int, screen_h: int, max_rects: int = 16):
        self._dirty_rects: list[pygame.Rect] = []
        self._full_redraw: bool = True  # First frame always full redraw
        self._screen_rect: pygame.Rect = pygame.Rect(0, 0, screen_w, screen_h)
        self._max_rects: int = max_rects

    def mark_dirty(self, rect: pygame.Rect | None) -> None:
        """Mark a screen-region rectangle as dirty.

        *rect* may be ``None`` to force a full redraw on this frame.
        Overlapping / adjacent rectangles are merged to keep the count low.
        """
        if rect is None:
            self._full_redraw = True
            return

        # Clamp to screen bounds
        rect = rect.clip(self._screen_rect)
        if rect.width == 0 or rect.height == 0:
            return

        # Merge with existing rects if they overlap
        merged = False
        for i, existing in enumerate(self._dirty_rects):
            if rect.colliderect(existing):
                union = rect.union(existing)
                # Only merge if union is not much larger than sum (avoids bloating)
                if (
                    union.width * union.height
                    < rect.width * rect.height + existing.width * existing.height + 200
                ):
                    self._dirty_rects[i] = union
                    merged = True
                    break
        if not merged:
            self._dirty_rects.append(rect)

    def mark_full_dirty(self) -> None:
        """Force a full-screen update on the current frame."""
        self._full_redraw = True
        self._dirty_rects.clear()

    def get_update_rects(self) -> list[pygame.Rect] | None:
        """Return the list of rects to update, or *None* for full flip."""
        if self._full_redraw:
            return None  # Caller should use flip()
        if len(self._dirty_rects) > self._max_rects:
            return None  # Too many regions → fall back
        if not self._dirty_rects:
            return [pygame.Rect(0, 0, 0, 0)]  # No-op: empty update
        return self._dirty_rects.copy()

    def next_frame(self) -> None:
        """Clear per-frame state; call after ``display.flip/update``."""
        if self._full_redraw:
            self._full_redraw = False
        self._dirty_rects.clear()
