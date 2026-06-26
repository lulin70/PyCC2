"""Unit roster rendering for the CC2 bottom panel."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pygame import Rect, Surface, draw

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit
    from pycc2.presentation.rendering.cc2_bottom_panel import CC2BottomPanel


class RosterRenderer:
    """Renders the scrollable friendly-unit roster on the left side of the panel."""

    def __init__(self, panel: CC2BottomPanel) -> None:
        self._panel = panel

    def render(self, surface: Surface, x: int, y: int, w: int, h: int) -> None:
        """Render the unit roster list."""
        # Background
        draw.rect(surface, (30, 33, 38), Rect(x, y, w, h))
        draw.rect(surface, self._panel.BORDER_COLOR, Rect(x, y, w, h), 1)

        # Title
        title = self._panel._font_title.render("TROOPS", True, self._panel.HIGHLIGHT_COLOR)
        surface.blit(title, (x + 5, y + 2))

        # Separator line under title
        draw.line(surface, (45, 48, 55), (x, y + 18), (x + w, y + 18), 1)

        # Unit list
        self._panel._roster_item_rects = []
        visible_units = self._panel._friendly_units[
            self._panel._roster_scroll_offset : self._panel._roster_scroll_offset
            + self._panel._visible_roster_items
        ]

        item_y = y + 22
        for unit in visible_units:
            is_selected = unit.id == self._panel._selected_unit_id
            item_rect = Rect(x + 2, item_y, w - 4, self._panel._roster_item_height)

            # Background
            bg_color = self._panel.SELECTED_BG if is_selected else (35, 38, 43)
            draw.rect(surface, bg_color, item_rect)

            # Selection highlight: 2px bright left indicator bar
            if is_selected:
                draw.rect(
                    surface,
                    self._panel.HIGHLIGHT_COLOR,
                    Rect(x + 2, item_y, 2, self._panel._roster_item_height),
                )

            # Unit type thumbnail icon (16x16)
            icon_key = self._map_unit_type_to_icon_key(unit)
            roster_icon = self._panel._roster_icons.get(icon_key)
            if roster_icon:
                surface.blit(roster_icon, (x + 5, item_y + 5))

            # Unit name (truncated) — Unit uses .name, not .display_name
            name = unit.name
            name = str(name)[:12]
            text_color = self._panel.HIGHLIGHT_COLOR if is_selected else self._panel.TEXT_COLOR
            name_surf = self._panel._font_small.render(name, True, text_color)
            surface.blit(name_surf, (x + 23, item_y + 5))

            # Health bar with 1px dark border — HealthComponent uses .hp/.max_hp
            hp_current = unit.health.hp
            hp_max = unit.health.max_hp
            hp_ratio = hp_current / max(hp_max, 1)
            bar_width = 50
            bar_x = x + w - bar_width - 45  # P2-A: Shifted left to make room for HP text
            # Dark border around health bar
            draw.rect(surface, (40, 42, 48), Rect(bar_x - 1, item_y + 8, bar_width + 2, 10))
            draw.rect(surface, (60, 60, 60), Rect(bar_x, item_y + 9, bar_width, 8))
            hp_color = (
                (255, 50, 50)
                if hp_ratio < 0.3
                else (255, 200, 0)
                if hp_ratio < 0.6
                else (50, 200, 50)
            )
            draw.rect(surface, hp_color, Rect(bar_x, item_y + 9, int(bar_width * hp_ratio), 8))

            # P2-A: HP numeric value next to bar for better readability
            hp_text = f"{hp_current}/{hp_max}"
            hp_text_surf = self._panel._font_small.render(hp_text, True, hp_color)
            surface.blit(hp_text_surf, (bar_x + bar_width + 3, item_y + 7))

            # P2-A: Morale status indicator (small colored dot after name)
            if hasattr(unit, "morale") and unit.morale is not None:
                morale_val = unit.morale.value
                if morale_val > 70:
                    morale_dot_color = (100, 220, 100)  # Green - good morale
                elif morale_val > 40:
                    morale_dot_color = (220, 200, 80)  # Yellow - caution
                else:
                    morale_dot_color = (255, 100, 100)  # Red - low morale
                dot_x = x + 23 + name_surf.get_width() + 4
                draw.circle(surface, morale_dot_color, (dot_x, item_y + 13), 3)

            self._panel._roster_item_rects.append((item_rect, unit.id))
            item_y += self._panel._roster_item_height

        # Scroll indicator
        total_items = len(self._panel._friendly_units)
        if total_items > self._panel._visible_roster_items:
            scroll_bar_h = h * (self._panel._visible_roster_items / total_items)
            scroll_bar_y = (
                y
                + 22
                + (h - 22)
                * (self._panel._roster_scroll_offset / (total_items - self._panel._visible_roster_items))
            )
            draw.rect(surface, (80, 80, 80), Rect(x + w - 4, scroll_bar_y, 3, scroll_bar_h))

    @staticmethod
    def _map_unit_type_to_icon_key(unit: Unit) -> str:
        """Map a unit's type to the roster icon key."""
        type_name = unit.unit_type.name.lower()
        if "tank" in type_name or "armor" in type_name or "vehicle" in type_name:
            return "tank"
        elif "mg" in type_name or "machine" in type_name:
            return "mg"
        elif "sniper" in type_name or "scout" in type_name:
            return "sniper"
        elif "officer" in type_name or "commander" in type_name:
            return "commander"
        elif "at" in type_name or "anti" in type_name:
            return "at"
        elif "mortar" in type_name:
            return "mortar"
        elif "medic" in type_name or "aid" in type_name:
            return "medic"
        else:
            return "infantry"
