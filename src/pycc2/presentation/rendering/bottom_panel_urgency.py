"""Urgency/threat indicator rendering for the CC2 bottom panel."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pygame import Rect, Surface, draw

if TYPE_CHECKING:
    from pycc2.presentation.rendering.cc2_bottom_panel import CC2BottomPanel


class UrgencyIndicatorRenderer:
    """Renders the color-coded urgency indicator next to the command bar."""

    def __init__(self, panel: CC2BottomPanel) -> None:
        self._panel = panel

    def render(self, surface: Surface, x: int, y: int, w: int, h: int) -> None:
        """Render color-coded urgency/threat indicator."""
        # Background
        draw.rect(surface, (30, 33, 38), Rect(x, y, w, h))
        draw.rect(surface, self._panel.BORDER_COLOR, Rect(x, y, w, h), 1)

        # Title
        title = self._panel._font_small.render("URGENCY", True, self._panel.TEXT_COLOR)
        surface.blit(title, (x + 5, y + 3))

        # Determine urgency level based on selected unit
        urgency = "SAFE"
        urgency_value = 0

        if self._panel._selected_unit_id:
            unit = next(
                (u for u in self._panel._friendly_units if u.id == self._panel._selected_unit_id),
                None,
            )
            if unit:
                hp_current = unit.health.hp
                hp_max = unit.health.max_hp
                hp_ratio = hp_current / max(hp_max, 1)
                morale = unit.morale.value if unit.morale is not None else 75

                # Calculate urgency (0-100)
                urgency_value = int((1 - hp_ratio) * 50 + (1 - morale / 100) * 50)

                if urgency_value >= 80:
                    urgency = "CRITICAL"
                elif urgency_value >= 60:
                    urgency = "HIGH"
                elif urgency_value >= 40:
                    urgency = "MEDIUM"
                elif urgency_value >= 20:
                    urgency = "LOW"

        # Draw vertical urgency bar
        bar_x = x + w // 2 - 15
        bar_y = y + 25
        bar_h = h - 35
        bar_w = 30

        # Background
        draw.rect(surface, (40, 40, 40), Rect(bar_x, bar_y, bar_w, bar_h))

        # Filled portion (bottom-up)
        fill_h = int(bar_h * urgency_value / 100)
        color = self._panel.URGENCY_COLORS.get(urgency, self._panel.URGENCY_COLORS["SAFE"])
        draw.rect(surface, color, Rect(bar_x, bar_y + bar_h - fill_h, bar_w, fill_h))

        # Border
        draw.rect(surface, self._panel.BORDER_COLOR, Rect(bar_x, bar_y, bar_w, bar_h), 1)

        # Labels
        labels = ["!", "!!", "!!!", "", ""]
        label_idx = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "SAFE"].index(urgency)
        label = self._panel._font_small.render(labels[label_idx], True, color)
        surface.blit(
            label,
            (bar_x + 8, bar_y + bar_h - fill_h - 15 if fill_h > 15 else bar_y + 5),
        )
