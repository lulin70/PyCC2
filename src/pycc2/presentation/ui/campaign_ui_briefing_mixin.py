"""Briefing and preview screen rendering mixin — extracted from CampaignUIRenderer.

Extracted during Phase 2 P0-1 (2026-07-04). See ``campaign_ui_rendering.py``
facade for the public API entry point.

Provides:
  - ``_render_briefing``: operation briefing screen with day header, strategic map, and battle selection.
  - ``_render_preview``: pre-battle preview with mini map, objectives, and forces.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pygame import Rect, Surface, draw

from .campaign_ui_helpers import (
    draw_button,
    draw_mini_map,
    draw_strategic_map,
    wrap_text,
)

if TYPE_CHECKING:
    from .campaign_ui import CampaignUI


class CampaignUIBriefingMixin:
    """Mixin: briefing and preview screens for CampaignUIRenderer.

    Relies on the facade's ``__init__`` to set ``self._ui``.
    """

    # -- Facade attribute set by CampaignUIRenderer.__init__ (typing only) --
    _ui: CampaignUI

    def _render_briefing(self, surface: Surface) -> None:
        """Render operation briefing screen with day header, strategic map, and battle selection."""
        ui = self._ui
        assert (
            ui._font_title is not None
            and ui._font_normal is not None
            and ui._font_small is not None
        )
        sw, sh = surface.get_size()
        surface.fill(ui.BG_COLOR)
        ui._battle_rects = {}

        if not ui._current_operation:
            return

        op = ui._current_operation

        # Header: Operation name + "Day X of 9"
        header_y = ui.MARGIN
        title_surf = ui._font_title.render(op.name, True, ui.HIGHLIGHT_COLOR)
        surface.blit(title_surf, (ui.MARGIN, header_y))

        day_text = f"Day {op.day} of {op.total_days}"
        day_surf = ui._font_normal.render(day_text, True, ui.HIGHLIGHT_COLOR)
        surface.blit(day_surf, (sw - ui.MARGIN - day_surf.get_width(), header_y + 6))

        sep_y = header_y + title_surf.get_height() + 8
        draw.line(surface, ui.BORDER_COLOR, (ui.MARGIN, sep_y), (sw - ui.MARGIN, sep_y), 1)

        # Layout: Left panel (briefing + strategic map), Right panel (battle selection)
        left_w = min(400, sw // 2)
        right_w = sw - left_w - ui.MARGIN * 3
        content_y = sep_y + 10
        content_h = sh - content_y - ui.BUTTON_HEIGHT - ui.MARGIN * 2 - 10

        # --- Left panel: Briefing text + Strategic map ---
        left_x = ui.MARGIN
        draw.rect(surface, ui.PANEL_COLOR, Rect(left_x, content_y, left_w, content_h))
        draw.rect(surface, ui.BORDER_COLOR, Rect(left_x, content_y, left_w, content_h), 1)

        # Briefing title
        briefing_title = ui._font_normal.render("HISTORICAL BRIEFING", True, ui.HIGHLIGHT_COLOR)
        surface.blit(briefing_title, (left_x + 10, content_y + 8))
        draw.line(
            surface,
            ui.BORDER_COLOR,
            (left_x, content_y + 30),
            (left_x + left_w, content_y + 30),
            1,
        )

        # Briefing text (word-wrapped)
        text = op.historical_briefing or op.description or "No briefing available."
        dy = content_y + 38
        briefing_lines = wrap_text(text, ui._font_normal, left_w - 30)
        max_briefing_lines = min(len(briefing_lines), 8)
        for line in briefing_lines[:max_briefing_lines]:
            if dy + 20 > content_y + content_h // 2:
                break
            ls = ui._font_normal.render(line, True, (200, 200, 190))
            surface.blit(ls, (left_x + 10, dy))
            dy += 22

        # Strategic map section
        map_section_y = content_y + content_h // 2 + 5
        map_label = ui._font_normal.render("STRATEGIC MAP", True, ui.HIGHLIGHT_COLOR)
        surface.blit(map_label, (left_x + 10, map_section_y))
        draw.line(
            surface,
            ui.BORDER_COLOR,
            (left_x, map_section_y + 22),
            (left_x + left_w, map_section_y + 22),
            1,
        )

        map_y = map_section_y + 26
        map_size = min(left_w - 20, content_y + content_h - map_y - 10)
        if map_size > 50:
            map_x = left_x + 10
            draw_strategic_map(ui, surface, map_x, map_y, map_size, op.sector, op.day)

        # --- Right panel: Operation description + Battle selection ---
        right_x = left_x + left_w + ui.MARGIN
        draw.rect(surface, ui.PANEL_COLOR, Rect(right_x, content_y, right_w, content_h))
        draw.rect(surface, ui.BORDER_COLOR, Rect(right_x, content_y, right_w, content_h), 1)

        # Operation description
        desc_title = ui._font_normal.render("OPERATION DETAILS", True, ui.HIGHLIGHT_COLOR)
        surface.blit(desc_title, (right_x + 10, content_y + 8))
        draw.line(
            surface,
            ui.BORDER_COLOR,
            (right_x, content_y + 30),
            (right_x + right_w, content_y + 30),
            1,
        )

        if op.description:
            dy = content_y + 36
            for line in wrap_text(op.description, ui._font_small, right_w - 30):
                if dy + 16 > content_y + 80:
                    break
                ls = ui._font_small.render(line, True, (180, 180, 170))
                surface.blit(ls, (right_x + 10, dy))
                dy += 16

        # Battle selection
        battle_title_y = content_y + 85
        battle_title = ui._font_normal.render("BATTLES THIS DAY", True, ui.HIGHLIGHT_COLOR)
        surface.blit(battle_title, (right_x + 10, battle_title_y))
        draw.line(
            surface,
            ui.BORDER_COLOR,
            (right_x, battle_title_y + 22),
            (right_x + right_w, battle_title_y + 22),
            1,
        )

        item_y = battle_title_y + 28
        for battle in op.battles:
            if item_y + ui.BATTLE_ITEM_HEIGHT > content_y + content_h:
                break

            item_rect = Rect(right_x + 6, item_y, right_w - 12, ui.BATTLE_ITEM_HEIGHT - 4)
            ui._battle_rects[battle.battle_id] = item_rect

            is_selected = battle.battle_id == ui._selected_battle_id
            is_hovered = battle.battle_id == ui._hovered_battle_id

            if battle.locked:
                bg = (40, 42, 45)
            elif is_selected:
                bg = ui.SELECTED_BG
            elif is_hovered:
                bg = (55, 62, 50)
            else:
                bg = (45, 50, 42)

            draw.rect(surface, bg, item_rect, border_radius=3)
            if is_selected:
                draw.rect(
                    surface,
                    ui.HIGHLIGHT_COLOR,
                    Rect(item_rect.left, item_rect.top, 2, item_rect.height),
                )

            if battle.completed:
                icon = ui._font_small.render("[OK]", True, ui.COMPLETED_COLOR)
            elif battle.locked:
                icon = ui._font_small.render("[--]", True, ui.LOCKED_COLOR)
            else:
                icon = ui._font_small.render("[>]", True, ui.HIGHLIGHT_COLOR)
            surface.blit(icon, (item_rect.left + 6, item_rect.top + 4))

            name_color = ui.LOCKED_COLOR if battle.locked else ui.TEXT_COLOR
            name_surf = ui._font_normal.render(battle.name, True, name_color)
            surface.blit(name_surf, (item_rect.left + 40, item_rect.top + 4))

            item_y += ui.BATTLE_ITEM_HEIGHT

        # Selected battle description
        sel_battle = None
        if ui._selected_battle_id:
            sel_battle = next(
                (b for b in op.battles if b.battle_id == ui._selected_battle_id), None
            )
        if sel_battle and sel_battle.description:
            desc_y = item_y + 8
            for line in wrap_text(sel_battle.description, ui._font_small, right_w - 30):
                if desc_y + 16 > content_y + content_h:
                    break
                ls = ui._font_small.render(line, True, (180, 180, 170))
                surface.blit(ls, (right_x + 10, desc_y))
                desc_y += 16

        # Buttons: Start Battle + Back
        btn_y = sh - ui.BUTTON_HEIGHT - ui.MARGIN
        ui._start_button_rect = Rect(
            sw - ui.MARGIN - ui.BUTTON_WIDTH * 2 - 10,
            btn_y,
            ui.BUTTON_WIDTH,
            ui.BUTTON_HEIGHT,
        )
        ui._back_button_rect = Rect(
            sw - ui.MARGIN - ui.BUTTON_WIDTH, btn_y, ui.BUTTON_WIDTH, ui.BUTTON_HEIGHT
        )

        draw_button(
            ui, surface, ui._start_button_rect, "Start Battle", ui._hovered_button == "start"
        )
        draw_button(
            ui, surface, ui._back_button_rect, "Back", ui._hovered_button == "back", ui.TEXT_COLOR
        )

    def _render_preview(self, surface: Surface) -> None:
        """Render pre-battle preview with mini map, objectives, and forces."""
        ui = self._ui
        assert (
            ui._font_title is not None
            and ui._font_normal is not None
            and ui._font_small is not None
        )
        sw, sh = surface.get_size()
        surface.fill(ui.BG_COLOR)

        if not ui._current_battle:
            return

        battle = ui._current_battle

        # Header
        header_y = ui.MARGIN
        title_surf = ui._font_title.render(battle.name, True, ui.HIGHLIGHT_COLOR)
        surface.blit(title_surf, (ui.MARGIN, header_y))

        sep_y = header_y + title_surf.get_height() + 8
        draw.line(surface, ui.BORDER_COLOR, (ui.MARGIN, sep_y), (sw - ui.MARGIN, sep_y), 1)

        # Left panel: Mini map
        map_panel_size = min(280, sh - sep_y - 120)
        map_x = ui.MARGIN
        map_y = sep_y + 10

        draw.rect(surface, ui.MINIMAP_BG, Rect(map_x, map_y, map_panel_size, map_panel_size))
        draw.rect(surface, ui.BORDER_COLOR, Rect(map_x, map_y, map_panel_size, map_panel_size), 1)

        map_label = ui._font_small.render(f"Map: {battle.map_file}", True, (150, 150, 140))
        surface.blit(map_label, (map_x + 4, map_y + map_panel_size + 4))

        # Draw a simple terrain preview grid
        draw_mini_map(ui, surface, map_x, map_y, map_panel_size, battle.map_file)

        # Right panel: Objectives and forces
        right_x = map_x + map_panel_size + 20
        right_w = sw - right_x - ui.MARGIN
        right_y = map_y

        # Objectives section
        obj_panel_h = map_panel_size // 2 - 5
        draw.rect(surface, ui.PANEL_COLOR, Rect(right_x, right_y, right_w, obj_panel_h))
        draw.rect(surface, ui.BORDER_COLOR, Rect(right_x, right_y, right_w, obj_panel_h), 1)

        obj_title = ui._font_normal.render("OBJECTIVES", True, ui.HIGHLIGHT_COLOR)
        surface.blit(obj_title, (right_x + 8, right_y + 4))
        draw.line(
            surface,
            ui.BORDER_COLOR,
            (right_x, right_y + 24),
            (right_x + right_w, right_y + 24),
            1,
        )

        dy = right_y + 28
        if battle.objectives:
            for obj in battle.objectives:
                if dy + 16 > right_y + obj_panel_h:
                    break
                obj_surf = ui._font_small.render(f"  * {obj}", True, (200, 200, 190))
                surface.blit(obj_surf, (right_x + 8, dy))
                dy += 16
        else:
            obj_surf = ui._font_small.render("  Secure the objective", True, (180, 180, 170))
            surface.blit(obj_surf, (right_x + 8, dy))

        # Forces section
        forces_y = right_y + obj_panel_h + 10
        forces_panel_h = map_panel_size // 2 - 5
        draw.rect(surface, ui.PANEL_COLOR, Rect(right_x, forces_y, right_w, forces_panel_h))
        draw.rect(surface, ui.BORDER_COLOR, Rect(right_x, forces_y, right_w, forces_panel_h), 1)

        forces_title = ui._font_normal.render("AVAILABLE FORCES", True, ui.HIGHLIGHT_COLOR)
        surface.blit(forces_title, (right_x + 8, forces_y + 4))
        draw.line(
            surface,
            ui.BORDER_COLOR,
            (right_x, forces_y + 24),
            (right_x + right_w, forces_y + 24),
            1,
        )

        dy = forces_y + 28
        # Allied forces
        allied_label = ui._font_small.render("Allied:", True, ui.COMPLETED_COLOR)
        surface.blit(allied_label, (right_x + 8, dy))
        dy += 16
        for force in battle.allied_forces or ["Standard Infantry Platoon"]:
            if dy + 14 > forces_y + forces_panel_h:
                break
            f_surf = ui._font_small.render(f"  {force}", True, (180, 180, 170))
            surface.blit(f_surf, (right_x + 8, dy))
            dy += 14

        dy += 4
        # Axis forces
        axis_label = ui._font_small.render("Axis:", True, ui.DEFEAT_COLOR)
        surface.blit(axis_label, (right_x + 8, dy))
        dy += 16
        for force in battle.axis_forces or ["German Garrison"]:
            if dy + 14 > forces_y + forces_panel_h:
                break
            f_surf = ui._font_small.render(f"  {force}", True, (180, 180, 170))
            surface.blit(f_surf, (right_x + 8, dy))
            dy += 14

        # Description below
        desc_y = map_y + map_panel_size + 24
        if battle.description:
            for line in wrap_text(battle.description, ui._font_small, sw - ui.MARGIN * 2):
                desc_surf = ui._font_small.render(line, True, (180, 180, 170))
                surface.blit(desc_surf, (ui.MARGIN, desc_y))
                desc_y += 16

        # Buttons
        btn_y = sh - ui.BUTTON_HEIGHT - ui.MARGIN
        ui._deploy_button_rect = Rect(
            sw - ui.MARGIN - ui.BUTTON_WIDTH * 2 - 10,
            btn_y,
            ui.BUTTON_WIDTH,
            ui.BUTTON_HEIGHT,
        )
        ui._back_button_rect = Rect(
            sw - ui.MARGIN - ui.BUTTON_WIDTH, btn_y, ui.BUTTON_WIDTH, ui.BUTTON_HEIGHT
        )

        draw_button(ui, surface, ui._deploy_button_rect, "Deploy", ui._hovered_button == "deploy")
        draw_button(
            ui, surface, ui._back_button_rect, "Back", ui._hovered_button == "back", ui.TEXT_COLOR
        )
