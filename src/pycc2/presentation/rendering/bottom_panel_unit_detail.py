"""Selected-unit detail rendering for the CC2 bottom panel."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pygame import Rect, Surface, draw

from pycc2.presentation.rendering.bottom_panel_soldier_monitor import (
    SoldierMonitorRenderer,
)

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit
    from pycc2.presentation.rendering.cc2_bottom_panel import CC2BottomPanel


class UnitDetailRenderer:
    """Renders detailed status info and soldier monitor for the selected unit."""

    def __init__(self, panel: CC2BottomPanel) -> None:
        self._panel = panel
        self._soldier_monitor = SoldierMonitorRenderer(panel)

    def render(self, surface: Surface, x: int, y: int, w: int, h: int) -> None:
        """Render detailed info for selected unit."""
        # Background
        draw.rect(surface, (30, 33, 38), Rect(x, y, w, h))
        draw.rect(surface, self._panel.BORDER_COLOR, Rect(x, y, w, h), 1)

        if not self._panel._selected_unit_id:
            no_sel = self._panel._font_normal.render("No unit selected", True, (128, 128, 128))
            surface.blit(no_sel, (x + 10, y + h // 2 - 10))
            return

        # Find selected unit
        unit = next(
            (u for u in self._panel._friendly_units if u.id == self._panel._selected_unit_id),
            None,
        )
        if not unit:
            return

        line_y = y + 5
        line_height = 18

        # Commander portrait (24x24) if unit is commander/officer type
        portrait_offset = 0
        icon_key = self._map_unit_type_to_icon_key(unit)
        if icon_key == "commander" and self._panel._commander_portrait:
            surface.blit(self._panel._commander_portrait, (x + 8, line_y))
            portrait_offset = 28  # Shift title right to make room for portrait

        # Title — Unit uses .name, not .display_name
        display_name = unit.name
        title = self._panel._font_title.render(str(display_name), True, self._panel.HIGHLIGHT_COLOR)
        surface.blit(title, (x + 8 + portrait_offset, line_y))
        line_y += line_height + 5

        # Separator line under title
        draw.line(surface, (45, 48, 55), (x, line_y - 3), (x + w, line_y - 3), 1)

        # Type and faction
        type_str = f"Type: {unit.unit_type.name[:15]}"
        faction_str = f"Faction: {unit.faction.name}"
        surface.blit(
            self._panel._font_small.render(type_str, True, self._panel.TEXT_COLOR), (x + 8, line_y)
        )
        line_y += line_height
        surface.blit(
            self._panel._font_small.render(faction_str, True, self._panel.TEXT_COLOR),
            (x + 8, line_y),
        )
        line_y += line_height + 5

        # Health — HealthComponent uses .hp/.max_hp
        hp_current = unit.health.hp
        hp_max = unit.health.max_hp
        hp_text = f"HP: {hp_current}/{hp_max}"
        hp_color = (255, 80, 80) if hp_current < hp_max * 0.3 else self._panel.TEXT_COLOR
        surface.blit(self._panel._font_normal.render(hp_text, True, hp_color), (x + 8, line_y))
        # Health bar with 1px dark border
        bar_w = w - 120
        draw.rect(surface, (40, 42, 48), Rect(x + 109, line_y + 1, bar_w + 2, 14))
        draw.rect(surface, (60, 60, 60), Rect(x + 110, line_y + 2, bar_w, 12))
        hp_ratio = hp_current / max(hp_max, 1)
        draw.rect(surface, (50, 180, 50), Rect(x + 110, line_y + 2, int(bar_w * hp_ratio), 12))
        line_y += line_height + 3

        # Morale — MoraleComponent uses .value, not .current
        morale_val = unit.morale.value if unit.morale is not None else 75
        morale_text = f"Morale: {morale_val}%"
        morale_color = (
            (255, 80, 80)
            if morale_val < 30
            else (255, 200, 0)
            if morale_val < 60
            else (80, 200, 80)
        )
        surface.blit(
            self._panel._font_normal.render(morale_text, True, morale_color), (x + 8, line_y)
        )
        # Morale bar with 1px dark border
        draw.rect(surface, (40, 42, 48), Rect(x + 109, line_y + 1, bar_w + 2, 14))
        draw.rect(surface, (60, 60, 60), Rect(x + 110, line_y + 2, bar_w, 12))
        draw.rect(
            surface,
            morale_color,
            Rect(x + 110, line_y + 2, int(bar_w * morale_val / 100), 12),
        )
        line_y += line_height + 3

        # Ammo
        # Ammo — WeaponComponent uses .ammo_remaining/.max_ammo
        ammo_current = unit.weapon.ammo_remaining if unit.weapon is not None else 30
        ammo_max = unit.weapon.max_ammo if unit.weapon is not None else 30
        ammo_text = f"Ammo: {ammo_current}/{ammo_max}"
        surface.blit(
            self._panel._font_normal.render(ammo_text, True, self._panel.TEXT_COLOR),
            (x + 8, line_y),
        )
        # Ammo bar with 1px dark border
        draw.rect(surface, (40, 42, 48), Rect(x + 109, line_y + 1, bar_w + 2, 14))
        draw.rect(surface, (60, 60, 60), Rect(x + 110, line_y + 2, bar_w, 12))
        ammo_ratio = ammo_current / max(ammo_max, 1)
        draw.rect(surface, (100, 150, 255), Rect(x + 110, line_y + 2, int(bar_w * ammo_ratio), 12))
        line_y += line_height + 3

        # Smoke grenades (if applicable)
        smoke_count = getattr(unit, "smoke_grenades", 2)
        smoke_text = f"Smoke: {smoke_count}"
        surface.blit(
            self._panel._font_normal.render(smoke_text, True, (200, 200, 100)), (x + 8, line_y)
        )
        line_y += line_height + 3

        # AP/AT Resource Bars (Action Points / Attack Points) - CC2 style
        ap_current = getattr(unit, "action_points", getattr(unit, "ap", 10))
        ap_max = getattr(unit, "max_action_points", getattr(unit, "max_ap", 10))
        at_current = getattr(unit, "attack_points", getattr(unit, "at", 5))
        at_max = getattr(unit, "max_attack_points", getattr(unit, "max_at", 5))

        # AP Bar (Green - movement resource)
        ap_text = f"AP: {ap_current}/{ap_max}"
        surface.blit(
            self._panel._font_normal.render(ap_text, True, (100, 255, 150)), (x + 8, line_y)
        )
        draw.rect(surface, (40, 42, 48), Rect(x + 109, line_y + 1, bar_w + 2, 14))
        draw.rect(surface, (60, 60, 60), Rect(x + 110, line_y + 2, bar_w, 12))
        ap_ratio = ap_current / max(ap_max, 1)
        # AP color: Green (full) -> Yellow (mid) -> Red (low)
        if ap_ratio > 0.6:
            ap_color = (80, 220, 80)
        elif ap_ratio > 0.3:
            ap_color = (220, 200, 50)
        else:
            ap_color = (220, 80, 80)
        draw.rect(surface, ap_color, Rect(x + 110, line_y + 2, int(bar_w * ap_ratio), 12))
        line_y += line_height + 3

        # AT Bar (Orange - attack resource)
        at_text = f"AT: {at_current}/{at_max}"
        surface.blit(
            self._panel._font_normal.render(at_text, True, (255, 180, 100)), (x + 8, line_y)
        )
        draw.rect(surface, (40, 42, 48), Rect(x + 109, line_y + 1, bar_w + 2, 14))
        draw.rect(surface, (60, 60, 60), Rect(x + 110, line_y + 2, bar_w, 12))
        at_ratio = at_current / max(at_max, 1)
        # AT color: Orange (full) -> Yellow (mid) -> Red (low)
        if at_ratio > 0.6:
            at_color = (255, 180, 80)
        elif at_ratio > 0.3:
            at_color = (220, 180, 50)
        else:
            at_color = (220, 80, 80)
        draw.rect(surface, at_color, Rect(x + 110, line_y + 2, int(bar_w * at_ratio), 12))
        line_y += line_height + 3

        # Casualties
        squad_size = getattr(unit, "squad_size", 10)
        casualties = getattr(unit, "casualties", 0)
        alive = squad_size - casualties
        cas_text = f"Squad: {alive}/{squad_size} ({casualties} KIA)"
        cas_color = (255, 100, 100) if casualties > 0 else self._panel.TEXT_COLOR
        surface.blit(self._panel._font_small.render(cas_text, True, cas_color), (x + 8, line_y))
        line_y += line_height + 3

        # Status
        state_name = unit.state_machine.current.name if unit.state_machine is not None else "IDLE"
        status_text = f"Status: {state_name}"
        surface.blit(
            self._panel._font_small.render(status_text, True, (180, 180, 180)), (x + 8, line_y)
        )
        line_y += line_height + 3

        # Soldier Monitor (when unit has squad_ref)
        squad_ref = getattr(unit, "squad_ref", None)
        if squad_ref is not None and line_y < y + h - 10:
            self._soldier_monitor.render(surface, x, line_y, w, y + h - line_y, squad_ref)

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
