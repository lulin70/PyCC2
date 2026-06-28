"""Campaign UI rendering logic — extracted from CampaignUI.

All render methods live here as methods of ``CampaignUIRenderer``,
which holds a back-reference to the parent :class:`CampaignUI` instance
so it can read state (fonts, rects, selections, etc.) directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame
from pygame import Rect, Surface, draw

from .campaign_ui_helpers import (
    draw_button,
    draw_mini_map,
    draw_strategic_map,
    wrap_text,
)

if TYPE_CHECKING:
    from .campaign_ui import CampaignUI


class CampaignUIRenderer:
    """Renders every screen state for CampaignUI."""

    def __init__(self, ui: CampaignUI) -> None:
        """Initialize the CampaignUIRenderer."""
        self._ui = ui

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def render(self, surface: Surface) -> None:
        """Render the campaign screen based on current state."""
        ui = self._ui
        if not ui._visible or not ui._font_title:
            return

        if ui._state == "operation_select":
            self._render_operation_select(surface)
        elif ui._state == "briefing":
            self._render_briefing(surface)
        elif ui._state == "battle_select":
            self._render_battle_select(surface)
        elif ui._state == "preview":
            self._render_preview(surface)
        elif ui._state == "report":
            self._render_report(surface)
        elif ui._state == "campaign_end":
            self._render_campaign_end(surface)
        elif ui._state == "supply_procurement":
            self._render_supply_procurement(surface)

    # ------------------------------------------------------------------
    # Operation Select
    # ------------------------------------------------------------------

    def _render_operation_select(self, surface: Surface) -> None:
        """Render operation selection screen."""
        ui = self._ui
        assert (
            ui._font_title is not None
            and ui._font_normal is not None
            and ui._font_small is not None
        )
        sw, sh = surface.get_size()
        surface.fill(ui.BG_COLOR)
        ui._op_rects = {}

        # Header
        header_y = ui.MARGIN
        title_surf = ui._font_title.render("OPERATION MARKET GARDEN", True, ui.HIGHLIGHT_COLOR)
        surface.blit(title_surf, (sw // 2 - title_surf.get_width() // 2, header_y))

        sep_y = header_y + title_surf.get_height() + 8
        draw.line(surface, ui.BORDER_COLOR, (ui.MARGIN, sep_y), (sw - ui.MARGIN, sep_y), 1)

        # Operation list
        list_y = sep_y + 10
        list_h = sh - list_y - ui.BUTTON_HEIGHT - ui.MARGIN * 2 - 10
        list_x = sw // 2 - ui.OP_LIST_WIDTH // 2
        list_w = ui.OP_LIST_WIDTH

        draw.rect(surface, ui.PANEL_COLOR, Rect(list_x, list_y, list_w, list_h))
        draw.rect(surface, ui.BORDER_COLOR, Rect(list_x, list_y, list_w, list_h), 1)

        list_title = ui._font_normal.render("SELECT OPERATION", True, ui.HIGHLIGHT_COLOR)
        surface.blit(list_title, (list_x + 8, list_y + 4))
        draw.line(
            surface, ui.BORDER_COLOR, (list_x, list_y + 24), (list_x + list_w, list_y + 24), 1
        )

        item_y = list_y + 28
        for op in ui._operations:
            if item_y + ui.BATTLE_ITEM_HEIGHT > list_y + list_h:
                break

            item_rect = Rect(list_x + 4, item_y, list_w - 8, ui.BATTLE_ITEM_HEIGHT - 4)
            ui._op_rects[op.operation_id] = item_rect

            is_selected = op.operation_id == ui._selected_op_id
            is_hovered = op.operation_id == ui._hovered_op_id

            if is_selected:
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

            # Day badge
            day_surf = ui._font_small.render(f"Day {op.day}/{op.total_days}", True, (180, 180, 170))
            surface.blit(day_surf, (item_rect.left + 6, item_rect.top + 4))

            # Operation name
            name_surf = ui._font_normal.render(op.name, True, ui.TEXT_COLOR)
            surface.blit(name_surf, (item_rect.left + 60, item_rect.top + 4))

            # Completed count
            completed = sum(1 for b in op.battles if b.completed)
            total = len(op.battles)
            if total > 0:
                prog_surf = ui._font_small.render(
                    f"{completed}/{total}",
                    True,
                    ui.COMPLETED_COLOR if completed == total else (180, 180, 170),
                )
                surface.blit(prog_surf, (item_rect.right - 40, item_rect.top + 4))

            item_y += ui.BATTLE_ITEM_HEIGHT

        # Buttons
        btn_y = sh - ui.BUTTON_HEIGHT - ui.MARGIN
        ui._proceed_button_rect = Rect(
            sw // 2 - ui.BUTTON_WIDTH - 5, btn_y, ui.BUTTON_WIDTH, ui.BUTTON_HEIGHT
        )
        ui._back_button_rect = Rect(sw // 2 + 5, btn_y, ui.BUTTON_WIDTH, ui.BUTTON_HEIGHT)

        draw_button(
            ui, surface, ui._proceed_button_rect, "Proceed", ui._hovered_button == "proceed"
        )
        draw_button(
            ui, surface, ui._back_button_rect, "Back", ui._hovered_button == "back", ui.TEXT_COLOR
        )

    # ------------------------------------------------------------------
    # Briefing
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Battle Select
    # ------------------------------------------------------------------

    def _render_battle_select(self, surface: Surface) -> None:
        """Render battle selection screen (original layout)."""
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
            msg = ui._font_normal.render("No campaign loaded", True, ui.TEXT_COLOR)
            surface.blit(msg, (sw // 2 - msg.get_width() // 2, sh // 2))
            return

        op = ui._current_operation

        # Header
        header_y = ui.MARGIN
        title_surf = ui._font_title.render(op.name, True, ui.HIGHLIGHT_COLOR)
        surface.blit(title_surf, (ui.MARGIN, header_y))

        day_surf = ui._font_normal.render(f"Day {op.day} of {op.total_days}", True, ui.TEXT_COLOR)
        surface.blit(day_surf, (sw - ui.MARGIN - day_surf.get_width(), header_y + 6))

        sep_y = header_y + title_surf.get_height() + 8
        draw.line(surface, ui.BORDER_COLOR, (ui.MARGIN, sep_y), (sw - ui.MARGIN, sep_y), 1)

        # Description
        desc_y = sep_y + 10
        if op.description:
            desc_surf = ui._font_small.render(op.description, True, (180, 180, 170))
            surface.blit(desc_surf, (ui.MARGIN, desc_y))
            desc_y += desc_surf.get_height() + 8

        # Battle list panel
        list_y = desc_y + 5
        list_h = sh - list_y - ui.BUTTON_HEIGHT - ui.MARGIN * 2 - 10
        list_x = ui.MARGIN
        list_w = min(ui.BATTLE_LIST_WIDTH, sw - ui.MARGIN * 2)

        draw.rect(surface, ui.PANEL_COLOR, Rect(list_x, list_y, list_w, list_h))
        draw.rect(surface, ui.BORDER_COLOR, Rect(list_x, list_y, list_w, list_h), 1)

        list_title = ui._font_normal.render("BATTLES", True, ui.HIGHLIGHT_COLOR)
        surface.blit(list_title, (list_x + 8, list_y + 4))
        draw.line(
            surface, ui.BORDER_COLOR, (list_x, list_y + 24), (list_x + list_w, list_y + 24), 1
        )

        item_y = list_y + 28
        visible_battles = op.battles[ui._scroll_offset :]
        for battle in visible_battles:
            if item_y + ui.BATTLE_ITEM_HEIGHT > list_y + list_h:
                break

            item_rect = Rect(list_x + 4, item_y, list_w - 8, ui.BATTLE_ITEM_HEIGHT - 4)
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

        # Right panel: selected battle description
        right_x = list_x + list_w + 15
        right_w = sw - right_x - ui.MARGIN
        if right_w > 100:
            draw.rect(surface, ui.PANEL_COLOR, Rect(right_x, list_y, right_w, list_h))
            draw.rect(surface, ui.BORDER_COLOR, Rect(right_x, list_y, right_w, list_h), 1)

            sel_battle = None
            if ui._selected_battle_id:
                sel_battle = next(
                    (b for b in op.battles if b.battle_id == ui._selected_battle_id), None
                )

            if sel_battle:
                bt_title = ui._font_normal.render(sel_battle.name, True, ui.HIGHLIGHT_COLOR)
                surface.blit(bt_title, (right_x + 8, list_y + 8))

                if sel_battle.description:
                    dy = list_y + 32
                    for line in wrap_text(sel_battle.description, ui._font_small, right_w - 20):
                        if dy + 16 > list_y + list_h:
                            break
                        ls = ui._font_small.render(line, True, (180, 180, 170))
                        surface.blit(ls, (right_x + 8, dy))
                        dy += 16

                if sel_battle.map_file:
                    map_label = ui._font_small.render(
                        f"Map: {sel_battle.map_file}", True, (150, 150, 140)
                    )
                    surface.blit(map_label, (right_x + 8, list_y + list_h - 22))
            else:
                hint = ui._font_small.render("Select a battle", True, (128, 128, 128))
                surface.blit(hint, (right_x + 8, list_y + 8))

        # Buttons
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

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------

    def _render_report(self, surface: Surface) -> None:
        """Render post-battle report with narrative elements."""
        ui = self._ui
        assert (
            ui._font_title is not None
            and ui._font_normal is not None
            and ui._font_small is not None
        )
        sw, sh = surface.get_size()
        surface.fill(ui.BG_COLOR)

        result = ui._battle_result or {}

        # Victory/Defeat banner
        is_victory = result.get("victory", False)
        victor = result.get("winner", "allies" if is_victory else "axis")
        if is_victory or victor == "allies":
            banner_color = ui.VICTORY_COLOR
            banner_text = "VICTORY"
        elif victor == "axis":
            banner_color = ui.DEFEAT_COLOR
            banner_text = "DEFEAT"
        else:
            banner_color = ui.HIGHLIGHT_COLOR
            banner_text = "DRAW"

        banner_y = ui.MARGIN
        banner_surf = ui._font_title.render(banner_text, True, banner_color)
        surface.blit(banner_surf, (sw // 2 - banner_surf.get_width() // 2, banner_y))

        sep_y = banner_y + banner_surf.get_height() + 8
        draw.line(surface, ui.BORDER_COLOR, (ui.MARGIN, sep_y), (sw - ui.MARGIN, sep_y), 1)

        # Battle name
        battle_name = result.get("battle_name", "Unknown Battle")
        name_surf = ui._font_normal.render(battle_name, True, ui.HIGHLIGHT_COLOR)
        surface.blit(name_surf, (sw // 2 - name_surf.get_width() // 2, sep_y + 8))

        # Narrative summary section
        narrative_y = sep_y + 36
        narrative_h = sh - narrative_y - ui.BUTTON_HEIGHT - ui.MARGIN * 2 - 10

        # Left panel: Narrative battle summary
        left_w = (sw - ui.MARGIN * 3) // 2
        left_x = ui.MARGIN
        draw.rect(surface, ui.PANEL_COLOR, Rect(left_x, narrative_y, left_w, narrative_h))
        draw.rect(surface, ui.BORDER_COLOR, Rect(left_x, narrative_y, left_w, narrative_h), 1)

        nar_title = ui._font_normal.render("BATTLE SUMMARY", True, ui.HIGHLIGHT_COLOR)
        surface.blit(nar_title, (left_x + 8, narrative_y + 4))
        draw.line(
            surface,
            ui.BORDER_COLOR,
            (left_x, narrative_y + 24),
            (left_x + left_w, narrative_y + 24),
            1,
        )

        dy = narrative_y + 30
        narrative_lines = self._generate_narrative_report(result)
        for line in narrative_lines:
            if dy + 16 > narrative_y + narrative_h:
                break
            if line.startswith("---"):
                # Section header
                line_surf = ui._font_normal.render(line, True, ui.HIGHLIGHT_COLOR)
            elif "Killed in Action" in line:
                line_surf = ui._font_small.render(line, True, ui.DEFEAT_COLOR)
            elif any(
                kw in line
                for kw in ["commendation", "heroic", "held the line", "rallied", "distinguished"]
            ):
                line_surf = ui._font_small.render(line, True, ui.COMPLETED_COLOR)
            else:
                line_surf = ui._font_small.render(line, True, (200, 200, 190))
            surface.blit(line_surf, (left_x + 8, dy))
            dy += 16

        # Right panel: Casualties & Experience
        right_x = ui.MARGIN * 2 + left_w
        right_w = sw - right_x - ui.MARGIN
        draw.rect(surface, ui.PANEL_COLOR, Rect(right_x, narrative_y, right_w, narrative_h))
        draw.rect(surface, ui.BORDER_COLOR, Rect(right_x, narrative_y, right_w, narrative_h), 1)

        # Casualties section
        cas_title = ui._font_normal.render("CASUALTIES", True, ui.HIGHLIGHT_COLOR)
        surface.blit(cas_title, (right_x + 8, narrative_y + 4))
        draw.line(
            surface,
            ui.BORDER_COLOR,
            (right_x, narrative_y + 24),
            (right_x + right_w, narrative_y + 24),
            1,
        )

        dy = narrative_y + 30
        casualties = result.get("casualties", {})
        if casualties:
            for side, data in casualties.items():
                side_label = ui._font_normal.render(f"{side}:", True, ui.TEXT_COLOR)
                surface.blit(side_label, (right_x + 8, dy))
                dy += 20
                if isinstance(data, dict):
                    for key, val in data.items():
                        if dy + 16 > narrative_y + narrative_h:
                            break
                        entry = ui._font_small.render(f"  {key}: {val}", True, (180, 180, 170))
                        surface.blit(entry, (right_x + 8, dy))
                        dy += 16
                else:
                    entry = ui._font_small.render(f"  Total: {data}", True, (180, 180, 170))
                    surface.blit(entry, (right_x + 8, dy))
                    dy += 16
                dy += 6
        else:
            no_data = ui._font_small.render("No casualty data available", True, (128, 128, 128))
            surface.blit(no_data, (right_x + 8, dy))
            dy += 16

        # Experience section
        dy += 10
        exp_title = ui._font_normal.render("EXPERIENCE", True, ui.HIGHLIGHT_COLOR)
        surface.blit(exp_title, (right_x + 8, dy))
        draw.line(surface, ui.BORDER_COLOR, (right_x, dy + 20), (right_x + right_w, dy + 20), 1)
        dy += 26

        experience = result.get("experience", {})
        if experience:
            for key, val in experience.items():
                if dy + 16 > narrative_y + narrative_h:
                    break
                entry = ui._font_small.render(f"  {key}: {val}", True, (180, 180, 170))
                surface.blit(entry, (right_x + 8, dy))
                dy += 16
        else:
            no_data = ui._font_small.render("No experience data available", True, (128, 128, 128))
            surface.blit(no_data, (right_x + 8, dy))

        # Buttons
        btn_y = sh - ui.BUTTON_HEIGHT - ui.MARGIN
        ui._continue_button_rect = Rect(
            sw - ui.MARGIN - ui.BUTTON_WIDTH * 2 - 10,
            btn_y,
            ui.BUTTON_WIDTH,
            ui.BUTTON_HEIGHT,
        )
        ui._back_button_rect = Rect(
            sw - ui.MARGIN - ui.BUTTON_WIDTH, btn_y, ui.BUTTON_WIDTH, ui.BUTTON_HEIGHT
        )

        draw_button(
            ui, surface, ui._continue_button_rect, "Continue", ui._hovered_button == "continue"
        )
        draw_button(
            ui, surface, ui._back_button_rect, "Back", ui._hovered_button == "back", ui.TEXT_COLOR
        )

    @staticmethod
    def _generate_narrative_report(result: dict) -> list[str]:
        """Generate a narrative post-battle report."""
        lines = []

        # Header
        victor = result.get("winner", "unknown")
        is_victory = result.get("victory", False)
        if is_victory or victor == "allies":
            lines.append("Allied forces have secured the objective!")
        elif victor == "axis":
            lines.append("Axis forces have prevailed.")
        else:
            lines.append("Neither side achieved decisive victory.")

        lines.append("")

        # Key events narrative
        events = result.get("key_events", [])
        if events:
            lines.append("--- Key Events ---")
            for event in events:
                lines.append(f"  {event}")

        # Casualties with names
        allied_kia = result.get("allied_kia", [])
        if allied_kia:
            lines.append("")
            lines.append("--- Fallen ---")
            for name in allied_kia:
                lines.append(f"  {name} - Killed in Action")

        # Heroic actions
        heroic = result.get("heroic_actions", [])
        if heroic:
            lines.append("")
            lines.append("--- Commendations ---")
            for action in heroic:
                lines.append(f"  {action}")

        # If no narrative data, show basic summary
        if not events and not allied_kia and not heroic:
            lines.append("")
            lines.append("--- Summary ---")
            casualties = result.get("casualties", {})
            if casualties:
                for side, data in casualties.items():
                    if isinstance(data, dict):
                        kia = data.get("killed", data.get("KIA", 0))
                        wounded = data.get("wounded", data.get("Wounded", 0))
                        if kia or wounded:
                            lines.append(f"  {side}: {kia} KIA, {wounded} Wounded")
                    else:
                        lines.append(f"  {side}: {data} casualties")
            else:
                lines.append("  No significant casualties reported.")

        return lines

    # ------------------------------------------------------------------
    # Campaign End
    # ------------------------------------------------------------------

    def _render_campaign_end(self, surface: Surface) -> None:
        """Render the campaign end screen with historical outcome, casualties, and bridge status."""
        ui = self._ui
        assert (
            ui._font_title is not None
            and ui._font_normal is not None
            and ui._font_small is not None
        )
        sw, sh = surface.get_size()
        surface.fill(ui.BG_COLOR)

        summary = ui._campaign_summary or {}
        result = summary.get("result", "DRAW")
        day_ended = summary.get("day_ended", 9)
        allied_cas = summary.get("allied_casualties", {"kia": 0, "wia": 0})
        axis_cas = summary.get("axis_casualties", {"kia": 0, "wia": 0})
        bridge_status = summary.get("bridge_status", {})

        # --- Title banner ---
        if result == "ALLIES_VICTORY":
            banner_color = ui.VICTORY_COLOR
            result_text = "VICTORY"
            subtitle = "XXX Corps reached Arnhem!"
            historical = (
                "The Allied airborne assault succeeded. British 1st Airborne held the "
                "bridge at Arnhem long enough for XXX Corps to relieve them. The road to "
                "the Ruhr lies open."
            )
        elif result == "AXIS_VICTORY":
            banner_color = ui.DEFEAT_COLOR
            result_text = "DEFEAT"
            subtitle = "The Bridge at Arnhem holds"
            historical = (
                "The German defenses proved too strong. The British 1st Airborne was "
                "destroyed at Arnhem, and XXX Corps could not break through in time. "
                "Market Garden has failed."
            )
        else:
            banner_color = ui.HIGHLIGHT_COLOR
            result_text = "DRAW"
            subtitle = "Neither side achieved decisive victory"
            historical = (
                "The operation ended inconclusively. Some objectives were taken, but "
                "the key bridge at Arnhem remains contested. Both sides suffered "
                "heavily."
            )

        # Full-screen overlay with semi-transparent background
        overlay = Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((20, 24, 30, 230))
        surface.blit(overlay, (0, 0))

        # Title
        header_y = ui.MARGIN + 10
        title_surf = ui._font_title.render("OPERATION MARKET GARDEN", True, ui.HIGHLIGHT_COLOR)
        surface.blit(title_surf, (sw // 2 - title_surf.get_width() // 2, header_y))

        # Result banner
        banner_y = header_y + title_surf.get_height() + 12
        result_surf = ui._font_title.render(result_text, True, banner_color)
        surface.blit(result_surf, (sw // 2 - result_surf.get_width() // 2, banner_y))

        # Subtitle
        sub_y = banner_y + result_surf.get_height() + 8
        sub_surf = ui._font_normal.render(subtitle, True, ui.TEXT_COLOR)
        surface.blit(sub_surf, (sw // 2 - sub_surf.get_width() // 2, sub_y))

        # Separator
        sep_y = sub_y + sub_surf.get_height() + 10
        draw.line(surface, ui.BORDER_COLOR, (ui.MARGIN, sep_y), (sw - ui.MARGIN, sep_y), 1)

        # --- Left panel: Historical text + Bridge status ---
        left_w = (sw - ui.MARGIN * 3) // 2
        left_x = ui.MARGIN
        content_y = sep_y + 10
        content_h = sh - content_y - ui.BUTTON_HEIGHT - ui.MARGIN * 2 - 10

        draw.rect(surface, ui.PANEL_COLOR, Rect(left_x, content_y, left_w, content_h))
        draw.rect(surface, ui.BORDER_COLOR, Rect(left_x, content_y, left_w, content_h), 1)

        # Historical text
        hist_title = ui._font_normal.render("HISTORICAL OUTCOME", True, ui.HIGHLIGHT_COLOR)
        surface.blit(hist_title, (left_x + 10, content_y + 8))
        draw.line(
            surface,
            ui.BORDER_COLOR,
            (left_x, content_y + 28),
            (left_x + left_w, content_y + 28),
            1,
        )

        dy = content_y + 34
        for line in wrap_text(historical, ui._font_normal, left_w - 30):
            if dy + 20 > content_y + content_h // 2:
                break
            ls = ui._font_normal.render(line, True, (200, 200, 190))
            surface.blit(ls, (left_x + 10, dy))
            dy += 22

        # Day ended
        dy += 8
        day_surf = ui._font_normal.render(f"Day {day_ended} of 9", True, ui.HIGHLIGHT_COLOR)
        surface.blit(day_surf, (left_x + 10, dy))

        # Bridge status section
        bridge_section_y = content_y + content_h // 2 + 5
        bridge_title = ui._font_normal.render("BRIDGE STATUS", True, ui.HIGHLIGHT_COLOR)
        surface.blit(bridge_title, (left_x + 10, bridge_section_y))
        draw.line(
            surface,
            ui.BORDER_COLOR,
            (left_x, bridge_section_y + 22),
            (left_x + left_w, bridge_section_y + 22),
            1,
        )

        dy = bridge_section_y + 28
        if bridge_status:
            for bridge_name, status in bridge_status.items():
                if dy + 18 > content_y + content_h:
                    break
                if status == "captured_allied":
                    status_color = ui.COMPLETED_COLOR
                    status_label = "Captured (Allied)"
                elif status == "captured_axis":
                    status_color = ui.DEFEAT_COLOR
                    status_label = "Held (Axis)"
                else:
                    status_color = ui.HIGHLIGHT_COLOR
                    status_label = "Contested"
                name_surf = ui._font_small.render(bridge_name, True, ui.TEXT_COLOR)
                surface.blit(name_surf, (left_x + 10, dy))
                status_surf = ui._font_small.render(status_label, True, status_color)
                surface.blit(status_surf, (left_x + left_w - status_surf.get_width() - 10, dy))
                dy += 18
        else:
            no_data = ui._font_small.render("No bridge data available", True, (128, 128, 128))
            surface.blit(no_data, (left_x + 10, dy))

        # --- Right panel: Casualties table ---
        right_x = ui.MARGIN * 2 + left_w
        right_w = sw - right_x - ui.MARGIN
        draw.rect(surface, ui.PANEL_COLOR, Rect(right_x, content_y, right_w, content_h))
        draw.rect(surface, ui.BORDER_COLOR, Rect(right_x, content_y, right_w, content_h), 1)

        cas_title = ui._font_normal.render("TOTAL CASUALTIES", True, ui.HIGHLIGHT_COLOR)
        surface.blit(cas_title, (right_x + 10, content_y + 8))
        draw.line(
            surface,
            ui.BORDER_COLOR,
            (right_x, content_y + 28),
            (right_x + right_w, content_y + 28),
            1,
        )

        # Table header
        dy = content_y + 36
        col_x_side = right_x + 10
        col_x_kia = right_x + right_w // 3
        col_x_wia = right_x + 2 * right_w // 3

        hdr_surf = ui._font_normal.render("Side", True, ui.HIGHLIGHT_COLOR)
        surface.blit(hdr_surf, (col_x_side, dy))
        kia_hdr = ui._font_normal.render("KIA", True, ui.HIGHLIGHT_COLOR)
        surface.blit(kia_hdr, (col_x_kia, dy))
        wia_hdr = ui._font_normal.render("WIA", True, ui.HIGHLIGHT_COLOR)
        surface.blit(wia_hdr, (col_x_wia, dy))

        dy += 26
        draw.line(
            surface, ui.BORDER_COLOR, (right_x + 5, dy - 4), (right_x + right_w - 5, dy - 4), 1
        )

        # Allied row
        allied_label = ui._font_normal.render("Allies", True, ui.COMPLETED_COLOR)
        surface.blit(allied_label, (col_x_side, dy))
        allied_kia = ui._font_normal.render(str(allied_cas.get("kia", 0)), True, ui.DEFEAT_COLOR)
        surface.blit(allied_kia, (col_x_kia, dy))
        allied_wia = ui._font_normal.render(str(allied_cas.get("wia", 0)), True, ui.HIGHLIGHT_COLOR)
        surface.blit(allied_wia, (col_x_wia, dy))

        dy += 28

        # Axis row
        axis_label = ui._font_normal.render("Axis", True, ui.DEFEAT_COLOR)
        surface.blit(axis_label, (col_x_side, dy))
        axis_kia = ui._font_normal.render(str(axis_cas.get("kia", 0)), True, ui.DEFEAT_COLOR)
        surface.blit(axis_kia, (col_x_kia, dy))
        axis_wia = ui._font_normal.render(str(axis_cas.get("wia", 0)), True, ui.HIGHLIGHT_COLOR)
        surface.blit(axis_wia, (col_x_wia, dy))

        # MIA note
        dy += 40
        mia_note = ui._font_small.render(
            "MIA: Included in KIA for campaign accounting", True, (128, 128, 128)
        )
        surface.blit(mia_note, (right_x + 10, dy))

        # --- Buttons ---
        btn_y = sh - ui.BUTTON_HEIGHT - ui.MARGIN
        ui._new_campaign_button_rect = Rect(
            sw // 2 - ui.BUTTON_WIDTH - 10, btn_y, ui.BUTTON_WIDTH, ui.BUTTON_HEIGHT
        )
        ui._main_menu_button_rect = Rect(sw // 2 + 10, btn_y, ui.BUTTON_WIDTH, ui.BUTTON_HEIGHT)

        draw_button(
            ui,
            surface,
            ui._new_campaign_button_rect,
            "New Campaign",
            ui._hovered_button == "new_campaign",
        )
        draw_button(
            ui,
            surface,
            ui._main_menu_button_rect,
            "Main Menu",
            ui._hovered_button == "main_menu",
            ui.TEXT_COLOR,
        )

    # ------------------------------------------------------------------
    # Supply Procurement (P4-4)
    # ------------------------------------------------------------------

    def _render_supply_procurement(self, surface: Surface) -> None:
        """Render the supply procurement phase by delegating to SupplyProcurementUI.

        The :class:`SupplyProcurementUI` owns its full rendering pipeline
        (header, supply pool bar, per-sector rows, allocate buttons).
        We seed it with the campaign UI's normal font so the typography
        stays consistent with the rest of the campaign screens.

        """
        ui = self._ui
        supply_ui = ui._supply_procurement_ui
        # The supply UI is a no-op when its manager is unbound; this guard
        # keeps the screen from going blank if the state is entered without
        # a prior show_supply_procurement() call.
        if supply_ui.manager is None:
            surface.fill(ui.BG_COLOR)
            assert ui._font_normal is not None
            msg = ui._font_normal.render(
                "Supply procurement unavailable", True, ui.TEXT_COLOR
            )
            surface.blit(msg, (ui.MARGIN, ui.MARGIN))
            return

        supply_ui.render(surface, ui._font_normal)
