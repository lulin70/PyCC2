"""Strategic Map Renderer — displays the Operation Market Garden corridor.
Shows bridge status, unit positions, and campaign progress at a strategic level.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pygame


BRIDGE_POSITIONS: dict[str, dict[str, Any]] = {
    "arnhem": {"x": 0.50, "y": 0.08, "name": "Arnhem"},
    "nijmegen": {"x": 0.48, "y": 0.28, "name": "Nijmegen"},
    "grave": {"x": 0.45, "y": 0.48, "name": "Grave"},
    "veghel": {"x": 0.42, "y": 0.68, "name": "Veghel"},
    "son": {"x": 0.40, "y": 0.82, "name": "Son"},
}

CORRIDOR_PATH = [
    (0.40, 0.88),
    (0.40, 0.82),
    (0.42, 0.68),
    (0.45, 0.48),
    (0.48, 0.28),
    (0.50, 0.08),
]


@dataclass
class StrategicMapConfig:
    width: int = 800
    height: int = 500
    bg_color: tuple = (34, 40, 54)
    corridor_color: tuple = (70, 80, 100)
    bridge_neutral_color: tuple = (140, 120, 100)
    bridge_allied_color: tuple = (80, 160, 80)
    bridge_axis_color: tuple = (180, 70, 70)
    text_color: tuple = (220, 220, 220)
    highlight_color: tuple = (255, 200, 50)


class StrategicMapRenderer:
    def __init__(self, config: StrategicMapConfig | None = None):
        """Initialize the StrategicMapRenderer."""
        self.config = config or StrategicMapConfig()
        self._surface = None
        self._selected_bridge: str | None = None
        self._panel_surface: pygame.Surface | None = None
        self._panel_size: tuple[int, int] = (0, 0)

    def render(
        self,
        screen: pygame.Surface,
        campaign_state=None,
        font=None,
    ) -> None:
        """Render to the screen."""
        import pygame

        cfg = self.config
        w, h = cfg.width, cfg.height
        cx, cy = screen.get_size()

        offset_x = (cx - w) // 2
        offset_y = (cy - h) // 2 + 20

        # Lazy-init or resize panel surface
        if self._panel_surface is None or self._panel_size != (w, h):
            self._panel_surface = pygame.Surface((w, h))
            self._panel_size = (w, h)
        self._panel_surface.fill(cfg.bg_color)
        self._panel_surface.set_alpha(240)

        if len(CORRIDOR_PATH) >= 2:
            pts = [(int(p[0] * w) + offset_x, int(p[1] * h) + offset_y) for p in CORRIDOR_PATH]
            pygame.draw.lines(self._panel_surface, cfg.corridor_color, False, pts, 3)

        bridges_state = {}
        if campaign_state is not None:
            bridges_state = campaign_state.bridges_captured

        for key, pos in BRIDGE_POSITIONS.items():
            bx = int(pos["x"] * w) + offset_x
            by = int(pos["y"] * h) + offset_y

            captured = bridges_state.get(key, False)

            color = cfg.bridge_allied_color if captured else cfg.bridge_neutral_color

            if key == self._selected_bridge:
                pygame.draw.circle(self._panel_surface, cfg.highlight_color, (bx, by), 18, 2)

            pygame.draw.circle(self._panel_surface, color, (bx, by), 12)
            pygame.draw.circle(self._panel_surface, (255, 255, 255), (bx, by), 12, 1)

        screen.blit(self._panel_surface, (offset_x, offset_y))

        if font:
            for key, pos in BRIDGE_POSITIONS.items():
                bx = int(pos["x"] * w) + offset_x
                by = int(pos["y"] * h) + offset_y + 20
                name = BRIDGE_POSITIONS[key]["name"]
                captured = bridges_state.get(key, False)
                prefix = "✓ " if captured else "  "
                label = font.render(f"{prefix}{name}", True, cfg.text_color)
                screen.blit(label, (bx - label.get_width() // 2, by))

    def handle_click(self, x: int, y: int, map_offset: tuple[int, int]) -> str | None:
        """Handle click."""
        cfg = self.config
        ox, oy = map_offset
        mx, my = x - ox, y - oy

        for key, pos in BRIDGE_POSITIONS.items():
            bx = pos["x"] * cfg.width
            by = pos["y"] * cfg.height
            dist = math.sqrt((mx - bx) ** 2 + (my - by) ** 2)
            if dist <= 15:
                self._selected_bridge = key
                return key
        return None

    def get_bridge_info(self, bridge_key: str) -> dict | None:
        """Get the bridge info."""
        if bridge_key not in BRIDGE_POSITIONS:
            return None
        pos = BRIDGE_POSITIONS[bridge_key]
        return {
            "key": bridge_key,
            "name": pos["name"],
            "position_pct": (pos["x"], pos["y"]),
        }

    @property
    def all_bridges(self) -> list[dict[str, Any] | None]:
        """Get the all bridges."""
        return [self.get_bridge_info(k) for k in BRIDGE_POSITIONS]

    @property
    def selected_bridge(self) -> str | None:
        """Get the selected bridge."""
        return self._selected_bridge

    def clear_selection(self) -> None:
        """Clear selection."""
        self._selected_bridge = None
