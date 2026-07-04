"""Operation/battle selection screen rendering mixin — extracted from CampaignUIRenderer.

Extracted during Phase 2 P0-1 (2026-07-04). See ``campaign_ui_rendering.py``
facade for the public API entry point.

Provides:
  - ``_render_operation_select``: operation selection screen.
  - ``_render_battle_select``: battle selection screen (original layout).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pygame import Rect, Surface, draw

from .campaign_ui_helpers import draw_button, wrap_text

if TYPE_CHECKING:
    from .campaign_ui import CampaignUI


class CampaignUISelectMixin:
    """Mixin: operation and battle selection screens for CampaignUIRenderer.

    Relies on the facade's ``__init__`` to set ``self._ui``.
    """

    # -- Facade attribute set by CampaignUIRenderer.__init__ (typing only) --
    _ui: CampaignUI

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
