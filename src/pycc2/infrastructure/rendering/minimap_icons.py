"""Minimap icon differentiation system (C7)."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from enum import Enum


class UnitIconType(Enum):
    """Types of unit icons for minimap."""

    INFANTRY = "circle"
    VEHICLE = "rectangle"
    MG_TEAM = "diamond"
    OFFICER = "star"
    UNKNOWN = "dot"


@dataclass
class MinimapIconSystem:
    """
    Minimap icon differentiation system.

    Different icons for different unit types:
    - Infantry: circle
    - Vehicle: rectangle
    - MG Team: diamond
    - Officer: star
    """

    ICON_COLORS = {
        "allied": (0, 255, 0),  # Green
        "axis": (255, 50, 50),  # Red
        "neutral": (200, 200, 0),  # Yellow
    }

    def get_icon_type(self, unit) -> UnitIconType:
        """Determine icon type based on unit attributes."""
        unit_type = getattr(unit, "unit_type", "").lower()

        if "officer" in unit_type or "commander" in unit_type:
            return UnitIconType.OFFICER
        elif "vehicle" in unit_type or "tank" in unit_type:
            return UnitIconType.VEHICLE
        elif "mg" in unit_type or "machinegun" in unit_type:
            return UnitIconType.MG_TEAM
        elif "infantry" in unit_type or "rifle" in unit_type or "soldier" in unit_type:
            return UnitIconType.INFANTRY
        else:
            return UnitIconType.UNKNOWN

    def get_icon_color(self, unit) -> tuple[int, int, int]:
        """Get color based on faction."""
        faction = getattr(unit, "faction", "unknown").lower()

        if faction in ("allied", "player", "friendly"):
            return self.ICON_COLORS["allied"]
        elif faction in ("axis", "enemy", "hostile"):
            return self.ICON_COLORS["axis"]
        else:
            return self.ICON_COLORS["neutral"]

    def render_icon(
        self,
        surface,
        screen_pos: tuple[int, int],
        icon_type: UnitIconType,
        color: tuple[int, int, int],
        size: int = 4,
    ) -> None:
        """Render a single minimap icon."""
        try:
            import pygame

            x, y = screen_pos

            if icon_type == UnitIconType.INFANTRY:
                pygame.draw.circle(surface, color, (x, y), size)
            elif icon_type == UnitIconType.VEHICLE:
                rect = pygame.Rect(x - size, y - size // 2, size * 2, size)
                pygame.draw.rect(surface, color, rect)
            elif icon_type == UnitIconType.MG_TEAM:
                points = [
                    (x, y - size),
                    (x + size, y),
                    (x, y + size),
                    (x - size, y),
                ]
                pygame.draw.polygon(surface, color, points)
            elif icon_type == UnitIconType.OFFICER:
                self._draw_star(surface, x, y, color, size)
            else:
                pygame.draw.circle(surface, color, (x, y), size // 2)

        except Exception as e:
            logging.debug(f"Unit icon draw failed: {e}")

    @staticmethod
    def _draw_star(surface, cx, cy, color, size):
        """Draw a star shape."""
        try:
            import pygame

            points = []
            for i in range(10):
                angle = math.pi / 2 + i * math.pi / 5
                r = size if i % 2 == 0 else size // 2
                px = cx + r * math.cos(angle)
                py = cy - r * math.sin(angle)
                points.append((px, py))
            pygame.draw.polygon(surface, color, points)
        except Exception as e:
            logging.debug(f"Star shape draw failed: {e}")
