"""Context-sensitive mouse cursor manager for CC2-style interaction."""

from __future__ import annotations

from enum import Enum, auto

import pygame


class CursorType(Enum):
    DEFAULT = auto()
    MOVE = auto()  # Green arrow - Move/Fast/Sneak mode
    ATTACK = auto()  # Red crosshair - Fire mode
    SMOKE = auto()  # Yellow circle - Smoke mode
    INVALID = auto()  # Gray X - Invalid target
    SELECT = auto()  # White highlight - Can select unit


class CursorManager:
    """Manages context-sensitive cursor rendering."""

    def __init__(self, tile_size: int = 48):
        """Initialize the CursorManager."""
        self._current = CursorType.DEFAULT
        self._cursors: dict[CursorType, pygame.Surface | None] = {}
        self._tile_size = tile_size
        self._build_cursors()

    def _build_cursors(self) -> None:
        """Pre-build all cursor surfaces."""
        size = 32

        # DEFAULT - normal arrow (use system default, so empty)
        self._cursors[CursorType.DEFAULT] = None

        # MOVE - green arrow
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        points = [(4, 0), (4, 24), (10, 18), (16, 28), (20, 26), (14, 16), (22, 16)]
        pygame.draw.polygon(surf, (0, 200, 0), points)
        pygame.draw.polygon(surf, (0, 100, 0), points, 1)
        self._cursors[CursorType.MOVE] = surf

        # ATTACK - red crosshair
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        cx, cy = 16, 16
        pygame.draw.circle(surf, (200, 0, 0), (cx, cy), 12, 2)
        pygame.draw.line(surf, (200, 0, 0), (cx, cy - 14), (cx, cy + 14), 2)
        pygame.draw.line(surf, (200, 0, 0), (cx - 14, cy), (cx + 14, cy), 2)
        pygame.draw.circle(surf, (200, 0, 0), (cx, cy), 3)
        self._cursors[CursorType.ATTACK] = surf

        # SMOKE - yellow circle
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(surf, (200, 200, 0), (16, 16), 12, 2)
        pygame.draw.circle(surf, (200, 200, 0, 80), (16, 16), 8)
        self._cursors[CursorType.SMOKE] = surf

        # INVALID - gray X
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.line(surf, (150, 150, 150), (4, 4), (28, 28), 3)
        pygame.draw.line(surf, (150, 150, 150), (28, 4), (4, 28), 3)
        self._cursors[CursorType.INVALID] = surf

        # SELECT - white highlight
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(surf, (255, 255, 255, 120), (16, 16), 14, 2)
        self._cursors[CursorType.SELECT] = surf

    def set_cursor(self, cursor_type: CursorType) -> None:
        """Set the current cursor type."""
        if cursor_type == self._current:
            return
        self._current = cursor_type
        try:
            if cursor_type == CursorType.DEFAULT:
                pygame.mouse.set_visible(True)
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
            else:
                # Hide system cursor, we'll draw our own
                pygame.mouse.set_visible(False)
        except pygame.error:
            # Video system not initialized (e.g. headless test)
            pass

    def render(self, surface: pygame.Surface, mouse_pos: tuple[int, int]) -> None:
        """Render the custom cursor at mouse position."""
        if self._current == CursorType.DEFAULT:
            return
        cursor_surf = self._cursors.get(self._current)
        if cursor_surf:
            surface.blit(cursor_surf, (mouse_pos[0] - 4, mouse_pos[1] - 4))

    @property
    def current(self) -> CursorType:
        """Get the current."""
        return self._current
